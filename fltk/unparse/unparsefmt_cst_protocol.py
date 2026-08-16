# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol
__all__ = [
    "After",
    "AfterLabel",
    "Anchor",
    "AnchorLabel",
    "Before",
    "BeforeLabel",
    "CompoundLiteral",
    "CompoundLiteralLabel",
    "ConcatLiteral",
    "ConcatLiteralLabel",
    "CstModule",
    "Default",
    "DefaultLabel",
    "DocListLiteral",
    "DocListLiteralLabel",
    "DocLiteral",
    "DocLiteralLabel",
    "Formatter",
    "FormatterLabel",
    "FromSpec",
    "FromSpecLabel",
    "Group",
    "GroupLabel",
    "Identifier",
    "IdentifierLabel",
    "Integer",
    "IntegerLabel",
    "Join",
    "JoinLabel",
    "JoinLiteral",
    "JoinLiteralLabel",
    "LineComment",
    "LineCommentLabel",
    "Literal",
    "LiteralLabel",
    "Nest",
    "NestLabel",
    "NodeKind",
    "Omit",
    "OmitLabel",
    "PositionSpecStatement",
    "PositionSpecStatementLabel",
    "PreserveBlanks",
    "PreserveBlanksLabel",
    "Render",
    "RenderLabel",
    "RuleConfig",
    "RuleConfigLabel",
    "RuleStatement",
    "RuleStatementLabel",
    "Spacing",
    "SpacingLabel",
    "Span",
    "Statement",
    "StatementLabel",
    "TextLiteral",
    "TextLiteralLabel",
    "ToSpec",
    "ToSpecLabel",
    "Trivia",
    "TriviaLabel",
    "TriviaNodeList",
    "TriviaNodeListLabel",
    "TriviaPreserve",
    "TriviaPreserveLabel",
]


class NodeKind(enum.Enum):
    FORMATTER = enum.auto()
    STATEMENT = enum.auto()
    DEFAULT = enum.auto()
    RULECONFIG = enum.auto()
    RULESTATEMENT = enum.auto()
    GROUP = enum.auto()
    NEST = enum.auto()
    JOIN = enum.auto()
    FROMSPEC = enum.auto()
    TOSPEC = enum.auto()
    ANCHOR = enum.auto()
    AFTER = enum.auto()
    BEFORE = enum.auto()
    OMIT = enum.auto()
    RENDER = enum.auto()
    POSITIONSPECSTATEMENT = enum.auto()
    SPACING = enum.auto()
    DOCLITERAL = enum.auto()
    TEXTLITERAL = enum.auto()
    CONCATLITERAL = enum.auto()
    JOINLITERAL = enum.auto()
    DOCLISTLITERAL = enum.auto()
    COMPOUNDLITERAL = enum.auto()
    TRIVIAPRESERVE = enum.auto()
    TRIVIANODELIST = enum.auto()
    PRESERVEBLANKS = enum.auto()
    IDENTIFIER = enum.auto()
    LITERAL = enum.auto()
    INTEGER = enum.auto()
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


NodeKind.FORMATTER._fltk_canonical_name = "NodeKind.FORMATTER"
NodeKind.STATEMENT._fltk_canonical_name = "NodeKind.STATEMENT"
NodeKind.DEFAULT._fltk_canonical_name = "NodeKind.DEFAULT"
NodeKind.RULECONFIG._fltk_canonical_name = "NodeKind.RULECONFIG"
NodeKind.RULESTATEMENT._fltk_canonical_name = "NodeKind.RULESTATEMENT"
NodeKind.GROUP._fltk_canonical_name = "NodeKind.GROUP"
NodeKind.NEST._fltk_canonical_name = "NodeKind.NEST"
NodeKind.JOIN._fltk_canonical_name = "NodeKind.JOIN"
NodeKind.FROMSPEC._fltk_canonical_name = "NodeKind.FROMSPEC"
NodeKind.TOSPEC._fltk_canonical_name = "NodeKind.TOSPEC"
NodeKind.ANCHOR._fltk_canonical_name = "NodeKind.ANCHOR"
NodeKind.AFTER._fltk_canonical_name = "NodeKind.AFTER"
NodeKind.BEFORE._fltk_canonical_name = "NodeKind.BEFORE"
NodeKind.OMIT._fltk_canonical_name = "NodeKind.OMIT"
NodeKind.RENDER._fltk_canonical_name = "NodeKind.RENDER"
NodeKind.POSITIONSPECSTATEMENT._fltk_canonical_name = "NodeKind.POSITIONSPECSTATEMENT"
NodeKind.SPACING._fltk_canonical_name = "NodeKind.SPACING"
NodeKind.DOCLITERAL._fltk_canonical_name = "NodeKind.DOCLITERAL"
NodeKind.TEXTLITERAL._fltk_canonical_name = "NodeKind.TEXTLITERAL"
NodeKind.CONCATLITERAL._fltk_canonical_name = "NodeKind.CONCATLITERAL"
NodeKind.JOINLITERAL._fltk_canonical_name = "NodeKind.JOINLITERAL"
NodeKind.DOCLISTLITERAL._fltk_canonical_name = "NodeKind.DOCLISTLITERAL"
NodeKind.COMPOUNDLITERAL._fltk_canonical_name = "NodeKind.COMPOUNDLITERAL"
NodeKind.TRIVIAPRESERVE._fltk_canonical_name = "NodeKind.TRIVIAPRESERVE"
NodeKind.TRIVIANODELIST._fltk_canonical_name = "NodeKind.TRIVIANODELIST"
NodeKind.PRESERVEBLANKS._fltk_canonical_name = "NodeKind.PRESERVEBLANKS"
NodeKind.IDENTIFIER._fltk_canonical_name = "NodeKind.IDENTIFIER"
NodeKind.LITERAL._fltk_canonical_name = "NodeKind.LITERAL"
NodeKind.INTEGER._fltk_canonical_name = "NodeKind.INTEGER"
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


