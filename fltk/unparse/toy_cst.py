from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import typing

import fltk.fegen.pyrt.terminalsrc
from fltk.unparse.toy_cst_protocol import NodeKind

if typing.TYPE_CHECKING:
    import fltk.fegen.pyrt.label_protocol
    import fltk.fegen.pyrt.span_protocol
    import fltk.unparse.toy_cst_protocol as _cstp


def _get_native_span_type():
    m = sys.modules.get("fltk._native")
    return m.Span if m is not None else None


@dataclasses.dataclass
class Expr:
    class Label(enum.Enum):
        PLUS = enum.auto()
        TERM = enum.auto()
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

    kind: typing.Literal[NodeKind.EXPR] = NodeKind.EXPR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = dataclasses.field(
        default_factory=list
    )

    def append(
        self,
        child: _cstp.Term | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Term | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Expr) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.Term | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
        _allowed = Expr._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (Term, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            Expr._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Expr._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Expr._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Expr: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Expr.Label)):
            _cn = "Expr"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Term | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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

    def remove_at(self, index: int) -> tuple[Label | None, Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Expr.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Term | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Expr.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_plus(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Expr.Label.PLUS, child))

    def extend_plus(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Expr.Label.PLUS, child) for child in children)

    def children_plus(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Expr.Label.PLUS
        )

    def child_plus(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_plus())
        if (n := len(children)) != 1:
            msg = f"Expected one plus child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_plus(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_plus())
        if (n := len(children)) > 1:
            msg = f"Expected at most one plus child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_term(self, child: _cstp.Term) -> None:
        entry: typing.Any = (Expr.Label.TERM, child)
        self.children.append(entry)

    def extend_term(self, children: typing.Iterable[_cstp.Term]) -> None:
        entries: typing.Any = ((Expr.Label.TERM, child) for child in children)
        self.children.extend(entries)

    def children_term(self) -> typing.Iterator[Term]:
        return (typing.cast("Term", child) for (label, child) in self.children if label == Expr.Label.TERM)

    def child_term(self) -> Term:
        children = list(self.children_term())
        if (n := len(children)) != 1:
            msg = f"Expected one term child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_term(self) -> Term | None:
        children = list(self.children_term())
        if (n := len(children)) > 1:
            msg = f"Expected at most one term child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def plus(self) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return list(self.children_plus())

    def term(self) -> list[Term]:
        return list(self.children_term())


Expr.Label.PLUS._fltk_canonical_name = "Expr.Label.PLUS"
Expr.Label.TERM._fltk_canonical_name = "Expr.Label.TERM"


