# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol
__all__ = [
    "AnchoredWord",
    "AnchoredWordLabel",
    "Arrow",
    "ArrowLabel",
    "Atom",
    "AtomLabel",
    "CaseInsensitive",
    "CaseInsensitiveLabel",
    "Colour",
    "ColourLabel",
    "CstModule",
    "DecimalVal",
    "DecimalValLabel",
    "DigitSeq",
    "DigitSeqLabel",
    "Entries",
    "EntriesLabel",
    "Entry",
    "EntryKey",
    "EntryKeyLabel",
    "EntryLabel",
    "EscapedMetas",
    "EscapedMetasLabel",
    "ExactlyTwoDigits",
    "ExactlyTwoDigitsLabel",
    "Expr",
    "ExprLabel",
    "Grouped",
    "GroupedLabel",
    "Items",
    "ItemsLabel",
    "KwLabels",
    "KwLabelsLabel",
    "LatinRange",
    "LatinRangeLabel",
    "LatinWord",
    "LatinWordLabel",
    "LeadingWs",
    "LeadingWsLabel",
    "Lval",
    "LvalLabel",
    "MixedOpt",
    "MixedOptLabel",
    "MultiEntries",
    "MultiEntriesLabel",
    "MultiEntry",
    "MultiEntryLabel",
    "Name",
    "NameLabel",
    "NcGroupAlt",
    "NcGroupAltLabel",
    "Nest",
    "NestLabel",
    "NestSum",
    "NestSumLabel",
    "NodeKind",
    "Num",
    "NumLabel",
    "OptItem",
    "OptItemLabel",
    "OptWrapper",
    "OptWrapperLabel",
    "Pair",
    "PairLabel",
    "ParenExpr",
    "ParenExprLabel",
    "Quoted",
    "QuotedLabel",
    "RecViaSub",
    "RecViaSubLabel",
    "RepWrapper",
    "RepWrapperLabel",
    "Rval",
    "RvalLabel",
    "Span",
    "Stmt",
    "StmtLabel",
    "SumChain",
    "SumChainLabel",
    "Tagged",
    "TaggedLabel",
    "ThreeToFiveDigits",
    "ThreeToFiveDigitsLabel",
    "Trivia",
    "TriviaLabel",
    "UuidVal",
    "UuidValLabel",
    "Val",
    "ValLabel",
    "WordSeq",
    "WordSeqLabel",
    "Wrapper",
    "WrapperLabel",
    "WsSeq",
    "WsSeqLabel",
    "ZeroItems",
    "ZeroItemsLabel",
]


class NodeKind(enum.Enum):
    NUM = enum.auto()
    NAME = enum.auto()
    ATOM = enum.auto()
    PARENEXPR = enum.auto()
    STMT = enum.auto()
    ITEMS = enum.auto()
    OPTITEM = enum.auto()
    ZEROITEMS = enum.auto()
    EXPR = enum.auto()
    LVAL = enum.auto()
    RVAL = enum.auto()
    ARROW = enum.auto()
    LATINWORD = enum.auto()
    TAGGED = enum.auto()
    VAL = enum.auto()
    LEADINGWS = enum.auto()
    GROUPED = enum.auto()
    RECVIASUB = enum.auto()
    NEST = enum.auto()
    NESTSUM = enum.auto()
    DIGITSEQ = enum.auto()
    WORDSEQ = enum.auto()
    WSSEQ = enum.auto()
    THREETOFIVEDIGITS = enum.auto()
    EXACTLYTWODIGITS = enum.auto()
    ESCAPEDMETAS = enum.auto()
    LATINRANGE = enum.auto()
    NCGROUPALT = enum.auto()
    CASEINSENSITIVE = enum.auto()
    ANCHOREDWORD = enum.auto()
    PAIR = enum.auto()
    WRAPPER = enum.auto()
    OPTWRAPPER = enum.auto()
    REPWRAPPER = enum.auto()
    KWLABELS = enum.auto()
    QUOTED = enum.auto()
    MIXEDOPT = enum.auto()
    UUIDVAL = enum.auto()
    DECIMALVAL = enum.auto()
    COLOUR = enum.auto()
    SUMCHAIN = enum.auto()
    ENTRYKEY = enum.auto()
    ENTRY = enum.auto()
    ENTRIES = enum.auto()
    MULTIENTRY = enum.auto()
    MULTIENTRIES = enum.auto()
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


