from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk._native
    import fltk.fegen.pyrt.span


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


def _get_native_span_type():
    m = sys.modules.get("fltk._native")
    return m.Span if m is not None else None


@dataclasses.dataclass
class Formatter:
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

    kind: typing.Literal[NodeKind.FORMATTER] = NodeKind.FORMATTER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Statement | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Statement | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Statement | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Formatter) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Statement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Statement | Trivia) -> None:
        if not isinstance(child, Statement | Trivia):
            msg = f"Formatter: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Formatter.Label)):
            _cn = "Formatter"
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
            msg = f"Formatter.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Statement | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Formatter.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_statement(self, child: Statement) -> None:
        self.children.append((Formatter.Label.STATEMENT, child))

    def extend_statement(self, children: typing.Iterable[Statement]) -> None:
        self.children.extend((Formatter.Label.STATEMENT, child) for child in children)

    def children_statement(self) -> typing.Iterator[Statement]:
        return (
            typing.cast("Statement", child) for (label, child) in self.children if label == Formatter.Label.STATEMENT
        )

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


Formatter.Label.STATEMENT._fltk_canonical_name = "Formatter.Label.STATEMENT"


@dataclasses.dataclass
class Statement:
    class Label(enum.Enum):
        AFTER = enum.auto()
        BEFORE = enum.auto()
        DEFAULT = enum.auto()
        GROUP = enum.auto()
        JOIN = enum.auto()
        NEST = enum.auto()
        OMIT = enum.auto()
        PRESERVE_BLANKS = enum.auto()
        RENDER = enum.auto()
        RULE_CONFIG = enum.auto()
        TRIVIA_PRESERVE = enum.auto()
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
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
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
    ] = dataclasses.field(default_factory=list)

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
    ) -> None:
        self.children.append((label, child))

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
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Statement) -> None:
        self.children.extend(other.children)

    def child(
        self,
    ) -> tuple[
        Label | None,
        After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render | RuleConfig | TriviaPreserve,
    ]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
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
    ) -> None:
        if not isinstance(
            child,
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
        ):
            msg = f"Statement: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Statement.Label)):
            _cn = "Statement"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

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
    ) -> tuple[
        Label | None,
        After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render | RuleConfig | TriviaPreserve,
    ]:
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
    ) -> None:
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

    def append_after(self, child: After) -> None:
        self.children.append((Statement.Label.AFTER, child))

    def extend_after(self, children: typing.Iterable[After]) -> None:
        self.children.extend((Statement.Label.AFTER, child) for child in children)

    def children_after(self) -> typing.Iterator[After]:
        return (typing.cast("After", child) for (label, child) in self.children if label == Statement.Label.AFTER)

    def child_after(self) -> After:
        children = list(self.children_after())
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> After | None:
        children = list(self.children_after())
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_before(self, child: Before) -> None:
        self.children.append((Statement.Label.BEFORE, child))

    def extend_before(self, children: typing.Iterable[Before]) -> None:
        self.children.extend((Statement.Label.BEFORE, child) for child in children)

    def children_before(self) -> typing.Iterator[Before]:
        return (typing.cast("Before", child) for (label, child) in self.children if label == Statement.Label.BEFORE)

    def child_before(self) -> Before:
        children = list(self.children_before())
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> Before | None:
        children = list(self.children_before())
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_default(self, child: Default) -> None:
        self.children.append((Statement.Label.DEFAULT, child))

    def extend_default(self, children: typing.Iterable[Default]) -> None:
        self.children.extend((Statement.Label.DEFAULT, child) for child in children)

    def children_default(self) -> typing.Iterator[Default]:
        return (typing.cast("Default", child) for (label, child) in self.children if label == Statement.Label.DEFAULT)

    def child_default(self) -> Default:
        children = list(self.children_default())
        if (n := len(children)) != 1:
            msg = f"Expected one default child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_default(self) -> Default | None:
        children = list(self.children_default())
        if (n := len(children)) > 1:
            msg = f"Expected at most one default child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: Group) -> None:
        self.children.append((Statement.Label.GROUP, child))

    def extend_group(self, children: typing.Iterable[Group]) -> None:
        self.children.extend((Statement.Label.GROUP, child) for child in children)

    def children_group(self) -> typing.Iterator[Group]:
        return (typing.cast("Group", child) for (label, child) in self.children if label == Statement.Label.GROUP)

    def child_group(self) -> Group:
        children = list(self.children_group())
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> Group | None:
        children = list(self.children_group())
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_join(self, child: Join) -> None:
        self.children.append((Statement.Label.JOIN, child))

    def extend_join(self, children: typing.Iterable[Join]) -> None:
        self.children.extend((Statement.Label.JOIN, child) for child in children)

    def children_join(self) -> typing.Iterator[Join]:
        return (typing.cast("Join", child) for (label, child) in self.children if label == Statement.Label.JOIN)

    def child_join(self) -> Join:
        children = list(self.children_join())
        if (n := len(children)) != 1:
            msg = f"Expected one join child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_join(self) -> Join | None:
        children = list(self.children_join())
        if (n := len(children)) > 1:
            msg = f"Expected at most one join child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: Nest) -> None:
        self.children.append((Statement.Label.NEST, child))

    def extend_nest(self, children: typing.Iterable[Nest]) -> None:
        self.children.extend((Statement.Label.NEST, child) for child in children)

    def children_nest(self) -> typing.Iterator[Nest]:
        return (typing.cast("Nest", child) for (label, child) in self.children if label == Statement.Label.NEST)

    def child_nest(self) -> Nest:
        children = list(self.children_nest())
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> Nest | None:
        children = list(self.children_nest())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nest child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_omit(self, child: Omit) -> None:
        self.children.append((Statement.Label.OMIT, child))

    def extend_omit(self, children: typing.Iterable[Omit]) -> None:
        self.children.extend((Statement.Label.OMIT, child) for child in children)

    def children_omit(self) -> typing.Iterator[Omit]:
        return (typing.cast("Omit", child) for (label, child) in self.children if label == Statement.Label.OMIT)

    def child_omit(self) -> Omit:
        children = list(self.children_omit())
        if (n := len(children)) != 1:
            msg = f"Expected one omit child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_omit(self) -> Omit | None:
        children = list(self.children_omit())
        if (n := len(children)) > 1:
            msg = f"Expected at most one omit child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_preserve_blanks(self, child: PreserveBlanks) -> None:
        self.children.append((Statement.Label.PRESERVE_BLANKS, child))

    def extend_preserve_blanks(self, children: typing.Iterable[PreserveBlanks]) -> None:
        self.children.extend((Statement.Label.PRESERVE_BLANKS, child) for child in children)

    def children_preserve_blanks(self) -> typing.Iterator[PreserveBlanks]:
        return (
            typing.cast("PreserveBlanks", child)
            for (label, child) in self.children
            if label == Statement.Label.PRESERVE_BLANKS
        )

    def child_preserve_blanks(self) -> PreserveBlanks:
        children = list(self.children_preserve_blanks())
        if (n := len(children)) != 1:
            msg = f"Expected one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_preserve_blanks(self) -> PreserveBlanks | None:
        children = list(self.children_preserve_blanks())
        if (n := len(children)) > 1:
            msg = f"Expected at most one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_render(self, child: Render) -> None:
        self.children.append((Statement.Label.RENDER, child))

    def extend_render(self, children: typing.Iterable[Render]) -> None:
        self.children.extend((Statement.Label.RENDER, child) for child in children)

    def children_render(self) -> typing.Iterator[Render]:
        return (typing.cast("Render", child) for (label, child) in self.children if label == Statement.Label.RENDER)

    def child_render(self) -> Render:
        children = list(self.children_render())
        if (n := len(children)) != 1:
            msg = f"Expected one render child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_render(self) -> Render | None:
        children = list(self.children_render())
        if (n := len(children)) > 1:
            msg = f"Expected at most one render child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

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

    def append_trivia_preserve(self, child: TriviaPreserve) -> None:
        self.children.append((Statement.Label.TRIVIA_PRESERVE, child))

    def extend_trivia_preserve(self, children: typing.Iterable[TriviaPreserve]) -> None:
        self.children.extend((Statement.Label.TRIVIA_PRESERVE, child) for child in children)

    def children_trivia_preserve(self) -> typing.Iterator[TriviaPreserve]:
        return (
            typing.cast("TriviaPreserve", child)
            for (label, child) in self.children
            if label == Statement.Label.TRIVIA_PRESERVE
        )

    def child_trivia_preserve(self) -> TriviaPreserve:
        children = list(self.children_trivia_preserve())
        if (n := len(children)) != 1:
            msg = f"Expected one trivia_preserve child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_trivia_preserve(self) -> TriviaPreserve | None:
        children = list(self.children_trivia_preserve())
        if (n := len(children)) > 1:
            msg = f"Expected at most one trivia_preserve child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Statement.Label.AFTER._fltk_canonical_name = "Statement.Label.AFTER"
