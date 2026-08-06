"""Backend-neutral AST model: the analysis layer both AST emitters consume.

``build_ast_model`` turns an INLINE-expanded, trivia-classified grammar plus a resolved
``.fltkast`` sidecar into an ``AstModel``: one node form per non-trivia rule (product,
terminal-only, enum-shaped or sum), plus the auxiliary types the emitters materialise (sum
payload classes, field enums, value enums).  Rule classification, field typing, alternative
dispatch signatures and name hygiene are all decided here, so the Python and Rust ASTs are
shape-equivalent by construction.

The model describes types, the grammar-shaped synthesis plans the reverse converters
follow, and the analysis over those plans: which item position takes which value, how many
it must leave for later positions, and what guard tells rival positions apart.  The
backends render those decisions into source text; they do not re-derive them.  The same holds
for recursion: which by-value edges need an indirection, and which types nest deeply enough that
their teardown and comparison must not recurse, are computed here; only the ``Box<...>`` spelling
belongs to Rust.
"""

from __future__ import annotations

import dataclasses
import enum
import itertools
import math
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import TypeAlias

from fltk.fegen import ast_config as ac
from fltk.fegen import cst_ergonomics as ce
from fltk.fegen import grammar_shape as gshape
from fltk.fegen import gsm, naming
from fltk.fegen.grammar_shape import (
    AltInfo,
    AltSignature,
    alt_infos,
    alternatives_are_disjoint,
    has_whitespace_separator,
    visit_included_items,
)

# Members every generated node class carries, so no field may take these names.
RESERVED_FIELD_NAMES = frozenset({"span", "text", "from_cst", "to_cst"})

CST_FIELD_NAME = "cst"
"""The back-pointer member ``option cst = true;`` adds, reserved only while it is on."""

FOLD_LHS = "lhs"
FOLD_RHS = "rhs"
"""The two operand members of a fold link, which no operator field may be named."""

FOLD_OPERAND_VARIANT = "Operand"
FOLD_BINARY_VARIANT = "Binary"
"""The computed variant names of a fold rule, as a ``variant`` statement selects them."""

PARSE_FUNCTION = "parse"
UNPARSE_FUNCTION = "unparse"
"""The Python module's one-call entry points, emitted when a parser and an unparser are named."""

PARSE_STR_FUNCTION = "parse_str"
UNPARSE_STR_FUNCTION = "unparse_str"
"""The Rust module's spellings of the same two, which take and return text."""

ENTRY_POINTS = (PARSE_FUNCTION, UNPARSE_FUNCTION, PARSE_STR_FUNCTION, UNPARSE_STR_FUNCTION)
"""Every module-level entry point a backend can emit, claimed whether or not it is emitted."""

EQ_SUPPORT_MODULE = "eq_walk"
"""The Rust module holding the bounded-stack equality walk.

A Rust module and a Rust type share one namespace, so a rule renamed to this spelling would
collide with it; the name is claimed on both backends because the claim table is one namespace.
"""

ALT_SUFFIX = "_alt"
"""What the per-alternative halves of a private reverse helper are suffixed with."""

MODULE_IMPORT_NAMES = (
    "annotations",
    "astrt",
    "cst",
    "dataclasses",
    "enum",
    "fltk",
    "parser",
    "terminalsrc",
    "typing",
    "unparser",
    "_parser",
    "_unparser",
)
"""The fixed module-level names a generated module's own imports bind, on either backend.

An import alias occupies the namespace a generated class does: ``class cst:`` emitted under
``import <app>.cst as cst`` wins at module exec, and every ``cst.X`` the converters read then
resolves against the class, failing at conversion time with nothing said at generation time.
Rust collides the same way — ``use <path> as cst;`` and a type named ``cst`` share one
namespace.  Both backends' spellings are claimed together, because the claim table is one
namespace.
"""

RUST_PATH_ROOTS = frozenset({"crate", "super", "self", "Self"})
"""The Rust path heads that name a position in the module tree rather than a module-level name.

Every other bare head — ``app`` in ``app::Atom`` — resolves against the generated module's own
items before it reaches the extern prelude, so a generated type spelled that way shadows it.
"""

_MIN_ALTERNATIVES = 2
_FOLD_LABELS = 2

# A label's positions need a guard once two of them accept different things.
_RIVAL_SLOTS = 2

# A `bool:` rule maps one variant to true and one to false.
_BOOLEAN_VARIANTS = 2


def converter_names(rule_name: str) -> tuple[str, str]:
    """The public converter pair of a rule: forward, then reverse."""
    return f"{rule_name}_from_cst", f"{rule_name}_to_cst"


def erased_converter_names(rule_name: str) -> tuple[str, str]:
    """The private converter pair of a ``transparent;`` rule, which has no type to hang one on."""
    return f"_erased_{rule_name}_from_cst", f"_erased_{rule_name}_to_cst"


def flat_converter_names(rule_name: str) -> tuple[str, str]:
    """The private converter pair of a ``flatten;`` wrapper, whose fields live on its parents."""
    return f"_flat_{rule_name}_from_cst", f"_flat_{rule_name}_to_cst"


def erased_alt_converter_name(rule_name: str, index: int) -> str:
    """One alternative's half of a ``transparent;`` product's reverse helper."""
    return f"{erased_converter_names(rule_name)[1]}{ALT_SUFFIX}{index}"


def flat_alt_converter_name(rule_name: str, index: int) -> str:
    """One alternative's half of a ``flatten;`` wrapper's reverse helper."""
    return f"{flat_converter_names(rule_name)[1]}{ALT_SUFFIX}{index}"


def drop_witness_name(rule_name: str) -> str:
    """The function rendering the sentinel a fold link's iterative teardown writes back."""
    return f"_{rule_name}_drop_witness"


def alternative_dispatch_name(rule_name: str) -> str:
    """The function recovering which alternative of a sum rule matched.

    Emitted by the Rust backend only — Python dispatches through a module constant — but claimed
    on both, because the claim table is one namespace.
    """
    return f"_{rule_name}_alternative"


def field_enum_converter_name(enum_name: str) -> str:
    """The converter of a field enum, which dispatches on the kind of child that arrived."""
    return f"_{_snake_case(enum_name)}_from_cst"


def terminal_constant_name(rule_name: str) -> str:
    """The module constant holding a terminal rule's alternative patterns."""
    return f"_{rule_name.upper()}_TERMINALS"


def payload_constant_name(rule_name: str) -> str:
    """The module constant holding the classes a sum or fold rule's value can be."""
    return f"_{rule_name.upper()}_PAYLOADS"


def signature_constant_name(rule_name: str) -> str:
    """The module constant holding a sum rule's per-alternative label signatures."""
    return f"_{rule_name.upper()}_SIGNATURES"


class AstModelError(ValueError):
    """Every generation-time problem found while building the model, reported together."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("AST model errors:\n" + "\n".join(f"- {error}" for error in errors))


# --- Types -----------------------------------------------------------------------------


class ScalarKind(enum.Enum):
    """A field element that is not a generated node type."""

    TEXT = "text"
    """The child's span text: ``String`` / ``str``."""

    SPAN = "span"
    """Position only; a literal's text is a grammar constant."""

    BOOL = "bool"
    """Presence of an optional labeled literal."""


@dataclasses.dataclass(frozen=True, slots=True)
class ScalarType:
    kind: ScalarKind


TEXT = ScalarType(ScalarKind.TEXT)
SPAN = ScalarType(ScalarKind.SPAN)
BOOL = ScalarType(ScalarKind.BOOL)


@dataclasses.dataclass(frozen=True, slots=True)
class NodeType:
    """A reference to a generated AST type by name."""

    name: str


@dataclasses.dataclass(frozen=True, slots=True)
class CustomType:
    """A rule handed to a user-written type by ``custom(rust: ..., python: ...);``.

    The generator emits no type and no converter for the rule; each backend names its own
    entry and obtains values through the ``from_cst``/``to_cst`` convention.  An entry is
    ``None`` when the sidecar omits it, which validation permits only for a backend that is
    not being generated.
    """

    rule_name: str
    python: str | None
    rust: str | None


PYTHON_SCALAR_TYPES: Mapping[str, str] = {
    **dict.fromkeys(ac.INTEGER_SCALAR_TYPES, "int"),
    **dict.fromkeys(ac.FLOAT_SCALAR_TYPES, "float"),
    "uuid": "uuid.UUID",
    "decimal": "decimal.Decimal",
}
"""The Python type each builtin ``type:`` coercion maps to.

One table serves two layers whose agreement is load-bearing: the annotation the Python
emitter writes on a coerced node's ``value``, and the payload identity that keeps a sum's
Python union from listing one type twice.  Its keys are the sidecar's whole builtin
vocabulary — a builtin with no entry here has no Python spelling at all.
"""


@dataclasses.dataclass(frozen=True, slots=True)
class BuiltinCoercion:
    """``type: <builtin>;`` — one of the scalar mappings fixed on both backends.

    The name is the sidecar spelling; ``bits`` and ``signed`` are what the width-checked
    parse helpers need, and are meaningless for ``uuid`` and ``decimal``.
    """

    name: str

    @property
    def is_integer(self) -> bool:
        return self.name in ac.INTEGER_SCALAR_TYPES

    @property
    def is_float(self) -> bool:
        return self.name in ac.FLOAT_SCALAR_TYPES

    @property
    def bits(self) -> int:
        return int(self.name[1:])

    @property
    def signed(self) -> bool:
        return self.name.startswith("i")


@dataclasses.dataclass(frozen=True, slots=True)
class CustomCoercion:
    """``type: custom(...);`` — the user's scalar type and its paired parse/unparse functions.

    An entry is ``None`` when the sidecar omits it, which validation permits only for a
    backend that is not being generated.
    """

    rule_name: str
    python_type: str | None
    python_parse: str | None
    python_unparse: str | None
    rust_type: str | None
    rust_parse: str | None
    rust_unparse: str | None


Coercion: TypeAlias = BuiltinCoercion | CustomCoercion


@dataclasses.dataclass(frozen=True, slots=True)
class TransparentType:
    """A rule erased by ``transparent;``: use sites carry its payload, not a node of its own.

    ``payload`` is what the rule's single value is — the text of a terminal-only rule, its
    value enum, or the type of a single-field product's one field, which may itself be
    erased.  ``coercion`` is the rule's ``type:`` when it has one, and then ``payload`` is
    the raw text the coerced value replaces.  The rule name is kept because the conversion
    still goes through the erased rule's own private helper in both directions.
    """

    rule_name: str
    payload: ElementType
    coercion: Coercion | None = None


ElementType: TypeAlias = ScalarType | NodeType | CustomType | TransparentType


class Container(enum.Enum):
    SINGLE = "single"
    OPTIONAL = "optional"
    COLLECTION = "collection"
    MAP = "map"
    """An insertion-ordered map, for a collection of elements declaring ``key:``."""


_CONTAINER_BY_ARITY = {
    ce.ArityClass.REQUIRED_SINGLE: Container.SINGLE,
    ce.ArityClass.OPTIONAL_SINGLE: Container.OPTIONAL,
    ce.ArityClass.COLLECTION: Container.COLLECTION,
}


@dataclasses.dataclass(frozen=True, slots=True)
class MapKey:
    """What keys a ``MAP`` container: one field of the element rule that declared ``key:``.

    ``field_name`` is the member holding it, after any ``field { name: }`` rename — the field
    is authoritative and the map key a lookup convenience, so both directions read the key off
    the element rather than off the map.  ``element`` is the key's own resolved type, which is
    text or an integer coercion of it.
    """

    rule_name: str
    label: str
    field_name: str
    element: ElementType


@dataclasses.dataclass(frozen=True, slots=True)
class FieldType:
    element: ElementType
    container: Container

    key: MapKey | None = None
    """The map key, on a ``MAP`` container only."""


@dataclasses.dataclass(frozen=True, slots=True)
class Field:
    name: str
    label: str
    type: FieldType

    hoist: str | None = None
    """The label of the ``flatten;`` wrapper this field was hoisted out of, if any."""


@dataclasses.dataclass(frozen=True, slots=True)
class Hoist:
    """A ``flatten;`` wrapper spliced into the node that references it.

    ``label`` is the wrapper's own label in the containing rule, which is where the reverse
    direction re-materialises it.  ``fields`` are the wrapper's fields as they appear on the
    containing node — degraded to optional types where ``optional`` is set — in the
    wrapper's own declaration order, which is the order its private helpers use.  ``required``
    names the ones that had to be populated before degradation, so a partially filled optional
    wrapper is an error rather than a CST missing a required child.
    """

    rule_name: str
    label: str
    optional: bool
    fields: tuple[Field, ...]
    required: frozenset[str]


@dataclasses.dataclass(frozen=True, slots=True)
class FieldEnumVariant:
    name: str
    element: ElementType


