# ruff: noqa: N802
from __future__ import annotations

import enum
import typing

import fltk.fegen.pyrt.terminalsrc

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.span_protocol
__all__ = [
    "AnchoredWord",
    "Arrow",
    "Atom",
    "CaseInsensitive",
    "CstModule",
    "DigitSeq",
    "EscapedMetas",
    "ExactlyTwoDigits",
    "Expr",
    "Grouped",
    "Items",
    "LatinRange",
    "LatinWord",
    "LeadingWs",
    "Lval",
    "Name",
    "NcGroupAlt",
    "Nest",
    "NestSum",
    "NodeKind",
    "Num",
    "OptItem",
    "ParenExpr",
    "RecViaSub",
    "Rval",
    "Span",
    "Stmt",
    "Tagged",
    "ThreeToFiveDigits",
    "Trivia",
    "Val",
    "WordSeq",
    "WsSeq",
    "ZeroItems",
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
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.NUM] = NodeKind.NUM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Num) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


Num.Label.VALUE = _ProtocolLabelMember("Num.Label.VALUE")


class Name(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.NAME] = NodeKind.NAME
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Name) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


Name.Label.VALUE = _ProtocolLabelMember("Name.Label.VALUE")


class Atom(typing.Protocol):
    class Label:
        NAME: typing.ClassVar[object]
        NUM: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ATOM] = NodeKind.ATOM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Name | Num]]

    def append(self, child: Name | Num, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Name | Num], label: Label | None = None) -> None: ...

    def extend_children(self, other: Atom) -> None: ...

    def child(self) -> tuple[Label | None, Name | Num]: ...

    def insert(self, index: int, child: Name | Num, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Name | Num]: ...

    def replace_at(self, index: int, child: Name | Num, label: Label | None = None) -> None: ...

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


Atom.Label.NAME = _ProtocolLabelMember("Atom.Label.NAME")
Atom.Label.NUM = _ProtocolLabelMember("Atom.Label.NUM")


class ParenExpr(typing.Protocol):
    class Label:
        INNER: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.PARENEXPR] = NodeKind.PARENEXPR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Atom | Trivia]]

    def append(self, child: Atom | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Atom | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: ParenExpr) -> None: ...

    def child(self) -> tuple[Label | None, Atom | Trivia]: ...

    def insert(self, index: int, child: Atom | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Atom | Trivia]: ...

    def replace_at(self, index: int, child: Atom | Trivia, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_inner(self, child: Atom) -> None: ...

    def extend_inner(self, children: typing.Iterable[Atom]) -> None: ...

    def children_inner(self) -> typing.Iterator[Atom]: ...

    def child_inner(self) -> Atom: ...

    def maybe_inner(self) -> Atom | None: ...


ParenExpr.Label.INNER = _ProtocolLabelMember("ParenExpr.Label.INNER")


class Stmt(typing.Protocol):
    class Label:
        LHS: typing.ClassVar[object]
        RHS: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.STMT] = NodeKind.STMT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Atom | Trivia]]

    def append(self, child: Atom | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Atom | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: Stmt) -> None: ...

    def child(self) -> tuple[Label | None, Atom | Trivia]: ...

    def insert(self, index: int, child: Atom | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Atom | Trivia]: ...

    def replace_at(self, index: int, child: Atom | Trivia, label: Label | None = None) -> None: ...

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


Stmt.Label.LHS = _ProtocolLabelMember("Stmt.Label.LHS")
Stmt.Label.RHS = _ProtocolLabelMember("Stmt.Label.RHS")


