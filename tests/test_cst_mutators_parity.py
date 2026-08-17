"""Cross-backend parity tests for named CST mutators.

Asserts identical resulting trees (kind/label/span sequences) and — for errors — identical
exception type and message text across the Python dataclass backend and the Rust backend.

Backend abbreviations:
  py  — fltk.fegen.fltk_cst (Python dataclass backend)
  rust — fegen_rust_cst.cst (standalone Rust cdylib)

Both backends use fegen CST node classes (Identifier has one label, Items has four).
Identifier: single-label node; children are Spans.
Items: multi-label node; children are Spans and sub-nodes.

Note on span equality: terminalsrc.Span (Python) and fltk._native.Span (Rust) are not ==
even for matching start/end. Parity helpers compare span .start/.end directly, and label
equality is cross-backend.

Span hand-in asymmetry: Python backend accepts both terminalsrc.Span and native Span;
Rust backend accepts only native Span. Tests that verify span hand-in separately
are in the per-backend sections below (excluded from the exact-parity matrix).
"""

from __future__ import annotations

import ast
import subprocess
import sys
import textwrap

import pytest

pytest.importorskip("fltk._native", reason="Rust extension not available")
fegen_rust_cst_mod = pytest.importorskip(
    "fegen_rust_cst", reason="fegen_rust_cst not importable; it is built by //crates/fegen-rust:fegen_rust_cst"
)

import fegen_rust_cst.cst as rust_cst  # noqa: E402

from fltk._native import Span as NativeSpan  # noqa: E402
from fltk.fegen import fltk_cst as py_cst  # noqa: E402
from fltk.fegen import fltk_cst_protocol as py_protocol  # noqa: E402
from fltk.fegen.pyrt import terminalsrc  # noqa: E402
from tests.gsm2tree_helpers import make_generator as _make_generator  # noqa: E402
from tests.gsm2tree_helpers import make_zero_label_grammar as _make_zero_label_grammar  # noqa: E402

# ---------------------------------------------------------------------------
# Backend parametrization
# ---------------------------------------------------------------------------

# Each backend entry: (key, module, span_factory)
# span_factory(start, end) → a valid span for that backend.
_BACKENDS = {
    "py": (py_cst, terminalsrc.Span),
    "rust": (rust_cst, NativeSpan),
}
_BACKEND_KEYS = list(_BACKENDS.keys())


def _mod(backend: str):
    return _BACKENDS[backend][0]


def _span(backend: str, start: int = 0, end: int = 1):
    return _BACKENDS[backend][1](start, end)


def _span_eq(a, b) -> bool:
    """True when two spans have equal start/end regardless of backend type."""
    return a.start == b.start and a.end == b.end


def _children_equal(py_ch: list, rust_ch: list) -> bool:
    """Compare two children lists cross-backend: label equality + span value equality."""
    if len(py_ch) != len(rust_ch):
        return False
    for (pl, pc), (rl, rc) in zip(py_ch, rust_ch, strict=False):
        if pl != rl:
            return False
        if not _span_eq(pc, rc):
            return False
    return True


# ---------------------------------------------------------------------------
# Single-backend helpers for parametrized tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# insert — head / middle / tail / negative / clamping / labeled / unlabeled
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestInsert:
    """insert behavior parametrized over both backends."""

    def test_insert_head(self, backend: str) -> None:
        """insert(0, child) prepends."""
        mod = _mod(backend)
        node = mod.Identifier()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        node.append_name(s0)
        node.insert(0, s1, mod.Identifier.Label.NAME)
        ch = node.children
        assert len(ch) == 2
        assert ch[0][0] == mod.Identifier.Label.NAME
        assert _span_eq(ch[0][1], s1)
        assert _span_eq(ch[1][1], s0)

    def test_insert_tail(self, backend: str) -> None:
        """insert(len, child) appends."""
        mod = _mod(backend)
        node = mod.Identifier()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        node.append_name(s0)
        node.insert(1, s1, mod.Identifier.Label.NAME)
        ch = node.children
        assert len(ch) == 2
        assert _span_eq(ch[1][1], s1)

    def test_insert_middle(self, backend: str) -> None:
        """insert(1, child) inserts at index 1 in a 3-item list."""
        mod = _mod(backend)
        node = mod.Identifier()
        spans = [_span(backend, i, i + 1) for i in range(3)]
        for s in [spans[0], spans[2]]:
            node.append_name(s)
        node.insert(1, spans[1], mod.Identifier.Label.NAME)
        ch = node.children
        assert len(ch) == 3
        for i, s in enumerate(spans):
            assert _span_eq(ch[i][1], s)

    def test_insert_negative_index(self, backend: str) -> None:
        """insert(-1, child) inserts before last element."""
        mod = _mod(backend)
        node = mod.Identifier()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        s_new = _span(backend, 5, 6)
        node.append_name(s0)
        node.append_name(s1)
        node.insert(-1, s_new, mod.Identifier.Label.NAME)
        ch = node.children
        assert len(ch) == 3
        assert _span_eq(ch[1][1], s_new)
        assert _span_eq(ch[2][1], s1)

    def test_insert_clamp_large_positive(self, backend: str) -> None:
        """insert(10**25, child) on 2-item node clamps to append."""
        mod = _mod(backend)
        node = mod.Identifier()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        s_new = _span(backend, 5, 6)
        node.append_name(s0)
        node.append_name(s1)
        node.insert(10**25, s_new, mod.Identifier.Label.NAME)
        ch = node.children
        assert len(ch) == 3
        assert _span_eq(ch[2][1], s_new)

    def test_insert_clamp_large_negative(self, backend: str) -> None:
        """insert(-10**25, child) on 2-item node clamps to prepend."""
        mod = _mod(backend)
        node = mod.Identifier()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        s_new = _span(backend, 5, 6)
        node.append_name(s0)
        node.append_name(s1)
        node.insert(-(10**25), s_new, mod.Identifier.Label.NAME)
        ch = node.children
        assert len(ch) == 3
        assert _span_eq(ch[0][1], s_new)

    def test_insert_labeled(self, backend: str) -> None:
        """insert with explicit label stores the label correctly."""
        mod = _mod(backend)
        node = mod.Identifier()
        s = _span(backend, 0, 1)
        node.insert(0, s, mod.Identifier.Label.NAME)
        ch = node.children
        assert len(ch) == 1
        assert ch[0][0] == mod.Identifier.Label.NAME

    def test_insert_unlabeled(self, backend: str) -> None:
        """insert without label (default None) stores (None, child)."""
        mod = _mod(backend)
        node = mod.Identifier()
        s = _span(backend, 0, 1)
        node.insert(0, s)
        ch = node.children
        assert len(ch) == 1
        assert ch[0][0] is None

    def test_insert_empty_node(self, backend: str) -> None:
        """insert on empty node always succeeds regardless of index."""
        mod = _mod(backend)
        node = mod.Identifier()
        s = _span(backend, 0, 1)
        node.insert(42, s, mod.Identifier.Label.NAME)
        assert len(node.children) == 1

    def test_insert_bool_index(self, backend: str) -> None:
        """bool is int subclass; insert(True, child) inserts at index 1."""
        mod = _mod(backend)
        node = mod.Identifier()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        node.append_name(s0)
        node.append_name(s1)
        s_new = _span(backend, 5, 6)
        node.insert(True, s_new, mod.Identifier.Label.NAME)  # True == 1
        assert len(node.children) == 3
        assert _span_eq(node.children[1][1], s_new)