@dataclasses.dataclass(frozen=True, slots=True)
class FieldEnum:
    """The type of a label that carries more than one element type."""

    name: str
    rule_name: str
    label: str
    variants: tuple[FieldEnumVariant, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class ValueVariant:
    name: str
    """UpperCamelCase, as a Rust enum variant spells it."""

    member: str
    """UPPER_SNAKE_CASE, as a Python enum member spells it."""

    label: str

    literal: str
    """The canonical spelling: the text of the first alternative carrying ``label``.

    Alternatives of one rule sharing a label declare their spellings semantically equivalent —
    the parser does not record which was written — so they are one variant and this is what the
    reverse direction renders it as.
    """


@dataclasses.dataclass(frozen=True, slots=True)
class ValueEnum:
    """The fieldless value enum of an enum-shaped rule."""

    name: str
    rule_name: str
    variants: tuple[ValueVariant, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class ProductNode:
    """One struct/dataclass with one field per label, plus ``span``.

    ``merged`` marks a multi-alternative rule whose alternatives are not a sound
    structural fork; its field arities are the whole-rule combined view.
    """

    name: str
    rule_name: str
    fields: tuple[Field, ...]
    merged: bool

    hoists: tuple[Hoist, ...] = ()
    """The ``flatten;`` wrappers whose fields appear among ``fields``."""


@dataclasses.dataclass(frozen=True, slots=True)
class TerminalNode:
    """A rule whose children are terminals only: ``text`` plus ``span``."""

    name: str
    rule_name: str

    coercion: Coercion | None = None
    """``type:`` — the node carries ``value: T`` instead of ``text: str``."""

    text_from: str | None = None
    """``text_from:`` — the label whose child span the text comes from, not the node's span."""


@dataclasses.dataclass(frozen=True, slots=True)
class EnumNode:
    """A pure dispatch over literal alternatives: a value enum plus a span-carrying node."""

    name: str
    rule_name: str
    value_enum: ValueEnum
    """The variants' names, labels and literals.

    Under ``bool:`` the enum is not a generated type — the node carries ``value: bool`` — but
    the converters still need each alternative's label and literal, so it is built either way
    and only registered on ``AstModel.value_enums`` when it is emitted.
    """

    bool_truthy: str | None = None
    """``bool:`` — the alternative label that maps to ``True``; the other maps to ``False``."""


@dataclasses.dataclass(frozen=True, slots=True)
class PayloadClass:
    """The generated product-like payload of a sum variant that has no single node type."""

    name: str
    rule_name: str
    alternative_index: int
    fields: tuple[Field, ...]

    hoists: tuple[Hoist, ...] = ()
    """The ``flatten;`` wrappers whose fields appear among ``fields``."""


@dataclasses.dataclass(frozen=True, slots=True)
class SumVariant:
    name: str
    alternative_index: int
    payload: ElementType
    signature: AltSignature

    payload_rule: str | None = None
    """The rule the payload comes from, for a direct payload; ``None`` for a generated one."""


@dataclasses.dataclass(frozen=True, slots=True)
class SumNode:
    """A Rust enum / Python union alias over provably distinguishable alternatives."""

    name: str
    rule_name: str
    variants: tuple[SumVariant, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class FoldBinary:
    """One link of a fold chain: an operator and the two sub-chains it joins.

    ``op`` occurs exactly once per link.  The ``lhs``/``rhs`` members both carry the fold
    rule's own type, so a link may hold either an operand or a deeper link — which is what
    makes the chain a tree; ``FoldNode.direction`` says which side deepens.
    """

    name: str
    rule_name: str
    op: Field


@dataclasses.dataclass(frozen=True, slots=True)
class FoldNode:
    """A rule ``fold_left:``/``fold_right:`` turns into a binary chain over its operands.

    The rule's type is the choice between a bare operand and one link: a Rust enum with the
    two variants, a Python union of the operand's type and the link class.  A single-operand
    node converts to the operand itself, so the chain type appears only where the grammar
    actually repeated.
    """

    name: str
    rule_name: str
    direction: ac.FoldDirection
    binary: FoldBinary
    operand_variant: str
    binary_variant: str

    operand: Field
    """The operands one node's chain holds, as the collection the grammar matched.

    Both this and ``operators`` describe the *flattened* chain — the reverse direction
    distributes them back over the grammar's alternating item positions — while
    ``binary.op`` is the single-valued member of one link.
    """

    operators: Field


RuleNode: TypeAlias = ProductNode | TerminalNode | EnumNode | SumNode | FoldNode


# --- Synthesis plans -------------------------------------------------------------------


class SlotKind(enum.Enum):
    """What one grammar-item position contributes when a CST is synthesised from an AST."""

    NODE = "node"
    """A labeled rule reference: the referenced rule's reverse converter, per element."""

    TEXT = "text"
    """A labeled regex: a fresh source-bearing span over the field's text."""

    LITERAL = "literal"
    """A labeled literal: a sourceless span, one per recorded occurrence."""

    UNLABELED = "unlabeled"
    """An unlabeled included terminal: sourceless spans at the grammar minimum."""


@dataclasses.dataclass(frozen=True, slots=True)
class Slot:
    """One item position of an alternative, with the bounds it imposes on its label."""

    kind: SlotKind
    label: str | None
    rule_name: str | None
    """The referenced rule, for ``NODE`` slots."""

    pattern: str | None
    """The terminal a ``TEXT`` slot's value must match."""

    minimum: int
    maximum: float

    group: int | None = None
    """Shared by the slots of one sub-expression alternation's branches; ``None`` outside one."""

    branch: int = 0
    """Which branch of ``group`` the slot came from."""

    branch_count: int = 1
    """How many branches ``group`` has, counting those that contribute no slot at all."""

    group_maximum: float = 1
    """How often ``group`` itself may repeat, whatever the bounds of the slots inside it.

    A repeating alternation may fill one label from several branches in turn, which a slot's
    own maximum cannot say: a starred item inside a branch of a group that occurs once has an
    unbounded maximum too, and the two cases need opposite treatment.
    """

    literal: str | None = None
    """The text a ``LITERAL`` slot renders, which is the only value it can carry."""


@dataclasses.dataclass(frozen=True, slots=True)
class AltPlan:
    """One alternative's item positions, in grammar order."""

    index: int
    slots: tuple[Slot, ...]
    labels: frozenset[str]
    required_labels: frozenset[str]


@dataclasses.dataclass(frozen=True, slots=True)
class TerminalPiece:
    """One included item of a terminal-only alternative, and where its text comes from."""

    label: str | None
    group: str | None
    """The capture group holding the piece's text; ``None`` for a literal."""


@dataclasses.dataclass(frozen=True, slots=True)
class TerminalPlan:
    """How a terminal-only alternative splits a node's text back into children.

    ``pattern`` is the whole alternative spelled as one regex, with a named capture group
    per included regex item.  It is ``None`` when the alternative cannot be reconstructed
    from text alone (a sub-expression, a rule reference, or a repeated included item):
    a single regex cannot say which slice of the text each occurrence took.
    """

    index: int
    pattern: str | None
    pieces: tuple[TerminalPiece, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class SynthesisPlan:
    """Everything the reverse converters need about one rule's grammar shape."""

    alternatives: tuple[AltPlan, ...]
    terminals: tuple[TerminalPlan, ...]
    """Per-alternative text plans; empty for anything but a terminal-only rule."""


_GROUP_PREFIX = "_ast_g"

_QUANTIFIER_SUFFIX = {(1, 1): "", (0, 1): "?", (0, math.inf): "*", (1, math.inf): "+"}

# A group name's first character rules out `(?<=` and `(?<!`, which open a lookbehind rather
# than a group and whose body would otherwise be read as a name up to some later `>`.  `(?P<=`
# is not valid syntax in either engine, so excluding both spellings after the optional `P` is
# safe.
_NAMED_GROUP_RE = re.compile(r"\(\?P?<([^>=!][^>]*)>")


def _repeated_group_names(pattern: str) -> list[str]:
    """The capture group names ``pattern`` defines more than once, in order of first repeat.

    Both spellings count: ``(?P<x>)`` is the Python one and ``(?<x>)`` the Rust one, and a
    composed pattern is handed to whichever engine the backend uses.  A ``(`` preceded by an
    odd number of backslashes is escaped, so what follows it is text rather than a group.

    This is deliberately a text scan rather than a compile: a pattern only the Rust engine
    accepts must not be refused here.  Group-like text inside a character class is therefore
    out of reach and degrades to the pre-existing failure at first serialize.
    """
    seen: set[str] = set()
    repeated: list[str] = []
    for match in _NAMED_GROUP_RE.finditer(pattern):
        prefix = pattern[: match.start()]
        if (len(prefix) - len(prefix.rstrip("\\"))) % 2 == 1:
            continue
        name = match.group(1)
        if name in seen and name not in repeated:
            repeated.append(name)
        seen.add(name)
    return repeated


def _item_bounds(item: gsm.Item) -> tuple[int, float]:
    minimum = 0 if item.quantifier.is_optional() else 1
    maximum = math.inf if item.quantifier.is_multiple() else 1
    return minimum, maximum


def _slots_for_alternative(items: gsm.Items) -> list[Slot]:
    """The slots one alternative contributes, descending into INCLUDE sub-expressions.

    A sub-expression's own quantifier multiplies the bounds of every slot inside it.  The
    branches of an alternation are laid out consecutively and share a ``group`` id, each slot
    recording its branch and how many branches the group has: the branches are mutually
    exclusive, so a label they share is distributed over them by value rather than by
    position, and a label one branch omits is demanded by none of them.  A sub-expression
    with one alternative starts no group, and one nested inside a branch stays in that
    branch.
    """
    groups = itertools.count()

    def walk(
        items: gsm.Items, outer_min: int, outer_max: float, alternation: tuple[int, int, int, float] | None
    ) -> list[Slot]:
        slots: list[Slot] = []
        for item in items.items:
            if item.disposition == gsm.Disposition.INLINE:
                msg = f"{ce.INLINE_NOT_EXPANDED_MSG} (item {item!r})"
                raise ValueError(msg)
            if item.disposition != gsm.Disposition.INCLUDE:
                continue
            minimum, maximum = _item_bounds(item)
            minimum *= outer_min
            maximum *= outer_max
            group, branch, count, group_max = alternation if alternation is not None else (None, 0, 1, 1.0)
            shared = (group, branch, count, group_max)
            term = item.term
            if isinstance(term, gsm.Identifier):
                if item.label is not None:
                    slots.append(Slot(SlotKind.NODE, item.label, term.value, None, minimum, maximum, *shared))
            elif isinstance(term, gsm.Regex):
                kind = SlotKind.TEXT if item.label is not None else SlotKind.UNLABELED
                slots.append(Slot(kind, item.label, None, term.value, minimum, maximum, *shared))
            elif isinstance(term, gsm.Literal):
                kind = SlotKind.LITERAL if item.label is not None else SlotKind.UNLABELED
                slots.append(Slot(kind, item.label, None, None, minimum, maximum, *shared, literal=term.value))
            elif isinstance(term, Sequence):
                inner = alternation
                if inner is None and len(term) >= _MIN_ALTERNATIVES:
                    inner = (next(groups), 0, len(term), maximum)
                for index, alternative in enumerate(term):
                    # Inside a branch already: this alternation's slots stay in the outer one.
                    nested = inner
                    if inner is not None and alternation is None:
                        nested = (inner[0], index, inner[2], inner[3])
                    slots.extend(walk(alternative, minimum, maximum, nested))
        return slots

    return walk(items, 1, 1, None)


def _alt_plan(index: int, items: gsm.Items, arities: Mapping[str, ce.LabelCount]) -> AltPlan:
    return AltPlan(
        index=index,
        slots=tuple(_slots_for_alternative(items)),
        labels=frozenset(arities),
        required_labels=frozenset(label for label, count in arities.items() if count.min >= 1),
    )


def _terminal_plan(index: int, items: gsm.Items) -> TerminalPlan:
    parts: list[str] = []
    pieces: list[TerminalPiece] = []
    unsupported = TerminalPlan(index=index, pattern=None, pieces=())
    for item in items.items:
        if item.disposition == gsm.Disposition.INLINE:
            msg = f"{ce.INLINE_NOT_EXPANDED_MSG} (item {item!r})"
            raise ValueError(msg)
        term = item.term
        if isinstance(term, gsm.Literal):
            pattern = re.escape(term.value)
        elif isinstance(term, gsm.Regex):
            pattern = term.value
        else:
            return unsupported
        bounds = _item_bounds(item)
        if item.disposition != gsm.Disposition.INCLUDE:
            parts.append(f"(?:{pattern}){_QUANTIFIER_SUFFIX[bounds]}")
            continue
        if bounds != (1, 1):
            # TODO(ast-terminal-repeat-synthesis): split the text per occurrence instead.
            return unsupported
        if isinstance(term, gsm.Regex):
            group = f"{_GROUP_PREFIX}{len(pieces)}"
            parts.append(f"(?P<{group}>{pattern})")
            pieces.append(TerminalPiece(label=item.label, group=group))
        else:
            parts.append(f"(?:{pattern})")
            pieces.append(TerminalPiece(label=item.label, group=None))
    return TerminalPlan(index=index, pattern="".join(parts), pieces=tuple(pieces))


def _text_from_plan(index: int, items: gsm.Items, label: str) -> TerminalPlan:
    """How one alternative of a ``text_from:`` rule is rebuilt from the redirected text.

    Only the named label's item carries text, so the pattern is that item's own terminal and
    every other included item is a literal whose text comes back from the grammar.  An
    alternative whose items are not all top-level terminals cannot be rebuilt at all.
    """
    pattern: str | None = None
    pieces: list[TerminalPiece] = []
    for item in items.items:
        if item.disposition == gsm.Disposition.INLINE:
            msg = f"{ce.INLINE_NOT_EXPANDED_MSG} (item {item!r})"
            raise ValueError(msg)
        if item.disposition != gsm.Disposition.INCLUDE:
            continue
        term = item.term
        if isinstance(term, gsm.Literal):
            own = re.escape(term.value)
        elif isinstance(term, gsm.Regex):
            own = term.value
        else:
            return TerminalPlan(index=index, pattern=None, pieces=())
        if item.label == label:
            group = f"{_GROUP_PREFIX}{len(pieces)}"
            pattern = f"(?P<{group}>{own})"
            pieces.append(TerminalPiece(label=item.label, group=group))
        else:
            pieces.append(TerminalPiece(label=item.label, group=None))
    if pattern is None:
        return TerminalPlan(index=index, pattern=None, pieces=())
    return TerminalPlan(index=index, pattern=pattern, pieces=tuple(pieces))


@dataclasses.dataclass(frozen=True, slots=True)
class AstModel:
    grammar: gsm.Grammar
    nodes: Mapping[str, RuleNode]
    """Node form per non-trivia rule, in grammar order."""

    rule_type_names: Mapping[str, str]
    payload_classes: Mapping[str, PayloadClass]
    field_enums: Mapping[str, FieldEnum]
    value_enums: Mapping[str, ValueEnum]
    plans: Mapping[str, SynthesisPlan]
    """Synthesis plan per non-trivia rule, keyed by rule name."""

    custom_types: Mapping[str, CustomType] = dataclasses.field(default_factory=dict)
    """The rules a ``custom(...)`` statement hands to a user-written type."""

    transparent_types: Mapping[str, TransparentType] = dataclasses.field(default_factory=dict)
    """The rules ``transparent;`` erases, and the payload each one's use sites carry.

    Such a rule still has an entry in ``nodes`` — the converters need its shape — but emits no
    public type of its own; its conversion is a private helper the use sites call.
    """

    flattened_rules: frozenset[str] = frozenset()
    """The wrapper rules ``flatten;`` splices into the nodes that reference them.

    Like an erased rule such a wrapper keeps its entry in ``nodes``, because that is where its
    fields and their order live, but emits no public type: each use site carries the wrapper's
    fields directly and calls a private helper pair to cross the CST boundary.
    """

    cst_backpointers: bool = False
    """``option cst = true;`` — every node class carries the CST node it was converted from."""

    claimed_names: Mapping[str, str] = dataclasses.field(default_factory=dict)
    """Every module-level name generation reserves, mapped to a description of what claimed it.

    One table serves both backends and both shapes of name — types and functions — because a
    ``name:`` override can mint either into one Python module namespace.  Read-only: it is the
    record a claim already succeeded, which is what lets a test assert that every name an emitter
    writes was claimed.
    """

    rule_of_type: Mapping[str, str] = dataclasses.field(default_factory=dict)
    """Which rule emits under each generated type name.

    Erased and flattened rules emit no type of their own, so they have no entry — and their
    type name is free for another rule to claim.
    """


# --- Conversion analysis: sum dispatch -------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class DispatchPair:
    """One (label, child kind) a sum rule's labeled children can fall into."""

    label: str
    kind: str
    """The referenced rule's name, or ``grammar_shape.TEXT_KIND`` for a span child."""


@dataclasses.dataclass(frozen=True, slots=True)
class LabelBound:
    """How many children of one label an alternative accepts."""

    label: str
    pairs: tuple[int, ...]
    """The dispatch pairs whose counts add up to the label's occurrences here."""

    minimum: int
    maximum: float


@dataclasses.dataclass(frozen=True, slots=True)
class AltDispatch:
    """What one alternative requires of a node's per-pair child counts."""

    variant_index: int
    bounds: tuple[LabelBound, ...]
    """One per label the alternative carries; a label it accepts freely is left out."""

    forbidden: tuple[int, ...]
    """Pairs no child may occupy: a label the alternative omits, or a kind it cannot hold."""


@dataclasses.dataclass(frozen=True, slots=True)
class SumDispatch:
    """How a sum rule's converter recovers which alternative matched.

    The CST records no alternative, so the converter counts the node's labeled children per
    (label, kind) pair and takes the first alternative whose signature accepts those counts —
    the same test ``grammar_shape.AltSignature`` describes, laid out as a fixed table for a
    backend that counts into an array.
    """

    pairs: tuple[DispatchPair, ...]
    alternatives: tuple[AltDispatch, ...]


def sum_dispatch(node: SumNode) -> SumDispatch:
    """The dispatch table for one sum rule, its alternatives in grammar order."""
    pairs: list[DispatchPair] = []
    for variant in node.variants:
        for label, signature in variant.signature.labels.items():
            for kind in sorted(signature.kinds):
                pair = DispatchPair(label, kind)
                if pair not in pairs:
                    pairs.append(pair)
    index_of = {pair: index for index, pair in enumerate(pairs)}
    labels = list(dict.fromkeys(pair.label for pair in pairs))
    alternatives: list[AltDispatch] = []
    for position, variant in enumerate(node.variants):
        bounds: list[LabelBound] = []
        forbidden: list[int] = []
        for label in labels:
            own = [index_of[pair] for pair in pairs if pair.label == label]
            signature = variant.signature.labels.get(label)
            if signature is None:
                forbidden.extend(own)
                continue
            counted = tuple(index_of[pair] for pair in pairs if pair.label == label and pair.kind in signature.kinds)
            forbidden.extend(index for index in own if index not in counted)
            minimum, maximum = gshape.label_bounds(signature)
            if (minimum, maximum) != (0, math.inf):
                bounds.append(LabelBound(label=label, pairs=counted, minimum=minimum, maximum=maximum))
        alternatives.append(
            AltDispatch(variant_index=position, bounds=tuple(bounds), forbidden=tuple(sorted(forbidden)))
        )
    return SumDispatch(pairs=tuple(pairs), alternatives=tuple(alternatives))


# --- Synthesis analysis ----------------------------------------------------------------


class GuardKind(enum.Enum):
    """What a value must satisfy to occupy one item position."""

    NONE = "none"
    """Nothing: no rival position competes for the label's values."""

    NODE = "node"
    """The types a reference to the guard's rule can carry."""

    CONVERTIBLE = "convertible"
    """Whatever the guard rule's own reverse converter accepts."""

    TEXT = "text"
    """Any text value."""

    PATTERN = "pattern"
    """Text the position's own terminal matches."""

    LITERAL = "literal"
    """Exactly the position's own literal text."""


@dataclasses.dataclass(frozen=True, slots=True)
class Guard:
    """The test one item position applies to a value before taking it."""

    kind: GuardKind
    rule_name: str | None = None
    """The referenced rule, for a ``NODE`` or ``CONVERTIBLE`` guard."""

    pattern: str | None = None
    literal: str | None = None


NO_GUARD = Guard(GuardKind.NONE)


@dataclasses.dataclass(frozen=True, slots=True)
class SlotPlacement:
    """One item position of a run, with the guard deciding whether a value belongs to it."""

    slot: Slot
    guard: Guard


@dataclasses.dataclass(frozen=True, slots=True)
class SlotRun:
    """The item positions one loop serves, and how many of a label's values they take.

    ``slots`` are in grammar order; ``placements`` are in the order the guards are tested,
    which puts a boolean payload before an integer one.
    """

    position: int
    slots: tuple[Slot, ...]
    placements: tuple[SlotPlacement, ...]

    minimum: int
    """How many values the run must carry."""

    maximum: float
    """How many it may carry; ``math.inf`` when the grammar sets no bound."""

    reserve: int
    """How many of the label's values later positions still need."""

    @property
    def label(self) -> str | None:
        return self.slots[0].label

    @property
    def dispatched(self) -> bool:
        """Whether the run is a set of branches one loop routes each value between."""
        return len(self.slots) > 1


@dataclasses.dataclass(frozen=True, slots=True)
class GroupCheck:
    """What one sub-expression alternation demands of the values reaching it.

    The branches are mutually exclusive, so no position inside one may insist on a value:
    the bounds a position enforces are the fewest any branch demands, which is none for a
    label a sibling branch omits.  What is left to check is the group as a whole.
    """

    labels: tuple[str, ...]
    """The labels whose populated state the check reads, in a stable order."""

    branches: tuple[frozenset[str], ...]
    """The labels each branch carries, including the branches that carry none."""

    exclusive: frozenset[str]
    """Labels only this alternation can supply, which must therefore fit a single branch."""

    demanded: bool
    """Whether every branch needs a labeled value, so something must fill the group."""


def rival_signature(slot: Slot) -> tuple[object, ...]:
    """What one item position accepts, as the key deciding whether two positions are rivals.

    A regex position's own pattern is part of the answer: two branches of an alternation may
    share a label and a kind and still take different text, and telling them apart is what a
    dispatch run's content guards are for.  A labeled literal's text is deliberately left out
    — the AST records a bare position for it, so which literal a value came from is not
    recoverable and no guard could route it.
    """
    return (slot.kind, slot.rule_name, slot.pattern)


def mutually_exclusive(slot: Slot, other: Slot) -> bool:
    """Whether two positions belong to different branches of one alternation.

    Only one of them is ever taken, so neither has to leave the other any values.
    """
    return slot.group is not None and slot.group == other.group and slot.branch != other.branch


def run_minimum(run: Sequence[Slot]) -> int:
    """How many values a run of positions must carry: the fewest any single branch demands.

    The branches of an alternation are mutually exclusive, so a value placed in one is a value
    the others never wanted; a branch of the group that does not mention the label at all
    demands none of it, which is why a lone position inside an alternation cannot insist on
    anything.  Outside an alternation there is one branch and the answer is the position's own
    lower bound.
    """
    demands = dict.fromkeys(range(run[0].branch_count), 0)
    for slot in run:
        demands[slot.branch] += slot.minimum
    return min(demands.values())


def run_maximum(run: Sequence[Slot]) -> float:
    """How many values the run can carry: the most any single branch accepts."""
    totals: dict[int, float] = {}
    for slot in run:
        totals[slot.branch] = totals.get(slot.branch, 0) + slot.maximum
    return max(totals.values())


def instance_elements(model: AstModel, rule_name: str, seen: frozenset[str] = frozenset()) -> tuple[ElementType, ...]:
    """Every element type a value of ``rule_name``'s AST type can be.

    A sum contributes its variants' elements rather than its own name: a Python union alias is
    a plain string at runtime, so a nested sum has to be expanded for a type test against the
    outer one to be possible at all, and a Rust match over the payloads needs the same list.
    A fold expands to its operand's elements plus its chain link; an erased rule to whatever
    its payload is.
    """
    custom = model.custom_types.get(rule_name)
    if custom is not None:
        return (custom,)
    transparent = model.transparent_types.get(rule_name)
    if transparent is not None:
        return payload_elements(model, transparent, seen)
    node = model.nodes[rule_name]
    if isinstance(node, FoldNode):
        if rule_name in seen:
            return ()
        operands = payload_elements(model, node.operand.type.element, seen | {rule_name})
        return (*operands, NodeType(node.binary.name))
    if not isinstance(node, SumNode):
        return (NodeType(node.name),)
    if rule_name in seen:
        return ()
    elements: list[ElementType] = []
    for variant in node.variants:
        deeper = (
            (variant.payload,)
            if variant.payload_rule is None
            else instance_elements(model, variant.payload_rule, seen | {rule_name})
        )
        elements.extend(element for element in deeper if element not in elements)
    return tuple(elements)


def payload_elements(
    model: AstModel, element: ElementType, seen: frozenset[str] = frozenset()
) -> tuple[ElementType, ...]:
    """Every element type a value of ``element`` can be, for a type test.

    A field enum and a sum alias both stand for several concrete types, so both are expanded
    to the types behind them; a value enum is one type and stands alone.
    """
    if isinstance(element, CustomType):
        return (element,)
    if isinstance(element, TransparentType):
        if element.coercion is not None:
            return (element,)
        if element.rule_name in seen:
            return ()
        return payload_elements(model, element.payload, seen | {element.rule_name})
    if isinstance(element, NodeType):
        rule = model.rule_of_type.get(element.name)
        if rule is not None:
            return instance_elements(model, rule, seen)
        field_enum = model.field_enums.get(element.name)
        if field_enum is None:
            return (element,)
        elements: list[ElementType] = []
        for variant in field_enum.variants:
            deeper = payload_elements(model, variant.element, seen)
            elements.extend(member for member in deeper if member not in elements)
        return tuple(elements)
    return (element,)


def element_precedence(element: ElementType) -> int:
    """Where a value of ``element`` belongs in a chain of type tests; lower is tested first.

    A boolean is offered the value before an integer: Python's ``bool`` is a subclass of
    ``int``, so an integer test takes a ``True`` as the number 1 and then has no spelling to
    render it as.  The order is decided here so both backends dispatch identically.
    """
    return 0 if element == BOOL else 1


def rule_precedence(model: AstModel, rule_name: str) -> int:
    """Where the values of ``rule_name``'s AST type belong in a chain of type tests."""
    return min((element_precedence(element) for element in instance_elements(model, rule_name)), default=1)


def variant_test_order(model: AstModel, node: SumNode) -> tuple[SumVariant, ...]:
    """A sum's variants in the order its reverse converter tests them."""

    def rank(variant: SumVariant) -> int:
        return 1 if variant.payload_rule is None else rule_precedence(model, variant.payload_rule)

    return tuple(sorted(node.variants, key=rank))


def converter_guarded(element: ElementType) -> bool:
    """Whether an erased payload is told apart by its rule's terminal rather than its type.

    True for a payload that bottoms out in raw text or in a builtin ``type:`` coercion of it,
    however many erased rules the resolution walks through: the value is a plain string or
    number that a second erased rule can carry just as well, so what the rule's own terminal
    accepts is the only thing distinguishing them.  Every builtin renderer and the terminal
    validation behind it report a value they cannot take as an ``AstError``, which is what
    makes the converter safe to run as a probe.

    False for a ``type: custom(...)`` coercion: its rendering goes through the user's unparse
    function, which is written for the declared type and may do anything at all with a value of
    another.  False for a value enum or a node payload, which are concrete types already.
    """
    if not isinstance(element, TransparentType):
        return False
    if element.coercion is not None:
        return isinstance(element.coercion, BuiltinCoercion)
    return element.payload == TEXT or converter_guarded(element.payload)


def node_guard(model: AstModel, rule_name: str) -> Guard:
    """The guard admitting the values a labeled reference to ``rule_name`` can carry.

    Normally the referenced rule's own types.  A rule ``transparent;`` erased to a scalar the
    grammar's terminal is the only witness for has none — see :func:`converter_guarded` — and
    the rule's own reverse converter is the guard there instead.
    """
    transparent = model.transparent_types.get(rule_name)
    if transparent is not None and converter_guarded(transparent):
        return Guard(GuardKind.CONVERTIBLE, rule_name=rule_name)
    return Guard(GuardKind.NODE, rule_name=rule_name)


def _identities(payloads: Sequence[ElementType]) -> frozenset[tuple[str, str]]:
    """The type names, per backend, the values of a set of payloads occupy.

    This is what a type test actually distinguishes by, so two tests whose sets overlap
    cannot tell each other's values apart.
    """
    identities: set[tuple[str, str]] = set()
    for payload in payloads:
        identities |= _payload_identity(payload)
    return frozenset(identities)


def accepted_identities(model: AstModel, rule_name: str) -> frozenset[tuple[str, str]]:
    """The type names, per backend, a value reaching a reference to ``rule_name`` can occupy."""
    return _identities(instance_elements(model, rule_name))


def _dispatch_guard(model: AstModel, slot: Slot) -> Guard:
    """The guard one branch of a dispatch run applies.

    Content decides, not just type: a run's branches are told apart by what their terminals
    can match, so a bare text test would let a literal's branch swallow text meant for a regex
    branch and re-render it as the literal.
    """
    if slot.kind is SlotKind.NODE:
        return node_guard(model, slot.rule_name or "")
    if slot.kind is SlotKind.TEXT:
        return Guard(GuardKind.PATTERN, pattern=slot.pattern)
    return Guard(GuardKind.LITERAL, literal=slot.literal)


def _slot_guard(model: AstModel, slot: Slot, plan: AltPlan) -> Guard:
    """The guard a lone position applies, when the label has rival positions elsewhere.

    Sequential positions are served in grammar order, so a text position takes whatever text
    arrives and reports a terminal mismatch against its own pattern.  A literal position is the
    exception: it renders from the grammar, so taking anything but the literal's own text would
    silently replace the value.
    """
    siblings = [other for other in plan.slots if other.label == slot.label]
    if len({(other.kind, other.rule_name) for other in siblings}) < _RIVAL_SLOTS:
        return NO_GUARD
    if slot.kind is SlotKind.NODE:
        return node_guard(model, slot.rule_name or "")
    if slot.kind is SlotKind.TEXT:
        return Guard(GuardKind.TEXT)
    return Guard(GuardKind.LITERAL, literal=slot.literal)


def _slot_precedence(model: AstModel, slot: Slot) -> int:
    if slot.kind is not SlotKind.NODE:
        return 1
    return rule_precedence(model, slot.rule_name or "")


def _placements(model: AstModel, run: Sequence[Slot], plan: AltPlan) -> tuple[SlotPlacement, ...]:
    if len(run) == 1:
        return (SlotPlacement(slot=run[0], guard=_slot_guard(model, run[0], plan)),)
    ordered = sorted(run, key=lambda slot: _slot_precedence(model, slot))
    return tuple(SlotPlacement(slot=slot, guard=_dispatch_guard(model, slot)) for slot in ordered)


def _reserve(plan: AltPlan, run: Sequence[Slot], position: int) -> int:
    """How many of the label's values the positions after ``run`` still need.

    A rival branch of the same alternation reserves nothing: only one branch is ever taken.  A
    lone position also looks at what the later ones accept — two positions of different kinds
    do not compete for the same values — while a dispatch run stays content-blind, because its
    own branches have already sorted the values by what accepts them.
    """
    slot = run[0]
    later = plan.slots[position + len(run) :]
    signature = (slot.kind, slot.rule_name)
    return sum(
        1
        for other in later
        if other.label == slot.label
        and other.minimum >= 1
        and (len(run) > 1 or (other.kind, other.rule_name) == signature)
        and not mutually_exclusive(slot, other)
    )


def synthesis_runs(model: AstModel, plan: AltPlan) -> tuple[SlotRun, ...]:
    """One alternative's item positions, with each label's alternation branches grouped.

    A run of consecutive positions that share one label and one alternation group, and that do
    not all accept the same values, is served by a single per-value dispatch loop: the branches
    are mutually exclusive, so the label's values arrive in source order and any of them may
    occupy any branch.  Every other position is its own run.
    """
    runs: list[SlotRun] = []
    position = 0
    while position < len(plan.slots):
        slot = plan.slots[position]
        end = position + 1
        if slot.group is not None and slot.label is not None:
            while end < len(plan.slots) and plan.slots[end].group == slot.group and plan.slots[end].label == slot.label:
                end += 1
        if len({rival_signature(other) for other in plan.slots[position:end]}) < _RIVAL_SLOTS:
            end = position + 1
        run = tuple(plan.slots[position:end])
        runs.append(
            SlotRun(
                position=position,
                slots=run,
                placements=_placements(model, run, plan),
                minimum=run_minimum(run),
                maximum=run_maximum(run),
                reserve=_reserve(plan, run, position),
            )
        )
        position = end
    return tuple(runs)


@dataclasses.dataclass(frozen=True, slots=True)
class AcceptedKind:
    """One kind an alternative accepts at a label, and the test admitting its values.

    ``element`` is the field's own element type, which is the field enum variant holding it
    on a backend that tags its values; ``guard`` is the test a backend without tags applies
    to the value itself.
    """

    element: ElementType
    guard: Guard


@dataclasses.dataclass(frozen=True, slots=True)
class SelectionGuard:
    """The kinds one alternative's item positions accept at one label.

    A precondition on choosing that alternative: every value the label carries must be of a
    kind listed here.  ``accepted`` is in the order the kinds are tested, and is always a
    proper subset of what the field can hold — an alternative accepting everything the field
    holds constrains nothing and gets no guard at all.
    """

    label: str
    accepted: tuple[AcceptedKind, ...]


def field_elements(model: AstModel, field: Field) -> tuple[ElementType, ...]:
    """Every element type one field can hold, in declaration order.

    A label carrying more than one is typed by a field enum, whose variants are the union
    over the rule's alternatives; every other field holds its own element and nothing else.
    """
    element = field.type.element
    if isinstance(element, NodeType):
        field_enum = model.field_enums.get(element.name)
        if field_enum is not None:
            return tuple(variant.element for variant in field_enum.variants)
    return (element,)


def element_rule(model: AstModel, element: ElementType) -> str | None:
    """The rule whose values an element carries; ``None`` for a scalar."""
    if isinstance(element, CustomType | TransparentType):
        return element.rule_name
    if isinstance(element, NodeType):
        return model.rule_of_type.get(element.name)
    return None


def slot_element(model: AstModel, slot: Slot, elements: Sequence[ElementType]) -> ElementType | None:
    """Which of a field's element types one item position's values are.

    The single answer to that question: it decides both which alternative a value's kind lets
    a rule select and which field enum variant that alternative's body then reads it through,
    so the two cannot disagree about where a value belongs.

    ``None`` for a position that contributes no value to the field: an unlabeled terminal,
    or one whose element the field turns out not to hold, which no shape the model builds
    produces.  A caller wanting a variant treats that as the error it would be; one analysing
    a whole alternative treats it as unanalysable rather than as an empty answer.
    """
    if slot.kind is SlotKind.NODE:
        for element in elements:
            rule_name = element_rule(model, element)
            if rule_name is not None and rule_name == slot.rule_name:
                return element
        return None
    if slot.kind is SlotKind.TEXT:
        return TEXT if TEXT in elements else None
    if slot.kind is SlotKind.LITERAL:
        # A literal's own element is a bare position; a label mixing it with text or nodes
        # carries text instead, and one holding a lone optional literal carries presence.
        for candidate in (SPAN, TEXT, BOOL):
            if candidate in elements:
                return candidate
    return None


def _element_identities(model: AstModel, element: ElementType) -> frozenset[tuple[str, str]]:
    """The type names, per backend, a value of one field element can occupy."""
    return _identities(payload_elements(model, element))


def _kind_guard(model: AstModel, element: ElementType) -> Guard | None:
    """The test admitting the values of one field element, or ``None`` where none exists.

    The same guards a dispatch run's branches use, chosen the same way, so a value routed
    into an alternative here is one that alternative's item positions also accept.

    The element is all there is to go on, and a labeled literal's element is the same TEXT a
    regex position contributes, so an alternative whose only position for the label is a
    literal admits any text and then renders the literal.
    """
    # TODO(ast-select-literal-content): a literal-only accepted TEXT wants the literal's own
    # text as its test, on both backends.
    rule_name = element_rule(model, element)
    if rule_name is not None:
        return node_guard(model, rule_name)
    return Guard(GuardKind.TEXT) if element == TEXT else None


def _element_rank(model: AstModel, element: ElementType) -> int:
    """Where a field element belongs in a chain of type tests; lower is tested first."""
    return min((element_precedence(payload) for payload in payload_elements(model, element)), default=1)


def _kind_test_order(model: AstModel, elements: Sequence[ElementType]) -> list[ElementType]:
    """A field's element types in the order a chain of tests offers them a value.

    Selection offers a value every accepted kind and takes any of them, so this order does not
    decide which alternative wins; it is what keeps the two backends emitting one sequence, and
    it is the precedence a dispatch chain — where the first matching test does win — tests in.
    """
    return sorted(elements, key=lambda element: _element_rank(model, element))


def _distinguishable(model: AstModel, accepted: Sequence[AcceptedKind], excluded: Sequence[ElementType]) -> bool:
    """Whether both backends can tell the accepted kinds from the ones they exclude.

    A backend that tags its values reads the field enum variant, which is exact as long as
    the kinds have variants of their own.  A backend without tags tests the value, so two
    kinds that share a runtime type there are indistinguishable — unless the accepted one is
    told apart by its own converter, the probe rival item positions already dispatch on.
    Failing either question the answer is no on both, because a guard only one backend can
    evaluate would route one value two ways.

    What the probe answers is membership of the rule's terminal language, not identity, so two
    erased terminals whose languages overlap are separated by it only up to that overlap: a
    tagged backend routes an overlapping value by its tag, an untagged one by the first probe
    that accepts.  The two agree on every value a parse produced — the alternatives are tried
    in grammar order on both sides, which is the order the parse itself chose from — and
    differ only for a value hand-built with a tag an untagged backend has no spelling for.
    """
    excluded_variants = {_field_enum_variant_name(element) for element in excluded}
    excluded_identities = frozenset(
        identity for element in excluded for identity in _element_identities(model, element)
    )
    for kind in accepted:
        if _field_enum_variant_name(kind.element) in excluded_variants:
            return False
        if kind.guard.kind is GuardKind.CONVERTIBLE:
            continue
        if _element_identities(model, kind.element) & excluded_identities:
            return False
    return True


def selection_guards(model: AstModel, fields: Sequence[Field], plan: AltPlan) -> tuple[SelectionGuard, ...]:
    """What one alternative demands of the *kinds* its populated fields carry.

    Which alternative of a multi-alternative rule can rebuild a value is decided by the
    labels the value populates, and label names under-determine it: alternatives that label
    their positions identically but accept different kinds are indistinguishable that way, so
    the first one wins and the rest can render nothing.  The value itself carries what is
    missing, and this is the analysis that reads it — one guard per label whose positions in
    this alternative accept fewer kinds than the field can hold.

    A label whose positions accept everything the field holds gets no guard: the test would
    be vacuous, and its absence is what keeps every shape that is discriminated by names
    alone generating exactly the code it did before.  So does a label whose kinds one backend
    cannot tell apart, which degrades to the name-only choice rather than to two backends
    disagreeing.  Hoisted fields are left out — a flattened wrapper occupies one position and
    places its own fields — as are labels this alternative does not carry at all, which the
    name test already rules out.
    """
    guards: list[SelectionGuard] = []
    for field in fields:
        if field.hoist is not None or field.label not in plan.labels:
            continue
        elements = field_elements(model, field)
        if len(elements) < _RIVAL_SLOTS:
            continue
        slots = [slot for slot in plan.slots if slot.label == field.label]
        resolved = [slot_element(model, slot, elements) for slot in slots]
        if not resolved or any(element is None for element in resolved):
            continue
        accepted = _dedupe([element for element in resolved if element is not None])
        if len(accepted) == len(elements):
            continue
        tests: list[AcceptedKind] = []
        for element in _kind_test_order(model, accepted):
            guard = _kind_guard(model, element)
            if guard is None:
                break
            tests.append(AcceptedKind(element=element, guard=guard))
        if len(tests) != len(accepted):
            continue
        excluded = [element for element in elements if element not in accepted]
        if not _distinguishable(model, tests, excluded):
            continue
        guards.append(SelectionGuard(label=field.label, accepted=tuple(tests)))
    return tuple(guards)


def resolve_goal_rule(model: AstModel, goal_rule: str | None) -> str:
    """The rule the generated conveniences target; the grammar's first rule by default.

    A ``custom(...)`` first rule is still the default: marking a rule custom must not silently
    move the goal to the second.  A flattened rule is the exception — it has no type at all, so
    there is nothing for the conveniences to take or return.
    """
    if goal_rule is None:
        for rule in model.grammar.rules:
            if rule.is_trivia_rule or rule.name in model.flattened_rules:
                continue
            if rule.name in model.nodes or rule.name in model.custom_types:
                return rule.name
        msg = "the grammar has no rule with an AST type, so there is no goal rule to default to"
        raise ValueError(msg)
    if goal_rule in model.flattened_rules:
        msg = (
            f"goal rule '{goal_rule}' is flattened into its use sites, so it has no AST type of its "
            f"own; drop `flatten;` from it, or name another goal rule"
        )
        raise ValueError(msg)
    if goal_rule not in model.nodes and goal_rule not in model.custom_types:
        available = ", ".join((*model.nodes, *model.custom_types))
        msg = f"goal rule '{goal_rule}' has no AST node; available rules: {available}"
        raise ValueError(msg)
    return goal_rule


def generated_payload(model: AstModel, variant: SumVariant) -> PayloadClass | None:
    """The payload class a sum generates for ``variant``; ``None`` for a direct payload."""
    if variant.payload_rule is not None or not isinstance(variant.payload, NodeType):
        return None
    return model.payload_classes.get(variant.payload.name)


def coercions(model: AstModel) -> tuple[Coercion, ...]:
    """Every ``type:`` coercion the model carries, in rule order."""
    return tuple(
        node.coercion for node in model.nodes.values() if isinstance(node, TerminalNode) and node.coercion is not None
    )


def populated_directly(field: Field) -> bool:
    """Whether a field's own value already answers "is this populated".

    A presence flag does: its ``False`` means the optional literal was absent.  Every other
    field needs asking, because a field whose own value is a boolean — a rule ``bool:`` maps
    and ``transparent;`` erases — carries ``False`` as data, and reading that as absent leaves
    a populated alternative fitting nothing.
    """
    return field.type.element == BOOL and field.type.container is Container.SINGLE


def hoist_always_present(hoist: Hoist) -> bool:
    """Whether a flattened wrapper's label is there whatever the hoisted fields hold.

    A required wrapper is rebuilt unconditionally, so reading its presence off the hoisted
    values would make a legitimately empty wrapper look absent and leave no alternative
    fitting.  Only an optional wrapper collapses when nothing it carries is populated.
    """
    return not hoist.optional


def group_checks(plan: AltPlan, fields: Sequence[Field], hoists: Sequence[Hoist]) -> tuple[GroupCheck, ...]:
    """What each sub-expression alternation of one alternative demands of the values.

    A group with a label that has neither a field nor a flattened wrapper behind it is skipped:
    nothing records whether that label is populated, so the group cannot be checked at all.
    """
    by_label = {field.label: field for field in fields if field.hoist is None}
    hoisted = {hoist.label for hoist in hoists}
    checks: list[GroupCheck] = []
    for group in sorted({slot.group for slot in plan.slots if slot.group is not None}):
        slots = [slot for slot in plan.slots if slot.group == group]
        labels = sorted({slot.label for slot in slots if slot.label is not None})
        if not labels or any(label not in by_label and label not in hoisted for label in labels):
            continue
        branches = tuple(
            frozenset(slot.label for slot in slots if slot.branch == branch and slot.label is not None)
            for branch in range(slots[0].branch_count)
        )
        # A branch whose required items are all unlabeled renders with nothing populated.
        demanded = all(
            any(slot.minimum >= 1 and slot.label is not None for slot in slots if slot.branch == branch)
            for branch in range(slots[0].branch_count)
        )
        # A repeatable group may draw one label's values from several branches in turn, and a
        # label the alternative also uses outside the group may be populated from there.  The
        # bound that decides this is the group's own, not the slots': a starred item inside one
        # branch of a group that occurs once is still one branch's worth of values.
        outside = {slot.label for slot in plan.slots if slot.group != group}
        exclusive = (
            frozenset(label for label in labels if label not in outside) if slots[0].group_maximum <= 1 else frozenset()
        )
        if not demanded and not exclusive:
            continue
        checks.append(GroupCheck(labels=tuple(labels), branches=branches, exclusive=exclusive, demanded=demanded))
    return tuple(checks)


# --- Recursion analysis ----------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class Recursion:
    """Where the generated type graph closes a cycle on itself.

    A backend that embeds a node's children *by value* — Rust — has to indirect every edge whose
    target can reach the edge's owner again, or the type would have no finite size.  ``boxed``
    holds those ``(owner, target)`` type-name pairs; ``deep`` names the types whose values nest to
    a depth nothing in the grammar bounds, so their teardown and their comparison must not
    recurse.  Python needs neither answer: its containers are references and its recursion limit
    raises rather than aborting.
    """

    boxed: frozenset[tuple[str, str]]
    deep: frozenset[str]

    def is_boxed(self, owner: str, target: str) -> bool:
        """Whether the edge from ``owner`` to ``target`` needs an indirection."""
        return (owner, target) in self.boxed


def embedded_types(element: ElementType) -> tuple[str, ...]:
    """The generated types one element holds by value.

    A scalar, a coerced value and a ``custom(...)`` rule's user type hold none: the first two are
    not generated types at all, and the third is opaque — the generator does not know its shape,
    so it cannot place it in a cycle.
    """
    if isinstance(element, TransparentType):
        if element.coercion is not None:
            return ()
        return embedded_types(element.payload)
    if isinstance(element, NodeType):
        return (element.name,)
    return ()


def _field_targets(field: Field) -> tuple[str, ...]:
    """The types a field embeds by value; a container is an indirection and embeds nothing."""
    if field.type.container in (Container.COLLECTION, Container.MAP):
        return ()
    return embedded_types(field.type.element)


def type_graph(model: AstModel) -> Mapping[str, frozenset[str]]:
    """Every generated type, mapped to the types it embeds by value.

    ``Vec`` and map fields contribute no edge, and neither do the fold link's ``lhs``/``rhs``: both
    are indirections already, so a cycle running through one is finite by construction.  An erased
    or flattened rule contributes nothing of its own — its payload and its fields turn up at the
    use sites instead — while the value and field enums built for such a rule are real types and
    do appear.
    """
    edges: dict[str, set[str]] = {name: set() for name in (*model.value_enums, *model.field_enums)}
    for payload in model.payload_classes.values():
        edges.setdefault(payload.name, set()).update(
            target for field in payload.fields for target in _field_targets(field)
        )
    for field_enum in model.field_enums.values():
        edges[field_enum.name].update(
            target for variant in field_enum.variants for target in embedded_types(variant.element)
        )
    for rule_name, node in model.nodes.items():
        if rule_name in model.transparent_types or rule_name in model.flattened_rules:
            continue
        targets = edges.setdefault(node.name, set())
        if isinstance(node, ProductNode):
            targets.update(target for field in node.fields for target in _field_targets(field))
        elif isinstance(node, EnumNode):
            if node.bool_truthy is None:
                targets.add(node.value_enum.name)
        elif isinstance(node, SumNode):
            targets.update(target for variant in node.variants for target in embedded_types(variant.payload))
        elif isinstance(node, FoldNode):
            targets.update(embedded_types(node.operand.type.element))
            targets.add(node.binary.name)
            edges.setdefault(node.binary.name, set()).update(_field_targets(node.binary.op))
    # A target outside the graph is a type this model does not generate, so it can be in no cycle.
    return {owner: frozenset(target for target in targets if target in edges) for owner, targets in edges.items()}


def _strongly_connected(graph: Mapping[str, frozenset[str]]) -> dict[str, frozenset[str]]:
    """Each type mapped to its strongly connected component (Tarjan, with an explicit stack).

    The walk is iterative rather than recursive because the graph is as deep as the grammar is,
    and a grammar is user input.
    """
    order = itertools.count()
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    pending: list[str] = []
    on_stack: set[str] = set()
    components: dict[str, frozenset[str]] = {}

    def visit(node: str) -> None:
        index[node] = low[node] = next(order)
        pending.append(node)
        on_stack.add(node)

    for root in graph:
        if root in index:
            continue
        visit(root)
        work: list[tuple[str, Iterator[str]]] = [(root, iter(sorted(graph[root])))]
        while work:
            node, children = work[-1]
            descended = False
            for child in children:
                if child not in index:
                    visit(child)
                    work.append((child, iter(sorted(graph[child]))))
                    descended = True
                    break
                if child in on_stack:
                    low[node] = min(low[node], index[child])
            if descended:
                continue
            work.pop()
            if low[node] == index[node]:
                members: list[str] = []
                while True:
                    member = pending.pop()
                    on_stack.discard(member)
                    members.append(member)
                    if member == node:
                        break
                component = frozenset(members)
                for member in members:
                    components[member] = component
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[node])
    return components


def recursion(model: AstModel) -> Recursion:
    """Which by-value edges of ``model``'s types need indirection, and which types nest deeply.

    An edge is indirected exactly when its target is in the same strongly connected component as
    its owner.  That boxes some edges a hand-writer would leave direct, but it is uniform and
    order-free: a minimal feedback-edge set would make the public field types depend on the order
    the rules happen to be visited in.

    A type is ``deep`` when it belongs to a component of more than one type or embeds itself, and
    every fold rule's enum and chain link unconditionally: the boxing pass deliberately ignores
    the link's own ``lhs``/``rhs`` indirections, yet a chain is as deep as the operand count, so
    the parser's nesting limit bounds nothing there.
    """
    graph = type_graph(model)
    components = _strongly_connected(graph)
    boxed = frozenset(
        (owner, target)
        for owner, targets in graph.items()
        for target in targets
        if components[owner] == components[target]
    )
    deep = {name for name, targets in graph.items() if len(components[name]) > 1 or name in targets}
    for node in model.nodes.values():
        if isinstance(node, FoldNode):
            deep.update((node.name, node.binary.name))
    return Recursion(boxed=boxed, deep=frozenset(deep))


def _element_carries_span(element: ElementType, bearing: frozenset[str] | set[str]) -> bool:
    if isinstance(element, TransparentType):
        if element.coercion is not None:
            return False
        return _element_carries_span(element.payload, bearing)
    if isinstance(element, NodeType):
        return element.name in bearing
    return False


def span_bearing(model: AstModel) -> frozenset[str]:
    """The generated types every value of which carries a span.

    Every generated struct does, by construction.  Every enum over payloads — a sum, a fold, a
    field enum — does only when *all* of its payloads do: an erased payload is a bare ``i64``, a
    value enum or a plain ``String`` and has no span.  So the answer is a greatest fixpoint over
    those enums: assume each carries one, then drop the ones a payload disproves until nothing
    changes, which is what makes a cycle of sums that bottom out in span-bearing structs come out
    span-bearing.  A value enum never bears a span: it is a bare discriminant.
    """
    payloads: dict[str, tuple[ElementType, ...]] = {
        field_enum.name: tuple(variant.element for variant in field_enum.variants)
        for field_enum in model.field_enums.values()
    }
    bearing: set[str] = {payload.name for payload in model.payload_classes.values()}
    for rule_name, node in model.nodes.items():
        if rule_name in model.transparent_types or rule_name in model.flattened_rules:
            continue
        if isinstance(node, SumNode):
            payloads[node.name] = tuple(variant.payload for variant in node.variants)
        elif isinstance(node, FoldNode):
            payloads[node.name] = (node.operand.type.element, NodeType(node.binary.name))
            bearing.add(node.binary.name)
        else:
            bearing.add(node.name)
    bearing |= set(payloads)
    changed = True
    while changed:
        changed = False
        for name, elements in payloads.items():
            if name in bearing and not all(_element_carries_span(element, bearing) for element in elements):
                bearing.discard(name)
                changed = True
    return frozenset(bearing)


# --- Teardown witnesses ----------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class ScalarWitness:
    """A witness value of an element that is not a generated type.

    ``element`` is a scalar, or the erasure carrying the ``type:`` builtin whose zero value the
    backend spells; the backends map each to their own cheapest literal.
    """

    element: ElementType


@dataclasses.dataclass(frozen=True, slots=True)
class EmptyWitness:
    """The witness of a container member: absent, or holding no elements at all."""

    container: Container


@dataclasses.dataclass(frozen=True, slots=True)
class UnitWitness:
    """The witness of a value enum: its first variant, which wraps nothing."""

    type_name: str
    variant: str


@dataclasses.dataclass(frozen=True, slots=True)
class MemberWitness:
    """One member of a witness struct: what it is called, what it holds, and its value.

    ``element`` is kept beside the value because a backend that embeds children by value reaches
    some of them through an indirection, and which ones is that backend's own answer.
    """

    name: str
    element: ElementType
    value: Witness


@dataclasses.dataclass(frozen=True, slots=True)
class StructWitness:
    """The witness of a generated struct: one per member, plus the span every struct carries."""

    type_name: str
    members: tuple[MemberWitness, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class VariantWitness:
    """The witness of a generated enum: the first of its variants a witness reaches."""

    type_name: str
    variant: str
    element: ElementType
    payload: Witness


Witness: TypeAlias = ScalarWitness | EmptyWitness | UnitWitness | StructWitness | VariantWitness

_WitnessBuilder: TypeAlias = Callable[[Mapping[str, Witness]], Witness | None]


def _element_witness(element: ElementType, known: Mapping[str, Witness]) -> Witness | None:
    """A witness value of one element, or ``None`` where nothing can construct one yet.

    A ``custom(...)`` rule and a ``type: custom(...)`` coercion are permanently ``None``: the
    generator knows nothing about the user's type, so it can name no value of it.
    """
    if isinstance(element, ScalarType):
        return ScalarWitness(element)
    if isinstance(element, CustomType):
        return None
    if isinstance(element, TransparentType):
        if element.coercion is None:
            return _element_witness(element.payload, known)
        return ScalarWitness(element) if isinstance(element.coercion, BuiltinCoercion) else None
    return known.get(element.name)


def _struct_builder(type_name: str, members: Sequence[tuple[str, ElementType, Container]]) -> _WitnessBuilder:
    """A struct's witness: every required-single member's own, containers left empty."""

    def build(known: Mapping[str, Witness]) -> Witness | None:
        built: list[MemberWitness] = []
        for name, element, container in members:
            value = EmptyWitness(container) if container is not Container.SINGLE else _element_witness(element, known)
            if value is None:
                return None
            built.append(MemberWitness(name=name, element=element, value=value))
        return StructWitness(type_name=type_name, members=tuple(built))

    return build


def _enum_builder(type_name: str, variants: Sequence[tuple[str, ElementType]]) -> _WitnessBuilder:
    """An enum's witness: the first variant whose payload already has one."""

    def build(known: Mapping[str, Witness]) -> Witness | None:
        for variant, element in variants:
            payload = _element_witness(element, known)
            if payload is not None:
                return VariantWitness(type_name=type_name, variant=variant, element=element, payload=payload)
        return None

    return build


def _value_enum_builder(value_enum: ValueEnum) -> _WitnessBuilder:
    """A value enum's witness: its first variant, which needs nothing else."""

    def build(_known: Mapping[str, Witness]) -> Witness | None:
        if not value_enum.variants:
            return None
        return UnitWitness(type_name=value_enum.name, variant=value_enum.variants[0].name)

    return build


def _node_members(node: RuleNode) -> Sequence[tuple[str, ElementType, Container]] | None:
    """The members a rule node's witness has to fill, or ``None`` for the enum-shaped forms."""
    if isinstance(node, ProductNode):
        return [(field.name, field.type.element, field.type.container) for field in node.fields]
    if isinstance(node, TerminalNode):
        if node.coercion is None:
            return [("text", TEXT, Container.SINGLE)]
        coerced = TransparentType(rule_name=node.rule_name, payload=TEXT, coercion=node.coercion)
        return [("value", coerced, Container.SINGLE)]
    if isinstance(node, EnumNode):
        if node.bool_truthy is not None:
            return [("value", BOOL, Container.SINGLE)]
        return [("value", NodeType(node.value_enum.name), Container.SINGLE)]
    return None


def _witness_builders(model: AstModel) -> dict[str, _WitnessBuilder]:
    """One builder per generated type, in the order the fixpoint offers them a turn.

    A fold rule's chain link is deliberately absent.  Nothing but the fold enum's own link variant
    holds one, and that variant can never be the enum's witness — a link needs the enum's witness
    for both of its sides, so the enum has one first — which is what makes a fold's witness always
    a bare operand and so keeps the emitted teardown's own sentinel cheap.
    """
    builders: dict[str, _WitnessBuilder] = {}
    for value_enum in model.value_enums.values():
        builders[value_enum.name] = _value_enum_builder(value_enum)
    for field_enum in model.field_enums.values():
        builders[field_enum.name] = _enum_builder(
            field_enum.name, [(variant.name, variant.element) for variant in field_enum.variants]
        )
    for payload in model.payload_classes.values():
        builders[payload.name] = _struct_builder(
            payload.name, [(field.name, field.type.element, field.type.container) for field in payload.fields]
        )
    for rule_name, node in model.nodes.items():
        if rule_name in model.transparent_types or rule_name in model.flattened_rules:
            continue
        if isinstance(node, SumNode):
            builders[node.name] = _enum_builder(
                node.name, [(variant.name, variant.payload) for variant in node.variants]
            )
        elif isinstance(node, FoldNode):
            builders[node.name] = _enum_builder(
                node.name,
                [
                    (node.operand_variant, node.operand.type.element),
                    (node.binary_variant, NodeType(node.binary.name)),
                ],
            )
        else:
            members = _node_members(node)
            assert members is not None
            builders[node.name] = _struct_builder(node.name, members)
    return builders


def witnesses(model: AstModel) -> Mapping[str, Witness]:
    """A cheap constructible value per generated type, for those that have one.

    A backend that owns its children by value cannot move one out of a required member without
    writing something back, so tearing a chain down through a worklist instead of by recursion
    needs a sentinel of the chain's own type.  The generator owns the whole type graph, so it can
    name one: a plan is a construction-expression tree over scalars, empty containers, first
    variants and struct members, and each backend spells its own literals.

    The table is a least fixpoint: a type is offered a turn once per round and takes a witness as
    soon as everything it needs already has one, so every sub-witness was built in an earlier
    round and no plan can refer to itself.  A cycle with no constructible exit therefore has no
    entry at all — which is also the honest answer, since such a type has no finite values either.
    A type whose only path runs through a ``custom(...)`` rule or coercion has none for the same
    reason: the generator can name no value of a type it knows nothing about.
    """
    known: dict[str, Witness] = {}
    builders = _witness_builders(model)
    changed = True
    while changed:
        changed = False
        for type_name, build in builders.items():
            if type_name in known:
                continue
            witness = build(known)
            if witness is not None:
                known[type_name] = witness
                changed = True
    return known


def fold_witnesses(model: AstModel) -> Mapping[str, Witness]:
    """The teardown witness of each fold rule that has one, keyed by rule name."""
    table = witnesses(model)
    return {
        rule_name: table[node.name]
        for rule_name, node in model.nodes.items()
        if isinstance(node, FoldNode) and node.name in table
    }


# --- Model construction ----------------------------------------------------------------


class _ModelBuilder:
    def __init__(self, grammar: gsm.Grammar, config: ac.ResolvedAstConfig) -> None:
        self.grammar = grammar
        self.config = config
        self.errors: list[str] = []
        rules = [rule for rule in grammar.rules if not rule.is_trivia_rule]
        self.custom_types = {
            rule.name: CustomType(
                rule_name=rule.name,
                python=custom.entry("python"),
                rust=custom.entry("rust"),
            )
            for rule in rules
            if (custom := config.for_rule(rule.name).custom) is not None
        }
        self.reserved_fields = RESERVED_FIELD_NAMES | ({CST_FIELD_NAME} if config.cst_backpointers else frozenset())
        self.rules = [rule for rule in rules if rule.name not in self.custom_types]
        self.rules_by_name = {rule.name: rule for rule in self.rules}
        self.rule_type_names = {rule.name: self.type_name_for(rule.name) for rule in self.rules}
        self.transparent_rules = frozenset(rule.name for rule in self.rules if config.for_rule(rule.name).transparent)
        self.erasures: dict[str, TransparentType] = {}
        self.erasure_labels: dict[str, str] = {}
        self.map_keys: dict[str, MapKey] = {}
        self.fold_shapes: dict[str, tuple[str, str] | None] = {}
        self.flattened_rules: frozenset[str] = frozenset()
        self.product_shapes: dict[str, tuple[tuple[Field, ...], tuple[Hoist, ...]]] = {}
        self.flattening: set[str] = set()
        self.broken_wrappers: set[str] = set()
        self.unkeyed: set[str] = set()
        self.unresolvable: set[str] = set()
        self.resolving: set[str] = set()
        self.applied_field_renames: dict[str, set[str]] = {}
        self.forms: dict[str, gshape.RuleShape] = {}
        self.arities: dict[str, Sequence[Mapping[str, ce.LabelCount]]] = {}
        self.owners: dict[str, str] = {}
        self.nodes: dict[str, RuleNode] = {}
        self.payload_classes: dict[str, PayloadClass] = {}
        self.field_enums: dict[str, FieldEnum] = {}
        self.value_enums: dict[str, ValueEnum] = {}

    def error(self, message: str) -> None:
        self.errors.append(message)

    def type_name_for(self, rule_name: str) -> str:
        """The rule's generated type name: the ``name:`` override, else the camel-cased rule."""
        override = self.config.for_rule(rule_name).type_name
        return override if override is not None else naming.snake_to_upper_camel(rule_name)

    def claim_name(self, name: str, description: str) -> bool:
        """Claim one generated module-level name, reporting a second claimant.

        Types and functions share one table.  A generated type and a generated function
        occupy the same module namespace in Python, and the names a rename can produce are
        not restricted to one shape, so the two cannot be checked apart.
        """
        owner = self.owners.get(name)
        if owner is not None:
            self.error(
                f"Generated name {name!r} for {description} collides with {owner}; rename one of "
                f"them with `rule <rule> {{ name: <NewName>; }}`, `variant <computed>: <NewName>;` "
                f"or `field <label> {{ name: <new>; }}`"
            )
            return False
        self.owners[name] = description
        return True

    def claim_type_name(self, name: str, description: str) -> bool:
        return self.claim_name(name, description)

    def claim_converter_names(self) -> None:
        """Claim the module-level converters, whose names derive from rule and type names.

        Two different generated things can spell one converter: an erased rule ``foo`` and a
        field enum ``ErasedFoo`` both want ``_erased_foo_from_cst``, and whichever the emitter
        writes second silently wins.  The names run through the same table the types do.
        """
        for rule in self.rules:
            if rule.name in self.flattened_rules:
                names = flat_converter_names(rule.name)
                description = f"the private converters of the flattened rule {rule.name!r}"
            elif rule.name in self.erasures:
                names = erased_converter_names(rule.name)
                description = f"the private converters of the erased rule {rule.name!r}"
            else:
                names = converter_names(rule.name)
                description = f"the converters of rule {rule.name!r}"
            for name in names:
                self.claim_name(name, description)
        for enum_name, field_enum in self.field_enums.items():
            self.claim_name(
                field_enum_converter_name(enum_name),
                f"the converter of the {field_enum.label!r} field enum of rule {field_enum.rule_name!r}",
            )
        for name in ENTRY_POINTS:
            self.claim_name(name, f"the module-level `{name}()` entry point")
        self.claim_name(EQ_SUPPORT_MODULE, f"the Rust `{EQ_SUPPORT_MODULE}` equality-walk module")

    def imported_paths(self) -> Iterator[tuple[str, str]]:
        """Each dotted Python path a generated module names, with what asks for it.

        The module references a user type by its whole path and imports everything before the
        last component, so the path's head is a name the module binds.
        """
        for custom in self.custom_types.values():
            if custom.python is not None:
                yield custom.python, f"the `custom(...)` type of rule {custom.rule_name!r}"
        for rule_name, node in self.nodes.items():
            if not isinstance(node, TerminalNode) or node.coercion is None:
                continue
            if isinstance(node.coercion, CustomCoercion):
                for entry in ("type", "parse", "unparse"):
                    path = getattr(node.coercion, f"python_{entry}")
                    if path is not None:
                        yield path, f"the `type: custom(...)` {entry} of rule {rule_name!r}"
            else:
                name = node.coercion.name
                yield PYTHON_SCALAR_TYPES[name], f"the `type: {name}` coercion of rule {rule_name!r}"

    def referenced_rust_paths(self) -> Iterator[tuple[str, str]]:
        """Each ``::``-separated Rust path a generated module names, with what asks for it.

        Rust has no import to bind: the path is written inline, and its head is resolved against
        the module's own items first, so the head is a module-level name the module depends on.
        """
        for custom in self.custom_types.values():
            if custom.rust is not None:
                yield custom.rust, f"the `custom(...)` type of rule {custom.rule_name!r}"
        for rule_name, node in self.nodes.items():
            if not isinstance(node, TerminalNode) or not isinstance(node.coercion, CustomCoercion):
                continue
            for entry in ("type", "parse", "unparse"):
                path = getattr(node.coercion, f"rust_{entry}")
                if path is not None:
                    yield path, f"the `type: custom(...)` {entry} of rule {rule_name!r}"

    def claim_import_names(self) -> None:
        """Claim every module-level name a generated module binds or resolves a path through.

        The fixed aliases are the same whatever the grammar; the rest is the head of each path a
        ``custom(...)`` entry or a wide-scalar coercion makes the module name.  A rule renamed
        onto one of them shadows the import with a class — or, on Rust, wins the path's first
        segment and leaves rustc reporting a missing associated item — which is the same silent
        clobber a rename onto a converter would be.  Both backends' heads run through one dict, so
        a ``custom(...)`` whose two spellings share a head claims it once rather than colliding
        with itself.
        """
        for name in MODULE_IMPORT_NAMES:
            self.claim_name(name, f"the `{name}` a generated module's imports bind")
        heads: dict[str, str] = {}
        for path, origin in self.imported_paths():
            head, dot, _rest = path.partition(".")
            if dot and head not in MODULE_IMPORT_NAMES:
                heads.setdefault(head, f"the `import {head}` the Python module needs for {origin}")
        for path, origin in self.referenced_rust_paths():
            head, separator, _rest = path.partition("::")
            if separator and head and head not in RUST_PATH_ROOTS and head not in MODULE_IMPORT_NAMES:
                heads.setdefault(head, f"the `{head}` the Rust module's path for {origin} resolves through")
        for head, description in heads.items():
            self.claim_name(head, description)

    def claim_alternative_names(self) -> None:
        """Claim the per-alternative halves of the two private reverse helpers.

        A ``transparent;`` product and a ``flatten;`` wrapper with more than one alternative each
        get one helper per alternative.  The spellings derive from an already-claimed name but are
        names of their own: a rename spelled ``_flat_wrap_to_cst_alt0`` collides with the helper,
        and the function definition would overwrite the class with no diagnostic.
        """
        for rule in self.rules:
            if len(rule.alternatives) < _MIN_ALTERNATIVES:
                continue
            if rule.name in self.flattened_rules:
                spelling, kind = flat_alt_converter_name, "flattened"
            elif rule.name in self.erasures and isinstance(self.nodes.get(rule.name), ProductNode):
                spelling, kind = erased_alt_converter_name, "erased"
            else:
                continue
            description = f"the per-alternative reverse helpers of the {kind} rule {rule.name!r}"
            for index in range(len(rule.alternatives)):
                self.claim_name(spelling(rule.name, index), description)

    def claim_witness_names(self) -> None:
        """Claim each fold rule's teardown witness, whether or not one turns out constructible."""
        for rule_name, node in self.nodes.items():
            if isinstance(node, FoldNode):
                self.claim_name(drop_witness_name(rule_name), f"the teardown witness of fold rule {rule_name!r}")

    def claim_dispatch_names(self) -> None:
        """Claim each sum rule's alternative-dispatch function."""
        for rule_name, node in self.nodes.items():
            if isinstance(node, SumNode):
                self.claim_name(
                    alternative_dispatch_name(rule_name), f"the alternative dispatch of sum rule {rule_name!r}"
                )

    def claim_constant_names(self) -> None:
        """Claim the per-rule module constants the converters read.

        Each spelling derives from the rule name by a fixed uppercase transform, and rule names
        are lowercase, so two rules cannot want one constant.  A ``name:`` rename can: the
        renamed class and the constant then occupy one module-level name, and the assignment
        wins at module exec, leaving every use of the type broken with no diagnostic.
        """
        for rule_name, node in self.nodes.items():
            claims: list[tuple[str, str]] = []
            if isinstance(node, SumNode | FoldNode):
                claims.append((payload_constant_name(rule_name), f"the payload table of rule {rule_name!r}"))
            if isinstance(node, SumNode):
                claims.append((signature_constant_name(rule_name), f"the alternative signatures of rule {rule_name!r}"))
            if isinstance(node, TerminalNode):
                claims.append((terminal_constant_name(rule_name), f"the terminal patterns of rule {rule_name!r}"))
            for name, description in claims:
                self.claim_name(name, description)

    def build(self) -> AstModel:
        self.resolve_flattened()
        for rule in self.rules:
            # An erased or flattened rule emits no type under its own name, so the name stays
            # unclaimed and another rule may take it.  Its derived names (the value enum of an
            # enum-shaped rule, a field enum of a single-field product) are still claimed where
            # they are built, because those types *are* emitted.
            if rule.name not in self.transparent_rules and rule.name not in self.flattened_rules:
                self.claim_type_name(self.rule_type_names[rule.name], f"rule {rule.name!r}")

        # Erasures are resolved before any field is typed: a use site of an erased rule carries
        # its payload, and resolving that payload can walk further erased rules.
        for rule in self.rules:
            if rule.name in self.transparent_rules:
                self.erasure(rule.name)

        for rule in self.rules:
            self.nodes[rule.name] = self.build_rule(rule)
        self.check_field_renames_applied()
        self.claim_converter_names()
        self.claim_import_names()
        self.claim_alternative_names()
        self.claim_witness_names()
        self.claim_dispatch_names()
        self.claim_constant_names()
        # Built before the collected errors are raised: composing a rule's terminals into one
        # synthesis pattern is itself a check.
        plans = self.build_plans()

        if self.errors:
            raise AstModelError(self.errors)

        model = AstModel(
            grammar=self.grammar,
            nodes=self.nodes,
            rule_type_names=self.rule_type_names,
            payload_classes=self.payload_classes,
            field_enums=self.field_enums,
            value_enums=self.value_enums,
            plans=plans,
            custom_types=self.custom_types,
            transparent_types=dict(self.erasures),
            flattened_rules=self.flattened_rules,
            cst_backpointers=self.config.cst_backpointers,
            claimed_names=dict(self.owners),
            rule_of_type={
                type_name: rule
                for rule, type_name in self.rule_type_names.items()
                if rule not in self.erasures and rule not in self.flattened_rules
            },
        )
        # The dispatch guards are decided against the finished model, so this one check runs
        # after it is assembled rather than while the nodes are built.
        self.check_dispatch_guards(model)
        if self.errors:
            raise AstModelError(self.errors)
        return model

    def check_dispatch_guards(self, model: AstModel) -> None:
        """Reject two branches of an alternation whose values cannot be told apart.

        A dispatch loop routes one label's values by what each branch accepts.  Where two
        branches are guarded by type tests over the same types — two rules ``bool:`` maps and
        ``transparent;`` erases both carry a bare boolean, two ``custom(...)`` rules may name
        one user class — every value lands in whichever branch is tested first, and the AST
        records nothing that could have routed it: text written under one rule of the grammar
        comes back as the other rule's literal.
        """
        for rule_name, plan in model.plans.items():
            for alternative in plan.alternatives:
                for run in synthesis_runs(model, alternative):
                    if run.dispatched:
                        self.check_run_guards(rule_name, run, model)

    def check_run_guards(self, rule_name: str, run: SlotRun, model: AstModel) -> None:
        """Report the first pair of type-tested branches of one run that overlap."""
        typed = [
            (placement.guard.rule_name or "", accepted_identities(model, placement.guard.rule_name or ""))
            for placement in run.placements
            if placement.guard.kind is GuardKind.NODE
        ]
        for index, (name, identities) in enumerate(typed):
            for other, other_identities in typed[index + 1 :]:
                shared = identities & other_identities
                # Two positions referencing one rule append the same child either way, so which
                # of them takes a value is not observable.
                if name == other or not shared:
                    continue
                names = ", ".join(sorted({shared_name for _backend, shared_name in shared}))
                self.error(
                    f"Rule {rule_name!r}: the {run.label!r} branches referencing {name!r} and "
                    f"{other!r} both carry {names}, so a value records nothing that says which "
                    f"branch it came from and the first branch would render every one of them; "
                    f"give the two branches distinguishable types — a `transparent;` rule carries "
                    f"its payload rather than a node of its own — or give each branch its own label"
                )
                return

    def check_field_renames_applied(self) -> None:
        """Every ``field <label> { name: }`` must have renamed a field that exists.

        The sidecar validator rejects the statement on a shape with no fields at all, but
        whether one *label* becomes a field is only known once the fields are built — a
        suppressed item contributes none, nor does a sum variant that carries the referenced
        rule's own type, nor a fold's operand, which becomes the chain's leaves.  A rename that
        reached nothing must say so rather than evaporate.
        """
        for rule_name, rule in self.config.rules.items():
            if rule_name in self.custom_types or rule_name not in self.rule_type_names:
                continue
            applied = self.applied_field_renames.get(rule_name, frozenset())
            for label in rule.field_names:
                if label not in applied:
                    self.error(
                        f"Rule {rule_name!r}: `field {label} {{ name: ... }}` renames no field of this "
                        f"rule — the label produces no field of its own (a suppressed item, a sum "
                        f"variant that carries the referenced rule's type, or a fold's operand); "
                        f"drop the statement"
                    )

    def check_terminal_pattern(self, rule_name: str, plan: TerminalPlan) -> None:
        """The pattern that rebuilds one alternative's text has to compile.

        Text synthesis spells a whole alternative as a single regex, wrapping each included
        regex item in a named group of its own.  That composition is an artifact nothing else
        has ever validated — the parser generators saw only the individual terminals — so a
        group name two of the rule's terminals both define, or one that collides with the
        generated prefix, would reach a regex engine only at the first serialize: a panic on
        the Rust backend, a raw ``re.error`` on the Python one.
        """
        if plan.pattern is None:
            return
        for name in _repeated_group_names(plan.pattern):
            self.error(
                f"Rule {rule_name!r}: the capture group {name!r} is defined more than once in the "
                f"pattern that rebuilds this rule's text, which no regex engine compiles — a named "
                f"group in a terminal-only rule must be unique across the alternative and must not "
                f"start with {_GROUP_PREFIX!r}; rename it, or make it non-capturing (`(?:...)`)"
            )

    def build_plans(self) -> dict[str, SynthesisPlan]:
        plans: dict[str, SynthesisPlan] = {}
        for rule in self.rules:
            terminals: tuple[TerminalPlan, ...] = ()
            node = self.nodes[rule.name]
            if isinstance(node, TerminalNode):
                redirect = node.text_from
                terminals = tuple(
                    _terminal_plan(index, alt) if redirect is None else _text_from_plan(index, alt, redirect)
                    for index, alt in enumerate(rule.alternatives)
                )
                for plan in terminals:
                    self.check_terminal_pattern(rule.name, plan)
            arities = self.rule_arities(rule)
            plans[rule.name] = SynthesisPlan(
                alternatives=tuple(
                    _alt_plan(index, alt, arities[index]) for index, alt in enumerate(rule.alternatives)
                ),
                terminals=terminals,
            )
        return plans

    def rule_arities(self, rule: gsm.Rule) -> Sequence[Mapping[str, ce.LabelCount]]:
        """Per-alternative label arities, walked once per rule and shared by every consumer."""
        cached = self.arities.get(rule.name)
        if cached is None:
            cached = [ce.arities_for_alternative(alternative, rule.name) for alternative in rule.alternatives]
            self.arities[rule.name] = cached
        return cached

    def alt_infos(self, rule: gsm.Rule) -> list[AltInfo]:
        return alt_infos(rule, self.rule_arities(rule))

    def build_rule(self, rule: gsm.Rule) -> RuleNode:
        type_name = self.rule_type_names[rule.name]
        fold = self.config.for_rule(rule.name).fold
        if fold is not None:
            self.check_recorded_terminals(rule)
            folded = self.build_fold_node(rule, type_name, fold)
            if folded is not None:
                return folded
            # The fold did not resolve and has been reported; the rule's own shape is the
            # least surprising thing to fall back to so the rest of the model still builds.
        form = self.rule_form(rule)

        if form is gshape.RuleShape.ENUM:
            return self.build_enum_node(rule, type_name)
        if form is gshape.RuleShape.TERMINAL:
            return self.build_terminal_node(rule, type_name)

        # Only the sum and product forms need the per-alternative label walk.
        self.check_recorded_terminals(rule)
        infos = self.alt_infos(rule)
        if form is gshape.RuleShape.SUM:
            return self.build_sum_node(rule, type_name, infos)
        if rule.name in self.transparent_rules:
            return self.build_erased_product(rule, type_name)
        return self.build_product_node(rule, type_name, infos)

    # --- `transparent;` erasure ----------------------------------------------------------

    def erasure(self, rule_name: str) -> TransparentType | None:
        """The payload a ``transparent;`` rule's use sites carry, or ``None`` if it has none.

        Memoized, including the failure: the payload is asked for once per use site, and a rule
        whose erasure does not resolve must be reported once rather than at every site.
        """
        cached = self.erasures.get(rule_name)
        if cached is not None:
            return cached
        if rule_name in self.unresolvable:
            return None
        if rule_name in self.resolving:
            # The sidecar validator rejects transparency cycles; this catches a hand-built config.
            self.error(
                f"Rule {rule_name!r}: `transparent;` never bottoms out — the rule's payload is "
                f"reached through itself; at least one rule in the cycle must keep a type of its own"
            )
            self.unresolvable.add(rule_name)
            return None
        self.resolving.add(rule_name)
        try:
            resolved = self.compute_erasure(rule_name)
        finally:
            self.resolving.discard(rule_name)
        if resolved is None:
            self.unresolvable.add(rule_name)
            return None
        self.erasures[rule_name] = resolved
        return resolved

    def compute_erasure(self, rule_name: str) -> TransparentType | None:
        rule = self.rules_by_name[rule_name]
        configured = self.config.for_rule(rule_name)
        if configured.fold is not None:
            self.error(
                f"Rule {rule_name!r}: `transparent;` cannot apply to a fold rule — a fold's type is the "
                f"choice between an operand and a chain link, which has no single payload to erase to; "
                f"drop one of them"
            )
            return None
        form = self.rule_form(rule)
        if form is gshape.RuleShape.TERMINAL:
            return TransparentType(rule_name=rule_name, payload=TEXT, coercion=self.coercion_for(configured))
        if form is gshape.RuleShape.ENUM:
            if configured.bool_truthy is not None:
                return TransparentType(rule_name=rule_name, payload=BOOL)
            value_name = f"{self.rule_type_names[rule_name]}Value"
            return TransparentType(rule_name=rule_name, payload=NodeType(value_name))
        if form is gshape.RuleShape.SUM:
            self.error(
                f"Rule {rule_name!r}: `transparent;` applies to terminal-only, enum-shaped and "
                f"single-field product rules, but this rule is a sum, whose variants have no "
                f"common payload; drop `transparent;`"
            )
            return None
        return self.erased_product_payload(rule)

    @staticmethod
    def merged_terms(infos: Sequence[AltInfo]) -> dict[str, tuple[gsm.Term, ...]]:
        """Every label's terms, collected across the alternatives in grammar order."""
        terms: dict[str, tuple[gsm.Term, ...]] = {}
        for info in infos:
            for label, label_terms in info.terms.items():
                terms[label] = terms.get(label, ()) + label_terms
        return terms

    def erased_product_payload(self, rule: gsm.Rule) -> TransparentType | None:
        """The payload of a ``transparent;`` product: the type of its one field."""
        arities = ce.compute_label_arities(rule)
        terms = self.merged_terms(self.alt_infos(rule))
        if len(terms) != 1:
            named = ", ".join(sorted(terms)) or "(none)"
            self.error(
                f"Rule {rule.name!r}: `transparent;` needs a product rule with exactly one field "
                f"to erase to, but this rule has {len(terms)}: {named}; drop `transparent;`"
            )
            return None
        (label,) = terms
        if arities[label].arity_class is not ce.ArityClass.REQUIRED_SINGLE:
            # TODO(ast-transparent-container-payload): erase to the container type instead.
            self.error(
                f"Rule {rule.name!r}: `transparent;` erases the rule to its {label!r} field, which "
                f"is {arities[label].arity_class.value} — only a field occurring exactly once can "
                f"be a payload; drop `transparent;`, or make the item required"
            )
            return None
        elements = self.element_types(rule, label, terms[label])
        if elements is None:
            return None
        element = (
            elements[0]
            if len(elements) == 1
            else self.field_enum(rule, self.rule_type_names[rule.name], label, elements)
        )
        if element == SPAN:
            self.error(
                f"Rule {rule.name!r}: `transparent;` would erase the rule to the position of the "
                f"{label!r} literal, which carries no value — a literal's text is a grammar "
                f"constant; drop `transparent;`, or label a regex instead"
            )
            return None
        self.erasure_labels[rule.name] = label
        return TransparentType(rule_name=rule.name, payload=element)

    def build_erased_product(self, rule: gsm.Rule, type_name: str) -> ProductNode:
        """The node of a ``transparent;`` product: one field carrying the resolved payload.

        The field is named ``value`` rather than after its label: no public field is emitted, so
        the label never has to be a usable identifier — which makes ``transparent;`` one more
        fix for a rule whose only label is reserved or a keyword.
        """
        erased = self.erasures.get(rule.name)
        label = self.erasure_labels.get(rule.name)
        fields: tuple[Field, ...] = ()
        if erased is not None and label is not None:
            fields = (Field(name="value", label=label, type=FieldType(erased.payload, Container.SINGLE)),)
        return ProductNode(
            name=type_name,
            rule_name=rule.name,
            fields=fields,
            merged=len(rule.alternatives) > 1,
        )

    # --- `flatten;` wrapper hoisting -----------------------------------------------------

    def resolve_flattened(self) -> None:
        """The wrapper rules whose fields are spliced into the nodes referencing them.

        A rule the sidecar flattens but whose shape cannot be hoisted keeps a type of its own, so
        that the problem reported here is the only one; the sidecar validator refuses the same
        shapes before the model ever sees them.
        """
        flattened: set[str] = set()
        for rule_name, configured in self.config.rules.items():
            if not configured.flatten:
                continue
            rule = self.rules_by_name.get(rule_name)
            if rule is None:
                # A `custom(...)` rule has no generated fields; the sidecar reports the conflict.
                continue
            if configured.transparent or configured.fold is not None:
                other = "`transparent;`" if configured.transparent else "a fold"
                self.error(
                    f"Rule {rule_name!r}: `flatten;` cannot combine with {other} — the rule cannot both "
                    f"splice its fields into its parents and have a payload of its own; drop one of them"
                )
                continue
            if configured.key is not None:
                self.error(
                    f"Rule {rule_name!r}: `flatten;` and `key:` cannot both apply — a `key:` acts only "
                    f"where the rule is a collection, and a flattened wrapper cannot be one, so the "
                    f"`key:` would key nothing; drop one of them"
                )
                continue
            form = self.rule_form(rule)
            if form is not gshape.RuleShape.PRODUCT:
                self.error(
                    f"Rule {rule_name!r}: `flatten;` applies only to a product rule, whose fields can be "
                    f"hoisted into the rule that references it, but this rule is {form.value}; "
                    f"drop `flatten;`"
                )
                continue
            flattened.add(rule_name)
        self.flattened_rules = frozenset(flattened)

    def wrapper_for(self, label_terms: Sequence[gsm.Term], arity: ce.ArityClass) -> str | None:
        """The ``flatten;`` wrapper a label hoists, or ``None`` when the label is a plain field.

        Only a label occurring at most once and naming nothing but the wrapper hoists: a
        collection of wrappers has nowhere to put repeated hoisted fields, and a label carrying a
        second type would need the wrapper as one arm of a field enum.  Both fall through to the
        ordinary field path, where the wrapper's missing type is reported.
        """
        if arity is ce.ArityClass.COLLECTION:
            return None
        identifiers = [term for term in label_terms if isinstance(term, gsm.Identifier)]
        if not identifiers or len(identifiers) != len(label_terms):
            return None
        names = {term.value for term in identifiers}
        if len(names) != 1:
            return None
        (name,) = names
        return name if name in self.flattened_rules else None

    def hoist(
        self, rule: gsm.Rule, label: str, wrapper: str, arity: ce.ArityClass, names: dict[str, str]
    ) -> Hoist | None:
        """The wrapper spliced in at ``label``, or ``None`` with the reason reported.

        ``names`` is the containing rule's field-name table, which the hoisted names join: a
        hoisted field colliding with a sibling is a generation error, fixed by renaming the field
        inside the wrapper.
        """
        if not self.check_hoist_position(rule, label, wrapper):
            return None
        fields = self.wrapper_fields(wrapper)
        if fields is None:
            return None
        optional = arity is ce.ArityClass.OPTIONAL_SINGLE
        hoisted: list[Field] = []
        required: set[str] = set()
        for field in fields:
            previous = names.get(field.name)
            if previous is not None:
                self.error(
                    f"Rule {rule.name!r}: the field {field.name!r} hoisted from the flattened rule "
                    f"{wrapper!r} collides with the field of label {previous!r}; rename one with "
                    f"`rule {wrapper} {{ field {field.label} {{ name: <new>; }} }}`"
                )
                return None
            names[field.name] = label
            if field.type.container is Container.SINGLE and field.type.element != BOOL:
                required.add(field.name)
            field_type = _degrade(field.type) if optional else field.type
            hoisted.append(dataclasses.replace(field, hoist=label, type=field_type))
        return Hoist(
            rule_name=wrapper,
            label=label,
            optional=optional,
            fields=tuple(hoisted),
            required=frozenset(required),
        )

    def check_hoist_position(self, rule: gsm.Rule, label: str, wrapper: str) -> bool:
        """A hoisted wrapper is rebuilt at one item position, so its label needs exactly one."""
        for alternative in rule.alternatives:
            if sum(1 for slot in _slots_for_alternative(alternative) if slot.label == label) > 1:
                self.error(
                    f"Rule {rule.name!r}: the label {label!r} of the flattened rule {wrapper!r} is "
                    f"matched by more than one item position, so the hoisted fields have no single "
                    f"position to be rendered back through; give the label one position, or drop "
                    f"`flatten;` from {wrapper!r}"
                )
                return False
        return True

    def wrapper_fields(self, rule_name: str) -> tuple[Field, ...] | None:
        """The fields a ``flatten;`` wrapper contributes, or ``None`` with the reason reported."""
        if rule_name in self.broken_wrappers:
            return None
        if rule_name in self.flattening:
            # The sidecar validator rejects flatten cycles; this catches a hand-built config.
            self.error(
                f"Rule {rule_name!r}: `flatten;` never bottoms out — the rule's fields are hoisted "
                f"through itself; at least one rule in the cycle must keep a type of its own"
            )
            self.broken_wrappers.add(rule_name)
            return None
        self.flattening.add(rule_name)
        try:
            fields, _ = self.product_shape(self.rules_by_name[rule_name])
        finally:
            self.flattening.discard(rule_name)
        return fields

    def product_shape(self, rule: gsm.Rule) -> tuple[tuple[Field, ...], tuple[Hoist, ...]]:
        """A product rule's fields and hoisted wrappers, built once however many callers ask.

        A flattened wrapper's fields are asked for by each of its use sites as well as by the
        rule's own node, and building them reports name problems as it goes.
        """
        cached = self.product_shapes.get(rule.name)
        if cached is None:
            cached = self.build_fields(
                rule,
                self.rule_type_names[rule.name],
                ce.compute_label_arities(rule),
                self.merged_terms(self.alt_infos(rule)),
            )
            self.product_shapes[rule.name] = cached
        return cached

    # --- `key:` keyed collections --------------------------------------------------------

    def map_key(self, rule_name: str) -> MapKey | None:
        """The map key of ``rule_name``, or ``None`` when it keys no collection.

        Memoized, including the failure: every collection use site of the rule asks, and a
        ``key:`` that does not resolve must be reported once rather than at each of them.
        """
        if rule_name in self.unkeyed:
            return None
        cached = self.map_keys.get(rule_name)
        if cached is not None:
            return cached
        label = self.config.for_rule(rule_name).key
        resolved = None if label is None else self.compute_map_key(rule_name, label)
        if resolved is None:
            self.unkeyed.add(rule_name)
            return None
        self.map_keys[rule_name] = resolved
        return resolved

    def compute_map_key(self, rule_name: str, label: str) -> MapKey | None:
        """Resolve ``key: <label>;`` against the element rule's own fields."""
        rule = self.rules_by_name.get(rule_name)
        if rule is None:
            # A `custom(...)` rule has no generated fields; the sidecar reports the conflict.
            return None
        if rule_name in self.transparent_rules:
            self.error(
                f"Rule {rule_name!r}: `key:` and `transparent;` cannot both apply — an erased rule's "
                f"use sites carry its payload rather than a node with a {label!r} field to key on; "
                f"drop one of them"
            )
            return None
        if self.rule_form(rule) is not gshape.RuleShape.PRODUCT:
            self.error(
                f"Rule {rule_name!r}: `key:` applies only to a product rule, the one form with named "
                f"fields, but this rule is {self.rule_form(rule).value}; drop `key:`"
            )
            return None
        terms = self.merged_terms(self.alt_infos(rule))
        arities = ce.combine_alternatives(self.rule_arities(rule))
        if label not in terms:
            self.error(
                f"Rule {rule_name!r}: `key: {label};` names no field of this rule — its fields are: "
                f"{', '.join(sorted(terms)) or '(none)'}"
            )
            return None
        if arities[label].arity_class is not ce.ArityClass.REQUIRED_SINGLE:
            self.error(
                f"Rule {rule_name!r}: the `key:` field {label!r} is "
                f"{arities[label].arity_class.value} — only a field occurring exactly once can key a "
                f"map; key on another field, or make the item required"
            )
            return None
        elements = self.element_types(rule, label, terms[label])
        if elements is None:
            return None
        if len(elements) != 1 or not _is_key_scalar(elements[0]):
            self.error(
                f"Rule {rule_name!r}: the `key:` field {label!r} does not resolve to a string or an "
                f"integer, so it cannot key a map; label a regex instead, or mark the referenced rule "
                f"`transparent;` (optionally with an integer `type:` coercion)"
            )
            return None
        return MapKey(
            rule_name=rule_name,
            label=label,
            field_name=self.config.for_rule(rule_name).field_names.get(label, label),
            element=elements[0],
        )

    def keyed_element(self, terms: Sequence[gsm.Term]) -> MapKey | None:
        """The map key of a collection whose elements all come from one ``key:`` rule."""
        referenced = {term.value for term in terms if isinstance(term, gsm.Identifier)}
        if len(referenced) != 1:
            return None
        (rule_name,) = referenced
        return self.map_key(rule_name)

    def rule_form(self, rule: gsm.Rule) -> gshape.RuleShape:
        """The node form the rule takes, with a ``sum;``/``product;`` override applied.

        Memoized: a forced ``sum;`` over a non-disjoint pair reports its generation error as
        a side effect, and that report must happen exactly once.
        """
        cached = self.forms.get(rule.name)
        if cached is None:
            cached = self.classify(rule)
            self.forms[rule.name] = cached
        return cached

    def classify(self, rule: gsm.Rule) -> gshape.RuleShape:
        """The rule's node form, with the sidecar's ``sum;``/``product;`` override applied.

        A forced ``sum;`` still needs pairwise-disjoint alternatives: a non-disjoint pair
        cannot be told apart at dispatch time, so an unsound override is a generation error.
        """
        shape = gshape.classify_rule(rule, self.rule_arities(rule))
        multi = (gshape.RuleShape.SUM, gshape.RuleShape.PRODUCT)
        override = self.config.for_rule(rule.name).shape
        if override is None or shape not in multi or len(rule.alternatives) < _MIN_ALTERNATIVES:
            return shape
        if override is ac.Shape.PRODUCT:
            return gshape.RuleShape.PRODUCT
        if self.forced_sum_is_sound(rule, self.alt_infos(rule)):
            return gshape.RuleShape.SUM
        return gshape.RuleShape.PRODUCT

    def forced_sum_is_sound(self, rule: gsm.Rule, infos: Sequence[AltInfo]) -> bool:
        sound = True
        for index, one in enumerate(infos):
            for other in infos[index + 1 :]:
                if alternatives_are_disjoint(one.signature, other.signature):
                    continue
                sound = False
                self.error(
                    f"Rule {rule.name!r}: `sum;` needs every pair of alternatives to be told apart "
                    f"by their labeled children, but alternatives {one.index + 1} and "
                    f"{other.index + 1} cannot be; label a distinguishing terminal, split them into "
                    f"sub-rules, or drop the `sum;` and take the merged product"
                )
        return sound

    def check_recorded_terminals(self, rule: gsm.Rule) -> None:
        """Every included regex of a field-bearing rule must be labeled.

        A label is the only thing that records a regex's text in the AST.  An unlabeled
        included regex is dropped on the way in and cannot be put back on the way out, so
        ``unparse`` would emit text the grammar no longer accepts.  Terminal-only rules are
        exempt: their whole span is the ``text`` field, unlabeled parts included.
        """
        reported: set[str] = set()

        def visit(item: gsm.Item) -> None:
            if item.label is not None or not isinstance(item.term, gsm.Regex):
                return
            if item.term.value in reported:
                return
            reported.add(item.term.value)
            self.error(
                f"Rule {rule.name!r}: the included regex /{item.term.value}/ has no label, so its "
                f"text is recorded nowhere in the AST and could not be synthesised back; label the "
                f"item, or suppress it and let a labeled item carry the text"
            )

        for alternative in rule.alternatives:
            visit_included_items(alternative, visit)

    def build_enum_node(self, rule: gsm.Rule, type_name: str) -> EnumNode:
        # A `bool:` rule carries `value: bool`, so it generates no value enum and leaves the
        # `<Rule>Value` name free; its variants are still built, for their labels and literals.
        truthy = self.config.for_rule(rule.name).bool_truthy
        value_name = f"{type_name}Value"
        if truthy is None:
            self.claim_type_name(value_name, f"the value enum of rule {rule.name!r}")

        # Alternatives sharing a label are equivalent spellings of one variant; only the first
        # reaches the variant list, making its literal the canonical spelling.
        alternatives: list[tuple[str, str]] = []
        labeled: set[str] = set()
        for alternative in rule.alternatives:
            item = alternative.items[0]
            if item.label is None or not isinstance(item.term, gsm.Literal):
                # Unreachable: the enum-shaped predicate guarantees both.
                continue
            if item.label in labeled:
                continue
            labeled.add(item.label)
            alternatives.append((item.label, item.term.value))

        computed = [naming.snake_to_upper_camel(label) for label, _ in alternatives]
        names = computed if truthy is not None else self.rename_variants(rule, computed)

        variants: list[ValueVariant] = []
        seen: dict[str, str] = {}
        members: dict[str, str] = {}
        for (label, literal), selector, name in zip(alternatives, computed, names, strict=True):
            member = _upper_snake(name)
            # Two names can share one Python enum member: `_upper_snake` splits at case
            # boundaries only, so `HTTPCode` and `HttpCode` both give `HTTP_CODE`, and a
            # duplicate member is an import-time `TypeError` in the generated module.
            previous = seen.get(name) or members.get(member)
            if previous is not None:
                clash = f"value-enum variant {name!r}" if name in seen else f"the Python enum member {member!r}"
                self.error(
                    f"Rule {rule.name!r}: labels {previous!r} and {label!r} both produce {clash}; "
                    f"rename one with `rule {rule.name} {{ variant {selector}: <NewName>; }}`"
                )
                continue
            seen[name] = label
            members[member] = label
            variants.append(ValueVariant(name=name, member=member, label=label, literal=literal))

        if truthy is not None and len(variants) != _BOOLEAN_VARIANTS:
            # A boolean needs both values to exist as variants: with only one, `False` names no
            # alternative and nothing could render it.  Merged spellings are why the count is of
            # variants rather than of the rule's alternatives.
            spellings = ", ".join(repr(variant.label) for variant in variants)
            self.error(
                f"Rule {rule.name!r}: `bool:` needs exactly two variants — one true, one false — "
                f"but the rule has {len(variants)} ({spellings}); alternatives sharing a label are "
                f"one variant, so give the false value its own label"
            )

        value_enum = ValueEnum(name=value_name, rule_name=rule.name, variants=tuple(variants))
        if truthy is None:
            self.value_enums[value_name] = value_enum
        return EnumNode(name=type_name, rule_name=rule.name, value_enum=value_enum, bool_truthy=truthy)

    def rename_variants(self, rule: gsm.Rule, computed: Sequence[str]) -> list[str]:
        """Apply the rule's ``variant <computed>: <NewName>;`` statements to the computed names."""
        renames = self.config.for_rule(rule.name).variant_names
        if not renames:
            return list(computed)
        known = set(computed)
        for selector in renames:
            if selector not in known:
                self.error(
                    f"Rule {rule.name!r}: `variant {selector}:` names no variant of this rule; the "
                    f"computed variant names are: {', '.join(computed)}"
                )
        return [renames.get(name, name) for name in computed]

    def build_terminal_node(self, rule: gsm.Rule, type_name: str) -> TerminalNode:
        configured = self.config.for_rule(rule.name)
        text_from = configured.text_from
        if text_from is None:
            for alternative in rule.alternatives:
                if has_whitespace_separator(alternative):
                    self.error(
                        f"Terminal-only rule {rule.name!r} joins items with a whitespace-permitting "
                        f"separator, so its text could contain whitespace or comments; use '.' between "
                        f"every item, label the parts so the rule becomes a product, or redirect the "
                        f"text with `rule {rule.name} {{ text_from: <label>; }}`"
                    )
                    break
        else:
            self.check_redirect_label(rule, text_from)
            self.check_redirected_terminals(rule, text_from)
        return TerminalNode(
            name=type_name,
            rule_name=rule.name,
            coercion=self.coercion_for(configured),
            text_from=text_from,
        )

    def check_redirect_label(self, rule: gsm.Rule, text_from: str) -> None:
        """``text_from:`` reads one child's span, so its label must occur exactly once.

        The sidecar validator checks this; it is repeated here because ``build_ast_model`` also
        accepts a hand-built ``ResolvedAstConfig``.  An absent or suppressed label leaves the
        converter reading a child that is not there, and a label occurring twice leaves the text
        plan holding the second occurrence's capture group while its pieces still name the first.
        """
        arities = ce.compute_label_arities(rule)
        count = arities.get(text_from)
        if count is None:
            named = ", ".join(sorted(arities)) or "(none)"
            self.error(
                f"Rule {rule.name!r}: `text_from: {text_from};` names no included label of this rule — "
                f"its labels are: {named}"
            )
        elif count.arity_class is not ce.ArityClass.REQUIRED_SINGLE:
            self.error(
                f"Rule {rule.name!r}: the `text_from:` label {text_from!r} is {count.arity_class.value} — "
                f"only a label occurring exactly once carries the rule's text; redirect to another "
                f"label, or make the item required"
            )

    def check_redirected_terminals(self, rule: gsm.Rule, text_from: str) -> None:
        """Under ``text_from:``, only the named label's text survives the conversion.

        The whole node span is no longer the text, so any other included regex is dropped on
        the way in and cannot be put back on the way out — the same hole ``check_recorded_terminals``
        closes for field-bearing rules, which a terminal-only rule is exempt from only because
        its text normally covers every part.
        """
        reported: set[str] = set()

        def visit(item: gsm.Item) -> None:
            if item.label == text_from or not isinstance(item.term, gsm.Regex):
                return
            if item.term.value in reported:
                return
            reported.add(item.term.value)
            self.error(
                f"Rule {rule.name!r}: `text_from: {text_from};` keeps only the {text_from!r} text, so "
                f"the included regex /{item.term.value}/ is recorded nowhere in the AST and could not "
                f"be synthesised back; suppress that item, or convert the rule with `custom(...)`"
            )

        for alternative in rule.alternatives:
            visit_included_items(alternative, visit)

    def coercion_for(self, configured: ac.ResolvedRule) -> Coercion | None:
        """The rule's ``type:`` coercion, in the form the emitters consume."""
        coercion = configured.coercion
        if coercion is None:
            return None
        if isinstance(coercion, ac.BuiltinScalar):
            return BuiltinCoercion(name=coercion.name)
        return CustomCoercion(
            rule_name=configured.rule_name,
            python_type=coercion.entry("py_type"),
            python_parse=coercion.entry("py_parse"),
            python_unparse=coercion.entry("py_unparse"),
            rust_type=coercion.entry("rust_type"),
            rust_parse=coercion.entry("rust_parse"),
            rust_unparse=coercion.entry("rust_unparse"),
        )

    def build_product_node(self, rule: gsm.Rule, type_name: str, infos: Sequence[AltInfo]) -> ProductNode:
        fields, hoists = self.product_shape(rule)
        return ProductNode(
            name=type_name,
            rule_name=rule.name,
            fields=fields,
            hoists=hoists,
            merged=len(infos) > 1,
        )

    def build_sum_node(self, rule: gsm.Rule, type_name: str, infos: Sequence[AltInfo]) -> SumNode:
        variant_names = self.variant_names(rule, infos)
        direct = self.direct_payloads(infos, frozenset({rule.name}))

        variants: list[SumVariant] = []
        for info, variant_name in zip(infos, variant_names, strict=True):
            direct_rule = direct.get(info.index)
            payload: ElementType
            if direct_rule is None:
                payload_name = f"{type_name}{variant_name}"
                self.claim_type_name(payload_name, f"the payload of variant {variant_name!r} of rule {rule.name!r}")
                fields, hoists = self.build_fields(rule, payload_name, info.arities, info.terms)
                self.payload_classes[payload_name] = PayloadClass(
                    name=payload_name,
                    rule_name=rule.name,
                    alternative_index=info.index,
                    fields=fields,
                    hoists=hoists,
                )
                payload = NodeType(payload_name)
            else:
                payload = self.rule_element_type(direct_rule)
            variants.append(
                SumVariant(
                    name=variant_name,
                    alternative_index=info.index,
                    payload=payload,
                    signature=info.signature,
                    payload_rule=direct_rule,
                )
            )
        return SumNode(name=type_name, rule_name=rule.name, variants=tuple(variants))

    # --- `fold_left:` / `fold_right:` binary chains ---------------------------------------

    def build_fold_node(self, rule: gsm.Rule, type_name: str, fold: ac.Fold) -> FoldNode | None:
        """The operand/link pair a fold rule generates, or ``None`` with the reason reported."""
        labels = self.fold_labels(rule, fold)
        if labels is None:
            return None
        operand_label, op_label = labels
        self.check_fold_positions(rule, labels)
        terms = self.alt_infos(rule)[0].terms
        operand_element = self.fold_element(rule, type_name, operand_label, terms[operand_label])
        op_element = self.fold_element(rule, type_name, op_label, terms[op_label])
        op_name = self.fold_field_name(rule, op_label)
        if operand_element is None or op_element is None or op_name is None:
            return None

        operand_variant, binary_variant = self.fold_variants(rule)
        binary_name = f"{type_name}{binary_variant}"
        self.claim_type_name(binary_name, f"the chain link of fold rule {rule.name!r}")
        op_type = FieldType(op_element, Container.SINGLE)
        return FoldNode(
            name=type_name,
            rule_name=rule.name,
            direction=fold.direction,
            binary=FoldBinary(
                name=binary_name,
                rule_name=rule.name,
                op=Field(name=op_name, label=op_label, type=op_type),
            ),
            operand_variant=operand_variant,
            binary_variant=binary_variant,
            operand=Field(
                name=operand_label,
                label=operand_label,
                type=FieldType(operand_element, Container.COLLECTION),
            ),
            operators=Field(name=op_name, label=op_label, type=FieldType(op_element, Container.COLLECTION)),
        )

    def fold_labels(self, rule: gsm.Rule, fold: ac.Fold) -> tuple[str, str] | None:
        """The rule's (operand, operator) labels, or ``None`` with the reason reported.

        Memoized, including the failure: the payload-identity walk asks as well as the
        builder, and an unfoldable rule must be reported once rather than at each caller.
        """
        if rule.name not in self.fold_shapes:
            self.fold_shapes[rule.name] = self.compute_fold_labels(rule, fold)
        return self.fold_shapes[rule.name]

    def compute_fold_labels(self, rule: gsm.Rule, fold: ac.Fold) -> tuple[str, str] | None:
        """Check the rule against the shape a fold needs: ``operand , (op , operand)*``.

        The sidecar validator refuses every shape this refuses; the checks are repeated here
        because ``build_ast_model`` also accepts a hand-built ``ResolvedAstConfig``.
        """
        infos = self.alt_infos(rule)
        arities = infos[0].arities if len(infos) == 1 else {}
        labels = sorted(arities)
        if len(infos) != 1 or len(labels) != _FOLD_LABELS or fold.op_label not in labels:
            self.error(
                f"Rule {rule.name!r}: `fold_{fold.direction.value}: {fold.op_label};` needs a "
                f"single-alternative rule of the form `operand , ({fold.op_label}:op , operand)*`, "
                f"whose only two labels are the operand and the operator"
            )
            return None
        (operand_label,) = (label for label in labels if label != fold.op_label)
        operand = arities[operand_label]
        if (
            arities[fold.op_label].arity_class is not ce.ArityClass.COLLECTION
            or operand.arity_class is not ce.ArityClass.COLLECTION
            or operand.min < 1
        ):
            self.error(
                f"Rule {rule.name!r}: a fold's operator {fold.op_label!r} must be repeatable and its "
                f"operand {operand_label!r} must occur one or more times, as in "
                f"`{operand_label}:operand , ({fold.op_label}:op , {operand_label}:operand)*`"
            )
            return None
        return operand_label, fold.op_label

    def check_fold_positions(self, rule: gsm.Rule, labels: tuple[str, str]) -> None:
        """A fold is re-interleaved one item at a time, so each label needs one item position.

        The reverse direction walks operand, operator, operand, ..., rendering each value
        through the position its label names.  An unlabeled included item has no place in that
        walk, and a label matched by positions that do not accept the same values — an
        alternation inside the repetition, whether its branches differ by kind, by referenced
        rule, by terminal or by literal — has no single position to render through.  The
        signature is deliberately the whole content of a position: two literal branches under
        one label render as *one* of the two literals whichever value arrived, which for a fold
        operator silently rewrites the expression.
        """
        slots = _slots_for_alternative(rule.alternatives[0])
        if any(slot.label is None for slot in slots):
            self.error(
                f"Rule {rule.name!r}: a fold re-interleaves its operands and operators one at a time, "
                f"so every included item must be labeled, but this rule includes an unlabeled "
                f"terminal; suppress that item, or convert the rule with `custom(...)`"
            )
        for label in labels:
            positions = {
                (slot.kind, slot.rule_name, slot.pattern, slot.literal) for slot in slots if slot.label == label
            }
            if len(positions) > 1:
                self.error(
                    f"Rule {rule.name!r}: the fold label {label!r} is matched by item positions that do "
                    f"not all accept the same values, so a value of it has no single position to be "
                    f"rendered through; give the alternation a rule of its own and label that instead"
                )

    def fold_element(
        self, rule: gsm.Rule, owner_type_name: str, label: str, terms: Sequence[gsm.Term]
    ) -> ElementType | None:
        """The element type one fold label carries, as a field of that label would."""
        elements = self.element_types(rule, label, terms)
        if elements is None:
            return None
        if len(elements) > 1 and SPAN in elements:
            elements = _dedupe([TEXT if element == SPAN else element for element in elements])
        if len(elements) == 1:
            return elements[0]
        return self.field_enum(rule, owner_type_name, label, elements)

    def fold_field_name(self, rule: gsm.Rule, label: str) -> str | None:
        """The operator member of a chain link: the label, or its ``field { name: }`` rename."""
        renames = self.config.for_rule(rule.name).field_names
        name = renames.get(label, label)
        if label in renames:
            self.applied_field_renames.setdefault(rule.name, set()).add(label)
        elif not self.check_field_name(rule, label):
            return None
        if name in (FOLD_LHS, FOLD_RHS):
            self.error(
                f"Rule {rule.name!r}: the fold operator field {name!r} collides with the "
                f"{FOLD_LHS}/{FOLD_RHS} members every chain link carries; rename it with "
                f"`rule {rule.name} {{ field {label} {{ name: <new>; }} }}`"
            )
            return None
        return name

    def fold_identities(self, rule: gsm.Rule, fold: ac.Fold, seen: frozenset[str]) -> frozenset[tuple[str, str]]:
        """A fold's payload identities: its operand's, plus its own chain link.

        The link class and an operand field enum are both globally claimed generated names,
        so each collides with nothing; an opaque per-rule entry stands for them.
        """
        identities: set[tuple[str, str]] = {("payload", f"{rule.name}#binary")}
        labels = self.fold_labels(rule, fold)
        if labels is None:
            return frozenset(identities)
        terms = self.alt_infos(rule)[0].terms[labels[0]]
        if len(terms) == 1:
            term = terms[0]
            if isinstance(term, gsm.Identifier):
                if term.value in self.rule_type_names or term.value in self.custom_types:
                    return frozenset(identities | self.payload_identities(term.value, seen))
            else:
                return frozenset(identities | _payload_identity(TEXT if isinstance(term, gsm.Regex) else SPAN))
        identities.add(("payload", f"{rule.name}#operand"))
        return frozenset(identities)

    def fold_variants(self, rule: gsm.Rule) -> tuple[str, str]:
        operand, binary = self.rename_variants(rule, (FOLD_OPERAND_VARIANT, FOLD_BINARY_VARIANT))
        if operand == binary:
            self.error(
                f"Rule {rule.name!r}: both fold variants are named {operand!r}; rename one with "
                f"`rule {rule.name} {{ variant {FOLD_BINARY_VARIANT}: <NewName>; }}`"
            )
        return operand, binary

    def variant_names(self, rule: gsm.Rule, infos: Sequence[AltInfo]) -> list[str]:
        computed: list[str] = []
        for info in infos:
            labels = list(info.terms)
            computed.append(naming.snake_to_upper_camel(labels[0]) if len(labels) == 1 else f"Alt{info.index + 1}")
        names = self.rename_variants(rule, computed)

        seen: dict[str, int] = {}
        for index, name in enumerate(names):
            previous = seen.get(name)
            if previous is not None:
                self.error(
                    f"Rule {rule.name!r}: alternatives {previous + 1} and {index + 1} both produce "
                    f"variant name {name!r}; rename one with "
                    f"`rule {rule.name} {{ variant {computed[index]}: <NewName>; }}`"
                )
            else:
                seen[name] = index
        return names

    def rule_element_type(self, rule_name: str) -> ElementType:
        """The element type a reference to ``rule_name`` contributes.

        An erased rule contributes its payload; a rule whose erasure did not resolve falls back
        to its node type so that the one error already reported is the only one.
        """
        custom = self.custom_types.get(rule_name)
        if custom is not None:
            return custom
        if rule_name in self.transparent_rules:
            erased = self.erasure(rule_name)
            if erased is not None:
                return erased
        return NodeType(self.rule_type_names[rule_name])

    def payload_identities(self, rule_name: str, seen: frozenset[str]) -> frozenset[tuple[str, str]]:
        """Every payload identity a value of ``rule_name``'s AST type can carry.

        A sum expands to its variants' identities: its Python union *is* the union of theirs,
        so a class reachable through two variants of an enclosing sum would appear twice in
        that sum's union and its ``isinstance`` dispatch could not tell the two apart.  A fold
        expands the same way, over its operand and its chain link.  ``seen`` cuts recursion
        through the grammar, which leaves the fixpoint: a variant reachable only through
        itself adds nothing the other variants do not already carry.
        """
        element = self.rule_element_type(rule_name)
        rule = self.rules_by_name.get(rule_name)
        if rule is None:
            return _payload_identity(element)
        fold = self.config.for_rule(rule_name).fold
        if fold is not None:
            if rule_name in seen:
                return frozenset()
            return self.fold_identities(rule, fold, seen | {rule_name})
        if self.rule_form(rule) is not gshape.RuleShape.SUM:
            return _payload_identity(element)
        if rule_name in seen:
            return frozenset()

        infos = self.alt_infos(rule)
        deeper = seen | {rule_name}
        direct = self.direct_payloads(infos, deeper)
        identities: set[tuple[str, str]] = set()
        for info in infos:
            referenced = direct.get(info.index)
            if referenced is None:
                # A generated payload class is claimed globally, so it collides with nothing.
                identities.add(("payload", f"{rule_name}#{info.index}"))
            else:
                identities |= self.payload_identities(referenced, deeper)
        return frozenset(identities)

    def direct_payloads(self, infos: Sequence[AltInfo], seen: frozenset[str] = frozenset()) -> dict[int, str]:
        """Variants whose alternative is a single required rule reference used by no sibling.

        Maps alternative index to the referenced rule name.  Uniqueness is judged on the
        *payload type* rather than the rule: two ``custom(...)`` rules may name one user
        type, and a union or an ``isinstance`` dispatch cannot tell those variants apart.  A
        flattened wrapper is never a direct payload — it has no type to be one — so its variant
        takes a generated payload class carrying the hoisted fields instead.
        """
        candidates: dict[int, str] = {}
        for info in infos:
            if len(info.items.items) != 1:
                continue
            item = info.items.items[0]
            if item.label is None or item.disposition != gsm.Disposition.INCLUDE:
                continue
            if item.quantifier.min() != gsm.Arity.ONE or item.quantifier.max() != gsm.Arity.ONE:
                continue
            if not isinstance(item.term, gsm.Identifier):
                continue
            referenced = item.term.value
            if referenced in self.flattened_rules:
                continue
            if referenced in self.rule_type_names or referenced in self.custom_types:
                candidates[info.index] = referenced

        identities = {index: self.payload_identities(name, seen) for index, name in candidates.items()}
        counts: dict[tuple[str, str], int] = {}
        for identity in identities.values():
            for key in identity:
                counts[key] = counts.get(key, 0) + 1
        return {
            index: referenced
            for index, referenced in candidates.items()
            if all(counts[key] == 1 for key in identities[index])
        }

    def build_fields(
        self,
        rule: gsm.Rule,
        owner_type_name: str,
        arities: Mapping[str, ce.LabelCount],
        terms: Mapping[str, tuple[gsm.Term, ...]],
    ) -> tuple[tuple[Field, ...], tuple[Hoist, ...]]:
        renames = self.config.for_rule(rule.name).field_names
        fields: list[Field] = []
        hoists: list[Hoist] = []
        names: dict[str, str] = {}
        # Field name -> the wrapper rule it was hoisted from and its label inside that wrapper, so
        # a later plain field colliding with it reports the same wrapper-aware fix the opposite
        # declaration order already gets.
        hoisted_from: dict[str, tuple[str, str]] = {}
        for label, label_terms in terms.items():
            wrapper = self.wrapper_for(label_terms, arities[label].arity_class)
            if wrapper is not None:
                hoist = self.hoist(rule, label, wrapper, arities[label].arity_class, names)
                if hoist is not None:
                    hoists.append(hoist)
                    fields.extend(hoist.fields)
                    hoisted_from.update({field.name: (wrapper, field.label) for field in hoist.fields})
                continue
            name = renames.get(label, label)
            if label in renames:
                self.applied_field_renames.setdefault(rule.name, set()).add(label)
            # A `field { name: }` rename is itself the fix for an unusable label, and the sidecar
            # validator has already run the replacement through the same hygiene rules.
            if name == label and not self.check_field_name(rule, label):
                continue
            previous = names.get(name)
            if previous is not None:
                through = hoisted_from.get(name)
                if through is not None:
                    self.error(
                        f"Rule {rule.name!r}: the field {name!r} hoisted from the flattened rule "
                        f"{through[0]!r} collides with the field of label {label!r}; rename one with "
                        f"`rule {through[0]} {{ field {through[1]} {{ name: <new>; }} }}`"
                    )
                else:
                    self.error(
                        f"Rule {rule.name!r}: labels {previous!r} and {label!r} both produce field name "
                        f"{name!r}; rename one with `rule {rule.name} {{ field {label} {{ name: <new>; }} }}`"
                    )
                continue
            names[name] = label
            arity = arities[label].arity_class
            field_type = self.field_type(rule, owner_type_name, label, arity, label_terms)
            if field_type is not None:
                fields.append(Field(name=name, label=label, type=field_type))
        return tuple(fields), tuple(hoists)

    def check_field_name(self, rule: gsm.Rule, label: str) -> bool:
        reason = ac.name_problem(label)
        if reason is None and label in self.reserved_fields:
            reason = (
                "it is the CST back-pointer member `option cst = true;` adds"
                if label == CST_FIELD_NAME
                else "it is a member every generated node already carries"
            )
        if reason is None:
            return True
        self.error(
            f"Rule {rule.name!r}: label {label!r} cannot be a field name because {reason}; "
            f"rename the label or add `rule {rule.name} {{ field {label} {{ name: <new>; }} }}`"
        )
        return False

    def field_type(
        self,
        rule: gsm.Rule,
        owner_type_name: str,
        label: str,
        arity: ce.ArityClass,
        terms: Sequence[gsm.Term],
    ) -> FieldType | None:
        elements = self.element_types(rule, label, terms)
        if elements is None:
            return None

        if elements == [SPAN]:
            if arity is ce.ArityClass.OPTIONAL_SINGLE:
                return FieldType(element=BOOL, container=Container.SINGLE)
            return FieldType(element=SPAN, container=_CONTAINER_BY_ARITY[arity])

        if SPAN in elements:
            # A literal's text is recoverable from its span, so a label mixing literals with
            # other terminals or nodes carries text rather than bare positions.
            elements = _dedupe([TEXT if element == SPAN else element for element in elements])

        container = _CONTAINER_BY_ARITY[arity]
        if len(elements) == 1:
            if container is Container.COLLECTION and (key := self.keyed_element(terms)) is not None:
                return FieldType(element=elements[0], container=Container.MAP, key=key)
            return FieldType(element=elements[0], container=container)
        return FieldType(element=self.field_enum(rule, owner_type_name, label, elements), container=container)

    def element_types(self, rule: gsm.Rule, label: str, terms: Sequence[gsm.Term]) -> list[ElementType] | None:
        elements: list[ElementType] = []
        for term in terms:
            if isinstance(term, gsm.Identifier):
                if term.value in self.flattened_rules:
                    self.error(
                        f"Rule {rule.name!r}: label {label!r} references {term.value!r}, which `flatten;` "
                        f"splices into its use sites, so it has no AST type of its own; a flattened "
                        f"wrapper is reachable only through a label that occurs at most once and carries "
                        f"nothing else — drop `flatten;` from {term.value!r}, or restructure the label"
                    )
                    return None
                if term.value not in self.rule_type_names and term.value not in self.custom_types:
                    self.error(
                        f"Rule {rule.name!r}: label {label!r} references {term.value!r}, which is not "
                        f"a rule with an AST type"
                    )
                    return None
                elements.append(self.rule_element_type(term.value))
            elif isinstance(term, gsm.Regex):
                elements.append(TEXT)
            elif isinstance(term, gsm.Literal):
                elements.append(SPAN)
            else:
                self.error(
                    f"Rule {rule.name!r}: label {label!r} names an invocation term, which is not "
                    f"supported in AST generation"
                )
                return None
        return _dedupe(elements)

    def field_enum(self, rule: gsm.Rule, owner_type_name: str, label: str, elements: Sequence[ElementType]) -> NodeType:
        enum_name = f"{owner_type_name}{naming.snake_to_upper_camel(label)}"
        existing = self.field_enums.get(enum_name)
        if existing is None:
            self.claim_type_name(enum_name, f"the {label!r} field enum of rule {rule.name!r}")
            self.field_enums[enum_name] = FieldEnum(
                name=enum_name,
                rule_name=rule.name,
                label=label,
                variants=tuple(
                    FieldEnumVariant(name=_field_enum_variant_name(element), element=element) for element in elements
                ),
            )
        return NodeType(enum_name)


# The one word boundary behind every snake spelling of an UpperCamelCase name: after a
# non-capital, and before the last capital of a run that a lowercase letter follows.  An
# acronym therefore stays one word.
_CASE_BOUNDARY = re.compile(r"(?<=[^A-Z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _upper_snake(camel: str) -> str:
    """Turn an UpperCamelCase name into the UPPER_SNAKE_CASE a Python enum member uses.

    Splitting is at case boundaries only, so ``HttpCode`` and ``HTTPCode`` both give
    ``HTTP_CODE`` and ``XL`` stays ``XL``.  These are permanent public names on the
    generated module, so a rename must not come back mangled.
    """
    return _CASE_BOUNDARY.sub("_", camel).upper()


def _snake_case(camel: str) -> str:
    """Turn an UpperCamelCase name into the snake_case a generated function name uses.

    One boundary definition serves this and ``_upper_snake``, so ``HTTPCode`` gives
    ``http_code`` in a converter name and ``HTTP_CODE`` in an enum member.  Two boundary
    definitions would let the two backends spell one generated name differently.
    """
    return _upper_snake(camel).lower()


def _degrade(field_type: FieldType) -> FieldType:
    """A hoisted field's type where the ``flatten;`` wrapper's use site is optional.

    A required value becomes optional, because the wrapper may be absent.  An already-optional
    field, a collection, a map and a presence flag keep their type: their absent values are
    ``None``, empty and ``False``, which the wrapper's absence supplies directly.
    """
    if field_type.container is not Container.SINGLE or field_type.element == BOOL:
        return field_type
    return FieldType(element=field_type.element, container=Container.OPTIONAL, key=field_type.key)


def _payload_identity(element: ElementType) -> frozenset[tuple[str, str]]:
    """The type names a payload occupies, one entry per backend that has one.

    Two payloads collide when these sets intersect: a shared name on either backend makes
    the two variants indistinguishable there, and the fallback to generated payload classes
    has to happen on both backends to keep the two ASTs shape-equivalent.  An erased payload
    is named per backend because the two spellings differ: an ``i32`` and an ``i64`` rule are
    distinct Rust types but both plain ``int`` in Python, so they collide there.
    """
    if isinstance(element, NodeType):
        return frozenset({("generated", element.name)})
    if isinstance(element, CustomType):
        entries = (("python", element.python), ("rust", element.rust))
        return frozenset((backend, path) for backend, path in entries if path is not None)
    if isinstance(element, TransparentType):
        if element.coercion is None:
            return _payload_identity(element.payload)
        if isinstance(element.coercion, CustomCoercion):
            entries = (("python", element.coercion.python_type), ("rust", element.coercion.rust_type))
            return frozenset((backend, path) for backend, path in entries if path is not None)
        return frozenset({("python", PYTHON_SCALAR_TYPES[element.coercion.name]), ("rust", element.coercion.name)})
    return frozenset({("python", element.kind.value), ("rust", element.kind.value)})


def coercion_float_bits(coercion: Coercion | None) -> int | None:
    """The float width a ``type:`` coercion declares, or ``None`` when it is not a float.

    Python has a single float type, so a value declared narrower than 64 bits has to be kept
    rounded to what the Rust field of that width would hold; the width is what says so.
    """
    if isinstance(coercion, BuiltinCoercion) and coercion.is_float:
        return coercion.bits
    return None


def element_float_bits(element: ElementType) -> int | None:
    """The float width a field element's value is held at, or ``None`` when it is not a float."""
    if isinstance(element, TransparentType):
        if element.coercion is None:
            return element_float_bits(element.payload)
        return coercion_float_bits(element.coercion)
    return None


def _is_key_scalar(element: ElementType) -> bool:
    """Whether a resolved element can key a map: text, or an integer coercion of it.

    Floats and the ``uuid``/``decimal`` builtins are excluded.
    """
    if element == TEXT:
        return True
    if isinstance(element, TransparentType):
        if element.coercion is None:
            return _is_key_scalar(element.payload)
        return isinstance(element.coercion, BuiltinCoercion) and element.coercion.is_integer
    return False


def _field_enum_variant_name(element: ElementType) -> str:
    if isinstance(element, NodeType):
        return element.name
    if isinstance(element, CustomType | TransparentType):
        return naming.snake_to_upper_camel(element.rule_name)
    return {ScalarKind.TEXT: "Text", ScalarKind.SPAN: "Span", ScalarKind.BOOL: "Bool"}[element.kind]


def _dedupe(elements: Sequence[ElementType]) -> list[ElementType]:
    unique: list[ElementType] = []
    for element in elements:
        if element not in unique:
            unique.append(element)
    return unique


def build_ast_model(grammar: gsm.Grammar, config: ac.ResolvedAstConfig | None = None) -> AstModel:
    """Build the backend-neutral AST model for ``grammar``, shaped by ``config``.

    ``grammar`` must be INLINE-expanded and trivia-classified.  Trivia rules get no AST
    type; every other rule gets exactly one node form, except the rules a ``custom(...)``
    statement hands to a user-written type.  ``config`` is the resolved ``.fltkast``
    sidecar; omitting it is pure Tier 0.  All generation-time problems are collected and
    raised together as ``AstModelError``.
    """
    return _ModelBuilder(grammar, config if config is not None else ac.ResolvedAstConfig()).build()
