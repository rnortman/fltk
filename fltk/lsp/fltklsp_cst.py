from __future__ import annotations

import dataclasses
import enum
import operator
import sys
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

    kind: typing.Literal[NodeKind.LSPSPEC] = NodeKind.LSPSPEC
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

    def extend_children(self, other: _cstp.LspSpec) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Statement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Statement | _cstp.Trivia) -> None:
        if not isinstance(child, Statement | Trivia):
            msg = f"LspSpec: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, LspSpec.Label)):
            _cn = "LspSpec"
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
            msg = f"LspSpec.remove_at: index {index} out of range ({n} children)"
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
            msg = f"LspSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_statement(self, child: _cstp.Statement) -> None:
        entry: typing.Any = (LspSpec.Label.STATEMENT, child)
        self.children.append(entry)

    def extend_statement(self, children: typing.Iterable[_cstp.Statement]) -> None:
        entries: typing.Any = ((LspSpec.Label.STATEMENT, child) for child in children)
        self.children.extend(entries)

    def children_statement(self) -> typing.Iterator[Statement]:
        return (typing.cast("Statement", child) for (label, child) in self.children if label == LspSpec.Label.STATEMENT)

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

    kind: typing.Literal[NodeKind.STATEMENT] = NodeKind.STATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, RuleConfig | ScopeStmt]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.RuleConfig | _cstp.ScopeStmt,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.RuleConfig | _cstp.ScopeStmt],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Statement) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, RuleConfig | ScopeStmt]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.RuleConfig | _cstp.ScopeStmt) -> None:
        if not isinstance(child, RuleConfig | ScopeStmt):
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
        child: _cstp.RuleConfig | _cstp.ScopeStmt,
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

    def append_scope_stmt(self, child: _cstp.ScopeStmt) -> None:
        entry: typing.Any = (Statement.Label.SCOPE_STMT, child)
        self.children.append(entry)

    def extend_scope_stmt(self, children: typing.Iterable[_cstp.ScopeStmt]) -> None:
        entries: typing.Any = ((Statement.Label.SCOPE_STMT, child) for child in children)
        self.children.extend(entries)

    def children_scope_stmt(self) -> typing.Iterator[ScopeStmt]:
        return (
            typing.cast("ScopeStmt", child) for (label, child) in self.children if label == Statement.Label.SCOPE_STMT
        )

    def child_scope_stmt(self) -> ScopeStmt:
        children = list(self.children_scope_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one scope_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_scope_stmt(self) -> ScopeStmt | None:
        children = list(self.children_scope_stmt())
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
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.DefStmt | _cstp.NamespaceStmt | _cstp.RefStmt | _cstp.ScopeStmt],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.RuleStatement) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.DefStmt | _cstp.NamespaceStmt | _cstp.RefStmt | _cstp.ScopeStmt
    ) -> None:
        if not isinstance(child, DefStmt | NamespaceStmt | RefStmt | ScopeStmt):
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
        child: _cstp.DefStmt | _cstp.NamespaceStmt | _cstp.RefStmt | _cstp.ScopeStmt,
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

    def append_def_stmt(self, child: _cstp.DefStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.DEF_STMT, child)
        self.children.append(entry)

    def extend_def_stmt(self, children: typing.Iterable[_cstp.DefStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.DEF_STMT, child) for child in children)
        self.children.extend(entries)

    def children_def_stmt(self) -> typing.Iterator[DefStmt]:
        return (
            typing.cast("DefStmt", child) for (label, child) in self.children if label == RuleStatement.Label.DEF_STMT
        )

    def child_def_stmt(self) -> DefStmt:
        children = list(self.children_def_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one def_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_def_stmt(self) -> DefStmt | None:
        children = list(self.children_def_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one def_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_namespace_stmt(self, child: _cstp.NamespaceStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.NAMESPACE_STMT, child)
        self.children.append(entry)

    def extend_namespace_stmt(self, children: typing.Iterable[_cstp.NamespaceStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.NAMESPACE_STMT, child) for child in children)
        self.children.extend(entries)

    def children_namespace_stmt(self) -> typing.Iterator[NamespaceStmt]:
        return (
            typing.cast("NamespaceStmt", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.NAMESPACE_STMT
        )

    def child_namespace_stmt(self) -> NamespaceStmt:
        children = list(self.children_namespace_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one namespace_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_namespace_stmt(self) -> NamespaceStmt | None:
        children = list(self.children_namespace_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one namespace_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ref_stmt(self, child: _cstp.RefStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.REF_STMT, child)
        self.children.append(entry)

    def extend_ref_stmt(self, children: typing.Iterable[_cstp.RefStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.REF_STMT, child) for child in children)
        self.children.extend(entries)

    def children_ref_stmt(self) -> typing.Iterator[RefStmt]:
        return (
            typing.cast("RefStmt", child) for (label, child) in self.children if label == RuleStatement.Label.REF_STMT
        )

    def child_ref_stmt(self) -> RefStmt:
        children = list(self.children_ref_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one ref_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ref_stmt(self) -> RefStmt | None:
        children = list(self.children_ref_stmt())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ref_stmt child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_scope_stmt(self, child: _cstp.ScopeStmt) -> None:
        entry: typing.Any = (RuleStatement.Label.SCOPE_STMT, child)
        self.children.append(entry)

    def extend_scope_stmt(self, children: typing.Iterable[_cstp.ScopeStmt]) -> None:
        entries: typing.Any = ((RuleStatement.Label.SCOPE_STMT, child) for child in children)
        self.children.extend(entries)

    def children_scope_stmt(self) -> typing.Iterator[ScopeStmt]:
        return (
            typing.cast("ScopeStmt", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.SCOPE_STMT
        )

    def child_scope_stmt(self) -> ScopeStmt:
        children = list(self.children_scope_stmt())
        if (n := len(children)) != 1:
            msg = f"Expected one scope_stmt child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_scope_stmt(self) -> ScopeStmt | None:
        children = list(self.children_scope_stmt())
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

    kind: typing.Literal[NodeKind.SCOPESTMT] = NodeKind.SCOPESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, AnchorList | DottedName | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.AnchorList | _cstp.DottedName | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.AnchorList | _cstp.DottedName | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.ScopeStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, AnchorList | DottedName | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.AnchorList | _cstp.DottedName | _cstp.Trivia) -> None:
        if not isinstance(child, AnchorList | DottedName | Trivia):
            msg = f"ScopeStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, ScopeStmt.Label)):
            _cn = "ScopeStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.AnchorList | _cstp.DottedName | _cstp.Trivia,
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
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ScopeStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_anchor_list(self, child: _cstp.AnchorList) -> None:
        entry: typing.Any = (ScopeStmt.Label.ANCHOR_LIST, child)
        self.children.append(entry)

    def extend_anchor_list(self, children: typing.Iterable[_cstp.AnchorList]) -> None:
        entries: typing.Any = ((ScopeStmt.Label.ANCHOR_LIST, child) for child in children)
        self.children.extend(entries)

    def children_anchor_list(self) -> typing.Iterator[AnchorList]:
        return (
            typing.cast("AnchorList", child) for (label, child) in self.children if label == ScopeStmt.Label.ANCHOR_LIST
        )

    def child_anchor_list(self) -> AnchorList:
        children = list(self.children_anchor_list())
        if (n := len(children)) != 1:
            msg = f"Expected one anchor_list child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor_list(self) -> AnchorList | None:
        children = list(self.children_anchor_list())
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor_list child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_scope(self, child: _cstp.DottedName) -> None:
        entry: typing.Any = (ScopeStmt.Label.SCOPE, child)
        self.children.append(entry)

    def extend_scope(self, children: typing.Iterable[_cstp.DottedName]) -> None:
        entries: typing.Any = ((ScopeStmt.Label.SCOPE, child) for child in children)
        self.children.extend(entries)

    def children_scope(self) -> typing.Iterator[DottedName]:
        return (typing.cast("DottedName", child) for (label, child) in self.children if label == ScopeStmt.Label.SCOPE)

    def child_scope(self) -> DottedName:
        children = list(self.children_scope())
        if (n := len(children)) != 1:
            msg = f"Expected one scope child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_scope(self) -> DottedName | None:
        children = list(self.children_scope())
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

    kind: typing.Literal[NodeKind.DEFSTMT] = NodeKind.DEFSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | DottedName | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Anchor | _cstp.DottedName | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.DottedName | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.DefStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Anchor | DottedName | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Anchor | _cstp.DottedName | _cstp.Trivia) -> None:
        if not isinstance(child, Anchor | DottedName | Trivia):
            msg = f"DefStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, DefStmt.Label)):
            _cn = "DefStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.DottedName | _cstp.Trivia,
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
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DefStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: _cstp.Anchor) -> None:
        entry: typing.Any = (DefStmt.Label.ANCHOR, child)
        self.children.append(entry)

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        entries: typing.Any = ((DefStmt.Label.ANCHOR, child) for child in children)
        self.children.extend(entries)

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == DefStmt.Label.ANCHOR)

    def child_anchor(self) -> Anchor:
        children = list(self.children_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = list(self.children_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_kind(self, child: _cstp.DottedName) -> None:
        entry: typing.Any = (DefStmt.Label.KIND, child)
        self.children.append(entry)

    def extend_kind(self, children: typing.Iterable[_cstp.DottedName]) -> None:
        entries: typing.Any = ((DefStmt.Label.KIND, child) for child in children)
        self.children.extend(entries)

    def children_kind(self) -> typing.Iterator[DottedName]:
        return (typing.cast("DottedName", child) for (label, child) in self.children if label == DefStmt.Label.KIND)

    def child_kind(self) -> DottedName:
        children = list(self.children_kind())
        if (n := len(children)) != 1:
            msg = f"Expected one kind child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_kind(self) -> DottedName | None:
        children = list(self.children_kind())
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

    kind: typing.Literal[NodeKind.REFSTMT] = NodeKind.REFSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | KindList | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Anchor | _cstp.KindList | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.KindList | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.RefStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Anchor | KindList | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Anchor | _cstp.KindList | _cstp.Trivia) -> None:
        if not isinstance(child, Anchor | KindList | Trivia):
            msg = f"RefStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, RefStmt.Label)):
            _cn = "RefStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.KindList | _cstp.Trivia,
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
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RefStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: _cstp.Anchor) -> None:
        entry: typing.Any = (RefStmt.Label.ANCHOR, child)
        self.children.append(entry)

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        entries: typing.Any = ((RefStmt.Label.ANCHOR, child) for child in children)
        self.children.extend(entries)

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == RefStmt.Label.ANCHOR)

    def child_anchor(self) -> Anchor:
        children = list(self.children_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = list(self.children_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_kind_list(self, child: _cstp.KindList) -> None:
        entry: typing.Any = (RefStmt.Label.KIND_LIST, child)
        self.children.append(entry)

    def extend_kind_list(self, children: typing.Iterable[_cstp.KindList]) -> None:
        entries: typing.Any = ((RefStmt.Label.KIND_LIST, child) for child in children)
        self.children.extend(entries)

    def children_kind_list(self) -> typing.Iterator[KindList]:
        return (typing.cast("KindList", child) for (label, child) in self.children if label == RefStmt.Label.KIND_LIST)

    def child_kind_list(self) -> KindList:
        children = list(self.children_kind_list())
        if (n := len(children)) != 1:
            msg = f"Expected one kind_list child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_kind_list(self) -> KindList | None:
        children = list(self.children_kind_list())
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
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(self, children: typing.Iterable[_cstp.Trivia], label: None = None) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.NamespaceStmt) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia) -> None:
        if not isinstance(child, Trivia):
            msg = f"NamespaceStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"NamespaceStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
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
            msg = f"NamespaceStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: _cstp.Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NamespaceStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

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

    kind: typing.Literal[NodeKind.ANCHORLIST] = NodeKind.ANCHORLIST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Anchor | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.AnchorList) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Anchor | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Anchor | _cstp.Trivia) -> None:
        if not isinstance(child, Anchor | Trivia):
            msg = f"AnchorList: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, AnchorList.Label)):
            _cn = "AnchorList"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Trivia,
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
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"AnchorList.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: _cstp.Anchor) -> None:
        entry: typing.Any = (AnchorList.Label.ANCHOR, child)
        self.children.append(entry)

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        entries: typing.Any = ((AnchorList.Label.ANCHOR, child) for child in children)
        self.children.extend(entries)

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == AnchorList.Label.ANCHOR)

    def child_anchor(self) -> Anchor:
        children = list(self.children_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = list(self.children_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def anchor(self) -> list[Anchor]:
        return list(self.children_anchor())


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

    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Literal | Qualifier]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Identifier | _cstp.Literal | _cstp.Qualifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Literal | _cstp.Qualifier],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Anchor) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | Literal | Qualifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Literal | _cstp.Qualifier) -> None:
        if not isinstance(child, Identifier | Literal | Qualifier):
            msg = f"Anchor: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Anchor.Label)):
            _cn = "Anchor"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Identifier | _cstp.Literal | _cstp.Qualifier,
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
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Anchor.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_literal(self, child: _cstp.Literal) -> None:
        entry: typing.Any = (Anchor.Label.LITERAL, child)
        self.children.append(entry)

    def extend_literal(self, children: typing.Iterable[_cstp.Literal]) -> None:
        entries: typing.Any = ((Anchor.Label.LITERAL, child) for child in children)
        self.children.extend(entries)

    def children_literal(self) -> typing.Iterator[Literal]:
        return (typing.cast("Literal", child) for (label, child) in self.children if label == Anchor.Label.LITERAL)

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

    def append_name(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (Anchor.Label.NAME, child)
        self.children.append(entry)

    def extend_name(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((Anchor.Label.NAME, child) for child in children)
        self.children.extend(entries)

    def children_name(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == Anchor.Label.NAME)

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

    def append_qualifier(self, child: _cstp.Qualifier) -> None:
        entry: typing.Any = (Anchor.Label.QUALIFIER, child)
        self.children.append(entry)

    def extend_qualifier(self, children: typing.Iterable[_cstp.Qualifier]) -> None:
        entries: typing.Any = ((Anchor.Label.QUALIFIER, child) for child in children)
        self.children.extend(entries)

    def children_qualifier(self) -> typing.Iterator[Qualifier]:
        return (typing.cast("Qualifier", child) for (label, child) in self.children if label == Anchor.Label.QUALIFIER)

    def child_qualifier(self) -> Qualifier:
        children = list(self.children_qualifier())
        if (n := len(children)) != 1:
            msg = f"Expected one qualifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_qualifier(self) -> Qualifier | None:
        children = list(self.children_qualifier())
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
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Qualifier) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Qualifier._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Qualifier._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Qualifier._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Qualifier._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Qualifier: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Qualifier.Label)):
            _cn = "Qualifier"
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
            msg = f"Qualifier.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Qualifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_label(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Qualifier.Label.LABEL, child))

    def extend_label(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Qualifier.Label.LABEL, child) for child in children)

    def children_label(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Qualifier.Label.LABEL)

    def child_label(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_label())
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_label())
        if (n := len(children)) > 1:
            msg = f"Expected at most one label child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_rule(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Qualifier.Label.RULE, child))

    def extend_rule(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Qualifier.Label.RULE, child) for child in children)

    def children_rule(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Qualifier.Label.RULE)

    def child_rule(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_rule())
        if (n := len(children)) != 1:
            msg = f"Expected one rule child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_rule(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_rule())
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
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.DottedName | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.KindList) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.DottedName | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
        _allowed = KindList._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (DottedName, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            KindList._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            KindList._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = KindList._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"KindList: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, KindList.Label)):
            _cn = "KindList"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DottedName | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"KindList.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_kind(self, child: _cstp.DottedName) -> None:
        entry: typing.Any = (KindList.Label.KIND, child)
        self.children.append(entry)

    def extend_kind(self, children: typing.Iterable[_cstp.DottedName]) -> None:
        entries: typing.Any = ((KindList.Label.KIND, child) for child in children)
        self.children.extend(entries)

    def children_kind(self) -> typing.Iterator[DottedName]:
        return (typing.cast("DottedName", child) for (label, child) in self.children if label == KindList.Label.KIND)

    def child_kind(self) -> DottedName:
        children = list(self.children_kind())
        if (n := len(children)) != 1:
            msg = f"Expected one kind child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_kind(self) -> DottedName | None:
        children = list(self.children_kind())
        if (n := len(children)) > 1:
            msg = f"Expected at most one kind child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_wildcard(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((KindList.Label.WILDCARD, child))

    def extend_wildcard(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((KindList.Label.WILDCARD, child) for child in children)

    def children_wildcard(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == KindList.Label.WILDCARD
        )

    def child_wildcard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_wildcard())
        if (n := len(children)) != 1:
            msg = f"Expected one wildcard child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_wildcard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_wildcard())
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

    kind: typing.Literal[NodeKind.DOTTEDNAME] = NodeKind.DOTTEDNAME
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.DottedName) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier) -> None:
        if not isinstance(child, Identifier):
            msg = f"DottedName: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, DottedName.Label)):
            _cn = "DottedName"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.Identifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
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
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DottedName.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_part(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (DottedName.Label.PART, child)
        self.children.append(entry)

    def extend_part(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((DottedName.Label.PART, child) for child in children)
        self.children.extend(entries)

    def children_part(self) -> typing.Iterator[Identifier]:
        return (child for (label, child) in self.children if label == DottedName.Label.PART)

    def child_part(self) -> Identifier:
        children = list(self.children_part())
        if (n := len(children)) != 1:
            msg = f"Expected one part child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_part(self) -> Identifier | None:
        children = list(self.children_part())
        if (n := len(children)) > 1:
            msg = f"Expected at most one part child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def part(self) -> list[Identifier]:
        return list(self.children_part())


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

    def extend_children(self, other: _cstp.Literal) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Literal.Label)):
            _cn = "Literal"
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
            msg = f"Literal.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Literal.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

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
