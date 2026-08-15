# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol
__all__ = [
    "Alternation",
    "AlternationLabel",
    "Anchor",
    "AnchorEscape",
    "AnchorEscapeLabel",
    "AnchorLabel",
    "Assertion",
    "AssertionLabel",
    "Atom",
    "AtomLabel",
    "Bounded",
    "BoundedLabel",
    "Capturing",
    "CapturingLabel",
    "CharClass",
    "CharClassLabel",
    "CharEscape",
    "CharEscapeLabel",
    "ClassBody",
    "ClassBodyLabel",
    "ClassChar",
    "ClassCharEscape",
    "ClassCharEscapeLabel",
    "ClassCharLabel",
    "ClassEscape",
    "ClassEscapeBody",
    "ClassEscapeBodyLabel",
    "ClassEscapeLabel",
    "ClassItem",
    "ClassItemLabel",
    "ClassMember",
    "ClassMemberLabel",
    "ClassRange",
    "ClassRangeAtom",
    "ClassRangeAtomLabel",
    "ClassRangeLabel",
    "ClassShorthand",
    "ClassShorthandLabel",
    "Concatenation",
    "ConcatenationLabel",
    "ControlEscape",
    "ControlEscapeLabel",
    "CstModule",
    "Dot",
    "DotLabel",
    "Escape",
    "EscapeBody",
    "EscapeBodyLabel",
    "EscapeLabel",
    "FlagChars",
    "FlagCharsLabel",
    "FlagGroup",
    "FlagGroupLabel",
    "Group",
    "GroupLabel",
    "HexEscape",
    "HexEscapeLabel",
    "InlineFlags",
    "InlineFlagsLabel",
    "LiteralChar",
    "LiteralCharLabel",
    "MetaEscape",
    "MetaEscapeLabel",
    "NodeKind",
    "NonCapturing",
    "NonCapturingLabel",
    "Number",
    "NumberLabel",
    "Quantifier",
    "QuantifierLabel",
    "Regex",
    "RegexLabel",
    "Repetition",
    "RepetitionLabel",
    "Span",
    "Trivia",
    "TriviaLabel",
    "UnicodeEscape",
    "UnicodeEscapeLabel",
]


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


class Regex(typing.Protocol):
    kind: typing.Literal[NodeKind.REGEX] = NodeKind.REGEX
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation]]: ...

    def append(self, child: Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Alternation], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Regex) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation]: ...

    def insert(
        self, index: int, child: Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation]: ...

    def replace_at(
        self, index: int, child: Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_alternation(self, child: Alternation) -> None: ...

    def extend_alternation(self, children: typing.Iterable[Alternation]) -> None: ...

    def children_alternation(self) -> typing.Iterator[Alternation]: ...

    def child_alternation(self) -> Alternation: ...

    def maybe_alternation(self) -> Alternation | None: ...

    def alternation(self) -> Alternation: ...


class RegexLabel:
    """Sentinels equal to either backend's Regex labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ALTERNATION: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Regex.Label.ALTERNATION"
    )


class Alternation(typing.Protocol):
    kind: typing.Literal[NodeKind.ALTERNATION] = NodeKind.ALTERNATION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation | Concatenation]]: ...

    def append(
        self, child: Alternation | Concatenation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Alternation | Concatenation],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Alternation) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation | Concatenation]: ...

    def insert(
        self,
        index: int,
        child: Alternation | Concatenation,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation | Concatenation]: ...

    def replace_at(
        self,
        index: int,
        child: Alternation | Concatenation,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_branch(self, child: Concatenation) -> None: ...

    def extend_branch(self, children: typing.Iterable[Concatenation]) -> None: ...

    def children_branch(self) -> typing.Iterator[Concatenation]: ...

    def child_branch(self) -> Concatenation: ...

    def maybe_branch(self) -> Concatenation | None: ...

    def append_left(self, child: Alternation) -> None: ...

    def extend_left(self, children: typing.Iterable[Alternation]) -> None: ...

    def children_left(self) -> typing.Iterator[Alternation]: ...

    def child_left(self) -> Alternation: ...

    def maybe_left(self) -> Alternation | None: ...

    def append_right(self, child: Concatenation) -> None: ...

    def extend_right(self, children: typing.Iterable[Concatenation]) -> None: ...

    def children_right(self) -> typing.Iterator[Concatenation]: ...

    def child_right(self) -> Concatenation: ...

    def maybe_right(self) -> Concatenation | None: ...

    def branch(self) -> Concatenation | None: ...

    def left(self) -> Alternation | None: ...

    def right(self) -> Concatenation | None: ...


class AlternationLabel:
    """Sentinels equal to either backend's Alternation labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BRANCH: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Alternation.Label.BRANCH"
    )
    LEFT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Alternation.Label.LEFT")
    RIGHT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Alternation.Label.RIGHT")


