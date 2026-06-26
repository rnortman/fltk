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
    REGEX = enum.auto()
    ALTERNATION = enum.auto()
    CONCATENATION = enum.auto()
    REPETITION = enum.auto()
    QUANTIFIER = enum.auto()
    BOUNDED = enum.auto()
    NUMBER = enum.auto()
    ATOM = enum.auto()
    DOT = enum.auto()
    ANCHOR = enum.auto()
    GROUP = enum.auto()
    NONCAPTURING = enum.auto()
    FLAGGROUP = enum.auto()
    CAPTURING = enum.auto()
    INLINEFLAGS = enum.auto()
    FLAGCHARS = enum.auto()
    CHARCLASS = enum.auto()
    CLASSBODY = enum.auto()
    CLASSITEM = enum.auto()
    CLASSRANGE = enum.auto()
    CLASSMEMBER = enum.auto()
    CLASSRANGEATOM = enum.auto()
    CLASSCHAR = enum.auto()
    CLASSESCAPE = enum.auto()
    CLASSESCAPEBODY = enum.auto()
    CLASSCHARESCAPE = enum.auto()
    ESCAPE = enum.auto()
    ESCAPEBODY = enum.auto()
    CLASSSHORTHAND = enum.auto()
    ASSERTION = enum.auto()
    ANCHORESCAPE = enum.auto()
    CHARESCAPE = enum.auto()
    CONTROLESCAPE = enum.auto()
    HEXESCAPE = enum.auto()
    UNICODEESCAPE = enum.auto()
    METAESCAPE = enum.auto()
    LITERALCHAR = enum.auto()
    TRIVIA = enum.auto()
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


NodeKind.REGEX._fltk_canonical_name = "NodeKind.REGEX"
NodeKind.ALTERNATION._fltk_canonical_name = "NodeKind.ALTERNATION"
NodeKind.CONCATENATION._fltk_canonical_name = "NodeKind.CONCATENATION"
NodeKind.REPETITION._fltk_canonical_name = "NodeKind.REPETITION"
NodeKind.QUANTIFIER._fltk_canonical_name = "NodeKind.QUANTIFIER"
NodeKind.BOUNDED._fltk_canonical_name = "NodeKind.BOUNDED"
NodeKind.NUMBER._fltk_canonical_name = "NodeKind.NUMBER"
NodeKind.ATOM._fltk_canonical_name = "NodeKind.ATOM"
NodeKind.DOT._fltk_canonical_name = "NodeKind.DOT"
NodeKind.ANCHOR._fltk_canonical_name = "NodeKind.ANCHOR"
NodeKind.GROUP._fltk_canonical_name = "NodeKind.GROUP"
NodeKind.NONCAPTURING._fltk_canonical_name = "NodeKind.NONCAPTURING"
NodeKind.FLAGGROUP._fltk_canonical_name = "NodeKind.FLAGGROUP"
NodeKind.CAPTURING._fltk_canonical_name = "NodeKind.CAPTURING"
NodeKind.INLINEFLAGS._fltk_canonical_name = "NodeKind.INLINEFLAGS"
NodeKind.FLAGCHARS._fltk_canonical_name = "NodeKind.FLAGCHARS"
NodeKind.CHARCLASS._fltk_canonical_name = "NodeKind.CHARCLASS"
NodeKind.CLASSBODY._fltk_canonical_name = "NodeKind.CLASSBODY"
NodeKind.CLASSITEM._fltk_canonical_name = "NodeKind.CLASSITEM"
NodeKind.CLASSRANGE._fltk_canonical_name = "NodeKind.CLASSRANGE"
NodeKind.CLASSMEMBER._fltk_canonical_name = "NodeKind.CLASSMEMBER"
NodeKind.CLASSRANGEATOM._fltk_canonical_name = "NodeKind.CLASSRANGEATOM"
NodeKind.CLASSCHAR._fltk_canonical_name = "NodeKind.CLASSCHAR"
NodeKind.CLASSESCAPE._fltk_canonical_name = "NodeKind.CLASSESCAPE"
NodeKind.CLASSESCAPEBODY._fltk_canonical_name = "NodeKind.CLASSESCAPEBODY"
NodeKind.CLASSCHARESCAPE._fltk_canonical_name = "NodeKind.CLASSCHARESCAPE"
NodeKind.ESCAPE._fltk_canonical_name = "NodeKind.ESCAPE"
NodeKind.ESCAPEBODY._fltk_canonical_name = "NodeKind.ESCAPEBODY"
NodeKind.CLASSSHORTHAND._fltk_canonical_name = "NodeKind.CLASSSHORTHAND"
NodeKind.ASSERTION._fltk_canonical_name = "NodeKind.ASSERTION"
NodeKind.ANCHORESCAPE._fltk_canonical_name = "NodeKind.ANCHORESCAPE"
NodeKind.CHARESCAPE._fltk_canonical_name = "NodeKind.CHARESCAPE"
NodeKind.CONTROLESCAPE._fltk_canonical_name = "NodeKind.CONTROLESCAPE"
NodeKind.HEXESCAPE._fltk_canonical_name = "NodeKind.HEXESCAPE"
NodeKind.UNICODEESCAPE._fltk_canonical_name = "NodeKind.UNICODEESCAPE"
NodeKind.METAESCAPE._fltk_canonical_name = "NodeKind.METAESCAPE"
NodeKind.LITERALCHAR._fltk_canonical_name = "NodeKind.LITERALCHAR"
NodeKind.TRIVIA._fltk_canonical_name = "NodeKind.TRIVIA"


