# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol
__all__ = [
    "Anchor",
    "AnchorLabel",
    "AnchorList",
    "AnchorListLabel",
    "CstModule",
    "DefStmt",
    "DefStmtLabel",
    "DottedName",
    "DottedNameLabel",
    "Identifier",
    "IdentifierLabel",
    "KindList",
    "KindListLabel",
    "LineComment",
    "LineCommentLabel",
    "Literal",
    "LiteralLabel",
    "LspSpec",
    "LspSpecLabel",
    "NamespaceStmt",
    "NodeKind",
    "Qualifier",
    "QualifierLabel",
    "RefStmt",
    "RefStmtLabel",
    "RuleConfig",
    "RuleConfigLabel",
    "RuleStatement",
    "RuleStatementLabel",
    "ScopeStmt",
    "ScopeStmtLabel",
    "Span",
    "Statement",
    "StatementLabel",
    "Trivia",
    "TriviaLabel",
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
    kind: typing.Literal[NodeKind.LSPSPEC] = NodeKind.LSPSPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Statement | Trivia]]: ...

    def append(
        self, child: Statement | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Statement | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: LspSpec) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Statement | Trivia]: ...

    def insert(
        self, index: int, child: Statement | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Statement | Trivia]: ...

    def replace_at(
        self, index: int, child: Statement | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_statement(self, child: Statement) -> None: ...

    def extend_statement(self, children: typing.Iterable[Statement]) -> None: ...

    def children_statement(self) -> typing.Iterator[Statement]: ...

    def child_statement(self) -> Statement: ...

    def maybe_statement(self) -> Statement | None: ...

    def statement(self) -> typing.Sequence[Statement]: ...


class LspSpecLabel:
    """Sentinels equal to either backend's LspSpec labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    STATEMENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "LspSpec.Label.STATEMENT"
    )


class Statement(typing.Protocol):
    kind: typing.Literal[NodeKind.STATEMENT] = NodeKind.STATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, RuleConfig | ScopeStmt]]: ...

    def append(
        self, child: RuleConfig | ScopeStmt, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[RuleConfig | ScopeStmt],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Statement) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, RuleConfig | ScopeStmt]: ...

    def insert(
        self,
        index: int,
        child: RuleConfig | ScopeStmt,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, RuleConfig | ScopeStmt]: ...

    def replace_at(
        self,
        index: int,
        child: RuleConfig | ScopeStmt,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

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

    def rule_config(self) -> RuleConfig | None: ...

    def scope_stmt(self) -> ScopeStmt | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class StatementLabel:
    """Sentinels equal to either backend's Statement labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    RULE_CONFIG: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Statement.Label.RULE_CONFIG"
    )
    SCOPE_STMT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Statement.Label.SCOPE_STMT"
    )


class RuleConfig(typing.Protocol):
    kind: typing.Literal[NodeKind.RULECONFIG] = NodeKind.RULECONFIG
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | RuleStatement | Trivia]
    ]: ...

    def append(
        self,
        child: Identifier | RuleStatement | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Identifier | RuleStatement | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: RuleConfig) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | RuleStatement | Trivia]: ...

    def insert(
        self,
        index: int,
        child: Identifier | RuleStatement | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | RuleStatement | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: Identifier | RuleStatement | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
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

    def rule_name(self) -> Identifier: ...

    def rule_statement(self) -> typing.Sequence[RuleStatement]: ...


class RuleConfigLabel:
    """Sentinels equal to either backend's RuleConfig labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    RULE_NAME: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleConfig.Label.RULE_NAME"
    )
    RULE_STATEMENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleConfig.Label.RULE_STATEMENT"
    )


class RuleStatement(typing.Protocol):
    kind: typing.Literal[NodeKind.RULESTATEMENT] = NodeKind.RULESTATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]
    ]: ...

    def append(
        self,
        child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[DefStmt | NamespaceStmt | RefStmt | ScopeStmt],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: RuleStatement) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]: ...

    def insert(
        self,
        index: int,
        child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DefStmt | NamespaceStmt | RefStmt | ScopeStmt]: ...

    def replace_at(
        self,
        index: int,
        child: DefStmt | NamespaceStmt | RefStmt | ScopeStmt,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
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

    def def_stmt(self) -> DefStmt | None: ...

    def namespace_stmt(self) -> NamespaceStmt | None: ...

    def ref_stmt(self) -> RefStmt | None: ...

    def scope_stmt(self) -> ScopeStmt | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class RuleStatementLabel:
    """Sentinels equal to either backend's RuleStatement labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    DEF_STMT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.DEF_STMT"
    )
    NAMESPACE_STMT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.NAMESPACE_STMT"
    )
    REF_STMT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.REF_STMT"
    )
    SCOPE_STMT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.SCOPE_STMT"
    )