class Formatter(typing.Protocol):
    kind: typing.Literal[NodeKind.FORMATTER] = NodeKind.FORMATTER
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

    def extend_children(self, other: Formatter) -> None: ...

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


class FormatterLabel:
    """Sentinels equal to either backend's Formatter labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    STATEMENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Formatter.Label.STATEMENT"
    )


class Statement(typing.Protocol):
    kind: typing.Literal[NodeKind.STATEMENT] = NodeKind.STATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            After
            | Before
            | Default
            | Group
            | Join
            | Nest
            | Omit
            | PreserveBlanks
            | Render
            | RuleConfig
            | TriviaPreserve,
        ]
    ]: ...

    def append(
        self,
        child: After
        | Before
        | Default
        | Group
        | Join
        | Nest
        | Omit
        | PreserveBlanks
        | Render
        | RuleConfig
        | TriviaPreserve,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[
            After
            | Before
            | Default
            | Group
            | Join
            | Nest
            | Omit
            | PreserveBlanks
            | Render
            | RuleConfig
            | TriviaPreserve
        ],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Statement) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render | RuleConfig | TriviaPreserve,
    ]: ...

    def insert(
        self,
        index: int,
        child: After
        | Before
        | Default
        | Group
        | Join
        | Nest
        | Omit
        | PreserveBlanks
        | Render
        | RuleConfig
        | TriviaPreserve,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render | RuleConfig | TriviaPreserve,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: After
        | Before
        | Default
        | Group
        | Join
        | Nest
        | Omit
        | PreserveBlanks
        | Render
        | RuleConfig
        | TriviaPreserve,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_after(self, child: After) -> None: ...

    def extend_after(self, children: typing.Iterable[After]) -> None: ...

    def children_after(self) -> typing.Iterator[After]: ...

    def child_after(self) -> After: ...

    def maybe_after(self) -> After | None: ...

    def append_before(self, child: Before) -> None: ...

    def extend_before(self, children: typing.Iterable[Before]) -> None: ...

    def children_before(self) -> typing.Iterator[Before]: ...

    def child_before(self) -> Before: ...

    def maybe_before(self) -> Before | None: ...

    def append_default(self, child: Default) -> None: ...

    def extend_default(self, children: typing.Iterable[Default]) -> None: ...

    def children_default(self) -> typing.Iterator[Default]: ...

    def child_default(self) -> Default: ...

    def maybe_default(self) -> Default | None: ...

    def append_group(self, child: Group) -> None: ...

    def extend_group(self, children: typing.Iterable[Group]) -> None: ...

    def children_group(self) -> typing.Iterator[Group]: ...

    def child_group(self) -> Group: ...

    def maybe_group(self) -> Group | None: ...

    def append_join(self, child: Join) -> None: ...

    def extend_join(self, children: typing.Iterable[Join]) -> None: ...

    def children_join(self) -> typing.Iterator[Join]: ...

    def child_join(self) -> Join: ...

    def maybe_join(self) -> Join | None: ...

    def append_nest(self, child: Nest) -> None: ...

    def extend_nest(self, children: typing.Iterable[Nest]) -> None: ...

    def children_nest(self) -> typing.Iterator[Nest]: ...

    def child_nest(self) -> Nest: ...

    def maybe_nest(self) -> Nest | None: ...

    def append_omit(self, child: Omit) -> None: ...

    def extend_omit(self, children: typing.Iterable[Omit]) -> None: ...

    def children_omit(self) -> typing.Iterator[Omit]: ...

    def child_omit(self) -> Omit: ...

    def maybe_omit(self) -> Omit | None: ...

    def append_preserve_blanks(self, child: PreserveBlanks) -> None: ...

    def extend_preserve_blanks(self, children: typing.Iterable[PreserveBlanks]) -> None: ...

    def children_preserve_blanks(self) -> typing.Iterator[PreserveBlanks]: ...

    def child_preserve_blanks(self) -> PreserveBlanks: ...

    def maybe_preserve_blanks(self) -> PreserveBlanks | None: ...

    def append_render(self, child: Render) -> None: ...

    def extend_render(self, children: typing.Iterable[Render]) -> None: ...

    def children_render(self) -> typing.Iterator[Render]: ...

    def child_render(self) -> Render: ...

    def maybe_render(self) -> Render | None: ...

    def append_rule_config(self, child: RuleConfig) -> None: ...

    def extend_rule_config(self, children: typing.Iterable[RuleConfig]) -> None: ...

    def children_rule_config(self) -> typing.Iterator[RuleConfig]: ...

    def child_rule_config(self) -> RuleConfig: ...

    def maybe_rule_config(self) -> RuleConfig | None: ...

    def append_trivia_preserve(self, child: TriviaPreserve) -> None: ...

    def extend_trivia_preserve(self, children: typing.Iterable[TriviaPreserve]) -> None: ...

    def children_trivia_preserve(self) -> typing.Iterator[TriviaPreserve]: ...

    def child_trivia_preserve(self) -> TriviaPreserve: ...

    def maybe_trivia_preserve(self) -> TriviaPreserve | None: ...

    def after(self) -> After | None: ...

    def before(self) -> Before | None: ...

    def default(self) -> Default | None: ...

    def group(self) -> Group | None: ...

    def join(self) -> Join | None: ...

    def nest(self) -> Nest | None: ...

    def omit(self) -> Omit | None: ...

    def preserve_blanks(self) -> PreserveBlanks | None: ...

    def render(self) -> Render | None: ...

    def rule_config(self) -> RuleConfig | None: ...

    def trivia_preserve(self) -> TriviaPreserve | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class StatementLabel:
    """Sentinels equal to either backend's Statement labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    AFTER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Statement.Label.AFTER")
    BEFORE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Statement.Label.BEFORE")
    DEFAULT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Statement.Label.DEFAULT"
    )
    GROUP: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Statement.Label.GROUP")
    JOIN: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Statement.Label.JOIN")
    NEST: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Statement.Label.NEST")
    OMIT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Statement.Label.OMIT")
    PRESERVE_BLANKS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Statement.Label.PRESERVE_BLANKS"
    )
    RENDER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Statement.Label.RENDER")
    RULE_CONFIG: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Statement.Label.RULE_CONFIG"
    )
    TRIVIA_PRESERVE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Statement.Label.TRIVIA_PRESERVE"
    )


