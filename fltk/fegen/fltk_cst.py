from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.span_protocol


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
NodeKind.LINECOMMENT._fltk_canonical_name = "NodeKind.LINECOMMENT"
NodeKind.BLOCKCOMMENT._fltk_canonical_name = "NodeKind.BLOCKCOMMENT"


def _get_native_span_type():
    m = sys.modules.get("fltk._native")
    return m.Span if m is not None else None


@dataclasses.dataclass
class Grammar:
    class Label(enum.Enum):
        RULE = enum.auto()
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

    kind: typing.Literal[NodeKind.GRAMMAR] = NodeKind.GRAMMAR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Rule | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Rule | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Rule | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Grammar) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Rule | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Rule | Trivia) -> None:
        if not isinstance(child, Rule | Trivia):
            msg = f"Grammar: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Grammar.Label)):
            _cn = "Grammar"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Rule | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Rule | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Grammar.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Rule | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Grammar.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_rule(self, child: Rule) -> None:
        self.children.append((Grammar.Label.RULE, child))

    def extend_rule(self, children: typing.Iterable[Rule]) -> None:
        self.children.extend((Grammar.Label.RULE, child) for child in children)

    def children_rule(self) -> typing.Iterator[Rule]:
        return (typing.cast("Rule", child) for (label, child) in self.children if label == Grammar.Label.RULE)

    def child_rule(self) -> Rule:
        children = list(self.children_rule())
        if (n := len(children)) != 1:
            msg = f"Expected one rule child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule(self) -> Rule | None:
        children = list(self.children_rule())
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def rule(self) -> list[Rule]:
        return list(self.children_rule())


Grammar.Label.RULE._fltk_canonical_name = "Grammar.Label.RULE"


@dataclasses.dataclass
class Rule:
    class Label(enum.Enum):
        ALTERNATIVES = enum.auto()
        NAME = enum.auto()
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

    kind: typing.Literal[NodeKind.RULE] = NodeKind.RULE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternatives | Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Alternatives | Identifier | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Alternatives | Identifier | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Rule) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternatives | Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Alternatives | Identifier | Trivia) -> None:
        if not isinstance(child, Alternatives | Identifier | Trivia):
            msg = f"Rule: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Rule.Label)):
            _cn = "Rule"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Alternatives | Identifier | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Alternatives | Identifier | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Rule.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Alternatives | Identifier | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Rule.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_alternatives(self, child: Alternatives) -> None:
        self.children.append((Rule.Label.ALTERNATIVES, child))

    def extend_alternatives(self, children: typing.Iterable[Alternatives]) -> None:
        self.children.extend((Rule.Label.ALTERNATIVES, child) for child in children)

    def children_alternatives(self) -> typing.Iterator[Alternatives]:
        return (
            typing.cast("Alternatives", child) for (label, child) in self.children if label == Rule.Label.ALTERNATIVES
        )

    def child_alternatives(self) -> Alternatives:
        children = list(self.children_alternatives())
        if (n := len(children)) != 1:
            msg = f"Expected one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_alternatives(self) -> Alternatives | None:
        children = list(self.children_alternatives())
        if (n := len(children)) > 1:
            msg = f"Expected at most one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_name(self, child: Identifier) -> None:
        self.children.append((Rule.Label.NAME, child))

    def extend_name(self, children: typing.Iterable[Identifier]) -> None:
        self.children.extend((Rule.Label.NAME, child) for child in children)

    def children_name(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == Rule.Label.NAME)

    def child_name(self) -> Identifier:
        children = list(self.children_name())
        if (n := len(children)) != 1:
            msg = f"Expected one name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name(self) -> Identifier | None:
        children = list(self.children_name())
        if (n := len(children)) > 1:
            msg = f"Expected at most one name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def alternatives(self) -> Alternatives:
        return self.child_alternatives()

    def name(self) -> Identifier:
        return self.child_name()


Rule.Label.ALTERNATIVES._fltk_canonical_name = "Rule.Label.ALTERNATIVES"
Rule.Label.NAME._fltk_canonical_name = "Rule.Label.NAME"