Statement.Label.BEFORE._fltk_canonical_name = "Statement.Label.BEFORE"
Statement.Label.DEFAULT._fltk_canonical_name = "Statement.Label.DEFAULT"
Statement.Label.GROUP._fltk_canonical_name = "Statement.Label.GROUP"
Statement.Label.JOIN._fltk_canonical_name = "Statement.Label.JOIN"
Statement.Label.NEST._fltk_canonical_name = "Statement.Label.NEST"
Statement.Label.OMIT._fltk_canonical_name = "Statement.Label.OMIT"
Statement.Label.PRESERVE_BLANKS._fltk_canonical_name = "Statement.Label.PRESERVE_BLANKS"
Statement.Label.RENDER._fltk_canonical_name = "Statement.Label.RENDER"
Statement.Label.RULE_CONFIG._fltk_canonical_name = "Statement.Label.RULE_CONFIG"
Statement.Label.TRIVIA_PRESERVE._fltk_canonical_name = "Statement.Label.TRIVIA_PRESERVE"


@dataclasses.dataclass
class Default:
    class Label(enum.Enum):
        SPACING = enum.auto()
        WS_ALLOWED = enum.auto()
        WS_REQUIRED = enum.auto()
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

    kind: typing.Literal[NodeKind.DEFAULT] = NodeKind.DEFAULT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Spacing | Trivia | fltk.fegen.pyrt.span.Span]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Spacing | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Spacing | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Default) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Spacing | Trivia | fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: Spacing | Trivia | fltk.fegen.pyrt.span.Span) -> None:
        _allowed = Default._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (Spacing, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            Default._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Default._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Default._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Default: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Default.Label)):
            _cn = "Default"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: Spacing | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, Spacing | Trivia | fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Default.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Spacing | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Default.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_spacing(self, child: Spacing) -> None:
        self.children.append((Default.Label.SPACING, child))

    def extend_spacing(self, children: typing.Iterable[Spacing]) -> None:
        self.children.extend((Default.Label.SPACING, child) for child in children)

    def children_spacing(self) -> typing.Iterator[Spacing]:
        return (typing.cast("Spacing", child) for (label, child) in self.children if label == Default.Label.SPACING)

    def child_spacing(self) -> Spacing:
        children = list(self.children_spacing())
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> Spacing | None:
        children = list(self.children_spacing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_allowed(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Default.Label.WS_ALLOWED, child))

    def extend_ws_allowed(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Default.Label.WS_ALLOWED, child) for child in children)

    def children_ws_allowed(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Default.Label.WS_ALLOWED
        )

    def child_ws_allowed(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_ws_allowed())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_allowed(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_ws_allowed())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_required(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Default.Label.WS_REQUIRED, child))

    def extend_ws_required(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Default.Label.WS_REQUIRED, child) for child in children)

    def children_ws_required(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Default.Label.WS_REQUIRED
        )

    def child_ws_required(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_ws_required())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_required(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_ws_required())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Default.Label.SPACING._fltk_canonical_name = "Default.Label.SPACING"
Default.Label.WS_ALLOWED._fltk_canonical_name = "Default.Label.WS_ALLOWED"
Default.Label.WS_REQUIRED._fltk_canonical_name = "Default.Label.WS_REQUIRED"


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
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
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
        AFTER = enum.auto()
        BEFORE = enum.auto()
        DEFAULT = enum.auto()
        GROUP = enum.auto()
        JOIN = enum.auto()
        NEST = enum.auto()
        OMIT = enum.auto()
        PRESERVE_BLANKS = enum.auto()
        RENDER = enum.auto()
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
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[
        tuple[Label | None, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render]
    ] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
        label: Label | None = None,
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: RuleStatement) -> None:
        self.children.extend(other.children)

    def child(
        self,
    ) -> tuple[Label | None, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render
    ) -> None:
        if not isinstance(child, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render):
            msg = f"RuleStatement: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, RuleStatement.Label)):
            _cn = "RuleStatement"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
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
    ) -> tuple[Label | None, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render]:
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
        child: After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render,
        label: Label | None = None,
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

    def append_after(self, child: After) -> None:
        self.children.append((RuleStatement.Label.AFTER, child))

    def extend_after(self, children: typing.Iterable[After]) -> None:
        self.children.extend((RuleStatement.Label.AFTER, child) for child in children)

    def children_after(self) -> typing.Iterator[After]:
        return (typing.cast("After", child) for (label, child) in self.children if label == RuleStatement.Label.AFTER)

    def child_after(self) -> After:
        children = list(self.children_after())
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> After | None:
        children = list(self.children_after())
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_before(self, child: Before) -> None:
        self.children.append((RuleStatement.Label.BEFORE, child))

    def extend_before(self, children: typing.Iterable[Before]) -> None:
        self.children.extend((RuleStatement.Label.BEFORE, child) for child in children)

    def children_before(self) -> typing.Iterator[Before]:
        return (typing.cast("Before", child) for (label, child) in self.children if label == RuleStatement.Label.BEFORE)

    def child_before(self) -> Before:
        children = list(self.children_before())
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> Before | None:
        children = list(self.children_before())
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_default(self, child: Default) -> None:
        self.children.append((RuleStatement.Label.DEFAULT, child))

    def extend_default(self, children: typing.Iterable[Default]) -> None:
        self.children.extend((RuleStatement.Label.DEFAULT, child) for child in children)

    def children_default(self) -> typing.Iterator[Default]:
        return (
            typing.cast("Default", child) for (label, child) in self.children if label == RuleStatement.Label.DEFAULT
        )

    def child_default(self) -> Default:
        children = list(self.children_default())
        if (n := len(children)) != 1:
            msg = f"Expected one default child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_default(self) -> Default | None:
        children = list(self.children_default())
        if (n := len(children)) > 1:
            msg = f"Expected at most one default child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: Group) -> None:
        self.children.append((RuleStatement.Label.GROUP, child))

    def extend_group(self, children: typing.Iterable[Group]) -> None:
        self.children.extend((RuleStatement.Label.GROUP, child) for child in children)

    def children_group(self) -> typing.Iterator[Group]:
        return (typing.cast("Group", child) for (label, child) in self.children if label == RuleStatement.Label.GROUP)

    def child_group(self) -> Group:
        children = list(self.children_group())
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> Group | None:
        children = list(self.children_group())
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_join(self, child: Join) -> None:
        self.children.append((RuleStatement.Label.JOIN, child))

    def extend_join(self, children: typing.Iterable[Join]) -> None:
        self.children.extend((RuleStatement.Label.JOIN, child) for child in children)

    def children_join(self) -> typing.Iterator[Join]:
        return (typing.cast("Join", child) for (label, child) in self.children if label == RuleStatement.Label.JOIN)

    def child_join(self) -> Join:
        children = list(self.children_join())
        if (n := len(children)) != 1:
            msg = f"Expected one join child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_join(self) -> Join | None:
        children = list(self.children_join())
        if (n := len(children)) > 1:
            msg = f"Expected at most one join child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: Nest) -> None:
        self.children.append((RuleStatement.Label.NEST, child))

    def extend_nest(self, children: typing.Iterable[Nest]) -> None:
        self.children.extend((RuleStatement.Label.NEST, child) for child in children)

    def children_nest(self) -> typing.Iterator[Nest]:
        return (typing.cast("Nest", child) for (label, child) in self.children if label == RuleStatement.Label.NEST)

    def child_nest(self) -> Nest:
        children = list(self.children_nest())
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> Nest | None:
        children = list(self.children_nest())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nest child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_omit(self, child: Omit) -> None:
        self.children.append((RuleStatement.Label.OMIT, child))

    def extend_omit(self, children: typing.Iterable[Omit]) -> None:
        self.children.extend((RuleStatement.Label.OMIT, child) for child in children)

    def children_omit(self) -> typing.Iterator[Omit]:
        return (typing.cast("Omit", child) for (label, child) in self.children if label == RuleStatement.Label.OMIT)

    def child_omit(self) -> Omit:
        children = list(self.children_omit())
        if (n := len(children)) != 1:
            msg = f"Expected one omit child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_omit(self) -> Omit | None:
        children = list(self.children_omit())
        if (n := len(children)) > 1:
            msg = f"Expected at most one omit child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_preserve_blanks(self, child: PreserveBlanks) -> None:
        self.children.append((RuleStatement.Label.PRESERVE_BLANKS, child))

    def extend_preserve_blanks(self, children: typing.Iterable[PreserveBlanks]) -> None:
        self.children.extend((RuleStatement.Label.PRESERVE_BLANKS, child) for child in children)

    def children_preserve_blanks(self) -> typing.Iterator[PreserveBlanks]:
        return (
            typing.cast("PreserveBlanks", child)
            for (label, child) in self.children
            if label == RuleStatement.Label.PRESERVE_BLANKS
        )

    def child_preserve_blanks(self) -> PreserveBlanks:
        children = list(self.children_preserve_blanks())
        if (n := len(children)) != 1:
            msg = f"Expected one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_preserve_blanks(self) -> PreserveBlanks | None:
        children = list(self.children_preserve_blanks())
        if (n := len(children)) > 1:
            msg = f"Expected at most one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_render(self, child: Render) -> None:
        self.children.append((RuleStatement.Label.RENDER, child))

    def extend_render(self, children: typing.Iterable[Render]) -> None:
        self.children.extend((RuleStatement.Label.RENDER, child) for child in children)

    def children_render(self) -> typing.Iterator[Render]:
        return (typing.cast("Render", child) for (label, child) in self.children if label == RuleStatement.Label.RENDER)

    def child_render(self) -> Render:
        children = list(self.children_render())
        if (n := len(children)) != 1:
            msg = f"Expected one render child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_render(self) -> Render | None:
        children = list(self.children_render())
        if (n := len(children)) > 1:
            msg = f"Expected at most one render child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