NodeKind.NUM._fltk_canonical_name = "NodeKind.NUM"
NodeKind.NAME._fltk_canonical_name = "NodeKind.NAME"
NodeKind.ATOM._fltk_canonical_name = "NodeKind.ATOM"
NodeKind.PARENEXPR._fltk_canonical_name = "NodeKind.PARENEXPR"
NodeKind.STMT._fltk_canonical_name = "NodeKind.STMT"
NodeKind.ITEMS._fltk_canonical_name = "NodeKind.ITEMS"
NodeKind.OPTITEM._fltk_canonical_name = "NodeKind.OPTITEM"
NodeKind.ZEROITEMS._fltk_canonical_name = "NodeKind.ZEROITEMS"
NodeKind.EXPR._fltk_canonical_name = "NodeKind.EXPR"
NodeKind.LVAL._fltk_canonical_name = "NodeKind.LVAL"
NodeKind.RVAL._fltk_canonical_name = "NodeKind.RVAL"
NodeKind.ARROW._fltk_canonical_name = "NodeKind.ARROW"
NodeKind.LATINWORD._fltk_canonical_name = "NodeKind.LATINWORD"
NodeKind.TAGGED._fltk_canonical_name = "NodeKind.TAGGED"
NodeKind.VAL._fltk_canonical_name = "NodeKind.VAL"
NodeKind.LEADINGWS._fltk_canonical_name = "NodeKind.LEADINGWS"
NodeKind.GROUPED._fltk_canonical_name = "NodeKind.GROUPED"
NodeKind.RECVIASUB._fltk_canonical_name = "NodeKind.RECVIASUB"
NodeKind.NEST._fltk_canonical_name = "NodeKind.NEST"
NodeKind.NESTSUM._fltk_canonical_name = "NodeKind.NESTSUM"
NodeKind.DIGITSEQ._fltk_canonical_name = "NodeKind.DIGITSEQ"
NodeKind.WORDSEQ._fltk_canonical_name = "NodeKind.WORDSEQ"
NodeKind.WSSEQ._fltk_canonical_name = "NodeKind.WSSEQ"
NodeKind.THREETOFIVEDIGITS._fltk_canonical_name = "NodeKind.THREETOFIVEDIGITS"
NodeKind.EXACTLYTWODIGITS._fltk_canonical_name = "NodeKind.EXACTLYTWODIGITS"
NodeKind.ESCAPEDMETAS._fltk_canonical_name = "NodeKind.ESCAPEDMETAS"
NodeKind.LATINRANGE._fltk_canonical_name = "NodeKind.LATINRANGE"
NodeKind.NCGROUPALT._fltk_canonical_name = "NodeKind.NCGROUPALT"
NodeKind.CASEINSENSITIVE._fltk_canonical_name = "NodeKind.CASEINSENSITIVE"
NodeKind.ANCHOREDWORD._fltk_canonical_name = "NodeKind.ANCHOREDWORD"
NodeKind.PAIR._fltk_canonical_name = "NodeKind.PAIR"
NodeKind.WRAPPER._fltk_canonical_name = "NodeKind.WRAPPER"
NodeKind.OPTWRAPPER._fltk_canonical_name = "NodeKind.OPTWRAPPER"
NodeKind.REPWRAPPER._fltk_canonical_name = "NodeKind.REPWRAPPER"
NodeKind.KWLABELS._fltk_canonical_name = "NodeKind.KWLABELS"
NodeKind.QUOTED._fltk_canonical_name = "NodeKind.QUOTED"
NodeKind.MIXEDOPT._fltk_canonical_name = "NodeKind.MIXEDOPT"
NodeKind.UUIDVAL._fltk_canonical_name = "NodeKind.UUIDVAL"
NodeKind.DECIMALVAL._fltk_canonical_name = "NodeKind.DECIMALVAL"
NodeKind.COLOUR._fltk_canonical_name = "NodeKind.COLOUR"
NodeKind.SUMCHAIN._fltk_canonical_name = "NodeKind.SUMCHAIN"
NodeKind.ENTRYKEY._fltk_canonical_name = "NodeKind.ENTRYKEY"
NodeKind.ENTRY._fltk_canonical_name = "NodeKind.ENTRY"
NodeKind.ENTRIES._fltk_canonical_name = "NodeKind.ENTRIES"
NodeKind.MULTIENTRY._fltk_canonical_name = "NodeKind.MULTIENTRY"
NodeKind.MULTIENTRIES._fltk_canonical_name = "NodeKind.MULTIENTRIES"
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


class Num(typing.Protocol):
    kind: typing.Literal[NodeKind.NUM] = NodeKind.NUM
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

    def extend_children(self, other: Num) -> None: ...

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


class NumLabel:
    """Sentinels equal to either backend's Num labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Num.Label.VALUE")


class Name(typing.Protocol):
    kind: typing.Literal[NodeKind.NAME] = NodeKind.NAME
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

    def extend_children(self, other: Name) -> None: ...

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


class NameLabel:
    """Sentinels equal to either backend's Name labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Name.Label.VALUE")


