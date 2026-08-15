"""Runtime support for generated AST modules.

A generated ``<base>_ast.py`` imports this module and nothing else from FLTK beyond its
CST module.  It carries the error type every converter raises, the child-bucketing and
arity helpers the converters call, the alternative signatures a sum's converter tests to
recover which alternative matched, the strict-format scalar parsers and canonical
renderers a ``type:`` coercion goes through, the fold and unfold of a ``fold_left:`` /
``fold_right:`` binary chain, and — for the reverse direction — the cursor that distributes
field values over an alternative's item positions plus the terminal validation and span
construction ``to_cst`` needs.
"""

from __future__ import annotations

import dataclasses
import math
import re
import struct
import typing
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Final

from fltk.fegen.pyrt import errors, terminalsrc
from fltk.fegen.pyrt.label_protocol import label_member_name

if typing.TYPE_CHECKING:
    import decimal
    import uuid

    from fltk.fegen.pyrt.label_protocol import LabelProtocol
    from fltk.fegen.pyrt.span_protocol import SpanProtocol


class _TextKind:
    """The child kind of a span child, standing beside the CST's ``NodeKind`` members."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "TEXT"


TEXT: Final = _TextKind()

UNBOUNDED: Final = math.inf
"""The upper bound of a label that can repeat without limit."""


class AstError(Exception):
    """A CST could not be converted to its AST form.

    ``span`` locates the failure; ``related`` carries secondary locations, such as the
    earlier element a duplicate collides with.
    """

    def __init__(
        self,
        message: str,
        span: SpanProtocol,
        related: Sequence[tuple[str, SpanProtocol]] = (),
    ) -> None:
        self.message = message
        self.span = span
        self.related = list(related)
        super().__init__(message)

    def __str__(self) -> str:
        position = self.span.line_col()
        if position is None:
            return self.message
        return f"{self.message} at line {position.line + 1}, column {position.col + 1}"


class CrossBackendEnumMixin:
    """Equality and hashing over a canonical member name, for a generated value enum.

    A pure-Python enum member and its PyO3 counterpart carry the same
    ``_fltk_canonical_name`` — a plain string assigned per member after class creation — so
    they compare equal and hash alike across backends.  Generated CST ``NodeKind`` and
    ``Label`` enums implement the same protocol.
    """

    _fltk_canonical_name: str

    def __eq__(self, other: object) -> bool:
        if other is self:
            return True
        if type(other) is type(self):
            return self._fltk_canonical_name == typing.cast("CrossBackendEnumMixin", other)._fltk_canonical_name
        canonical = getattr(other, "_fltk_canonical_name", None)
        if canonical is not None:
            return self._fltk_canonical_name == canonical
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._fltk_canonical_name)


def bucket_children(children: Iterable[tuple[LabelProtocol | None, Any]]) -> dict[str, list[Any]]:
    """Group a CST node's labeled children by label name, in source order.

    A key is the ``<MEMBER>`` component of the label's ``_fltk_canonical_name``
    (``"<Class>.Label.<MEMBER>"``), which is the same string a Python enum label carries as its
    member name.  That canonical name is the cross-backend identity contract every CST backend
    conforming to ``LabelProtocol`` implements — the Python enums, the PyO3 pyclasses, the
    protocol module's own sentinels — so any of them buckets here, and the keys are
    backend-independent.  A label carrying no ``_fltk_canonical_name`` is not from a conforming
    backend and raises ``AttributeError`` naming the attribute.

    Unlabeled children — trivia and ``$``-included literals — are skipped, so the result
    is the same whether or not the parser captured trivia.
    """
    buckets: dict[str, list[Any]] = {}
    for label, child in children:
        if label is None:
            continue
        buckets.setdefault(label_member_name(label._fltk_canonical_name), []).append(child)
    return buckets


def one(buckets: Mapping[str, Sequence[Any]], key: str, rule: str, label: str, span: SpanProtocol) -> Any:
    """The single child of a required label."""
    children = buckets.get(key, ())
    if len(children) != 1:
        msg = f"rule {rule!r}: expected exactly one {label!r} child, found {len(children)}"
        raise AstError(msg, span)
    return children[0]


def optional(buckets: Mapping[str, Sequence[Any]], key: str, rule: str, label: str, span: SpanProtocol) -> Any | None:
    """The child of an optional label, or ``None``."""
    children = buckets.get(key, ())
    if len(children) > 1:
        msg = f"rule {rule!r}: expected at most one {label!r} child, found {len(children)}"
        raise AstError(msg, span)
    return children[0] if children else None


def presence(buckets: Mapping[str, Sequence[Any]], key: str, rule: str, label: str, span: SpanProtocol) -> bool:
    """Whether an optional labeled literal is present."""
    children = buckets.get(key, ())
    if len(children) > 1:
        msg = f"rule {rule!r}: expected at most one {label!r} child, found {len(children)}"
        raise AstError(msg, span)
    return bool(children)


def unexpected_child(rule: str, label: str, span: SpanProtocol) -> AstError:
    """A child of a kind the label cannot hold.

    Reachable only from a hand-built or mutated CST: the parser puts a child of the
    grammar's own term under each label.
    """
    return AstError(f"rule {rule!r}: label {label!r} has a child of unexpected kind", span)


def node_child(child: Any, kind: Any, rule: str, label: str, span: SpanProtocol) -> Any:
    """One node child of the kind a label carries, or the wrong-kind error."""
    if child_kind(child) != kind:
        raise unexpected_child(rule, label, span)
    return child


def span_child(child: Any, rule: str, label: str, span: SpanProtocol) -> Any:
    """One span child, or the wrong-kind error when a node arrived instead."""
    if child_kind(child) is not TEXT:
        raise unexpected_child(rule, label, span)
    return child


def text(child: Any, rule: str, label: str, span: SpanProtocol) -> str:
    """The source text of a span child."""
    if child_kind(child) is not TEXT:
        raise unexpected_child(rule, label, span)
    value = child.text()
    if value is None:
        msg = f"rule {rule!r}: the {label!r} span carries no source text"
        raise AstError(msg, span)
    return value


def node_text(span: SpanProtocol, rule: str) -> str:
    """The source text a node's own span covers."""
    value = span.text()
    if value is None:
        msg = f"rule {rule!r}: node span carries no source text"
        raise AstError(msg, span)
    return value


