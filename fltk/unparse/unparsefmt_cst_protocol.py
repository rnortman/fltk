# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk._native
    import fltk.fegen.pyrt.span
__all__ = [
    "After",
    "Anchor",
    "Before",
    "CompoundLiteral",
    "ConcatLiteral",
    "CstModule",
    "Default",
    "DocListLiteral",
    "DocLiteral",
    "Formatter",
    "FromSpec",
    "Group",
    "Identifier",
    "Integer",
    "Join",
    "JoinLiteral",
    "LineComment",
    "Literal",
    "Nest",
    "NodeKind",
    "Omit",
    "PositionSpecStatement",
    "PreserveBlanks",
    "Render",
    "RuleConfig",
    "RuleStatement",
    "Spacing",
    "Span",
    "Statement",
    "TextLiteral",
    "ToSpec",
    "Trivia",
    "TriviaNodeList",
    "TriviaPreserve",
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
    class Label:
        STATEMENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.FORMATTER] = NodeKind.FORMATTER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Statement | Trivia]]

    def append(self, child: Statement | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Statement | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: Formatter) -> None: ...

    def child(self) -> tuple[Label | None, Statement | Trivia]: ...

    def append_statement(self, child: Statement) -> None: ...

    def extend_statement(self, children: typing.Iterable[Statement]) -> None: ...

    def children_statement(self) -> typing.Iterator[Statement]: ...

    def child_statement(self) -> Statement: ...

    def maybe_statement(self) -> Statement | None: ...


Formatter.Label.STATEMENT = _ProtocolLabelMember("Formatter.Label.STATEMENT")


class Statement(typing.Protocol):
    class Label:
        AFTER: typing.ClassVar[object]
        BEFORE: typing.ClassVar[object]
        DEFAULT: typing.ClassVar[object]
        GROUP: typing.ClassVar[object]
        JOIN: typing.ClassVar[object]
        NEST: typing.ClassVar[object]
        OMIT: typing.ClassVar[object]
        PRESERVE_BLANKS: typing.ClassVar[object]
        RENDER: typing.ClassVar[object]
        RULE_CONFIG: typing.ClassVar[object]
        TRIVIA_PRESERVE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.STATEMENT] = NodeKind.STATEMENT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[
        tuple[
            Label | None,
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
    ]

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
        label: Label | None = None,
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
        label: Label | None = None,
    ) -> None: ...

    def extend_children(self, other: Statement) -> None: ...

    def child(
        self,
    ) -> tuple[
        Label | None,
        After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render | RuleConfig | TriviaPreserve,
    ]: ...

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


Statement.Label.AFTER = _ProtocolLabelMember("Statement.Label.AFTER")
Statement.Label.BEFORE = _ProtocolLabelMember("Statement.Label.BEFORE")
Statement.Label.DEFAULT = _ProtocolLabelMember("Statement.Label.DEFAULT")
Statement.Label.GROUP = _ProtocolLabelMember("Statement.Label.GROUP")
Statement.Label.JOIN = _ProtocolLabelMember("Statement.Label.JOIN")
Statement.Label.NEST = _ProtocolLabelMember("Statement.Label.NEST")
Statement.Label.OMIT = _ProtocolLabelMember("Statement.Label.OMIT")
Statement.Label.PRESERVE_BLANKS = _ProtocolLabelMember("Statement.Label.PRESERVE_BLANKS")
Statement.Label.RENDER = _ProtocolLabelMember("Statement.Label.RENDER")
Statement.Label.RULE_CONFIG = _ProtocolLabelMember("Statement.Label.RULE_CONFIG")
Statement.Label.TRIVIA_PRESERVE = _ProtocolLabelMember("Statement.Label.TRIVIA_PRESERVE")


