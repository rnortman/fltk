import dataclasses
import enum
import typing

import fltk.fegen.pyrt.terminalsrc


@dataclasses.dataclass
class Grammar:
    class Label(enum.Enum):
        RULE = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Rule", "Trivia"]]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union["Rule", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[typing.Union["Rule", "Trivia"]], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Rule", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_rule(self, child: "Rule") -> None:
        self.children.append((Grammar.Label.RULE, child))

    def extend_rule(self, children: typing.Iterable["Rule"]) -> None:
        self.children.extend((Grammar.Label.RULE, child) for child in children)

    def children_rule(self) -> typing.Iterator["Rule"]:
        return (typing.cast("Rule", child) for label, child in self.children if label == Grammar.Label.RULE)

    def child_rule(self) -> "Rule":
        children = list(self.children_rule())
        if (n := len(children)) != 1:
            msg = f"Expected one rule child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule(self) -> typing.Optional["Rule"]:
        children = list(self.children_rule())
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Rule:
    class Label(enum.Enum):
        ALTERNATIVES = enum.auto()
        NAME = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Alternatives", "Identifier", "Trivia"]]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: typing.Union["Alternatives", "Identifier", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Alternatives", "Identifier", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Alternatives", "Identifier", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_alternatives(self, child: "Alternatives") -> None:
        self.children.append((Rule.Label.ALTERNATIVES, child))

    def extend_alternatives(self, children: typing.Iterable["Alternatives"]) -> None:
        self.children.extend((Rule.Label.ALTERNATIVES, child) for child in children)

    def children_alternatives(self) -> typing.Iterator["Alternatives"]:
        return (
            typing.cast("Alternatives", child) for label, child in self.children if label == Rule.Label.ALTERNATIVES
        )

    def child_alternatives(self) -> "Alternatives":
        children = list(self.children_alternatives())
        if (n := len(children)) != 1:
            msg = f"Expected one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_alternatives(self) -> typing.Optional["Alternatives"]:
        children = list(self.children_alternatives())
        if (n := len(children)) > 1:
            msg = f"Expected at most one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_name(self, child: "Identifier") -> None:
        self.children.append((Rule.Label.NAME, child))

    def extend_name(self, children: typing.Iterable["Identifier"]) -> None:
        self.children.extend((Rule.Label.NAME, child) for child in children)

    def children_name(self) -> typing.Iterator["Identifier"]:
        return (typing.cast("Identifier", child) for label, child in self.children if label == Rule.Label.NAME)

    def child_name(self) -> "Identifier":
        children = list(self.children_name())
        if (n := len(children)) != 1:
            msg = f"Expected one name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name(self) -> typing.Optional["Identifier"]:
        children = list(self.children_name())
        if (n := len(children)) > 1:
            msg = f"Expected at most one name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Alternatives:
    class Label(enum.Enum):
        ITEMS = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Items", "Trivia"]]] = dataclasses.field(default_factory=list)

    def append(self, child: typing.Union["Items", "Trivia"], label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[typing.Union["Items", "Trivia"]], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[Label | None, typing.Union["Items", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_items(self, child: "Items") -> None:
        self.children.append((Alternatives.Label.ITEMS, child))

    def extend_items(self, children: typing.Iterable["Items"]) -> None:
        self.children.extend((Alternatives.Label.ITEMS, child) for child in children)

    def children_items(self) -> typing.Iterator["Items"]:
        return (typing.cast("Items", child) for label, child in self.children if label == Alternatives.Label.ITEMS)

    def child_items(self) -> "Items":
        children = list(self.children_items())
        if (n := len(children)) != 1:
            msg = f"Expected one items child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_items(self) -> typing.Optional["Items"]:
        children = list(self.children_items())
        if (n := len(children)) > 1:
            msg = f"Expected at most one items child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Items:
    class Label(enum.Enum):
        ITEM = enum.auto()
        NO_WS = enum.auto()
        WS_ALLOWED = enum.auto()
        WS_REQUIRED = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Item", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: typing.Union["Item", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Item", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["Item", "Trivia", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_item(self, child: "Item") -> None:
        self.children.append((Items.Label.ITEM, child))

    def extend_item(self, children: typing.Iterable["Item"]) -> None:
        self.children.extend((Items.Label.ITEM, child) for child in children)

    def children_item(self) -> typing.Iterator["Item"]:
        return (typing.cast("Item", child) for label, child in self.children if label == Items.Label.ITEM)

    def child_item(self) -> "Item":
        children = list(self.children_item())
        if (n := len(children)) != 1:
            msg = f"Expected one item child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_item(self) -> typing.Optional["Item"]:
        children = list(self.children_item())
        if (n := len(children)) > 1:
            msg = f"Expected at most one item child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_no_ws(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Items.Label.NO_WS, child))

    def extend_no_ws(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Items.Label.NO_WS, child) for child in children)

    def children_no_ws(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Items.Label.NO_WS
        )

    def child_no_ws(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_no_ws())
        if (n := len(children)) != 1:
            msg = f"Expected one no_ws child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_no_ws(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_no_ws())
        if (n := len(children)) > 1:
            msg = f"Expected at most one no_ws child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_allowed(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Items.Label.WS_ALLOWED, child))

    def extend_ws_allowed(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Items.Label.WS_ALLOWED, child) for child in children)

    def children_ws_allowed(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Items.Label.WS_ALLOWED
        )

    def child_ws_allowed(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_ws_allowed())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_allowed(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_ws_allowed())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_required(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Items.Label.WS_REQUIRED, child))

    def extend_ws_required(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Items.Label.WS_REQUIRED, child) for child in children)

    def children_ws_required(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Items.Label.WS_REQUIRED
        )

    def child_ws_required(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_ws_required())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_required(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_ws_required())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Item:
    class Label(enum.Enum):
        DISPOSITION = enum.auto()
        LABEL = enum.auto()
        QUANTIFIER = enum.auto()
        TERM = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, typing.Union["Disposition", "Identifier", "Quantifier", "Term", "Trivia"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: typing.Union["Disposition", "Identifier", "Quantifier", "Term", "Trivia"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Disposition", "Identifier", "Quantifier", "Term", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["Disposition", "Identifier", "Quantifier", "Term", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_disposition(self, child: "Disposition") -> None:
        self.children.append((Item.Label.DISPOSITION, child))

    def extend_disposition(self, children: typing.Iterable["Disposition"]) -> None:
        self.children.extend((Item.Label.DISPOSITION, child) for child in children)

    def children_disposition(self) -> typing.Iterator["Disposition"]:
        return (typing.cast("Disposition", child) for label, child in self.children if label == Item.Label.DISPOSITION)

    def child_disposition(self) -> "Disposition":
        children = list(self.children_disposition())
        if (n := len(children)) != 1:
            msg = f"Expected one disposition child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_disposition(self) -> typing.Optional["Disposition"]:
        children = list(self.children_disposition())
        if (n := len(children)) > 1:
            msg = f"Expected at most one disposition child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_label(self, child: "Identifier") -> None:
        self.children.append((Item.Label.LABEL, child))

    def extend_label(self, children: typing.Iterable["Identifier"]) -> None:
        self.children.extend((Item.Label.LABEL, child) for child in children)

    def children_label(self) -> typing.Iterator["Identifier"]:
        return (typing.cast("Identifier", child) for label, child in self.children if label == Item.Label.LABEL)

    def child_label(self) -> "Identifier":
        children = list(self.children_label())
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> typing.Optional["Identifier"]:
        children = list(self.children_label())
        if (n := len(children)) > 1:
            msg = f"Expected at most one label child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_quantifier(self, child: "Quantifier") -> None:
        self.children.append((Item.Label.QUANTIFIER, child))

    def extend_quantifier(self, children: typing.Iterable["Quantifier"]) -> None:
        self.children.extend((Item.Label.QUANTIFIER, child) for child in children)

    def children_quantifier(self) -> typing.Iterator["Quantifier"]:
        return (typing.cast("Quantifier", child) for label, child in self.children if label == Item.Label.QUANTIFIER)

    def child_quantifier(self) -> "Quantifier":
        children = list(self.children_quantifier())
        if (n := len(children)) != 1:
            msg = f"Expected one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_quantifier(self) -> typing.Optional["Quantifier"]:
        children = list(self.children_quantifier())
        if (n := len(children)) > 1:
            msg = f"Expected at most one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_term(self, child: "Term") -> None:
        self.children.append((Item.Label.TERM, child))

    def extend_term(self, children: typing.Iterable["Term"]) -> None:
        self.children.extend((Item.Label.TERM, child) for child in children)

    def children_term(self) -> typing.Iterator["Term"]:
        return (typing.cast("Term", child) for label, child in self.children if label == Item.Label.TERM)

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
        ALTERNATIVES = enum.auto()
        IDENTIFIER = enum.auto()
        LITERAL = enum.auto()
        REGEX = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[
        tuple[Label | None, typing.Union["Alternatives", "Identifier", "Literal", "RawString", "Trivia"]]
    ] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: typing.Union["Alternatives", "Identifier", "Literal", "RawString", "Trivia"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Alternatives", "Identifier", "Literal", "RawString", "Trivia"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["Alternatives", "Identifier", "Literal", "RawString", "Trivia"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_alternatives(self, child: "Alternatives") -> None:
        self.children.append((Term.Label.ALTERNATIVES, child))

    def extend_alternatives(self, children: typing.Iterable["Alternatives"]) -> None:
        self.children.extend((Term.Label.ALTERNATIVES, child) for child in children)

    def children_alternatives(self) -> typing.Iterator["Alternatives"]:
        return (
            typing.cast("Alternatives", child) for label, child in self.children if label == Term.Label.ALTERNATIVES
        )

    def child_alternatives(self) -> "Alternatives":
        children = list(self.children_alternatives())
        if (n := len(children)) != 1:
            msg = f"Expected one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_alternatives(self) -> typing.Optional["Alternatives"]:
        children = list(self.children_alternatives())
        if (n := len(children)) > 1:
            msg = f"Expected at most one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_identifier(self, child: "Identifier") -> None:
        self.children.append((Term.Label.IDENTIFIER, child))

    def extend_identifier(self, children: typing.Iterable["Identifier"]) -> None:
        self.children.extend((Term.Label.IDENTIFIER, child) for child in children)

    def children_identifier(self) -> typing.Iterator["Identifier"]:
        return (typing.cast("Identifier", child) for label, child in self.children if label == Term.Label.IDENTIFIER)

    def child_identifier(self) -> "Identifier":
        children = list(self.children_identifier())
        if (n := len(children)) != 1:
            msg = f"Expected one identifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_identifier(self) -> typing.Optional["Identifier"]:
        children = list(self.children_identifier())
        if (n := len(children)) > 1:
            msg = f"Expected at most one identifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_literal(self, child: "Literal") -> None:
        self.children.append((Term.Label.LITERAL, child))

    def extend_literal(self, children: typing.Iterable["Literal"]) -> None:
        self.children.extend((Term.Label.LITERAL, child) for child in children)

    def children_literal(self) -> typing.Iterator["Literal"]:
        return (typing.cast("Literal", child) for label, child in self.children if label == Term.Label.LITERAL)

    def child_literal(self) -> "Literal":
        children = list(self.children_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_literal(self) -> typing.Optional["Literal"]:
        children = list(self.children_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_regex(self, child: "RawString") -> None:
        self.children.append((Term.Label.REGEX, child))

    def extend_regex(self, children: typing.Iterable["RawString"]) -> None:
        self.children.extend((Term.Label.REGEX, child) for child in children)

    def children_regex(self) -> typing.Iterator["RawString"]:
        return (typing.cast("RawString", child) for label, child in self.children if label == Term.Label.REGEX)

    def child_regex(self) -> "RawString":
        children = list(self.children_regex())
        if (n := len(children)) != 1:
            msg = f"Expected one regex child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_regex(self) -> typing.Optional["RawString"]:
        children = list(self.children_regex())
        if (n := len(children)) > 1:
            msg = f"Expected at most one regex child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Disposition:
    class Label(enum.Enum):
        INCLUDE = enum.auto()
        INLINE = enum.auto()
        SUPPRESS = enum.auto()

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

    def append_include(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Disposition.Label.INCLUDE, child))

    def extend_include(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Disposition.Label.INCLUDE, child) for child in children)

    def children_include(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Disposition.Label.INCLUDE)

    def child_include(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_include())
        if (n := len(children)) != 1:
            msg = f"Expected one include child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_include(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_include())
        if (n := len(children)) > 1:
            msg = f"Expected at most one include child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_inline(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Disposition.Label.INLINE, child))

    def extend_inline(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Disposition.Label.INLINE, child) for child in children)

    def children_inline(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Disposition.Label.INLINE)

    def child_inline(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_inline())
        if (n := len(children)) != 1:
            msg = f"Expected one inline child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_inline(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_inline())
        if (n := len(children)) > 1:
            msg = f"Expected at most one inline child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_suppress(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Disposition.Label.SUPPRESS, child))

    def extend_suppress(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Disposition.Label.SUPPRESS, child) for child in children)

    def children_suppress(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Disposition.Label.SUPPRESS)

    def child_suppress(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_suppress())
        if (n := len(children)) != 1:
            msg = f"Expected one suppress child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_suppress(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_suppress())
        if (n := len(children)) > 1:
            msg = f"Expected at most one suppress child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Quantifier:
    class Label(enum.Enum):
        ONE_OR_MORE = enum.auto()
        OPTIONAL = enum.auto()
        ZERO_OR_MORE = enum.auto()

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

    def append_one_or_more(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Quantifier.Label.ONE_OR_MORE, child))

    def extend_one_or_more(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Quantifier.Label.ONE_OR_MORE, child) for child in children)

    def children_one_or_more(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Quantifier.Label.ONE_OR_MORE)

    def child_one_or_more(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_one_or_more())
        if (n := len(children)) != 1:
            msg = f"Expected one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_one_or_more(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_one_or_more())
        if (n := len(children)) > 1:
            msg = f"Expected at most one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_optional(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Quantifier.Label.OPTIONAL, child))

    def extend_optional(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Quantifier.Label.OPTIONAL, child) for child in children)

    def children_optional(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Quantifier.Label.OPTIONAL)

    def child_optional(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_optional())
        if (n := len(children)) != 1:
            msg = f"Expected one optional child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_optional(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_optional())
        if (n := len(children)) > 1:
            msg = f"Expected at most one optional child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_zero_or_more(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Quantifier.Label.ZERO_OR_MORE, child))

    def extend_zero_or_more(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Quantifier.Label.ZERO_OR_MORE, child) for child in children)

    def children_zero_or_more(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Quantifier.Label.ZERO_OR_MORE)

    def child_zero_or_more(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_zero_or_more())
        if (n := len(children)) != 1:
            msg = f"Expected one zero_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_zero_or_more(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_zero_or_more())
        if (n := len(children)) > 1:
            msg = f"Expected at most one zero_or_more child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class Identifier:
    class Label(enum.Enum):
        NAME = enum.auto()

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

    def append_name(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Identifier.Label.NAME, child))

    def extend_name(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Identifier.Label.NAME, child) for child in children)

    def children_name(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Identifier.Label.NAME)

    def child_name(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_name())
        if (n := len(children)) != 1:
            msg = f"Expected one name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_name())
        if (n := len(children)) > 1:
            msg = f"Expected at most one name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class RawString:
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
        self.children.append((RawString.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((RawString.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == RawString.Label.VALUE)

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
class Literal:
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
        self.children.append((Literal.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Literal.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == Literal.Label.VALUE)

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
        BLOCK_COMMENT = enum.auto()
        LINE_COMMENT = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[
        tuple[Label | None, typing.Union["BlockComment", "LineComment", "fltk.fegen.pyrt.terminalsrc.Span"]]
    ] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: typing.Union["BlockComment", "LineComment", "fltk.fegen.pyrt.terminalsrc.Span"],
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["BlockComment", "LineComment", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[Label | None, typing.Union["BlockComment", "LineComment", "fltk.fegen.pyrt.terminalsrc.Span"]]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_block_comment(self, child: "BlockComment") -> None:
        self.children.append((Trivia.Label.BLOCK_COMMENT, child))

    def extend_block_comment(self, children: typing.Iterable["BlockComment"]) -> None:
        self.children.extend((Trivia.Label.BLOCK_COMMENT, child) for child in children)

    def children_block_comment(self) -> typing.Iterator["BlockComment"]:
        return (
            typing.cast("BlockComment", child) for label, child in self.children if label == Trivia.Label.BLOCK_COMMENT
        )

    def child_block_comment(self) -> "BlockComment":
        children = list(self.children_block_comment())
        if (n := len(children)) != 1:
            msg = f"Expected one block_comment child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_block_comment(self) -> typing.Optional["BlockComment"]:
        children = list(self.children_block_comment())
        if (n := len(children)) > 1:
            msg = f"Expected at most one block_comment child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_line_comment(self, child: "LineComment") -> None:
        self.children.append((Trivia.Label.LINE_COMMENT, child))

    def extend_line_comment(self, children: typing.Iterable["LineComment"]) -> None:
        self.children.extend((Trivia.Label.LINE_COMMENT, child) for child in children)

    def children_line_comment(self) -> typing.Iterator["LineComment"]:
        return (
            typing.cast("LineComment", child) for label, child in self.children if label == Trivia.Label.LINE_COMMENT
        )

    def child_line_comment(self) -> "LineComment":
        children = list(self.children_line_comment())
        if (n := len(children)) != 1:
            msg = f"Expected one line_comment child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_line_comment(self) -> typing.Optional["LineComment"]:
        children = list(self.children_line_comment())
        if (n := len(children)) > 1:
            msg = f"Expected at most one line_comment child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class LineComment:
    class Label(enum.Enum):
        CONTENT = enum.auto()
        PREFIX = enum.auto()

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
        self.children.append((LineComment.Label.CONTENT, child))

    def extend_content(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((LineComment.Label.CONTENT, child) for child in children)

    def children_content(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == LineComment.Label.CONTENT)

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

    def append_prefix(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((LineComment.Label.PREFIX, child))

    def extend_prefix(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((LineComment.Label.PREFIX, child) for child in children)

    def children_prefix(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == LineComment.Label.PREFIX)

    def child_prefix(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_prefix())
        if (n := len(children)) != 1:
            msg = f"Expected one prefix child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_prefix(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_prefix())
        if (n := len(children)) > 1:
            msg = f"Expected at most one prefix child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


@dataclasses.dataclass
class BlockComment:
    class Label(enum.Enum):
        CONTENT = enum.auto()
        END = enum.auto()
        START = enum.auto()

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
        self.children.append((BlockComment.Label.CONTENT, child))

    def extend_content(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((BlockComment.Label.CONTENT, child) for child in children)

    def children_content(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == BlockComment.Label.CONTENT)

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

    def append_end(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((BlockComment.Label.END, child))

    def extend_end(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((BlockComment.Label.END, child) for child in children)

    def children_end(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == BlockComment.Label.END)

    def child_end(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_end())
        if (n := len(children)) != 1:
            msg = f"Expected one end child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_end(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_end())
        if (n := len(children)) > 1:
            msg = f"Expected at most one end child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_start(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((BlockComment.Label.START, child))

    def extend_start(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((BlockComment.Label.START, child) for child in children)

    def children_start(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (child for label, child in self.children if label == BlockComment.Label.START)

    def child_start(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_start())
        if (n := len(children)) != 1:
            msg = f"Expected one start child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_start(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_start())
        if (n := len(children)) > 1:
            msg = f"Expected at most one start child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None