def keyed(elements: Sequence[Any], key_field: str, rule: str) -> dict[Any, Any]:
    """Index a collection's elements by one of their own fields, in source order.

    A repeated key is an error carrying both locations, the way a hand-written resolver
    reports a redefinition: the offending element's span, and the earlier element's as
    ``related``.
    """
    result: dict[Any, Any] = {}
    for element in elements:
        key = getattr(element, key_field)
        previous = result.get(key)
        if previous is not None:
            msg = f"duplicate {rule} key {key!r}"
            raise AstError(msg, element.span, [("previously defined here", previous.span)])
        result[key] = element
    return result


def keyed_multi(elements: Sequence[Any], key_field: str) -> dict[Any, list[Any]]:
    """Group a collection's elements by one of their own fields, in source order.

    The accumulating half of :func:`keyed`, for ``key: <label> multi;``: elements sharing a key
    are collected under it rather than refused, and a key takes its place in the map where its
    first element occurred.
    """
    result: dict[Any, list[Any]] = {}
    for element in elements:
        result.setdefault(getattr(element, key_field), []).append(element)
    return result


def child_kind(child: Any) -> Any:
    """The child's ``NodeKind``, or ``TEXT`` for a span child.

    Node children own a ``children`` list; span children do not.
    """
    if hasattr(child, "children"):
        return child.kind
    return TEXT


def child_span(child: Any) -> Any:
    """The span one CST child covers: a node child's own span, or the span child itself."""
    if hasattr(child, "children"):
        return child.span
    return child


@dataclasses.dataclass(frozen=True)
class LabelSignature:
    """How often one label occurs in an alternative, and what its children can be."""

    minimum: int
    maximum: float
    kinds: frozenset[Any]


@dataclasses.dataclass(frozen=True)
class AltSignature:
    """The labeled-children shape of one alternative of a sum rule."""

    labels: Mapping[str, LabelSignature]

    def accepts(self, buckets: Mapping[str, Sequence[Any]]) -> bool:
        """Whether bucketed children could have come from this alternative."""
        for key, children in buckets.items():
            signature = self.labels.get(key)
            if signature is None or not signature.minimum <= len(children) <= signature.maximum:
                return False
            if any(child_kind(child) not in signature.kinds for child in children):
                return False
        return all(signature.minimum == 0 for key, signature in self.labels.items() if key not in buckets)


# --- Scalar coercions -------------------------------------------------------------------

# Format gates every coercion passes before the native parse runs.  The native parses are
# laxer than these — Python's ``float`` takes ``inf``/``nan``, ``uuid.UUID`` takes braced
# and URN spellings, ``int`` takes underscores — and Rust's are laxer in different places,
# so a shared gate is what makes the two backends accept and reject the same lexemes.
_INTEGER_FORMAT: Final = re.compile(r"[+-]?[0-9]+")
_FLOAT_FORMAT: Final = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_DECIMAL_FORMAT: Final = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
_UUID_FORMAT: Final = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
)

