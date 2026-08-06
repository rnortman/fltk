//! Folding a rule's operands into a binary chain, for the generated `from_cst` converters.
//!
//! A grammar spells a precedence level as `operand , (op , operand)*`, which the CST records as a
//! flat run of children. The AST shape is the nested one: a bare operand, or a link joining two
//! sub-chains. Generated code collects the operands with their own spans and the operators, then
//! hands both to [`fold_left`] or [`fold_right`] along with two closures — one wrapping an operand
//! as the rule's own type, one building a link — because those are the only parts that name
//! generated types.
//!
//! The loop lives here rather than in the emitters so the nesting order, the span merging and the
//! diagnostics are one implementation. Each helper has a counterpart of the same name in
//! `fltk.fegen.pyrt.astrt`, and the message templates are one text under the translation
//! `tests/test_ast_error_message_parity.py` enforces.
//!
//! A parser-produced CST always interleaves as the grammar says, so the arity failure is
//! reachable only from a hand-built or mutated one, and the source-mismatch failure only from one
//! whose operands were parsed from different sources. [`fold_left`] and [`fold_right`] check the
//! interleaving themselves, so a caller who has not run [`check_fold_arity`] over its own runs —
//! anything but a generated converter, which checks against the CST node's span first — gets the
//! same diagnostic rather than a chain with values quietly dropped from it.

use fltk_cst_core::Span;

use crate::error::AstError;

/// A node with no operand at all, which no fold can reduce.
fn no_operands(rule: &str, span: &Span) -> AstError {
    AstError::new(
        format!("rule {rule:?}: a fold needs at least one operand, but the node has none"),
        span.clone(),
    )
}

/// Check the interleaving a fold rule's grammar fixes: one operator between each operand pair.
pub fn check_fold_arity(operands: usize, operators: usize, rule: &str, span: &Span) -> Result<(), AstError> {
    if operands < 1 {
        return Err(no_operands(rule, span));
    }
    if operators != operands - 1 {
        return Err(AstError::new(
            format!(
                "rule {rule:?}: a fold over {operands} operand(s) needs {} operator(s), but the node has {operators}",
                operands - 1
            ),
            span.clone(),
        ));
    }
    Ok(())
}

/// A chain nested against the fold's own direction, which the grammar has no shape for.
///
/// `side` is the side of a link that holds the offending sub-chain: a `fold_left` rule nests to the
/// left, so a link in a link's `rhs` cannot be unfolded back into the alternating item run.
pub fn against_direction(rule: &str, side: &str) -> AstError {
    AstError::new(
        format!(
            "rule {rule:?}: this fold nests the other way, so the {side} operand of a link cannot itself be a chain — the grammar has no shape to render it as; rebuild the chain in the fold's own direction"
        ),
        Span::unknown(),
    )
}

/// The span covering both sides of one link.
fn merge(left: &Span, right: &Span, rule: &str) -> Result<Span, AstError> {
    left.merge(right).map_err(|_| {
        AstError::new(
            format!("rule {rule:?}: the operands of a fold come from different sources, so their spans cannot merge"),
            left.clone(),
        )
    })
}

/// Left-nest a fold rule's operands: `a op b op c` becomes `(a op b) op c`.
///
/// Each operand arrives with its own CST span, in source order; every synthesized link carries the
/// merge of everything below it. A single operand comes back wrapped by `operand` and nothing
/// else, so the link type appears only where the grammar actually repeated. `span` is the whole
/// node's, used for the arity diagnostic, which has no operand to point at.
///
/// The interleaving is checked here: one operator between each operand pair, or [`AstError`].
pub fn fold_left<T, O, V>(
    rule: &str,
    span: &Span,
    operands: Vec<(T, Span)>,
    operators: Vec<O>,
    operand: impl Fn(T) -> V,
    link: impl Fn(O, V, V, Span) -> V,
) -> Result<V, AstError> {
    check_fold_arity(operands.len(), operators.len(), rule, span)?;
    let mut rest = operands.into_iter();
    let (first, first_span) = rest.next().expect("the arity check leaves at least one operand");
    let mut value = operand(first);
    let mut covered = first_span;
    for ((next, next_span), operator) in rest.zip(operators) {
        covered = merge(&covered, &next_span, rule)?;
        value = link(operator, value, operand(next), covered.clone());
    }
    Ok(value)
}

