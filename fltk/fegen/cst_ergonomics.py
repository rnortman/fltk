"""Arity analysis and member planning for the ergonomic CST accessor surface.

Two things live here:

``compute_label_arities``
    Per-rule, per-label multiplicity derived from item quantifiers — information that
    ``gsm2tree.ItemsModel`` discards.

``plan_rule``
    The single decision point for which ergonomic members a rule's node class gets.
    Every emission surface (the Python dataclasses, the shared protocol classes, and the
    Rust structs / pymethods / type stubs) consumes the same plan, so a member exists on
    all of them or on none of them.

Both entry points operate on a grammar whose INLINE items have already been expanded;
an INLINE item raises ``ValueError``.
"""

from __future__ import annotations

import dataclasses
import enum
import keyword
import logging
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from fltk.fegen import gsm

if TYPE_CHECKING:
    from fltk.fegen.gsm2tree import ItemsModel, ModelType

logger = logging.getLogger(__name__)

_ONE = 1
# Counts saturate here: as a minimum it reads "two or more", as a maximum "unbounded".
_MANY = 2

INLINE_NOT_EXPANDED_MSG = (
    "INLINE disposition must be expanded with gsm.expand_inline_dispositions() before arity analysis"
)


class ArityClass(enum.Enum):
    """The API-relevant classification of a label's whole-rule multiplicity."""

    REQUIRED_SINGLE = "required_single"
    OPTIONAL_SINGLE = "optional_single"
    COLLECTION = "collection"


@dataclasses.dataclass(frozen=True, slots=True)
class LabelCount:
    """How many children a label can carry across a whole rule.

    Both bounds saturate at 2: a ``min`` of 2 means "two or more", a ``max`` of 2 means
    "unbounded".  Only the {0, 1, many} x {1, many} distinctions affect the generated API.
    """

    min: int
    max: int

    @staticmethod
    def of(minimum: int, maximum: int) -> LabelCount:
        """Build a count with both bounds saturated at ``_MANY``."""
        return LabelCount(min=min(minimum, _MANY), max=min(maximum, _MANY))

    @property
    def arity_class(self) -> ArityClass:
        if self.max > _ONE:
            return ArityClass.COLLECTION
        if self.min == _ONE:
            return ArityClass.REQUIRED_SINGLE
        return ArityClass.OPTIONAL_SINGLE


SINGLE_ARITIES = (ArityClass.REQUIRED_SINGLE, ArityClass.OPTIONAL_SINGLE)


def _quantify(count: LabelCount, quantifier: gsm.Quantifier) -> LabelCount:
    """Apply an item's quantifier to the counts contributed by that item's term."""
    minimum = 0 if quantifier.is_optional() else count.min
    maximum = _MANY if quantifier.is_multiple() else count.max
    return LabelCount.of(minimum, maximum)


def _combine_sequence(left: Mapping[str, LabelCount], right: Mapping[str, LabelCount]) -> dict[str, LabelCount]:
    """Combine counts for two consecutive positions within one alternative."""
    combined = dict(left)
    for label, count in right.items():
        existing = combined.get(label)
        if existing is None:
            combined[label] = count
        else:
            combined[label] = LabelCount.of(existing.min + count.min, existing.max + count.max)
    return combined


def combine_alternatives(maps: Sequence[Mapping[str, LabelCount]]) -> dict[str, LabelCount]:
    """Combine counts across mutually exclusive alternatives.

    A label absent from an alternative contributes zero to that alternative, so it comes
    out with ``min == 0``.
    """
    labels: list[str] = []
    for one_map in maps:
        for label in one_map:
            if label not in labels:
                labels.append(label)

    combined: dict[str, LabelCount] = {}
    for label in labels:
        minimum = min((one_map[label].min if label in one_map else 0) for one_map in maps)
        maximum = max((one_map[label].max if label in one_map else 0) for one_map in maps)
        combined[label] = LabelCount.of(minimum, maximum)
    return combined