_FLOAT_PACK: Final[Mapping[int, str]] = {32: "<f", 64: "<d"}


def _coercion_error(text: Any, expected: str, rule: str, span: SpanProtocol) -> AstError:
    return AstError(f"rule {rule!r}: {text!r} is not {expected}", span)


def _gated(text: Any, gate: re.Pattern[str], expected: str, rule: str, span: SpanProtocol) -> str:
    if not isinstance(text, str) or gate.fullmatch(text) is None:
        raise _coercion_error(text, expected, rule, span)
    return text


def _int_bounds(bits: int, *, signed: bool) -> tuple[int, int]:
    if signed:
        return -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
    return 0, 2**bits - 1


def _rounded(value: float, bits: int) -> float:
    """``value`` as the named width holds it; an infinity when the magnitude overflows it."""
    try:
        return typing.cast("float", struct.unpack(_FLOAT_PACK[bits], struct.pack(_FLOAT_PACK[bits], value))[0])
    except OverflowError:
        return math.inf


def narrowed(value: Any, bits: int) -> Any:
    """``value`` rounded through a narrower float width, for a generated ``__post_init__``.

    A field declared ``f32`` is an ``f32`` on the Rust backend and a Python ``float`` here, so
    the value a hand-built node holds is rounded through 32 bits at construction: that is what
    the Rust field would hold, so the two backends compare and render alike, and the round-trip
    law holds without a normalising pass through ``unparse``.  A list's elements are rounded too;
    a map's are not reached, because a keyed collection's elements are nodes of the rule that
    declared the key and round their own fields.  Anything that is not a float — a value of the
    wrong type, a magnitude the width cannot hold at all — is left alone for the renderer to
    name.
    """
    if isinstance(value, float):
        rounded = _rounded(value, bits)
        return value if math.isinf(rounded) and not math.isinf(value) else rounded
    if isinstance(value, list):
        return [narrowed(element, bits) for element in value]
    return value


def parse_int(text: Any, bits: int, rule: str, span: SpanProtocol, *, signed: bool) -> int:
    """Coerce a terminal's text to an integer of the named width."""
    width = f"{'i' if signed else 'u'}{bits}"
    value = int(_gated(text, _INTEGER_FORMAT, f"a valid {width}", rule, span))
    low, high = _int_bounds(bits, signed=signed)
    if not low <= value <= high:
        raise _coercion_error(text, f"in range for {width} ({low} to {high})", rule, span)
    return value


def parse_float(text: Any, bits: int, rule: str, span: SpanProtocol) -> float:
    """Coerce a terminal's text to a float, rounded to the named width.

    ``f32`` values are rounded through the 32-bit representation so that the Python value is
    the one the Rust backend would hold.  A magnitude that overflows the width is out of
    range rather than an infinity: the gate rejects the ``inf`` lexeme, so accepting one by
    overflow would make a value that has no spelling to render back to.
    """
    value = float(_gated(text, _FLOAT_FORMAT, f"a valid f{bits}", rule, span))
    rounded = _rounded(value, bits)
    if math.isinf(rounded):
        raise _coercion_error(text, f"in range for f{bits}", rule, span)
    return rounded


def parse_uuid(text: Any, rule: str, span: SpanProtocol) -> uuid.UUID:
    """Coerce a terminal's text to a UUID, in the canonical 8-4-4-4-12 spelling only."""
    import uuid as uuid_module  # noqa: PLC0415

    return uuid_module.UUID(_gated(text, _UUID_FORMAT, "a canonical 8-4-4-4-12 UUID", rule, span))


_DECIMAL_MAX_SCALE: Final = 28
"""The most fractional digits a ``decimal`` coercion holds."""

_DECIMAL_MAX_MANTISSA: Final = 2**96
"""One past the largest mantissa a ``decimal`` coercion holds."""

_DECIMAL_DOMAIN: Final = "a decimal of at most 28 fractional digits and 96 bits of mantissa"


def parse_decimal(text: Any, rule: str, span: SpanProtocol) -> decimal.Decimal:
    """Coerce a terminal's text to a decimal; exponent forms are not accepted.

    Python's decimal type is unbounded and the Rust backend's is a 96-bit mantissa scaled by
    at most ``10**28``, so a value past that domain is refused here rather than accepted: a
    ``type: decimal`` lexeme one backend takes must not be one the other rejects, and the
    alternative — rounding to fit — would render back as different text than it was read from.
    """
    import decimal as decimal_module  # noqa: PLC0415

    value = decimal_module.Decimal(_gated(text, _DECIMAL_FORMAT, "a plain decimal number", rule, span))
    if _outside_decimal_domain(value):
        raise _coercion_error(text, _DECIMAL_DOMAIN, rule, span)
    return value