class Concatenation(typing.Protocol):
    kind: typing.Literal[NodeKind.CONCATENATION] = NodeKind.CONCATENATION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Concatenation | Repetition]]: ...

    def append(
        self, child: Concatenation | Repetition, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Concatenation | Repetition],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Concatenation) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Concatenation | Repetition]: ...

    def insert(
        self,
        index: int,
        child: Concatenation | Repetition,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Concatenation | Repetition]: ...

    def replace_at(
        self,
        index: int,
        child: Concatenation | Repetition,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_head(self, child: Concatenation) -> None: ...

    def extend_head(self, children: typing.Iterable[Concatenation]) -> None: ...

    def children_head(self) -> typing.Iterator[Concatenation]: ...

    def child_head(self) -> Concatenation: ...

    def maybe_head(self) -> Concatenation | None: ...

    def append_single(self, child: Repetition) -> None: ...

    def extend_single(self, children: typing.Iterable[Repetition]) -> None: ...

    def children_single(self) -> typing.Iterator[Repetition]: ...

    def child_single(self) -> Repetition: ...

    def maybe_single(self) -> Repetition | None: ...

    def append_tail(self, child: Repetition) -> None: ...

    def extend_tail(self, children: typing.Iterable[Repetition]) -> None: ...

    def children_tail(self) -> typing.Iterator[Repetition]: ...

    def child_tail(self) -> Repetition: ...

    def maybe_tail(self) -> Repetition | None: ...

    def head(self) -> Concatenation | None: ...

    def single(self) -> Repetition | None: ...

    def tail(self) -> Repetition | None: ...


class ConcatenationLabel:
    """Sentinels equal to either backend's Concatenation labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    HEAD: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Concatenation.Label.HEAD")
    SINGLE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Concatenation.Label.SINGLE"
    )
    TAIL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Concatenation.Label.TAIL")


class Repetition(typing.Protocol):
    kind: typing.Literal[NodeKind.REPETITION] = NodeKind.REPETITION
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Quantifier]]: ...

    def append(
        self, child: Atom | Quantifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Atom | Quantifier],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Repetition) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Quantifier]: ...

    def insert(
        self, index: int, child: Atom | Quantifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Quantifier]: ...

    def replace_at(
        self, index: int, child: Atom | Quantifier, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_atom(self, child: Atom) -> None: ...

    def extend_atom(self, children: typing.Iterable[Atom]) -> None: ...

    def children_atom(self) -> typing.Iterator[Atom]: ...

    def child_atom(self) -> Atom: ...

    def maybe_atom(self) -> Atom | None: ...

    def append_quantifier(self, child: Quantifier) -> None: ...

    def extend_quantifier(self, children: typing.Iterable[Quantifier]) -> None: ...

    def children_quantifier(self) -> typing.Iterator[Quantifier]: ...

    def child_quantifier(self) -> Quantifier: ...

    def maybe_quantifier(self) -> Quantifier | None: ...

    def atom(self) -> Atom: ...

    def quantifier(self) -> Quantifier | None: ...


class RepetitionLabel:
    """Sentinels equal to either backend's Repetition labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ATOM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Repetition.Label.ATOM")
    QUANTIFIER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Repetition.Label.QUANTIFIER"
    )