# ---------------------------------------------------------------------------
# remove_at — positive / negative / return value / out-of-range / empty
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestRemoveAt:
    """remove_at behavior parametrized over both backends."""

    def test_remove_at_positive(self, backend: str) -> None:
        """remove_at(0) on single-element node removes and returns it."""
        mod = _mod(backend)
        node = mod.Identifier()
        s = _span(backend, 3, 7)
        node.append_name(s)
        lbl, child = node.remove_at(0)
        assert lbl == mod.Identifier.Label.NAME
        assert _span_eq(child, s)
        assert len(node.children) == 0

    def test_remove_at_negative(self, backend: str) -> None:
        """remove_at(-1) removes the last element."""
        mod = _mod(backend)
        node = mod.Identifier()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        node.append_name(s0)
        node.append_name(s1)
        _lbl, child = node.remove_at(-1)
        assert _span_eq(child, s1)
        assert len(node.children) == 1
        assert _span_eq(node.children[0][1], s0)

    def test_remove_at_return_matches_children(self, backend: str) -> None:
        """Return value of remove_at equals the prior children[index] entry."""
        mod = _mod(backend)
        node = mod.Items()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        node.append_item(s0)
        node.append_no_ws(s1)
        # Read what children[0] looks like before removal
        prior = node.children[0]
        lbl, child = node.remove_at(0)
        assert lbl == prior[0]
        assert _span_eq(child, prior[1])

    def test_remove_at_empty_node_raises(self, backend: str) -> None:
        """remove_at(0) on empty node raises IndexError with parity message."""
        mod = _mod(backend)
        node = mod.Identifier()
        with pytest.raises(IndexError, match=r"Identifier\.remove_at: index 0 out of range \(0 children\)"):
            node.remove_at(0)

    def test_remove_at_out_of_range_positive(self, backend: str) -> None:
        """remove_at(5) on 1-item node raises IndexError."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        with pytest.raises(IndexError, match=r"Identifier\.remove_at: index 5 out of range \(1 children\)"):
            node.remove_at(5)

    def test_remove_at_out_of_range_negative(self, backend: str) -> None:
        """remove_at(-2) on 1-item node raises IndexError."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        with pytest.raises(IndexError, match=r"Identifier\.remove_at: index -2 out of range \(1 children\)"):
            node.remove_at(-2)

    def test_remove_at_large_positive_out_of_range(self, backend: str) -> None:
        """remove_at(10**25) on 1-item node raises IndexError with exact message."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        big = 10**25
        with pytest.raises(IndexError, match=rf"Identifier\.remove_at: index {big} out of range \(1 children\)"):
            node.remove_at(big)

    def test_remove_at_large_negative_out_of_range(self, backend: str) -> None:
        """remove_at(-10**25) on 1-item node raises IndexError with exact message."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        big = -(10**25)
        with pytest.raises(IndexError, match=rf"Identifier\.remove_at: index {big} out of range \(1 children\)"):
            node.remove_at(big)

    def test_remove_at_middle(self, backend: str) -> None:
        """remove_at(1) removes the middle element from a 3-element node."""
        mod = _mod(backend)
        node = mod.Identifier()
        spans = [_span(backend, i, i + 1) for i in range(3)]
        for s in spans:
            node.append_name(s)
        _lbl, child = node.remove_at(1)
        assert _span_eq(child, spans[1])
        ch = node.children
        assert len(ch) == 2
        assert _span_eq(ch[0][1], spans[0])
        assert _span_eq(ch[1][1], spans[2])


# ---------------------------------------------------------------------------
# replace_at — order/length preservation / label=None clears / out-of-range
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestReplaceAt:
    """replace_at behavior parametrized over both backends."""

    def test_replace_at_preserves_length(self, backend: str) -> None:
        """replace_at does not change length."""
        mod = _mod(backend)
        node = mod.Identifier()
        s_old = _span(backend, 0, 1)
        s_new = _span(backend, 5, 6)
        node.append_name(s_old)
        node.replace_at(0, s_new, mod.Identifier.Label.NAME)
        assert len(node.children) == 1

    def test_replace_at_updates_child(self, backend: str) -> None:
        """replace_at(i, new) updates the child at position i."""
        mod = _mod(backend)
        node = mod.Identifier()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        s_new = _span(backend, 5, 6)
        node.append_name(s0)
        node.append_name(s1)
        node.replace_at(0, s_new, mod.Identifier.Label.NAME)
        ch = node.children
        assert _span_eq(ch[0][1], s_new)
        assert _span_eq(ch[1][1], s1)

    def test_replace_at_label_none_clears_label(self, backend: str) -> None:
        """replace_at with label=None clears the old label (None != preserve)."""
        mod = _mod(backend)
        node = mod.Identifier()
        s_old = _span(backend, 0, 1)
        s_new = _span(backend, 5, 6)
        node.append_name(s_old)  # starts with NAME label
        node.replace_at(0, s_new)  # label=None (default)
        ch = node.children
        assert ch[0][0] is None

    def test_replace_at_negative_index(self, backend: str) -> None:
        """replace_at(-1, new) replaces the last element."""
        mod = _mod(backend)
        node = mod.Identifier()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        s_new = _span(backend, 5, 6)
        node.append_name(s0)
        node.append_name(s1)
        node.replace_at(-1, s_new, mod.Identifier.Label.NAME)
        ch = node.children
        assert _span_eq(ch[0][1], s0)
        assert _span_eq(ch[1][1], s_new)

    def test_replace_at_out_of_range(self, backend: str) -> None:
        """replace_at out of range raises IndexError with parity message."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        with pytest.raises(IndexError, match=r"Identifier\.replace_at: index 5 out of range \(1 children\)"):
            node.replace_at(5, _span(backend, 1, 2))

    def test_replace_at_large_out_of_range(self, backend: str) -> None:
        """replace_at(10**25) on 1-item node raises IndexError with exact message."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        big = 10**25
        with pytest.raises(IndexError, match=rf"Identifier\.replace_at: index {big} out of range \(1 children\)"):
            node.replace_at(big, _span(backend, 1, 2))

    def test_replace_at_large_negative_out_of_range(self, backend: str) -> None:
        """replace_at(-(10**25)) on 1-item node raises IndexError with exact message."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        big = -(10**25)
        with pytest.raises(IndexError, match=rf"Identifier\.replace_at: index {big} out of range \(1 children\)"):
            node.replace_at(big, _span(backend, 1, 2))

    def test_replace_at_returns_none(self, backend: str) -> None:
        """replace_at returns None (assignment-like; callers read children[i] first if needed)."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        result = node.replace_at(0, _span(backend, 1, 2), mod.Identifier.Label.NAME)
        assert result is None


