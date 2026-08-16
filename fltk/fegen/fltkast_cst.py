from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import types
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


def _type_name_for_error(obj: object) -> str:
    t = type(obj)
    return f"{t.__module__}.{t.__qualname__}"


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"AstSpec.Label.STATEMENT": Label.STATEMENT})
    kind: typing.Literal[NodeKind.ASTSPEC] = NodeKind.ASTSPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Statement | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Statement | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, AstSpec.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Statement | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, AstSpec.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.AstSpec) -> None:
        if not isinstance(other, AstSpec):
            msg = f"AstSpec: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Statement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Statement | _cstp.Trivia) -> Statement | Trivia:
        if isinstance(child, Statement | Trivia):
            return child
        msg = f"AstSpec: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> AstSpec.Label | None:
        if label is None or isinstance(label, AstSpec.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = AstSpec._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "AstSpec"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Statement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, AstSpec.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, AstSpec.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"AstSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: AstSpec.Label) -> list[Statement | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_statement(self, child: _cstp.Statement) -> None:
        self.children.append((AstSpec.Label.STATEMENT, self._check_child_type_for_mutators(child)))

    def extend_statement(self, children: typing.Iterable[_cstp.Statement]) -> None:
        self.children.extend(
            [(AstSpec.Label.STATEMENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_statement(self) -> typing.Iterator[Statement]:
        return iter(typing.cast("list[Statement]", self._children_snapshot(AstSpec.Label.STATEMENT)))

    def child_statement(self) -> Statement:
        children = typing.cast("list[Statement]", self._children_snapshot(AstSpec.Label.STATEMENT))
        if (n := len(children)) != 1:
            msg = f"Expected one statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_statement(self) -> Statement | None:
        children = typing.cast("list[Statement]", self._children_snapshot(AstSpec.Label.STATEMENT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def statement(self) -> list[Statement]:
        return typing.cast("list[Statement]", self._children_snapshot(AstSpec.Label.STATEMENT))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Statement.Label.OPTION_STMT": Label.OPTION_STMT, "Statement.Label.RULE_CONFIG": Label.RULE_CONFIG}
    )
    kind: typing.Literal[NodeKind.STATEMENT] = NodeKind.STATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, OptionStmt | RuleConfig]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.OptionStmt | _cstp.RuleConfig,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Statement.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.OptionStmt | _cstp.RuleConfig],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Statement.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Statement) -> None:
        if not isinstance(other, Statement):
            msg = f"Statement: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, OptionStmt | RuleConfig]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.OptionStmt | _cstp.RuleConfig) -> OptionStmt | RuleConfig:
        if isinstance(child, OptionStmt | RuleConfig):
            return child
        msg = f"Statement: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Statement.Label | None:
        if label is None or isinstance(label, Statement.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Statement._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Statement"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.OptionStmt | _cstp.RuleConfig,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Statement.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Statement.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Statement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Statement.Label) -> list[OptionStmt | RuleConfig]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_option_stmt(self, child: _cstp.OptionStmt) -> None:
        self.children.append((Statement.Label.OPTION_STMT, self._check_child_type_for_mutators(child)))

    def extend_option_stmt(self, children: typing.Iterable[_cstp.OptionStmt]) -> None:
        self.children.extend(
            [(Statement.Label.OPTION_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_option_stmt(self) -> typing.Iterator[OptionStmt]:
        return iter(typing.cast("list[OptionStmt]", self._children_snapshot(Statement.Label.OPTION_STMT)))

    def child_option_stmt(self) -> OptionStmt:
        children = typing.cast("list[OptionStmt]", self._children_snapshot(Statement.Label.OPTION_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one option_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_option_stmt(self) -> OptionStmt | None:
        children = typing.cast("list[OptionStmt]", self._children_snapshot(Statement.Label.OPTION_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one option_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_rule_config(self, child: _cstp.RuleConfig) -> None:
        self.children.append((Statement.Label.RULE_CONFIG, self._check_child_type_for_mutators(child)))

    def extend_rule_config(self, children: typing.Iterable[_cstp.RuleConfig]) -> None:
        self.children.extend(
            [(Statement.Label.RULE_CONFIG, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_rule_config(self) -> typing.Iterator[RuleConfig]:
        return iter(typing.cast("list[RuleConfig]", self._children_snapshot(Statement.Label.RULE_CONFIG)))

    def child_rule_config(self) -> RuleConfig:
        children = typing.cast("list[RuleConfig]", self._children_snapshot(Statement.Label.RULE_CONFIG))
        if (n := len(children)) != 1:
            msg = f"Expected one rule_config child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule_config(self) -> RuleConfig | None:
        children = typing.cast("list[RuleConfig]", self._children_snapshot(Statement.Label.RULE_CONFIG))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"OptionStmt.Label.KEY": Label.KEY, "OptionStmt.Label.VALUE": Label.VALUE}
    )
    kind: typing.Literal[NodeKind.OPTIONSTMT] = NodeKind.OPTIONSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | OptionValue | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Identifier | _cstp.OptionValue | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, OptionStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.OptionValue | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, OptionStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.OptionStmt) -> None:
        if not isinstance(other, OptionStmt):
            msg = f"OptionStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | OptionValue | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Identifier | _cstp.OptionValue | _cstp.Trivia
    ) -> Identifier | OptionValue | Trivia:
        if isinstance(child, Identifier | OptionValue | Trivia):
            return child
        msg = f"OptionStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> OptionStmt.Label | None:
        if label is None or isinstance(label, OptionStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = OptionStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "OptionStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.OptionValue | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, OptionStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, OptionStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"OptionStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: OptionStmt.Label) -> list[Identifier | OptionValue | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_key(self, child: _cstp.Identifier) -> None:
        self.children.append((OptionStmt.Label.KEY, self._check_child_type_for_mutators(child)))

    def extend_key(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend([(OptionStmt.Label.KEY, self._check_child_type_for_mutators(child)) for child in children])

    def children_key(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(OptionStmt.Label.KEY)))

    def child_key(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(OptionStmt.Label.KEY))
        if (n := len(children)) != 1:
            msg = f"Expected one key child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_key(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(OptionStmt.Label.KEY))
        if (n := len(children)) > 1:
            msg = f"Expected at most one key child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_value(self, child: _cstp.OptionValue) -> None:
        self.children.append((OptionStmt.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[_cstp.OptionValue]) -> None:
        self.children.extend(
            [(OptionStmt.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[OptionValue]:
        return iter(typing.cast("list[OptionValue]", self._children_snapshot(OptionStmt.Label.VALUE)))

    def child_value(self) -> OptionValue:
        children = typing.cast("list[OptionValue]", self._children_snapshot(OptionStmt.Label.VALUE))
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> OptionValue | None:
        children = typing.cast("list[OptionValue]", self._children_snapshot(OptionStmt.Label.VALUE))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "OptionValue.Label.FALSE": Label.FALSE,
            "OptionValue.Label.STRING": Label.STRING,
            "OptionValue.Label.TRUE": Label.TRUE,
        }
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, OptionValue.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.String | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, OptionValue.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.OptionValue) -> None:
        if not isinstance(other, OptionValue):
            msg = f"OptionValue: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, String | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.String | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> String | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, String | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"OptionValue: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> OptionValue.Label | None:
        if label is None or isinstance(label, OptionValue.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = OptionValue._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "OptionValue"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.String | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, OptionValue.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, OptionValue.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"OptionValue.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: OptionValue.Label) -> list[String | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_false(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((OptionValue.Label.FALSE, self._check_child_type_for_mutators(child)))

    def extend_false(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(OptionValue.Label.FALSE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_false(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(OptionValue.Label.FALSE)
            )
        )

    def child_false(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(OptionValue.Label.FALSE)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one false child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_false(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(OptionValue.Label.FALSE)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one false child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_string(self, child: _cstp.String) -> None:
        self.children.append((OptionValue.Label.STRING, self._check_child_type_for_mutators(child)))

    def extend_string(self, children: typing.Iterable[_cstp.String]) -> None:
        self.children.extend(
            [(OptionValue.Label.STRING, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_string(self) -> typing.Iterator[String]:
        return iter(typing.cast("list[String]", self._children_snapshot(OptionValue.Label.STRING)))

    def child_string(self) -> String:
        children = typing.cast("list[String]", self._children_snapshot(OptionValue.Label.STRING))
        if (n := len(children)) != 1:
            msg = f"Expected one string child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_string(self) -> String | None:
        children = typing.cast("list[String]", self._children_snapshot(OptionValue.Label.STRING))
        if (n := len(children)) > 1:
            msg = f"Expected at most one string child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_true(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((OptionValue.Label.TRUE, self._check_child_type_for_mutators(child)))

    def extend_true(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(OptionValue.Label.TRUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_true(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(OptionValue.Label.TRUE)
            )
        )

    def child_true(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(OptionValue.Label.TRUE)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one true child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_true(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(OptionValue.Label.TRUE)
        )
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"RuleConfig.Label.RULE_NAME": Label.RULE_NAME, "RuleConfig.Label.RULE_STATEMENT": Label.RULE_STATEMENT}
    )
    kind: typing.Literal[NodeKind.RULECONFIG] = NodeKind.RULECONFIG
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | RuleStatement | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Identifier | _cstp.RuleStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RuleConfig.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.RuleStatement | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RuleConfig.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.RuleConfig) -> None:
        if not isinstance(other, RuleConfig):
            msg = f"RuleConfig: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | RuleStatement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Identifier | _cstp.RuleStatement | _cstp.Trivia
    ) -> Identifier | RuleStatement | Trivia:
        if isinstance(child, Identifier | RuleStatement | Trivia):
            return child
        msg = f"RuleConfig: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> RuleConfig.Label | None:
        if label is None or isinstance(label, RuleConfig.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = RuleConfig._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "RuleConfig"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.RuleStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RuleConfig.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, RuleConfig.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleConfig.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: RuleConfig.Label) -> list[Identifier | RuleStatement | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_rule_name(self, child: _cstp.Identifier) -> None:
        self.children.append((RuleConfig.Label.RULE_NAME, self._check_child_type_for_mutators(child)))

    def extend_rule_name(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(RuleConfig.Label.RULE_NAME, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_rule_name(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(RuleConfig.Label.RULE_NAME)))

    def child_rule_name(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(RuleConfig.Label.RULE_NAME))
        if (n := len(children)) != 1:
            msg = f"Expected one rule_name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule_name(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(RuleConfig.Label.RULE_NAME))
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule_name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_rule_statement(self, child: _cstp.RuleStatement) -> None:
        self.children.append((RuleConfig.Label.RULE_STATEMENT, self._check_child_type_for_mutators(child)))

    def extend_rule_statement(self, children: typing.Iterable[_cstp.RuleStatement]) -> None:
        self.children.extend(
            [(RuleConfig.Label.RULE_STATEMENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_rule_statement(self) -> typing.Iterator[RuleStatement]:
        return iter(typing.cast("list[RuleStatement]", self._children_snapshot(RuleConfig.Label.RULE_STATEMENT)))

    def child_rule_statement(self) -> RuleStatement:
        children = typing.cast("list[RuleStatement]", self._children_snapshot(RuleConfig.Label.RULE_STATEMENT))
        if (n := len(children)) != 1:
            msg = f"Expected one rule_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule_statement(self) -> RuleStatement | None:
        children = typing.cast("list[RuleStatement]", self._children_snapshot(RuleConfig.Label.RULE_STATEMENT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def rule_name(self) -> Identifier:
        return self.child_rule_name()

    def rule_statement(self) -> list[RuleStatement]:
        return typing.cast("list[RuleStatement]", self._children_snapshot(RuleConfig.Label.RULE_STATEMENT))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "RuleStatement.Label.BOOL_STMT": Label.BOOL_STMT,
            "RuleStatement.Label.CUSTOM_STMT": Label.CUSTOM_STMT,
            "RuleStatement.Label.FIELD_STMT": Label.FIELD_STMT,
            "RuleStatement.Label.FLATTEN_STMT": Label.FLATTEN_STMT,
            "RuleStatement.Label.FOLD_STMT": Label.FOLD_STMT,
            "RuleStatement.Label.KEY_STMT": Label.KEY_STMT,
            "RuleStatement.Label.NAME_STMT": Label.NAME_STMT,
            "RuleStatement.Label.PRODUCT_STMT": Label.PRODUCT_STMT,
            "RuleStatement.Label.SUM_STMT": Label.SUM_STMT,
            "RuleStatement.Label.TEXT_FROM_STMT": Label.TEXT_FROM_STMT,
            "RuleStatement.Label.TRANSPARENT_STMT": Label.TRANSPARENT_STMT,
            "RuleStatement.Label.TYPE_STMT": Label.TYPE_STMT,
            "RuleStatement.Label.VARIANT_STMT": Label.VARIANT_STMT,
        }
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, RuleStatement.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

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
        checked_label = (
            label
            if label is None or isinstance(label, RuleStatement.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.RuleStatement) -> None:
        if not isinstance(other, RuleStatement):
            msg = f"RuleStatement: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

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
    ) -> (
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
        | VariantStmt
    ):
        if isinstance(
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
            return child
        msg = f"RuleStatement: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> RuleStatement.Label | None:
        if label is None or isinstance(label, RuleStatement.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = RuleStatement._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
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
        checked_label = (
            label
            if label is None or isinstance(label, RuleStatement.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, RuleStatement.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleStatement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: RuleStatement.Label
    ) -> list[
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
        | VariantStmt
    ]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_bool_stmt(self, child: _cstp.BoolStmt) -> None:
        self.children.append((RuleStatement.Label.BOOL_STMT, self._check_child_type_for_mutators(child)))

    def extend_bool_stmt(self, children: typing.Iterable[_cstp.BoolStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.BOOL_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_bool_stmt(self) -> typing.Iterator[BoolStmt]:
        return iter(typing.cast("list[BoolStmt]", self._children_snapshot(RuleStatement.Label.BOOL_STMT)))

    def child_bool_stmt(self) -> BoolStmt:
        children = typing.cast("list[BoolStmt]", self._children_snapshot(RuleStatement.Label.BOOL_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one bool_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_bool_stmt(self) -> BoolStmt | None:
        children = typing.cast("list[BoolStmt]", self._children_snapshot(RuleStatement.Label.BOOL_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one bool_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_custom_stmt(self, child: _cstp.CustomStmt) -> None:
        self.children.append((RuleStatement.Label.CUSTOM_STMT, self._check_child_type_for_mutators(child)))

    def extend_custom_stmt(self, children: typing.Iterable[_cstp.CustomStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.CUSTOM_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_custom_stmt(self) -> typing.Iterator[CustomStmt]:
        return iter(typing.cast("list[CustomStmt]", self._children_snapshot(RuleStatement.Label.CUSTOM_STMT)))

    def child_custom_stmt(self) -> CustomStmt:
        children = typing.cast("list[CustomStmt]", self._children_snapshot(RuleStatement.Label.CUSTOM_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one custom_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_custom_stmt(self) -> CustomStmt | None:
        children = typing.cast("list[CustomStmt]", self._children_snapshot(RuleStatement.Label.CUSTOM_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one custom_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_field_stmt(self, child: _cstp.FieldStmt) -> None:
        self.children.append((RuleStatement.Label.FIELD_STMT, self._check_child_type_for_mutators(child)))

    def extend_field_stmt(self, children: typing.Iterable[_cstp.FieldStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.FIELD_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_field_stmt(self) -> typing.Iterator[FieldStmt]:
        return iter(typing.cast("list[FieldStmt]", self._children_snapshot(RuleStatement.Label.FIELD_STMT)))

    def child_field_stmt(self) -> FieldStmt:
        children = typing.cast("list[FieldStmt]", self._children_snapshot(RuleStatement.Label.FIELD_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one field_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_field_stmt(self) -> FieldStmt | None:
        children = typing.cast("list[FieldStmt]", self._children_snapshot(RuleStatement.Label.FIELD_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one field_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_flatten_stmt(self, child: _cstp.FlattenStmt) -> None:
        self.children.append((RuleStatement.Label.FLATTEN_STMT, self._check_child_type_for_mutators(child)))

    def extend_flatten_stmt(self, children: typing.Iterable[_cstp.FlattenStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.FLATTEN_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_flatten_stmt(self) -> typing.Iterator[FlattenStmt]:
        return iter(typing.cast("list[FlattenStmt]", self._children_snapshot(RuleStatement.Label.FLATTEN_STMT)))

    def child_flatten_stmt(self) -> FlattenStmt:
        children = typing.cast("list[FlattenStmt]", self._children_snapshot(RuleStatement.Label.FLATTEN_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one flatten_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_flatten_stmt(self) -> FlattenStmt | None:
        children = typing.cast("list[FlattenStmt]", self._children_snapshot(RuleStatement.Label.FLATTEN_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one flatten_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_fold_stmt(self, child: _cstp.FoldStmt) -> None:
        self.children.append((RuleStatement.Label.FOLD_STMT, self._check_child_type_for_mutators(child)))

    def extend_fold_stmt(self, children: typing.Iterable[_cstp.FoldStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.FOLD_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_fold_stmt(self) -> typing.Iterator[FoldStmt]:
        return iter(typing.cast("list[FoldStmt]", self._children_snapshot(RuleStatement.Label.FOLD_STMT)))

    def child_fold_stmt(self) -> FoldStmt:
        children = typing.cast("list[FoldStmt]", self._children_snapshot(RuleStatement.Label.FOLD_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one fold_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_fold_stmt(self) -> FoldStmt | None:
        children = typing.cast("list[FoldStmt]", self._children_snapshot(RuleStatement.Label.FOLD_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one fold_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_key_stmt(self, child: _cstp.KeyStmt) -> None:
        self.children.append((RuleStatement.Label.KEY_STMT, self._check_child_type_for_mutators(child)))

    def extend_key_stmt(self, children: typing.Iterable[_cstp.KeyStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.KEY_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_key_stmt(self) -> typing.Iterator[KeyStmt]:
        return iter(typing.cast("list[KeyStmt]", self._children_snapshot(RuleStatement.Label.KEY_STMT)))

    def child_key_stmt(self) -> KeyStmt:
        children = typing.cast("list[KeyStmt]", self._children_snapshot(RuleStatement.Label.KEY_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one key_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_key_stmt(self) -> KeyStmt | None:
        children = typing.cast("list[KeyStmt]", self._children_snapshot(RuleStatement.Label.KEY_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one key_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_name_stmt(self, child: _cstp.NameStmt) -> None:
        self.children.append((RuleStatement.Label.NAME_STMT, self._check_child_type_for_mutators(child)))

    def extend_name_stmt(self, children: typing.Iterable[_cstp.NameStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.NAME_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_name_stmt(self) -> typing.Iterator[NameStmt]:
        return iter(typing.cast("list[NameStmt]", self._children_snapshot(RuleStatement.Label.NAME_STMT)))

    def child_name_stmt(self) -> NameStmt:
        children = typing.cast("list[NameStmt]", self._children_snapshot(RuleStatement.Label.NAME_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one name_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name_stmt(self) -> NameStmt | None:
        children = typing.cast("list[NameStmt]", self._children_snapshot(RuleStatement.Label.NAME_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one name_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_product_stmt(self, child: _cstp.ProductStmt) -> None:
        self.children.append((RuleStatement.Label.PRODUCT_STMT, self._check_child_type_for_mutators(child)))

    def extend_product_stmt(self, children: typing.Iterable[_cstp.ProductStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.PRODUCT_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_product_stmt(self) -> typing.Iterator[ProductStmt]:
        return iter(typing.cast("list[ProductStmt]", self._children_snapshot(RuleStatement.Label.PRODUCT_STMT)))

    def child_product_stmt(self) -> ProductStmt:
        children = typing.cast("list[ProductStmt]", self._children_snapshot(RuleStatement.Label.PRODUCT_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one product_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_product_stmt(self) -> ProductStmt | None:
        children = typing.cast("list[ProductStmt]", self._children_snapshot(RuleStatement.Label.PRODUCT_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one product_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_sum_stmt(self, child: _cstp.SumStmt) -> None:
        self.children.append((RuleStatement.Label.SUM_STMT, self._check_child_type_for_mutators(child)))

    def extend_sum_stmt(self, children: typing.Iterable[_cstp.SumStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.SUM_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_sum_stmt(self) -> typing.Iterator[SumStmt]:
        return iter(typing.cast("list[SumStmt]", self._children_snapshot(RuleStatement.Label.SUM_STMT)))

    def child_sum_stmt(self) -> SumStmt:
        children = typing.cast("list[SumStmt]", self._children_snapshot(RuleStatement.Label.SUM_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one sum_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_sum_stmt(self) -> SumStmt | None:
        children = typing.cast("list[SumStmt]", self._children_snapshot(RuleStatement.Label.SUM_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one sum_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_text_from_stmt(self, child: _cstp.TextFromStmt) -> None:
        self.children.append((RuleStatement.Label.TEXT_FROM_STMT, self._check_child_type_for_mutators(child)))

    def extend_text_from_stmt(self, children: typing.Iterable[_cstp.TextFromStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.TEXT_FROM_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_text_from_stmt(self) -> typing.Iterator[TextFromStmt]:
        return iter(typing.cast("list[TextFromStmt]", self._children_snapshot(RuleStatement.Label.TEXT_FROM_STMT)))

    def child_text_from_stmt(self) -> TextFromStmt:
        children = typing.cast("list[TextFromStmt]", self._children_snapshot(RuleStatement.Label.TEXT_FROM_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one text_from_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_text_from_stmt(self) -> TextFromStmt | None:
        children = typing.cast("list[TextFromStmt]", self._children_snapshot(RuleStatement.Label.TEXT_FROM_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one text_from_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_transparent_stmt(self, child: _cstp.TransparentStmt) -> None:
        self.children.append((RuleStatement.Label.TRANSPARENT_STMT, self._check_child_type_for_mutators(child)))

    def extend_transparent_stmt(self, children: typing.Iterable[_cstp.TransparentStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.TRANSPARENT_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_transparent_stmt(self) -> typing.Iterator[TransparentStmt]:
        return iter(typing.cast("list[TransparentStmt]", self._children_snapshot(RuleStatement.Label.TRANSPARENT_STMT)))

    def child_transparent_stmt(self) -> TransparentStmt:
        children = typing.cast("list[TransparentStmt]", self._children_snapshot(RuleStatement.Label.TRANSPARENT_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one transparent_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_transparent_stmt(self) -> TransparentStmt | None:
        children = typing.cast("list[TransparentStmt]", self._children_snapshot(RuleStatement.Label.TRANSPARENT_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one transparent_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_type_stmt(self, child: _cstp.TypeStmt) -> None:
        self.children.append((RuleStatement.Label.TYPE_STMT, self._check_child_type_for_mutators(child)))

    def extend_type_stmt(self, children: typing.Iterable[_cstp.TypeStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.TYPE_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_type_stmt(self) -> typing.Iterator[TypeStmt]:
        return iter(typing.cast("list[TypeStmt]", self._children_snapshot(RuleStatement.Label.TYPE_STMT)))

    def child_type_stmt(self) -> TypeStmt:
        children = typing.cast("list[TypeStmt]", self._children_snapshot(RuleStatement.Label.TYPE_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one type_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_type_stmt(self) -> TypeStmt | None:
        children = typing.cast("list[TypeStmt]", self._children_snapshot(RuleStatement.Label.TYPE_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one type_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_variant_stmt(self, child: _cstp.VariantStmt) -> None:
        self.children.append((RuleStatement.Label.VARIANT_STMT, self._check_child_type_for_mutators(child)))

    def extend_variant_stmt(self, children: typing.Iterable[_cstp.VariantStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.VARIANT_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_variant_stmt(self) -> typing.Iterator[VariantStmt]:
        return iter(typing.cast("list[VariantStmt]", self._children_snapshot(RuleStatement.Label.VARIANT_STMT)))

    def child_variant_stmt(self) -> VariantStmt:
        children = typing.cast("list[VariantStmt]", self._children_snapshot(RuleStatement.Label.VARIANT_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one variant_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_variant_stmt(self) -> VariantStmt | None:
        children = typing.cast("list[VariantStmt]", self._children_snapshot(RuleStatement.Label.VARIANT_STMT))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"TypeStmt.Label.SPEC": Label.SPEC})
    kind: typing.Literal[NodeKind.TYPESTMT] = NodeKind.TYPESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Trivia | TypeSpec]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Trivia | _cstp.TypeSpec, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TypeStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Trivia | _cstp.TypeSpec],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TypeStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.TypeStmt) -> None:
        if not isinstance(other, TypeStmt):
            msg = f"TypeStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Trivia | TypeSpec]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia | _cstp.TypeSpec) -> Trivia | TypeSpec:
        if isinstance(child, Trivia | TypeSpec):
            return child
        msg = f"TypeStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> TypeStmt.Label | None:
        if label is None or isinstance(label, TypeStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = TypeStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "TypeStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Trivia | _cstp.TypeSpec,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TypeStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, TypeStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TypeStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: TypeStmt.Label) -> list[Trivia | TypeSpec]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_spec(self, child: _cstp.TypeSpec) -> None:
        self.children.append((TypeStmt.Label.SPEC, self._check_child_type_for_mutators(child)))

    def extend_spec(self, children: typing.Iterable[_cstp.TypeSpec]) -> None:
        self.children.extend([(TypeStmt.Label.SPEC, self._check_child_type_for_mutators(child)) for child in children])

    def children_spec(self) -> typing.Iterator[TypeSpec]:
        return iter(typing.cast("list[TypeSpec]", self._children_snapshot(TypeStmt.Label.SPEC)))

    def child_spec(self) -> TypeSpec:
        children = typing.cast("list[TypeSpec]", self._children_snapshot(TypeStmt.Label.SPEC))
        if (n := len(children)) != 1:
            msg = f"Expected one spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spec(self) -> TypeSpec | None:
        children = typing.cast("list[TypeSpec]", self._children_snapshot(TypeStmt.Label.SPEC))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"TypeSpec.Label.BUILTIN": Label.BUILTIN, "TypeSpec.Label.CUSTOM": Label.CUSTOM}
    )
    kind: typing.Literal[NodeKind.TYPESPEC] = NodeKind.TYPESPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CustomSpec | Identifier]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.CustomSpec | _cstp.Identifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TypeSpec.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.CustomSpec | _cstp.Identifier],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TypeSpec.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.TypeSpec) -> None:
        if not isinstance(other, TypeSpec):
            msg = f"TypeSpec: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, CustomSpec | Identifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.CustomSpec | _cstp.Identifier) -> CustomSpec | Identifier:
        if isinstance(child, CustomSpec | Identifier):
            return child
        msg = f"TypeSpec: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> TypeSpec.Label | None:
        if label is None or isinstance(label, TypeSpec.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = TypeSpec._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "TypeSpec"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.CustomSpec | _cstp.Identifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TypeSpec.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, TypeSpec.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TypeSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: TypeSpec.Label) -> list[CustomSpec | Identifier]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_builtin(self, child: _cstp.Identifier) -> None:
        self.children.append((TypeSpec.Label.BUILTIN, self._check_child_type_for_mutators(child)))

    def extend_builtin(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(TypeSpec.Label.BUILTIN, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_builtin(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(TypeSpec.Label.BUILTIN)))

    def child_builtin(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(TypeSpec.Label.BUILTIN))
        if (n := len(children)) != 1:
            msg = f"Expected one builtin child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_builtin(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(TypeSpec.Label.BUILTIN))
        if (n := len(children)) > 1:
            msg = f"Expected at most one builtin child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_custom(self, child: _cstp.CustomSpec) -> None:
        self.children.append((TypeSpec.Label.CUSTOM, self._check_child_type_for_mutators(child)))

    def extend_custom(self, children: typing.Iterable[_cstp.CustomSpec]) -> None:
        self.children.extend(
            [(TypeSpec.Label.CUSTOM, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_custom(self) -> typing.Iterator[CustomSpec]:
        return iter(typing.cast("list[CustomSpec]", self._children_snapshot(TypeSpec.Label.CUSTOM)))

    def child_custom(self) -> CustomSpec:
        children = typing.cast("list[CustomSpec]", self._children_snapshot(TypeSpec.Label.CUSTOM))
        if (n := len(children)) != 1:
            msg = f"Expected one custom child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_custom(self) -> CustomSpec | None:
        children = typing.cast("list[CustomSpec]", self._children_snapshot(TypeSpec.Label.CUSTOM))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"CustomSpec.Label.ARG": Label.ARG})
    kind: typing.Literal[NodeKind.CUSTOMSPEC] = NodeKind.CUSTOMSPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CustomArg | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.CustomArg | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CustomSpec.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.CustomArg | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CustomSpec.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.CustomSpec) -> None:
        if not isinstance(other, CustomSpec):
            msg = f"CustomSpec: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, CustomArg | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.CustomArg | _cstp.Trivia) -> CustomArg | Trivia:
        if isinstance(child, CustomArg | Trivia):
            return child
        msg = f"CustomSpec: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> CustomSpec.Label | None:
        if label is None or isinstance(label, CustomSpec.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = CustomSpec._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "CustomSpec"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.CustomArg | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CustomSpec.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, CustomSpec.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CustomSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: CustomSpec.Label) -> list[CustomArg | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_arg(self, child: _cstp.CustomArg) -> None:
        self.children.append((CustomSpec.Label.ARG, self._check_child_type_for_mutators(child)))

    def extend_arg(self, children: typing.Iterable[_cstp.CustomArg]) -> None:
        self.children.extend([(CustomSpec.Label.ARG, self._check_child_type_for_mutators(child)) for child in children])

    def children_arg(self) -> typing.Iterator[CustomArg]:
        return iter(typing.cast("list[CustomArg]", self._children_snapshot(CustomSpec.Label.ARG)))

    def child_arg(self) -> CustomArg:
        children = typing.cast("list[CustomArg]", self._children_snapshot(CustomSpec.Label.ARG))
        if (n := len(children)) != 1:
            msg = f"Expected one arg child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_arg(self) -> CustomArg | None:
        children = typing.cast("list[CustomArg]", self._children_snapshot(CustomSpec.Label.ARG))
        if (n := len(children)) > 1:
            msg = f"Expected at most one arg child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def arg(self) -> list[CustomArg]:
        return typing.cast("list[CustomArg]", self._children_snapshot(CustomSpec.Label.ARG))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"CustomArg.Label.KEY": Label.KEY, "CustomArg.Label.VALUE": Label.VALUE}
    )
    kind: typing.Literal[NodeKind.CUSTOMARG] = NodeKind.CUSTOMARG
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | String | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Identifier | _cstp.String | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CustomArg.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.String | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CustomArg.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.CustomArg) -> None:
        if not isinstance(other, CustomArg):
            msg = f"CustomArg: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | String | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Identifier | _cstp.String | _cstp.Trivia
    ) -> Identifier | String | Trivia:
        if isinstance(child, Identifier | String | Trivia):
            return child
        msg = f"CustomArg: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> CustomArg.Label | None:
        if label is None or isinstance(label, CustomArg.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = CustomArg._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "CustomArg"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.String | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CustomArg.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, CustomArg.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CustomArg.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: CustomArg.Label) -> list[Identifier | String | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_key(self, child: _cstp.Identifier) -> None:
        self.children.append((CustomArg.Label.KEY, self._check_child_type_for_mutators(child)))

    def extend_key(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend([(CustomArg.Label.KEY, self._check_child_type_for_mutators(child)) for child in children])

    def children_key(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(CustomArg.Label.KEY)))

    def child_key(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(CustomArg.Label.KEY))
        if (n := len(children)) != 1:
            msg = f"Expected one key child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_key(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(CustomArg.Label.KEY))
        if (n := len(children)) > 1:
            msg = f"Expected at most one key child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_value(self, child: _cstp.String) -> None:
        self.children.append((CustomArg.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[_cstp.String]) -> None:
        self.children.extend(
            [(CustomArg.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[String]:
        return iter(typing.cast("list[String]", self._children_snapshot(CustomArg.Label.VALUE)))

    def child_value(self) -> String:
        children = typing.cast("list[String]", self._children_snapshot(CustomArg.Label.VALUE))
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> String | None:
        children = typing.cast("list[String]", self._children_snapshot(CustomArg.Label.VALUE))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"BoolStmt.Label.TRUTHY": Label.TRUTHY})
    kind: typing.Literal[NodeKind.BOOLSTMT] = NodeKind.BOOLSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, BoolStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, BoolStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.BoolStmt) -> None:
        if not isinstance(other, BoolStmt):
            msg = f"BoolStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Trivia) -> Identifier | Trivia:
        if isinstance(child, Identifier | Trivia):
            return child
        msg = f"BoolStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> BoolStmt.Label | None:
        if label is None or isinstance(label, BoolStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = BoolStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "BoolStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, BoolStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, BoolStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"BoolStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: BoolStmt.Label) -> list[Identifier | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_truthy(self, child: _cstp.Identifier) -> None:
        self.children.append((BoolStmt.Label.TRUTHY, self._check_child_type_for_mutators(child)))

    def extend_truthy(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(BoolStmt.Label.TRUTHY, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_truthy(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(BoolStmt.Label.TRUTHY)))

    def child_truthy(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(BoolStmt.Label.TRUTHY))
        if (n := len(children)) != 1:
            msg = f"Expected one truthy child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_truthy(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(BoolStmt.Label.TRUTHY))
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
        if label is not None:
            self._check_label_type_for_mutators(label, "append")
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((None, checked_child))

    def extend(self, children: typing.Iterable[_cstp.Trivia], label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "extend")
        self.children.extend([(None, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.TransparentStmt) -> None:
        if not isinstance(other, TransparentStmt):
            msg = f"TransparentStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia) -> Trivia:
        if isinstance(child, Trivia):
            return child
        msg = f"TransparentStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"TransparentStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
            raise TypeError(msg)

    def insert(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "insert")
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (None, checked_child))

    def remove_at(self, index: int) -> tuple[None, Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TransparentStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "replace_at")
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TransparentStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (None, checked_child)

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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"TextFromStmt.Label.LABEL": Label.LABEL})
    kind: typing.Literal[NodeKind.TEXTFROMSTMT] = NodeKind.TEXTFROMSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TextFromStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TextFromStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.TextFromStmt) -> None:
        if not isinstance(other, TextFromStmt):
            msg = f"TextFromStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Trivia) -> Identifier | Trivia:
        if isinstance(child, Identifier | Trivia):
            return child
        msg = f"TextFromStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> TextFromStmt.Label | None:
        if label is None or isinstance(label, TextFromStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = TextFromStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "TextFromStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TextFromStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, TextFromStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TextFromStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: TextFromStmt.Label) -> list[Identifier | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_label(self, child: _cstp.Identifier) -> None:
        self.children.append((TextFromStmt.Label.LABEL, self._check_child_type_for_mutators(child)))

    def extend_label(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(TextFromStmt.Label.LABEL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_label(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(TextFromStmt.Label.LABEL)))

    def child_label(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(TextFromStmt.Label.LABEL))
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(TextFromStmt.Label.LABEL))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"KeyStmt.Label.LABEL": Label.LABEL, "KeyStmt.Label.MULTI": Label.MULTI}
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, KeyStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, KeyStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.KeyStmt) -> None:
        if not isinstance(other, KeyStmt):
            msg = f"KeyStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Identifier | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> Identifier | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, Identifier | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"KeyStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> KeyStmt.Label | None:
        if label is None or isinstance(label, KeyStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = KeyStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "KeyStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, KeyStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, KeyStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"KeyStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: KeyStmt.Label
    ) -> list[Identifier | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_label(self, child: _cstp.Identifier) -> None:
        self.children.append((KeyStmt.Label.LABEL, self._check_child_type_for_mutators(child)))

    def extend_label(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend([(KeyStmt.Label.LABEL, self._check_child_type_for_mutators(child)) for child in children])

    def children_label(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(KeyStmt.Label.LABEL)))

    def child_label(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(KeyStmt.Label.LABEL))
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(KeyStmt.Label.LABEL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one label child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_multi(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((KeyStmt.Label.MULTI, self._check_child_type_for_mutators(child)))

    def extend_multi(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(KeyStmt.Label.MULTI, self._check_child_type_for_mutators(child)) for child in children])

    def children_multi(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(KeyStmt.Label.MULTI)
            )
        )

    def child_multi(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(KeyStmt.Label.MULTI)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one multi child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_multi(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(KeyStmt.Label.MULTI)
        )
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"FoldStmt.Label.DIR": Label.DIR, "FoldStmt.Label.OP": Label.OP})
    kind: typing.Literal[NodeKind.FOLDSTMT] = NodeKind.FOLDSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FoldDir | Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.FoldDir | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FoldStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.FoldDir | _cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FoldStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.FoldStmt) -> None:
        if not isinstance(other, FoldStmt):
            msg = f"FoldStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, FoldDir | Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.FoldDir | _cstp.Identifier | _cstp.Trivia
    ) -> FoldDir | Identifier | Trivia:
        if isinstance(child, FoldDir | Identifier | Trivia):
            return child
        msg = f"FoldStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> FoldStmt.Label | None:
        if label is None or isinstance(label, FoldStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = FoldStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "FoldStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.FoldDir | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FoldStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, FoldStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FoldStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: FoldStmt.Label) -> list[FoldDir | Identifier | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_dir(self, child: _cstp.FoldDir) -> None:
        self.children.append((FoldStmt.Label.DIR, self._check_child_type_for_mutators(child)))

    def extend_dir(self, children: typing.Iterable[_cstp.FoldDir]) -> None:
        self.children.extend([(FoldStmt.Label.DIR, self._check_child_type_for_mutators(child)) for child in children])

    def children_dir(self) -> typing.Iterator[FoldDir]:
        return iter(typing.cast("list[FoldDir]", self._children_snapshot(FoldStmt.Label.DIR)))

    def child_dir(self) -> FoldDir:
        children = typing.cast("list[FoldDir]", self._children_snapshot(FoldStmt.Label.DIR))
        if (n := len(children)) != 1:
            msg = f"Expected one dir child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_dir(self) -> FoldDir | None:
        children = typing.cast("list[FoldDir]", self._children_snapshot(FoldStmt.Label.DIR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one dir child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_op(self, child: _cstp.Identifier) -> None:
        self.children.append((FoldStmt.Label.OP, self._check_child_type_for_mutators(child)))

    def extend_op(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend([(FoldStmt.Label.OP, self._check_child_type_for_mutators(child)) for child in children])

    def children_op(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(FoldStmt.Label.OP)))

    def child_op(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(FoldStmt.Label.OP))
        if (n := len(children)) != 1:
            msg = f"Expected one op child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_op(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(FoldStmt.Label.OP))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"FoldDir.Label.LEFT": Label.LEFT, "FoldDir.Label.RIGHT": Label.RIGHT}
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, FoldDir.Label)
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
            if label is None or isinstance(label, FoldDir.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.FoldDir) -> None:
        if not isinstance(other, FoldDir):
            msg = f"FoldDir: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"FoldDir: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> FoldDir.Label | None:
        if label is None or isinstance(label, FoldDir.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = FoldDir._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "FoldDir"
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
            if label is None or isinstance(label, FoldDir.Label)
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
            msg = f"FoldDir.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, FoldDir.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FoldDir.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: FoldDir.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_left(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((FoldDir.Label.LEFT, self._check_child_type_for_mutators(child)))

    def extend_left(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(FoldDir.Label.LEFT, self._check_child_type_for_mutators(child)) for child in children])

    def children_left(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(FoldDir.Label.LEFT))

    def child_left(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(FoldDir.Label.LEFT)
        if (n := len(children)) != 1:
            msg = f"Expected one left child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_left(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(FoldDir.Label.LEFT)
        if (n := len(children)) > 1:
            msg = f"Expected at most one left child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_right(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((FoldDir.Label.RIGHT, self._check_child_type_for_mutators(child)))

    def extend_right(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(FoldDir.Label.RIGHT, self._check_child_type_for_mutators(child)) for child in children])

    def children_right(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(FoldDir.Label.RIGHT))

    def child_right(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(FoldDir.Label.RIGHT)
        if (n := len(children)) != 1:
            msg = f"Expected one right child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_right(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(FoldDir.Label.RIGHT)
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
        if label is not None:
            self._check_label_type_for_mutators(label, "append")
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((None, checked_child))

    def extend(self, children: typing.Iterable[_cstp.Trivia], label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "extend")
        self.children.extend([(None, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.FlattenStmt) -> None:
        if not isinstance(other, FlattenStmt):
            msg = f"FlattenStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia) -> Trivia:
        if isinstance(child, Trivia):
            return child
        msg = f"FlattenStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"FlattenStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
            raise TypeError(msg)

    def insert(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "insert")
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (None, checked_child))

    def remove_at(self, index: int) -> tuple[None, Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FlattenStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "replace_at")
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FlattenStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (None, checked_child)

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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"CustomStmt.Label.ARG": Label.ARG})
    kind: typing.Literal[NodeKind.CUSTOMSTMT] = NodeKind.CUSTOMSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CustomArg | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.CustomArg | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CustomStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.CustomArg | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CustomStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.CustomStmt) -> None:
        if not isinstance(other, CustomStmt):
            msg = f"CustomStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, CustomArg | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.CustomArg | _cstp.Trivia) -> CustomArg | Trivia:
        if isinstance(child, CustomArg | Trivia):
            return child
        msg = f"CustomStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> CustomStmt.Label | None:
        if label is None or isinstance(label, CustomStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = CustomStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "CustomStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.CustomArg | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CustomStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, CustomStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CustomStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: CustomStmt.Label) -> list[CustomArg | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_arg(self, child: _cstp.CustomArg) -> None:
        self.children.append((CustomStmt.Label.ARG, self._check_child_type_for_mutators(child)))

    def extend_arg(self, children: typing.Iterable[_cstp.CustomArg]) -> None:
        self.children.extend([(CustomStmt.Label.ARG, self._check_child_type_for_mutators(child)) for child in children])

    def children_arg(self) -> typing.Iterator[CustomArg]:
        return iter(typing.cast("list[CustomArg]", self._children_snapshot(CustomStmt.Label.ARG)))

    def child_arg(self) -> CustomArg:
        children = typing.cast("list[CustomArg]", self._children_snapshot(CustomStmt.Label.ARG))
        if (n := len(children)) != 1:
            msg = f"Expected one arg child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_arg(self) -> CustomArg | None:
        children = typing.cast("list[CustomArg]", self._children_snapshot(CustomStmt.Label.ARG))
        if (n := len(children)) > 1:
            msg = f"Expected at most one arg child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def arg(self) -> list[CustomArg]:
        return typing.cast("list[CustomArg]", self._children_snapshot(CustomStmt.Label.ARG))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"NameStmt.Label.NEW_NAME": Label.NEW_NAME})
    kind: typing.Literal[NodeKind.NAMESTMT] = NodeKind.NAMESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, NameStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, NameStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.NameStmt) -> None:
        if not isinstance(other, NameStmt):
            msg = f"NameStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Trivia) -> Identifier | Trivia:
        if isinstance(child, Identifier | Trivia):
            return child
        msg = f"NameStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> NameStmt.Label | None:
        if label is None or isinstance(label, NameStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = NameStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "NameStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, NameStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, NameStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NameStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: NameStmt.Label) -> list[Identifier | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_new_name(self, child: _cstp.Identifier) -> None:
        self.children.append((NameStmt.Label.NEW_NAME, self._check_child_type_for_mutators(child)))

    def extend_new_name(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(NameStmt.Label.NEW_NAME, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_new_name(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(NameStmt.Label.NEW_NAME)))

    def child_new_name(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(NameStmt.Label.NEW_NAME))
        if (n := len(children)) != 1:
            msg = f"Expected one new_name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_new_name(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(NameStmt.Label.NEW_NAME))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"VariantStmt.Label.NEW_NAME": Label.NEW_NAME, "VariantStmt.Label.SELECTOR": Label.SELECTOR}
    )
    kind: typing.Literal[NodeKind.VARIANTSTMT] = NodeKind.VARIANTSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, VariantStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, VariantStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.VariantStmt) -> None:
        if not isinstance(other, VariantStmt):
            msg = f"VariantStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Trivia) -> Identifier | Trivia:
        if isinstance(child, Identifier | Trivia):
            return child
        msg = f"VariantStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> VariantStmt.Label | None:
        if label is None or isinstance(label, VariantStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = VariantStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "VariantStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, VariantStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, VariantStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"VariantStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: VariantStmt.Label) -> list[Identifier | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_new_name(self, child: _cstp.Identifier) -> None:
        self.children.append((VariantStmt.Label.NEW_NAME, self._check_child_type_for_mutators(child)))

    def extend_new_name(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(VariantStmt.Label.NEW_NAME, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_new_name(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(VariantStmt.Label.NEW_NAME)))

    def child_new_name(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(VariantStmt.Label.NEW_NAME))
        if (n := len(children)) != 1:
            msg = f"Expected one new_name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_new_name(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(VariantStmt.Label.NEW_NAME))
        if (n := len(children)) > 1:
            msg = f"Expected at most one new_name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_selector(self, child: _cstp.Identifier) -> None:
        self.children.append((VariantStmt.Label.SELECTOR, self._check_child_type_for_mutators(child)))

    def extend_selector(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(VariantStmt.Label.SELECTOR, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_selector(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(VariantStmt.Label.SELECTOR)))

    def child_selector(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(VariantStmt.Label.SELECTOR))
        if (n := len(children)) != 1:
            msg = f"Expected one selector child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_selector(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(VariantStmt.Label.SELECTOR))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"FieldStmt.Label.FIELD_STATEMENT": Label.FIELD_STATEMENT, "FieldStmt.Label.LABEL": Label.LABEL}
    )
    kind: typing.Literal[NodeKind.FIELDSTMT] = NodeKind.FIELDSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FieldStatement | Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.FieldStatement | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FieldStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.FieldStatement | _cstp.Identifier | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FieldStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.FieldStmt) -> None:
        if not isinstance(other, FieldStmt):
            msg = f"FieldStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, FieldStatement | Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.FieldStatement | _cstp.Identifier | _cstp.Trivia
    ) -> FieldStatement | Identifier | Trivia:
        if isinstance(child, FieldStatement | Identifier | Trivia):
            return child
        msg = f"FieldStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> FieldStmt.Label | None:
        if label is None or isinstance(label, FieldStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = FieldStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "FieldStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.FieldStatement | _cstp.Identifier | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FieldStmt.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, FieldStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FieldStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: FieldStmt.Label) -> list[FieldStatement | Identifier | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_field_statement(self, child: _cstp.FieldStatement) -> None:
        self.children.append((FieldStmt.Label.FIELD_STATEMENT, self._check_child_type_for_mutators(child)))

    def extend_field_statement(self, children: typing.Iterable[_cstp.FieldStatement]) -> None:
        self.children.extend(
            [(FieldStmt.Label.FIELD_STATEMENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_field_statement(self) -> typing.Iterator[FieldStatement]:
        return iter(typing.cast("list[FieldStatement]", self._children_snapshot(FieldStmt.Label.FIELD_STATEMENT)))

    def child_field_statement(self) -> FieldStatement:
        children = typing.cast("list[FieldStatement]", self._children_snapshot(FieldStmt.Label.FIELD_STATEMENT))
        if (n := len(children)) != 1:
            msg = f"Expected one field_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_field_statement(self) -> FieldStatement | None:
        children = typing.cast("list[FieldStatement]", self._children_snapshot(FieldStmt.Label.FIELD_STATEMENT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one field_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_label(self, child: _cstp.Identifier) -> None:
        self.children.append((FieldStmt.Label.LABEL, self._check_child_type_for_mutators(child)))

    def extend_label(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(FieldStmt.Label.LABEL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_label(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(FieldStmt.Label.LABEL)))

    def child_label(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(FieldStmt.Label.LABEL))
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(FieldStmt.Label.LABEL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one label child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def field_statement(self) -> list[FieldStatement]:
        return typing.cast("list[FieldStatement]", self._children_snapshot(FieldStmt.Label.FIELD_STATEMENT))

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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"FieldStatement.Label.NAME_STMT": Label.NAME_STMT})
    kind: typing.Literal[NodeKind.FIELDSTATEMENT] = NodeKind.FIELDSTATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, NameStmt]] = dataclasses.field(default_factory=list)

    def append(self, child: _cstp.NameStmt, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FieldStatement.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.NameStmt],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FieldStatement.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.FieldStatement) -> None:
        if not isinstance(other, FieldStatement):
            msg = f"FieldStatement: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, NameStmt]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.NameStmt) -> NameStmt:
        if isinstance(child, NameStmt):
            return child
        msg = f"FieldStatement: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> FieldStatement.Label | None:
        if label is None or isinstance(label, FieldStatement.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = FieldStatement._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "FieldStatement"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.NameStmt, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FieldStatement.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, FieldStatement.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FieldStatement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: FieldStatement.Label) -> list[NameStmt]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_name_stmt(self, child: _cstp.NameStmt) -> None:
        self.children.append((FieldStatement.Label.NAME_STMT, self._check_child_type_for_mutators(child)))

    def extend_name_stmt(self, children: typing.Iterable[_cstp.NameStmt]) -> None:
        self.children.extend(
            [(FieldStatement.Label.NAME_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_name_stmt(self) -> typing.Iterator[NameStmt]:
        return iter(self._children_snapshot(FieldStatement.Label.NAME_STMT))

    def child_name_stmt(self) -> NameStmt:
        children = self._children_snapshot(FieldStatement.Label.NAME_STMT)
        if (n := len(children)) != 1:
            msg = f"Expected one name_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name_stmt(self) -> NameStmt | None:
        children = self._children_snapshot(FieldStatement.Label.NAME_STMT)
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
        if label is not None:
            self._check_label_type_for_mutators(label, "append")
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((None, checked_child))

    def extend(self, children: typing.Iterable[_cstp.Trivia], label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "extend")
        self.children.extend([(None, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.SumStmt) -> None:
        if not isinstance(other, SumStmt):
            msg = f"SumStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia) -> Trivia:
        if isinstance(child, Trivia):
            return child
        msg = f"SumStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"SumStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
            raise TypeError(msg)

    def insert(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "insert")
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (None, checked_child))

    def remove_at(self, index: int) -> tuple[None, Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"SumStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "replace_at")
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"SumStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (None, checked_child)

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
        if label is not None:
            self._check_label_type_for_mutators(label, "append")
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((None, checked_child))

    def extend(self, children: typing.Iterable[_cstp.Trivia], label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "extend")
        self.children.extend([(None, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ProductStmt) -> None:
        if not isinstance(other, ProductStmt):
            msg = f"ProductStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia) -> Trivia:
        if isinstance(child, Trivia):
            return child
        msg = f"ProductStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"ProductStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
            raise TypeError(msg)

    def insert(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "insert")
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (None, checked_child))

    def remove_at(self, index: int) -> tuple[None, Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ProductStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        if label is not None:
            self._check_label_type_for_mutators(label, "replace_at")
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ProductStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (None, checked_child)

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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"String.Label.VALUE": Label.VALUE})
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
        checked_label = (
            label
            if label is None or isinstance(label, String.Label)
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
            if label is None or isinstance(label, String.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.String) -> None:
        if not isinstance(other, String):
            msg = f"String: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"String: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> String.Label | None:
        if label is None or isinstance(label, String.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = String._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "String"
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
            if label is None or isinstance(label, String.Label)
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
            msg = f"String.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, String.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"String.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: String.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((String.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(String.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children])

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(String.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(String.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(String.Label.VALUE)
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Trivia.Label.LINE_COMMENT": Label.LINE_COMMENT})
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
        checked_label = (
            label
            if label is None or isinstance(label, Trivia.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol],
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

    def child(self) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, LineComment | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
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
        child: _cstp.LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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

    def _children_snapshot(self, label: Trivia.Label) -> list[LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

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

    def line_comment(self) -> list[LineComment]:
        return typing.cast("list[LineComment]", self._children_snapshot(Trivia.Label.LINE_COMMENT))


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