class Default(typing.Protocol):
    kind: typing.Literal[NodeKind.DEFAULT] = NodeKind.DEFAULT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Default) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def insert(
        self,
        index: int,
        child: Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_spacing(self, child: Spacing) -> None: ...

    def extend_spacing(self, children: typing.Iterable[Spacing]) -> None: ...

    def children_spacing(self) -> typing.Iterator[Spacing]: ...

    def child_spacing(self) -> Spacing: ...

    def maybe_spacing(self) -> Spacing | None: ...

    def append_ws_allowed(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_ws_allowed(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_ws_allowed(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_ws_required(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_ws_required(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_ws_required(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def spacing(self) -> Spacing: ...

    def ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def ws_allowed_text(self) -> str | None: ...

    def ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def ws_required_text(self) -> str | None: ...


class DefaultLabel:
    """Sentinels equal to either backend's Default labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    SPACING: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Default.Label.SPACING")
    WS_ALLOWED: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Default.Label.WS_ALLOWED"
    )
    WS_REQUIRED: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Default.Label.WS_REQUIRED"
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

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
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
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
        ]
    ]: ...

    def append(
        self,
        child: After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: RuleStatement) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
    ]: ...

    def insert(
        self,
        index: int,
        child: After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_after(self, child: After) -> None: ...

    def extend_after(self, children: typing.Iterable[After]) -> None: ...

    def children_after(self) -> typing.Iterator[After]: ...

    def child_after(self) -> After: ...

    def maybe_after(self) -> After | None: ...

    def append_before(self, child: Before) -> None: ...

    def extend_before(self, children: typing.Iterable[Before]) -> None: ...

    def children_before(self) -> typing.Iterator[Before]: ...

    def child_before(self) -> Before: ...

    def maybe_before(self) -> Before | None: ...

    def append_default(self, child: Default) -> None: ...

    def extend_default(self, children: typing.Iterable[Default]) -> None: ...

    def children_default(self) -> typing.Iterator[Default]: ...

    def child_default(self) -> Default: ...

    def maybe_default(self) -> Default | None: ...

    def append_group(self, child: Group) -> None: ...

    def extend_group(self, children: typing.Iterable[Group]) -> None: ...

    def children_group(self) -> typing.Iterator[Group]: ...

    def child_group(self) -> Group: ...

    def maybe_group(self) -> Group | None: ...

    def append_join(self, child: Join) -> None: ...

    def extend_join(self, children: typing.Iterable[Join]) -> None: ...

    def children_join(self) -> typing.Iterator[Join]: ...

    def child_join(self) -> Join: ...

    def maybe_join(self) -> Join | None: ...

    def append_nest(self, child: Nest) -> None: ...

    def extend_nest(self, children: typing.Iterable[Nest]) -> None: ...

    def children_nest(self) -> typing.Iterator[Nest]: ...

    def child_nest(self) -> Nest: ...

    def maybe_nest(self) -> Nest | None: ...

    def append_omit(self, child: Omit) -> None: ...

    def extend_omit(self, children: typing.Iterable[Omit]) -> None: ...

    def children_omit(self) -> typing.Iterator[Omit]: ...

    def child_omit(self) -> Omit: ...

    def maybe_omit(self) -> Omit | None: ...

    def append_preserve_blanks(self, child: PreserveBlanks) -> None: ...

    def extend_preserve_blanks(self, children: typing.Iterable[PreserveBlanks]) -> None: ...

    def children_preserve_blanks(self) -> typing.Iterator[PreserveBlanks]: ...

    def child_preserve_blanks(self) -> PreserveBlanks: ...

    def maybe_preserve_blanks(self) -> PreserveBlanks | None: ...

    def append_render(self, child: Render) -> None: ...

    def extend_render(self, children: typing.Iterable[Render]) -> None: ...

    def children_render(self) -> typing.Iterator[Render]: ...

    def child_render(self) -> Render: ...

    def maybe_render(self) -> Render | None: ...

    def after(self) -> After | None: ...

    def before(self) -> Before | None: ...

    def default(self) -> Default | None: ...

    def group(self) -> Group | None: ...

    def join(self) -> Join | None: ...

    def nest(self) -> Nest | None: ...

    def omit(self) -> Omit | None: ...

    def preserve_blanks(self) -> PreserveBlanks | None: ...

    def render(self) -> Render | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class RuleStatementLabel:
    """Sentinels equal to either backend's RuleStatement labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    AFTER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.AFTER"
    )
    BEFORE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.BEFORE"
    )
    DEFAULT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.DEFAULT"
    )
    GROUP: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.GROUP"
    )
    JOIN: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("RuleStatement.Label.JOIN")
    NEST: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("RuleStatement.Label.NEST")
    OMIT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("RuleStatement.Label.OMIT")
    PRESERVE_BLANKS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.PRESERVE_BLANKS"
    )
    RENDER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "RuleStatement.Label.RENDER"
    )


class Group(typing.Protocol):
    kind: typing.Literal[NodeKind.GROUP] = NodeKind.GROUP
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, FromSpec | ToSpec | Trivia]]: ...

    def append(
        self, child: FromSpec | ToSpec | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[FromSpec | ToSpec | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Group) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, FromSpec | ToSpec | Trivia]: ...

    def insert(
        self,
        index: int,
        child: FromSpec | ToSpec | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, FromSpec | ToSpec | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: FromSpec | ToSpec | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_from_spec(self, child: FromSpec) -> None: ...

    def extend_from_spec(self, children: typing.Iterable[FromSpec]) -> None: ...

    def children_from_spec(self) -> typing.Iterator[FromSpec]: ...

    def child_from_spec(self) -> FromSpec: ...

    def maybe_from_spec(self) -> FromSpec | None: ...

    def append_to_spec(self, child: ToSpec) -> None: ...

    def extend_to_spec(self, children: typing.Iterable[ToSpec]) -> None: ...

    def children_to_spec(self) -> typing.Iterator[ToSpec]: ...

    def child_to_spec(self) -> ToSpec: ...

    def maybe_to_spec(self) -> ToSpec | None: ...

    def from_spec(self) -> FromSpec | None: ...

    def to_spec(self) -> ToSpec | None: ...


class GroupLabel:
    """Sentinels equal to either backend's Group labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    FROM_SPEC: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Group.Label.FROM_SPEC"
    )
    TO_SPEC: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Group.Label.TO_SPEC")


class Nest(typing.Protocol):
    kind: typing.Literal[NodeKind.NEST] = NodeKind.NEST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, FromSpec | Integer | ToSpec | Trivia]
    ]: ...

    def append(
        self,
        child: FromSpec | Integer | ToSpec | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[FromSpec | Integer | ToSpec | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Nest) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, FromSpec | Integer | ToSpec | Trivia]: ...

    def insert(
        self,
        index: int,
        child: FromSpec | Integer | ToSpec | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, FromSpec | Integer | ToSpec | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: FromSpec | Integer | ToSpec | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_from_spec(self, child: FromSpec) -> None: ...

    def extend_from_spec(self, children: typing.Iterable[FromSpec]) -> None: ...

    def children_from_spec(self) -> typing.Iterator[FromSpec]: ...

    def child_from_spec(self) -> FromSpec: ...

    def maybe_from_spec(self) -> FromSpec | None: ...

    def append_indent(self, child: Integer) -> None: ...

    def extend_indent(self, children: typing.Iterable[Integer]) -> None: ...

    def children_indent(self) -> typing.Iterator[Integer]: ...

    def child_indent(self) -> Integer: ...

    def maybe_indent(self) -> Integer | None: ...

    def append_to_spec(self, child: ToSpec) -> None: ...

    def extend_to_spec(self, children: typing.Iterable[ToSpec]) -> None: ...

    def children_to_spec(self) -> typing.Iterator[ToSpec]: ...

    def child_to_spec(self) -> ToSpec: ...

    def maybe_to_spec(self) -> ToSpec | None: ...

    def from_spec(self) -> FromSpec | None: ...

    def indent(self) -> Integer | None: ...

    def to_spec(self) -> ToSpec | None: ...


class NestLabel:
    """Sentinels equal to either backend's Nest labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    FROM_SPEC: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Nest.Label.FROM_SPEC")
    INDENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Nest.Label.INDENT")
    TO_SPEC: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Nest.Label.TO_SPEC")


class Join(typing.Protocol):
    kind: typing.Literal[NodeKind.JOIN] = NodeKind.JOIN
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocLiteral | FromSpec | ToSpec | Trivia]
    ]: ...

    def append(
        self,
        child: DocLiteral | FromSpec | ToSpec | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[DocLiteral | FromSpec | ToSpec | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Join) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocLiteral | FromSpec | ToSpec | Trivia]: ...

    def insert(
        self,
        index: int,
        child: DocLiteral | FromSpec | ToSpec | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocLiteral | FromSpec | ToSpec | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: DocLiteral | FromSpec | ToSpec | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_doc_literal(self, child: DocLiteral) -> None: ...

    def extend_doc_literal(self, children: typing.Iterable[DocLiteral]) -> None: ...

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]: ...

    def child_doc_literal(self) -> DocLiteral: ...

    def maybe_doc_literal(self) -> DocLiteral | None: ...

    def append_from_spec(self, child: FromSpec) -> None: ...

    def extend_from_spec(self, children: typing.Iterable[FromSpec]) -> None: ...

    def children_from_spec(self) -> typing.Iterator[FromSpec]: ...

    def child_from_spec(self) -> FromSpec: ...

    def maybe_from_spec(self) -> FromSpec | None: ...

    def append_to_spec(self, child: ToSpec) -> None: ...

    def extend_to_spec(self, children: typing.Iterable[ToSpec]) -> None: ...

    def children_to_spec(self) -> typing.Iterator[ToSpec]: ...

    def child_to_spec(self) -> ToSpec: ...

    def maybe_to_spec(self) -> ToSpec | None: ...

    def doc_literal(self) -> DocLiteral: ...

    def from_spec(self) -> FromSpec | None: ...

    def to_spec(self) -> ToSpec | None: ...


