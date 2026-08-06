"""Labeled-literal analysis shared by the two unparser generators.

A label is a statement about semantic content: labeling a literal encodes a distinction the
parser is responsible for, and application code recovers that distinction from the label,
never from the literal's text.  Two consequences live here, and both unparser generators
(Python and Rust) read them from this one implementation:

``label_literals``
    The spellings each label of a rule carries.  Alternative spellings under one label
    (``gray:"gray" | gray:"grey"``) declare the spellings equivalent, so trial matching
    accepts a span child whose text is any of them while rendering still emits the
    grammar's first spelling.

``check_labeled_literal_texts``
    Refuses the one mechanically fishy shape: a label that is always present, carries
    literals only, and covers more than one spelling.  Such a label records a bare position
    in the CST while its author almost certainly expected the written word to survive.

Both take a grammar whose INLINE items have already been expanded.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from fltk.fegen import cst_ergonomics as ce
from fltk.fegen import gsm
from fltk.fegen.grammar_shape import visit_included_items

if TYPE_CHECKING:
    from collections.abc import Mapping

# Two spellings under one always-present label is the shape check_labeled_literal_texts refuses.
MIN_SPELLINGS = 2


@dataclasses.dataclass(frozen=True, slots=True)
class LabelLiterals:
    """The literal spellings one label of a rule carries."""

    texts: tuple[str, ...]
    """The label's distinct literal texts, in grammar order; the first is the canonical one."""

    literal_only: bool
    """True when no other kind of term carries the label."""


def label_literals(rule: gsm.Rule) -> Mapping[str, LabelLiterals]:
    """Every label of ``rule`` that a literal term carries, with that label's spellings.

    Labels are rule-scoped — a sub-expression's children are inlined into the rule's own node
    — so the walk covers every alternative at every INCLUDE sub-expression depth.  A label
    carried by no literal at all is absent from the result.
    """
    texts: dict[str, list[str]] = {}
    other_kinds: set[str] = set()

    def visit(item: gsm.Item) -> None:
        if item.label is None:
            return
        if isinstance(item.term, gsm.Literal):
            spellings = texts.setdefault(item.label, [])
            if item.term.value not in spellings:
                spellings.append(item.term.value)
        else:
            other_kinds.add(item.label)

    for alternative in rule.alternatives:
        visit_included_items(alternative, visit)

    return {
        label: LabelLiterals(texts=tuple(spellings), literal_only=label not in other_kinds)
        for label, spellings in texts.items()
    }


def spellings_for(rule: gsm.Rule, item: gsm.Item) -> tuple[str, ...]:
    """The literal texts a labeled literal item's span child may carry.

    The item's own text is always in the set; a label shared with other literal items adds
    their spellings, because a shared label declares the spellings equivalent.  An unlabeled
    literal carries no semantic content — its spellings are equivalent by definition and
    text-checking one would break keyword evolution — so it gets an empty set, which callers
    read as "emit no text check".

    ``rule`` is the rule ``item`` belongs to, so ``label_literals`` always knows the label:
    narrowing a multi-spelling label to one spelling would make every sibling spelling fail
    the trial, so a lookup that cannot succeed is a defect rather than something to absorb.
    """
    if item.label is None or not isinstance(item.term, gsm.Literal):
        return ()
    return label_literals(rule)[item.label].texts


def check_labeled_literal_texts(grammar: gsm.Grammar) -> None:
    """Refuse a grammar whose labeled literals expect their spelling to survive unparsing.

    Raises ``RuntimeError`` for a label that is (a) always present (its whole-rule count has
    a minimum of one), (b) carried only by literal terms, and (c) written with two or more
    distinct texts.  The CST records which position matched, never which text, so no
    formatter can reproduce the spelling the author wrote — and the AST field for such a
    label is a bare position too.  A label that is sometimes absent is left alone: their
    presence is the datum and several spellings are legitimate.
    """
    for rule in grammar.rules:
        try:
            arities = ce.compute_label_arities(rule)
        except ValueError:
            # A labeled sub-expression has no per-label count, so the shape cannot be judged;
            # leave the rule exactly as the generators already handle it.
            continue
        for label, literals in label_literals(rule).items():
            if not literals.literal_only or len(literals.texts) < MIN_SPELLINGS:
                continue
            count = arities.get(label)
            if count is None or count.min < 1:
                continue
            spellings = ", ".join(repr(text) for text in literals.texts)
            msg = (
                f"Cannot generate unparser for rule {rule.name!r}: label {label!r} is always present, "
                f"is carried only by literals, and covers more than one spelling ({spellings}). "
                f"The CST records which position matched, never which text, so the spelling the "
                f"author wrote cannot be reproduced. If the spellings mean the same thing, remove "
                f"the label; if they are distinct values, give each its own label "
                f'(e.g. `yes:"yes" | no:"no"`, optionally as a rule of its own).'
            )
            raise RuntimeError(msg)
