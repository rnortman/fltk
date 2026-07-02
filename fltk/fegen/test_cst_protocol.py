"""Tests for CST Protocol generation and pyright-checkability.

Design: docs/adr/2026/06/05-cst-type-annotations-regression/design.md
Tests cover: T1 (protocol generation unit), T2a (member-access fixture), T2b (boundary probe),
T4 (backend-agnostic swap), T5 (runtime unaffected).
T3 and T6 are gate-level and run via `make check` / `uv run pyright`.
"""

from __future__ import annotations

import ast
import pathlib
import shutil
import subprocess
import textwrap
from typing import Any

import pytest

from fltk.fegen import gsm, gsm2tree
from fltk.fegen.genparser import _parse_grammar_raw, create_default_context
from fltk.iir.py import reg as pyreg
from tests.pyright_test_utils import _diags_for_file, _run_pyright_over_dir, write_pyright_config

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FEGEN_FLTKG = pathlib.Path(__file__).parent / "fegen.fltkg"
PROTOCOL_MODULE = pathlib.Path(__file__).parent / "fltk_cst_protocol.py"
CONCRETE_MODULE = pathlib.Path(__file__).parent / "fltk_cst.py"

# ---------------------------------------------------------------------------
# Pyright harness
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pyright_available() -> bool:
    """Return True when uv + pyright are runnable in this environment."""
    if shutil.which("uv") is None:
        return False
    result = subprocess.run(
        ["uv", "run", "pyright", "--version"],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# T1 — Protocol generation unit test
# ---------------------------------------------------------------------------


def _build_cst_generator(py_module: pyreg.Module | None = None) -> gsm2tree.CstGenerator:
    """Build a CstGenerator from the fegen grammar.

    Defaults to a real module path; pass ``pyreg.Builtins`` for a Builtins-backed
    (empty, falsy import_path) generator.
    """
    if py_module is None:
        py_module = pyreg.Module(["fltk", "fegen", "fltk_cst"])
    grammar = _parse_grammar_raw(FEGEN_FLTKG)
    grammar = gsm.add_trivia_rule_to_grammar(grammar, create_default_context())
    return gsm2tree.CstGenerator(grammar=grammar, py_module=py_module, context=create_default_context())


# ---------------------------------------------------------------------------
# emit_kind_literal parameter
# ---------------------------------------------------------------------------


def test_builtins_backed_generator_emits_literal_kind_by_default() -> None:
    """A Builtins-backed generator emits the precise Literal discriminant by default.

    py_module does not gate the discriminant: even a Builtins-backed generator (empty, falsy
    import_path) emits `kind: typing.Literal[NodeKind.*]` rather than the degraded `kind: object`.
    """
    text = _build_cst_generator(pyreg.Builtins).gen_protocol_module_text()
    assert "kind: typing.Literal[NodeKind." in text
    assert "kind: object" not in text


def test_protocol_text_independent_of_py_module() -> None:
    """py_module independence: protocol text is byte-identical regardless of the backing py_module.

    Pins the invariant that py_module plays no role in protocol output.
    """
    builtins_text = _build_cst_generator(pyreg.Builtins).gen_protocol_module_text()
    real_module_text = _build_cst_generator().gen_protocol_module_text()
    assert builtins_text == real_module_text


def test_emit_kind_literal_false_produces_degraded_form() -> None:
    """Explicit opt-out: emit_kind_literal=False emits `kind: object` and no Literal discriminant."""
    text = _build_cst_generator().gen_protocol_module_text(emit_kind_literal=False)
    assert "kind: object" in text
    assert "Literal[NodeKind." not in text


@pytest.fixture(scope="module")
def cst_generator() -> gsm2tree.CstGenerator:
    return _build_cst_generator()


@pytest.fixture(scope="module")
def protocol_module_ast(cst_generator: gsm2tree.CstGenerator) -> ast.Module:
    return cst_generator.gen_protocol_module()


def test_protocol_module_has_one_class_per_rule(
    cst_generator: gsm2tree.CstGenerator,
    protocol_module_ast: ast.Module,
) -> None:
    """Every grammar rule produces exactly one Protocol class in the module."""
    rule_names = set(cst_generator.rule_models.keys())
    class_defs = {node.name for node in protocol_module_ast.body if isinstance(node, ast.ClassDef)}
    expected_node_names = {cst_generator.protocol_node_name(r) for r in rule_names}
    # CstModule and Span protocol are also generated; include them in the expected set
    expected_node_names.add("CstModule")
    expected_node_names.add("Span")
    # NodeKind and _ProtocolLabelMember are module-level classes also in the body
    expected_node_names.add("NodeKind")
    expected_node_names.add("_ProtocolLabelMember")
    assert expected_node_names == class_defs


def test_protocol_node_has_required_members(
    cst_generator: gsm2tree.CstGenerator,
    protocol_module_ast: ast.Module,
) -> None:
    """Each Protocol node class has span, children, append, extend, child, and per-label methods."""
    class_map: dict[str, ast.ClassDef] = {
        node.name: node for node in protocol_module_ast.body if isinstance(node, ast.ClassDef)
    }

    for rule_name, model in cst_generator.rule_models.items():
        node_class_name = cst_generator.protocol_node_name(rule_name)
        assert node_class_name in class_map, f"Missing Protocol class for rule {rule_name!r}"
        klass = class_map[node_class_name]

        # Collect member names (attributes + methods)
        member_names: set[str] = set()
        for item in klass.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                member_names.add(item.target.id)
            elif isinstance(item, ast.FunctionDef):
                member_names.add(item.name)
            elif isinstance(item, ast.ClassDef):
                member_names.add(item.name)

        # Required base members
        assert "span" in member_names, f"{node_class_name} missing 'span'"
        assert "children" in member_names, f"{node_class_name} missing 'children'"
        assert "append" in member_names, f"{node_class_name} missing 'append'"
        assert "extend" in member_names, f"{node_class_name} missing 'extend'"
        assert "child" in member_names, f"{node_class_name} missing 'child'"

        labels = sorted(model.labels.keys())
        if labels:
            assert "Label" in member_names, f"{node_class_name} has labels but no nested Label class"
            for label in labels:
                for prefix in ("append_", "extend_", "children_", "child_", "maybe_"):
                    expected = f"{prefix}{label}"
                    assert expected in member_names, f"{node_class_name} missing '{expected}'"


def test_cst_module_protocol_has_property_per_rule(
    cst_generator: gsm2tree.CstGenerator,
    protocol_module_ast: ast.Module,
) -> None:
    """CstModule has one @property per grammar rule, returning the node type."""
    class_map: dict[str, ast.ClassDef] = {
        node.name: node for node in protocol_module_ast.body if isinstance(node, ast.ClassDef)
    }
    assert "CstModule" in class_map
    cst_module_klass = class_map["CstModule"]

    prop_names: set[str] = set()
    for item in cst_module_klass.body:
        if isinstance(item, ast.FunctionDef):
            # Must have @property decorator
            decorators = [ast.unparse(d) for d in item.decorator_list]
            assert "property" in decorators, f"CstModule.{item.name} lacks @property decorator"
            prop_names.add(item.name)

    expected_class_names = {cst_generator.class_name_for_rule_node(r) for r in cst_generator.rule_models}
    # No Span property: Span is a common-lib type, not a generated-module attribute (§2.1a).
    assert expected_class_names == prop_names

    # These specific names are accessed by Cst2Gsm at runtime (fltk2gsm.py).
    # If the grammar renames these rules, both the generator and fltk2gsm.py need updating.
    for required_name in ("Items", "Item", "Disposition", "Quantifier"):
        assert required_name in prop_names, (
            f"CstModule missing required property '{required_name}' (accessed by Cst2Gsm at runtime)"
        )


# ---------------------------------------------------------------------------
# Batched pyright fixtures (module-scoped)
# ---------------------------------------------------------------------------
#
# All pyright-invoking tests share two module-scoped batch runs:
#   - cst_protocol_pyright_diagnostics: positive + known-limitation tests (4 fixture files)
#   - cst_protocol_negative_pyright_diagnostics: negative tests (2 fixture files)
# Each test filters the partitioned results by its own fixture file name.


@pytest.fixture(scope="module")
def cst_protocol_pyright_diagnostics(
    pyright_available: bool,  # noqa: FBT001
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[dict[str, Any]]]:
    """Run pyright once over all positive CST-protocol fixture files.

    Writes all positive fixture files into a shared tmpdir and runs a single
    `uv run pyright --outputjson <dir>` invocation.  Returns diagnostics
    partitioned by absolute file path.  Negative-test fixtures (which deliberately
    contain errors) are batched separately to keep error attribution unambiguous.
    """
    tmpdir = tmp_path_factory.mktemp("cst_protocol_pyright")
    write_pyright_config(tmpdir)
    (tmpdir / "wrong_label_value_fixture.py").write_text(_WRONG_LABEL_VALUE_FIXTURE)
    (tmpdir / "member_access_fixture.py").write_text(_MEMBER_ACCESS_FIXTURE)
    (tmpdir / "standin_fixture.py").write_text(_STANDIN_FIXTURE)
    (tmpdir / "agnostic_spanprotocol_consumer.py").write_text(_AGNOSTIC_SPANPROTOCOL_CONSUMER_FIXTURE)
    return _run_pyright_over_dir(tmpdir, pyright_available=pyright_available)


@pytest.fixture(scope="module")
def cst_protocol_negative_pyright_diagnostics(
    pyright_available: bool,  # noqa: FBT001
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, list[dict[str, Any]]]:
    """Run pyright once over all negative CST-protocol fixture files (those that expect errors).

    Batched separately so that expected errors in one file don't appear as noise when filtering
    another file's results.
    """
    tmpdir = tmp_path_factory.mktemp("cst_protocol_negative_pyright")
    write_pyright_config(tmpdir)
    (tmpdir / "wrong_access_fixture.py").write_text(_WRONG_ACCESS_FIXTURE)
    (tmpdir / "castless_probe.py").write_text(_CASTLESS_PROBE_FIXTURE)
    return _run_pyright_over_dir(tmpdir, pyright_available=pyright_available)


# ---------------------------------------------------------------------------
# T2a — Member-access fixture (verifies Protocol surface resolves on concrete module)
# ---------------------------------------------------------------------------

# This fixture file accesses CstModule-typed attributes so pyright verifies
# each member resolves without Any-degradation.
_MEMBER_ACCESS_FIXTURE = """\
# ruff: noqa
from __future__ import annotations
from typing import Any, cast

from fltk.fegen import fltk_cst_protocol as cstp
from fltk.fegen import fltk_cst

_m: cstp.CstModule = cast(cstp.CstModule, fltk_cst)

# Access every top-level node type
_grammar_type = _m.Grammar
_rule_type = _m.Rule
_alternatives_type = _m.Alternatives
_items_type = _m.Items
_item_type = _m.Item
_term_type = _m.Term
_disposition_type = _m.Disposition
_quantifier_type = _m.Quantifier
_identifier_type = _m.Identifier
_raw_string_type = _m.RawString
_literal_type = _m.Literal
_trivia_type = _m.Trivia

# Access label constants
_no_ws = _m.Items.Label.NO_WS
_item_label = _m.Items.Label.ITEM
_disposition_include = _m.Disposition.Label.INCLUDE

# Access methods on a typed instance
def _check_grammar_node(g: cstp.Grammar) -> None:
    _ = g.span
    _ = g.children
    _ = g.children_rule()
    _ = g.child_rule()
    _ = g.maybe_rule()

def _check_items_node(items: cstp.Items) -> None:
    _ = items.span
    _ = items.children
    _ = items.children_item()
    _ = items.child_item()
    _ = items.maybe_item()
    _ = items.Label.NO_WS
    _ = items.Label.ITEM

def _check_item_node(item: cstp.Item) -> None:
    _ = item.child_term()
    _ = item.maybe_label()
    _ = item.maybe_disposition()
    _ = item.maybe_quantifier()

def _check_rule_node(rule: cstp.Rule) -> None:
    _ = rule.span
    _ = rule.children
    _ = rule.child_name()
    _ = rule.child_alternatives()

def _check_term_node(term: cstp.Term) -> None:
    _ = term.span
    _ = term.children
    _ = term.maybe_alternatives()
    _ = term.maybe_literal()
    _ = term.maybe_identifier()

def _check_disposition_node(d: cstp.Disposition) -> None:
    _ = d.span
    _ = d.child()
    _ = d.Label.INCLUDE

def _check_quantifier_node(q: cstp.Quantifier) -> None:
    _ = q.span
    _ = q.child()

def _check_literal_node(lit: cstp.Literal) -> None:
    _ = lit.span
    _ = lit.child_value()

def _check_raw_string_node(rs: cstp.RawString) -> None:
    _ = rs.span
    _ = rs.child_value()
"""

_WRONG_ACCESS_FIXTURE = """\
# ruff: noqa
from __future__ import annotations
from fltk.fegen import fltk_cst_protocol as cstp

def _bad_method(g: cstp.Grammar) -> None:
    _ = g.no_such_method()  # line 6: should be flagged by pyright
"""

# Known-limitation fixture: pyright does NOT flag valid-but-semantically-wrong label comparisons.
# The Protocol provides attribute-presence checking only (a non-existent label is flagged),
# but comparing two valid label constants of different semantic meaning is not caught.
# This is a nominal-enum limitation: == on ClassVar[object] members cannot distinguish semantic intent.
# Documented here so future readers do not assume full label-value safety. See design.md.
_WRONG_LABEL_VALUE_FIXTURE = """\
# ruff: noqa
from __future__ import annotations
from fltk.fegen import fltk_cst_protocol as cstp

def _compare_wrong_labels(items: cstp.Items) -> bool:
    # Comparing ITEM vs NO_WS is semantically wrong but pyright does NOT flag it (nominal-enum limitation).
    # Both are valid ClassVar[object] members; their values are opaque to pyright.
    return items.Label.ITEM == items.Label.NO_WS  # line 7: valid attributes, wrong semantic comparison
"""


def test_wrong_label_value_not_flagged(
    cst_protocol_pyright_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """T2a (known limitation): wrong-but-existing label comparison is NOT flagged by pyright.

    The Protocol provides attribute-presence checking only. A valid-but-semantically-wrong label
    comparison (e.g., Items.Label.ITEM == Items.Label.NO_WS) produces zero pyright errors.
    This documents the nominal-enum limitation so consumers don't over-trust the type safety.
    """
    errors = _diags_for_file(cst_protocol_pyright_diagnostics, "wrong_label_value_fixture.py")
    assert errors == [], (
        "Unexpected: pyright now flags a valid-but-semantically-wrong label comparison. "
        "If pyright gained nominal-enum checking, update the Protocol's Label members to use a typed enum "
        "and remove this known-limitation test."
    )


def test_member_access_fixture_zero_errors(
    cst_protocol_pyright_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """T2a: CstModule-typed bindings resolve without pyright errors."""
    errors = _diags_for_file(cst_protocol_pyright_diagnostics, "member_access_fixture.py")
    assert errors == [], f"Unexpected pyright errors in member-access fixture:\n{errors}"


def test_wrong_member_access_is_flagged(
    cst_protocol_negative_pyright_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """T2a (negative): accessing a non-existent method on a typed node is flagged."""
    errors = _diags_for_file(cst_protocol_negative_pyright_diagnostics, "wrong_access_fixture.py")
    # Expect at least one error on or near line 6 (the wrong method call)
    assert errors, "Expected pyright to flag 'no_such_method' access but no errors were reported"


# ---------------------------------------------------------------------------
# T2b — Boundary-assignability probe (documents nested-Label cast necessity)
# ---------------------------------------------------------------------------

_CASTLESS_PROBE_FIXTURE = """\
# ruff: noqa
# Probe without type: ignore — used to count raw mismatches.
from __future__ import annotations
from fltk.fegen import fltk_cst_protocol as cstp
from fltk.fegen import fltk_cst

_m: cstp.CstModule = fltk_cst
"""


def test_boundary_probe_documents_label_mismatch(
    cst_protocol_negative_pyright_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """T2b: bare fltk_cst assignment to CstModule produces errors due to nested-Label nominal mismatch.

    This test confirms the cast in fltk2gsm.py _DEFAULT_CST is *required* (not optional).
    The number of errors should equal or exceed the number of label-bearing node types.
    """
    errors = _diags_for_file(cst_protocol_negative_pyright_diagnostics, "castless_probe.py")
    # Must have at least one error (the nested-Label nominal mismatch).
    assert errors, (
        "Expected pyright to report errors for bare fltk_cst -> CstModule assignment "
        "(nested-Label nominal mismatch). If this passes, the boundary cast in _DEFAULT_CST may be unnecessary."
    )


# ---------------------------------------------------------------------------
# T4 — Backend-agnostic swap: a stand-in module structurally satisfies CstModule
# ---------------------------------------------------------------------------

# A minimal hand-written stand-in that confirms Protocol is not Python-dataclass-specific.
# Uses a plain class cast to Grammar — no @dataclass, no enum.Enum, no specific base.
_STANDIN_FIXTURE = textwrap.dedent("""\
    # ruff: noqa
    # Minimal stand-in confirms the Protocol imposes no dataclass-specific requirements.
    from __future__ import annotations
    import typing

    import fltk.fegen.pyrt.terminalsrc as _t
    from fltk.fegen import fltk_cst_protocol as cstp

    class _FakeGrammar:
        class Label:
            RULE: typing.ClassVar[object] = object()
        span: _t.Span = _t.UnknownSpan
        children: list = []
        def append(self, child, label=None) -> None: ...
        def extend(self, children, label=None) -> None: ...
        def child(self): ...
        def append_rule(self, child) -> None: ...
        def extend_rule(self, children) -> None: ...
        def children_rule(self): ...
        def child_rule(self): ...
        def maybe_rule(self): ...

    # The cast mirrors production usage: the nested-Label nominal mismatch (see design.md, DI boundary)
    # means a direct structural assignment `_node: cstp.Grammar = _FakeGrammar()` is rejected
    # by pyright for the same reason fltk_cst modules require a cast.  The cast here is intentional —
    # it documents the known boundary, not a workaround for a real type gap.
    # The member-access calls below (_node.span, _node.children_rule()) are the real T4 check:
    # they verify that Protocol members resolve on a non-dataclass, non-enum plain class.
    _node: cstp.Grammar = typing.cast(cstp.Grammar, _FakeGrammar())
    _ = _node.span
    _ = _node.children_rule()
""")


def test_protocol_is_not_dataclass_specific(
    cst_protocol_pyright_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """T4: A plain-class stand-in cast to Grammar resolves members without errors.

    Confirms the Protocol imposes no dataclass-specific requirements (no @dataclass,
    no enum.Enum, no specific base class). The Protocol is structurally matchable by
    any backend — Python dataclasses, PyO3 classes, or plain Python classes.
    """
    errors = _diags_for_file(cst_protocol_pyright_diagnostics, "standin_fixture.py")
    assert errors == [], f"Unexpected pyright errors with plain-class stand-in:\n{errors}"


# ---------------------------------------------------------------------------
# T5 — Runtime unaffected: fltk_cst_protocol not imported at runtime by fltk2gsm
# ---------------------------------------------------------------------------


def test_fltk2gsm_imports_protocol_not_concrete_at_runtime() -> None:
    """T5 (updated): fltk2gsm imports the protocol module at runtime, NOT the concrete fltk_cst.

    After the clean-protocol-consumer-api work, fltk2gsm.py uses fltk_cst_protocol as its
    sole CST import (no runtime fltk_cst, no TYPE_CHECKING shadow).  This test verifies the
    inversion: protocol IS in sys.modules, concrete fltk_cst is NOT triggered by fltk2gsm itself
    (though fltk_cst_protocol imports terminalsrc which is fine — we check for fltk_cst, the
    concrete CST module, not for terminalsrc).

    Uses a subprocess to guarantee a clean sys.modules state.
    """
    result = subprocess.run(
        [  # noqa: S607
            "uv",
            "run",
            "python",
            "-c",
            (
                "import fltk.fegen.fltk2gsm; "
                "import sys; "
                "assert 'fltk.fegen.fltk_cst_protocol' in sys.modules, "
                "'fltk_cst_protocol was not imported at runtime by fltk2gsm'; "
                "assert 'fltk.fegen.fltk_cst' not in sys.modules, "
                "'fltk_cst (concrete) was imported at runtime by fltk2gsm — should only be protocol'"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"fltk2gsm import-behavior assertion failed.\nstderr: {result.stderr}"


# ---------------------------------------------------------------------------
# Agnostic SpanProtocol consumer surface (delta D3.4 — supersedes §4 item-8 union widening)
# ---------------------------------------------------------------------------
#
# The protocol ``span`` field and span-typed children moved from the explicit union
# ``terminalsrc.Span | fltk._native.Span`` to the agnostic
# ``fltk.fegen.pyrt.span_protocol.SpanProtocol`` (delta D3.4).  The old union-widening
# backward-compat tests are superseded: there is no union to narrow, and the agnostic
# ``SpanProtocol`` contract IS the swap-ability mechanism.  A consumer that annotates spans with
# ``SpanProtocol`` reads ``node.span`` with no cast for either backend.  The runtime ``isinstance``
# conformance of both backends (incl. the Rust span) is pinned by
# ``pyrt/test_span_protocol_assignability.py`` (delta D5.2), so it is not re-asserted here.

# A backend-agnostic consumer annotates spans with the agnostic SpanProtocol, reads node.span with
# NO cast, and passes it into SpanProtocol-typed parameters.  This must type-check unedited — it is
# the consumer side of the swap-ability the requirements mandate.
_AGNOSTIC_SPANPROTOCOL_CONSUMER_FIXTURE = textwrap.dedent("""\
    # ruff: noqa
    from __future__ import annotations

    import fltk.fegen.pyrt.span_protocol as _sp
    from fltk.fegen import fltk_cst_protocol as cstp

    def read_span(node: cstp.Grammar) -> _sp.SpanProtocol:
        # node.span is the agnostic SpanProtocol — assignable to a SpanProtocol slot with no cast.
        span: _sp.SpanProtocol = node.span
        return span

    def use_span_api(node: cstp.Grammar) -> int:
        # The full span API surface is reachable through the agnostic protocol.
        return node.span.start + node.span.end

    def accept_span_protocol(span: _sp.SpanProtocol) -> bool:
        return span.has_source()

    def pass_node_span_to_protocol_param(node: cstp.Grammar) -> bool:
        # node.span flows into a SpanProtocol-typed parameter with no cast.
        return accept_span_protocol(node.span)
""")


def test_agnostic_consumer_reads_span_as_spanprotocol(
    cst_protocol_pyright_diagnostics: dict[str, list[dict[str, Any]]],
) -> None:
    """A SpanProtocol-annotated consumer reads node.span unedited and cast-free (delta D3.4).

    After the protocol span surface moved to fltk.fegen.pyrt.span_protocol.SpanProtocol, node.span
    IS SpanProtocol, so a backend-agnostic consumer that annotates spans with SpanProtocol
    type-checks with no cast regardless of which backend produced the CST — the consumer side of
    the swap-ability the requirements mandate.  Supersedes the old union-widening tests
    (terminalsrc.Span | fltk._native.Span), whose premise D3.4 removes; the Rust-span runtime
    conformance they covered is pinned by pyrt/test_span_protocol_assignability.py (delta D5.2).
    """
    errors = _diags_for_file(cst_protocol_pyright_diagnostics, "agnostic_spanprotocol_consumer.py")
    assert errors == [], (
        f"Agnostic SpanProtocol consumer failed pyright after the span surface moved to SpanProtocol.\n"
        f"Errors:\n{errors}"
    )


# ---------------------------------------------------------------------------
# Committed CST/protocol source names neither fltk._native nor the span selector (delta D5.1 / R2)
# ---------------------------------------------------------------------------
#
# The user's R2 requires the Python pipeline to never resolve a span annotation to fltk._native and
# to type-check identically whether or not the native stub is importable.  For the *generated
# pipeline* the delta guarantees this structurally (D5.1): a module that names neither fltk._native
# nor the fltk.fegen.pyrt.span selector cannot produce stub-dependent pyright results for those
# symbols.  The parser (test_genparser.py), the Rust .pyi (test_gsm2tree_rs.py), and the unparser
# (test_is_span_guard.py) already pin this at the source level; these two tests complete the
# coverage for the committed concrete-CST and protocol modules.  This deterministic source-level
# guarantee supersedes a fragile stub-present-vs-absent differential pyright run (see implementation
# log, increment 18 deviation): a symbol that is never named is trivially stub-stable.
#
# The generator emits all CST/protocol files from one code path, so these checks parameterize over
# EVERY committed concrete-CST and protocol module (not just the fltk_cst pair) — a generator
# regression that reintroduced a native/selector reference would otherwise regress the unasserted
# files silently.

_FEGEN_DIR = pathlib.Path(__file__).parent
_UNPARSE_DIR = _FEGEN_DIR.parent / "unparse"

ALL_PROTOCOL_MODULES = [
    _FEGEN_DIR / "bootstrap_cst_protocol.py",
    _FEGEN_DIR / "fltk_cst_protocol.py",
    _FEGEN_DIR / "regex_cst_protocol.py",
    _UNPARSE_DIR / "toy_cst_protocol.py",
    _UNPARSE_DIR / "unparsefmt_cst_protocol.py",
]

ALL_CONCRETE_CST_MODULES = [
    _FEGEN_DIR / "bootstrap_cst.py",
    _FEGEN_DIR / "fltk_cst.py",
    _FEGEN_DIR / "regex_cst.py",
    _UNPARSE_DIR / "toy_cst.py",
    _UNPARSE_DIR / "unparsefmt_cst.py",
]


@pytest.mark.parametrize("protocol_module", ALL_PROTOCOL_MODULES, ids=lambda p: p.name)
def test_committed_protocol_source_names_no_native_no_selector(protocol_module: pathlib.Path) -> None:
    """Every committed protocol module names neither fltk._native nor the span selector (delta D5.1 / R2).

    The protocol's span surface is the agnostic span_protocol.SpanProtocol, imported under
    TYPE_CHECKING.  Naming neither fltk._native nor fltk.fegen.pyrt.span makes pyright's result on
    this module identical with or without the native stub.  Protocol modules carry NO fltk._native
    reference at all (unlike the concrete CST, which has the runtime _get_native_span_type() lookup),
    so the full-text "appears nowhere" assertion is both correct and the strictest check here — it
    catches a stray native annotation string as well as an import.
    """
    text = protocol_module.read_text()
    lines = text.splitlines()
    assert "fltk._native" not in text, (
        f"{protocol_module.name} must name fltk._native nowhere (no import, no annotation, no string)"
    )
    selector = [ln for ln in lines if ln.strip() == "import fltk.fegen.pyrt.span"]
    assert not selector, f"{protocol_module.name} must not import the fltk.fegen.pyrt.span selector; found {selector}"
    assert any(ln.strip() == "import fltk.fegen.pyrt.span_protocol" for ln in lines), (
        f"{protocol_module.name} must import the agnostic span_protocol (under TYPE_CHECKING)"
    )


@pytest.mark.parametrize("cst_module", ALL_CONCRETE_CST_MODULES, ids=lambda p: p.name)
def test_committed_cst_source_imports_no_native_no_selector(cst_module: pathlib.Path) -> None:
    """Every committed concrete CST module names fltk._native only in the runtime lookup (delta D5.1 / R2).

    Span annotations are the agnostic span_protocol.SpanProtocol.  The concrete CST legitimately
    contains exactly one fltk._native reference — the runtime _get_native_span_type() lookup
    ``sys.modules.get("fltk._native")``, a mutator-validation mechanism independent of the static
    annotation surface.  Asserting that EVERY fltk._native occurrence is that runtime lookup (rather
    than only checking for an `import fltk._native` line) catches a stray native annotation string
    too — under `from __future__ import annotations` a regression could emit `fltk._native.Span` as a
    lazy-string annotation with no import line, which an import-only check would miss.
    """
    text = cst_module.read_text()
    lines = text.splitlines()
    offending_native = [ln for ln in lines if "fltk._native" in ln and 'sys.modules.get("fltk._native")' not in ln]
    assert not offending_native, (
        f"{cst_module.name} must reference fltk._native only via the runtime "
        f'sys.modules.get("fltk._native") lookup; found {offending_native}'
    )
    selector = [ln for ln in lines if ln.strip() == "import fltk.fegen.pyrt.span"]
    assert not selector, f"{cst_module.name} must not import the fltk.fegen.pyrt.span selector; found {selector}"
    assert any(ln.strip() == "import fltk.fegen.pyrt.span_protocol" for ln in lines), (
        f"{cst_module.name} must import the agnostic span_protocol (under TYPE_CHECKING)"
    )