class Atom(typing.Protocol):
    kind: typing.Literal[NodeKind.ATOM] = NodeKind.ATOM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]]: ...

    def append(self, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Name | Num], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Atom) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def insert(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def replace_at(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_name(self, child: Name) -> None: ...

    def extend_name(self, children: typing.Iterable[Name]) -> None: ...

    def children_name(self) -> typing.Iterator[Name]: ...

    def child_name(self) -> Name: ...

    def maybe_name(self) -> Name | None: ...

    def append_num(self, child: Num) -> None: ...

    def extend_num(self, children: typing.Iterable[Num]) -> None: ...

    def children_num(self) -> typing.Iterator[Num]: ...

    def child_num(self) -> Num: ...

    def maybe_num(self) -> Num | None: ...

    def name(self) -> Name | None: ...

    def num(self) -> Num | None: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class AtomLabel:
    """Sentinels equal to either backend's Atom labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    NAME: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Atom.Label.NAME")
    NUM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Atom.Label.NUM")


class ParenExpr(typing.Protocol):
    kind: typing.Literal[NodeKind.PARENEXPR] = NodeKind.PARENEXPR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Trivia]]: ...

    def append(
        self, child: Atom | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Atom | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: ParenExpr) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Trivia]: ...

    def insert(
        self, index: int, child: Atom | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Trivia]: ...

    def replace_at(
        self, index: int, child: Atom | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_inner(self, child: Atom) -> None: ...

    def extend_inner(self, children: typing.Iterable[Atom]) -> None: ...

    def children_inner(self) -> typing.Iterator[Atom]: ...

    def child_inner(self) -> Atom: ...

    def maybe_inner(self) -> Atom | None: ...

    def inner(self) -> Atom: ...


class ParenExprLabel:
    """Sentinels equal to either backend's ParenExpr labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    INNER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("ParenExpr.Label.INNER")


class Stmt(typing.Protocol):
    kind: typing.Literal[NodeKind.STMT] = NodeKind.STMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Trivia]]: ...

    def append(
        self, child: Atom | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Atom | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Stmt) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Trivia]: ...

    def insert(
        self, index: int, child: Atom | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Trivia]: ...

    def replace_at(
        self, index: int, child: Atom | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_lhs(self, child: Atom) -> None: ...

    def extend_lhs(self, children: typing.Iterable[Atom]) -> None: ...

    def children_lhs(self) -> typing.Iterator[Atom]: ...

    def child_lhs(self) -> Atom: ...

    def maybe_lhs(self) -> Atom | None: ...

    def append_rhs(self, child: Atom) -> None: ...

    def extend_rhs(self, children: typing.Iterable[Atom]) -> None: ...

    def children_rhs(self) -> typing.Iterator[Atom]: ...

    def child_rhs(self) -> Atom: ...

    def maybe_rhs(self) -> Atom | None: ...

    def lhs(self) -> Atom: ...

    def rhs(self) -> Atom: ...


class StmtLabel:
    """Sentinels equal to either backend's Stmt labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    LHS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Stmt.Label.LHS")
    RHS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Stmt.Label.RHS")


class Items(typing.Protocol):
    kind: typing.Literal[NodeKind.ITEMS] = NodeKind.ITEMS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom]]: ...

    def append(self, child: Atom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Atom], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Items) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom]: ...

    def insert(
        self, index: int, child: Atom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom]: ...

    def replace_at(
        self, index: int, child: Atom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_item(self, child: Atom) -> None: ...

    def extend_item(self, children: typing.Iterable[Atom]) -> None: ...

    def children_item(self) -> typing.Iterator[Atom]: ...

    def child_item(self) -> Atom: ...

    def maybe_item(self) -> Atom | None: ...

    def item(self) -> typing.Sequence[Atom]: ...


class ItemsLabel:
    """Sentinels equal to either backend's Items labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ITEM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Items.Label.ITEM")


class OptItem(typing.Protocol):
    kind: typing.Literal[NodeKind.OPTITEM] = NodeKind.OPTITEM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom]]: ...

    def append(self, child: Atom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Atom], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: OptItem) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom]: ...

    def insert(
        self, index: int, child: Atom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom]: ...

    def replace_at(
        self, index: int, child: Atom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_item(self, child: Atom) -> None: ...

    def extend_item(self, children: typing.Iterable[Atom]) -> None: ...

    def children_item(self) -> typing.Iterator[Atom]: ...

    def child_item(self) -> Atom: ...

    def maybe_item(self) -> Atom | None: ...

    def item(self) -> Atom | None: ...


class OptItemLabel:
    """Sentinels equal to either backend's OptItem labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ITEM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("OptItem.Label.ITEM")


class ZeroItems(typing.Protocol):
    kind: typing.Literal[NodeKind.ZEROITEMS] = NodeKind.ZEROITEMS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom]]: ...

    def append(self, child: Atom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Atom], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: ZeroItems) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom]: ...

    def insert(
        self, index: int, child: Atom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom]: ...

    def replace_at(
        self, index: int, child: Atom, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_item(self, child: Atom) -> None: ...

    def extend_item(self, children: typing.Iterable[Atom]) -> None: ...

    def children_item(self) -> typing.Iterator[Atom]: ...

    def child_item(self) -> Atom: ...

    def maybe_item(self) -> Atom | None: ...

    def item(self) -> typing.Sequence[Atom]: ...


class ZeroItemsLabel:
    """Sentinels equal to either backend's ZeroItems labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ITEM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("ZeroItems.Label.ITEM")


class Expr(typing.Protocol):
    kind: typing.Literal[NodeKind.EXPR] = NodeKind.EXPR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Expr]]: ...

    def append(self, child: Atom | Expr, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Atom | Expr], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Expr) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Expr]: ...

    def insert(
        self, index: int, child: Atom | Expr, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Expr]: ...

    def replace_at(
        self, index: int, child: Atom | Expr, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_atom(self, child: Atom) -> None: ...

    def extend_atom(self, children: typing.Iterable[Atom]) -> None: ...

    def children_atom(self) -> typing.Iterator[Atom]: ...

    def child_atom(self) -> Atom: ...

    def maybe_atom(self) -> Atom | None: ...

    def append_lhs(self, child: Expr) -> None: ...

    def extend_lhs(self, children: typing.Iterable[Expr]) -> None: ...

    def children_lhs(self) -> typing.Iterator[Expr]: ...

    def child_lhs(self) -> Expr: ...

    def maybe_lhs(self) -> Expr | None: ...

    def append_rhs(self, child: Atom) -> None: ...

    def extend_rhs(self, children: typing.Iterable[Atom]) -> None: ...

    def children_rhs(self) -> typing.Iterator[Atom]: ...

    def child_rhs(self) -> Atom: ...

    def maybe_rhs(self) -> Atom | None: ...

    def atom(self) -> Atom | None: ...

    def lhs(self) -> Expr | None: ...

    def rhs(self) -> Atom | None: ...


class ExprLabel:
    """Sentinels equal to either backend's Expr labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ATOM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Expr.Label.ATOM")
    LHS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Expr.Label.LHS")
    RHS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Expr.Label.RHS")


class Lval(typing.Protocol):
    kind: typing.Literal[NodeKind.LVAL] = NodeKind.LVAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Rval]]: ...

    def append(self, child: Name | Rval, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Name | Rval], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Lval) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Rval]: ...

    def insert(
        self, index: int, child: Name | Rval, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Rval]: ...

    def replace_at(
        self, index: int, child: Name | Rval, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_base(self, child: Name) -> None: ...

    def extend_base(self, children: typing.Iterable[Name]) -> None: ...

    def children_base(self) -> typing.Iterator[Name]: ...

    def child_base(self) -> Name: ...

    def maybe_base(self) -> Name | None: ...

    def append_inner(self, child: Rval) -> None: ...

    def extend_inner(self, children: typing.Iterable[Rval]) -> None: ...

    def children_inner(self) -> typing.Iterator[Rval]: ...

    def child_inner(self) -> Rval: ...

    def maybe_inner(self) -> Rval | None: ...

    def base(self) -> Name | None: ...

    def inner(self) -> Rval | None: ...


class LvalLabel:
    """Sentinels equal to either backend's Lval labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BASE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Lval.Label.BASE")
    INNER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Lval.Label.INNER")


class Rval(typing.Protocol):
    kind: typing.Literal[NodeKind.RVAL] = NodeKind.RVAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Lval | Num]]: ...

    def append(self, child: Lval | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Lval | Num], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Rval) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Lval | Num]: ...

    def insert(
        self, index: int, child: Lval | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Lval | Num]: ...

    def replace_at(
        self, index: int, child: Lval | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_base(self, child: Num) -> None: ...

    def extend_base(self, children: typing.Iterable[Num]) -> None: ...

    def children_base(self) -> typing.Iterator[Num]: ...

    def child_base(self) -> Num: ...

    def maybe_base(self) -> Num | None: ...

    def append_inner(self, child: Lval) -> None: ...

    def extend_inner(self, children: typing.Iterable[Lval]) -> None: ...

    def children_inner(self) -> typing.Iterator[Lval]: ...

    def child_inner(self) -> Lval: ...

    def maybe_inner(self) -> Lval | None: ...

    def base(self) -> Num | None: ...

    def inner(self) -> Lval | None: ...


class RvalLabel:
    """Sentinels equal to either backend's Rval labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    BASE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Rval.Label.BASE")
    INNER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Rval.Label.INNER")


class Arrow(typing.Protocol):
    kind: typing.Literal[NodeKind.ARROW] = NodeKind.ARROW
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name]]: ...

    def append(self, child: Name, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Name], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Arrow) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name]: ...

    def insert(
        self, index: int, child: Name, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name]: ...

    def replace_at(
        self, index: int, child: Name, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_target(self, child: Name) -> None: ...

    def extend_target(self, children: typing.Iterable[Name]) -> None: ...

    def children_target(self) -> typing.Iterator[Name]: ...

    def child_target(self) -> Name: ...

    def maybe_target(self) -> Name | None: ...

    def target(self) -> Name: ...


class ArrowLabel:
    """Sentinels equal to either backend's Arrow labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    TARGET: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Arrow.Label.TARGET")


class LatinWord(typing.Protocol):
    kind: typing.Literal[NodeKind.LATINWORD] = NodeKind.LATINWORD
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

    def extend_children(self, other: LatinWord) -> None: ...

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


class LatinWordLabel:
    """Sentinels equal to either backend's LatinWord labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("LatinWord.Label.VALUE")


class Tagged(typing.Protocol):
    kind: typing.Literal[NodeKind.TAGGED] = NodeKind.TAGGED
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

    def extend_children(self, other: Tagged) -> None: ...

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


class TaggedLabel:
    """Sentinels equal to either backend's Tagged labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Tagged.Label.VALUE")


class Val(typing.Protocol):
    kind: typing.Literal[NodeKind.VAL] = NodeKind.VAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol
        ]
    ]: ...

    def append(
        self,
        child: Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Val) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def insert(
        self,
        index: int,
        child: Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_item(self, child: Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_item(
        self, children: typing.Iterable[Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ) -> None: ...

    def children_item(self) -> typing.Iterator[Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_item(self) -> Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_item(self) -> Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def item(self) -> Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class ValLabel:
    """Sentinels equal to either backend's Val labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ITEM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Val.Label.ITEM")


class LeadingWs(typing.Protocol):
    kind: typing.Literal[NodeKind.LEADINGWS] = NodeKind.LEADINGWS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | Trivia]]: ...

    def append(
        self, child: Num | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self, children: typing.Iterable[Num | Trivia], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: LeadingWs) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | Trivia]: ...

    def insert(
        self, index: int, child: Num | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | Trivia]: ...

    def replace_at(
        self, index: int, child: Num | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_num(self, child: Num) -> None: ...

    def extend_num(self, children: typing.Iterable[Num]) -> None: ...

    def children_num(self) -> typing.Iterator[Num]: ...

    def child_num(self) -> Num: ...

    def maybe_num(self) -> Num | None: ...

    def num(self) -> Num: ...


class LeadingWsLabel:
    """Sentinels equal to either backend's LeadingWs labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    NUM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("LeadingWs.Label.NUM")


class Grouped(typing.Protocol):
    kind: typing.Literal[NodeKind.GROUPED] = NodeKind.GROUPED
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num | Trivia]]: ...

    def append(
        self, child: Name | Num | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Name | Num | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Grouped) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num | Trivia]: ...

    def insert(
        self, index: int, child: Name | Num | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num | Trivia]: ...

    def replace_at(
        self, index: int, child: Name | Num | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_left(self, child: Name | Num) -> None: ...

    def extend_left(self, children: typing.Iterable[Name | Num]) -> None: ...

    def children_left(self) -> typing.Iterator[Name | Num]: ...

    def child_left(self) -> Name | Num: ...

    def maybe_left(self) -> Name | Num | None: ...

    def left(self) -> Name | Num: ...


class GroupedLabel:
    """Sentinels equal to either backend's Grouped labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    LEFT: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Grouped.Label.LEFT")


class RecViaSub(typing.Protocol):
    kind: typing.Literal[NodeKind.RECVIASUB] = NodeKind.RECVIASUB
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Name | RecViaSub]]: ...

    def append(
        self, child: Atom | Name | RecViaSub, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Atom | Name | RecViaSub],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: RecViaSub) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Name | RecViaSub]: ...

    def insert(
        self,
        index: int,
        child: Atom | Name | RecViaSub,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | Name | RecViaSub]: ...

    def replace_at(
        self,
        index: int,
        child: Atom | Name | RecViaSub,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_inner(self, child: Atom | RecViaSub) -> None: ...

    def extend_inner(self, children: typing.Iterable[Atom | RecViaSub]) -> None: ...

    def children_inner(self) -> typing.Iterator[Atom | RecViaSub]: ...

    def child_inner(self) -> Atom | RecViaSub: ...

    def maybe_inner(self) -> Atom | RecViaSub | None: ...

    def append_suffix(self, child: Name) -> None: ...

    def extend_suffix(self, children: typing.Iterable[Name]) -> None: ...

    def children_suffix(self) -> typing.Iterator[Name]: ...

    def child_suffix(self) -> Name: ...

    def maybe_suffix(self) -> Name | None: ...

    def inner(self) -> Atom | RecViaSub: ...

    def suffix(self) -> Name: ...


class RecViaSubLabel:
    """Sentinels equal to either backend's RecViaSub labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    INNER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("RecViaSub.Label.INNER")
    SUFFIX: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("RecViaSub.Label.SUFFIX")


class Nest(typing.Protocol):
    kind: typing.Literal[NodeKind.NEST] = NodeKind.NEST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Nest | Num]]: ...

    def append(self, child: Nest | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Nest | Num], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Nest) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Nest | Num]: ...

    def insert(
        self, index: int, child: Nest | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Nest | Num]: ...

    def replace_at(
        self, index: int, child: Nest | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_inner(self, child: Nest) -> None: ...

    def extend_inner(self, children: typing.Iterable[Nest]) -> None: ...

    def children_inner(self) -> typing.Iterator[Nest]: ...

    def child_inner(self) -> Nest: ...

    def maybe_inner(self) -> Nest | None: ...

    def append_leaf(self, child: Num) -> None: ...

    def extend_leaf(self, children: typing.Iterable[Num]) -> None: ...

    def children_leaf(self) -> typing.Iterator[Num]: ...

    def child_leaf(self) -> Num: ...

    def maybe_leaf(self) -> Num | None: ...

    def inner(self) -> Nest | None: ...

    def leaf(self) -> Num | None: ...


class NestLabel:
    """Sentinels equal to either backend's Nest labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    INNER: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Nest.Label.INNER")
    LEAF: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Nest.Label.LEAF")


class NestSum(typing.Protocol):
    kind: typing.Literal[NodeKind.NESTSUM] = NodeKind.NESTSUM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Nest | NestSum]]: ...

    def append(
        self, child: Nest | NestSum, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Nest | NestSum],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: NestSum) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Nest | NestSum]: ...

    def insert(
        self, index: int, child: Nest | NestSum, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Nest | NestSum]: ...

    def replace_at(
        self, index: int, child: Nest | NestSum, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_first(self, child: Nest) -> None: ...

    def extend_first(self, children: typing.Iterable[Nest]) -> None: ...

    def children_first(self) -> typing.Iterator[Nest]: ...

    def child_first(self) -> Nest: ...

    def maybe_first(self) -> Nest | None: ...

    def append_lhs(self, child: NestSum) -> None: ...

    def extend_lhs(self, children: typing.Iterable[NestSum]) -> None: ...

    def children_lhs(self) -> typing.Iterator[NestSum]: ...

    def child_lhs(self) -> NestSum: ...

    def maybe_lhs(self) -> NestSum | None: ...

    def append_rhs(self, child: Nest) -> None: ...

    def extend_rhs(self, children: typing.Iterable[Nest]) -> None: ...

    def children_rhs(self) -> typing.Iterator[Nest]: ...

    def child_rhs(self) -> Nest: ...

    def maybe_rhs(self) -> Nest | None: ...

    def first(self) -> Nest | None: ...

    def lhs(self) -> NestSum | None: ...

    def rhs(self) -> Nest | None: ...


class NestSumLabel:
    """Sentinels equal to either backend's NestSum labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    FIRST: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("NestSum.Label.FIRST")
    LHS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("NestSum.Label.LHS")
    RHS: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("NestSum.Label.RHS")


class DigitSeq(typing.Protocol):
    kind: typing.Literal[NodeKind.DIGITSEQ] = NodeKind.DIGITSEQ
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

    def extend_children(self, other: DigitSeq) -> None: ...

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


class DigitSeqLabel:
    """Sentinels equal to either backend's DigitSeq labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("DigitSeq.Label.VALUE")


class WordSeq(typing.Protocol):
    kind: typing.Literal[NodeKind.WORDSEQ] = NodeKind.WORDSEQ
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

    def extend_children(self, other: WordSeq) -> None: ...

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


class WordSeqLabel:
    """Sentinels equal to either backend's WordSeq labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("WordSeq.Label.VALUE")


class WsSeq(typing.Protocol):
    kind: typing.Literal[NodeKind.WSSEQ] = NodeKind.WSSEQ
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

    def extend_children(self, other: WsSeq) -> None: ...

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


class WsSeqLabel:
    """Sentinels equal to either backend's WsSeq labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("WsSeq.Label.VALUE")


class ThreeToFiveDigits(typing.Protocol):
    kind: typing.Literal[NodeKind.THREETOFIVEDIGITS] = NodeKind.THREETOFIVEDIGITS
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

    def extend_children(self, other: ThreeToFiveDigits) -> None: ...

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


class ThreeToFiveDigitsLabel:
    """Sentinels equal to either backend's ThreeToFiveDigits labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ThreeToFiveDigits.Label.VALUE"
    )


