# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.span_protocol
__all__ = [
    "Anchor",
    "AnchorList",
    "CstModule",
    "DefStmt",
    "DottedName",
    "Identifier",
    "KindList",
    "LineComment",
    "Literal",
    "LspSpec",
    "NamespaceStmt",
    "NodeKind",
    "Qualifier",
    "RefStmt",
    "RuleConfig",
    "RuleStatement",
    "ScopeStmt",
    "Span",
    "Statement",
    "Trivia",
]


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


class LspSpec(typing.Protocol):
    class Label:
        STATEMENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LSPSPEC] = NodeKind.LSPSPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Statement | Trivia]]

    def append(self, child: Statement | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Statement | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: LspSpec) -> None: ...

    def child(self) -> tuple[Label | None, Statement | Trivia]: ...

    def insert(self, index: int, child: Statement | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Statement | Trivia]: ...

    def replace_at(self, index: int, child: Statement | Trivia, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_statement(self, child: Statement) -> None: ...

    def extend_statement(self, children: typing.Iterable[Statement]) -> None: ...

    def children_statement(self) -> typing.Iterator[Statement]: ...

    def child_statement(self) -> Statement: ...

    def maybe_statement(self) -> Statement | None: ...


LspSpec.Label.STATEMENT = _ProtocolLabelMember("LspSpec.Label.STATEMENT")


class Statement(typing.Protocol):
    class Label:
        RULE_CONFIG: typing.ClassVar[object]
        SCOPE_STMT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.STATEMENT] = NodeKind.STATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, RuleConfig | ScopeStmt]]

    def append(self, child: RuleConfig | ScopeStmt, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[RuleConfig | ScopeStmt], label: Label | None = None) -> None: ...

    def extend_children(self, other: Statement) -> None: ...

    def child(self) -> tuple[Label | None, RuleConfig | ScopeStmt]: ...

    def insert(self, index: int, child: RuleConfig | ScopeStmt, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, RuleConfig | ScopeStmt]: ...

    def replace_at(self, index: int, child: RuleConfig | ScopeStmt, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_rule_config(self, child: RuleConfig) -> None: ...

    def extend_rule_config(self, children: typing.Iterable[RuleConfig]) -> None: ...

    def children_rule_config(self) -> typing.Iterator[RuleConfig]: ...

    def child_rule_config(self) -> RuleConfig: ...

    def maybe_rule_config(self) -> RuleConfig | None: ...

    def append_scope_stmt(self, child: ScopeStmt) -> None: ...

    def extend_scope_stmt(self, children: typing.Iterable[ScopeStmt]) -> None: ...

    def children_scope_stmt(self) -> typing.Iterator[ScopeStmt]: ...

    def child_scope_stmt(self) -> ScopeStmt: ...

    def maybe_scope_stmt(self) -> ScopeStmt | None: ...


Statement.Label.RULE_CONFIG = _ProtocolLabelMember("Statement.Label.RULE_CONFIG")
Statement.Label.SCOPE_STMT = _ProtocolLabelMember("Statement.Label.SCOPE_STMT")


class RuleConfig(typing.Protocol):
    class Label:
        RULE_NAME: typing.ClassVar[object]
        RULE_STATEMENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.RULECONFIG] = NodeKind.RULECONFIG
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Identifier | RuleStatement | Trivia]]

    def append(self, child: Identifier | RuleStatement | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Identifier | RuleStatement | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: RuleConfig) -> None: ...

    def child(self) -> tuple[Label | None, Identifier | RuleStatement | Trivia]: ...

    def insert(self, index: int, child: Identifier | RuleStatement | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | RuleStatement | Trivia]: ...

    def replace_at(
        self, index: int, child: Identifier | RuleStatement | Trivia, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_rule_name(self, child: Identifier) -> None: ...

    def extend_rule_name(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_rule_name(self) -> typing.Iterator[Identifier]: ...

    def child_rule_name(self) -> Identifier: ...

    def maybe_rule_name(self) -> Identifier | None: ...

    def append_rule_statement(self, child: RuleStatement) -> None: ...

    def extend_rule_statement(self, children: typing.Iterable[RuleStatement]) -> None: ...

    def children_rule_statement(self) -> typing.Iterator[RuleStatement]: ...

    def child_rule_statement(self) -> RuleStatement: ...

    def maybe_rule_statement(self) -> RuleStatement | None: ...


RuleConfig.Label.RULE_NAME = _ProtocolLabelMember("RuleConfig.Label.RULE_NAME")
RuleConfig.Label.RULE_STATEMENT = _ProtocolLabelMember("RuleConfig.Label.RULE_STATEMENT")


class RuleStatement(typing.Protocol):
    class Label:
        DEF_STMT: typing.ClassVar[object]
        NAMESPACE_STMT: typing.ClassVar[object]
        REF_STMT: typing.ClassVar[object]
        SCOPE_STMT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.RULESTATEMENT] = NodeKind.RULESTATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]]

    def append(self, child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[DefStmt | NamespaceStmt | RefStmt | ScopeStmt], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: RuleStatement) -> None: ...

    def child(self) -> tuple[Label | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]: ...

    def insert(
        self, index: int, child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]: ...

    def replace_at(
        self, index: int, child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_def_stmt(self, child: DefStmt) -> None: ...

    def extend_def_stmt(self, children: typing.Iterable[DefStmt]) -> None: ...

    def children_def_stmt(self) -> typing.Iterator[DefStmt]: ...

    def child_def_stmt(self) -> DefStmt: ...

    def maybe_def_stmt(self) -> DefStmt | None: ...

    def append_namespace_stmt(self, child: NamespaceStmt) -> None: ...

    def extend_namespace_stmt(self, children: typing.Iterable[NamespaceStmt]) -> None: ...

    def children_namespace_stmt(self) -> typing.Iterator[NamespaceStmt]: ...

    def child_namespace_stmt(self) -> NamespaceStmt: ...

    def maybe_namespace_stmt(self) -> NamespaceStmt | None: ...

    def append_ref_stmt(self, child: RefStmt) -> None: ...

    def extend_ref_stmt(self, children: typing.Iterable[RefStmt]) -> None: ...

    def children_ref_stmt(self) -> typing.Iterator[RefStmt]: ...

    def child_ref_stmt(self) -> RefStmt: ...

    def maybe_ref_stmt(self) -> RefStmt | None: ...

    def append_scope_stmt(self, child: ScopeStmt) -> None: ...

    def extend_scope_stmt(self, children: typing.Iterable[ScopeStmt]) -> None: ...

    def children_scope_stmt(self) -> typing.Iterator[ScopeStmt]: ...

    def child_scope_stmt(self) -> ScopeStmt: ...

    def maybe_scope_stmt(self) -> ScopeStmt | None: ...


RuleStatement.Label.DEF_STMT = _ProtocolLabelMember("RuleStatement.Label.DEF_STMT")
RuleStatement.Label.NAMESPACE_STMT = _ProtocolLabelMember("RuleStatement.Label.NAMESPACE_STMT")
RuleStatement.Label.REF_STMT = _ProtocolLabelMember("RuleStatement.Label.REF_STMT")
RuleStatement.Label.SCOPE_STMT = _ProtocolLabelMember("RuleStatement.Label.SCOPE_STMT")


class ScopeStmt(typing.Protocol):
    class Label:
        ANCHOR_LIST: typing.ClassVar[object]
        SCOPE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.SCOPESTMT] = NodeKind.SCOPESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, AnchorList | DottedName | Trivia]]

    def append(self, child: AnchorList | DottedName | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[AnchorList | DottedName | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: ScopeStmt) -> None: ...

    def child(self) -> tuple[Label | None, AnchorList | DottedName | Trivia]: ...

    def insert(self, index: int, child: AnchorList | DottedName | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, AnchorList | DottedName | Trivia]: ...

    def replace_at(self, index: int, child: AnchorList | DottedName | Trivia, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_anchor_list(self, child: AnchorList) -> None: ...

    def extend_anchor_list(self, children: typing.Iterable[AnchorList]) -> None: ...

    def children_anchor_list(self) -> typing.Iterator[AnchorList]: ...

    def child_anchor_list(self) -> AnchorList: ...

    def maybe_anchor_list(self) -> AnchorList | None: ...

    def append_scope(self, child: DottedName) -> None: ...

    def extend_scope(self, children: typing.Iterable[DottedName]) -> None: ...

    def children_scope(self) -> typing.Iterator[DottedName]: ...

    def child_scope(self) -> DottedName: ...

    def maybe_scope(self) -> DottedName | None: ...


ScopeStmt.Label.ANCHOR_LIST = _ProtocolLabelMember("ScopeStmt.Label.ANCHOR_LIST")
ScopeStmt.Label.SCOPE = _ProtocolLabelMember("ScopeStmt.Label.SCOPE")


class DefStmt(typing.Protocol):
    class Label:
        ANCHOR: typing.ClassVar[object]
        KIND: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.DEFSTMT] = NodeKind.DEFSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Anchor | DottedName | Trivia]]

    def append(self, child: Anchor | DottedName | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Anchor | DottedName | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: DefStmt) -> None: ...

    def child(self) -> tuple[Label | None, Anchor | DottedName | Trivia]: ...

    def insert(self, index: int, child: Anchor | DottedName | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | DottedName | Trivia]: ...

    def replace_at(self, index: int, child: Anchor | DottedName | Trivia, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_anchor(self, child: Anchor) -> None: ...

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_anchor(self) -> Anchor: ...

    def maybe_anchor(self) -> Anchor | None: ...

    def append_kind(self, child: DottedName) -> None: ...

    def extend_kind(self, children: typing.Iterable[DottedName]) -> None: ...

    def children_kind(self) -> typing.Iterator[DottedName]: ...

    def child_kind(self) -> DottedName: ...

    def maybe_kind(self) -> DottedName | None: ...


DefStmt.Label.ANCHOR = _ProtocolLabelMember("DefStmt.Label.ANCHOR")
DefStmt.Label.KIND = _ProtocolLabelMember("DefStmt.Label.KIND")


class RefStmt(typing.Protocol):
    class Label:
        ANCHOR: typing.ClassVar[object]
        KIND_LIST: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.REFSTMT] = NodeKind.REFSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Anchor | KindList | Trivia]]

    def append(self, child: Anchor | KindList | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Anchor | KindList | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: RefStmt) -> None: ...

    def child(self) -> tuple[Label | None, Anchor | KindList | Trivia]: ...

    def insert(self, index: int, child: Anchor | KindList | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | KindList | Trivia]: ...

    def replace_at(self, index: int, child: Anchor | KindList | Trivia, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_anchor(self, child: Anchor) -> None: ...

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_anchor(self) -> Anchor: ...

    def maybe_anchor(self) -> Anchor | None: ...

    def append_kind_list(self, child: KindList) -> None: ...

    def extend_kind_list(self, children: typing.Iterable[KindList]) -> None: ...

    def children_kind_list(self) -> typing.Iterator[KindList]: ...

    def child_kind_list(self) -> KindList: ...

    def maybe_kind_list(self) -> KindList | None: ...


RefStmt.Label.ANCHOR = _ProtocolLabelMember("RefStmt.Label.ANCHOR")
RefStmt.Label.KIND_LIST = _ProtocolLabelMember("RefStmt.Label.KIND_LIST")


class NamespaceStmt(typing.Protocol):
    kind: typing.Literal[NodeKind.NAMESPACESTMT] = NodeKind.NAMESPACESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[None, Trivia]]

    def append(self, child: Trivia, label: None = None) -> None: ...

    def extend(self, children: typing.Iterable[Trivia], label: None = None) -> None: ...

    def extend_children(self, other: NamespaceStmt) -> None: ...

    def child(self) -> tuple[None, Trivia]: ...

    def insert(self, index: int, child: Trivia, label: None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[None, Trivia]: ...

    def replace_at(self, index: int, child: Trivia, label: None = None) -> None: ...

    def clear(self) -> None: ...


class AnchorList(typing.Protocol):
    class Label:
        ANCHOR: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ANCHORLIST] = NodeKind.ANCHORLIST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Anchor | Trivia]]

    def append(self, child: Anchor | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Anchor | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: AnchorList) -> None: ...

    def child(self) -> tuple[Label | None, Anchor | Trivia]: ...

    def insert(self, index: int, child: Anchor | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | Trivia]: ...

    def replace_at(self, index: int, child: Anchor | Trivia, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_anchor(self, child: Anchor) -> None: ...

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_anchor(self) -> Anchor: ...

    def maybe_anchor(self) -> Anchor | None: ...


AnchorList.Label.ANCHOR = _ProtocolLabelMember("AnchorList.Label.ANCHOR")


class Anchor(typing.Protocol):
    class Label:
        LITERAL: typing.ClassVar[object]
        NAME: typing.ClassVar[object]
        QUALIFIER: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Identifier | Literal | Qualifier]]

    def append(self, child: Identifier | Literal | Qualifier, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Identifier | Literal | Qualifier], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Anchor) -> None: ...

    def child(self) -> tuple[Label | None, Identifier | Literal | Qualifier]: ...

    def insert(self, index: int, child: Identifier | Literal | Qualifier, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Literal | Qualifier]: ...

    def replace_at(self, index: int, child: Identifier | Literal | Qualifier, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_literal(self, child: Literal) -> None: ...

    def extend_literal(self, children: typing.Iterable[Literal]) -> None: ...

    def children_literal(self) -> typing.Iterator[Literal]: ...

    def child_literal(self) -> Literal: ...

    def maybe_literal(self) -> Literal | None: ...

    def append_name(self, child: Identifier) -> None: ...

    def extend_name(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_name(self) -> typing.Iterator[Identifier]: ...

    def child_name(self) -> Identifier: ...

    def maybe_name(self) -> Identifier | None: ...

    def append_qualifier(self, child: Qualifier) -> None: ...

    def extend_qualifier(self, children: typing.Iterable[Qualifier]) -> None: ...

    def children_qualifier(self) -> typing.Iterator[Qualifier]: ...

    def child_qualifier(self) -> Qualifier: ...

    def maybe_qualifier(self) -> Qualifier | None: ...


Anchor.Label.LITERAL = _ProtocolLabelMember("Anchor.Label.LITERAL")
Anchor.Label.NAME = _ProtocolLabelMember("Anchor.Label.NAME")
Anchor.Label.QUALIFIER = _ProtocolLabelMember("Anchor.Label.QUALIFIER")


class Qualifier(typing.Protocol):
    class Label:
        LABEL: typing.ClassVar[object]
        RULE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.QUALIFIER] = NodeKind.QUALIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Qualifier) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_label(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_label(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_label(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_label(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_label(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_rule(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_rule(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_rule(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_rule(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_rule(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


Qualifier.Label.LABEL = _ProtocolLabelMember("Qualifier.Label.LABEL")
Qualifier.Label.RULE = _ProtocolLabelMember("Qualifier.Label.RULE")


class KindList(typing.Protocol):
    class Label:
        KIND: typing.ClassVar[object]
        WILDCARD: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.KINDLIST] = NodeKind.KINDLIST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(
        self, child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None: ...

    def extend_children(self, other: KindList) -> None: ...

    def child(self) -> tuple[Label | None, DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self,
        index: int,
        child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: Label | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[Label | None, DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self,
        index: int,
        child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: Label | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_kind(self, child: DottedName) -> None: ...

    def extend_kind(self, children: typing.Iterable[DottedName]) -> None: ...

    def children_kind(self) -> typing.Iterator[DottedName]: ...

    def child_kind(self) -> DottedName: ...

    def maybe_kind(self) -> DottedName | None: ...

    def append_wildcard(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_wildcard(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_wildcard(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_wildcard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_wildcard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


KindList.Label.KIND = _ProtocolLabelMember("KindList.Label.KIND")
KindList.Label.WILDCARD = _ProtocolLabelMember("KindList.Label.WILDCARD")


class DottedName(typing.Protocol):
    class Label:
        PART: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.DOTTEDNAME] = NodeKind.DOTTEDNAME
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Identifier]]

    def append(self, child: Identifier, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Identifier], label: Label | None = None) -> None: ...

    def extend_children(self, other: DottedName) -> None: ...

    def child(self) -> tuple[Label | None, Identifier]: ...

    def insert(self, index: int, child: Identifier, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Identifier]: ...

    def replace_at(self, index: int, child: Identifier, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_part(self, child: Identifier) -> None: ...

    def extend_part(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_part(self) -> typing.Iterator[Identifier]: ...

    def child_part(self) -> Identifier: ...

    def maybe_part(self) -> Identifier | None: ...


DottedName.Label.PART = _ProtocolLabelMember("DottedName.Label.PART")


class Identifier(typing.Protocol):
    class Label:
        NAME: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.IDENTIFIER] = NodeKind.IDENTIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Identifier) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_name(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_name(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_name(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


Identifier.Label.NAME = _ProtocolLabelMember("Identifier.Label.NAME")


class Literal(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LITERAL] = NodeKind.LITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Literal) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


Literal.Label.VALUE = _ProtocolLabelMember("Literal.Label.VALUE")


class Trivia(typing.Protocol):
    class Label:
        LINE_COMMENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(
        self, child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None: ...

    def extend_children(self, other: Trivia) -> None: ...

    def child(self) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_line_comment(self, child: LineComment) -> None: ...

    def extend_line_comment(self, children: typing.Iterable[LineComment]) -> None: ...

    def children_line_comment(self) -> typing.Iterator[LineComment]: ...

    def child_line_comment(self) -> LineComment: ...

    def maybe_line_comment(self) -> LineComment | None: ...


Trivia.Label.LINE_COMMENT = _ProtocolLabelMember("Trivia.Label.LINE_COMMENT")


class LineComment(typing.Protocol):
    class Label:
        CONTENT: typing.ClassVar[object]
        NEWLINE: typing.ClassVar[object]
        PREFIX: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LINECOMMENT] = NodeKind.LINECOMMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: LineComment) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_newline(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_newline(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_newline(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_newline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_newline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_prefix(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_prefix(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_prefix(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_prefix(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_prefix(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


LineComment.Label.CONTENT = _ProtocolLabelMember("LineComment.Label.CONTENT")
LineComment.Label.NEWLINE = _ProtocolLabelMember("LineComment.Label.NEWLINE")
LineComment.Label.PREFIX = _ProtocolLabelMember("LineComment.Label.PREFIX")


class Span(typing.Protocol):
    kind: typing.Literal[fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN] = fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN


class CstModule(typing.Protocol):
    @property
    def LspSpec(self) -> type[LspSpec]: ...

    @property
    def Statement(self) -> type[Statement]: ...

    @property
    def RuleConfig(self) -> type[RuleConfig]: ...

    @property
    def RuleStatement(self) -> type[RuleStatement]: ...

    @property
    def ScopeStmt(self) -> type[ScopeStmt]: ...

    @property
    def DefStmt(self) -> type[DefStmt]: ...

    @property
    def RefStmt(self) -> type[RefStmt]: ...

    @property
    def NamespaceStmt(self) -> type[NamespaceStmt]: ...

    @property
    def AnchorList(self) -> type[AnchorList]: ...

    @property
    def Anchor(self) -> type[Anchor]: ...

    @property
    def Qualifier(self) -> type[Qualifier]: ...

    @property
    def KindList(self) -> type[KindList]: ...

    @property
    def DottedName(self) -> type[DottedName]: ...

    @property
    def Identifier(self) -> type[Identifier]: ...

    @property
    def Literal(self) -> type[Literal]: ...

    @property
    def Trivia(self) -> type[Trivia]: ...

    @property
    def LineComment(self) -> type[LineComment]: ...