class JoinLabel:
    """Sentinels equal to either backend's Join labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    DOC_LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Join.Label.DOC_LITERAL"
    )
    FROM_SPEC: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Join.Label.FROM_SPEC")
    TO_SPEC: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Join.Label.TO_SPEC")


class FromSpec(typing.Protocol):
    kind: typing.Literal[NodeKind.FROMSPEC] = NodeKind.FROMSPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: FromSpec) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def insert(
        self,
        index: int,
        child: Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_after(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_after(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_after(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_after(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_after(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_from_anchor(self, child: Anchor) -> None: ...

    def extend_from_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_from_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_from_anchor(self) -> Anchor: ...

    def maybe_from_anchor(self) -> Anchor | None: ...

    def after(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def after_text(self) -> str | None: ...

    def from_anchor(self) -> Anchor: ...


class FromSpecLabel:
    """Sentinels equal to either backend's FromSpec labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    AFTER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("FromSpec.Label.AFTER")
    FROM_ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "FromSpec.Label.FROM_ANCHOR"
    )


class ToSpec(typing.Protocol):
    kind: typing.Literal[NodeKind.TOSPEC] = NodeKind.TOSPEC
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ToSpec) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def insert(
        self,
        index: int,
        child: Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_before(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_before(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_before(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_before(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_before(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_to_anchor(self, child: Anchor) -> None: ...

    def extend_to_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_to_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_to_anchor(self) -> Anchor: ...

    def maybe_to_anchor(self) -> Anchor | None: ...

    def before(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def before_text(self) -> str | None: ...

    def to_anchor(self) -> Anchor: ...


class ToSpecLabel:
    """Sentinels equal to either backend's ToSpec labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    BEFORE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("ToSpec.Label.BEFORE")
    TO_ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ToSpec.Label.TO_ANCHOR"
    )


class Anchor(typing.Protocol):
    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | Literal]]: ...

    def append(
        self, child: Identifier | Literal, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Identifier | Literal],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Anchor) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | Literal]: ...

    def insert(
        self, index: int, child: Identifier | Literal, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | Literal]: ...

    def replace_at(
        self, index: int, child: Identifier | Literal, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_label(self, child: Identifier) -> None: ...

    def extend_label(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_label(self) -> typing.Iterator[Identifier]: ...

    def child_label(self) -> Identifier: ...

    def maybe_label(self) -> Identifier | None: ...

    def append_literal(self, child: Literal) -> None: ...

    def extend_literal(self, children: typing.Iterable[Literal]) -> None: ...

    def children_literal(self) -> typing.Iterator[Literal]: ...

    def child_literal(self) -> Literal: ...

    def maybe_literal(self) -> Literal | None: ...

    def label(self) -> Identifier | None: ...

    def literal(self) -> Literal | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class AnchorLabel:
    """Sentinels equal to either backend's Anchor labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    LABEL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Anchor.Label.LABEL")
    LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Anchor.Label.LITERAL")


class After(typing.Protocol):
    kind: typing.Literal[NodeKind.AFTER] = NodeKind.AFTER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | PositionSpecStatement | Trivia]
    ]: ...

    def append(
        self,
        child: Anchor | PositionSpecStatement | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Anchor | PositionSpecStatement | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: After) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | PositionSpecStatement | Trivia]: ...

    def insert(
        self,
        index: int,
        child: Anchor | PositionSpecStatement | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | PositionSpecStatement | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: Anchor | PositionSpecStatement | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_anchor(self, child: Anchor) -> None: ...

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_anchor(self) -> Anchor: ...

    def maybe_anchor(self) -> Anchor | None: ...

    def append_position_spec_statement(self, child: PositionSpecStatement) -> None: ...

    def extend_position_spec_statement(self, children: typing.Iterable[PositionSpecStatement]) -> None: ...

    def children_position_spec_statement(self) -> typing.Iterator[PositionSpecStatement]: ...

    def child_position_spec_statement(self) -> PositionSpecStatement: ...

    def maybe_position_spec_statement(self) -> PositionSpecStatement | None: ...

    def anchor(self) -> Anchor: ...

    def position_spec_statement(self) -> typing.Sequence[PositionSpecStatement]: ...


class AfterLabel:
    """Sentinels equal to either backend's After labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("After.Label.ANCHOR")
    POSITION_SPEC_STATEMENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "After.Label.POSITION_SPEC_STATEMENT"
    )


class Before(typing.Protocol):
    kind: typing.Literal[NodeKind.BEFORE] = NodeKind.BEFORE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | PositionSpecStatement | Trivia]
    ]: ...

    def append(
        self,
        child: Anchor | PositionSpecStatement | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Anchor | PositionSpecStatement | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Before) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | PositionSpecStatement | Trivia]: ...

    def insert(
        self,
        index: int,
        child: Anchor | PositionSpecStatement | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | PositionSpecStatement | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: Anchor | PositionSpecStatement | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_anchor(self, child: Anchor) -> None: ...

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_anchor(self) -> Anchor: ...

    def maybe_anchor(self) -> Anchor | None: ...

    def append_position_spec_statement(self, child: PositionSpecStatement) -> None: ...

    def extend_position_spec_statement(self, children: typing.Iterable[PositionSpecStatement]) -> None: ...

    def children_position_spec_statement(self) -> typing.Iterator[PositionSpecStatement]: ...

    def child_position_spec_statement(self) -> PositionSpecStatement: ...

    def maybe_position_spec_statement(self) -> PositionSpecStatement | None: ...

    def anchor(self) -> Anchor: ...

    def position_spec_statement(self) -> typing.Sequence[PositionSpecStatement]: ...


class BeforeLabel:
    """Sentinels equal to either backend's Before labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Before.Label.ANCHOR")
    POSITION_SPEC_STATEMENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Before.Label.POSITION_SPEC_STATEMENT"
    )


class Omit(typing.Protocol):
    kind: typing.Literal[NodeKind.OMIT] = NodeKind.OMIT
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

    def extend_children(self, other: Omit) -> None: ...

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

    def anchor(self) -> Anchor: ...


class OmitLabel:
    """Sentinels equal to either backend's Omit labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Omit.Label.ANCHOR")


class Render(typing.Protocol):
    kind: typing.Literal[NodeKind.RENDER] = NodeKind.RENDER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | Spacing | Trivia]]: ...

    def append(
        self, child: Anchor | Spacing | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Anchor | Spacing | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Render) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | Spacing | Trivia]: ...

    def insert(
        self,
        index: int,
        child: Anchor | Spacing | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Anchor | Spacing | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: Anchor | Spacing | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_anchor(self, child: Anchor) -> None: ...

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_anchor(self) -> Anchor: ...

    def maybe_anchor(self) -> Anchor | None: ...

    def append_spacing(self, child: Spacing) -> None: ...

    def extend_spacing(self, children: typing.Iterable[Spacing]) -> None: ...

    def children_spacing(self) -> typing.Iterator[Spacing]: ...

    def child_spacing(self) -> Spacing: ...

    def maybe_spacing(self) -> Spacing | None: ...

    def anchor(self) -> Anchor: ...

    def spacing(self) -> Spacing: ...


class RenderLabel:
    """Sentinels equal to either backend's Render labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Render.Label.ANCHOR")
    SPACING: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Render.Label.SPACING")


class PositionSpecStatement(typing.Protocol):
    kind: typing.Literal[NodeKind.POSITIONSPECSTATEMENT] = NodeKind.POSITIONSPECSTATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, PreserveBlanks | Spacing | Trivia]
    ]: ...

    def append(
        self,
        child: PreserveBlanks | Spacing | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[PreserveBlanks | Spacing | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: PositionSpecStatement) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, PreserveBlanks | Spacing | Trivia]: ...

    def insert(
        self,
        index: int,
        child: PreserveBlanks | Spacing | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, PreserveBlanks | Spacing | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: PreserveBlanks | Spacing | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_preserve_blanks(self, child: PreserveBlanks) -> None: ...

    def extend_preserve_blanks(self, children: typing.Iterable[PreserveBlanks]) -> None: ...

    def children_preserve_blanks(self) -> typing.Iterator[PreserveBlanks]: ...

    def child_preserve_blanks(self) -> PreserveBlanks: ...

    def maybe_preserve_blanks(self) -> PreserveBlanks | None: ...

    def append_spacing(self, child: Spacing) -> None: ...

    def extend_spacing(self, children: typing.Iterable[Spacing]) -> None: ...

    def children_spacing(self) -> typing.Iterator[Spacing]: ...

    def child_spacing(self) -> Spacing: ...

    def maybe_spacing(self) -> Spacing | None: ...

    def preserve_blanks(self) -> PreserveBlanks | None: ...

    def spacing(self) -> Spacing | None: ...


class PositionSpecStatementLabel:
    """Sentinels equal to either backend's PositionSpecStatement labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    PRESERVE_BLANKS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "PositionSpecStatement.Label.PRESERVE_BLANKS"
    )
    SPACING: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "PositionSpecStatement.Label.SPACING"
    )


class Spacing(typing.Protocol):
    kind: typing.Literal[NodeKind.SPACING] = NodeKind.SPACING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Spacing) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def insert(
        self,
        index: int,
        child: Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_blank(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_blank(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_blank(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_blank(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_blank(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_bsp(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_bsp(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_bsp(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_bsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_bsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_hard(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_hard(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_hard(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_hard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_hard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_nbsp(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_nbsp(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_nbsp(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_nbsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_nbsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_nil(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_nil(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_nil(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_nil(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_nil(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_num_blanks(self, child: Integer) -> None: ...

    def extend_num_blanks(self, children: typing.Iterable[Integer]) -> None: ...

    def children_num_blanks(self) -> typing.Iterator[Integer]: ...

    def child_num_blanks(self) -> Integer: ...

    def maybe_num_blanks(self) -> Integer | None: ...

    def append_soft(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_soft(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_soft(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_soft(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_soft(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def blank(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def blank_text(self) -> str | None: ...

    def bsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def bsp_text(self) -> str | None: ...

    def hard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def hard_text(self) -> str | None: ...

    def nbsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def nbsp_text(self) -> str | None: ...

    def nil(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def nil_text(self) -> str | None: ...

    def num_blanks(self) -> Integer | None: ...

    def soft(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def soft_text(self) -> str | None: ...


class SpacingLabel:
    """Sentinels equal to either backend's Spacing labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    BLANK: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Spacing.Label.BLANK")
    BSP: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Spacing.Label.BSP")
    HARD: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Spacing.Label.HARD")
    NBSP: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Spacing.Label.NBSP")
    NIL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Spacing.Label.NIL")
    NUM_BLANKS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Spacing.Label.NUM_BLANKS"
    )
    SOFT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Spacing.Label.SOFT")


class DocLiteral(typing.Protocol):
    kind: typing.Literal[NodeKind.DOCLITERAL] = NodeKind.DOCLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral,
        ]
    ]: ...

    def append(
        self,
        child: CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: DocLiteral) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral,
    ]: ...

    def insert(
        self,
        index: int,
        child: CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_compound_literal(self, child: CompoundLiteral) -> None: ...

    def extend_compound_literal(self, children: typing.Iterable[CompoundLiteral]) -> None: ...

    def children_compound_literal(self) -> typing.Iterator[CompoundLiteral]: ...

    def child_compound_literal(self) -> CompoundLiteral: ...

    def maybe_compound_literal(self) -> CompoundLiteral | None: ...

    def append_concat_literal(self, child: ConcatLiteral) -> None: ...

    def extend_concat_literal(self, children: typing.Iterable[ConcatLiteral]) -> None: ...

    def children_concat_literal(self) -> typing.Iterator[ConcatLiteral]: ...

    def child_concat_literal(self) -> ConcatLiteral: ...

    def maybe_concat_literal(self) -> ConcatLiteral | None: ...

    def append_join_literal(self, child: JoinLiteral) -> None: ...

    def extend_join_literal(self, children: typing.Iterable[JoinLiteral]) -> None: ...

    def children_join_literal(self) -> typing.Iterator[JoinLiteral]: ...

    def child_join_literal(self) -> JoinLiteral: ...

    def maybe_join_literal(self) -> JoinLiteral | None: ...

    def append_spacing(self, child: Spacing) -> None: ...

    def extend_spacing(self, children: typing.Iterable[Spacing]) -> None: ...

    def children_spacing(self) -> typing.Iterator[Spacing]: ...

    def child_spacing(self) -> Spacing: ...

    def maybe_spacing(self) -> Spacing | None: ...

    def append_text_literal(self, child: TextLiteral) -> None: ...

    def extend_text_literal(self, children: typing.Iterable[TextLiteral]) -> None: ...

    def children_text_literal(self) -> typing.Iterator[TextLiteral]: ...

    def child_text_literal(self) -> TextLiteral: ...

    def maybe_text_literal(self) -> TextLiteral | None: ...

    def compound_literal(self) -> CompoundLiteral | None: ...

    def concat_literal(self) -> ConcatLiteral | None: ...

    def join_literal(self) -> JoinLiteral | None: ...

    def spacing(self) -> Spacing | None: ...

    def text_literal(self) -> TextLiteral | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class DocLiteralLabel:
    """Sentinels equal to either backend's DocLiteral labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    COMPOUND_LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "DocLiteral.Label.COMPOUND_LITERAL"
    )
    CONCAT_LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "DocLiteral.Label.CONCAT_LITERAL"
    )
    JOIN_LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "DocLiteral.Label.JOIN_LITERAL"
    )
    SPACING: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "DocLiteral.Label.SPACING"
    )
    TEXT_LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "DocLiteral.Label.TEXT_LITERAL"
    )


class TextLiteral(typing.Protocol):
    kind: typing.Literal[NodeKind.TEXTLITERAL] = NodeKind.TEXTLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Literal | Trivia]]: ...

    def append(
        self, child: Literal | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Literal | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: TextLiteral) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Literal | Trivia]: ...

    def insert(
        self, index: int, child: Literal | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Literal | Trivia]: ...

    def replace_at(
        self, index: int, child: Literal | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_text(self, child: Literal) -> None: ...

    def extend_text(self, children: typing.Iterable[Literal]) -> None: ...

    def children_text(self) -> typing.Iterator[Literal]: ...

    def child_text(self) -> Literal: ...

    def maybe_text(self) -> Literal | None: ...


class TextLiteralLabel:
    """Sentinels equal to either backend's TextLiteral labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    TEXT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("TextLiteral.Label.TEXT")


class ConcatLiteral(typing.Protocol):
    kind: typing.Literal[NodeKind.CONCATLITERAL] = NodeKind.CONCATLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocListLiteral | Trivia]]: ...

    def append(
        self, child: DocListLiteral | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[DocListLiteral | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ConcatLiteral) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocListLiteral | Trivia]: ...

    def insert(
        self,
        index: int,
        child: DocListLiteral | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocListLiteral | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: DocListLiteral | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_doc_list_literal(self, child: DocListLiteral) -> None: ...

    def extend_doc_list_literal(self, children: typing.Iterable[DocListLiteral]) -> None: ...

    def children_doc_list_literal(self) -> typing.Iterator[DocListLiteral]: ...

    def child_doc_list_literal(self) -> DocListLiteral: ...

    def maybe_doc_list_literal(self) -> DocListLiteral | None: ...

    def doc_list_literal(self) -> DocListLiteral: ...


class ConcatLiteralLabel:
    """Sentinels equal to either backend's ConcatLiteral labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    DOC_LIST_LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ConcatLiteral.Label.DOC_LIST_LITERAL"
    )


class JoinLiteral(typing.Protocol):
    kind: typing.Literal[NodeKind.JOINLITERAL] = NodeKind.JOINLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocListLiteral | DocLiteral | Trivia]
    ]: ...

    def append(
        self,
        child: DocListLiteral | DocLiteral | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[DocListLiteral | DocLiteral | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: JoinLiteral) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocListLiteral | DocLiteral | Trivia]: ...

    def insert(
        self,
        index: int,
        child: DocListLiteral | DocLiteral | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocListLiteral | DocLiteral | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: DocListLiteral | DocLiteral | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_doc_list_literal(self, child: DocListLiteral) -> None: ...

    def extend_doc_list_literal(self, children: typing.Iterable[DocListLiteral]) -> None: ...

    def children_doc_list_literal(self) -> typing.Iterator[DocListLiteral]: ...

    def child_doc_list_literal(self) -> DocListLiteral: ...

    def maybe_doc_list_literal(self) -> DocListLiteral | None: ...

    def append_separator(self, child: DocLiteral) -> None: ...

    def extend_separator(self, children: typing.Iterable[DocLiteral]) -> None: ...

    def children_separator(self) -> typing.Iterator[DocLiteral]: ...

    def child_separator(self) -> DocLiteral: ...

    def maybe_separator(self) -> DocLiteral | None: ...

    def doc_list_literal(self) -> DocListLiteral: ...

    def separator(self) -> DocLiteral: ...


class JoinLiteralLabel:
    """Sentinels equal to either backend's JoinLiteral labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    DOC_LIST_LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "JoinLiteral.Label.DOC_LIST_LITERAL"
    )
    SEPARATOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "JoinLiteral.Label.SEPARATOR"
    )