class Items(typing.Protocol):
    class Label:
        ITEM: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ITEMS] = NodeKind.ITEMS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Atom]]

    def append(self, child: Atom, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Atom], label: Label | None = None) -> None: ...

    def extend_children(self, other: Items) -> None: ...

    def child(self) -> tuple[Label | None, Atom]: ...

    def insert(self, index: int, child: Atom, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Atom]: ...

    def replace_at(self, index: int, child: Atom, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_item(self, child: Atom) -> None: ...

    def extend_item(self, children: typing.Iterable[Atom]) -> None: ...

    def children_item(self) -> typing.Iterator[Atom]: ...

    def child_item(self) -> Atom: ...

    def maybe_item(self) -> Atom | None: ...


Items.Label.ITEM = _ProtocolLabelMember("Items.Label.ITEM")


class OptItem(typing.Protocol):
    class Label:
        ITEM: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.OPTITEM] = NodeKind.OPTITEM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Atom]]

    def append(self, child: Atom, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Atom], label: Label | None = None) -> None: ...

    def extend_children(self, other: OptItem) -> None: ...

    def child(self) -> tuple[Label | None, Atom]: ...

    def insert(self, index: int, child: Atom, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Atom]: ...

    def replace_at(self, index: int, child: Atom, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_item(self, child: Atom) -> None: ...

    def extend_item(self, children: typing.Iterable[Atom]) -> None: ...

    def children_item(self) -> typing.Iterator[Atom]: ...

    def child_item(self) -> Atom: ...

    def maybe_item(self) -> Atom | None: ...


OptItem.Label.ITEM = _ProtocolLabelMember("OptItem.Label.ITEM")


class ZeroItems(typing.Protocol):
    class Label:
        ITEM: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ZEROITEMS] = NodeKind.ZEROITEMS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Atom]]

    def append(self, child: Atom, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Atom], label: Label | None = None) -> None: ...

    def extend_children(self, other: ZeroItems) -> None: ...

    def child(self) -> tuple[Label | None, Atom]: ...

    def insert(self, index: int, child: Atom, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Atom]: ...

    def replace_at(self, index: int, child: Atom, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_item(self, child: Atom) -> None: ...

    def extend_item(self, children: typing.Iterable[Atom]) -> None: ...

    def children_item(self) -> typing.Iterator[Atom]: ...

    def child_item(self) -> Atom: ...

    def maybe_item(self) -> Atom | None: ...


ZeroItems.Label.ITEM = _ProtocolLabelMember("ZeroItems.Label.ITEM")


class Expr(typing.Protocol):
    class Label:
        ATOM: typing.ClassVar[object]
        LHS: typing.ClassVar[object]
        RHS: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.EXPR] = NodeKind.EXPR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Atom | Expr]]

    def append(self, child: Atom | Expr, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Atom | Expr], label: Label | None = None) -> None: ...

    def extend_children(self, other: Expr) -> None: ...

    def child(self) -> tuple[Label | None, Atom | Expr]: ...

    def insert(self, index: int, child: Atom | Expr, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Atom | Expr]: ...

    def replace_at(self, index: int, child: Atom | Expr, label: Label | None = None) -> None: ...

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


Expr.Label.ATOM = _ProtocolLabelMember("Expr.Label.ATOM")
Expr.Label.LHS = _ProtocolLabelMember("Expr.Label.LHS")
Expr.Label.RHS = _ProtocolLabelMember("Expr.Label.RHS")


class Lval(typing.Protocol):
    class Label:
        BASE: typing.ClassVar[object]
        INNER: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LVAL] = NodeKind.LVAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Name | Rval]]

    def append(self, child: Name | Rval, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Name | Rval], label: Label | None = None) -> None: ...

    def extend_children(self, other: Lval) -> None: ...

    def child(self) -> tuple[Label | None, Name | Rval]: ...

    def insert(self, index: int, child: Name | Rval, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Name | Rval]: ...

    def replace_at(self, index: int, child: Name | Rval, label: Label | None = None) -> None: ...

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


Lval.Label.BASE = _ProtocolLabelMember("Lval.Label.BASE")
Lval.Label.INNER = _ProtocolLabelMember("Lval.Label.INNER")


class Rval(typing.Protocol):
    class Label:
        BASE: typing.ClassVar[object]
        INNER: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.RVAL] = NodeKind.RVAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Lval | Num]]

    def append(self, child: Lval | Num, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Lval | Num], label: Label | None = None) -> None: ...

    def extend_children(self, other: Rval) -> None: ...

    def child(self) -> tuple[Label | None, Lval | Num]: ...

    def insert(self, index: int, child: Lval | Num, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Lval | Num]: ...

    def replace_at(self, index: int, child: Lval | Num, label: Label | None = None) -> None: ...

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


Rval.Label.BASE = _ProtocolLabelMember("Rval.Label.BASE")
Rval.Label.INNER = _ProtocolLabelMember("Rval.Label.INNER")


class Arrow(typing.Protocol):
    class Label:
        TARGET: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ARROW] = NodeKind.ARROW
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Name]]

    def append(self, child: Name, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Name], label: Label | None = None) -> None: ...

    def extend_children(self, other: Arrow) -> None: ...

    def child(self) -> tuple[Label | None, Name]: ...

    def insert(self, index: int, child: Name, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Name]: ...

    def replace_at(self, index: int, child: Name, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_target(self, child: Name) -> None: ...

    def extend_target(self, children: typing.Iterable[Name]) -> None: ...

    def children_target(self) -> typing.Iterator[Name]: ...

    def child_target(self) -> Name: ...

    def maybe_target(self) -> Name | None: ...


Arrow.Label.TARGET = _ProtocolLabelMember("Arrow.Label.TARGET")


class LatinWord(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LATINWORD] = NodeKind.LATINWORD
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: LatinWord) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


