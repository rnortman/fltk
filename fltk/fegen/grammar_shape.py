"""Grammar-shape analysis shared by the AST model, the ``.fltkast`` validator, and the
unparse subsystem's labeled-literal analysis (``fltk.unparse.literal_labels``).

Everything here is a pure function of an INLINE-expanded, trivia-classified GSM grammar:
which child kinds a label can carry, whether two alternatives are told apart by their
labeled children, and which of the four node forms a rule falls into.

The sidecar validator and the model both need these answers — the validator to reject an
annotation against the shape it does not apply to, the model to emit that shape — and they
must give the same answer, so the analysis lives in one place that neither imports from
the other.
"""

from __future__ import annotations

import dataclasses
import enum
import math
from collections.abc import Sequence
from typing import TYPE_CHECKING

from fltk.fegen import cst_ergonomics as ce
from fltk.fegen import gsm

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

# Child-kind sentinel for a span child (a literal or regex terminal).  Every other child
# kind is the name of the referenced rule.
TEXT_KIND = "#text"

# ``LabelCount`` saturates both bounds here; a max of 2 means "unbounded".
_SATURATED = 2

MIN_ALTERNATIVES = 2


# --- Walking a rule's included items -----------------------------------------------------


def visit_included_items(items: gsm.Items, visitor: Callable[[gsm.Item], None]) -> None:
    """Call ``visitor(item)`` for every INCLUDE item, descending into INCLUDE sub-expressions.

    Suppressed sub-expressions contribute no children, so the walk does not enter them.
    """
    for item in items.items:
        if item.disposition == gsm.Disposition.INLINE:
            msg = f"{ce.INLINE_NOT_EXPANDED_MSG} (item {item!r})"
            raise ValueError(msg)
        if item.disposition != gsm.Disposition.INCLUDE:
            continue
        if isinstance(item.term, gsm.Identifier | gsm.Literal | gsm.Regex | gsm.Invocation):
            visitor(item)
        elif isinstance(item.term, Sequence):
            for alternative in item.term:
                visit_included_items(alternative, visitor)


def label_terms(items: gsm.Items) -> dict[str, tuple[gsm.Term, ...]]:
    """Every labeled INCLUDE term of one alternative, grouped by label in source order."""
    collected: dict[str, list[gsm.Term]] = {}

    def visit(item: gsm.Item) -> None:
        if item.label is not None:
            collected.setdefault(item.label, []).append(item.term)

    visit_included_items(items, visit)
    return {label: tuple(terms) for label, terms in collected.items()}


def child_kind(term: gsm.Term) -> str:
    """The ``NodeKind`` a term's child carries, or ``TEXT_KIND`` for a span child."""
    return term.value if isinstance(term, gsm.Identifier) else TEXT_KIND


def rule_has_identifier_term(rule: gsm.Rule) -> bool:
    """True when some item of the rule references another rule, at any depth."""
    found = False

    def visit(_idx: int, item: gsm.Item) -> None:
        nonlocal found
        if isinstance(item.term, gsm.Identifier):
            found = True

    for alternative in rule.alternatives:
        gsm.for_each_item(alternative, visit)
    return found


def rule_has_regex_term(rule: gsm.Rule) -> bool:
    """True when some item of the rule matches a regex, at any depth.

    A rule whose terminals are all literals carries no text of its own: its span is a grammar
    constant modulo whitespace, so a ``text`` field on it would hold formatting rather than
    data.  Such a rule is therefore not terminal-only.
    """
    found = False

    def visit(_idx: int, item: gsm.Item) -> None:
        nonlocal found
        if isinstance(item.term, gsm.Regex):
            found = True

    for alternative in rule.alternatives:
        gsm.for_each_item(alternative, visit)
    return found


def rule_is_enum_shaped(rule: gsm.Rule) -> bool:
    """Two or more alternatives, each exactly one required, included, labeled literal."""
    return ce.rule_has_variant_discriminant(rule) and all(
        isinstance(alternative.items[0].term, gsm.Literal) for alternative in rule.alternatives
    )


def has_whitespace_separator(items: gsm.Items) -> bool:
    """True when some separator inside ``items`` permits trivia, at any sub-expression depth.

    A rule's span covers everything its items matched, sub-expressions included, so trivia
    admitted anywhere inside it lands in the node's text.
    """
    if any(separator != gsm.Separator.NO_WS for separator in (items.initial_sep, *items.sep_after)):
        return True
    return any(
        isinstance(item.term, Sequence) and any(has_whitespace_separator(alternative) for alternative in item.term)
        for item in items.items
    )


@dataclasses.dataclass(frozen=True, slots=True)
class LabelSignature:
    count: ce.LabelCount
    kinds: frozenset[str]


@dataclasses.dataclass(frozen=True, slots=True)
class AltSignature:
    """What one alternative's labeled children look like, for dispatch and shape tests."""

    labels: Mapping[str, LabelSignature]


