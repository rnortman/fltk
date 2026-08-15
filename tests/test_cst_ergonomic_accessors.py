"""Emission tests for the ergonomic CST accessors on the Python backend.

Covers what ``cst_ergonomics.plan_rule`` decides once and ``gsm2tree`` emits twice: the bare
per-label accessors, the ``<label>_text()`` span shortcuts, the rule-level ``text()`` and the
``variant()`` discriminant — on the concrete dataclasses and on the shared protocol classes.

Three layers:
  * AST level — which members exist, with which signatures, in which order.
  * Runtime level — a generated-and-exec'd parser, real parses, and the error behaviour of
    each accessor on hand-mutated trees.
  * Type level — pyright over a freshly generated concrete+protocol module pair.
"""

from __future__ import annotations

import ast
import pathlib
import re
from typing import Any

import pytest

from fltk import plumbing
from fltk.fegen import cst_ergonomics, gsm, gsm2tree
from fltk.fegen.pyrt import terminalsrc
from fltk.iir.context import create_default_context
from fltk.iir.py import reg as pyreg
from tests.pyright_test_utils import _diags_for_file, _run_pyright_over_dir, write_pyright_config

# A grammar exercising every plan decision:
#   doc       — required-single node label, optional-single node label, collection label
#   ident     — span label named `text`, colliding with the rule-level text() reservation
#   tag       — required-single span label; terminal-only, so it gets text()
#   pair      — two required-single span labels; terminal-only
#   block     — collection of node children; not terminal-only, so no text()
#   op        — keyword-enum dispatch: optional-single span labels + variant()
#   entity    — rule-reference dispatch: auto-labeled alternatives + variant()
GRAMMAR_TEXT = """
doc := name:ident , body:block? , tags:tag* ;
ident := text:/[a-z]+/ ;
tag := "#" . name:/[a-z]+/ ;
pair := key:/[a-z]+/ . "=" . value:/[0-9]+/ ;
block := "{" , items:ident* , "}" ;
op := plus:"+" | minus:"-" ;
entity := op | pair ;
"""


_PROTOCOL_MODULE_NAME = "ergo_cst_protocol"
"""Import name of the protocol module the emitted CST module takes ``NodeKind`` from.

Matches the file the pyright fixture writes beside the generated ``ergo_cst.py``."""


def _generator(py_module: pyreg.Module | None = None) -> gsm2tree.CstGenerator:
    context = create_default_context(capture_trivia=True)
    grammar = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(plumbing.parse_grammar(GRAMMAR_TEXT), context))
    return gsm2tree.CstGenerator(grammar=grammar, py_module=py_module or pyreg.Builtins, context=context)


def _method_names(klass: ast.ClassDef) -> list[str]:
    return [stmt.name for stmt in klass.body if isinstance(stmt, ast.FunctionDef)]


def _find_function(klass: ast.ClassDef, name: str) -> ast.FunctionDef | None:
    for stmt in klass.body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == name:
            return stmt
    return None


def _function(klass: ast.ClassDef, name: str) -> ast.FunctionDef:
    fn = _find_function(klass, name)
    assert fn is not None, f"{name}() not emitted on {klass.name}"
    return fn


def _return_annotation(klass: ast.ClassDef, name: str) -> str:
    fn = _function(klass, name)
    assert fn.returns is not None, f"{name}() has no return annotation"
    return ast.unparse(fn.returns)


def _source(klass: ast.ClassDef, name: str) -> str:
    return ast.unparse(_function(klass, name))


@pytest.fixture(scope="module")
def generator() -> gsm2tree.CstGenerator:
    return _generator()


@pytest.fixture(scope="module")
def concrete_classes(generator: gsm2tree.CstGenerator) -> dict[str, ast.ClassDef]:
    """Concrete dataclass ClassDefs by class name."""
    module = generator.gen_py_module(_PROTOCOL_MODULE_NAME)
    return {stmt.name: stmt for stmt in module.body if isinstance(stmt, ast.ClassDef)}


@pytest.fixture(scope="module")
def protocol_classes(generator: gsm2tree.CstGenerator) -> dict[str, ast.ClassDef]:
    """Protocol ClassDefs by class name."""
    module = generator.gen_protocol_module()
    return {stmt.name: stmt for stmt in module.body if isinstance(stmt, ast.ClassDef)}