def _arities_for_item(item: gsm.Item, rule_name: str, idx: int) -> dict[str, LabelCount]:
    context = f"rule {rule_name!r} item {idx}"
    if item.disposition == gsm.Disposition.INLINE:
        msg = f"{INLINE_NOT_EXPANDED_MSG} ({context})"
        raise ValueError(msg)
    if item.disposition == gsm.Disposition.SUPPRESS:
        # Suppressed items never reach `children`, so they contribute no labels.
        return {}

    counts: dict[str, LabelCount]
    if isinstance(item.term, gsm.Identifier | gsm.Literal | gsm.Regex | gsm.Invocation):
        counts = {item.label: LabelCount(min=1, max=1)} if item.label is not None else {}
    elif isinstance(item.term, Sequence):
        if item.label is not None:
            msg = (
                f"Label {item.label!r} on a sub-expression item in {context} is not supported: "
                f"a sub-expression contributes its inner labels to the parent, so there is no "
                f"single child for the outer label to name."
            )
            raise ValueError(msg)
        counts = combine_alternatives([arities_for_alternative(alt, rule_name) for alt in item.term])
    else:
        msg = f"Unsupported term type {type(item.term).__name__} in {context}"
        raise ValueError(msg)

    return {label: _quantify(count, item.quantifier) for label, count in counts.items()}


def arities_for_alternative(items: gsm.Items, rule_name: str) -> dict[str, LabelCount]:
    """Return each label's multiplicity within a single alternative.

    The per-alternative view keeps the distinctions ``compute_label_arities`` folds away
    when it combines alternatives: a label required in one alternative and absent from
    another is required here and optional there.

    Raises ``ValueError`` for an INLINE item (expand the grammar first) and for a labeled
    sub-expression item.
    """
    counts: dict[str, LabelCount] = {}
    for idx, item in enumerate(items.items):
        counts = _combine_sequence(counts, _arities_for_item(item, rule_name, idx))
    return counts


def compute_label_arities(rule: gsm.Rule) -> Mapping[str, LabelCount]:
    """Return each label's whole-rule multiplicity.

    The analysis is rule-local: labels come only from the rule's own items and its nested
    sub-expressions.  A rule-reference item contributes that item's label, never the
    referenced rule's internals.

    Raises ``ValueError`` for an INLINE item (expand the grammar first) and for a labeled
    sub-expression item.
    """
    return combine_alternatives([arities_for_alternative(alt, rule.name) for alt in rule.alternatives])


# --- Member planning -------------------------------------------------------------------

# Fixed member names on the Python-visible node classes (Python backend dataclasses and
# Rust handle pymethods alike).
_PYTHON_FIXED_MEMBERS = frozenset(
    {
        "append",
        "extend",
        "extend_children",
        "child",
        "insert",
        "remove_at",
        "replace_at",
        "clear",
        "span",
        "kind",
        "children",
        "Label",
        "_check_child_type_for_mutators",
        "_check_label_type_for_mutators",
        "_LABELS_BY_CANONICAL_NAME",
        "_children_snapshot",
    }
)

# Fixed method names on the Rust native data struct.
_RUST_NATIVE_FIXED_MEMBERS = frozenset(
    {
        "new",
        "set_span",
        "push_child",
        "insert_child",
        "remove_child",
        "replace_child",
        "clear_children",
    }
)

# Fixed method names on the Rust handle struct.
_RUST_HANDLE_FIXED_MEMBERS = frozenset({"shared", "to_py_canonical", "py_children_snapshot"})

# Trait methods callable on the generated Rust structs, either through a derive (`Clone`,
# `Debug`, `PartialEq`) or through a blanket impl (`Into`, `Borrow`, `ToOwned`, `TryInto`,
# `Any`).  An inherent method takes precedence over a trait method in method-call syntax, so
# emitting `pub fn clone(&self) -> &Span` would silently redirect `node.clone()` away from
# `Clone::clone` for every downstream caller.
_RUST_TRAIT_METHODS = frozenset(
    {
        "as_ref",
        "borrow",
        "borrow_mut",
        "clone",
        "drop",
        "eq",
        "fmt",
        "hash",
        "into",
        "ne",
        "to_owned",
        "try_into",
        "type_id",
    }
)