def _get_native_span_type():
    m = sys.modules.get("fltk._native")
    return m.Span if m is not None else None


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

    kind: typing.Literal[NodeKind.REGEX] = NodeKind.REGEX
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation]] = dataclasses.field(default_factory=list)

    def append(self, child: Alternation, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Alternation], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Regex) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Alternation) -> None:
        if not isinstance(child, Alternation):
            msg = f"Regex: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Regex.Label)):
            _cn = "Regex"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Alternation, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Alternation]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Regex.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Alternation, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Regex.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_alternation(self, child: Alternation) -> None:
        self.children.append((Regex.Label.ALTERNATION, child))

    def extend_alternation(self, children: typing.Iterable[Alternation]) -> None:
        self.children.extend((Regex.Label.ALTERNATION, child) for child in children)

    def children_alternation(self) -> typing.Iterator[Alternation]:
        return (child for (label, child) in self.children if label == Regex.Label.ALTERNATION)

    def child_alternation(self) -> Alternation:
        children = list(self.children_alternation())
        if (n := len(children)) != 1:
            msg = f"Expected one alternation child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_alternation(self) -> Alternation | None:
        children = list(self.children_alternation())
        if (n := len(children)) > 1:
            msg = f"Expected at most one alternation child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.ALTERNATION] = NodeKind.ALTERNATION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation | Concatenation]] = dataclasses.field(default_factory=list)

    def append(self, child: Alternation | Concatenation, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Alternation | Concatenation], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Alternation) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation | Concatenation]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Alternation | Concatenation) -> None:
        if not isinstance(child, Alternation | Concatenation):
            msg = f"Alternation: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Alternation.Label)):
            _cn = "Alternation"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Alternation | Concatenation, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Alternation | Concatenation]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Alternation.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Alternation | Concatenation, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Alternation.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_branch(self, child: Concatenation) -> None:
        self.children.append((Alternation.Label.BRANCH, child))

    def extend_branch(self, children: typing.Iterable[Concatenation]) -> None:
        self.children.extend((Alternation.Label.BRANCH, child) for child in children)

    def children_branch(self) -> typing.Iterator[Concatenation]:
        return (
            typing.cast("Concatenation", child) for (label, child) in self.children if label == Alternation.Label.BRANCH
        )

    def child_branch(self) -> Concatenation:
        children = list(self.children_branch())
        if (n := len(children)) != 1:
            msg = f"Expected one branch child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_branch(self) -> Concatenation | None:
        children = list(self.children_branch())
        if (n := len(children)) > 1:
            msg = f"Expected at most one branch child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_left(self, child: Alternation) -> None:
        self.children.append((Alternation.Label.LEFT, child))

    def extend_left(self, children: typing.Iterable[Alternation]) -> None:
        self.children.extend((Alternation.Label.LEFT, child) for child in children)

    def children_left(self) -> typing.Iterator[Alternation]:
        return (
            typing.cast("Alternation", child) for (label, child) in self.children if label == Alternation.Label.LEFT
        )

    def child_left(self) -> Alternation:
        children = list(self.children_left())
        if (n := len(children)) != 1:
            msg = f"Expected one left child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_left(self) -> Alternation | None:
        children = list(self.children_left())
        if (n := len(children)) > 1:
            msg = f"Expected at most one left child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_right(self, child: Concatenation) -> None:
        self.children.append((Alternation.Label.RIGHT, child))

    def extend_right(self, children: typing.Iterable[Concatenation]) -> None:
        self.children.extend((Alternation.Label.RIGHT, child) for child in children)

    def children_right(self) -> typing.Iterator[Concatenation]:
        return (
            typing.cast("Concatenation", child) for (label, child) in self.children if label == Alternation.Label.RIGHT
        )

    def child_right(self) -> Concatenation:
        children = list(self.children_right())
        if (n := len(children)) != 1:
            msg = f"Expected one right child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_right(self) -> Concatenation | None:
        children = list(self.children_right())
        if (n := len(children)) > 1:
            msg = f"Expected at most one right child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CONCATENATION] = NodeKind.CONCATENATION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Concatenation | Repetition]] = dataclasses.field(default_factory=list)

    def append(self, child: Concatenation | Repetition, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Concatenation | Repetition], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Concatenation) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Concatenation | Repetition]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Concatenation | Repetition) -> None:
        if not isinstance(child, Concatenation | Repetition):
            msg = f"Concatenation: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Concatenation.Label)):
            _cn = "Concatenation"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Concatenation | Repetition, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Concatenation | Repetition]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Concatenation.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Concatenation | Repetition, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Concatenation.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_head(self, child: Concatenation) -> None:
        self.children.append((Concatenation.Label.HEAD, child))

    def extend_head(self, children: typing.Iterable[Concatenation]) -> None:
        self.children.extend((Concatenation.Label.HEAD, child) for child in children)

    def children_head(self) -> typing.Iterator[Concatenation]:
        return (
            typing.cast("Concatenation", child) for (label, child) in self.children if label == Concatenation.Label.HEAD
        )

    def child_head(self) -> Concatenation:
        children = list(self.children_head())
        if (n := len(children)) != 1:
            msg = f"Expected one head child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_head(self) -> Concatenation | None:
        children = list(self.children_head())
        if (n := len(children)) > 1:
            msg = f"Expected at most one head child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_single(self, child: Repetition) -> None:
        self.children.append((Concatenation.Label.SINGLE, child))

    def extend_single(self, children: typing.Iterable[Repetition]) -> None:
        self.children.extend((Concatenation.Label.SINGLE, child) for child in children)

    def children_single(self) -> typing.Iterator[Repetition]:
        return (
            typing.cast("Repetition", child) for (label, child) in self.children if label == Concatenation.Label.SINGLE
        )

    def child_single(self) -> Repetition:
        children = list(self.children_single())
        if (n := len(children)) != 1:
            msg = f"Expected one single child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_single(self) -> Repetition | None:
        children = list(self.children_single())
        if (n := len(children)) > 1:
            msg = f"Expected at most one single child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_tail(self, child: Repetition) -> None:
        self.children.append((Concatenation.Label.TAIL, child))

    def extend_tail(self, children: typing.Iterable[Repetition]) -> None:
        self.children.extend((Concatenation.Label.TAIL, child) for child in children)

    def children_tail(self) -> typing.Iterator[Repetition]:
        return (
            typing.cast("Repetition", child) for (label, child) in self.children if label == Concatenation.Label.TAIL
        )

    def child_tail(self) -> Repetition:
        children = list(self.children_tail())
        if (n := len(children)) != 1:
            msg = f"Expected one tail child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_tail(self) -> Repetition | None:
        children = list(self.children_tail())
        if (n := len(children)) > 1:
            msg = f"Expected at most one tail child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.REPETITION] = NodeKind.REPETITION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Atom | Quantifier]] = dataclasses.field(default_factory=list)

    def append(self, child: Atom | Quantifier, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Atom | Quantifier], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Repetition) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Atom | Quantifier]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Atom | Quantifier) -> None:
        if not isinstance(child, Atom | Quantifier):
            msg = f"Repetition: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Repetition.Label)):
            _cn = "Repetition"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Atom | Quantifier, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Atom | Quantifier]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Repetition.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Atom | Quantifier, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Repetition.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_atom(self, child: Atom) -> None:
        self.children.append((Repetition.Label.ATOM, child))

    def extend_atom(self, children: typing.Iterable[Atom]) -> None:
        self.children.extend((Repetition.Label.ATOM, child) for child in children)

    def children_atom(self) -> typing.Iterator[Atom]:
        return (typing.cast("Atom", child) for (label, child) in self.children if label == Repetition.Label.ATOM)

    def child_atom(self) -> Atom:
        children = list(self.children_atom())
        if (n := len(children)) != 1:
            msg = f"Expected one atom child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_atom(self) -> Atom | None:
        children = list(self.children_atom())
        if (n := len(children)) > 1:
            msg = f"Expected at most one atom child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_quantifier(self, child: Quantifier) -> None:
        self.children.append((Repetition.Label.QUANTIFIER, child))

    def extend_quantifier(self, children: typing.Iterable[Quantifier]) -> None:
        self.children.extend((Repetition.Label.QUANTIFIER, child) for child in children)

    def children_quantifier(self) -> typing.Iterator[Quantifier]:
        return (
            typing.cast("Quantifier", child) for (label, child) in self.children if label == Repetition.Label.QUANTIFIER
        )

    def child_quantifier(self) -> Quantifier:
        children = list(self.children_quantifier())
        if (n := len(children)) != 1:
            msg = f"Expected one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_quantifier(self) -> Quantifier | None:
        children = list(self.children_quantifier())
        if (n := len(children)) > 1:
            msg = f"Expected at most one quantifier child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.QUANTIFIER] = NodeKind.QUANTIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Quantifier) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Quantifier._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (Bounded, fltk.fegen.pyrt.terminalsrc.Span)
            Quantifier._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Quantifier._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Quantifier._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Quantifier: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Quantifier.Label)):
            _cn = "Quantifier"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Quantifier.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Quantifier.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_bound(self, child: Bounded) -> None:
        self.children.append((Quantifier.Label.BOUND, child))

    def extend_bound(self, children: typing.Iterable[Bounded]) -> None:
        self.children.extend((Quantifier.Label.BOUND, child) for child in children)

    def children_bound(self) -> typing.Iterator[Bounded]:
        return (typing.cast("Bounded", child) for (label, child) in self.children if label == Quantifier.Label.BOUND)

    def child_bound(self) -> Bounded:
        children = list(self.children_bound())
        if (n := len(children)) != 1:
            msg = f"Expected one bound child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_bound(self) -> Bounded | None:
        children = list(self.children_bound())
        if (n := len(children)) > 1:
            msg = f"Expected at most one bound child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_lazy(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.LAZY, child))

    def extend_lazy(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Quantifier.Label.LAZY, child) for child in children)

    def children_lazy(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Quantifier.Label.LAZY
        )

    def child_lazy(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_lazy())
        if (n := len(children)) != 1:
            msg = f"Expected one lazy child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_lazy(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_lazy())
        if (n := len(children)) > 1:
            msg = f"Expected at most one lazy child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_one_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.ONE_OR_MORE, child))

    def extend_one_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Quantifier.Label.ONE_OR_MORE, child) for child in children)

    def children_one_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Quantifier.Label.ONE_OR_MORE
        )

    def child_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_one_or_more())
        if (n := len(children)) != 1:
            msg = f"Expected one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_one_or_more())
        if (n := len(children)) > 1:
            msg = f"Expected at most one one_or_more child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_optional(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.OPTIONAL, child))

    def extend_optional(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Quantifier.Label.OPTIONAL, child) for child in children)

    def children_optional(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Quantifier.Label.OPTIONAL
        )

    def child_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_optional())
        if (n := len(children)) != 1:
            msg = f"Expected one optional child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_optional())
        if (n := len(children)) > 1:
            msg = f"Expected at most one optional child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_zero_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Quantifier.Label.ZERO_OR_MORE, child))

    def extend_zero_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Quantifier.Label.ZERO_OR_MORE, child) for child in children)

    def children_zero_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Quantifier.Label.ZERO_OR_MORE
        )

    def child_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_zero_or_more())
        if (n := len(children)) != 1:
            msg = f"Expected one zero_or_more child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_zero_or_more())
        if (n := len(children)) > 1:
            msg = f"Expected at most one zero_or_more child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.BOUNDED] = NodeKind.BOUNDED
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Number]] = dataclasses.field(default_factory=list)

    def append(self, child: Number, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Number], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Bounded) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Number]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Number) -> None:
        if not isinstance(child, Number):
            msg = f"Bounded: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Bounded.Label)):
            _cn = "Bounded"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Number, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Number]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Bounded.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Number, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Bounded.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_count(self, child: Number) -> None:
        self.children.append((Bounded.Label.COUNT, child))

    def extend_count(self, children: typing.Iterable[Number]) -> None:
        self.children.extend((Bounded.Label.COUNT, child) for child in children)

    def children_count(self) -> typing.Iterator[Number]:
        return (child for (label, child) in self.children if label == Bounded.Label.COUNT)

    def child_count(self) -> Number:
        children = list(self.children_count())
        if (n := len(children)) != 1:
            msg = f"Expected one count child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_count(self) -> Number | None:
        children = list(self.children_count())
        if (n := len(children)) > 1:
            msg = f"Expected at most one count child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_max(self, child: Number) -> None:
        self.children.append((Bounded.Label.MAX, child))

    def extend_max(self, children: typing.Iterable[Number]) -> None:
        self.children.extend((Bounded.Label.MAX, child) for child in children)

    def children_max(self) -> typing.Iterator[Number]:
        return (child for (label, child) in self.children if label == Bounded.Label.MAX)

    def child_max(self) -> Number:
        children = list(self.children_max())
        if (n := len(children)) != 1:
            msg = f"Expected one max child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_max(self) -> Number | None:
        children = list(self.children_max())
        if (n := len(children)) > 1:
            msg = f"Expected at most one max child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_min(self, child: Number) -> None:
        self.children.append((Bounded.Label.MIN, child))

    def extend_min(self, children: typing.Iterable[Number]) -> None:
        self.children.extend((Bounded.Label.MIN, child) for child in children)

    def children_min(self) -> typing.Iterator[Number]:
        return (child for (label, child) in self.children if label == Bounded.Label.MIN)

    def child_min(self) -> Number:
        children = list(self.children_min())
        if (n := len(children)) != 1:
            msg = f"Expected one min child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_min(self) -> Number | None:
        children = list(self.children_min())
        if (n := len(children)) > 1:
            msg = f"Expected at most one min child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.NUMBER] = NodeKind.NUMBER
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

    def extend_children(self, other: Number) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Number._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Number._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Number._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Number._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Number: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Number.Label)):
            _cn = "Number"
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
            msg = f"Number.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Number.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_digits(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Number.Label.DIGITS, child))

    def extend_digits(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Number.Label.DIGITS, child) for child in children)

    def children_digits(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Number.Label.DIGITS)

    def child_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_digits())
        if (n := len(children)) != 1:
            msg = f"Expected one digits child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_digits())
        if (n := len(children)) > 1:
            msg = f"Expected at most one digits child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.ATOM] = NodeKind.ATOM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self, child: Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar, label: Label | None = None
    ) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Atom) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar
    ) -> None:
        if not isinstance(child, Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar):
            msg = f"Atom: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Atom.Label)):
            _cn = "Atom"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar,
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
        child: Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar,
        label: Label | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Atom.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor(self, child: Anchor) -> None:
        self.children.append((Atom.Label.ANCHOR, child))

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None:
        self.children.extend((Atom.Label.ANCHOR, child) for child in children)

    def children_anchor(self) -> typing.Iterator[Anchor]:
        return (typing.cast("Anchor", child) for (label, child) in self.children if label == Atom.Label.ANCHOR)

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

    def append_char_class(self, child: CharClass) -> None:
        self.children.append((Atom.Label.CHAR_CLASS, child))

    def extend_char_class(self, children: typing.Iterable[CharClass]) -> None:
        self.children.extend((Atom.Label.CHAR_CLASS, child) for child in children)

    def children_char_class(self) -> typing.Iterator[CharClass]:
        return (typing.cast("CharClass", child) for (label, child) in self.children if label == Atom.Label.CHAR_CLASS)

    def child_char_class(self) -> CharClass:
        children = list(self.children_char_class())
        if (n := len(children)) != 1:
            msg = f"Expected one char_class child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_char_class(self) -> CharClass | None:
        children = list(self.children_char_class())
        if (n := len(children)) > 1:
            msg = f"Expected at most one char_class child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_dot(self, child: Dot) -> None:
        self.children.append((Atom.Label.DOT, child))

    def extend_dot(self, children: typing.Iterable[Dot]) -> None:
        self.children.extend((Atom.Label.DOT, child) for child in children)

    def children_dot(self) -> typing.Iterator[Dot]:
        return (typing.cast("Dot", child) for (label, child) in self.children if label == Atom.Label.DOT)

    def child_dot(self) -> Dot:
        children = list(self.children_dot())
        if (n := len(children)) != 1:
            msg = f"Expected one dot child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_dot(self) -> Dot | None:
        children = list(self.children_dot())
        if (n := len(children)) > 1:
            msg = f"Expected at most one dot child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_escape(self, child: Escape) -> None:
        self.children.append((Atom.Label.ESCAPE, child))

    def extend_escape(self, children: typing.Iterable[Escape]) -> None:
        self.children.extend((Atom.Label.ESCAPE, child) for child in children)

    def children_escape(self) -> typing.Iterator[Escape]:
        return (typing.cast("Escape", child) for (label, child) in self.children if label == Atom.Label.ESCAPE)

    def child_escape(self) -> Escape:
        children = list(self.children_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_escape(self) -> Escape | None:
        children = list(self.children_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_group(self, child: Group) -> None:
        self.children.append((Atom.Label.GROUP, child))

    def extend_group(self, children: typing.Iterable[Group]) -> None:
        self.children.extend((Atom.Label.GROUP, child) for child in children)

    def children_group(self) -> typing.Iterator[Group]:
        return (typing.cast("Group", child) for (label, child) in self.children if label == Atom.Label.GROUP)

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

    def append_inline_flags(self, child: InlineFlags) -> None:
        self.children.append((Atom.Label.INLINE_FLAGS, child))

    def extend_inline_flags(self, children: typing.Iterable[InlineFlags]) -> None:
        self.children.extend((Atom.Label.INLINE_FLAGS, child) for child in children)

    def children_inline_flags(self) -> typing.Iterator[InlineFlags]:
        return (
            typing.cast("InlineFlags", child) for (label, child) in self.children if label == Atom.Label.INLINE_FLAGS
        )

    def child_inline_flags(self) -> InlineFlags:
        children = list(self.children_inline_flags())
        if (n := len(children)) != 1:
            msg = f"Expected one inline_flags child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_inline_flags(self) -> InlineFlags | None:
        children = list(self.children_inline_flags())
        if (n := len(children)) > 1:
            msg = f"Expected at most one inline_flags child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_literal_char(self, child: LiteralChar) -> None:
        self.children.append((Atom.Label.LITERAL_CHAR, child))

    def extend_literal_char(self, children: typing.Iterable[LiteralChar]) -> None:
        self.children.extend((Atom.Label.LITERAL_CHAR, child) for child in children)

    def children_literal_char(self) -> typing.Iterator[LiteralChar]:
        return (
            typing.cast("LiteralChar", child) for (label, child) in self.children if label == Atom.Label.LITERAL_CHAR
        )

    def child_literal_char(self) -> LiteralChar:
        children = list(self.children_literal_char())
        if (n := len(children)) != 1:
            msg = f"Expected one literal_char child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_literal_char(self) -> LiteralChar | None:
        children = list(self.children_literal_char())
        if (n := len(children)) > 1:
            msg = f"Expected at most one literal_char child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.DOT] = NodeKind.DOT
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

    def extend_children(self, other: Dot) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Dot._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Dot._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Dot._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Dot._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Dot: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Dot.Label)):
            _cn = "Dot"
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
            msg = f"Dot.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Dot.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Dot.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Dot.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Dot.Label.VALUE)

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

    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
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

    def extend_children(self, other: Anchor) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Anchor._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Anchor._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Anchor._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Anchor._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Anchor: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Anchor.Label)):
            _cn = "Anchor"
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
            msg = f"Anchor.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Anchor.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_caret(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Anchor.Label.CARET, child))

    def extend_caret(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Anchor.Label.CARET, child) for child in children)

    def children_caret(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Anchor.Label.CARET)

    def child_caret(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_caret())
        if (n := len(children)) != 1:
            msg = f"Expected one caret child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_caret(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_caret())
        if (n := len(children)) > 1:
            msg = f"Expected at most one caret child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_dollar(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Anchor.Label.DOLLAR, child))

    def extend_dollar(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Anchor.Label.DOLLAR, child) for child in children)

    def children_dollar(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Anchor.Label.DOLLAR)

    def child_dollar(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_dollar())
        if (n := len(children)) != 1:
            msg = f"Expected one dollar child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_dollar(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_dollar())
        if (n := len(children)) > 1:
            msg = f"Expected at most one dollar child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.GROUP] = NodeKind.GROUP
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Capturing | FlagGroup | NonCapturing]] = dataclasses.field(default_factory=list)

    def append(self, child: Capturing | FlagGroup | NonCapturing, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self, children: typing.Iterable[Capturing | FlagGroup | NonCapturing], label: Label | None = None
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Group) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Capturing | FlagGroup | NonCapturing]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Capturing | FlagGroup | NonCapturing) -> None:
        if not isinstance(child, Capturing | FlagGroup | NonCapturing):
            msg = f"Group: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Group.Label)):
            _cn = "Group"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Capturing | FlagGroup | NonCapturing, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Capturing | FlagGroup | NonCapturing]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Group.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Capturing | FlagGroup | NonCapturing, label: Label | None = None) -> None:
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

    def append_capturing(self, child: Capturing) -> None:
        self.children.append((Group.Label.CAPTURING, child))

    def extend_capturing(self, children: typing.Iterable[Capturing]) -> None:
        self.children.extend((Group.Label.CAPTURING, child) for child in children)

    def children_capturing(self) -> typing.Iterator[Capturing]:
        return (typing.cast("Capturing", child) for (label, child) in self.children if label == Group.Label.CAPTURING)

    def child_capturing(self) -> Capturing:
        children = list(self.children_capturing())
        if (n := len(children)) != 1:
            msg = f"Expected one capturing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_capturing(self) -> Capturing | None:
        children = list(self.children_capturing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one capturing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_flag_group(self, child: FlagGroup) -> None:
        self.children.append((Group.Label.FLAG_GROUP, child))

    def extend_flag_group(self, children: typing.Iterable[FlagGroup]) -> None:
        self.children.extend((Group.Label.FLAG_GROUP, child) for child in children)

    def children_flag_group(self) -> typing.Iterator[FlagGroup]:
        return (typing.cast("FlagGroup", child) for (label, child) in self.children if label == Group.Label.FLAG_GROUP)

    def child_flag_group(self) -> FlagGroup:
        children = list(self.children_flag_group())
        if (n := len(children)) != 1:
            msg = f"Expected one flag_group child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_flag_group(self) -> FlagGroup | None:
        children = list(self.children_flag_group())
        if (n := len(children)) > 1:
            msg = f"Expected at most one flag_group child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_non_capturing(self, child: NonCapturing) -> None:
        self.children.append((Group.Label.NON_CAPTURING, child))

    def extend_non_capturing(self, children: typing.Iterable[NonCapturing]) -> None:
        self.children.extend((Group.Label.NON_CAPTURING, child) for child in children)

    def children_non_capturing(self) -> typing.Iterator[NonCapturing]:
        return (
            typing.cast("NonCapturing", child) for (label, child) in self.children if label == Group.Label.NON_CAPTURING
        )

    def child_non_capturing(self) -> NonCapturing:
        children = list(self.children_non_capturing())
        if (n := len(children)) != 1:
            msg = f"Expected one non_capturing child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_non_capturing(self) -> NonCapturing | None:
        children = list(self.children_non_capturing())
        if (n := len(children)) > 1:
            msg = f"Expected at most one non_capturing child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.NONCAPTURING] = NodeKind.NONCAPTURING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation]] = dataclasses.field(default_factory=list)

    def append(self, child: Alternation, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Alternation], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: NonCapturing) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Alternation) -> None:
        if not isinstance(child, Alternation):
            msg = f"NonCapturing: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, NonCapturing.Label)):
            _cn = "NonCapturing"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Alternation, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Alternation]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NonCapturing.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Alternation, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"NonCapturing.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_body(self, child: Alternation) -> None:
        self.children.append((NonCapturing.Label.BODY, child))

    def extend_body(self, children: typing.Iterable[Alternation]) -> None:
        self.children.extend((NonCapturing.Label.BODY, child) for child in children)

    def children_body(self) -> typing.Iterator[Alternation]:
        return (child for (label, child) in self.children if label == NonCapturing.Label.BODY)

    def child_body(self) -> Alternation:
        children = list(self.children_body())
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> Alternation | None:
        children = list(self.children_body())
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.FLAGGROUP] = NodeKind.FLAGGROUP
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation | FlagChars]] = dataclasses.field(default_factory=list)

    def append(self, child: Alternation | FlagChars, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Alternation | FlagChars], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: FlagGroup) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation | FlagChars]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Alternation | FlagChars) -> None:
        if not isinstance(child, Alternation | FlagChars):
            msg = f"FlagGroup: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, FlagGroup.Label)):
            _cn = "FlagGroup"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Alternation | FlagChars, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Alternation | FlagChars]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FlagGroup.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Alternation | FlagChars, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"FlagGroup.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_body(self, child: Alternation) -> None:
        self.children.append((FlagGroup.Label.BODY, child))

    def extend_body(self, children: typing.Iterable[Alternation]) -> None:
        self.children.extend((FlagGroup.Label.BODY, child) for child in children)

    def children_body(self) -> typing.Iterator[Alternation]:
        return (typing.cast("Alternation", child) for (label, child) in self.children if label == FlagGroup.Label.BODY)

    def child_body(self) -> Alternation:
        children = list(self.children_body())
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> Alternation | None:
        children = list(self.children_body())
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_flags(self, child: FlagChars) -> None:
        self.children.append((FlagGroup.Label.FLAGS, child))

    def extend_flags(self, children: typing.Iterable[FlagChars]) -> None:
        self.children.extend((FlagGroup.Label.FLAGS, child) for child in children)

    def children_flags(self) -> typing.Iterator[FlagChars]:
        return (typing.cast("FlagChars", child) for (label, child) in self.children if label == FlagGroup.Label.FLAGS)

    def child_flags(self) -> FlagChars:
        children = list(self.children_flags())
        if (n := len(children)) != 1:
            msg = f"Expected one flags child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_flags(self) -> FlagChars | None:
        children = list(self.children_flags())
        if (n := len(children)) > 1:
            msg = f"Expected at most one flags child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CAPTURING] = NodeKind.CAPTURING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Alternation]] = dataclasses.field(default_factory=list)

    def append(self, child: Alternation, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[Alternation], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Capturing) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Alternation]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: Alternation) -> None:
        if not isinstance(child, Alternation):
            msg = f"Capturing: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Capturing.Label)):
            _cn = "Capturing"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: Alternation, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, Alternation]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Capturing.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: Alternation, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Capturing.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_body(self, child: Alternation) -> None:
        self.children.append((Capturing.Label.BODY, child))

    def extend_body(self, children: typing.Iterable[Alternation]) -> None:
        self.children.extend((Capturing.Label.BODY, child) for child in children)

    def children_body(self) -> typing.Iterator[Alternation]:
        return (child for (label, child) in self.children if label == Capturing.Label.BODY)

    def child_body(self) -> Alternation:
        children = list(self.children_body())
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> Alternation | None:
        children = list(self.children_body())
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.INLINEFLAGS] = NodeKind.INLINEFLAGS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, FlagChars]] = dataclasses.field(default_factory=list)

    def append(self, child: FlagChars, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[FlagChars], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: InlineFlags) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, FlagChars]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: FlagChars) -> None:
        if not isinstance(child, FlagChars):
            msg = f"InlineFlags: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, InlineFlags.Label)):
            _cn = "InlineFlags"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: FlagChars, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, FlagChars]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"InlineFlags.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: FlagChars, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"InlineFlags.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_flags(self, child: FlagChars) -> None:
        self.children.append((InlineFlags.Label.FLAGS, child))

    def extend_flags(self, children: typing.Iterable[FlagChars]) -> None:
        self.children.extend((InlineFlags.Label.FLAGS, child) for child in children)

    def children_flags(self) -> typing.Iterator[FlagChars]:
        return (child for (label, child) in self.children if label == InlineFlags.Label.FLAGS)

    def child_flags(self) -> FlagChars:
        children = list(self.children_flags())
        if (n := len(children)) != 1:
            msg = f"Expected one flags child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_flags(self) -> FlagChars | None:
        children = list(self.children_flags())
        if (n := len(children)) > 1:
            msg = f"Expected at most one flags child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.FLAGCHARS] = NodeKind.FLAGCHARS
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

    def extend_children(self, other: FlagChars) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = FlagChars._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            FlagChars._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            FlagChars._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = FlagChars._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"FlagChars: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, FlagChars.Label)):
            _cn = "FlagChars"
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
            msg = f"FlagChars.remove_at: index {index} out of range ({n} children)"
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
            msg = f"FlagChars.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((FlagChars.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((FlagChars.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == FlagChars.Label.VALUE)

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

    kind: typing.Literal[NodeKind.CHARCLASS] = NodeKind.CHARCLASS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: CharClass) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = CharClass._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (ClassBody, fltk.fegen.pyrt.terminalsrc.Span)
            CharClass._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            CharClass._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = CharClass._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"CharClass: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, CharClass.Label)):
            _cn = "CharClass"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CharClass.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CharClass.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_class_body(self, child: ClassBody) -> None:
        self.children.append((CharClass.Label.CLASS_BODY, child))

    def extend_class_body(self, children: typing.Iterable[ClassBody]) -> None:
        self.children.extend((CharClass.Label.CLASS_BODY, child) for child in children)

    def children_class_body(self) -> typing.Iterator[ClassBody]:
        return (
            typing.cast("ClassBody", child) for (label, child) in self.children if label == CharClass.Label.CLASS_BODY
        )

    def child_class_body(self) -> ClassBody:
        children = list(self.children_class_body())
        if (n := len(children)) != 1:
            msg = f"Expected one class_body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_body(self) -> ClassBody | None:
        children = list(self.children_class_body())
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_negated(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((CharClass.Label.NEGATED, child))

    def extend_negated(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((CharClass.Label.NEGATED, child) for child in children)

    def children_negated(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == CharClass.Label.NEGATED
        )

    def child_negated(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_negated())
        if (n := len(children)) != 1:
            msg = f"Expected one negated child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_negated(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_negated())
        if (n := len(children)) > 1:
            msg = f"Expected at most one negated child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CLASSBODY] = NodeKind.CLASSBODY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ClassBody) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = ClassBody._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (ClassItem, fltk.fegen.pyrt.terminalsrc.Span)
            ClassBody._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            ClassBody._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = ClassBody._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"ClassBody: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassBody.Label)):
            _cn = "ClassBody"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassBody.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassBody.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_items(self, child: ClassItem) -> None:
        self.children.append((ClassBody.Label.ITEMS, child))

    def extend_items(self, children: typing.Iterable[ClassItem]) -> None:
        self.children.extend((ClassBody.Label.ITEMS, child) for child in children)

    def children_items(self) -> typing.Iterator[ClassItem]:
        return (typing.cast("ClassItem", child) for (label, child) in self.children if label == ClassBody.Label.ITEMS)

    def child_items(self) -> ClassItem:
        children = list(self.children_items())
        if (n := len(children)) != 1:
            msg = f"Expected one items child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_items(self) -> ClassItem | None:
        children = list(self.children_items())
        if (n := len(children)) > 1:
            msg = f"Expected at most one items child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_lead_dash(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ClassBody.Label.LEAD_DASH, child))

    def extend_lead_dash(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((ClassBody.Label.LEAD_DASH, child) for child in children)

    def children_lead_dash(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == ClassBody.Label.LEAD_DASH
        )

    def child_lead_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_lead_dash())
        if (n := len(children)) != 1:
            msg = f"Expected one lead_dash child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_lead_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_lead_dash())
        if (n := len(children)) > 1:
            msg = f"Expected at most one lead_dash child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_trail_dash(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ClassBody.Label.TRAIL_DASH, child))

    def extend_trail_dash(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((ClassBody.Label.TRAIL_DASH, child) for child in children)

    def children_trail_dash(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == ClassBody.Label.TRAIL_DASH
        )

    def child_trail_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_trail_dash())
        if (n := len(children)) != 1:
            msg = f"Expected one trail_dash child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_trail_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_trail_dash())
        if (n := len(children)) > 1:
            msg = f"Expected at most one trail_dash child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CLASSITEM] = NodeKind.CLASSITEM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassMember | ClassRange]] = dataclasses.field(default_factory=list)

    def append(self, child: ClassMember | ClassRange, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[ClassMember | ClassRange], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ClassItem) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassMember | ClassRange]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: ClassMember | ClassRange) -> None:
        if not isinstance(child, ClassMember | ClassRange):
            msg = f"ClassItem: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassItem.Label)):
            _cn = "ClassItem"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: ClassMember | ClassRange, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, ClassMember | ClassRange]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassItem.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: ClassMember | ClassRange, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassItem.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_class_member(self, child: ClassMember) -> None:
        self.children.append((ClassItem.Label.CLASS_MEMBER, child))

    def extend_class_member(self, children: typing.Iterable[ClassMember]) -> None:
        self.children.extend((ClassItem.Label.CLASS_MEMBER, child) for child in children)

    def children_class_member(self) -> typing.Iterator[ClassMember]:
        return (
            typing.cast("ClassMember", child)
            for (label, child) in self.children
            if label == ClassItem.Label.CLASS_MEMBER
        )

    def child_class_member(self) -> ClassMember:
        children = list(self.children_class_member())
        if (n := len(children)) != 1:
            msg = f"Expected one class_member child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_member(self) -> ClassMember | None:
        children = list(self.children_class_member())
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_member child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_range(self, child: ClassRange) -> None:
        self.children.append((ClassItem.Label.CLASS_RANGE, child))

    def extend_class_range(self, children: typing.Iterable[ClassRange]) -> None:
        self.children.extend((ClassItem.Label.CLASS_RANGE, child) for child in children)

    def children_class_range(self) -> typing.Iterator[ClassRange]:
        return (
            typing.cast("ClassRange", child) for (label, child) in self.children if label == ClassItem.Label.CLASS_RANGE
        )

    def child_class_range(self) -> ClassRange:
        children = list(self.children_class_range())
        if (n := len(children)) != 1:
            msg = f"Expected one class_range child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_range(self) -> ClassRange | None:
        children = list(self.children_class_range())
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_range child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CLASSRANGE] = NodeKind.CLASSRANGE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassRangeAtom]] = dataclasses.field(default_factory=list)

    def append(self, child: ClassRangeAtom, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[ClassRangeAtom], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ClassRange) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassRangeAtom]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: ClassRangeAtom) -> None:
        if not isinstance(child, ClassRangeAtom):
            msg = f"ClassRange: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassRange.Label)):
            _cn = "ClassRange"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: ClassRangeAtom, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, ClassRangeAtom]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassRange.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: ClassRangeAtom, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassRange.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_hi(self, child: ClassRangeAtom) -> None:
        self.children.append((ClassRange.Label.HI, child))

    def extend_hi(self, children: typing.Iterable[ClassRangeAtom]) -> None:
        self.children.extend((ClassRange.Label.HI, child) for child in children)

    def children_hi(self) -> typing.Iterator[ClassRangeAtom]:
        return (child for (label, child) in self.children if label == ClassRange.Label.HI)

    def child_hi(self) -> ClassRangeAtom:
        children = list(self.children_hi())
        if (n := len(children)) != 1:
            msg = f"Expected one hi child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_hi(self) -> ClassRangeAtom | None:
        children = list(self.children_hi())
        if (n := len(children)) > 1:
            msg = f"Expected at most one hi child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_lo(self, child: ClassRangeAtom) -> None:
        self.children.append((ClassRange.Label.LO, child))

    def extend_lo(self, children: typing.Iterable[ClassRangeAtom]) -> None:
        self.children.extend((ClassRange.Label.LO, child) for child in children)

    def children_lo(self) -> typing.Iterator[ClassRangeAtom]:
        return (child for (label, child) in self.children if label == ClassRange.Label.LO)

    def child_lo(self) -> ClassRangeAtom:
        children = list(self.children_lo())
        if (n := len(children)) != 1:
            msg = f"Expected one lo child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_lo(self) -> ClassRangeAtom | None:
        children = list(self.children_lo())
        if (n := len(children)) > 1:
            msg = f"Expected at most one lo child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CLASSMEMBER] = NodeKind.CLASSMEMBER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassChar | ClassEscape]] = dataclasses.field(default_factory=list)

    def append(self, child: ClassChar | ClassEscape, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[ClassChar | ClassEscape], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ClassMember) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassChar | ClassEscape]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: ClassChar | ClassEscape) -> None:
        if not isinstance(child, ClassChar | ClassEscape):
            msg = f"ClassMember: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassMember.Label)):
            _cn = "ClassMember"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: ClassChar | ClassEscape, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, ClassChar | ClassEscape]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassMember.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: ClassChar | ClassEscape, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassMember.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_class_char(self, child: ClassChar) -> None:
        self.children.append((ClassMember.Label.CLASS_CHAR, child))

    def extend_class_char(self, children: typing.Iterable[ClassChar]) -> None:
        self.children.extend((ClassMember.Label.CLASS_CHAR, child) for child in children)

    def children_class_char(self) -> typing.Iterator[ClassChar]:
        return (
            typing.cast("ClassChar", child) for (label, child) in self.children if label == ClassMember.Label.CLASS_CHAR
        )

    def child_class_char(self) -> ClassChar:
        children = list(self.children_class_char())
        if (n := len(children)) != 1:
            msg = f"Expected one class_char child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_char(self) -> ClassChar | None:
        children = list(self.children_class_char())
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_char child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_escape(self, child: ClassEscape) -> None:
        self.children.append((ClassMember.Label.CLASS_ESCAPE, child))

    def extend_class_escape(self, children: typing.Iterable[ClassEscape]) -> None:
        self.children.extend((ClassMember.Label.CLASS_ESCAPE, child) for child in children)

    def children_class_escape(self) -> typing.Iterator[ClassEscape]:
        return (
            typing.cast("ClassEscape", child)
            for (label, child) in self.children
            if label == ClassMember.Label.CLASS_ESCAPE
        )

    def child_class_escape(self) -> ClassEscape:
        children = list(self.children_class_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one class_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_escape(self) -> ClassEscape | None:
        children = list(self.children_class_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CLASSRANGEATOM] = NodeKind.CLASSRANGEATOM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassChar | ClassCharEscape]] = dataclasses.field(default_factory=list)

    def append(self, child: ClassChar | ClassCharEscape, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[ClassChar | ClassCharEscape], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ClassRangeAtom) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassChar | ClassCharEscape]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: ClassChar | ClassCharEscape) -> None:
        if not isinstance(child, ClassChar | ClassCharEscape):
            msg = f"ClassRangeAtom: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassRangeAtom.Label)):
            _cn = "ClassRangeAtom"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: ClassChar | ClassCharEscape, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, ClassChar | ClassCharEscape]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassRangeAtom.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: ClassChar | ClassCharEscape, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassRangeAtom.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_class_char(self, child: ClassChar) -> None:
        self.children.append((ClassRangeAtom.Label.CLASS_CHAR, child))

    def extend_class_char(self, children: typing.Iterable[ClassChar]) -> None:
        self.children.extend((ClassRangeAtom.Label.CLASS_CHAR, child) for child in children)

    def children_class_char(self) -> typing.Iterator[ClassChar]:
        return (
            typing.cast("ClassChar", child)
            for (label, child) in self.children
            if label == ClassRangeAtom.Label.CLASS_CHAR
        )

    def child_class_char(self) -> ClassChar:
        children = list(self.children_class_char())
        if (n := len(children)) != 1:
            msg = f"Expected one class_char child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_char(self) -> ClassChar | None:
        children = list(self.children_class_char())
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_char child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_char_escape(self, child: ClassCharEscape) -> None:
        self.children.append((ClassRangeAtom.Label.CLASS_CHAR_ESCAPE, child))

    def extend_class_char_escape(self, children: typing.Iterable[ClassCharEscape]) -> None:
        self.children.extend((ClassRangeAtom.Label.CLASS_CHAR_ESCAPE, child) for child in children)

    def children_class_char_escape(self) -> typing.Iterator[ClassCharEscape]:
        return (
            typing.cast("ClassCharEscape", child)
            for (label, child) in self.children
            if label == ClassRangeAtom.Label.CLASS_CHAR_ESCAPE
        )

    def child_class_char_escape(self) -> ClassCharEscape:
        children = list(self.children_class_char_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one class_char_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_char_escape(self) -> ClassCharEscape | None:
        children = list(self.children_class_char_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_char_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CLASSCHAR] = NodeKind.CLASSCHAR
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

    def extend_children(self, other: ClassChar) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = ClassChar._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            ClassChar._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            ClassChar._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = ClassChar._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"ClassChar: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassChar.Label)):
            _cn = "ClassChar"
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
            msg = f"ClassChar.remove_at: index {index} out of range ({n} children)"
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
            msg = f"ClassChar.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ClassChar.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((ClassChar.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == ClassChar.Label.VALUE)

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

    kind: typing.Literal[NodeKind.CLASSESCAPE] = NodeKind.CLASSESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ClassEscapeBody]] = dataclasses.field(default_factory=list)

    def append(self, child: ClassEscapeBody, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[ClassEscapeBody], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ClassEscape) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ClassEscapeBody]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: ClassEscapeBody) -> None:
        if not isinstance(child, ClassEscapeBody):
            msg = f"ClassEscape: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassEscape.Label)):
            _cn = "ClassEscape"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: ClassEscapeBody, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, ClassEscapeBody]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassEscape.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: ClassEscapeBody, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_body(self, child: ClassEscapeBody) -> None:
        self.children.append((ClassEscape.Label.BODY, child))

    def extend_body(self, children: typing.Iterable[ClassEscapeBody]) -> None:
        self.children.extend((ClassEscape.Label.BODY, child) for child in children)

    def children_body(self) -> typing.Iterator[ClassEscapeBody]:
        return (child for (label, child) in self.children if label == ClassEscape.Label.BODY)

    def child_body(self) -> ClassEscapeBody:
        children = list(self.children_body())
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> ClassEscapeBody | None:
        children = list(self.children_body())
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CLASSESCAPEBODY] = NodeKind.CLASSESCAPEBODY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CharEscape | ClassShorthand]] = dataclasses.field(default_factory=list)

    def append(self, child: CharEscape | ClassShorthand, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[CharEscape | ClassShorthand], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ClassEscapeBody) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, CharEscape | ClassShorthand]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: CharEscape | ClassShorthand) -> None:
        if not isinstance(child, CharEscape | ClassShorthand):
            msg = f"ClassEscapeBody: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassEscapeBody.Label)):
            _cn = "ClassEscapeBody"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: CharEscape | ClassShorthand, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, CharEscape | ClassShorthand]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassEscapeBody.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: CharEscape | ClassShorthand, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassEscapeBody.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_char_escape(self, child: CharEscape) -> None:
        self.children.append((ClassEscapeBody.Label.CHAR_ESCAPE, child))

    def extend_char_escape(self, children: typing.Iterable[CharEscape]) -> None:
        self.children.extend((ClassEscapeBody.Label.CHAR_ESCAPE, child) for child in children)

    def children_char_escape(self) -> typing.Iterator[CharEscape]:
        return (
            typing.cast("CharEscape", child)
            for (label, child) in self.children
            if label == ClassEscapeBody.Label.CHAR_ESCAPE
        )

    def child_char_escape(self) -> CharEscape:
        children = list(self.children_char_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one char_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_char_escape(self) -> CharEscape | None:
        children = list(self.children_char_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one char_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_shorthand(self, child: ClassShorthand) -> None:
        self.children.append((ClassEscapeBody.Label.CLASS_SHORTHAND, child))

    def extend_class_shorthand(self, children: typing.Iterable[ClassShorthand]) -> None:
        self.children.extend((ClassEscapeBody.Label.CLASS_SHORTHAND, child) for child in children)

    def children_class_shorthand(self) -> typing.Iterator[ClassShorthand]:
        return (
            typing.cast("ClassShorthand", child)
            for (label, child) in self.children
            if label == ClassEscapeBody.Label.CLASS_SHORTHAND
        )

    def child_class_shorthand(self) -> ClassShorthand:
        children = list(self.children_class_shorthand())
        if (n := len(children)) != 1:
            msg = f"Expected one class_shorthand child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_shorthand(self) -> ClassShorthand | None:
        children = list(self.children_class_shorthand())
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_shorthand child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CLASSCHARESCAPE] = NodeKind.CLASSCHARESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, CharEscape]] = dataclasses.field(default_factory=list)

    def append(self, child: CharEscape, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[CharEscape], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: ClassCharEscape) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, CharEscape]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: CharEscape) -> None:
        if not isinstance(child, CharEscape):
            msg = f"ClassCharEscape: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassCharEscape.Label)):
            _cn = "ClassCharEscape"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: CharEscape, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, CharEscape]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassCharEscape.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: CharEscape, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"ClassCharEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_body(self, child: CharEscape) -> None:
        self.children.append((ClassCharEscape.Label.BODY, child))

    def extend_body(self, children: typing.Iterable[CharEscape]) -> None:
        self.children.extend((ClassCharEscape.Label.BODY, child) for child in children)

    def children_body(self) -> typing.Iterator[CharEscape]:
        return (child for (label, child) in self.children if label == ClassCharEscape.Label.BODY)

    def child_body(self) -> CharEscape:
        children = list(self.children_body())
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> CharEscape | None:
        children = list(self.children_body())
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.ESCAPE] = NodeKind.ESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, EscapeBody]] = dataclasses.field(default_factory=list)

    def append(self, child: EscapeBody, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(self, children: typing.Iterable[EscapeBody], label: Label | None = None) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: Escape) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, EscapeBody]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: EscapeBody) -> None:
        if not isinstance(child, EscapeBody):
            msg = f"Escape: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Escape.Label)):
            _cn = "Escape"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(self, index: int, child: EscapeBody, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "insert")
        idx = operator.index(index)
        n = len(self.children)
        if idx < 0:
            idx = max(n + idx, 0)
        else:
            idx = min(idx, n)
        self.children.insert(idx, (label, child))

    def remove_at(self, index: int) -> tuple[Label | None, EscapeBody]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Escape.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(self, index: int, child: EscapeBody, label: Label | None = None) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Escape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_body(self, child: EscapeBody) -> None:
        self.children.append((Escape.Label.BODY, child))

    def extend_body(self, children: typing.Iterable[EscapeBody]) -> None:
        self.children.extend((Escape.Label.BODY, child) for child in children)

    def children_body(self) -> typing.Iterator[EscapeBody]:
        return (child for (label, child) in self.children if label == Escape.Label.BODY)

    def child_body(self) -> EscapeBody:
        children = list(self.children_body())
        if (n := len(children)) != 1:
            msg = f"Expected one body child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_body(self) -> EscapeBody | None:
        children = list(self.children_body())
        if (n := len(children)) > 1:
            msg = f"Expected at most one body child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.ESCAPEBODY] = NodeKind.ESCAPEBODY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, AnchorEscape | Assertion | CharEscape | ClassShorthand]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: AnchorEscape | Assertion | CharEscape | ClassShorthand, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[AnchorEscape | Assertion | CharEscape | ClassShorthand],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: EscapeBody) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, AnchorEscape | Assertion | CharEscape | ClassShorthand]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: AnchorEscape | Assertion | CharEscape | ClassShorthand) -> None:
        if not isinstance(child, AnchorEscape | Assertion | CharEscape | ClassShorthand):
            msg = f"EscapeBody: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, EscapeBody.Label)):
            _cn = "EscapeBody"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: AnchorEscape | Assertion | CharEscape | ClassShorthand, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, AnchorEscape | Assertion | CharEscape | ClassShorthand]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"EscapeBody.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: AnchorEscape | Assertion | CharEscape | ClassShorthand, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"EscapeBody.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_anchor_escape(self, child: AnchorEscape) -> None:
        self.children.append((EscapeBody.Label.ANCHOR_ESCAPE, child))

    def extend_anchor_escape(self, children: typing.Iterable[AnchorEscape]) -> None:
        self.children.extend((EscapeBody.Label.ANCHOR_ESCAPE, child) for child in children)

    def children_anchor_escape(self) -> typing.Iterator[AnchorEscape]:
        return (
            typing.cast("AnchorEscape", child)
            for (label, child) in self.children
            if label == EscapeBody.Label.ANCHOR_ESCAPE
        )

    def child_anchor_escape(self) -> AnchorEscape:
        children = list(self.children_anchor_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one anchor_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_anchor_escape(self) -> AnchorEscape | None:
        children = list(self.children_anchor_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one anchor_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_assertion(self, child: Assertion) -> None:
        self.children.append((EscapeBody.Label.ASSERTION, child))

    def extend_assertion(self, children: typing.Iterable[Assertion]) -> None:
        self.children.extend((EscapeBody.Label.ASSERTION, child) for child in children)

    def children_assertion(self) -> typing.Iterator[Assertion]:
        return (
            typing.cast("Assertion", child) for (label, child) in self.children if label == EscapeBody.Label.ASSERTION
        )

    def child_assertion(self) -> Assertion:
        children = list(self.children_assertion())
        if (n := len(children)) != 1:
            msg = f"Expected one assertion child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_assertion(self) -> Assertion | None:
        children = list(self.children_assertion())
        if (n := len(children)) > 1:
            msg = f"Expected at most one assertion child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_char_escape(self, child: CharEscape) -> None:
        self.children.append((EscapeBody.Label.CHAR_ESCAPE, child))

    def extend_char_escape(self, children: typing.Iterable[CharEscape]) -> None:
        self.children.extend((EscapeBody.Label.CHAR_ESCAPE, child) for child in children)

    def children_char_escape(self) -> typing.Iterator[CharEscape]:
        return (
            typing.cast("CharEscape", child)
            for (label, child) in self.children
            if label == EscapeBody.Label.CHAR_ESCAPE
        )

    def child_char_escape(self) -> CharEscape:
        children = list(self.children_char_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one char_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_char_escape(self) -> CharEscape | None:
        children = list(self.children_char_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one char_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_class_shorthand(self, child: ClassShorthand) -> None:
        self.children.append((EscapeBody.Label.CLASS_SHORTHAND, child))

    def extend_class_shorthand(self, children: typing.Iterable[ClassShorthand]) -> None:
        self.children.extend((EscapeBody.Label.CLASS_SHORTHAND, child) for child in children)

    def children_class_shorthand(self) -> typing.Iterator[ClassShorthand]:
        return (
            typing.cast("ClassShorthand", child)
            for (label, child) in self.children
            if label == EscapeBody.Label.CLASS_SHORTHAND
        )

    def child_class_shorthand(self) -> ClassShorthand:
        children = list(self.children_class_shorthand())
        if (n := len(children)) != 1:
            msg = f"Expected one class_shorthand child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_class_shorthand(self) -> ClassShorthand | None:
        children = list(self.children_class_shorthand())
        if (n := len(children)) > 1:
            msg = f"Expected at most one class_shorthand child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CLASSSHORTHAND] = NodeKind.CLASSSHORTHAND
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

    def extend_children(self, other: ClassShorthand) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = ClassShorthand._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            ClassShorthand._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            ClassShorthand._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = ClassShorthand._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"ClassShorthand: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ClassShorthand.Label)):
            _cn = "ClassShorthand"
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
            msg = f"ClassShorthand.remove_at: index {index} out of range ({n} children)"
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
            msg = f"ClassShorthand.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ClassShorthand.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((ClassShorthand.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == ClassShorthand.Label.VALUE)

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

    kind: typing.Literal[NodeKind.ASSERTION] = NodeKind.ASSERTION
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

    def extend_children(self, other: Assertion) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Assertion._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            Assertion._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Assertion._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Assertion._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Assertion: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, Assertion.Label)):
            _cn = "Assertion"
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
            msg = f"Assertion.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Assertion.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Assertion.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Assertion.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Assertion.Label.VALUE)

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

    kind: typing.Literal[NodeKind.ANCHORESCAPE] = NodeKind.ANCHORESCAPE
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

    def extend_children(self, other: AnchorEscape) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = AnchorEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            AnchorEscape._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            AnchorEscape._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = AnchorEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"AnchorEscape: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, AnchorEscape.Label)):
            _cn = "AnchorEscape"
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
            msg = f"AnchorEscape.remove_at: index {index} out of range ({n} children)"
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
            msg = f"AnchorEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((AnchorEscape.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((AnchorEscape.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == AnchorEscape.Label.VALUE)

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

    kind: typing.Literal[NodeKind.CHARESCAPE] = NodeKind.CHARESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, ControlEscape | HexEscape | MetaEscape | UnicodeEscape]] = dataclasses.field(
        default_factory=list
    )

    def append(self, child: ControlEscape | HexEscape | MetaEscape | UnicodeEscape, label: Label | None = None) -> None:
        self.children.append((label, child))

    def extend(
        self,
        children: typing.Iterable[ControlEscape | HexEscape | MetaEscape | UnicodeEscape],
        label: Label | None = None,
    ) -> None:
        self.children.extend((label, child) for child in children)

    def extend_children(self, other: CharEscape) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, ControlEscape | HexEscape | MetaEscape | UnicodeEscape]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: ControlEscape | HexEscape | MetaEscape | UnicodeEscape) -> None:
        if not isinstance(child, ControlEscape | HexEscape | MetaEscape | UnicodeEscape):
            msg = f"CharEscape: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, CharEscape.Label)):
            _cn = "CharEscape"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self, index: int, child: ControlEscape | HexEscape | MetaEscape | UnicodeEscape, label: Label | None = None
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

    def remove_at(self, index: int) -> tuple[Label | None, ControlEscape | HexEscape | MetaEscape | UnicodeEscape]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CharEscape.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self, index: int, child: ControlEscape | HexEscape | MetaEscape | UnicodeEscape, label: Label | None = None
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"CharEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_control_escape(self, child: ControlEscape) -> None:
        self.children.append((CharEscape.Label.CONTROL_ESCAPE, child))

    def extend_control_escape(self, children: typing.Iterable[ControlEscape]) -> None:
        self.children.extend((CharEscape.Label.CONTROL_ESCAPE, child) for child in children)

    def children_control_escape(self) -> typing.Iterator[ControlEscape]:
        return (
            typing.cast("ControlEscape", child)
            for (label, child) in self.children
            if label == CharEscape.Label.CONTROL_ESCAPE
        )

    def child_control_escape(self) -> ControlEscape:
        children = list(self.children_control_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one control_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_control_escape(self) -> ControlEscape | None:
        children = list(self.children_control_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one control_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_hex_escape(self, child: HexEscape) -> None:
        self.children.append((CharEscape.Label.HEX_ESCAPE, child))

    def extend_hex_escape(self, children: typing.Iterable[HexEscape]) -> None:
        self.children.extend((CharEscape.Label.HEX_ESCAPE, child) for child in children)

    def children_hex_escape(self) -> typing.Iterator[HexEscape]:
        return (
            typing.cast("HexEscape", child) for (label, child) in self.children if label == CharEscape.Label.HEX_ESCAPE
        )

    def child_hex_escape(self) -> HexEscape:
        children = list(self.children_hex_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one hex_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_hex_escape(self) -> HexEscape | None:
        children = list(self.children_hex_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one hex_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_meta_escape(self, child: MetaEscape) -> None:
        self.children.append((CharEscape.Label.META_ESCAPE, child))

    def extend_meta_escape(self, children: typing.Iterable[MetaEscape]) -> None:
        self.children.extend((CharEscape.Label.META_ESCAPE, child) for child in children)

    def children_meta_escape(self) -> typing.Iterator[MetaEscape]:
        return (
            typing.cast("MetaEscape", child)
            for (label, child) in self.children
            if label == CharEscape.Label.META_ESCAPE
        )

    def child_meta_escape(self) -> MetaEscape:
        children = list(self.children_meta_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one meta_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_meta_escape(self) -> MetaEscape | None:
        children = list(self.children_meta_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one meta_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_unicode_escape(self, child: UnicodeEscape) -> None:
        self.children.append((CharEscape.Label.UNICODE_ESCAPE, child))

    def extend_unicode_escape(self, children: typing.Iterable[UnicodeEscape]) -> None:
        self.children.extend((CharEscape.Label.UNICODE_ESCAPE, child) for child in children)

    def children_unicode_escape(self) -> typing.Iterator[UnicodeEscape]:
        return (
            typing.cast("UnicodeEscape", child)
            for (label, child) in self.children
            if label == CharEscape.Label.UNICODE_ESCAPE
        )

    def child_unicode_escape(self) -> UnicodeEscape:
        children = list(self.children_unicode_escape())
        if (n := len(children)) != 1:
            msg = f"Expected one unicode_escape child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_unicode_escape(self) -> UnicodeEscape | None:
        children = list(self.children_unicode_escape())
        if (n := len(children)) > 1:
            msg = f"Expected at most one unicode_escape child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.CONTROLESCAPE] = NodeKind.CONTROLESCAPE
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

    def extend_children(self, other: ControlEscape) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = ControlEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            ControlEscape._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            ControlEscape._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = ControlEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"ControlEscape: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, ControlEscape.Label)):
            _cn = "ControlEscape"
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
            msg = f"ControlEscape.remove_at: index {index} out of range ({n} children)"
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
            msg = f"ControlEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((ControlEscape.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((ControlEscape.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == ControlEscape.Label.VALUE)

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

    kind: typing.Literal[NodeKind.HEXESCAPE] = NodeKind.HEXESCAPE
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

    def extend_children(self, other: HexEscape) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = HexEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            HexEscape._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            HexEscape._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = HexEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"HexEscape: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, HexEscape.Label)):
            _cn = "HexEscape"
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
            msg = f"HexEscape.remove_at: index {index} out of range ({n} children)"
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
            msg = f"HexEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_digits(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((HexEscape.Label.DIGITS, child))

    def extend_digits(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((HexEscape.Label.DIGITS, child) for child in children)

    def children_digits(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == HexEscape.Label.DIGITS)

    def child_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_digits())
        if (n := len(children)) != 1:
            msg = f"Expected one digits child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_digits())
        if (n := len(children)) > 1:
            msg = f"Expected at most one digits child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.UNICODEESCAPE] = NodeKind.UNICODEESCAPE
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

    def extend_children(self, other: UnicodeEscape) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = UnicodeEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            UnicodeEscape._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            UnicodeEscape._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = UnicodeEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"UnicodeEscape: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, UnicodeEscape.Label)):
            _cn = "UnicodeEscape"
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
            msg = f"UnicodeEscape.remove_at: index {index} out of range ({n} children)"
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
            msg = f"UnicodeEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_digits(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((UnicodeEscape.Label.DIGITS, child))

    def extend_digits(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((UnicodeEscape.Label.DIGITS, child) for child in children)

    def children_digits(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == UnicodeEscape.Label.DIGITS)

    def child_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_digits())
        if (n := len(children)) != 1:
            msg = f"Expected one digits child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_digits())
        if (n := len(children)) > 1:
            msg = f"Expected at most one digits child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None


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

    kind: typing.Literal[NodeKind.METAESCAPE] = NodeKind.METAESCAPE
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

    def extend_children(self, other: MetaEscape) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = MetaEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            MetaEscape._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            MetaEscape._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = MetaEscape._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"MetaEscape: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, MetaEscape.Label)):
            _cn = "MetaEscape"
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
            msg = f"MetaEscape.remove_at: index {index} out of range ({n} children)"
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
            msg = f"MetaEscape.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((MetaEscape.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((MetaEscape.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == MetaEscape.Label.VALUE)

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

    kind: typing.Literal[NodeKind.LITERALCHAR] = NodeKind.LITERALCHAR
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

    def extend_children(self, other: LiteralChar) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = LiteralChar._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
            LiteralChar._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            LiteralChar._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = LiteralChar._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"LiteralChar: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(self, label: Label | None, method: str) -> None:
        if label is not None and (not isinstance(label, LiteralChar.Label)):
            _cn = "LiteralChar"
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
            msg = f"LiteralChar.remove_at: index {index} out of range ({n} children)"
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
            msg = f"LiteralChar.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((LiteralChar.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((LiteralChar.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == LiteralChar.Label.VALUE)

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

    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
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

    def extend_children(self, other: Trivia) -> None:
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        _allowed = Trivia._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (fltk.fegen.pyrt.terminalsrc.Span,)
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
            msg = f"Trivia.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Trivia.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (label, child)

    def clear(self) -> None:
        self.children.clear()

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Trivia.Label.CONTENT, child))

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Trivia.Label.CONTENT, child) for child in children)

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Trivia.Label.CONTENT)

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


Trivia.Label.CONTENT._fltk_canonical_name = "Trivia.Label.CONTENT"