class DocListLiteral(typing.Protocol):
    kind: typing.Literal[NodeKind.DOCLISTLITERAL] = NodeKind.DOCLISTLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocLiteral | Trivia]]: ...

    def append(
        self, child: DocLiteral | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[DocLiteral | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: DocListLiteral) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocLiteral | Trivia]: ...

    def insert(
        self, index: int, child: DocLiteral | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, DocLiteral | Trivia]: ...

    def replace_at(
        self, index: int, child: DocLiteral | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_doc_literal(self, child: DocLiteral) -> None: ...

    def extend_doc_literal(self, children: typing.Iterable[DocLiteral]) -> None: ...

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]: ...

    def child_doc_literal(self) -> DocLiteral: ...

    def maybe_doc_literal(self) -> DocLiteral | None: ...

    def doc_literal(self) -> typing.Sequence[DocLiteral]: ...


class DocListLiteralLabel:
    """Sentinels equal to either backend's DocListLiteral labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    DOC_LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "DocListLiteral.Label.DOC_LITERAL"
    )


class CompoundLiteral(typing.Protocol):
    kind: typing.Literal[NodeKind.COMPOUNDLITERAL] = NodeKind.COMPOUNDLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: CompoundLiteral) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def insert(
        self,
        index: int,
        child: DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_doc_literal(self, child: DocLiteral) -> None: ...

    def extend_doc_literal(self, children: typing.Iterable[DocLiteral]) -> None: ...

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]: ...

    def child_doc_literal(self) -> DocLiteral: ...

    def maybe_doc_literal(self) -> DocLiteral | None: ...

    def append_group(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_group(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_group(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_group(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_group(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_nest(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_nest(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_nest(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_nest(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_nest(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def doc_literal(self) -> DocLiteral: ...

    def group(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def group_text(self) -> str | None: ...

    def nest(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def nest_text(self) -> str | None: ...


class CompoundLiteralLabel:
    """Sentinels equal to either backend's CompoundLiteral labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    DOC_LITERAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CompoundLiteral.Label.DOC_LITERAL"
    )
    GROUP: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CompoundLiteral.Label.GROUP"
    )
    NEST: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CompoundLiteral.Label.NEST"
    )