# ---------------------------------------------------------------------------
# clear — populated and empty nodes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestClear:
    """clear behavior parametrized over both backends."""

    def test_clear_populated(self, backend: str) -> None:
        """clear() removes all children from a populated node."""
        mod = _mod(backend)
        node = mod.Identifier()
        for i in range(5):
            node.append_name(_span(backend, i, i + 1))
        assert len(node.children) == 5
        node.clear()
        assert len(node.children) == 0

    def test_clear_empty_noop(self, backend: str) -> None:
        """clear() on empty node is a no-op."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.clear()  # must not raise
        assert len(node.children) == 0

    def test_clear_returns_none(self, backend: str) -> None:
        """clear() returns None."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        assert node.clear() is None


# ---------------------------------------------------------------------------
# Error behavior — bad label type, bad child type, non-index-able index
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestErrorBehavior:
    """Error type and message parity across backends."""

    def test_bad_label_type_insert(self, backend: str) -> None:
        """insert with non-Label label raises TypeError with parity message."""
        mod = _mod(backend)
        node = mod.Identifier()
        s = _span(backend, 0, 1)
        with pytest.raises(TypeError, match=r"Identifier\.insert: label argument is not a Identifier_Label; got str"):
            node.insert(0, s, label="bad_label")  # type: ignore[arg-type]

    def test_bad_label_type_replace_at(self, backend: str) -> None:
        """replace_at with non-Label label raises TypeError with parity message."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        with pytest.raises(
            TypeError, match=r"Identifier\.replace_at: label argument is not a Identifier_Label; got str"
        ):
            node.replace_at(0, _span(backend, 1, 2), label="bad")  # type: ignore[arg-type]

    def test_bad_child_type_insert(self, backend: str) -> None:
        """insert with bad child type raises TypeError."""
        mod = _mod(backend)
        node = mod.Items()
        with pytest.raises(TypeError):
            node.insert(0, "not_a_span")  # type: ignore[arg-type]

    def test_bad_child_type_replace_at(self, backend: str) -> None:
        """replace_at with bad child type raises TypeError."""
        mod = _mod(backend)
        node = mod.Items()
        node.append_item(_span(backend, 0, 1))
        with pytest.raises(TypeError):
            node.replace_at(0, "not_a_span")  # type: ignore[arg-type]

    def test_non_index_remove_at_raises_type_error(self, backend: str) -> None:
        """remove_at with non-index raises TypeError (operator.index semantics)."""
        mod = _mod(backend)
        node = mod.Identifier()
        with pytest.raises(TypeError):
            node.remove_at("not_an_int")  # type: ignore[arg-type]

    def test_non_index_replace_at_raises_type_error(self, backend: str) -> None:
        """replace_at with non-index raises TypeError (operator.index semantics)."""
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        with pytest.raises(TypeError):
            node.replace_at("not_an_int", _span(backend, 1, 2))  # type: ignore[arg-type]

    def test_non_index_insert_raises_type_error(self, backend: str) -> None:
        """insert with non-index raises TypeError (operator.index semantics)."""
        mod = _mod(backend)
        node = mod.Identifier()
        with pytest.raises(TypeError):
            node.insert("not_an_int", _span(backend, 0, 1))  # type: ignore[arg-type]

    @pytest.mark.parametrize("mutator", ["append", "extend", "insert", "replace_at"])
    def test_bad_label_wins_over_bad_child(self, backend: str, mutator: str) -> None:
        """One validation order everywhere: the label is resolved before the child is looked at.

        Error precedence is the only thing this decides for `append` / `extend` (neither can
        mutate partially), which is exactly why it should not vary per mutator.
        """
        mod = _mod(backend)
        node = mod.Identifier()
        node.append_name(_span(backend, 0, 1))
        calls = {
            "append": lambda: node.append("not_a_span", label="bad_label"),
            "extend": lambda: node.extend(["not_a_span"], label="bad_label"),
            "insert": lambda: node.insert(0, "not_a_span", label="bad_label"),
            "replace_at": lambda: node.replace_at(0, "not_a_span", label="bad_label"),
        }
        with pytest.raises(TypeError, match="label argument is not a Identifier_Label"):
            calls[mutator]()
        assert len(node.children) == 1

    def test_wrong_backend_label_on_insert(self, backend: str) -> None:
        """Passing an Items.Label to an Identifier.insert raises TypeError."""
        mod = _mod(backend)
        node = mod.Identifier()
        s = _span(backend, 0, 1)
        with pytest.raises(TypeError):
            node.insert(0, s, label=mod.Items.Label.ITEM)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Labels are values: matched by canonical name, normalized to the node's own member
# ---------------------------------------------------------------------------

_LABELED_MUTATORS = ["append", "extend", "insert", "replace_at"]


def _mutate_with_label(node, mutator: str, backend: str, label) -> None:
    """Drive one labeled mutator so the node ends up holding exactly one labeled child."""
    span = _span(backend, 0, 1)
    if mutator == "append":
        node.append(span, label)
    elif mutator == "extend":
        node.extend([span], label)
    elif mutator == "insert":
        node.insert(0, span, label)
    elif mutator == "replace_at":
        node.append_name(_span(backend, 5, 6))
        node.replace_at(0, span, label)
    else:  # pragma: no cover - guards a typo in the parametrization
        msg = f"unknown mutator {mutator!r}"
        raise AssertionError(msg)


class _SpoofedLabel:
    """An arbitrary object carrying a real label's canonical name.

    Canonical name *is* label identity — it is already the cross-backend ``__eq__``/``__hash__``
    key — so this resolves like any other spelling of that label.
    """

    _fltk_canonical_name = "Identifier.Label.NAME"


class _UnhashableCanonicalName:
    """Canonical name that is not a string and cannot even be hashed."""

    _fltk_canonical_name = ["Identifier.Label.NAME"]  # noqa: RUF012


class _NonStringCanonicalName:
    """Canonical name that is hashable but not a string."""

    _fltk_canonical_name = 7


class _CanonicalNameError(RuntimeError):
    pass


class _RaisingLabel:
    """A label-like object whose canonical name cannot be read."""

    @property
    def _fltk_canonical_name(self) -> str:
        raise _CanonicalNameError


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
@pytest.mark.parametrize("mutator", _LABELED_MUTATORS)
class TestLabelsAreMatchedByCanonicalName:
    """Every labeled mutator accepts any spelling of one of the node's labels, and stores its own.

    A purely protocol-typed consumer can name only the protocol module's sentinels
    (`cstp.<Class>Label.<X>`); they type-check into every mutator, so rejecting them would leave a
    pyright-clean call that always raises.  Labels carry no backend-specific storage — their
    identity is the canonical name — so a matching spelling resolves to the mutating node's own
    member and that is what lands in `children`.  The tree's invariant is unchanged: a Python tree
    holds concrete enum members, a Rust tree holds native label objects.
    """

    @staticmethod
    def _stored_label(node):
        (label, _child) = node.child()
        return label

    def test_own_label_member(self, backend: str, mutator: str) -> None:
        mod = _mod(backend)
        node = mod.Identifier()
        _mutate_with_label(node, mutator, backend, mod.Identifier.Label.NAME)
        assert self._stored_label(node) == mod.Identifier.Label.NAME

    def test_none_label(self, backend: str, mutator: str) -> None:
        node = _mod(backend).Identifier()
        _mutate_with_label(node, mutator, backend, None)
        assert self._stored_label(node) is None

    def test_protocol_sentinel_is_normalized(self, backend: str, mutator: str) -> None:
        """The one label object a protocol-typed consumer holds is accepted, not stored."""
        mod = _mod(backend)
        node = mod.Identifier()
        _mutate_with_label(node, mutator, backend, py_protocol.IdentifierLabel.NAME)
        stored = self._stored_label(node)
        assert isinstance(stored, mod.Identifier.Label), type(stored)
        assert not isinstance(stored, py_protocol._ProtocolLabelMember)
        assert stored == mod.Identifier.Label.NAME

    def test_other_backends_member_is_normalized(self, backend: str, mutator: str) -> None:
        """Same rule, no special case: canonical-name equality is what admits it."""
        mod = _mod(backend)
        other = rust_cst if backend == "py" else py_cst
        foreign_label = other.Identifier.Label.NAME
        assert foreign_label == mod.Identifier.Label.NAME, "the two labels must compare equal"
        node = mod.Identifier()
        _mutate_with_label(node, mutator, backend, foreign_label)
        stored = self._stored_label(node)
        assert isinstance(stored, mod.Identifier.Label), type(stored)
        assert not isinstance(stored, other.Identifier.Label)

    def test_a_spoofed_canonical_name_is_normalized(self, backend: str, mutator: str) -> None:
        """Accepted deliberately: the stored value is still the backend's own member."""
        mod = _mod(backend)
        node = mod.Identifier()
        _mutate_with_label(node, mutator, backend, _SpoofedLabel())
        stored = self._stored_label(node)
        assert isinstance(stored, mod.Identifier.Label), type(stored)
        assert stored == mod.Identifier.Label.NAME

    def test_cross_class_sentinel_is_refused(self, backend: str, mutator: str) -> None:
        """`ItemsLabel.ITEM` names no `Identifier` label, so the mapping is class-scoped."""
        node = _mod(backend).Identifier()
        with pytest.raises(
            TypeError,
            match=r"Identifier\.\w+: label argument is not a Identifier_Label; got _ProtocolLabelMember",
        ):
            _mutate_with_label(node, mutator, backend, py_protocol.ItemsLabel.ITEM)

    def test_junk_label_is_refused(self, backend: str, mutator: str) -> None:
        node = _mod(backend).Identifier()
        with pytest.raises(TypeError, match=r"Identifier\.\w+: label argument is not a Identifier_Label; got str"):
            _mutate_with_label(node, mutator, backend, "NAME")

    def test_a_raising_canonical_name_propagates(self, backend: str, mutator: str) -> None:
        """Only a *missing* attribute means "not a label"; anything else is the caller's error.

        Reporting a broken descriptor as `TypeError: ... is not a Identifier_Label` hides the one
        useful signal, and would hide it on one backend only if the two resolved the attribute
        differently.
        """
        node = _mod(backend).Identifier()
        with pytest.raises(_CanonicalNameError):
            _mutate_with_label(node, mutator, backend, _RaisingLabel())

    @pytest.mark.parametrize("label_factory", [_UnhashableCanonicalName, _NonStringCanonicalName])
    def test_a_non_string_canonical_name_is_not_a_label(self, backend: str, mutator: str, label_factory) -> None:
        """Only a string canonical name can name a label, and it must fail the same way on both.

        The Python backend looks the name up in a dict, the Rust backend extracts it as a
        `String`; without a string guard on the Python side an unhashable value would surface as
        `unhashable type: 'list'` there and as the pinned `TypeError` on Rust.
        """
        node = _mod(backend).Identifier()
        with pytest.raises(TypeError, match=r"Identifier\.\w+: label argument is not a Identifier_Label"):
            _mutate_with_label(node, mutator, backend, label_factory())
        assert len(node.children) == (1 if mutator == "replace_at" else 0)


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
@pytest.mark.parametrize("member", ["ITEM", "NO_WS", "WS_ALLOWED"])
class TestMultiLabelCanonicalNormalization:
    """Canonical-name resolution pairs each name with *its own* member, not the first one.

    `Identifier` has a single label, so every one-label test passes just as well against a
    generator that collapsed the whole mapping onto the first member.  `Items` has four, and a
    mispairing there would silently relabel children — surfacing far from the mutator, in a
    `children_<label>()` bucket or in `astrt.bucket_children`.
    """

    def test_sentinel_resolves_to_its_own_member(self, backend: str, member: str) -> None:
        mod = _mod(backend)
        node = mod.Items()
        expected = getattr(mod.Items.Label, member)
        node.append(_span(backend, 0, 1), getattr(py_protocol.ItemsLabel, member))
        (stored, _child) = node.child()
        assert isinstance(stored, mod.Items.Label), type(stored)
        assert stored == expected
        if member != "ITEM":
            assert stored != mod.Items.Label.ITEM

    def test_the_other_backends_member_resolves_to_its_own_member(self, backend: str, member: str) -> None:
        mod = _mod(backend)
        other = rust_cst if backend == "py" else py_cst
        node = mod.Items()
        node.append(_span(backend, 0, 1), getattr(other.Items.Label, member))
        (stored, _child) = node.child()
        assert isinstance(stored, mod.Items.Label), type(stored)
        assert stored == getattr(mod.Items.Label, member)
        if member != "ITEM":
            assert stored != mod.Items.Label.ITEM