def _outside_decimal_domain(value: Any) -> bool:
    """Whether a decimal is wider than the domain both backends share."""
    _, digits, exponent = value.as_tuple()
    mantissa = int("".join(str(digit) for digit in digits))
    return -int(exponent) > _DECIMAL_MAX_SCALE or mantissa >= _DECIMAL_MAX_MANTISSA


def parse_custom(parse: Callable[[str], Any], text: Any, rule: str, span: SpanProtocol) -> Any:
    """Coerce a terminal's text through a ``type: custom(...)`` parse function.

    The contract is a ``ValueError`` on bad input, which becomes an ``AstError`` carrying the
    node's span — the function itself has no way to know where its text came from.
    """
    if not isinstance(text, str):
        raise _coercion_error(text, "text", rule, span)
    try:
        return parse(text)
    except ValueError as error:
        msg = f"rule {rule!r}: {error}"
        raise AstError(msg, span) from error


def render_int(value: Any, bits: int, rule: str, span: SpanProtocol, *, signed: bool) -> str:
    """An integer coercion's canonical text: the native decimal spelling.

    The width bounds the parse half enforces are enforced here too.  The Rust field is the
    named integer type and cannot hold anything else, so a Python value outside the width is
    one no parse of the rendered text could return — text that re-parses to a different value,
    or to an error, breaks the round-trip law rather than reporting anything.
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise _coercion_error(value, "an integer", rule, span)
    low, high = _int_bounds(bits, signed=signed)
    if not low <= value <= high:
        width = f"{'i' if signed else 'u'}{bits}"
        raise _coercion_error(value, f"in range for {width} ({low} to {high})", rule, span)
    return str(value)


def render_float(value: Any, bits: int, rule: str, span: SpanProtocol) -> str:
    """A float coercion's canonical text: the shortest spelling that round-trips the width.

    Both backends must render a given value to the same bytes, so the canonical form is the
    shortest decimal string that reads back as the same value *at the declared width*, spelled
    with CPython ``repr`` conventions.  For ``f64`` that is ``repr`` itself; for ``f32`` it is
    what keeps a parsed ``3.14`` rendering as ``3.14`` rather than in seventeen digits.  A
    value the width cannot hold exactly is rounded through it silently, as Rust rounds
    ``let x: f32 = 3.14;``.  Infinities and NaN have no grammar spelling, and neither has a
    magnitude too large for the width.
    """
    if not isinstance(value, float) or not math.isfinite(value):
        raise _coercion_error(value, "a finite float", rule, span)
    rounded = _rounded(value, bits)
    if math.isinf(rounded):
        raise _coercion_error(value, f"in range for f{bits}", rule, span)
    return repr(_shortest_float(rounded, bits))


# How many significant digits always suffice to round-trip a width, for the widths that need
# the search at all: ``repr`` is already the shortest f64 spelling, so f64 has no entry.
_SHORTEST_DIGITS: Final[Mapping[int, int]] = {32: 9}


def _shortest_float(value: float, bits: int) -> float:
    """The float whose ``repr`` is the shortest decimal that round-trips ``value`` at ``bits``.

    ``repr`` of the returned float is a spelling that reads back as ``value`` at the declared
    width: it parses to exactly this float, which rounds to ``value``.
    """
    digits = _SHORTEST_DIGITS.get(bits)
    if digits is None:
        return value
    for precision in range(1, digits + 1):
        candidate = float(f"{value:.{precision}g}")
        if _rounded(candidate, bits) == value:
            return candidate
    return value


def render_decimal(value: Any, rule: str, span: SpanProtocol) -> str:
    """A decimal coercion's canonical text: plain notation, keeping the value's scale.

    Python's decimal type is unbounded, so a hand-built value wider than the domain the parse
    half shares with the Rust backend is refused here rather than rendered: its text would be
    something no parse of it could read back, on either backend.  Negative zero renders
    unsigned — the sign carries no value, and both backends must emit the same bytes.
    """
    import decimal as decimal_module  # noqa: PLC0415

    if not isinstance(value, decimal_module.Decimal) or not value.is_finite():
        raise _coercion_error(value, "a finite Decimal", rule, span)
    if _outside_decimal_domain(value):
        raise _coercion_error(value, _DECIMAL_DOMAIN, rule, span)
    return format(abs(value) if value == 0 else value, "f")


def render_uuid(value: Any, rule: str, span: SpanProtocol) -> str:
    """A UUID coercion's canonical text: lowercase, hyphenated."""
    import uuid as uuid_module  # noqa: PLC0415

    if not isinstance(value, uuid_module.UUID):
        raise _coercion_error(value, "a UUID", rule, span)
    return str(value)


