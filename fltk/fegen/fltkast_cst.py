from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import typing

import fltk.fegen.pyrt.terminalsrc
from fltk.fegen.fltkast_cst_protocol import NodeKind

if typing.TYPE_CHECKING:
    import fltk.fegen.fltkast_cst_protocol as _cstp
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol


def _get_native_span_type():
    m = sys.modules.get("fltk._native")
    return m.Span if m is not None else None


@dataclasses.dataclass
class AstSpec:
    class Label(enum.Enum):
        STATEMENT = enum.auto()
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

    kind: typing.Literal[NodeKind.ASTSPEC] = NodeKind.ASTSPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Statement | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Statement | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Statement | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.AstSpec) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Statement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Statement | _cstp.Trivia) -> None:
        if not isinstance(child, Statement | Trivia):
            msg = f"AstSpec: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, AstSpec.Label)):
            _cn = "AstSpec"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Statement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, Statement | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"AstSpec.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Statement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"AstSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_statement(self, child: _cstp.Statement) -> None:
        entry: typing.Any = (AstSpec.Label.STATEMENT, child)
        self.children.append(entry)

    def extend_statement(self, children: typing.Iterable[_cstp.Statement]) -> None:
        entries: typing.Any = ((AstSpec.Label.STATEMENT, child) for child in children)
        self.children.extend(entries)

    def children_statement(self) -> typing.Iterator[Statement]:
        return (typing.cast("Statement", child) for (label, child) in self.children if label == AstSpec.Label.STATEMENT)

    def child_statement(self) -> Statement:
        children = list(self.children_statement())
        if (n := len(children)) != 1:
            msg = f"Expected one statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_statement(self) -> Statement | None:
        children = list(self.children_statement())
        if (n := len(children)) > 1:
            msg = f"Expected at most one statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def statement(self) -> list[Statement]:
        return list(self.children_statement())


AstSpec.Label.STATEMENT._fltk_canonical_name = "AstSpec.Label.STATEMENT"


