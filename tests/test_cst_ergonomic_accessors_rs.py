"""Emission tests for the ergonomic CST accessors on the Rust backend.

The planner in ``cst_ergonomics`` decides the member set once; ``gsm2tree_rs`` emits it three
more times — as native methods on the data struct, as pymethods on the handle, and as
declarations in the ``.pyi`` stub.  These tests cover:

  * the native surface — arity-typed signatures, borrowed ``&str`` text accessors, and the
    panic-on-violated-invariant contract that distinguishes it from the checked quintet;
  * the pymethod surface — delegation to the quintet (hence identical ``ValueError`` text) and
    the absence of panics;
  * the stub — protocol-wide parameters and stub-local returns, which keep each class assignable
    to its protocol counterpart while still letting concrete annotations descend a tree;
  * cross-surface parity — pymethods, stub and protocol declare the same ergonomic members.
"""

from __future__ import annotations

import ast
import pathlib
import re
from typing import Any

import pytest

from fltk import plumbing
from fltk.fegen import cst_ergonomics
from fltk.fegen.gsm2tree_rs import RustCstGenerator
from tests.pyright_test_utils import _diags_for_file, _run_pyright_over_dir, write_pyright_config

# A grammar exercising every plan decision the Rust surface has to encode:
#   doc      — required-single, optional-single and collection node labels
#   ident    — span label `text`, colliding with the rule-level text() reservation
#   tag      — required-single span label; terminal-only, so it gets text()
#   pair     — two required-single span labels; terminal-only
#   block    — collection of node children; not terminal-only
#   op       — keyword-enum dispatch: optional-single span labels + variant()
#   entity   — rule-reference dispatch: auto-labeled alternatives + variant()
#   mixed    — one label spanning alternatives with different child types (union label)
#   mix2     — span label alongside a node label: the child enum has more than one variant
#   optmix   — the same, with the span label optional
#   kwlbl    — labels that are Rust (`match`) and Python (`class`) keywords
GRAMMAR_TEXT = """
doc := name:ident , body:block? , tags:tag* ;
ident := text:/[a-z]+/ ;
tag := "#" . name:/[a-z]+/ ;
pair := key:/[a-z]+/ . "=" . value:/[0-9]+/ ;
block := "{" , items:ident* , "}" ;
op := plus:"+" | minus:"-" ;
entity := op | pair ;
mixed := thing:ident | thing:tag ;
mix2 := key:/[a-z]+/ , node:ident ;
optmix := key:/[a-z]+/? , node:ident ;
kwlbl := match:/[a-z]+/ . class:/[0-9]+/ ;
"""

_PROTOCOL_MODULE = "ergo_cst_protocol"

# Fixed members of the generated surfaces, on every backend.  Ergonomic members can never be
# named one of these (the planner seeds them into its claim table), so subtracting them isolates
# the ergonomic surface for parity comparison.
_FIXED_MEMBERS = (cst_ergonomics.RESERVED_MEMBER_NAMES - cst_ergonomics.RULE_MEMBER_NAMES) | {
    "__eq__",
    "__hash__",
    "__repr__",
    "_fltk_canonical_name",
}


@pytest.fixture(scope="module")
def generator() -> RustCstGenerator:
    return RustCstGenerator(plumbing.parse_grammar(GRAMMAR_TEXT), source_name="ergo.fltkg")


@pytest.fixture(scope="module")
def rust_src(generator: RustCstGenerator) -> str:
    return generator.generate()


@pytest.fixture(scope="module")
def pyi_text(generator: RustCstGenerator) -> str:
    return generator.generate_pyi(_PROTOCOL_MODULE)


@pytest.fixture(scope="module")
def protocol_text(generator: RustCstGenerator) -> str:
    return generator.generate_protocol()


# ---------------------------------------------------------------------------
# Source-slicing helpers
# ---------------------------------------------------------------------------

_FN_RE = re.compile(r"^    (?:pub )?fn (?:r#)?(\w+)\(", re.MULTILINE)
_RENAMED_FN_RE = re.compile(r'^    #\[pyo3\(name = "(\w+)"\)\]\n    (?:pub )?fn (?:r#)?(\w+)\(', re.MULTILINE)


def _block(src: str, header: str) -> str:
    """Return the impl block introduced by ``header``, up to its closing brace at column 0."""
    idx = src.find(header)
    assert idx >= 0, f"block not found: {header!r}"
    body = src[idx:].splitlines()
    out = [body[0]]
    for line in body[1:]:
        if line == "}":
            break
        out.append(line)
    return "\n".join(out)


