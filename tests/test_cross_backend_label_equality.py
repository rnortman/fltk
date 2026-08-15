"""Cross-backend Label and NodeKind equality / hash / membership matrix.

Requires fegen_rust_cst to be built.
Tests are skipped when the modules are unavailable.

Backend abbreviations used throughout:
  py      — fltk.fegen.fltk_cst (Python dataclass backend)
  ext     — fegen_rust_cst (standalone Rust cdylib)
"""

from __future__ import annotations

import typing

import pytest

# ---------------------------------------------------------------------------
# Module-level skip guards
# ---------------------------------------------------------------------------

fegen_rust_cst = pytest.importorskip(
    "fegen_rust_cst",
    reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first",
)

from fltk.fegen import fltk_cst as py_cst  # noqa: E402
from fltk.fegen import fltk_parser  # noqa: E402
from fltk.fegen.pyrt import astrt, terminalsrc  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Two backend pairs: (backend_A, backend_B)
# Each test is parametrized over these so it exercises py↔ext.
_BACKEND_PAIRS = [
    ("py", "ext"),
]

_BACKENDS = {
    "py": py_cst,
    "ext": fegen_rust_cst.cst,
}


def _label(backend_key: str, class_name: str, member_name: str) -> object:
    mod = _BACKENDS[backend_key]
    node_cls = getattr(mod, class_name)
    return getattr(node_cls.Label, member_name)


def _nodekind(backend_key: str, member_name: str) -> object:
    mod = _BACKENDS[backend_key]
    return getattr(mod.NodeKind, member_name)


# ---------------------------------------------------------------------------
# Label cross-backend equality (AC1-AC7) per-pair
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("a_key,b_key", _BACKEND_PAIRS)
class TestLabelCrossBackend:
    """AC1-AC7 for Label members, exercised across all backend pairs."""

    def test_ac1_equal_same_member_both_directions(self, a_key: str, b_key: str) -> None:
        """AC1: A.Items.Label.NO_WS == B.Items.Label.NO_WS both directions."""
        a = _label(a_key, "Items", "NO_WS")
        b = _label(b_key, "Items", "NO_WS")
        assert a == b, f"{a_key}.Items.Label.NO_WS != {b_key}.Items.Label.NO_WS"
        assert b == a, f"{b_key}.Items.Label.NO_WS != {a_key}.Items.Label.NO_WS (reflected)"

    def test_ac2_unequal_different_member(self, a_key: str, b_key: str) -> None:
        """AC2: NO_WS != WS_ALLOWED; != is True both directions."""
        a = _label(a_key, "Items", "NO_WS")
        b = _label(b_key, "Items", "WS_ALLOWED")
        assert not (a == b), f"{a_key}.NO_WS should not == {b_key}.WS_ALLOWED"
        assert a != b
        assert b != a

    def test_ac3_same_backend_self_eq_unchanged(self, a_key: str, b_key: str) -> None:
        """AC3: within each backend, X == X is True; distinct members are !=."""
        for key in (a_key, b_key):
            x = _label(key, "Items", "NO_WS")
            y = _label(key, "Items", "WS_ALLOWED")
            z = x  # same object; name compare to satisfy PLR0124 linter
            assert z == x, f"{key}.NO_WS != itself"
            assert x != y, f"{key}.NO_WS should not == {key}.WS_ALLOWED"

    def test_ac4_hash_consistent_cross_backend(self, a_key: str, b_key: str) -> None:
        """AC4: hash(A.X) == hash(B.X) whenever A.X == B.X."""
        members = ["NO_WS", "WS_ALLOWED", "WS_REQUIRED", "ITEM"]
        for member in members:
            a = _label(a_key, "Items", member)
            b = _label(b_key, "Items", member)
            assert hash(a) == hash(b), f"hash({a_key}.Items.Label.{member}) != hash({b_key}.Items.Label.{member})"
        # Also verify a second label class to catch per-enum-type hash bugs
        for disp_member in ["INCLUDE", "SUPPRESS"]:
            a_disp = _label(a_key, "Disposition", disp_member)
            b_disp = _label(b_key, "Disposition", disp_member)
            assert hash(a_disp) == hash(b_disp), (
                f"hash({a_key}.Disposition.Label.{disp_member}) != hash({b_key}.Disposition.Label.{disp_member})"
            )

    def test_ac5_set_collapse(self, a_key: str, b_key: str) -> None:
        """AC5: {A.X, B.X} has length 1; B.X in {A.X} is True; dict round-trip works."""
        a = _label(a_key, "Items", "NO_WS")
        b = _label(b_key, "Items", "NO_WS")
        s = {a, b}
        assert len(s) == 1, f"Set collapsed to {len(s)} entries instead of 1 for {a_key}↔{b_key}"
        assert b in {a}, f"{b_key}.NO_WS not found in set containing {a_key}.NO_WS"
        d = {a: "value"}
        assert d[b] == "value", f"Dict keyed by {a_key}.NO_WS not retrievable with {b_key}.NO_WS"

    def test_ac6_membership_in_tuple(self, a_key: str, b_key: str) -> None:
        """AC6: B.X in (A.X, A.Y) is True when X matches."""
        b_no_ws = _label(b_key, "Items", "NO_WS")
        a_no_ws = _label(a_key, "Items", "NO_WS")
        a_ws_allowed = _label(a_key, "Items", "WS_ALLOWED")
        assert b_no_ws in (a_no_ws, a_ws_allowed), f"{b_key}.NO_WS not found in tuple of {a_key} labels"
        # Also check it is NOT found when not present
        a_ws_req = _label(a_key, "Items", "WS_REQUIRED")
        b_item = _label(b_key, "Items", "ITEM")
        assert b_item not in (a_no_ws, a_ws_allowed, a_ws_req), (
            f"{b_key}.ITEM incorrectly found in tuple not containing it"
        )

    def test_ac7_no_raise_on_unrelated_objects(self, a_key: str, b_key: str) -> None:
        """AC7: comparison against unrelated objects returns False/True, never raises."""
        label = _label(a_key, "Items", "NO_WS")
        unrelated: list[object] = [None, 1, "Items.Label.NO_WS", object()]
        # Same-backend cross-class label
        unrelated.append(_label(a_key, "Disposition", "INCLUDE"))
        # Cross-backend cross-class label (exercises canonical-name path with different class prefix)
        unrelated.append(_label(b_key, "Disposition", "INCLUDE"))
        for other in unrelated:
            # Must not raise
            result_eq = label == other
            result_ne = label != other
            assert result_eq is False, f"{a_key}.NO_WS == {other!r} should be False"
            assert result_ne is True, f"{a_key}.NO_WS != {other!r} should be True"
            # Symmetric direction
            result_eq_sym = other == label
            result_ne_sym = other != label
            assert result_eq_sym is False, f"{other!r} == {a_key}.NO_WS should be False"
            assert result_ne_sym is True, f"{other!r} != {a_key}.NO_WS should be True"


