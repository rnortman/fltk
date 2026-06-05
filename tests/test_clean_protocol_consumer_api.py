"""Tests for the clean protocol-only consumer API (section 4 of design.md).

Design: docs/adr/2026/06/05-clean-protocol-consumer-api/design.md
Requirements: docs/adr/2026/06/05-clean-protocol-consumer-api/requirements.md

Covers design section 4 items 1-9:
  1. Shape 1 + Shape 2 pyright + ruff clean (AC 8a, 11)
  2. fltk2gsm.py cleanliness (AC 1-5)
  3. fltk2gsm.py behavioral equivalence (AC 9)
  4. Runtime enum values (AC 6)
  5. AC 7 cross-backend equality/hash
  6. AC 12 cross-backend dual-shape dispatch
  7. Canonical-string agreement invariant
  8. Span equality/hash unchanged
  9. Structural-mismatch contract preserved (Option A)
"""

from __future__ import annotations

import enum
import json
import pathlib
import shutil
import subprocess

import pytest

# fltk._native is always available in the project (Rust extension built by maturin develop)
from fltk._native import Span as RustSpan
from fltk._native import fegen_cst as embedded_rust_cst
from fltk.fegen import fltk_cst as py_cst
from fltk.fegen import fltk_cst_protocol as proto_cst
from fltk.fegen import fltk_parser
from fltk.fegen.pyrt import terminalsrc
from fltk.fegen.pyrt.terminalsrc import SpanKind
from fltk.plumbing import generate_parser, parse_grammar_file

# ---------------------------------------------------------------------------
# Module-level availability guards
# ---------------------------------------------------------------------------

# fegen_rust_cst is optional (needs `make build-fegen-rust-cst`)
fegen_rust_cst = pytest.importorskip(
    "fegen_rust_cst",
    reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first",
)

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------

FLTK2GSM_PATH = pathlib.Path(__file__).parent.parent / "fltk" / "fegen" / "fltk2gsm.py"
PROTOCOL_MODULE_PATH = pathlib.Path(__file__).parent.parent / "fltk" / "fegen" / "fltk_cst_protocol.py"
FEGEN_FLTKG_PATH = pathlib.Path(__file__).parent.parent / "fltk" / "fegen" / "fegen.fltkg"

# A grammar text with Items nodes that have heterogeneous children (Item, Trivia, Span).
# "hello" separated by a comma (WS_ALLOWED separator) → produces Items with two Items
# children interleaved by a Span separator.
_SIMPLE_GRAMMAR_TEXT = 'test := "hello" , "world" ;'

# ---------------------------------------------------------------------------
# Helpers: pyright and ruff
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def pyright_available() -> bool:
    """Return True when uv + pyright are runnable."""
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


def _run_pyright(file_path: pathlib.Path, *, pyright_available: bool) -> list[dict]:
    """Run pyright --outputjson on file_path; return list of error diagnostics."""
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
        pytest.fail(f"pyright produced non-JSON output:\n{result.stdout[:500]}")
    return [d for d in data.get("generalDiagnostics", []) if d.get("severity") == "error"]


def _run_ruff(file_path: pathlib.Path) -> list[str]:
    """Run ruff check on file_path; return list of violation lines."""
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "ruff", "check", str(file_path)],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode == 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Helpers: CST tree builders
# ---------------------------------------------------------------------------


def _python_cst_grammar(grammar_text: str):  # type: ignore[return]
    """Parse grammar_text with the Python fltk_parser; return CST Grammar node."""
    tsrc = terminalsrc.TerminalSource(grammar_text)
    parser = fltk_parser.Parser(terminalsrc=tsrc)
    result = parser.apply__parse_grammar(0)
    assert result is not None and result.pos == len(tsrc.terminals)
    return result.result


def _rust_cst_grammar(grammar_text: str):  # type: ignore[return]
    """Parse grammar_text with the embedded Rust fegen parser; return CST Grammar node (Rust-backed)."""
    fegen_grammar = parse_grammar_file(FEGEN_FLTKG_PATH)
    pr = generate_parser(fegen_grammar, capture_trivia=False, rust_cst_module="fltk._native.fegen_cst")
    tsrc = terminalsrc.TerminalSource(grammar_text)
    parser = pr.parser_class(terminalsrc=tsrc)
    result = parser.apply__parse_grammar(0)
    assert result is not None and result.pos == len(tsrc.terminals)
    return result.result


def _get_first_items_node(grammar_tree) -> object:
    """Return the first Items child from the first rule of a parsed Grammar CST tree."""
    for rule in grammar_tree.children_rule():
        for alt in rule.child_alternatives().children_items():
            return alt
    pytest.fail("No Items node found in grammar tree")