def test_canonical_name_resolution_is_not_a_public_label_api() -> None:
    """The Rust label enums resolve canonical names internally; exposing it would be a second API.

    The Python backend has no such method, so a visible one would be a cross-backend divergence on
    generated public API.
    """
    assert not hasattr(rust_cst.Identifier.Label, "from_canonical_name")
    assert not hasattr(rust_cst.Items.Label, "from_canonical_name")


# ---------------------------------------------------------------------------
# Foreign children accepted by the type signature but rejected at runtime
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestForeignChildrenAreRejected:
    """Children the widened mutator signatures statically accept must still be refused.

    `insert` / `replace_at` take the protocol node union, so another backend's node type-checks
    into them.  The isinstance guards are what stop it reaching `children`, and nothing else does:
    without these cases a later "the annotations already constrain the input" simplification of
    `_check_child_type_for_mutators` would store a foreign value silently and surface it far away
    — in the unparser, in `astrt.bucket_children`, or in a `child()` tuple unpack.
    """

    def test_other_backends_child_on_insert(self, backend: str) -> None:
        """A node from the other backend is not an accepted child type."""
        other = rust_cst if backend == "py" else py_cst
        node = _mod(backend).Items()
        with pytest.raises(TypeError, match="unsupported child type"):
            node.insert(0, other.Item())

    def test_other_backends_child_on_replace_at(self, backend: str) -> None:
        other = rust_cst if backend == "py" else py_cst
        node = _mod(backend).Items()
        node.append_item(_span(backend, 0, 1))
        with pytest.raises(TypeError, match="unsupported child type"):
            node.replace_at(0, other.Item())


