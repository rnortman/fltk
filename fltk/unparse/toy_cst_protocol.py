# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk._native
    import fltk.fegen.pyrt.span
__all__ = ["CstModule", "Expr", "Factor", "NodeKind", "Number", "Span", "Term", "Trivia"]


class NodeKind(enum.Enum):
    EXPR = enum.auto()
    TERM = enum.auto()
    FACTOR = enum.auto()
    NUMBER = enum.auto()
    TRIVIA = enum.auto()
    _fltk_canonical_name: str

    def __eq__(self, other: object) -> bool:
        if other is self:
            return True
        if type(other) is type(self):
            return self.name == other.name
        cn = getattr(other, "_fltk_canonical_name", None)
        if cn is not None:
            return self._fltk_canonical_name == cn
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._fltk_canonical_name)


NodeKind.EXPR._fltk_canonical_name = "NodeKind.EXPR"
NodeKind.TERM._fltk_canonical_name = "NodeKind.TERM"
NodeKind.FACTOR._fltk_canonical_name = "NodeKind.FACTOR"
NodeKind.NUMBER._fltk_canonical_name = "NodeKind.NUMBER"
NodeKind.TRIVIA._fltk_canonical_name = "NodeKind.TRIVIA"


class _ProtocolLabelMember:
    _fltk_canonical_name: str

    def __init__(self, canonical_name: str) -> None:
        self._fltk_canonical_name = canonical_name

    def __eq__(self, other: object) -> bool:
        if other is self:
            return True
        if type(other) is type(self):
            return self._fltk_canonical_name == other._fltk_canonical_name
        cn = getattr(other, "_fltk_canonical_name", None)
        if cn is not None:
            return self._fltk_canonical_name == cn
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._fltk_canonical_name)

    def __repr__(self) -> str:
        return f"_ProtocolLabelMember({self._fltk_canonical_name!r})"


class Expr(typing.Protocol):
    class Label:
        PLUS: typing.ClassVar[object]
        TERM: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.EXPR] = NodeKind.EXPR
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Term | Trivia | fltk.fegen.pyrt.span.Span]]

    def append(self, child: Term | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Term | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Expr) -> None: ...

    def child(self) -> tuple[Label | None, Term | Trivia | fltk.fegen.pyrt.span.Span]: ...

    def append_plus(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_plus(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_plus(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_plus(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_plus(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_term(self, child: Term) -> None: ...

    def extend_term(self, children: typing.Iterable[Term]) -> None: ...

    def children_term(self) -> typing.Iterator[Term]: ...

    def child_term(self) -> Term: ...

    def maybe_term(self) -> Term | None: ...


Expr.Label.PLUS = _ProtocolLabelMember("Expr.Label.PLUS")
Expr.Label.TERM = _ProtocolLabelMember("Expr.Label.TERM")


class Term(typing.Protocol):
    class Label:
        FACTOR: typing.ClassVar[object]
        MULT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TERM] = NodeKind.TERM
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Factor | Trivia | fltk.fegen.pyrt.span.Span]]

    def append(self, child: Factor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Factor | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Term) -> None: ...

    def child(self) -> tuple[Label | None, Factor | Trivia | fltk.fegen.pyrt.span.Span]: ...

    def append_factor(self, child: Factor) -> None: ...

    def extend_factor(self, children: typing.Iterable[Factor]) -> None: ...

    def children_factor(self) -> typing.Iterator[Factor]: ...

    def child_factor(self) -> Factor: ...

    def maybe_factor(self) -> Factor | None: ...

    def append_mult(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_mult(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_mult(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_mult(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_mult(self) -> fltk.fegen.pyrt.span.Span | None: ...


Term.Label.FACTOR = _ProtocolLabelMember("Term.Label.FACTOR")
Term.Label.MULT = _ProtocolLabelMember("Term.Label.MULT")


class Factor(typing.Protocol):
    class Label:
        EXPR: typing.ClassVar[object]
        NUMBER: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.FACTOR] = NodeKind.FACTOR
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Expr | Number | Trivia]]

    def append(self, child: Expr | Number | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Expr | Number | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: Factor) -> None: ...

    def child(self) -> tuple[Label | None, Expr | Number | Trivia]: ...

    def append_expr(self, child: Expr) -> None: ...

    def extend_expr(self, children: typing.Iterable[Expr]) -> None: ...

    def children_expr(self) -> typing.Iterator[Expr]: ...

    def child_expr(self) -> Expr: ...

    def maybe_expr(self) -> Expr | None: ...

    def append_number(self, child: Number) -> None: ...

    def extend_number(self, children: typing.Iterable[Number]) -> None: ...

    def children_number(self) -> typing.Iterator[Number]: ...

    def child_number(self) -> Number: ...

    def maybe_number(self) -> Number | None: ...


Factor.Label.EXPR = _ProtocolLabelMember("Factor.Label.EXPR")
Factor.Label.NUMBER = _ProtocolLabelMember("Factor.Label.NUMBER")


class Number(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.NUMBER] = NodeKind.NUMBER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Number) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_value(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_value(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span.Span | None: ...


Number.Label.VALUE = _ProtocolLabelMember("Number.Label.VALUE")


class Trivia(typing.Protocol):
    class Label:
        CONTENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Trivia) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_content(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_content(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_content(self) -> fltk.fegen.pyrt.span.Span | None: ...


Trivia.Label.CONTENT = _ProtocolLabelMember("Trivia.Label.CONTENT")


class Span(typing.Protocol):
    kind: typing.Literal[fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN] = fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN


class CstModule(typing.Protocol):
    @property
    def Expr(self) -> type[Expr]: ...

    @property
    def Term(self) -> type[Term]: ...

    @property
    def Factor(self) -> type[Factor]: ...

    @property
    def Number(self) -> type[Number]: ...

    @property
    def Trivia(self) -> type[Trivia]: ...