@dataclasses.dataclass
class Alternatives:
    class Label(enum.Enum):
        ITEMS = enum.auto()
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

    kind: typing.Literal[NodeKind.ALTERNATIVES] = NodeKind.ALTERNATIVES
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Items | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Items | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Items | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Alternatives) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Items | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Items | Trivia) -> None:
        if not isinstance(child, Items | Trivia):
            msg = f"Alternatives: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Alternatives.Label)):
            _cn = "Alternatives"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Items | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Items | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Alternatives.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Items | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Alternatives.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_items(self, child: Items) -> None:
        self.children.append((Alternatives.Label.ITEMS, child))

    def extend_items(self, children: typing.Iterable[Items]) -> None:
        self.children.extend((Alternatives.Label.ITEMS, child) for child in children)

    def children_items(self) -> typing.Iterator[Items]:
        return (typing.cast("Items", child) for (label, child) in self.children if label == Alternatives.Label.ITEMS)

    def child_items(self) -> Items:
        children = list(self.children_items())
        if (n := len(children)) != 1:
            msg = f"Expected one items child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_items(self) -> Items | None:
        children = list(self.children_items())
        if (n := len(children)) > 1:
            msg = f"Expected at most one items child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def items(self) -> list[Items]:
        return list(self.children_items())


Alternatives.Label.ITEMS._fltk_canonical_name = "Alternatives.Label.ITEMS"


@dataclasses.dataclass
class Items:
    class Label(enum.Enum):
        ITEM = enum.auto()
        NO_WS = enum.auto()
        WS_ALLOWED = enum.auto()
        WS_REQUIRED = enum.auto()
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

    kind: typing.Literal[NodeKind.ITEMS] = NodeKind.ITEMS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self, child: Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Items) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Items._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (Item, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            Items._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Items._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Items._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Items: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Items.Label)):
            _cn = "Items"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Items.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Items.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_item(self, child: Item) -> None:
        self.children.append((Items.Label.ITEM, child))

    def extend_item(self, children: typing.Iterable[Item]) -> None:
        self.children.extend((Items.Label.ITEM, child) for child in children)

    def children_item(self) -> typing.Iterator[Item]:
        return (typing.cast("Item", child) for (label, child) in self.children if label == Items.Label.ITEM)

    def child_item(self) -> Item:
        children = list(self.children_item())
        if (n := len(children)) != 1:
            msg = f"Expected one item child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_item(self) -> Item | None:
        children = list(self.children_item())
        if (n := len(children)) > 1:
            msg = f"Expected at most one item child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_no_ws(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Items.Label.NO_WS, child))

    def extend_no_ws(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Items.Label.NO_WS, child) for child in children)

    def children_no_ws(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Items.Label.NO_WS
        )

    def child_no_ws(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_no_ws())
        if (n := len(children)) != 1:
            msg = f"Expected one no_ws child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_no_ws(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_no_ws())
        if (n := len(children)) > 1:
            msg = f"Expected at most one no_ws child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_allowed(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Items.Label.WS_ALLOWED, child))

    def extend_ws_allowed(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Items.Label.WS_ALLOWED, child) for child in children)

    def children_ws_allowed(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Items.Label.WS_ALLOWED
        )

    def child_ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_ws_allowed())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_ws_allowed())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_required(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Items.Label.WS_REQUIRED, child))

    def extend_ws_required(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Items.Label.WS_REQUIRED, child) for child in children)

    def children_ws_required(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Items.Label.WS_REQUIRED
        )

    def child_ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_ws_required())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_ws_required())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def item(self) -> list[Item]:
        return list(self.children_item())

    def no_ws(self) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return list(self.children_no_ws())

    def ws_allowed(self) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return list(self.children_ws_allowed())

    def ws_required(self) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return list(self.children_ws_required())


Items.Label.ITEM._fltk_canonical_name = "Items.Label.ITEM"
Items.Label.NO_WS._fltk_canonical_name = "Items.Label.NO_WS"
Items.Label.WS_ALLOWED._fltk_canonical_name = "Items.Label.WS_ALLOWED"
Items.Label.WS_REQUIRED._fltk_canonical_name = "Items.Label.WS_REQUIRED"