RuleStatement.Label.AFTER._fltk_canonical_name = "RuleStatement.Label.AFTER"
RuleStatement.Label.BEFORE._fltk_canonical_name = "RuleStatement.Label.BEFORE"
RuleStatement.Label.DEFAULT._fltk_canonical_name = "RuleStatement.Label.DEFAULT"
RuleStatement.Label.GROUP._fltk_canonical_name = "RuleStatement.Label.GROUP"
RuleStatement.Label.JOIN._fltk_canonical_name = "RuleStatement.Label.JOIN"
RuleStatement.Label.NEST._fltk_canonical_name = "RuleStatement.Label.NEST"
RuleStatement.Label.OMIT._fltk_canonical_name = "RuleStatement.Label.OMIT"
RuleStatement.Label.PRESERVE_BLANKS._fltk_canonical_name = "RuleStatement.Label.PRESERVE_BLANKS"
RuleStatement.Label.RENDER._fltk_canonical_name = "RuleStatement.Label.RENDER"


@dataclasses.dataclass
class Group:
    class Label(enum.Enum):
        FROM_SPEC = enum.auto()
        TO_SPEC = enum.auto()
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

    kind: typing.Literal[NodeKind.GROUP] = NodeKind.GROUP
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FromSpec | ToSpec | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: FromSpec | ToSpec | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[FromSpec | ToSpec | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Group) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, FromSpec | ToSpec | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: FromSpec | ToSpec | Trivia) -> None:
        if not isinstance(child, FromSpec | ToSpec | Trivia):
            msg = f"Group: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Group.Label)):
            _cn = "Group"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: FromSpec | ToSpec | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, FromSpec | ToSpec | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Group.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: FromSpec | ToSpec | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Group.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_from_spec(self, child: FromSpec) -> None:
        self.children.append((Group.Label.FROM_SPEC, child))

    def extend_from_spec(self, children: typing.Iterable[FromSpec]) -> None:
        self.children.extend((Group.Label.FROM_SPEC, child) for child in children)

    def children_from_spec(self) -> typing.Iterator[FromSpec]:
        return (typing.cast("FromSpec", child) for (label, child) in self.children if label == Group.Label.FROM_SPEC)

    def child_from_spec(self) -> FromSpec:
        children = list(self.children_from_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_spec(self) -> FromSpec | None:
        children = list(self.children_from_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_spec(self, child: ToSpec) -> None:
        self.children.append((Group.Label.TO_SPEC, child))

    def extend_to_spec(self, children: typing.Iterable[ToSpec]) -> None:
        self.children.extend((Group.Label.TO_SPEC, child) for child in children)

    def children_to_spec(self) -> typing.Iterator[ToSpec]:
        return (typing.cast("ToSpec", child) for (label, child) in self.children if label == Group.Label.TO_SPEC)

    def child_to_spec(self) -> ToSpec:
        children = list(self.children_to_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_spec(self) -> ToSpec | None:
        children = list(self.children_to_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Group.Label.FROM_SPEC._fltk_canonical_name = "Group.Label.FROM_SPEC"
Group.Label.TO_SPEC._fltk_canonical_name = "Group.Label.TO_SPEC"


@dataclasses.dataclass
class Nest:
    class Label(enum.Enum):
        FROM_SPEC = enum.auto()
        INDENT = enum.auto()
        TO_SPEC = enum.auto()
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

    kind: typing.Literal[NodeKind.NEST] = NodeKind.NEST
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: FromSpec | Integer | ToSpec | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[FromSpec | Integer | ToSpec | Trivia], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Nest) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: FromSpec | Integer | ToSpec | Trivia) -> None:
        if not isinstance(child, FromSpec | Integer | ToSpec | Trivia):
            msg = f"Nest: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Nest.Label)):
            _cn = "Nest"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: FromSpec | Integer | ToSpec | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Nest.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: FromSpec | Integer | ToSpec | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Nest.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_from_spec(self, child: FromSpec) -> None:
        self.children.append((Nest.Label.FROM_SPEC, child))

    def extend_from_spec(self, children: typing.Iterable[FromSpec]) -> None:
        self.children.extend((Nest.Label.FROM_SPEC, child) for child in children)

    def children_from_spec(self) -> typing.Iterator[FromSpec]:
        return (typing.cast("FromSpec", child) for (label, child) in self.children if label == Nest.Label.FROM_SPEC)

    def child_from_spec(self) -> FromSpec:
        children = list(self.children_from_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_spec(self) -> FromSpec | None:
        children = list(self.children_from_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_indent(self, child: Integer) -> None:
        self.children.append((Nest.Label.INDENT, child))

    def extend_indent(self, children: typing.Iterable[Integer]) -> None:
        self.children.extend((Nest.Label.INDENT, child) for child in children)

    def children_indent(self) -> typing.Iterator[Integer]:
        return (typing.cast("Integer", child) for (label, child) in self.children if label == Nest.Label.INDENT)

    def child_indent(self) -> Integer:
        children = list(self.children_indent())
        if (n := len(children)) != 1:
            msg = f"Expected one indent child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_indent(self) -> Integer | None:
        children = list(self.children_indent())
        if (n := len(children)) > 1:
            msg = f"Expected at most one indent child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_spec(self, child: ToSpec) -> None:
        self.children.append((Nest.Label.TO_SPEC, child))

    def extend_to_spec(self, children: typing.Iterable[ToSpec]) -> None:
        self.children.extend((Nest.Label.TO_SPEC, child) for child in children)

    def children_to_spec(self) -> typing.Iterator[ToSpec]:
        return (typing.cast("ToSpec", child) for (label, child) in self.children if label == Nest.Label.TO_SPEC)

    def child_to_spec(self) -> ToSpec:
        children = list(self.children_to_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_spec(self) -> ToSpec | None:
        children = list(self.children_to_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Nest.Label.FROM_SPEC._fltk_canonical_name = "Nest.Label.FROM_SPEC"
Nest.Label.INDENT._fltk_canonical_name = "Nest.Label.INDENT"
Nest.Label.TO_SPEC._fltk_canonical_name = "Nest.Label.TO_SPEC"


@dataclasses.dataclass
class Join:
    class Label(enum.Enum):
        DOC_LITERAL = enum.auto()
        FROM_SPEC = enum.auto()
        TO_SPEC = enum.auto()
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

    kind: typing.Literal[NodeKind.JOIN] = NodeKind.JOIN
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocLiteral | FromSpec | ToSpec | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: DocLiteral | FromSpec | ToSpec | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[DocLiteral | FromSpec | ToSpec | Trivia], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Join) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocLiteral | FromSpec | ToSpec | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: DocLiteral | FromSpec | ToSpec | Trivia) -> None:
        if not isinstance(child, DocLiteral | FromSpec | ToSpec | Trivia):
            msg = f"Join: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Join.Label)):
            _cn = "Join"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: DocLiteral | FromSpec | ToSpec | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, DocLiteral | FromSpec | ToSpec | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Join.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: DocLiteral | FromSpec | ToSpec | Trivia, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Join.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_doc_literal(self, child: DocLiteral) -> None:
        self.children.append((Join.Label.DOC_LITERAL, child))

    def extend_doc_literal(self, children: typing.Iterable[DocLiteral]) -> None:
        self.children.extend((Join.Label.DOC_LITERAL, child) for child in children)

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]:
        return (typing.cast("DocLiteral", child) for (label, child) in self.children if label == Join.Label.DOC_LITERAL)

    def child_doc_literal(self) -> DocLiteral:
        children = list(self.children_doc_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_literal(self) -> DocLiteral | None:
        children = list(self.children_doc_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_from_spec(self, child: FromSpec) -> None:
        self.children.append((Join.Label.FROM_SPEC, child))

    def extend_from_spec(self, children: typing.Iterable[FromSpec]) -> None:
        self.children.extend((Join.Label.FROM_SPEC, child) for child in children)

    def children_from_spec(self) -> typing.Iterator[FromSpec]:
        return (typing.cast("FromSpec", child) for (label, child) in self.children if label == Join.Label.FROM_SPEC)

    def child_from_spec(self) -> FromSpec:
        children = list(self.children_from_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_spec(self) -> FromSpec | None:
        children = list(self.children_from_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_spec(self, child: ToSpec) -> None:
        self.children.append((Join.Label.TO_SPEC, child))

    def extend_to_spec(self, children: typing.Iterable[ToSpec]) -> None:
        self.children.extend((Join.Label.TO_SPEC, child) for child in children)

    def children_to_spec(self) -> typing.Iterator[ToSpec]:
        return (typing.cast("ToSpec", child) for (label, child) in self.children if label == Join.Label.TO_SPEC)

    def child_to_spec(self) -> ToSpec:
        children = list(self.children_to_spec())
        if (n := len(children)) != 1:
            msg = f"Expected one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_spec(self) -> ToSpec | None:
        children = list(self.children_to_spec())
        if (n := len(children)) > 1:
            msg = f"Expected at most one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Join.Label.DOC_LITERAL._fltk_canonical_name = "Join.Label.DOC_LITERAL"
Join.Label.FROM_SPEC._fltk_canonical_name = "Join.Label.FROM_SPEC"
Join.Label.TO_SPEC._fltk_canonical_name = "Join.Label.TO_SPEC"


@dataclasses.dataclass
class FromSpec:
    class Label(enum.Enum):
        AFTER = enum.auto()
        FROM_ANCHOR = enum.auto()
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

    kind: typing.Literal[NodeKind.FROMSPEC] = NodeKind.FROMSPEC
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Anchor | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: FromSpec) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span) -> None:
        _allowed = FromSpec._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (Anchor, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            FromSpec._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            FromSpec._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = FromSpec._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"FromSpec: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, FromSpec.Label)):
            _cn = "FromSpec"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FromSpec.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FromSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_after(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((FromSpec.Label.AFTER, child))

    def extend_after(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((FromSpec.Label.AFTER, child) for child in children)

    def children_after(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == FromSpec.Label.AFTER
        )

    def child_after(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_after())
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_after())
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_from_anchor(self, child: Anchor) -> None:
        self.children.append((FromSpec.Label.FROM_ANCHOR, child))

    def extend_from_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((FromSpec.Label.FROM_ANCHOR, child) for child in children)

    def children_from_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == FromSpec.Label.FROM_ANCHOR)

    def child_from_anchor(self) -> Anchor:
        children = list(self.children_from_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one from_anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_anchor(self) -> Anchor | None:
        children = list(self.children_from_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


FromSpec.Label.AFTER._fltk_canonical_name = "FromSpec.Label.AFTER"
FromSpec.Label.FROM_ANCHOR._fltk_canonical_name = "FromSpec.Label.FROM_ANCHOR"


@dataclasses.dataclass
class ToSpec:
    class Label(enum.Enum):
        BEFORE = enum.auto()
        TO_ANCHOR = enum.auto()
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

    kind: typing.Literal[NodeKind.TOSPEC] = NodeKind.TOSPEC
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Anchor | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ToSpec) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span) -> None:
        _allowed = ToSpec._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (Anchor, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            ToSpec._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            ToSpec._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = ToSpec._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"ToSpec: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ToSpec.Label)):
            _cn = "ToSpec"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ToSpec.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Anchor | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ToSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_before(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((ToSpec.Label.BEFORE, child))

    def extend_before(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((ToSpec.Label.BEFORE, child) for child in children)

    def children_before(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == ToSpec.Label.BEFORE
        )

    def child_before(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_before())
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_before())
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_anchor(self, child: Anchor) -> None:
        self.children.append((ToSpec.Label.TO_ANCHOR, child))

    def extend_to_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((ToSpec.Label.TO_ANCHOR, child) for child in children)

    def children_to_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == ToSpec.Label.TO_ANCHOR)

    def child_to_anchor(self) -> Anchor:
        children = list(self.children_to_anchor())
        if (n := len(children)) != 1:
            msg = f"Expected one to_anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_anchor(self) -> Anchor | None:
        children = list(self.children_to_anchor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one to_anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


ToSpec.Label.BEFORE._fltk_canonical_name = "ToSpec.Label.BEFORE"
ToSpec.Label.TO_ANCHOR._fltk_canonical_name = "ToSpec.Label.TO_ANCHOR"


@dataclasses.dataclass
class Anchor:
    class Label(enum.Enum):
        LABEL = enum.auto()
        LITERAL = enum.auto()
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
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Literal]] = dataclasses.field(default_factory=list)

    def append(self, child: Identifier | Literal, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Identifier | Literal], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Anchor) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | Literal]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Identifier | Literal) -> None:
        if not isinstance(child, Identifier | Literal):
            msg = f"Anchor: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Anchor.Label)):
            _cn = "Anchor"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Identifier | Literal, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Literal]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Anchor.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Identifier | Literal, label: Label | None = None) -> None:
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

    def append_label(self, child: Identifier) -> None:
        self.children.append((Anchor.Label.LABEL, child))

    def extend_label(self, children: typing.Iterable[Identifier]) -> None:
        self.children.extend((Anchor.Label.LABEL, child) for child in children)

    def children_label(self) -> typing.Iterator[Identifier]:
        return (typing.cast("Identifier", child) for (label, child) in self.children if label == Anchor.Label.LABEL)

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


Anchor.Label.LABEL._fltk_canonical_name = "Anchor.Label.LABEL"
Anchor.Label.LITERAL._fltk_canonical_name = "Anchor.Label.LITERAL"


@dataclasses.dataclass
class After:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
        POSITION_SPEC_STATEMENT = enum.auto()
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

    kind: typing.Literal[NodeKind.AFTER] = NodeKind.AFTER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | PositionSpecStatement | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Anchor | PositionSpecStatement | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Anchor | PositionSpecStatement | Trivia], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: After) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Anchor | PositionSpecStatement | Trivia) -> None:
        if not isinstance(child, Anchor | PositionSpecStatement | Trivia):
            msg = f"After: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, After.Label)):
            _cn = "After"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Anchor | PositionSpecStatement | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"After.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Anchor | PositionSpecStatement | Trivia, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"After.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: Anchor) -> None:
        self.children.append((After.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((After.Label.ANCHOR, child) for child in children)

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == After.Label.ANCHOR)

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

    def append_position_spec_statement(self, child: PositionSpecStatement) -> None:
        self.children.append((After.Label.POSITION_SPEC_STATEMENT, child))

    def extend_position_spec_statement(self, children: typing.Iterable[PositionSpecStatement]) -> None:
        self.children.extend((After.Label.POSITION_SPEC_STATEMENT, child) for child in children)

    def children_position_spec_statement(self) -> typing.Iterator[PositionSpecStatement]:
        return (
            typing.cast("PositionSpecStatement", child)
            for (label, child) in self.children
            if label == After.Label.POSITION_SPEC_STATEMENT
        )

    def child_position_spec_statement(self) -> PositionSpecStatement:
        children = list(self.children_position_spec_statement())
        if (n := len(children)) != 1:
            msg = f"Expected one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_position_spec_statement(self) -> PositionSpecStatement | None:
        children = list(self.children_position_spec_statement())
        if (n := len(children)) > 1:
            msg = f"Expected at most one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


After.Label.ANCHOR._fltk_canonical_name = "After.Label.ANCHOR"
After.Label.POSITION_SPEC_STATEMENT._fltk_canonical_name = "After.Label.POSITION_SPEC_STATEMENT"


@dataclasses.dataclass
class Before:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
        POSITION_SPEC_STATEMENT = enum.auto()
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

    kind: typing.Literal[NodeKind.BEFORE] = NodeKind.BEFORE
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | PositionSpecStatement | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Anchor | PositionSpecStatement | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Anchor | PositionSpecStatement | Trivia], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Before) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Anchor | PositionSpecStatement | Trivia) -> None:
        if not isinstance(child, Anchor | PositionSpecStatement | Trivia):
            msg = f"Before: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Before.Label)):
            _cn = "Before"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Anchor | PositionSpecStatement | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Before.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Anchor | PositionSpecStatement | Trivia, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Before.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: Anchor) -> None:
        self.children.append((Before.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((Before.Label.ANCHOR, child) for child in children)

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == Before.Label.ANCHOR)

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

    def append_position_spec_statement(self, child: PositionSpecStatement) -> None:
        self.children.append((Before.Label.POSITION_SPEC_STATEMENT, child))

    def extend_position_spec_statement(self, children: typing.Iterable[PositionSpecStatement]) -> None:
        self.children.extend((Before.Label.POSITION_SPEC_STATEMENT, child) for child in children)

    def children_position_spec_statement(self) -> typing.Iterator[PositionSpecStatement]:
        return (
            typing.cast("PositionSpecStatement", child)
            for (label, child) in self.children
            if label == Before.Label.POSITION_SPEC_STATEMENT
        )

    def child_position_spec_statement(self) -> PositionSpecStatement:
        children = list(self.children_position_spec_statement())
        if (n := len(children)) != 1:
            msg = f"Expected one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_position_spec_statement(self) -> PositionSpecStatement | None:
        children = list(self.children_position_spec_statement())
        if (n := len(children)) > 1:
            msg = f"Expected at most one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Before.Label.ANCHOR._fltk_canonical_name = "Before.Label.ANCHOR"
Before.Label.POSITION_SPEC_STATEMENT._fltk_canonical_name = "Before.Label.POSITION_SPEC_STATEMENT"


@dataclasses.dataclass
class Omit:
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

    kind: typing.Literal[NodeKind.OMIT] = NodeKind.OMIT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Anchor | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Anchor | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Omit) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Anchor | Trivia) -> None:
        if not isinstance(child, Anchor | Trivia):
            msg = f"Omit: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Omit.Label)):
            _cn = "Omit"
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
            msg = f"Omit.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Anchor | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Omit.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: Anchor) -> None:
        self.children.append((Omit.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((Omit.Label.ANCHOR, child) for child in children)

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == Omit.Label.ANCHOR)

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


Omit.Label.ANCHOR._fltk_canonical_name = "Omit.Label.ANCHOR"


@dataclasses.dataclass
class Render:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
        SPACING = enum.auto()
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

    kind: typing.Literal[NodeKind.RENDER] = NodeKind.RENDER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Spacing | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Anchor | Spacing | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Anchor | Spacing | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Render) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | Spacing | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Anchor | Spacing | Trivia) -> None:
        if not isinstance(child, Anchor | Spacing | Trivia):
            msg = f"Render: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Render.Label)):
            _cn = "Render"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Anchor | Spacing | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | Spacing | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Render.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Anchor | Spacing | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Render.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: Anchor) -> None:
        self.children.append((Render.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((Render.Label.ANCHOR, child) for child in children)

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == Render.Label.ANCHOR)

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

    def append_spacing(self, child: Spacing) -> None:
        self.children.append((Render.Label.SPACING, child))

    def extend_spacing(self, children: typing.Iterable[Spacing]) -> None:
        self.children.extend((Render.Label.SPACING, child) for child in children)

    def children_spacing(self) -> typing.Iterator[Spacing]:
        return (typing.cast("Spacing", child) for (label, child) in self.children if label == Render.Label.SPACING)

    def child_spacing(self) -> Spacing:
        children = list(self.children_spacing())
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> Spacing | None:
        children = list(self.children_spacing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Render.Label.ANCHOR._fltk_canonical_name = "Render.Label.ANCHOR"
Render.Label.SPACING._fltk_canonical_name = "Render.Label.SPACING"


@dataclasses.dataclass
class PositionSpecStatement:
    class Label(enum.Enum):
        PRESERVE_BLANKS = enum.auto()
        SPACING = enum.auto()
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

    kind: typing.Literal[NodeKind.POSITIONSPECSTATEMENT] = NodeKind.POSITIONSPECSTATEMENT
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, PreserveBlanks | Spacing | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: PreserveBlanks | Spacing | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[PreserveBlanks | Spacing | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: PositionSpecStatement) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, PreserveBlanks | Spacing | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: PreserveBlanks | Spacing | Trivia) -> None:
        if not isinstance(child, PreserveBlanks | Spacing | Trivia):
            msg = f"PositionSpecStatement: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, PositionSpecStatement.Label)):
            _cn = "PositionSpecStatement"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: PreserveBlanks | Spacing | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, PreserveBlanks | Spacing | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PositionSpecStatement.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: PreserveBlanks | Spacing | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PositionSpecStatement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_preserve_blanks(self, child: PreserveBlanks) -> None:
        self.children.append((PositionSpecStatement.Label.PRESERVE_BLANKS, child))

    def extend_preserve_blanks(self, children: typing.Iterable[PreserveBlanks]) -> None:
        self.children.extend((PositionSpecStatement.Label.PRESERVE_BLANKS, child) for child in children)

    def children_preserve_blanks(self) -> typing.Iterator[PreserveBlanks]:
        return (
            typing.cast("PreserveBlanks", child)
            for (label, child) in self.children
            if label == PositionSpecStatement.Label.PRESERVE_BLANKS
        )

    def child_preserve_blanks(self) -> PreserveBlanks:
        children = list(self.children_preserve_blanks())
        if (n := len(children)) != 1:
            msg = f"Expected one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_preserve_blanks(self) -> PreserveBlanks | None:
        children = list(self.children_preserve_blanks())
        if (n := len(children)) > 1:
            msg = f"Expected at most one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_spacing(self, child: Spacing) -> None:
        self.children.append((PositionSpecStatement.Label.SPACING, child))

    def extend_spacing(self, children: typing.Iterable[Spacing]) -> None:
        self.children.extend((PositionSpecStatement.Label.SPACING, child) for child in children)

    def children_spacing(self) -> typing.Iterator[Spacing]:
        return (
            typing.cast("Spacing", child)
            for (label, child) in self.children
            if label == PositionSpecStatement.Label.SPACING
        )

    def child_spacing(self) -> Spacing:
        children = list(self.children_spacing())
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> Spacing | None:
        children = list(self.children_spacing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


PositionSpecStatement.Label.PRESERVE_BLANKS._fltk_canonical_name = "PositionSpecStatement.Label.PRESERVE_BLANKS"
PositionSpecStatement.Label.SPACING._fltk_canonical_name = "PositionSpecStatement.Label.SPACING"


@dataclasses.dataclass
class Spacing:
    class Label(enum.Enum):
        BLANK = enum.auto()
        BSP = enum.auto()
        HARD = enum.auto()
        NBSP = enum.auto()
        NIL = enum.auto()
        NUM_BLANKS = enum.auto()
        SOFT = enum.auto()
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

    kind: typing.Literal[NodeKind.SPACING] = NodeKind.SPACING
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Integer | Trivia | fltk.fegen.pyrt.span.Span]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Integer | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Integer | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Spacing) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Integer | Trivia | fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: Integer | Trivia | fltk.fegen.pyrt.span.Span) -> None:
        _allowed = Spacing._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (Integer, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            Spacing._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Spacing._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Spacing._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Spacing: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Spacing.Label)):
            _cn = "Spacing"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: Integer | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, Integer | Trivia | fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Spacing.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Integer | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Spacing.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_blank(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Spacing.Label.BLANK, child))

    def extend_blank(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Spacing.Label.BLANK, child) for child in children)

    def children_blank(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Spacing.Label.BLANK
        )

    def child_blank(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_blank())
        if (n := len(children)) != 1:
            msg = f"Expected one blank child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_blank(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_blank())
        if (n := len(children)) > 1:
            msg = f"Expected at most one blank child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_bsp(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Spacing.Label.BSP, child))

    def extend_bsp(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Spacing.Label.BSP, child) for child in children)

    def children_bsp(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Spacing.Label.BSP
        )

    def child_bsp(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_bsp())
        if (n := len(children)) != 1:
            msg = f"Expected one bsp child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_bsp(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_bsp())
        if (n := len(children)) > 1:
            msg = f"Expected at most one bsp child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_hard(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Spacing.Label.HARD, child))

    def extend_hard(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Spacing.Label.HARD, child) for child in children)

    def children_hard(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Spacing.Label.HARD
        )

    def child_hard(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_hard())
        if (n := len(children)) != 1:
            msg = f"Expected one hard child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_hard(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_hard())
        if (n := len(children)) > 1:
            msg = f"Expected at most one hard child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nbsp(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Spacing.Label.NBSP, child))

    def extend_nbsp(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Spacing.Label.NBSP, child) for child in children)

    def children_nbsp(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Spacing.Label.NBSP
        )

    def child_nbsp(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_nbsp())
        if (n := len(children)) != 1:
            msg = f"Expected one nbsp child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nbsp(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_nbsp())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nbsp child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nil(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Spacing.Label.NIL, child))

    def extend_nil(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Spacing.Label.NIL, child) for child in children)

    def children_nil(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Spacing.Label.NIL
        )

    def child_nil(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_nil())
        if (n := len(children)) != 1:
            msg = f"Expected one nil child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nil(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_nil())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nil child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_num_blanks(self, child: Integer) -> None:
        self.children.append((Spacing.Label.NUM_BLANKS, child))

    def extend_num_blanks(self, children: typing.Iterable[Integer]) -> None:
        self.children.extend((Spacing.Label.NUM_BLANKS, child) for child in children)

    def children_num_blanks(self) -> typing.Iterator[Integer]:
        return (typing.cast("Integer", child) for (label, child) in self.children if label == Spacing.Label.NUM_BLANKS)

    def child_num_blanks(self) -> Integer:
        children = list(self.children_num_blanks())
        if (n := len(children)) != 1:
            msg = f"Expected one num_blanks child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_num_blanks(self) -> Integer | None:
        children = list(self.children_num_blanks())
        if (n := len(children)) > 1:
            msg = f"Expected at most one num_blanks child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_soft(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Spacing.Label.SOFT, child))

    def extend_soft(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Spacing.Label.SOFT, child) for child in children)

    def children_soft(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == Spacing.Label.SOFT
        )

    def child_soft(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_soft())
        if (n := len(children)) != 1:
            msg = f"Expected one soft child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_soft(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_soft())
        if (n := len(children)) > 1:
            msg = f"Expected at most one soft child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Spacing.Label.BLANK._fltk_canonical_name = "Spacing.Label.BLANK"
