"""Tests for CST Protocol generation and pyright-checkability.

Design: docs/adr/2026/06/05-cst-type-annotations-regression/design.md
Tests cover: T1 (protocol generation unit), T2a (member-access fixture), T2b (boundary probe),
T4 (backend-agnostic swap), T5 (runtime unaffected).
T3 and T6 are gate-level and run via `make check` / `uv run pyright`.
"""

from __future__ import annotations

import ast
import json
import pathlib
import shutil
import subprocess
import textwrap
from typing import Any

import pytest

from fltk.fegen import gsm, gsm2tree
from fltk.fegen.genparser import _parse_grammar_raw, create_default_context
from fltk.iir.py import reg as pyreg

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FEGEN_FLTKG = pathlib.Path(__file__).parent / "fegen.fltkg"
PROTOCOL_MODULE = pathlib.Path(__file__).parent / "fltk_cst_protocol.py"

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


def run_pyright(file_path: pathlib.Path, *, pyright_available: bool) -> list[dict[str, Any]]:
    """Run pyright --outputjson on file_path, return list of diagnostics for that file.

    Returns empty list on success; raises pytest.skip if pyright unavailable.
    Each entry is a dict with keys: file, severity, message, rule, range.
    """
    if not pyright_available:
        pytest.skip("pyright not available in this environment")
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "pyright", "--outputjson", str(file_path)],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"pyright produced non-JSON output: {result.stdout[:500]}")
    diagnostics = data.get("generalDiagnostics", [])
    # Filter to the target file (pyright may report diagnostics for dependencies)
    file_str = str(file_path.resolve())
    return [d for d in diagnostics if d.get("file", "").endswith(file_path.name) or file_str in d.get("file", "")]


# ---------------------------------------------------------------------------
# T1 — Protocol generation unit test
# ---------------------------------------------------------------------------


def _build_cst_generator() -> gsm2tree.CstGenerator:
    """Build a CstGenerator from the fegen grammar."""
    grammar = _parse_grammar_raw(FEGEN_FLTKG)
    grammar = gsm.add_trivia_rule_to_grammar(grammar, create_default_context())
    cst_module = pyreg.Module(["fltk", "fegen", "fltk_cst"])
    return gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module, context=create_default_context())


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
    # CstModule is also generated; include it in the expected set
    expected_node_names.add("CstModule")
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
    assert expected_class_names == prop_names

    # These specific names are accessed by Cst2Gsm at runtime (fltk2gsm.py).
    # If the grammar renames these rules, both the generator and fltk2gsm.py need updating.
    for required_name in ("Items", "Item", "Disposition", "Quantifier"):
        assert required_name in prop_names, (
            f"CstModule missing required property '{required_name}' (accessed by Cst2Gsm at runtime)"
        )


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
    tmp_path: pathlib.Path,
    pyright_available: bool,  # noqa: FBT001
) -> None:
    """T2a (known limitation): wrong-but-existing label comparison is NOT flagged by pyright.

    The Protocol provides attribute-presence checking only. A valid-but-semantically-wrong label
    comparison (e.g., Items.Label.ITEM == Items.Label.NO_WS) produces zero pyright errors.
    This documents the nominal-enum limitation so consumers don't over-trust the type safety.
    """
    fixture = tmp_path / "wrong_label_value_fixture.py"
    fixture.write_text(_WRONG_LABEL_VALUE_FIXTURE)
    diags = run_pyright(fixture, pyright_available=pyright_available)
    errors = [d for d in diags if d.get("severity") == "error"]
    assert errors == [], (
        "Unexpected: pyright now flags a valid-but-semantically-wrong label comparison. "
        "If pyright gained nominal-enum checking, update the Protocol's Label members to use a typed enum "
        "and remove this known-limitation test."
    )


def test_member_access_fixture_zero_errors(
    tmp_path: pathlib.Path,
    pyright_available: bool,  # noqa: FBT001
) -> None:
    """T2a: CstModule-typed bindings resolve without pyright errors."""
    fixture = tmp_path / "member_access_fixture.py"
    fixture.write_text(_MEMBER_ACCESS_FIXTURE)
    diags = run_pyright(fixture, pyright_available=pyright_available)
    errors = [d for d in diags if d.get("severity") == "error"]
    assert errors == [], f"Unexpected pyright errors in member-access fixture:\n{errors}"


def test_wrong_member_access_is_flagged(
    tmp_path: pathlib.Path,
    pyright_available: bool,  # noqa: FBT001
) -> None:
    """T2a (negative): accessing a non-existent method on a typed node is flagged."""
    fixture = tmp_path / "wrong_access_fixture.py"
    fixture.write_text(_WRONG_ACCESS_FIXTURE)
    diags = run_pyright(fixture, pyright_available=pyright_available)
    # Expect at least one error on or near line 6 (the wrong method call)
    errors = [d for d in diags if d.get("severity") == "error"]
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
    tmp_path: pathlib.Path,
    pyright_available: bool,  # noqa: FBT001
) -> None:
    """T2b: bare fltk_cst assignment to CstModule produces errors due to nested-Label nominal mismatch.

    This test confirms the cast in fltk2gsm.py _DEFAULT_CST is *required* (not optional).
    The number of errors should equal or exceed the number of label-bearing node types.
    """
    fixture = tmp_path / "castless_probe.py"
    fixture.write_text(_CASTLESS_PROBE_FIXTURE)
    diags = run_pyright(fixture, pyright_available=pyright_available)
    errors = [d for d in diags if d.get("severity") == "error"]
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
    tmp_path: pathlib.Path,
    pyright_available: bool,  # noqa: FBT001
) -> None:
    """T4: A plain-class stand-in cast to Grammar resolves members without errors.

    Confirms the Protocol imposes no dataclass-specific requirements (no @dataclass,
    no enum.Enum, no specific base class). The Protocol is structurally matchable by
    any backend — Python dataclasses, PyO3 classes, or plain Python classes.
    """
    fixture = tmp_path / "standin_fixture.py"
    fixture.write_text(_STANDIN_FIXTURE)
    diags = run_pyright(fixture, pyright_available=pyright_available)
    errors = [d for d in diags if d.get("severity") == "error"]
    assert errors == [], f"Unexpected pyright errors with plain-class stand-in:\n{errors}"


# ---------------------------------------------------------------------------
# T5 — Runtime unaffected: fltk_cst_protocol not imported at runtime by fltk2gsm
# ---------------------------------------------------------------------------


def test_fltk2gsm_does_not_import_protocol_at_runtime() -> None:
    """T5: Importing fltk2gsm must not trigger a runtime import of fltk_cst_protocol.

    The protocol module is TYPE_CHECKING-only; it must not appear in sys.modules
    after importing fltk2gsm under normal (non-type-checking) conditions.

    Uses a subprocess to guarantee a clean sys.modules state regardless of collection order.
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
                "assert 'fltk.fegen.fltk_cst_protocol' not in sys.modules, "
                "'fltk_cst_protocol was imported at runtime'"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        "fltk.fegen.fltk_cst_protocol was imported at runtime by fltk2gsm — "
        "it must be TYPE_CHECKING-only to satisfy the no-runtime-cost constraint.\n"
        f"stderr: {result.stderr}"
    )
