"""Labeled-literal analysis shared by the two unparser generators.

A label is a statement about semantic content: labeling a literal encodes a distinction the
parser is responsible for, and application code recovers that distinction from the label,
never from the literal's text.  The spellings each label carries
(``fltk.fegen.grammar_shape.label_literals``) are grammar analysis the AST model shares; the
refusal here is the unparser's own policy, and both unparser generators (Python and Rust)
read it from this one implementation:

``check_labeled_literal_texts``
    Refuses the one mechanically fishy shape: a label that is always present, carries
    literals only, and covers more than one spelling.  Such a label records a bare position
    in the CST while its author almost certainly expected the written word to survive.

It takes a grammar whose INLINE items have already been expanded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fltk.fegen import cst_ergonomics as ce
from fltk.fegen.grammar_shape import label_literals

if TYPE_CHECKING:
    from fltk.fegen import gsm

# Two spellings under one always-present label is the shape check_labeled_literal_texts refuses.
MIN_SPELLINGS = 2


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