Spacing.Label.BSP._fltk_canonical_name = "Spacing.Label.BSP"
Spacing.Label.HARD._fltk_canonical_name = "Spacing.Label.HARD"
Spacing.Label.NBSP._fltk_canonical_name = "Spacing.Label.NBSP"
Spacing.Label.NIL._fltk_canonical_name = "Spacing.Label.NIL"
Spacing.Label.NUM_BLANKS._fltk_canonical_name = "Spacing.Label.NUM_BLANKS"
Spacing.Label.SOFT._fltk_canonical_name = "Spacing.Label.SOFT"


@dataclasses.dataclass
class DocLiteral:
    class Label(enum.Enum):
        COMPOUND_LITERAL = enum.auto()
        CONCAT_LITERAL = enum.auto()
        JOIN_LITERAL = enum.auto()
        SPACING = enum.auto()
        TEXT_LITERAL = enum.auto()
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

    kind: typing.Literal[NodeKind.DOCLITERAL] = NodeKind.DOCLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self, child: CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral, label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: DocLiteral) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral
    ) -> None:
        if not isinstance(child, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral):
            msg = f"DocLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, DocLiteral.Label)):
            _cn = "DocLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral,
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
    ) -> tuple[Label | None, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DocLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral,
        label: Label | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DocLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_compound_literal(self, child: CompoundLiteral) -> None:
        self.children.append((DocLiteral.Label.COMPOUND_LITERAL, child))

    def extend_compound_literal(self, children: typing.Iterable[CompoundLiteral]) -> None:
        self.children.extend((DocLiteral.Label.COMPOUND_LITERAL, child) for child in children)

    def children_compound_literal(self) -> typing.Iterator[CompoundLiteral]:
        return (
            typing.cast("CompoundLiteral", child)
            for (label, child) in self.children
            if label == DocLiteral.Label.COMPOUND_LITERAL
        )

    def child_compound_literal(self) -> CompoundLiteral:
        children = list(self.children_compound_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one compound_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_compound_literal(self) -> CompoundLiteral | None:
        children = list(self.children_compound_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one compound_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_concat_literal(self, child: ConcatLiteral) -> None:
        self.children.append((DocLiteral.Label.CONCAT_LITERAL, child))

    def extend_concat_literal(self, children: typing.Iterable[ConcatLiteral]) -> None:
        self.children.extend((DocLiteral.Label.CONCAT_LITERAL, child) for child in children)

    def children_concat_literal(self) -> typing.Iterator[ConcatLiteral]:
        return (
            typing.cast("ConcatLiteral", child)
            for (label, child) in self.children
            if label == DocLiteral.Label.CONCAT_LITERAL
        )

    def child_concat_literal(self) -> ConcatLiteral:
        children = list(self.children_concat_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one concat_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_concat_literal(self) -> ConcatLiteral | None:
        children = list(self.children_concat_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one concat_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_join_literal(self, child: JoinLiteral) -> None:
        self.children.append((DocLiteral.Label.JOIN_LITERAL, child))

    def extend_join_literal(self, children: typing.Iterable[JoinLiteral]) -> None:
        self.children.extend((DocLiteral.Label.JOIN_LITERAL, child) for child in children)

    def children_join_literal(self) -> typing.Iterator[JoinLiteral]:
        return (
            typing.cast("JoinLiteral", child)
            for (label, child) in self.children
            if label == DocLiteral.Label.JOIN_LITERAL
        )

    def child_join_literal(self) -> JoinLiteral:
        children = list(self.children_join_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one join_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_join_literal(self) -> JoinLiteral | None:
        children = list(self.children_join_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one join_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_spacing(self, child: Spacing) -> None:
        self.children.append((DocLiteral.Label.SPACING, child))

    def extend_spacing(self, children: typing.Iterable[Spacing]) -> None:
        self.children.extend((DocLiteral.Label.SPACING, child) for child in children)

    def children_spacing(self) -> typing.Iterator[Spacing]:
        return (typing.cast("Spacing", child) for (label, child) in self.children if label == DocLiteral.Label.SPACING)

    def child_spacing(self) -> Spacing:
        children = list(self.children_spacing())
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> Spacing | None:
        children = list(self.children_spacing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_text_literal(self, child: TextLiteral) -> None:
        self.children.append((DocLiteral.Label.TEXT_LITERAL, child))

    def extend_text_literal(self, children: typing.Iterable[TextLiteral]) -> None:
        self.children.extend((DocLiteral.Label.TEXT_LITERAL, child) for child in children)

    def children_text_literal(self) -> typing.Iterator[TextLiteral]:
        return (
            typing.cast("TextLiteral", child)
            for (label, child) in self.children
            if label == DocLiteral.Label.TEXT_LITERAL
        )

    def child_text_literal(self) -> TextLiteral:
        children = list(self.children_text_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one text_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_text_literal(self) -> TextLiteral | None:
        children = list(self.children_text_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one text_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


DocLiteral.Label.COMPOUND_LITERAL._fltk_canonical_name = "DocLiteral.Label.COMPOUND_LITERAL"
DocLiteral.Label.CONCAT_LITERAL._fltk_canonical_name = "DocLiteral.Label.CONCAT_LITERAL"
DocLiteral.Label.JOIN_LITERAL._fltk_canonical_name = "DocLiteral.Label.JOIN_LITERAL"
DocLiteral.Label.SPACING._fltk_canonical_name = "DocLiteral.Label.SPACING"
DocLiteral.Label.TEXT_LITERAL._fltk_canonical_name = "DocLiteral.Label.TEXT_LITERAL"


@dataclasses.dataclass
class TextLiteral:
    class Label(enum.Enum):
        TEXT = enum.auto()
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

    kind: typing.Literal[NodeKind.TEXTLITERAL] = NodeKind.TEXTLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Literal | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Literal | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Literal | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: TextLiteral) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Literal | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Literal | Trivia) -> None:
        if not isinstance(child, Literal | Trivia):
            msg = f"TextLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, TextLiteral.Label)):
            _cn = "TextLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Literal | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Literal | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TextLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Literal | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TextLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_text(self, child: Literal) -> None:
        self.children.append((TextLiteral.Label.TEXT, child))

    def extend_text(self, children: typing.Iterable[Literal]) -> None:
        self.children.extend((TextLiteral.Label.TEXT, child) for child in children)

    def children_text(self) -> typing.Iterator[Literal]:
        return (typing.cast("Literal", child) for (label, child) in self.children if label == TextLiteral.Label.TEXT)

    def child_text(self) -> Literal:
        children = list(self.children_text())
        if (n := len(children)) != 1:
            msg = f"Expected one text child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_text(self) -> Literal | None:
        children = list(self.children_text())
        if (n := len(children)) > 1:
            msg = f"Expected at most one text child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


TextLiteral.Label.TEXT._fltk_canonical_name = "TextLiteral.Label.TEXT"


@dataclasses.dataclass
class ConcatLiteral:
    class Label(enum.Enum):
        DOC_LIST_LITERAL = enum.auto()
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

    kind: typing.Literal[NodeKind.CONCATLITERAL] = NodeKind.CONCATLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocListLiteral | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: DocListLiteral | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[DocListLiteral | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ConcatLiteral) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocListLiteral | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: DocListLiteral | Trivia) -> None:
        if not isinstance(child, DocListLiteral | Trivia):
            msg = f"ConcatLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ConcatLiteral.Label)):
            _cn = "ConcatLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: DocListLiteral | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, DocListLiteral | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ConcatLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: DocListLiteral | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ConcatLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_doc_list_literal(self, child: DocListLiteral) -> None:
        self.children.append((ConcatLiteral.Label.DOC_LIST_LITERAL, child))

    def extend_doc_list_literal(self, children: typing.Iterable[DocListLiteral]) -> None:
        self.children.extend((ConcatLiteral.Label.DOC_LIST_LITERAL, child) for child in children)

    def children_doc_list_literal(self) -> typing.Iterator[DocListLiteral]:
        return (
            typing.cast("DocListLiteral", child)
            for (label, child) in self.children
            if label == ConcatLiteral.Label.DOC_LIST_LITERAL
        )

    def child_doc_list_literal(self) -> DocListLiteral:
        children = list(self.children_doc_list_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_list_literal(self) -> DocListLiteral | None:
        children = list(self.children_doc_list_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


ConcatLiteral.Label.DOC_LIST_LITERAL._fltk_canonical_name = "ConcatLiteral.Label.DOC_LIST_LITERAL"


@dataclasses.dataclass
class JoinLiteral:
    class Label(enum.Enum):
        DOC_LIST_LITERAL = enum.auto()
        SEPARATOR = enum.auto()
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

    kind: typing.Literal[NodeKind.JOINLITERAL] = NodeKind.JOINLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocListLiteral | DocLiteral | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: DocListLiteral | DocLiteral | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[DocListLiteral | DocLiteral | Trivia], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: JoinLiteral) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocListLiteral | DocLiteral | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: DocListLiteral | DocLiteral | Trivia) -> None:
        if not isinstance(child, DocListLiteral | DocLiteral | Trivia):
            msg = f"JoinLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, JoinLiteral.Label)):
            _cn = "JoinLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: DocListLiteral | DocLiteral | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, DocListLiteral | DocLiteral | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"JoinLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: DocListLiteral | DocLiteral | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"JoinLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_doc_list_literal(self, child: DocListLiteral) -> None:
        self.children.append((JoinLiteral.Label.DOC_LIST_LITERAL, child))

    def extend_doc_list_literal(self, children: typing.Iterable[DocListLiteral]) -> None:
        self.children.extend((JoinLiteral.Label.DOC_LIST_LITERAL, child) for child in children)

    def children_doc_list_literal(self) -> typing.Iterator[DocListLiteral]:
        return (
            typing.cast("DocListLiteral", child)
            for (label, child) in self.children
            if label == JoinLiteral.Label.DOC_LIST_LITERAL
        )

    def child_doc_list_literal(self) -> DocListLiteral:
        children = list(self.children_doc_list_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_list_literal(self) -> DocListLiteral | None:
        children = list(self.children_doc_list_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_separator(self, child: DocLiteral) -> None:
        self.children.append((JoinLiteral.Label.SEPARATOR, child))

    def extend_separator(self, children: typing.Iterable[DocLiteral]) -> None:
        self.children.extend((JoinLiteral.Label.SEPARATOR, child) for child in children)

    def children_separator(self) -> typing.Iterator[DocLiteral]:
        return (
            typing.cast("DocLiteral", child) for (label, child) in self.children if label == JoinLiteral.Label.SEPARATOR
        )

    def child_separator(self) -> DocLiteral:
        children = list(self.children_separator())
        if (n := len(children)) != 1:
            msg = f"Expected one separator child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_separator(self) -> DocLiteral | None:
        children = list(self.children_separator())
        if (n := len(children)) > 1:
            msg = f"Expected at most one separator child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


JoinLiteral.Label.DOC_LIST_LITERAL._fltk_canonical_name = "JoinLiteral.Label.DOC_LIST_LITERAL"
JoinLiteral.Label.SEPARATOR._fltk_canonical_name = "JoinLiteral.Label.SEPARATOR"


@dataclasses.dataclass
class DocListLiteral:
    class Label(enum.Enum):
        DOC_LITERAL = enum.auto()
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

    kind: typing.Literal[NodeKind.DOCLISTLITERAL] = NodeKind.DOCLISTLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocLiteral | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: DocLiteral | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[DocLiteral | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: DocListLiteral) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocLiteral | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: DocLiteral | Trivia) -> None:
        if not isinstance(child, DocLiteral | Trivia):
            msg = f"DocListLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, DocListLiteral.Label)):
            _cn = "DocListLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: DocLiteral | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, DocLiteral | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DocListLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: DocLiteral | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DocListLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_doc_literal(self, child: DocLiteral) -> None:
        self.children.append((DocListLiteral.Label.DOC_LITERAL, child))

    def extend_doc_literal(self, children: typing.Iterable[DocLiteral]) -> None:
        self.children.extend((DocListLiteral.Label.DOC_LITERAL, child) for child in children)

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]:
        return (
            typing.cast("DocLiteral", child)
            for (label, child) in self.children
            if label == DocListLiteral.Label.DOC_LITERAL
        )

    def child_doc_literal(self) -> DocLiteral:
        children = list(self.children_doc_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_literal(self) -> DocLiteral | None:
        children = list(self.children_doc_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


DocListLiteral.Label.DOC_LITERAL._fltk_canonical_name = "DocListLiteral.Label.DOC_LITERAL"


@dataclasses.dataclass
class CompoundLiteral:
    class Label(enum.Enum):
        DOC_LITERAL = enum.auto()
        GROUP = enum.auto()
        NEST = enum.auto()
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

    kind: typing.Literal[NodeKind.COMPOUNDLITERAL] = NodeKind.COMPOUNDLITERAL
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocLiteral | Trivia | fltk.fegen.pyrt.span.Span]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: DocLiteral | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[DocLiteral | Trivia | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: CompoundLiteral) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocLiteral | Trivia | fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: DocLiteral | Trivia | fltk.fegen.pyrt.span.Span) -> None:
        _allowed = CompoundLiteral._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (DocLiteral, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            CompoundLiteral._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            CompoundLiteral._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = CompoundLiteral._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"CompoundLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, CompoundLiteral.Label)):
            _cn = "CompoundLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: DocLiteral | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, DocLiteral | Trivia | fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CompoundLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: DocLiteral | Trivia | fltk.fegen.pyrt.span.Span, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CompoundLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_doc_literal(self, child: DocLiteral) -> None:
        self.children.append((CompoundLiteral.Label.DOC_LITERAL, child))

    def extend_doc_literal(self, children: typing.Iterable[DocLiteral]) -> None:
        self.children.extend((CompoundLiteral.Label.DOC_LITERAL, child) for child in children)

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]:
        return (
            typing.cast("DocLiteral", child)
            for (label, child) in self.children
            if label == CompoundLiteral.Label.DOC_LITERAL
        )

    def child_doc_literal(self) -> DocLiteral:
        children = list(self.children_doc_literal())
        if (n := len(children)) != 1:
            msg = f"Expected one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_literal(self) -> DocLiteral | None:
        children = list(self.children_doc_literal())
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((CompoundLiteral.Label.GROUP, child))

    def extend_group(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((CompoundLiteral.Label.GROUP, child) for child in children)

    def children_group(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == CompoundLiteral.Label.GROUP
        )

    def child_group(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_group())
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_group())
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((CompoundLiteral.Label.NEST, child))

    def extend_nest(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((CompoundLiteral.Label.NEST, child) for child in children)

    def children_nest(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (
            typing.cast("fltk.fegen.pyrt.span.Span", child)
            for (label, child) in self.children
            if label == CompoundLiteral.Label.NEST
        )

    def child_nest(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_nest())
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_nest())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nest child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


CompoundLiteral.Label.DOC_LITERAL._fltk_canonical_name = "CompoundLiteral.Label.DOC_LITERAL"
CompoundLiteral.Label.GROUP._fltk_canonical_name = "CompoundLiteral.Label.GROUP"
CompoundLiteral.Label.NEST._fltk_canonical_name = "CompoundLiteral.Label.NEST"


@dataclasses.dataclass
class TriviaPreserve:
    class Label(enum.Enum):
        TRIVIA_NODE_LIST = enum.auto()
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

    kind: typing.Literal[NodeKind.TRIVIAPRESERVE] = NodeKind.TRIVIAPRESERVE
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Trivia | TriviaNodeList]] = dataclasses.field(default_factory=list)

    def append(self, child: Trivia | TriviaNodeList, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Trivia | TriviaNodeList], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: TriviaPreserve) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Trivia | TriviaNodeList]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Trivia | TriviaNodeList) -> None:
        if not isinstance(child, Trivia | TriviaNodeList):
            msg = f"TriviaPreserve: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, TriviaPreserve.Label)):
            _cn = "TriviaPreserve"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Trivia | TriviaNodeList, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Trivia | TriviaNodeList]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TriviaPreserve.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Trivia | TriviaNodeList, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TriviaPreserve.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_trivia_node_list(self, child: TriviaNodeList) -> None:
        self.children.append((TriviaPreserve.Label.TRIVIA_NODE_LIST, child))

    def extend_trivia_node_list(self, children: typing.Iterable[TriviaNodeList]) -> None:
        self.children.extend((TriviaPreserve.Label.TRIVIA_NODE_LIST, child) for child in children)

    def children_trivia_node_list(self) -> typing.Iterator[TriviaNodeList]:
        return (
            typing.cast("TriviaNodeList", child)
            for (label, child) in self.children
            if label == TriviaPreserve.Label.TRIVIA_NODE_LIST
        )

    def child_trivia_node_list(self) -> TriviaNodeList:
        children = list(self.children_trivia_node_list())
        if (n := len(children)) != 1:
            msg = f"Expected one trivia_node_list child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_trivia_node_list(self) -> TriviaNodeList | None:
        children = list(self.children_trivia_node_list())
        if (n := len(children)) > 1:
            msg = f"Expected at most one trivia_node_list child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


TriviaPreserve.Label.TRIVIA_NODE_LIST._fltk_canonical_name = "TriviaPreserve.Label.TRIVIA_NODE_LIST"


@dataclasses.dataclass
class TriviaNodeList:
    class Label(enum.Enum):
        IDENTIFIER = enum.auto()
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

    kind: typing.Literal[NodeKind.TRIVIANODELIST] = NodeKind.TRIVIANODELIST
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Identifier | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Identifier | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: TriviaNodeList) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Identifier | Trivia) -> None:
        if not isinstance(child, Identifier | Trivia):
            msg = f"TriviaNodeList: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, TriviaNodeList.Label)):
            _cn = "TriviaNodeList"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Identifier | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TriviaNodeList.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Identifier | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TriviaNodeList.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_identifier(self, child: Identifier) -> None:
        self.children.append((TriviaNodeList.Label.IDENTIFIER, child))

    def extend_identifier(self, children: typing.Iterable[Identifier]) -> None:
        self.children.extend((TriviaNodeList.Label.IDENTIFIER, child) for child in children)

    def children_identifier(self) -> typing.Iterator[Identifier]:
        return (
            typing.cast("Identifier", child)
            for (label, child) in self.children
            if label == TriviaNodeList.Label.IDENTIFIER
        )

    def child_identifier(self) -> Identifier:
        children = list(self.children_identifier())
        if (n := len(children)) != 1:
            msg = f"Expected one identifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_identifier(self) -> Identifier | None:
        children = list(self.children_identifier())
        if (n := len(children)) > 1:
            msg = f"Expected at most one identifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