# ---------------------------------------------------------------------------
# Child validation on the append/extend family
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestAppendFamilyChildValidation:
    """append / extend / extend_children / per-label mutators reject a child they cannot store.

    The mutator signatures take the protocol node union, so a foreign-backend node and outright
    junk both type-check into them.  Storing either corrupts the tree and surfaces far from the
    call — in the unparser, in `astrt.bucket_children`, or in a `child()` tuple unpack — so every
    mutator validates, on both backends, with the same message template as insert/replace_at.
    """

    def test_append_rejects_junk(self, backend: str) -> None:
        node = _mod(backend).Items()
        with pytest.raises(TypeError, match=r"Items: unsupported child type builtins\.str"):
            node.append("not_a_span")  # type: ignore[arg-type]
        assert len(node.children) == 0

    def test_append_rejects_foreign_backend_child(self, backend: str) -> None:
        other = rust_cst if backend == "py" else py_cst
        node = _mod(backend).Items()
        with pytest.raises(TypeError, match="unsupported child type"):
            node.append(other.Item())
        assert len(node.children) == 0

    def test_rejected_child_message_names_the_module(self, backend: str) -> None:
        """The rejected type is qualified: both backends export node classes under the same names.

        A bare ``__name__`` renders the most likely trip — mixing backends — as
        ``Items: unsupported child type Item``, which tells the consumer nothing.  Both backends
        spell it ``module.qualname``, so the two agree on any given object.
        """
        other = rust_cst if backend == "py" else py_cst
        foreign = other.Item()
        expected = f"{type(foreign).__module__}.{type(foreign).__qualname__}"
        node = _mod(backend).Items()
        with pytest.raises(TypeError) as exc_info:
            node.append(foreign)
        assert str(exc_info.value) == f"Items: unsupported child type {expected}"

    def test_per_label_append_rejects_foreign_backend_child(self, backend: str) -> None:
        other = rust_cst if backend == "py" else py_cst
        node = _mod(backend).Items()
        with pytest.raises(TypeError, match="unsupported child type"):
            node.append_item(other.Item())
        assert len(node.children) == 0

    def test_per_label_append_stores_an_off_type_known_child(self, backend: str) -> None:
        """TODO(cst-per-label-mutator-narrow-child-check): pins the gap, invert when it closes.

        ``append_item`` validates against the node-wide child union, not the ``item`` label's own
        child annotation, so a ``Trivia`` — a class ``Items`` can hold, but never under ``ITEM`` —
        is accepted, and ``children_item()`` then hands it back under an ``Item`` annotation.  The
        assertions are on the child's identity, not on a count: the defect is the type confusion,
        so an accessor that started filtering by kind must fail here.
        """
        mod = _mod(backend)
        node = mod.Items()
        node.append_item(mod.Trivia())  # type: ignore[arg-type]
        assert len(node.children) == 1
        assert node.children[0][0] == mod.Items.Label.ITEM
        assert node.children[0][1].kind == mod.NodeKind.TRIVIA
        (item,) = node.children_item()
        assert item.kind == mod.NodeKind.TRIVIA

    def test_extend_rejects_junk(self, backend: str) -> None:
        node = _mod(backend).Items()
        with pytest.raises(TypeError, match=r"Items: unsupported child type builtins\.str"):
            node.extend(["not_a_span"])  # type: ignore[list-item]
        assert len(node.children) == 0

    def test_extend_is_atomic_on_a_mid_sequence_failure(self, backend: str) -> None:
        """A rejected element leaves the node exactly as it was: no partial extend."""
        mod = _mod(backend)
        node = mod.Items()
        node.append_item(_span(backend, 0, 1))
        good = _span(backend, 1, 2)
        with pytest.raises(TypeError, match="unsupported child type"):
            node.extend([good, "not_a_span"], mod.Items.Label.ITEM)  # type: ignore[list-item]
        assert len(node.children) == 1
        assert _span_eq(node.children[0][1], _span(backend, 0, 1))

    def test_per_label_extend_is_atomic_on_a_mid_sequence_failure(self, backend: str) -> None:
        node = _mod(backend).Items()
        good = _span(backend, 1, 2)
        with pytest.raises(TypeError, match="unsupported child type"):
            node.extend_item([good, "not_a_span"])  # type: ignore[list-item]
        assert len(node.children) == 0

    def test_extend_children_rejects_foreign_backend_other(self, backend: str) -> None:
        """The rejection message is backend-specific here, so only Python's is asserted.

        Python raises the ``unsupported child type`` template from its own isinstance guard — the
        only diagnostic a consumer gets for an ``extend_children`` mix-up, so its class prefix and
        module-qualified type name are pinned.  Rust rejects at PyO3 signature extraction
        (``other: &PyItems``) and so carries PyO3's own argument-conversion text, which moves with
        PyO3 releases; there the guarantee is the exception type and the unmutated node.
        """
        other = rust_cst if backend == "py" else py_cst
        node = _mod(backend).Items()
        donor = other.Items()
        donor.append_item(_span("py" if backend == "rust" else "rust", 0, 1))
        with pytest.raises(TypeError) as exc_info:
            node.extend_children(donor)
        if backend == "py":
            expected = f"{type(donor).__module__}.{type(donor).__qualname__}"
            assert str(exc_info.value) == f"Items: unsupported child type {expected}"
        assert len(node.children) == 0

    def test_extend_children_rejects_a_different_node_class(self, backend: str) -> None:
        """Backend-specific message here too — see the foreign-backend case above."""
        mod = _mod(backend)
        node = mod.Items()
        donor = mod.Identifier()
        with pytest.raises(TypeError) as exc_info:
            node.extend_children(donor)  # type: ignore[arg-type]
        if backend == "py":
            expected = f"{type(donor).__module__}.{type(donor).__qualname__}"
            assert str(exc_info.value) == f"Items: unsupported child type {expected}"
        assert len(node.children) == 0

    def test_extend_children_accepts_the_same_class(self, backend: str) -> None:
        mod = _mod(backend)
        node = mod.Items()
        donor = mod.Items()
        donor.append_item(_span(backend, 0, 1))
        node.extend_children(donor)
        assert len(node.children) == 1
        assert node.children[0][0] == mod.Items.Label.ITEM