# --- Binary-chain folding ---------------------------------------------------------------

# The generated ``<Rule>Binary`` class is called positionally as ``binary(op, lhs, rhs,
# span)``; the emitter declares the fields in exactly that order.
_FoldBinary = Callable[[Any, Any, Any, Any], Any]


def check_fold_arity(operands: int, operators: int, rule: str, span: SpanProtocol) -> None:
    """The interleaving a fold rule's grammar fixes: one operator between each operand pair.

    A parser-produced CST always satisfies this, because the grammar shape is what produced
    it; a hand-built or mutated one need not.
    """
    if operands < 1:
        msg = f"rule {rule!r}: a fold needs at least one operand, but the node has none"
        raise AstError(msg, span)
    if operators != operands - 1:
        msg = (
            f"rule {rule!r}: a fold over {operands} operand(s) needs {operands - 1} operator(s), "
            f"but the node has {operators}"
        )
        raise AstError(msg, span)


def _merged(left: Any, right: Any, rule: str) -> Any:
    """The span covering both operands of one link.

    Both spans of a parser-produced fold come from the same parse, so the source-mismatch
    arm is reachable only from a hand-built CST mixing sources.
    """
    try:
        return left.merge(right)
    except ValueError as error:
        msg = f"rule {rule!r}: the operands of a fold come from different sources, so their spans cannot merge"
        raise AstError(msg, left) from error


def fold_left(
    binary: _FoldBinary, values: Sequence[Any], spans: Sequence[Any], operators: Sequence[Any], rule: str
) -> Any:
    """Left-nest a fold rule's operands: ``a op b op c`` becomes ``(a op b) op c``.

    ``spans`` are the operands' own CST spans, in source order; each synthesised link carries
    the merge of everything below it.  A single operand is returned unwrapped.

    The interleaving is checked here — one operator between each operand pair — so a caller who
    has not run :func:`check_fold_arity` over its own runs gets that diagnostic rather than a
    chain with values quietly dropped from it.  A generated converter checks first, against the
    CST node's own span, which is the better position to report.
    """
    check_fold_arity(len(values), len(operators), rule, spans[0] if spans else terminalsrc.UnknownSpan)
    result = values[0]
    span = spans[0]
    for operator, value, value_span in zip(operators, values[1:], spans[1:], strict=True):
        span = _merged(span, value_span, rule)
        result = binary(operator, result, value, span)
    return result


def fold_right(
    binary: _FoldBinary, values: Sequence[Any], spans: Sequence[Any], operators: Sequence[Any], rule: str
) -> Any:
    """Right-nest a fold rule's operands: ``a op b op c`` becomes ``a op (b op c)``.

    The interleaving is checked here, as in :func:`fold_left`.
    """
    check_fold_arity(len(values), len(operators), rule, spans[-1] if spans else terminalsrc.UnknownSpan)
    result = values[-1]
    span = spans[-1]
    pairs = zip(reversed(operators), reversed(values[:-1]), reversed(spans[:-1]), strict=True)
    for operator, value, value_span in pairs:
        span = _merged(value_span, span, rule)
        result = binary(operator, value, result, span)
    return result


def _against_direction(rule: str, side: str) -> typing.NoReturn:
    msg = (
        f"rule {rule!r}: this fold nests the other way, so the {side} operand of a link cannot itself "
        f"be a chain — the grammar has no shape to render it as; rebuild the chain in the fold's own "
        f"direction"
    )
    raise AstError(msg, terminalsrc.UnknownSpan)


def unfold_left(value: Any, binary: type, op_field: str, rule: str) -> tuple[list[Any], list[Any]]:
    """Split a left-nested chain back into its operands and operators, in source order."""
    operands: list[Any] = []
    operators: list[Any] = []
    node = value
    while isinstance(node, binary):
        operators.append(getattr(node, op_field))
        operands.append(node.rhs)
        node = node.lhs
    operands.append(node)
    operands.reverse()
    operators.reverse()
    if any(isinstance(operand, binary) for operand in operands[1:]):
        _against_direction(rule, "right")
    return operands, operators


def unfold_right(value: Any, binary: type, op_field: str, rule: str) -> tuple[list[Any], list[Any]]:
    """Split a right-nested chain back into its operands and operators, in source order."""
    operands: list[Any] = []
    operators: list[Any] = []
    node = value
    while isinstance(node, binary):
        operators.append(getattr(node, op_field))
        operands.append(node.lhs)
        node = node.rhs
    operands.append(node)
    if any(isinstance(operand, binary) for operand in operands[:-1]):
        _against_direction(rule, "left")
    return operands, operators