TriviaNodeList.Label.IDENTIFIER._fltk_canonical_name = "TriviaNodeList.Label.IDENTIFIER"


@dataclasses.dataclass
class PreserveBlanks:
    class Label(enum.Enum):
        COUNT = enum.auto()
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

    kind: typing.Literal[NodeKind.PRESERVEBLANKS] = NodeKind.PRESERVEBLANKS
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Integer | Trivia]] = dataclasses.field(default_factory=list)

    def append(self, child: Integer | Trivia, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Integer | Trivia], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: PreserveBlanks) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Integer | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Integer | Trivia) -> None:
        if not isinstance(child, Integer | Trivia):
            msg = f"PreserveBlanks: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, PreserveBlanks.Label)):
            _cn = "PreserveBlanks"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Integer | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Integer | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PreserveBlanks.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Integer | Trivia, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PreserveBlanks.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_count(self, child: Integer) -> None:
        self.children.append((PreserveBlanks.Label.COUNT, child))

    def extend_count(self, children: typing.Iterable[Integer]) -> None:
        self.children.extend((PreserveBlanks.Label.COUNT, child) for child in children)

    def children_count(self) -> typing.Iterator[Integer]:
        return (
            typing.cast("Integer", child) for (label, child) in self.children if label == PreserveBlanks.Label.COUNT
        )

    def child_count(self) -> Integer:
        children = list(self.children_count())
        if (n := len(children)) != 1:
            msg = f"Expected one count child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_count(self) -> Integer | None:
        children = list(self.children_count())
        if (n := len(children)) > 1:
            msg = f"Expected at most one count child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