class TestExtendLengthHintIsNotTrusted:
    """A caller-supplied ``__len__`` must not size the Rust backend's staging vector.

    ``extend`` / ``extend_<label>`` pre-size a staging vec from the iterable's length hint.  The
    hint comes from arbitrary Python code and need not match what the iterator yields; an
    oversized reservation is not a catchable error in Rust — the allocation-failure path aborts the
    process, taking the interpreter with it.  Run out-of-process: a regression here kills the
    session rather than failing a test.
    """

    _SCRIPT = """\
        import sys

        sys.path[:] = {path!r}

        import fegen_rust_cst.cst as cst
        from fltk._native import Span


        class LyingLength:
            def __len__(self):
                return 2**40

            def __iter__(self):
                return iter([Span(0, 1)])


        node = cst.Identifier()
        node.extend_name(LyingLength())
        node.extend(LyingLength(), cst.Identifier.Label.NAME)
        assert len(node.children) == 2, node.children
        """

    def _run(self) -> subprocess.CompletedProcess[str]:
        script = textwrap.dedent(self._SCRIPT).format(path=list(sys.path))
        return subprocess.run(  # noqa: S603
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=300, check=False
        )

    def test_a_huge_length_hint_extends_normally(self) -> None:
        proc = self._run()
        assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"


# ---------------------------------------------------------------------------
# Cross-backend message parity (exact equality)
# ---------------------------------------------------------------------------


class TestMessageParity:
    """Assert that Python and Rust backends produce identical error messages for the same operation."""

    def _try_and_capture(self, exc_type, fn) -> str:
        with pytest.raises(exc_type) as exc_info:
            fn()
        return str(exc_info.value)

    def test_remove_at_empty_message_parity(self) -> None:
        py_node = py_cst.Identifier()
        emb_node = rust_cst.Identifier()
        py_msg = self._try_and_capture(IndexError, lambda: py_node.remove_at(0))
        emb_msg = self._try_and_capture(IndexError, lambda: emb_node.remove_at(0))
        assert py_msg == emb_msg

    def test_remove_at_oob_message_parity(self) -> None:
        py_node = py_cst.Identifier()
        emb_node = rust_cst.Identifier()
        py_node.append_name(terminalsrc.Span(0, 1))
        emb_node.append_name(NativeSpan(0, 1))
        py_msg = self._try_and_capture(IndexError, lambda: py_node.remove_at(5))
        emb_msg = self._try_and_capture(IndexError, lambda: emb_node.remove_at(5))
        assert py_msg == emb_msg

    def test_replace_at_oob_message_parity(self) -> None:
        py_node = py_cst.Identifier()
        emb_node = rust_cst.Identifier()
        py_node.append_name(terminalsrc.Span(0, 1))
        emb_node.append_name(NativeSpan(0, 1))
        py_msg = self._try_and_capture(IndexError, lambda: py_node.replace_at(5, terminalsrc.Span(1, 2)))
        emb_msg = self._try_and_capture(IndexError, lambda: emb_node.replace_at(5, NativeSpan(1, 2)))
        assert py_msg == emb_msg

    def test_bad_label_insert_message_parity(self) -> None:
        py_node = py_cst.Identifier()
        emb_node = rust_cst.Identifier()
        s_py = terminalsrc.Span(0, 1)
        s_emb = NativeSpan(0, 1)
        py_msg = self._try_and_capture(TypeError, lambda: py_node.insert(0, s_py, label="bad"))  # type: ignore
        emb_msg = self._try_and_capture(TypeError, lambda: emb_node.insert(0, s_emb, label="bad"))  # type: ignore
        assert py_msg == emb_msg

    def test_unhashable_canonical_name_message_parity(self) -> None:
        """A label whose canonical name is unhashable is diagnosed identically on both backends.

        The Python backend resolves through a dict lookup and the Rust backend through a `String`
        extraction; only a string guard on the Python side keeps the two texts equal here.
        """
        py_node = py_cst.Identifier()
        emb_node = rust_cst.Identifier()
        py_msg = self._try_and_capture(
            TypeError, lambda: py_node.append(terminalsrc.Span(0, 1), _UnhashableCanonicalName())
        )  # type: ignore
        emb_msg = self._try_and_capture(
            TypeError, lambda: emb_node.append(NativeSpan(0, 1), _UnhashableCanonicalName())
        )  # type: ignore
        assert py_msg == emb_msg

    def test_bad_child_type_insert_message_parity(self) -> None:
        py_node = py_cst.Items()
        emb_node = rust_cst.Items()
        py_msg = self._try_and_capture(TypeError, lambda: py_node.insert(0, "not_a_span"))  # type: ignore
        emb_msg = self._try_and_capture(TypeError, lambda: emb_node.insert(0, "not_a_span"))  # type: ignore
        assert py_msg == emb_msg

    def test_bad_child_type_append_message_parity(self) -> None:
        """The same object rejected by both backends' `append` yields the same message text.

        Each backend computing its own expectation would not catch a divergence; the guarantee is
        that a consumer matching on the message gets the same string whichever backend it holds.
        `"not_a_span"` is `builtins.str` on both.
        """
        py_node = py_cst.Items()
        emb_node = rust_cst.Items()
        py_msg = self._try_and_capture(TypeError, lambda: py_node.append("not_a_span"))  # type: ignore
        emb_msg = self._try_and_capture(TypeError, lambda: emb_node.append("not_a_span"))  # type: ignore
        assert py_msg == emb_msg

    def test_bad_child_type_extend_message_parity(self) -> None:
        py_node = py_cst.Items()
        emb_node = rust_cst.Items()
        py_msg = self._try_and_capture(TypeError, lambda: py_node.extend(["not_a_span"]))  # type: ignore
        emb_msg = self._try_and_capture(TypeError, lambda: emb_node.extend(["not_a_span"]))  # type: ignore
        assert py_msg == emb_msg

    def test_bad_child_type_per_label_append_message_parity(self) -> None:
        py_node = py_cst.Items()
        emb_node = rust_cst.Items()
        py_msg = self._try_and_capture(TypeError, lambda: py_node.append_item("not_a_span"))  # type: ignore
        emb_msg = self._try_and_capture(TypeError, lambda: emb_node.append_item("not_a_span"))  # type: ignore
        assert py_msg == emb_msg

    def test_bad_child_type_per_label_extend_message_parity(self) -> None:
        py_node = py_cst.Items()
        emb_node = rust_cst.Items()
        py_msg = self._try_and_capture(TypeError, lambda: py_node.extend_item(["not_a_span"]))  # type: ignore
        emb_msg = self._try_and_capture(TypeError, lambda: emb_node.extend_item(["not_a_span"]))  # type: ignore
        assert py_msg == emb_msg

    def test_remove_at_large_positive_message_parity(self) -> None:
        big = 10**25
        py_node = py_cst.Identifier()
        emb_node = rust_cst.Identifier()
        py_node.append_name(terminalsrc.Span(0, 1))
        emb_node.append_name(NativeSpan(0, 1))
        py_msg = self._try_and_capture(IndexError, lambda: py_node.remove_at(big))
        emb_msg = self._try_and_capture(IndexError, lambda: emb_node.remove_at(big))
        assert py_msg == emb_msg

    def test_remove_at_large_negative_message_parity(self) -> None:
        big = -(10**25)
        py_node = py_cst.Identifier()
        emb_node = rust_cst.Identifier()
        py_node.append_name(terminalsrc.Span(0, 1))
        emb_node.append_name(NativeSpan(0, 1))
        py_msg = self._try_and_capture(IndexError, lambda: py_node.remove_at(big))
        emb_msg = self._try_and_capture(IndexError, lambda: emb_node.remove_at(big))
        assert py_msg == emb_msg