class Quantifier(typing.Protocol):
    kind: typing.Literal[NodeKind.QUANTIFIER] = NodeKind.QUANTIFIER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ]: ...

    def append(
        self,
        child: Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Quantifier) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def insert(
        self,
        index: int,
        child: Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Bounded | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_bound(self, child: Bounded) -> None: ...

    def extend_bound(self, children: typing.Iterable[Bounded]) -> None: ...

    def children_bound(self) -> typing.Iterator[Bounded]: ...

    def child_bound(self) -> Bounded: ...

    def maybe_bound(self) -> Bounded | None: ...

    def append_lazy(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_lazy(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_lazy(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_lazy(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_lazy(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_one_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_one_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_one_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_optional(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_optional(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_optional(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_zero_or_more(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_zero_or_more(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_zero_or_more(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def bound(self) -> Bounded | None: ...

    def lazy(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def lazy_text(self) -> str | None: ...

    def one_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def one_or_more_text(self) -> str | None: ...

    def optional(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def optional_text(self) -> str | None: ...

    def zero_or_more(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def zero_or_more_text(self) -> str | None: ...


class QuantifierLabel:
    """Sentinels equal to either backend's Quantifier labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BOUND: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Quantifier.Label.BOUND")
    LAZY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Quantifier.Label.LAZY")
    ONE_OR_MORE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Quantifier.Label.ONE_OR_MORE"
    )
    OPTIONAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Quantifier.Label.OPTIONAL"
    )
    ZERO_OR_MORE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Quantifier.Label.ZERO_OR_MORE"
    )


class Bounded(typing.Protocol):
    kind: typing.Literal[NodeKind.BOUNDED] = NodeKind.BOUNDED
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Number]]: ...

    def append(self, child: Number, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Number], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Bounded) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Number]: ...

    def insert(
        self, index: int, child: Number, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Number]: ...

    def replace_at(
        self, index: int, child: Number, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_count(self, child: Number) -> None: ...

    def extend_count(self, children: typing.Iterable[Number]) -> None: ...

    def children_count(self) -> typing.Iterator[Number]: ...

    def child_count(self) -> Number: ...

    def maybe_count(self) -> Number | None: ...

    def append_max(self, child: Number) -> None: ...

    def extend_max(self, children: typing.Iterable[Number]) -> None: ...

    def children_max(self) -> typing.Iterator[Number]: ...

    def child_max(self) -> Number: ...

    def maybe_max(self) -> Number | None: ...

    def append_min(self, child: Number) -> None: ...

    def extend_min(self, children: typing.Iterable[Number]) -> None: ...

    def children_min(self) -> typing.Iterator[Number]: ...

    def child_min(self) -> Number: ...

    def maybe_min(self) -> Number | None: ...

    def count(self) -> Number | None: ...

    def max(self) -> Number | None: ...

    def min(self) -> Number | None: ...


class BoundedLabel:
    """Sentinels equal to either backend's Bounded labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    COUNT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Bounded.Label.COUNT")
    MAX: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Bounded.Label.MAX")
    MIN: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Bounded.Label.MIN")


class Number(typing.Protocol):
    kind: typing.Literal[NodeKind.NUMBER] = NodeKind.NUMBER
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

    def extend_children(self, other: Number) -> None: ...

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

    def append_digits(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_digits(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_digits(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def digits_text(self) -> str: ...

    def text(self) -> str: ...


class NumberLabel:
    """Sentinels equal to either backend's Number labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    DIGITS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Number.Label.DIGITS")


class Atom(typing.Protocol):
    kind: typing.Literal[NodeKind.ATOM] = NodeKind.ATOM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar,
        ]
    ]: ...

    def append(
        self,
        child: Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Atom) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar,
    ]: ...

    def insert(
        self,
        index: int,
        child: Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
        Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar,
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Anchor | CharClass | Dot | Escape | Group | InlineFlags | LiteralChar,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_anchor(self, child: Anchor) -> None: ...

    def extend_anchor(self, children: typing.Iterable[Anchor]) -> None: ...

    def children_anchor(self) -> typing.Iterator[Anchor]: ...

    def child_anchor(self) -> Anchor: ...

    def maybe_anchor(self) -> Anchor | None: ...

    def append_char_class(self, child: CharClass) -> None: ...

    def extend_char_class(self, children: typing.Iterable[CharClass]) -> None: ...

    def children_char_class(self) -> typing.Iterator[CharClass]: ...

    def child_char_class(self) -> CharClass: ...

    def maybe_char_class(self) -> CharClass | None: ...

    def append_dot(self, child: Dot) -> None: ...

    def extend_dot(self, children: typing.Iterable[Dot]) -> None: ...

    def children_dot(self) -> typing.Iterator[Dot]: ...

    def child_dot(self) -> Dot: ...

    def maybe_dot(self) -> Dot | None: ...

    def append_escape(self, child: Escape) -> None: ...

    def extend_escape(self, children: typing.Iterable[Escape]) -> None: ...

    def children_escape(self) -> typing.Iterator[Escape]: ...

    def child_escape(self) -> Escape: ...

    def maybe_escape(self) -> Escape | None: ...

    def append_group(self, child: Group) -> None: ...

    def extend_group(self, children: typing.Iterable[Group]) -> None: ...

    def children_group(self) -> typing.Iterator[Group]: ...

    def child_group(self) -> Group: ...

    def maybe_group(self) -> Group | None: ...

    def append_inline_flags(self, child: InlineFlags) -> None: ...

    def extend_inline_flags(self, children: typing.Iterable[InlineFlags]) -> None: ...

    def children_inline_flags(self) -> typing.Iterator[InlineFlags]: ...

    def child_inline_flags(self) -> InlineFlags: ...

    def maybe_inline_flags(self) -> InlineFlags | None: ...

    def append_literal_char(self, child: LiteralChar) -> None: ...

    def extend_literal_char(self, children: typing.Iterable[LiteralChar]) -> None: ...

    def children_literal_char(self) -> typing.Iterator[LiteralChar]: ...

    def child_literal_char(self) -> LiteralChar: ...

    def maybe_literal_char(self) -> LiteralChar | None: ...

    def anchor(self) -> Anchor | None: ...

    def char_class(self) -> CharClass | None: ...

    def dot(self) -> Dot | None: ...

    def escape(self) -> Escape | None: ...

    def group(self) -> Group | None: ...

    def inline_flags(self) -> InlineFlags | None: ...

    def literal_char(self) -> LiteralChar | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class AtomLabel:
    """Sentinels equal to either backend's Atom labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ANCHOR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Atom.Label.ANCHOR")
    CHAR_CLASS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Atom.Label.CHAR_CLASS"
    )
    DOT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Atom.Label.DOT")
    ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Atom.Label.ESCAPE")
    GROUP: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Atom.Label.GROUP")
    INLINE_FLAGS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Atom.Label.INLINE_FLAGS"
    )
    LITERAL_CHAR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Atom.Label.LITERAL_CHAR"
    )


class Dot(typing.Protocol):
    kind: typing.Literal[NodeKind.DOT] = NodeKind.DOT
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

    def extend_children(self, other: Dot) -> None: ...

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


class DotLabel:
    """Sentinels equal to either backend's Dot labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Dot.Label.VALUE")


class Anchor(typing.Protocol):
    kind: typing.Literal[NodeKind.ANCHOR] = NodeKind.ANCHOR
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

    def extend_children(self, other: Anchor) -> None: ...

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

    def append_caret(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_caret(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_caret(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_caret(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_caret(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_dollar(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_dollar(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_dollar(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_dollar(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_dollar(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def caret(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def caret_text(self) -> str | None: ...

    def dollar(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def dollar_text(self) -> str | None: ...

    def text(self) -> str: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class AnchorLabel:
    """Sentinels equal to either backend's Anchor labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CARET: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Anchor.Label.CARET")
    DOLLAR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Anchor.Label.DOLLAR")


class Group(typing.Protocol):
    kind: typing.Literal[NodeKind.GROUP] = NodeKind.GROUP
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Capturing | FlagGroup | NonCapturing]
    ]: ...

    def append(
        self,
        child: Capturing | FlagGroup | NonCapturing,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Capturing | FlagGroup | NonCapturing],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Group) -> None: ...

    def child(
        self,
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Capturing | FlagGroup | NonCapturing]: ...

    def insert(
        self,
        index: int,
        child: Capturing | FlagGroup | NonCapturing,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Capturing | FlagGroup | NonCapturing]: ...

    def replace_at(
        self,
        index: int,
        child: Capturing | FlagGroup | NonCapturing,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_capturing(self, child: Capturing) -> None: ...

    def extend_capturing(self, children: typing.Iterable[Capturing]) -> None: ...

    def children_capturing(self) -> typing.Iterator[Capturing]: ...

    def child_capturing(self) -> Capturing: ...

    def maybe_capturing(self) -> Capturing | None: ...

    def append_flag_group(self, child: FlagGroup) -> None: ...

    def extend_flag_group(self, children: typing.Iterable[FlagGroup]) -> None: ...

    def children_flag_group(self) -> typing.Iterator[FlagGroup]: ...

    def child_flag_group(self) -> FlagGroup: ...

    def maybe_flag_group(self) -> FlagGroup | None: ...

    def append_non_capturing(self, child: NonCapturing) -> None: ...

    def extend_non_capturing(self, children: typing.Iterable[NonCapturing]) -> None: ...

    def children_non_capturing(self) -> typing.Iterator[NonCapturing]: ...

    def child_non_capturing(self) -> NonCapturing: ...

    def maybe_non_capturing(self) -> NonCapturing | None: ...

    def capturing(self) -> Capturing | None: ...

    def flag_group(self) -> FlagGroup | None: ...

    def non_capturing(self) -> NonCapturing | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class GroupLabel:
    """Sentinels equal to either backend's Group labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CAPTURING: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Group.Label.CAPTURING"
    )
    FLAG_GROUP: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Group.Label.FLAG_GROUP"
    )
    NON_CAPTURING: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "Group.Label.NON_CAPTURING"
    )


class NonCapturing(typing.Protocol):
    kind: typing.Literal[NodeKind.NONCAPTURING] = NodeKind.NONCAPTURING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation]]: ...

    def append(self, child: Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Alternation], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: NonCapturing) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation]: ...

    def insert(
        self, index: int, child: Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation]: ...

    def replace_at(
        self, index: int, child: Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_body(self, child: Alternation) -> None: ...

    def extend_body(self, children: typing.Iterable[Alternation]) -> None: ...

    def children_body(self) -> typing.Iterator[Alternation]: ...

    def child_body(self) -> Alternation: ...

    def maybe_body(self) -> Alternation | None: ...

    def body(self) -> Alternation: ...


class NonCapturingLabel:
    """Sentinels equal to either backend's NonCapturing labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BODY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("NonCapturing.Label.BODY")


class FlagGroup(typing.Protocol):
    kind: typing.Literal[NodeKind.FLAGGROUP] = NodeKind.FLAGGROUP
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation | FlagChars]]: ...

    def append(
        self, child: Alternation | FlagChars, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Alternation | FlagChars],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: FlagGroup) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation | FlagChars]: ...

    def insert(
        self,
        index: int,
        child: Alternation | FlagChars,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation | FlagChars]: ...

    def replace_at(
        self,
        index: int,
        child: Alternation | FlagChars,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_body(self, child: Alternation) -> None: ...

    def extend_body(self, children: typing.Iterable[Alternation]) -> None: ...

    def children_body(self) -> typing.Iterator[Alternation]: ...

    def child_body(self) -> Alternation: ...

    def maybe_body(self) -> Alternation | None: ...

    def append_flags(self, child: FlagChars) -> None: ...

    def extend_flags(self, children: typing.Iterable[FlagChars]) -> None: ...

    def children_flags(self) -> typing.Iterator[FlagChars]: ...

    def child_flags(self) -> FlagChars: ...

    def maybe_flags(self) -> FlagChars | None: ...

    def body(self) -> Alternation: ...

    def flags(self) -> FlagChars: ...


class FlagGroupLabel:
    """Sentinels equal to either backend's FlagGroup labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BODY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("FlagGroup.Label.BODY")
    FLAGS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("FlagGroup.Label.FLAGS")


class Capturing(typing.Protocol):
    kind: typing.Literal[NodeKind.CAPTURING] = NodeKind.CAPTURING
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation]]: ...

    def append(self, child: Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Alternation], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Capturing) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation]: ...

    def insert(
        self, index: int, child: Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Alternation]: ...

    def replace_at(
        self, index: int, child: Alternation, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_body(self, child: Alternation) -> None: ...

    def extend_body(self, children: typing.Iterable[Alternation]) -> None: ...

    def children_body(self) -> typing.Iterator[Alternation]: ...

    def child_body(self) -> Alternation: ...

    def maybe_body(self) -> Alternation | None: ...

    def body(self) -> Alternation: ...


class CapturingLabel:
    """Sentinels equal to either backend's Capturing labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BODY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Capturing.Label.BODY")


class InlineFlags(typing.Protocol):
    kind: typing.Literal[NodeKind.INLINEFLAGS] = NodeKind.INLINEFLAGS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, FlagChars]]: ...

    def append(self, child: FlagChars, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[FlagChars], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: InlineFlags) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, FlagChars]: ...

    def insert(
        self, index: int, child: FlagChars, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, FlagChars]: ...

    def replace_at(
        self, index: int, child: FlagChars, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_flags(self, child: FlagChars) -> None: ...

    def extend_flags(self, children: typing.Iterable[FlagChars]) -> None: ...

    def children_flags(self) -> typing.Iterator[FlagChars]: ...

    def child_flags(self) -> FlagChars: ...

    def maybe_flags(self) -> FlagChars | None: ...

    def flags(self) -> FlagChars: ...


class InlineFlagsLabel:
    """Sentinels equal to either backend's InlineFlags labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    FLAGS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("InlineFlags.Label.FLAGS")


class FlagChars(typing.Protocol):
    kind: typing.Literal[NodeKind.FLAGCHARS] = NodeKind.FLAGCHARS
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

    def extend_children(self, other: FlagChars) -> None: ...

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


class FlagCharsLabel:
    """Sentinels equal to either backend's FlagChars labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("FlagChars.Label.VALUE")


class CharClass(typing.Protocol):
    kind: typing.Literal[NodeKind.CHARCLASS] = NodeKind.CHARCLASS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol
        ]
    ]: ...

    def append(
        self,
        child: ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: CharClass) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def insert(
        self,
        index: int,
        child: ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def replace_at(
        self,
        index: int,
        child: ClassBody | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_class_body(self, child: ClassBody) -> None: ...

    def extend_class_body(self, children: typing.Iterable[ClassBody]) -> None: ...

    def children_class_body(self) -> typing.Iterator[ClassBody]: ...

    def child_class_body(self) -> ClassBody: ...

    def maybe_class_body(self) -> ClassBody | None: ...

    def append_negated(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_negated(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_negated(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_negated(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_negated(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def class_body(self) -> ClassBody: ...

    def negated(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def negated_text(self) -> str | None: ...


class CharClassLabel:
    """Sentinels equal to either backend's CharClass labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CLASS_BODY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CharClass.Label.CLASS_BODY"
    )
    NEGATED: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CharClass.Label.NEGATED"
    )


class ClassBody(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSBODY] = NodeKind.CLASSBODY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol
        ]
    ]: ...

    def append(
        self,
        child: ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ClassBody) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def insert(
        self,
        index: int,
        child: ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def replace_at(
        self,
        index: int,
        child: ClassItem | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_items(self, child: ClassItem) -> None: ...

    def extend_items(self, children: typing.Iterable[ClassItem]) -> None: ...

    def children_items(self) -> typing.Iterator[ClassItem]: ...

    def child_items(self) -> ClassItem: ...

    def maybe_items(self) -> ClassItem | None: ...

    def append_lead_dash(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_lead_dash(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_lead_dash(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_lead_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_lead_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_trail_dash(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_trail_dash(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_trail_dash(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_trail_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_trail_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def items(self) -> typing.Sequence[ClassItem]: ...

    def lead_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def lead_dash_text(self) -> str | None: ...

    def trail_dash(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def trail_dash_text(self) -> str | None: ...


class ClassBodyLabel:
    """Sentinels equal to either backend's ClassBody labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ITEMS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("ClassBody.Label.ITEMS")
    LEAD_DASH: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassBody.Label.LEAD_DASH"
    )
    TRAIL_DASH: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassBody.Label.TRAIL_DASH"
    )


class ClassItem(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSITEM] = NodeKind.CLASSITEM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassMember | ClassRange]]: ...

    def append(
        self, child: ClassMember | ClassRange, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[ClassMember | ClassRange],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ClassItem) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassMember | ClassRange]: ...

    def insert(
        self,
        index: int,
        child: ClassMember | ClassRange,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassMember | ClassRange]: ...

    def replace_at(
        self,
        index: int,
        child: ClassMember | ClassRange,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_class_member(self, child: ClassMember) -> None: ...

    def extend_class_member(self, children: typing.Iterable[ClassMember]) -> None: ...

    def children_class_member(self) -> typing.Iterator[ClassMember]: ...

    def child_class_member(self) -> ClassMember: ...

    def maybe_class_member(self) -> ClassMember | None: ...

    def append_class_range(self, child: ClassRange) -> None: ...

    def extend_class_range(self, children: typing.Iterable[ClassRange]) -> None: ...

    def children_class_range(self) -> typing.Iterator[ClassRange]: ...

    def child_class_range(self) -> ClassRange: ...

    def maybe_class_range(self) -> ClassRange | None: ...

    def class_member(self) -> ClassMember | None: ...

    def class_range(self) -> ClassRange | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class ClassItemLabel:
    """Sentinels equal to either backend's ClassItem labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CLASS_MEMBER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassItem.Label.CLASS_MEMBER"
    )
    CLASS_RANGE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassItem.Label.CLASS_RANGE"
    )


class ClassRange(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSRANGE] = NodeKind.CLASSRANGE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassRangeAtom]]: ...

    def append(
        self, child: ClassRangeAtom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[ClassRangeAtom],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ClassRange) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassRangeAtom]: ...

    def insert(
        self, index: int, child: ClassRangeAtom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassRangeAtom]: ...

    def replace_at(
        self, index: int, child: ClassRangeAtom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_hi(self, child: ClassRangeAtom) -> None: ...

    def extend_hi(self, children: typing.Iterable[ClassRangeAtom]) -> None: ...

    def children_hi(self) -> typing.Iterator[ClassRangeAtom]: ...

    def child_hi(self) -> ClassRangeAtom: ...

    def maybe_hi(self) -> ClassRangeAtom | None: ...

    def append_lo(self, child: ClassRangeAtom) -> None: ...

    def extend_lo(self, children: typing.Iterable[ClassRangeAtom]) -> None: ...

    def children_lo(self) -> typing.Iterator[ClassRangeAtom]: ...

    def child_lo(self) -> ClassRangeAtom: ...

    def maybe_lo(self) -> ClassRangeAtom | None: ...

    def hi(self) -> ClassRangeAtom: ...

    def lo(self) -> ClassRangeAtom: ...


class ClassRangeLabel:
    """Sentinels equal to either backend's ClassRange labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    HI: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("ClassRange.Label.HI")
    LO: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("ClassRange.Label.LO")


class ClassMember(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSMEMBER] = NodeKind.CLASSMEMBER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassChar | ClassEscape]]: ...

    def append(
        self, child: ClassChar | ClassEscape, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[ClassChar | ClassEscape],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ClassMember) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassChar | ClassEscape]: ...

    def insert(
        self,
        index: int,
        child: ClassChar | ClassEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassChar | ClassEscape]: ...

    def replace_at(
        self,
        index: int,
        child: ClassChar | ClassEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_class_char(self, child: ClassChar) -> None: ...

    def extend_class_char(self, children: typing.Iterable[ClassChar]) -> None: ...

    def children_class_char(self) -> typing.Iterator[ClassChar]: ...

    def child_class_char(self) -> ClassChar: ...

    def maybe_class_char(self) -> ClassChar | None: ...

    def append_class_escape(self, child: ClassEscape) -> None: ...

    def extend_class_escape(self, children: typing.Iterable[ClassEscape]) -> None: ...

    def children_class_escape(self) -> typing.Iterator[ClassEscape]: ...

    def child_class_escape(self) -> ClassEscape: ...

    def maybe_class_escape(self) -> ClassEscape | None: ...

    def class_char(self) -> ClassChar | None: ...

    def class_escape(self) -> ClassEscape | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class ClassMemberLabel:
    """Sentinels equal to either backend's ClassMember labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CLASS_CHAR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassMember.Label.CLASS_CHAR"
    )
    CLASS_ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassMember.Label.CLASS_ESCAPE"
    )


class ClassRangeAtom(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSRANGEATOM] = NodeKind.CLASSRANGEATOM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassChar | ClassCharEscape]]: ...

    def append(
        self, child: ClassChar | ClassCharEscape, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[ClassChar | ClassCharEscape],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ClassRangeAtom) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassChar | ClassCharEscape]: ...

    def insert(
        self,
        index: int,
        child: ClassChar | ClassCharEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassChar | ClassCharEscape]: ...

    def replace_at(
        self,
        index: int,
        child: ClassChar | ClassCharEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_class_char(self, child: ClassChar) -> None: ...

    def extend_class_char(self, children: typing.Iterable[ClassChar]) -> None: ...

    def children_class_char(self) -> typing.Iterator[ClassChar]: ...

    def child_class_char(self) -> ClassChar: ...

    def maybe_class_char(self) -> ClassChar | None: ...

    def append_class_char_escape(self, child: ClassCharEscape) -> None: ...

    def extend_class_char_escape(self, children: typing.Iterable[ClassCharEscape]) -> None: ...

    def children_class_char_escape(self) -> typing.Iterator[ClassCharEscape]: ...

    def child_class_char_escape(self) -> ClassCharEscape: ...

    def maybe_class_char_escape(self) -> ClassCharEscape | None: ...

    def class_char(self) -> ClassChar | None: ...

    def class_char_escape(self) -> ClassCharEscape | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class ClassRangeAtomLabel:
    """Sentinels equal to either backend's ClassRangeAtom labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CLASS_CHAR: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassRangeAtom.Label.CLASS_CHAR"
    )
    CLASS_CHAR_ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassRangeAtom.Label.CLASS_CHAR_ESCAPE"
    )


class ClassChar(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSCHAR] = NodeKind.CLASSCHAR
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

    def extend_children(self, other: ClassChar) -> None: ...

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


class ClassCharLabel:
    """Sentinels equal to either backend's ClassChar labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("ClassChar.Label.VALUE")


class ClassEscape(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSESCAPE] = NodeKind.CLASSESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassEscapeBody]]: ...

    def append(
        self, child: ClassEscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[ClassEscapeBody],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ClassEscape) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassEscapeBody]: ...

    def insert(
        self, index: int, child: ClassEscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ClassEscapeBody]: ...

    def replace_at(
        self, index: int, child: ClassEscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_body(self, child: ClassEscapeBody) -> None: ...

    def extend_body(self, children: typing.Iterable[ClassEscapeBody]) -> None: ...

    def children_body(self) -> typing.Iterator[ClassEscapeBody]: ...

    def child_body(self) -> ClassEscapeBody: ...

    def maybe_body(self) -> ClassEscapeBody | None: ...

    def body(self) -> ClassEscapeBody: ...


class ClassEscapeLabel:
    """Sentinels equal to either backend's ClassEscape labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BODY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("ClassEscape.Label.BODY")


class ClassEscapeBody(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSESCAPEBODY] = NodeKind.CLASSESCAPEBODY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, CharEscape | ClassShorthand]]: ...

    def append(
        self, child: CharEscape | ClassShorthand, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[CharEscape | ClassShorthand],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ClassEscapeBody) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, CharEscape | ClassShorthand]: ...

    def insert(
        self,
        index: int,
        child: CharEscape | ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, CharEscape | ClassShorthand]: ...

    def replace_at(
        self,
        index: int,
        child: CharEscape | ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_char_escape(self, child: CharEscape) -> None: ...

    def extend_char_escape(self, children: typing.Iterable[CharEscape]) -> None: ...

    def children_char_escape(self) -> typing.Iterator[CharEscape]: ...

    def child_char_escape(self) -> CharEscape: ...

    def maybe_char_escape(self) -> CharEscape | None: ...

    def append_class_shorthand(self, child: ClassShorthand) -> None: ...

    def extend_class_shorthand(self, children: typing.Iterable[ClassShorthand]) -> None: ...

    def children_class_shorthand(self) -> typing.Iterator[ClassShorthand]: ...

    def child_class_shorthand(self) -> ClassShorthand: ...

    def maybe_class_shorthand(self) -> ClassShorthand | None: ...

    def char_escape(self) -> CharEscape | None: ...

    def class_shorthand(self) -> ClassShorthand | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class ClassEscapeBodyLabel:
    """Sentinels equal to either backend's ClassEscapeBody labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CHAR_ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassEscapeBody.Label.CHAR_ESCAPE"
    )
    CLASS_SHORTHAND: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassEscapeBody.Label.CLASS_SHORTHAND"
    )


class ClassCharEscape(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSCHARESCAPE] = NodeKind.CLASSCHARESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, CharEscape]]: ...

    def append(self, child: CharEscape, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[CharEscape], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: ClassCharEscape) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, CharEscape]: ...

    def insert(
        self, index: int, child: CharEscape, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, CharEscape]: ...

    def replace_at(
        self, index: int, child: CharEscape, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_body(self, child: CharEscape) -> None: ...

    def extend_body(self, children: typing.Iterable[CharEscape]) -> None: ...

    def children_body(self) -> typing.Iterator[CharEscape]: ...

    def child_body(self) -> CharEscape: ...

    def maybe_body(self) -> CharEscape | None: ...

    def body(self) -> CharEscape: ...


class ClassCharEscapeLabel:
    """Sentinels equal to either backend's ClassCharEscape labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BODY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassCharEscape.Label.BODY"
    )


class Escape(typing.Protocol):
    kind: typing.Literal[NodeKind.ESCAPE] = NodeKind.ESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, EscapeBody]]: ...

    def append(self, child: EscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[EscapeBody], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Escape) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, EscapeBody]: ...

    def insert(
        self, index: int, child: EscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, EscapeBody]: ...

    def replace_at(
        self, index: int, child: EscapeBody, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_body(self, child: EscapeBody) -> None: ...

    def extend_body(self, children: typing.Iterable[EscapeBody]) -> None: ...

    def children_body(self) -> typing.Iterator[EscapeBody]: ...

    def child_body(self) -> EscapeBody: ...

    def maybe_body(self) -> EscapeBody | None: ...

    def body(self) -> EscapeBody: ...


class EscapeLabel:
    """Sentinels equal to either backend's Escape labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BODY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Escape.Label.BODY")


class EscapeBody(typing.Protocol):
    kind: typing.Literal[NodeKind.ESCAPEBODY] = NodeKind.ESCAPEBODY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None, AnchorEscape | Assertion | CharEscape | ClassShorthand
        ]
    ]: ...

    def append(
        self,
        child: AnchorEscape | Assertion | CharEscape | ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[AnchorEscape | Assertion | CharEscape | ClassShorthand],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: EscapeBody) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, AnchorEscape | Assertion | CharEscape | ClassShorthand
    ]: ...

    def insert(
        self,
        index: int,
        child: AnchorEscape | Assertion | CharEscape | ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, AnchorEscape | Assertion | CharEscape | ClassShorthand
    ]: ...

    def replace_at(
        self,
        index: int,
        child: AnchorEscape | Assertion | CharEscape | ClassShorthand,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_anchor_escape(self, child: AnchorEscape) -> None: ...

    def extend_anchor_escape(self, children: typing.Iterable[AnchorEscape]) -> None: ...

    def children_anchor_escape(self) -> typing.Iterator[AnchorEscape]: ...

    def child_anchor_escape(self) -> AnchorEscape: ...

    def maybe_anchor_escape(self) -> AnchorEscape | None: ...

    def append_assertion(self, child: Assertion) -> None: ...

    def extend_assertion(self, children: typing.Iterable[Assertion]) -> None: ...

    def children_assertion(self) -> typing.Iterator[Assertion]: ...

    def child_assertion(self) -> Assertion: ...

    def maybe_assertion(self) -> Assertion | None: ...

    def append_char_escape(self, child: CharEscape) -> None: ...

    def extend_char_escape(self, children: typing.Iterable[CharEscape]) -> None: ...

    def children_char_escape(self) -> typing.Iterator[CharEscape]: ...

    def child_char_escape(self) -> CharEscape: ...

    def maybe_char_escape(self) -> CharEscape | None: ...

    def append_class_shorthand(self, child: ClassShorthand) -> None: ...

    def extend_class_shorthand(self, children: typing.Iterable[ClassShorthand]) -> None: ...

    def children_class_shorthand(self) -> typing.Iterator[ClassShorthand]: ...

    def child_class_shorthand(self) -> ClassShorthand: ...

    def maybe_class_shorthand(self) -> ClassShorthand | None: ...

    def anchor_escape(self) -> AnchorEscape | None: ...

    def assertion(self) -> Assertion | None: ...

    def char_escape(self) -> CharEscape | None: ...

    def class_shorthand(self) -> ClassShorthand | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class EscapeBodyLabel:
    """Sentinels equal to either backend's EscapeBody labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ANCHOR_ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "EscapeBody.Label.ANCHOR_ESCAPE"
    )
    ASSERTION: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "EscapeBody.Label.ASSERTION"
    )
    CHAR_ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "EscapeBody.Label.CHAR_ESCAPE"
    )
    CLASS_SHORTHAND: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "EscapeBody.Label.CLASS_SHORTHAND"
    )