@dataclasses.dataclass
class Item:
    class Label(enum.Enum):
        DISPOSITION = enum.auto()
        LABEL = enum.auto()
        QUANTIFIER = enum.auto()
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

    kind: typing.Literal[NodeKind.ITEM] = NodeKind.ITEM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Disposition | Identifier | Quantifier | Term | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[Disposition | Identifier | Quantifier | Term | Trivia],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Item) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Disposition | Identifier | Quantifier | Term | Trivia) -> None:
        if not isinstance(child, Disposition | Identifier | Quantifier | Term | Trivia):
            msg = f"Item: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Item.Label)):
            _cn = "Item"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: Disposition | Identifier | Quantifier | Term | Trivia, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Item.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Disposition | Identifier | Quantifier | Term | Trivia, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Item.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_disposition(self, child: Disposition) -> None:
        self.children.append((Item.Label.DISPOSITION, child))

    def extend_disposition(self, children: typing.Iterable[Disposition]) -> None:
        self.children.extend((Item.Label.DISPOSITION, child) for child in children)

    def children_disposition(self) -> typing.Iterator[Disposition]:
        return (
            typing.cast("Disposition", child) for (label, child) in self.children if label == Item.Label.DISPOSITION
        )

    def child_disposition(self) -> Disposition:
        children = list(self.children_disposition())
        if (n := len(children)) != 1:
            msg = f"Expected one disposition child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_disposition(self) -> Disposition | None:
        children = list(self.children_disposition())
        if (n := len(children)) > 1:
            msg = f"Expected at most one disposition child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_label(self, child: Identifier) -> None:
        self.children.append((Item.Label.LABEL, child))

    def extend_label(self, children: typing.Iterable[Identifier]) -> None:
        self.children.extend((Item.Label.LABEL, child) for child in children)

    def children_label(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == Item.Label.LABEL)

    def child_label(self) -> Identifier:
        children = list(self.children_label())
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> Identifier | None:
        children = list(self.children_label())
        if (n := len(children)) > 1:
            msg = f"Expected at most one label child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_quantifier(self, child: Quantifier) -> None:
        self.children.append((Item.Label.QUANTIFIER, child))

    def extend_quantifier(self, children: typing.Iterable[Quantifier]) -> None:
        self.children.extend((Item.Label.QUANTIFIER, child) for child in children)

    def children_quantifier(self) -> typing.Iterator[Quantifier]:
        return (typing.cast("Quantifier", child) for (label, child) in self.children if label == Item.Label.QUANTIFIER)

    def child_quantifier(self) -> Quantifier:
        children = list(self.children_quantifier())
        if (n := len(children)) != 1:
            msg = f"Expected one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_quantifier(self) -> Quantifier | None:
        children = list(self.children_quantifier())
        if (n := len(children)) > 1:
            msg = f"Expected at most one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_term(self, child: Term) -> None:
        self.children.append((Item.Label.TERM, child))

    def extend_term(self, children: typing.Iterable[Term]) -> None:
        self.children.extend((Item.Label.TERM, child) for child in children)

    def children_term(self) -> typing.Iterator[Term]:
        return (typing.cast("Term", child) for (label, child) in self.children if label == Item.Label.TERM)

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

    def disposition(self) -> Disposition | None:
        return self.maybe_disposition()

    def label(self) -> Identifier | None:
        return self.maybe_label()

    def quantifier(self) -> Quantifier | None:
        return self.maybe_quantifier()

    def term(self) -> Term:
        return self.child_term()


Item.Label.DISPOSITION._fltk_canonical_name = "Item.Label.DISPOSITION"
Item.Label.LABEL._fltk_canonical_name = "Item.Label.LABEL"
Item.Label.QUANTIFIER._fltk_canonical_name = "Item.Label.QUANTIFIER"
Item.Label.TERM._fltk_canonical_name = "Item.Label.TERM"


