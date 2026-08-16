from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import types
import typing

import fltk.fegen.pyrt.terminalsrc
from fltk.fegen.regex_cst_protocol import NodeKind

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol
    import fltk.fegen.regex_cst_protocol as _cstp


def _get_native_span_type():
    m = sys.modules.get("fltk._native")
    return m.Span if m is not None else None


def _type_name_for_error(obj: object) -> str:
    t = type(obj)
    return f"{t.__module__}.{t.__qualname__}"


@dataclasses.dataclass
class Regex:
    class Label(enum.Enum):
        ALTERNATION = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Regex.Label.ALTERNATION": Label.ALTERNATION})
    kind: typing.Literal[NodeKind.REGEX] = NodeKind.REGEX
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Regex.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Alternation],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Regex.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Regex) -> None:
        if not isinstance(other, Regex):
            msg = f"Regex: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Alternation) -> Alternation:
        if isinstance(child, Alternation):
            return child
        msg = f"Regex: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Regex.Label | None:
        if label is None or isinstance(label, Regex.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Regex._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Regex"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Regex.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Alternation]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Regex.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Regex.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Regex.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Regex.Label) -> list[Alternation]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_alternation(self, child: _cstp.Alternation) -> None:
        self.children.append((Regex.Label.ALTERNATION, self._check_child_type_for_mutators(child)))

    def extend_alternation(self, children: typing.Iterable[_cstp.Alternation]) -> None:
        self.children.extend(
            [(Regex.Label.ALTERNATION, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_alternation(self) -> typing.Iterator[Alternation]:
        return iter(self._children_snapshot(Regex.Label.ALTERNATION))

    def child_alternation(self) -> Alternation:
        children = self._children_snapshot(Regex.Label.ALTERNATION)
        if (n := len(children)) != 1:
            msg = f"Expected one alternation child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_alternation(self) -> Alternation | None:
        children = self._children_snapshot(Regex.Label.ALTERNATION)
        if (n := len(children)) > 1:
            msg = f"Expected at most one alternation child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def alternation(self) -> Alternation:
        return self.child_alternation()


Regex.Label.ALTERNATION._fltk_canonical_name = "Regex.Label.ALTERNATION"


@dataclasses.dataclass
class Alternation:
    class Label(enum.Enum):
        BRANCH = enum.auto()
        LEFT = enum.auto()
        RIGHT = enum.auto()
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
            "Alternation.Label.BRANCH": Label.BRANCH,
            "Alternation.Label.LEFT": Label.LEFT,
            "Alternation.Label.RIGHT": Label.RIGHT,
        }
    )
    kind: typing.Literal[NodeKind.ALTERNATION] = NodeKind.ALTERNATION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation | Concatenation]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Alternation | _cstp.Concatenation,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Alternation.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Alternation | _cstp.Concatenation],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Alternation.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Alternation) -> None:
        if not isinstance(other, Alternation):
            msg = f"Alternation: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation | Concatenation]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Alternation | _cstp.Concatenation
    ) -> Alternation | Concatenation:
        if isinstance(child, Alternation | Concatenation):
            return child
        msg = f"Alternation: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Alternation.Label | None:
        if label is None or isinstance(label, Alternation.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Alternation._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Alternation"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Alternation | _cstp.Concatenation,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Alternation.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Alternation | Concatenation]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Alternation.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Alternation | _cstp.Concatenation,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Alternation.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Alternation.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Alternation.Label) -> list[Alternation | Concatenation]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_branch(self, child: _cstp.Concatenation) -> None:
        self.children.append((Alternation.Label.BRANCH, self._check_child_type_for_mutators(child)))

    def extend_branch(self, children: typing.Iterable[_cstp.Concatenation]) -> None:
        self.children.extend(
            [(Alternation.Label.BRANCH, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_branch(self) -> typing.Iterator[Concatenation]:
        return iter(typing.cast("list[Concatenation]", self._children_snapshot(Alternation.Label.BRANCH)))

    def child_branch(self) -> Concatenation:
        children = typing.cast("list[Concatenation]", self._children_snapshot(Alternation.Label.BRANCH))
        if (n := len(children)) != 1:
            msg = f"Expected one branch child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_branch(self) -> Concatenation | None:
        children = typing.cast("list[Concatenation]", self._children_snapshot(Alternation.Label.BRANCH))
        if (n := len(children)) > 1:
            msg = f"Expected at most one branch child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_left(self, child: _cstp.Alternation) -> None:
        self.children.append((Alternation.Label.LEFT, self._check_child_type_for_mutators(child)))

    def extend_left(self, children: typing.Iterable[_cstp.Alternation]) -> None:
        self.children.extend(
            [(Alternation.Label.LEFT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_left(self) -> typing.Iterator[Alternation]:
        return iter(typing.cast("list[Alternation]", self._children_snapshot(Alternation.Label.LEFT)))

    def child_left(self) -> Alternation:
        children = typing.cast("list[Alternation]", self._children_snapshot(Alternation.Label.LEFT))
        if (n := len(children)) != 1:
            msg = f"Expected one left child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_left(self) -> Alternation | None:
        children = typing.cast("list[Alternation]", self._children_snapshot(Alternation.Label.LEFT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one left child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_right(self, child: _cstp.Concatenation) -> None:
        self.children.append((Alternation.Label.RIGHT, self._check_child_type_for_mutators(child)))

    def extend_right(self, children: typing.Iterable[_cstp.Concatenation]) -> None:
        self.children.extend(
            [(Alternation.Label.RIGHT, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_right(self) -> typing.Iterator[Concatenation]:
        return iter(typing.cast("list[Concatenation]", self._children_snapshot(Alternation.Label.RIGHT)))

    def child_right(self) -> Concatenation:
        children = typing.cast("list[Concatenation]", self._children_snapshot(Alternation.Label.RIGHT))
        if (n := len(children)) != 1:
            msg = f"Expected one right child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_right(self) -> Concatenation | None:
        children = typing.cast("list[Concatenation]", self._children_snapshot(Alternation.Label.RIGHT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one right child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def branch(self) -> Concatenation | None:
        return self.maybe_branch()

    def left(self) -> Alternation | None:
        return self.maybe_left()

    def right(self) -> Concatenation | None:
        return self.maybe_right()


Alternation.Label.BRANCH._fltk_canonical_name = "Alternation.Label.BRANCH"
Alternation.Label.LEFT._fltk_canonical_name = "Alternation.Label.LEFT"
Alternation.Label.RIGHT._fltk_canonical_name = "Alternation.Label.RIGHT"


@dataclasses.dataclass
class Concatenation:
    class Label(enum.Enum):
        HEAD = enum.auto()
        SINGLE = enum.auto()
        TAIL = enum.auto()
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
            "Concatenation.Label.HEAD": Label.HEAD,
            "Concatenation.Label.SINGLE": Label.SINGLE,
            "Concatenation.Label.TAIL": Label.TAIL,
        }
    )
    kind: typing.Literal[NodeKind.CONCATENATION] = NodeKind.CONCATENATION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Concatenation | Repetition]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Concatenation | _cstp.Repetition,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Concatenation.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Concatenation | _cstp.Repetition],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Concatenation.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Concatenation) -> None:
        if not isinstance(other, Concatenation):
            msg = f"Concatenation: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Concatenation | Repetition]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Concatenation | _cstp.Repetition
    ) -> Concatenation | Repetition:
        if isinstance(child, Concatenation | Repetition):
            return child
        msg = f"Concatenation: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Concatenation.Label | None:
        if label is None or isinstance(label, Concatenation.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Concatenation._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Concatenation"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Concatenation | _cstp.Repetition,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Concatenation.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Concatenation | Repetition]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Concatenation.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Concatenation | _cstp.Repetition,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Concatenation.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Concatenation.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Concatenation.Label) -> list[Concatenation | Repetition]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_head(self, child: _cstp.Concatenation) -> None:
        self.children.append((Concatenation.Label.HEAD, self._check_child_type_for_mutators(child)))

    def extend_head(self, children: typing.Iterable[_cstp.Concatenation]) -> None:
        self.children.extend(
            [(Concatenation.Label.HEAD, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_head(self) -> typing.Iterator[Concatenation]:
        return iter(typing.cast("list[Concatenation]", self._children_snapshot(Concatenation.Label.HEAD)))

    def child_head(self) -> Concatenation:
        children = typing.cast("list[Concatenation]", self._children_snapshot(Concatenation.Label.HEAD))
        if (n := len(children)) != 1:
            msg = f"Expected one head child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_head(self) -> Concatenation | None:
        children = typing.cast("list[Concatenation]", self._children_snapshot(Concatenation.Label.HEAD))
        if (n := len(children)) > 1:
            msg = f"Expected at most one head child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_single(self, child: _cstp.Repetition) -> None:
        self.children.append((Concatenation.Label.SINGLE, self._check_child_type_for_mutators(child)))

    def extend_single(self, children: typing.Iterable[_cstp.Repetition]) -> None:
        self.children.extend(
            [(Concatenation.Label.SINGLE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_single(self) -> typing.Iterator[Repetition]:
        return iter(typing.cast("list[Repetition]", self._children_snapshot(Concatenation.Label.SINGLE)))

    def child_single(self) -> Repetition:
        children = typing.cast("list[Repetition]", self._children_snapshot(Concatenation.Label.SINGLE))
        if (n := len(children)) != 1:
            msg = f"Expected one single child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_single(self) -> Repetition | None:
        children = typing.cast("list[Repetition]", self._children_snapshot(Concatenation.Label.SINGLE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one single child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_tail(self, child: _cstp.Repetition) -> None:
        self.children.append((Concatenation.Label.TAIL, self._check_child_type_for_mutators(child)))

    def extend_tail(self, children: typing.Iterable[_cstp.Repetition]) -> None:
        self.children.extend(
            [(Concatenation.Label.TAIL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_tail(self) -> typing.Iterator[Repetition]:
        return iter(typing.cast("list[Repetition]", self._children_snapshot(Concatenation.Label.TAIL)))

    def child_tail(self) -> Repetition:
        children = typing.cast("list[Repetition]", self._children_snapshot(Concatenation.Label.TAIL))
        if (n := len(children)) != 1:
            msg = f"Expected one tail child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_tail(self) -> Repetition | None:
        children = typing.cast("list[Repetition]", self._children_snapshot(Concatenation.Label.TAIL))
        if (n := len(children)) > 1:
            msg = f"Expected at most one tail child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def head(self) -> Concatenation | None:
        return self.maybe_head()

    def single(self) -> Repetition | None:
        return self.maybe_single()

    def tail(self) -> Repetition | None:
        return self.maybe_tail()


Concatenation.Label.HEAD._fltk_canonical_name = "Concatenation.Label.HEAD"
Concatenation.Label.SINGLE._fltk_canonical_name = "Concatenation.Label.SINGLE"
Concatenation.Label.TAIL._fltk_canonical_name = "Concatenation.Label.TAIL"


@dataclasses.dataclass
class Repetition:
    class Label(enum.Enum):
        ATOM = enum.auto()
        QUANTIFIER = enum.auto()
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
        {"Repetition.Label.ATOM": Label.ATOM, "Repetition.Label.QUANTIFIER": Label.QUANTIFIER}
    )
    kind: typing.Literal[NodeKind.REPETITION] = NodeKind.REPETITION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Atom | Quantifier]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Atom | _cstp.Quantifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Repetition.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Atom | _cstp.Quantifier],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Repetition.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Repetition) -> None:
        if not isinstance(other, Repetition):
            msg = f"Repetition: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Atom | Quantifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Atom | _cstp.Quantifier) -> Atom | Quantifier:
        if isinstance(child, Atom | Quantifier):
            return child
        msg = f"Repetition: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Repetition.Label | None:
        if label is None or isinstance(label, Repetition.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Repetition._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Repetition"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Atom | _cstp.Quantifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Repetition.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Atom | Quantifier]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Repetition.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Atom | _cstp.Quantifier,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Repetition.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Repetition.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Repetition.Label) -> list[Atom | Quantifier]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_atom(self, child: _cstp.Atom) -> None:
        self.children.append((Repetition.Label.ATOM, self._check_child_type_for_mutators(child)))

    def extend_atom(self, children: typing.Iterable[_cstp.Atom]) -> None:
        self.children.extend(
            [(Repetition.Label.ATOM, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_atom(self) -> typing.Iterator[Atom]:
        return iter(typing.cast("list[Atom]", self._children_snapshot(Repetition.Label.ATOM)))

    def child_atom(self) -> Atom:
        children = typing.cast("list[Atom]", self._children_snapshot(Repetition.Label.ATOM))
        if (n := len(children)) != 1:
            msg = f"Expected one atom child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_atom(self) -> Atom | None:
        children = typing.cast("list[Atom]", self._children_snapshot(Repetition.Label.ATOM))
        if (n := len(children)) > 1:
            msg = f"Expected at most one atom child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_quantifier(self, child: _cstp.Quantifier) -> None:
        self.children.append((Repetition.Label.QUANTIFIER, self._check_child_type_for_mutators(child)))

    def extend_quantifier(self, children: typing.Iterable[_cstp.Quantifier]) -> None:
        self.children.extend(
            [(Repetition.Label.QUANTIFIER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_quantifier(self) -> typing.Iterator[Quantifier]:
        return iter(typing.cast("list[Quantifier]", self._children_snapshot(Repetition.Label.QUANTIFIER)))

    def child_quantifier(self) -> Quantifier:
        children = typing.cast("list[Quantifier]", self._children_snapshot(Repetition.Label.QUANTIFIER))
        if (n := len(children)) != 1:
            msg = f"Expected one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_quantifier(self) -> Quantifier | None:
        children = typing.cast("list[Quantifier]", self._children_snapshot(Repetition.Label.QUANTIFIER))
        if (n := len(children)) > 1:
            msg = f"Expected at most one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def atom(self) -> Atom:
        return self.child_atom()

    def quantifier(self) -> Quantifier | None:
        return self.maybe_quantifier()


Repetition.Label.ATOM._fltk_canonical_name = "Repetition.Label.ATOM"
Repetition.Label.QUANTIFIER._fltk_canonical_name = "Repetition.Label.QUANTIFIER"


@dataclasses.dataclass
class Quantifier:
    class Label(enum.Enum):
        BOUND = enum.auto()
        LAZY = enum.auto()
        ONE_OR_MORE = enum.auto()
        OPTIONAL = enum.auto()
        ZERO_OR_MORE = enum.auto()
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
            "Quantifier.Label.BOUND": Label.BOUND,
            "Quantifier.Label.LAZY": Label.LAZY,
            "Quantifier.Label.ONE_OR_MORE": Label.ONE_OR_MORE,
            "Quantifier.Label.OPTIONAL": Label.OPTIONAL,
            "Quantifier.Label.ZERO_OR_MORE": Label.ZERO_OR_MORE,
        }
    )
    kind: typing.Literal[NodeKind.QUANTIFIER] = NodeKind.QUANTIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Quantifier.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Quantifier.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Quantifier) -> None:
        if not isinstance(other, Quantifier):
            msg = f"Quantifier: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, Bounded | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Quantifier: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Quantifier.Label | None:
        if label is None or isinstance(label, Quantifier.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Quantifier._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Quantifier"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Quantifier.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Quantifier.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Quantifier.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Quantifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Quantifier.Label) -> list[Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_bound(self, child: _cstp.Bounded) -> None:
        self.children.append((Quantifier.Label.BOUND, self._check_child_type_for_mutators(child)))

    def extend_bound(self, children: typing.Iterable[_cstp.Bounded]) -> None:
        self.children.extend(
            [(Quantifier.Label.BOUND, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_bound(self) -> typing.Iterator[Bounded]:
        return iter(typing.cast("list[Bounded]", self._children_snapshot(Quantifier.Label.BOUND)))

    def child_bound(self) -> Bounded:
        children = typing.cast("list[Bounded]", self._children_snapshot(Quantifier.Label.BOUND))
        if (n := len(children)) != 1:
            msg = f"Expected one bound child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_bound(self) -> Bounded | None:
        children = typing.cast("list[Bounded]", self._children_snapshot(Quantifier.Label.BOUND))
        if (n := len(children)) > 1:
            msg = f"Expected at most one bound child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_lazy(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.LAZY, self._check_child_type_for_mutators(child)))

    def extend_lazy(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Quantifier.Label.LAZY, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_lazy(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.LAZY)
            )
        )

    def child_lazy(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.LAZY)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one lazy child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_lazy(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.LAZY)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one lazy child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_one_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.ONE_OR_MORE, self._check_child_type_for_mutators(child)))

    def extend_one_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Quantifier.Label.ONE_OR_MORE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_one_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]",
                self._children_snapshot(Quantifier.Label.ONE_OR_MORE),
            )
        )

    def child_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.ONE_OR_MORE)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.ONE_OR_MORE)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_optional(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.OPTIONAL, self._check_child_type_for_mutators(child)))

    def extend_optional(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Quantifier.Label.OPTIONAL, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_optional(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.OPTIONAL)
            )
        )

    def child_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.OPTIONAL)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one optional child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.OPTIONAL)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one optional child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_zero_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.ZERO_OR_MORE, self._check_child_type_for_mutators(child)))

    def extend_zero_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Quantifier.Label.ZERO_OR_MORE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_zero_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]",
                self._children_snapshot(Quantifier.Label.ZERO_OR_MORE),
            )
        )

    def child_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.ZERO_OR_MORE)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one zero_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Quantifier.Label.ZERO_OR_MORE)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one zero_or_more child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def bound(self) -> Bounded | None:
        return self.maybe_bound()

    def lazy(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_lazy()

    def lazy_text(self) -> str | None:
        child = self.maybe_lazy()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Quantifier.lazy_text: child labelled 'lazy' is not a Span"
            raise TypeError(msg) from None

    def one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_one_or_more()

    def one_or_more_text(self) -> str | None:
        child = self.maybe_one_or_more()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Quantifier.one_or_more_text: child labelled 'one_or_more' is not a Span"
            raise TypeError(msg) from None

    def optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_optional()

    def optional_text(self) -> str | None:
        child = self.maybe_optional()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Quantifier.optional_text: child labelled 'optional' is not a Span"
            raise TypeError(msg) from None

    def zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_zero_or_more()

    def zero_or_more_text(self) -> str | None:
        child = self.maybe_zero_or_more()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Quantifier.zero_or_more_text: child labelled 'zero_or_more' is not a Span"
            raise TypeError(msg) from None


Quantifier.Label.BOUND._fltk_canonical_name = "Quantifier.Label.BOUND"
Quantifier.Label.LAZY._fltk_canonical_name = "Quantifier.Label.LAZY"
Quantifier.Label.ONE_OR_MORE._fltk_canonical_name = "Quantifier.Label.ONE_OR_MORE"
Quantifier.Label.OPTIONAL._fltk_canonical_name = "Quantifier.Label.OPTIONAL"
Quantifier.Label.ZERO_OR_MORE._fltk_canonical_name = "Quantifier.Label.ZERO_OR_MORE"


@dataclasses.dataclass
class Bounded:
    class Label(enum.Enum):
        COUNT = enum.auto()
        MAX = enum.auto()
        MIN = enum.auto()
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
        {"Bounded.Label.COUNT": Label.COUNT, "Bounded.Label.MAX": Label.MAX, "Bounded.Label.MIN": Label.MIN}
    )
    kind: typing.Literal[NodeKind.BOUNDED] = NodeKind.BOUNDED
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Number]] = dataclasses.field(default_factory=list)

    def append(self, child: _cstp.Number, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Bounded.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self, children: typing.Iterable[_cstp.Number], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Bounded.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Bounded) -> None:
        if not isinstance(other, Bounded):
            msg = f"Bounded: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Number]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Number) -> Number:
        if isinstance(child, Number):
            return child
        msg = f"Bounded: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Bounded.Label | None:
        if label is None or isinstance(label, Bounded.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Bounded._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Bounded"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.Number, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Bounded.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Number]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Bounded.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.Number, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Bounded.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Bounded.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Bounded.Label) -> list[Number]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_count(self, child: _cstp.Number) -> None:
        self.children.append((Bounded.Label.COUNT, self._check_child_type_for_mutators(child)))

    def extend_count(self, children: typing.Iterable[_cstp.Number]) -> None:
        self.children.extend([(Bounded.Label.COUNT, self._check_child_type_for_mutators(child)) for child in children])

    def children_count(self) -> typing.Iterator[Number]:
        return iter(self._children_snapshot(Bounded.Label.COUNT))

    def child_count(self) -> Number:
        children = self._children_snapshot(Bounded.Label.COUNT)
        if (n := len(children)) != 1:
            msg = f"Expected one count child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_count(self) -> Number | None:
        children = self._children_snapshot(Bounded.Label.COUNT)
        if (n := len(children)) > 1:
            msg = f"Expected at most one count child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_max(self, child: _cstp.Number) -> None:
        self.children.append((Bounded.Label.MAX, self._check_child_type_for_mutators(child)))

    def extend_max(self, children: typing.Iterable[_cstp.Number]) -> None:
        self.children.extend([(Bounded.Label.MAX, self._check_child_type_for_mutators(child)) for child in children])

    def children_max(self) -> typing.Iterator[Number]:
        return iter(self._children_snapshot(Bounded.Label.MAX))

    def child_max(self) -> Number:
        children = self._children_snapshot(Bounded.Label.MAX)
        if (n := len(children)) != 1:
            msg = f"Expected one max child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_max(self) -> Number | None:
        children = self._children_snapshot(Bounded.Label.MAX)
        if (n := len(children)) > 1:
            msg = f"Expected at most one max child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_min(self, child: _cstp.Number) -> None:
        self.children.append((Bounded.Label.MIN, self._check_child_type_for_mutators(child)))

    def extend_min(self, children: typing.Iterable[_cstp.Number]) -> None:
        self.children.extend([(Bounded.Label.MIN, self._check_child_type_for_mutators(child)) for child in children])

    def children_min(self) -> typing.Iterator[Number]:
        return iter(self._children_snapshot(Bounded.Label.MIN))

    def child_min(self) -> Number:
        children = self._children_snapshot(Bounded.Label.MIN)
        if (n := len(children)) != 1:
            msg = f"Expected one min child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_min(self) -> Number | None:
        children = self._children_snapshot(Bounded.Label.MIN)
        if (n := len(children)) > 1:
            msg = f"Expected at most one min child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def count(self) -> Number | None:
        return self.maybe_count()

    def max(self) -> Number | None:
        return self.maybe_max()

    def min(self) -> Number | None:
        return self.maybe_min()


Bounded.Label.COUNT._fltk_canonical_name = "Bounded.Label.COUNT"
Bounded.Label.MAX._fltk_canonical_name = "Bounded.Label.MAX"
Bounded.Label.MIN._fltk_canonical_name = "Bounded.Label.MIN"


@dataclasses.dataclass
class Number:
    class Label(enum.Enum):
        DIGITS = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Number.Label.DIGITS": Label.DIGITS})
    kind: typing.Literal[NodeKind.NUMBER] = NodeKind.NUMBER
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
            if label is None or isinstance(label, Number.Label)
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
            if label is None or isinstance(label, Number.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Number) -> None:
        if not isinstance(other, Number):
            msg = f"Number: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"Number: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Number.Label | None:
        if label is None or isinstance(label, Number.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Number._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Number"
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
            if label is None or isinstance(label, Number.Label)
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
            msg = f"Number.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, Number.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Number.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Number.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_digits(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Number.Label.DIGITS, self._check_child_type_for_mutators(child)))

    def extend_digits(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Number.Label.DIGITS, self._check_child_type_for_mutators(child)) for child in children])

    def children_digits(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Number.Label.DIGITS))

    def child_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Number.Label.DIGITS)
        if (n := len(children)) != 1:
            msg = f"Expected one digits child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Number.Label.DIGITS)
        if (n := len(children)) > 1:
            msg = f"Expected at most one digits child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_digits()

    def digits_text(self) -> str:
        child = self.child_digits()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Number.digits_text: child labelled 'digits' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


Number.Label.DIGITS._fltk_canonical_name = "Number.Label.DIGITS"


@dataclasses.dataclass
class Atom:
    class Label(enum.Enum):
        ANCHOR = enum.auto()
        CHAR_CLASS = enum.auto()
        DOT = enum.auto()
        ESCAPE = enum.auto()
        GROUP = enum.auto()
        INLINE_FLAGS = enum.auto()
        LITERAL_CHAR = enum.auto()
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
            "Atom.Label.ANCHOR": Label.ANCHOR,
            "Atom.Label.CHAR_CLASS": Label.CHAR_CLASS,
            "Atom.Label.DOT": Label.DOT,
            "Atom.Label.ESCAPE": Label.ESCAPE,
            "Atom.Label.GROUP": Label.GROUP,
            "Atom.Label.INLINE_FLAGS": Label.INLINE_FLAGS,
            "Atom.Label.LITERAL_CHAR": Label.LITERAL_CHAR,
        }
    )
    kind: typing.Literal[NodeKind.ATOM] = NodeKind.ATOM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.Anchor
        | _cstp.CharClass
        | _cstp.Dot
        | _cstp.Escape
        | _cstp.Group
        | _cstp.InlineFlags
        | _cstp.LiteralChar,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Atom.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[
            _cstp.Anchor
            | _cstp.CharClass
            | _cstp.Dot
            | _cstp.Escape
            | _cstp.Group
            | _cstp.InlineFlags
            | _cstp.LiteralChar
        ],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Atom.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Atom) -> None:
        if not isinstance(other, Atom):
            msg = f"Atom: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self,
        child: _cstp.Anchor
        | _cstp.CharClass
        | _cstp.Dot
        | _cstp.Escape
        | _cstp.Group
        | _cstp.InlineFlags
        | _cstp.LiteralChar,
    ) -> Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar:
        if isinstance(child, Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar):
            return child
        msg = f"Atom: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Atom.Label | None:
        if label is None or isinstance(label, Atom.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Atom._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Atom"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Anchor
        | _cstp.CharClass
        | _cstp.Dot
        | _cstp.Escape
        | _cstp.Group
        | _cstp.InlineFlags
        | _cstp.LiteralChar,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Atom.Label)
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
    ) -> tuple[Label | None, Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Atom.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Anchor
        | _cstp.CharClass
        | _cstp.Dot
        | _cstp.Escape
        | _cstp.Group
        | _cstp.InlineFlags
        | _cstp.LiteralChar,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Atom.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Atom.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: Atom.Label
    ) -> list[Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor(self, child: _cstp.Anchor) -> None:
        self.children.append((Atom.Label.ANCHOR, self._check_child_type_for_mutators(child)))

    def extend_anchor(self, children: typing.Iterable[_cstp.Anchor]) -> None:
        self.children.extend([(Atom.Label.ANCHOR, self._check_child_type_for_mutators(child)) for child in children])

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return iter(typing.cast("list[Anchor]", self._children_snapshot(Atom.Label.ANCHOR)))

    def child_anchor(self) -> Anchor:
        children = typing.cast("list[Anchor]", self._children_snapshot(Atom.Label.ANCHOR))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor(self) -> Anchor | None:
        children = typing.cast("list[Anchor]", self._children_snapshot(Atom.Label.ANCHOR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_char_class(self, child: _cstp.CharClass) -> None:
        self.children.append((Atom.Label.CHAR_CLASS, self._check_child_type_for_mutators(child)))

    def extend_char_class(self, children: typing.Iterable[_cstp.CharClass]) -> None:
        self.children.extend(
            [(Atom.Label.CHAR_CLASS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_char_class(self) -> typing.Iterator[CharClass]:
        return iter(typing.cast("list[CharClass]", self._children_snapshot(Atom.Label.CHAR_CLASS)))

    def child_char_class(self) -> CharClass:
        children = typing.cast("list[CharClass]", self._children_snapshot(Atom.Label.CHAR_CLASS))
        if (n := len(children)) != 1:
            msg = f"Expected one char_class child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_char_class(self) -> CharClass | None:
        children = typing.cast("list[CharClass]", self._children_snapshot(Atom.Label.CHAR_CLASS))
        if (n := len(children)) > 1:
            msg = f"Expected at most one char_class child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_dot(self, child: _cstp.Dot) -> None:
        self.children.append((Atom.Label.DOT, self._check_child_type_for_mutators(child)))

    def extend_dot(self, children: typing.Iterable[_cstp.Dot]) -> None:
        self.children.extend([(Atom.Label.DOT, self._check_child_type_for_mutators(child)) for child in children])

    def children_dot(self) -> typing.Iterator[Dot]:
        return iter(typing.cast("list[Dot]", self._children_snapshot(Atom.Label.DOT)))

    def child_dot(self) -> Dot:
        children = typing.cast("list[Dot]", self._children_snapshot(Atom.Label.DOT))
        if (n := len(children)) != 1:
            msg = f"Expected one dot child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_dot(self) -> Dot | None:
        children = typing.cast("list[Dot]", self._children_snapshot(Atom.Label.DOT))
        if (n := len(children)) > 1:
            msg = f"Expected at most one dot child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_escape(self, child: _cstp.Escape) -> None:
        self.children.append((Atom.Label.ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_escape(self, children: typing.Iterable[_cstp.Escape]) -> None:
        self.children.extend([(Atom.Label.ESCAPE, self._check_child_type_for_mutators(child)) for child in children])

    def children_escape(self) -> typing.Iterator[Escape]:
        return iter(typing.cast("list[Escape]", self._children_snapshot(Atom.Label.ESCAPE)))

    def child_escape(self) -> Escape:
        children = typing.cast("list[Escape]", self._children_snapshot(Atom.Label.ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_escape(self) -> Escape | None:
        children = typing.cast("list[Escape]", self._children_snapshot(Atom.Label.ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: _cstp.Group) -> None:
        self.children.append((Atom.Label.GROUP, self._check_child_type_for_mutators(child)))

    def extend_group(self, children: typing.Iterable[_cstp.Group]) -> None:
        self.children.extend([(Atom.Label.GROUP, self._check_child_type_for_mutators(child)) for child in children])

    def children_group(self) -> typing.Iterator[Group]:
        return iter(typing.cast("list[Group]", self._children_snapshot(Atom.Label.GROUP)))

    def child_group(self) -> Group:
        children = typing.cast("list[Group]", self._children_snapshot(Atom.Label.GROUP))
        if (n := len(children)) != 1:
            msg = f"Expected one group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_group(self) -> Group | None:
        children = typing.cast("list[Group]", self._children_snapshot(Atom.Label.GROUP))
        if (n := len(children)) > 1:
            msg = f"Expected at most one group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_inline_flags(self, child: _cstp.InlineFlags) -> None:
        self.children.append((Atom.Label.INLINE_FLAGS, self._check_child_type_for_mutators(child)))

    def extend_inline_flags(self, children: typing.Iterable[_cstp.InlineFlags]) -> None:
        self.children.extend(
            [(Atom.Label.INLINE_FLAGS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_inline_flags(self) -> typing.Iterator[InlineFlags]:
        return iter(typing.cast("list[InlineFlags]", self._children_snapshot(Atom.Label.INLINE_FLAGS)))

    def child_inline_flags(self) -> InlineFlags:
        children = typing.cast("list[InlineFlags]", self._children_snapshot(Atom.Label.INLINE_FLAGS))
        if (n := len(children)) != 1:
            msg = f"Expected one inline_flags child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_inline_flags(self) -> InlineFlags | None:
        children = typing.cast("list[InlineFlags]", self._children_snapshot(Atom.Label.INLINE_FLAGS))
        if (n := len(children)) > 1:
            msg = f"Expected at most one inline_flags child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_literal_char(self, child: _cstp.LiteralChar) -> None:
        self.children.append((Atom.Label.LITERAL_CHAR, self._check_child_type_for_mutators(child)))

    def extend_literal_char(self, children: typing.Iterable[_cstp.LiteralChar]) -> None:
        self.children.extend(
            [(Atom.Label.LITERAL_CHAR, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_literal_char(self) -> typing.Iterator[LiteralChar]:
        return iter(typing.cast("list[LiteralChar]", self._children_snapshot(Atom.Label.LITERAL_CHAR)))

    def child_literal_char(self) -> LiteralChar:
        children = typing.cast("list[LiteralChar]", self._children_snapshot(Atom.Label.LITERAL_CHAR))
        if (n := len(children)) != 1:
            msg = f"Expected one literal_char child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_literal_char(self) -> LiteralChar | None:
        children = typing.cast("list[LiteralChar]", self._children_snapshot(Atom.Label.LITERAL_CHAR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one literal_char child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def anchor(self) -> Anchor | None:
        return self.maybe_anchor()

    def char_class(self) -> CharClass | None:
        return self.maybe_char_class()

    def dot(self) -> Dot | None:
        return self.maybe_dot()

    def escape(self) -> Escape | None:
        return self.maybe_escape()

    def group(self) -> Group | None:
        return self.maybe_group()

    def inline_flags(self) -> InlineFlags | None:
        return self.maybe_inline_flags()

    def literal_char(self) -> LiteralChar | None:
        return self.maybe_literal_char()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Atom.variant: node has no labeled child"
        raise ValueError(msg)


Atom.Label.ANCHOR._fltk_canonical_name = "Atom.Label.ANCHOR"
Atom.Label.CHAR_CLASS._fltk_canonical_name = "Atom.Label.CHAR_CLASS"
Atom.Label.DOT._fltk_canonical_name = "Atom.Label.DOT"
Atom.Label.ESCAPE._fltk_canonical_name = "Atom.Label.ESCAPE"
Atom.Label.GROUP._fltk_canonical_name = "Atom.Label.GROUP"
Atom.Label.INLINE_FLAGS._fltk_canonical_name = "Atom.Label.INLINE_FLAGS"
Atom.Label.LITERAL_CHAR._fltk_canonical_name = "Atom.Label.LITERAL_CHAR"


@dataclasses.dataclass
class Dot:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Dot.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.DOT] = NodeKind.DOT
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
            if label is None or isinstance(label, Dot.Label)
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
            if label is None or isinstance(label, Dot.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Dot) -> None:
        if not isinstance(other, Dot):
            msg = f"Dot: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"Dot: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Dot.Label | None:
        if label is None or isinstance(label, Dot.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Dot._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Dot"
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
            if label is None or isinstance(label, Dot.Label)
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
            msg = f"Dot.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, Dot.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Dot.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Dot.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Dot.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Dot.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children])

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Dot.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Dot.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Dot.Label.VALUE)
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
            msg = "Dot.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


Dot.Label.VALUE._fltk_canonical_name = "Dot.Label.VALUE"


@dataclasses.dataclass
class Anchor:
    class Label(enum.Enum):
        CARET = enum.auto()
        DOLLAR = enum.auto()
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
        {"Anchor.Label.CARET": Label.CARET, "Anchor.Label.DOLLAR": Label.DOLLAR}
    )
    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
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
            if label is None or isinstance(label, Anchor.Label)
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
            if label is None or isinstance(label, Anchor.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Anchor) -> None:
        if not isinstance(other, Anchor):
            msg = f"Anchor: unsupported child type {_type_name_for_error(other)}"
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
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
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

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
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
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
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

    def _children_snapshot(self, label: Anchor.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_caret(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Anchor.Label.CARET, self._check_child_type_for_mutators(child)))

    def extend_caret(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Anchor.Label.CARET, self._check_child_type_for_mutators(child)) for child in children])

    def children_caret(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Anchor.Label.CARET))

    def child_caret(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Anchor.Label.CARET)
        if (n := len(children)) != 1:
            msg = f"Expected one caret child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_caret(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Anchor.Label.CARET)
        if (n := len(children)) > 1:
            msg = f"Expected at most one caret child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_dollar(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Anchor.Label.DOLLAR, self._check_child_type_for_mutators(child)))

    def extend_dollar(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Anchor.Label.DOLLAR, self._check_child_type_for_mutators(child)) for child in children])

    def children_dollar(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Anchor.Label.DOLLAR))

    def child_dollar(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Anchor.Label.DOLLAR)
        if (n := len(children)) != 1:
            msg = f"Expected one dollar child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_dollar(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Anchor.Label.DOLLAR)
        if (n := len(children)) > 1:
            msg = f"Expected at most one dollar child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def caret(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_caret()

    def caret_text(self) -> str | None:
        child = self.maybe_caret()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Anchor.caret_text: child labelled 'caret' is not a Span"
            raise TypeError(msg) from None

    def dollar(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_dollar()

    def dollar_text(self) -> str | None:
        child = self.maybe_dollar()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Anchor.dollar_text: child labelled 'dollar' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Anchor.variant: node has no labeled child"
        raise ValueError(msg)


Anchor.Label.CARET._fltk_canonical_name = "Anchor.Label.CARET"
Anchor.Label.DOLLAR._fltk_canonical_name = "Anchor.Label.DOLLAR"


@dataclasses.dataclass
class Group:
    class Label(enum.Enum):
        CAPTURING = enum.auto()
        FLAG_GROUP = enum.auto()
        NON_CAPTURING = enum.auto()
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
            "Group.Label.CAPTURING": Label.CAPTURING,
            "Group.Label.FLAG_GROUP": Label.FLAG_GROUP,
            "Group.Label.NON_CAPTURING": Label.NON_CAPTURING,
        }
    )
    kind: typing.Literal[NodeKind.GROUP] = NodeKind.GROUP
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Capturing | FlagGroup | NonCapturing]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Capturing | _cstp.FlagGroup | _cstp.NonCapturing,
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
        children: typing.Iterable[_cstp.Capturing | _cstp.FlagGroup | _cstp.NonCapturing],
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

    def child(self) -> tuple[Label | None, Capturing | FlagGroup | NonCapturing]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Capturing | _cstp.FlagGroup | _cstp.NonCapturing
    ) -> Capturing | FlagGroup | NonCapturing:
        if isinstance(child, Capturing | FlagGroup | NonCapturing):
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
        child: _cstp.Capturing | _cstp.FlagGroup | _cstp.NonCapturing,
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

    def remove_at(self, index: int) -> tuple[Label | None, Capturing | FlagGroup | NonCapturing]:
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
        child: _cstp.Capturing | _cstp.FlagGroup | _cstp.NonCapturing,
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

    def _children_snapshot(self, label: Group.Label) -> list[Capturing | FlagGroup | NonCapturing]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_capturing(self, child: _cstp.Capturing) -> None:
        self.children.append((Group.Label.CAPTURING, self._check_child_type_for_mutators(child)))

    def extend_capturing(self, children: typing.Iterable[_cstp.Capturing]) -> None:
        self.children.extend(
            [(Group.Label.CAPTURING, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_capturing(self) -> typing.Iterator[Capturing]:
        return iter(typing.cast("list[Capturing]", self._children_snapshot(Group.Label.CAPTURING)))

    def child_capturing(self) -> Capturing:
        children = typing.cast("list[Capturing]", self._children_snapshot(Group.Label.CAPTURING))
        if (n := len(children)) != 1:
            msg = f"Expected one capturing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_capturing(self) -> Capturing | None:
        children = typing.cast("list[Capturing]", self._children_snapshot(Group.Label.CAPTURING))
        if (n := len(children)) > 1:
            msg = f"Expected at most one capturing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_flag_group(self, child: _cstp.FlagGroup) -> None:
        self.children.append((Group.Label.FLAG_GROUP, self._check_child_type_for_mutators(child)))

    def extend_flag_group(self, children: typing.Iterable[_cstp.FlagGroup]) -> None:
        self.children.extend(
            [(Group.Label.FLAG_GROUP, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_flag_group(self) -> typing.Iterator[FlagGroup]:
        return iter(typing.cast("list[FlagGroup]", self._children_snapshot(Group.Label.FLAG_GROUP)))

    def child_flag_group(self) -> FlagGroup:
        children = typing.cast("list[FlagGroup]", self._children_snapshot(Group.Label.FLAG_GROUP))
        if (n := len(children)) != 1:
            msg = f"Expected one flag_group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_flag_group(self) -> FlagGroup | None:
        children = typing.cast("list[FlagGroup]", self._children_snapshot(Group.Label.FLAG_GROUP))
        if (n := len(children)) > 1:
            msg = f"Expected at most one flag_group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_non_capturing(self, child: _cstp.NonCapturing) -> None:
        self.children.append((Group.Label.NON_CAPTURING, self._check_child_type_for_mutators(child)))

    def extend_non_capturing(self, children: typing.Iterable[_cstp.NonCapturing]) -> None:
        self.children.extend(
            [(Group.Label.NON_CAPTURING, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_non_capturing(self) -> typing.Iterator[NonCapturing]:
        return iter(typing.cast("list[NonCapturing]", self._children_snapshot(Group.Label.NON_CAPTURING)))

    def child_non_capturing(self) -> NonCapturing:
        children = typing.cast("list[NonCapturing]", self._children_snapshot(Group.Label.NON_CAPTURING))
        if (n := len(children)) != 1:
            msg = f"Expected one non_capturing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_non_capturing(self) -> NonCapturing | None:
        children = typing.cast("list[NonCapturing]", self._children_snapshot(Group.Label.NON_CAPTURING))
        if (n := len(children)) > 1:
            msg = f"Expected at most one non_capturing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def capturing(self) -> Capturing | None:
        return self.maybe_capturing()

    def flag_group(self) -> FlagGroup | None:
        return self.maybe_flag_group()

    def non_capturing(self) -> NonCapturing | None:
        return self.maybe_non_capturing()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "Group.variant: node has no labeled child"
        raise ValueError(msg)


Group.Label.CAPTURING._fltk_canonical_name = "Group.Label.CAPTURING"
Group.Label.FLAG_GROUP._fltk_canonical_name = "Group.Label.FLAG_GROUP"
Group.Label.NON_CAPTURING._fltk_canonical_name = "Group.Label.NON_CAPTURING"


@dataclasses.dataclass
class NonCapturing:
    class Label(enum.Enum):
        BODY = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"NonCapturing.Label.BODY": Label.BODY})
    kind: typing.Literal[NodeKind.NONCAPTURING] = NodeKind.NONCAPTURING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, NonCapturing.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Alternation],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, NonCapturing.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.NonCapturing) -> None:
        if not isinstance(other, NonCapturing):
            msg = f"NonCapturing: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Alternation) -> Alternation:
        if isinstance(child, Alternation):
            return child
        msg = f"NonCapturing: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> NonCapturing.Label | None:
        if label is None or isinstance(label, NonCapturing.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = NonCapturing._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "NonCapturing"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, NonCapturing.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Alternation]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NonCapturing.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, NonCapturing.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NonCapturing.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: NonCapturing.Label) -> list[Alternation]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_body(self, child: _cstp.Alternation) -> None:
        self.children.append((NonCapturing.Label.BODY, self._check_child_type_for_mutators(child)))

    def extend_body(self, children: typing.Iterable[_cstp.Alternation]) -> None:
        self.children.extend(
            [(NonCapturing.Label.BODY, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_body(self) -> typing.Iterator[Alternation]:
        return iter(self._children_snapshot(NonCapturing.Label.BODY))

    def child_body(self) -> Alternation:
        children = self._children_snapshot(NonCapturing.Label.BODY)
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> Alternation | None:
        children = self._children_snapshot(NonCapturing.Label.BODY)
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def body(self) -> Alternation:
        return self.child_body()


NonCapturing.Label.BODY._fltk_canonical_name = "NonCapturing.Label.BODY"


@dataclasses.dataclass
class FlagGroup:
    class Label(enum.Enum):
        BODY = enum.auto()
        FLAGS = enum.auto()
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
        {"FlagGroup.Label.BODY": Label.BODY, "FlagGroup.Label.FLAGS": Label.FLAGS}
    )
    kind: typing.Literal[NodeKind.FLAGGROUP] = NodeKind.FLAGGROUP
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation | FlagChars]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Alternation | _cstp.FlagChars,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FlagGroup.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Alternation | _cstp.FlagChars],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FlagGroup.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.FlagGroup) -> None:
        if not isinstance(other, FlagGroup):
            msg = f"FlagGroup: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation | FlagChars]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Alternation | _cstp.FlagChars) -> Alternation | FlagChars:
        if isinstance(child, Alternation | FlagChars):
            return child
        msg = f"FlagGroup: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> FlagGroup.Label | None:
        if label is None or isinstance(label, FlagGroup.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = FlagGroup._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "FlagGroup"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Alternation | _cstp.FlagChars,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FlagGroup.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Alternation | FlagChars]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FlagGroup.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Alternation | _cstp.FlagChars,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, FlagGroup.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FlagGroup.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: FlagGroup.Label) -> list[Alternation | FlagChars]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_body(self, child: _cstp.Alternation) -> None:
        self.children.append((FlagGroup.Label.BODY, self._check_child_type_for_mutators(child)))

    def extend_body(self, children: typing.Iterable[_cstp.Alternation]) -> None:
        self.children.extend([(FlagGroup.Label.BODY, self._check_child_type_for_mutators(child)) for child in children])

    def children_body(self) -> typing.Iterator[Alternation]:
        return iter(typing.cast("list[Alternation]", self._children_snapshot(FlagGroup.Label.BODY)))

    def child_body(self) -> Alternation:
        children = typing.cast("list[Alternation]", self._children_snapshot(FlagGroup.Label.BODY))
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> Alternation | None:
        children = typing.cast("list[Alternation]", self._children_snapshot(FlagGroup.Label.BODY))
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_flags(self, child: _cstp.FlagChars) -> None:
        self.children.append((FlagGroup.Label.FLAGS, self._check_child_type_for_mutators(child)))

    def extend_flags(self, children: typing.Iterable[_cstp.FlagChars]) -> None:
        self.children.extend(
            [(FlagGroup.Label.FLAGS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_flags(self) -> typing.Iterator[FlagChars]:
        return iter(typing.cast("list[FlagChars]", self._children_snapshot(FlagGroup.Label.FLAGS)))

    def child_flags(self) -> FlagChars:
        children = typing.cast("list[FlagChars]", self._children_snapshot(FlagGroup.Label.FLAGS))
        if (n := len(children)) != 1:
            msg = f"Expected one flags child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_flags(self) -> FlagChars | None:
        children = typing.cast("list[FlagChars]", self._children_snapshot(FlagGroup.Label.FLAGS))
        if (n := len(children)) > 1:
            msg = f"Expected at most one flags child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def body(self) -> Alternation:
        return self.child_body()

    def flags(self) -> FlagChars:
        return self.child_flags()


FlagGroup.Label.BODY._fltk_canonical_name = "FlagGroup.Label.BODY"
FlagGroup.Label.FLAGS._fltk_canonical_name = "FlagGroup.Label.FLAGS"


@dataclasses.dataclass
class Capturing:
    class Label(enum.Enum):
        BODY = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Capturing.Label.BODY": Label.BODY})
    kind: typing.Literal[NodeKind.CAPTURING] = NodeKind.CAPTURING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Capturing.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Alternation],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Capturing.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Capturing) -> None:
        if not isinstance(other, Capturing):
            msg = f"Capturing: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Alternation) -> Alternation:
        if isinstance(child, Alternation):
            return child
        msg = f"Capturing: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Capturing.Label | None:
        if label is None or isinstance(label, Capturing.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Capturing._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Capturing"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Capturing.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, Alternation]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Capturing.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Capturing.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Capturing.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Capturing.Label) -> list[Alternation]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_body(self, child: _cstp.Alternation) -> None:
        self.children.append((Capturing.Label.BODY, self._check_child_type_for_mutators(child)))

    def extend_body(self, children: typing.Iterable[_cstp.Alternation]) -> None:
        self.children.extend([(Capturing.Label.BODY, self._check_child_type_for_mutators(child)) for child in children])

    def children_body(self) -> typing.Iterator[Alternation]:
        return iter(self._children_snapshot(Capturing.Label.BODY))

    def child_body(self) -> Alternation:
        children = self._children_snapshot(Capturing.Label.BODY)
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> Alternation | None:
        children = self._children_snapshot(Capturing.Label.BODY)
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def body(self) -> Alternation:
        return self.child_body()


Capturing.Label.BODY._fltk_canonical_name = "Capturing.Label.BODY"


@dataclasses.dataclass
class InlineFlags:
    class Label(enum.Enum):
        FLAGS = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"InlineFlags.Label.FLAGS": Label.FLAGS})
    kind: typing.Literal[NodeKind.INLINEFLAGS] = NodeKind.INLINEFLAGS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FlagChars]] = dataclasses.field(default_factory=list)

    def append(self, child: _cstp.FlagChars, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, InlineFlags.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.FlagChars],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, InlineFlags.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.InlineFlags) -> None:
        if not isinstance(other, InlineFlags):
            msg = f"InlineFlags: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, FlagChars]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.FlagChars) -> FlagChars:
        if isinstance(child, FlagChars):
            return child
        msg = f"InlineFlags: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> InlineFlags.Label | None:
        if label is None or isinstance(label, InlineFlags.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = InlineFlags._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "InlineFlags"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.FlagChars, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, InlineFlags.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, FlagChars]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"InlineFlags.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.FlagChars, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, InlineFlags.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"InlineFlags.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: InlineFlags.Label) -> list[FlagChars]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_flags(self, child: _cstp.FlagChars) -> None:
        self.children.append((InlineFlags.Label.FLAGS, self._check_child_type_for_mutators(child)))

    def extend_flags(self, children: typing.Iterable[_cstp.FlagChars]) -> None:
        self.children.extend(
            [(InlineFlags.Label.FLAGS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_flags(self) -> typing.Iterator[FlagChars]:
        return iter(self._children_snapshot(InlineFlags.Label.FLAGS))

    def child_flags(self) -> FlagChars:
        children = self._children_snapshot(InlineFlags.Label.FLAGS)
        if (n := len(children)) != 1:
            msg = f"Expected one flags child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_flags(self) -> FlagChars | None:
        children = self._children_snapshot(InlineFlags.Label.FLAGS)
        if (n := len(children)) > 1:
            msg = f"Expected at most one flags child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def flags(self) -> FlagChars:
        return self.child_flags()


InlineFlags.Label.FLAGS._fltk_canonical_name = "InlineFlags.Label.FLAGS"


@dataclasses.dataclass
class FlagChars:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"FlagChars.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.FLAGCHARS] = NodeKind.FLAGCHARS
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
            if label is None or isinstance(label, FlagChars.Label)
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
            if label is None or isinstance(label, FlagChars.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.FlagChars) -> None:
        if not isinstance(other, FlagChars):
            msg = f"FlagChars: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"FlagChars: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> FlagChars.Label | None:
        if label is None or isinstance(label, FlagChars.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = FlagChars._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "FlagChars"
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
            if label is None or isinstance(label, FlagChars.Label)
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
            msg = f"FlagChars.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, FlagChars.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FlagChars.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: FlagChars.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((FlagChars.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(FlagChars.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(FlagChars.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(FlagChars.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(FlagChars.Label.VALUE)
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
            msg = "FlagChars.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


FlagChars.Label.VALUE._fltk_canonical_name = "FlagChars.Label.VALUE"


@dataclasses.dataclass
class CharClass:
    class Label(enum.Enum):
        CLASS_BODY = enum.auto()
        NEGATED = enum.auto()
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
        {"CharClass.Label.CLASS_BODY": Label.CLASS_BODY, "CharClass.Label.NEGATED": Label.NEGATED}
    )
    kind: typing.Literal[NodeKind.CHARCLASS] = NodeKind.CHARCLASS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CharClass.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CharClass.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.CharClass) -> None:
        if not isinstance(other, CharClass):
            msg = f"CharClass: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, ClassBody | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"CharClass: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> CharClass.Label | None:
        if label is None or isinstance(label, CharClass.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = CharClass._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "CharClass"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CharClass.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CharClass.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CharClass.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CharClass.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: CharClass.Label
    ) -> list[ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_class_body(self, child: _cstp.ClassBody) -> None:
        self.children.append((CharClass.Label.CLASS_BODY, self._check_child_type_for_mutators(child)))

    def extend_class_body(self, children: typing.Iterable[_cstp.ClassBody]) -> None:
        self.children.extend(
            [(CharClass.Label.CLASS_BODY, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_class_body(self) -> typing.Iterator[ClassBody]:
        return iter(typing.cast("list[ClassBody]", self._children_snapshot(CharClass.Label.CLASS_BODY)))

    def child_class_body(self) -> ClassBody:
        children = typing.cast("list[ClassBody]", self._children_snapshot(CharClass.Label.CLASS_BODY))
        if (n := len(children)) != 1:
            msg = f"Expected one class_body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_body(self) -> ClassBody | None:
        children = typing.cast("list[ClassBody]", self._children_snapshot(CharClass.Label.CLASS_BODY))
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_negated(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((CharClass.Label.NEGATED, self._check_child_type_for_mutators(child)))

    def extend_negated(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(CharClass.Label.NEGATED, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_negated(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(CharClass.Label.NEGATED)
            )
        )

    def child_negated(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(CharClass.Label.NEGATED)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one negated child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_negated(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(CharClass.Label.NEGATED)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one negated child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def class_body(self) -> ClassBody:
        return self.child_class_body()

    def negated(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_negated()

    def negated_text(self) -> str | None:
        child = self.maybe_negated()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "CharClass.negated_text: child labelled 'negated' is not a Span"
            raise TypeError(msg) from None


CharClass.Label.CLASS_BODY._fltk_canonical_name = "CharClass.Label.CLASS_BODY"
CharClass.Label.NEGATED._fltk_canonical_name = "CharClass.Label.NEGATED"


@dataclasses.dataclass
class ClassBody:
    class Label(enum.Enum):
        ITEMS = enum.auto()
        LEAD_DASH = enum.auto()
        TRAIL_DASH = enum.auto()
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
            "ClassBody.Label.ITEMS": Label.ITEMS,
            "ClassBody.Label.LEAD_DASH": Label.LEAD_DASH,
            "ClassBody.Label.TRAIL_DASH": Label.TRAIL_DASH,
        }
    )
    kind: typing.Literal[NodeKind.CLASSBODY] = NodeKind.CLASSBODY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassBody.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassBody.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassBody) -> None:
        if not isinstance(other, ClassBody):
            msg = f"ClassBody: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, ClassItem | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"ClassBody: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassBody.Label | None:
        if label is None or isinstance(label, ClassBody.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassBody._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassBody"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassBody.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassBody.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassBody.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassBody.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: ClassBody.Label
    ) -> list[ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_items(self, child: _cstp.ClassItem) -> None:
        self.children.append((ClassBody.Label.ITEMS, self._check_child_type_for_mutators(child)))

    def extend_items(self, children: typing.Iterable[_cstp.ClassItem]) -> None:
        self.children.extend(
            [(ClassBody.Label.ITEMS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_items(self) -> typing.Iterator[ClassItem]:
        return iter(typing.cast("list[ClassItem]", self._children_snapshot(ClassBody.Label.ITEMS)))

    def child_items(self) -> ClassItem:
        children = typing.cast("list[ClassItem]", self._children_snapshot(ClassBody.Label.ITEMS))
        if (n := len(children)) != 1:
            msg = f"Expected one items child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_items(self) -> ClassItem | None:
        children = typing.cast("list[ClassItem]", self._children_snapshot(ClassBody.Label.ITEMS))
        if (n := len(children)) > 1:
            msg = f"Expected at most one items child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_lead_dash(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ClassBody.Label.LEAD_DASH, self._check_child_type_for_mutators(child)))

    def extend_lead_dash(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(ClassBody.Label.LEAD_DASH, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_lead_dash(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(ClassBody.Label.LEAD_DASH)
            )
        )

    def child_lead_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(ClassBody.Label.LEAD_DASH)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one lead_dash child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_lead_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(ClassBody.Label.LEAD_DASH)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one lead_dash child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_trail_dash(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ClassBody.Label.TRAIL_DASH, self._check_child_type_for_mutators(child)))

    def extend_trail_dash(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(ClassBody.Label.TRAIL_DASH, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_trail_dash(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast(
                "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(ClassBody.Label.TRAIL_DASH)
            )
        )

    def child_trail_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(ClassBody.Label.TRAIL_DASH)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one trail_dash child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_trail_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(ClassBody.Label.TRAIL_DASH)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one trail_dash child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def items(self) -> list[ClassItem]:
        return typing.cast("list[ClassItem]", self._children_snapshot(ClassBody.Label.ITEMS))

    def lead_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_lead_dash()

    def lead_dash_text(self) -> str | None:
        child = self.maybe_lead_dash()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "ClassBody.lead_dash_text: child labelled 'lead_dash' is not a Span"
            raise TypeError(msg) from None

    def trail_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        return self.maybe_trail_dash()

    def trail_dash_text(self) -> str | None:
        child = self.maybe_trail_dash()
        if child is None:
            return None
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "ClassBody.trail_dash_text: child labelled 'trail_dash' is not a Span"
            raise TypeError(msg) from None


ClassBody.Label.ITEMS._fltk_canonical_name = "ClassBody.Label.ITEMS"
ClassBody.Label.LEAD_DASH._fltk_canonical_name = "ClassBody.Label.LEAD_DASH"
ClassBody.Label.TRAIL_DASH._fltk_canonical_name = "ClassBody.Label.TRAIL_DASH"


@dataclasses.dataclass
class ClassItem:
    class Label(enum.Enum):
        CLASS_MEMBER = enum.auto()
        CLASS_RANGE = enum.auto()
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
        {"ClassItem.Label.CLASS_MEMBER": Label.CLASS_MEMBER, "ClassItem.Label.CLASS_RANGE": Label.CLASS_RANGE}
    )
    kind: typing.Literal[NodeKind.CLASSITEM] = NodeKind.CLASSITEM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassMember | ClassRange]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.ClassMember | _cstp.ClassRange,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassItem.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.ClassMember | _cstp.ClassRange],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassItem.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassItem) -> None:
        if not isinstance(other, ClassItem):
            msg = f"ClassItem: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassMember | ClassRange]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.ClassMember | _cstp.ClassRange) -> ClassMember | ClassRange:
        if isinstance(child, ClassMember | ClassRange):
            return child
        msg = f"ClassItem: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassItem.Label | None:
        if label is None or isinstance(label, ClassItem.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassItem._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassItem"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.ClassMember | _cstp.ClassRange,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassItem.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, ClassMember | ClassRange]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassItem.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.ClassMember | _cstp.ClassRange,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassItem.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassItem.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ClassItem.Label) -> list[ClassMember | ClassRange]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_class_member(self, child: _cstp.ClassMember) -> None:
        self.children.append((ClassItem.Label.CLASS_MEMBER, self._check_child_type_for_mutators(child)))

    def extend_class_member(self, children: typing.Iterable[_cstp.ClassMember]) -> None:
        self.children.extend(
            [(ClassItem.Label.CLASS_MEMBER, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_class_member(self) -> typing.Iterator[ClassMember]:
        return iter(typing.cast("list[ClassMember]", self._children_snapshot(ClassItem.Label.CLASS_MEMBER)))

    def child_class_member(self) -> ClassMember:
        children = typing.cast("list[ClassMember]", self._children_snapshot(ClassItem.Label.CLASS_MEMBER))
        if (n := len(children)) != 1:
            msg = f"Expected one class_member child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_member(self) -> ClassMember | None:
        children = typing.cast("list[ClassMember]", self._children_snapshot(ClassItem.Label.CLASS_MEMBER))
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_member child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_range(self, child: _cstp.ClassRange) -> None:
        self.children.append((ClassItem.Label.CLASS_RANGE, self._check_child_type_for_mutators(child)))

    def extend_class_range(self, children: typing.Iterable[_cstp.ClassRange]) -> None:
        self.children.extend(
            [(ClassItem.Label.CLASS_RANGE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_class_range(self) -> typing.Iterator[ClassRange]:
        return iter(typing.cast("list[ClassRange]", self._children_snapshot(ClassItem.Label.CLASS_RANGE)))

    def child_class_range(self) -> ClassRange:
        children = typing.cast("list[ClassRange]", self._children_snapshot(ClassItem.Label.CLASS_RANGE))
        if (n := len(children)) != 1:
            msg = f"Expected one class_range child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_range(self) -> ClassRange | None:
        children = typing.cast("list[ClassRange]", self._children_snapshot(ClassItem.Label.CLASS_RANGE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_range child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def class_member(self) -> ClassMember | None:
        return self.maybe_class_member()

    def class_range(self) -> ClassRange | None:
        return self.maybe_class_range()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "ClassItem.variant: node has no labeled child"
        raise ValueError(msg)


ClassItem.Label.CLASS_MEMBER._fltk_canonical_name = "ClassItem.Label.CLASS_MEMBER"
ClassItem.Label.CLASS_RANGE._fltk_canonical_name = "ClassItem.Label.CLASS_RANGE"


@dataclasses.dataclass
class ClassRange:
    class Label(enum.Enum):
        HI = enum.auto()
        LO = enum.auto()
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
        {"ClassRange.Label.HI": Label.HI, "ClassRange.Label.LO": Label.LO}
    )
    kind: typing.Literal[NodeKind.CLASSRANGE] = NodeKind.CLASSRANGE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassRangeAtom]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.ClassRangeAtom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassRange.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.ClassRangeAtom],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassRange.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassRange) -> None:
        if not isinstance(other, ClassRange):
            msg = f"ClassRange: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassRangeAtom]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.ClassRangeAtom) -> ClassRangeAtom:
        if isinstance(child, ClassRangeAtom):
            return child
        msg = f"ClassRange: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassRange.Label | None:
        if label is None or isinstance(label, ClassRange.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassRange._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassRange"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.ClassRangeAtom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassRange.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, ClassRangeAtom]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassRange.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.ClassRangeAtom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassRange.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassRange.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ClassRange.Label) -> list[ClassRangeAtom]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_hi(self, child: _cstp.ClassRangeAtom) -> None:
        self.children.append((ClassRange.Label.HI, self._check_child_type_for_mutators(child)))

    def extend_hi(self, children: typing.Iterable[_cstp.ClassRangeAtom]) -> None:
        self.children.extend([(ClassRange.Label.HI, self._check_child_type_for_mutators(child)) for child in children])

    def children_hi(self) -> typing.Iterator[ClassRangeAtom]:
        return iter(self._children_snapshot(ClassRange.Label.HI))

    def child_hi(self) -> ClassRangeAtom:
        children = self._children_snapshot(ClassRange.Label.HI)
        if (n := len(children)) != 1:
            msg = f"Expected one hi child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_hi(self) -> ClassRangeAtom | None:
        children = self._children_snapshot(ClassRange.Label.HI)
        if (n := len(children)) > 1:
            msg = f"Expected at most one hi child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_lo(self, child: _cstp.ClassRangeAtom) -> None:
        self.children.append((ClassRange.Label.LO, self._check_child_type_for_mutators(child)))

    def extend_lo(self, children: typing.Iterable[_cstp.ClassRangeAtom]) -> None:
        self.children.extend([(ClassRange.Label.LO, self._check_child_type_for_mutators(child)) for child in children])

    def children_lo(self) -> typing.Iterator[ClassRangeAtom]:
        return iter(self._children_snapshot(ClassRange.Label.LO))

    def child_lo(self) -> ClassRangeAtom:
        children = self._children_snapshot(ClassRange.Label.LO)
        if (n := len(children)) != 1:
            msg = f"Expected one lo child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_lo(self) -> ClassRangeAtom | None:
        children = self._children_snapshot(ClassRange.Label.LO)
        if (n := len(children)) > 1:
            msg = f"Expected at most one lo child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def hi(self) -> ClassRangeAtom:
        return self.child_hi()

    def lo(self) -> ClassRangeAtom:
        return self.child_lo()


ClassRange.Label.HI._fltk_canonical_name = "ClassRange.Label.HI"
ClassRange.Label.LO._fltk_canonical_name = "ClassRange.Label.LO"


@dataclasses.dataclass
class ClassMember:
    class Label(enum.Enum):
        CLASS_CHAR = enum.auto()
        CLASS_ESCAPE = enum.auto()
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
        {"ClassMember.Label.CLASS_CHAR": Label.CLASS_CHAR, "ClassMember.Label.CLASS_ESCAPE": Label.CLASS_ESCAPE}
    )
    kind: typing.Literal[NodeKind.CLASSMEMBER] = NodeKind.CLASSMEMBER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassChar | ClassEscape]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.ClassChar | _cstp.ClassEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassMember.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.ClassChar | _cstp.ClassEscape],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassMember.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassMember) -> None:
        if not isinstance(other, ClassMember):
            msg = f"ClassMember: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassChar | ClassEscape]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.ClassChar | _cstp.ClassEscape) -> ClassChar | ClassEscape:
        if isinstance(child, ClassChar | ClassEscape):
            return child
        msg = f"ClassMember: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassMember.Label | None:
        if label is None or isinstance(label, ClassMember.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassMember._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassMember"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.ClassChar | _cstp.ClassEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassMember.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, ClassChar | ClassEscape]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassMember.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.ClassChar | _cstp.ClassEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassMember.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassMember.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ClassMember.Label) -> list[ClassChar | ClassEscape]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_class_char(self, child: _cstp.ClassChar) -> None:
        self.children.append((ClassMember.Label.CLASS_CHAR, self._check_child_type_for_mutators(child)))

    def extend_class_char(self, children: typing.Iterable[_cstp.ClassChar]) -> None:
        self.children.extend(
            [(ClassMember.Label.CLASS_CHAR, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_class_char(self) -> typing.Iterator[ClassChar]:
        return iter(typing.cast("list[ClassChar]", self._children_snapshot(ClassMember.Label.CLASS_CHAR)))

    def child_class_char(self) -> ClassChar:
        children = typing.cast("list[ClassChar]", self._children_snapshot(ClassMember.Label.CLASS_CHAR))
        if (n := len(children)) != 1:
            msg = f"Expected one class_char child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_char(self) -> ClassChar | None:
        children = typing.cast("list[ClassChar]", self._children_snapshot(ClassMember.Label.CLASS_CHAR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_char child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_escape(self, child: _cstp.ClassEscape) -> None:
        self.children.append((ClassMember.Label.CLASS_ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_class_escape(self, children: typing.Iterable[_cstp.ClassEscape]) -> None:
        self.children.extend(
            [(ClassMember.Label.CLASS_ESCAPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_class_escape(self) -> typing.Iterator[ClassEscape]:
        return iter(typing.cast("list[ClassEscape]", self._children_snapshot(ClassMember.Label.CLASS_ESCAPE)))

    def child_class_escape(self) -> ClassEscape:
        children = typing.cast("list[ClassEscape]", self._children_snapshot(ClassMember.Label.CLASS_ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one class_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_escape(self) -> ClassEscape | None:
        children = typing.cast("list[ClassEscape]", self._children_snapshot(ClassMember.Label.CLASS_ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def class_char(self) -> ClassChar | None:
        return self.maybe_class_char()

    def class_escape(self) -> ClassEscape | None:
        return self.maybe_class_escape()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "ClassMember.variant: node has no labeled child"
        raise ValueError(msg)


ClassMember.Label.CLASS_CHAR._fltk_canonical_name = "ClassMember.Label.CLASS_CHAR"
ClassMember.Label.CLASS_ESCAPE._fltk_canonical_name = "ClassMember.Label.CLASS_ESCAPE"


@dataclasses.dataclass
class ClassRangeAtom:
    class Label(enum.Enum):
        CLASS_CHAR = enum.auto()
        CLASS_CHAR_ESCAPE = enum.auto()
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
            "ClassRangeAtom.Label.CLASS_CHAR": Label.CLASS_CHAR,
            "ClassRangeAtom.Label.CLASS_CHAR_ESCAPE": Label.CLASS_CHAR_ESCAPE,
        }
    )
    kind: typing.Literal[NodeKind.CLASSRANGEATOM] = NodeKind.CLASSRANGEATOM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassChar | ClassCharEscape]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.ClassChar | _cstp.ClassCharEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassRangeAtom.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.ClassChar | _cstp.ClassCharEscape],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassRangeAtom.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassRangeAtom) -> None:
        if not isinstance(other, ClassRangeAtom):
            msg = f"ClassRangeAtom: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassChar | ClassCharEscape]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.ClassChar | _cstp.ClassCharEscape
    ) -> ClassChar | ClassCharEscape:
        if isinstance(child, ClassChar | ClassCharEscape):
            return child
        msg = f"ClassRangeAtom: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassRangeAtom.Label | None:
        if label is None or isinstance(label, ClassRangeAtom.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassRangeAtom._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassRangeAtom"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.ClassChar | _cstp.ClassCharEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassRangeAtom.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, ClassChar | ClassCharEscape]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassRangeAtom.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.ClassChar | _cstp.ClassCharEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassRangeAtom.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassRangeAtom.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ClassRangeAtom.Label) -> list[ClassChar | ClassCharEscape]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_class_char(self, child: _cstp.ClassChar) -> None:
        self.children.append((ClassRangeAtom.Label.CLASS_CHAR, self._check_child_type_for_mutators(child)))

    def extend_class_char(self, children: typing.Iterable[_cstp.ClassChar]) -> None:
        self.children.extend(
            [(ClassRangeAtom.Label.CLASS_CHAR, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_class_char(self) -> typing.Iterator[ClassChar]:
        return iter(typing.cast("list[ClassChar]", self._children_snapshot(ClassRangeAtom.Label.CLASS_CHAR)))

    def child_class_char(self) -> ClassChar:
        children = typing.cast("list[ClassChar]", self._children_snapshot(ClassRangeAtom.Label.CLASS_CHAR))
        if (n := len(children)) != 1:
            msg = f"Expected one class_char child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_char(self) -> ClassChar | None:
        children = typing.cast("list[ClassChar]", self._children_snapshot(ClassRangeAtom.Label.CLASS_CHAR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_char child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_char_escape(self, child: _cstp.ClassCharEscape) -> None:
        self.children.append((ClassRangeAtom.Label.CLASS_CHAR_ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_class_char_escape(self, children: typing.Iterable[_cstp.ClassCharEscape]) -> None:
        self.children.extend(
            [(ClassRangeAtom.Label.CLASS_CHAR_ESCAPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_class_char_escape(self) -> typing.Iterator[ClassCharEscape]:
        return iter(
            typing.cast("list[ClassCharEscape]", self._children_snapshot(ClassRangeAtom.Label.CLASS_CHAR_ESCAPE))
        )

    def child_class_char_escape(self) -> ClassCharEscape:
        children = typing.cast("list[ClassCharEscape]", self._children_snapshot(ClassRangeAtom.Label.CLASS_CHAR_ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one class_char_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_char_escape(self) -> ClassCharEscape | None:
        children = typing.cast("list[ClassCharEscape]", self._children_snapshot(ClassRangeAtom.Label.CLASS_CHAR_ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_char_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def class_char(self) -> ClassChar | None:
        return self.maybe_class_char()

    def class_char_escape(self) -> ClassCharEscape | None:
        return self.maybe_class_char_escape()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "ClassRangeAtom.variant: node has no labeled child"
        raise ValueError(msg)


ClassRangeAtom.Label.CLASS_CHAR._fltk_canonical_name = "ClassRangeAtom.Label.CLASS_CHAR"
ClassRangeAtom.Label.CLASS_CHAR_ESCAPE._fltk_canonical_name = "ClassRangeAtom.Label.CLASS_CHAR_ESCAPE"


@dataclasses.dataclass
class ClassChar:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"ClassChar.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.CLASSCHAR] = NodeKind.CLASSCHAR
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
            if label is None or isinstance(label, ClassChar.Label)
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
            if label is None or isinstance(label, ClassChar.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassChar) -> None:
        if not isinstance(other, ClassChar):
            msg = f"ClassChar: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"ClassChar: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassChar.Label | None:
        if label is None or isinstance(label, ClassChar.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassChar._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassChar"
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
            if label is None or isinstance(label, ClassChar.Label)
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
            msg = f"ClassChar.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, ClassChar.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassChar.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ClassChar.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ClassChar.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(ClassChar.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(ClassChar.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(ClassChar.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(ClassChar.Label.VALUE)
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
            msg = "ClassChar.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


ClassChar.Label.VALUE._fltk_canonical_name = "ClassChar.Label.VALUE"


@dataclasses.dataclass
class ClassEscape:
    class Label(enum.Enum):
        BODY = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"ClassEscape.Label.BODY": Label.BODY})
    kind: typing.Literal[NodeKind.CLASSESCAPE] = NodeKind.CLASSESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassEscapeBody]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.ClassEscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassEscape.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.ClassEscapeBody],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassEscape.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassEscape) -> None:
        if not isinstance(other, ClassEscape):
            msg = f"ClassEscape: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassEscapeBody]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.ClassEscapeBody) -> ClassEscapeBody:
        if isinstance(child, ClassEscapeBody):
            return child
        msg = f"ClassEscape: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassEscape.Label | None:
        if label is None or isinstance(label, ClassEscape.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassEscape._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassEscape"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.ClassEscapeBody,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassEscape.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, ClassEscapeBody]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassEscape.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.ClassEscapeBody,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassEscape.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ClassEscape.Label) -> list[ClassEscapeBody]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_body(self, child: _cstp.ClassEscapeBody) -> None:
        self.children.append((ClassEscape.Label.BODY, self._check_child_type_for_mutators(child)))

    def extend_body(self, children: typing.Iterable[_cstp.ClassEscapeBody]) -> None:
        self.children.extend(
            [(ClassEscape.Label.BODY, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_body(self) -> typing.Iterator[ClassEscapeBody]:
        return iter(self._children_snapshot(ClassEscape.Label.BODY))

    def child_body(self) -> ClassEscapeBody:
        children = self._children_snapshot(ClassEscape.Label.BODY)
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> ClassEscapeBody | None:
        children = self._children_snapshot(ClassEscape.Label.BODY)
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def body(self) -> ClassEscapeBody:
        return self.child_body()


ClassEscape.Label.BODY._fltk_canonical_name = "ClassEscape.Label.BODY"


@dataclasses.dataclass
class ClassEscapeBody:
    class Label(enum.Enum):
        CHAR_ESCAPE = enum.auto()
        CLASS_SHORTHAND = enum.auto()
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
            "ClassEscapeBody.Label.CHAR_ESCAPE": Label.CHAR_ESCAPE,
            "ClassEscapeBody.Label.CLASS_SHORTHAND": Label.CLASS_SHORTHAND,
        }
    )
    kind: typing.Literal[NodeKind.CLASSESCAPEBODY] = NodeKind.CLASSESCAPEBODY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CharEscape | ClassShorthand]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.CharEscape | _cstp.ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassEscapeBody.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.CharEscape | _cstp.ClassShorthand],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassEscapeBody.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassEscapeBody) -> None:
        if not isinstance(other, ClassEscapeBody):
            msg = f"ClassEscapeBody: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, CharEscape | ClassShorthand]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.CharEscape | _cstp.ClassShorthand
    ) -> CharEscape | ClassShorthand:
        if isinstance(child, CharEscape | ClassShorthand):
            return child
        msg = f"ClassEscapeBody: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassEscapeBody.Label | None:
        if label is None or isinstance(label, ClassEscapeBody.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassEscapeBody._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassEscapeBody"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.CharEscape | _cstp.ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassEscapeBody.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, CharEscape | ClassShorthand]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassEscapeBody.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.CharEscape | _cstp.ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassEscapeBody.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassEscapeBody.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ClassEscapeBody.Label) -> list[CharEscape | ClassShorthand]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_char_escape(self, child: _cstp.CharEscape) -> None:
        self.children.append((ClassEscapeBody.Label.CHAR_ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_char_escape(self, children: typing.Iterable[_cstp.CharEscape]) -> None:
        self.children.extend(
            [(ClassEscapeBody.Label.CHAR_ESCAPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_char_escape(self) -> typing.Iterator[CharEscape]:
        return iter(typing.cast("list[CharEscape]", self._children_snapshot(ClassEscapeBody.Label.CHAR_ESCAPE)))

    def child_char_escape(self) -> CharEscape:
        children = typing.cast("list[CharEscape]", self._children_snapshot(ClassEscapeBody.Label.CHAR_ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one char_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_char_escape(self) -> CharEscape | None:
        children = typing.cast("list[CharEscape]", self._children_snapshot(ClassEscapeBody.Label.CHAR_ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one char_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_shorthand(self, child: _cstp.ClassShorthand) -> None:
        self.children.append((ClassEscapeBody.Label.CLASS_SHORTHAND, self._check_child_type_for_mutators(child)))

    def extend_class_shorthand(self, children: typing.Iterable[_cstp.ClassShorthand]) -> None:
        self.children.extend(
            [(ClassEscapeBody.Label.CLASS_SHORTHAND, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_class_shorthand(self) -> typing.Iterator[ClassShorthand]:
        return iter(typing.cast("list[ClassShorthand]", self._children_snapshot(ClassEscapeBody.Label.CLASS_SHORTHAND)))

    def child_class_shorthand(self) -> ClassShorthand:
        children = typing.cast("list[ClassShorthand]", self._children_snapshot(ClassEscapeBody.Label.CLASS_SHORTHAND))
        if (n := len(children)) != 1:
            msg = f"Expected one class_shorthand child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_shorthand(self) -> ClassShorthand | None:
        children = typing.cast("list[ClassShorthand]", self._children_snapshot(ClassEscapeBody.Label.CLASS_SHORTHAND))
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_shorthand child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def char_escape(self) -> CharEscape | None:
        return self.maybe_char_escape()

    def class_shorthand(self) -> ClassShorthand | None:
        return self.maybe_class_shorthand()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "ClassEscapeBody.variant: node has no labeled child"
        raise ValueError(msg)


ClassEscapeBody.Label.CHAR_ESCAPE._fltk_canonical_name = "ClassEscapeBody.Label.CHAR_ESCAPE"
ClassEscapeBody.Label.CLASS_SHORTHAND._fltk_canonical_name = "ClassEscapeBody.Label.CLASS_SHORTHAND"


@dataclasses.dataclass
class ClassCharEscape:
    class Label(enum.Enum):
        BODY = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"ClassCharEscape.Label.BODY": Label.BODY})
    kind: typing.Literal[NodeKind.CLASSCHARESCAPE] = NodeKind.CLASSCHARESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CharEscape]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.CharEscape, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassCharEscape.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.CharEscape],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassCharEscape.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassCharEscape) -> None:
        if not isinstance(other, ClassCharEscape):
            msg = f"ClassCharEscape: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, CharEscape]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.CharEscape) -> CharEscape:
        if isinstance(child, CharEscape):
            return child
        msg = f"ClassCharEscape: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassCharEscape.Label | None:
        if label is None or isinstance(label, ClassCharEscape.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassCharEscape._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassCharEscape"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.CharEscape, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassCharEscape.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, CharEscape]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassCharEscape.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.CharEscape, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, ClassCharEscape.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassCharEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ClassCharEscape.Label) -> list[CharEscape]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_body(self, child: _cstp.CharEscape) -> None:
        self.children.append((ClassCharEscape.Label.BODY, self._check_child_type_for_mutators(child)))

    def extend_body(self, children: typing.Iterable[_cstp.CharEscape]) -> None:
        self.children.extend(
            [(ClassCharEscape.Label.BODY, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_body(self) -> typing.Iterator[CharEscape]:
        return iter(self._children_snapshot(ClassCharEscape.Label.BODY))

    def child_body(self) -> CharEscape:
        children = self._children_snapshot(ClassCharEscape.Label.BODY)
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> CharEscape | None:
        children = self._children_snapshot(ClassCharEscape.Label.BODY)
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def body(self) -> CharEscape:
        return self.child_body()


ClassCharEscape.Label.BODY._fltk_canonical_name = "ClassCharEscape.Label.BODY"


@dataclasses.dataclass
class Escape:
    class Label(enum.Enum):
        BODY = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Escape.Label.BODY": Label.BODY})
    kind: typing.Literal[NodeKind.ESCAPE] = NodeKind.ESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, EscapeBody]] = dataclasses.field(default_factory=list)

    def append(
        self, child: _cstp.EscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Escape.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.EscapeBody],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Escape.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Escape) -> None:
        if not isinstance(other, Escape):
            msg = f"Escape: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, EscapeBody]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.EscapeBody) -> EscapeBody:
        if isinstance(child, EscapeBody):
            return child
        msg = f"Escape: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Escape.Label | None:
        if label is None or isinstance(label, Escape.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Escape._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Escape"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self, index: int, child: _cstp.EscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Escape.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, EscapeBody]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Escape.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: _cstp.EscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Escape.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Escape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Escape.Label) -> list[EscapeBody]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_body(self, child: _cstp.EscapeBody) -> None:
        self.children.append((Escape.Label.BODY, self._check_child_type_for_mutators(child)))

    def extend_body(self, children: typing.Iterable[_cstp.EscapeBody]) -> None:
        self.children.extend([(Escape.Label.BODY, self._check_child_type_for_mutators(child)) for child in children])

    def children_body(self) -> typing.Iterator[EscapeBody]:
        return iter(self._children_snapshot(Escape.Label.BODY))

    def child_body(self) -> EscapeBody:
        children = self._children_snapshot(Escape.Label.BODY)
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> EscapeBody | None:
        children = self._children_snapshot(Escape.Label.BODY)
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def body(self) -> EscapeBody:
        return self.child_body()


Escape.Label.BODY._fltk_canonical_name = "Escape.Label.BODY"


@dataclasses.dataclass
class EscapeBody:
    class Label(enum.Enum):
        ANCHOR_ESCAPE = enum.auto()
        ASSERTION = enum.auto()
        CHAR_ESCAPE = enum.auto()
        CLASS_SHORTHAND = enum.auto()
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
            "EscapeBody.Label.ANCHOR_ESCAPE": Label.ANCHOR_ESCAPE,
            "EscapeBody.Label.ASSERTION": Label.ASSERTION,
            "EscapeBody.Label.CHAR_ESCAPE": Label.CHAR_ESCAPE,
            "EscapeBody.Label.CLASS_SHORTHAND": Label.CLASS_SHORTHAND,
        }
    )
    kind: typing.Literal[NodeKind.ESCAPEBODY] = NodeKind.ESCAPEBODY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, AnchorEscape | Assertion | CharEscape | ClassShorthand]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.AnchorEscape | _cstp.Assertion | _cstp.CharEscape | _cstp.ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, EscapeBody.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.AnchorEscape | _cstp.Assertion | _cstp.CharEscape | _cstp.ClassShorthand],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, EscapeBody.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.EscapeBody) -> None:
        if not isinstance(other, EscapeBody):
            msg = f"EscapeBody: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, AnchorEscape | Assertion | CharEscape | ClassShorthand]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.AnchorEscape | _cstp.Assertion | _cstp.CharEscape | _cstp.ClassShorthand
    ) -> AnchorEscape | Assertion | CharEscape | ClassShorthand:
        if isinstance(child, AnchorEscape | Assertion | CharEscape | ClassShorthand):
            return child
        msg = f"EscapeBody: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> EscapeBody.Label | None:
        if label is None or isinstance(label, EscapeBody.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = EscapeBody._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "EscapeBody"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.AnchorEscape | _cstp.Assertion | _cstp.CharEscape | _cstp.ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, EscapeBody.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, AnchorEscape | Assertion | CharEscape | ClassShorthand]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"EscapeBody.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.AnchorEscape | _cstp.Assertion | _cstp.CharEscape | _cstp.ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, EscapeBody.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"EscapeBody.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: EscapeBody.Label
    ) -> list[AnchorEscape | Assertion | CharEscape | ClassShorthand]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_anchor_escape(self, child: _cstp.AnchorEscape) -> None:
        self.children.append((EscapeBody.Label.ANCHOR_ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_anchor_escape(self, children: typing.Iterable[_cstp.AnchorEscape]) -> None:
        self.children.extend(
            [(EscapeBody.Label.ANCHOR_ESCAPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_anchor_escape(self) -> typing.Iterator[AnchorEscape]:
        return iter(typing.cast("list[AnchorEscape]", self._children_snapshot(EscapeBody.Label.ANCHOR_ESCAPE)))

    def child_anchor_escape(self) -> AnchorEscape:
        children = typing.cast("list[AnchorEscape]", self._children_snapshot(EscapeBody.Label.ANCHOR_ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one anchor_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor_escape(self) -> AnchorEscape | None:
        children = typing.cast("list[AnchorEscape]", self._children_snapshot(EscapeBody.Label.ANCHOR_ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_assertion(self, child: _cstp.Assertion) -> None:
        self.children.append((EscapeBody.Label.ASSERTION, self._check_child_type_for_mutators(child)))

    def extend_assertion(self, children: typing.Iterable[_cstp.Assertion]) -> None:
        self.children.extend(
            [(EscapeBody.Label.ASSERTION, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_assertion(self) -> typing.Iterator[Assertion]:
        return iter(typing.cast("list[Assertion]", self._children_snapshot(EscapeBody.Label.ASSERTION)))

    def child_assertion(self) -> Assertion:
        children = typing.cast("list[Assertion]", self._children_snapshot(EscapeBody.Label.ASSERTION))
        if (n := len(children)) != 1:
            msg = f"Expected one assertion child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_assertion(self) -> Assertion | None:
        children = typing.cast("list[Assertion]", self._children_snapshot(EscapeBody.Label.ASSERTION))
        if (n := len(children)) > 1:
            msg = f"Expected at most one assertion child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_char_escape(self, child: _cstp.CharEscape) -> None:
        self.children.append((EscapeBody.Label.CHAR_ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_char_escape(self, children: typing.Iterable[_cstp.CharEscape]) -> None:
        self.children.extend(
            [(EscapeBody.Label.CHAR_ESCAPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_char_escape(self) -> typing.Iterator[CharEscape]:
        return iter(typing.cast("list[CharEscape]", self._children_snapshot(EscapeBody.Label.CHAR_ESCAPE)))

    def child_char_escape(self) -> CharEscape:
        children = typing.cast("list[CharEscape]", self._children_snapshot(EscapeBody.Label.CHAR_ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one char_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_char_escape(self) -> CharEscape | None:
        children = typing.cast("list[CharEscape]", self._children_snapshot(EscapeBody.Label.CHAR_ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one char_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_shorthand(self, child: _cstp.ClassShorthand) -> None:
        self.children.append((EscapeBody.Label.CLASS_SHORTHAND, self._check_child_type_for_mutators(child)))

    def extend_class_shorthand(self, children: typing.Iterable[_cstp.ClassShorthand]) -> None:
        self.children.extend(
            [(EscapeBody.Label.CLASS_SHORTHAND, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_class_shorthand(self) -> typing.Iterator[ClassShorthand]:
        return iter(typing.cast("list[ClassShorthand]", self._children_snapshot(EscapeBody.Label.CLASS_SHORTHAND)))

    def child_class_shorthand(self) -> ClassShorthand:
        children = typing.cast("list[ClassShorthand]", self._children_snapshot(EscapeBody.Label.CLASS_SHORTHAND))
        if (n := len(children)) != 1:
            msg = f"Expected one class_shorthand child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_shorthand(self) -> ClassShorthand | None:
        children = typing.cast("list[ClassShorthand]", self._children_snapshot(EscapeBody.Label.CLASS_SHORTHAND))
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_shorthand child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def anchor_escape(self) -> AnchorEscape | None:
        return self.maybe_anchor_escape()

    def assertion(self) -> Assertion | None:
        return self.maybe_assertion()

    def char_escape(self) -> CharEscape | None:
        return self.maybe_char_escape()

    def class_shorthand(self) -> ClassShorthand | None:
        return self.maybe_class_shorthand()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "EscapeBody.variant: node has no labeled child"
        raise ValueError(msg)


EscapeBody.Label.ANCHOR_ESCAPE._fltk_canonical_name = "EscapeBody.Label.ANCHOR_ESCAPE"
EscapeBody.Label.ASSERTION._fltk_canonical_name = "EscapeBody.Label.ASSERTION"
EscapeBody.Label.CHAR_ESCAPE._fltk_canonical_name = "EscapeBody.Label.CHAR_ESCAPE"
EscapeBody.Label.CLASS_SHORTHAND._fltk_canonical_name = "EscapeBody.Label.CLASS_SHORTHAND"


@dataclasses.dataclass
class ClassShorthand:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"ClassShorthand.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.CLASSSHORTHAND] = NodeKind.CLASSSHORTHAND
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
            if label is None or isinstance(label, ClassShorthand.Label)
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
            if label is None or isinstance(label, ClassShorthand.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ClassShorthand) -> None:
        if not isinstance(other, ClassShorthand):
            msg = f"ClassShorthand: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"ClassShorthand: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ClassShorthand.Label | None:
        if label is None or isinstance(label, ClassShorthand.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ClassShorthand._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ClassShorthand"
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
            if label is None or isinstance(label, ClassShorthand.Label)
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
            msg = f"ClassShorthand.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, ClassShorthand.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassShorthand.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ClassShorthand.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ClassShorthand.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(ClassShorthand.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(ClassShorthand.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(ClassShorthand.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(ClassShorthand.Label.VALUE)
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
            msg = "ClassShorthand.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


ClassShorthand.Label.VALUE._fltk_canonical_name = "ClassShorthand.Label.VALUE"


@dataclasses.dataclass
class Assertion:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Assertion.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.ASSERTION] = NodeKind.ASSERTION
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
            if label is None or isinstance(label, Assertion.Label)
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
            if label is None or isinstance(label, Assertion.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Assertion) -> None:
        if not isinstance(other, Assertion):
            msg = f"Assertion: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"Assertion: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Assertion.Label | None:
        if label is None or isinstance(label, Assertion.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Assertion._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Assertion"
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
            if label is None or isinstance(label, Assertion.Label)
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
            msg = f"Assertion.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, Assertion.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Assertion.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Assertion.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Assertion.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(Assertion.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Assertion.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Assertion.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Assertion.Label.VALUE)
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
            msg = "Assertion.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


Assertion.Label.VALUE._fltk_canonical_name = "Assertion.Label.VALUE"


@dataclasses.dataclass
class AnchorEscape:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"AnchorEscape.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.ANCHORESCAPE] = NodeKind.ANCHORESCAPE
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
            if label is None or isinstance(label, AnchorEscape.Label)
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
            if label is None or isinstance(label, AnchorEscape.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.AnchorEscape) -> None:
        if not isinstance(other, AnchorEscape):
            msg = f"AnchorEscape: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"AnchorEscape: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> AnchorEscape.Label | None:
        if label is None or isinstance(label, AnchorEscape.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = AnchorEscape._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "AnchorEscape"
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
            if label is None or isinstance(label, AnchorEscape.Label)
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
            msg = f"AnchorEscape.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, AnchorEscape.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"AnchorEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: AnchorEscape.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((AnchorEscape.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(AnchorEscape.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(AnchorEscape.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(AnchorEscape.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(AnchorEscape.Label.VALUE)
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
            msg = "AnchorEscape.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


AnchorEscape.Label.VALUE._fltk_canonical_name = "AnchorEscape.Label.VALUE"


@dataclasses.dataclass
class CharEscape:
    class Label(enum.Enum):
        CONTROL_ESCAPE = enum.auto()
        HEX_ESCAPE = enum.auto()
        META_ESCAPE = enum.auto()
        UNICODE_ESCAPE = enum.auto()
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
            "CharEscape.Label.CONTROL_ESCAPE": Label.CONTROL_ESCAPE,
            "CharEscape.Label.HEX_ESCAPE": Label.HEX_ESCAPE,
            "CharEscape.Label.META_ESCAPE": Label.META_ESCAPE,
            "CharEscape.Label.UNICODE_ESCAPE": Label.UNICODE_ESCAPE,
        }
    )
    kind: typing.Literal[NodeKind.CHARESCAPE] = NodeKind.CHARESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ControlEscape | HexEscape | MetaEscape | UnicodeEscape]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.ControlEscape | _cstp.HexEscape | _cstp.MetaEscape | _cstp.UnicodeEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CharEscape.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.ControlEscape | _cstp.HexEscape | _cstp.MetaEscape | _cstp.UnicodeEscape],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CharEscape.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.CharEscape) -> None:
        if not isinstance(other, CharEscape):
            msg = f"CharEscape: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ControlEscape | HexEscape | MetaEscape | UnicodeEscape]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.ControlEscape | _cstp.HexEscape | _cstp.MetaEscape | _cstp.UnicodeEscape
    ) -> ControlEscape | HexEscape | MetaEscape | UnicodeEscape:
        if isinstance(child, ControlEscape | HexEscape | MetaEscape | UnicodeEscape):
            return child
        msg = f"CharEscape: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> CharEscape.Label | None:
        if label is None or isinstance(label, CharEscape.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = CharEscape._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "CharEscape"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.ControlEscape | _cstp.HexEscape | _cstp.MetaEscape | _cstp.UnicodeEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CharEscape.Label)
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

    def remove_at(self, index: int) -> tuple[Label | None, ControlEscape | HexEscape | MetaEscape | UnicodeEscape]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CharEscape.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.ControlEscape | _cstp.HexEscape | _cstp.MetaEscape | _cstp.UnicodeEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, CharEscape.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CharEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: CharEscape.Label
    ) -> list[ControlEscape | HexEscape | MetaEscape | UnicodeEscape]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_control_escape(self, child: _cstp.ControlEscape) -> None:
        self.children.append((CharEscape.Label.CONTROL_ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_control_escape(self, children: typing.Iterable[_cstp.ControlEscape]) -> None:
        self.children.extend(
            [(CharEscape.Label.CONTROL_ESCAPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_control_escape(self) -> typing.Iterator[ControlEscape]:
        return iter(typing.cast("list[ControlEscape]", self._children_snapshot(CharEscape.Label.CONTROL_ESCAPE)))

    def child_control_escape(self) -> ControlEscape:
        children = typing.cast("list[ControlEscape]", self._children_snapshot(CharEscape.Label.CONTROL_ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one control_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_control_escape(self) -> ControlEscape | None:
        children = typing.cast("list[ControlEscape]", self._children_snapshot(CharEscape.Label.CONTROL_ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one control_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_hex_escape(self, child: _cstp.HexEscape) -> None:
        self.children.append((CharEscape.Label.HEX_ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_hex_escape(self, children: typing.Iterable[_cstp.HexEscape]) -> None:
        self.children.extend(
            [(CharEscape.Label.HEX_ESCAPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_hex_escape(self) -> typing.Iterator[HexEscape]:
        return iter(typing.cast("list[HexEscape]", self._children_snapshot(CharEscape.Label.HEX_ESCAPE)))

    def child_hex_escape(self) -> HexEscape:
        children = typing.cast("list[HexEscape]", self._children_snapshot(CharEscape.Label.HEX_ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one hex_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_hex_escape(self) -> HexEscape | None:
        children = typing.cast("list[HexEscape]", self._children_snapshot(CharEscape.Label.HEX_ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one hex_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_meta_escape(self, child: _cstp.MetaEscape) -> None:
        self.children.append((CharEscape.Label.META_ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_meta_escape(self, children: typing.Iterable[_cstp.MetaEscape]) -> None:
        self.children.extend(
            [(CharEscape.Label.META_ESCAPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_meta_escape(self) -> typing.Iterator[MetaEscape]:
        return iter(typing.cast("list[MetaEscape]", self._children_snapshot(CharEscape.Label.META_ESCAPE)))

    def child_meta_escape(self) -> MetaEscape:
        children = typing.cast("list[MetaEscape]", self._children_snapshot(CharEscape.Label.META_ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one meta_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_meta_escape(self) -> MetaEscape | None:
        children = typing.cast("list[MetaEscape]", self._children_snapshot(CharEscape.Label.META_ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one meta_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_unicode_escape(self, child: _cstp.UnicodeEscape) -> None:
        self.children.append((CharEscape.Label.UNICODE_ESCAPE, self._check_child_type_for_mutators(child)))

    def extend_unicode_escape(self, children: typing.Iterable[_cstp.UnicodeEscape]) -> None:
        self.children.extend(
            [(CharEscape.Label.UNICODE_ESCAPE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_unicode_escape(self) -> typing.Iterator[UnicodeEscape]:
        return iter(typing.cast("list[UnicodeEscape]", self._children_snapshot(CharEscape.Label.UNICODE_ESCAPE)))

    def child_unicode_escape(self) -> UnicodeEscape:
        children = typing.cast("list[UnicodeEscape]", self._children_snapshot(CharEscape.Label.UNICODE_ESCAPE))
        if (n := len(children)) != 1:
            msg = f"Expected one unicode_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_unicode_escape(self) -> UnicodeEscape | None:
        children = typing.cast("list[UnicodeEscape]", self._children_snapshot(CharEscape.Label.UNICODE_ESCAPE))
        if (n := len(children)) > 1:
            msg = f"Expected at most one unicode_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def control_escape(self) -> ControlEscape | None:
        return self.maybe_control_escape()

    def hex_escape(self) -> HexEscape | None:
        return self.maybe_hex_escape()

    def meta_escape(self) -> MetaEscape | None:
        return self.maybe_meta_escape()

    def unicode_escape(self) -> UnicodeEscape | None:
        return self.maybe_unicode_escape()

    def variant(self) -> Label:
        for label, _child in self.children:
            if label is not None:
                return label
        msg = "CharEscape.variant: node has no labeled child"
        raise ValueError(msg)


CharEscape.Label.CONTROL_ESCAPE._fltk_canonical_name = "CharEscape.Label.CONTROL_ESCAPE"
CharEscape.Label.HEX_ESCAPE._fltk_canonical_name = "CharEscape.Label.HEX_ESCAPE"
CharEscape.Label.META_ESCAPE._fltk_canonical_name = "CharEscape.Label.META_ESCAPE"
CharEscape.Label.UNICODE_ESCAPE._fltk_canonical_name = "CharEscape.Label.UNICODE_ESCAPE"


@dataclasses.dataclass
class ControlEscape:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"ControlEscape.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.CONTROLESCAPE] = NodeKind.CONTROLESCAPE
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
            if label is None or isinstance(label, ControlEscape.Label)
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
            if label is None or isinstance(label, ControlEscape.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.ControlEscape) -> None:
        if not isinstance(other, ControlEscape):
            msg = f"ControlEscape: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"ControlEscape: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> ControlEscape.Label | None:
        if label is None or isinstance(label, ControlEscape.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = ControlEscape._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "ControlEscape"
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
            if label is None or isinstance(label, ControlEscape.Label)
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
            msg = f"ControlEscape.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, ControlEscape.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ControlEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: ControlEscape.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ControlEscape.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(ControlEscape.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(ControlEscape.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(ControlEscape.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(ControlEscape.Label.VALUE)
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
            msg = "ControlEscape.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


ControlEscape.Label.VALUE._fltk_canonical_name = "ControlEscape.Label.VALUE"


@dataclasses.dataclass
class HexEscape:
    class Label(enum.Enum):
        DIGITS = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"HexEscape.Label.DIGITS": Label.DIGITS})
    kind: typing.Literal[NodeKind.HEXESCAPE] = NodeKind.HEXESCAPE
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
            if label is None or isinstance(label, HexEscape.Label)
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
            if label is None or isinstance(label, HexEscape.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.HexEscape) -> None:
        if not isinstance(other, HexEscape):
            msg = f"HexEscape: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"HexEscape: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> HexEscape.Label | None:
        if label is None or isinstance(label, HexEscape.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = HexEscape._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "HexEscape"
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
            if label is None or isinstance(label, HexEscape.Label)
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
            msg = f"HexEscape.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, HexEscape.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"HexEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: HexEscape.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_digits(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((HexEscape.Label.DIGITS, self._check_child_type_for_mutators(child)))

    def extend_digits(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(HexEscape.Label.DIGITS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_digits(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(HexEscape.Label.DIGITS))

    def child_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(HexEscape.Label.DIGITS)
        if (n := len(children)) != 1:
            msg = f"Expected one digits child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(HexEscape.Label.DIGITS)
        if (n := len(children)) > 1:
            msg = f"Expected at most one digits child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_digits()

    def digits_text(self) -> str:
        child = self.child_digits()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "HexEscape.digits_text: child labelled 'digits' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


HexEscape.Label.DIGITS._fltk_canonical_name = "HexEscape.Label.DIGITS"


@dataclasses.dataclass
class UnicodeEscape:
    class Label(enum.Enum):
        DIGITS = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"UnicodeEscape.Label.DIGITS": Label.DIGITS})
    kind: typing.Literal[NodeKind.UNICODEESCAPE] = NodeKind.UNICODEESCAPE
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
            if label is None or isinstance(label, UnicodeEscape.Label)
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
            if label is None or isinstance(label, UnicodeEscape.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.UnicodeEscape) -> None:
        if not isinstance(other, UnicodeEscape):
            msg = f"UnicodeEscape: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"UnicodeEscape: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> UnicodeEscape.Label | None:
        if label is None or isinstance(label, UnicodeEscape.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = UnicodeEscape._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "UnicodeEscape"
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
            if label is None or isinstance(label, UnicodeEscape.Label)
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
            msg = f"UnicodeEscape.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, UnicodeEscape.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"UnicodeEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: UnicodeEscape.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_digits(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((UnicodeEscape.Label.DIGITS, self._check_child_type_for_mutators(child)))

    def extend_digits(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(UnicodeEscape.Label.DIGITS, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_digits(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(UnicodeEscape.Label.DIGITS))

    def child_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(UnicodeEscape.Label.DIGITS)
        if (n := len(children)) != 1:
            msg = f"Expected one digits child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(UnicodeEscape.Label.DIGITS)
        if (n := len(children)) > 1:
            msg = f"Expected at most one digits child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_digits()

    def digits_text(self) -> str:
        child = self.child_digits()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "UnicodeEscape.digits_text: child labelled 'digits' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


UnicodeEscape.Label.DIGITS._fltk_canonical_name = "UnicodeEscape.Label.DIGITS"


@dataclasses.dataclass
class MetaEscape:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"MetaEscape.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.METAESCAPE] = NodeKind.METAESCAPE
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
            if label is None or isinstance(label, MetaEscape.Label)
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
            if label is None or isinstance(label, MetaEscape.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.MetaEscape) -> None:
        if not isinstance(other, MetaEscape):
            msg = f"MetaEscape: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"MetaEscape: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> MetaEscape.Label | None:
        if label is None or isinstance(label, MetaEscape.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = MetaEscape._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "MetaEscape"
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
            if label is None or isinstance(label, MetaEscape.Label)
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
            msg = f"MetaEscape.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, MetaEscape.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"MetaEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: MetaEscape.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((MetaEscape.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(MetaEscape.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(MetaEscape.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(MetaEscape.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(MetaEscape.Label.VALUE)
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
            msg = "MetaEscape.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


MetaEscape.Label.VALUE._fltk_canonical_name = "MetaEscape.Label.VALUE"


@dataclasses.dataclass
class LiteralChar:
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"LiteralChar.Label.VALUE": Label.VALUE})
    kind: typing.Literal[NodeKind.LITERALCHAR] = NodeKind.LITERALCHAR
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
            if label is None or isinstance(label, LiteralChar.Label)
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
            if label is None or isinstance(label, LiteralChar.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.LiteralChar) -> None:
        if not isinstance(other, LiteralChar):
            msg = f"LiteralChar: unsupported child type {_type_name_for_error(other)}"
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
        msg = f"LiteralChar: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> LiteralChar.Label | None:
        if label is None or isinstance(label, LiteralChar.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = LiteralChar._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "LiteralChar"
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
            if label is None or isinstance(label, LiteralChar.Label)
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
            msg = f"LiteralChar.remove_at: index {index} out of range ({n} children)"
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
            if label is None or isinstance(label, LiteralChar.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"LiteralChar.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: LiteralChar.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((LiteralChar.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend(
            [(LiteralChar.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children]
        )

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(LiteralChar.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(LiteralChar.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(LiteralChar.Label.VALUE)
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
            msg = "LiteralChar.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


LiteralChar.Label.VALUE._fltk_canonical_name = "LiteralChar.Label.VALUE"


@dataclasses.dataclass
class Trivia:
    class Label(enum.Enum):
        CONTENT = enum.auto()
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Trivia.Label.CONTENT": Label.CONTENT})
    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
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
            if label is None or isinstance(label, Trivia.Label)
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
            if label is None or isinstance(label, Trivia.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Trivia) -> None:
        if not isinstance(other, Trivia):
            msg = f"Trivia: unsupported child type {_type_name_for_error(other)}"
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
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
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

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
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
        child: fltk.fegen.pyrt.span_protocol.SpanProtocol,
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

    def _children_snapshot(self, label: Trivia.Label) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Trivia.Label.CONTENT, self._check_child_type_for_mutators(child)))

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Trivia.Label.CONTENT, self._check_child_type_for_mutators(child)) for child in children])

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Trivia.Label.CONTENT))

    def child_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Trivia.Label.CONTENT)
        if (n := len(children)) != 1:
            msg = f"Expected one content child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Trivia.Label.CONTENT)
        if (n := len(children)) > 1:
            msg = f"Expected at most one content child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        return self.child_content()

    def content_text(self) -> str:
        child = self.child_content()
        try:
            return child.text_or_raise()
        except AttributeError:
            msg = "Trivia.content_text: child labelled 'content' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


Trivia.Label.CONTENT._fltk_canonical_name = "Trivia.Label.CONTENT"