# ---------------------------------------------------------------------------
# Mixed operation sequences — identical trees both backends
# ---------------------------------------------------------------------------


class TestMixedOperationsParity:
    """Interleaved insert/remove/replace/append produce identical trees on both backends."""

    def _build_py(self) -> py_cst.Identifier:
        node = py_cst.Identifier()
        s = terminalsrc.Span
        for i in range(5):
            node.append_name(s(i * 10, i * 10 + 5))
        node.insert(0, s(100, 101), py_cst.Identifier.Label.NAME)  # prepend
        node.remove_at(2)  # remove index 2
        node.replace_at(1, s(200, 201), py_cst.Identifier.Label.NAME)
        node.insert(-1, s(300, 301), py_cst.Identifier.Label.NAME)
        return node

    def _build_emb(self) -> rust_cst.Identifier:
        node = rust_cst.Identifier()
        s = NativeSpan
        for i in range(5):
            node.append_name(s(i * 10, i * 10 + 5))
        node.insert(0, s(100, 101), rust_cst.Identifier.Label.NAME)  # prepend
        node.remove_at(2)  # remove index 2
        node.replace_at(1, s(200, 201), rust_cst.Identifier.Label.NAME)
        node.insert(-1, s(300, 301), rust_cst.Identifier.Label.NAME)
        return node

    def test_mixed_operations_identical_structure(self) -> None:
        py_node = self._build_py()
        emb_node = self._build_emb()
        assert _children_equal(py_node.children, emb_node.children)

    def test_clear_after_operations(self) -> None:
        py_node = self._build_py()
        emb_node = self._build_emb()
        py_node.clear()
        emb_node.clear()
        assert len(py_node.children) == 0
        assert len(emb_node.children) == 0

    def test_append_after_clear_parity(self) -> None:
        py_node = self._build_py()
        emb_node = self._build_emb()
        py_node.clear()
        emb_node.clear()
        s_py = terminalsrc.Span(99, 100)
        s_emb = NativeSpan(99, 100)
        py_node.append_name(s_py)
        emb_node.append_name(s_emb)
        assert _children_equal(py_node.children, emb_node.children)


# ---------------------------------------------------------------------------
# Span hand-in per-backend (excluded from exact-parity matrix; span types differ across backends)
# ---------------------------------------------------------------------------


class TestSpanHandInPerBackend:
    """Python backend accepts both span types; Rust backend accepts only native spans."""

    def test_python_accepts_terminalsrc_span(self) -> None:
        """Python backend accepts terminalsrc.Span in insert."""
        node = py_cst.Identifier()
        node.insert(0, terminalsrc.Span(0, 1), py_cst.Identifier.Label.NAME)
        assert len(node.children) == 1

    def test_python_accepts_native_span_when_loaded(self) -> None:
        """Python backend accepts native Span when fltk._native is already loaded."""
        # fltk._native is already loaded (we imported it for rust_cst)
        assert "fltk._native" in sys.modules
        node = py_cst.Identifier()
        node.insert(0, NativeSpan(0, 1), py_cst.Identifier.Label.NAME)
        assert len(node.children) == 1

    def test_python_append_family_accepts_a_native_span(self) -> None:
        """The append family resolves a native Span too, not only `insert`.

        The append family routes children through `_check_child_type_for_mutators`, whose miss
        branch resolves a native Span; without a case here, dropping the lazy `fltk._native`
        probe would break cross-backend span hand-in with the suite green.
        """
        assert "fltk._native" in sys.modules
        node = py_cst.Identifier()
        node.append(NativeSpan(0, 1), py_cst.Identifier.Label.NAME)
        node.append_name(NativeSpan(1, 2))
        node.extend([NativeSpan(2, 3)], py_cst.Identifier.Label.NAME)
        node.extend_name([NativeSpan(3, 4)])
        assert [(c.start, c.end) for _label, c in node.children] == [(0, 1), (1, 2), (2, 3), (3, 4)]

    def test_python_append_family_accepts_a_terminalsrc_span(self) -> None:
        node = py_cst.Identifier()
        node.append(terminalsrc.Span(0, 1), py_cst.Identifier.Label.NAME)
        node.append_name(terminalsrc.Span(1, 2))
        node.extend([terminalsrc.Span(2, 3)], py_cst.Identifier.Label.NAME)
        node.extend_name([terminalsrc.Span(3, 4)])
        assert [(c.start, c.end) for _label, c in node.children] == [(0, 1), (1, 2), (2, 3), (3, 4)]

    def test_rust_accepts_native_span(self) -> None:
        """Rust backend accepts native Span in insert."""
        node = rust_cst.Identifier()
        node.insert(0, NativeSpan(0, 1), rust_cst.Identifier.Label.NAME)
        assert len(node.children) == 1

    def test_rust_rejects_terminalsrc_span(self) -> None:
        """Rust backend rejects terminalsrc.Span with unsupported child type TypeError."""
        node = rust_cst.Identifier()
        with pytest.raises(TypeError, match="unsupported child type"):
            node.insert(0, terminalsrc.Span(0, 1), rust_cst.Identifier.Label.NAME)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Multi-label node (Items) — label-specific operations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestItemsMultiLabel:
    """insert/remove_at/replace_at with multiple label types."""

    def test_insert_different_labels(self, backend: str) -> None:
        """insert with different labels stores each label correctly."""
        mod = _mod(backend)
        node = mod.Items()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        node.insert(0, s0, mod.Items.Label.ITEM)
        node.insert(1, s1, mod.Items.Label.NO_WS)
        ch = node.children
        assert len(ch) == 2
        assert ch[0][0] == mod.Items.Label.ITEM
        assert ch[1][0] == mod.Items.Label.NO_WS

    def test_remove_at_returns_correct_label(self, backend: str) -> None:
        """remove_at returns the exact label that was stored."""
        mod = _mod(backend)
        node = mod.Items()
        s0 = _span(backend, 0, 1)
        s1 = _span(backend, 1, 2)
        node.append_item(s0)
        node.append_no_ws(s1)
        lbl, child = node.remove_at(1)
        assert lbl == mod.Items.Label.NO_WS
        assert _span_eq(child, s1)

    def test_replace_at_changes_label(self, backend: str) -> None:
        """replace_at with a different label updates the label."""
        mod = _mod(backend)
        node = mod.Items()
        s_old = _span(backend, 0, 1)
        s_new = _span(backend, 5, 6)
        node.append_item(s_old)
        node.replace_at(0, s_new, mod.Items.Label.WS_ALLOWED)
        ch = node.children
        assert ch[0][0] == mod.Items.Label.WS_ALLOWED
        assert _span_eq(ch[0][1], s_new)


# ---------------------------------------------------------------------------
# Mixed operations with node-typed children
# ---------------------------------------------------------------------------