# ---------------------------------------------------------------------------
# AC8: py ↔ ext cross-backend pair explicit checks
# ---------------------------------------------------------------------------


class TestAC8PyRustCross:
    """AC8: py and fegen_rust_cst.cst are distinct implementations; equality holds."""

    def test_crates_are_distinct_python_types(self) -> None:
        """The Python and Rust crates expose distinct Python types for the same class name."""
        assert type(py_cst.Items.Label.NO_WS) is not type(fegen_rust_cst.cst.Items.Label.NO_WS), (
            "py and ext crates should have distinct Python types for Items_Label"
        )

    def test_cross_backend_label_eq(self) -> None:
        """py.Items.Label.NO_WS == ext.Items.Label.NO_WS both directions."""
        a = py_cst.Items.Label.NO_WS
        b = fegen_rust_cst.cst.Items.Label.NO_WS
        assert a == b
        assert b == a

    def test_cross_backend_hash_agreement(self) -> None:
        """hash agrees between the Python and Rust backends."""
        for member in ["NO_WS", "WS_ALLOWED", "ITEM"]:
            a = getattr(py_cst.Items.Label, member)
            b = getattr(fegen_rust_cst.cst.Items.Label, member)
            assert hash(a) == hash(b), f"hash mismatch between py and ext for Items.Label.{member}"