@dataclasses.dataclass
class Term:
    class Label(enum.Enum):
        ALTERNATIVES = enum.auto()
        IDENTIFIER = enum.auto()
        LITERAL = enum.auto()
        REGEX = enum.auto()
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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self, child: Alternatives | Identifier | Literal | RawString | Trivia, label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[Alternatives | Identifier | Literal | RawString | Trivia],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Term) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Alternatives | Identifier | Literal | RawString | Trivia) -> None:
        if not isinstance(child, Alternatives | Identifier | Literal | RawString | Trivia):
            msg = f"Term: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Term.Label)):
            _cn = "Term"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: Alternatives | Identifier | Literal | RawString | Trivia, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Term.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Alternatives | Identifier | Literal | RawString | Trivia, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Term.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_alternatives(self, child: Alternatives) -> None:
        self.children.append((Term.Label.ALTERNATIVES, child))

    def extend_alternatives(self, children: typing.Iterable[Alternatives]) -> None:
        self.children.extend((Term.Label.ALTERNATIVES, child) for child in children)

    def children_alternatives(self) -> typing.Iterator[Alternatives]:
        return (
            typing.cast("Alternatives", child) for (label, child) in self.children if label == Term.Label.ALTERNATIVES
        )

    def child_alternatives(self) -> Alternatives:
        children = list(self.children_alternatives())
        if (n := len(children)) != 1:
            msg = f"Expected one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_alternatives(self) -> Alternatives | None:
        children = list(self.children_alternatives())
        if (n := len(children)) > 1:
            msg = f"Expected at most one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_identifier(self, child: Identifier) -> None:
        self.children.append((Term.Label.IDENTIFIER, child))

    def extend_identifier(self, children: typing.Iterable[Identifier]) -> None:
        self.children.extend((Term.Label.IDENTIFIER, child) for child in children)

    def children_identifier(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == Term.Label.IDENTIFIER)

    def child_identifier(self) -> Identifier:
        children = list(self.children_identifier())
        if (n := len(children)) != 1:
            msg = f"Expected one identifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_identifier(self) -> Identifier | None:
        children = list(self.children_identifier())
        if (n := len(children)) > 1:
            msg = f"Expected at most one identifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_literal(self, child: Literal) -> None:
        self.children.append((Term.Label.LITERAL, child))

    def extend_literal(self, children: typing.Iterable[Literal]) -> None:
        self.children.extend((Term.Label.LITERAL, child) for child in children)

    def children_literal(self) -> typing.Iterator[Literal]:
        return (typing.cast("Literal", child) for (label, child) in self.children if label == Term.Label.LITERAL)

    def child_literal(self) -> Literal:
        children = list(self.children_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_literal(self) -> Literal | None:
        children = list(self.children_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_regex(self, child: RawString) -> None:
        self.children.append((Term.Label.REGEX, child))

    def extend_regex(self, children: typing.Iterable[RawString]) -> None:
        self.children.extend((Term.Label.REGEX, child) for child in children)

    def children_regex(self) -> typing.Iterator[RawString]:
        return (typing.cast("RawString", child) for (label, child) in self.children if label == Term.Label.REGEX)

    def child_regex(self) -> RawString:
        children = list(self.children_regex())
        if (n := len(children)) != 1:
            msg = f"Expected one regex child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_regex(self) -> RawString | None:
        children = list(self.children_regex())
        if (n := len(children)) > 1:
            msg = f"Expected at most one regex child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def alternatives(self) -> Alternatives | None:
        return self.maybe_alternatives()

    def identifier(self) -> Identifier | None:
        return self.maybe_identifier()

    def literal(self) -> Literal | None:
        return self.maybe_literal()

    def regex(self) -> RawString | None:
        return self.maybe_regex()


Term.Label.ALTERNATIVES._fltk_canonical_name = "Term.Label.ALTERNATIVES"
Term.Label.IDENTIFIER._fltk_canonical_name = "Term.Label.IDENTIFIER"
Term.Label.LITERAL._fltk_canonical_name = "Term.Label.LITERAL"
Term.Label.REGEX._fltk_canonical_name = "Term.Label.REGEX"


@dataclasses.dataclass
class Disposition:
    class Label(enum.Enum):
        INCLUDE = enum.auto()
        INLINE = enum.auto()
        SUPPRESS = enum.auto()
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

    kind: typing.Literal[NodeKind.DISPOSITION] = NodeKind.DISPOSITION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Disposition) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Disposition._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Disposition._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Disposition._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Disposition._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Disposition: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Disposition.Label)):
            _cn = "Disposition"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Disposition.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Disposition.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_include(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Disposition.Label.INCLUDE, child))

    def extend_include(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Disposition.Label.INCLUDE, child) for child in children)

    def children_include(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Disposition.Label.INCLUDE)

    def child_include(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_include())
        if (n := len(children)) != 1:
            msg = f"Expected one include child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_include(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_include())
        if (n := len(children)) > 1:
            msg = f"Expected at most one include child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_inline(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Disposition.Label.INLINE, child))

    def extend_inline(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Disposition.Label.INLINE, child) for child in children)

    def children_inline(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Disposition.Label.INLINE)

    def child_inline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_inline())
        if (n := len(children)) != 1:
            msg = f"Expected one inline child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_inline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_inline())
        if (n := len(children)) > 1:
            msg = f"Expected at most one inline child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_suppress(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Disposition.Label.SUPPRESS, child))

    def extend_suppress(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Disposition.Label.SUPPRESS, child) for child in children)

    def children_suppress(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Disposition.Label.SUPPRESS)

    def child_suppress(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_suppress())
        if (n := len(children)) != 1:
            msg = f"Expected one suppress child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_suppress(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_suppress())
        if (n := len(children)) > 1:
            msg = f"Expected at most one suppress child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def include(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_include()

    def include_text(self) -> str | None:
        child = self.maybe_include()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Disposition.include_text: child labelled 'include' is not a Span"
            raise TypeError(msg) from None

    def inline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_inline()

    def inline_text(self) -> str | None:
        child = self.maybe_inline()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Disposition.inline_text: child labelled 'inline' is not a Span"
            raise TypeError(msg) from None

    def suppress(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_suppress()

    def suppress_text(self) -> str | None:
        child = self.maybe_suppress()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Disposition.suppress_text: child labelled 'suppress' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Disposition.variant: node has no labeled child"
        raise ValueError(msg)


Disposition.Label.INCLUDE._fltk_canonical_name = "Disposition.Label.INCLUDE"
Disposition.Label.INLINE._fltk_canonical_name = "Disposition.Label.INLINE"
Disposition.Label.SUPPRESS._fltk_canonical_name = "Disposition.Label.SUPPRESS"


@dataclasses.dataclass
class Quantifier:
    class Label(enum.Enum):
        ONE_OR_MORE = enum.auto()
        OPTIONAL = enum.auto()
        ZERO_OR_MORE = enum.auto()
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

    kind: typing.Literal[NodeKind.QUANTIFIER] = NodeKind.QUANTIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Quantifier) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Quantifier._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Quantifier._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Quantifier._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Quantifier._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Quantifier: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Quantifier.Label)):
            _cn = "Quantifier"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Quantifier.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Quantifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_one_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.ONE_OR_MORE, child))

    def extend_one_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Quantifier.Label.ONE_OR_MORE, child) for child in children)

    def children_one_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Quantifier.Label.ONE_OR_MORE)

    def child_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_one_or_more())
        if (n := len(children)) != 1:
            msg = f"Expected one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_one_or_more())
        if (n := len(children)) > 1:
            msg = f"Expected at most one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_optional(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.OPTIONAL, child))

    def extend_optional(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Quantifier.Label.OPTIONAL, child) for child in children)

    def children_optional(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Quantifier.Label.OPTIONAL)

    def child_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_optional())
        if (n := len(children)) != 1:
            msg = f"Expected one optional child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_optional())
        if (n := len(children)) > 1:
            msg = f"Expected at most one optional child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_zero_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.ZERO_OR_MORE, child))

    def extend_zero_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Quantifier.Label.ZERO_OR_MORE, child) for child in children)

    def children_zero_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Quantifier.Label.ZERO_OR_MORE)

    def child_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_zero_or_more())
        if (n := len(children)) != 1:
            msg = f"Expected one zero_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_zero_or_more())
        if (n := len(children)) > 1:
            msg = f"Expected at most one zero_or_more child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_one_or_more()

    def one_or_more_text(self) -> str | None:
        child = self.maybe_one_or_more()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Quantifier.one_or_more_text: child labelled 'one_or_more' is not a Span"
            raise TypeError(msg) from None

    def optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_optional()

    def optional_text(self) -> str | None:
        child = self.maybe_optional()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Quantifier.optional_text: child labelled 'optional' is not a Span"
            raise TypeError(msg) from None

    def zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_zero_or_more()

    def zero_or_more_text(self) -> str | None:
        child = self.maybe_zero_or_more()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Quantifier.zero_or_more_text: child labelled 'zero_or_more' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Quantifier.variant: node has no labeled child"
        raise ValueError(msg)