class Default(typing.Protocol):
    class Label:
        SPACING: typing.ClassVar[object]
        WS_ALLOWED: typing.ClassVar[object]
        WS_REQUIRED: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.DEFAULT] = NodeKind.DEFAULT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Spacing | Trivia | fltk.fegen.pyrt.span.Span]]

    def append(self, child: Spacing | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Spacing | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Default) -> None: ...

    def child(self) -> tuple[Label | None, Spacing | Trivia | fltk.fegen.pyrt.span.Span]: ...

    def append_spacing(self, child: Spacing) -> None: ...

    def extend_spacing(self, children: typing.Iterable[Spacing]) -> None: ...

    def children_spacing(self) -> typing.Iterator[Spacing]: ...

    def child_spacing(self) -> Spacing: ...

    def maybe_spacing(self) -> Spacing | None: ...

    def append_ws_allowed(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_ws_allowed(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_ws_allowed(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_ws_allowed(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_ws_allowed(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_ws_required(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_ws_required(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_ws_required(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_ws_required(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_ws_required(self) -> fltk.fegen.pyrt.span.Span | None: ...


Default.Label.SPACING = _ProtocolLabelMember("Default.Label.SPACING")
Default.Label.WS_ALLOWED = _ProtocolLabelMember("Default.Label.WS_ALLOWED")
Default.Label.WS_REQUIRED = _ProtocolLabelMember("Default.Label.WS_REQUIRED")


class RuleConfig(typing.Protocol):
    class Label:
        RULE_NAME: typing.ClassVar[object]
        RULE_STATEMENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.RULECONFIG] = NodeKind.RULECONFIG
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Identifier | RuleStatement | Trivia]]

    def append(self, child: Identifier | RuleStatement | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Identifier | RuleStatement | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: RuleConfig) -> None: ...

    def child(self) -> tuple[Label | None, Identifier | RuleStatement | Trivia]: ...

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
        AFTER: typing.ClassVar[object]
        BEFORE: typing.ClassVar[object]
        DEFAULT: typing.ClassVar[object]
        GROUP: typing.ClassVar[object]
        JOIN: typing.ClassVar[object]
        NEST: typing.ClassVar[object]
        OMIT: typing.ClassVar[object]
        PRESERVE_BLANKS: typing.ClassVar[object]
        RENDER: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.RULESTATEMENT] = NodeKind.RULESTATEMENT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render]]

    def append(
        self,
        child: After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
        label: Label | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render],
        label: Label | None = None,
    ) -> None: ...

    def extend_children(self, other: RuleStatement) -> None: ...

    def child(
        self,
    ) -> tuple[Label | None, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render]: ...

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


RuleStatement.Label.AFTER = _ProtocolLabelMember("RuleStatement.Label.AFTER")
RuleStatement.Label.BEFORE = _ProtocolLabelMember("RuleStatement.Label.BEFORE")
RuleStatement.Label.DEFAULT = _ProtocolLabelMember("RuleStatement.Label.DEFAULT")
RuleStatement.Label.GROUP = _ProtocolLabelMember("RuleStatement.Label.GROUP")
RuleStatement.Label.JOIN = _ProtocolLabelMember("RuleStatement.Label.JOIN")
RuleStatement.Label.NEST = _ProtocolLabelMember("RuleStatement.Label.NEST")
RuleStatement.Label.OMIT = _ProtocolLabelMember("RuleStatement.Label.OMIT")
RuleStatement.Label.PRESERVE_BLANKS = _ProtocolLabelMember("RuleStatement.Label.PRESERVE_BLANKS")
RuleStatement.Label.RENDER = _ProtocolLabelMember("RuleStatement.Label.RENDER")


class Group(typing.Protocol):
    class Label:
        FROM_SPEC: typing.ClassVar[object]
        TO_SPEC: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.GROUP] = NodeKind.GROUP
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, FromSpec | ToSpec | Trivia]]

    def append(self, child: FromSpec | ToSpec | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[FromSpec | ToSpec | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: Group) -> None: ...

    def child(self) -> tuple[Label | None, FromSpec | ToSpec | Trivia]: ...

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


Group.Label.FROM_SPEC = _ProtocolLabelMember("Group.Label.FROM_SPEC")
Group.Label.TO_SPEC = _ProtocolLabelMember("Group.Label.TO_SPEC")


class Nest(typing.Protocol):
    class Label:
        FROM_SPEC: typing.ClassVar[object]
        INDENT: typing.ClassVar[object]
        TO_SPEC: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.NEST] = NodeKind.NEST
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]]

    def append(self, child: FromSpec | Integer | ToSpec | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[FromSpec | Integer | ToSpec | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Nest) -> None: ...

    def child(self) -> tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]: ...

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