# ---------------------------------------------------------------------------
# NodeKind cross-backend equality matrix (same contract as Label)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("a_key,b_key", _BACKEND_PAIRS)
class TestNodeKindCrossBackend:
    """NodeKind members carry the same cross-backend eq/hash contract as Label."""

    def test_equal_same_member_both_directions(self, a_key: str, b_key: str) -> None:
        """A.NodeKind.ITEMS == B.NodeKind.ITEMS both directions."""
        a = _nodekind(a_key, "ITEMS")
        b = _nodekind(b_key, "ITEMS")
        assert a == b
        assert b == a

    def test_unequal_different_member(self, a_key: str, b_key: str) -> None:
        """A.NodeKind.ITEMS != B.NodeKind.GRAMMAR."""
        a = _nodekind(a_key, "ITEMS")
        b = _nodekind(b_key, "GRAMMAR")
        assert a != b
        assert b != a

    def test_hash_consistent(self, a_key: str, b_key: str) -> None:
        """hash(A.NodeKind.X) == hash(B.NodeKind.X)."""
        for member in ["ITEMS", "GRAMMAR", "RULE", "ITEM"]:
            a = _nodekind(a_key, member)
            b = _nodekind(b_key, member)
            assert hash(a) == hash(b), f"hash mismatch for NodeKind.{member} between {a_key} and {b_key}"

    def test_set_collapse(self, a_key: str, b_key: str) -> None:
        """{A.NodeKind.ITEMS, B.NodeKind.ITEMS} has length 1."""
        a = _nodekind(a_key, "ITEMS")
        b = _nodekind(b_key, "ITEMS")
        assert len({a, b}) == 1

    def test_canonical_strings_disjoint_from_label(self, a_key: str, b_key: str) -> None:
        """NodeKind canonical strings never match Label canonical strings (family disjoint)."""
        kind = _nodekind(a_key, "ITEMS")
        label = _label(b_key, "Items", "NO_WS")
        assert kind != label, "NodeKind.ITEMS should not equal Items.Label.NO_WS"
        # Also verify the canonical strings have the right form
        kind_cn: str = kind._fltk_canonical_name  # type: ignore[union-attr]
        label_cn: str = label._fltk_canonical_name  # type: ignore[union-attr]
        assert ".Label." in label_cn, f"Label canonical name should contain '.Label.': {label_cn!r}"
        assert ".Label." not in kind_cn, f"NodeKind canonical name should not contain '.Label.': {kind_cn!r}"
        assert kind_cn.startswith("NodeKind."), f"NodeKind canonical name should start with 'NodeKind.': {kind_cn!r}"
        # Critical disjointness check: NodeKind.ITEM and Items.Label.ITEM share the same word
        # ("ITEM"); verify the two families' canonical strings are still disjoint.
        kind_item = _nodekind(a_key, "ITEM")
        label_item = _label(b_key, "Items", "ITEM")
        kind_item_cn: str = kind_item._fltk_canonical_name  # type: ignore[union-attr]
        label_item_cn: str = label_item._fltk_canonical_name  # type: ignore[union-attr]
        assert kind_item_cn != label_item_cn, (
            f"NodeKind.ITEM and Items.Label.ITEM canonical strings must differ: {kind_item_cn!r} vs {label_item_cn!r}"
        )
        assert kind_item != label_item, "NodeKind.ITEM should not equal Items.Label.ITEM"

    def test_no_raise_on_unrelated(self, a_key: str, b_key: str) -> None:
        """NodeKind comparison against unrelated objects never raises; symmetric direction included."""
        kind = _nodekind(a_key, "ITEMS")
        unrelated: list[object] = [None, 1, "NodeKind.ITEMS", object()]
        # Also include a cross-backend label (cross-family, canonical strings disjoint by construction)
        unrelated.append(_label(b_key, "Items", "NO_WS"))
        for other in unrelated:
            result_eq = kind == other
            result_ne = kind != other
            assert result_eq is False, f"{a_key}.NodeKind.ITEMS == {other!r} should be False"
            assert result_ne is True, f"{a_key}.NodeKind.ITEMS != {other!r} should be True"
            # Symmetric direction: other.__eq__(kind) or Python fallback
            result_eq_sym = other == kind
            result_ne_sym = other != kind
            assert result_eq_sym is False, f"{other!r} == {a_key}.NodeKind.ITEMS should be False"
            assert result_ne_sym is True, f"{other!r} != {a_key}.NodeKind.ITEMS should be True"


# ---------------------------------------------------------------------------
# Marker scope: node objects must NOT expose _fltk_canonical_name
# ---------------------------------------------------------------------------