Quantifier.Label.ONE_OR_MORE._fltk_canonical_name = "Quantifier.Label.ONE_OR_MORE"
Quantifier.Label.OPTIONAL._fltk_canonical_name = "Quantifier.Label.OPTIONAL"
Quantifier.Label.ZERO_OR_MORE._fltk_canonical_name = "Quantifier.Label.ZERO_OR_MORE"


@dataclasses.dataclass
class Identifier:
    class Label(enum.Enum):
        NAME = enum.auto()
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

    kind: typing.Literal[NodeKind.IDENTIFIER] = NodeKind.IDENTIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Identifier) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Identifier._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Identifier._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Identifier._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Identifier._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Identifier: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Identifier.Label)):
            _cn = "Identifier"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Identifier.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Identifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_name(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Identifier.Label.NAME, child))

    def extend_name(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Identifier.Label.NAME, child) for child in children)

    def children_name(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Identifier.Label.NAME)

    def child_name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_name())
        if (n := len(children)) != 1:
            msg = f"Expected one name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_name())
        if (n := len(children)) > 1:
            msg = f"Expected at most one name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_name()

    def name_text(self) -> str:
        child = self.child_name()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Identifier.name_text: child labelled 'name' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


Identifier.Label.NAME._fltk_canonical_name = "Identifier.Label.NAME"