Nest.Label.FROM_SPEC = _ProtocolLabelMember("Nest.Label.FROM_SPEC")
Nest.Label.INDENT = _ProtocolLabelMember("Nest.Label.INDENT")
Nest.Label.TO_SPEC = _ProtocolLabelMember("Nest.Label.TO_SPEC")


class Join(typing.Protocol):
    class Label:
        DOC_LITERAL: typing.ClassVar[object]
        FROM_SPEC: typing.ClassVar[object]
        TO_SPEC: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.JOIN] = NodeKind.JOIN
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, DocLiteral | FromSpec | ToSpec | Trivia]]

    def append(self, child: DocLiteral | FromSpec | ToSpec | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[DocLiteral | FromSpec | ToSpec | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Join) -> None: ...

    def child(self) -> tuple[Label | None, DocLiteral | FromSpec | ToSpec | Trivia]: ...

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


Join.Label.DOC_LITERAL = _ProtocolLabelMember("Join.Label.DOC_LITERAL")
Join.Label.FROM_SPEC = _ProtocolLabelMember("Join.Label.FROM_SPEC")
Join.Label.TO_SPEC = _ProtocolLabelMember("Join.Label.TO_SPEC")


class FromSpec(typing.Protocol):
    class Label:
        AFTER: typing.ClassVar[object]
        FROM_ANCHOR: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.FROMSPEC] = NodeKind.FROMSPEC
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]]

    def append(self, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Anchor | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: FromSpec) -> None: ...

    def child(self) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]: ...

    def append_after(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_after(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_after(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_after(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_after(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_from_anchor(self, child: Anchor) -> None: ...

    def extend_from_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_from_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_from_anchor(self) -> Anchor: ...

    def maybe_from_anchor(self) -> Anchor | None: ...


FromSpec.Label.AFTER = _ProtocolLabelMember("FromSpec.Label.AFTER")
FromSpec.Label.FROM_ANCHOR = _ProtocolLabelMember("FromSpec.Label.FROM_ANCHOR")


class ToSpec(typing.Protocol):
    class Label:
        BEFORE: typing.ClassVar[object]
        TO_ANCHOR: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TOSPEC] = NodeKind.TOSPEC
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]]

    def append(self, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Anchor | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: ToSpec) -> None: ...

    def child(self) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]: ...

    def append_before(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_before(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_before(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_before(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_before(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_to_anchor(self, child: Anchor) -> None: ...

    def extend_to_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_to_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_to_anchor(self) -> Anchor: ...

    def maybe_to_anchor(self) -> Anchor | None: ...


ToSpec.Label.BEFORE = _ProtocolLabelMember("ToSpec.Label.BEFORE")
ToSpec.Label.TO_ANCHOR = _ProtocolLabelMember("ToSpec.Label.TO_ANCHOR")


class Anchor(typing.Protocol):
    class Label:
        LABEL: typing.ClassVar[object]
        LITERAL: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Identifier | Literal]]

    def append(self, child: Identifier | Literal, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Identifier | Literal], label: Label | None = None) -> None: ...

    def extend_children(self, other: Anchor) -> None: ...

    def child(self) -> tuple[Label | None, Identifier | Literal]: ...

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


Anchor.Label.LABEL = _ProtocolLabelMember("Anchor.Label.LABEL")
Anchor.Label.LITERAL = _ProtocolLabelMember("Anchor.Label.LITERAL")


class After(typing.Protocol):
    class Label:
        ANCHOR: typing.ClassVar[object]
        POSITION_SPEC_STATEMENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.AFTER] = NodeKind.AFTER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Anchor | PositionSpecStatement | Trivia]]

    def append(self, child: Anchor | PositionSpecStatement | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Anchor | PositionSpecStatement | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: After) -> None: ...

    def child(self) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]: ...

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


