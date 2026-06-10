# Stub package for fltk._native (compiled PyO3 extension fltk/_native.abi3.so).
#
# Layout note: this directory holds only .pyi files (no __init__.py).
# CPython's import machinery selects the regular extension module _native.abi3.so
# over a namespace-package portion; the stub directory does NOT shadow the compiled
# module at import time. Adding an __init__.py here WOULD shadow the extension and
# break every runtime import of fltk._native. Do not add __init__.py.
#
# PoC grammar classes (Identifier, Items, Trivia and their Label enums) registered
# by cst_generated::register_classes (src/lib.rs:29) are intentionally omitted.
# They have no committed protocol module (required by the OQ-0(a) .pyi emitter) and
# no static in-repo references, so omission costs nothing statically.
# See TODO(gencode-poc-fltkg): the PoC grammar has no .fltkg source file; the classes
# must be hand-maintained here once that TODO is resolved.
from __future__ import annotations

import typing

import fltk.fegen.pyrt.terminalsrc

class SourceText:
    """Opaque handle to a shared source string.

    Constructing a SourceText from Python copies the string once (Python str → UTF-8).
    All Span objects created from the same SourceText share the underlying allocation.
    """

    def __init__(self, text: str) -> None: ...

class Span:
    """Half-open Unicode-codepoint index range [start, end) into a shared UTF-8 source string.

    Equality and hashing use only (start, end); the source reference is excluded.
    Frozen: attribute assignment raises AttributeError.
    """

    def __init__(self, start: int, end: int) -> None: ...
    @classmethod
    def with_source(cls, start: int, end: int, source: SourceText) -> Span: ...
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
