from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import types
import typing

import fltk.fegen.pyrt.terminalsrc
from fltk.fegen.bootstrap_cst_protocol import NodeKind

if typing.TYPE_CHECKING:
    import fltk.fegen.bootstrap_cst_protocol as _cstp
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol


def _get_native_span_type():
    m = sys.modules.get("fltk._native")
    return m.Span if m is not None else None


def _type_name_for_error(obj: object) -> str:
    t = type(obj)
    return f"{t.__module__}.{t.__qualname__}"


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Grammar.Label.RULE": Label.RULE})
    kind: typing.Literal[NodeKind.GRAMMAR] = NodeKind.GRAMMAR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Rule]] = dataclasses.field(default_factory=list)

    def append(self, child: _cstp.Rule, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Grammar.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self, children: typing.Iterable[_cstp.Rule], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Grammar.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Grammar) -> None:
        if not isinstance(other, Grammar):
            msg = f"Grammar: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Rule]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Rule) -> Rule:
        if isinstance(child, Rule):
            return child
        msg = f"Grammar: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Grammar.Label | None:
        if label is None or isinstance(label, Grammar.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Grammar._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Grammar"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.Rule, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Grammar.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, Rule]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Grammar.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.Rule, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Grammar.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Grammar.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Grammar.Label) -> list[Rule]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_rule(self, child: _cstp.Rule) -> None:
        self.children.append((Grammar.Label.RULE, self._check_child_type_for_mutators(child)))

    def extend_rule(self, children: typing.Iterable[_cstp.Rule]) -> None:
        self.children.extend([(Grammar.Label.RULE, self._check_child_type_for_mutators(child)) for child in children])

    def children_rule(self) -> typing.Iterator[Rule]:
        return iter(self._children_snapshot(Grammar.Label.RULE))

    def child_rule(self) -> Rule:
        children = self._children_snapshot(Grammar.Label.RULE)
        if (n := len(children)) != 1:
            msg = f"Expected one rule child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule(self) -> Rule | None:
        children = self._children_snapshot(Grammar.Label.RULE)
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def rule(self) -> list[Rule]:
        return self._children_snapshot(Grammar.Label.RULE)


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Rule.Label.ALTERNATIVES": Label.ALTERNATIVES, "Rule.Label.NAME": Label.NAME}
    )
    kind: typing.Literal[NodeKind.RULE] = NodeKind.RULE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternatives | Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Alternatives | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Rule.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Alternatives | _cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Rule.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Rule) -> None:
        if not isinstance(other, Rule):
            msg = f"Rule: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternatives | Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Alternatives | _cstp.Identifier | _cstp.Trivia
    ) -> Alternatives | Identifier | Trivia:
        if isinstance(child, Alternatives | Identifier | Trivia):
            return child
        msg = f"Rule: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Rule.Label | None:
        if label is None or isinstance(label, Rule.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Rule._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Rule"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Alternatives | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Rule.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, Alternatives | Identifier | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Rule.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Alternatives | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Rule.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Rule.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Rule.Label) -> list[Alternatives | Identifier | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_alternatives(self, child: _cstp.Alternatives) -> None:
        self.children.append((Rule.Label.ALTERNATIVES, self._check_child_type_for_mutators(child)))

    def extend_alternatives(self, children: typing.Iterable[_cstp.Alternatives]) -> None:
        self.children.extend(
            [(Rule.Label.ALTERNATIVES, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_alternatives(self) -> typing.Iterator[Alternatives]:
        return iter(typing.cast("list[Alternatives]", self._children_snapshot(Rule.Label.ALTERNATIVES)))

    def child_alternatives(self) -> Alternatives:
        children = typing.cast("list[Alternatives]", self._children_snapshot(Rule.Label.ALTERNATIVES))
        if (n := len(children)) != 1:
            msg = f"Expected one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_alternatives(self) -> Alternatives | None:
        children = typing.cast("list[Alternatives]", self._children_snapshot(Rule.Label.ALTERNATIVES))
        if (n := len(children)) > 1:
            msg = f"Expected at most one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_name(self, child: _cstp.Identifier) -> None:
        self.children.append((Rule.Label.NAME, self._check_child_type_for_mutators(child)))

    def extend_name(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend([(Rule.Label.NAME, self._check_child_type_for_mutators(child)) for child in children])

    def children_name(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(Rule.Label.NAME)))

    def child_name(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(Rule.Label.NAME))
        if (n := len(children)) != 1:
            msg = f"Expected one name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(Rule.Label.NAME))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Alternatives.Label.ITEMS": Label.ITEMS})
    kind: typing.Literal[NodeKind.ALTERNATIVES] = NodeKind.ALTERNATIVES
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Items | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Items | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Alternatives.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Items | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Alternatives.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Alternatives) -> None:
        if not isinstance(other, Alternatives):
            msg = f"Alternatives: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Items | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Items | _cstp.Trivia) -> Items | Trivia:
        if isinstance(child, Items | Trivia):
            return child
        msg = f"Alternatives: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Alternatives.Label | None:
        if label is None or isinstance(label, Alternatives.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Alternatives._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Alternatives"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Items | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Alternatives.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, Items | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Alternatives.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Items | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Alternatives.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Alternatives.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Alternatives.Label) -> list[Items | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_items(self, child: _cstp.Items) -> None:
        self.children.append((Alternatives.Label.ITEMS, self._check_child_type_for_mutators(child)))

    def extend_items(self, children: typing.Iterable[_cstp.Items]) -> None:
        self.children.extend(
            [(Alternatives.Label.ITEMS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_items(self) -> typing.Iterator[Items]:
        return iter(typing.cast("list[Items]", self._children_snapshot(Alternatives.Label.ITEMS)))

    def child_items(self) -> Items:
        children = typing.cast("list[Items]", self._children_snapshot(Alternatives.Label.ITEMS))
        if (n := len(children)) != 1:
            msg = f"Expected one items child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_items(self) -> Items | None:
        children = typing.cast("list[Items]", self._children_snapshot(Alternatives.Label.ITEMS))
        if (n := len(children)) > 1:
            msg = f"Expected at most one items child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def items(self) -> list[Items]:
        return typing.cast("list[Items]", self._children_snapshot(Alternatives.Label.ITEMS))


Alternatives.Label.ITEMS._fltk_canonical_name = "Alternatives.Label.ITEMS"


@dataclasses.dataclass
class Items:
    class Label(enum.Enum):
        ITEM = enum.auto()
        NO_WS = enum.auto()
        WS = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Items.Label.ITEM": Label.ITEM, "Items.Label.NO_WS": Label.NO_WS, "Items.Label.WS": Label.WS}
    )
    kind: typing.Literal[NodeKind.ITEMS] = NodeKind.ITEMS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.Item | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Items.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Item | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Items.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Items) -> None:
        if not isinstance(other, Items):
            msg = f"Items: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Item | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, Item | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Items: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Items.Label | None:
        if label is None or isinstance(label, Items.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Items._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Items"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Item | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Items.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Items.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Item | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Items.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Items.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: Items.Label
    ) -> list[Item | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_item(self, child: _cstp.Item) -> None:
        self.children.append((Items.Label.ITEM, self._check_child_type_for_mutators(child)))

    def extend_item(self, children: typing.Iterable[_cstp.Item]) -> None:
        self.children.extend([(Items.Label.ITEM, self._check_child_type_for_mutators(child)) for child in children])

    def children_item(self) -> typing.Iterator[Item]:
        return iter(typing.cast("list[Item]", self._children_snapshot(Items.Label.ITEM)))

    def child_item(self) -> Item:
        children = typing.cast("list[Item]", self._children_snapshot(Items.Label.ITEM))
        if (n := len(children)) != 1:
            msg = f"Expected one item child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_item(self) -> Item | None:
        children = typing.cast("list[Item]", self._children_snapshot(Items.Label.ITEM))
        if (n := len(children)) > 1:
            msg = f"Expected at most one item child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_no_ws(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Items.Label.NO_WS, self._check_child_type_for_mutators(child)))

    def extend_no_ws(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Items.Label.NO_WS, self._check_child_type_for_mutators(child)) for child in children])

    def children_no_ws(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Items.Label.NO_WS))
        )

    def child_no_ws(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Items.Label.NO_WS)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one no_ws child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_no_ws(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Items.Label.NO_WS)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one no_ws child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Items.Label.WS, self._check_child_type_for_mutators(child)))

    def extend_ws(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Items.Label.WS, self._check_child_type_for_mutators(child)) for child in children])

    def children_ws(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Items.Label.WS))
        )

    def child_ws(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Items.Label.WS)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one ws child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Items.Label.WS)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def item(self) -> list[Item]:
        return typing.cast("list[Item]", self._children_snapshot(Items.Label.ITEM))

    def no_ws(self) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Items.Label.NO_WS)
        )

    def ws(self) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Items.Label.WS))