def native_block(src: str, class_name: str) -> str:
    """The plain ``impl <Class>`` block carrying the GIL-free API."""
    return _block(src, f"\nimpl {class_name} {{\n")


def pymethods_block(src: str, class_name: str) -> str:
    """The ``#[pymethods] impl Py<Class>`` block carrying the Python-visible API."""
    return _block(src, f"#[pymethods]\nimpl Py{class_name} {{\n")


def python_visible_names(block: str) -> set[str]:
    """Method names a pymethods block exposes to Python, honouring ``#[pyo3(name = ...)]``."""
    renamed = {rust_name: py_name for py_name, rust_name in _RENAMED_FN_RE.findall(block)}
    return {renamed.get(name, name) for name in _FN_RE.findall(block)}


def ergonomic_names(names: set[str], labels: set[str]) -> set[str]:
    """Strip the fixed and quintet members, leaving the ergonomic surface."""
    quintet = {name for label in labels for name in cst_ergonomics.quintet_member_names(label)}
    return names - _FIXED_MEMBERS - quintet


def class_defs(module_text: str) -> dict[str, ast.ClassDef]:
    return {stmt.name: stmt for stmt in ast.parse(module_text).body if isinstance(stmt, ast.ClassDef)}


def stub_signature(pyi_text: str, class_name: str, method: str) -> str:
    """The full ``def`` line for one method of one stub class."""
    klass = class_defs(pyi_text)[class_name]
    for stmt in klass.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == method:
            return ast.unparse(stmt).splitlines()[0]
    msg = f"{method}() not declared on stub class {class_name}"
    raise AssertionError(msg)


class TestNativeBareAccessors:
    def test_required_single_node_label(self, rust_src: str) -> None:
        block = native_block(rust_src, "Doc")
        assert "pub fn name(&self) -> &Shared<Ident> {" in block
        assert "self.child_name()" in block

    def test_optional_single_node_label(self, rust_src: str) -> None:
        assert "pub fn body(&self) -> ::std::option::Option<&Shared<Block>> {" in native_block(rust_src, "Doc")

    def test_collection_label_is_an_iterator(self, rust_src: str) -> None:
        block = native_block(rust_src, "Doc")
        assert "pub fn tags(&self) -> impl ::std::iter::Iterator<Item = &Shared<Tag>> + '_ {" in block
        assert "        self.children_tags()" in block

    def test_union_typed_label_returns_the_child_enum(self, rust_src: str) -> None:
        assert "pub fn thing(&self) -> &MixedChild {" in native_block(rust_src, "Mixed")

    def test_span_label_returns_a_span_reference(self, rust_src: str) -> None:
        assert "pub fn key(&self) -> &Span {" in native_block(rust_src, "Pair")

    def test_rust_keyword_label_uses_a_raw_identifier(self, rust_src: str) -> None:
        assert "pub fn r#match(&self) -> &Span {" in native_block(rust_src, "Kwlbl")

    def test_python_keyword_label_is_skipped(self, rust_src: str) -> None:
        """`class` is unspellable on the Python surface, so neither backend gets the accessor."""
        block = native_block(rust_src, "Kwlbl")
        assert "pub fn class(" not in block
        assert "pub fn class_text(&self) -> &str {" in block

    def test_accessors_panic_naming_class_and_label(self, rust_src: str) -> None:
        assert 'panic!("Doc.name: {e}")' in native_block(rust_src, "Doc")


class TestNativeTextAccessors:
    def test_required_single_borrows_a_str(self, rust_src: str) -> None:
        block = native_block(rust_src, "Tag")
        assert "pub fn name_text(&self) -> &str {" in block
        assert ".text_or_message()" in block

    def test_optional_single_borrows_an_option(self, rust_src: str) -> None:
        assert "pub fn plus_text(&self) -> ::std::option::Option<&str> {" in native_block(rust_src, "Op")

    def test_absent_for_node_labels(self, rust_src: str) -> None:
        assert "pub fn name_text" not in native_block(rust_src, "Doc")

    def test_absent_for_collection_labels(self, rust_src: str) -> None:
        assert "pub fn items_text" not in native_block(rust_src, "Block")