class ClassShorthand(typing.Protocol):
    kind: typing.Literal[NodeKind.CLASSSHORTHAND] = NodeKind.CLASSSHORTHAND
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

    def extend_children(self, other: ClassShorthand) -> None: ...

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


class ClassShorthandLabel:
    """Sentinels equal to either backend's ClassShorthand labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ClassShorthand.Label.VALUE"
    )


class Assertion(typing.Protocol):
    kind: typing.Literal[NodeKind.ASSERTION] = NodeKind.ASSERTION
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

    def extend_children(self, other: Assertion) -> None: ...

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


class AssertionLabel:
    """Sentinels equal to either backend's Assertion labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Assertion.Label.VALUE")


class AnchorEscape(typing.Protocol):
    kind: typing.Literal[NodeKind.ANCHORESCAPE] = NodeKind.ANCHORESCAPE
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

    def extend_children(self, other: AnchorEscape) -> None: ...

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


class AnchorEscapeLabel:
    """Sentinels equal to either backend's AnchorEscape labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("AnchorEscape.Label.VALUE")


class CharEscape(typing.Protocol):
    kind: typing.Literal[NodeKind.CHARESCAPE] = NodeKind.CHARESCAPE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ControlEscape | HexEscape | MetaEscape | UnicodeEscape
        ]
    ]: ...

    def append(
        self,
        child: ControlEscape | HexEscape | MetaEscape | UnicodeEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[ControlEscape | HexEscape | MetaEscape | UnicodeEscape],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: CharEscape) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ControlEscape | HexEscape | MetaEscape | UnicodeEscape
    ]: ...

    def insert(
        self,
        index: int,
        child: ControlEscape | HexEscape | MetaEscape | UnicodeEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, ControlEscape | HexEscape | MetaEscape | UnicodeEscape
    ]: ...

    def replace_at(
        self,
        index: int,
        child: ControlEscape | HexEscape | MetaEscape | UnicodeEscape,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_control_escape(self, child: ControlEscape) -> None: ...

    def extend_control_escape(self, children: typing.Iterable[ControlEscape]) -> None: ...

    def children_control_escape(self) -> typing.Iterator[ControlEscape]: ...

    def child_control_escape(self) -> ControlEscape: ...

    def maybe_control_escape(self) -> ControlEscape | None: ...

    def append_hex_escape(self, child: HexEscape) -> None: ...

    def extend_hex_escape(self, children: typing.Iterable[HexEscape]) -> None: ...

    def children_hex_escape(self) -> typing.Iterator[HexEscape]: ...

    def child_hex_escape(self) -> HexEscape: ...

    def maybe_hex_escape(self) -> HexEscape | None: ...

    def append_meta_escape(self, child: MetaEscape) -> None: ...

    def extend_meta_escape(self, children: typing.Iterable[MetaEscape]) -> None: ...

    def children_meta_escape(self) -> typing.Iterator[MetaEscape]: ...

    def child_meta_escape(self) -> MetaEscape: ...

    def maybe_meta_escape(self) -> MetaEscape | None: ...

    def append_unicode_escape(self, child: UnicodeEscape) -> None: ...

    def extend_unicode_escape(self, children: typing.Iterable[UnicodeEscape]) -> None: ...

    def children_unicode_escape(self) -> typing.Iterator[UnicodeEscape]: ...

    def child_unicode_escape(self) -> UnicodeEscape: ...

    def maybe_unicode_escape(self) -> UnicodeEscape | None: ...

    def control_escape(self) -> ControlEscape | None: ...

    def hex_escape(self) -> HexEscape | None: ...

    def meta_escape(self) -> MetaEscape | None: ...

    def unicode_escape(self) -> UnicodeEscape | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class CharEscapeLabel:
    """Sentinels equal to either backend's CharEscape labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CONTROL_ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CharEscape.Label.CONTROL_ESCAPE"
    )
    HEX_ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CharEscape.Label.HEX_ESCAPE"
    )
    META_ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CharEscape.Label.META_ESCAPE"
    )
    UNICODE_ESCAPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CharEscape.Label.UNICODE_ESCAPE"
    )


