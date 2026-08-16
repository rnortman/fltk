from __future__ import annotations

import dataclasses
import enum
import operator
import sys
import types
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


def _type_name_for_error(obj: object) -> str:
    t = type(obj)
    return f"{t.__module__}.{t.__qualname__}"


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Expr.Label.PLUS": Label.PLUS, "Expr.Label.TERM": Label.TERM})
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
        checked_label = (
            label
            if label is None or isinstance(label, Expr.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Term | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Expr.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Expr) -> None:
        if not isinstance(other, Expr):
            msg = f"Expr: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Term | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, Term | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Expr: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Expr.Label | None:
        if label is None or isinstance(label, Expr.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Expr._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Expr"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Term | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Expr.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Expr.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Expr.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Expr.Label) -> list[Term | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_plus(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Expr.Label.PLUS, self._check_child_type_for_mutators(child)))

    def extend_plus(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Expr.Label.PLUS, self._check_child_type_for_mutators(child)) for child in children])

    def children_plus(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Expr.Label.PLUS))
        )

    def child_plus(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Expr.Label.PLUS)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one plus child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_plus(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Expr.Label.PLUS)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one plus child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_term(self, child: _cstp.Term) -> None:
        self.children.append((Expr.Label.TERM, self._check_child_type_for_mutators(child)))

    def extend_term(self, children: typing.Iterable[_cstp.Term]) -> None:
        self.children.extend([(Expr.Label.TERM, self._check_child_type_for_mutators(child)) for child in children])

    def children_term(self) -> typing.Iterator[Term]:
        return iter(typing.cast("list[Term]", self._children_snapshot(Expr.Label.TERM)))

    def child_term(self) -> Term:
        children = typing.cast("list[Term]", self._children_snapshot(Expr.Label.TERM))
        if (n := len(children)) != 1:
            msg = f"Expected one term child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_term(self) -> Term | None:
        children = typing.cast("list[Term]", self._children_snapshot(Expr.Label.TERM))
        if (n := len(children)) > 1:
            msg = f"Expected at most one term child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def plus(self) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Expr.Label.PLUS))

    def term(self) -> list[Term]:
        return typing.cast("list[Term]", self._children_snapshot(Expr.Label.TERM))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Term.Label.FACTOR": Label.FACTOR, "Term.Label.MULT": Label.MULT}
    )
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
        checked_label = (
            label
            if label is None or isinstance(label, Term.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Factor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Term.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Term) -> None:
        if not isinstance(other, Term):
            msg = f"Term: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(
        self, child: _cstp.Factor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol
    ) -> Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol:
        if isinstance(child, Factor | Trivia | fltk.fegen.pyrt.terminalsrc.Span):
            return child
        _ns = _get_native_span_type()
        if _ns is not None and isinstance(child, _ns):
            native_span: typing.Any = child
            return native_span
        msg = f"Term: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Term.Label | None:
        if label is None or isinstance(label, Term.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Term._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Term"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Factor | _cstp.Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Term.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Term.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Term.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(
        self, label: Term.Label
    ) -> list[Factor | Trivia | fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_factor(self, child: _cstp.Factor) -> None:
        self.children.append((Term.Label.FACTOR, self._check_child_type_for_mutators(child)))

    def extend_factor(self, children: typing.Iterable[_cstp.Factor]) -> None:
        self.children.extend([(Term.Label.FACTOR, self._check_child_type_for_mutators(child)) for child in children])

    def children_factor(self) -> typing.Iterator[Factor]:
        return iter(typing.cast("list[Factor]", self._children_snapshot(Term.Label.FACTOR)))

    def child_factor(self) -> Factor:
        children = typing.cast("list[Factor]", self._children_snapshot(Term.Label.FACTOR))
        if (n := len(children)) != 1:
            msg = f"Expected one factor child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_factor(self) -> Factor | None:
        children = typing.cast("list[Factor]", self._children_snapshot(Term.Label.FACTOR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one factor child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_mult(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Term.Label.MULT, self._check_child_type_for_mutators(child)))

    def extend_mult(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Term.Label.MULT, self._check_child_type_for_mutators(child)) for child in children])

    def children_mult(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(
            typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Term.Label.MULT))
        )

    def child_mult(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Term.Label.MULT)
        )
        if (n := len(children)) != 1:
            msg = f"Expected one mult child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_mult(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = typing.cast(
            "list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Term.Label.MULT)
        )
        if (n := len(children)) > 1:
            msg = f"Expected at most one mult child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def factor(self) -> list[Factor]:
        return typing.cast("list[Factor]", self._children_snapshot(Term.Label.FACTOR))

    def mult(self) -> list[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return typing.cast("list[fltk.fegen.pyrt.span_protocol.SpanProtocol]", self._children_snapshot(Term.Label.MULT))


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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType(
        {"Factor.Label.EXPR": Label.EXPR, "Factor.Label.NUMBER": Label.NUMBER}
    )
    kind: typing.Literal[NodeKind.FACTOR] = NodeKind.FACTOR
    span: fltk.fegen.pyrt.span_protocol.SpanProtocol = fltk.fegen.pyrt.terminalsrc.UnknownSpan
    children: list[tuple[Label | None, Expr | Number | Trivia]] = dataclasses.field(default_factory=list)

    def append(
        self,
        child: _cstp.Expr | _cstp.Number | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Factor.Label)
            else self._check_label_type_for_mutators(label, "append")
        )
        checked_child = self._check_child_type_for_mutators(child)
        self.children.append((checked_label, checked_child))

    def extend(
        self,
        children: typing.Iterable[_cstp.Expr | _cstp.Number | _cstp.Trivia],
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Factor.Label)
            else self._check_label_type_for_mutators(label, "extend")
        )
        self.children.extend([(checked_label, self._check_child_type_for_mutators(child)) for child in children])

    def extend_children(self, other: _cstp.Factor) -> None:
        if not isinstance(other, Factor):
            msg = f"Factor: unsupported child type {_type_name_for_error(other)}"
            raise TypeError(msg)
        self.children.extend(other.children)

    def child(self) -> tuple[Label | None, Expr | Number | Trivia]:
        if (n := len(self.children)) != 1:
            msg = f"Expected one child but have {n}"
            raise ValueError(msg)
        return self.children[0]

    def _check_child_type_for_mutators(self, child: _cstp.Expr | _cstp.Number | _cstp.Trivia) -> Expr | Number | Trivia:
        if isinstance(child, Expr | Number | Trivia):
            return child
        msg = f"Factor: unsupported child type {_type_name_for_error(child)}"
        raise TypeError(msg)

    def _check_label_type_for_mutators(
        self, label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None, method: str
    ) -> Factor.Label | None:
        if label is None or isinstance(label, Factor.Label):
            return label
        _canonical = getattr(label, "_fltk_canonical_name", None)
        if isinstance(_canonical, str):
            _resolved = Factor._LABELS_BY_CANONICAL_NAME.get(_canonical)
            if _resolved is not None:
                return _resolved
        _cn = "Factor"
        msg = f"{_cn}.{method}: label argument is not a {_cn}_Label; got {type(label).__name__}"
        raise TypeError(msg)

    def insert(
        self,
        index: int,
        child: _cstp.Expr | _cstp.Number | _cstp.Trivia,
        label: fltk.fegen.pyrt.label_protocol.LabelProtocol | None = None,
    ) -> None:
        checked_label = (
            label
            if label is None or isinstance(label, Factor.Label)
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
        checked_label = (
            label
            if label is None or isinstance(label, Factor.Label)
            else self._check_label_type_for_mutators(label, "replace_at")
        )
        checked_child = self._check_child_type_for_mutators(child)
        idx = operator.index(index)
        n = len(self.children)
        norm = idx + n if idx < 0 else idx
        if norm < 0 or norm >= n:
            msg = f"Factor.replace_at: index {index} out of range ({n} children)"
            raise IndexError(msg)
        self.children[norm] = (checked_label, checked_child)

    def clear(self) -> None:
        self.children.clear()

    def _children_snapshot(self, label: Factor.Label) -> list[Expr | Number | Trivia]:
        return [child for (lbl, child) in self.children if lbl == label]

    def append_expr(self, child: _cstp.Expr) -> None:
        self.children.append((Factor.Label.EXPR, self._check_child_type_for_mutators(child)))

    def extend_expr(self, children: typing.Iterable[_cstp.Expr]) -> None:
        self.children.extend([(Factor.Label.EXPR, self._check_child_type_for_mutators(child)) for child in children])

    def children_expr(self) -> typing.Iterator[Expr]:
        return iter(typing.cast("list[Expr]", self._children_snapshot(Factor.Label.EXPR)))

    def child_expr(self) -> Expr:
        children = typing.cast("list[Expr]", self._children_snapshot(Factor.Label.EXPR))
        if (n := len(children)) != 1:
            msg = f"Expected one expr child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_expr(self) -> Expr | None:
        children = typing.cast("list[Expr]", self._children_snapshot(Factor.Label.EXPR))
        if (n := len(children)) > 1:
            msg = f"Expected at most one expr child but have {n}"
            raise ValueError(msg)
        return children[0] if children else None

    def append_number(self, child: _cstp.Number) -> None:
        self.children.append((Factor.Label.NUMBER, self._check_child_type_for_mutators(child)))

    def extend_number(self, children: typing.Iterable[_cstp.Number]) -> None:
        self.children.extend([(Factor.Label.NUMBER, self._check_child_type_for_mutators(child)) for child in children])

    def children_number(self) -> typing.Iterator[Number]:
        return iter(typing.cast("list[Number]", self._children_snapshot(Factor.Label.NUMBER)))

    def child_number(self) -> Number:
        children = typing.cast("list[Number]", self._children_snapshot(Factor.Label.NUMBER))
        if (n := len(children)) != 1:
            msg = f"Expected one number child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_number(self) -> Number | None:
        children = typing.cast("list[Number]", self._children_snapshot(Factor.Label.NUMBER))
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

    _LABELS_BY_CANONICAL_NAME = types.MappingProxyType({"Number.Label.VALUE": Label.VALUE})
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

    def append_value(self, child: fltk.fegen.pyrt.span_protocol.SpanProtocol) -> None:
        self.children.append((Number.Label.VALUE, self._check_child_type_for_mutators(child)))

    def extend_value(self, children: typing.Iterable[fltk.fegen.pyrt.span_protocol.SpanProtocol]) -> None:
        self.children.extend([(Number.Label.VALUE, self._check_child_type_for_mutators(child)) for child in children])

    def children_value(self) -> typing.Iterator[fltk.fegen.pyrt.span_protocol.SpanProtocol]:
        return iter(self._children_snapshot(Number.Label.VALUE))

    def child_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol:
        children = self._children_snapshot(Number.Label.VALUE)
        if (n := len(children)) != 1:
            msg = f"Expected one value child but have {n}"
            raise ValueError(msg)
        return children[0]

    def maybe_value(self) -> fltk.fegen.pyrt.span_protocol.SpanProtocol | None:
        children = self._children_snapshot(Number.Label.VALUE)
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
