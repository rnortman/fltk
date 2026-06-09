# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk._native
    import fltk.fegen.pyrt.span
__all__ = [
    "Alternatives",
    "BlockComment",
    "CstModule",
    "Disposition",
    "Grammar",
    "Identifier",
    "Item",
    "Items",
    "LineComment",
    "Literal",
    "NodeKind",
    "Quantifier",
    "RawString",
    "Rule",
    "Span",
    "Term",
    "Trivia",
    "Whitespace",
]


class NodeKind(enum.Enum):
    GRAMMAR = enum.auto()
    RULE = enum.auto()
    ALTERNATIVES = enum.auto()
    ITEMS = enum.auto()
    ITEM = enum.auto()
    TERM = enum.auto()
    DISPOSITION = enum.auto()
    QUANTIFIER = enum.auto()
    IDENTIFIER = enum.auto()
    RAWSTRING = enum.auto()
    LITERAL = enum.auto()
    TRIVIA = enum.auto()
    WHITESPACE = enum.auto()
    LINECOMMENT = enum.auto()
    BLOCKCOMMENT = enum.auto()
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


NodeKind.GRAMMAR._fltk_canonical_name = "NodeKind.GRAMMAR"
NodeKind.RULE._fltk_canonical_name = "NodeKind.RULE"
NodeKind.ALTERNATIVES._fltk_canonical_name = "NodeKind.ALTERNATIVES"
NodeKind.ITEMS._fltk_canonical_name = "NodeKind.ITEMS"
NodeKind.ITEM._fltk_canonical_name = "NodeKind.ITEM"
NodeKind.TERM._fltk_canonical_name = "NodeKind.TERM"
NodeKind.DISPOSITION._fltk_canonical_name = "NodeKind.DISPOSITION"
NodeKind.QUANTIFIER._fltk_canonical_name = "NodeKind.QUANTIFIER"
NodeKind.IDENTIFIER._fltk_canonical_name = "NodeKind.IDENTIFIER"
NodeKind.RAWSTRING._fltk_canonical_name = "NodeKind.RAWSTRING"
NodeKind.LITERAL._fltk_canonical_name = "NodeKind.LITERAL"
NodeKind.TRIVIA._fltk_canonical_name = "NodeKind.TRIVIA"
NodeKind.WHITESPACE._fltk_canonical_name = "NodeKind.WHITESPACE"
NodeKind.LINECOMMENT._fltk_canonical_name = "NodeKind.LINECOMMENT"
NodeKind.BLOCKCOMMENT._fltk_canonical_name = "NodeKind.BLOCKCOMMENT"


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


class Grammar(typing.Protocol):
    class Label:
        RULE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.GRAMMAR] = NodeKind.GRAMMAR
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Rule]]

    def append(self, child: Rule, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Rule], label: Label | None = None) -> None: ...

    def extend_children(self, other: Grammar) -> None: ...

    def child(self) -> tuple[Label | None, Rule]: ...

    def append_rule(self, child: Rule) -> None: ...

    def extend_rule(self, children: typing.Iterable[Rule]) -> None: ...

    def children_rule(self) -> typing.Iterator[Rule]: ...

    def child_rule(self) -> Rule: ...

    def maybe_rule(self) -> Rule | None: ...


Grammar.Label.RULE = _ProtocolLabelMember("Grammar.Label.RULE")


class Rule(typing.Protocol):
    class Label:
        ALTERNATIVES: typing.ClassVar[object]
        NAME: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.RULE] = NodeKind.RULE
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Alternatives | Identifier | Trivia]]

    def append(self, child: Alternatives | Identifier | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Alternatives | Identifier | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Rule) -> None: ...

    def child(self) -> tuple[Label | None, Alternatives | Identifier | Trivia]: ...

    def append_alternatives(self, child: Alternatives) -> None: ...

    def extend_alternatives(self, children: typing.Iterable[Alternatives]) -> None: ...

    def children_alternatives(self) -> typing.Iterator[Alternatives]: ...

    def child_alternatives(self) -> Alternatives: ...

    def maybe_alternatives(self) -> Alternatives | None: ...

    def append_name(self, child: Identifier) -> None: ...

    def extend_name(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_name(self) -> typing.Iterator[Identifier]: ...

    def child_name(self) -> Identifier: ...

    def maybe_name(self) -> Identifier | None: ...


Rule.Label.ALTERNATIVES = _ProtocolLabelMember("Rule.Label.ALTERNATIVES")
Rule.Label.NAME = _ProtocolLabelMember("Rule.Label.NAME")


class Alternatives(typing.Protocol):
    class Label:
        ITEMS: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ALTERNATIVES] = NodeKind.ALTERNATIVES
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Items | Trivia]]

    def append(self, child: Items | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Items | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: Alternatives) -> None: ...

    def child(self) -> tuple[Label | None, Items | Trivia]: ...

    def append_items(self, child: Items) -> None: ...

    def extend_items(self, children: typing.Iterable[Items]) -> None: ...

    def children_items(self) -> typing.Iterator[Items]: ...

    def child_items(self) -> Items: ...

    def maybe_items(self) -> Items | None: ...