/// Right-nest a fold rule's operands: `a op b op c` becomes `a op (b op c)`.
///
/// The interleaving is checked here, as in [`fold_left`].
pub fn fold_right<T, O, V>(
    rule: &str,
    span: &Span,
    operands: Vec<(T, Span)>,
    operators: Vec<O>,
    operand: impl Fn(T) -> V,
    link: impl Fn(O, V, V, Span) -> V,
) -> Result<V, AstError> {
    check_fold_arity(operands.len(), operators.len(), rule, span)?;
    let mut rest = operands;
    let (last, last_span) = rest.pop().expect("the arity check leaves at least one operand");
    let mut value = operand(last);
    let mut covered = last_span;
    for ((previous, previous_span), operator) in rest.into_iter().rev().zip(operators.into_iter().rev()) {
        covered = merge(&previous_span, &covered, rule)?;
        value = link(operator, operand(previous), value, covered.clone());
    }
    Ok(value)
}

#[cfg(test)]
mod tests {
    use fltk_cst_core::SourceText;

    use super::*;

    /// A stand-in for a generated fold pair: the enum's two variants over one operand type.
    #[derive(Debug, PartialEq)]
    enum Chain {
        Operand(i64),
        Link(Box<Link>),
    }

    #[derive(Debug, PartialEq)]
    struct Link {
        op: char,
        lhs: Chain,
        rhs: Chain,
        span: Span,
    }

    fn operand(value: i64) -> Chain {
        Chain::Operand(value)
    }

    fn link(op: char, lhs: Chain, rhs: Chain, span: Span) -> Chain {
        Chain::Link(Box::new(Link { op, lhs, rhs, span }))
    }

    /// One source holding `1+2+3`, so operand spans are the digit positions in it.
    fn source() -> SourceText {
        SourceText::from_str("1+2+3", None)
    }

    fn operands(count: usize) -> Vec<(i64, Span)> {
        let source = source();
        (0..count)
            .map(|index| {
                let start = i64::try_from(index * 2).expect("index fits");
                (
                    i64::try_from(index + 1).expect("index fits"),
                    Span::new_with_source(start, start + 1, &source),
                )
            })
            .collect()
    }

    fn span() -> Span {
        Span::unknown()
    }

    #[test]
    fn a_lone_operand_is_not_wrapped_in_a_link() {
        let folded = fold_left("expr", &span(), operands(1), Vec::<char>::new(), operand, link);
        assert_eq!(folded, Ok(Chain::Operand(1)));
        let folded = fold_right("expr", &span(), operands(1), Vec::<char>::new(), operand, link);
        assert_eq!(folded, Ok(Chain::Operand(1)));
    }

    #[test]
    fn a_left_fold_nests_the_earlier_operands_deeper() {
        let folded = fold_left("expr", &span(), operands(3), vec!['+', '-'], operand, link).expect("three operands");
        let Chain::Link(outer) = folded else {
            panic!("three operands fold into a link");
        };
        assert_eq!(outer.op, '-');
        assert_eq!(outer.rhs, Chain::Operand(3));
        let Chain::Link(inner) = outer.lhs else {
            panic!("the left side of a left fold is the deeper chain");
        };
        assert_eq!(inner.op, '+');
        assert_eq!(inner.lhs, Chain::Operand(1));
        assert_eq!(inner.rhs, Chain::Operand(2));
    }

    #[test]
    fn a_right_fold_nests_the_later_operands_deeper() {
        let folded = fold_right("expr", &span(), operands(3), vec!['+', '-'], operand, link).expect("three operands");
        let Chain::Link(outer) = folded else {
            panic!("three operands fold into a link");
        };
        assert_eq!(outer.op, '+');
        assert_eq!(outer.lhs, Chain::Operand(1));
        let Chain::Link(inner) = outer.rhs else {
            panic!("the right side of a right fold is the deeper chain");
        };
        assert_eq!(inner.op, '-');
        assert_eq!(inner.lhs, Chain::Operand(2));
        assert_eq!(inner.rhs, Chain::Operand(3));
    }

    #[test]
    fn each_link_covers_everything_below_it() {
        let folded = fold_left("expr", &span(), operands(3), vec!['+', '-'], operand, link).expect("three operands");
        let Chain::Link(outer) = folded else {
            panic!("three operands fold into a link");
        };
        // "1+2+3": the outer link spans all five characters, the inner one the first three.
        assert_eq!((outer.span.start(), outer.span.end()), (0, 5));
        let Chain::Link(inner) = &outer.lhs else {
            panic!("the left side is the deeper chain");
        };
        assert_eq!((inner.span.start(), inner.span.end()), (0, 3));
        assert_eq!(outer.span.text().as_deref(), Some("1+2+3"));
    }