class ControlEscape(typing.Protocol):
    kind: typing.Literal[NodeKind.CONTROLESCAPE] = NodeKind.CONTROLESCAPE
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

    def extend_children(self, other: ControlEscape) -> None: ...

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


class ControlEscapeLabel:
    """Sentinels equal to either backend's ControlEscape labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ControlEscape.Label.VALUE"
    )


class HexEscape(typing.Protocol):
    kind: typing.Literal[NodeKind.HEXESCAPE] = NodeKind.HEXESCAPE
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

    def extend_children(self, other: HexEscape) -> None: ...

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

    def append_digits(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_digits(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_digits(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def digits_text(self) -> str: ...

    def text(self) -> str: ...


class HexEscapeLabel:
    """Sentinels equal to either backend's HexEscape labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    DIGITS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("HexEscape.Label.DIGITS")


class UnicodeEscape(typing.Protocol):
    kind: typing.Literal[NodeKind.UNICODEESCAPE] = NodeKind.UNICODEESCAPE
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

    def extend_children(self, other: UnicodeEscape) -> None: ...

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

    def append_digits(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_digits(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_digits(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def digits(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def digits_text(self) -> str: ...

    def text(self) -> str: ...


class UnicodeEscapeLabel:
    """Sentinels equal to either backend's UnicodeEscape labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    DIGITS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "UnicodeEscape.Label.DIGITS"
    )


class MetaEscape(typing.Protocol):
    kind: typing.Literal[NodeKind.METAESCAPE] = NodeKind.METAESCAPE
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

    def extend_children(self, other: MetaEscape) -> None: ...

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


class MetaEscapeLabel:
    """Sentinels equal to either backend's MetaEscape labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("MetaEscape.Label.VALUE")


class LiteralChar(typing.Protocol):
    kind: typing.Literal[NodeKind.LITERALCHAR] = NodeKind.LITERALCHAR
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

    def extend_children(self, other: LiteralChar) -> None: ...

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


class LiteralCharLabel:
    """Sentinels equal to either backend's LiteralChar labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("LiteralChar.Label.VALUE")


class Trivia(typing.Protocol):
    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
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

    def extend_children(self, other: Trivia) -> None: ...

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

    def content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def content_text(self) -> str: ...

    def text(self) -> str: ...


class TriviaLabel:
    """Sentinels equal to either backend's Trivia labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    CONTENT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Trivia.Label.CONTENT")


class Span(typing.Protocol):
    kind: typing.Literal[fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN] = fltk.fegen.pyrt.terminalsrc.SpanKind.SPAN


class CstModule(typing.Protocol):
    @property
    def Regex(self) -> type[Regex]: ...

    @property
    def Alternation(self) -> type[Alternation]: ...

    @property
    def Concatenation(self) -> type[Concatenation]: ...

    @property
    def Repetition(self) -> type[Repetition]: ...

    @property
    def Quantifier(self) -> type[Quantifier]: ...

    @property
    def Bounded(self) -> type[Bounded]: ...

    @property
    def Number(self) -> type[Number]: ...

    @property
    def Atom(self) -> type[Atom]: ...

    @property
    def Dot(self) -> type[Dot]: ...

    @property
    def Anchor(self) -> type[Anchor]: ...

    @property
    def Group(self) -> type[Group]: ...

    @property
    def NonCapturing(self) -> type[NonCapturing]: ...

    @property
    def FlagGroup(self) -> type[FlagGroup]: ...

    @property
    def Capturing(self) -> type[Capturing]: ...

    @property
    def InlineFlags(self) -> type[InlineFlags]: ...

    @property
    def FlagChars(self) -> type[FlagChars]: ...

    @property
    def CharClass(self) -> type[CharClass]: ...

    @property
    def ClassBody(self) -> type[ClassBody]: ...

    @property
    def ClassItem(self) -> type[ClassItem]: ...

    @property
    def ClassRange(self) -> type[ClassRange]: ...

    @property
    def ClassMember(self) -> type[ClassMember]: ...

    @property
    def ClassRangeAtom(self) -> type[ClassRangeAtom]: ...

    @property
    def ClassChar(self) -> type[ClassChar]: ...

    @property
    def ClassEscape(self) -> type[ClassEscape]: ...

    @property
    def ClassEscapeBody(self) -> type[ClassEscapeBody]: ...

    @property
    def ClassCharEscape(self) -> type[ClassCharEscape]: ...

    @property
    def Escape(self) -> type[Escape]: ...

    @property
    def EscapeBody(self) -> type[EscapeBody]: ...

    @property
    def ClassShorthand(self) -> type[ClassShorthand]: ...

    @property
    def Assertion(self) -> type[Assertion]: ...

    @property
    def AnchorEscape(self) -> type[AnchorEscape]: ...

    @property
    def CharEscape(self) -> type[CharEscape]: ...

    @property
    def ControlEscape(self) -> type[ControlEscape]: ...

    @property
    def HexEscape(self) -> type[HexEscape]: ...

    @property
    def UnicodeEscape(self) -> type[UnicodeEscape]: ...

    @property
    def MetaEscape(self) -> type[MetaEscape]: ...

    @property
    def LiteralChar(self) -> type[LiteralChar]: ...

    @property
    def Trivia(self) -> type[Trivia]: ...
