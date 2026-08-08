//! Which alternative of a sum rule a node's labeled children came from.
//!
//! A CST node records the rule it matched, never the alternative, so a sum rule's converter
//! recovers the alternative by counting the node's labeled children per (label, child kind)
//! pair and taking the first alternative in grammar order whose signature accepts those counts.
//! The counting rule is one thing, described once per rule as a [`Table`] a generated module
//! holds as a `static` and evaluated once here, so every consumer of the same grammar — the AST
//! converters and the serde runtime alike — resolves an alternative the same way.

/// The child kind of a span child: a literal or regex terminal, which references no rule.
pub const TEXT_KIND: &str = "#text";

/// How many pairs a table can have before its per-node counts need the heap.
///
/// Selection runs once per sum node of every conversion, so the counts live in a stack buffer
/// covering the pair counts a grammar realistically produces; a wider table falls back to a
/// `Vec` rather than capping anything.
const INLINE_PAIRS: usize = 16;

/// One (label, child kind) a sum rule's labeled children can fall into.
#[derive(Debug)]
pub struct Pair {
    pub label: &'static str,
    /// The referenced rule's name, or [`TEXT_KIND`] for a span child.
    pub kind: &'static str,
}

/// How many children of one label an alternative accepts.
#[derive(Debug)]
pub struct Bound {
    pub label: &'static str,
    /// The pairs of [`Table::pairs`] whose counts add up to the label's occurrences.
    pub pairs: &'static [usize],
    pub minimum: usize,
    /// [`crate::UNBOUNDED`] where the grammar sets no limit.
    pub maximum: usize,
}

/// What one alternative requires of a node's per-pair child counts.
#[derive(Debug)]
pub struct Alt {
    /// Which alternative this is, in grammar order.
    pub variant: usize,
    /// One per label the alternative constrains; a label it accepts freely is left out.
    pub bounds: &'static [Bound],
    /// Pairs no child may occupy: a label the alternative omits, or a kind it cannot hold.
    pub forbidden: &'static [usize],
}

impl Alt {
    /// Whether one alternative's bounds and forbidden pairs fit the counts a node produced.
    fn fits(&self, counts: &[usize]) -> bool {
        self.bounds.iter().all(|bound| {
            let counted: usize = bound.pairs.iter().map(|index| counts[*index]).sum();
            bound.minimum <= counted && counted <= bound.maximum
        }) && self.forbidden.iter().all(|index| counts[*index] == 0)
    }
}

/// How one sum rule's alternatives are told apart by the labeled children a node carries.
#[derive(Debug)]
pub struct Table {
    pub pairs: &'static [Pair],
    /// The alternatives in grammar order, which is the order they are tried in.
    pub alternatives: &'static [Alt],
}

impl Table {
    /// The alternative a node's children came from, or `None` when none of them fits.
    ///
    /// `children` yields one entry per child in source order: the label the child carries
    /// (`None` for an unlabeled child, which no alternative constrains and which is skipped)
    /// and the kind of child it is. A *labeled* child occupying no pair of the table — a label
    /// no alternative carries, or a kind no alternative accepts under that label — belongs to
    /// no alternative at all, so the node matches none. That case is unreachable from a
    /// parser-produced CST and is what a hand-built one is refused by.
    pub fn select<'a>(&self, children: impl IntoIterator<Item = (Option<&'a str>, &'a str)>) -> Option<usize> {
        let wide = self.pairs.len() > INLINE_PAIRS;
        let mut inline = [0usize; INLINE_PAIRS];
        let mut spilled = if wide { vec![0usize; self.pairs.len()] } else { Vec::new() };
        let counts: &mut [usize] = if wide {
            &mut spilled
        } else {
            &mut inline[..self.pairs.len()]
        };
        for (label, kind) in children {
            let Some(label) = label else { continue };
            let index = self.pairs.iter().position(|pair| pair.label == label && pair.kind == kind)?;
            counts[index] += 1;
        }
        self.alternatives.iter().find(|alt| alt.fits(counts)).map(|alt| alt.variant)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::UNBOUNDED;

    /// `s := a:word . b:other | c:word ;` — one label per alternative, two kinds of child.
    static DISJOINT: Table = Table {
        pairs: &[
            Pair { label: "a", kind: "word" },
            Pair { label: "b", kind: "other" },
            Pair { label: "c", kind: "word" },
        ],
        alternatives: &[
            Alt {
                variant: 0,
                bounds: &[
                    Bound { label: "a", pairs: &[0], minimum: 1, maximum: 1 },
                    Bound { label: "b", pairs: &[1], minimum: 1, maximum: 1 },
                ],
                forbidden: &[2],
            },
            Alt {
                variant: 1,
                bounds: &[Bound { label: "c", pairs: &[2], minimum: 1, maximum: 1 }],
                forbidden: &[0, 1],
            },
        ],
    };

    /// `s := a:word+ . b:other? | a:word ;` — a repeated label, an optional one, and a first
    /// alternative the second is a subset of, so grammar order decides.
    static OVERLAPPING: Table = Table {
        pairs: &[Pair { label: "a", kind: "word" }, Pair { label: "b", kind: "other" }],
        alternatives: &[
            Alt {
                variant: 0,
                bounds: &[
                    Bound { label: "a", pairs: &[0], minimum: 1, maximum: UNBOUNDED },
                    Bound { label: "b", pairs: &[1], minimum: 1, maximum: 1 },
                ],
                forbidden: &[],
            },
            Alt {
                variant: 1,
                bounds: &[Bound { label: "a", pairs: &[0], minimum: 1, maximum: 1 }],
                forbidden: &[1],
            },
        ],
    };