# ---------------------------------------------------------------------------
# Which members are emitted
# ---------------------------------------------------------------------------


class TestBareAccessorEmission:
    def test_required_single_node_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        """A label present exactly once in every alternative gets a non-optional accessor."""
        assert _return_annotation(concrete_classes["Doc"], "name") == "'Ident'"

    def test_optional_single_node_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _return_annotation(concrete_classes["Doc"], "body") == "typing.Optional['Block']"

    def test_collection_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _return_annotation(concrete_classes["Doc"], "tags") == "list['Tag']"

    def test_collection_label_of_nodes(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _return_annotation(concrete_classes["Block"], "items") == "list['Ident']"

    def test_optional_single_span_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        ret = _return_annotation(concrete_classes["Op"], "plus")
        assert ret.startswith("typing.Optional["), ret

    def test_bare_accessor_delegates_to_quintet(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        """Bodies delegate so that count checks and error messages are identical by construction."""
        assert _source(concrete_classes["Doc"], "name").endswith("return self.child_name()")
        assert _source(concrete_classes["Doc"], "body").endswith("return self.maybe_body()")
        assert _source(concrete_classes["Doc"], "tags").endswith("return list(self.children_tags())")

    def test_colliding_bare_accessor_skipped(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        """`ident`'s label is `text`, which the rule-level text() reserves: bare accessor skipped."""
        assert _source(concrete_classes["Ident"], "text").endswith("return self.span.text_or_raise()"), (
            "text() on Ident must be the rule-level span shortcut, not the label accessor"
        )

    def test_quintet_still_emitted_for_skipped_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        for name in ("append_text", "extend_text", "children_text", "child_text", "maybe_text"):
            assert _find_function(concrete_classes["Ident"], name) is not None, name


class TestTextAccessorEmission:
    def test_required_single_span_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _return_annotation(concrete_classes["Tag"], "name_text") == "str"

    def test_optional_single_span_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _return_annotation(concrete_classes["Op"], "plus_text") == "typing.Optional[str]"

    def test_derived_name_emitted_for_skipped_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        """The skipped bare `text` accessor does not take `text_text` down with it."""
        assert _return_annotation(concrete_classes["Ident"], "text_text") == "str"

    def test_no_text_accessor_for_node_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _find_function(concrete_classes["Doc"], "name_text") is None

    def test_no_text_accessor_for_collection_label(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _find_function(concrete_classes["Block"], "items_text") is None


class TestRuleLevelMembers:
    def test_text_on_terminal_only_rule(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _return_annotation(concrete_classes["Pair"], "text") == "str"

    def test_no_text_on_rule_with_node_children(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _find_function(concrete_classes["Block"], "text") is None
        assert _find_function(concrete_classes["Doc"], "text") is None

    def test_variant_on_keyword_dispatch_rule(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _return_annotation(concrete_classes["Op"], "variant") == "Label"

    def test_variant_on_rule_reference_dispatch_rule(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        """Unlabeled rule references are auto-labeled, so plain dispatch rules qualify too."""
        assert _return_annotation(concrete_classes["Entity"], "variant") == "Label"

    def test_no_variant_on_single_alternative_rule(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        assert _find_function(concrete_classes["Doc"], "variant") is None
        assert _find_function(concrete_classes["Tag"], "variant") is None


class TestEmissionOrder:
    def test_ergonomics_follow_the_quintet(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        names = _method_names(concrete_classes["Doc"])
        assert names.index("maybe_tags") < names.index("body")

    def test_per_label_members_sorted_bare_then_text(self, concrete_classes: dict[str, ast.ClassDef]) -> None:
        names = _method_names(concrete_classes["Op"])
        ergonomic = [n for n in names if n in {"minus", "minus_text", "plus", "plus_text", "text", "variant"}]
        assert ergonomic == ["minus", "minus_text", "plus", "plus_text", "text", "variant"]


class TestProtocolMirrorsConcrete:
    """A member exists on both emission surfaces or on neither."""

    def test_same_method_names_per_rule(
        self,
        concrete_classes: dict[str, ast.ClassDef],
        protocol_classes: dict[str, ast.ClassDef],
        generator: gsm2tree.CstGenerator,
    ) -> None:
        for rule_name in generator.rule_models:
            class_name = generator.class_name_for_rule_node(rule_name)
            concrete = set(_method_names(concrete_classes[class_name]))
            protocol = set(_method_names(protocol_classes[class_name]))
            # The concrete class carries private validation helpers the protocol does not declare.
            concrete -= {"_check_child_type_for_mutators", "_check_label_type_for_mutators"}
            # The protocol declares children as a read-only property; the concrete class as a field.
            protocol -= {"children"}
            assert concrete == protocol, f"{class_name}: concrete/protocol member mismatch"

    def test_protocol_return_annotations_match_shape(
        self, protocol_classes: dict[str, ast.ClassDef], concrete_classes: dict[str, ast.ClassDef]
    ) -> None:
        assert _return_annotation(protocol_classes["Tag"], "name_text") == "str"
        assert _return_annotation(protocol_classes["Op"], "plus_text") == "typing.Optional[str]"
        assert _return_annotation(protocol_classes["Op"], "variant") == gsm2tree.LABEL_PROTOCOL_ANNOTATION
        # A MULTIPLE accessor promises only a Sequence in the protocol: list is invariant, so a
        # backend returning a list of its own node classes could not satisfy list[<protocol node>].
        assert _return_annotation(protocol_classes["Doc"], "tags") == "typing.Sequence['Tag']"
        assert _return_annotation(concrete_classes["Doc"], "tags") == "list['Tag']"

    def test_protocol_bodies_are_ellipsis(self, protocol_classes: dict[str, ast.ClassDef]) -> None:
        for name in ("plus", "plus_text", "text", "variant"):
            assert _source(protocol_classes["Op"], name).endswith("..."), name


class TestPlanIsShared:
    """The emitters read the planner's decisions rather than re-deriving them."""

    def test_generator_exposes_a_plan_per_rule(self, generator: gsm2tree.CstGenerator) -> None:
        assert set(generator.rule_plans) == {rule.name for rule in generator.grammar.rules}

    def test_plan_matches_emitted_members(
        self, generator: gsm2tree.CstGenerator, concrete_classes: dict[str, ast.ClassDef]
    ) -> None:
        for rule_name, plan in generator.rule_plans.items():
            klass = concrete_classes[generator.class_name_for_rule_node(rule_name)]
            names = set(_method_names(klass))
            for label in plan.bare_accessors:
                assert label in names, f"{rule_name}.{label}"
            for label in plan.text_accessors:
                assert f"{label}_text" in names, f"{rule_name}.{label}_text"
            assert ("text" in names) is (plan.rule_text or "text" in plan.bare_accessors)
            assert ("variant" in names) is plan.variant

    def test_skipped_members_are_absent(self, generator: gsm2tree.CstGenerator) -> None:
        ident_plan = generator.rule_plans["ident"]
        skipped = {(member.name, member.kind) for member in ident_plan.skipped}
        assert ("text", cst_ergonomics.MemberKind.BARE_ACCESSOR) in skipped

    def test_unknown_rule_has_no_plan(self, generator: gsm2tree.CstGenerator) -> None:
        assert generator.plan_for_rule("") is None


def test_unknown_ergonomic_member_kind_raises(generator: gsm2tree.CstGenerator) -> None:
    """The body dispatcher rejects a member kind it does not know how to emit."""
    plan = generator.rule_plans["op"]
    with pytest.raises(ValueError, match="Unknown ergonomic member"):
        gsm2tree.CstGenerator._concrete_ergonomic_body(
            plan=plan,
            class_name="Op",
            member="nope",  # type: ignore[arg-type]
            label="",
        )


# ---------------------------------------------------------------------------
# Runtime behaviour
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def parser_result() -> plumbing.ParserResult:
    return plumbing.generate_parser(plumbing.parse_grammar(GRAMMAR_TEXT), capture_trivia=True)


def _parse(parser_result: plumbing.ParserResult, text: str, rule_name: str) -> Any:
    result = plumbing.parse_text(parser_result, text, rule_name)
    assert result.success, result.error_message
    return result.cst


class TestRuntimeBareAccessors:
    def test_required_single_returns_child(self, parser_result: plumbing.ParserResult) -> None:
        doc = _parse(parser_result, "alpha", "doc")
        assert doc.name() is doc.child_name()

    def test_optional_single_returns_none_when_absent(self, parser_result: plumbing.ParserResult) -> None:
        doc = _parse(parser_result, "alpha", "doc")
        assert doc.body() is None

    def test_optional_single_returns_child_when_present(self, parser_result: plumbing.ParserResult) -> None:
        doc = _parse(parser_result, "alpha { beta }", "doc")
        assert doc.body() is doc.child_body()

    def test_collection_returns_list(self, parser_result: plumbing.ParserResult) -> None:
        doc = _parse(parser_result, "alpha #one#two", "doc")
        assert doc.tags() == list(doc.children_tags())
        assert len(doc.tags()) == 2

    def test_collection_returns_empty_list(self, parser_result: plumbing.ParserResult) -> None:
        doc = _parse(parser_result, "alpha", "doc")
        assert doc.tags() == []

    def test_required_single_raises_same_message_as_quintet(self, parser_result: plumbing.ParserResult) -> None:
        doc = _parse(parser_result, "alpha", "doc")
        doc.clear()
        with pytest.raises(ValueError, match="Expected one name child but have 0"):
            doc.name()

    def test_optional_single_raises_when_over_one(self, parser_result: plumbing.ParserResult) -> None:
        doc = _parse(parser_result, "alpha { beta }", "doc")
        doc.append(doc.child_body(), doc.Label.BODY)
        with pytest.raises(ValueError, match="Expected at most one body child but have 2"):
            doc.body()


class TestRuntimeTextAccessors:
    def test_required_single_text(self, parser_result: plumbing.ParserResult) -> None:
        tag = _parse(parser_result, "#hello", "tag")
        assert tag.name_text() == "hello"

    def test_derived_name_for_skipped_label(self, parser_result: plumbing.ParserResult) -> None:
        ident = _parse(parser_result, "alpha", "ident")
        assert ident.text_text() == "alpha"

    def test_optional_text_present(self, parser_result: plumbing.ParserResult) -> None:
        op = _parse(parser_result, "+", "op")
        assert op.plus_text() == "+"

    def test_optional_text_absent(self, parser_result: plumbing.ParserResult) -> None:
        op = _parse(parser_result, "+", "op")
        assert op.minus_text() is None

    def test_text_accessor_raises_on_sourceless_span(self, parser_result: plumbing.ParserResult) -> None:
        tag_cls = parser_result.cst_module.Tag
        node = tag_cls()
        node.append_name(terminalsrc.Span(0, 1))
        with pytest.raises(ValueError, match="no source"):
            node.name_text()

    def test_required_text_accessor_rejects_a_non_span_child(self, parser_result: plumbing.ParserResult) -> None:
        """Only reachable through the untyped mutators."""
        tag = _parse(parser_result, "#hello", "tag")
        tag.clear()
        tag.append(_parse(parser_result, "alpha", "ident"), tag.Label.NAME)
        with pytest.raises(TypeError, match=re.escape("Tag.name_text: child labelled 'name' is not a Span")):
            tag.name_text()

    def test_optional_text_accessor_rejects_a_non_span_child(self, parser_result: plumbing.ParserResult) -> None:
        op = _parse(parser_result, "+", "op")
        op.clear()
        op.append(_parse(parser_result, "alpha", "ident"), op.Label.PLUS)
        with pytest.raises(TypeError, match=re.escape("Op.plus_text: child labelled 'plus' is not a Span")):
            op.plus_text()


class TestRuntimeRuleText:
    def test_text_is_the_nodes_own_span(self, parser_result: plumbing.ParserResult) -> None:
        pair = _parse(parser_result, "age=42", "pair")
        assert pair.text() == "age=42"

    def test_text_covers_suppressed_content(self, parser_result: plumbing.ParserResult) -> None:
        """The node span spans suppressed terminals; the label shortcut does not."""
        tag = _parse(parser_result, "#hello", "tag")
        assert tag.text() == "#hello"
        assert tag.name_text() == "hello"

    def test_text_raises_on_sourceless_span(self, parser_result: plumbing.ParserResult) -> None:
        node = parser_result.cst_module.Pair()
        with pytest.raises(ValueError, match="no source"):
            node.text()


class TestRuntimeVariant:
    def test_keyword_dispatch(self, parser_result: plumbing.ParserResult) -> None:
        op_cls = parser_result.cst_module.Op
        assert _parse(parser_result, "+", "op").variant() == op_cls.Label.PLUS
        assert _parse(parser_result, "-", "op").variant() == op_cls.Label.MINUS

    def test_rule_reference_dispatch(self, parser_result: plumbing.ParserResult) -> None:
        entity_cls = parser_result.cst_module.Entity
        assert _parse(parser_result, "age=42", "entity").variant() == entity_cls.Label.PAIR
        assert _parse(parser_result, "-", "entity").variant() == entity_cls.Label.OP

    def test_variant_skips_unlabeled_children(self, parser_result: plumbing.ParserResult) -> None:
        op_cls = parser_result.cst_module.Op
        node = op_cls()
        node.append(terminalsrc.Span(0, 1), None)
        node.append_plus(terminalsrc.Span(1, 2))
        assert node.variant() == op_cls.Label.PLUS

    def test_variant_raises_without_a_labeled_child(self, parser_result: plumbing.ParserResult) -> None:
        node = parser_result.cst_module.Op()
        with pytest.raises(ValueError, match=re.escape("Op.variant: node has no labeled child")):
            node.variant()


# ---------------------------------------------------------------------------
# Type level
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def generated_pair_diagnostics(
    pyright_available: bool,  # noqa: FBT001
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[dict[str, Any]]]:
    """Type-check a freshly generated concrete module and its protocol module together."""
    tmpdir = tmp_path_factory.mktemp("ergonomic_accessors_pyright")
    write_pyright_config(tmpdir)
    generator = _generator(pyreg.Module(("ergo_cst",)))
    (tmpdir / "ergo_cst.py").write_text(ast.unparse(generator.gen_py_module(_PROTOCOL_MODULE_NAME)) + "\n")
    (tmpdir / "ergo_cst_protocol.py").write_text(generator.gen_protocol_module_text() + "\n")
    (tmpdir / "consumer.py").write_text(_CONSUMER_FIXTURE)
    return _run_pyright_over_dir(tmpdir, pyright_available=pyright_available)


_CONSUMER_FIXTURE = """\
# ruff: noqa
from __future__ import annotations

import ergo_cst_protocol as cstp


def use_doc(doc: cstp.Doc) -> str:
    parts: list[str] = [doc.name().text_text()]
    body = doc.body()
    if body is not None:
        parts.extend(item.text_text() for item in body.items())
    parts.extend(tag.name_text() for tag in doc.tags())
    return " ".join(parts)


def use_op(op: cstp.Op) -> str:
    if op.variant() == cstp.OpLabel.PLUS:
        return op.plus_text() or ""
    return op.text()
"""


def test_generated_modules_typecheck(generated_pair_diagnostics: dict[str, list[dict[str, Any]]]) -> None:
    """The emitted members must not introduce pyright errors in either module."""
    for filename in ("ergo_cst.py", "ergo_cst_protocol.py"):
        errors = _diags_for_file(generated_pair_diagnostics, filename)
        assert errors == [], f"pyright errors in {filename}:\n{errors}"


def test_protocol_consumer_typechecks(generated_pair_diagnostics: dict[str, list[dict[str, Any]]]) -> None:
    """A protocol-typed consumer can use the ergonomic members without casts."""
    errors = _diags_for_file(generated_pair_diagnostics, "consumer.py")
    assert errors == [], f"pyright errors in the protocol consumer fixture:\n{errors}"


@pytest.mark.parametrize(
    "grammar_path",
    [
        "fltk/fegen/fegen.fltkg",
        "fltk/lsp/fltklsp.fltkg",
        "fltk/unparse/unparsefmt.fltkg",
    ],
)
def test_in_tree_grammars_emit(grammar_path: str) -> None:
    """Every in-tree grammar generates a CST module and its protocol."""
    repo_root = pathlib.Path(__file__).parent.parent
    context = create_default_context(capture_trivia=True)
    grammar = plumbing.parse_grammar_file(repo_root / grammar_path)
    grammar = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))
    generator = gsm2tree.CstGenerator(grammar=grammar, py_module=pyreg.Builtins, context=context)
    assert ast.unparse(generator.gen_py_module(_PROTOCOL_MODULE_NAME))
    assert generator.gen_protocol_module_text()


def test_skipped_member_logged_during_generation(caplog: pytest.LogCaptureFixture) -> None:
    """Skipping a member is never silent: generation logs rule, member and reason."""
    with caplog.at_level("INFO", logger="fltk.fegen.cst_ergonomics"):
        _generator()
    assert any("ident" in record.message and "text" in record.message for record in caplog.records)