# ---------------------------------------------------------------------------
# §4 item 1 — Shape 1 + Shape 2 pyright + ruff clean (AC 8a, 11)
# ---------------------------------------------------------------------------

# These Shape 1 and Shape 2 fixtures are consumed by the pyright/ruff cleanliness tests below.
# They import ONLY the protocol module and use both structurally different traversal shapes.
#
# Shape 1: interleaved (item, separator) pairing — the fltk2gsm.py pattern.
# Shape 2: match/case dispatch over a heterogeneous child union — the out-of-tree pattern.
#
# Neither shape uses cast, TYPE_CHECKING shadow, @runtime_checkable, or any CST-forced suppression.

# Pyright fixture for AC 8a.  Written to match the Shape 1 and Shape 2 requirements verbatim.
_SHAPES_FIXTURE = '''\
"""Shape 1 + Shape 2 protocol-only consumer fixture.

Both shapes import ONLY the generated protocol module: no casts, no suppression directives.
"""

from __future__ import annotations

from typing import Any

from fltk.fegen import fltk_cst_protocol as cst


def shape1_interleaved_walk(items: cst.Items) -> list[tuple[str, Any]]:
    """Shape 1: interleaved (item, separator) pairing — the fltk2gsm.py pattern."""
    results: list[tuple[str, Any]] = []
    children = items.children
    start_idx = 0
    if children and children[0][0] in (
        cst.Items.Label.NO_WS,
        cst.Items.Label.WS_ALLOWED,
        cst.Items.Label.WS_REQUIRED,
    ):
        start_idx = 1
    remaining = children[start_idx:]
    for (item_label, item), (sep_label, _) in zip(remaining[::2], remaining[1::2], strict=False):
        assert item_label == cst.Items.Label.ITEM
        assert item.kind == cst.Item.kind  # narrows item: Item|Trivia|Span -> cst.Item
        results.append(("item", item))
        results.append(("sep", sep_label))
    if len(remaining) % 2 != 0:
        item_label, item = remaining[-1]
        assert item_label == cst.Items.Label.ITEM
        assert item.kind == cst.Item.kind
        results.append(("item", item))
    return results


def shape2_match_dispatch(items: cst.Items) -> list[tuple[str, Any]]:
    """Shape 2: match/case dispatch over a heterogeneous child union — out-of-tree pattern."""
    results: list[tuple[str, Any]] = []
    for _label, child in items.children:
        match child.kind:
            case cst.Item.kind:
                results.append(("item", child))
            case cst.Trivia.kind:
                results.append(("trivia", child))
            case cst.Span.kind:
                results.append(("span", child))
            case _:
                results.append(("other", child))
    return results
'''


def test_shapes_fixture_pyright_clean(
    tmp_path: pathlib.Path,
    pyright_available: bool,  # noqa: FBT001
) -> None:
    """§4 item 1 (AC 8a): Shape 1 + Shape 2 fixture is pyright-clean with zero errors."""
    fixture = tmp_path / "shapes_fixture.py"
    fixture.write_text(_SHAPES_FIXTURE)
    errors = _run_pyright(fixture, pyright_available=pyright_available)
    assert errors == [], f"Unexpected pyright errors in shapes fixture:\n{errors}"


def test_shapes_fixture_ruff_clean(tmp_path: pathlib.Path) -> None:
    """§4 item 1 (AC 8a): Shape 1 + Shape 2 fixture is ruff-clean with zero violations."""
    fixture = tmp_path / "shapes_fixture.py"
    fixture.write_text(_SHAPES_FIXTURE)
    violations = _run_ruff(fixture)
    assert violations == [], f"Unexpected ruff violations in shapes fixture:\n{violations}"


def test_shapes_fixture_no_forbidden_patterns() -> None:
    """§4 item 1 (AC 8a, 11): fixture text contains no cast, runtime_checkable, or S101 noqa."""
    # Check by scanning lines that contain actual code (not docstring content)
    code_lines = [line for line in _SHAPES_FIXTURE.splitlines() if not line.strip().startswith('"""')]
    code_text = "\n".join(code_lines)
    assert "typing.cast" not in code_text
    assert "cast(" not in code_text
    assert "runtime_checkable" not in code_text
    # No bare noqa suppression (the fixture has no CST-forced noqa)
    assert "# noqa: S101" not in code_text


# ---------------------------------------------------------------------------
# Section 4 item 2: fltk2gsm.py cleanliness (AC 1-5)
# ---------------------------------------------------------------------------