# --- Serialisation: AST -> CST ----------------------------------------------------------


class ParseError(Exception):
    """Source text could not be parsed into a CST.

    ``position`` is the offset the parser reached; ``message`` is the parser's own
    formatted diagnostic.
    """

    def __init__(self, message: str, position: int) -> None:
        self.message = message
        self.position = position
        super().__init__(message)


@dataclasses.dataclass(frozen=True)
class Pattern:
    """A guard admitting only text the grammar's terminal could have matched."""

    pattern: str


@dataclasses.dataclass(frozen=True)
class LiteralText:
    """A guard admitting only a literal's own text.

    A labeled literal renders from the grammar, so a position holding one may take a value
    only when that value *is* the literal: anything else would come back as different text.
    """

    text: str


@dataclasses.dataclass(frozen=True)
class Convertible:
    """A guard admitting a value an erased rule's own reverse converter accepts.

    Two rules ``transparent;`` erases to one Python type — two text-carrying terminals, or two
    integer coercions — leave nothing on the value itself to tell their positions apart.  What
    distinguishes them is which terminal the value renders to, which is exactly what the
    converter checks, so the converter is the guard.

    Only a converter that reports every rejection as an ``AstError`` may be used this way: the
    probe runs it on values meant for the sibling positions, and any other exception escapes.
    """

    convert: Callable[[Any], Any]


def accepts(guard: Any, value: Any) -> bool:
    """Whether ``value`` can occupy an item position carrying ``guard``."""
    if isinstance(guard, Pattern):
        return isinstance(value, str) and re.fullmatch(guard.pattern, value) is not None
    if isinstance(guard, LiteralText):
        return value == guard.text
    if isinstance(guard, Convertible):
        try:
            guard.convert(value)
        except AstError:
            return False
        return True
    return isinstance(value, guard)


class Cursor:
    """A field's values, handed out to the item positions that can carry them.

    Each position takes as many values as its quantifier allows, leaving behind whatever
    later required positions for the same label still need.  A ``guard`` restricts a
    position to the values it can actually hold, which is how the branches of a
    sub-expression alternation share one label.
    """

    __slots__ = ("_pos", "_values")

    def __init__(self, values: Sequence[Any]) -> None:
        self._values = values
        self._pos = 0

    def take(self, maximum: float, reserve: int = 0, guard: Any = None) -> list[Any]:
        taken: list[Any] = []
        while len(taken) < maximum and len(self._values) - self._pos > reserve:
            value = self._values[self._pos]
            if guard is not None and not accepts(guard, value):
                break
            taken.append(value)
            self._pos += 1
        return taken

    def remaining(self) -> int:
        return len(self._values) - self._pos


def field_values(value: Any) -> Sequence[Any]:
    """One field's values, whatever container holds them.

    A map hands its values out in insertion order; each element carries its own key field,
    which is the authoritative one, so the map's keys are never read back.
    """
    if value is None:
        return ()
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, list):
        return value
    return (value,)


def cursor(value: Any) -> Cursor:
    """A cursor over one field: absent, single, collection or keyed map alike."""
    return Cursor(field_values(value))


def multi_values(grouped: Mapping[Any, Sequence[Any]], rule: str) -> list[Any]:
    """One ``multi`` keyed field's elements, its keys' groups in insertion order.

    Grouping is what the map records, so the elements come out grouped and the source order
    that interleaved two keys is not recoverable.  A key whose group is empty carries no
    element to render — the key lives on the element, not on the map — so it is refused rather
    than dropped silently.
    """
    values: list[Any] = []
    for key, elements in grouped.items():
        if not elements:
            msg = f"rule {rule!r}: the {key!r} key has no element to render it on"
            raise AstError(msg, terminalsrc.UnknownSpan)
        values.extend(elements)
    return values


def multi_cursor(grouped: Mapping[Any, Sequence[Any]], rule: str) -> Cursor:
    """A cursor over one ``multi`` keyed field, in grouped order."""
    return Cursor(multi_values(grouped, rule))


def flag_cursor(flag: bool) -> Cursor:  # noqa: FBT001
    """A cursor over a presence field: one occurrence when set, none otherwise."""
    return Cursor((flag,) if flag else ())


def check_consumed(rule: str, cursors: Sequence[tuple[str, Cursor]]) -> None:
    """Every field value must have found an item position to occupy."""
    for label, values in cursors:
        left = values.remaining()
        if left:
            msg = f"rule {rule!r}: the grammar has no place for {left} more {label!r} value(s)"
            raise AstError(msg, terminalsrc.UnknownSpan)