    /// `s := a:word . a:other | b:word ;` — one label carrying two kinds of child under one
    /// alternative, which is what a [`Bound`] spanning several pairs is for.
    static UNION: Table = Table {
        pairs: &[
            Pair { label: "a", kind: "other" },
            Pair { label: "a", kind: "word" },
            Pair { label: "b", kind: "word" },
        ],
        alternatives: &[
            Alt {
                variant: 0,
                bounds: &[Bound { label: "a", pairs: &[0, 1], minimum: 2, maximum: UNBOUNDED }],
                forbidden: &[2],
            },
            Alt {
                variant: 1,
                bounds: &[Bound { label: "b", pairs: &[2], minimum: 1, maximum: 1 }],
                forbidden: &[0, 1],
            },
        ],
    };

    /// More pairs than the inline count buffer holds, so counting spills to the heap.
    static WIDE: Table = Table {
        pairs: &[
            Pair { label: "p0", kind: "word" },
            Pair { label: "p1", kind: "word" },
            Pair { label: "p2", kind: "word" },
            Pair { label: "p3", kind: "word" },
            Pair { label: "p4", kind: "word" },
            Pair { label: "p5", kind: "word" },
            Pair { label: "p6", kind: "word" },
            Pair { label: "p7", kind: "word" },
            Pair { label: "p8", kind: "word" },
            Pair { label: "p9", kind: "word" },
            Pair { label: "p10", kind: "word" },
            Pair { label: "p11", kind: "word" },
            Pair { label: "p12", kind: "word" },
            Pair { label: "p13", kind: "word" },
            Pair { label: "p14", kind: "word" },
            Pair { label: "p15", kind: "word" },
            Pair { label: "p16", kind: "word" },
        ],
        alternatives: &[Alt {
            variant: 0,
            bounds: &[Bound { label: "p16", pairs: &[16], minimum: 1, maximum: 1 }],
            forbidden: &[0],
        }],
    };

    #[test]
    fn a_table_wider_than_the_inline_buffer_counts_the_same_way() {
        assert_eq!(WIDE.select([(Some("p16"), "word")]), Some(0));
        // The last pair still carries its own count, and the forbidden first one still rules the
        // alternative out — neither is lost by spilling.
        assert_eq!(WIDE.select([(Some("p16"), "word"), (Some("p16"), "word")]), None);
        assert_eq!(WIDE.select([(Some("p0"), "word"), (Some("p16"), "word")]), None);
    }

    #[test]
    fn each_alternative_is_picked_by_the_labels_it_carries() {
        assert_eq!(DISJOINT.select([(Some("a"), "word"), (Some("b"), "other")]), Some(0));
        assert_eq!(DISJOINT.select([(Some("c"), "word")]), Some(1));
    }

    #[test]
    fn an_unlabeled_child_is_not_counted_against_any_alternative() {
        assert_eq!(
            DISJOINT.select([(None, "word"), (Some("c"), "word"), (None, TEXT_KIND)]),
            Some(1)
        );
    }

    #[test]
    fn a_kind_no_alternative_accepts_under_that_label_matches_nothing() {
        // The label is one both alternatives know; the child under it is not what either holds.
        assert_eq!(DISJOINT.select([(Some("a"), "other")]), None);
    }

    #[test]
    fn a_label_no_alternative_carries_matches_nothing() {
        assert_eq!(DISJOINT.select([(Some("c"), "word"), (Some("z"), "word")]), None);
    }

    #[test]
    fn a_forbidden_pair_rules_its_alternative_out() {
        assert_eq!(
            DISJOINT.select([(Some("a"), "word"), (Some("b"), "other"), (Some("c"), "word")]),
            None
        );
    }

    #[test]
    fn a_missing_required_label_rules_its_alternative_out() {
        assert_eq!(DISJOINT.select([(Some("a"), "word")]), None);
    }

    #[test]
    fn an_unbounded_maximum_accepts_a_run() {
        let children = [(Some("a"), "word"), (Some("a"), "word"), (Some("b"), "other")];
        assert_eq!(OVERLAPPING.select(children), Some(0));
    }

    #[test]
    fn the_first_alternative_that_fits_wins_even_where_a_later_one_would() {
        // Both alternatives accept one `a` and no `b`... except the first requires a `b`.
        assert_eq!(OVERLAPPING.select([(Some("a"), "word")]), Some(1));
    }

    #[test]
    fn counts_over_a_bounds_maximum_rule_it_out() {
        let children = [(Some("a"), "word"), (Some("a"), "word")];
        assert_eq!(OVERLAPPING.select(children), None);
    }

    #[test]
    fn a_bound_over_several_pairs_counts_them_together() {
        // One child of each kind, and two of one kind, both reach the minimum of 2 — which only
        // the sum over the bound's pairs can see. A grammar with a union label produces this
        // shape, so it is reachable from a parser-produced CST and not only a hand-built one.
        assert_eq!(UNION.select([(Some("a"), "word"), (Some("a"), "other")]), Some(0));
        assert_eq!(UNION.select([(Some("a"), "word"), (Some("a"), "word")]), Some(0));
        // One child of either kind counts once, which is short of the minimum, and the second
        // alternative forbids both pairs.
        assert_eq!(UNION.select([(Some("a"), "other")]), None);
        assert_eq!(UNION.select([(Some("b"), "word")]), Some(1));
    }

    #[test]
    fn a_node_with_no_labeled_children_fits_only_an_alternative_that_needs_none() {
        assert_eq!(DISJOINT.select([]), None);
        static FREE: Table = Table {
            pairs: &[Pair { label: "a", kind: "word" }],
            alternatives: &[Alt { variant: 0, bounds: &[], forbidden: &[] }],
        };
        assert_eq!(FREE.select([]), Some(0));
    }
}