PreserveBlanks.Label.COUNT._fltk_canonical_name = "PreserveBlanks.Label.COUNT"


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
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]] = dataclasses.field(default_factory=list)

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Identifier) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span.Span) -> None:
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

    def insert(self, index: int, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Identifier.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
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

    def append_name(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Identifier.Label.NAME, child))

    def extend_name(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Identifier.Label.NAME, child) for child in children)

    def children_name(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (child for (label, child) in self.children if label == Identifier.Label.NAME)

    def child_name(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_name())
        if (n := len(children)) != 1:
            msg = f"Expected one name child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_name(self) -> fltk.fegen.pyrt.span.Span | None:
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
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]] = dataclasses.field(default_factory=list)

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Literal) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span.Span) -> None:
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

    def insert(self, index: int, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Literal.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
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

    def append_value(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Literal.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Literal.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (child for (label, child) in self.children if label == Literal.Label.VALUE)

    def child_value(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Literal.Label.VALUE._fltk_canonical_name = "Literal.Label.VALUE"


@dataclasses.dataclass
class Integer:
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

    kind: typing.Literal[NodeKind.INTEGER] = NodeKind.INTEGER
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]] = dataclasses.field(default_factory=list)

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Integer) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span.Span) -> None:
        _allowed = Integer._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Integer._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Integer._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Integer._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Integer: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Integer.Label)):
            _cn = "Integer"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Integer.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Integer.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((Integer.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((Integer.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (child for (label, child) in self.children if label == Integer.Label.VALUE)

    def child_value(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_value())
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_value())
        if (n := len(children)) > 1:
            msg = f"Expected at most one value child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


Integer.Label.VALUE._fltk_canonical_name = "Integer.Label.VALUE"


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
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, LineComment | fltk.fegen.pyrt.span.Span]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: LineComment | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[LineComment | fltk.fegen.pyrt.span.Span], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Trivia) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: LineComment | fltk.fegen.pyrt.span.Span) -> None:
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

    def insert(self, index: int, child: LineComment | fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, LineComment | fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Trivia.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: LineComment | fltk.fegen.pyrt.span.Span, label: Label | None = None
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
    span: fltk.fegen.pyrt.terminalsrc.Span | fltk._native.Span = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, fltk.fegen.pyrt.span.Span]] = dataclasses.field(default_factory=list)

    def append(self, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: LineComment) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span.Span) -> None:
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

    def insert(self, index: int, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span.Span]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LineComment.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: fltk.fegen.pyrt.span.Span, label: Label | None = None) -> None:
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

    def append_content(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((LineComment.Label.CONTENT, child))

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((LineComment.Label.CONTENT, child) for child in children)

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (child for (label, child) in self.children if label == LineComment.Label.CONTENT)

    def child_content(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_content())
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_content())
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_newline(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((LineComment.Label.NEWLINE, child))

    def extend_newline(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((LineComment.Label.NEWLINE, child) for child in children)

    def children_newline(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (child for (label, child) in self.children if label == LineComment.Label.NEWLINE)

    def child_newline(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_newline())
        if (n := len(children)) != 1:
            msg = f"Expected one newline child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_newline(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_newline())
        if (n := len(children)) > 1:
            msg = f"Expected at most one newline child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_prefix(self, child: fltk.fegen.pyrt.span.Span) -> None:
        self.children.append((LineComment.Label.PREFIX, child))

    def extend_prefix(self, children: typing.Iterable[fltk.fegen.pyrt.span.Span]) -> None:
        self.children.extend((LineComment.Label.PREFIX, child) for child in children)

    def children_prefix(self) -> typing.Iterator[fltk.fegen.pyrt.span.Span]:
        return (child for (label, child) in self.children if label == LineComment.Label.PREFIX)

    def child_prefix(self) -> fltk.fegen.pyrt.span.Span:
        children = list(self.children_prefix())
        if (n := len(children)) != 1:
            msg = f"Expected one prefix child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_prefix(self) -> fltk.fegen.pyrt.span.Span | None:
        children = list(self.children_prefix())
        if (n := len(children)) > 1:
            msg = f"Expected at most one prefix child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


LineComment.Label.CONTENT._fltk_canonical_name = "LineComment.Label.CONTENT"
LineComment.Label.NEWLINE._fltk_canonical_name = "LineComment.Label.NEWLINE"
LineComment.Label.PREFIX._fltk_canonical_name = "LineComment.Label.PREFIX"
