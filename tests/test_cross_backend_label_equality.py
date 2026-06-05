"""Cross-backend Label and NodeKind equality / hash / membership matrix.

Covers AC1-AC8 from the cross-backend-label-equality design (section 4).

Requires fegen_rust_cst and fltk._native.fegen_cst to be built.
Tests are skipped when the modules are unavailable.

Backend abbreviations used throughout:
  py      — fltk.fegen.fltk_cst (Python dataclass backend)
  emb     — fltk._native.fegen_cst (embedded Rust crate, same abi3 as py)
  ext     — fegen_rust_cst (external Rust crate, separate cdylib)
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

from fltk._native import fegen_cst as emb_cst  # noqa: E402
from fltk.fegen import fltk_cst as py_cst  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Three backend pairs: (backend_A, backend_B)
# Each test is parametrized over these so it exercises py↔ext, py↔emb, emb↔ext.
_BACKEND_PAIRS = [
    ("py", "ext"),
    ("py", "emb"),
    ("emb", "ext"),
]

_BACKENDS = {
    "py": py_cst,
    "emb": emb_cst,
    "ext": fegen_rust_cst,
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
    """AC1-AC7 for Label members, exercised across all three backend pairs."""

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

    def test_ac7_no_raise_on_unrelated_objects(self, a_key: str, b_key: str) -> None:  # noqa: ARG002
        """AC7: comparison against unrelated objects returns False/True, never raises."""
        label = _label(a_key, "Items", "NO_WS")
        unrelated: list[object] = [None, 1, "Items.Label.NO_WS", object()]
        # Also a label from a different class
        unrelated.append(_label(a_key, "Disposition", "INCLUDE"))
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
# AC8: embedded (fltk._native.fegen_cst) ↔ external (fegen_rust_cst) pair
# (covered above as ("emb", "ext"); this class adds a targeted explicit check)
# ---------------------------------------------------------------------------


class TestAC8TwoRustCrates:
    """AC8: fltk._native.fegen_cst and fegen_rust_cst are distinct cdylib crates; equality holds."""

    def test_crates_are_distinct_python_types(self) -> None:
        """The two Rust crates expose distinct Python types for the same class name."""
        assert type(emb_cst.Items.Label.NO_WS) is not type(fegen_rust_cst.Items.Label.NO_WS), (
            "emb and ext crates should have distinct Python types for Items_Label"
        )

    def test_cross_crate_label_eq(self) -> None:
        """emb.Items.Label.NO_WS == ext.Items.Label.NO_WS both directions."""
        a = emb_cst.Items.Label.NO_WS
        b = fegen_rust_cst.Items.Label.NO_WS
        assert a == b
        assert b == a

    def test_cross_crate_hash_agreement(self) -> None:
        """hash agrees between the two distinct Rust crates (both route through CPython hash)."""
        for member in ["NO_WS", "WS_ALLOWED", "ITEM"]:
            a = getattr(emb_cst.Items.Label, member)
            b = getattr(fegen_rust_cst.Items.Label, member)
            assert hash(a) == hash(b), f"hash mismatch between emb and ext crates for Items.Label.{member}"


# ---------------------------------------------------------------------------
# NodeKind cross-backend equality matrix (same contract as Label)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("a_key,b_key", _BACKEND_PAIRS)
class TestNodeKindCrossBackend:
    """NodeKind members carry the same §2.1 cross-backend eq/hash contract as Label."""

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

    def test_no_raise_on_unrelated(self, a_key: str, b_key: str) -> None:  # noqa: ARG002
        """NodeKind comparison against unrelated objects never raises."""
        kind = _nodekind(a_key, "ITEMS")
        for other in [None, 1, "NodeKind.ITEMS", object()]:
            result = kind == other
            assert result is False, f"{a_key}.NodeKind.ITEMS == {other!r} should be False"


# ---------------------------------------------------------------------------
# NodeKind narrowing pyright fixture
#
# This function is type-checked by pyright (via make check) and confirms that
# `node.kind == NodeKind.X` narrows correctly over a homogeneous union of
# kind-bearing node Protocols (§2.4 validation, design §4).
#
# The fixture uses the Protocol types from fltk_cst_protocol — the same
# Protocol surface out-of-tree consumers program against.
# ---------------------------------------------------------------------------

if typing.TYPE_CHECKING:
    from collections.abc import Sequence as _Seq

    from fltk.fegen import fltk_cst_protocol as _proto
    from fltk.fegen.fltk_cst import NodeKind as _NodeKind

    def _narrowing_fixture(node: _proto.Items | _proto.Grammar) -> None:
        """Pyright must narrow each branch correctly with zero errors."""
        if node.kind == _NodeKind.ITEMS:
            # In this branch pyright knows node is Items; Items-specific access is valid.
            _: _Seq[tuple[_proto.Items.Label | None, object]] = node.children
        else:
            # In this branch pyright knows node is Grammar.
            _2: _Seq[tuple[_proto.Grammar.Label | None, object]] = node.children