class ScopeStmt(typing.Protocol):
    kind: typing.Literal[NodeKind.SCOPESTMT] = NodeKind.SCOPESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, AnchorList | DottedName | Trivia]
    ]: ...

    def append(
        self, child: AnchorList | DottedName | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[AnchorList | DottedName | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ScopeStmt) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, AnchorList | DottedName | Trivia]: ...

    def insert(
        self,
        index: int,
        child: AnchorList | DottedName | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, AnchorList | DottedName | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: AnchorList | DottedName | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

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

    def anchor_list(self) -> AnchorList: ...

    def scope(self) -> DottedName: ...


class ScopeStmtLabel:
    """Sentinels equal to either backend's ScopeStmt labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ANCHOR_LIST: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ScopeStmt.Label.ANCHOR_LIST"
    )
    SCOPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("ScopeStmt.Label.SCOPE")


class DefStmt(typing.Protocol):
    kind: typing.Literal[NodeKind.DEFSTMT] = NodeKind.DEFSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | DottedName | Trivia]]: ...

    def append(
        self, child: Anchor | DottedName | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Anchor | DottedName | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: DefStmt) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | DottedName | Trivia]: ...

    def insert(
        self,
        index: int,
        child: Anchor | DottedName | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | DottedName | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: Anchor | DottedName | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

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

    def anchor(self) -> Anchor: ...


class DefStmtLabel:
    """Sentinels equal to either backend's DefStmt labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("DefStmt.Label.ANCHOR")
    KIND: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("DefStmt.Label.KIND")


class RefStmt(typing.Protocol):
    kind: typing.Literal[NodeKind.REFSTMT] = NodeKind.REFSTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | KindList | Trivia]]: ...

    def append(
        self, child: Anchor | KindList | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Anchor | KindList | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: RefStmt) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | KindList | Trivia]: ...

    def insert(
        self,
        index: int,
        child: Anchor | KindList | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | KindList | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: Anchor | KindList | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

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

    def anchor(self) -> Anchor: ...

    def kind_list(self) -> KindList: ...


class RefStmtLabel:
    """Sentinels equal to either backend's RefStmt labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("RefStmt.Label.ANCHOR")
    KIND_LIST: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RefStmt.Label.KIND_LIST"
    )


class NamespaceStmt(typing.Protocol):
    kind: typing.Literal[NodeKind.NAMESPACESTMT] = NodeKind.NAMESPACESTMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[None, Trivia]]: ...

    def append(self, child: Trivia, label: None = None) -> None: ...

    def extend(self, children: typing.Iterable[Trivia], label: None = None) -> None: ...

    def extend_children(self, other: NamespaceStmt) -> None: ...

    def child(self) -> tuple[None, Trivia]: ...

    def insert(self, index: int, child: Trivia, label: None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[None, Trivia]: ...

    def replace_at(self, index: int, child: Trivia, label: None = None) -> None: ...

    def clear(self) -> None: ...

    def text(self) -> str: ...


class AnchorList(typing.Protocol):
    kind: typing.Literal[NodeKind.ANCHORLIST] = NodeKind.ANCHORLIST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | Trivia]]: ...

    def append(
        self, child: Anchor | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Anchor | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: AnchorList) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | Trivia]: ...

    def insert(
        self, index: int, child: Anchor | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | Trivia]: ...

    def replace_at(
        self, index: int, child: Anchor | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_anchor(self, child: Anchor) -> None: ...

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_anchor(self) -> Anchor: ...

    def maybe_anchor(self) -> Anchor | None: ...

    def anchor(self) -> typing.Sequence[Anchor]: ...


class AnchorListLabel:
    """Sentinels equal to either backend's AnchorList labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("AnchorList.Label.ANCHOR")


class Anchor(typing.Protocol):
    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | Literal | Qualifier]
    ]: ...

    def append(
        self, child: Identifier | Literal | Qualifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Identifier | Literal | Qualifier],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Anchor) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | Literal | Qualifier]: ...

    def insert(
        self,
        index: int,
        child: Identifier | Literal | Qualifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | Literal | Qualifier]: ...

    def replace_at(
        self,
        index: int,
        child: Identifier | Literal | Qualifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

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

    def literal(self) -> Literal | None: ...

    def name(self) -> Identifier | None: ...

    def qualifier(self) -> Qualifier | None: ...


class AnchorLabel:
    """Sentinels equal to either backend's Anchor labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Anchor.Label.LITERAL")
    NAME: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Anchor.Label.NAME")
    QUALIFIER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Anchor.Label.QUALIFIER"
    )


class Qualifier(typing.Protocol):
    kind: typing.Literal[NodeKind.QUALIFIER] = NodeKind.QUALIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ]: ...

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Qualifier) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
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

    def label(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def label_text(self) -> str | None: ...

    def rule(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def rule_text(self) -> str | None: ...

    def text(self) -> str: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class QualifierLabel:
    """Sentinels equal to either backend's Qualifier labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    LABEL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Qualifier.Label.LABEL")
    RULE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Qualifier.Label.RULE")


class KindList(typing.Protocol):
    kind: typing.Literal[NodeKind.KINDLIST] = NodeKind.KINDLIST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: KindList) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def insert(
        self,
        index: int,
        child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: DottedName | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
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

    def wildcard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def wildcard_text(self) -> str | None: ...


class KindListLabel:
    """Sentinels equal to either backend's KindList labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    KIND: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("KindList.Label.KIND")
    WILDCARD: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "KindList.Label.WILDCARD"
    )


class DottedName(typing.Protocol):
    kind: typing.Literal[NodeKind.DOTTEDNAME] = NodeKind.DOTTEDNAME
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier]]: ...

    def append(self, child: Identifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Identifier], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: DottedName) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier]: ...

    def insert(
        self, index: int, child: Identifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier]: ...

    def replace_at(
        self, index: int, child: Identifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_part(self, child: Identifier) -> None: ...

    def extend_part(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_part(self) -> typing.Iterator[Identifier]: ...

    def child_part(self) -> Identifier: ...

    def maybe_part(self) -> Identifier | None: ...

    def part(self) -> typing.Sequence[Identifier]: ...


class DottedNameLabel:
    """Sentinels equal to either backend's DottedName labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    PART: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("DottedName.Label.PART")


class Identifier(typing.Protocol):
    kind: typing.Literal[NodeKind.IDENTIFIER] = NodeKind.IDENTIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ]: ...

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Identifier) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_name(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_name(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_name(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def name(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def name_text(self) -> str: ...

    def text(self) -> str: ...


class IdentifierLabel:
    """Sentinels equal to either backend's Identifier labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    NAME: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Identifier.Label.NAME")


class Literal(typing.Protocol):
    kind: typing.Literal[NodeKind.LITERAL] = NodeKind.LITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ]: ...

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Literal) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def value_text(self) -> str: ...

    def text(self) -> str: ...


class LiteralLabel:
    """Sentinels equal to either backend's Literal labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Literal.Label.VALUE")


class Trivia(typing.Protocol):
    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Trivia) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def insert(
        self,
        index: int,
        child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def replace_at(
        self,
        index: int,
        child: LineComment | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_line_comment(self, child: LineComment) -> None: ...

    def extend_line_comment(self, children: typing.Iterable[LineComment]) -> None: ...

    def children_line_comment(self) -> typing.Iterator[LineComment]: ...

    def child_line_comment(self) -> LineComment: ...

    def maybe_line_comment(self) -> LineComment | None: ...

    def line_comment(self) -> typing.Sequence[LineComment]: ...


class TriviaLabel:
    """Sentinels equal to either backend's Trivia labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    LINE_COMMENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Trivia.Label.LINE_COMMENT"
    )


class LineComment(typing.Protocol):
    kind: typing.Literal[NodeKind.LINECOMMENT] = NodeKind.LINECOMMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ]: ...

    def append(
        self,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: LineComment) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self,
        index: int,
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
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

    def content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def content_text(self) -> str: ...

    def newline(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def newline_text(self) -> str: ...

    def prefix(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def prefix_text(self) -> str: ...

    def text(self) -> str: ...


class LineCommentLabel:
    """Sentinels equal to either backend's LineComment labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CONTENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "LineComment.Label.CONTENT"
    )
    NEWLINE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "LineComment.Label.NEWLINE"
    )
    PREFIX: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "LineComment.Label.PREFIX"
    )


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