LatinWord.Label.VALUE = _ProtocolLabelMember("LatinWord.Label.VALUE")


class Tagged(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TAGGED] = NodeKind.TAGGED
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Tagged) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


Tagged.Label.VALUE = _ProtocolLabelMember("Tagged.Label.VALUE")


class Val(typing.Protocol):
    class Label:
        ITEM: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.VAL] = NodeKind.VAL
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(
        self, child: Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def extend(
        self,
        children: typing.Iterable[Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: Label | None = None,
    ) -> None: ...

    def extend_children(self, other: Val) -> None: ...

    def child(self) -> tuple[Label | None, Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_item(self, child: Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_item(
        self, children: typing.Iterable[Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol]
    ) -> None: ...

    def children_item(self) -> typing.Iterator[Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_item(self) -> Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_item(self) -> Name | Num | fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


Val.Label.ITEM = _ProtocolLabelMember("Val.Label.ITEM")


class LeadingWs(typing.Protocol):
    class Label:
        NUM: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LEADINGWS] = NodeKind.LEADINGWS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Num | Trivia]]

    def append(self, child: Num | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Num | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: LeadingWs) -> None: ...

    def child(self) -> tuple[Label | None, Num | Trivia]: ...

    def insert(self, index: int, child: Num | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Num | Trivia]: ...

    def replace_at(self, index: int, child: Num | Trivia, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_num(self, child: Num) -> None: ...

    def extend_num(self, children: typing.Iterable[Num]) -> None: ...

    def children_num(self) -> typing.Iterator[Num]: ...

    def child_num(self) -> Num: ...

    def maybe_num(self) -> Num | None: ...


LeadingWs.Label.NUM = _ProtocolLabelMember("LeadingWs.Label.NUM")


class Grouped(typing.Protocol):
    class Label:
        LEFT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.GROUPED] = NodeKind.GROUPED
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Name | Num | Trivia]]

    def append(self, child: Name | Num | Trivia, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Name | Num | Trivia], label: Label | None = None) -> None: ...

    def extend_children(self, other: Grouped) -> None: ...

    def child(self) -> tuple[Label | None, Name | Num | Trivia]: ...

    def insert(self, index: int, child: Name | Num | Trivia, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Name | Num | Trivia]: ...

    def replace_at(self, index: int, child: Name | Num | Trivia, label: Label | None = None) -> None: ...

    def clear(self) -> None: ...

    def append_left(self, child: Name | Num) -> None: ...

    def extend_left(self, children: typing.Iterable[Name | Num]) -> None: ...

    def children_left(self) -> typing.Iterator[Name | Num]: ...

    def child_left(self) -> Name | Num: ...

    def maybe_left(self) -> Name | Num | None: ...


Grouped.Label.LEFT = _ProtocolLabelMember("Grouped.Label.LEFT")


class RecViaSub(typing.Protocol):
    class Label:
        INNER: typing.ClassVar[object]
        SUFFIX: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.RECVIASUB] = NodeKind.RECVIASUB
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Atom | Name | RecViaSub]]

    def append(self, child: Atom | Name | RecViaSub, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Atom | Name | RecViaSub], label: Label | None = None) -> None: ...

    def extend_children(self, other: RecViaSub) -> None: ...

    def child(self) -> tuple[Label | None, Atom | Name | RecViaSub]: ...

    def insert(self, index: int, child: Atom | Name | RecViaSub, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Atom | Name | RecViaSub]: ...

    def replace_at(self, index: int, child: Atom | Name | RecViaSub, label: Label | None = None) -> None: ...

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


RecViaSub.Label.INNER = _ProtocolLabelMember("RecViaSub.Label.INNER")
RecViaSub.Label.SUFFIX = _ProtocolLabelMember("RecViaSub.Label.SUFFIX")


class Nest(typing.Protocol):
    class Label:
        INNER: typing.ClassVar[object]
        LEAF: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.NEST] = NodeKind.NEST
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Nest | Num]]

    def append(self, child: Nest | Num, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Nest | Num], label: Label | None = None) -> None: ...

    def extend_children(self, other: Nest) -> None: ...

    def child(self) -> tuple[Label | None, Nest | Num]: ...

    def insert(self, index: int, child: Nest | Num, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Nest | Num]: ...

    def replace_at(self, index: int, child: Nest | Num, label: Label | None = None) -> None: ...

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


Nest.Label.INNER = _ProtocolLabelMember("Nest.Label.INNER")
Nest.Label.LEAF = _ProtocolLabelMember("Nest.Label.LEAF")