Items.Label.ITEM._fltk_canonical_name = "Items.Label.ITEM"
Items.Label.NO_WS._fltk_canonical_name = "Items.Label.NO_WS"
Items.Label.WS._fltk_canonical_name = "Items.Label.WS"


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Item.Label.DISPOSITION": Label.DISPOSITION,
            "Item.Label.LABEL": Label.LABEL,
            "Item.Label.QUANTIFIER": Label.QUANTIFIER,
            "Item.Label.TERM": Label.TERM,
        }
    )
    kind: typing.Literal[NodeKind.ITEM] = NodeKind.ITEM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.Disposition | _cstp.Identifier | _cstp.Quantifier | _cstp.Term | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Item.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Disposition | _cstp.Identifier | _cstp.Quantifier | _cstp.Term | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Item.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Item) -> None:
        if not isinstance(other, Item):
            msg = f"Item: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Disposition | _cstp.Identifier | _cstp.Quantifier | _cstp.Term | _cstp.Trivia
    ) -> Disposition | Identifier | Quantifier | Term | Trivia:
        if isinstance(child, Disposition | Identifier | Quantifier | Term | Trivia):
            return child
        msg = f"Item: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Item.Label | None:
        if label is None or isinstance(label, Item.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Item._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Item"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Disposition | _cstp.Identifier | _cstp.Quantifier | _cstp.Term | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Item.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, Disposition | Identifier | Quantifier | Term | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Item.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Disposition | _cstp.Identifier | _cstp.Quantifier | _cstp.Term | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Item.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Item.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Item.Label) -> list[Disposition | Identifier | Quantifier | Term | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_disposition(self, child: _cstp.Disposition) -> None:
        self.children.append((Item.Label.DISPOSITION, self._check_child_type_for_mutators(child)))

    def extend_disposition(self, children: typing.Iterable[_cstp.Disposition]) -> None:
        self.children.extend(
            [(Item.Label.DISPOSITION, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_disposition(self) -> typing.Iterator[Disposition]:
        return iter(typing.cast("list[Disposition]", self._children_snapshot(Item.Label.DISPOSITION)))

    def child_disposition(self) -> Disposition:
        children = typing.cast("list[Disposition]", self._children_snapshot(Item.Label.DISPOSITION))
        if (n := len(children)) != 1:
            msg = f"Expected one disposition child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_disposition(self) -> Disposition | None:
        children = typing.cast("list[Disposition]", self._children_snapshot(Item.Label.DISPOSITION))
        if (n := len(children)) > 1:
            msg = f"Expected at most one disposition child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_label(self, child: _cstp.Identifier) -> None:
        self.children.append((Item.Label.LABEL, self._check_child_type_for_mutators(child)))

    def extend_label(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend([(Item.Label.LABEL, self._check_child_type_for_mutators(child)) for child in children])

    def children_label(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(Item.Label.LABEL)))

    def child_label(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(Item.Label.LABEL))
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(Item.Label.LABEL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one label child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_quantifier(self, child: _cstp.Quantifier) -> None:
        self.children.append((Item.Label.QUANTIFIER, self._check_child_type_for_mutators(child)))

    def extend_quantifier(self, children: typing.Iterable[_cstp.Quantifier]) -> None:
        self.children.extend(
            [(Item.Label.QUANTIFIER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_quantifier(self) -> typing.Iterator[Quantifier]:
        return iter(typing.cast("list[Quantifier]", self._children_snapshot(Item.Label.QUANTIFIER)))

    def child_quantifier(self) -> Quantifier:
        children = typing.cast("list[Quantifier]", self._children_snapshot(Item.Label.QUANTIFIER))
        if (n := len(children)) != 1:
            msg = f"Expected one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_quantifier(self) -> Quantifier | None:
        children = typing.cast("list[Quantifier]", self._children_snapshot(Item.Label.QUANTIFIER))
        if (n := len(children)) > 1:
            msg = f"Expected at most one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_term(self, child: _cstp.Term) -> None:
        self.children.append((Item.Label.TERM, self._check_child_type_for_mutators(child)))

    def extend_term(self, children: typing.Iterable[_cstp.Term]) -> None:
        self.children.extend([(Item.Label.TERM, self._check_child_type_for_mutators(child)) for child in children])

    def children_term(self) -> typing.Iterator[Term]:
        return iter(typing.cast("list[Term]", self._children_snapshot(Item.Label.TERM)))

    def child_term(self) -> Term:
        children = typing.cast("list[Term]", self._children_snapshot(Item.Label.TERM))
        if (n := len(children)) != 1:
            msg = f"Expected one term child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_term(self) -> Term | None:
        children = typing.cast("list[Term]", self._children_snapshot(Item.Label.TERM))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Term.Label.ALTERNATIVES": Label.ALTERNATIVES,
            "Term.Label.IDENTIFIER": Label.IDENTIFIER,
            "Term.Label.LITERAL": Label.LITERAL,
            "Term.Label.REGEX": Label.REGEX,
        }
    )
    kind: typing.Literal[NodeKind.TERM] = NodeKind.TERM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.Alternatives | _cstp.Identifier | _cstp.Literal | _cstp.RawString | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Term.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[
            _cstp.Alternatives | _cstp.Identifier | _cstp.Literal | _cstp.RawString | _cstp.Trivia
        ],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Term.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Term) -> None:
        if not isinstance(other, Term):
            msg = f"Term: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Alternatives | _cstp.Identifier | _cstp.Literal | _cstp.RawString | _cstp.Trivia
    ) -> Alternatives | Identifier | Literal | RawString | Trivia:
        if isinstance(child, Alternatives | Identifier | Literal | RawString | Trivia):
            return child
        msg = f"Term: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Term.Label | None:
        if label is None or isinstance(label, Term.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Term._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Term"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Alternatives | _cstp.Identifier | _cstp.Literal | _cstp.RawString | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Term.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, Alternatives | Identifier | Literal | RawString | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Term.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Alternatives | _cstp.Identifier | _cstp.Literal | _cstp.RawString | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Term.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Term.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Term.Label) -> list[Alternatives | Identifier | Literal | RawString | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_alternatives(self, child: _cstp.Alternatives) -> None:
        self.children.append((Term.Label.ALTERNATIVES, self._check_child_type_for_mutators(child)))

    def extend_alternatives(self, children: typing.Iterable[_cstp.Alternatives]) -> None:
        self.children.extend(
            [(Term.Label.ALTERNATIVES, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_alternatives(self) -> typing.Iterator[Alternatives]:
        return iter(typing.cast("list[Alternatives]", self._children_snapshot(Term.Label.ALTERNATIVES)))

    def child_alternatives(self) -> Alternatives:
        children = typing.cast("list[Alternatives]", self._children_snapshot(Term.Label.ALTERNATIVES))
        if (n := len(children)) != 1:
            msg = f"Expected one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_alternatives(self) -> Alternatives | None:
        children = typing.cast("list[Alternatives]", self._children_snapshot(Term.Label.ALTERNATIVES))
        if (n := len(children)) > 1:
            msg = f"Expected at most one alternatives child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_identifier(self, child: _cstp.Identifier) -> None:
        self.children.append((Term.Label.IDENTIFIER, self._check_child_type_for_mutators(child)))

    def extend_identifier(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(Term.Label.IDENTIFIER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_identifier(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(Term.Label.IDENTIFIER)))

    def child_identifier(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(Term.Label.IDENTIFIER))
        if (n := len(children)) != 1:
            msg = f"Expected one identifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_identifier(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(Term.Label.IDENTIFIER))
        if (n := len(children)) > 1:
            msg = f"Expected at most one identifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_literal(self, child: _cstp.Literal) -> None:
        self.children.append((Term.Label.LITERAL, self._check_child_type_for_mutators(child)))

    def extend_literal(self, children: typing.Iterable[_cstp.Literal]) -> None:
        self.children.extend([(Term.Label.LITERAL, self._check_child_type_for_mutators(child)) for child in children])

    def children_literal(self) -> typing.Iterator[Literal]:
        return iter(typing.cast("list[Literal]", self._children_snapshot(Term.Label.LITERAL)))

    def child_literal(self) -> Literal:
        children = typing.cast("list[Literal]", self._children_snapshot(Term.Label.LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_literal(self) -> Literal | None:
        children = typing.cast("list[Literal]", self._children_snapshot(Term.Label.LITERAL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_regex(self, child: _cstp.RawString) -> None:
        self.children.append((Term.Label.REGEX, self._check_child_type_for_mutators(child)))

    def extend_regex(self, children: typing.Iterable[_cstp.RawString]) -> None:
        self.children.extend([(Term.Label.REGEX, self._check_child_type_for_mutators(child)) for child in children])

    def children_regex(self) -> typing.Iterator[RawString]:
        return iter(typing.cast("list[RawString]", self._children_snapshot(Term.Label.REGEX)))

    def child_regex(self) -> RawString:
        children = typing.cast("list[RawString]", self._children_snapshot(Term.Label.REGEX))
        if (n := len(children)) != 1:
            msg = f"Expected one regex child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_regex(self) -> RawString | None:
        children = typing.cast("list[RawString]", self._children_snapshot(Term.Label.REGEX))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Disposition.Label.INCLUDE": Label.INCLUDE,
            "Disposition.Label.INLINE": Label.INLINE,
            "Disposition.Label.SUPPRESS": Label.SUPPRESS,
        }
    )
    kind: typing.Literal[NodeKind.DISPOSITION] = NodeKind.DISPOSITION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Disposition.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Disposition.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Disposition) -> None:
        if not isinstance(other, Disposition):
            msg = f"Disposition: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Disposition: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Disposition.Label | None:
        if label is None or isinstance(label, Disposition.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Disposition._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Disposition"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Disposition.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Disposition.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Disposition.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Disposition.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Disposition.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_include(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Disposition.Label.INCLUDE, self._check_child_type_for_mutators(child)))

    def extend_include(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Disposition.Label.INCLUDE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_include(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Disposition.Label.INCLUDE))

    def child_include(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Disposition.Label.INCLUDE)
        if (n := len(children)) != 1:
            msg = f"Expected one include child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_include(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Disposition.Label.INCLUDE)
        if (n := len(children)) > 1:
            msg = f"Expected at most one include child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_inline(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Disposition.Label.INLINE, self._check_child_type_for_mutators(child)))

    def extend_inline(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Disposition.Label.INLINE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_inline(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Disposition.Label.INLINE))

    def child_inline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Disposition.Label.INLINE)
        if (n := len(children)) != 1:
            msg = f"Expected one inline child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_inline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Disposition.Label.INLINE)
        if (n := len(children)) > 1:
            msg = f"Expected at most one inline child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_suppress(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Disposition.Label.SUPPRESS, self._check_child_type_for_mutators(child)))

    def extend_suppress(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Disposition.Label.SUPPRESS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_suppress(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Disposition.Label.SUPPRESS))

    def child_suppress(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Disposition.Label.SUPPRESS)
        if (n := len(children)) != 1:
            msg = f"Expected one suppress child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_suppress(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Disposition.Label.SUPPRESS)
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Quantifier.Label.ONE_OR_MORE": Label.ONE_OR_MORE,
            "Quantifier.Label.OPTIONAL": Label.OPTIONAL,
            "Quantifier.Label.ZERO_OR_MORE": Label.ZERO_OR_MORE,
        }
    )
    kind: typing.Literal[NodeKind.QUANTIFIER] = NodeKind.QUANTIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Quantifier.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Quantifier.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Quantifier) -> None:
        if not isinstance(other, Quantifier):
            msg = f"Quantifier: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Quantifier: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Quantifier.Label | None:
        if label is None or isinstance(label, Quantifier.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Quantifier._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Quantifier"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Quantifier.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Quantifier.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Quantifier.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Quantifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Quantifier.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_one_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.ONE_OR_MORE, self._check_child_type_for_mutators(child)))

    def extend_one_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Quantifier.Label.ONE_OR_MORE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_one_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Quantifier.Label.ONE_OR_MORE))

    def child_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Quantifier.Label.ONE_OR_MORE)
        if (n := len(children)) != 1:
            msg = f"Expected one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Quantifier.Label.ONE_OR_MORE)
        if (n := len(children)) > 1:
            msg = f"Expected at most one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_optional(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.OPTIONAL, self._check_child_type_for_mutators(child)))

    def extend_optional(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Quantifier.Label.OPTIONAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_optional(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Quantifier.Label.OPTIONAL))

    def child_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Quantifier.Label.OPTIONAL)
        if (n := len(children)) != 1:
            msg = f"Expected one optional child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Quantifier.Label.OPTIONAL)
        if (n := len(children)) > 1:
            msg = f"Expected at most one optional child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_zero_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.ZERO_OR_MORE, self._check_child_type_for_mutators(child)))

    def extend_zero_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Quantifier.Label.ZERO_OR_MORE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_zero_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Quantifier.Label.ZERO_OR_MORE))

    def child_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Quantifier.Label.ZERO_OR_MORE)
        if (n := len(children)) != 1:
            msg = f"Expected one zero_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Quantifier.Label.ZERO_OR_MORE)
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Identifier.Label.NAME": Label.NAME})
    kind: typing.Literal[NodeKind.IDENTIFIER] = NodeKind.IDENTIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Identifier.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Identifier.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Identifier) -> None:
        if not isinstance(other, Identifier):
            msg = f"Identifier: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Identifier: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Identifier.Label | None:
        if label is None or isinstance(label, Identifier.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Identifier._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Identifier"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Identifier.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Identifier.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Identifier.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Identifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Identifier.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_name(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Identifier.Label.NAME, self._check_child_type_for_mutators(child)))

    def extend_name(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Identifier.Label.NAME, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_name(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Identifier.Label.NAME))

    def child_name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Identifier.Label.NAME)
        if (n := len(children)) != 1:
            msg = f"Expected one name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Identifier.Label.NAME)
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"RawString.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.RAWSTRING] = NodeKind.RAWSTRING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RawString.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RawString.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.RawString) -> None:
        if not isinstance(other, RawString):
            msg = f"RawString: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"RawString: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> RawString.Label | None:
        if label is None or isinstance(label, RawString.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = RawString._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "RawString"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RawString.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RawString.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RawString.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RawString.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: RawString.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((RawString.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(RawString.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(RawString.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(RawString.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(RawString.Label.VALUE)
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Literal.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.LITERAL] = NodeKind.LITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Literal.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Literal.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Literal) -> None:
        if not isinstance(other, Literal):
            msg = f"Literal: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Literal: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Literal.Label | None:
        if label is None or isinstance(label, Literal.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Literal._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Literal"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Literal.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Literal.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Literal.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Literal.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Literal.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Literal.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Literal.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children])

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Literal.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Literal.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Literal.Label.VALUE)
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
        WHITESPACE = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Trivia.Label.BLOCK_COMMENT": Label.BLOCK_COMMENT,
            "Trivia.Label.LINE_COMMENT": Label.LINE_COMMENT,
            "Trivia.Label.WHITESPACE": Label.WHITESPACE,
        }
    )
    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, BlockComment | LineComment | Whitespace]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.BlockComment | _cstp.LineComment | _cstp.Whitespace,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Trivia.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.BlockComment | _cstp.LineComment | _cstp.Whitespace],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Trivia.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Trivia) -> None:
        if not isinstance(other, Trivia):
            msg = f"Trivia: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, BlockComment | LineComment | Whitespace]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.BlockComment | _cstp.LineComment | _cstp.Whitespace
    ) -> BlockComment | LineComment | Whitespace:
        if isinstance(child, BlockComment | LineComment | Whitespace):
            return child
        msg = f"Trivia: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Trivia.Label | None:
        if label is None or isinstance(label, Trivia.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Trivia._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Trivia"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.BlockComment | _cstp.LineComment | _cstp.Whitespace,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Trivia.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, BlockComment | LineComment | Whitespace]:
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
        child: _cstp.BlockComment | _cstp.LineComment | _cstp.Whitespace,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Trivia.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Trivia.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Trivia.Label) -> list[BlockComment | LineComment | Whitespace]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_block_comment(self, child: _cstp.BlockComment) -> None:
        self.children.append((Trivia.Label.BLOCK_COMMENT, self._check_child_type_for_mutators(child)))

    def extend_block_comment(self, children: typing.Iterable[_cstp.BlockComment]) -> None:
        self.children.extend(
            [(Trivia.Label.BLOCK_COMMENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_block_comment(self) -> typing.Iterator[BlockComment]:
        return iter(typing.cast("list[BlockComment]", self._children_snapshot(Trivia.Label.BLOCK_COMMENT)))

    def child_block_comment(self) -> BlockComment:
        children = typing.cast("list[BlockComment]", self._children_snapshot(Trivia.Label.BLOCK_COMMENT))
        if (n := len(children)) != 1:
            msg = f"Expected one block_comment child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_block_comment(self) -> BlockComment | None:
        children = typing.cast("list[BlockComment]", self._children_snapshot(Trivia.Label.BLOCK_COMMENT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one block_comment child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_line_comment(self, child: _cstp.LineComment) -> None:
        self.children.append((Trivia.Label.LINE_COMMENT, self._check_child_type_for_mutators(child)))

    def extend_line_comment(self, children: typing.Iterable[_cstp.LineComment]) -> None:
        self.children.extend(
            [(Trivia.Label.LINE_COMMENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_line_comment(self) -> typing.Iterator[LineComment]:
        return iter(typing.cast("list[LineComment]", self._children_snapshot(Trivia.Label.LINE_COMMENT)))

    def child_line_comment(self) -> LineComment:
        children = typing.cast("list[LineComment]", self._children_snapshot(Trivia.Label.LINE_COMMENT))
        if (n := len(children)) != 1:
            msg = f"Expected one line_comment child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_line_comment(self) -> LineComment | None:
        children = typing.cast("list[LineComment]", self._children_snapshot(Trivia.Label.LINE_COMMENT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one line_comment child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_whitespace(self, child: _cstp.Whitespace) -> None:
        self.children.append((Trivia.Label.WHITESPACE, self._check_child_type_for_mutators(child)))

    def extend_whitespace(self, children: typing.Iterable[_cstp.Whitespace]) -> None:
        self.children.extend(
            [(Trivia.Label.WHITESPACE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_whitespace(self) -> typing.Iterator[Whitespace]:
        return iter(typing.cast("list[Whitespace]", self._children_snapshot(Trivia.Label.WHITESPACE)))

    def child_whitespace(self) -> Whitespace:
        children = typing.cast("list[Whitespace]", self._children_snapshot(Trivia.Label.WHITESPACE))
        if (n := len(children)) != 1:
            msg = f"Expected one whitespace child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_whitespace(self) -> Whitespace | None:
        children = typing.cast("list[Whitespace]", self._children_snapshot(Trivia.Label.WHITESPACE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one whitespace child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def block_comment(self) -> BlockComment | None:
        return self.maybe_block_comment()

    def line_comment(self) -> LineComment | None:
        return self.maybe_line_comment()

    def whitespace(self) -> Whitespace | None:
        return self.maybe_whitespace()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Trivia.variant: node has no labeled child"
        raise ValueError(msg)


Trivia.Label.BLOCK_COMMENT._fltk_canonical_name = "Trivia.Label.BLOCK_COMMENT"
Trivia.Label.LINE_COMMENT._fltk_canonical_name = "Trivia.Label.LINE_COMMENT"
Trivia.Label.WHITESPACE._fltk_canonical_name = "Trivia.Label.WHITESPACE"


@dataclasses.dataclass
class Whitespace:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Whitespace.Label.CONTENT": Label.CONTENT})
    kind: typing.Literal[NodeKind.WHITESPACE] = NodeKind.WHITESPACE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Whitespace.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Whitespace.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Whitespace) -> None:
        if not isinstance(other, Whitespace):
            msg = f"Whitespace: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Whitespace: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Whitespace.Label | None:
        if label is None or isinstance(label, Whitespace.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Whitespace._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Whitespace"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Whitespace.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Whitespace.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Whitespace.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Whitespace.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Whitespace.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Whitespace.Label.CONTENT, self._check_child_type_for_mutators(child)))

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Whitespace.Label.CONTENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Whitespace.Label.CONTENT))

    def child_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Whitespace.Label.CONTENT)
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Whitespace.Label.CONTENT)
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_content()

    def content_text(self) -> str:
        child = self.child_content()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Whitespace.content_text: child labelled 'content' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


Whitespace.Label.CONTENT._fltk_canonical_name = "Whitespace.Label.CONTENT"


@dataclasses.dataclass
class LineComment:
    class Label(enum.Enum):
        CONTENT = enum.auto()
        NEWLINE = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "LineComment.Label.CONTENT": Label.CONTENT,
            "LineComment.Label.NEWLINE": Label.NEWLINE,
            "LineComment.Label.PREFIX": Label.PREFIX,
        }
    )
    kind: typing.Literal[NodeKind.LINECOMMENT] = NodeKind.LINECOMMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, LineComment.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, LineComment.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.LineComment) -> None:
        if not isinstance(other, LineComment):
            msg = f"LineComment: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"LineComment: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> LineComment.Label | None:
        if label is None or isinstance(label, LineComment.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = LineComment._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "LineComment"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, LineComment.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LineComment.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, LineComment.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LineComment.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: LineComment.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((LineComment.Label.CONTENT, self._check_child_type_for_mutators(child)))

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(LineComment.Label.CONTENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(LineComment.Label.CONTENT))

    def child_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(LineComment.Label.CONTENT)
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(LineComment.Label.CONTENT)
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_newline(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((LineComment.Label.NEWLINE, self._check_child_type_for_mutators(child)))

    def extend_newline(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(LineComment.Label.NEWLINE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_newline(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(LineComment.Label.NEWLINE))

    def child_newline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(LineComment.Label.NEWLINE)
        if (n := len(children)) != 1:
            msg = f"Expected one newline child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_newline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(LineComment.Label.NEWLINE)
        if (n := len(children)) > 1:
            msg = f"Expected at most one newline child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_prefix(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((LineComment.Label.PREFIX, self._check_child_type_for_mutators(child)))

    def extend_prefix(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(LineComment.Label.PREFIX, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_prefix(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(LineComment.Label.PREFIX))

    def child_prefix(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(LineComment.Label.PREFIX)
        if (n := len(children)) != 1:
            msg = f"Expected one prefix child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_prefix(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(LineComment.Label.PREFIX)
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

    def newline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_newline()

    def newline_text(self) -> str:
        child = self.child_newline()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "LineComment.newline_text: child labelled 'newline' is not a Span"
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
LineComment.Label.NEWLINE._fltk_canonical_name = "LineComment.Label.NEWLINE"
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "BlockComment.Label.CONTENT": Label.CONTENT,
            "BlockComment.Label.END": Label.END,
            "BlockComment.Label.START": Label.START,
        }
    )
    kind: typing.Literal[NodeKind.BLOCKCOMMENT] = NodeKind.BLOCKCOMMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, BlockComment.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, BlockComment.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.BlockComment) -> None:
        if not isinstance(other, BlockComment):
            msg = f"BlockComment: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"BlockComment: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> BlockComment.Label | None:
        if label is None or isinstance(label, BlockComment.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = BlockComment._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "BlockComment"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, BlockComment.Label)
            else self._check_label_type_for_mutators(label, "insert")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (checked_label, checked_child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"BlockComment.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, BlockComment.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"BlockComment.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: BlockComment.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((BlockComment.Label.CONTENT, self._check_child_type_for_mutators(child)))

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(BlockComment.Label.CONTENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(BlockComment.Label.CONTENT))

    def child_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(BlockComment.Label.CONTENT)
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(BlockComment.Label.CONTENT)
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_end(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((BlockComment.Label.END, self._check_child_type_for_mutators(child)))

    def extend_end(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(BlockComment.Label.END, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_end(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(BlockComment.Label.END))

    def child_end(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(BlockComment.Label.END)
        if (n := len(children)) != 1:
            msg = f"Expected one end child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_end(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(BlockComment.Label.END)
        if (n := len(children)) > 1:
            msg = f"Expected at most one end child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_start(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((BlockComment.Label.START, self._check_child_type_for_mutators(child)))

    def extend_start(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(BlockComment.Label.START, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_start(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(BlockComment.Label.START))

    def child_start(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(BlockComment.Label.START)
        if (n := len(children)) != 1:
            msg = f"Expected one start child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_start(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(BlockComment.Label.START)
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