def filled(values: Sequence[Any], minimum: int, rule: str, label: str) -> Sequence[Any]:
    """The values an item position took, once its own lower bound is known to be met.

    A required position left empty would put a CST missing a required child in front of the
    formatter, which can only report that something is wrong with the whole node; the
    shortfall is the user's data and is named here instead.
    """
    if len(values) < minimum:
        msg = (
            f"rule {rule!r}: the grammar needs {minimum} {label!r} value(s) at this position, "
            f"but {len(values)} were available"
        )
        raise AstError(msg, terminalsrc.UnknownSpan)
    return values


def unplaceable(value: Any, rule: str, label: str) -> typing.NoReturn:
    """No branch of an alternation can carry this value."""
    msg = f"rule {rule!r}: no item position accepts a {type(value).__name__} value for {label!r}"
    raise AstError(msg, terminalsrc.UnknownSpan)


def populated(values: Mapping[str, Any]) -> frozenset[str]:
    """The fields that carry something: not ``None``, not ``False``, not an empty container."""
    return frozenset(name for name, value in values.items() if _is_populated(value))


def holds(value: Any) -> bool:
    """Whether a field carries a value, for a field that can legitimately hold ``False``.

    ``populated`` reads a bare ``False`` as absent, which is what the presence flag of an
    optional labeled literal means and the opposite of what a field whose own value is a boolean
    means — a rule ``bool:`` maps and ``transparent;`` erases carries ``False`` as data.  Only
    ``None`` and an empty container are absent here.
    """
    if value is None:
        return False
    if isinstance(value, list | dict):
        return bool(value)
    return True


def _is_populated(value: Any) -> bool:
    return value is not False and holds(value)


def wrapper_needed(values: Sequence[Any]) -> bool:
    """Whether an optional ``flatten;`` wrapper has to be rebuilt around its hoisted fields.

    The wrapper is what the grammar spells; the AST holds only its contents, so it is emitted
    exactly when something it would carry is populated.  A value whose hoisted fields all sit at
    their absent defaults therefore renders without the wrapper, as an absent one does.
    """
    return any(_is_populated(value) for value in values)


def hoisted(value: Any, rule: str, field: Any) -> Any:
    """One field a flattened wrapper requires, checked before the wrapper is rebuilt."""
    if value is None:
        msg = (
            f"rule {rule!r}: the flattened wrapper needs a {field!r} value, but it is absent; "
            f"populate it, or leave every field hoisted out of the wrapper empty"
        )
        raise AstError(msg, terminalsrc.UnknownSpan)
    return value


def check_group(
    rule: str,
    present: frozenset[str],
    branches: Sequence[frozenset[str]],
    exclusive: frozenset[str],
    *,
    demanded: bool,
) -> None:
    """The populated fields of one sub-expression alternation must suit a single branch.

    ``branches`` is the labels each branch carries.  ``demanded`` says every branch needs a
    value, so leaving all of them empty renders nothing where the grammar requires something.
    ``exclusive`` narrows the second test to the labels this alternation alone can supply: a
    label the alternative also uses elsewhere may legitimately be populated from there, and a
    repeatable alternation may draw one label's values from several branches in turn, so its
    ``exclusive`` set is empty and only the first test applies.
    """
    if demanded and not present:
        offered = sorted(frozenset[str]().union(*branches))
        msg = f"rule {rule!r}: the grammar needs one of {offered} at this position, but none is populated"
        raise AstError(msg, terminalsrc.UnknownSpan)
    narrowed = present & exclusive
    if narrowed and not any(narrowed <= labels for labels in branches):
        offered = " | ".join(str(sorted(labels)) for labels in branches)
        msg = (
            f"rule {rule!r}: {sorted(narrowed)} cannot come from one branch of this alternation, "
            f"which carries {offered}; populate the fields of a single branch"
        )
        raise AstError(msg, terminalsrc.UnknownSpan)


def alternative_fits(present: frozenset[str], required: frozenset[str], labels: frozenset[str]) -> bool:
    """Whether an alternative can carry exactly the populated fields."""
    return required <= present <= labels


def field_fits(value: Any, guards: Sequence[Any]) -> bool:
    """Whether every value a field holds is of a kind an alternative accepts at that label.

    The kind half of alternative selection, beside ``alternative_fits``'s name half: a label
    carrying several types is one field, and which of them a value is decides which
    alternatives can render it.  An empty field constrains nothing — what an alternative does
    with a label it is not given is the name half's question.
    """
    return all(any(accepts(guard, item) for guard in guards) for item in field_values(value))