Alternatives.Label.ITEMS = _ProtocolLabelMember("Alternatives.Label.ITEMS")


class Items(typing.Protocol):
    class Label:
        ITEM: typing.ClassVar[object]
        NO_WS: typing.ClassVar[object]
        WS: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ITEMS] = NodeKind.ITEMS
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.span.Span]]

    def append(self, child: Item | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Item | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Items) -> None: ...

    def child(self) -> tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.span.Span]: ...

    def append_item(self, child: Item) -> None: ...

    def extend_item(self, children: typing.Iterable[Item]) -> None: ...

    def children_item(self) -> typing.Iterator[Item]: ...

    def child_item(self) -> Item: ...

    def maybe_item(self) -> Item | None: ...

    def append_no_ws(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_no_ws(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_no_ws(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_no_ws(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_no_ws(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_ws(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_ws(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_ws(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_ws(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_ws(self) -> fltk.fegen.pyrt.span.Span | None: ...


Items.Label.ITEM = _ProtocolLabelMember("Items.Label.ITEM")
Items.Label.NO_WS = _ProtocolLabelMember("Items.Label.NO_WS")
Items.Label.WS = _ProtocolLabelMember("Items.Label.WS")


class Item(typing.Protocol):
    class Label:
        DISPOSITION: typing.ClassVar[object]
        LABEL: typing.ClassVar[object]
        QUANTIFIER: typing.ClassVar[object]
        TERM: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ITEM] = NodeKind.ITEM
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]]

    def append(
        self, child: Disposition | Identifier | Quantifier | Term | Trivia, label: Label | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Disposition | Identifier | Quantifier | Term | Trivia],
        label: Label | None = None,
    ) -> None: ...

    def extend_children(self, other: Item) -> None: ...

    def child(self) -> tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]: ...

    def append_disposition(self, child: Disposition) -> None: ...

    def extend_disposition(self, children: typing.Iterable[Disposition]) -> None: ...

    def children_disposition(self) -> typing.Iterator[Disposition]: ...

    def child_disposition(self) -> Disposition: ...

    def maybe_disposition(self) -> Disposition | None: ...

    def append_label(self, child: Identifier) -> None: ...

    def extend_label(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_label(self) -> typing.Iterator[Identifier]: ...

    def child_label(self) -> Identifier: ...

    def maybe_label(self) -> Identifier | None: ...

    def append_quantifier(self, child: Quantifier) -> None: ...

    def extend_quantifier(self, children: typing.Iterable[Quantifier]) -> None: ...

    def children_quantifier(self) -> typing.Iterator[Quantifier]: ...

    def child_quantifier(self) -> Quantifier: ...

    def maybe_quantifier(self) -> Quantifier | None: ...

    def append_term(self, child: Term) -> None: ...

    def extend_term(self, children: typing.Iterable[Term]) -> None: ...

    def children_term(self) -> typing.Iterator[Term]: ...

    def child_term(self) -> Term: ...

    def maybe_term(self) -> Term | None: ...


Item.Label.DISPOSITION = _ProtocolLabelMember("Item.Label.DISPOSITION")
Item.Label.LABEL = _ProtocolLabelMember("Item.Label.LABEL")
Item.Label.QUANTIFIER = _ProtocolLabelMember("Item.Label.QUANTIFIER")
Item.Label.TERM = _ProtocolLabelMember("Item.Label.TERM")


class Term(typing.Protocol):
    class Label:
        ALTERNATIVES: typing.ClassVar[object]
        IDENTIFIER: typing.ClassVar[object]
        LITERAL: typing.ClassVar[object]
        REGEX: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TERM] = NodeKind.TERM
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]]

    def append(
        self, child: Alternatives | Identifier | Literal | RawString | Trivia, label: Label | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Alternatives | Identifier | Literal | RawString | Trivia],
        label: Label | None = None,
    ) -> None: ...

    def extend_children(self, other: Term) -> None: ...

    def child(self) -> tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]: ...

    def append_alternatives(self, child: Alternatives) -> None: ...

    def extend_alternatives(self, children: typing.Iterable[Alternatives]) -> None: ...

    def children_alternatives(self) -> typing.Iterator[Alternatives]: ...

    def child_alternatives(self) -> Alternatives: ...

    def maybe_alternatives(self) -> Alternatives | None: ...

    def append_identifier(self, child: Identifier) -> None: ...

    def extend_identifier(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_identifier(self) -> typing.Iterator[Identifier]: ...

    def child_identifier(self) -> Identifier: ...

    def maybe_identifier(self) -> Identifier | None: ...

    def append_literal(self, child: Literal) -> None: ...

    def extend_literal(self, children: typing.Iterable[Literal]) -> None: ...

    def children_literal(self) -> typing.Iterator[Literal]: ...

    def child_literal(self) -> Literal: ...

    def maybe_literal(self) -> Literal | None: ...

    def append_regex(self, child: RawString) -> None: ...

    def extend_regex(self, children: typing.Iterable[RawString]) -> None: ...

    def children_regex(self) -> typing.Iterator[RawString]: ...

    def child_regex(self) -> RawString: ...

    def maybe_regex(self) -> RawString | None: ...


Term.Label.ALTERNATIVES = _ProtocolLabelMember("Term.Label.ALTERNATIVES")
Term.Label.IDENTIFIER = _ProtocolLabelMember("Term.Label.IDENTIFIER")
Term.Label.LITERAL = _ProtocolLabelMember("Term.Label.LITERAL")
Term.Label.REGEX = _ProtocolLabelMember("Term.Label.REGEX")


class Disposition(typing.Protocol):
    class Label:
        INCLUDE: typing.ClassVar[object]
        INLINE: typing.ClassVar[object]
        SUPPRESS: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.DISPOSITION] = NodeKind.DISPOSITION
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Disposition) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_include(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_include(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_include(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_include(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_include(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_inline(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_inline(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_inline(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_inline(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_inline(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_suppress(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_suppress(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_suppress(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_suppress(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_suppress(self) -> fltk.fegen.pyrt.span.Span | None: ...


Disposition.Label.INCLUDE = _ProtocolLabelMember("Disposition.Label.INCLUDE")
Disposition.Label.INLINE = _ProtocolLabelMember("Disposition.Label.INLINE")
Disposition.Label.SUPPRESS = _ProtocolLabelMember("Disposition.Label.SUPPRESS")


class Quantifier(typing.Protocol):
    class Label:
        ONE_OR_MORE: typing.ClassVar[object]
        OPTIONAL: typing.ClassVar[object]
        ZERO_OR_MORE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.QUANTIFIER] = NodeKind.QUANTIFIER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Quantifier) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_one_or_more(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_one_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_one_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_one_or_more(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_one_or_more(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_optional(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_optional(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_optional(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_optional(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_optional(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_zero_or_more(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_zero_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_zero_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_zero_or_more(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_zero_or_more(self) -> fltk.fegen.pyrt.span.Span | None: ...


Quantifier.Label.ONE_OR_MORE = _ProtocolLabelMember("Quantifier.Label.ONE_OR_MORE")
Quantifier.Label.OPTIONAL = _ProtocolLabelMember("Quantifier.Label.OPTIONAL")
Quantifier.Label.ZERO_OR_MORE = _ProtocolLabelMember("Quantifier.Label.ZERO_OR_MORE")


class Identifier(typing.Protocol):
    class Label:
        NAME: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.IDENTIFIER] = NodeKind.IDENTIFIER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Identifier) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_name(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_name(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_name(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_name(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_name(self) -> fltk.fegen.pyrt.span.Span | None: ...


Identifier.Label.NAME = _ProtocolLabelMember("Identifier.Label.NAME")


class RawString(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.RAWSTRING] = NodeKind.RAWSTRING
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: RawString) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_value(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_value(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span.Span | None: ...


RawString.Label.VALUE = _ProtocolLabelMember("RawString.Label.VALUE")


class Literal(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LITERAL] = NodeKind.LITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Literal) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_value(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_value(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span.Span | None: ...


Literal.Label.VALUE = _ProtocolLabelMember("Literal.Label.VALUE")


class Trivia(typing.Protocol):
    class Label:
        BLOCK_COMMENT: typing.ClassVar[object]
        LINE_COMMENT: typing.ClassVar[object]
        WHITESPACE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, BlockComment | LineComment | Whitespace]]

    def append(self, child: BlockComment | LineComment | Whitespace, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[BlockComment | LineComment | Whitespace], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Trivia) -> None: ...

    def child(self) -> tuple[Label | None, BlockComment | LineComment | Whitespace]: ...

    def append_block_comment(self, child: BlockComment) -> None: ...

    def extend_block_comment(self, children: typing.Iterable[BlockComment]) -> None: ...

    def children_block_comment(self) -> typing.Iterator[BlockComment]: ...

    def child_block_comment(self) -> BlockComment: ...

    def maybe_block_comment(self) -> BlockComment | None: ...

    def append_line_comment(self, child: LineComment) -> None: ...

    def extend_line_comment(self, children: typing.Iterable[LineComment]) -> None: ...

    def children_line_comment(self) -> typing.Iterator[LineComment]: ...

    def child_line_comment(self) -> LineComment: ...

    def maybe_line_comment(self) -> LineComment | None: ...

    def append_whitespace(self, child: Whitespace) -> None: ...

    def extend_whitespace(self, children: typing.Iterable[Whitespace]) -> None: ...

    def children_whitespace(self) -> typing.Iterator[Whitespace]: ...

    def child_whitespace(self) -> Whitespace: ...

    def maybe_whitespace(self) -> Whitespace | None: ...


Trivia.Label.BLOCK_COMMENT = _ProtocolLabelMember("Trivia.Label.BLOCK_COMMENT")
Trivia.Label.LINE_COMMENT = _ProtocolLabelMember("Trivia.Label.LINE_COMMENT")
Trivia.Label.WHITESPACE = _ProtocolLabelMember("Trivia.Label.WHITESPACE")


class Whitespace(typing.Protocol):
    class Label:
        CONTENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.WHITESPACE] = NodeKind.WHITESPACE
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Whitespace) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_content(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_content(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_content(self) -> fltk.fegen.pyrt.span.Span | None: ...


Whitespace.Label.CONTENT = _ProtocolLabelMember("Whitespace.Label.CONTENT")


class LineComment(typing.Protocol):
    class Label:
        CONTENT: typing.ClassVar[object]
        NEWLINE: typing.ClassVar[object]
        PREFIX: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LINECOMMENT] = NodeKind.LINECOMMENT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: LineComment) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_content(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_content(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_content(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_newline(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_newline(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_newline(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_newline(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_newline(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_prefix(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_prefix(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_prefix(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_prefix(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_prefix(self) -> fltk.fegen.pyrt.span.Span | None: ...


LineComment.Label.CONTENT = _ProtocolLabelMember("LineComment.Label.CONTENT")
LineComment.Label.NEWLINE = _ProtocolLabelMember("LineComment.Label.NEWLINE")
LineComment.Label.PREFIX = _ProtocolLabelMember("LineComment.Label.PREFIX")


class BlockComment(typing.Protocol):
    class Label:
        CONTENT: typing.ClassVar[object]
        END: typing.ClassVar[object]
        START: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.BLOCKCOMMENT] = NodeKind.BLOCKCOMMENT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: BlockComment) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_content(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_content(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_content(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_end(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_end(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_end(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_end(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_end(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_start(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_start(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_start(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_start(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_start(self) -> fltk.fegen.pyrt.span.Span | None: ...


BlockComment.Label.CONTENT = _ProtocolLabelMember("BlockComment.Label.CONTENT")
BlockComment.Label.END = _ProtocolLabelMember("BlockComment.Label.END")
BlockComment.Label.START = _ProtocolLabelMember("BlockComment.Label.START")


class Span(typing.Protocol):
    kind: typing.Literal[fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN] = fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN


class CstModule(typing.Protocol):
    @property
    def Grammar(self) -> type[Grammar]: ...

    @property
    def Rule(self) -> type[Rule]: ...

    @property
    def Alternatives(self) -> type[Alternatives]: ...

    @property
    def Items(self) -> type[Items]: ...

    @property
    def Item(self) -> type[Item]: ...

    @property
    def Term(self) -> type[Term]: ...

    @property
    def Disposition(self) -> type[Disposition]: ...

    @property
    def Quantifier(self) -> type[Quantifier]: ...

    @property
    def Identifier(self) -> type[Identifier]: ...

    @property
    def RawString(self) -> type[RawString]: ...

    @property
    def Literal(self) -> type[Literal]: ...

    @property
    def Trivia(self) -> type[Trivia]: ...

    @property
    def Whitespace(self) -> type[Whitespace]: ...

    @property
    def LineComment(self) -> type[LineComment]: ...

    @property
    def BlockComment(self) -> type[BlockComment]: ...

    @property
    def Span(self) -> type[Span]: ...
