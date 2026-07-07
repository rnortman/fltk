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
    LSPSPEC = enum.auto()
    STATEMENT = enum.auto()
    RULECONFIG = enum.auto()
    RULESTATEMENT = enum.auto()
    SCOPESTMT = enum.auto()
    DEFSTMT = enum.auto()
    REFSTMT = enum.auto()
    NAMESPACESTMT = enum.auto()
    ANCHORLIST = enum.auto()
    ANCHOR = enum.auto()
    QUALIFIER = enum.auto()
    KINDLIST = enum.auto()
    DOTTEDNAME = enum.auto()
    IDENTIFIER = enum.auto()
    LITERAL = enum.auto()
    TRIVIA = enum.auto()
    LINECOMMENT = enum.auto()
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


NodeKind.LSPSPEC._fltk_canonical_name = "NodeKind.LSPSPEC"
NodeKind.STATEMENT._fltk_canonical_name = "NodeKind.STATEMENT"
NodeKind.RULECONFIG._fltk_canonical_name = "NodeKind.RULECONFIG"
NodeKind.RULESTATEMENT._fltk_canonical_name = "NodeKind.RULESTATEMENT"
NodeKind.SCOPESTMT._fltk_canonical_name = "NodeKind.SCOPESTMT"
NodeKind.DEFSTMT._fltk_canonical_name = "NodeKind.DEFSTMT"
NodeKind.REFSTMT._fltk_canonical_name = "NodeKind.REFSTMT"
NodeKind.NAMESPACESTMT._fltk_canonical_name = "NodeKind.NAMESPACESTMT"
NodeKind.ANCHORLIST._fltk_canonical_name = "NodeKind.ANCHORLIST"
NodeKind.ANCHOR._fltk_canonical_name = "NodeKind.ANCHOR"
NodeKind.QUALIFIER._fltk_canonical_name = "NodeKind.QUALIFIER"
NodeKind.KINDLIST._fltk_canonical_name = "NodeKind.KINDLIST"
NodeKind.DOTTEDNAME._fltk_canonical_name = "NodeKind.DOTTEDNAME"
NodeKind.IDENTIFIER._fltk_canonical_name = "NodeKind.IDENTIFIER"
NodeKind.LITERAL._fltk_canonical_name = "NodeKind.LITERAL"
NodeKind.TRIVIA._fltk_canonical_name = "NodeKind.TRIVIA"
NodeKind.LINECOMMENT._fltk_canonical_name = "NodeKind.LINECOMMENT"


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

    def append(self, child: Statement | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Statement | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: LspSpec) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Statement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Statement | Trivia) -> None:
        if not isinstance(child, Statement | Trivia):
            msg = f"LspSpec: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, LspSpec.Label)):
            _cn = "LspSpec"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Statement | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Statement | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LspSpec.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Statement | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LspSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_statement(self, child: Statement) -> None:
        self.children.append((LspSpec.Label.STATEMENT, child))

    def extend_statement(self, children: typing.Iterable[Statement]) -> None:
        self.children.extend((LspSpec.Label.STATEMENT, child) for child in children)

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

    def append(self, child: RuleConfig | ScopeStmt, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[RuleConfig | ScopeStmt], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Statement) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, RuleConfig | ScopeStmt]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: RuleConfig | ScopeStmt) -> None:
        if not isinstance(child, RuleConfig | ScopeStmt):
            msg = f"Statement: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Statement.Label)):
            _cn = "Statement"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: RuleConfig | ScopeStmt, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, RuleConfig | ScopeStmt]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Statement.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: RuleConfig | ScopeStmt, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Statement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_rule_config(self, child: RuleConfig) -> None:
        self.children.append((Statement.Label.RULE_CONFIG, child))

    def extend_rule_config(self, children: typing.Iterable[RuleConfig]) -> None:
        self.children.extend((Statement.Label.RULE_CONFIG, child) for child in children)

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

    def append_scope_stmt(self, child: ScopeStmt) -> None:
        self.children.append((Statement.Label.SCOPE_STMT, child))

    def extend_scope_stmt(self, children: typing.Iterable[ScopeStmt]) -> None:
        self.children.extend((Statement.Label.SCOPE_STMT, child) for child in children)

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

    def append(self, child: Identifier | RuleStatement | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Identifier | RuleStatement | Trivia], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: RuleConfig) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | RuleStatement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Identifier | RuleStatement | Trivia) -> None:
        if not isinstance(child, Identifier | RuleStatement | Trivia):
            msg = f"RuleConfig: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, RuleConfig.Label)):
            _cn = "RuleConfig"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Identifier | RuleStatement | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | RuleStatement | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleConfig.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Identifier | RuleStatement | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleConfig.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_rule_name(self, child: Identifier) -> None:
        self.children.append((RuleConfig.Label.RULE_NAME, child))

    def extend_rule_name(self, children: typing.Iterable[Identifier]) -> None:
        self.children.extend((RuleConfig.Label.RULE_NAME, child) for child in children)

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

    def append_rule_statement(self, child: RuleStatement) -> None:
        self.children.append((RuleConfig.Label.RULE_STATEMENT, child))

    def extend_rule_statement(self, children: typing.Iterable[RuleStatement]) -> None:
        self.children.extend((RuleConfig.Label.RULE_STATEMENT, child) for child in children)

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

    def append(self, child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[DefStmt | NamespaceStmt | RefStmt | ScopeStmt], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: RuleStatement) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt) -> None:
        if not isinstance(child, DefStmt | NamespaceStmt | RefStmt | ScopeStmt):
            msg = f"RuleStatement: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, RuleStatement.Label)):
            _cn = "RuleStatement"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleStatement.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RuleStatement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_def_stmt(self, child: DefStmt) -> None:
        self.children.append((RuleStatement.Label.DEF_STMT, child))

    def extend_def_stmt(self, children: typing.Iterable[DefStmt]) -> None:
        self.children.extend((RuleStatement.Label.DEF_STMT, child) for child in children)

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

    def append_namespace_stmt(self, child: NamespaceStmt) -> None:
        self.children.append((RuleStatement.Label.NAMESPACE_STMT, child))

    def extend_namespace_stmt(self, children: typing.Iterable[NamespaceStmt]) -> None:
        self.children.extend((RuleStatement.Label.NAMESPACE_STMT, child) for child in children)

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

    def append_ref_stmt(self, child: RefStmt) -> None:
        self.children.append((RuleStatement.Label.REF_STMT, child))

    def extend_ref_stmt(self, children: typing.Iterable[RefStmt]) -> None:
        self.children.extend((RuleStatement.Label.REF_STMT, child) for child in children)

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

    def append_scope_stmt(self, child: ScopeStmt) -> None:
        self.children.append((RuleStatement.Label.SCOPE_STMT, child))

    def extend_scope_stmt(self, children: typing.Iterable[ScopeStmt]) -> None:
        self.children.extend((RuleStatement.Label.SCOPE_STMT, child) for child in children)

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

    def append(self, child: AnchorList | DottedName | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[AnchorList | DottedName | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ScopeStmt) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, AnchorList | DottedName | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: AnchorList | DottedName | Trivia) -> None:
        if not isinstance(child, AnchorList | DottedName | Trivia):
            msg = f"ScopeStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ScopeStmt.Label)):
            _cn = "ScopeStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: AnchorList | DottedName | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, AnchorList | DottedName | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ScopeStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: AnchorList | DottedName | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ScopeStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor_list(self, child: AnchorList) -> None:
        self.children.append((ScopeStmt.Label.ANCHOR_LIST, child))

    def extend_anchor_list(self, children: typing.Iterable[AnchorList]) -> None:
        self.children.extend((ScopeStmt.Label.ANCHOR_LIST, child) for child in children)

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

    def append_scope(self, child: DottedName) -> None:
        self.children.append((ScopeStmt.Label.SCOPE, child))

    def extend_scope(self, children: typing.Iterable[DottedName]) -> None:
        self.children.extend((ScopeStmt.Label.SCOPE, child) for child in children)

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

    def append(self, child: Anchor | DottedName | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Anchor | DottedName | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: DefStmt) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | DottedName | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Anchor | DottedName | Trivia) -> None:
        if not isinstance(child, Anchor | DottedName | Trivia):
            msg = f"DefStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, DefStmt.Label)):
            _cn = "DefStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Anchor | DottedName | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | DottedName | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DefStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Anchor | DottedName | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DefStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: Anchor) -> None:
        self.children.append((DefStmt.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((DefStmt.Label.ANCHOR, child) for child in children)

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

    def append_kind(self, child: DottedName) -> None:
        self.children.append((DefStmt.Label.KIND, child))

    def extend_kind(self, children: typing.Iterable[DottedName]) -> None:
        self.children.extend((DefStmt.Label.KIND, child) for child in children)

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

    def append(self, child: Anchor | KindList | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Anchor | KindList | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: RefStmt) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | KindList | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Anchor | KindList | Trivia) -> None:
        if not isinstance(child, Anchor | KindList | Trivia):
            msg = f"RefStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, RefStmt.Label)):
            _cn = "RefStmt"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Anchor | KindList | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | KindList | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RefStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Anchor | KindList | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"RefStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: Anchor) -> None:
        self.children.append((RefStmt.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((RefStmt.Label.ANCHOR, child) for child in children)

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

    def append_kind_list(self, child: KindList) -> None:
        self.children.append((RefStmt.Label.KIND_LIST, child))

    def extend_kind_list(self, children: typing.Iterable[KindList]) -> None:
        self.children.extend((RefStmt.Label.KIND_LIST, child) for child in children)

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


RefStmt.Label.ANCHOR._fltk_canonical_name = "RefStmt.Label.ANCHOR"
RefStmt.Label.KIND_LIST._fltk_canonical_name = "RefStmt.Label.KIND_LIST"


@dataclasses.dataclass
class NamespaceStmt:
    kind: typing.Literal[NodeKind.NAMESPACESTMT] = NodeKind.NAMESPACESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[None, Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Trivia, label: None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Trivia], label: None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: NamespaceStmt) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[None, Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Trivia) -> None:
        if not isinstance(child, Trivia):
            msg = f"NamespaceStmt: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: None, method: str) -> None:
        if label is not None:
            msg = f"NamespaceStmt.{method}: no labels defined for this node; got {type(label).__name__} label"
            raise TypeError(msg)

    def insert(self, index: int, child: Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[None, Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NamespaceStmt.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Trivia, label: None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NamespaceStmt.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()


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

    def append(self, child: Anchor | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Anchor | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: AnchorList) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Anchor | Trivia) -> None:
        if not isinstance(child, Anchor | Trivia):
            msg = f"AnchorList: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, AnchorList.Label)):
            _cn = "AnchorList"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Anchor | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"AnchorList.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Anchor | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"AnchorList.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: Anchor) -> None:
        self.children.append((AnchorList.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((AnchorList.Label.ANCHOR, child) for child in children)

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

    def append(self, child: Identifier | Literal | Qualifier, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Identifier | Literal | Qualifier], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Anchor) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | Literal | Qualifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Identifier | Literal | Qualifier) -> None:
        if not isinstance(child, Identifier | Literal | Qualifier):
            msg = f"Anchor: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Anchor.Label)):
            _cn = "Anchor"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Identifier | Literal | Qualifier, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Literal | Qualifier]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Anchor.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Identifier | Literal | Qualifier, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Anchor.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_literal(self, child: Literal) -> None:
        self.children.append((Anchor.Label.LITERAL, child))

    def extend_literal(self, children: typing.Iterable[Literal]) -> None:
        self.children.extend((Anchor.Label.LITERAL, child) for child in children)

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

    def append_name(self, child: Identifier) -> None:
        self.children.append((Anchor.Label.NAME, child))

    def extend_name(self, children: typing.Iterable[Identifier]) -> None:
        self.children.extend((Anchor.Label.NAME, child) for child in children)

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

    def append_qualifier(self, child: Qualifier) -> None:
        self.children.append((Anchor.Label.QUALIFIER, child))

    def extend_qualifier(self, children: typing.Iterable[Qualifier]) -> None:
        self.children.extend((Anchor.Label.QUALIFIER, child) for child in children)

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

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Qualifier) -> None:
        self.children.extend(other.children)

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

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Qualifier.Label)):
            _cn = "Qualifier"
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
            msg = f"Qualifier.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Qualifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

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
        self, child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: KindList) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
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

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, KindList.Label)):
            _cn = "KindList"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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
        child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: Label | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"KindList.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_kind(self, child: DottedName) -> None:
        self.children.append((KindList.Label.KIND, child))

    def extend_kind(self, children: typing.Iterable[DottedName]) -> None:
        self.children.extend((KindList.Label.KIND, child) for child in children)

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

    def append(self, child: Identifier, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Identifier], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: DottedName) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Identifier) -> None:
        if not isinstance(child, Identifier):
            msg = f"DottedName: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, DottedName.Label)):
            _cn = "DottedName"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Identifier, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Identifier]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DottedName.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Identifier, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DottedName.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_part(self, child: Identifier) -> None:
        self.children.append((DottedName.Label.PART, child))

    def extend_part(self, children: typing.Iterable[Identifier]) -> None:
        self.children.extend((DottedName.Label.PART, child) for child in children)

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
        self, child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Trivia) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
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

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Trivia.Label)):
            _cn = "Trivia"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Trivia.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
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


LineComment.Label.CONTENT._fltk_canonical_name = "LineComment.Label.CONTENT"
LineComment.Label.NEWLINE._fltk_canonical_name = "LineComment.Label.NEWLINE"
LineComment.Label.PREFIX._fltk_canonical_name = "LineComment.Label.PREFIX"