@dataclasses.dataclass
class RawString:
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

    kind: typing.Literal[NodeKind.RAWSTRING] = NodeKind.RAWSTRING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: RawString) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = RawString._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            RawString._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            RawString._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = RawString._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"RawString: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, RawString.Label)):
            _cn = "RawString"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RawString.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RawString.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((RawString.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((RawString.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == RawString.Label.VALUE)

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_value()

    def value_text(self) -> str:
        child = self.child_value()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "RawString.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


RawString.Label.VALUE._fltk_canonical_name = "RawString.Label.VALUE"


@dataclasses.dataclass
class Literal:
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

    kind: typing.Literal[NodeKind.LITERAL] = NodeKind.LITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Literal) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Literal._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Literal._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Literal._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Literal._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Literal: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Literal.Label)):
            _cn = "Literal"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Literal.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Literal.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Literal.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Literal.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Literal.Label.VALUE)

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_value()

    def value_text(self) -> str:
        child = self.child_value()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Literal.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


Literal.Label.VALUE._fltk_canonical_name = "Literal.Label.VALUE"


@dataclasses.dataclass
class Trivia:
    class Label(enum.Enum):
        BLOCK_COMMENT = enum.auto()
        LINE_COMMENT = enum.auto()
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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, BlockComment | LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self, child: BlockComment | LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[BlockComment | LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Trivia) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, BlockComment | LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: BlockComment | LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
        _allowed = Trivia._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (BlockComment, LineComment, fltk.fegen.pyrt.terminalsrc.Span)
            Trivia._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Trivia._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Trivia._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Trivia: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Trivia.Label)):
            _cn = "Trivia"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: BlockComment | LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: Label | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(
        self, index: int
    ) -> tuple[Label | None, BlockComment | LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Trivia.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: BlockComment | LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: Label | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Trivia.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_block_comment(self, child: BlockComment) -> None:
        self.children.append((Trivia.Label.BLOCK_COMMENT, child))

    def extend_block_comment(self, children: typing.Iterable[BlockComment]) -> None:
        self.children.extend((Trivia.Label.BLOCK_COMMENT, child) for child in children)

    def children_block_comment(self) -> typing.Iterator[BlockComment]:
        return (
            typing.cast("BlockComment", child)
            for (label, child) in self.children
            if label == Trivia.Label.BLOCK_COMMENT
        )

    def child_block_comment(self) -> BlockComment:
        children = list(self.children_block_comment())
        if (n := len(children)) != 1:
            msg = f"Expected one block_comment child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_block_comment(self) -> BlockComment | None:
        children = list(self.children_block_comment())
        if (n := len(children)) > 1:
            msg = f"Expected at most one block_comment child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_line_comment(self, child: LineComment) -> None:
        self.children.append((Trivia.Label.LINE_COMMENT, child))

    def extend_line_comment(self, children: typing.Iterable[LineComment]) -> None:
        self.children.extend((Trivia.Label.LINE_COMMENT, child) for child in children)

    def children_line_comment(self) -> typing.Iterator[LineComment]:
        return (
            typing.cast("LineComment", child) for (label, child) in self.children if label == Trivia.Label.LINE_COMMENT
        )

    def child_line_comment(self) -> LineComment:
        children = list(self.children_line_comment())
        if (n := len(children)) != 1:
            msg = f"Expected one line_comment child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_line_comment(self) -> LineComment | None:
        children = list(self.children_line_comment())
        if (n := len(children)) > 1:
            msg = f"Expected at most one line_comment child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def block_comment(self) -> list[BlockComment]:
        return list(self.children_block_comment())

    def line_comment(self) -> list[LineComment]:
        return list(self.children_line_comment())


Trivia.Label.BLOCK_COMMENT._fltk_canonical_name = "Trivia.Label.BLOCK_COMMENT"
Trivia.Label.LINE_COMMENT._fltk_canonical_name = "Trivia.Label.LINE_COMMENT"


@dataclasses.dataclass
class LineComment:
    class Label(enum.Enum):
        CONTENT = enum.auto()
        PREFIX = enum.auto()
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

    kind: typing.Literal[NodeKind.LINECOMMENT] = NodeKind.LINECOMMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: LineComment) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = LineComment._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            LineComment._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            LineComment._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = LineComment._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"LineComment: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, LineComment.Label)):
            _cn = "LineComment"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LineComment.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LineComment.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((LineComment.Label.CONTENT, child))

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((LineComment.Label.CONTENT, child) for child in children)

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == LineComment.Label.CONTENT)

    def child_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_content())
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_content())
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_prefix(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((LineComment.Label.PREFIX, child))

    def extend_prefix(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((LineComment.Label.PREFIX, child) for child in children)

    def children_prefix(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == LineComment.Label.PREFIX)

    def child_prefix(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_prefix())
        if (n := len(children)) != 1:
            msg = f"Expected one prefix child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_prefix(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_prefix())
        if (n := len(children)) > 1:
            msg = f"Expected at most one prefix child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_content()

    def content_text(self) -> str:
        child = self.child_content()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "LineComment.content_text: child labelled 'content' is not a Span"
            raise TypeError(msg) from None

    def prefix(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_prefix()

    def prefix_text(self) -> str:
        child = self.child_prefix()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "LineComment.prefix_text: child labelled 'prefix' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


LineComment.Label.CONTENT._fltk_canonical_name = "LineComment.Label.CONTENT"
LineComment.Label.PREFIX._fltk_canonical_name = "LineComment.Label.PREFIX"


@dataclasses.dataclass
class BlockComment:
    class Label(enum.Enum):
        CONTENT = enum.auto()
        END = enum.auto()
        START = enum.auto()
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

    kind: typing.Literal[NodeKind.BLOCKCOMMENT] = NodeKind.BLOCKCOMMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: BlockComment) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = BlockComment._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            BlockComment._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            BlockComment._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = BlockComment._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"BlockComment: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, BlockComment.Label)):
            _cn = "BlockComment"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"BlockComment.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"BlockComment.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((BlockComment.Label.CONTENT, child))

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((BlockComment.Label.CONTENT, child) for child in children)

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == BlockComment.Label.CONTENT)

    def child_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_content())
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_content())
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_end(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((BlockComment.Label.END, child))

    def extend_end(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((BlockComment.Label.END, child) for child in children)

    def children_end(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == BlockComment.Label.END)

    def child_end(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_end())
        if (n := len(children)) != 1:
            msg = f"Expected one end child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_end(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_end())
        if (n := len(children)) > 1:
            msg = f"Expected at most one end child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_start(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((BlockComment.Label.START, child))

    def extend_start(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((BlockComment.Label.START, child) for child in children)

    def children_start(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == BlockComment.Label.START)

    def child_start(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_start())
        if (n := len(children)) != 1:
            msg = f"Expected one start child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_start(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_start())
        if (n := len(children)) > 1:
            msg = f"Expected at most one start child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_content()

    def content_text(self) -> str:
        child = self.child_content()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "BlockComment.content_text: child labelled 'content' is not a Span"
            raise TypeError(msg) from None

    def end(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_end()

    def end_text(self) -> str:
        child = self.child_end()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "BlockComment.end_text: child labelled 'end' is not a Span"
            raise TypeError(msg) from None

    def start(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_start()

    def start_text(self) -> str:
        child = self.child_start()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "BlockComment.start_text: child labelled 'start' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


BlockComment.Label.CONTENT._fltk_canonical_name = "BlockComment.Label.CONTENT"
BlockComment.Label.END._fltk_canonical_name = "BlockComment.Label.END"
BlockComment.Label.START._fltk_canonical_name = "BlockComment.Label.START"