After.Label.ANCHOR = _ProtocolLabelMember("After.Label.ANCHOR")
After.Label.POSITION_SPEC_STATEMENT = _ProtocolLabelMember("After.Label.POSITION_SPEC_STATEMENT")


class Before(typing.Protocol):
    class Label:
        ANCHOR: typing.ClassVar[object]
        POSITION_SPEC_STATEMENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.BEFORE] = NodeKind.BEFORE
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Anchor | PositionSpecStatement | Trivia]]

    def append(self, child: Anchor | PositionSpecStatement | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Anchor | PositionSpecStatement | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Before) -> None: ...

    def child(self) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]: ...

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


Before.Label.ANCHOR = _ProtocolLabelMember("Before.Label.ANCHOR")
Before.Label.POSITION_SPEC_STATEMENT = _ProtocolLabelMember("Before.Label.POSITION_SPEC_STATEMENT")


class Omit(typing.Protocol):
    class Label:
        ANCHOR: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.OMIT] = NodeKind.OMIT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Anchor | Trivia]]

    def append(self, child: Anchor | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Anchor | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: Omit) -> None: ...

    def child(self) -> tuple[Label | None, Anchor | Trivia]: ...

    def append_anchor(self, child: Anchor) -> None: ...

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_anchor(self) -> Anchor: ...

    def maybe_anchor(self) -> Anchor | None: ...


Omit.Label.ANCHOR = _ProtocolLabelMember("Omit.Label.ANCHOR")


class Render(typing.Protocol):
    class Label:
        ANCHOR: typing.ClassVar[object]
        SPACING: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.RENDER] = NodeKind.RENDER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Anchor | Spacing | Trivia]]

    def append(self, child: Anchor | Spacing | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Anchor | Spacing | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: Render) -> None: ...

    def child(self) -> tuple[Label | None, Anchor | Spacing | Trivia]: ...

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


Render.Label.ANCHOR = _ProtocolLabelMember("Render.Label.ANCHOR")
Render.Label.SPACING = _ProtocolLabelMember("Render.Label.SPACING")


