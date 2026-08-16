from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import types
import typing

import fltk.fegen.pyrt.terminalsrc
from fltk.lsp.fltklsp_cst_protocol import NodeKind

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol
    import fltk.lsp.fltklsp_cst_protocol as _cstp


def _get_native_span_type():
    m = sys.modules.get("fltk._native")
    return m.Span if m is not None else None


def _type_name_for_error(obj: object) -> str:
    t = type(obj)
    return f"{t.__module__}.{t.__qualname__}"


@dataclasses.dataclass
class LspSpec:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"LspSpec.Label.STATEMENT": Label.STATEMENT})
    kind: typing.Literal[NodeKind.LSPSPEC] = NodeKind.LSPSPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Statement | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Statement | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, LspSpec.Label)
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
            if label is None or isinstance(label, LspSpec.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.LspSpec) -> None:
        if not isinstance(other, LspSpec):
            msg = f"LspSpec: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"LspSpec: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> LspSpec.Label | None:
        if label is None or isinstance(label, LspSpec.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = LspSpec._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "LspSpec"
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
            if label is None or isinstance(label, LspSpec.Label)
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
            msg = f"LspSpec.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, LspSpec.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LspSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: LspSpec.Label) -> list[Statement | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_statement(self, child: _cstp.Statement) -> None:
        self.children.append((LspSpec.Label.STATEMENT, self._check_child_type_for_mutators(child)))

    def extend_statement(self, children: typing.Iterable[_cstp.Statement]) -> None:
        self.children.extend(
            [(LspSpec.Label.STATEMENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_statement(self) -> typing.Iterator[Statement]:
        return iter(typing.cast("list[Statement]", self._children_snapshot(LspSpec.Label.STATEMENT)))

    def child_statement(self) -> Statement:
        children = typing.cast("list[Statement]", self._children_snapshot(LspSpec.Label.STATEMENT))
        if (n := len(children)) != 1:
            msg = f"Expected one statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_statement(self) -> Statement | None:
        children = typing.cast("list[Statement]", self._children_snapshot(LspSpec.Label.STATEMENT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def statement(self) -> list[Statement]:
        return typing.cast("list[Statement]", self._children_snapshot(LspSpec.Label.STATEMENT))


LspSpec.Label.STATEMENT._fltk_canonical_name = "LspSpec.Label.STATEMENT"


@dataclasses.dataclass
class Statement:
    class Label(enum.Enum):
        RULE_CONFIG = enum.auto()
        SCOPE_STMT = enum.auto()
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
        {"Statement.Label.RULE_CONFIG": Label.RULE_CONFIG, "Statement.Label.SCOPE_STMT": Label.SCOPE_STMT}
    )
    kind: typing.Literal[NodeKind.STATEMENT] = NodeKind.STATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, RuleConfig | ScopeStmt]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.RuleConfig | _cstp.ScopeStmt,
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
        children: typing.Iterable[_cstp.RuleConfig | _cstp.ScopeStmt],
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

    def child(self) -> tuple[Label | None, RuleConfig | ScopeStmt]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.RuleConfig | _cstp.ScopeStmt) -> RuleConfig | ScopeStmt:
        if isinstance(child, RuleConfig | ScopeStmt):
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
        child: _cstp.RuleConfig | _cstp.ScopeStmt,
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

    def remove_at(self, index: int) -> tuple[Label | None, RuleConfig | ScopeStmt]:
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
        child: _cstp.RuleConfig | _cstp.ScopeStmt,
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

    def _children_snapshot(self, label: Statement.Label) -> list[RuleConfig | ScopeStmt]:
        return [child for (lbl, child) in self.children if lbl == label]

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

    def append_scope_stmt(self, child: _cstp.ScopeStmt) -> None:
        self.children.append((Statement.Label.SCOPE_STMT, self._check_child_type_for_mutators(child)))

    def extend_scope_stmt(self, children: typing.Iterable[_cstp.ScopeStmt]) -> None:
        self.children.extend(
            [(Statement.Label.SCOPE_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_scope_stmt(self) -> typing.Iterator[ScopeStmt]:
        return iter(typing.cast("list[ScopeStmt]", self._children_snapshot(Statement.Label.SCOPE_STMT)))

    def child_scope_stmt(self) -> ScopeStmt:
        children = typing.cast("list[ScopeStmt]", self._children_snapshot(Statement.Label.SCOPE_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one scope_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_scope_stmt(self) -> ScopeStmt | None:
        children = typing.cast("list[ScopeStmt]", self._children_snapshot(Statement.Label.SCOPE_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one scope_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def rule_config(self) -> RuleConfig | None:
        return self.maybe_rule_config()

    def scope_stmt(self) -> ScopeStmt | None:
        return self.maybe_scope_stmt()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Statement.variant: node has no labeled child"
        raise ValueError(msg)


Statement.Label.RULE_CONFIG._fltk_canonical_name = "Statement.Label.RULE_CONFIG"
Statement.Label.SCOPE_STMT._fltk_canonical_name = "Statement.Label.SCOPE_STMT"


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
        DEF_STMT = enum.auto()
        NAMESPACE_STMT = enum.auto()
        REF_STMT = enum.auto()
        SCOPE_STMT = enum.auto()
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
            "RuleStatement.Label.DEF_STMT": Label.DEF_STMT,
            "RuleStatement.Label.NAMESPACE_STMT": Label.NAMESPACE_STMT,
            "RuleStatement.Label.REF_STMT": Label.REF_STMT,
            "RuleStatement.Label.SCOPE_STMT": Label.SCOPE_STMT,
        }
    )
    kind: typing.Literal[NodeKind.RULESTATEMENT] = NodeKind.RULESTATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.DefStmt | _cstp.NamespaceStmt | _cstp.RefStmt | _cstp.ScopeStmt,
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
        children: typing.Iterable[_cstp.DefStmt | _cstp.NamespaceStmt | _cstp.RefStmt | _cstp.ScopeStmt],
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

    def child(self) -> tuple[Label | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.DefStmt | _cstp.NamespaceStmt | _cstp.RefStmt | _cstp.ScopeStmt
    ) -> DefStmt | NamespaceStmt | RefStmt | ScopeStmt:
        if isinstance(child, DefStmt | NamespaceStmt | RefStmt | ScopeStmt):
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
        child: _cstp.DefStmt | _cstp.NamespaceStmt | _cstp.RefStmt | _cstp.ScopeStmt,
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

    def remove_at(self, index: int) -> tuple[Label | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]:
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
        child: _cstp.DefStmt | _cstp.NamespaceStmt | _cstp.RefStmt | _cstp.ScopeStmt,
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

    def _children_snapshot(self, label: RuleStatement.Label) -> list[DefStmt | NamespaceStmt | RefStmt | ScopeStmt]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_def_stmt(self, child: _cstp.DefStmt) -> None:
        self.children.append((RuleStatement.Label.DEF_STMT, self._check_child_type_for_mutators(child)))

    def extend_def_stmt(self, children: typing.Iterable[_cstp.DefStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.DEF_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_def_stmt(self) -> typing.Iterator[DefStmt]:
        return iter(typing.cast("list[DefStmt]", self._children_snapshot(RuleStatement.Label.DEF_STMT)))

    def child_def_stmt(self) -> DefStmt:
        children = typing.cast("list[DefStmt]", self._children_snapshot(RuleStatement.Label.DEF_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one def_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_def_stmt(self) -> DefStmt | None:
        children = typing.cast("list[DefStmt]", self._children_snapshot(RuleStatement.Label.DEF_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one def_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_namespace_stmt(self, child: _cstp.NamespaceStmt) -> None:
        self.children.append((RuleStatement.Label.NAMESPACE_STMT, self._check_child_type_for_mutators(child)))

    def extend_namespace_stmt(self, children: typing.Iterable[_cstp.NamespaceStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.NAMESPACE_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_namespace_stmt(self) -> typing.Iterator[NamespaceStmt]:
        return iter(typing.cast("list[NamespaceStmt]", self._children_snapshot(RuleStatement.Label.NAMESPACE_STMT)))

    def child_namespace_stmt(self) -> NamespaceStmt:
        children = typing.cast("list[NamespaceStmt]", self._children_snapshot(RuleStatement.Label.NAMESPACE_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one namespace_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_namespace_stmt(self) -> NamespaceStmt | None:
        children = typing.cast("list[NamespaceStmt]", self._children_snapshot(RuleStatement.Label.NAMESPACE_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one namespace_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ref_stmt(self, child: _cstp.RefStmt) -> None:
        self.children.append((RuleStatement.Label.REF_STMT, self._check_child_type_for_mutators(child)))

    def extend_ref_stmt(self, children: typing.Iterable[_cstp.RefStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.REF_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_ref_stmt(self) -> typing.Iterator[RefStmt]:
        return iter(typing.cast("list[RefStmt]", self._children_snapshot(RuleStatement.Label.REF_STMT)))

    def child_ref_stmt(self) -> RefStmt:
        children = typing.cast("list[RefStmt]", self._children_snapshot(RuleStatement.Label.REF_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one ref_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ref_stmt(self) -> RefStmt | None:
        children = typing.cast("list[RefStmt]", self._children_snapshot(RuleStatement.Label.REF_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one ref_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_scope_stmt(self, child: _cstp.ScopeStmt) -> None:
        self.children.append((RuleStatement.Label.SCOPE_STMT, self._check_child_type_for_mutators(child)))

    def extend_scope_stmt(self, children: typing.Iterable[_cstp.ScopeStmt]) -> None:
        self.children.extend(
            [(RuleStatement.Label.SCOPE_STMT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_scope_stmt(self) -> typing.Iterator[ScopeStmt]:
        return iter(typing.cast("list[ScopeStmt]", self._children_snapshot(RuleStatement.Label.SCOPE_STMT)))

    def child_scope_stmt(self) -> ScopeStmt:
        children = typing.cast("list[ScopeStmt]", self._children_snapshot(RuleStatement.Label.SCOPE_STMT))
        if (n := len(children)) != 1:
            msg = f"Expected one scope_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_scope_stmt(self) -> ScopeStmt | None:
        children = typing.cast("list[ScopeStmt]", self._children_snapshot(RuleStatement.Label.SCOPE_STMT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one scope_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def def_stmt(self) -> DefStmt | None:
        return self.maybe_def_stmt()

    def namespace_stmt(self) -> NamespaceStmt | None:
        return self.maybe_namespace_stmt()

    def ref_stmt(self) -> RefStmt | None:
        return self.maybe_ref_stmt()

    def scope_stmt(self) -> ScopeStmt | None:
        return self.maybe_scope_stmt()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "RuleStatement.variant: node has no labeled child"
        raise ValueError(msg)


RuleStatement.Label.DEF_STMT._fltk_canonical_name = "RuleStatement.Label.DEF_STMT"
RuleStatement.Label.NAMESPACE_STMT._fltk_canonical_name = "RuleStatement.Label.NAMESPACE_STMT"
RuleStatement.Label.REF_STMT._fltk_canonical_name = "RuleStatement.Label.REF_STMT"
RuleStatement.Label.SCOPE_STMT._fltk_canonical_name = "RuleStatement.Label.SCOPE_STMT"


@dataclasses.dataclass
class ScopeStmt:
    class Label(enum.Enum):
        ANCHOR_LIST = enum.auto()
        SCOPE = enum.auto()
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
        {"ScopeStmt.Label.ANCHOR_LIST": Label.ANCHOR_LIST, "ScopeStmt.Label.SCOPE": Label.SCOPE}
    )
    kind: typing.Literal[NodeKind.SCOPESTMT] = NodeKind.SCOPESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, AnchorList | DottedName | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.AnchorList | _cstp.DottedName | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ScopeStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.AnchorList | _cstp.DottedName | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ScopeStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ScopeStmt) -> None:
        if not isinstance(other, ScopeStmt):
            msg = f"ScopeStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, AnchorList | DottedName | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.AnchorList | _cstp.DottedName | _cstp.Trivia
    ) -> AnchorList | DottedName | Trivia:
        if isinstance(child, AnchorList | DottedName | Trivia):
            return child
        msg = f"ScopeStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ScopeStmt.Label | None:
        if label is None or isinstance(label, ScopeStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ScopeStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ScopeStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.AnchorList | _cstp.DottedName | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ScopeStmt.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, AnchorList | DottedName | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ScopeStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.AnchorList | _cstp.DottedName | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ScopeStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ScopeStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ScopeStmt.Label) -> list[AnchorList | DottedName | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor_list(self, child: _cstp.AnchorList) -> None:
        self.children.append((ScopeStmt.Label.ANCHOR_LIST, self._check_child_type_for_mutators(child)))

    def extend_anchor_list(self, children: typing.Iterable[_cstp.AnchorList]) -> None:
        self.children.extend(
            [(ScopeStmt.Label.ANCHOR_LIST, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_anchor_list(self) -> typing.Iterator[AnchorList]:
        return iter(typing.cast("list[AnchorList]", self._children_snapshot(ScopeStmt.Label.ANCHOR_LIST)))

    def child_anchor_list(self) -> AnchorList:
        children = typing.cast("list[AnchorList]", self._children_snapshot(ScopeStmt.Label.ANCHOR_LIST))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor_list child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor_list(self) -> AnchorList | None:
        children = typing.cast("list[AnchorList]", self._children_snapshot(ScopeStmt.Label.ANCHOR_LIST))
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor_list child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_scope(self, child: _cstp.DottedName) -> None:
        self.children.append((ScopeStmt.Label.SCOPE, self._check_child_type_for_mutators(child)))

    def extend_scope(self, children: typing.Iterable[_cstp.DottedName]) -> None:
        self.children.extend(
            [(ScopeStmt.Label.SCOPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_scope(self) -> typing.Iterator[DottedName]:
        return iter(typing.cast("list[DottedName]", self._children_snapshot(ScopeStmt.Label.SCOPE)))

    def child_scope(self) -> DottedName:
        children = typing.cast("list[DottedName]", self._children_snapshot(ScopeStmt.Label.SCOPE))
        if (n := len(children)) != 1:
            msg = f"Expected one scope child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_scope(self) -> DottedName | None:
        children = typing.cast("list[DottedName]", self._children_snapshot(ScopeStmt.Label.SCOPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one scope child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def anchor_list(self) -> AnchorList:
        return self.child_anchor_list()

    def scope(self) -> DottedName:
        return self.child_scope()


ScopeStmt.Label.ANCHOR_LIST._fltk_canonical_name = "ScopeStmt.Label.ANCHOR_LIST"
ScopeStmt.Label.SCOPE._fltk_canonical_name = "ScopeStmt.Label.SCOPE"


@dataclasses.dataclass
class DefStmt:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
        KIND = enum.auto()
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
        {"DefStmt.Label.ANCHOR": Label.ANCHOR, "DefStmt.Label.KIND": Label.KIND}
    )
    kind: typing.Literal[NodeKind.DEFSTMT] = NodeKind.DEFSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | DottedName | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Anchor | _cstp.DottedName | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DefStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.DottedName | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DefStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.DefStmt) -> None:
        if not isinstance(other, DefStmt):
            msg = f"DefStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | DottedName | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Anchor | _cstp.DottedName | _cstp.Trivia
    ) -> Anchor | DottedName | Trivia:
        if isinstance(child, Anchor | DottedName | Trivia):
            return child
        msg = f"DefStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> DefStmt.Label | None:
        if label is None or isinstance(label, DefStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = DefStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "DefStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.DottedName | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DefStmt.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | DottedName | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DefStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.DottedName | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DefStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DefStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: DefStmt.Label) -> list[Anchor | DottedName | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((DefStmt.Label.ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend([(DefStmt.Label.ANCHOR, self._check_child_type_for_mutators(child)) for child in children])

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(DefStmt.Label.ANCHOR)))

    def child_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(DefStmt.Label.ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(DefStmt.Label.ANCHOR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_kind(self, child: _cstp.DottedName) -> None:
        self.children.append((DefStmt.Label.KIND, self._check_child_type_for_mutators(child)))

    def extend_kind(self, children: typing.Iterable[_cstp.DottedName]) -> None:
        self.children.extend([(DefStmt.Label.KIND, self._check_child_type_for_mutators(child)) for child in children])

    def children_kind(self) -> typing.Iterator[DottedName]:
        return iter(typing.cast("list[DottedName]", self._children_snapshot(DefStmt.Label.KIND)))

    def child_kind(self) -> DottedName:
        children = typing.cast("list[DottedName]", self._children_snapshot(DefStmt.Label.KIND))
        if (n := len(children)) != 1:
            msg = f"Expected one kind child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_kind(self) -> DottedName | None:
        children = typing.cast("list[DottedName]", self._children_snapshot(DefStmt.Label.KIND))
        if (n := len(children)) > 1:
            msg = f"Expected at most one kind child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def anchor(self) -> Anchor:
        return self.child_anchor()


DefStmt.Label.ANCHOR._fltk_canonical_name = "DefStmt.Label.ANCHOR"
DefStmt.Label.KIND._fltk_canonical_name = "DefStmt.Label.KIND"


@dataclasses.dataclass
class RefStmt:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
        KIND_LIST = enum.auto()
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
        {"RefStmt.Label.ANCHOR": Label.ANCHOR, "RefStmt.Label.KIND_LIST": Label.KIND_LIST}
    )
    kind: typing.Literal[NodeKind.REFSTMT] = NodeKind.REFSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | KindList | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Anchor | _cstp.KindList | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RefStmt.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.KindList | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RefStmt.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.RefStmt) -> None:
        if not isinstance(other, RefStmt):
            msg = f"RefStmt: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | KindList | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Anchor | _cstp.KindList | _cstp.Trivia
    ) -> Anchor | KindList | Trivia:
        if isinstance(child, Anchor | KindList | Trivia):
            return child
        msg = f"RefStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> RefStmt.Label | None:
        if label is None or isinstance(label, RefStmt.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = RefStmt._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "RefStmt"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.KindList | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RefStmt.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | KindList | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RefStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.KindList | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, RefStmt.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RefStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: RefStmt.Label) -> list[Anchor | KindList | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((RefStmt.Label.ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend([(RefStmt.Label.ANCHOR, self._check_child_type_for_mutators(child)) for child in children])

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(RefStmt.Label.ANCHOR)))

    def child_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(RefStmt.Label.ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(RefStmt.Label.ANCHOR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_kind_list(self, child: _cstp.KindList) -> None:
        self.children.append((RefStmt.Label.KIND_LIST, self._check_child_type_for_mutators(child)))

    def extend_kind_list(self, children: typing.Iterable[_cstp.KindList]) -> None:
        self.children.extend(
            [(RefStmt.Label.KIND_LIST, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_kind_list(self) -> typing.Iterator[KindList]:
        return iter(typing.cast("list[KindList]", self._children_snapshot(RefStmt.Label.KIND_LIST)))

    def child_kind_list(self) -> KindList:
        children = typing.cast("list[KindList]", self._children_snapshot(RefStmt.Label.KIND_LIST))
        if (n := len(children)) != 1:
            msg = f"Expected one kind_list child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_kind_list(self) -> KindList | None:
        children = typing.cast("list[KindList]", self._children_snapshot(RefStmt.Label.KIND_LIST))
        if (n := len(children)) > 1:
            msg = f"Expected at most one kind_list child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def anchor(self) -> Anchor:
        return self.child_anchor()

    def kind_list(self) -> KindList:
        return self.child_kind_list()


RefStmt.Label.ANCHOR._fltk_canonical_name = "RefStmt.Label.ANCHOR"
RefStmt.Label.KIND_LIST._fltk_canonical_name = "RefStmt.Label.KIND_LIST"


@dataclasses.dataclass
class NamespaceStmt:
    kind: typing.Literal[NodeKind.NAMESPACESTMT] = NodeKind.NAMESPACESTMT
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

    def extend_children(self, other: _cstp.NamespaceStmt) -> None:
        if not isinstance(other, NamespaceStmt):
            msg = f"NamespaceStmt: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"NamespaceStmt: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"NamespaceStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
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
            msg = f"NamespaceStmt.remove_at: index {index} out of range ({n} children)"
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
            msg = f"NamespaceStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (None, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def text(self) -> str:
        return self.span.text_or_raise()


@dataclasses.dataclass
class AnchorList:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"AnchorList.Label.ANCHOR": Label.ANCHOR})
    kind: typing.Literal[NodeKind.ANCHORLIST] = NodeKind.ANCHORLIST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Anchor | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, AnchorList.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, AnchorList.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.AnchorList) -> None:
        if not isinstance(other, AnchorList):
            msg = f"AnchorList: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Anchor | _cstp.Trivia) -> Anchor | Trivia:
        if isinstance(child, Anchor | Trivia):
            return child
        msg = f"AnchorList: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> AnchorList.Label | None:
        if label is None or isinstance(label, AnchorList.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = AnchorList._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "AnchorList"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, AnchorList.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"AnchorList.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, AnchorList.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"AnchorList.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: AnchorList.Label) -> list[Anchor | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((AnchorList.Label.ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend(
            [(AnchorList.Label.ANCHOR, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(AnchorList.Label.ANCHOR)))

    def child_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(AnchorList.Label.ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(AnchorList.Label.ANCHOR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def anchor(self) -> list[Anchor]:
        return typing.cast("list[Anchor]", self._children_snapshot(AnchorList.Label.ANCHOR))


AnchorList.Label.ANCHOR._fltk_canonical_name = "AnchorList.Label.ANCHOR"


@dataclasses.dataclass
class Anchor:
    class Label(enum.Enum):
        LITERAL = enum.auto()
        NAME = enum.auto()
        QUALIFIER = enum.auto()
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
            "Anchor.Label.LITERAL": Label.LITERAL,
            "Anchor.Label.NAME": Label.NAME,
            "Anchor.Label.QUALIFIER": Label.QUALIFIER,
        }
    )
    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Literal | Qualifier]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Identifier | _cstp.Literal | _cstp.Qualifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Anchor.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Literal | _cstp.Qualifier],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Anchor.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Anchor) -> None:
        if not isinstance(other, Anchor):
            msg = f"Anchor: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | Literal | Qualifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Identifier | _cstp.Literal | _cstp.Qualifier
    ) -> Identifier | Literal | Qualifier:
        if isinstance(child, Identifier | Literal | Qualifier):
            return child
        msg = f"Anchor: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Anchor.Label | None:
        if label is None or isinstance(label, Anchor.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Anchor._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Anchor"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Literal | _cstp.Qualifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Anchor.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Literal | Qualifier]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Anchor.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Literal | _cstp.Qualifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Anchor.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Anchor.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Anchor.Label) -> list[Identifier | Literal | Qualifier]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_literal(self, child: _cstp.Literal) -> None:
        self.children.append((Anchor.Label.LITERAL, self._check_child_type_for_mutators(child)))

    def extend_literal(self, children: typing.Iterable[_cstp.Literal]) -> None:
        self.children.extend([(Anchor.Label.LITERAL, self._check_child_type_for_mutators(child)) for child in children])

    def children_literal(self) -> typing.Iterator[Literal]:
        return iter(typing.cast("list[Literal]", self._children_snapshot(Anchor.Label.LITERAL)))

    def child_literal(self) -> Literal:
        children = typing.cast("list[Literal]", self._children_snapshot(Anchor.Label.LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_literal(self) -> Literal | None:
        children = typing.cast("list[Literal]", self._children_snapshot(Anchor.Label.LITERAL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_name(self, child: _cstp.Identifier) -> None:
        self.children.append((Anchor.Label.NAME, self._check_child_type_for_mutators(child)))

    def extend_name(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend([(Anchor.Label.NAME, self._check_child_type_for_mutators(child)) for child in children])

    def children_name(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(Anchor.Label.NAME)))

    def child_name(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(Anchor.Label.NAME))
        if (n := len(children)) != 1:
            msg = f"Expected one name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(Anchor.Label.NAME))
        if (n := len(children)) > 1:
            msg = f"Expected at most one name child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_qualifier(self, child: _cstp.Qualifier) -> None:
        self.children.append((Anchor.Label.QUALIFIER, self._check_child_type_for_mutators(child)))

    def extend_qualifier(self, children: typing.Iterable[_cstp.Qualifier]) -> None:
        self.children.extend(
            [(Anchor.Label.QUALIFIER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_qualifier(self) -> typing.Iterator[Qualifier]:
        return iter(typing.cast("list[Qualifier]", self._children_snapshot(Anchor.Label.QUALIFIER)))

    def child_qualifier(self) -> Qualifier:
        children = typing.cast("list[Qualifier]", self._children_snapshot(Anchor.Label.QUALIFIER))
        if (n := len(children)) != 1:
            msg = f"Expected one qualifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_qualifier(self) -> Qualifier | None:
        children = typing.cast("list[Qualifier]", self._children_snapshot(Anchor.Label.QUALIFIER))
        if (n := len(children)) > 1:
            msg = f"Expected at most one qualifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def literal(self) -> Literal | None:
        return self.maybe_literal()

    def name(self) -> Identifier | None:
        return self.maybe_name()

    def qualifier(self) -> Qualifier | None:
        return self.maybe_qualifier()


Anchor.Label.LITERAL._fltk_canonical_name = "Anchor.Label.LITERAL"
Anchor.Label.NAME._fltk_canonical_name = "Anchor.Label.NAME"
Anchor.Label.QUALIFIER._fltk_canonical_name = "Anchor.Label.QUALIFIER"


@dataclasses.dataclass
class Qualifier:
    class Label(enum.Enum):
        LABEL = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Qualifier.Label.LABEL": Label.LABEL, "Qualifier.Label.RULE": Label.RULE}
    )
    kind: typing.Literal[NodeKind.QUALIFIER] = NodeKind.QUALIFIER
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
            if label is None or isinstance(label, Qualifier.Label)
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
            if label is None or isinstance(label, Qualifier.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Qualifier) -> None:
        if not isinstance(other, Qualifier):
            msg = f"Qualifier: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"Qualifier: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Qualifier.Label | None:
        if label is None or isinstance(label, Qualifier.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Qualifier._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Qualifier"
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
            if label is None or isinstance(label, Qualifier.Label)
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
            msg = f"Qualifier.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, Qualifier.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Qualifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Qualifier.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_label(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Qualifier.Label.LABEL, self._check_child_type_for_mutators(child)))

    def extend_label(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Qualifier.Label.LABEL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_label(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Qualifier.Label.LABEL))

    def child_label(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Qualifier.Label.LABEL)
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Qualifier.Label.LABEL)
        if (n := len(children)) > 1:
            msg = f"Expected at most one label child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_rule(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Qualifier.Label.RULE, self._check_child_type_for_mutators(child)))

    def extend_rule(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Qualifier.Label.RULE, self._check_child_type_for_mutators(child)) for child in children])

    def children_rule(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Qualifier.Label.RULE))

    def child_rule(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Qualifier.Label.RULE)
        if (n := len(children)) != 1:
            msg = f"Expected one rule child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Qualifier.Label.RULE)
        if (n := len(children)) > 1:
            msg = f"Expected at most one rule child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def label(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_label()

    def label_text(self) -> str | None:
        child = self.maybe_label()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Qualifier.label_text: child labelled 'label' is not a Span"
            raise TypeError(msg) from None

    def rule(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_rule()

    def rule_text(self) -> str | None:
        child = self.maybe_rule()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Qualifier.rule_text: child labelled 'rule' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Qualifier.variant: node has no labeled child"
        raise ValueError(msg)


Qualifier.Label.LABEL._fltk_canonical_name = "Qualifier.Label.LABEL"
Qualifier.Label.RULE._fltk_canonical_name = "Qualifier.Label.RULE"


@dataclasses.dataclass
class KindList:
    class Label(enum.Enum):
        KIND = enum.auto()
        WILDCARD = enum.auto()
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
        {"KindList.Label.KIND": Label.KIND, "KindList.Label.WILDCARD": Label.WILDCARD}
    )
    kind: typing.Literal[NodeKind.KINDLIST] = NodeKind.KINDLIST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.DottedName | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, KindList.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.DottedName | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, KindList.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.KindList) -> None:
        if not isinstance(other, KindList):
            msg = f"KindList: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.DottedName | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, DottedName | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"KindList: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> KindList.Label | None:
        if label is None or isinstance(label, KindList.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = KindList._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "KindList"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DottedName | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, KindList.Label)
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
    ) -> tuple[Label | None, DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"KindList.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.DottedName | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, KindList.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"KindList.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: KindList.Label
    ) -> list[DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_kind(self, child: _cstp.DottedName) -> None:
        self.children.append((KindList.Label.KIND, self._check_child_type_for_mutators(child)))

    def extend_kind(self, children: typing.Iterable[_cstp.DottedName]) -> None:
        self.children.extend([(KindList.Label.KIND, self._check_child_type_for_mutators(child)) for child in children])

    def children_kind(self) -> typing.Iterator[DottedName]:
        return iter(typing.cast("list[DottedName]", self._children_snapshot(KindList.Label.KIND)))

    def child_kind(self) -> DottedName:
        children = typing.cast("list[DottedName]", self._children_snapshot(KindList.Label.KIND))
        if (n := len(children)) != 1:
            msg = f"Expected one kind child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_kind(self) -> DottedName | None:
        children = typing.cast("list[DottedName]", self._children_snapshot(KindList.Label.KIND))
        if (n := len(children)) > 1:
            msg = f"Expected at most one kind child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_wildcard(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((KindList.Label.WILDCARD, self._check_child_type_for_mutators(child)))

    def extend_wildcard(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(KindList.Label.WILDCARD, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_wildcard(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(KindList.Label.WILDCARD)
            )
        )

    def child_wildcard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(KindList.Label.WILDCARD)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one wildcard child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_wildcard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(KindList.Label.WILDCARD)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one wildcard child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def wildcard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_wildcard()

    def wildcard_text(self) -> str | None:
        child = self.maybe_wildcard()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "KindList.wildcard_text: child labelled 'wildcard' is not a Span"
            raise TypeError(msg) from None


KindList.Label.KIND._fltk_canonical_name = "KindList.Label.KIND"
KindList.Label.WILDCARD._fltk_canonical_name = "KindList.Label.WILDCARD"


@dataclasses.dataclass
class DottedName:
    class Label(enum.Enum):
        PART = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"DottedName.Label.PART": Label.PART})
    kind: typing.Literal[NodeKind.DOTTEDNAME] = NodeKind.DOTTEDNAME
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DottedName.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DottedName.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.DottedName) -> None:
        if not isinstance(other, DottedName):
            msg = f"DottedName: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier) -> Identifier:
        if isinstance(child, Identifier):
            return child
        msg = f"DottedName: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> DottedName.Label | None:
        if label is None or isinstance(label, DottedName.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = DottedName._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "DottedName"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.Identifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DottedName.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Identifier]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DottedName.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.Identifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DottedName.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DottedName.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: DottedName.Label) -> list[Identifier]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_part(self, child: _cstp.Identifier) -> None:
        self.children.append((DottedName.Label.PART, self._check_child_type_for_mutators(child)))

    def extend_part(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(DottedName.Label.PART, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_part(self) -> typing.Iterator[Identifier]:
        return iter(self._children_snapshot(DottedName.Label.PART))

    def child_part(self) -> Identifier:
        children = self._children_snapshot(DottedName.Label.PART)
        if (n := len(children)) != 1:
            msg = f"Expected one part child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_part(self) -> Identifier | None:
        children = self._children_snapshot(DottedName.Label.PART)
        if (n := len(children)) > 1:
            msg = f"Expected at most one part child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def part(self) -> list[Identifier]:
        return self._children_snapshot(DottedName.Label.PART)


DottedName.Label.PART._fltk_canonical_name = "DottedName.Label.PART"


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
