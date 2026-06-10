from __future__ import annotations

import dataclasses
import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk._native
    import fltk.fegen.pyrt.span


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


@dataclasses.dataclass
class Expr:
    class Label(enum.Enum):
        PLUS = enum.auto()
        TERM = enum.auto()
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

    kind: typing.Literal[NodeKind.EXPR] = NodeKind.EXPR
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Term | Trivia | fltk.fegen.pyrt.span.Span]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Term | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Term | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Expr) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Term | Trivia | fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_plus(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Expr.Label.PLUS, child))

    def extend_plus(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Expr.Label.PLUS, child) for child in children)

    def children_plus(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Expr.Label.PLUS
        )

    def child_plus(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_plus())
        if (n := len(children)) != 1:
            msg = f"Expected one plus child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_plus(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_plus())
        if (n := len(children)) > 1:
            msg = f"Expected at most one plus child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_term(self, child: Term) -> None:
        self.children.append((Expr.Label.TERM, child))

    def extend_term(self, children: typing.Iterable[Term]) -> None:
        self.children.extend((Expr.Label.TERM, child) for child in children)

    def children_term(self) -> typing.Iterator[Term]:
        return (typing.cast("Term", child) for (label, child) in self.children if label == Expr.Label.TERM)

    def child_term(self) -> Term:
        children = list(self.children_term())
        if (n := len(children)) != 1:
            msg = f"Expected one term child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_term(self) -> Term | None:
        children = list(self.children_term())
        if (n := len(children)) > 1:
            msg = f"Expected at most one term child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Expr.Label.PLUS._fltk_canonical_name = "Expr.Label.PLUS"
Expr.Label.TERM._fltk_canonical_name = "Expr.Label.TERM"


@dataclasses.dataclass
class Term:
    class Label(enum.Enum):
        FACTOR = enum.auto()
        MULT = enum.auto()
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

    kind: typing.Literal[NodeKind.TERM] = NodeKind.TERM
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Factor | Trivia | fltk.fegen.pyrt.span.Span]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Factor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Factor | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Term) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Factor | Trivia | fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_factor(self, child: Factor) -> None:
        self.children.append((Term.Label.FACTOR, child))

    def extend_factor(self, children: typing.Iterable[Factor]) -> None:
        self.children.extend((Term.Label.FACTOR, child) for child in children)

    def children_factor(self) -> typing.Iterator[Factor]:
        return (typing.cast("Factor", child) for (label, child) in self.children if label == Term.Label.FACTOR)

    def child_factor(self) -> Factor:
        children = list(self.children_factor())
        if (n := len(children)) != 1:
            msg = f"Expected one factor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_factor(self) -> Factor | None:
        children = list(self.children_factor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one factor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_mult(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Term.Label.MULT, child))

    def extend_mult(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Term.Label.MULT, child) for child in children)

    def children_mult(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Term.Label.MULT
        )

    def child_mult(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_mult())
        if (n := len(children)) != 1:
            msg = f"Expected one mult child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_mult(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_mult())
        if (n := len(children)) > 1:
            msg = f"Expected at most one mult child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Term.Label.FACTOR._fltk_canonical_name = "Term.Label.FACTOR"
Term.Label.MULT._fltk_canonical_name = "Term.Label.MULT"


@dataclasses.dataclass
class Factor:
    class Label(enum.Enum):
        EXPR = enum.auto()
        NUMBER = enum.auto()
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

    kind: typing.Literal[NodeKind.FACTOR] = NodeKind.FACTOR
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Expr | Number | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Expr | Number | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Expr | Number | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Factor) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Expr | Number | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_expr(self, child: Expr) -> None:
        self.children.append((Factor.Label.EXPR, child))

    def extend_expr(self, children: typing.Iterable[Expr]) -> None:
        self.children.extend((Factor.Label.EXPR, child) for child in children)

    def children_expr(self) -> typing.Iterator[Expr]:
        return (typing.cast("Expr", child) for (label, child) in self.children if label == Factor.Label.EXPR)

    def child_expr(self) -> Expr:
        children = list(self.children_expr())
        if (n := len(children)) != 1:
            msg = f"Expected one expr child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_expr(self) -> Expr | None:
        children = list(self.children_expr())
        if (n := len(children)) > 1:
            msg = f"Expected at most one expr child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_number(self, child: Number) -> None:
        self.children.append((Factor.Label.NUMBER, child))

    def extend_number(self, children: typing.Iterable[Number]) -> None:
        self.children.extend((Factor.Label.NUMBER, child) for child in children)

    def children_number(self) -> typing.Iterator[Number]:
        return (typing.cast("Number", child) for (label, child) in self.children if label == Factor.Label.NUMBER)

    def child_number(self) -> Number:
        children = list(self.children_number())
        if (n := len(children)) != 1:
            msg = f"Expected one number child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_number(self) -> Number | None:
        children = list(self.children_number())
        if (n := len(children)) > 1:
            msg = f"Expected at most one number child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Factor.Label.EXPR._fltk_canonical_name = "Factor.Label.EXPR"
Factor.Label.NUMBER._fltk_canonical_name = "Factor.Label.NUMBER"


@dataclasses.dataclass
class Number:
    class Label(enum.Enum):
        VALUE = enum.auto()
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

    kind: typing.Literal[NodeKind.NUMBER] = NodeKind.NUMBER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]] = dataclasses.field(default_factory=list)

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Number) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_value(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Number.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Number.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (child for (label, child) in self.children if label == Number.Label.VALUE)

    def child_value(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Number.Label.VALUE._fltk_canonical_name = "Number.Label.VALUE"


@dataclasses.dataclass
class Trivia:
    class Label(enum.Enum):
        CONTENT = enum.auto()
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

    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]] = dataclasses.field(default_factory=list)

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Trivia) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_content(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Trivia.Label.CONTENT, child))

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Trivia.Label.CONTENT, child) for child in children)

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (child for (label, child) in self.children if label == Trivia.Label.CONTENT)

    def child_content(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_content())
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_content())
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Trivia.Label.CONTENT._fltk_canonical_name = "Trivia.Label.CONTENT"