class PositionSpecStatement(typing.Protocol):
    class Label:
        PRESERVE_BLANKS: typing.ClassVar[object]
        SPACING: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.POSITIONSPECSTATEMENT] = NodeKind.POSITIONSPECSTATEMENT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, PreserveBlanks | Spacing | Trivia]]

    def append(self, child: PreserveBlanks | Spacing | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[PreserveBlanks | Spacing | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: PositionSpecStatement) -> None: ...

    def child(self) -> tuple[Label | None, PreserveBlanks | Spacing | Trivia]: ...

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


PositionSpecStatement.Label.PRESERVE_BLANKS = _ProtocolLabelMember("PositionSpecStatement.Label.PRESERVE_BLANKS")
PositionSpecStatement.Label.SPACING = _ProtocolLabelMember("PositionSpecStatement.Label.SPACING")


class Spacing(typing.Protocol):
    class Label:
        BLANK: typing.ClassVar[object]
        BSP: typing.ClassVar[object]
        HARD: typing.ClassVar[object]
        NBSP: typing.ClassVar[object]
        NIL: typing.ClassVar[object]
        NUM_BLANKS: typing.ClassVar[object]
        SOFT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.SPACING] = NodeKind.SPACING
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Integer | Trivia | fltk.fegen.pyrt.span.Span]]

    def append(self, child: Integer | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Integer | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Spacing) -> None: ...

    def child(self) -> tuple[Label | None, Integer | Trivia | fltk.fegen.pyrt.span.Span]: ...

    def append_blank(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_blank(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_blank(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_blank(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_blank(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_bsp(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_bsp(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_bsp(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_bsp(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_bsp(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_hard(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_hard(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_hard(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_hard(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_hard(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_nbsp(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_nbsp(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_nbsp(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_nbsp(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_nbsp(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_nil(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_nil(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_nil(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_nil(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_nil(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_num_blanks(self, child: Integer) -> None: ...

    def extend_num_blanks(self, children: typing.Iterable[Integer]) -> None: ...

    def children_num_blanks(self) -> typing.Iterator[Integer]: ...

    def child_num_blanks(self) -> Integer: ...

    def maybe_num_blanks(self) -> Integer | None: ...

    def append_soft(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_soft(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_soft(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_soft(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_soft(self) -> fltk.fegen.pyrt.span.Span | None: ...


Spacing.Label.BLANK = _ProtocolLabelMember("Spacing.Label.BLANK")
Spacing.Label.BSP = _ProtocolLabelMember("Spacing.Label.BSP")
Spacing.Label.HARD = _ProtocolLabelMember("Spacing.Label.HARD")
Spacing.Label.NBSP = _ProtocolLabelMember("Spacing.Label.NBSP")
Spacing.Label.NIL = _ProtocolLabelMember("Spacing.Label.NIL")
Spacing.Label.NUM_BLANKS = _ProtocolLabelMember("Spacing.Label.NUM_BLANKS")
Spacing.Label.SOFT = _ProtocolLabelMember("Spacing.Label.SOFT")


class DocLiteral(typing.Protocol):
    class Label:
        COMPOUND_LITERAL: typing.ClassVar[object]
        CONCAT_LITERAL: typing.ClassVar[object]
        JOIN_LITERAL: typing.ClassVar[object]
        SPACING: typing.ClassVar[object]
        TEXT_LITERAL: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.DOCLITERAL] = NodeKind.DOCLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral]]

    def append(
        self, child: CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral, label: Label | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral],
        label: Label | None = None,
    ) -> None: ...

    def extend_children(self, other: DocLiteral) -> None: ...

    def child(self) -> tuple[Label | None, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral]: ...

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


DocLiteral.Label.COMPOUND_LITERAL = _ProtocolLabelMember("DocLiteral.Label.COMPOUND_LITERAL")
DocLiteral.Label.CONCAT_LITERAL = _ProtocolLabelMember("DocLiteral.Label.CONCAT_LITERAL")
DocLiteral.Label.JOIN_LITERAL = _ProtocolLabelMember("DocLiteral.Label.JOIN_LITERAL")
DocLiteral.Label.SPACING = _ProtocolLabelMember("DocLiteral.Label.SPACING")
DocLiteral.Label.TEXT_LITERAL = _ProtocolLabelMember("DocLiteral.Label.TEXT_LITERAL")


class TextLiteral(typing.Protocol):
    class Label:
        TEXT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TEXTLITERAL] = NodeKind.TEXTLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Literal | Trivia]]

    def append(self, child: Literal | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Literal | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: TextLiteral) -> None: ...

    def child(self) -> tuple[Label | None, Literal | Trivia]: ...

    def append_text(self, child: Literal) -> None: ...

    def extend_text(self, children: typing.Iterable[Literal]) -> None: ...

    def children_text(self) -> typing.Iterator[Literal]: ...

    def child_text(self) -> Literal: ...

    def maybe_text(self) -> Literal | None: ...


TextLiteral.Label.TEXT = _ProtocolLabelMember("TextLiteral.Label.TEXT")


class ConcatLiteral(typing.Protocol):
    class Label:
        DOC_LIST_LITERAL: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.CONCATLITERAL] = NodeKind.CONCATLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, DocListLiteral | Trivia]]

    def append(self, child: DocListLiteral | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[DocListLiteral | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: ConcatLiteral) -> None: ...

    def child(self) -> tuple[Label | None, DocListLiteral | Trivia]: ...

    def append_doc_list_literal(self, child: DocListLiteral) -> None: ...

    def extend_doc_list_literal(self, children: typing.Iterable[DocListLiteral]) -> None: ...

    def children_doc_list_literal(self) -> typing.Iterator[DocListLiteral]: ...

    def child_doc_list_literal(self) -> DocListLiteral: ...

    def maybe_doc_list_literal(self) -> DocListLiteral | None: ...


ConcatLiteral.Label.DOC_LIST_LITERAL = _ProtocolLabelMember("ConcatLiteral.Label.DOC_LIST_LITERAL")


class JoinLiteral(typing.Protocol):
    class Label:
        DOC_LIST_LITERAL: typing.ClassVar[object]
        SEPARATOR: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.JOINLITERAL] = NodeKind.JOINLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, DocListLiteral | DocLiteral | Trivia]]

    def append(self, child: DocListLiteral | DocLiteral | Trivia, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[DocListLiteral | DocLiteral | Trivia], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: JoinLiteral) -> None: ...

    def child(self) -> tuple[Label | None, DocListLiteral | DocLiteral | Trivia]: ...

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


JoinLiteral.Label.DOC_LIST_LITERAL = _ProtocolLabelMember("JoinLiteral.Label.DOC_LIST_LITERAL")
JoinLiteral.Label.SEPARATOR = _ProtocolLabelMember("JoinLiteral.Label.SEPARATOR")


class DocListLiteral(typing.Protocol):
    class Label:
        DOC_LITERAL: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.DOCLISTLITERAL] = NodeKind.DOCLISTLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, DocLiteral | Trivia]]

    def append(self, child: DocLiteral | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[DocLiteral | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: DocListLiteral) -> None: ...

    def child(self) -> tuple[Label | None, DocLiteral | Trivia]: ...

    def append_doc_literal(self, child: DocLiteral) -> None: ...

    def extend_doc_literal(self, children: typing.Iterable[DocLiteral]) -> None: ...

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]: ...

    def child_doc_literal(self) -> DocLiteral: ...

    def maybe_doc_literal(self) -> DocLiteral | None: ...


DocListLiteral.Label.DOC_LITERAL = _ProtocolLabelMember("DocListLiteral.Label.DOC_LITERAL")


class CompoundLiteral(typing.Protocol):
    class Label:
        DOC_LITERAL: typing.ClassVar[object]
        GROUP: typing.ClassVar[object]
        NEST: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.COMPOUNDLITERAL] = NodeKind.COMPOUNDLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, DocLiteral | Trivia | fltk.fegen.pyrt.span.Span]]

    def append(self, child: DocLiteral | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[DocLiteral | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: CompoundLiteral) -> None: ...

    def child(self) -> tuple[Label | None, DocLiteral | Trivia | fltk.fegen.pyrt.span.Span]: ...

    def append_doc_literal(self, child: DocLiteral) -> None: ...

    def extend_doc_literal(self, children: typing.Iterable[DocLiteral]) -> None: ...

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]: ...

    def child_doc_literal(self) -> DocLiteral: ...

    def maybe_doc_literal(self) -> DocLiteral | None: ...

    def append_group(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_group(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_group(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_group(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_group(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_nest(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_nest(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_nest(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_nest(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_nest(self) -> fltk.fegen.pyrt.span.Span | None: ...


CompoundLiteral.Label.DOC_LITERAL = _ProtocolLabelMember("CompoundLiteral.Label.DOC_LITERAL")
CompoundLiteral.Label.GROUP = _ProtocolLabelMember("CompoundLiteral.Label.GROUP")
CompoundLiteral.Label.NEST = _ProtocolLabelMember("CompoundLiteral.Label.NEST")


class TriviaPreserve(typing.Protocol):
    class Label:
        TRIVIA_NODE_LIST: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TRIVIAPRESERVE] = NodeKind.TRIVIAPRESERVE
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Trivia | TriviaNodeList]]

    def append(self, child: Trivia | TriviaNodeList, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Trivia | TriviaNodeList], label: Label | None = None) -> None: ...

    def extend_children(self, other: TriviaPreserve) -> None: ...

    def child(self) -> tuple[Label | None, Trivia | TriviaNodeList]: ...

    def append_trivia_node_list(self, child: TriviaNodeList) -> None: ...

    def extend_trivia_node_list(self, children: typing.Iterable[TriviaNodeList]) -> None: ...

    def children_trivia_node_list(self) -> typing.Iterator[TriviaNodeList]: ...

    def child_trivia_node_list(self) -> TriviaNodeList: ...

    def maybe_trivia_node_list(self) -> TriviaNodeList | None: ...


TriviaPreserve.Label.TRIVIA_NODE_LIST = _ProtocolLabelMember("TriviaPreserve.Label.TRIVIA_NODE_LIST")


class TriviaNodeList(typing.Protocol):
    class Label:
        IDENTIFIER: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TRIVIANODELIST] = NodeKind.TRIVIANODELIST
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Identifier | Trivia]]

    def append(self, child: Identifier | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Identifier | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: TriviaNodeList) -> None: ...

    def child(self) -> tuple[Label | None, Identifier | Trivia]: ...

    def append_identifier(self, child: Identifier) -> None: ...

    def extend_identifier(self, children: typing.Iterable[Identifier]) -> None: ...

    def children_identifier(self) -> typing.Iterator[Identifier]: ...

    def child_identifier(self) -> Identifier: ...

    def maybe_identifier(self) -> Identifier | None: ...


TriviaNodeList.Label.IDENTIFIER = _ProtocolLabelMember("TriviaNodeList.Label.IDENTIFIER")


class PreserveBlanks(typing.Protocol):
    class Label:
        COUNT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.PRESERVEBLANKS] = NodeKind.PRESERVEBLANKS
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, Integer | Trivia]]

    def append(self, child: Integer | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Integer | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: PreserveBlanks) -> None: ...

    def child(self) -> tuple[Label | None, Integer | Trivia]: ...

    def append_count(self, child: Integer) -> None: ...

    def extend_count(self, children: typing.Iterable[Integer]) -> None: ...

    def children_count(self) -> typing.Iterator[Integer]: ...

    def child_count(self) -> Integer: ...

    def maybe_count(self) -> Integer | None: ...


PreserveBlanks.Label.COUNT = _ProtocolLabelMember("PreserveBlanks.Label.COUNT")


class Identifier(typing.Protocol):
    class Label:
        NAME: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.IDENTIFIER] = NodeKind.IDENTIFIER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Identifier) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_name(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_name(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_name(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_name(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_name(self) -> fltk.fegen.pyrt.span.Span | None: ...


Identifier.Label.NAME = _ProtocolLabelMember("Identifier.Label.NAME")


class Literal(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LITERAL] = NodeKind.LITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Literal) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_value(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_value(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span.Span | None: ...


Literal.Label.VALUE = _ProtocolLabelMember("Literal.Label.VALUE")


class Integer(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.INTEGER] = NodeKind.INTEGER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: Integer) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_value(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_value(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span.Span | None: ...


Integer.Label.VALUE = _ProtocolLabelMember("Integer.Label.VALUE")


class Trivia(typing.Protocol):
    class Label:
        LINE_COMMENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, LineComment | fltk.fegen.pyrt.span.Span]]

    def append(self, child: LineComment | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[LineComment | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Trivia) -> None: ...

    def child(self) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span.Span]: ...

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
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]]

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None: ...

    def extend_children(self, other: LineComment) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]: ...

    def append_content(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_content(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_content(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_newline(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_newline(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_newline(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_newline(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_newline(self) -> fltk.fegen.pyrt.span.Span | None: ...

    def append_prefix(self, child: fltk.fegen.pyrt.span.Span) -> None: ...

    def extend_prefix(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None: ...

    def children_prefix(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]: ...

    def child_prefix(self) -> fltk.fegen.pyrt.span.Span: ...

    def maybe_prefix(self) -> fltk.fegen.pyrt.span.Span | None: ...


LineComment.Label.CONTENT = _ProtocolLabelMember("LineComment.Label.CONTENT")
LineComment.Label.NEWLINE = _ProtocolLabelMember("LineComment.Label.NEWLINE")
LineComment.Label.PREFIX = _ProtocolLabelMember("LineComment.Label.PREFIX")


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
