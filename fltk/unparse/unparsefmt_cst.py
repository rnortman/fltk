from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import types
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


def _type_name_for_error(obj: object) -> str:
    t = type(obj)
    return f"{t.__module__}.{t.__qualname__}"


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Formatter.Label.STATEMENT": Label.STATEMENT})
    kind: typing.Literal[NodeKind.FORMATTER] = NodeKind.FORMATTER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Statement | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Statement | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Formatter.Label)
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
            if label is None or isinstance(label, Formatter.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Formatter) -> None:
        if not isinstance(other, Formatter):
            msg = f"Formatter: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"Formatter: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Formatter.Label | None:
        if label is None or isinstance(label, Formatter.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Formatter._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Formatter"
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
            if label is None or isinstance(label, Formatter.Label)
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
            msg = f"Formatter.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, Formatter.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Formatter.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Formatter.Label) -> list[Statement | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_statement(self, child: _cstp.Statement) -> None:
        self.children.append((Formatter.Label.STATEMENT, self._check_child_type_for_mutators(child)))

    def extend_statement(self, children: typing.Iterable[_cstp.Statement]) -> None:
        self.children.extend(
            [(Formatter.Label.STATEMENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_statement(self) -> typing.Iterator[Statement]:
        return iter(typing.cast("list[Statement]", self._children_snapshot(Formatter.Label.STATEMENT)))

    def child_statement(self) -> Statement:
        children = typing.cast("list[Statement]", self._children_snapshot(Formatter.Label.STATEMENT))
        if (n := len(children)) != 1:
            msg = f"Expected one statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_statement(self) -> Statement | None:
        children = typing.cast("list[Statement]", self._children_snapshot(Formatter.Label.STATEMENT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def statement(self) -> list[Statement]:
        return typing.cast("list[Statement]", self._children_snapshot(Formatter.Label.STATEMENT))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Statement.Label.AFTER": Label.AFTER,
            "Statement.Label.BEFORE": Label.BEFORE,
            "Statement.Label.DEFAULT": Label.DEFAULT,
            "Statement.Label.GROUP": Label.GROUP,
            "Statement.Label.JOIN": Label.JOIN,
            "Statement.Label.NEST": Label.NEST,
            "Statement.Label.OMIT": Label.OMIT,
            "Statement.Label.PRESERVE_BLANKS": Label.PRESERVE_BLANKS,
            "Statement.Label.RENDER": Label.RENDER,
            "Statement.Label.RULE_CONFIG": Label.RULE_CONFIG,
            "Statement.Label.TRIVIA_PRESERVE": Label.TRIVIA_PRESERVE,
        }
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, Statement.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

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
    ) -> After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render | RuleConfig | TriviaPreserve:
        if isinstance(
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

    def _children_snapshot(
        self, label: Statement.Label
    ) -> list[
        After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render | RuleConfig | TriviaPreserve
    ]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_after(self, child: _cstp.After) -> None:
        self.children.append((Statement.Label.AFTER, self._check_child_type_for_mutators(child)))

    def extend_after(self, children: typing.Iterable[_cstp.After]) -> None:
        self.children.extend(
            [(Statement.Label.AFTER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_after(self) -> typing.Iterator[After]:
        return iter(typing.cast("list[After]", self._children_snapshot(Statement.Label.AFTER)))

    def child_after(self) -> After:
        children = typing.cast("list[After]", self._children_snapshot(Statement.Label.AFTER))
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> After | None:
        children = typing.cast("list[After]", self._children_snapshot(Statement.Label.AFTER))
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_before(self, child: _cstp.Before) -> None:
        self.children.append((Statement.Label.BEFORE, self._check_child_type_for_mutators(child)))

    def extend_before(self, children: typing.Iterable[_cstp.Before]) -> None:
        self.children.extend(
            [(Statement.Label.BEFORE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_before(self) -> typing.Iterator[Before]:
        return iter(typing.cast("list[Before]", self._children_snapshot(Statement.Label.BEFORE)))

    def child_before(self) -> Before:
        children = typing.cast("list[Before]", self._children_snapshot(Statement.Label.BEFORE))
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> Before | None:
        children = typing.cast("list[Before]", self._children_snapshot(Statement.Label.BEFORE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_default(self, child: _cstp.Default) -> None:
        self.children.append((Statement.Label.DEFAULT, self._check_child_type_for_mutators(child)))

    def extend_default(self, children: typing.Iterable[_cstp.Default]) -> None:
        self.children.extend(
            [(Statement.Label.DEFAULT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_default(self) -> typing.Iterator[Default]:
        return iter(typing.cast("list[Default]", self._children_snapshot(Statement.Label.DEFAULT)))

    def child_default(self) -> Default:
        children = typing.cast("list[Default]", self._children_snapshot(Statement.Label.DEFAULT))
        if (n := len(children)) != 1:
            msg = f"Expected one default child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_default(self) -> Default | None:
        children = typing.cast("list[Default]", self._children_snapshot(Statement.Label.DEFAULT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one default child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: _cstp.Group) -> None:
        self.children.append((Statement.Label.GROUP, self._check_child_type_for_mutators(child)))

    def extend_group(self, children: typing.Iterable[_cstp.Group]) -> None:
        self.children.extend(
            [(Statement.Label.GROUP, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_group(self) -> typing.Iterator[Group]:
        return iter(typing.cast("list[Group]", self._children_snapshot(Statement.Label.GROUP)))

    def child_group(self) -> Group:
        children = typing.cast("list[Group]", self._children_snapshot(Statement.Label.GROUP))
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> Group | None:
        children = typing.cast("list[Group]", self._children_snapshot(Statement.Label.GROUP))
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_join(self, child: _cstp.Join) -> None:
        self.children.append((Statement.Label.JOIN, self._check_child_type_for_mutators(child)))

    def extend_join(self, children: typing.Iterable[_cstp.Join]) -> None:
        self.children.extend([(Statement.Label.JOIN, self._check_child_type_for_mutators(child)) for child in children])

    def children_join(self) -> typing.Iterator[Join]:
        return iter(typing.cast("list[Join]", self._children_snapshot(Statement.Label.JOIN)))

    def child_join(self) -> Join:
        children = typing.cast("list[Join]", self._children_snapshot(Statement.Label.JOIN))
        if (n := len(children)) != 1:
            msg = f"Expected one join child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_join(self) -> Join | None:
        children = typing.cast("list[Join]", self._children_snapshot(Statement.Label.JOIN))
        if (n := len(children)) > 1:
            msg = f"Expected at most one join child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: _cstp.Nest) -> None:
        self.children.append((Statement.Label.NEST, self._check_child_type_for_mutators(child)))

    def extend_nest(self, children: typing.Iterable[_cstp.Nest]) -> None:
        self.children.extend([(Statement.Label.NEST, self._check_child_type_for_mutators(child)) for child in children])

    def children_nest(self) -> typing.Iterator[Nest]:
        return iter(typing.cast("list[Nest]", self._children_snapshot(Statement.Label.NEST)))

    def child_nest(self) -> Nest:
        children = typing.cast("list[Nest]", self._children_snapshot(Statement.Label.NEST))
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> Nest | None:
        children = typing.cast("list[Nest]", self._children_snapshot(Statement.Label.NEST))
        if (n := len(children)) > 1:
            msg = f"Expected at most one nest child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_omit(self, child: _cstp.Omit) -> None:
        self.children.append((Statement.Label.OMIT, self._check_child_type_for_mutators(child)))

    def extend_omit(self, children: typing.Iterable[_cstp.Omit]) -> None:
        self.children.extend([(Statement.Label.OMIT, self._check_child_type_for_mutators(child)) for child in children])

    def children_omit(self) -> typing.Iterator[Omit]:
        return iter(typing.cast("list[Omit]", self._children_snapshot(Statement.Label.OMIT)))

    def child_omit(self) -> Omit:
        children = typing.cast("list[Omit]", self._children_snapshot(Statement.Label.OMIT))
        if (n := len(children)) != 1:
            msg = f"Expected one omit child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_omit(self) -> Omit | None:
        children = typing.cast("list[Omit]", self._children_snapshot(Statement.Label.OMIT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one omit child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_preserve_blanks(self, child: _cstp.PreserveBlanks) -> None:
        self.children.append((Statement.Label.PRESERVE_BLANKS, self._check_child_type_for_mutators(child)))

    def extend_preserve_blanks(self, children: typing.Iterable[_cstp.PreserveBlanks]) -> None:
        self.children.extend(
            [(Statement.Label.PRESERVE_BLANKS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_preserve_blanks(self) -> typing.Iterator[PreserveBlanks]:
        return iter(typing.cast("list[PreserveBlanks]", self._children_snapshot(Statement.Label.PRESERVE_BLANKS)))

    def child_preserve_blanks(self) -> PreserveBlanks:
        children = typing.cast("list[PreserveBlanks]", self._children_snapshot(Statement.Label.PRESERVE_BLANKS))
        if (n := len(children)) != 1:
            msg = f"Expected one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_preserve_blanks(self) -> PreserveBlanks | None:
        children = typing.cast("list[PreserveBlanks]", self._children_snapshot(Statement.Label.PRESERVE_BLANKS))
        if (n := len(children)) > 1:
            msg = f"Expected at most one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_render(self, child: _cstp.Render) -> None:
        self.children.append((Statement.Label.RENDER, self._check_child_type_for_mutators(child)))

    def extend_render(self, children: typing.Iterable[_cstp.Render]) -> None:
        self.children.extend(
            [(Statement.Label.RENDER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_render(self) -> typing.Iterator[Render]:
        return iter(typing.cast("list[Render]", self._children_snapshot(Statement.Label.RENDER)))

    def child_render(self) -> Render:
        children = typing.cast("list[Render]", self._children_snapshot(Statement.Label.RENDER))
        if (n := len(children)) != 1:
            msg = f"Expected one render child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_render(self) -> Render | None:
        children = typing.cast("list[Render]", self._children_snapshot(Statement.Label.RENDER))
        if (n := len(children)) > 1:
            msg = f"Expected at most one render child but have {n}"
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

    def append_trivia_preserve(self, child: _cstp.TriviaPreserve) -> None:
        self.children.append((Statement.Label.TRIVIA_PRESERVE, self._check_child_type_for_mutators(child)))

    def extend_trivia_preserve(self, children: typing.Iterable[_cstp.TriviaPreserve]) -> None:
        self.children.extend(
            [(Statement.Label.TRIVIA_PRESERVE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_trivia_preserve(self) -> typing.Iterator[TriviaPreserve]:
        return iter(typing.cast("list[TriviaPreserve]", self._children_snapshot(Statement.Label.TRIVIA_PRESERVE)))

    def child_trivia_preserve(self) -> TriviaPreserve:
        children = typing.cast("list[TriviaPreserve]", self._children_snapshot(Statement.Label.TRIVIA_PRESERVE))
        if (n := len(children)) != 1:
            msg = f"Expected one trivia_preserve child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_trivia_preserve(self) -> TriviaPreserve | None:
        children = typing.cast("list[TriviaPreserve]", self._children_snapshot(Statement.Label.TRIVIA_PRESERVE))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Default.Label.SPACING": Label.SPACING,
            "Default.Label.WS_ALLOWED": Label.WS_ALLOWED,
            "Default.Label.WS_REQUIRED": Label.WS_REQUIRED,
        }
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, Default.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Spacing | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Default.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Default) -> None:
        if not isinstance(other, Default):
            msg = f"Default: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Spacing | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, Spacing | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Default: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Default.Label | None:
        if label is None or isinstance(label, Default.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Default._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Default"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Spacing | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Default.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Default.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Default.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: Default.Label
    ) -> list[Spacing | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_spacing(self, child: _cstp.Spacing) -> None:
        self.children.append((Default.Label.SPACING, self._check_child_type_for_mutators(child)))

    def extend_spacing(self, children: typing.Iterable[_cstp.Spacing]) -> None:
        self.children.extend(
            [(Default.Label.SPACING, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_spacing(self) -> typing.Iterator[Spacing]:
        return iter(typing.cast("list[Spacing]", self._children_snapshot(Default.Label.SPACING)))

    def child_spacing(self) -> Spacing:
        children = typing.cast("list[Spacing]", self._children_snapshot(Default.Label.SPACING))
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> Spacing | None:
        children = typing.cast("list[Spacing]", self._children_snapshot(Default.Label.SPACING))
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_allowed(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Default.Label.WS_ALLOWED, self._check_child_type_for_mutators(child)))

    def extend_ws_allowed(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Default.Label.WS_ALLOWED, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_ws_allowed(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Default.Label.WS_ALLOWED)
            )
        )

    def child_ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Default.Label.WS_ALLOWED)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_allowed(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Default.Label.WS_ALLOWED)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one ws_allowed child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_ws_required(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Default.Label.WS_REQUIRED, self._check_child_type_for_mutators(child)))

    def extend_ws_required(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Default.Label.WS_REQUIRED, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_ws_required(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Default.Label.WS_REQUIRED)
            )
        )

    def child_ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Default.Label.WS_REQUIRED)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one ws_required child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_ws_required(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Default.Label.WS_REQUIRED)
        )
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "RuleStatement.Label.AFTER": Label.AFTER,
            "RuleStatement.Label.BEFORE": Label.BEFORE,
            "RuleStatement.Label.DEFAULT": Label.DEFAULT,
            "RuleStatement.Label.GROUP": Label.GROUP,
            "RuleStatement.Label.JOIN": Label.JOIN,
            "RuleStatement.Label.NEST": Label.NEST,
            "RuleStatement.Label.OMIT": Label.OMIT,
            "RuleStatement.Label.PRESERVE_BLANKS": Label.PRESERVE_BLANKS,
            "RuleStatement.Label.RENDER": Label.RENDER,
        }
    )
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
    ) -> After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render:
        if isinstance(child, After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render):
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
    ) -> list[After | Before | Default | Group | Join | Nest | Omit | PreserveBlanks | Render]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_after(self, child: _cstp.After) -> None:
        self.children.append((RuleStatement.Label.AFTER, self._check_child_type_for_mutators(child)))

    def extend_after(self, children: typing.Iterable[_cstp.After]) -> None:
        self.children.extend(
            [(RuleStatement.Label.AFTER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_after(self) -> typing.Iterator[After]:
        return iter(typing.cast("list[After]", self._children_snapshot(RuleStatement.Label.AFTER)))

    def child_after(self) -> After:
        children = typing.cast("list[After]", self._children_snapshot(RuleStatement.Label.AFTER))
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> After | None:
        children = typing.cast("list[After]", self._children_snapshot(RuleStatement.Label.AFTER))
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_before(self, child: _cstp.Before) -> None:
        self.children.append((RuleStatement.Label.BEFORE, self._check_child_type_for_mutators(child)))

    def extend_before(self, children: typing.Iterable[_cstp.Before]) -> None:
        self.children.extend(
            [(RuleStatement.Label.BEFORE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_before(self) -> typing.Iterator[Before]:
        return iter(typing.cast("list[Before]", self._children_snapshot(RuleStatement.Label.BEFORE)))

    def child_before(self) -> Before:
        children = typing.cast("list[Before]", self._children_snapshot(RuleStatement.Label.BEFORE))
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> Before | None:
        children = typing.cast("list[Before]", self._children_snapshot(RuleStatement.Label.BEFORE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_default(self, child: _cstp.Default) -> None:
        self.children.append((RuleStatement.Label.DEFAULT, self._check_child_type_for_mutators(child)))

    def extend_default(self, children: typing.Iterable[_cstp.Default]) -> None:
        self.children.extend(
            [(RuleStatement.Label.DEFAULT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_default(self) -> typing.Iterator[Default]:
        return iter(typing.cast("list[Default]", self._children_snapshot(RuleStatement.Label.DEFAULT)))

    def child_default(self) -> Default:
        children = typing.cast("list[Default]", self._children_snapshot(RuleStatement.Label.DEFAULT))
        if (n := len(children)) != 1:
            msg = f"Expected one default child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_default(self) -> Default | None:
        children = typing.cast("list[Default]", self._children_snapshot(RuleStatement.Label.DEFAULT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one default child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: _cstp.Group) -> None:
        self.children.append((RuleStatement.Label.GROUP, self._check_child_type_for_mutators(child)))

    def extend_group(self, children: typing.Iterable[_cstp.Group]) -> None:
        self.children.extend(
            [(RuleStatement.Label.GROUP, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_group(self) -> typing.Iterator[Group]:
        return iter(typing.cast("list[Group]", self._children_snapshot(RuleStatement.Label.GROUP)))

    def child_group(self) -> Group:
        children = typing.cast("list[Group]", self._children_snapshot(RuleStatement.Label.GROUP))
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> Group | None:
        children = typing.cast("list[Group]", self._children_snapshot(RuleStatement.Label.GROUP))
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_join(self, child: _cstp.Join) -> None:
        self.children.append((RuleStatement.Label.JOIN, self._check_child_type_for_mutators(child)))

    def extend_join(self, children: typing.Iterable[_cstp.Join]) -> None:
        self.children.extend(
            [(RuleStatement.Label.JOIN, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_join(self) -> typing.Iterator[Join]:
        return iter(typing.cast("list[Join]", self._children_snapshot(RuleStatement.Label.JOIN)))

    def child_join(self) -> Join:
        children = typing.cast("list[Join]", self._children_snapshot(RuleStatement.Label.JOIN))
        if (n := len(children)) != 1:
            msg = f"Expected one join child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_join(self) -> Join | None:
        children = typing.cast("list[Join]", self._children_snapshot(RuleStatement.Label.JOIN))
        if (n := len(children)) > 1:
            msg = f"Expected at most one join child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: _cstp.Nest) -> None:
        self.children.append((RuleStatement.Label.NEST, self._check_child_type_for_mutators(child)))

    def extend_nest(self, children: typing.Iterable[_cstp.Nest]) -> None:
        self.children.extend(
            [(RuleStatement.Label.NEST, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_nest(self) -> typing.Iterator[Nest]:
        return iter(typing.cast("list[Nest]", self._children_snapshot(RuleStatement.Label.NEST)))

    def child_nest(self) -> Nest:
        children = typing.cast("list[Nest]", self._children_snapshot(RuleStatement.Label.NEST))
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> Nest | None:
        children = typing.cast("list[Nest]", self._children_snapshot(RuleStatement.Label.NEST))
        if (n := len(children)) > 1:
            msg = f"Expected at most one nest child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_omit(self, child: _cstp.Omit) -> None:
        self.children.append((RuleStatement.Label.OMIT, self._check_child_type_for_mutators(child)))

    def extend_omit(self, children: typing.Iterable[_cstp.Omit]) -> None:
        self.children.extend(
            [(RuleStatement.Label.OMIT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_omit(self) -> typing.Iterator[Omit]:
        return iter(typing.cast("list[Omit]", self._children_snapshot(RuleStatement.Label.OMIT)))

    def child_omit(self) -> Omit:
        children = typing.cast("list[Omit]", self._children_snapshot(RuleStatement.Label.OMIT))
        if (n := len(children)) != 1:
            msg = f"Expected one omit child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_omit(self) -> Omit | None:
        children = typing.cast("list[Omit]", self._children_snapshot(RuleStatement.Label.OMIT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one omit child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_preserve_blanks(self, child: _cstp.PreserveBlanks) -> None:
        self.children.append((RuleStatement.Label.PRESERVE_BLANKS, self._check_child_type_for_mutators(child)))

    def extend_preserve_blanks(self, children: typing.Iterable[_cstp.PreserveBlanks]) -> None:
        self.children.extend(
            [(RuleStatement.Label.PRESERVE_BLANKS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_preserve_blanks(self) -> typing.Iterator[PreserveBlanks]:
        return iter(typing.cast("list[PreserveBlanks]", self._children_snapshot(RuleStatement.Label.PRESERVE_BLANKS)))

    def child_preserve_blanks(self) -> PreserveBlanks:
        children = typing.cast("list[PreserveBlanks]", self._children_snapshot(RuleStatement.Label.PRESERVE_BLANKS))
        if (n := len(children)) != 1:
            msg = f"Expected one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_preserve_blanks(self) -> PreserveBlanks | None:
        children = typing.cast("list[PreserveBlanks]", self._children_snapshot(RuleStatement.Label.PRESERVE_BLANKS))
        if (n := len(children)) > 1:
            msg = f"Expected at most one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_render(self, child: _cstp.Render) -> None:
        self.children.append((RuleStatement.Label.RENDER, self._check_child_type_for_mutators(child)))

    def extend_render(self, children: typing.Iterable[_cstp.Render]) -> None:
        self.children.extend(
            [(RuleStatement.Label.RENDER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_render(self) -> typing.Iterator[Render]:
        return iter(typing.cast("list[Render]", self._children_snapshot(RuleStatement.Label.RENDER)))

    def child_render(self) -> Render:
        children = typing.cast("list[Render]", self._children_snapshot(RuleStatement.Label.RENDER))
        if (n := len(children)) != 1:
            msg = f"Expected one render child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_render(self) -> Render | None:
        children = typing.cast("list[Render]", self._children_snapshot(RuleStatement.Label.RENDER))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Group.Label.FROM_SPEC": Label.FROM_SPEC, "Group.Label.TO_SPEC": Label.TO_SPEC}
    )
    kind: typing.Literal[NodeKind.GROUP] = NodeKind.GROUP
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FromSpec | ToSpec | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Group.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Group.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Group) -> None:
        if not isinstance(other, Group):
            msg = f"Group: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, FromSpec | ToSpec | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia
    ) -> FromSpec | ToSpec | Trivia:
        if isinstance(child, FromSpec | ToSpec | Trivia):
            return child
        msg = f"Group: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Group.Label | None:
        if label is None or isinstance(label, Group.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Group._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Group"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Group.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Group.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Group.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Group.Label) -> list[FromSpec | ToSpec | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_from_spec(self, child: _cstp.FromSpec) -> None:
        self.children.append((Group.Label.FROM_SPEC, self._check_child_type_for_mutators(child)))

    def extend_from_spec(self, children: typing.Iterable[_cstp.FromSpec]) -> None:
        self.children.extend(
            [(Group.Label.FROM_SPEC, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_from_spec(self) -> typing.Iterator[FromSpec]:
        return iter(typing.cast("list[FromSpec]", self._children_snapshot(Group.Label.FROM_SPEC)))

    def child_from_spec(self) -> FromSpec:
        children = typing.cast("list[FromSpec]", self._children_snapshot(Group.Label.FROM_SPEC))
        if (n := len(children)) != 1:
            msg = f"Expected one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_spec(self) -> FromSpec | None:
        children = typing.cast("list[FromSpec]", self._children_snapshot(Group.Label.FROM_SPEC))
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_spec(self, child: _cstp.ToSpec) -> None:
        self.children.append((Group.Label.TO_SPEC, self._check_child_type_for_mutators(child)))

    def extend_to_spec(self, children: typing.Iterable[_cstp.ToSpec]) -> None:
        self.children.extend([(Group.Label.TO_SPEC, self._check_child_type_for_mutators(child)) for child in children])

    def children_to_spec(self) -> typing.Iterator[ToSpec]:
        return iter(typing.cast("list[ToSpec]", self._children_snapshot(Group.Label.TO_SPEC)))

    def child_to_spec(self) -> ToSpec:
        children = typing.cast("list[ToSpec]", self._children_snapshot(Group.Label.TO_SPEC))
        if (n := len(children)) != 1:
            msg = f"Expected one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_spec(self) -> ToSpec | None:
        children = typing.cast("list[ToSpec]", self._children_snapshot(Group.Label.TO_SPEC))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Nest.Label.FROM_SPEC": Label.FROM_SPEC,
            "Nest.Label.INDENT": Label.INDENT,
            "Nest.Label.TO_SPEC": Label.TO_SPEC,
        }
    )
    kind: typing.Literal[NodeKind.NEST] = NodeKind.NEST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.FromSpec | _cstp.Integer | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Nest.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.FromSpec | _cstp.Integer | _cstp.ToSpec | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Nest.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Nest) -> None:
        if not isinstance(other, Nest):
            msg = f"Nest: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, FromSpec | Integer | ToSpec | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.FromSpec | _cstp.Integer | _cstp.ToSpec | _cstp.Trivia
    ) -> FromSpec | Integer | ToSpec | Trivia:
        if isinstance(child, FromSpec | Integer | ToSpec | Trivia):
            return child
        msg = f"Nest: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Nest.Label | None:
        if label is None or isinstance(label, Nest.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Nest._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Nest"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.FromSpec | _cstp.Integer | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Nest.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Nest.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Nest.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Nest.Label) -> list[FromSpec | Integer | ToSpec | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_from_spec(self, child: _cstp.FromSpec) -> None:
        self.children.append((Nest.Label.FROM_SPEC, self._check_child_type_for_mutators(child)))

    def extend_from_spec(self, children: typing.Iterable[_cstp.FromSpec]) -> None:
        self.children.extend([(Nest.Label.FROM_SPEC, self._check_child_type_for_mutators(child)) for child in children])

    def children_from_spec(self) -> typing.Iterator[FromSpec]:
        return iter(typing.cast("list[FromSpec]", self._children_snapshot(Nest.Label.FROM_SPEC)))

    def child_from_spec(self) -> FromSpec:
        children = typing.cast("list[FromSpec]", self._children_snapshot(Nest.Label.FROM_SPEC))
        if (n := len(children)) != 1:
            msg = f"Expected one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_spec(self) -> FromSpec | None:
        children = typing.cast("list[FromSpec]", self._children_snapshot(Nest.Label.FROM_SPEC))
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_indent(self, child: _cstp.Integer) -> None:
        self.children.append((Nest.Label.INDENT, self._check_child_type_for_mutators(child)))

    def extend_indent(self, children: typing.Iterable[_cstp.Integer]) -> None:
        self.children.extend([(Nest.Label.INDENT, self._check_child_type_for_mutators(child)) for child in children])

    def children_indent(self) -> typing.Iterator[Integer]:
        return iter(typing.cast("list[Integer]", self._children_snapshot(Nest.Label.INDENT)))

    def child_indent(self) -> Integer:
        children = typing.cast("list[Integer]", self._children_snapshot(Nest.Label.INDENT))
        if (n := len(children)) != 1:
            msg = f"Expected one indent child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_indent(self) -> Integer | None:
        children = typing.cast("list[Integer]", self._children_snapshot(Nest.Label.INDENT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one indent child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_spec(self, child: _cstp.ToSpec) -> None:
        self.children.append((Nest.Label.TO_SPEC, self._check_child_type_for_mutators(child)))

    def extend_to_spec(self, children: typing.Iterable[_cstp.ToSpec]) -> None:
        self.children.extend([(Nest.Label.TO_SPEC, self._check_child_type_for_mutators(child)) for child in children])

    def children_to_spec(self) -> typing.Iterator[ToSpec]:
        return iter(typing.cast("list[ToSpec]", self._children_snapshot(Nest.Label.TO_SPEC)))

    def child_to_spec(self) -> ToSpec:
        children = typing.cast("list[ToSpec]", self._children_snapshot(Nest.Label.TO_SPEC))
        if (n := len(children)) != 1:
            msg = f"Expected one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_spec(self) -> ToSpec | None:
        children = typing.cast("list[ToSpec]", self._children_snapshot(Nest.Label.TO_SPEC))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Join.Label.DOC_LITERAL": Label.DOC_LITERAL,
            "Join.Label.FROM_SPEC": Label.FROM_SPEC,
            "Join.Label.TO_SPEC": Label.TO_SPEC,
        }
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, Join.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.DocLiteral | _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Join.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Join) -> None:
        if not isinstance(other, Join):
            msg = f"Join: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocLiteral | FromSpec | ToSpec | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.DocLiteral | _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia
    ) -> DocLiteral | FromSpec | ToSpec | Trivia:
        if isinstance(child, DocLiteral | FromSpec | ToSpec | Trivia):
            return child
        msg = f"Join: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Join.Label | None:
        if label is None or isinstance(label, Join.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Join._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Join"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocLiteral | _cstp.FromSpec | _cstp.ToSpec | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Join.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Join.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Join.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Join.Label) -> list[DocLiteral | FromSpec | ToSpec | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_doc_literal(self, child: _cstp.DocLiteral) -> None:
        self.children.append((Join.Label.DOC_LITERAL, self._check_child_type_for_mutators(child)))

    def extend_doc_literal(self, children: typing.Iterable[_cstp.DocLiteral]) -> None:
        self.children.extend(
            [(Join.Label.DOC_LITERAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]:
        return iter(typing.cast("list[DocLiteral]", self._children_snapshot(Join.Label.DOC_LITERAL)))

    def child_doc_literal(self) -> DocLiteral:
        children = typing.cast("list[DocLiteral]", self._children_snapshot(Join.Label.DOC_LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_literal(self) -> DocLiteral | None:
        children = typing.cast("list[DocLiteral]", self._children_snapshot(Join.Label.DOC_LITERAL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_from_spec(self, child: _cstp.FromSpec) -> None:
        self.children.append((Join.Label.FROM_SPEC, self._check_child_type_for_mutators(child)))

    def extend_from_spec(self, children: typing.Iterable[_cstp.FromSpec]) -> None:
        self.children.extend([(Join.Label.FROM_SPEC, self._check_child_type_for_mutators(child)) for child in children])

    def children_from_spec(self) -> typing.Iterator[FromSpec]:
        return iter(typing.cast("list[FromSpec]", self._children_snapshot(Join.Label.FROM_SPEC)))

    def child_from_spec(self) -> FromSpec:
        children = typing.cast("list[FromSpec]", self._children_snapshot(Join.Label.FROM_SPEC))
        if (n := len(children)) != 1:
            msg = f"Expected one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_spec(self) -> FromSpec | None:
        children = typing.cast("list[FromSpec]", self._children_snapshot(Join.Label.FROM_SPEC))
        if (n := len(children)) > 1:
            msg = f"Expected at most one from_spec child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_spec(self, child: _cstp.ToSpec) -> None:
        self.children.append((Join.Label.TO_SPEC, self._check_child_type_for_mutators(child)))

    def extend_to_spec(self, children: typing.Iterable[_cstp.ToSpec]) -> None:
        self.children.extend([(Join.Label.TO_SPEC, self._check_child_type_for_mutators(child)) for child in children])

    def children_to_spec(self) -> typing.Iterator[ToSpec]:
        return iter(typing.cast("list[ToSpec]", self._children_snapshot(Join.Label.TO_SPEC)))

    def child_to_spec(self) -> ToSpec:
        children = typing.cast("list[ToSpec]", self._children_snapshot(Join.Label.TO_SPEC))
        if (n := len(children)) != 1:
            msg = f"Expected one to_spec child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_spec(self) -> ToSpec | None:
        children = typing.cast("list[ToSpec]", self._children_snapshot(Join.Label.TO_SPEC))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"FromSpec.Label.AFTER": Label.AFTER, "FromSpec.Label.FROM_ANCHOR": Label.FROM_ANCHOR}
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, FromSpec.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FromSpec.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.FromSpec) -> None:
        if not isinstance(other, FromSpec):
            msg = f"FromSpec: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, Anchor | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"FromSpec: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> FromSpec.Label | None:
        if label is None or isinstance(label, FromSpec.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = FromSpec._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "FromSpec"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FromSpec.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, FromSpec.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FromSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: FromSpec.Label
    ) -> list[Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_after(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((FromSpec.Label.AFTER, self._check_child_type_for_mutators(child)))

    def extend_after(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(FromSpec.Label.AFTER, self._check_child_type_for_mutators(child)) for child in children])

    def children_after(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(FromSpec.Label.AFTER)
            )
        )

    def child_after(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(FromSpec.Label.AFTER)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one after child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_after(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(FromSpec.Label.AFTER)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one after child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_from_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((FromSpec.Label.FROM_ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_from_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend(
            [(FromSpec.Label.FROM_ANCHOR, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_from_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(FromSpec.Label.FROM_ANCHOR)))

    def child_from_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(FromSpec.Label.FROM_ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one from_anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_from_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(FromSpec.Label.FROM_ANCHOR))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"ToSpec.Label.BEFORE": Label.BEFORE, "ToSpec.Label.TO_ANCHOR": Label.TO_ANCHOR}
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, ToSpec.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ToSpec.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ToSpec) -> None:
        if not isinstance(other, ToSpec):
            msg = f"ToSpec: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, Anchor | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"ToSpec: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ToSpec.Label | None:
        if label is None or isinstance(label, ToSpec.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ToSpec._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ToSpec"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ToSpec.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, ToSpec.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ToSpec.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: ToSpec.Label
    ) -> list[Anchor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_before(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ToSpec.Label.BEFORE, self._check_child_type_for_mutators(child)))

    def extend_before(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(ToSpec.Label.BEFORE, self._check_child_type_for_mutators(child)) for child in children])

    def children_before(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(ToSpec.Label.BEFORE)
            )
        )

    def child_before(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(ToSpec.Label.BEFORE)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one before child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_before(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(ToSpec.Label.BEFORE)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one before child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_to_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((ToSpec.Label.TO_ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_to_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend(
            [(ToSpec.Label.TO_ANCHOR, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_to_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(ToSpec.Label.TO_ANCHOR)))

    def child_to_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(ToSpec.Label.TO_ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one to_anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_to_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(ToSpec.Label.TO_ANCHOR))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Anchor.Label.LABEL": Label.LABEL, "Anchor.Label.LITERAL": Label.LITERAL}
    )
    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Literal]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Literal, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
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
        children: typing.Iterable[_cstp.Identifier | _cstp.Literal],
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

    def child(self) -> tuple[Label | None, Identifier | Literal]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Identifier | _cstp.Literal) -> Identifier | Literal:
        if isinstance(child, Identifier | Literal):
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
        child: _cstp.Identifier | _cstp.Literal,
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

    def _children_snapshot(self, label: Anchor.Label) -> list[Identifier | Literal]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_label(self, child: _cstp.Identifier) -> None:
        self.children.append((Anchor.Label.LABEL, self._check_child_type_for_mutators(child)))

    def extend_label(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend([(Anchor.Label.LABEL, self._check_child_type_for_mutators(child)) for child in children])

    def children_label(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(Anchor.Label.LABEL)))

    def child_label(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(Anchor.Label.LABEL))
        if (n := len(children)) != 1:
            msg = f"Expected one label child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_label(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(Anchor.Label.LABEL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one label child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"After.Label.ANCHOR": Label.ANCHOR, "After.Label.POSITION_SPEC_STATEMENT": Label.POSITION_SPEC_STATEMENT}
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, After.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, After.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.After) -> None:
        if not isinstance(other, After):
            msg = f"After: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia
    ) -> Anchor | PositionSpecStatement | Trivia:
        if isinstance(child, Anchor | PositionSpecStatement | Trivia):
            return child
        msg = f"After: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> After.Label | None:
        if label is None or isinstance(label, After.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = After._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "After"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, After.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, After.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"After.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: After.Label) -> list[Anchor | PositionSpecStatement | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((After.Label.ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend([(After.Label.ANCHOR, self._check_child_type_for_mutators(child)) for child in children])

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(After.Label.ANCHOR)))

    def child_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(After.Label.ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(After.Label.ANCHOR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_position_spec_statement(self, child: _cstp.PositionSpecStatement) -> None:
        self.children.append((After.Label.POSITION_SPEC_STATEMENT, self._check_child_type_for_mutators(child)))

    def extend_position_spec_statement(self, children: typing.Iterable[_cstp.PositionSpecStatement]) -> None:
        self.children.extend(
            [(After.Label.POSITION_SPEC_STATEMENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_position_spec_statement(self) -> typing.Iterator[PositionSpecStatement]:
        return iter(
            typing.cast("list[PositionSpecStatement]", self._children_snapshot(After.Label.POSITION_SPEC_STATEMENT))
        )

    def child_position_spec_statement(self) -> PositionSpecStatement:
        children = typing.cast(
            "list[PositionSpecStatement]", self._children_snapshot(After.Label.POSITION_SPEC_STATEMENT)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_position_spec_statement(self) -> PositionSpecStatement | None:
        children = typing.cast(
            "list[PositionSpecStatement]", self._children_snapshot(After.Label.POSITION_SPEC_STATEMENT)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def anchor(self) -> Anchor:
        return self.child_anchor()

    def position_spec_statement(self) -> list[PositionSpecStatement]:
        return typing.cast("list[PositionSpecStatement]", self._children_snapshot(After.Label.POSITION_SPEC_STATEMENT))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Before.Label.ANCHOR": Label.ANCHOR, "Before.Label.POSITION_SPEC_STATEMENT": Label.POSITION_SPEC_STATEMENT}
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, Before.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Before.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Before) -> None:
        if not isinstance(other, Before):
            msg = f"Before: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | PositionSpecStatement | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia
    ) -> Anchor | PositionSpecStatement | Trivia:
        if isinstance(child, Anchor | PositionSpecStatement | Trivia):
            return child
        msg = f"Before: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Before.Label | None:
        if label is None or isinstance(label, Before.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Before._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Before"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.PositionSpecStatement | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Before.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Before.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Before.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Before.Label) -> list[Anchor | PositionSpecStatement | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((Before.Label.ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend([(Before.Label.ANCHOR, self._check_child_type_for_mutators(child)) for child in children])

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(Before.Label.ANCHOR)))

    def child_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(Before.Label.ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(Before.Label.ANCHOR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_position_spec_statement(self, child: _cstp.PositionSpecStatement) -> None:
        self.children.append((Before.Label.POSITION_SPEC_STATEMENT, self._check_child_type_for_mutators(child)))

    def extend_position_spec_statement(self, children: typing.Iterable[_cstp.PositionSpecStatement]) -> None:
        self.children.extend(
            [(Before.Label.POSITION_SPEC_STATEMENT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_position_spec_statement(self) -> typing.Iterator[PositionSpecStatement]:
        return iter(
            typing.cast("list[PositionSpecStatement]", self._children_snapshot(Before.Label.POSITION_SPEC_STATEMENT))
        )

    def child_position_spec_statement(self) -> PositionSpecStatement:
        children = typing.cast(
            "list[PositionSpecStatement]", self._children_snapshot(Before.Label.POSITION_SPEC_STATEMENT)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_position_spec_statement(self) -> PositionSpecStatement | None:
        children = typing.cast(
            "list[PositionSpecStatement]", self._children_snapshot(Before.Label.POSITION_SPEC_STATEMENT)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one position_spec_statement child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def anchor(self) -> Anchor:
        return self.child_anchor()

    def position_spec_statement(self) -> list[PositionSpecStatement]:
        return typing.cast("list[PositionSpecStatement]", self._children_snapshot(Before.Label.POSITION_SPEC_STATEMENT))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Omit.Label.ANCHOR": Label.ANCHOR})
    kind: typing.Literal[NodeKind.OMIT] = NodeKind.OMIT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Anchor | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Omit.Label)
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
            if label is None or isinstance(label, Omit.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Omit) -> None:
        if not isinstance(other, Omit):
            msg = f"Omit: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"Omit: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Omit.Label | None:
        if label is None or isinstance(label, Omit.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Omit._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Omit"
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
            if label is None or isinstance(label, Omit.Label)
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
            msg = f"Omit.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, Omit.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Omit.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Omit.Label) -> list[Anchor | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((Omit.Label.ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend([(Omit.Label.ANCHOR, self._check_child_type_for_mutators(child)) for child in children])

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(Omit.Label.ANCHOR)))

    def child_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(Omit.Label.ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(Omit.Label.ANCHOR))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Render.Label.ANCHOR": Label.ANCHOR, "Render.Label.SPACING": Label.SPACING}
    )
    kind: typing.Literal[NodeKind.RENDER] = NodeKind.RENDER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | Spacing | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Anchor | _cstp.Spacing | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Render.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Anchor | _cstp.Spacing | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Render.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Render) -> None:
        if not isinstance(other, Render):
            msg = f"Render: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | Spacing | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Anchor | _cstp.Spacing | _cstp.Trivia
    ) -> Anchor | Spacing | Trivia:
        if isinstance(child, Anchor | Spacing | Trivia):
            return child
        msg = f"Render: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Render.Label | None:
        if label is None or isinstance(label, Render.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Render._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Render"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor | _cstp.Spacing | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Render.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Render.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Render.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Render.Label) -> list[Anchor | Spacing | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((Render.Label.ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend([(Render.Label.ANCHOR, self._check_child_type_for_mutators(child)) for child in children])

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(Render.Label.ANCHOR)))

    def child_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(Render.Label.ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(Render.Label.ANCHOR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_spacing(self, child: _cstp.Spacing) -> None:
        self.children.append((Render.Label.SPACING, self._check_child_type_for_mutators(child)))

    def extend_spacing(self, children: typing.Iterable[_cstp.Spacing]) -> None:
        self.children.extend([(Render.Label.SPACING, self._check_child_type_for_mutators(child)) for child in children])

    def children_spacing(self) -> typing.Iterator[Spacing]:
        return iter(typing.cast("list[Spacing]", self._children_snapshot(Render.Label.SPACING)))

    def child_spacing(self) -> Spacing:
        children = typing.cast("list[Spacing]", self._children_snapshot(Render.Label.SPACING))
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> Spacing | None:
        children = typing.cast("list[Spacing]", self._children_snapshot(Render.Label.SPACING))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "PositionSpecStatement.Label.PRESERVE_BLANKS": Label.PRESERVE_BLANKS,
            "PositionSpecStatement.Label.SPACING": Label.SPACING,
        }
    )
    kind: typing.Literal[NodeKind.POSITIONSPECSTATEMENT] = NodeKind.POSITIONSPECSTATEMENT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, PreserveBlanks | Spacing | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.PreserveBlanks | _cstp.Spacing | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, PositionSpecStatement.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.PreserveBlanks | _cstp.Spacing | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, PositionSpecStatement.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.PositionSpecStatement) -> None:
        if not isinstance(other, PositionSpecStatement):
            msg = f"PositionSpecStatement: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, PreserveBlanks | Spacing | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.PreserveBlanks | _cstp.Spacing | _cstp.Trivia
    ) -> PreserveBlanks | Spacing | Trivia:
        if isinstance(child, PreserveBlanks | Spacing | Trivia):
            return child
        msg = f"PositionSpecStatement: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> PositionSpecStatement.Label | None:
        if label is None or isinstance(label, PositionSpecStatement.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = PositionSpecStatement._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "PositionSpecStatement"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.PreserveBlanks | _cstp.Spacing | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, PositionSpecStatement.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, PositionSpecStatement.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PositionSpecStatement.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: PositionSpecStatement.Label) -> list[PreserveBlanks | Spacing | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_preserve_blanks(self, child: _cstp.PreserveBlanks) -> None:
        self.children.append((PositionSpecStatement.Label.PRESERVE_BLANKS, self._check_child_type_for_mutators(child)))

    def extend_preserve_blanks(self, children: typing.Iterable[_cstp.PreserveBlanks]) -> None:
        self.children.extend(
            [
                (PositionSpecStatement.Label.PRESERVE_BLANKS, self._check_child_type_for_mutators(child))
                for child in children
            ]
        )

    def children_preserve_blanks(self) -> typing.Iterator[PreserveBlanks]:
        return iter(
            typing.cast("list[PreserveBlanks]", self._children_snapshot(PositionSpecStatement.Label.PRESERVE_BLANKS))
        )

    def child_preserve_blanks(self) -> PreserveBlanks:
        children = typing.cast(
            "list[PreserveBlanks]", self._children_snapshot(PositionSpecStatement.Label.PRESERVE_BLANKS)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_preserve_blanks(self) -> PreserveBlanks | None:
        children = typing.cast(
            "list[PreserveBlanks]", self._children_snapshot(PositionSpecStatement.Label.PRESERVE_BLANKS)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one preserve_blanks child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_spacing(self, child: _cstp.Spacing) -> None:
        self.children.append((PositionSpecStatement.Label.SPACING, self._check_child_type_for_mutators(child)))

    def extend_spacing(self, children: typing.Iterable[_cstp.Spacing]) -> None:
        self.children.extend(
            [(PositionSpecStatement.Label.SPACING, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_spacing(self) -> typing.Iterator[Spacing]:
        return iter(typing.cast("list[Spacing]", self._children_snapshot(PositionSpecStatement.Label.SPACING)))

    def child_spacing(self) -> Spacing:
        children = typing.cast("list[Spacing]", self._children_snapshot(PositionSpecStatement.Label.SPACING))
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> Spacing | None:
        children = typing.cast("list[Spacing]", self._children_snapshot(PositionSpecStatement.Label.SPACING))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "Spacing.Label.BLANK": Label.BLANK,
            "Spacing.Label.BSP": Label.BSP,
            "Spacing.Label.HARD": Label.HARD,
            "Spacing.Label.NBSP": Label.NBSP,
            "Spacing.Label.NIL": Label.NIL,
            "Spacing.Label.NUM_BLANKS": Label.NUM_BLANKS,
            "Spacing.Label.SOFT": Label.SOFT,
        }
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, Spacing.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Integer | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Spacing.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Spacing) -> None:
        if not isinstance(other, Spacing):
            msg = f"Spacing: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Integer | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, Integer | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Spacing: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Spacing.Label | None:
        if label is None or isinstance(label, Spacing.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Spacing._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Spacing"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Integer | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Spacing.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Spacing.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Spacing.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: Spacing.Label
    ) -> list[Integer | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_blank(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.BLANK, self._check_child_type_for_mutators(child)))

    def extend_blank(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Spacing.Label.BLANK, self._check_child_type_for_mutators(child)) for child in children])

    def children_blank(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.BLANK)
            )
        )

    def child_blank(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.BLANK)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one blank child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_blank(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.BLANK)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one blank child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_bsp(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.BSP, self._check_child_type_for_mutators(child)))

    def extend_bsp(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Spacing.Label.BSP, self._check_child_type_for_mutators(child)) for child in children])

    def children_bsp(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.BSP))
        )

    def child_bsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.BSP)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one bsp child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_bsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.BSP)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one bsp child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_hard(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.HARD, self._check_child_type_for_mutators(child)))

    def extend_hard(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Spacing.Label.HARD, self._check_child_type_for_mutators(child)) for child in children])

    def children_hard(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.HARD))
        )

    def child_hard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.HARD)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one hard child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_hard(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.HARD)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one hard child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nbsp(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.NBSP, self._check_child_type_for_mutators(child)))

    def extend_nbsp(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Spacing.Label.NBSP, self._check_child_type_for_mutators(child)) for child in children])

    def children_nbsp(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.NBSP))
        )

    def child_nbsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.NBSP)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one nbsp child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nbsp(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.NBSP)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one nbsp child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nil(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.NIL, self._check_child_type_for_mutators(child)))

    def extend_nil(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Spacing.Label.NIL, self._check_child_type_for_mutators(child)) for child in children])

    def children_nil(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.NIL))
        )

    def child_nil(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.NIL)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one nil child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nil(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.NIL)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one nil child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_num_blanks(self, child: _cstp.Integer) -> None:
        self.children.append((Spacing.Label.NUM_BLANKS, self._check_child_type_for_mutators(child)))

    def extend_num_blanks(self, children: typing.Iterable[_cstp.Integer]) -> None:
        self.children.extend(
            [(Spacing.Label.NUM_BLANKS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_num_blanks(self) -> typing.Iterator[Integer]:
        return iter(typing.cast("list[Integer]", self._children_snapshot(Spacing.Label.NUM_BLANKS)))

    def child_num_blanks(self) -> Integer:
        children = typing.cast("list[Integer]", self._children_snapshot(Spacing.Label.NUM_BLANKS))
        if (n := len(children)) != 1:
            msg = f"Expected one num_blanks child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_num_blanks(self) -> Integer | None:
        children = typing.cast("list[Integer]", self._children_snapshot(Spacing.Label.NUM_BLANKS))
        if (n := len(children)) > 1:
            msg = f"Expected at most one num_blanks child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_soft(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Spacing.Label.SOFT, self._check_child_type_for_mutators(child)))

    def extend_soft(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Spacing.Label.SOFT, self._check_child_type_for_mutators(child)) for child in children])

    def children_soft(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.SOFT))
        )

    def child_soft(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.SOFT)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one soft child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_soft(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Spacing.Label.SOFT)
        )
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "DocLiteral.Label.COMPOUND_LITERAL": Label.COMPOUND_LITERAL,
            "DocLiteral.Label.CONCAT_LITERAL": Label.CONCAT_LITERAL,
            "DocLiteral.Label.JOIN_LITERAL": Label.JOIN_LITERAL,
            "DocLiteral.Label.SPACING": Label.SPACING,
            "DocLiteral.Label.TEXT_LITERAL": Label.TEXT_LITERAL,
        }
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, DocLiteral.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[
            _cstp.CompoundLiteral | _cstp.ConcatLiteral | _cstp.JoinLiteral | _cstp.Spacing | _cstp.TextLiteral
        ],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DocLiteral.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.DocLiteral) -> None:
        if not isinstance(other, DocLiteral):
            msg = f"DocLiteral: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.CompoundLiteral | _cstp.ConcatLiteral | _cstp.JoinLiteral | _cstp.Spacing | _cstp.TextLiteral
    ) -> CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral:
        if isinstance(child, CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral):
            return child
        msg = f"DocLiteral: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> DocLiteral.Label | None:
        if label is None or isinstance(label, DocLiteral.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = DocLiteral._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "DocLiteral"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.CompoundLiteral | _cstp.ConcatLiteral | _cstp.JoinLiteral | _cstp.Spacing | _cstp.TextLiteral,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DocLiteral.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, DocLiteral.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DocLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: DocLiteral.Label
    ) -> list[CompoundLiteral | ConcatLiteral | JoinLiteral | Spacing | TextLiteral]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_compound_literal(self, child: _cstp.CompoundLiteral) -> None:
        self.children.append((DocLiteral.Label.COMPOUND_LITERAL, self._check_child_type_for_mutators(child)))

    def extend_compound_literal(self, children: typing.Iterable[_cstp.CompoundLiteral]) -> None:
        self.children.extend(
            [(DocLiteral.Label.COMPOUND_LITERAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_compound_literal(self) -> typing.Iterator[CompoundLiteral]:
        return iter(typing.cast("list[CompoundLiteral]", self._children_snapshot(DocLiteral.Label.COMPOUND_LITERAL)))

    def child_compound_literal(self) -> CompoundLiteral:
        children = typing.cast("list[CompoundLiteral]", self._children_snapshot(DocLiteral.Label.COMPOUND_LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one compound_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_compound_literal(self) -> CompoundLiteral | None:
        children = typing.cast("list[CompoundLiteral]", self._children_snapshot(DocLiteral.Label.COMPOUND_LITERAL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one compound_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_concat_literal(self, child: _cstp.ConcatLiteral) -> None:
        self.children.append((DocLiteral.Label.CONCAT_LITERAL, self._check_child_type_for_mutators(child)))

    def extend_concat_literal(self, children: typing.Iterable[_cstp.ConcatLiteral]) -> None:
        self.children.extend(
            [(DocLiteral.Label.CONCAT_LITERAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_concat_literal(self) -> typing.Iterator[ConcatLiteral]:
        return iter(typing.cast("list[ConcatLiteral]", self._children_snapshot(DocLiteral.Label.CONCAT_LITERAL)))

    def child_concat_literal(self) -> ConcatLiteral:
        children = typing.cast("list[ConcatLiteral]", self._children_snapshot(DocLiteral.Label.CONCAT_LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one concat_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_concat_literal(self) -> ConcatLiteral | None:
        children = typing.cast("list[ConcatLiteral]", self._children_snapshot(DocLiteral.Label.CONCAT_LITERAL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one concat_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_join_literal(self, child: _cstp.JoinLiteral) -> None:
        self.children.append((DocLiteral.Label.JOIN_LITERAL, self._check_child_type_for_mutators(child)))

    def extend_join_literal(self, children: typing.Iterable[_cstp.JoinLiteral]) -> None:
        self.children.extend(
            [(DocLiteral.Label.JOIN_LITERAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_join_literal(self) -> typing.Iterator[JoinLiteral]:
        return iter(typing.cast("list[JoinLiteral]", self._children_snapshot(DocLiteral.Label.JOIN_LITERAL)))

    def child_join_literal(self) -> JoinLiteral:
        children = typing.cast("list[JoinLiteral]", self._children_snapshot(DocLiteral.Label.JOIN_LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one join_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_join_literal(self) -> JoinLiteral | None:
        children = typing.cast("list[JoinLiteral]", self._children_snapshot(DocLiteral.Label.JOIN_LITERAL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one join_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_spacing(self, child: _cstp.Spacing) -> None:
        self.children.append((DocLiteral.Label.SPACING, self._check_child_type_for_mutators(child)))

    def extend_spacing(self, children: typing.Iterable[_cstp.Spacing]) -> None:
        self.children.extend(
            [(DocLiteral.Label.SPACING, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_spacing(self) -> typing.Iterator[Spacing]:
        return iter(typing.cast("list[Spacing]", self._children_snapshot(DocLiteral.Label.SPACING)))

    def child_spacing(self) -> Spacing:
        children = typing.cast("list[Spacing]", self._children_snapshot(DocLiteral.Label.SPACING))
        if (n := len(children)) != 1:
            msg = f"Expected one spacing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_spacing(self) -> Spacing | None:
        children = typing.cast("list[Spacing]", self._children_snapshot(DocLiteral.Label.SPACING))
        if (n := len(children)) > 1:
            msg = f"Expected at most one spacing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_text_literal(self, child: _cstp.TextLiteral) -> None:
        self.children.append((DocLiteral.Label.TEXT_LITERAL, self._check_child_type_for_mutators(child)))

    def extend_text_literal(self, children: typing.Iterable[_cstp.TextLiteral]) -> None:
        self.children.extend(
            [(DocLiteral.Label.TEXT_LITERAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_text_literal(self) -> typing.Iterator[TextLiteral]:
        return iter(typing.cast("list[TextLiteral]", self._children_snapshot(DocLiteral.Label.TEXT_LITERAL)))

    def child_text_literal(self) -> TextLiteral:
        children = typing.cast("list[TextLiteral]", self._children_snapshot(DocLiteral.Label.TEXT_LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one text_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_text_literal(self) -> TextLiteral | None:
        children = typing.cast("list[TextLiteral]", self._children_snapshot(DocLiteral.Label.TEXT_LITERAL))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"TextLiteral.Label.TEXT": Label.TEXT})
    kind: typing.Literal[NodeKind.TEXTLITERAL] = NodeKind.TEXTLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Literal | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Literal | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TextLiteral.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Literal | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TextLiteral.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.TextLiteral) -> None:
        if not isinstance(other, TextLiteral):
            msg = f"TextLiteral: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Literal | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Literal | _cstp.Trivia) -> Literal | Trivia:
        if isinstance(child, Literal | Trivia):
            return child
        msg = f"TextLiteral: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> TextLiteral.Label | None:
        if label is None or isinstance(label, TextLiteral.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = TextLiteral._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "TextLiteral"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Literal | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TextLiteral.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, TextLiteral.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TextLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: TextLiteral.Label) -> list[Literal | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_text(self, child: _cstp.Literal) -> None:
        self.children.append((TextLiteral.Label.TEXT, self._check_child_type_for_mutators(child)))

    def extend_text(self, children: typing.Iterable[_cstp.Literal]) -> None:
        self.children.extend(
            [(TextLiteral.Label.TEXT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_text(self) -> typing.Iterator[Literal]:
        return iter(typing.cast("list[Literal]", self._children_snapshot(TextLiteral.Label.TEXT)))

    def child_text(self) -> Literal:
        children = typing.cast("list[Literal]", self._children_snapshot(TextLiteral.Label.TEXT))
        if (n := len(children)) != 1:
            msg = f"Expected one text child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_text(self) -> Literal | None:
        children = typing.cast("list[Literal]", self._children_snapshot(TextLiteral.Label.TEXT))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"ConcatLiteral.Label.DOC_LIST_LITERAL": Label.DOC_LIST_LITERAL})
    kind: typing.Literal[NodeKind.CONCATLITERAL] = NodeKind.CONCATLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocListLiteral | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.DocListLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ConcatLiteral.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.DocListLiteral | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ConcatLiteral.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ConcatLiteral) -> None:
        if not isinstance(other, ConcatLiteral):
            msg = f"ConcatLiteral: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocListLiteral | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.DocListLiteral | _cstp.Trivia) -> DocListLiteral | Trivia:
        if isinstance(child, DocListLiteral | Trivia):
            return child
        msg = f"ConcatLiteral: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ConcatLiteral.Label | None:
        if label is None or isinstance(label, ConcatLiteral.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ConcatLiteral._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ConcatLiteral"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocListLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ConcatLiteral.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, ConcatLiteral.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ConcatLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ConcatLiteral.Label) -> list[DocListLiteral | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_doc_list_literal(self, child: _cstp.DocListLiteral) -> None:
        self.children.append((ConcatLiteral.Label.DOC_LIST_LITERAL, self._check_child_type_for_mutators(child)))

    def extend_doc_list_literal(self, children: typing.Iterable[_cstp.DocListLiteral]) -> None:
        self.children.extend(
            [(ConcatLiteral.Label.DOC_LIST_LITERAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_doc_list_literal(self) -> typing.Iterator[DocListLiteral]:
        return iter(typing.cast("list[DocListLiteral]", self._children_snapshot(ConcatLiteral.Label.DOC_LIST_LITERAL)))

    def child_doc_list_literal(self) -> DocListLiteral:
        children = typing.cast("list[DocListLiteral]", self._children_snapshot(ConcatLiteral.Label.DOC_LIST_LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_list_literal(self) -> DocListLiteral | None:
        children = typing.cast("list[DocListLiteral]", self._children_snapshot(ConcatLiteral.Label.DOC_LIST_LITERAL))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"JoinLiteral.Label.DOC_LIST_LITERAL": Label.DOC_LIST_LITERAL, "JoinLiteral.Label.SEPARATOR": Label.SEPARATOR}
    )
    kind: typing.Literal[NodeKind.JOINLITERAL] = NodeKind.JOINLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocListLiteral | DocLiteral | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.DocListLiteral | _cstp.DocLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, JoinLiteral.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.DocListLiteral | _cstp.DocLiteral | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, JoinLiteral.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.JoinLiteral) -> None:
        if not isinstance(other, JoinLiteral):
            msg = f"JoinLiteral: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocListLiteral | DocLiteral | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.DocListLiteral | _cstp.DocLiteral | _cstp.Trivia
    ) -> DocListLiteral | DocLiteral | Trivia:
        if isinstance(child, DocListLiteral | DocLiteral | Trivia):
            return child
        msg = f"JoinLiteral: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> JoinLiteral.Label | None:
        if label is None or isinstance(label, JoinLiteral.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = JoinLiteral._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "JoinLiteral"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocListLiteral | _cstp.DocLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, JoinLiteral.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, JoinLiteral.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"JoinLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: JoinLiteral.Label) -> list[DocListLiteral | DocLiteral | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_doc_list_literal(self, child: _cstp.DocListLiteral) -> None:
        self.children.append((JoinLiteral.Label.DOC_LIST_LITERAL, self._check_child_type_for_mutators(child)))

    def extend_doc_list_literal(self, children: typing.Iterable[_cstp.DocListLiteral]) -> None:
        self.children.extend(
            [(JoinLiteral.Label.DOC_LIST_LITERAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_doc_list_literal(self) -> typing.Iterator[DocListLiteral]:
        return iter(typing.cast("list[DocListLiteral]", self._children_snapshot(JoinLiteral.Label.DOC_LIST_LITERAL)))

    def child_doc_list_literal(self) -> DocListLiteral:
        children = typing.cast("list[DocListLiteral]", self._children_snapshot(JoinLiteral.Label.DOC_LIST_LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_list_literal(self) -> DocListLiteral | None:
        children = typing.cast("list[DocListLiteral]", self._children_snapshot(JoinLiteral.Label.DOC_LIST_LITERAL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_list_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_separator(self, child: _cstp.DocLiteral) -> None:
        self.children.append((JoinLiteral.Label.SEPARATOR, self._check_child_type_for_mutators(child)))

    def extend_separator(self, children: typing.Iterable[_cstp.DocLiteral]) -> None:
        self.children.extend(
            [(JoinLiteral.Label.SEPARATOR, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_separator(self) -> typing.Iterator[DocLiteral]:
        return iter(typing.cast("list[DocLiteral]", self._children_snapshot(JoinLiteral.Label.SEPARATOR)))

    def child_separator(self) -> DocLiteral:
        children = typing.cast("list[DocLiteral]", self._children_snapshot(JoinLiteral.Label.SEPARATOR))
        if (n := len(children)) != 1:
            msg = f"Expected one separator child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_separator(self) -> DocLiteral | None:
        children = typing.cast("list[DocLiteral]", self._children_snapshot(JoinLiteral.Label.SEPARATOR))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"DocListLiteral.Label.DOC_LITERAL": Label.DOC_LITERAL})
    kind: typing.Literal[NodeKind.DOCLISTLITERAL] = NodeKind.DOCLISTLITERAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, DocLiteral | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.DocLiteral | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DocListLiteral.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.DocLiteral | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DocListLiteral.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.DocListLiteral) -> None:
        if not isinstance(other, DocListLiteral):
            msg = f"DocListLiteral: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocLiteral | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.DocLiteral | _cstp.Trivia) -> DocLiteral | Trivia:
        if isinstance(child, DocLiteral | Trivia):
            return child
        msg = f"DocListLiteral: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> DocListLiteral.Label | None:
        if label is None or isinstance(label, DocListLiteral.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = DocListLiteral._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "DocListLiteral"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocLiteral | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, DocListLiteral.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, DocListLiteral.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"DocListLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: DocListLiteral.Label) -> list[DocLiteral | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_doc_literal(self, child: _cstp.DocLiteral) -> None:
        self.children.append((DocListLiteral.Label.DOC_LITERAL, self._check_child_type_for_mutators(child)))

    def extend_doc_literal(self, children: typing.Iterable[_cstp.DocLiteral]) -> None:
        self.children.extend(
            [(DocListLiteral.Label.DOC_LITERAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]:
        return iter(typing.cast("list[DocLiteral]", self._children_snapshot(DocListLiteral.Label.DOC_LITERAL)))

    def child_doc_literal(self) -> DocLiteral:
        children = typing.cast("list[DocLiteral]", self._children_snapshot(DocListLiteral.Label.DOC_LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_literal(self) -> DocLiteral | None:
        children = typing.cast("list[DocLiteral]", self._children_snapshot(DocListLiteral.Label.DOC_LITERAL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def doc_literal(self) -> list[DocLiteral]:
        return typing.cast("list[DocLiteral]", self._children_snapshot(DocListLiteral.Label.DOC_LITERAL))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {
            "CompoundLiteral.Label.DOC_LITERAL": Label.DOC_LITERAL,
            "CompoundLiteral.Label.GROUP": Label.GROUP,
            "CompoundLiteral.Label.NEST": Label.NEST,
        }
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, CompoundLiteral.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.DocLiteral | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CompoundLiteral.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.CompoundLiteral) -> None:
        if not isinstance(other, CompoundLiteral):
            msg = f"CompoundLiteral: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.DocLiteral | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, DocLiteral | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"CompoundLiteral: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> CompoundLiteral.Label | None:
        if label is None or isinstance(label, CompoundLiteral.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = CompoundLiteral._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "CompoundLiteral"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.DocLiteral | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CompoundLiteral.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, CompoundLiteral.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CompoundLiteral.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: CompoundLiteral.Label
    ) -> list[DocLiteral | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_doc_literal(self, child: _cstp.DocLiteral) -> None:
        self.children.append((CompoundLiteral.Label.DOC_LITERAL, self._check_child_type_for_mutators(child)))

    def extend_doc_literal(self, children: typing.Iterable[_cstp.DocLiteral]) -> None:
        self.children.extend(
            [(CompoundLiteral.Label.DOC_LITERAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_doc_literal(self) -> typing.Iterator[DocLiteral]:
        return iter(typing.cast("list[DocLiteral]", self._children_snapshot(CompoundLiteral.Label.DOC_LITERAL)))

    def child_doc_literal(self) -> DocLiteral:
        children = typing.cast("list[DocLiteral]", self._children_snapshot(CompoundLiteral.Label.DOC_LITERAL))
        if (n := len(children)) != 1:
            msg = f"Expected one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_doc_literal(self) -> DocLiteral | None:
        children = typing.cast("list[DocLiteral]", self._children_snapshot(CompoundLiteral.Label.DOC_LITERAL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one doc_literal child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((CompoundLiteral.Label.GROUP, self._check_child_type_for_mutators(child)))

    def extend_group(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(CompoundLiteral.Label.GROUP, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_group(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(CompoundLiteral.Label.GROUP)
            )
        )

    def child_group(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(CompoundLiteral.Label.GROUP)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(CompoundLiteral.Label.GROUP)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_nest(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((CompoundLiteral.Label.NEST, self._check_child_type_for_mutators(child)))

    def extend_nest(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(CompoundLiteral.Label.NEST, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_nest(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(CompoundLiteral.Label.NEST)
            )
        )

    def child_nest(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(CompoundLiteral.Label.NEST)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one nest child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_nest(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(CompoundLiteral.Label.NEST)
        )
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"TriviaPreserve.Label.TRIVIA_NODE_LIST": Label.TRIVIA_NODE_LIST}
    )
    kind: typing.Literal[NodeKind.TRIVIAPRESERVE] = NodeKind.TRIVIAPRESERVE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Trivia | TriviaNodeList]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Trivia | _cstp.TriviaNodeList,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TriviaPreserve.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Trivia | _cstp.TriviaNodeList],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TriviaPreserve.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.TriviaPreserve) -> None:
        if not isinstance(other, TriviaPreserve):
            msg = f"TriviaPreserve: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Trivia | TriviaNodeList]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Trivia | _cstp.TriviaNodeList) -> Trivia | TriviaNodeList:
        if isinstance(child, Trivia | TriviaNodeList):
            return child
        msg = f"TriviaPreserve: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> TriviaPreserve.Label | None:
        if label is None or isinstance(label, TriviaPreserve.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = TriviaPreserve._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "TriviaPreserve"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Trivia | _cstp.TriviaNodeList,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TriviaPreserve.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, TriviaPreserve.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TriviaPreserve.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: TriviaPreserve.Label) -> list[Trivia | TriviaNodeList]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_trivia_node_list(self, child: _cstp.TriviaNodeList) -> None:
        self.children.append((TriviaPreserve.Label.TRIVIA_NODE_LIST, self._check_child_type_for_mutators(child)))

    def extend_trivia_node_list(self, children: typing.Iterable[_cstp.TriviaNodeList]) -> None:
        self.children.extend(
            [(TriviaPreserve.Label.TRIVIA_NODE_LIST, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_trivia_node_list(self) -> typing.Iterator[TriviaNodeList]:
        return iter(typing.cast("list[TriviaNodeList]", self._children_snapshot(TriviaPreserve.Label.TRIVIA_NODE_LIST)))

    def child_trivia_node_list(self) -> TriviaNodeList:
        children = typing.cast("list[TriviaNodeList]", self._children_snapshot(TriviaPreserve.Label.TRIVIA_NODE_LIST))
        if (n := len(children)) != 1:
            msg = f"Expected one trivia_node_list child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_trivia_node_list(self) -> TriviaNodeList | None:
        children = typing.cast("list[TriviaNodeList]", self._children_snapshot(TriviaPreserve.Label.TRIVIA_NODE_LIST))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"TriviaNodeList.Label.IDENTIFIER": Label.IDENTIFIER})
    kind: typing.Literal[NodeKind.TRIVIANODELIST] = NodeKind.TRIVIANODELIST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Identifier | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Identifier | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, TriviaNodeList.Label)
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
            if label is None or isinstance(label, TriviaNodeList.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.TriviaNodeList) -> None:
        if not isinstance(other, TriviaNodeList):
            msg = f"TriviaNodeList: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"TriviaNodeList: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> TriviaNodeList.Label | None:
        if label is None or isinstance(label, TriviaNodeList.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = TriviaNodeList._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "TriviaNodeList"
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
            if label is None or isinstance(label, TriviaNodeList.Label)
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
            msg = f"TriviaNodeList.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, TriviaNodeList.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"TriviaNodeList.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: TriviaNodeList.Label) -> list[Identifier | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_identifier(self, child: _cstp.Identifier) -> None:
        self.children.append((TriviaNodeList.Label.IDENTIFIER, self._check_child_type_for_mutators(child)))

    def extend_identifier(self, children: typing.Iterable[_cstp.Identifier]) -> None:
        self.children.extend(
            [(TriviaNodeList.Label.IDENTIFIER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_identifier(self) -> typing.Iterator[Identifier]:
        return iter(typing.cast("list[Identifier]", self._children_snapshot(TriviaNodeList.Label.IDENTIFIER)))

    def child_identifier(self) -> Identifier:
        children = typing.cast("list[Identifier]", self._children_snapshot(TriviaNodeList.Label.IDENTIFIER))
        if (n := len(children)) != 1:
            msg = f"Expected one identifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_identifier(self) -> Identifier | None:
        children = typing.cast("list[Identifier]", self._children_snapshot(TriviaNodeList.Label.IDENTIFIER))
        if (n := len(children)) > 1:
            msg = f"Expected at most one identifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def identifier(self) -> list[Identifier]:
        return typing.cast("list[Identifier]", self._children_snapshot(TriviaNodeList.Label.IDENTIFIER))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"PreserveBlanks.Label.COUNT": Label.COUNT})
    kind: typing.Literal[NodeKind.PRESERVEBLANKS] = NodeKind.PRESERVEBLANKS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Integer | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Integer | _cstp.Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, PreserveBlanks.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Integer | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, PreserveBlanks.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.PreserveBlanks) -> None:
        if not isinstance(other, PreserveBlanks):
            msg = f"PreserveBlanks: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Integer | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Integer | _cstp.Trivia) -> Integer | Trivia:
        if isinstance(child, Integer | Trivia):
            return child
        msg = f"PreserveBlanks: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> PreserveBlanks.Label | None:
        if label is None or isinstance(label, PreserveBlanks.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = PreserveBlanks._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "PreserveBlanks"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Integer | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, PreserveBlanks.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, PreserveBlanks.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"PreserveBlanks.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: PreserveBlanks.Label) -> list[Integer | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_count(self, child: _cstp.Integer) -> None:
        self.children.append((PreserveBlanks.Label.COUNT, self._check_child_type_for_mutators(child)))

    def extend_count(self, children: typing.Iterable[_cstp.Integer]) -> None:
        self.children.extend(
            [(PreserveBlanks.Label.COUNT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_count(self) -> typing.Iterator[Integer]:
        return iter(typing.cast("list[Integer]", self._children_snapshot(PreserveBlanks.Label.COUNT)))

    def child_count(self) -> Integer:
        children = typing.cast("list[Integer]", self._children_snapshot(PreserveBlanks.Label.COUNT))
        if (n := len(children)) != 1:
            msg = f"Expected one count child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_count(self) -> Integer | None:
        children = typing.cast("list[Integer]", self._children_snapshot(PreserveBlanks.Label.COUNT))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Integer.Label.VALUE": Label.VALUE})
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
        checked_label = (
            label
            if label is None or isinstance(label, Integer.Label)
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
            if label is None or isinstance(label, Integer.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Integer) -> None:
        if not isinstance(other, Integer):
            msg = f"Integer: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"Integer: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Integer.Label | None:
        if label is None or isinstance(label, Integer.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Integer._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Integer"
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
            if label is None or isinstance(label, Integer.Label)
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
            msg = f"Integer.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, Integer.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Integer.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Integer.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Integer.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Integer.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children])

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Integer.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Integer.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Integer.Label.VALUE)
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