class ExactlyTwoDigits(typing.Protocol):
    kind: typing.Literal[NodeKind.EXACTLYTWODIGITS] = NodeKind.EXACTLYTWODIGITS
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

    def extend_children(self, other: ExactlyTwoDigits) -> None: ...

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


class ExactlyTwoDigitsLabel:
    """Sentinels equal to either backend's ExactlyTwoDigits labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "ExactlyTwoDigits.Label.VALUE"
    )


class EscapedMetas(typing.Protocol):
    kind: typing.Literal[NodeKind.ESCAPEDMETAS] = NodeKind.ESCAPEDMETAS
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

    def extend_children(self, other: EscapedMetas) -> None: ...

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


class EscapedMetasLabel:
    """Sentinels equal to either backend's EscapedMetas labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("EscapedMetas.Label.VALUE")


class LatinRange(typing.Protocol):
    kind: typing.Literal[NodeKind.LATINRANGE] = NodeKind.LATINRANGE
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

    def extend_children(self, other: LatinRange) -> None: ...

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


class LatinRangeLabel:
    """Sentinels equal to either backend's LatinRange labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("LatinRange.Label.VALUE")


class NcGroupAlt(typing.Protocol):
    kind: typing.Literal[NodeKind.NCGROUPALT] = NodeKind.NCGROUPALT
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

    def extend_children(self, other: NcGroupAlt) -> None: ...

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


class NcGroupAltLabel:
    """Sentinels equal to either backend's NcGroupAlt labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("NcGroupAlt.Label.VALUE")