def test_fltk2gsm_single_cst_import() -> None:
    """§4 item 2 (AC 1): fltk2gsm.py imports exactly one CST module (the protocol module)."""
    source = FLTK2GSM_PATH.read_text()
    assert "fltk_cst_protocol" in source, "fltk2gsm must import fltk_cst_protocol"
    # Ensure no import of the concrete fltk_cst module (the protocol is the only CST import).
    # We check that "fltk_cst" appears only as part of "fltk_cst_protocol", never standalone.
    lines = source.splitlines()
    for line in lines:
        stripped = line.strip()
        if "fltk_cst" in stripped and "fltk_cst_protocol" not in stripped:
            pytest.fail(
                f"fltk2gsm.py contains a reference to concrete fltk_cst (not via protocol):\n  {line!r}"
            )


def test_fltk2gsm_no_type_checking_block() -> None:
    """§4 item 2 (AC 1): fltk2gsm.py has no TYPE_CHECKING block for CST shadowing."""
    source = FLTK2GSM_PATH.read_text()
    assert "TYPE_CHECKING" not in source, "fltk2gsm must not use TYPE_CHECKING for CST shadowing"


def test_fltk2gsm_no_typing_cast() -> None:
    """§4 item 2 (AC 2): fltk2gsm.py has no typing.cast calls forced by CST types."""
    source = FLTK2GSM_PATH.read_text()
    assert "typing.cast" not in source, "fltk2gsm must not use typing.cast"
    assert "cast(" not in source, "fltk2gsm must not use cast()"


def test_fltk2gsm_no_cst_forced_suppressions() -> None:
    """§4 item 2 (AC 3): fltk2gsm.py has no CST-forced suppressions (no noqa S101)."""
    source = FLTK2GSM_PATH.read_text()
    assert "# noqa: S101" not in source, "fltk2gsm must not use # noqa: S101 suppressions"
    assert "# type: ignore" not in source, "fltk2gsm must not use # type: ignore suppressions"
    assert "# pyright: ignore" not in source, "fltk2gsm must not use # pyright: ignore"


def test_fltk2gsm_pyright_clean(
    pyright_available: bool,  # noqa: FBT001
) -> None:
    """§4 item 2 (AC 4): pyright is clean on fltk2gsm.py."""
    errors = _run_pyright(FLTK2GSM_PATH, pyright_available=pyright_available)
    assert errors == [], f"Unexpected pyright errors in fltk2gsm.py:\n{errors}"


def test_fltk2gsm_ruff_clean() -> None:
    """§4 item 2 (AC 5): ruff check is clean on fltk2gsm.py."""
    violations = _run_ruff(FLTK2GSM_PATH)
    assert violations == [], f"Unexpected ruff violations in fltk2gsm.py:\n{violations}"


# ---------------------------------------------------------------------------
# §4 item 3 — fltk2gsm.py behavioral equivalence (AC 9)
# ---------------------------------------------------------------------------


def test_fltk2gsm_behavioral_equivalence() -> None:
    """AC 9: fltk2gsm produces same GSM output as before on same input.

    Exercises the existing fegen self-host round-trip; both backends must produce equal GSMs.
    """
    python_gsm = parse_grammar_file(FEGEN_FLTKG_PATH)
    rust_gsm = parse_grammar_file(FEGEN_FLTKG_PATH, rust_fegen_cst_module="fegen_rust_cst")
    assert python_gsm == rust_gsm, "fltk2gsm produces different GSM from Python vs Rust backend"


# ---------------------------------------------------------------------------
# §4 item 4 — Runtime enum values (AC 6)
# ---------------------------------------------------------------------------


def test_protocol_label_members_have_runtime_values() -> None:
    """§4 item 4 (AC 6): Protocol Label members are runtime objects usable in ==."""
    # Access the member — must not be an unbound annotation (which would be None or raise)
    label_item = proto_cst.Items.Label.ITEM
    assert label_item is not None, "Items.Label.ITEM must be a runtime object"
    label_no_ws = proto_cst.Items.Label.NO_WS
    assert label_no_ws is not None, "Items.Label.NO_WS must be a runtime object"

    # Usable in == (compare against a fresh access of the same member to avoid PLR0124)
    assert label_item == proto_cst.Items.Label.ITEM
    assert label_item != label_no_ws

    # Disposition labels
    assert proto_cst.Disposition.Label.INCLUDE is not None
    assert proto_cst.Disposition.Label.SUPPRESS is not None


def test_protocol_nodekind_members_have_runtime_values() -> None:
    """§4 item 4 (AC 6): Protocol NodeKind members are runtime objects usable in ==."""
    kind_items = proto_cst.NodeKind.ITEMS
    assert kind_items is not None
    kind_grammar = proto_cst.NodeKind.GRAMMAR
    assert kind_grammar is not None
    assert kind_items != kind_grammar
    assert kind_items == proto_cst.NodeKind.ITEMS  # compare with fresh access to avoid PLR0124


