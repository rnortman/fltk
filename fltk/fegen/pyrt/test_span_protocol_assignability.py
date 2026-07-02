"""Pins SpanProtocol assignability (delta D3.1).

After the D3.1 root-fix (``merge``/``intersect`` typed with ``Self``; a ``kind`` discriminant), a
concrete ``terminalsrc.Span`` *value* is statically assignable to a ``SpanProtocol`` slot — the
property every later delta increment relies on (CST/protocol/``.pyi``/unparser span slots become
``SpanProtocol``, and the pure-Python parser feeds them ``terminalsrc.Span``).

The module-level assignments below ARE the pyright assertions: this file lives under ``fltk/``, so
``make check``'s pyright type-checks them. They would error before D3.1 (the pre-fix
``SpanProtocol`` rejects a concrete span: ``merge`` declares ``other: SpanProtocol``, a wider param
than the concrete ``Span``, which is contravariantly incompatible). The runtime tests pin
``isinstance`` for both backends.

Native ``fltk._native.Span`` is statically assigned into a ``SpanProtocol`` slot here (under
``if _rust_available:`` — pyright checks the branch body regardless of the runtime condition). The
structural ``LineColPosProtocol`` makes native spans statically conformant, so this native pin
enforces the "near-drop-in Rust backend" promise via ``make check`` on every future edit.
"""

import dataclasses

import pytest

import fltk._native as _fltk_native
from fltk.fegen.pyrt.span_protocol import LineColPosProtocol, SpanProtocol
from fltk.fegen.pyrt.terminalsrc import Span as PySpan
from fltk.fegen.pyrt.terminalsrc import SpanKind, UnknownSpan

_rust_available = hasattr(_fltk_native, "Span")


# --- pyright-checked assignability (delta D3.1) ----------------------------------------------
# Variable slot: a concrete terminalsrc.Span is assignable to a SpanProtocol-typed name.
_span_slot: SpanProtocol = PySpan(0, 1)

# LineColPosProtocol pin for the Python backend: a concrete terminalsrc.LineColPos result is
# assignable to a LineColPosProtocol slot.
_py_linecol_slot: LineColPosProtocol = PySpan.with_source(0, 1, "x").line_col_or_raise()

if _rust_available:
    # Headline pin: a native span is statically assignable to SpanProtocol.
    _native_span_slot: SpanProtocol = _fltk_native.Span(0, 1)
    # LineColPosProtocol pin for the native backend: native Span.line_col() result is assignable to
    # a LineColPosProtocol | None slot.
    _native_linecol_slot: LineColPosProtocol | None = _fltk_native.Span.with_source(
        0, 1, _fltk_native.SourceText("x")
    ).line_col()


@dataclasses.dataclass
class _HasSpanField:
    # Dataclass field typed SpanProtocol with a concrete terminalsrc UnknownSpan default —
    # exactly the shape the regenerated CST node ``span`` field takes after delta D3.4.
    span: SpanProtocol = UnknownSpan


def _returns_protocol() -> SpanProtocol:
    # Return slot: a concrete terminalsrc.Span satisfies a ``-> SpanProtocol`` return.
    return PySpan.with_source(0, 1, "x")


class TestSpanProtocolAssignability:
    """Runtime exercises of the pyright-checked slots, plus cross-backend isinstance."""

    def test_pyright_checked_slots_construct(self):
        # The module-level assignments above are the static assertions; exercise them at runtime so
        # the test also fails loudly if they ever stop constructing valid spans.
        assert isinstance(_span_slot, SpanProtocol)
        assert isinstance(_HasSpanField().span, SpanProtocol)
        assert isinstance(_returns_protocol(), SpanProtocol)
        assert isinstance(_py_linecol_slot, LineColPosProtocol)
        if _rust_available:
            assert isinstance(_native_span_slot, SpanProtocol)
            assert isinstance(_native_linecol_slot, LineColPosProtocol)

    def test_py_span_isinstance_protocol(self):
        assert isinstance(PySpan(0, 1), SpanProtocol)

    def test_py_linecol_isinstance_protocol(self):
        assert isinstance(PySpan.with_source(0, 1, "x").line_col_or_raise(), LineColPosProtocol)

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_rust_span_isinstance_protocol(self):
        assert isinstance(_fltk_native.Span(0, 1), SpanProtocol)

    @pytest.mark.skipif(not _rust_available, reason="Rust extension not available")
    def test_rust_linecol_isinstance_protocol(self):
        native_linecol = _fltk_native.Span.with_source(0, 1, _fltk_native.SourceText("x")).line_col()
        assert isinstance(native_linecol, LineColPosProtocol)

    def test_kind_discriminant_present(self):
        # The D3.1 ``kind`` discriminant is exposed and matches the shared SpanKind.SPAN value
        # both backends carry (the subject of Shape-2 ``case proto_cst.Span.kind:`` dispatch).
        assert PySpan(0, 1).kind is SpanKind.SPAN
        if _rust_available:
            assert _fltk_native.Span(0, 1).kind == SpanKind.SPAN