# Rule-level ergonomic members.  Reserved unconditionally — including for rules that do
# not get them — so that a label's eligibility does not depend on the rule's shape.
RULE_MEMBER_NAMES = frozenset({"text", "variant"})

RESERVED_MEMBER_NAMES = frozenset(
    _PYTHON_FIXED_MEMBERS
    | _RUST_NATIVE_FIXED_MEMBERS
    | _RUST_HANDLE_FIXED_MEMBERS
    | _RUST_TRAIT_METHODS
    | RULE_MEMBER_NAMES
)

# Rust keywords that a method name must be escaped as a raw identifier (`r#type`) to use.
RUST_KEYWORDS = frozenset(
    {
        "abstract",
        "as",
        "async",
        "await",
        "become",
        "box",
        "break",
        "const",
        "continue",
        "do",
        "dyn",
        "else",
        "enum",
        "extern",
        "false",
        "final",
        "fn",
        "for",
        "gen",
        "if",
        "impl",
        "in",
        "let",
        "loop",
        "macro",
        "match",
        "mod",
        "move",
        "mut",
        "override",
        "priv",
        "pub",
        "ref",
        "return",
        "static",
        "struct",
        "trait",
        "true",
        "try",
        "type",
        "typeof",
        "unsafe",
        "unsized",
        "use",
        "virtual",
        "where",
        "while",
        "yield",
    }
)

# Rust keywords that cannot be written as raw identifiers at all.
RUST_UNRAWABLE_KEYWORDS = frozenset({"crate", "self", "super", "Self", "_"})

_QUINTET_PREFIXES = ("append_", "extend_", "children_", "child_", "maybe_")


def rust_method_ident(name: str) -> str:
    """Return ``name`` spelled as a usable Rust method identifier."""
    return f"r#{name}" if name in RUST_KEYWORDS else name


def quintet_member_names(label: str) -> tuple[str, ...]:
    """The five existing per-label accessor names generated for ``label``."""
    return tuple(f"{prefix}{label}" for prefix in _QUINTET_PREFIXES)


class MemberKind(enum.Enum):
    BARE_ACCESSOR = "bare accessor"
    TEXT_ACCESSOR = "label text accessor"


@dataclasses.dataclass(frozen=True, slots=True)
class SkippedMember:
    """A candidate member that was not emitted, and why."""

    name: str
    kind: MemberKind
    label: str
    reason: str


@dataclasses.dataclass(frozen=True)
class RulePlan:
    """Which ergonomic members a rule's node class gets, on every backend."""

    bare_accessors: Mapping[str, ArityClass]
    text_accessors: Mapping[str, ArityClass]
    rule_text: bool
    variant: bool
    skipped: Sequence[SkippedMember]


def is_span_model_type(model_type: ModelType) -> bool:
    """True for the model type standing in for a terminal's span."""
    return not isinstance(model_type, str) and model_type.cname == "Span"


def rule_is_terminal_only(model: ItemsModel) -> bool:
    """True when a rule's children are terminals only.

    The ``_trivia`` child type injected for any rule with whitespace separators is ignored:
    the rule-level text accessor reads the node's own span, which is well defined whether or
    not trivia children are captured.
    """
    return all(model_type == gsm.TRIVIA_RULE_NAME for model_type in model.types if isinstance(model_type, str))


def rule_has_variant_discriminant(rule: gsm.Rule) -> bool:
    """True when a rule is a pure dispatch over alternatives.

    That is: two or more alternatives, each of which is exactly one required, included,
    labeled item.  The node then always has exactly one labeled child, and its label
    identifies which alternative matched.
    """
    if len(rule.alternatives) < _MANY:
        return False
    for alternative in rule.alternatives:
        if len(alternative.items) != 1:
            return False
        item = alternative.items[0]
        if item.label is None or item.disposition != gsm.Disposition.INCLUDE:
            return False
        if item.quantifier.min() != gsm.Arity.ONE or item.quantifier.max() != gsm.Arity.ONE:
            return False
    return True


