from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import typing

import fltk.fegen.pyrt.terminalsrc
from fltk.unparse.unparsefmt_cst_protocol import NodeKind

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol
    import fltk.unparse.unparsefmt_cst_protocol as _cstp


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

    def extend_children(self, other: _cstp.Formatter) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Statement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Statement | _cstp.Trivia) -> None:
        if not isinstance(child, Statement | Trivia):
            msg = f"Formatter: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Formatter.Label)):
            _cn = "Formatter"
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
            msg = f"Formatter.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Formatter.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_statement(self, child: _cstp.Statement) -> None:
        entry: typing.Any = (Formatter.Label.STATEMENT, child)
        self.children.append(entry)

    def extend_statement(self, children: typing.Iterable[_cstp.Statement]) -> None:
        entries: typing.Any = ((Formatter.Label.STATEMENT, child) for child in children)
        self.children.extend(entries)

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

    def statement(self) -> list[Statement]:
        return list(self.children_statement())


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
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
        child: _cstp.After
        | _cstp.Before
        | _cstp.Default
        | _cstp.Group
        | _cstp.Join
        | _cstp.Nest
        | _cstp.Omit
        | _cstp.PreserveBlanks
        | _cstp.Render
        | _cstp.RuleConfig
        | _cstp.TriviaPreserve,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[
            _cstp.After
            | _cstp.Before
            | _cstp.Default
            | _cstp.Group
            | _cstp.Join
            | _cstp.Nest
            | _cstp.Omit
            | _cstp.PreserveBlanks
            | _cstp.Render
            | _cstp.RuleConfig
            | _cstp.TriviaPreserve
        ],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Statement) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

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
        child: _cstp.After
        | _cstp.Before
        | _cstp.Default
        | _cstp.Group
        | _cstp.Join
        | _cstp.Nest
        | _cstp.Omit
        | _cstp.PreserveBlanks
        | _cstp.Render
        | _cstp.RuleConfig
        | _cstp.TriviaPreserve,
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
        child: _cstp.After
        | _cstp.Before
        | _cstp.Default
        | _cstp.Group
        | _cstp.Join
        | _cstp.Nest
        | _cstp.Omit
        | _cstp.PreserveBlanks
        | _cstp.Render
        | _cstp.RuleConfig
        | _cstp.TriviaPreserve,
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
        child: _cstp.After
        | _cstp.Before
        | _cstp.Default
        | _cstp.Group
        | _cstp.Join
        | _cstp.Nest
        | _cstp.Omit
        | _cstp.PreserveBlanks
        | _cstp.Render
        | _cstp.RuleConfig
        | _cstp.TriviaPreserve,
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

    def append_after(self, child: _cstp.After) -> None:
        entry: typing.Any = (Statement.Label.AFTER, child)
        self.children.append(entry)

    def extend_after(self, children: typing.Iterable[_cstp.After]) -> None:
        entries: typing.Any = ((Statement.Label.AFTER, child) for child in children)
        self.children.extend(entries)

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

    def append_before(self, child: _cstp.Before) -> None:
        entry: typing.Any = (Statement.Label.BEFORE, child)
        self.children.append(entry)

    def extend_before(self, children: typing.Iterable[_cstp.Before]) -> None:
        entries: typing.Any = ((Statement.Label.BEFORE, child) for child in children)
        self.children.extend(entries)

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

    def append_default(self, child: _cstp.Default) -> None:
        entry: typing.Any = (Statement.Label.DEFAULT, child)
        self.children.append(entry)

    def extend_default(self, children: typing.Iterable[_cstp.Default]) -> None:
        entries: typing.Any = ((Statement.Label.DEFAULT, child) for child in children)
        self.children.extend(entries)

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

    def append_group(self, child: _cstp.Group) -> None:
        entry: typing.Any = (Statement.Label.GROUP, child)
        self.children.append(entry)

    def extend_group(self, children: typing.Iterable[_cstp.Group]) -> None:
        entries: typing.Any = ((Statement.Label.GROUP, child) for child in children)
        self.children.extend(entries)

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

    def append_join(self, child: _cstp.Join) -> None:
        entry: typing.Any = (Statement.Label.JOIN, child)
        self.children.append(entry)

    def extend_join(self, children: typing.Iterable[_cstp.Join]) -> None:
        entries: typing.Any = ((Statement.Label.JOIN, child) for child in children)
        self.children.extend(entries)

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

    def append_nest(self, child: _cstp.Nest) -> None:
        entry: typing.Any = (Statement.Label.NEST, child)
        self.children.append(entry)

    def extend_nest(self, children: typing.Iterable[_cstp.Nest]) -> None:
        entries: typing.Any = ((Statement.Label.NEST, child) for child in children)
        self.children.extend(entries)

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

    def append_omit(self, child: _cstp.Omit) -> None:
        entry: typing.Any = (Statement.Label.OMIT, child)
        self.children.append(entry)

    def extend_omit(self, children: typing.Iterable[_cstp.Omit]) -> None:
        entries: typing.Any = ((Statement.Label.OMIT, child) for child in children)
        self.children.extend(entries)

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

    def append_preserve_blanks(self, child: _cstp.PreserveBlanks) -> None:
        entry: typing.Any = (Statement.Label.PRESERVE_BLANKS, child)
        self.children.append(entry)

    def extend_preserve_blanks(self, children: typing.Iterable[_cstp.PreserveBlanks]) -> None:
        entries: typing.Any = ((Statement.Label.PRESERVE_BLANKS, child) for child in children)
        self.children.extend(entries)

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

    def append_render(self, child: _cstp.Render) -> None:
        entry: typing.Any = (Statement.Label.RENDER, child)
        self.children.append(entry)

    def extend_render(self, children: typing.Iterable[_cstp.Render]) -> None:
        entries: typing.Any = ((Statement.Label.RENDER, child) for child in children)
        self.children.extend(entries)

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

    def append_trivia_preserve(self, child: _cstp.TriviaPreserve) -> None:
        entry: typing.Any = (Statement.Label.TRIVIA_PRESERVE, child)
        self.children.append(entry)

    def extend_trivia_preserve(self, children: typing.Iterable[_cstp.TriviaPreserve]) -> None:
        entries: typing.Any = ((Statement.Label.TRIVIA_PRESERVE, child) for child in children)
        self.children.extend(entries)

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

    def after(self) -> After | None:
        return self.maybe_after()

    def before(self) -> Before | None:
        return self.maybe_before()

    def default(self) -> Default | None:
        return self.maybe_default()

    def group(self) -> Group | None:
        return self.maybe_group()

    def join(self) -> Join | None:
        return self.maybe_join()

    def nest(self) -> Nest | None:
        return self.maybe_nest()

    def omit(self) -> Omit | None:
        return self.maybe_omit()

    def preserve_blanks(self) -> PreserveBlanks | None:
        return self.maybe_preserve_blanks()

    def render(self) -> Render | None:
        return self.maybe_render()

    def rule_config(self) -> RuleConfig | None:
        return self.maybe_rule_config()

    def trivia_preserve(self) -> TriviaPreserve | None:
        return self.maybe_trivia_preserve()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Statement.variant: node has no labeled child"
        raise ValueError(msg)


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.Spacing | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Spacing | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Default) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.Spacing | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Default.Label)):
            _cn = "Default"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Spacing | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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
    ) -> tuple[Label | None, Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Default.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Spacing | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Default.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_spacing(self, child: _cstp.Spacing) -> None:
        entry: typing.Any = (Default.Label.SPACING, child)
        self.children.append(entry)

    def extend_spacing(self, children: typing.Iterable[_cstp.Spacing]) -> None:
        entries: typing.Any = ((Default.Label.SPACING, child) for child in children)
        self.children.extend(entries)

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

    def append_ws_allowed(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Default.Label.WS_ALLOWED, child))

    def extend_ws_allowed(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Default.Label.WS_ALLOWED, child) for child in children)

    def children_ws_allowed(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Default.Label.WS_ALLOWED
        )

    def child_ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_ws_allowed())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_ws_allowed())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_required(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Default.Label.WS_REQUIRED, child))

    def extend_ws_required(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Default.Label.WS_REQUIRED, child) for child in children)

    def children_ws_required(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Default.Label.WS_REQUIRED
        )

    def child_ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_ws_required())
        if (n := len(children)) != 1:
            msg = f"Expected one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_ws_required())
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def spacing(self) -> Spacing:
        return self.child_spacing()

    def ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_ws_allowed()

    def ws_allowed_text(self) -> str | None:
        child = self.maybe_ws_allowed()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Default.ws_allowed_text: child labelled 'ws_allowed' is not a Span"
            raise TypeError(msg) from None

    def ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_ws_required()

    def ws_required_text(self) -> str | None:
        child = self.maybe_ws_required()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Default.ws_required_text: child labelled 'ws_required' is not a Span"
            raise TypeError(msg) from None


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[
        tuple[Label | None, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render]
    ] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.After
        | _cstp.Before
        | _cstp.Default
        | _cstp.Group
        | _cstp.Join
        | _cstp.Nest
        | _cstp.Omit
        | _cstp.PreserveBlanks
        | _cstp.Render,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[
            _cstp.After
            | _cstp.Before
            | _cstp.Default
            | _cstp.Group
            | _cstp.Join
            | _cstp.Nest
            | _cstp.Omit
            | _cstp.PreserveBlanks
            | _cstp.Render
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
    ) -> tuple[Label | None, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self,
        child: _cstp.After
        | _cstp.Before
        | _cstp.Default
        | _cstp.Group
        | _cstp.Join
        | _cstp.Nest
        | _cstp.Omit
        | _cstp.PreserveBlanks
        | _cstp.Render,
    ) -> None:
        if not isinstance(child, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render):
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
        child: _cstp.After
        | _cstp.Before
        | _cstp.Default
        | _cstp.Group
        | _cstp.Join
        | _cstp.Nest
        | _cstp.Omit
        | _cstp.PreserveBlanks
        | _cstp.Render,
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
        child: _cstp.After
        | _cstp.Before
        | _cstp.Default
        | _cstp.Group
        | _cstp.Join
        | _cstp.Nest
        | _cstp.Omit
        | _cstp.PreserveBlanks
        | _cstp.Render,
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

    def append_after(self, child: _cstp.After) -> None:
        entry: typing.Any = (RuleStatement.Label.AFTER, child)
        self.children.append(entry)

    def extend_after(self, children: typing.Iterable[_cstp.After]) -> None:
        entries: typing.Any = ((RuleStatement.Label.AFTER, child) for child in children)
        self.children.extend(entries)

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

    def append_before(self, child: _cstp.Before) -> None:
        entry: typing.Any = (RuleStatement.Label.BEFORE, child)
        self.children.append(entry)

    def extend_before(self, children: typing.Iterable[_cstp.Before]) -> None:
        entries: typing.Any = ((RuleStatement.Label.BEFORE, child) for child in children)
        self.children.extend(entries)

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

    def append_default(self, child: _cstp.Default) -> None:
        entry: typing.Any = (RuleStatement.Label.DEFAULT, child)
        self.children.append(entry)

    def extend_default(self, children: typing.Iterable[_cstp.Default]) -> None:
        entries: typing.Any = ((RuleStatement.Label.DEFAULT, child) for child in children)
        self.children.extend(entries)

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

    def append_group(self, child: _cstp.Group) -> None:
        entry: typing.Any = (RuleStatement.Label.GROUP, child)
        self.children.append(entry)

    def extend_group(self, children: typing.Iterable[_cstp.Group]) -> None:
        entries: typing.Any = ((RuleStatement.Label.GROUP, child) for child in children)
        self.children.extend(entries)

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

    def append_join(self, child: _cstp.Join) -> None:
        entry: typing.Any = (RuleStatement.Label.JOIN, child)
        self.children.append(entry)

    def extend_join(self, children: typing.Iterable[_cstp.Join]) -> None:
        entries: typing.Any = ((RuleStatement.Label.JOIN, child) for child in children)
        self.children.extend(entries)

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

    def append_nest(self, child: _cstp.Nest) -> None:
        entry: typing.Any = (RuleStatement.Label.NEST, child)
        self.children.append(entry)

    def extend_nest(self, children: typing.Iterable[_cstp.Nest]) -> None:
        entries: typing.Any = ((RuleStatement.Label.NEST, child) for child in children)
        self.children.extend(entries)

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

    def append_omit(self, child: _cstp.Omit) -> None:
        entry: typing.Any = (RuleStatement.Label.OMIT, child)
        self.children.append(entry)

    def extend_omit(self, children: typing.Iterable[_cstp.Omit]) -> None:
        entries: typing.Any = ((RuleStatement.Label.OMIT, child) for child in children)
        self.children.extend(entries)

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

    def append_preserve_blanks(self, child: _cstp.PreserveBlanks) -> None:
        entry: typing.Any = (RuleStatement.Label.PRESERVE_BLANKS, child)
        self.children.append(entry)

    def extend_preserve_blanks(self, children: typing.Iterable[_cstp.PreserveBlanks]) -> None:
        entries: typing.Any = ((RuleStatement.Label.PRESERVE_BLANKS, child) for child in children)
        self.children.extend(entries)

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

    def append_render(self, child: _cstp.Render) -> None:
        entry: typing.Any = (RuleStatement.Label.RENDER, child)
        self.children.append(entry)

    def extend_render(self, children: typing.Iterable[_cstp.Render]) -> None:
        entries: typing.Any = ((RuleStatement.Label.RENDER, child) for child in children)
        self.children.extend(entries)

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

    def after(self) -> After | None:
        return self.maybe_after()

    def before(self) -> Before | None:
        return self.maybe_before()

    def default(self) -> Default | None:
        return self.maybe_default()

    def group(self) -> Group | None:
        return self.maybe_group()

    def join(self) -> Join | None:
        return self.maybe_join()

    def nest(self) -> Nest | None:
        return self.maybe_nest()

    def omit(self) -> Omit | None:
        return self.maybe_omit()

    def preserve_blanks(self) -> PreserveBlanks | None:
        return self.maybe_preserve_blanks()

    def render(self) -> Render | None:
        return self.maybe_render()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "RuleStatement.variant: node has no labeled child"
        raise ValueError(msg)


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FromSpec | ToSpec | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Group) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, FromSpec | ToSpec | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia) -> None:
        if not isinstance(child, FromSpec | ToSpec | Trivia):
            msg = f"Group: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Group.Label)):
            _cn = "Group"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, FromSpec | ToSpec | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Group.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Group.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_from_spec(self, child: _cstp.FromSpec) -> None:
        entry: typing.Any = (Group.Label.FROM_SPEC, child)
        self.children.append(entry)

    def extend_from_spec(self, children: typing.Iterable[_cstp.FromSpec]) -> None:
        entries: typing.Any = ((Group.Label.FROM_SPEC, child) for child in children)
        self.children.extend(entries)

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

    def append_to_spec(self, child: _cstp.ToSpec) -> None:
        entry: typing.Any = (Group.Label.TO_SPEC, child)
        self.children.append(entry)

    def extend_to_spec(self, children: typing.Iterable[_cstp.ToSpec]) -> None:
        entries: typing.Any = ((Group.Label.TO_SPEC, child) for child in children)
        self.children.extend(entries)

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

    def from_spec(self) -> FromSpec | None:
        return self.maybe_from_spec()

    def to_spec(self) -> ToSpec | None:
        return self.maybe_to_spec()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.FromSpec | _cstp.Integer | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.FromSpec | _cstp.Integer | _cstp.ToSpec | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Nest) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.FromSpec | _cstp.Integer | _cstp.ToSpec | _cstp.Trivia
    ) -> None:
        if not isinstance(child, FromSpec | Integer | ToSpec | Trivia):
            msg = f"Nest: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Nest.Label)):
            _cn = "Nest"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.FromSpec | _cstp.Integer | _cstp.ToSpec | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Nest.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.FromSpec | _cstp.Integer | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Nest.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_from_spec(self, child: _cstp.FromSpec) -> None:
        entry: typing.Any = (Nest.Label.FROM_SPEC, child)
        self.children.append(entry)

    def extend_from_spec(self, children: typing.Iterable[_cstp.FromSpec]) -> None:
        entries: typing.Any = ((Nest.Label.FROM_SPEC, child) for child in children)
        self.children.extend(entries)

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

    def append_indent(self, child: _cstp.Integer) -> None:
        entry: typing.Any = (Nest.Label.INDENT, child)
        self.children.append(entry)

    def extend_indent(self, children: typing.Iterable[_cstp.Integer]) -> None:
        entries: typing.Any = ((Nest.Label.INDENT, child) for child in children)
        self.children.extend(entries)

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

    def append_to_spec(self, child: _cstp.ToSpec) -> None:
        entry: typing.Any = (Nest.Label.TO_SPEC, child)
        self.children.append(entry)

    def extend_to_spec(self, children: typing.Iterable[_cstp.ToSpec]) -> None:
        entries: typing.Any = ((Nest.Label.TO_SPEC, child) for child in children)
        self.children.extend(entries)

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

    def from_spec(self) -> FromSpec | None:
        return self.maybe_from_spec()

    def indent(self) -> Integer | None:
        return self.maybe_indent()

    def to_spec(self) -> ToSpec | None:
        return self.maybe_to_spec()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocLiteral | FromSpec | ToSpec | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.DocLiteral | _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.DocLiteral | _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Join) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, DocLiteral | FromSpec | ToSpec | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.DocLiteral | _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia
    ) -> None:
        if not isinstance(child, DocLiteral | FromSpec | ToSpec | Trivia):
            msg = f"Join: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Join.Label)):
            _cn = "Join"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocLiteral | _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, DocLiteral | FromSpec | ToSpec | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Join.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.DocLiteral | _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Join.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_doc_literal(self, child: _cstp.DocLiteral) -> None:
        entry: typing.Any = (Join.Label.DOC_LITERAL, child)
        self.children.append(entry)

    def extend_doc_literal(self, children: typing.Iterable[_cstp.DocLiteral]) -> None:
        entries: typing.Any = ((Join.Label.DOC_LITERAL, child) for child in children)
        self.children.extend(entries)

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

    def append_from_spec(self, child: _cstp.FromSpec) -> None:
        entry: typing.Any = (Join.Label.FROM_SPEC, child)
        self.children.append(entry)

    def extend_from_spec(self, children: typing.Iterable[_cstp.FromSpec]) -> None:
        entries: typing.Any = ((Join.Label.FROM_SPEC, child) for child in children)
        self.children.extend(entries)

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

    def append_to_spec(self, child: _cstp.ToSpec) -> None:
        entry: typing.Any = (Join.Label.TO_SPEC, child)
        self.children.append(entry)

    def extend_to_spec(self, children: typing.Iterable[_cstp.ToSpec]) -> None:
        entries: typing.Any = ((Join.Label.TO_SPEC, child) for child in children)
        self.children.extend(entries)

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

    def doc_literal(self) -> DocLiteral:
        return self.child_doc_literal()

    def from_spec(self) -> FromSpec | None:
        return self.maybe_from_spec()

    def to_spec(self) -> ToSpec | None:
        return self.maybe_to_spec()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.FromSpec) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, FromSpec.Label)):
            _cn = "FromSpec"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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
    ) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FromSpec.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FromSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_after(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((FromSpec.Label.AFTER, child))

    def extend_after(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((FromSpec.Label.AFTER, child) for child in children)

    def children_after(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == FromSpec.Label.AFTER
        )

    def child_after(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_after())
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_after())
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_from_anchor(self, child: _cstp.Anchor) -> None:
        entry: typing.Any = (FromSpec.Label.FROM_ANCHOR, child)
        self.children.append(entry)

    def extend_from_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        entries: typing.Any = ((FromSpec.Label.FROM_ANCHOR, child) for child in children)
        self.children.extend(entries)

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

    def after(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_after()

    def after_text(self) -> str | None:
        child = self.maybe_after()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "FromSpec.after_text: child labelled 'after' is not a Span"
            raise TypeError(msg) from None

    def from_anchor(self) -> Anchor:
        return self.child_from_anchor()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.ToSpec) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, ToSpec.Label)):
            _cn = "ToSpec"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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
    ) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ToSpec.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ToSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_before(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ToSpec.Label.BEFORE, child))

    def extend_before(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((ToSpec.Label.BEFORE, child) for child in children)

    def children_before(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == ToSpec.Label.BEFORE
        )

    def child_before(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_before())
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_before())
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_anchor(self, child: _cstp.Anchor) -> None:
        entry: typing.Any = (ToSpec.Label.TO_ANCHOR, child)
        self.children.append(entry)

    def extend_to_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        entries: typing.Any = ((ToSpec.Label.TO_ANCHOR, child) for child in children)
        self.children.extend(entries)

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

    def before(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_before()

    def before_text(self) -> str | None:
        child = self.maybe_before()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "ToSpec.before_text: child labelled 'before' is not a Span"
            raise TypeError(msg) from None

    def to_anchor(self) -> Anchor:
        return self.child_to_anchor()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Literal]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Literal, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Identifier | _cstp.Literal],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Anchor) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | Literal]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Literal) -> None:
        if not isinstance(child, Identifier | Literal):
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
        child: _cstp.Identifier | _cstp.Literal,
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

    def remove_at(self, index: int) -> tuple[Label | None, Identifier | Literal]:
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
        child: _cstp.Identifier | _cstp.Literal,
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

    def append_label(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (Anchor.Label.LABEL, child)
        self.children.append(entry)

    def extend_label(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((Anchor.Label.LABEL, child) for child in children)
        self.children.extend(entries)

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

    def label(self) -> Identifier | None:
        return self.maybe_label()

    def literal(self) -> Literal | None:
        return self.maybe_literal()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Anchor.variant: node has no labeled child"
        raise ValueError(msg)


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | PositionSpecStatement | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.After) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia) -> None:
        if not isinstance(child, Anchor | PositionSpecStatement | Trivia):
            msg = f"After: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, After.Label)):
            _cn = "After"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"After.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"After.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: _cstp.Anchor) -> None:
        entry: typing.Any = (After.Label.ANCHOR, child)
        self.children.append(entry)

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        entries: typing.Any = ((After.Label.ANCHOR, child) for child in children)
        self.children.extend(entries)

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

    def append_position_spec_statement(self, child: _cstp.PositionSpecStatement) -> None:
        entry: typing.Any = (After.Label.POSITION_SPEC_STATEMENT, child)
        self.children.append(entry)

    def extend_position_spec_statement(self, children: typing.Iterable[_cstp.PositionSpecStatement]) -> None:
        entries: typing.Any = ((After.Label.POSITION_SPEC_STATEMENT, child) for child in children)
        self.children.extend(entries)

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

    def anchor(self) -> Anchor:
        return self.child_anchor()

    def position_spec_statement(self) -> list[PositionSpecStatement]:
        return list(self.children_position_spec_statement())


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | PositionSpecStatement | Trivia]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Before) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia) -> None:
        if not isinstance(child, Anchor | PositionSpecStatement | Trivia):
            msg = f"Before: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Before.Label)):
            _cn = "Before"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Before.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Before.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: _cstp.Anchor) -> None:
        entry: typing.Any = (Before.Label.ANCHOR, child)
        self.children.append(entry)

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        entries: typing.Any = ((Before.Label.ANCHOR, child) for child in children)
        self.children.extend(entries)

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

    def append_position_spec_statement(self, child: _cstp.PositionSpecStatement) -> None:
        entry: typing.Any = (Before.Label.POSITION_SPEC_STATEMENT, child)
        self.children.append(entry)

    def extend_position_spec_statement(self, children: typing.Iterable[_cstp.PositionSpecStatement]) -> None:
        entries: typing.Any = ((Before.Label.POSITION_SPEC_STATEMENT, child) for child in children)
        self.children.extend(entries)

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

    def anchor(self) -> Anchor:
        return self.child_anchor()

    def position_spec_statement(self) -> list[PositionSpecStatement]:
        return list(self.children_position_spec_statement())


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

    def extend_children(self, other: _cstp.Omit) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Anchor | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Anchor | _cstp.Trivia) -> None:
        if not isinstance(child, Anchor | Trivia):
            msg = f"Omit: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Omit.Label)):
            _cn = "Omit"
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
            msg = f"Omit.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Omit.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: _cstp.Anchor) -> None:
        entry: typing.Any = (Omit.Label.ANCHOR, child)
        self.children.append(entry)

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        entries: typing.Any = ((Omit.Label.ANCHOR, child) for child in children)
        self.children.extend(entries)

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

    def anchor(self) -> Anchor:
        return self.child_anchor()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Spacing | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Anchor | _cstp.Spacing | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.Spacing | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Render) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Anchor | Spacing | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Anchor | _cstp.Spacing | _cstp.Trivia) -> None:
        if not isinstance(child, Anchor | Spacing | Trivia):
            msg = f"Render: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Render.Label)):
            _cn = "Render"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Spacing | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, Anchor | Spacing | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Render.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Spacing | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Render.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: _cstp.Anchor) -> None:
        entry: typing.Any = (Render.Label.ANCHOR, child)
        self.children.append(entry)

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        entries: typing.Any = ((Render.Label.ANCHOR, child) for child in children)
        self.children.extend(entries)

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

    def append_spacing(self, child: _cstp.Spacing) -> None:
        entry: typing.Any = (Render.Label.SPACING, child)
        self.children.append(entry)

    def extend_spacing(self, children: typing.Iterable[_cstp.Spacing]) -> None:
        entries: typing.Any = ((Render.Label.SPACING, child) for child in children)
        self.children.extend(entries)

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

    def anchor(self) -> Anchor:
        return self.child_anchor()

    def spacing(self) -> Spacing:
        return self.child_spacing()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, PreserveBlanks | Spacing | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.PreserveBlanks | _cstp.Spacing | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.PreserveBlanks | _cstp.Spacing | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.PositionSpecStatement) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, PreserveBlanks | Spacing | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.PreserveBlanks | _cstp.Spacing | _cstp.Trivia) -> None:
        if not isinstance(child, PreserveBlanks | Spacing | Trivia):
            msg = f"PositionSpecStatement: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, PositionSpecStatement.Label)):
            _cn = "PositionSpecStatement"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.PreserveBlanks | _cstp.Spacing | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, PreserveBlanks | Spacing | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PositionSpecStatement.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.PreserveBlanks | _cstp.Spacing | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PositionSpecStatement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_preserve_blanks(self, child: _cstp.PreserveBlanks) -> None:
        entry: typing.Any = (PositionSpecStatement.Label.PRESERVE_BLANKS, child)
        self.children.append(entry)

    def extend_preserve_blanks(self, children: typing.Iterable[_cstp.PreserveBlanks]) -> None:
        entries: typing.Any = ((PositionSpecStatement.Label.PRESERVE_BLANKS, child) for child in children)
        self.children.extend(entries)

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

    def append_spacing(self, child: _cstp.Spacing) -> None:
        entry: typing.Any = (PositionSpecStatement.Label.SPACING, child)
        self.children.append(entry)

    def extend_spacing(self, children: typing.Iterable[_cstp.Spacing]) -> None:
        entries: typing.Any = ((PositionSpecStatement.Label.SPACING, child) for child in children)
        self.children.extend(entries)

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

    def preserve_blanks(self) -> PreserveBlanks | None:
        return self.maybe_preserve_blanks()

    def spacing(self) -> Spacing | None:
        return self.maybe_spacing()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.Integer | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Integer | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Spacing) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.Integer | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Spacing.Label)):
            _cn = "Spacing"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Integer | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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
    ) -> tuple[Label | None, Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Spacing.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Integer | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Spacing.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_blank(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.BLANK, child))

    def extend_blank(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Spacing.Label.BLANK, child) for child in children)

    def children_blank(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Spacing.Label.BLANK
        )

    def child_blank(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_blank())
        if (n := len(children)) != 1:
            msg = f"Expected one blank child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_blank(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_blank())
        if (n := len(children)) > 1:
            msg = f"Expected at most one blank child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_bsp(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.BSP, child))

    def extend_bsp(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Spacing.Label.BSP, child) for child in children)

    def children_bsp(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Spacing.Label.BSP
        )

    def child_bsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_bsp())
        if (n := len(children)) != 1:
            msg = f"Expected one bsp child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_bsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_bsp())
        if (n := len(children)) > 1:
            msg = f"Expected at most one bsp child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_hard(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.HARD, child))

    def extend_hard(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Spacing.Label.HARD, child) for child in children)

    def children_hard(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Spacing.Label.HARD
        )

    def child_hard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_hard())
        if (n := len(children)) != 1:
            msg = f"Expected one hard child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_hard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_hard())
        if (n := len(children)) > 1:
            msg = f"Expected at most one hard child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nbsp(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.NBSP, child))

    def extend_nbsp(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Spacing.Label.NBSP, child) for child in children)

    def children_nbsp(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Spacing.Label.NBSP
        )

    def child_nbsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_nbsp())
        if (n := len(children)) != 1:
            msg = f"Expected one nbsp child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nbsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_nbsp())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nbsp child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nil(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.NIL, child))

    def extend_nil(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Spacing.Label.NIL, child) for child in children)

    def children_nil(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Spacing.Label.NIL
        )

    def child_nil(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_nil())
        if (n := len(children)) != 1:
            msg = f"Expected one nil child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nil(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_nil())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nil child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_num_blanks(self, child: _cstp.Integer) -> None:
        entry: typing.Any = (Spacing.Label.NUM_BLANKS, child)
        self.children.append(entry)

    def extend_num_blanks(self, children: typing.Iterable[_cstp.Integer]) -> None:
        entries: typing.Any = ((Spacing.Label.NUM_BLANKS, child) for child in children)
        self.children.extend(entries)

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

    def append_soft(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.SOFT, child))

    def extend_soft(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Spacing.Label.SOFT, child) for child in children)

    def children_soft(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Spacing.Label.SOFT
        )

    def child_soft(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_soft())
        if (n := len(children)) != 1:
            msg = f"Expected one soft child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_soft(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_soft())
        if (n := len(children)) > 1:
            msg = f"Expected at most one soft child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def blank(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_blank()

    def blank_text(self) -> str | None:
        child = self.maybe_blank()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Spacing.blank_text: child labelled 'blank' is not a Span"
            raise TypeError(msg) from None

    def bsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_bsp()

    def bsp_text(self) -> str | None:
        child = self.maybe_bsp()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Spacing.bsp_text: child labelled 'bsp' is not a Span"
            raise TypeError(msg) from None

    def hard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_hard()

    def hard_text(self) -> str | None:
        child = self.maybe_hard()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Spacing.hard_text: child labelled 'hard' is not a Span"
            raise TypeError(msg) from None

    def nbsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_nbsp()

    def nbsp_text(self) -> str | None:
        child = self.maybe_nbsp()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Spacing.nbsp_text: child labelled 'nbsp' is not a Span"
            raise TypeError(msg) from None

    def nil(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_nil()

    def nil_text(self) -> str | None:
        child = self.maybe_nil()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Spacing.nil_text: child labelled 'nil' is not a Span"
            raise TypeError(msg) from None

    def num_blanks(self) -> Integer | None:
        return self.maybe_num_blanks()

    def soft(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_soft()

    def soft_text(self) -> str | None:
        child = self.maybe_soft()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Spacing.soft_text: child labelled 'soft' is not a Span"
            raise TypeError(msg) from None


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.CompoundLiteral | _cstp.ConcatLiteral | _cstp.JoinLiteral | _cstp.Spacing | _cstp.TextLiteral,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[
            _cstp.CompoundLiteral | _cstp.ConcatLiteral | _cstp.JoinLiteral | _cstp.Spacing | _cstp.TextLiteral
        ],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.DocLiteral) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.CompoundLiteral | _cstp.ConcatLiteral | _cstp.JoinLiteral | _cstp.Spacing | _cstp.TextLiteral
    ) -> None:
        if not isinstance(child, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral):
            msg = f"DocLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, DocLiteral.Label)):
            _cn = "DocLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.CompoundLiteral | _cstp.ConcatLiteral | _cstp.JoinLiteral | _cstp.Spacing | _cstp.TextLiteral,
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
        child: _cstp.CompoundLiteral | _cstp.ConcatLiteral | _cstp.JoinLiteral | _cstp.Spacing | _cstp.TextLiteral,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DocLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_compound_literal(self, child: _cstp.CompoundLiteral) -> None:
        entry: typing.Any = (DocLiteral.Label.COMPOUND_LITERAL, child)
        self.children.append(entry)

    def extend_compound_literal(self, children: typing.Iterable[_cstp.CompoundLiteral]) -> None:
        entries: typing.Any = ((DocLiteral.Label.COMPOUND_LITERAL, child) for child in children)
        self.children.extend(entries)

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

    def append_concat_literal(self, child: _cstp.ConcatLiteral) -> None:
        entry: typing.Any = (DocLiteral.Label.CONCAT_LITERAL, child)
        self.children.append(entry)

    def extend_concat_literal(self, children: typing.Iterable[_cstp.ConcatLiteral]) -> None:
        entries: typing.Any = ((DocLiteral.Label.CONCAT_LITERAL, child) for child in children)
        self.children.extend(entries)

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

    def append_join_literal(self, child: _cstp.JoinLiteral) -> None:
        entry: typing.Any = (DocLiteral.Label.JOIN_LITERAL, child)
        self.children.append(entry)

    def extend_join_literal(self, children: typing.Iterable[_cstp.JoinLiteral]) -> None:
        entries: typing.Any = ((DocLiteral.Label.JOIN_LITERAL, child) for child in children)
        self.children.extend(entries)

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

    def append_spacing(self, child: _cstp.Spacing) -> None:
        entry: typing.Any = (DocLiteral.Label.SPACING, child)
        self.children.append(entry)

    def extend_spacing(self, children: typing.Iterable[_cstp.Spacing]) -> None:
        entries: typing.Any = ((DocLiteral.Label.SPACING, child) for child in children)
        self.children.extend(entries)

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

    def append_text_literal(self, child: _cstp.TextLiteral) -> None:
        entry: typing.Any = (DocLiteral.Label.TEXT_LITERAL, child)
        self.children.append(entry)

    def extend_text_literal(self, children: typing.Iterable[_cstp.TextLiteral]) -> None:
        entries: typing.Any = ((DocLiteral.Label.TEXT_LITERAL, child) for child in children)
        self.children.extend(entries)

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

    def compound_literal(self) -> CompoundLiteral | None:
        return self.maybe_compound_literal()

    def concat_literal(self) -> ConcatLiteral | None:
        return self.maybe_concat_literal()

    def join_literal(self) -> JoinLiteral | None:
        return self.maybe_join_literal()

    def spacing(self) -> Spacing | None:
        return self.maybe_spacing()

    def text_literal(self) -> TextLiteral | None:
        return self.maybe_text_literal()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "DocLiteral.variant: node has no labeled child"
        raise ValueError(msg)


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Literal | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Literal | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Literal | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.TextLiteral) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Literal | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Literal | _cstp.Trivia) -> None:
        if not isinstance(child, Literal | Trivia):
            msg = f"TextLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, TextLiteral.Label)):
            _cn = "TextLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Literal | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, Literal | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TextLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Literal | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TextLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_text(self, child: _cstp.Literal) -> None:
        entry: typing.Any = (TextLiteral.Label.TEXT, child)
        self.children.append(entry)

    def extend_text(self, children: typing.Iterable[_cstp.Literal]) -> None:
        entries: typing.Any = ((TextLiteral.Label.TEXT, child) for child in children)
        self.children.extend(entries)

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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocListLiteral | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.DocListLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.DocListLiteral | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.ConcatLiteral) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, DocListLiteral | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.DocListLiteral | _cstp.Trivia) -> None:
        if not isinstance(child, DocListLiteral | Trivia):
            msg = f"ConcatLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, ConcatLiteral.Label)):
            _cn = "ConcatLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocListLiteral | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, DocListLiteral | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ConcatLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.DocListLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ConcatLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_doc_list_literal(self, child: _cstp.DocListLiteral) -> None:
        entry: typing.Any = (ConcatLiteral.Label.DOC_LIST_LITERAL, child)
        self.children.append(entry)

    def extend_doc_list_literal(self, children: typing.Iterable[_cstp.DocListLiteral]) -> None:
        entries: typing.Any = ((ConcatLiteral.Label.DOC_LIST_LITERAL, child) for child in children)
        self.children.extend(entries)

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

    def doc_list_literal(self) -> DocListLiteral:
        return self.child_doc_list_literal()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocListLiteral | DocLiteral | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.DocListLiteral | _cstp.DocLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.DocListLiteral | _cstp.DocLiteral | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.JoinLiteral) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, DocListLiteral | DocLiteral | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.DocListLiteral | _cstp.DocLiteral | _cstp.Trivia) -> None:
        if not isinstance(child, DocListLiteral | DocLiteral | Trivia):
            msg = f"JoinLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, JoinLiteral.Label)):
            _cn = "JoinLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocListLiteral | _cstp.DocLiteral | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, DocListLiteral | DocLiteral | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"JoinLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.DocListLiteral | _cstp.DocLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"JoinLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_doc_list_literal(self, child: _cstp.DocListLiteral) -> None:
        entry: typing.Any = (JoinLiteral.Label.DOC_LIST_LITERAL, child)
        self.children.append(entry)

    def extend_doc_list_literal(self, children: typing.Iterable[_cstp.DocListLiteral]) -> None:
        entries: typing.Any = ((JoinLiteral.Label.DOC_LIST_LITERAL, child) for child in children)
        self.children.extend(entries)

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

    def append_separator(self, child: _cstp.DocLiteral) -> None:
        entry: typing.Any = (JoinLiteral.Label.SEPARATOR, child)
        self.children.append(entry)

    def extend_separator(self, children: typing.Iterable[_cstp.DocLiteral]) -> None:
        entries: typing.Any = ((JoinLiteral.Label.SEPARATOR, child) for child in children)
        self.children.extend(entries)

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

    def doc_list_literal(self) -> DocListLiteral:
        return self.child_doc_list_literal()

    def separator(self) -> DocLiteral:
        return self.child_separator()


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocLiteral | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.DocLiteral | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.DocLiteral | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.DocListLiteral) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, DocLiteral | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.DocLiteral | _cstp.Trivia) -> None:
        if not isinstance(child, DocLiteral | Trivia):
            msg = f"DocListLiteral: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, DocListLiteral.Label)):
            _cn = "DocListLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocLiteral | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, DocLiteral | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DocListLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.DocLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DocListLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_doc_literal(self, child: _cstp.DocLiteral) -> None:
        entry: typing.Any = (DocListLiteral.Label.DOC_LITERAL, child)
        self.children.append(entry)

    def extend_doc_literal(self, children: typing.Iterable[_cstp.DocLiteral]) -> None:
        entries: typing.Any = ((DocListLiteral.Label.DOC_LITERAL, child) for child in children)
        self.children.extend(entries)

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

    def doc_literal(self) -> list[DocLiteral]:
        return list(self.children_doc_literal())


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.DocLiteral | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.DocLiteral | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.CompoundLiteral) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.DocLiteral | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, CompoundLiteral.Label)):
            _cn = "CompoundLiteral"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocLiteral | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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
    ) -> tuple[Label | None, DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CompoundLiteral.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.DocLiteral | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CompoundLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_doc_literal(self, child: _cstp.DocLiteral) -> None:
        entry: typing.Any = (CompoundLiteral.Label.DOC_LITERAL, child)
        self.children.append(entry)

    def extend_doc_literal(self, children: typing.Iterable[_cstp.DocLiteral]) -> None:
        entries: typing.Any = ((CompoundLiteral.Label.DOC_LITERAL, child) for child in children)
        self.children.extend(entries)

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

    def append_group(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((CompoundLiteral.Label.GROUP, child))

    def extend_group(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((CompoundLiteral.Label.GROUP, child) for child in children)

    def children_group(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == CompoundLiteral.Label.GROUP
        )

    def child_group(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_group())
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_group())
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((CompoundLiteral.Label.NEST, child))

    def extend_nest(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((CompoundLiteral.Label.NEST, child) for child in children)

    def children_nest(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == CompoundLiteral.Label.NEST
        )

    def child_nest(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_nest())
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_nest())
        if (n := len(children)) > 1:
            msg = f"Expected at most one nest child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def doc_literal(self) -> DocLiteral:
        return self.child_doc_literal()

    def group(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_group()

    def group_text(self) -> str | None:
        child = self.maybe_group()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "CompoundLiteral.group_text: child labelled 'group' is not a Span"
            raise TypeError(msg) from None

    def nest(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_nest()

    def nest_text(self) -> str | None:
        child = self.maybe_nest()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "CompoundLiteral.nest_text: child labelled 'nest' is not a Span"
            raise TypeError(msg) from None


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Trivia | TriviaNodeList]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Trivia | _cstp.TriviaNodeList,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Trivia | _cstp.TriviaNodeList],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.TriviaPreserve) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Trivia | TriviaNodeList]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia | _cstp.TriviaNodeList) -> None:
        if not isinstance(child, Trivia | TriviaNodeList):
            msg = f"TriviaPreserve: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, TriviaPreserve.Label)):
            _cn = "TriviaPreserve"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Trivia | _cstp.TriviaNodeList,
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

    def remove_at(self, index: int) -> tuple[Label | None, Trivia | TriviaNodeList]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TriviaPreserve.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Trivia | _cstp.TriviaNodeList,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TriviaPreserve.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_trivia_node_list(self, child: _cstp.TriviaNodeList) -> None:
        entry: typing.Any = (TriviaPreserve.Label.TRIVIA_NODE_LIST, child)
        self.children.append(entry)

    def extend_trivia_node_list(self, children: typing.Iterable[_cstp.TriviaNodeList]) -> None:
        entries: typing.Any = ((TriviaPreserve.Label.TRIVIA_NODE_LIST, child) for child in children)
        self.children.extend(entries)

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

    def trivia_node_list(self) -> TriviaNodeList:
        return self.child_trivia_node_list()


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

    def extend_children(self, other: _cstp.TriviaNodeList) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Identifier | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Trivia) -> None:
        if not isinstance(child, Identifier | Trivia):
            msg = f"TriviaNodeList: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, TriviaNodeList.Label)):
            _cn = "TriviaNodeList"
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
            msg = f"TriviaNodeList.remove_at: index {index} out of range ({n} children)"
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
            msg = f"TriviaNodeList.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_identifier(self, child: _cstp.Identifier) -> None:
        entry: typing.Any = (TriviaNodeList.Label.IDENTIFIER, child)
        self.children.append(entry)

    def extend_identifier(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        entries: typing.Any = ((TriviaNodeList.Label.IDENTIFIER, child) for child in children)
        self.children.extend(entries)

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

    def identifier(self) -> list[Identifier]:
        return list(self.children_identifier())


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
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Integer | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Integer | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Integer | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.PreserveBlanks) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Integer | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Integer | _cstp.Trivia) -> None:
        if not isinstance(child, Integer | Trivia):
            msg = f"PreserveBlanks: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, PreserveBlanks.Label)):
            _cn = "PreserveBlanks"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Integer | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, Integer | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PreserveBlanks.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Integer | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PreserveBlanks.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_count(self, child: _cstp.Integer) -> None:
        entry: typing.Any = (PreserveBlanks.Label.COUNT, child)
        self.children.append(entry)

    def extend_count(self, children: typing.Iterable[_cstp.Integer]) -> None:
        entries: typing.Any = ((PreserveBlanks.Label.COUNT, child) for child in children)
        self.children.extend(entries)

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

    def count(self) -> Integer:
        return self.child_count()


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

    def extend_children(self, other: _cstp.Integer) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Integer.Label)):
            _cn = "Integer"
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
            msg = f"Integer.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Integer.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Integer.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Integer.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Integer.Label.VALUE)

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
            msg = "Integer.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


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