class CaseInsensitive(typing.Protocol):
    kind: typing.Literal[NodeKind.CASEINSENSITIVE] = NodeKind.CASEINSENSITIVE
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

    def extend_children(self, other: CaseInsensitive) -> None: ...

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


class CaseInsensitiveLabel:
    """Sentinels equal to either backend's CaseInsensitive labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "CaseInsensitive.Label.VALUE"
    )


class AnchoredWord(typing.Protocol):
    kind: typing.Literal[NodeKind.ANCHOREDWORD] = NodeKind.ANCHOREDWORD
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

    def extend_children(self, other: AnchoredWord) -> None: ...

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


class AnchoredWordLabel:
    """Sentinels equal to either backend's AnchoredWord labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("AnchoredWord.Label.VALUE")


class Pair(typing.Protocol):
    kind: typing.Literal[NodeKind.PAIR] = NodeKind.PAIR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]]: ...

    def append(self, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Name | Num], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Pair) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def insert(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def replace_at(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_key(self, child: Name) -> None: ...

    def extend_key(self, children: typing.Iterable[Name]) -> None: ...

    def children_key(self) -> typing.Iterator[Name]: ...

    def child_key(self) -> Name: ...

    def maybe_key(self) -> Name | None: ...

    def append_val(self, child: Num) -> None: ...

    def extend_val(self, children: typing.Iterable[Num]) -> None: ...

    def children_val(self) -> typing.Iterator[Num]: ...

    def child_val(self) -> Num: ...

    def maybe_val(self) -> Num | None: ...

    def key(self) -> Name: ...

    def val(self) -> Num: ...


class PairLabel:
    """Sentinels equal to either backend's Pair labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    KEY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Pair.Label.KEY")
    VAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Pair.Label.VAL")


class Wrapper(typing.Protocol):
    kind: typing.Literal[NodeKind.WRAPPER] = NodeKind.WRAPPER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]]: ...

    def append(self, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Name | Num], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: Wrapper) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def insert(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def replace_at(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_key(self, child: Name) -> None: ...

    def extend_key(self, children: typing.Iterable[Name]) -> None: ...

    def children_key(self) -> typing.Iterator[Name]: ...

    def child_key(self) -> Name: ...

    def maybe_key(self) -> Name | None: ...

    def append_val(self, child: Num) -> None: ...

    def extend_val(self, children: typing.Iterable[Num]) -> None: ...

    def children_val(self) -> typing.Iterator[Num]: ...

    def child_val(self) -> Num: ...

    def maybe_val(self) -> Num | None: ...

    def key(self) -> Name: ...

    def val(self) -> Num: ...


class WrapperLabel:
    """Sentinels equal to either backend's Wrapper labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    KEY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Wrapper.Label.KEY")
    VAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Wrapper.Label.VAL")


class OptWrapper(typing.Protocol):
    kind: typing.Literal[NodeKind.OPTWRAPPER] = NodeKind.OPTWRAPPER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]]: ...

    def append(self, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Name | Num], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: OptWrapper) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def insert(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def replace_at(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_key(self, child: Name) -> None: ...

    def extend_key(self, children: typing.Iterable[Name]) -> None: ...

    def children_key(self) -> typing.Iterator[Name]: ...

    def child_key(self) -> Name: ...

    def maybe_key(self) -> Name | None: ...

    def append_val(self, child: Num) -> None: ...

    def extend_val(self, children: typing.Iterable[Num]) -> None: ...

    def children_val(self) -> typing.Iterator[Num]: ...

    def child_val(self) -> Num: ...

    def maybe_val(self) -> Num | None: ...

    def key(self) -> Name | None: ...

    def val(self) -> Num | None: ...


class OptWrapperLabel:
    """Sentinels equal to either backend's OptWrapper labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    KEY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("OptWrapper.Label.KEY")
    VAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("OptWrapper.Label.VAL")


class RepWrapper(typing.Protocol):
    kind: typing.Literal[NodeKind.REPWRAPPER] = NodeKind.REPWRAPPER
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(self) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]]: ...

    def append(self, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[Name | Num], label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend_children(self, other: RepWrapper) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def insert(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Name | Num]: ...

    def replace_at(
        self, index: int, child: Name | Num, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_key(self, child: Name) -> None: ...

    def extend_key(self, children: typing.Iterable[Name]) -> None: ...

    def children_key(self) -> typing.Iterator[Name]: ...

    def child_key(self) -> Name: ...

    def maybe_key(self) -> Name | None: ...

    def append_val(self, child: Num) -> None: ...

    def extend_val(self, children: typing.Iterable[Num]) -> None: ...

    def children_val(self) -> typing.Iterator[Num]: ...

    def child_val(self) -> Num: ...

    def maybe_val(self) -> Num | None: ...

    def key(self) -> typing.Sequence[Name]: ...

    def val(self) -> typing.Sequence[Num]: ...


class RepWrapperLabel:
    """Sentinels equal to either backend's RepWrapper labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    KEY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("RepWrapper.Label.KEY")
    VAL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("RepWrapper.Label.VAL")


class KwLabels(typing.Protocol):
    kind: typing.Literal[NodeKind.KWLABELS] = NodeKind.KWLABELS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ]: ...

    def append(
        self,
        child: Num | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Num | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: KwLabels) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def insert(
        self,
        index: int,
        child: Num | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Num | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_match(self, child: Num) -> None: ...

    def extend_match(self, children: typing.Iterable[Num]) -> None: ...

    def children_match(self) -> typing.Iterator[Num]: ...

    def child_match(self) -> Num: ...

    def maybe_match(self) -> Num | None: ...

    def append_type(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_type(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_type(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_type(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_type(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def match(self) -> Num: ...

    def type(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def type_text(self) -> str: ...


class KwLabelsLabel:
    """Sentinels equal to either backend's KwLabels labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    MATCH: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("KwLabels.Label.MATCH")
    TYPE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("KwLabels.Label.TYPE")


class Quoted(typing.Protocol):
    kind: typing.Literal[NodeKind.QUOTED] = NodeKind.QUOTED
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

    def extend_children(self, other: Quoted) -> None: ...

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

    def append_tail(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_tail(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_tail(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_tail(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_tail(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def tail(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def tail_text(self) -> str | None: ...

    def value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def value_text(self) -> str: ...

    def text(self) -> str: ...


class QuotedLabel:
    """Sentinels equal to either backend's Quoted labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    TAIL: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Quoted.Label.TAIL")
    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Quoted.Label.VALUE")


class MixedOpt(typing.Protocol):
    kind: typing.Literal[NodeKind.MIXEDOPT] = NodeKind.MIXEDOPT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ]: ...

    def append(
        self,
        child: Num | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Num | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: MixedOpt) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def insert(
        self,
        index: int,
        child: Num | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Num | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_key(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_key(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_key(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_key(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_key(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_node(self, child: Num) -> None: ...

    def extend_node(self, children: typing.Iterable[Num]) -> None: ...

    def children_node(self) -> typing.Iterator[Num]: ...

    def child_node(self) -> Num: ...

    def maybe_node(self) -> Num | None: ...

    def key(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def key_text(self) -> str | None: ...

    def node(self) -> Num: ...


class MixedOptLabel:
    """Sentinels equal to either backend's MixedOpt labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    KEY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("MixedOpt.Label.KEY")
    NODE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("MixedOpt.Label.NODE")


class UuidVal(typing.Protocol):
    kind: typing.Literal[NodeKind.UUIDVAL] = NodeKind.UUIDVAL
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

    def extend_children(self, other: UuidVal) -> None: ...

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


class UuidValLabel:
    """Sentinels equal to either backend's UuidVal labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("UuidVal.Label.VALUE")


class DecimalVal(typing.Protocol):
    kind: typing.Literal[NodeKind.DECIMALVAL] = NodeKind.DECIMALVAL
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

    def extend_children(self, other: DecimalVal) -> None: ...

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


class DecimalValLabel:
    """Sentinels equal to either backend's DecimalVal labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("DecimalVal.Label.VALUE")


class Colour(typing.Protocol):
    kind: typing.Literal[NodeKind.COLOUR] = NodeKind.COLOUR
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

    def extend_children(self, other: Colour) -> None: ...

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

    def append_dark(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_dark(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_dark(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_dark(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_dark(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_shade(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_shade(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_shade(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_shade(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_shade(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def dark(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def dark_text(self) -> str | None: ...

    def shade(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def shade_text(self) -> str | None: ...

    def text(self) -> str: ...

    def variant(self) -> fltk.fegen.pyrt.label_protocol.LabelProtocol: ...


class ColourLabel:
    """Sentinels equal to either backend's Colour labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    DARK: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Colour.Label.DARK")
    SHADE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Colour.Label.SHADE")


class SumChain(typing.Protocol):
    kind: typing.Literal[NodeKind.SUMCHAIN] = NodeKind.SUMCHAIN
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[
        tuple[
            fltk.fegen.pyrt.label_protocol.LabelProtocol | None,
            Num | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        ]
    ]: ...

    def append(
        self,
        child: Num | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Num | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: SumChain) -> None: ...

    def child(
        self,
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def insert(
        self,
        index: int,
        child: Num | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[
        fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Num | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ]: ...

    def replace_at(
        self,
        index: int,
        child: Num | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_op(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_op(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_op(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_op(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_op(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...

    def append_term(self, child: Num) -> None: ...

    def extend_term(self, children: typing.Iterable[Num]) -> None: ...

    def children_term(self) -> typing.Iterator[Num]: ...

    def child_term(self) -> Num: ...

    def maybe_term(self) -> Num | None: ...

    def op(self) -> typing.Sequence[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def term(self) -> typing.Sequence[Num]: ...


class SumChainLabel:
    """Sentinels equal to either backend's SumChain labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    OP: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("SumChain.Label.OP")
    TERM: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("SumChain.Label.TERM")


class EntryKey(typing.Protocol):
    kind: typing.Literal[NodeKind.ENTRYKEY] = NodeKind.ENTRYKEY
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

    def extend_children(self, other: EntryKey) -> None: ...

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


class EntryKeyLabel:
    """Sentinels equal to either backend's EntryKey labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("EntryKey.Label.VALUE")


class Entry(typing.Protocol):
    kind: typing.Literal[NodeKind.ENTRY] = NodeKind.ENTRY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | EntryKey | Trivia]]: ...

    def append(
        self, child: Atom | EntryKey | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Atom | EntryKey | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Entry) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | EntryKey | Trivia]: ...

    def insert(
        self,
        index: int,
        child: Atom | EntryKey | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | EntryKey | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: Atom | EntryKey | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_key(self, child: EntryKey) -> None: ...

    def extend_key(self, children: typing.Iterable[EntryKey]) -> None: ...

    def children_key(self) -> typing.Iterator[EntryKey]: ...

    def child_key(self) -> EntryKey: ...

    def maybe_key(self) -> EntryKey | None: ...

    def append_value(self, child: Atom) -> None: ...

    def extend_value(self, children: typing.Iterable[Atom]) -> None: ...

    def children_value(self) -> typing.Iterator[Atom]: ...

    def child_value(self) -> Atom: ...

    def maybe_value(self) -> Atom | None: ...

    def key(self) -> EntryKey: ...

    def value(self) -> Atom: ...


class EntryLabel:
    """Sentinels equal to either backend's Entry labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    KEY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Entry.Label.KEY")
    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Entry.Label.VALUE")


class Entries(typing.Protocol):
    kind: typing.Literal[NodeKind.ENTRIES] = NodeKind.ENTRIES
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Entry | Trivia]]: ...

    def append(
        self, child: Entry | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Entry | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: Entries) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Entry | Trivia]: ...

    def insert(
        self, index: int, child: Entry | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Entry | Trivia]: ...

    def replace_at(
        self, index: int, child: Entry | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_entry(self, child: Entry) -> None: ...

    def extend_entry(self, children: typing.Iterable[Entry]) -> None: ...

    def children_entry(self) -> typing.Iterator[Entry]: ...

    def child_entry(self) -> Entry: ...

    def maybe_entry(self) -> Entry | None: ...

    def entry(self) -> typing.Sequence[Entry]: ...


class EntriesLabel:
    """Sentinels equal to either backend's Entries labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    ENTRY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("Entries.Label.ENTRY")


class MultiEntry(typing.Protocol):
    kind: typing.Literal[NodeKind.MULTIENTRY] = NodeKind.MULTIENTRY
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | EntryKey | Trivia]]: ...

    def append(
        self, child: Atom | EntryKey | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Atom | EntryKey | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: MultiEntry) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | EntryKey | Trivia]: ...

    def insert(
        self,
        index: int,
        child: Atom | EntryKey | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, Atom | EntryKey | Trivia]: ...

    def replace_at(
        self,
        index: int,
        child: Atom | EntryKey | Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def clear(self) -> None: ...

    def append_key(self, child: EntryKey) -> None: ...

    def extend_key(self, children: typing.Iterable[EntryKey]) -> None: ...

    def children_key(self) -> typing.Iterator[EntryKey]: ...

    def child_key(self) -> EntryKey: ...

    def maybe_key(self) -> EntryKey | None: ...

    def append_value(self, child: Atom) -> None: ...

    def extend_value(self, children: typing.Iterable[Atom]) -> None: ...

    def children_value(self) -> typing.Iterator[Atom]: ...

    def child_value(self) -> Atom: ...

    def maybe_value(self) -> Atom | None: ...

    def key(self) -> EntryKey: ...

    def value(self) -> Atom: ...


class MultiEntryLabel:
    """Sentinels equal to either backend's MultiEntry labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    KEY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("MultiEntry.Label.KEY")
    VALUE: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember("MultiEntry.Label.VALUE")


class MultiEntries(typing.Protocol):
    kind: typing.Literal[NodeKind.MULTIENTRIES] = NodeKind.MULTIENTRIES
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol

    @property
    def children(
        self,
    ) -> typing.Sequence[tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, MultiEntry | Trivia]]: ...

    def append(
        self, child: MultiEntry | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[MultiEntry | Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None: ...

    def extend_children(self, other: MultiEntries) -> None: ...

    def child(self) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, MultiEntry | Trivia]: ...

    def insert(
        self, index: int, child: MultiEntry | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def remove_at(
        self, index: int
    ) -> tuple[fltk.fegen.pyrt.label_protocol.LabelProtocol | None, MultiEntry | Trivia]: ...

    def replace_at(
        self, index: int, child: MultiEntry | Trivia, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_multi_entry(self, child: MultiEntry) -> None: ...

    def extend_multi_entry(self, children: typing.Iterable[MultiEntry]) -> None: ...

    def children_multi_entry(self) -> typing.Iterator[MultiEntry]: ...

    def child_multi_entry(self) -> MultiEntry: ...

    def maybe_multi_entry(self) -> MultiEntry | None: ...

    def multi_entry(self) -> typing.Sequence[MultiEntry]: ...


class MultiEntriesLabel:
    """Sentinels equal to either backend's MultiEntries labels, for identifying one.

    They are not a backend's own label objects, so insert() and replace_at() reject
    them on every backend; pass those a label read off the node being mutated (from
    children, remove_at() or variant()).
    """

    MULTI_ENTRY: typing.Final[fltk.fegen.pyrt.label_protocol.LabelProtocol] = _ProtocolLabelMember(
        "MultiEntries.Label.MULTI_ENTRY"
    )


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
    def Num(self) -> type[Num]: ...

    @property
    def Name(self) -> type[Name]: ...

    @property
    def Atom(self) -> type[Atom]: ...

    @property
    def ParenExpr(self) -> type[ParenExpr]: ...

    @property
    def Stmt(self) -> type[Stmt]: ...

    @property
    def Items(self) -> type[Items]: ...

    @property
    def OptItem(self) -> type[OptItem]: ...

    @property
    def ZeroItems(self) -> type[ZeroItems]: ...

    @property
    def Expr(self) -> type[Expr]: ...

    @property
    def Lval(self) -> type[Lval]: ...

    @property
    def Rval(self) -> type[Rval]: ...

    @property
    def Arrow(self) -> type[Arrow]: ...

    @property
    def LatinWord(self) -> type[LatinWord]: ...

    @property
    def Tagged(self) -> type[Tagged]: ...

    @property
    def Val(self) -> type[Val]: ...

    @property
    def LeadingWs(self) -> type[LeadingWs]: ...

    @property
    def Grouped(self) -> type[Grouped]: ...

    @property
    def RecViaSub(self) -> type[RecViaSub]: ...

    @property
    def Nest(self) -> type[Nest]: ...

    @property
    def NestSum(self) -> type[NestSum]: ...

    @property
    def DigitSeq(self) -> type[DigitSeq]: ...

    @property
    def WordSeq(self) -> type[WordSeq]: ...

    @property
    def WsSeq(self) -> type[WsSeq]: ...

    @property
    def ThreeToFiveDigits(self) -> type[ThreeToFiveDigits]: ...

    @property
    def ExactlyTwoDigits(self) -> type[ExactlyTwoDigits]: ...

    @property
    def EscapedMetas(self) -> type[EscapedMetas]: ...

    @property
    def LatinRange(self) -> type[LatinRange]: ...

    @property
    def NcGroupAlt(self) -> type[NcGroupAlt]: ...

    @property
    def CaseInsensitive(self) -> type[CaseInsensitive]: ...

    @property
    def AnchoredWord(self) -> type[AnchoredWord]: ...

    @property
    def Pair(self) -> type[Pair]: ...

    @property
    def Wrapper(self) -> type[Wrapper]: ...

    @property
    def OptWrapper(self) -> type[OptWrapper]: ...

    @property
    def RepWrapper(self) -> type[RepWrapper]: ...

    @property
    def KwLabels(self) -> type[KwLabels]: ...

    @property
    def Quoted(self) -> type[Quoted]: ...

    @property
    def MixedOpt(self) -> type[MixedOpt]: ...

    @property
    def UuidVal(self) -> type[UuidVal]: ...

    @property
    def DecimalVal(self) -> type[DecimalVal]: ...

    @property
    def Colour(self) -> type[Colour]: ...

    @property
    def SumChain(self) -> type[SumChain]: ...

    @property
    def EntryKey(self) -> type[EntryKey]: ...

    @property
    def Entry(self) -> type[Entry]: ...

    @property
    def Entries(self) -> type[Entries]: ...

    @property
    def MultiEntry(self) -> type[MultiEntry]: ...

    @property
    def MultiEntries(self) -> type[MultiEntries]: ...

    @property
    def Trivia(self) -> type[Trivia]: ...
