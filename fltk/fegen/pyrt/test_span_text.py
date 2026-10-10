"""Tests for ``terminalsrc.span_text``.

Every case runs on both backends' ``Span``: the Python ``terminalsrc.Span`` and the native
``fltk._native.Span``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from fltk.fegen.pyrt import terminalsrc
from fltk.unparse.pyrt import extract_span_text

native = pytest.importorskip("fltk._native", reason="Rust extension not available")


@dataclass(frozen=True)
class _Backend:
    sourced: Callable[[int, int, str], Any]
    sourceless: Callable[[int, int], Any]


_PYTHON = _Backend(
    sourced=terminalsrc.Span.with_source,
    sourceless=terminalsrc.Span,
)
_NATIVE = _Backend(
    sourced=lambda start, end, text: native.Span.with_source(start, end, native.SourceText(text)),
    sourceless=native.Span,
)

_BACKENDS = pytest.mark.parametrize("backend", [_PYTHON, _NATIVE], ids=["python", "native"])


@_BACKENDS
def test_attached_source_wins_over_a_differing_buffer(backend: _Backend) -> None:
    assert terminalsrc.span_text(backend.sourced(0, 5, "hello"), "world") == "hello"


@_BACKENDS
def test_valid_empty_text_is_not_a_fallback(backend: _Backend) -> None:
    assert terminalsrc.span_text(backend.sourced(2, 2, "abcd"), "zzzz") == ""


@_BACKENDS
def test_non_ascii_offsets_are_codepoints(backend: _Backend) -> None:
    assert terminalsrc.span_text(backend.sourced(1, 2, "héllo"), "xxxxx") == "é"
    assert terminalsrc.span_text(backend.sourceless(1, 2), "héllo") == "é"


@_BACKENDS
def test_inconsistent_source_bearing_span_raises(backend: _Backend) -> None:
    span = backend.sourced(7, 999, "hello")
    with pytest.raises(ValueError, match=r"source-bearing span") as excinfo:
        terminalsrc.span_text(span, "world")
    assert "Span(start=7, end=999)" in str(excinfo.value)


@_BACKENDS
def test_inverted_source_bearing_span_raises(backend: _Backend) -> None:
    with pytest.raises(ValueError, match=r"source-bearing span"):
        terminalsrc.span_text(backend.sourced(3, 1, "hello"), "world")


@_BACKENDS
def test_sourceless_span_slices_the_buffer(backend: _Backend) -> None:
    assert terminalsrc.span_text(backend.sourceless(0, 5), "world") == "world"


@_BACKENDS
def test_sourceless_span_uses_ordinary_slicing(backend: _Backend) -> None:
    assert terminalsrc.span_text(backend.sourceless(-1, -1), "world") == ""


@_BACKENDS
def test_extract_span_text_applies_the_same_policy(backend: _Backend) -> None:
    assert extract_span_text(backend.sourced(0, 5, "hello"), "world") == "hello"
    assert extract_span_text(backend.sourceless(0, 5), "world") == "world"
    with pytest.raises(ValueError, match=r"source-bearing span"):
        extract_span_text(backend.sourced(0, 999, "hello"), "world")


def test_non_span_object_is_rejected() -> None:
    class _OffsetsOnly:
        start = 0
        end = 5

    with pytest.raises(AttributeError):
        terminalsrc.span_text(_OffsetsOnly(), "world")  # type: ignore[arg-type]