class TestMixedOpsNodeChildren:
    """Interleaved mutations on a node with node-typed children (not just spans).

    Uses Alternatives, whose children include Items sub-nodes.
    Both backends must produce identical child-kind sequences.
    """

    def _assert_items_parity(self, py_node, emb_node) -> None:
        """Assert that py_node and emb_node have the same number of children with the same labels.

        Node-typed children are compared by label only (identity is backend-specific).
        """
        py_ch = py_node.children
        emb_ch = emb_node.children
        assert len(py_ch) == len(emb_ch), f"length mismatch: {len(py_ch)} vs {len(emb_ch)}"
        for (pl, _pc), (rl, _rc) in zip(py_ch, emb_ch, strict=False):
            assert pl == rl, f"label mismatch: {pl} vs {rl}"

    def test_insert_node_child_parity(self) -> None:
        """insert with a node-typed child produces identical label sequences on both backends."""
        py_alt = py_cst.Alternatives()
        emb_alt = rust_cst.Alternatives()
        # Create Items children
        py_items_a = py_cst.Items()
        py_items_b = py_cst.Items()
        emb_items_a = rust_cst.Items()
        emb_items_b = rust_cst.Items()
        # Append then insert at head
        py_alt.append_items(py_items_a)
        py_alt.insert(0, py_items_b, py_cst.Alternatives.Label.ITEMS)
        emb_alt.append_items(emb_items_a)
        emb_alt.insert(0, emb_items_b, rust_cst.Alternatives.Label.ITEMS)
        assert len(py_alt.children) == 2
        self._assert_items_parity(py_alt, emb_alt)

    def test_remove_node_child_parity(self) -> None:
        """remove_at on a node-typed child produces identical residual label sequences."""
        py_alt = py_cst.Alternatives()
        emb_alt = rust_cst.Alternatives()
        for _i in range(3):
            py_alt.append_items(py_cst.Items())
            emb_alt.append_items(rust_cst.Items())
        py_alt.remove_at(1)
        emb_alt.remove_at(1)
        assert len(py_alt.children) == 2
        self._assert_items_parity(py_alt, emb_alt)

    def test_replace_node_child_parity(self) -> None:
        """replace_at on a node-typed child produces identical label sequences."""
        py_alt = py_cst.Alternatives()
        emb_alt = rust_cst.Alternatives()
        for _i in range(2):
            py_alt.append_items(py_cst.Items())
            emb_alt.append_items(rust_cst.Items())
        py_alt.replace_at(0, py_cst.Items(), py_cst.Alternatives.Label.ITEMS)
        emb_alt.replace_at(0, rust_cst.Items(), rust_cst.Alternatives.Label.ITEMS)
        assert len(py_alt.children) == 2
        self._assert_items_parity(py_alt, emb_alt)

    def test_clear_node_children_parity(self) -> None:
        """clear on a node with node-typed children empties both backends identically."""
        py_alt = py_cst.Alternatives()
        emb_alt = rust_cst.Alternatives()
        for _i in range(3):
            py_alt.append_items(py_cst.Items())
            emb_alt.append_items(rust_cst.Items())
        py_alt.clear()
        emb_alt.clear()
        assert len(py_alt.children) == 0
        assert len(emb_alt.children) == 0


# ---------------------------------------------------------------------------
# Label-free node — non-None label raises TypeError
# ---------------------------------------------------------------------------


class TestLabelFreeNodeErrors:
    """Runtime behavior of mutators on label-free nodes.

    Uses a dynamically-compiled label-free CST class (Python backend only;
    the fegen CST has no label-free nodes to test the Rust backend against).
    """

    @pytest.fixture(scope="class")
    def foo_cls(self):
        """Compile and return the Foo class from the zero-label grammar."""
        gen = _make_generator(_make_zero_label_grammar())
        model = gen.rule_models["foo"]
        stmts = gen.py_class_for_model("Foo", model, "foo")
        # Build a minimal module to exec the generated class in
        module_stmts = [
            ast.parse("import dataclasses, enum, operator, typing").body[0],
            ast.parse("import fltk.fegen.pyrt.terminalsrc, fltk.fegen.pyrt.span").body[0],
            ast.parse("import fltk._native").body[0],
            # NodeKind enum stub (minimal — just needs FOO)
            ast.parse("class NodeKind(enum.Enum): FOO = enum.auto()").body[0],
            # _get_native_span_type stub
            ast.parse(
                "def _get_native_span_type():\n"
                "    import sys\n"
                "    m = sys.modules.get('fltk._native')\n"
                "    return getattr(m, 'Span', None) if m else None"
            ).body[0],
            *stmts,
        ]
        mod_ast = ast.Module(body=module_stmts, type_ignores=[])
        ast.fix_missing_locations(mod_ast)
        code = compile(mod_ast, "<foo_cst>", "exec")
        ns: dict = {}
        exec(code, ns)  # noqa: S102
        return ns["Foo"]

    def test_insert_non_none_label_on_label_free_node_raises_type_error(self, foo_cls) -> None:
        """insert with a non-None label on a label-free node raises TypeError."""
        node = foo_cls()
        with pytest.raises(TypeError, match=r"Foo\.insert: no labels defined for this node; got str label"):
            node.insert(0, terminalsrc.Span(0, 1), label="bad")  # type: ignore[call-arg]

    def test_replace_at_non_none_label_on_label_free_node_raises_type_error(self, foo_cls) -> None:
        """replace_at with a non-None label on a label-free node raises TypeError."""
        node = foo_cls()
        node.append(terminalsrc.Span(0, 1))
        with pytest.raises(TypeError, match=r"Foo\.replace_at: no labels defined for this node; got str label"):
            node.replace_at(0, terminalsrc.Span(1, 2), label="bad")  # type: ignore[call-arg]

    def test_append_non_none_label_on_label_free_node_raises_type_error(self, foo_cls) -> None:
        """append checks the label too, and a label-free node has nothing to normalize against."""
        node = foo_cls()
        with pytest.raises(TypeError, match=r"Foo\.append: no labels defined for this node; got str label"):
            node.append(terminalsrc.Span(0, 1), label="bad")  # type: ignore[call-arg]
        assert len(node.children) == 0

    def test_extend_non_none_label_on_label_free_node_raises_type_error(self, foo_cls) -> None:
        """The label is checked before any child is read, so the node is left unmutated."""
        node = foo_cls()
        with pytest.raises(TypeError, match=r"Foo\.extend: no labels defined for this node; got str label"):
            node.extend([terminalsrc.Span(0, 1)], "bad")  # type: ignore[call-arg]
        assert len(node.children) == 0

    def test_a_sentinel_is_refused_by_a_label_free_node(self, foo_cls) -> None:
        """A protocol sentinel names a label of some other class; this node declares none."""
        node = foo_cls()
        with pytest.raises(
            TypeError, match=r"Foo\.append: no labels defined for this node; got _ProtocolLabelMember label"
        ):
            node.append(terminalsrc.Span(0, 1), label=py_protocol.IdentifierLabel.NAME)  # type: ignore[call-arg]