def test_protocol_import_does_not_import_concrete_backends() -> None:
    """§4 item 4 (AC 6): importing only the protocol module must not import concrete backends."""
    result = subprocess.run(
        [  # noqa: S607
            "uv",
            "run",
            "python",
            "-c",
            (
                "import fltk.fegen.fltk_cst_protocol; "
                "import sys; "
                "assert 'fltk.fegen.fltk_cst' not in sys.modules, "
                "'Importing fltk_cst_protocol pulled in concrete fltk_cst'; "
                "assert 'fltk._native' not in sys.modules, "
                "'Importing fltk_cst_protocol pulled in fltk._native'"
            ),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        "Protocol module import pulled in a concrete backend.\n"
        f"stderr: {result.stderr}\nstdout: {result.stdout}"
    )


# ---------------------------------------------------------------------------
# §4 item 5 — AC 7 cross-backend equality/hash
# ---------------------------------------------------------------------------


class TestCrossBackendEqualityHash:
    """§4 item 5 (AC 7): protocol-module Label/NodeKind members compare equal to Python and Rust
    backend counterparts, both operand orders, with consistent hashing."""

    # --- NodeKind ---

    def test_nodekind_proto_eq_python(self) -> None:
        """proto_cst.NodeKind.ITEMS == py_cst.NodeKind.ITEMS (and reverse)."""
        proto_kind = proto_cst.NodeKind.ITEMS
        py_kind = py_cst.NodeKind.ITEMS
        assert proto_kind == py_kind, "proto NodeKind.ITEMS != python NodeKind.ITEMS"
        assert py_kind == proto_kind, "python NodeKind.ITEMS != proto NodeKind.ITEMS (reverse)"

    def test_nodekind_proto_eq_rust_embedded(self) -> None:
        """proto_cst.NodeKind.ITEMS == embedded_rust_cst.NodeKind.ITEMS (and reverse)."""
        proto_kind = proto_cst.NodeKind.ITEMS
        rust_kind = embedded_rust_cst.NodeKind.ITEMS
        assert proto_kind == rust_kind, "proto NodeKind.ITEMS != embedded rust NodeKind.ITEMS"
        assert rust_kind == proto_kind, "embedded rust NodeKind.ITEMS != proto NodeKind.ITEMS (reverse)"

    def test_nodekind_proto_eq_rust_external(self) -> None:
        """proto_cst.NodeKind.ITEMS == fegen_rust_cst.NodeKind.ITEMS (and reverse)."""
        proto_kind = proto_cst.NodeKind.ITEMS
        rust_kind = fegen_rust_cst.NodeKind.ITEMS
        assert proto_kind == rust_kind, "proto NodeKind.ITEMS != external rust NodeKind.ITEMS"
        assert rust_kind == proto_kind, "external rust NodeKind.ITEMS != proto NodeKind.ITEMS (reverse)"

    def test_nodekind_nonmatching_neq(self) -> None:
        """proto NodeKind.ITEMS != py/rust NodeKind.GRAMMAR."""
        proto_kind = proto_cst.NodeKind.ITEMS
        assert proto_kind != py_cst.NodeKind.GRAMMAR
        assert py_cst.NodeKind.GRAMMAR != proto_kind

    def test_nodekind_hash_consistent(self) -> None:
        """hash(proto NodeKind.X) == hash(py NodeKind.X) == hash(rust NodeKind.X)."""
        for member in ("ITEMS", "GRAMMAR", "RULE", "ITEM"):
            proto_kind = getattr(proto_cst.NodeKind, member)
            py_kind = getattr(py_cst.NodeKind, member)
            rust_emb_kind = getattr(embedded_rust_cst.NodeKind, member)
            rust_ext_kind = getattr(fegen_rust_cst.NodeKind, member)
            assert hash(proto_kind) == hash(py_kind), f"hash mismatch proto vs py for NodeKind.{member}"
            assert hash(proto_kind) == hash(rust_emb_kind), f"hash mismatch proto vs rust emb for NodeKind.{member}"
            assert hash(proto_kind) == hash(rust_ext_kind), f"hash mismatch proto vs rust ext for NodeKind.{member}"

    # --- Label (Items.Label.ITEM) ---

    def test_label_proto_eq_python_matching(self) -> None:
        """proto Items.Label.ITEM == py_cst.Items.Label.ITEM (both operand orders)."""
        proto_label = proto_cst.Items.Label.ITEM
        py_label = py_cst.Items.Label.ITEM
        assert proto_label == py_label, "proto Items.Label.ITEM != py Items.Label.ITEM"
        assert py_label == proto_label, "py Items.Label.ITEM != proto Items.Label.ITEM (reverse)"

    def test_label_proto_eq_rust_embedded_matching(self) -> None:
        """proto Items.Label.ITEM == embedded_rust_cst.Items.Label.ITEM (both orders)."""
        proto_label = proto_cst.Items.Label.ITEM
        rust_label = embedded_rust_cst.Items.Label.ITEM
        assert proto_label == rust_label, "proto Items.Label.ITEM != rust emb Items.Label.ITEM"
        assert rust_label == proto_label, "rust emb Items.Label.ITEM != proto Items.Label.ITEM (reverse)"

    def test_label_proto_eq_rust_external_matching(self) -> None:
        """proto Items.Label.ITEM == fegen_rust_cst.Items.Label.ITEM (both orders)."""
        proto_label = proto_cst.Items.Label.ITEM
        rust_label = fegen_rust_cst.Items.Label.ITEM
        assert proto_label == rust_label, "proto Items.Label.ITEM != rust ext Items.Label.ITEM"
        assert rust_label == proto_label, "rust ext Items.Label.ITEM != proto Items.Label.ITEM (reverse)"

    def test_label_proto_nonmatching_neq(self) -> None:
        """proto Items.Label.ITEM != py/rust Items.Label.NO_WS (nonmatching, both orders)."""
        proto_label = proto_cst.Items.Label.ITEM
        assert proto_label != py_cst.Items.Label.NO_WS
        assert py_cst.Items.Label.NO_WS != proto_label
        assert proto_label != embedded_rust_cst.Items.Label.NO_WS
        assert embedded_rust_cst.Items.Label.NO_WS != proto_label

    def test_label_hash_consistent(self) -> None:
        """hash(proto_label) == hash(py_label) == hash(rust_label) for matching pairs."""
        for member in ("ITEM", "NO_WS", "WS_ALLOWED", "WS_REQUIRED"):
            proto_label = getattr(proto_cst.Items.Label, member)
            py_label = getattr(py_cst.Items.Label, member)
            rust_emb_label = getattr(embedded_rust_cst.Items.Label, member)
            rust_ext_label = getattr(fegen_rust_cst.Items.Label, member)
            assert hash(proto_label) == hash(py_label), f"hash mismatch proto vs py for Items.Label.{member}"
            assert hash(proto_label) == hash(rust_emb_label), (
                f"hash mismatch proto vs rust emb for Items.Label.{member}"
            )
            assert hash(proto_label) == hash(rust_ext_label), (
                f"hash mismatch proto vs rust ext for Items.Label.{member}"
            )

    def test_label_set_collapse_with_proto(self) -> None:
        """{proto_label, py_label, rust_label} has length 1 for matching members."""
        proto_label = proto_cst.Items.Label.ITEM
        py_label = py_cst.Items.Label.ITEM
        rust_label = embedded_rust_cst.Items.Label.ITEM
        s = {proto_label, py_label, rust_label}
        assert len(s) == 1, f"Set did not collapse to 1 for ITEM labels: {s!r}"

    def test_nodekind_set_collapse_with_proto(self) -> None:
        """{proto NodeKind.ITEMS, py NodeKind.ITEMS, rust NodeKind.ITEMS} has length 1."""
        proto_kind = proto_cst.NodeKind.ITEMS
        py_kind = py_cst.NodeKind.ITEMS
        rust_kind = embedded_rust_cst.NodeKind.ITEMS
        s = {proto_kind, py_kind, rust_kind}
        assert len(s) == 1, f"NodeKind.ITEMS set did not collapse to 1: {s!r}"


# ---------------------------------------------------------------------------
# §4 item 6 — AC 12 cross-backend dual-shape dispatch (load-bearing)
# ---------------------------------------------------------------------------


class TestCrossBackendDualShapeDispatch:
    """§4 item 6 (AC 12): protocol-only consumer runs both Shape 1 and Shape 2 against both
    Python-produced and Rust-produced trees; identical, correct dispatch for all 4 combinations.
    Includes case cst.Span.kind: matching Python terminalsrc.Span AND Rust fltk._native.Span.
    No backend-specific code path; no enum-namespace name in the consumer.
    """

    @pytest.fixture(scope="class")
    def python_items(self):
        """First Items node from a Python-backend-parsed grammar."""
        tree = _python_cst_grammar(_SIMPLE_GRAMMAR_TEXT)
        return _get_first_items_node(tree)

    @pytest.fixture(scope="class")
    def rust_items(self):
        """First Items node from a Rust-backend-parsed grammar (embedded fltk._native.fegen_cst)."""
        tree = _rust_cst_grammar(_SIMPLE_GRAMMAR_TEXT)
        return _get_first_items_node(tree)

    # --- Shape 2 dispatch ---

    def _shape2_dispatch(self, items_node) -> list[tuple[str, object]]:
        """Shape 2: match/case dispatch — protocol-only, no enum-namespace exposure."""
        results: list[tuple[str, object]] = []
        for _, child in items_node.children:
            match child.kind:
                case proto_cst.Item.kind:
                    results.append(("item", child))
                case proto_cst.Trivia.kind:
                    results.append(("trivia", child))
                case proto_cst.Span.kind:
                    results.append(("span", child))
                case _:
                    results.append(("other", child))
        return results

    # --- Shape 1 dispatch ---

    def _shape1_interleaved(self, items_node) -> list[tuple[str, object]]:
        """Shape 1: interleaved item/separator walk — protocol-only, no enum-namespace exposure."""
        results: list[tuple[str, object]] = []
        children = items_node.children
        start_idx = 0
        if children and children[0][0] in (
            proto_cst.Items.Label.NO_WS,
            proto_cst.Items.Label.WS_ALLOWED,
            proto_cst.Items.Label.WS_REQUIRED,
        ):
            start_idx = 1
        remaining = children[start_idx:]
        for (item_label, item), (sep_label, _) in zip(remaining[::2], remaining[1::2], strict=False):
            assert item_label == proto_cst.Items.Label.ITEM
            assert item.kind == proto_cst.Item.kind
            results.append(("item", item))
            results.append(("sep_label", sep_label))
        if len(remaining) % 2 != 0:
            item_label, item = remaining[-1]
            assert item_label == proto_cst.Items.Label.ITEM
            assert item.kind == proto_cst.Item.kind
            results.append(("item", item))
        return results

    def test_shape2_python_backend_dispatches_correctly(self, python_items) -> None:
        """Shape 2 + Python backend: items and spans dispatched to correct arms."""
        results = self._shape2_dispatch(python_items)
        item_count = sum(1 for tag, _ in results if tag == "item")
        span_count = sum(1 for tag, _ in results if tag == "span")
        assert item_count >= 1, "Shape 2 (Python): expected at least one Item"
        assert span_count >= 1, "Shape 2 (Python): expected at least one Span (separator)"
        assert all(tag in ("item", "span", "trivia") for tag, _ in results), (
            f"Shape 2 (Python): unexpected 'other' dispatch: {results!r}"
        )

    def test_shape2_rust_backend_dispatches_correctly(self, rust_items) -> None:
        """Shape 2 + Rust backend: items and spans dispatched to correct arms (Rust Span narrowed)."""
        results = self._shape2_dispatch(rust_items)
        item_count = sum(1 for tag, _ in results if tag == "item")
        span_count = sum(1 for tag, _ in results if tag == "span")
        assert item_count >= 1, "Shape 2 (Rust): expected at least one Item"
        assert span_count >= 1, "Shape 2 (Rust): expected at least one Span (Rust separator)"
        assert all(tag in ("item", "span", "trivia") for tag, _ in results), (
            f"Shape 2 (Rust): unexpected 'other' dispatch: {results!r}"
        )

    def test_shape2_python_and_rust_structurally_identical(self, python_items, rust_items) -> None:
        """Shape 2 produces identical structural dispatch results from Python and Rust backends."""
        py_results = [(tag, type(child).__name__) for tag, child in self._shape2_dispatch(python_items)]
        rust_results = [(tag, type(child).__name__) for tag, child in self._shape2_dispatch(rust_items)]
        assert [tag for tag, _ in py_results] == [tag for tag, _ in rust_results], (
            f"Shape 2 dispatch tag sequences differ:\n  Python: {py_results}\n  Rust: {rust_results}"
        )

    def test_shape1_python_backend(self, python_items) -> None:
        """Shape 1 + Python backend: assert item.kind == cst.Item.kind narrows correctly."""
        results = self._shape1_interleaved(python_items)
        item_count = sum(1 for tag, _ in results if tag == "item")
        assert item_count >= 1, "Shape 1 (Python): expected at least one item"

    def test_shape1_rust_backend(self, rust_items) -> None:
        """Shape 1 + Rust backend: assert item.kind == cst.Item.kind narrows correctly."""
        results = self._shape1_interleaved(rust_items)
        item_count = sum(1 for tag, _ in results if tag == "item")
        assert item_count >= 1, "Shape 1 (Rust): expected at least one item"

    def test_shape1_python_and_rust_structurally_identical(self, python_items, rust_items) -> None:
        """Shape 1 produces identical structural tag sequences from Python and Rust backends."""
        py_tags = [tag for tag, _ in self._shape1_interleaved(python_items)]
        rust_tags = [tag for tag, _ in self._shape1_interleaved(rust_items)]
        assert py_tags == rust_tags, (
            f"Shape 1 tag sequences differ:\n  Python: {py_tags}\n  Rust: {rust_tags}"
        )

    def test_span_kind_narrows_rust_backend_span_children(self, rust_items) -> None:
        """Assert that cst.Span.kind matches Span separator children in a Rust-backend Items node.

        The Rust fegen_cst parser (running on top of the Rust CST node classes) still uses
        Python terminalsrc.Span instances for separator children (the Python parser glue code
        creates them via Span(start, end)).  The key invariant is that cst.Span.kind correctly
        identifies them — the match/case dispatch must work regardless of which Span class the
        runtime provides (Python terminalsrc.Span or Rust fltk._native.Span), since both carry
        SpanKind.SPAN with the same canonical string.
        """
        span_children = [(label, child) for label, child in rust_items.children if child.kind == proto_cst.Span.kind]
        assert span_children, (
            "Expected at least one Span child in Rust-backend Items node; none matched via cst.Span.kind"
        )
        # All matched children must have the SpanKind.SPAN kind (by identity or canonical equality)
        for _, child in span_children:
            assert child.kind._fltk_canonical_name == "SpanKind.SPAN", (
                f"Matched span child has wrong canonical name: {child.kind._fltk_canonical_name!r}"
            )

    def test_rust_native_span_kind_also_matches(self) -> None:
        """fltk._native.Span.kind == proto_cst.Span.kind (Rust node .span field Spans match too)."""
        rust_span = RustSpan(1, 5)
        assert rust_span.kind == proto_cst.Span.kind, (
            "fltk._native.Span.kind must equal proto_cst.Span.kind (cross-backend narrowing)"
        )


# ---------------------------------------------------------------------------
# §4 item 7 — Canonical-string agreement invariant
# ---------------------------------------------------------------------------


class TestCanonicalStringAgreement:
    """§4 item 7: canonical strings agree across protocol / Python-concrete / Rust-concrete."""

    def test_nodekind_canonical_strings_agree(self) -> None:
        """NodeKind._fltk_canonical_name agrees across all three backends."""
        for member in ("ITEMS", "GRAMMAR", "RULE", "ITEM", "TERM"):
            proto_kind = getattr(proto_cst.NodeKind, member)
            py_kind = getattr(py_cst.NodeKind, member)
            rust_emb_kind = getattr(embedded_rust_cst.NodeKind, member)
            rust_ext_kind = getattr(fegen_rust_cst.NodeKind, member)

            proto_cn = proto_kind._fltk_canonical_name
            py_cn = py_kind._fltk_canonical_name
            rust_emb_cn = rust_emb_kind._fltk_canonical_name
            rust_ext_cn = rust_ext_kind._fltk_canonical_name

            expected = f"NodeKind.{member}"
            assert proto_cn == expected, f"proto NodeKind.{member} canonical name: {proto_cn!r} != {expected!r}"
            assert py_cn == expected, f"py NodeKind.{member} canonical name: {py_cn!r} != {expected!r}"
            assert rust_emb_cn == expected, (
                f"rust emb NodeKind.{member} canonical name: {rust_emb_cn!r} != {expected!r}"
            )
            assert rust_ext_cn == expected, (
                f"rust ext NodeKind.{member} canonical name: {rust_ext_cn!r} != {expected!r}"
            )

    def test_spankind_canonical_string_agrees(self) -> None:
        """SpanKind.SPAN._fltk_canonical_name agrees across Python Span and Rust Span.kind."""
        py_span_kind = SpanKind.SPAN
        python_span_instance = terminalsrc.Span(1, 5)
        rust_span_instance = RustSpan(1, 5)

        assert py_span_kind._fltk_canonical_name == "SpanKind.SPAN"
        assert python_span_instance.kind._fltk_canonical_name == "SpanKind.SPAN"
        assert rust_span_instance.kind._fltk_canonical_name == "SpanKind.SPAN"

    def test_spankind_rust_span_returns_shared_python_object(self) -> None:
        """Rust Span.kind returns the shared Python SpanKind.SPAN object (same identity)."""
        rust_span = RustSpan(1, 5)
        assert rust_span.kind is SpanKind.SPAN, (
            "Rust Span.kind must return the shared Python SpanKind.SPAN object (same identity)"
        )

    def test_label_canonical_strings_agree(self) -> None:
        """Label._fltk_canonical_name agrees across proto / Python / Rust for Items.Label members."""
        for member in ("ITEM", "NO_WS", "WS_ALLOWED", "WS_REQUIRED"):
            proto_label = getattr(proto_cst.Items.Label, member)
            py_label = getattr(py_cst.Items.Label, member)
            rust_emb_label = getattr(embedded_rust_cst.Items.Label, member)

            expected = f"Items.Label.{member}"
            assert proto_label._fltk_canonical_name == expected
            assert py_label._fltk_canonical_name == expected
            assert rust_emb_label._fltk_canonical_name == expected


# ---------------------------------------------------------------------------
# §4 item 8 — Span equality/hash unchanged
# ---------------------------------------------------------------------------


class TestSpanEqualityHashUnchanged:
    """§4 item 8: adding Span.kind field did not change ==, hash, or repr contracts."""

    def test_span_equality_same_position(self) -> None:
        """Two Spans at the same (start, end) are == regardless of kind (which is constant)."""
        a = terminalsrc.Span(1, 5)
        b = terminalsrc.Span(1, 5)
        assert a == b

    def test_span_equality_different_positions(self) -> None:
        """Spans at different positions are !=."""
        a = terminalsrc.Span(1, 5)
        b = terminalsrc.Span(1, 6)
        assert a != b

    def test_span_hash_same_position(self) -> None:
        """Spans at the same (start, end) hash equal."""
        assert hash(terminalsrc.Span(1, 5)) == hash(terminalsrc.Span(1, 5))

    def test_span_hash_ignores_source(self) -> None:
        """Span hash ignores _source (unchanged by kind field)."""
        with_source = terminalsrc.Span.with_source(1, 5, "hello world")
        without_source = terminalsrc.Span(1, 5)
        assert hash(with_source) == hash(without_source)

    def test_span_sourceless_eq_source_bearing(self) -> None:
        """Span(1, 5) == Span.with_source(1, 5, ...) — the 'sourceless sentinel == source-bearing' invariant."""
        source_span = terminalsrc.Span.with_source(1, 5, "hello world")
        sourceless = terminalsrc.Span(1, 5)
        assert sourceless == source_span

    def test_span_kind_not_in_repr(self) -> None:
        """Span.kind does not appear in repr (repr=False is set)."""
        r = repr(terminalsrc.Span(1, 5))
        assert "kind" not in r, f"Span repr should not include 'kind': {r!r}"
        assert "SpanKind" not in r, f"Span repr should not include 'SpanKind': {r!r}"

    def test_span_construction_unchanged(self) -> None:
        """Span(start, end) and Span(start, end, source) still work (kind has default)."""
        s1 = terminalsrc.Span(0, 5)
        s2 = terminalsrc.Span(0, 5, None)
        assert s1 == s2

    def test_span_kind_field_value(self) -> None:
        """Span.kind is SpanKind.SPAN (the constant field value)."""
        s = terminalsrc.Span(1, 5)
        assert s.kind is SpanKind.SPAN


# ---------------------------------------------------------------------------
# §4 item 9 — Structural-mismatch contract preserved (Option A)
# ---------------------------------------------------------------------------


def test_structural_mismatch_contract_preserved(
    tmp_path: pathlib.Path,
    pyright_available: bool,  # noqa: FBT001
) -> None:
    """§4 item 9: test_boundary_probe_documents_label_mismatch still passes.

    Concrete enum.Enum Label remains non-assignable to the protocol plain-class Label.
    Adding runtime values to Label members (Option A) must NOT make the protocol Label
    structurally compatible with the concrete enum.Enum Label.
    """
    fixture_text = """\
# ruff: noqa
# Probe without type: ignore — used to count raw mismatches.
from __future__ import annotations
from fltk.fegen import fltk_cst_protocol as cstp
from fltk.fegen import fltk_cst

_m: cstp.CstModule = fltk_cst
"""
    fixture = tmp_path / "castless_probe.py"
    fixture.write_text(fixture_text)
    errors = _run_pyright(fixture, pyright_available=pyright_available)
    assert errors, (
        "Expected pyright to report errors for bare fltk_cst -> CstModule assignment "
        "(nested-Label nominal mismatch). The structural-mismatch contract (Option A) has been broken — "
        "protocol Label members becoming runtime values must NOT make the Label classes structurally compatible."
    )


def test_protocol_label_remains_plain_class_not_enum() -> None:
    """§4 item 9 (Option A): protocol Label is a plain class, not an enum.Enum subclass.

    Adding runtime values (Option A) must not change the Label to an enum.
    """
    # Protocol Label is the class itself (accessed on the Protocol, not an instance)
    label_class = proto_cst.Items.Label
    assert not issubclass(label_class, enum.Enum), (
        "Protocol Items.Label must remain a plain class (not an enum.Enum subclass). "
        "Option A requires additive change only — no type promotion."
    )

    # Concrete Label IS an enum.Enum
    concrete_label_class = py_cst.Items.Label
    assert issubclass(concrete_label_class, enum.Enum), (
        "Concrete Items.Label should be an enum.Enum (for the structural mismatch to be real)"
    )

    # Structural mismatch: concrete (enum.Enum) is NOT the same type as protocol (plain class)
    assert type(label_class) is not type(concrete_label_class), (
        "Protocol and concrete Label classes have the same metaclass — structural mismatch may have been lost"
    )