class TriviaPreserve(typing.Protocol):
    kind: typing.Literal[NodeKind.TRIVIAPRESERVE] = NodeKind.TRIVIAPRESERVE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Trivia | TriviaNodeList]]: ...

    def append(
        self, child: Trivia | TriviaNodeList, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Trivia | TriviaNodeList],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: TriviaPreserve) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Trivia | TriviaNodeList]: ...

    def insert(
        self,
        index: int,
        child: Trivia | TriviaNodeList,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Trivia | TriviaNodeList]: ...

    def replace_at(
        self,
        index: int,
        child: Trivia | TriviaNodeList,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_trivia_node_list(self, child: TriviaNodeList) -> None: ...

    def extend_trivia_node_list(self, children: typing.Iterable[TriviaNodeList]) -> None: ...

    def children_trivia_node_list(self) -> typing.Iterator[TriviaNodeList]: ...

    def child_trivia_node_list(self) -> TriviaNodeList: ...

    def maybe_trivia_node_list(self) -> TriviaNodeList | None: ...

    def trivia_node_list(self) -> TriviaNodeList: ...


class TriviaPreserveLabel:
    """Sentinels equal to either backend's TriviaPreserve labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    TRIVIA_NODE_LIST: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "TriviaPreserve.Label.TRIVIA_NODE_LIST"
    )


class TriviaNodeList(typing.Protocol):
    kind: typing.Literal[NodeKind.TRIVIANODELIST] = NodeKind.TRIVIANODELIST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | Trivia]]: ...

    def append(
        self, child: Identifier | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Identifier | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: TriviaNodeList) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | Trivia]: ...

    def insert(
        self, index: int, child: Identifier | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Identifier | Trivia]: ...

    def replace_at(
        self, index: int, child: Identifier | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_identifier(self, child: Identifier) -> None: ...

    def extend_identifier(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_identifier(self) -> typing.Iterator[Identifier]: ...

    def child_identifier(self) -> Identifier: ...

    def maybe_identifier(self) -> Identifier | None: ...

    def identifier(self) -> typing.Sequence[Identifier]: ...


class TriviaNodeListLabel:
    """Sentinels equal to either backend's TriviaNodeList labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    IDENTIFIER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "TriviaNodeList.Label.IDENTIFIER"
    )