class TestNativeRuleMembers:
    def test_text_on_terminal_only_rule(self, rust_src: str) -> None:
        block = native_block(rust_src, "Pair")
        assert "pub fn text(&self) -> &str {" in block
        assert "        self.span" in block

    def test_no_text_on_rule_with_node_children(self, rust_src: str) -> None:
        assert "pub fn text(&self) -> &str {" not in native_block(rust_src, "Doc")

    def test_variant_returns_the_label_enum(self, rust_src: str) -> None:
        block = native_block(rust_src, "Op")
        assert "pub fn variant(&self) -> OpLabel {" in block
        assert 'expect("Op.variant: node has no labeled child")' in block

    def test_variant_on_rule_reference_dispatch(self, rust_src: str) -> None:
        assert "pub fn variant(&self) -> EntityLabel {" in native_block(rust_src, "Entity")

    def test_no_variant_on_single_alternative_rule(self, rust_src: str) -> None:
        assert "pub fn variant" not in native_block(rust_src, "Doc")


class TestPymethodDelegation:
    def test_required_single_delegates_to_child(self, rust_src: str) -> None:
        block = pymethods_block(rust_src, "Doc")
        expected = (
            "    fn name(&self, py: Python<'_>) -> pyo3::PyResult<Py<pyo3::PyAny>> {\n        self.child_name(py)"
        )
        assert expected in block

    def test_optional_single_delegates_to_maybe(self, rust_src: str) -> None:
        block = pymethods_block(rust_src, "Doc")
        assert "-> pyo3::PyResult<::std::option::Option<Py<pyo3::PyAny>>> {\n        self.maybe_body(py)" in block

    def test_collection_delegates_to_the_snapshot_helper_and_returns_a_list(self, rust_src: str) -> None:
        block = pymethods_block(rust_src, "Doc")
        assert (
            "-> pyo3::PyResult<Py<pyo3::types::PyList>> {\n"
            "        self.py_children_snapshot(py, &DocLabel::Tags)" in block
        )
        assert "fn py_children_snapshot" not in block

    def test_the_snapshot_helper_is_emitted_once_per_class(self, rust_src: str) -> None:
        """The body is label-invariant, so it takes the label rather than being emitted per label."""
        assert rust_src.count("fn py_children_snapshot(&self, py: Python<'_>, label: &DocLabel)") == 1

    def test_rust_keyword_label_keeps_its_python_name(self, rust_src: str) -> None:
        assert '#[pyo3(name = "match")]\n    fn r#match(' in pymethods_block(rust_src, "Kwlbl")

    def test_no_pymethod_panics(self, rust_src: str) -> None:
        """The panic contract is native-only; the Python surface raises instead.

        A panic in a pymethod unwinds across the FFI boundary rather than becoming a Python
        exception, so `panic!` and `.unwrap()` are banned outright.  `.expect(...)` survives only
        for arms that are unreachable by construction, which the message must say.
        """
        for class_name in ("Doc", "Tag", "Op", "Pair", "Mix2", "Optmix", "Entity"):
            block = pymethods_block(rust_src, class_name)
            assert "panic!" not in block, class_name
            assert ".unwrap()" not in block, class_name
            for message in re.findall(r'\.expect\(\s*"([^"]*)', block):
                assert message.startswith("invariant: "), (class_name, message)


class TestPymethodTextAccessors:
    def test_required_single_mirrors_the_child_count_message(self, rust_src: str) -> None:
        block = pymethods_block(rust_src, "Tag")
        assert "    fn name_text(&self) -> pyo3::PyResult<::std::string::String> {" in block
        assert '"Expected one name child but have {count}"' in block

    def test_optional_single_mirrors_the_maybe_count_message(self, rust_src: str) -> None:
        block = pymethods_block(rust_src, "Op")
        assert "    fn plus_text(&self) -> pyo3::PyResult<::std::option::Option<::std::string::String>> {" in block
        assert '"Expected at most one plus child but have at least 2",' in block

    def test_wrong_child_variant_raises_type_error(self, rust_src: str) -> None:
        """Only reachable through the untyped mutators, so a distinct error rather than a lie."""
        assert "Mix2.key_text: child labelled 'key' is not a Span" in pymethods_block(rust_src, "Mix2")

    def test_optional_single_wrong_child_variant_raises_type_error(self, rust_src: str) -> None:
        """The optional arity carries the arm too, under `Some(_)` rather than `_`."""
        block = pymethods_block(rust_src, "Optmix")
        assert "    fn key_text(&self) -> pyo3::PyResult<::std::option::Option<::std::string::String>> {" in block
        arm = "Some(_) => Err(PyTypeError::new_err(\"Optmix.key_text: child labelled 'key' is not a Span\")),"
        assert arm in block

    def test_no_wrong_variant_arm_when_the_enum_is_span_only(self, rust_src: str) -> None:
        assert "is not a Span" not in pymethods_block(rust_src, "Tag")


