import dataclasses
import enum
import typing

import fltk.fegen.pyrt.terminalsrc


@dataclasses.dataclass
class Expr:
    class Label(enum.Enum):
        PLUS = enum.auto()
        TERM = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Term", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self, child: typing.Union["Term", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"], label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Term", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Term", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_plus(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Expr.Label.PLUS, child))

    def extend_plus(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Expr.Label.PLUS, child) for child in children)

    def children_plus(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Expr.Label.PLUS
        )

    def child_plus(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_plus())
        if (n := len(children)) != 1:
            msg = f"Expected one plus child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_plus(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_plus())
        if (n := len(children)) > 1:
            msg = f"Expected at most one plus child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_term(self, child: "Term") -> None:
        self.children.append((Expr.Label.TERM, child))

    def extend_term(self, children: typing.Iterable["Term"]) -> None:
        self.children.extend((Expr.Label.TERM, child) for child in children)

    def children_term(self) -> typing.Iterator["Term"]:
        return (typing.cast("Term", child) for label, child in self.children if label == Expr.Label.TERM)

    def child_term(self) -> "Term":
        children = list(self.children_term())
        if (n := len(children)) != 1:
            msg = f"Expected one term child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_term(self) -> typing.Optional["Term"]:
        children = list(self.children_term())
        if (n := len(children)) > 1:
            msg = f"Expected at most one term child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Term:
    class Label(enum.Enum):
        FACTOR = enum.auto()
        MULT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Factor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self, child: typing.Union["Factor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"], label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Factor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Factor", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_factor(self, child: "Factor") -> None:
        self.children.append((Term.Label.FACTOR, child))

    def extend_factor(self, children: typing.Iterable["Factor"]) -> None:
        self.children.extend((Term.Label.FACTOR, child) for child in children)

    def children_factor(self) -> typing.Iterator["Factor"]:
        return (typing.cast("Factor", child) for label, child in self.children if label == Term.Label.FACTOR)

    def child_factor(self) -> "Factor":
        children = list(self.children_factor())
        if (n := len(children)) != 1:
            msg = f"Expected one factor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_factor(self) -> typing.Optional["Factor"]:
        children = list(self.children_factor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one factor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_mult(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Term.Label.MULT, child))

    def extend_mult(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Term.Label.MULT, child) for child in children)

    def children_mult(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Term.Label.MULT
        )

    def child_mult(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_mult())
        if (n := len(children)) != 1:
            msg = f"Expected one mult child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_mult(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_mult())
        if (n := len(children)) > 1:
            msg = f"Expected at most one mult child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Factor:
    class Label(enum.Enum):
        EXPR = enum.auto()
        NUMBER = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Expr", "Number", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: typing.Union["Expr", "Number", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[typing.Union["Expr", "Number", "Trivia"]], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Expr", "Number", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_expr(self, child: "Expr") -> None:
        self.children.append((Factor.Label.EXPR, child))

    def extend_expr(self, children: typing.Iterable["Expr"]) -> None:
        self.children.extend((Factor.Label.EXPR, child) for child in children)

    def children_expr(self) -> typing.Iterator["Expr"]:
        return (typing.cast("Expr", child) for label, child in self.children if label == Factor.Label.EXPR)

    def child_expr(self) -> "Expr":
        children = list(self.children_expr())
        if (n := len(children)) != 1:
            msg = f"Expected one expr child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_expr(self) -> typing.Optional["Expr"]:
        children = list(self.children_expr())
        if (n := len(children)) > 1:
            msg = f"Expected at most one expr child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_number(self, child: "Number") -> None:
        self.children.append((Factor.Label.NUMBER, child))

    def extend_number(self, children: typing.Iterable["Number"]) -> None:
        self.children.extend((Factor.Label.NUMBER, child) for child in children)

    def children_number(self) -> typing.Iterator["Number"]:
        return (typing.cast("Number", child) for label, child in self.children if label == Factor.Label.NUMBER)

    def child_number(self) -> "Number":
        children = list(self.children_number())
        if (n := len(children)) != 1:
            msg = f"Expected one number child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_number(self) -> typing.Optional["Number"]:
        children = list(self.children_number())
        if (n := len(children)) > 1:
            msg = f"Expected at most one number child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Number:
    class Label(enum.Enum):
        VALUE = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(default_factory=list)

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_value(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Number.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Number.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Number.Label.VALUE)

    def child_value(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Trivia:
    class Label(enum.Enum):
        CONTENT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(default_factory=list)

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_content(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Trivia.Label.CONTENT, child))

    def extend_content(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Trivia.Label.CONTENT, child) for child in children)

    def children_content(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Trivia.Label.CONTENT)

    def child_content(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_content())
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_content())
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None