class NestSum(typing.Protocol):
    class Label:
        FIRST: typing.ClassVar[object]
        LHS: typing.ClassVar[object]
        RHS: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.NESTSUM] = NodeKind.NESTSUM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, Nest | NestSum]]

    def append(self, child: Nest | NestSum, label: Label | None = None) -> None: ...

    def extend(self, children: typing.Iterable[Nest | NestSum], label: Label | None = None) -> None: ...

    def extend_children(self, other: NestSum) -> None: ...

    def child(self) -> tuple[Label | None, Nest | NestSum]: ...

    def insert(self, index: int, child: Nest | NestSum, label: Label | None = None) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, Nest | NestSum]: ...

    def replace_at(self, index: int, child: Nest | NestSum, label: Label | None = None) -> None: ...

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


NestSum.Label.FIRST = _ProtocolLabelMember("NestSum.Label.FIRST")
NestSum.Label.LHS = _ProtocolLabelMember("NestSum.Label.LHS")
NestSum.Label.RHS = _ProtocolLabelMember("NestSum.Label.RHS")


class DigitSeq(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.DIGITSEQ] = NodeKind.DIGITSEQ
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: DigitSeq) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


DigitSeq.Label.VALUE = _ProtocolLabelMember("DigitSeq.Label.VALUE")


class WordSeq(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.WORDSEQ] = NodeKind.WORDSEQ
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: WordSeq) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


WordSeq.Label.VALUE = _ProtocolLabelMember("WordSeq.Label.VALUE")


class WsSeq(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.WSSEQ] = NodeKind.WSSEQ
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: WsSeq) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


WsSeq.Label.VALUE = _ProtocolLabelMember("WsSeq.Label.VALUE")


class ThreeToFiveDigits(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.THREETOFIVEDIGITS] = NodeKind.THREETOFIVEDIGITS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: ThreeToFiveDigits) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


ThreeToFiveDigits.Label.VALUE = _ProtocolLabelMember("ThreeToFiveDigits.Label.VALUE")


class ExactlyTwoDigits(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.EXACTLYTWODIGITS] = NodeKind.EXACTLYTWODIGITS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: ExactlyTwoDigits) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


ExactlyTwoDigits.Label.VALUE = _ProtocolLabelMember("ExactlyTwoDigits.Label.VALUE")


class EscapedMetas(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ESCAPEDMETAS] = NodeKind.ESCAPEDMETAS
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: EscapedMetas) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


EscapedMetas.Label.VALUE = _ProtocolLabelMember("EscapedMetas.Label.VALUE")


class LatinRange(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.LATINRANGE] = NodeKind.LATINRANGE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: LatinRange) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


LatinRange.Label.VALUE = _ProtocolLabelMember("LatinRange.Label.VALUE")


class NcGroupAlt(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.NCGROUPALT] = NodeKind.NCGROUPALT
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: NcGroupAlt) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


NcGroupAlt.Label.VALUE = _ProtocolLabelMember("NcGroupAlt.Label.VALUE")


class CaseInsensitive(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.CASEINSENSITIVE] = NodeKind.CASEINSENSITIVE
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: CaseInsensitive) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


CaseInsensitive.Label.VALUE = _ProtocolLabelMember("CaseInsensitive.Label.VALUE")


class AnchoredWord(typing.Protocol):
    class Label:
        VALUE: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.ANCHOREDWORD] = NodeKind.ANCHOREDWORD
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: AnchoredWord) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


AnchoredWord.Label.VALUE = _ProtocolLabelMember("AnchoredWord.Label.VALUE")


class Trivia(typing.Protocol):
    class Label:
        CONTENT: typing.ClassVar[object]

    kind: typing.Literal[NodeKind.TRIVIA] = NodeKind.TRIVIA
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol
    children: list[tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]]

    def append(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None) -> None: ...

    def extend(
        self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol], label: Label | None = None
    ) -> None: ...

    def extend_children(self, other: Trivia) -> None: ...

    def child(self) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def insert(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def remove_at(self, index: int) -> tuple[Label | None, fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def replace_at(
        self, index: int, child: fltk.fegen.pyrt.span_protocol.SpanProtocol, label: Label | None = None
    ) -> None: ...

    def clear(self) -> None: ...

    def append_content(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None: ...

    def extend_content(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None: ...

    def children_content(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]: ...

    def child_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol: ...

    def maybe_content(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None: ...


Trivia.Label.CONTENT = _ProtocolLabelMember("Trivia.Label.CONTENT")


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
    def Trivia(self) -> type[Trivia]: ...