class PreserveBlanks(typing.Protocol):
    kind: typing.Literal[NodeKind.PRESERVEBLANKS] = NodeKind.PRESERVEBLANKS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Integer | Trivia]]: ...

    def append(
        self, child: Integer | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Integer | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: PreserveBlanks) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Integer | Trivia]: ...

    def insert(
        self, index: int, child: Integer | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Integer | Trivia]: ...

    def replace_at(
        self, index: int, child: Integer | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_count(self, child: Integer) -> None: ...

    def extend_count(self, children: typing.Iterable[Integer]) -> None: ...

    def children_count(self) -> typing.Iterator[Integer]: ...

    def child_count(self) -> Integer: ...

    def maybe_count(self) -> Integer | None: ...

    def count(self) -> Integer: ...


class PreserveBlanksLabel:
    """Sentinels equal to either backend's PreserveBlanks labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    COUNT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "PreserveBlanks.Label.COUNT"
    )


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

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
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

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Literal.Label.VALUE")


class Integer(typing.Protocol):
    kind: typing.Literal[NodeKind.INTEGER] = NodeKind.INTEGER
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

    def extend_children(self, other: Integer) -> None: ...

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


class IntegerLabel:
    """Sentinels equal to either backend's Integer labels, for identifying one.

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Integer.Label.VALUE")


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

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
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

    Every mutator on every backend accepts one and stores the mutated node's own
    label member in its place: a label is matched by canonical name, not by identity.
    A label read off a tree keeps whatever object the backend put there.
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
    def Formatter(self) -> type[Formatter]: ...

    @property
    def Statement(self) -> type[Statement]: ...

    @property
    def Default(self) -> type[Default]: ...

    @property
    def RuleConfig(self) -> type[RuleConfig]: ...

    @property
    def RuleStatement(self) -> type[RuleStatement]: ...

    @property
    def Group(self) -> type[Group]: ...

    @property
    def Nest(self) -> type[Nest]: ...

    @property
    def Join(self) -> type[Join]: ...

    @property
    def FromSpec(self) -> type[FromSpec]: ...

    @property
    def ToSpec(self) -> type[ToSpec]: ...

    @property
    def Anchor(self) -> type[Anchor]: ...

    @property
    def After(self) -> type[After]: ...

    @property
    def Before(self) -> type[Before]: ...

    @property
    def Omit(self) -> type[Omit]: ...

    @property
    def Render(self) -> type[Render]: ...

    @property
    def PositionSpecStatement(self) -> type[PositionSpecStatement]: ...

    @property
    def Spacing(self) -> type[Spacing]: ...

    @property
    def DocLiteral(self) -> type[DocLiteral]: ...

    @property
    def TextLiteral(self) -> type[TextLiteral]: ...

    @property
    def ConcatLiteral(self) -> type[ConcatLiteral]: ...

    @property
    def JoinLiteral(self) -> type[JoinLiteral]: ...

    @property
    def DocListLiteral(self) -> type[DocListLiteral]: ...

    @property
    def CompoundLiteral(self) -> type[CompoundLiteral]: ...

    @property
    def TriviaPreserve(self) -> type[TriviaPreserve]: ...

    @property
    def TriviaNodeList(self) -> type[TriviaNodeList]: ...

    @property
    def PreserveBlanks(self) -> type[PreserveBlanks]: ...

    @property
    def Identifier(self) -> type[Identifier]: ...

    @property
    def Literal(self) -> type[Literal]: ...

    @property
    def Integer(self) -> type[Integer]: ...

    @property
    def Trivia(self) -> type[Trivia]: ...

    @property
    def LineComment(self) -> type[LineComment]: ...
