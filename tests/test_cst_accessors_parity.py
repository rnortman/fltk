"""Cross-backend parity tests for the per-label CST read accessors.

Scope is the read side of the quintet — `children_<label>()` and the bare arity accessors.
The mutator surface has its own parity module (`test_cst_mutators_parity.py`).

`children_<label>()` is declared `typing.Iterator[T]` by the protocol module, the Rust stub
and the grammar reference, and both backends return exactly that: a fresh, single-pass
iterator over a snapshot of the matching children taken at call time.  The bare
multiple-arity accessor (`<label>()`) returns a `list` on both backends.

"""

from __future__ import annotations

import pytest

pytest.importorskip("fltk._native", reason="Rust extension not available")
pytest.importorskip("fegen_rust_cst", reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first")

import fegen_rust_cst.cst as rust_cst

from fltk._native import Span as NativeSpan
from fltk.fegen import fltk_cst as py_cst
from fltk.fegen.pyrt import terminalsrc

_BACKENDS = {
    "py": (py_cst, terminalsrc.Span),
    "rust": (rust_cst, NativeSpan),
}
_BACKEND_KEYS = list(_BACKENDS.keys())


def _mod(backend: str):
    return _BACKENDS[backend][0]


def _span(backend: str, start: int, end: int):
    return _BACKENDS[backend][1](start, end)


def _identifier_with_names(backend: str, count: int):
    """An Identifier carrying `count` NAME spans, one per unit position."""
    mod = _mod(backend)
    node = mod.Identifier()
    for i in range(count):
        node.append_name(_span(backend, i, i + 1))
    return node


def _items_with_no_ws(backend: str, count: int):
    """An Items carrying `count` NO_WS spans."""
    mod = _mod(backend)
    node = mod.Items()
    for i in range(count):
        node.append_no_ws(_span(backend, i, i + 1))
    return node


def _bounds(spans) -> list[tuple[int, int]]:
    return [(s.start, s.end) for s in spans]


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestChildrenLabelIsAnIterator:
    """The declared `Iterator[T]` return is the runtime return on both backends."""

    def test_next_works_directly_on_the_returned_object(self, backend: str) -> None:
        node = _identifier_with_names(backend, 3)
        first = next(node.children_name())
        assert (first.start, first.end) == (0, 1)

    def test_the_returned_object_is_its_own_iterator(self, backend: str) -> None:
        """`iter(x) is x` is what distinguishes an iterator from a re-iterable list."""
        got = _identifier_with_names(backend, 2).children_name()
        assert iter(got) is got

    def test_a_second_pass_over_the_same_object_is_empty(self, backend: str) -> None:
        got = _identifier_with_names(backend, 3).children_name()
        assert len(list(got)) == 3
        assert list(got) == []

    def test_two_calls_yield_independent_iterators(self, backend: str) -> None:
        node = _identifier_with_names(backend, 3)
        a = node.children_name()
        b = node.children_name()
        next(a)
        assert _bounds(b) == [(0, 1), (1, 2), (2, 3)]
        assert _bounds(a) == [(1, 2), (2, 3)]

    def test_the_iterator_is_a_snapshot_taken_at_call_time(self, backend: str) -> None:
        node = _identifier_with_names(backend, 2)
        got = node.children_name()
        node.append_name(_span(backend, 9, 10))
        assert _bounds(got) == [(0, 1), (1, 2)]
        assert _bounds(node.children_name()) == [(0, 1), (1, 2), (9, 10)]

    def test_a_clear_after_the_call_does_not_empty_the_iterator(self, backend: str) -> None:
        node = _identifier_with_names(backend, 2)
        got = node.children_name()
        node.clear()
        assert _bounds(got) == [(0, 1), (1, 2)]

    def test_no_matching_children_yields_an_empty_iterator(self, backend: str) -> None:
        mod = _mod(backend)
        node = mod.Identifier()
        got = node.children_name()
        assert iter(got) is got
        assert list(got) == []

    def test_other_labels_are_filtered_out(self, backend: str) -> None:
        """Both a differently-labelled child and an unlabelled one are excluded."""
        mod = _mod(backend)
        node = mod.Items()
        node.append_no_ws(_span(backend, 0, 1))
        node.append_ws_required(_span(backend, 1, 2))
        node.append_no_ws(_span(backend, 2, 3))
        node.append(_span(backend, 3, 4))
        assert _bounds(node.children_no_ws()) == [(0, 1), (2, 3)]
        assert _bounds(node.children_ws_required()) == [(1, 2)]

    def test_node_typed_children_come_back_as_nodes(self, backend: str) -> None:
        mod = _mod(backend)
        node = mod.Items()
        node.append_item(mod.Item(span=_span(backend, 0, 1)))
        node.append_item(mod.Item(span=_span(backend, 1, 2)))
        got = list(node.children_item())
        assert [type(c) for c in got] == [mod.Item, mod.Item]


@pytest.mark.parametrize("backend", _BACKEND_KEYS)
class TestBareAccessorsAreUnchanged:
    """The arity accessors keep their own return shapes; only the quintet member is an iterator."""

    def test_multiple_arity_returns_a_list(self, backend: str) -> None:
        node = _items_with_no_ws(backend, 2)
        got = node.no_ws()
        assert isinstance(got, list)
        assert _bounds(got) == [(0, 1), (1, 2)]

    def test_the_list_is_a_snapshot_too(self, backend: str) -> None:
        node = _items_with_no_ws(backend, 1)
        got = node.no_ws()
        node.append_no_ws(_span(backend, 5, 6))
        assert _bounds(got) == [(0, 1)]
