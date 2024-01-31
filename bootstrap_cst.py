import dataclasses
import enum
import typing

import fltk.fegen.pyrt.terminalsrc


@dataclasses.dataclass
class Grammar:
    class Label(enum.Enum):
        RULE = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[typing.Optional[Label], "Rule"]] = dataclasses.field(default_factory=list)

    def append(self, child: "Rule", label: typing.Optional[Label] = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable["Rule"], label: typing.Optional[Label] = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], "Rule"]:
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
    children: list[tuple[typing.Optional[Label], typing.Union["Alternatives", "Identifier"]]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: typing.Union["Alternatives", "Identifier"], label: typing.Optional[Label] = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Alternatives", "Identifier"]],
        label: typing.Optional[Label] = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], typing.Union["Alternatives", "Identifier"]]:
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
    children: list[tuple[typing.Optional[Label], "Items"]] = dataclasses.field(default_factory=list)

    def append(self, child: "Items", label: typing.Optional[Label] = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable["Items"], label: typing.Optional[Label] = None) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], "Items"]:
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
        WS = enum.auto()

    span: fltk.fegen.pyrt.terminalsrc.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[typing.Optional[Label], typing.Union["Item", "fltk.fegen.pyrt.terminalsrc.Span"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self, child: typing.Union["Item", "fltk.fegen.pyrt.terminalsrc.Span"], label: typing.Optional[Label] = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Item", "fltk.fegen.pyrt.terminalsrc.Span"]],
        label: typing.Optional[Label] = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], typing.Union["Item", "fltk.fegen.pyrt.terminalsrc.Span"]]:
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

    def append_ws(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Items.Label.WS, child))

    def extend_ws(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Items.Label.WS, child) for child in children)

    def children_ws(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Items.Label.WS
        )

    def child_ws(self) -> "fltk.fegen.pyrt.terminalsrc.Span":
        children = list(self.children_ws())
        if (n := len(children)) != 1:
            msg = f"Expected one ws child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws(self) -> typing.Optional["fltk.fegen.pyrt.terminalsrc.Span"]:
        children = list(self.children_ws())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws child but have {n}"
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
    children: list[tuple[typing.Optional[Label], typing.Union["Disposition", "Identifier", "Quantifier", "Term"]]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: typing.Union["Disposition", "Identifier", "Quantifier", "Term"],
        label: typing.Optional[Label] = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Disposition", "Identifier", "Quantifier", "Term"]],
        label: typing.Optional[Label] = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], typing.Union["Disposition", "Identifier", "Quantifier", "Term"]]:
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
        tuple[typing.Optional[Label], typing.Union["Alternatives", "Identifier", "Literal", "RawString"]]
    ] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: typing.Union["Alternatives", "Identifier", "Literal", "RawString"],
        label: typing.Optional[Label] = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[typing.Union["Alternatives", "Identifier", "Literal", "RawString"]],
        label: typing.Optional[Label] = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(
        self,
    ) -> tuple[typing.Optional[Label], typing.Union["Alternatives", "Identifier", "Literal", "RawString"]]:
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
    children: list[tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: typing.Optional[Label] = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: typing.Optional[Label] = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_include(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Disposition.Label.INCLUDE, child))

    def extend_include(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Disposition.Label.INCLUDE, child) for child in children)

    def children_include(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Disposition.Label.INCLUDE
        )

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
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Disposition.Label.INLINE
        )

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
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Disposition.Label.SUPPRESS
        )

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
    children: list[tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: typing.Optional[Label] = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: typing.Optional[Label] = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_one_or_more(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Quantifier.Label.ONE_OR_MORE, child))

    def extend_one_or_more(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Quantifier.Label.ONE_OR_MORE, child) for child in children)

    def children_one_or_more(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Quantifier.Label.ONE_OR_MORE
        )

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
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Quantifier.Label.OPTIONAL
        )

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
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Quantifier.Label.ZERO_OR_MORE
        )

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
    children: list[tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: typing.Optional[Label] = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: typing.Optional[Label] = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_name(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Identifier.Label.NAME, child))

    def extend_name(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Identifier.Label.NAME, child) for child in children)

    def children_name(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Identifier.Label.NAME
        )

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
    children: list[tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: typing.Optional[Label] = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: typing.Optional[Label] = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_value(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((RawString.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((RawString.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == RawString.Label.VALUE
        )

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
    children: list[tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: "fltk.fegen.pyrt.terminalsrc.Span", label: typing.Optional[Label] = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"], label: typing.Optional[Label] = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def child(self) -> tuple[typing.Optional[Label], "fltk.fegen.pyrt.terminalsrc.Span"]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def append_value(self, child: "fltk.fegen.pyrt.terminalsrc.Span") -> None:
        self.children.append((Literal.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable["fltk.fegen.pyrt.terminalsrc.Span"]) -> None:
        self.children.extend((Literal.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator["fltk.fegen.pyrt.terminalsrc.Span"]:
        return (
            typing.cast("fltk.fegen.pyrt.terminalsrc.Span", child)
            for label, child in self.children
            if label == Literal.Label.VALUE
        )

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