def label_bounds(signature: LabelSignature | None) -> tuple[int, float]:
    """The label's (low, high) occurrence bounds; an absent label is exactly zero.

    ``LabelCount`` saturates its upper bound, so a maximum of two means "unbounded"; this is
    the one place that reading is applied.
    """
    if signature is None:
        return (0, 0)
    high = math.inf if signature.count.max >= _SATURATED else signature.count.max
    return (signature.count.min, high)


def _counts_intersect(left: LabelSignature | None, right: LabelSignature | None) -> bool:
    low_left, high_left = label_bounds(left)
    low_right, high_right = label_bounds(right)
    return low_left <= high_right and low_right <= high_left


# TODO(ast-dispatch-order): use child order to tell two alternatives apart as well.
def alternatives_are_disjoint(left: AltSignature, right: AltSignature) -> bool:
    """True when some label tells the two alternatives apart in the CST.

    Either the label's occurrence counts cannot both be satisfied, or the label is
    required in both alternatives with disjoint child kinds.  The test cannot use child
    order, so it is an over-approximation of indistinguishability: alternatives that
    differ only in the order of the same labels read as non-disjoint.
    """
    for label in {*left.labels, *right.labels}:
        one = left.labels.get(label)
        other = right.labels.get(label)
        if not _counts_intersect(one, other):
            return True
        if one is None or other is None:
            continue
        both_required = one.count.min >= 1 and other.count.min >= 1
        if both_required and not (one.kinds & other.kinds):
            return True
    return False


def alternatives_are_subset_shaped(left: AltSignature, right: AltSignature) -> bool:
    """True when one alternative is a strict extension of the other.

    That is: one label set is a strict subset of the other and every shared label is
    compatible (intersecting counts and intersecting kinds).  Such a pair is one shape
    with optional parts rather than a structural fork.
    """
    left_labels = set(left.labels)
    right_labels = set(right.labels)
    if left_labels < right_labels:
        subset, superset = left, right
    elif right_labels < left_labels:
        subset, superset = right, left
    else:
        return False

    for label, shared in subset.labels.items():
        other = superset.labels[label]
        if not _counts_intersect(shared, other) or not (shared.kinds & other.kinds):
            return False
    return True


# --- Rule classification -----------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class AltInfo:
    """One alternative's labels, viewed per-alternative rather than whole-rule."""

    index: int
    items: gsm.Items
    arities: Mapping[str, ce.LabelCount]
    terms: Mapping[str, tuple[gsm.Term, ...]]
    signature: AltSignature


def alt_infos(rule: gsm.Rule, arities: Sequence[Mapping[str, ce.LabelCount]]) -> list[AltInfo]:
    """Per-alternative label information, given the rule's per-alternative arities."""
    infos: list[AltInfo] = []
    for index, alternative in enumerate(rule.alternatives):
        terms = label_terms(alternative)
        signature = AltSignature(
            labels={
                label: LabelSignature(
                    count=arities[index][label],
                    kinds=frozenset(child_kind(term) for term in label_terms_),
                )
                for label, label_terms_ in terms.items()
            }
        )
        infos.append(AltInfo(index=index, items=alternative, arities=arities[index], terms=terms, signature=signature))
    return infos


def alternatives_are_sum(infos: Sequence[AltInfo]) -> bool:
    """Sum iff there are ≥2 alternatives, every pair disjoint and no pair subset-shaped."""
    if len(infos) < MIN_ALTERNATIVES:
        return False
    for index, one in enumerate(infos):
        for other in infos[index + 1 :]:
            if not alternatives_are_disjoint(one.signature, other.signature):
                return False
            if alternatives_are_subset_shaped(one.signature, other.signature):
                return False
    return True


class RuleShape(enum.Enum):
    """Which of the four node forms a rule falls into, before any sidecar override."""

    ENUM = "enum-shaped"

    TERMINAL = "terminal-only"
    """A rule whose children are terminals and at least one of them a regex.

    The regex is what carries data: a rule of literals alone spans a grammar constant, so it
    classifies as a product (a marker product when it has no labels at all) rather than
    growing a ``text`` field that holds whichever separators the parse happened to see.
    """

    SUM = "sum"
    PRODUCT = "product"


def rule_arities(rule: gsm.Rule) -> list[Mapping[str, ce.LabelCount]]:
    """Per-alternative label arities, in grammar order."""
    return [ce.arities_for_alternative(alternative, rule.name) for alternative in rule.alternatives]


def classify_rule(rule: gsm.Rule, arities: Sequence[Mapping[str, ce.LabelCount]] | None = None) -> RuleShape:
    """The node form ``rule`` falls into: enum, terminal, sum, product (first match wins).

    ``arities`` is the rule's per-alternative label counts; a caller that already holds
    them passes them in rather than paying for a second walk.
    """
    if rule_is_enum_shaped(rule):
        return RuleShape.ENUM
    if not rule_has_identifier_term(rule) and rule_has_regex_term(rule):
        return RuleShape.TERMINAL
    if alternatives_are_sum(alt_infos(rule, arities if arities is not None else rule_arities(rule))):
        return RuleShape.SUM
    return RuleShape.PRODUCT