def _unusable_name_reason(name: str) -> str | None:
    """Why ``name`` cannot be a generated method name on both backends, or None."""
    if name.startswith("__"):
        return (
            "names starting with '__' are subject to Python private name mangling and would override dataclass dunders"
        )
    if keyword.iskeyword(name):
        return "it is a Python keyword"
    if name in RUST_UNRAWABLE_KEYWORDS:
        return "it is a Rust keyword that cannot be written as a raw identifier"
    return None


def _skip_log_level(member: SkippedMember) -> int:
    """Severity for reporting a skipped candidate member.

    A label that happens to share a name with one of the node class's fixed members
    (``text``, ``span``, ``children``, ...) is the routine case — a grammar cannot avoid it
    except by renaming the label, and the surviving members are still emitted, so it reports
    at INFO.  Everything else — a collision with another label's quintet accessor, a
    ``__``-leading label, a keyword label — is rare enough to be worth a WARNING.
    """
    if member.name in RESERVED_MEMBER_NAMES:
        return logging.INFO
    return logging.WARNING


def _claim(
    name: str,
    kind: MemberKind,
    label: str,
    claimed: dict[str, str],
    skipped: list[SkippedMember],
    *,
    description: str,
) -> bool:
    """Claim ``name`` for a candidate member, or record why it was skipped."""
    reason = _unusable_name_reason(name)
    if reason is None:
        owner = claimed.get(name)
        if owner is not None:
            reason = f"the name is already taken by {owner}"
    if reason is not None:
        skipped.append(SkippedMember(name=name, kind=kind, label=label, reason=reason))
        return False
    claimed[name] = description
    return True


def plan_rule(rule: gsm.Rule, model: ItemsModel) -> RulePlan:
    """Decide the ergonomic members for one rule.

    Candidate names are claimed in a fixed order — the rule-level members first, then per
    label in sorted order the bare accessor followed by its text accessor — against the
    reserved fixed members and the full quintet name set for every label of the rule.  A
    candidate that loses is skipped and logged, never renamed, so that adding these members
    cannot break a grammar that generates today.
    """
    arities = compute_label_arities(rule)
    labels = sorted(model.labels)
    missing = [label for label in labels if label not in arities]
    if missing:
        msg = f"Rule {rule.name!r} model carries labels with no arity information: {missing!r}"
        raise ValueError(msg)

    claimed: dict[str, str] = dict.fromkeys(RESERVED_MEMBER_NAMES, "an existing member of the generated node class")
    for label in labels:
        for name in quintet_member_names(label):
            claimed[name] = f"the {name}() accessor for label {label!r}"

    skipped: list[SkippedMember] = []
    bare_accessors: dict[str, ArityClass] = {}
    text_accessors: dict[str, ArityClass] = {}

    for label in labels:
        arity = arities[label].arity_class
        if _claim(
            label,
            MemberKind.BARE_ACCESSOR,
            label,
            claimed,
            skipped,
            description=f"the {label}() accessor",
        ):
            bare_accessors[label] = arity

        if arity in SINGLE_ARITIES and _label_is_span_only(model, label):
            name = f"{label}_text"
            if _claim(
                name,
                MemberKind.TEXT_ACCESSOR,
                label,
                claimed,
                skipped,
                description=f"the {name}() accessor",
            ):
                text_accessors[label] = arity

    for member in skipped:
        logger.log(
            _skip_log_level(member),
            "Rule %r: skipping %s %s() for label %r: %s",
            rule.name,
            member.kind.value,
            member.name,
            member.label,
            member.reason,
        )

    return RulePlan(
        bare_accessors=bare_accessors,
        text_accessors=text_accessors,
        rule_text=rule_is_terminal_only(model),
        variant=rule_has_variant_discriminant(rule),
        skipped=skipped,
    )


def _label_is_span_only(model: ItemsModel, label: str) -> bool:
    types = model.labels[label]
    return len(types) == 1 and is_span_model_type(next(iter(types)))