class TestPymethodRuleMembers:
    def test_text_reads_the_nodes_own_span(self, rust_src: str) -> None:
        block = pymethods_block(rust_src, "Pair")
        assert "    fn text(&self) -> pyo3::PyResult<::std::string::String> {" in block
        assert "let span = self.inner.read().span.clone();" in block

    def test_variant_returns_the_label_enum(self, rust_src: str) -> None:
        block = pymethods_block(rust_src, "Op")
        assert "    fn variant(&self) -> pyo3::PyResult<OpLabel> {" in block
        assert '"Op.variant: node has no labeled child",' in block


class TestPyiEmission:
    """Node-typed returns name the stub's own classes; only parameters stay protocol-wide.

    A consumer annotated against these classes can descend the tree with the accessors, which a
    ``_proto.``-qualified return would forbid.
    """

    def test_required_single(self, pyi_text: str) -> None:
        assert stub_signature(pyi_text, "Doc", "name") == "def name(self) -> Ident:"

    def test_optional_single(self, pyi_text: str) -> None:
        assert stub_signature(pyi_text, "Doc", "body") == "def body(self) -> typing.Optional[Block]:"

    def test_collection(self, pyi_text: str) -> None:
        assert stub_signature(pyi_text, "Doc", "tags") == "def tags(self) -> list[Tag]:"

    def test_accessor_quintet_splits_parameters_from_returns(self, pyi_text: str) -> None:
        """The quintet carries both positions for one label, so it pins the rule end to end."""
        assert stub_signature(pyi_text, "Doc", "append_tags") == "def append_tags(self, child: _proto.Tag) -> None:"
        assert (
            stub_signature(pyi_text, "Doc", "extend_tags")
            == "def extend_tags(self, children: typing.Iterable[_proto.Tag]) -> None:"
        )
        assert stub_signature(pyi_text, "Doc", "children_tags") == "def children_tags(self) -> typing.Iterator[Tag]:"
        assert stub_signature(pyi_text, "Doc", "child_tags") == "def child_tags(self) -> Tag:"
        assert stub_signature(pyi_text, "Doc", "maybe_tags") == "def maybe_tags(self) -> typing.Optional[Tag]:"

    def test_generic_mutators_and_readers_split_the_same_way(self, pyi_text: str) -> None:
        klass = class_defs(pyi_text)["Doc"]
        children = next(
            stmt for stmt in klass.body if isinstance(stmt, ast.AnnAssign) and ast.unparse(stmt.target) == "children"
        )
        assert "_proto." not in ast.unparse(children.annotation)
        assert "_proto." not in stub_signature(pyi_text, "Doc", "child")
        assert "_proto." not in stub_signature(pyi_text, "Doc", "remove_at")
        assert "_proto." in stub_signature(pyi_text, "Doc", "append")
        assert "_proto." in stub_signature(pyi_text, "Doc", "insert")
        assert "_proto." in stub_signature(pyi_text, "Doc", "replace_at")
        # extend_children is the one parameter that names a whole node rather than a child union.
        assert (
            stub_signature(pyi_text, "Doc", "extend_children")
            == "def extend_children(self, other: _proto.Doc) -> None:"
        )

    def test_text_accessors(self, pyi_text: str) -> None:
        assert stub_signature(pyi_text, "Tag", "name_text") == "def name_text(self) -> str:"
        assert stub_signature(pyi_text, "Op", "plus_text") == "def plus_text(self) -> typing.Optional[str]:"

    def test_rule_text(self, pyi_text: str) -> None:
        assert stub_signature(pyi_text, "Pair", "text") == "def text(self) -> str:"

    def test_variant_uses_the_agnostic_label_protocol(self, pyi_text: str) -> None:
        """Annotating LabelProtocol, as the protocol does, is what keeps the stub assignable to it."""
        assert (
            stub_signature(pyi_text, "Op", "variant")
            == "def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol:"
        )

    def test_keyword_label_named_by_its_python_name(self, pyi_text: str) -> None:
        assert stub_signature(pyi_text, "Kwlbl", "match").startswith("def match(self) ->")