@dataclasses.dataclass
class Term:
    class Label(enum.Enum):
        FACTOR = enum.auto()
        MULT = enum.auto()
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

    kind: typing.Literal[NodeKind.TERM] = NodeKind.TERM
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]] = (
        dataclasses.field(default_factory=list)
    )

    def append(
        self,
        child: _cstp.Factor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Factor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Term) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    _MUTATOR_ALLOWED_CHILD_TYPES = None

    def _check_child_type_for_mutators(
        self, child: _cstp.Factor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> None:
        _allowed = Term._MUTATOR_ALLOWED_CHILD_TYPES
        if _allowed is None:
            _allowed = (Factor, Trivia, fltk.fegen.pyrt.terminalsrc.Span)
            Term._MUTATOR_ALLOWED_CHILD_TYPES = _allowed
        _ns = _get_native_span_type()
        if _ns is not None and _ns not in _allowed:
            Term._MUTATOR_ALLOWED_CHILD_TYPES = (*_allowed, _ns)
            _allowed = Term._MUTATOR_ALLOWED_CHILD_TYPES
        if not isinstance(child, _allowed):
            msg = f"Term: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Term.Label)):
            _cn = "Term"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Factor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
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
    ) -> tuple[Label | None, Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Term.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Factor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Term.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_factor(self, child: _cstp.Factor) -> None:
        entry: typing.Any = (Term.Label.FACTOR, child)
        self.children.append(entry)

    def extend_factor(self, children: typing.Iterable[_cstp.Factor]) -> None:
        entries: typing.Any = ((Term.Label.FACTOR, child) for child in children)
        self.children.extend(entries)

    def children_factor(self) -> typing.Iterator[Factor]:
        return (typing.cast("Factor", child) for (label, child) in self.children if label == Term.Label.FACTOR)

    def child_factor(self) -> Factor:
        children = list(self.children_factor())
        if (n := len(children)) != 1:
            msg = f"Expected one factor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_factor(self) -> Factor | None:
        children = list(self.children_factor())
        if (n := len(children)) > 1:
            msg = f"Expected at most one factor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_mult(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Term.Label.MULT, child))

    def extend_mult(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Term.Label.MULT, child) for child in children)

    def children_mult(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (
            typing.cast("fltk.fegen.pyrt.span_protocol.SpanProtocol", child)
            for (label, child) in self.children
            if label == Term.Label.MULT
        )

    def child_mult(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = list(self.children_mult())
        if (n := len(children)) != 1:
            msg = f"Expected one mult child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_mult(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = list(self.children_mult())
        if (n := len(children)) > 1:
            msg = f"Expected at most one mult child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def factor(self) -> list[Factor]:
        return list(self.children_factor())

    def mult(self) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return list(self.children_mult())


Term.Label.FACTOR._fltk_canonical_name = "Term.Label.FACTOR"
Term.Label.MULT._fltk_canonical_name = "Term.Label.MULT"


@dataclasses.dataclass
class Factor:
    class Label(enum.Enum):
        EXPR = enum.auto()
        NUMBER = enum.auto()
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

    kind: typing.Literal[NodeKind.FACTOR] = NodeKind.FACTOR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Expr | Number | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Expr | _cstp.Number | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[_cstp.Expr | _cstp.Number | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Factor) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

    def child(self) -> tuple[Label | None, Expr | Number | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Expr | _cstp.Number | _cstp.Trivia) -> None:
        if not isinstance(child, Expr | Number | Trivia):
            msg = f"Factor: unsupported child type {type(child).__name__}"
            raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Factor.Label)):
            _cn = "Factor"
            msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
            raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Expr | _cstp.Number | _cstp.Trivia,
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

    def remove_at(self, index: int) -> tuple[Label | None, Expr | Number | Trivia]:
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Factor.remove_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        return self.children.pop(norm)

    def replace_at(
        self,
        index: int,
        child: _cstp.Expr | _cstp.Number | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        self._check_child_type_for_mutators(child)
        self._check_label_type_for_mutators(label, "replace_at")
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Factor.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_expr(self, child: _cstp.Expr) -> None:
        entry: typing.Any = (Factor.Label.EXPR, child)
        self.children.append(entry)

    def extend_expr(self, children: typing.Iterable[_cstp.Expr]) -> None:
        entries: typing.Any = ((Factor.Label.EXPR, child) for child in children)
        self.children.extend(entries)

    def children_expr(self) -> typing.Iterator[Expr]:
        return (typing.cast("Expr", child) for (label, child) in self.children if label == Factor.Label.EXPR)

    def child_expr(self) -> Expr:
        children = list(self.children_expr())
        if (n := len(children)) != 1:
            msg = f"Expected one expr child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_expr(self) -> Expr | None:
        children = list(self.children_expr())
        if (n := len(children)) > 1:
            msg = f"Expected at most one expr child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_number(self, child: _cstp.Number) -> None:
        entry: typing.Any = (Factor.Label.NUMBER, child)
        self.children.append(entry)

    def extend_number(self, children: typing.Iterable[_cstp.Number]) -> None:
        entries: typing.Any = ((Factor.Label.NUMBER, child) for child in children)
        self.children.extend(entries)

    def children_number(self) -> typing.Iterator[Number]:
        return (typing.cast("Number", child) for (label, child) in self.children if label == Factor.Label.NUMBER)

    def child_number(self) -> Number:
        children = list(self.children_number())
        if (n := len(children)) != 1:
            msg = f"Expected one number child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_number(self) -> Number | None:
        children = list(self.children_number())
        if (n := len(children)) > 1:
            msg = f"Expected at most one number child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def expr(self) -> Expr | None:
        return self.maybe_expr()

    def number(self) -> Number | None:
        return self.maybe_number()


Factor.Label.EXPR._fltk_canonical_name = "Factor.Label.EXPR"
Factor.Label.NUMBER._fltk_canonical_name = "Factor.Label.NUMBER"


@dataclasses.dataclass
class Number:
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
        entry: typing.Any = (label, child)
        self.children.append(entry)

    def extend(
        self,
        children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        entries: typing.Any = ((label, child) for child in children)
        self.children.extend(entries)

    def extend_children(self, other: _cstp.Number) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

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

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> None:
        if label is not None and (not isinstance(label, Number.Label)):
            _cn = "Number"
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
            msg = f"Number.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Number.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

    def clear(self) -> None:
        self.children.clear()

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Number.Label.VALUE, child))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend((Number.Label.VALUE, child) for child in children)

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return (child for (label, child) in self.children if label == Number.Label.VALUE)

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
            msg = "Number.value_text: child labelled 'value' is not a Span"
            raise TypeError(msg) from None

    def text(self) -> str:
        return self.span.text_or_raise()


Number.Label.VALUE._fltk_canonical_name = "Number.Label.VALUE"


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

    def extend_children(self, other: _cstp.Trivia) -> None:
        entries: typing.Any = other.children
        self.children.extend(entries)

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
            msg = f"Trivia.remove_at: index {index} out of range ({n} children)"
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
            msg = f"Trivia.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        entry: typing.Any = (label, child)
        self.children[norm] = entry

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