@dataclasses.dataclass
class Statement:
    class Label(enum.Enum):
        OPTION_STMT = enum.auto()
        RULE_CONFIG = enum.auto()
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

    kind: typing.Literal[NodeKind.STATEMENT] = NodeKind.STATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, OptionStmt | RuleConfig]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.OptionStmt | _cstp.RuleConfig,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.OptionStmt | _cstp.RuleConfig],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Statement) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, OptionStmt | RuleConfig]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.OptionStmt | _cstp.RuleConfig) -> None:
        if not isinstance(child, OptionStmt | RuleConfig):
            msg = f"Statement: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Statement.Label)):
            _cn = "Statement"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.OptionStmt | _cstp.RuleConfig,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, OptionStmt | RuleConfig]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Statement.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.OptionStmt | _cstp.RuleConfig,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Statement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_option_stmt(self, child: _cstp.OptionStmt) -> None:
        entry: typing.Any = (Statement.Label.OPTION_STMT, child)
        self.children.append(entry)

    def extend_option_stmt(self, children: typing.Iterable[_cstp.OptionStmt]) -> None:
        entries: typing.Any = ((Statement.Label.OPTION_STMT, child) for child in children)
        self.children.extend(entries)

    def children_option_stmt(self) -> typing.Iterator[OptionStmt]:
        return (
            typing.cast("OptionStmt", child) for (label, child) in self.children if label == Statement.Label.OPTION_STMT
        )

    def child_option_stmt(self) -> OptionStmt:
        children = list(self.children_option_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one option_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_option_stmt(self) -> OptionStmt | None:
        children = list(self.children_option_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one option_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_rule_config(self, child: _cstp.RuleConfig) -> None:
        entry: typing.Any = (Statement.Label.RULE_CONFIG, child)
        self.children.append(entry)

    def extend_rule_config(self, children: typing.Iterable[_cstp.RuleConfig]) -> None:
        entries: typing.Any = ((Statement.Label.RULE_CONFIG, child) for child in children)
        self.children.extend(entries)

    def children_rule_config(self) -> typing.Iterator[RuleConfig]:
        return (
            typing.cast("RuleConfig", child) for (label, child) in self.children if label == Statement.Label.RULE_CONFIG
        )

    def child_rule_config(self) -> RuleConfig:
        children = list(self.children_rule_config())
        if (n := len(children)) != 1:
            msg = f"Expected one rule_config child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule_config(self) -> RuleConfig | None:
        children = list(self.children_rule_config())
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule_config child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def option_stmt(self) -> OptionStmt | None:
        return self.maybe_option_stmt()

    def rule_config(self) -> RuleConfig | None:
        return self.maybe_rule_config()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Statement.variant: node has no labeled child"
        raise ValueError(msg)


Statement.Label.OPTION_STMT._fltk_canonical_name = "Statement.Label.OPTION_STMT"
Statement.Label.RULE_CONFIG._fltk_canonical_name = "Statement.Label.RULE_CONFIG"


@dataclasses.dataclass
class OptionStmt:
    class Label(enum.Enum):
        KEY = enum.auto()
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

    kind: typing.Literal[NodeKind.OPTIONSTMT] = NodeKind.OPTIONSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | OptionValue | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Identifier | _cstp.OptionValue | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.OptionValue | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.OptionStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | OptionValue | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.OptionValue | _cstp.Trivia) -> None:
        if not isinstance(child, Identifier | OptionValue | Trivia):
            msg = f"OptionStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, OptionStmt.Label)):
            _cn = "OptionStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.OptionValue | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | OptionValue | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"OptionStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.OptionValue | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"OptionStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_key(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (OptionStmt.Label.KEY, child)
        self.children.append(entry)

    def extend_key(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((OptionStmt.Label.KEY, child) for child in children)
        self.children.extend(entries)

    def children_key(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == OptionStmt.Label.KEY)

    def child_key(self) -> Identifier:
        children = list(self.children_key())
        if (n := len(children)) != 1:
            msg = f"Expected one key child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_key(self) -> Identifier | None:
        children = list(self.children_key())
        if (n := len(children)) > 1:
            msg = f"Expected at most one key child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_value(self, child: _cstp.OptionValue) -> None:
        entry: typing.Any = (OptionStmt.Label.VALUE, child)
        self.children.append(entry)

    def extend_value(self, children: typing.Iterable[_cstp.OptionValue]) -> None:
        entries: typing.Any = ((OptionStmt.Label.VALUE, child) for child in children)
        self.children.extend(entries)

    def children_value(self) -> typing.Iterator[OptionValue]:
        return (
            typing.cast("OptionValue", child) for (label, child) in self.children if label == OptionStmt.Label.VALUE
        )

    def child_value(self) -> OptionValue:
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> OptionValue | None:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def key(self) -> Identifier:
        return self.child_key()

    def value(self) -> OptionValue:
        return self.child_value()


OptionStmt.Label.KEY._fltk_canonical_name = "OptionStmt.Label.KEY"
OptionStmt.Label.VALUE._fltk_canonical_name = "OptionStmt.Label.VALUE"


@dataclasses.dataclass
class OptionValue:
    class Label(enum.Enum):
        FALSE = enum.auto()
        STRING = enum.auto()
        TRUE = enum.auto()
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

    kind: typing.Literal[NodeKind.OPTIONVALUE] = NodeKind.OPTIONVALUE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, String | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.String | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.String | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.OptionValue) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, String | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: _cstp.String | fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = OptionValue._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (String, fltk.fegen.pyrt.terminalsrc.Span)
            OptionValue._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            OptionValue._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = OptionValue._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"OptionValue: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, OptionValue.Label)):
            _cn = "OptionValue"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.String | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, String | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"OptionValue.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.String | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"OptionValue.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_false(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((OptionValue.Label.FALSE, child))

    def extend_false(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((OptionValue.Label.FALSE, child) for child in children)

    def children_false(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == OptionValue.Label.FALSE
        )

    def child_false(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_false())
        if (n := len(children)) != 1:
            msg = f"Expected one false child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_false(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_false())
        if (n := len(children)) > 1:
            msg = f"Expected at most one false child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_string(self, child: _cstp.String) -> None:
        entry: typing.Any = (OptionValue.Label.STRING, child)
        self.children.append(entry)

    def extend_string(self, children: typing.Iterable[_cstp.String]) -> None:
        entries: typing.Any = ((OptionValue.Label.STRING, child) for child in children)
        self.children.extend(entries)

    def children_string(self) -> typing.Iterator[String]:
        return (typing.cast("String", child) for (label, child) in self.children if label == OptionValue.Label.STRING)

    def child_string(self) -> String:
        children = list(self.children_string())
        if (n := len(children)) != 1:
            msg = f"Expected one string child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_string(self) -> String | None:
        children = list(self.children_string())
        if (n := len(children)) > 1:
            msg = f"Expected at most one string child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_true(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((OptionValue.Label.TRUE, child))

    def extend_true(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((OptionValue.Label.TRUE, child) for child in children)

    def children_true(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == OptionValue.Label.TRUE
        )

    def child_true(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_true())
        if (n := len(children)) != 1:
            msg = f"Expected one true child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_true(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_true())
        if (n := len(children)) > 1:
            msg = f"Expected at most one true child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def false(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_false()

    def false_text(self) -> str | None:
        child = self.maybe_false()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "OptionValue.false_text: child labelled 'false' is not a Span"
            raise TypeError(msg) from None

    def string(self) -> String | None:
        return self.maybe_string()

    def true(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_true()

    def true_text(self) -> str | None:
        child = self.maybe_true()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "OptionValue.true_text: child labelled 'true' is not a Span"
            raise TypeError(msg) from None

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "OptionValue.variant: node has no labeled child"
        raise ValueError(msg)


OptionValue.Label.FALSE._fltk_canonical_name = "OptionValue.Label.FALSE"
OptionValue.Label.STRING._fltk_canonical_name = "OptionValue.Label.STRING"
OptionValue.Label.TRUE._fltk_canonical_name = "OptionValue.Label.TRUE"


@dataclasses.dataclass
class RuleConfig:
    class Label(enum.Enum):
        RULE_NAME = enum.auto()
        RULE_STATEMENT = enum.auto()
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

    kind: typing.Literal[NodeKind.RULECONFIG] = NodeKind.RULECONFIG
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | RuleStatement | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Identifier | _cstp.RuleStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.RuleStatement | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.RuleConfig) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | RuleStatement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.RuleStatement | _cstp.Trivia) -> None:
        if not isinstance(child, Identifier | RuleStatement | Trivia):
            msg = f"RuleConfig: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, RuleConfig.Label)):
            _cn = "RuleConfig"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.RuleStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | RuleStatement | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleConfig.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.RuleStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleConfig.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_rule_name(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (RuleConfig.Label.RULE_NAME, child)
        self.children.append(entry)

    def extend_rule_name(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((RuleConfig.Label.RULE_NAME, child) for child in children)
        self.children.extend(entries)

    def children_rule_name(self) -> typing.Iterator[Identifier]:
        return (
            typing.cast("Identifier", child) for (label, child) in self.children if label == RuleConfig.Label.RULE_NAME
        )

    def child_rule_name(self) -> Identifier:
        children = list(self.children_rule_name())
        if (n := len(children)) != 1:
            msg = f"Expected one rule_name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule_name(self) -> Identifier | None:
        children = list(self.children_rule_name())
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule_name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_rule_statement(self, child: _cstp.RuleStatement) -> None:
        entry: typing.Any = (RuleConfig.Label.RULE_STATEMENT, child)
        self.children.append(entry)

    def extend_rule_statement(self, children: typing.Iterable[_cstp.RuleStatement]) -> None:
        entries: typing.Any = ((RuleConfig.Label.RULE_STATEMENT, child) for child in children)
        self.children.extend(entries)

    def children_rule_statement(self) -> typing.Iterator[RuleStatement]:
        return (
            typing.cast("RuleStatement", child)
            for (label, child) in self.children
            if label == RuleConfig.Label.RULE_STATEMENT
        )

    def child_rule_statement(self) -> RuleStatement:
        children = list(self.children_rule_statement())
        if (n := len(children)) != 1:
            msg = f"Expected one rule_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule_statement(self) -> RuleStatement | None:
        children = list(self.children_rule_statement())
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def rule_name(self) -> Identifier:
        return self.child_rule_name()

    def rule_statement(self) -> list[RuleStatement]:
        return list(self.children_rule_statement())


RuleConfig.Label.RULE_NAME._fltk_canonical_name = "RuleConfig.Label.RULE_NAME"
RuleConfig.Label.RULE_STATEMENT._fltk_canonical_name = "RuleConfig.Label.RULE_STATEMENT"


@dataclasses.dataclass
class RuleStatement:
    class Label(enum.Enum):
        BOOL_STMT = enum.auto()
        CUSTOM_STMT = enum.auto()
        FIELD_STMT = enum.auto()
        FLATTEN_STMT = enum.auto()
        FOLD_STMT = enum.auto()
        KEY_STMT = enum.auto()
        NAME_STMT = enum.auto()
        PRODUCT_STMT = enum.auto()
        SUM_STMT = enum.auto()
        TEXT_FROM_STMT = enum.auto()
        TRANSPARENT_STMT = enum.auto()
        TYPE_STMT = enum.auto()
        VARIANT_STMT = enum.auto()
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

    kind: typing.Literal[NodeKind.RULESTATEMENT] = NodeKind.RULESTATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[
        tuple[
            Label | None,
            BoolStmt
            | CustomStmt
            | FieldStmt
            | FlattenStmt
            | FoldStmt
            | KeyStmt
            | NameStmt
            | ProductStmt
            | SumStmt
            | TextFromStmt
            | TransparentStmt
            | TypeStmt
            | VariantStmt,
        ]
    ] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.BoolStmt
        | _cstp.CustomStmt
        | _cstp.FieldStmt
        | _cstp.FlattenStmt
        | _cstp.FoldStmt
        | _cstp.KeyStmt
        | _cstp.NameStmt
        | _cstp.ProductStmt
        | _cstp.SumStmt
        | _cstp.TextFromStmt
        | _cstp.TransparentStmt
        | _cstp.TypeStmt
        | _cstp.VariantStmt,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[
            _cstp.BoolStmt
            | _cstp.CustomStmt
            | _cstp.FieldStmt
            | _cstp.FlattenStmt
            | _cstp.FoldStmt
            | _cstp.KeyStmt
            | _cstp.NameStmt
            | _cstp.ProductStmt
            | _cstp.SumStmt
            | _cstp.TextFromStmt
            | _cstp.TransparentStmt
            | _cstp.TypeStmt
            | _cstp.VariantStmt
        ],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.RuleStatement) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(
        self,
    ) -> tuple[
        Label | None,
        BoolStmt
        | CustomStmt
        | FieldStmt
        | FlattenStmt
        | FoldStmt
        | KeyStmt
        | NameStmt
        | ProductStmt
        | SumStmt
        | TextFromStmt
        | TransparentStmt
        | TypeStmt
        | VariantStmt,
    ]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self,
        child: _cstp.BoolStmt
        | _cstp.CustomStmt
        | _cstp.FieldStmt
        | _cstp.FlattenStmt
        | _cstp.FoldStmt
        | _cstp.KeyStmt
        | _cstp.NameStmt
        | _cstp.ProductStmt
        | _cstp.SumStmt
        | _cstp.TextFromStmt
        | _cstp.TransparentStmt
        | _cstp.TypeStmt
        | _cstp.VariantStmt,
    ) -> None:
        if not isinstance(
            child,
            BoolStmt
            | CustomStmt
            | FieldStmt
            | FlattenStmt
            | FoldStmt
            | KeyStmt
            | NameStmt
            | ProductStmt
            | SumStmt
            | TextFromStmt
            | TransparentStmt
            | TypeStmt
            | VariantStmt,
        ):
            msg = f"RuleStatement: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, RuleStatement.Label)):
            _cn = "RuleStatement"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.BoolStmt
        | _cstp.CustomStmt
        | _cstp.FieldStmt
        | _cstp.FlattenStmt
        | _cstp.FoldStmt
        | _cstp.KeyStmt
        | _cstp.NameStmt
        | _cstp.ProductStmt
        | _cstp.SumStmt
        | _cstp.TextFromStmt
        | _cstp.TransparentStmt
        | _cstp.TypeStmt
        | _cstp.VariantStmt,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(
        self, index: int
    ) -> tuple[
        Label | None,
        BoolStmt
        | CustomStmt
        | FieldStmt
        | FlattenStmt
        | FoldStmt
        | KeyStmt
        | NameStmt
        | ProductStmt
        | SumStmt
        | TextFromStmt
        | TransparentStmt
        | TypeStmt
        | VariantStmt,
    ]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleStatement.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.BoolStmt
        | _cstp.CustomStmt
        | _cstp.FieldStmt
        | _cstp.FlattenStmt
        | _cstp.FoldStmt
        | _cstp.KeyStmt
        | _cstp.NameStmt
        | _cstp.ProductStmt
        | _cstp.SumStmt
        | _cstp.TextFromStmt
        | _cstp.TransparentStmt
        | _cstp.TypeStmt
        | _cstp.VariantStmt,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleStatement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_bool_stmt(self, child: _cstp.BoolStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.BOOL_STMT, child)
        self.children.append(entry)

    def extend_bool_stmt(self, children: typing.Iterable[_cstp.BoolStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.BOOL_STMT, child) for child in children)
        self.children.extend(entries)

    def children_bool_stmt(self) -> typing.Iterator[BoolStmt]:
        return (
            typing.cast("BoolStmt", child) for (label, child) in self.children if label == RuleStatement.Label.BOOL_STMT
        )

    def child_bool_stmt(self) -> BoolStmt:
        children = list(self.children_bool_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one bool_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_bool_stmt(self) -> BoolStmt | None:
        children = list(self.children_bool_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one bool_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_custom_stmt(self, child: _cstp.CustomStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.CUSTOM_STMT, child)
        self.children.append(entry)

    def extend_custom_stmt(self, children: typing.Iterable[_cstp.CustomStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.CUSTOM_STMT, child) for child in children)
        self.children.extend(entries)

    def children_custom_stmt(self) -> typing.Iterator[CustomStmt]:
        return (
            typing.cast("CustomStmt", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.CUSTOM_STMT
        )

    def child_custom_stmt(self) -> CustomStmt:
        children = list(self.children_custom_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one custom_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_custom_stmt(self) -> CustomStmt | None:
        children = list(self.children_custom_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one custom_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_field_stmt(self, child: _cstp.FieldStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.FIELD_STMT, child)
        self.children.append(entry)

    def extend_field_stmt(self, children: typing.Iterable[_cstp.FieldStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.FIELD_STMT, child) for child in children)
        self.children.extend(entries)

    def children_field_stmt(self) -> typing.Iterator[FieldStmt]:
        return (
            typing.cast("FieldStmt", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.FIELD_STMT
        )

    def child_field_stmt(self) -> FieldStmt:
        children = list(self.children_field_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one field_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_field_stmt(self) -> FieldStmt | None:
        children = list(self.children_field_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one field_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_flatten_stmt(self, child: _cstp.FlattenStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.FLATTEN_STMT, child)
        self.children.append(entry)

    def extend_flatten_stmt(self, children: typing.Iterable[_cstp.FlattenStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.FLATTEN_STMT, child) for child in children)
        self.children.extend(entries)

    def children_flatten_stmt(self) -> typing.Iterator[FlattenStmt]:
        return (
            typing.cast("FlattenStmt", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.FLATTEN_STMT
        )

    def child_flatten_stmt(self) -> FlattenStmt:
        children = list(self.children_flatten_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one flatten_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_flatten_stmt(self) -> FlattenStmt | None:
        children = list(self.children_flatten_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one flatten_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_fold_stmt(self, child: _cstp.FoldStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.FOLD_STMT, child)
        self.children.append(entry)

    def extend_fold_stmt(self, children: typing.Iterable[_cstp.FoldStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.FOLD_STMT, child) for child in children)
        self.children.extend(entries)

    def children_fold_stmt(self) -> typing.Iterator[FoldStmt]:
        return (
            typing.cast("FoldStmt", child) for (label, child) in self.children if label == RuleStatement.Label.FOLD_STMT
        )

    def child_fold_stmt(self) -> FoldStmt:
        children = list(self.children_fold_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one fold_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_fold_stmt(self) -> FoldStmt | None:
        children = list(self.children_fold_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one fold_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_key_stmt(self, child: _cstp.KeyStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.KEY_STMT, child)
        self.children.append(entry)

    def extend_key_stmt(self, children: typing.Iterable[_cstp.KeyStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.KEY_STMT, child) for child in children)
        self.children.extend(entries)

    def children_key_stmt(self) -> typing.Iterator[KeyStmt]:
        return (
            typing.cast("KeyStmt", child) for (label, child) in self.children if label == RuleStatement.Label.KEY_STMT
        )

    def child_key_stmt(self) -> KeyStmt:
        children = list(self.children_key_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one key_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_key_stmt(self) -> KeyStmt | None:
        children = list(self.children_key_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one key_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_name_stmt(self, child: _cstp.NameStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.NAME_STMT, child)
        self.children.append(entry)

    def extend_name_stmt(self, children: typing.Iterable[_cstp.NameStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.NAME_STMT, child) for child in children)
        self.children.extend(entries)

    def children_name_stmt(self) -> typing.Iterator[NameStmt]:
        return (
            typing.cast("NameStmt", child) for (label, child) in self.children if label == RuleStatement.Label.NAME_STMT
        )

    def child_name_stmt(self) -> NameStmt:
        children = list(self.children_name_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one name_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name_stmt(self) -> NameStmt | None:
        children = list(self.children_name_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one name_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_product_stmt(self, child: _cstp.ProductStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.PRODUCT_STMT, child)
        self.children.append(entry)

    def extend_product_stmt(self, children: typing.Iterable[_cstp.ProductStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.PRODUCT_STMT, child) for child in children)
        self.children.extend(entries)

    def children_product_stmt(self) -> typing.Iterator[ProductStmt]:
        return (
            typing.cast("ProductStmt", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.PRODUCT_STMT
        )

    def child_product_stmt(self) -> ProductStmt:
        children = list(self.children_product_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one product_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_product_stmt(self) -> ProductStmt | None:
        children = list(self.children_product_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one product_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_sum_stmt(self, child: _cstp.SumStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.SUM_STMT, child)
        self.children.append(entry)

    def extend_sum_stmt(self, children: typing.Iterable[_cstp.SumStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.SUM_STMT, child) for child in children)
        self.children.extend(entries)

    def children_sum_stmt(self) -> typing.Iterator[SumStmt]:
        return (
            typing.cast("SumStmt", child) for (label, child) in self.children if label == RuleStatement.Label.SUM_STMT
        )

    def child_sum_stmt(self) -> SumStmt:
        children = list(self.children_sum_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one sum_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_sum_stmt(self) -> SumStmt | None:
        children = list(self.children_sum_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one sum_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_text_from_stmt(self, child: _cstp.TextFromStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.TEXT_FROM_STMT, child)
        self.children.append(entry)

    def extend_text_from_stmt(self, children: typing.Iterable[_cstp.TextFromStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.TEXT_FROM_STMT, child) for child in children)
        self.children.extend(entries)

    def children_text_from_stmt(self) -> typing.Iterator[TextFromStmt]:
        return (
            typing.cast("TextFromStmt", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.TEXT_FROM_STMT
        )

    def child_text_from_stmt(self) -> TextFromStmt:
        children = list(self.children_text_from_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one text_from_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_text_from_stmt(self) -> TextFromStmt | None:
        children = list(self.children_text_from_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one text_from_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_transparent_stmt(self, child: _cstp.TransparentStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.TRANSPARENT_STMT, child)
        self.children.append(entry)

    def extend_transparent_stmt(self, children: typing.Iterable[_cstp.TransparentStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.TRANSPARENT_STMT, child) for child in children)
        self.children.extend(entries)

    def children_transparent_stmt(self) -> typing.Iterator[TransparentStmt]:
        return (
            typing.cast("TransparentStmt", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.TRANSPARENT_STMT
        )

    def child_transparent_stmt(self) -> TransparentStmt:
        children = list(self.children_transparent_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one transparent_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_transparent_stmt(self) -> TransparentStmt | None:
        children = list(self.children_transparent_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one transparent_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_type_stmt(self, child: _cstp.TypeStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.TYPE_STMT, child)
        self.children.append(entry)

    def extend_type_stmt(self, children: typing.Iterable[_cstp.TypeStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.TYPE_STMT, child) for child in children)
        self.children.extend(entries)

    def children_type_stmt(self) -> typing.Iterator[TypeStmt]:
        return (
            typing.cast("TypeStmt", child) for (label, child) in self.children if label == RuleStatement.Label.TYPE_STMT
        )

    def child_type_stmt(self) -> TypeStmt:
        children = list(self.children_type_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one type_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_type_stmt(self) -> TypeStmt | None:
        children = list(self.children_type_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one type_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_variant_stmt(self, child: _cstp.VariantStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.VARIANT_STMT, child)
        self.children.append(entry)

    def extend_variant_stmt(self, children: typing.Iterable[_cstp.VariantStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.VARIANT_STMT, child) for child in children)
        self.children.extend(entries)

    def children_variant_stmt(self) -> typing.Iterator[VariantStmt]:
        return (
            typing.cast("VariantStmt", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.VARIANT_STMT
        )

    def child_variant_stmt(self) -> VariantStmt:
        children = list(self.children_variant_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one variant_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_variant_stmt(self) -> VariantStmt | None:
        children = list(self.children_variant_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one variant_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def bool_stmt(self) -> BoolStmt | None:
        return self.maybe_bool_stmt()

    def custom_stmt(self) -> CustomStmt | None:
        return self.maybe_custom_stmt()

    def field_stmt(self) -> FieldStmt | None:
        return self.maybe_field_stmt()

    def flatten_stmt(self) -> FlattenStmt | None:
        return self.maybe_flatten_stmt()

    def fold_stmt(self) -> FoldStmt | None:
        return self.maybe_fold_stmt()

    def key_stmt(self) -> KeyStmt | None:
        return self.maybe_key_stmt()

    def name_stmt(self) -> NameStmt | None:
        return self.maybe_name_stmt()

    def product_stmt(self) -> ProductStmt | None:
        return self.maybe_product_stmt()

    def sum_stmt(self) -> SumStmt | None:
        return self.maybe_sum_stmt()

    def text_from_stmt(self) -> TextFromStmt | None:
        return self.maybe_text_from_stmt()

    def transparent_stmt(self) -> TransparentStmt | None:
        return self.maybe_transparent_stmt()

    def type_stmt(self) -> TypeStmt | None:
        return self.maybe_type_stmt()

    def variant_stmt(self) -> VariantStmt | None:
        return self.maybe_variant_stmt()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "RuleStatement.variant: node has no labeled child"
        raise ValueError(msg)


RuleStatement.Label.BOOL_STMT._fltk_canonical_name = "RuleStatement.Label.BOOL_STMT"
RuleStatement.Label.CUSTOM_STMT._fltk_canonical_name = "RuleStatement.Label.CUSTOM_STMT"
RuleStatement.Label.FIELD_STMT._fltk_canonical_name = "RuleStatement.Label.FIELD_STMT"
RuleStatement.Label.FLATTEN_STMT._fltk_canonical_name = "RuleStatement.Label.FLATTEN_STMT"
RuleStatement.Label.FOLD_STMT._fltk_canonical_name = "RuleStatement.Label.FOLD_STMT"
RuleStatement.Label.KEY_STMT._fltk_canonical_name = "RuleStatement.Label.KEY_STMT"
RuleStatement.Label.NAME_STMT._fltk_canonical_name = "RuleStatement.Label.NAME_STMT"
RuleStatement.Label.PRODUCT_STMT._fltk_canonical_name = "RuleStatement.Label.PRODUCT_STMT"
RuleStatement.Label.SUM_STMT._fltk_canonical_name = "RuleStatement.Label.SUM_STMT"
RuleStatement.Label.TEXT_FROM_STMT._fltk_canonical_name = "RuleStatement.Label.TEXT_FROM_STMT"
RuleStatement.Label.TRANSPARENT_STMT._fltk_canonical_name = "RuleStatement.Label.TRANSPARENT_STMT"
RuleStatement.Label.TYPE_STMT._fltk_canonical_name = "RuleStatement.Label.TYPE_STMT"
RuleStatement.Label.VARIANT_STMT._fltk_canonical_name = "RuleStatement.Label.VARIANT_STMT"


@dataclasses.dataclass
class TypeStmt:
    class Label(enum.Enum):
        SPEC = enum.auto()
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

    kind: typing.Literal[NodeKind.TYPESTMT] = NodeKind.TYPESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Trivia | TypeSpec]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Trivia | _cstp.TypeSpec, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Trivia | _cstp.TypeSpec],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.TypeStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Trivia | TypeSpec]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia | _cstp.TypeSpec) -> None:
        if not isinstance(child, Trivia | TypeSpec):
            msg = f"TypeStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, TypeStmt.Label)):
            _cn = "TypeStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Trivia | _cstp.TypeSpec,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, Trivia | TypeSpec]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TypeStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Trivia | _cstp.TypeSpec,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TypeStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_spec(self, child: _cstp.TypeSpec) -> None:
        entry: typing.Any = (TypeStmt.Label.SPEC, child)
        self.children.append(entry)

    def extend_spec(self, children: typing.Iterable[_cstp.TypeSpec]) -> None:
        entries: typing.Any = ((TypeStmt.Label.SPEC, child) for child in children)
        self.children.extend(entries)

    def children_spec(self) -> typing.Iterator[TypeSpec]:
        return (typing.cast("TypeSpec", child) for (label, child) in self.children if label == TypeStmt.Label.SPEC)

    def child_spec(self) -> TypeSpec:
        children = list(self.children_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spec(self) -> TypeSpec | None:
        children = list(self.children_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def spec(self) -> TypeSpec:
        return self.child_spec()


TypeStmt.Label.SPEC._fltk_canonical_name = "TypeStmt.Label.SPEC"


@dataclasses.dataclass
class TypeSpec:
    class Label(enum.Enum):
        BUILTIN = enum.auto()
        CUSTOM = enum.auto()
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

    kind: typing.Literal[NodeKind.TYPESPEC] = NodeKind.TYPESPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CustomSpec | Identifier]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.CustomSpec | _cstp.Identifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.CustomSpec | _cstp.Identifier],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.TypeSpec) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, CustomSpec | Identifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.CustomSpec | _cstp.Identifier) -> None:
        if not isinstance(child, CustomSpec | Identifier):
            msg = f"TypeSpec: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, TypeSpec.Label)):
            _cn = "TypeSpec"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.CustomSpec | _cstp.Identifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, CustomSpec | Identifier]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TypeSpec.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.CustomSpec | _cstp.Identifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TypeSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_builtin(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (TypeSpec.Label.BUILTIN, child)
        self.children.append(entry)

    def extend_builtin(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((TypeSpec.Label.BUILTIN, child) for child in children)
        self.children.extend(entries)

    def children_builtin(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == TypeSpec.Label.BUILTIN)

    def child_builtin(self) -> Identifier:
        children = list(self.children_builtin())
        if (n := len(children)) != 1:
            msg = f"Expected one builtin child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_builtin(self) -> Identifier | None:
        children = list(self.children_builtin())
        if (n := len(children)) > 1:
            msg = f"Expected at most one builtin child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_custom(self, child: _cstp.CustomSpec) -> None:
        entry: typing.Any = (TypeSpec.Label.CUSTOM, child)
        self.children.append(entry)

    def extend_custom(self, children: typing.Iterable[_cstp.CustomSpec]) -> None:
        entries: typing.Any = ((TypeSpec.Label.CUSTOM, child) for child in children)
        self.children.extend(entries)

    def children_custom(self) -> typing.Iterator[CustomSpec]:
        return (typing.cast("CustomSpec", child) for (label, child) in self.children if label == TypeSpec.Label.CUSTOM)

    def child_custom(self) -> CustomSpec:
        children = list(self.children_custom())
        if (n := len(children)) != 1:
            msg = f"Expected one custom child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_custom(self) -> CustomSpec | None:
        children = list(self.children_custom())
        if (n := len(children)) > 1:
            msg = f"Expected at most one custom child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def builtin(self) -> Identifier | None:
        return self.maybe_builtin()

    def custom(self) -> CustomSpec | None:
        return self.maybe_custom()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "TypeSpec.variant: node has no labeled child"
        raise ValueError(msg)


TypeSpec.Label.BUILTIN._fltk_canonical_name = "TypeSpec.Label.BUILTIN"
TypeSpec.Label.CUSTOM._fltk_canonical_name = "TypeSpec.Label.CUSTOM"


@dataclasses.dataclass
class CustomSpec:
    class Label(enum.Enum):
        ARG = enum.auto()
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

    kind: typing.Literal[NodeKind.CUSTOMSPEC] = NodeKind.CUSTOMSPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CustomArg | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.CustomArg | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.CustomArg | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.CustomSpec) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, CustomArg | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.CustomArg | _cstp.Trivia) -> None:
        if not isinstance(child, CustomArg | Trivia):
            msg = f"CustomSpec: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, CustomSpec.Label)):
            _cn = "CustomSpec"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.CustomArg | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, CustomArg | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CustomSpec.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.CustomArg | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CustomSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_arg(self, child: _cstp.CustomArg) -> None:
        entry: typing.Any = (CustomSpec.Label.ARG, child)
        self.children.append(entry)

    def extend_arg(self, children: typing.Iterable[_cstp.CustomArg]) -> None:
        entries: typing.Any = ((CustomSpec.Label.ARG, child) for child in children)
        self.children.extend(entries)

    def children_arg(self) -> typing.Iterator[CustomArg]:
        return (typing.cast("CustomArg", child) for (label, child) in self.children if label == CustomSpec.Label.ARG)

    def child_arg(self) -> CustomArg:
        children = list(self.children_arg())
        if (n := len(children)) != 1:
            msg = f"Expected one arg child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_arg(self) -> CustomArg | None:
        children = list(self.children_arg())
        if (n := len(children)) > 1:
            msg = f"Expected at most one arg child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def arg(self) -> list[CustomArg]:
        return list(self.children_arg())


CustomSpec.Label.ARG._fltk_canonical_name = "CustomSpec.Label.ARG"


@dataclasses.dataclass
class CustomArg:
    class Label(enum.Enum):
        KEY = enum.auto()
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

    kind: typing.Literal[NodeKind.CUSTOMARG] = NodeKind.CUSTOMARG
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | String | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Identifier | _cstp.String | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.String | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.CustomArg) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | String | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.String | _cstp.Trivia) -> None:
        if not isinstance(child, Identifier | String | Trivia):
            msg = f"CustomArg: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, CustomArg.Label)):
            _cn = "CustomArg"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.String | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | String | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CustomArg.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.String | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CustomArg.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_key(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (CustomArg.Label.KEY, child)
        self.children.append(entry)

    def extend_key(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((CustomArg.Label.KEY, child) for child in children)
        self.children.extend(entries)

    def children_key(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == CustomArg.Label.KEY)

    def child_key(self) -> Identifier:
        children = list(self.children_key())
        if (n := len(children)) != 1:
            msg = f"Expected one key child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_key(self) -> Identifier | None:
        children = list(self.children_key())
        if (n := len(children)) > 1:
            msg = f"Expected at most one key child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_value(self, child: _cstp.String) -> None:
        entry: typing.Any = (CustomArg.Label.VALUE, child)
        self.children.append(entry)

    def extend_value(self, children: typing.Iterable[_cstp.String]) -> None:
        entries: typing.Any = ((CustomArg.Label.VALUE, child) for child in children)
        self.children.extend(entries)

    def children_value(self) -> typing.Iterator[String]:
        return (typing.cast("String", child) for (label, child) in self.children if label == CustomArg.Label.VALUE)

    def child_value(self) -> String:
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> String | None:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def key(self) -> Identifier:
        return self.child_key()

    def value(self) -> String:
        return self.child_value()


CustomArg.Label.KEY._fltk_canonical_name = "CustomArg.Label.KEY"
CustomArg.Label.VALUE._fltk_canonical_name = "CustomArg.Label.VALUE"


@dataclasses.dataclass
class BoolStmt:
    class Label(enum.Enum):
        TRUTHY = enum.auto()
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

    kind: typing.Literal[NodeKind.BOOLSTMT] = NodeKind.BOOLSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.BoolStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Trivia) -> None:
        if not isinstance(child, Identifier | Trivia):
            msg = f"BoolStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, BoolStmt.Label)):
            _cn = "BoolStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"BoolStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"BoolStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_truthy(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (BoolStmt.Label.TRUTHY, child)
        self.children.append(entry)

    def extend_truthy(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((BoolStmt.Label.TRUTHY, child) for child in children)
        self.children.extend(entries)

    def children_truthy(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == BoolStmt.Label.TRUTHY)

    def child_truthy(self) -> Identifier:
        children = list(self.children_truthy())
        if (n := len(children)) != 1:
            msg = f"Expected one truthy child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_truthy(self) -> Identifier | None:
        children = list(self.children_truthy())
        if (n := len(children)) > 1:
            msg = f"Expected at most one truthy child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def truthy(self) -> Identifier:
        return self.child_truthy()


BoolStmt.Label.TRUTHY._fltk_canonical_name = "BoolStmt.Label.TRUTHY"


@dataclasses.dataclass
class TransparentStmt:
    kind: typing.Literal[NodeKind.TRANSPARENTSTMT] = NodeKind.TRANSPARENTSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[None, Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: _cstp.Trivia, label: None = None) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(self, children: typing.Iterable[_cstp.Trivia], label: None = None) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.TransparentStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia) -> None:
        if not isinstance(child, Trivia):
            msg = f"TransparentStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"TransparentStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
            raise TypeError(msg)

    def insert(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[None, Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TransparentStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TransparentStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def text(self) -> str:
        return self.span.text_or_raise()


@dataclasses.dataclass
class TextFromStmt:
    class Label(enum.Enum):
        LABEL = enum.auto()
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

    kind: typing.Literal[NodeKind.TEXTFROMSTMT] = NodeKind.TEXTFROMSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.TextFromStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Trivia) -> None:
        if not isinstance(child, Identifier | Trivia):
            msg = f"TextFromStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, TextFromStmt.Label)):
            _cn = "TextFromStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TextFromStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TextFromStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_label(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (TextFromStmt.Label.LABEL, child)
        self.children.append(entry)

    def extend_label(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((TextFromStmt.Label.LABEL, child) for child in children)
        self.children.extend(entries)

    def children_label(self) -> typing.Iterator[Identifier]:
        return (
            typing.cast("Identifier", child) for (label, child) in self.children if label == TextFromStmt.Label.LABEL
        )

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

    def label(self) -> Identifier:
        return self.child_label()


TextFromStmt.Label.LABEL._fltk_canonical_name = "TextFromStmt.Label.LABEL"


@dataclasses.dataclass
class KeyStmt:
    class Label(enum.Enum):
        LABEL = enum.auto()
        MULTI = enum.auto()
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

    kind: typing.Literal[NodeKind.KEYSTMT] = NodeKind.KEYSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.Identifier | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.KeyStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.Identifier | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
        _allowed = KeyStmt._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (Identifier, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            KeyStmt._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            KeyStmt._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = KeyStmt._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"KeyStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, KeyStmt.Label)):
            _cn = "KeyStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(
        self, index: int
    ) -> tuple[Label | None, Identifier | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"KeyStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"KeyStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_label(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (KeyStmt.Label.LABEL, child)
        self.children.append(entry)

    def extend_label(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((KeyStmt.Label.LABEL, child) for child in children)
        self.children.extend(entries)

    def children_label(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == KeyStmt.Label.LABEL)

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

    def append_multi(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((KeyStmt.Label.MULTI, child))

    def extend_multi(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((KeyStmt.Label.MULTI, child) for child in children)

    def children_multi(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == KeyStmt.Label.MULTI
        )

    def child_multi(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_multi())
        if (n := len(children)) != 1:
            msg = f"Expected one multi child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_multi(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_multi())
        if (n := len(children)) > 1:
            msg = f"Expected at most one multi child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def label(self) -> Identifier:
        return self.child_label()

    def multi(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_multi()

    def multi_text(self) -> str | None:
        child = self.maybe_multi()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "KeyStmt.multi_text: child labelled 'multi' is not a Span"
            raise TypeError(msg) from None


KeyStmt.Label.LABEL._fltk_canonical_name = "KeyStmt.Label.LABEL"
KeyStmt.Label.MULTI._fltk_canonical_name = "KeyStmt.Label.MULTI"


@dataclasses.dataclass
class FoldStmt:
    class Label(enum.Enum):
        DIR = enum.auto()
        OP = enum.auto()
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

    kind: typing.Literal[NodeKind.FOLDSTMT] = NodeKind.FOLDSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FoldDir | Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.FoldDir | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.FoldDir | _cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.FoldStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, FoldDir | Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.FoldDir | _cstp.Identifier | _cstp.Trivia) -> None:
        if not isinstance(child, FoldDir | Identifier | Trivia):
            msg = f"FoldStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, FoldStmt.Label)):
            _cn = "FoldStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.FoldDir | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, FoldDir | Identifier | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FoldStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.FoldDir | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FoldStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_dir(self, child: _cstp.FoldDir) -> None:
        entry: typing.Any = (FoldStmt.Label.DIR, child)
        self.children.append(entry)

    def extend_dir(self, children: typing.Iterable[_cstp.FoldDir]) -> None:
        entries: typing.Any = ((FoldStmt.Label.DIR, child) for child in children)
        self.children.extend(entries)

    def children_dir(self) -> typing.Iterator[FoldDir]:
        return (typing.cast("FoldDir", child) for (label, child) in self.children if label == FoldStmt.Label.DIR)

    def child_dir(self) -> FoldDir:
        children = list(self.children_dir())
        if (n := len(children)) != 1:
            msg = f"Expected one dir child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_dir(self) -> FoldDir | None:
        children = list(self.children_dir())
        if (n := len(children)) > 1:
            msg = f"Expected at most one dir child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_op(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (FoldStmt.Label.OP, child)
        self.children.append(entry)

    def extend_op(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((FoldStmt.Label.OP, child) for child in children)
        self.children.extend(entries)

    def children_op(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == FoldStmt.Label.OP)

    def child_op(self) -> Identifier:
        children = list(self.children_op())
        if (n := len(children)) != 1:
            msg = f"Expected one op child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_op(self) -> Identifier | None:
        children = list(self.children_op())
        if (n := len(children)) > 1:
            msg = f"Expected at most one op child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def dir(self) -> FoldDir:
        return self.child_dir()

    def op(self) -> Identifier:
        return self.child_op()


FoldStmt.Label.DIR._fltk_canonical_name = "FoldStmt.Label.DIR"
FoldStmt.Label.OP._fltk_canonical_name = "FoldStmt.Label.OP"


@dataclasses.dataclass
class FoldDir:
    class Label(enum.Enum):
        LEFT = enum.auto()
        RIGHT = enum.auto()
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

    kind: typing.Literal[NodeKind.FOLDDIR] = NodeKind.FOLDDIR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.FoldDir) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = FoldDir._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            FoldDir._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            FoldDir._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = FoldDir._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"FoldDir: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, FoldDir.Label)):
            _cn = "FoldDir"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FoldDir.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FoldDir.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_left(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((FoldDir.Label.LEFT, child))

    def extend_left(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((FoldDir.Label.LEFT, child) for child in children)

    def children_left(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == FoldDir.Label.LEFT)

    def child_left(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_left())
        if (n := len(children)) != 1:
            msg = f"Expected one left child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_left(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_left())
        if (n := len(children)) > 1:
            msg = f"Expected at most one left child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_right(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((FoldDir.Label.RIGHT, child))

    def extend_right(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((FoldDir.Label.RIGHT, child) for child in children)

    def children_right(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == FoldDir.Label.RIGHT)

    def child_right(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_right())
        if (n := len(children)) != 1:
            msg = f"Expected one right child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_right(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_right())
        if (n := len(children)) > 1:
            msg = f"Expected at most one right child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def left(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_left()

    def left_text(self) -> str | None:
        child = self.maybe_left()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "FoldDir.left_text: child labelled 'left' is not a Span"
            raise TypeError(msg) from None

    def right(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_right()

    def right_text(self) -> str | None:
        child = self.maybe_right()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "FoldDir.right_text: child labelled 'right' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "FoldDir.variant: node has no labeled child"
        raise ValueError(msg)


FoldDir.Label.LEFT._fltk_canonical_name = "FoldDir.Label.LEFT"
FoldDir.Label.RIGHT._fltk_canonical_name = "FoldDir.Label.RIGHT"


@dataclasses.dataclass
class FlattenStmt:
    kind: typing.Literal[NodeKind.FLATTENSTMT] = NodeKind.FLATTENSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[None, Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: _cstp.Trivia, label: None = None) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(self, children: typing.Iterable[_cstp.Trivia], label: None = None) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.FlattenStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia) -> None:
        if not isinstance(child, Trivia):
            msg = f"FlattenStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"FlattenStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
            raise TypeError(msg)

    def insert(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[None, Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FlattenStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FlattenStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def text(self) -> str:
        return self.span.text_or_raise()


@dataclasses.dataclass
class CustomStmt:
    class Label(enum.Enum):
        ARG = enum.auto()
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

    kind: typing.Literal[NodeKind.CUSTOMSTMT] = NodeKind.CUSTOMSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CustomArg | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.CustomArg | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.CustomArg | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.CustomStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, CustomArg | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.CustomArg | _cstp.Trivia) -> None:
        if not isinstance(child, CustomArg | Trivia):
            msg = f"CustomStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, CustomStmt.Label)):
            _cn = "CustomStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.CustomArg | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, CustomArg | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CustomStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.CustomArg | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CustomStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_arg(self, child: _cstp.CustomArg) -> None:
        entry: typing.Any = (CustomStmt.Label.ARG, child)
        self.children.append(entry)

    def extend_arg(self, children: typing.Iterable[_cstp.CustomArg]) -> None:
        entries: typing.Any = ((CustomStmt.Label.ARG, child) for child in children)
        self.children.extend(entries)

    def children_arg(self) -> typing.Iterator[CustomArg]:
        return (typing.cast("CustomArg", child) for (label, child) in self.children if label == CustomStmt.Label.ARG)

    def child_arg(self) -> CustomArg:
        children = list(self.children_arg())
        if (n := len(children)) != 1:
            msg = f"Expected one arg child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_arg(self) -> CustomArg | None:
        children = list(self.children_arg())
        if (n := len(children)) > 1:
            msg = f"Expected at most one arg child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def arg(self) -> list[CustomArg]:
        return list(self.children_arg())


CustomStmt.Label.ARG._fltk_canonical_name = "CustomStmt.Label.ARG"


@dataclasses.dataclass
class NameStmt:
    class Label(enum.Enum):
        NEW_NAME = enum.auto()
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

    kind: typing.Literal[NodeKind.NAMESTMT] = NodeKind.NAMESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.NameStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Trivia) -> None:
        if not isinstance(child, Identifier | Trivia):
            msg = f"NameStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, NameStmt.Label)):
            _cn = "NameStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NameStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NameStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_new_name(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (NameStmt.Label.NEW_NAME, child)
        self.children.append(entry)

    def extend_new_name(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((NameStmt.Label.NEW_NAME, child) for child in children)
        self.children.extend(entries)

    def children_new_name(self) -> typing.Iterator[Identifier]:
        return (
            typing.cast("Identifier", child) for (label, child) in self.children if label == NameStmt.Label.NEW_NAME
        )

    def child_new_name(self) -> Identifier:
        children = list(self.children_new_name())
        if (n := len(children)) != 1:
            msg = f"Expected one new_name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_new_name(self) -> Identifier | None:
        children = list(self.children_new_name())
        if (n := len(children)) > 1:
            msg = f"Expected at most one new_name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def new_name(self) -> Identifier:
        return self.child_new_name()


NameStmt.Label.NEW_NAME._fltk_canonical_name = "NameStmt.Label.NEW_NAME"


@dataclasses.dataclass
class VariantStmt:
    class Label(enum.Enum):
        NEW_NAME = enum.auto()
        SELECTOR = enum.auto()
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

    kind: typing.Literal[NodeKind.VARIANTSTMT] = NodeKind.VARIANTSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.VariantStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Trivia) -> None:
        if not isinstance(child, Identifier | Trivia):
            msg = f"VariantStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, VariantStmt.Label)):
            _cn = "VariantStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"VariantStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"VariantStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_new_name(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (VariantStmt.Label.NEW_NAME, child)
        self.children.append(entry)

    def extend_new_name(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((VariantStmt.Label.NEW_NAME, child) for child in children)
        self.children.extend(entries)

    def children_new_name(self) -> typing.Iterator[Identifier]:
        return (
            typing.cast("Identifier", child) for (label, child) in self.children if label == VariantStmt.Label.NEW_NAME
        )

    def child_new_name(self) -> Identifier:
        children = list(self.children_new_name())
        if (n := len(children)) != 1:
            msg = f"Expected one new_name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_new_name(self) -> Identifier | None:
        children = list(self.children_new_name())
        if (n := len(children)) > 1:
            msg = f"Expected at most one new_name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_selector(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (VariantStmt.Label.SELECTOR, child)
        self.children.append(entry)

    def extend_selector(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((VariantStmt.Label.SELECTOR, child) for child in children)
        self.children.extend(entries)

    def children_selector(self) -> typing.Iterator[Identifier]:
        return (
            typing.cast("Identifier", child) for (label, child) in self.children if label == VariantStmt.Label.SELECTOR
        )

    def child_selector(self) -> Identifier:
        children = list(self.children_selector())
        if (n := len(children)) != 1:
            msg = f"Expected one selector child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_selector(self) -> Identifier | None:
        children = list(self.children_selector())
        if (n := len(children)) > 1:
            msg = f"Expected at most one selector child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def new_name(self) -> Identifier:
        return self.child_new_name()

    def selector(self) -> Identifier:
        return self.child_selector()


VariantStmt.Label.NEW_NAME._fltk_canonical_name = "VariantStmt.Label.NEW_NAME"
VariantStmt.Label.SELECTOR._fltk_canonical_name = "VariantStmt.Label.SELECTOR"


@dataclasses.dataclass
class FieldStmt:
    class Label(enum.Enum):
        FIELD_STATEMENT = enum.auto()
        LABEL = enum.auto()
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

    kind: typing.Literal[NodeKind.FIELDSTMT] = NodeKind.FIELDSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FieldStatement | Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.FieldStatement | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.FieldStatement | _cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.FieldStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, FieldStatement | Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.FieldStatement | _cstp.Identifier | _cstp.Trivia) -> None:
        if not isinstance(child, FieldStatement | Identifier | Trivia):
            msg = f"FieldStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, FieldStmt.Label)):
            _cn = "FieldStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.FieldStatement | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, FieldStatement | Identifier | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FieldStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.FieldStatement | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FieldStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_field_statement(self, child: _cstp.FieldStatement) -> None:
        entry: typing.Any = (FieldStmt.Label.FIELD_STATEMENT, child)
        self.children.append(entry)

    def extend_field_statement(self, children: typing.Iterable[_cstp.FieldStatement]) -> None:
        entries: typing.Any = ((FieldStmt.Label.FIELD_STATEMENT, child) for child in children)
        self.children.extend(entries)

    def children_field_statement(self) -> typing.Iterator[FieldStatement]:
        return (
            typing.cast("FieldStatement", child)
            for (label, child) in self.children
            if label == FieldStmt.Label.FIELD_STATEMENT
        )

    def child_field_statement(self) -> FieldStatement:
        children = list(self.children_field_statement())
        if (n := len(children)) != 1:
            msg = f"Expected one field_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_field_statement(self) -> FieldStatement | None:
        children = list(self.children_field_statement())
        if (n := len(children)) > 1:
            msg = f"Expected at most one field_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_label(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (FieldStmt.Label.LABEL, child)
        self.children.append(entry)

    def extend_label(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((FieldStmt.Label.LABEL, child) for child in children)
        self.children.extend(entries)

    def children_label(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == FieldStmt.Label.LABEL)

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

    def field_statement(self) -> list[FieldStatement]:
        return list(self.children_field_statement())

    def label(self) -> Identifier:
        return self.child_label()


FieldStmt.Label.FIELD_STATEMENT._fltk_canonical_name = "FieldStmt.Label.FIELD_STATEMENT"
FieldStmt.Label.LABEL._fltk_canonical_name = "FieldStmt.Label.LABEL"


@dataclasses.dataclass
class FieldStatement:
    class Label(enum.Enum):
        NAME_STMT = enum.auto()
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

    kind: typing.Literal[NodeKind.FIELDSTATEMENT] = NodeKind.FIELDSTATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, NameStmt]] = dataclasses.field(default_factory=list)

    def append(self, child: _cstp.NameStmt, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.NameStmt],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.FieldStatement) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, NameStmt]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.NameStmt) -> None:
        if not isinstance(child, NameStmt):
            msg = f"FieldStatement: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, FieldStatement.Label)):
            _cn = "FieldStatement"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.NameStmt, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, NameStmt]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FieldStatement.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.NameStmt, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FieldStatement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_name_stmt(self, child: _cstp.NameStmt) -> None:
        entry: typing.Any = (FieldStatement.Label.NAME_STMT, child)
        self.children.append(entry)

    def extend_name_stmt(self, children: typing.Iterable[_cstp.NameStmt]) -> None:
        entries: typing.Any = ((FieldStatement.Label.NAME_STMT, child) for child in children)
        self.children.extend(entries)

    def children_name_stmt(self) -> typing.Iterator[NameStmt]:
        return (child for (label, child) in self.children if label == FieldStatement.Label.NAME_STMT)

    def child_name_stmt(self) -> NameStmt:
        children = list(self.children_name_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one name_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name_stmt(self) -> NameStmt | None:
        children = list(self.children_name_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one name_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def name_stmt(self) -> NameStmt:
        return self.child_name_stmt()


FieldStatement.Label.NAME_STMT._fltk_canonical_name = "FieldStatement.Label.NAME_STMT"


@dataclasses.dataclass
class SumStmt:
    kind: typing.Literal[NodeKind.SUMSTMT] = NodeKind.SUMSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[None, Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: _cstp.Trivia, label: None = None) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(self, children: typing.Iterable[_cstp.Trivia], label: None = None) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.SumStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia) -> None:
        if not isinstance(child, Trivia):
            msg = f"SumStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"SumStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
            raise TypeError(msg)

    def insert(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[None, Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"SumStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"SumStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def text(self) -> str:
        return self.span.text_or_raise()


@dataclasses.dataclass
class ProductStmt:
    kind: typing.Literal[NodeKind.PRODUCTSTMT] = NodeKind.PRODUCTSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[None, Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: _cstp.Trivia, label: None = None) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(self, children: typing.Iterable[_cstp.Trivia], label: None = None) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.ProductStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia) -> None:
        if not isinstance(child, Trivia):
            msg = f"ProductStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"ProductStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
            raise TypeError(msg)

    def insert(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[None, Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ProductStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ProductStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def text(self) -> str:
        return self.span.text_or_raise()


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

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Identifier) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Identifier.Label)):
            _cn = "Identifier"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

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
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Identifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

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
class String:
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

    kind: typing.Literal[NodeKind.STRING] = NodeKind.STRING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.String) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = String._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            String._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            String._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = String._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"String: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, String.Label)):
            _cn = "String"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"String.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"String.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((String.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((String.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == String.Label.VALUE)

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
            msg = "String.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


String.Label.VALUE._fltk_canonical_name = "String.Label.VALUE"


@dataclasses.dataclass
class Trivia:
    class Label(enum.Enum):
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
    children: list[tuple[Label | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Trivia) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
        _allowed = Trivia._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (LineComment, fltk.fegen.pyrt.terminalsrc.Span)
            Trivia._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Trivia._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Trivia._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Trivia: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Trivia.Label)):
            _cn = "Trivia"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

    def remove_at(self, index: int) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
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
        child: _cstp.LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Trivia.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_line_comment(self, child: _cstp.LineComment) -> None:
        entry: typing.Any = (Trivia.Label.LINE_COMMENT, child)
        self.children.append(entry)

    def extend_line_comment(self, children: typing.Iterable[_cstp.LineComment]) -> None:
        entries: typing.Any = ((Trivia.Label.LINE_COMMENT, child) for child in children)
        self.children.extend(entries)

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

    def line_comment(self) -> list[LineComment]:
        return list(self.children_line_comment())


Trivia.Label.LINE_COMMENT._fltk_canonical_name = "Trivia.Label.LINE_COMMENT"


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
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.LineComment) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, LineComment.Label)):
            _cn = "LineComment"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        entry: typing.Any = (label, child)
        self.children.insert(idx, entry)

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
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LineComment.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

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

    def append_newline(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((LineComment.Label.NEWLINE, child))

    def extend_newline(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((LineComment.Label.NEWLINE, child) for child in children)

    def children_newline(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == LineComment.Label.NEWLINE)

    def child_newline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_newline())
        if (n := len(children)) != 1:
            msg = f"Expected one newline child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_newline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_newline())
        if (n := len(children)) > 1:
            msg = f"Expected at most one newline child but have {n}"
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
