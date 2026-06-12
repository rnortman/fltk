# Stub package for fltk._native (compiled PyO3 extension fltk/_native.abi3.so).
#
# Layout note: this directory holds only .pyi files (no __init__.py).
# CPython's import machinery selects the regular extension module _native.abi3.so
# over a namespace-package portion; the stub directory does NOT shadow the compiled
# module at import time. Adding an __init__.py here WOULD shadow the extension and
# break every runtime import of fltk._native. Do not add __init__.py.
#
# PoC grammar classes (Identifier, Items, Trivia and their Label enums) are in the
# fltk._native.poc_cst submodule (src/lib.rs; cst_generated::register_classes). They are
# intentionally omitted from this stub: no committed protocol module (required by the
# OQ-0(a) .pyi emitter) and no static in-repo references. The PoC grammar source is at
# fltk/fegen/test_data/poc_grammar.fltkg; classes would need to be hand-maintained here
# if a protocol module were added for the PoC grammar.
from __future__ import annotations

import typing

import fltk.fegen.pyrt.terminalsrc

class SourceText:
    """Opaque handle to a shared source string.

    Constructing a SourceText from Python copies the string once (Python str → UTF-8).
    All Span objects created from the same SourceText share the underlying allocation.
    """

    _fltk_cst_core_abi: typing.ClassVar[str]

    def __init__(self, text: str) -> None: ...

class Span:
    """Half-open Unicode-codepoint index range [start, end) into a shared UTF-8 source string.

    Equality and hashing use only (start, end); the source reference is excluded.
    Frozen: attribute assignment raises AttributeError.
    """

    def __init__(self, start: int, end: int) -> None: ...
    @classmethod
    def with_source(cls, start: int, end: int, source: SourceText) -> Span: ...
    @classmethod
    def _with_source_unchecked(cls, start: int, end: int, source: object) -> Span:
        """Internal cross-cdylib constructor (generated-code use only).

        Like with_source, but accepts a SourceText registered by another
        fltk-cst-core-linking cdylib. The ABI marker check in extract_source_text
        gates the cast. Passing a forged-marker object is UB. Do not call directly.
        """
        ...
    def text(self) -> str | None: ...
    def text_or_raise(self) -> str: ...
    def has_source(self) -> bool: ...
    def len(self) -> int: ...
    def is_empty(self) -> bool: ...
    def merge(self, other: Span) -> Span: ...
    def intersect(self, other: Span) -> Span: ...
    @property
    def start(self) -> int: ...
    @property
    def end(self) -> int: ...
    @property
    def kind(self) -> typing.Literal[fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN]: ...
    def __repr__(self) -> str: ...
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...

UnknownSpan: Span