class TestMarkerScope:
    """The _fltk_canonical_name marker must not appear on node objects.

    If a node exposed the marker, `node == label` could accidentally return True
    (if their canonical strings coincided), breaking the invariant that node==label is False.
    """

    def test_python_node_has_no_canonical_name_marker(self) -> None:
        """Python Items() node does not expose _fltk_canonical_name."""
        node = py_cst.Items()
        assert not hasattr(node, "_fltk_canonical_name"), (
            "Python node should not expose _fltk_canonical_name; marker is for Label/NodeKind only"
        )

    def test_rust_node_has_no_canonical_name_marker(self) -> None:
        """Rust Items() node does not expose _fltk_canonical_name."""
        node = fegen_rust_cst.cst.Items()
        assert not hasattr(node, "_fltk_canonical_name"), (
            "Rust node should not expose _fltk_canonical_name; marker is for Label/NodeKind only"
        )

    def test_node_neq_label_python(self) -> None:
        """Python node != Python label (node == label must be False, not True via canonical-name path)."""
        node = py_cst.Items()
        label = py_cst.Items.Label.ITEM
        assert node != label, "Items() node should not equal Items.Label.ITEM"
        assert not (node == label), "Items() == Items.Label.ITEM should be False"

    def test_node_neq_label_cross_backend(self) -> None:
        """Python node != Rust label (cross-backend path must also stay False)."""
        node = py_cst.Items()
        label = fegen_rust_cst.cst.Items.Label.ITEM
        assert node != label, "Python Items() node should not equal Rust Items.Label.ITEM"
        assert not (node == label), "Python Items() == Rust Items.Label.ITEM should be False"


# ---------------------------------------------------------------------------
# astrt.bucket_children over a real Rust CST
# ---------------------------------------------------------------------------

_BUCKETING_GRAMMAR = """\
grammar := rule+ ;
rule := name:identifier , ":=" , alternatives:alternatives , ";" ;
"""


def _bucket_shape(node: object) -> list[tuple[str, ...]]:
    """Every node's bucket keys with their child counts, in document order.

    ``bucket_children`` is the one place a generated ``from_cst`` reads labels, and it keys on
    the cross-backend canonical name; identical shapes from both backends is what makes one
    generated AST module convert either one's CST.
    """
    children = typing.cast("list[tuple[typing.Any, typing.Any]]", node.children)  # type: ignore[attr-defined]
    buckets = astrt.bucket_children(children)
    shape: list[tuple[str, ...]] = [tuple(f"{key}={len(value)}" for key, value in sorted(buckets.items()))]
    for _label, child in children:
        if hasattr(child, "children"):
            shape.extend(_bucket_shape(child))
    return shape


class TestBucketChildrenAcrossBackends:
    """bucket_children over genuine PyO3 labels must produce the same shape as over Python labels."""

    @staticmethod
    def _rust_grammar_node(text: str) -> object:
        parser = fegen_rust_cst.parser.Parser(text, capture_trivia=False)
        result = parser.apply__parse_grammar(0)
        assert result is not None, parser.error_message()
        assert result.pos == len(text), parser.error_message()
        return result.result

    @staticmethod
    def _python_grammar_node(text: str) -> object:
        terminals = terminalsrc.TerminalSource(text)
        parser = fltk_parser.Parser(terminalsrc=terminals)
        result = parser.apply__parse_grammar(0)
        assert result is not None
        assert result.pos == len(terminals.terminals)
        return result.result

    def test_a_rust_cst_buckets_exactly_like_the_python_one(self) -> None:
        """Rust labels are pyclasses with no ``.name``; the canonical-name key is what bridges them."""
        rust_shape = _bucket_shape(self._rust_grammar_node(_BUCKETING_GRAMMAR))
        python_shape = _bucket_shape(self._python_grammar_node(_BUCKETING_GRAMMAR))

        assert rust_shape == python_shape
        assert any("RULE=" in entry for row in rust_shape for entry in row), rust_shape

    def test_the_keys_are_the_python_enum_member_names(self) -> None:
        """A key drift on either side would make every generated converter miss its children."""
        node = self._rust_grammar_node(_BUCKETING_GRAMMAR)
        children = typing.cast("list[tuple[typing.Any, typing.Any]]", node.children)  # type: ignore[attr-defined]

        assert set(astrt.bucket_children(children)) == {py_cst.Grammar.Label.RULE.name}
