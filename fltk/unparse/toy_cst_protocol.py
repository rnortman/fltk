# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol
__all__ = [
    "CstModule",
    "Expr",
    "ExprLabel",
    "Factor",
    "FactorLabel",
    "NodeKind",
    "Number",
    "NumberLabel",
    "Span",
    "Term",
    "TermLabel",
    "Trivia",
    "TriviaLabel",
]


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
    kind: typing.Literal[NodeKind.EXPR] = NodeKind.EXPR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Expr) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def insert(
        self,
        index: int,
        child: Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_plus(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_plus(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_plus(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_plus(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_plus(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_term(self, child: Term) -> None: ...

    def extend_term(self, children: typing.Iterable[Term]) -> None: ...

    def children_term(self) -> typing.Iterator[Term]: ...

    def child_term(self) -> Term: ...

    def maybe_term(self) -> Term | None: ...

    def plus(self) -> typing.Sequence[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def term(self) -> typing.Sequence[Term]: ...


class ExprLabel:
    """Sentinels equal to either backend's Expr labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    PLUS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Expr.Label.PLUS")
    TERM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Expr.Label.TERM")


class Term(typing.Protocol):
    kind: typing.Literal[NodeKind.TERM] = NodeKind.TERM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Term) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def insert(
        self,
        index: int,
        child: Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_factor(self, child: Factor) -> None: ...

    def extend_factor(self, children: typing.Iterable[Factor]) -> None: ...

    def children_factor(self) -> typing.Iterator[Factor]: ...

    def child_factor(self) -> Factor: ...

    def maybe_factor(self) -> Factor | None: ...

    def append_mult(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_mult(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_mult(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_mult(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_mult(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def factor(self) -> typing.Sequence[Factor]: ...

    def mult(self) -> typing.Sequence[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...


class TermLabel:
    """Sentinels equal to either backend's Term labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    FACTOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Term.Label.FACTOR")
    MULT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Term.Label.MULT")


class Factor(typing.Protocol):
    kind: typing.Literal[NodeKind.FACTOR] = NodeKind.FACTOR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Expr | Number | Trivia]]: ...

    def append(
        self, child: Expr | Number | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Expr | Number | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Factor) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Expr | Number | Trivia]: ...

    def insert(
        self,
        index: int,
        child: Expr | Number | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Expr | Number | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: Expr | Number | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

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

    def expr(self) -> Expr | None: ...

    def number(self) -> Number | None: ...


class FactorLabel:
    """Sentinels equal to either backend's Factor labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    EXPR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Factor.Label.EXPR")
    NUMBER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Factor.Label.NUMBER")


class Number(typing.Protocol):
    kind: typing.Literal[NodeKind.NUMBER] = NodeKind.NUMBER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ]: ...

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Number) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def value_text(self) -> str: ...

    def text(self) -> str: ...


class NumberLabel:
    """Sentinels equal to either backend's Number labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Number.Label.VALUE")


class Trivia(typing.Protocol):
    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ]: ...

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Trivia) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def content_text(self) -> str: ...

    def text(self) -> str: ...


class TriviaLabel:
    """Sentinels equal to either backend's Trivia labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    CONTENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Trivia.Label.CONTENT")


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