    #[test]
    fn a_right_fold_merges_the_same_extents() {
        let folded = fold_right("expr", &span(), operands(3), vec!['+', '-'], operand, link).expect("three operands");
        let Chain::Link(outer) = folded else {
            panic!("three operands fold into a link");
        };
        assert_eq!((outer.span.start(), outer.span.end()), (0, 5));
        let Chain::Link(inner) = &outer.rhs else {
            panic!("the right side is the deeper chain");
        };
        assert_eq!((inner.span.start(), inner.span.end()), (2, 5));
    }

    #[test]
    fn a_node_with_no_operand_names_the_rule() {
        assert_eq!(
            check_fold_arity(0, 0, "expr", &span()).unwrap_err().message,
            "rule \"expr\": a fold needs at least one operand, but the node has none"
        );
        let folded = fold_left("expr", &span(), Vec::<(i64, Span)>::new(), Vec::<char>::new(), operand, link);
        assert_eq!(
            folded.unwrap_err().message,
            "rule \"expr\": a fold needs at least one operand, but the node has none"
        );
        let folded = fold_right("expr", &span(), Vec::<(i64, Span)>::new(), Vec::<char>::new(), operand, link);
        assert!(folded.is_err());
    }

    #[test]
    fn a_fold_refuses_a_run_the_interleaving_does_not_fit() {
        // Neither surplus is dropped to fit the shorter run: a chain missing an operand — or an
        // operator — is not the value the caller handed over.
        let surplus_operators = fold_left("expr", &span(), operands(2), vec!['+', '-'], operand, link);
        assert_eq!(
            surplus_operators.unwrap_err().message,
            "rule \"expr\": a fold over 2 operand(s) needs 1 operator(s), but the node has 2"
        );
        let surplus_operands = fold_left("expr", &span(), operands(3), vec!['+'], operand, link);
        assert_eq!(
            surplus_operands.unwrap_err().message,
            "rule \"expr\": a fold over 3 operand(s) needs 2 operator(s), but the node has 1"
        );
        let surplus_operators = fold_right("expr", &span(), operands(2), vec!['+', '-'], operand, link);
        assert!(surplus_operators.is_err());
        let surplus_operands = fold_right("expr", &span(), operands(3), vec!['+'], operand, link);
        assert!(surplus_operands.is_err());
    }

    #[test]
    fn the_operator_count_has_to_sit_between_the_operands() {
        assert_eq!(check_fold_arity(1, 0, "expr", &span()), Ok(()));
        assert_eq!(check_fold_arity(3, 2, "expr", &span()), Ok(()));
        assert_eq!(
            check_fold_arity(3, 1, "expr", &span()).unwrap_err().message,
            "rule \"expr\": a fold over 3 operand(s) needs 2 operator(s), but the node has 1"
        );
        assert_eq!(
            check_fold_arity(1, 4, "expr", &span()).unwrap_err().message,
            "rule \"expr\": a fold over 1 operand(s) needs 0 operator(s), but the node has 4"
        );
    }

    #[test]
    fn operands_from_two_sources_cannot_be_covered_by_one_span() {
        let other = SourceText::from_str("9", None);
        let mut mixed = operands(2);
        mixed[1].1 = Span::new_with_source(0, 1, &other);
        let error = fold_left("expr", &span(), mixed, vec!['+'], operand, link).unwrap_err();
        assert_eq!(
            error.message,
            "rule \"expr\": the operands of a fold come from different sources, so their spans cannot merge"
        );
    }

    #[test]
    fn a_long_chain_folds_without_recursing() {
        // The loop is iterative; only the eventual drop of the chain is not, which is why this
        // stays at a depth ordinary drop glue survives.
        let count = 1000;
        let operators = vec!['+'; count - 1];
        let folded = fold_left("expr", &span(), operands(count), operators, operand, link).expect("a long chain");
        let mut depth = 0;
        let mut node = &folded;
        while let Chain::Link(current) = node {
            depth += 1;
            node = &current.lhs;
        }
        assert_eq!(depth, count - 1);
        assert_eq!(node, &Chain::Operand(1));
    }
}