class TestSurfacesAgree:
    def test_plan_drives_every_surface(
        self, generator: RustCstGenerator, rust_src: str, pyi_text: str, protocol_text: str
    ) -> None:
        """pymethods, stub and protocol declare exactly the members the plan names."""
        pyi_classes = class_defs(pyi_text)
        protocol_classes = class_defs(protocol_text)
        for class_name, label_list, rule_name in generator._rule_info():
            plan = generator.plan_for_rule(rule_name)
            labels = set(label_list)

            expected = set(plan.bare_accessors) | {f"{label}_text" for label in plan.text_accessors}
            if plan.rule_text:
                expected.add("text")
            if plan.variant:
                expected.add("variant")

            handle = ergonomic_names(python_visible_names(pymethods_block(rust_src, class_name)), labels)
            stub = ergonomic_names(
                {stmt.name for stmt in pyi_classes[class_name].body if isinstance(stmt, ast.FunctionDef)}, labels
            )
            protocol = ergonomic_names(
                {stmt.name for stmt in protocol_classes[class_name].body if isinstance(stmt, ast.FunctionDef)}, labels
            )
            assert handle == expected, f"{class_name}: pymethods diverge from the plan"
            assert stub == expected, f"{class_name}: .pyi diverges from the plan"
            assert protocol == expected, f"{class_name}: protocol diverges from the plan"

    def test_skipped_members_appear_on_no_surface(
        self, generator: RustCstGenerator, rust_src: str, pyi_text: str
    ) -> None:
        pyi_classes = class_defs(pyi_text)
        for rule in generator.grammar.rules:
            plan = generator.plan_for_rule(rule.name)
            if not plan.skipped:
                continue
            class_name = generator.class_name_for_rule(rule.name)
            handle = python_visible_names(pymethods_block(rust_src, class_name))
            stub = {stmt.name for stmt in pyi_classes[class_name].body if isinstance(stmt, ast.FunctionDef)}
            for member in plan.skipped:
                # A skipped candidate name may still be taken by the member that won the claim
                # (e.g. the rule-level text()); what must not happen is a second declaration.
                assert len([n for n in handle if n == member.name]) <= 1
                assert sum(1 for n in stub if n == member.name) <= 1

    def test_plan_missing_for_unknown_rule(self, generator: RustCstGenerator) -> None:
        with pytest.raises(RuntimeError, match="No ergonomic member plan"):
            generator.plan_for_rule("no_such_rule")


@pytest.fixture(scope="module")
def stub_diagnostics(
    pyi_text: str,
    protocol_text: str,
    generator: RustCstGenerator,
    pyright_available: bool,  # noqa: FBT001
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[dict[str, Any]]]:
    """Type-check the stub against a protocol module generated from the same grammar."""
    tmpdir: pathlib.Path = tmp_path_factory.mktemp("ergonomic_accessors_rs_pyright")
    write_pyright_config(tmpdir)
    (tmpdir / "ergo_cst.pyi").write_text(pyi_text)
    (tmpdir / "ergo_cst.py").write_text("")
    (tmpdir / f"{_PROTOCOL_MODULE}.py").write_text(protocol_text + "\n")

    class_names = [generator.class_name_for_rule(rule.name) for rule in generator.grammar.rules]
    lines = [
        "# ruff: noqa",
        "from __future__ import annotations",
        f"import {_PROTOCOL_MODULE} as cstp",
        "import ergo_cst",
        "",
        "_m: cstp.CstModule = ergo_cst",
        "",
    ]
    for name in class_names:
        lines.append(f"def _check_{name.lower()}(x: ergo_cst.{name}) -> None:")
        lines.append(f"    _x: cstp.{name} = x")
        lines.append("")
    (tmpdir / "conformance_fixture.py").write_text("\n".join(lines))
    return _run_pyright_over_dir(tmpdir, pyright_available=pyright_available)


def test_stub_self_check(stub_diagnostics: dict[str, list[dict[str, Any]]]) -> None:
    errors = _diags_for_file(stub_diagnostics, "ergo_cst.pyi")
    assert errors == [], f"pyright errors in the generated stub:\n{errors}"


def test_stub_conforms_to_protocol(stub_diagnostics: dict[str, list[dict[str, Any]]]) -> None:
    """Every stub class stays assignable to its protocol counterpart."""
    errors = _diags_for_file(stub_diagnostics, "conformance_fixture.py")
    assert errors == [], f"stub/protocol conformance broke:\n{errors}"


@pytest.mark.parametrize(
    "grammar_path",
    [
        "fltk/fegen/fegen.fltkg",
        "fltk/fegen/test_data/rust_parser_fixture.fltkg",
        "fltk/fegen/test_data/phase4_roundtrip.fltkg",
    ],
)
def test_in_tree_grammars_emit(grammar_path: str) -> None:
    """Every grammar the repo generates Rust for emits .rs, .pyi and protocol text."""
    repo_root = pathlib.Path(__file__).parent.parent
    gen = RustCstGenerator(plumbing.parse_grammar_file(repo_root / grammar_path))
    assert gen.generate()
    assert gen.generate_pyi("fltk.fegen.fltk_cst_protocol")
    assert gen.generate_protocol()