def validate_terminal(text: Any, pattern: str, rule: str, label: str) -> str:
    """Check that a field's text is something the grammar's terminal could have matched."""
    if not isinstance(text, str):
        msg = f"rule {rule!r}: the {label!r} value is {type(text).__name__}, not text"
        raise AstError(msg, terminalsrc.UnknownSpan)
    if re.fullmatch(pattern, text) is None:
        msg = f"rule {rule!r}: the {label!r} text {text!r} does not match the terminal /{pattern}/"
        raise AstError(msg, terminalsrc.UnknownSpan)
    return text


def text_span(text: Any, pattern: str, rule: str, label: str) -> terminalsrc.Span:
    """A span carrying its own single-token source, for a synthesised regex child."""
    return source_span(validate_terminal(text, pattern, rule, label))


def source_span(text: str) -> terminalsrc.Span:
    return terminalsrc.Span.with_source(0, len(text), text)


@dataclasses.dataclass(frozen=True)
class TerminalAlt:
    """One alternative of a terminal-only rule, as a single regex over the node's text."""

    pattern: str | None
    pieces: tuple[tuple[str | None, str | None], ...]
    """Per included item: its label name (``None`` when unlabeled) and capture group."""


def terminal_to_cst(
    node_class: Any,
    text: Any,
    alternatives: Sequence[TerminalAlt],
    rule: str,
    *,
    redirected: bool = False,
) -> Any:
    """Rebuild a terminal-only rule's node by splitting its text across the grammar's items.

    The node's span must carry the full text for round-tripping through ``from_cst``, which
    reads it back.  Under ``text_from:`` the text belongs to one child instead, so the node's
    own span stays unknown and ``redirected`` says so.
    """
    if all(alternative.pattern is None for alternative in alternatives):
        msg = (
            f"rule {rule!r}: the rule's shape cannot be rebuilt from text — every alternative holds "
            f"a repeated terminal, a sub-expression or a rule reference, so no split of the text "
            f"back into children is determined; restructure the rule or convert it by hand"
        )
        raise AstError(msg, terminalsrc.UnknownSpan)
    if not isinstance(text, str):
        msg = f"rule {rule!r}: text is {type(text).__name__}, not text"
        raise AstError(msg, terminalsrc.UnknownSpan)
    for alternative in alternatives:
        if alternative.pattern is None:
            continue
        match = re.fullmatch(alternative.pattern, text)
        if match is None:
            continue
        node = node_class(span=terminalsrc.UnknownSpan if redirected else source_span(text))
        for label, group in alternative.pieces:
            child = terminalsrc.UnknownSpan if group is None else source_span(match.group(group))
            node.append(child, None if label is None else getattr(node_class.Label, label))
        return node
    msg = f"rule {rule!r}: text {text!r} is not something the rule could have matched"
    raise AstError(msg, terminalsrc.UnknownSpan)


def parse_cst(parser_class: Any, rule: str, source: str, filename: str | None = None) -> Any:
    """Parse ``source`` as ``rule`` and return the CST, raising ``ParseError`` on failure."""
    terminals = terminalsrc.TerminalSource(source, filename)
    parser = parser_class(terminals)
    result = getattr(parser, f"apply__parse_{rule}")(0)
    if not result or result.pos != len(terminals.terminals):
        message, position = errors.failure_details(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
            result.pos if result else None,
        )
        raise ParseError(message, position)
    return result.result


def unrenderable(rule: str) -> AstError:
    """The error for a synthesised CST the generated formatter declined to render.

    Synthesis follows the positional contract the formatter checks, so either the grammar has a
    shape the formatter cannot rebuild from any CST — in which case parsing the same text and
    formatting the result fails the same way — or the synthesis itself is wrong.
    """
    msg = (
        f"the formatter could not render a synthesised {rule!r} node; either the grammar has a "
        f"shape the formatter cannot rebuild from a CST — parsing the same text and formatting "
        f"the result fails the same way — or this is a bug in FLTK's AST synthesis"
    )
    return AstError(msg, terminalsrc.UnknownSpan)


def unparse_cst(unparser_class: Any, rule: str, node: Any, renderer_config: Any = None) -> str:
    """Render a synthesised CST through the grammar's generated formatter.

    The formatter package is imported here rather than at module scope so that consumers
    who only convert in the parse direction do not pay for it.
    """
    from fltk.unparse.renderer import Renderer, RendererConfig  # noqa: PLC0415
    from fltk.unparse.resolve_specs import resolve_spacing_specs  # noqa: PLC0415

    unparser = unparser_class("")
    result = getattr(unparser, f"unparse_{rule}")(node)
    if result is None:
        raise unrenderable(rule)
    return Renderer(renderer_config or RendererConfig()).render(resolve_spacing_specs(result.accumulator.doc))
