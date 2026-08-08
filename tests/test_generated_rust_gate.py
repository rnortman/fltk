"""The generated Rust compiles, warning-free, and does what the Python backend does.

`tests/test_gsm2ast_rs.py` and `tests/test_rust_unparser_generator.py` assert what the emitters
write; neither asserts that what they write is Rust, or what it does when run. This does: one
crate holding the generated modules for each shape below, checked with
`cargo clippy -- -D warnings` and then `cargo test`. Warnings are denied because the repo's own
gate denies them (CLAUDE.md) and because a downstream consumer building with `-D warnings` gets a
hard failure from one unused binding in a generated file they cannot edit.

The shapes are chosen to reach the branches a source assertion cannot judge: brace placement in
the line-breaking helpers, `Box` on cyclic fields (a missing one is an infinitely-sized type), the
irrefutable-vs-refutable destructure chosen by child-variant count, and the `_child` / `_span`
bindings that exist only to keep the module warning-free. Most shapes go further and run, because
the wiring a generator emits around the runtime helpers — which item position takes which value,
which branch a variant belongs to, which alternative a trial picks — is plain data that compiling
cannot judge: the config language's `from_cst` over a real parse plus the one-call entry points
either side of a round trip through *text*, the fold grammar's nesting, merged spans and unfold,
the leaf forms' text synthesis, the labeled-literal trial matching — whose whole point is a
silent-corruption fix — the flattened wrapper's two hoisted fields, the span-child positions at
every arity, and the merged-product trial with its per-alternative erased and flattened helpers.

Four cases carry the serde frontend as well, three over the same generation inputs as their AST
half: the emitted `de.rs` is a description of the tree written against `fltk-serde-core`'s
vocabulary, and only a compiler says the two halves still agree — a renamed member, a mis-rendered
match arm or a warning that is a hard build failure downstream is invisible to a substring
assertion. The fourth carries no AST module at all, because a `de.rs` generated without one is a
different module and the frontend's headline mode.

One shape is one module, so a case exists per *generation input*: a shape whose grammar and sidecar
match another's belongs in that module, because a case of its own compiles a second copy of the
whole language.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from fltk.fegen import ast_test_grammars as fixtures
from tests.generated_rust_gate import Case, run_cargo, write_crate

# What the config language's converters must actually do, run against a parse of `CONFIG_TEXT`.
CONFIG_RUNTIME = """//! `from_cst` over a real parse of the config language.

use super::ast::{self, Config, MetricTypeValue, Stanza, Value};
use super::cst;
use super::parser::Parser;

const TEXT: &str = r#"
server web {
  host = "localhost";
  port = 8080;
  debug = true;
  tags = [1, 2];
}
metric hits : counter interval 30 ;
"#;

fn parse(text: &str) -> ::fltk_cst_core::Shared<cst::Config> {
    let mut parser = Parser::new(text, None, false);
    let parsed = parser.apply__parse_config(0).expect("the config document must parse");
    assert!(
        parsed.pos as usize == text.len(),
        "the parse must consume the whole document, stopped at {}",
        parsed.pos
    );
    parsed.result
}

fn config(text: &str) -> Config {
    Config::from_cst(&parse(text)).expect("a parser-produced CST must convert")
}

#[test]
fn a_keyed_collection_is_looked_up_by_its_key_field() {
    let parsed = config(TEXT);
    let Stanza::ServerDef(server) = &parsed.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    assert_eq!(server.name, "web");
    assert_eq!(server.settings.len(), 4);
    assert_eq!(server.settings["port"].value, Value::Number(8080));
    assert_eq!(server.settings["host"].value, Value::String("localhost".to_string()));
    assert_eq!(server.settings["debug"].value, Value::Flag(true));
    assert!(matches!(server.settings["tags"].value, Value::List(_)));
    // Insertion order, which is what `IndexMap` is here for.
    assert_eq!(
        server.settings.keys().collect::<Vec<_>>(),
        vec!["host", "port", "debug", "tags"]
    );
}

#[test]
fn an_optional_coerced_field_and_a_value_enum_come_through() {
    let parsed = config(TEXT);
    let Stanza::MetricDef(metric) = &parsed.stanzas[1] else {
        panic!("the second stanza is a metric definition");
    };
    assert_eq!(metric.name, "hits");
    assert_eq!(metric.metric_kind, MetricTypeValue::Counter);
    assert_eq!(metric.interval, Some(30));
}

#[test]
fn two_values_converted_from_identical_text_at_different_offsets_are_equal() {
    let padded = format!("\\n\\n{}", TEXT.trim_start());
    assert_eq!(config(TEXT), config(&padded));
}

#[test]
fn a_difference_in_semantic_data_is_not_equal() {
    let changed = TEXT.replace("8080", "8081");
    assert_ne!(config(TEXT), config(&changed));
}

#[test]
fn a_parsed_value_synthesises_the_cst_it_was_read_from() {
    // The round-trip law at the CST level: what `to_cst` writes is what `from_cst` reads.
    let parsed = config(TEXT);
    let node = parsed.to_cst().expect("a parsed value must synthesise");
    assert_eq!(Config::from_cst(&node).expect("a synthesised CST must convert"), parsed);
}

#[test]
fn a_mutated_value_round_trips_and_keeps_its_map_in_order() {
    let mut parsed = config(TEXT);
    let Stanza::ServerDef(server) = &mut parsed.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    server.name = "other".to_string();
    server.settings.shift_remove("debug");
    let node = parsed.to_cst().expect("a mutated value must synthesise");
    let read = Config::from_cst(&node).expect("a synthesised CST must convert");
    assert_eq!(read, parsed);
    let Stanza::ServerDef(server) = &read.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    // Map equality is order-independent, so the insertion order needs its own assertion.
    assert_eq!(server.settings.keys().collect::<Vec<_>>(), vec!["host", "port", "tags"]);
}

#[test]
fn text_the_rules_terminal_cannot_match_is_refused() {
    let mut parsed = config(TEXT);
    let Stanza::ServerDef(server) = &mut parsed.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    server.name = "Not An Identifier".to_string();
    let error = parsed.to_cst().expect_err("the identifier terminal accepts no spaces");
    assert_eq!(
        error.message,
        "rule \\"identifier\\": text \\"Not An Identifier\\" is not something the rule could have matched"
    );
}

/// A `boolean` node standing for one of its two alternatives, with no source text behind it.
fn boolean_node(truthy: bool) -> ::fltk_cst_core::Shared<cst::Boolean> {
    let label = if truthy {
        cst::BooleanLabel::True
    } else {
        cst::BooleanLabel::False
    };
    let mut node = cst::Boolean::new(::fltk_cst_core::Span::unknown());
    node.push_child(Some(label), cst::BooleanChild::Span(::fltk_cst_core::Span::unknown()));
    node.into()
}

#[test]
fn a_child_no_alternative_accepts_under_its_label_matches_no_alternative() {
    // The parser cannot produce this: the label decides the kind of child under it. A hand-built
    // node can, and the dispatch table has no pair for the combination, so nothing claims it.
    let mut node = cst::Value::new(::fltk_cst_core::Span::unknown());
    node.push_child(Some(cst::ValueLabel::String), cst::ValueChild::Boolean(boolean_node(true)));
    let error = Value::from_cst(&node.into()).expect_err("no alternative carries a boolean under `string`");
    assert_eq!(
        error.message,
        "rule \\"value\\": no alternative matches the node's labeled children"
    );
}

#[test]
fn an_unlabeled_child_is_not_counted_against_any_alternative() {
    let mut node = cst::Value::new(::fltk_cst_core::Span::unknown());
    node.push_child(Some(cst::ValueLabel::Flag), cst::ValueChild::Boolean(boolean_node(true)));
    node.push_child(None, cst::ValueChild::Boolean(boolean_node(false)));
    let value = Value::from_cst(&node.into()).expect("an unlabeled child constrains no alternative");
    assert_eq!(value, Value::Flag(true));
}

#[test]
fn a_repeated_key_reports_both_locations() {
    let duplicated = TEXT.replace("port = 8080;", "host = \\"other\\";");
    let error = Config::from_cst(&parse(&duplicated)).expect_err("a repeated key must be refused");
    assert_eq!(error.message, "duplicate setting key \\"host\\"");
    assert_eq!(error.related.len(), 1);
    assert_eq!(error.related[0].0, "previously defined here");
    assert_ne!(
        error.span, error.related[0].1,
        "the two spans locate the two colliding elements"
    );
}
"""

# What a fold rule's converter must produce: the nesting the direction asks for, one precedence
# level inside the other, and a link span covering everything below it. None of that is visible in
# the emitted source, and the boxing the cycle forces is only proven by compiling.
FOLD_RUNTIME = """//! `from_cst` over a real parse of the expression grammar.

use super::ast::{AddOpValue, Expr, ExprBinary, Factor, MulOpValue, Term};
use super::cst;
use super::parser::Parser;

fn parse(text: &str) -> ::fltk_cst_core::Shared<cst::Expr> {
    let mut parser = Parser::new(text, None, false);
    let parsed = parser.apply__parse_expr(0).expect("the expression must parse");
    assert!(
        parsed.pos as usize == text.len(),
        "the parse must consume {text:?}, stopped at {}",
        parsed.pos
    );
    parsed.result
}

fn expr(text: &str) -> Expr {
    Expr::from_cst(&parse(text)).expect("a parser-produced CST must convert")
}

#[test]
fn a_single_operand_stays_a_bare_operand() {
    let Expr::Operand(term) = expr("7") else {
        panic!("one operand does not fold into a link");
    };
    let Term::Operand(factor) = *term else {
        panic!("one factor does not fold into a link either");
    };
    assert_eq!(*factor, Factor::Num(7));
}

#[test]
fn a_left_fold_nests_the_earliest_operands_deepest() {
    let Expr::Binary(outer) = expr("1+2-3") else {
        panic!("three operands fold into a link");
    };
    assert_eq!(outer.op, AddOpValue::Minus);
    assert!(matches!(outer.rhs.as_ref(), Expr::Operand(_)));
    // A link is read through a reference: it carries a `Drop` impl, so its sides cannot be moved
    // out of an owned one.
    let Expr::Binary(inner) = outer.lhs.as_ref() else {
        panic!("the left side of a left fold is the deeper chain");
    };
    assert_eq!(inner.op, AddOpValue::Plus);
    assert!(matches!(inner.lhs.as_ref(), Expr::Operand(_)));
}

#[test]
fn the_tighter_precedence_level_folds_inside_the_looser_one() {
    let Expr::Binary(sum) = expr("1+2*3") else {
        panic!("two operands fold into a link");
    };
    assert_eq!(sum.op, AddOpValue::Plus);
    let Expr::Operand(term) = sum.rhs.as_ref() else {
        panic!("the right operand of the sum is a term");
    };
    let Term::Binary(product) = term.as_ref() else {
        panic!("the term folds a chain of its own");
    };
    assert_eq!(product.op, MulOpValue::Times);
}

#[test]
fn each_link_span_covers_everything_below_it() {
    let Expr::Binary(outer) = expr("1+2-3") else {
        panic!("three operands fold into a link");
    };
    assert_eq!(outer.span.text().as_deref(), Some("1+2-3"));
    let Expr::Binary(inner) = outer.lhs.as_ref() else {
        panic!("the left side is the deeper chain");
    };
    assert_eq!(inner.span.text().as_deref(), Some("1+2"));
}

#[test]
fn a_parenthesized_operand_closes_the_cycle_by_value() {
    let Expr::Operand(term) = expr("(1+2)") else {
        panic!("a single parenthesized operand does not fold");
    };
    let Term::Operand(factor) = *term else {
        panic!("one factor does not fold");
    };
    let Factor::Paren(inner) = *factor else {
        panic!("the factor is the erased paren wrapper");
    };
    assert!(matches!(*inner, Expr::Binary(_)));
}

#[test]
fn spans_do_not_take_part_in_equality_but_operators_do() {
    assert_eq!(expr("1+2"), expr("1 + 2"));
    assert_ne!(expr("1+2"), expr("1-2"));
    assert_ne!(expr("1+2"), expr("1+3"));
}

#[test]
fn an_operator_with_no_operand_pair_to_join_is_refused() {
    let node = parse("1+2");
    let extra = {
        let guard = node.read();
        guard
            .children()
            .iter()
            .find(|(label, _)| matches!(label, Some(cst::ExprLabel::Op)))
            .expect("the parse recorded one operator")
            .clone()
    };
    node.write().push_child(extra.0, extra.1);
    let error = Expr::from_cst(&node).expect_err("a fold needs one operator between each operand pair");
    assert_eq!(
        error.message,
        "rule \\"expr\\": a fold over 2 operand(s) needs 1 operator(s), but the node has 2"
    );
}

#[test]
fn a_chain_unfolds_into_the_run_it_was_folded_from() {
    // The unfold is the converter's inverse, so a reordered descent, a missing `reverse()` or an
    // operator pushed out of step comes back as a different expression.
    for text in ["7", "1+2", "1+2-3", "1+2*3-4", "(1+2)*3"] {
        let value = expr(text);
        let node = value.to_cst().expect("a value read off a parse must synthesise");
        assert_eq!(
            Expr::from_cst(&node).expect("a synthesised CST must convert"),
            value,
            "{text}"
        );
    }
}

#[test]
fn a_chain_nested_against_the_folds_direction_has_no_grammar_shape() {
    // A `fold_left` rule nests to the left, so a link in a link's `rhs` cannot be written down.
    let against = Expr::Binary(ExprBinary {
        op: AddOpValue::Plus,
        lhs: Box::new(expr("1")),
        rhs: Box::new(expr("2-3")),
        span: ::fltk_cst_core::Span::unknown(),
    });
    let error = against.to_cst().expect_err("the grammar has no shape for a right-nested chain");
    assert_eq!(
        error.message,
        "rule \\"expr\\": this fold nests the other way, so the right operand of a link cannot \\
         itself be a chain — the grammar has no shape to render it as; rebuild the chain in the \\
         fold's own direction"
    );
}

#[test]
fn a_chain_of_two_hundred_thousand_links_tears_down_without_recursing() {
    // A fold turns flat input into depth, so a chain is as long as the source repeated the
    // operator. Derived drop glue recurses once per link, which is a stack overflow — a process
    // abort, not a catchable failure — well below this length. There is nothing to assert
    // afterwards: without the emitted `Drop` this takes the whole test binary down with it.
    const LINKS: usize = 200_000;
    let span = ::fltk_cst_core::Span::unknown();
    let operands: Vec<(Term, ::fltk_cst_core::Span)> = (0..=LINKS)
        .map(|_| (Term::Operand(Box::new(Factor::Num(1))), span.clone()))
        .collect();
    let operators = vec![AddOpValue::Plus; LINKS];
    let chain = ::fltk_ast_core::fold_left(
        "expr",
        &span,
        operands,
        operators,
        |operand| Expr::Operand(Box::new(operand)),
        |op, lhs, rhs, span| {
            Expr::Binary(ExprBinary {
                op,
                lhs: Box::new(lhs),
                rhs: Box::new(rhs),
                span,
            })
        },
    )
    .expect("a long run of operands folds");
    assert!(matches!(chain, Expr::Binary(_)));
    drop(chain);
}
"""

# Labeled-literal trial matching on the compiled Rust formatter. `fegen.fltkg`'s nine labeled
# literals are all single-spelling, so the existing byte-parity sweep exercises only the "text
# matches the one spelling" direction; these grammars reach the multi-spelling and rival-regex
# paths. An inverted `is_some_and`, or a mis-rendered pattern alternation, passes every
# emitted-source assertion and fails here.
LITERAL_LABEL_GRAMMAR = (
    'val := ( x:"null" | x:/[0-9]+/ ) . u:word ;\n'
    'seq := x:"null"? . x:/[0-9]+/ . u:word ;\n'
    'colour := red:"red" | blue:"blue" | gray:"gray" | gray:"grey" ;\n'
    'sole := v:"null" . u:word ;\n'
    "word := c:/[a-z]+/ ;\n"
)

LITERAL_LABEL_RUNTIME = """//! Text-aware trial matching over the compiled Rust unparser.

use super::cst;
use super::parser::Parser;
use super::unparser::Unparser;
use ::fltk_unparser_core::{resolve_spacing_specs, Renderer, RendererConfig};

macro_rules! format_native {
    ($src:expr, $parse:ident, $unparse:ident) => {{
        let src: &str = $src;
        let mut parser = Parser::new(src, None, true);
        let parsed = parser.$parse(0).expect("the input must parse");
        assert!(parsed.pos as usize == src.len(), "the parse must consume {src:?}");
        let guard = parsed.result.read();
        let unparsed = Unparser::new()
            .$unparse(&*guard)
            .expect("a parser-produced CST must unparse");
        let resolved = resolve_spacing_specs(unparsed.doc());
        Renderer::new(RendererConfig {
            indent_width: 2,
            max_width: 80,
        })
        .render(&resolved)
    }};
}

#[test]
fn a_rival_regex_under_the_same_label_keeps_its_own_text() {
    // Without the text check the literal position takes the regex child and renders its own
    // text ("null") instead of the parsed digits.
    assert_eq!(format_native!("42u", apply__parse_val, unparse_val), "42u");
}

#[test]
fn the_literal_branch_still_renders_the_literal() {
    assert_eq!(format_native!("nullu", apply__parse_val, unparse_val), "nullu");
}

#[test]
fn the_sequential_spelling_declines_the_child_it_cannot_spell() {
    // Without the text check the literal takes the child and fails rather than letting the
    // regex item accept it.
    assert_eq!(format_native!("42u", apply__parse_seq, unparse_seq), "42u");
    assert_eq!(format_native!("null42u", apply__parse_seq, unparse_seq), "null42u");
}

#[test]
fn a_sibling_spelling_of_one_label_is_accepted_and_canonicalized() {
    assert_eq!(format_native!("grey", apply__parse_colour, unparse_colour), "gray");
    assert_eq!(format_native!("gray", apply__parse_colour, unparse_colour), "gray");
    assert_eq!(format_native!("blue", apply__parse_colour, unparse_colour), "blue");
}

#[test]
fn a_hand_built_span_no_position_accepts_fails_the_unparse() {
    // `sole` has no rival regex under the label, so nothing else can take the child: a text no
    // position accepts must fail, not render as the literal.
    let mut parser = Parser::new("nullu", None, true);
    let parsed = parser.apply__parse_sole(0).expect("the input must parse");
    let source = ::fltk_cst_core::SourceText::from_str("oops", None);
    {
        let mut guard = parsed.result.write();
        let label = guard.children()[0].0.clone();
        let replacement = ::fltk_cst_core::Span::new_with_source(0, 4, &source);
        guard.replace_child(0, label, cst::SoleChild::Span(replacement));
    }
    let guard = parsed.result.read();
    assert!(
        Unparser::new().unparse_sole(&guard).is_none(),
        "text no position accepts must fail loudly, not render as the literal"
    );
}

#[test]
fn a_synthesized_sourceless_span_still_renders_the_canonical_spelling() {
    // The AST's `to_cst` path: a literal child carries position only, so text cannot decide.
    let mut parser = Parser::new("nullu", None, true);
    let parsed = parser.apply__parse_sole(0).expect("the input must parse");
    {
        let mut guard = parsed.result.write();
        let label = guard.children()[0].0.clone();
        let replacement = ::fltk_cst_core::Span::new_sourceless(0, 4);
        guard.replace_child(0, label, cst::SoleChild::Span(replacement));
    }
    let guard = parsed.result.read();
    let unparsed = Unparser::new()
        .unparse_sole(&guard)
        .expect("a sourceless literal child is accepted unconditionally");
    let resolved = resolve_spacing_specs(unparsed.doc());
    let rendered = Renderer::new(RendererConfig {
        indent_width: 2,
        max_width: 80,
    })
    .render(&resolved);
    assert_eq!(rendered, "nullu");
}
"""

# What a split produces, and whether `from_cst` reads back what `to_cst` wrote, is not visible in
# the emitted source: `tests/test_gsm2ast_rs.py` asserts what is written for `LEAF_GRAMMAR`, and
# this runs it.
SERIALIZE_RUNTIME = """//! `to_cst` over hand-built values of the leaf node forms.

use super::ast::{Count, Flag, Num, Pick, PickValue, Quoted, Ratio, Tag};
use super::cst;
use ::fltk_cst_core::Span;

/// The label and text of each child a synthesised node holds, in order.
///
/// Every rule here holds span children only, so the child enum has one variant and the match is
/// exhaustive with one arm.
macro_rules! children {
    ($result:expr, $span:path) => {{
        let node = $result.expect("a hand-built value must synthesise");
        let guard = node.read();
        guard
            .children()
            .iter()
            .map(|(label, child)| match child {
                $span(span) => (label.clone(), span.text().map(|text| text.to_string())),
            })
            .collect::<Vec<_>>()
    }};
}

fn num(text: &str) -> Num {
    Num {
        text: text.to_string(),
        span: Span::unknown(),
    }
}

#[test]
fn a_terminal_rules_text_comes_back_as_its_child_span() {
    assert_eq!(
        children!(num("42").to_cst(), cst::NumChild::Span),
        vec![(Some(cst::NumLabel::D), Some("42".to_string()))]
    );
}

#[test]
fn a_synthesised_terminal_node_carries_its_text_as_its_own_span() {
    // `from_cst` reads a terminal-only rule's text off the node's own span, so a synthesised
    // node has to carry it there too.
    let node = num("42").to_cst().expect("a hand-built value must synthesise");
    assert_eq!(node.read().span().text().as_deref(), Some("42"));
}

#[test]
fn a_redirected_text_leaves_the_node_span_unknown_and_the_quotes_to_the_grammar() {
    let value = Quoted {
        text: "hi".to_string(),
        span: Span::unknown(),
    };
    let node = value.to_cst().expect("a hand-built value must synthesise");
    assert_eq!(*node.read().span(), Span::unknown(), "the text belongs to the child");
    assert_eq!(
        children!(value.to_cst(), cst::QuotedChild::Span),
        vec![(Some(cst::QuotedLabel::Content), Some("hi".to_string()))],
        "the suppressed quotes come back from the grammar, not from the value"
    );
}

#[test]
fn the_alternative_the_text_matches_decides_the_children() {
    let lower = Tag {
        text: "#host".to_string(),
        span: Span::unknown(),
    };
    assert_eq!(
        children!(lower.to_cst(), cst::TagChild::Span),
        vec![
            // The `$`-included literal records position only.
            (None, None),
            (Some(cst::TagLabel::Name), Some("host".to_string())),
        ]
    );
    let upper = Tag {
        text: "HOST".to_string(),
        span: Span::unknown(),
    };
    assert_eq!(
        children!(upper.to_cst(), cst::TagChild::Span),
        vec![(Some(cst::TagLabel::Name), Some("HOST".to_string()))]
    );
}

#[test]
fn a_coercion_renders_through_the_canonical_renderer() {
    let count = Count {
        value: 42,
        span: Span::unknown(),
    };
    assert_eq!(
        children!(count.to_cst(), cst::CountChild::Span),
        vec![(Some(cst::CountLabel::C), Some("42".to_string()))]
    );
    // The shortest spelling that round-trips at 32 bits, not the seventeen digits an f64 needs.
    let ratio = Ratio {
        value: 0.1,
        span: Span::unknown(),
    };
    assert_eq!(
        children!(ratio.to_cst(), cst::RatioChild::Span),
        vec![(Some(cst::RatioLabel::V), Some("0.1".to_string()))]
    );
}

#[test]
fn an_enum_shaped_value_appends_the_label_of_its_alternative() {
    let value = Pick {
        value: PickValue::B,
        span: Span::unknown(),
    };
    // A literal renders from the grammar, so the child carries no text of its own.
    assert_eq!(
        children!(value.to_cst(), cst::PickChild::Span),
        vec![(Some(cst::PickLabel::B), None)]
    );
}

#[test]
fn a_boolean_value_appends_the_label_of_the_alternative_it_names() {
    let value = Flag {
        value: false,
        span: Span::unknown(),
    };
    assert_eq!(
        children!(value.to_cst(), cst::FlagChild::Span),
        vec![(Some(cst::FlagLabel::No), None)]
    );
}

#[test]
fn text_the_terminal_cannot_match_is_refused() {
    let error = num("12x").to_cst().expect_err("the terminal does not accept a trailing letter");
    assert_eq!(
        error.message,
        "rule \\"num\\": text \\"12x\\" is not something the rule could have matched"
    );
}

#[test]
fn every_leaf_form_reads_back_as_the_value_it_was_built_from() {
    // The round-trip law, on the forms that can already synthesise: what `to_cst` writes
    // is what `from_cst` reads.
    macro_rules! reads_back {
        ($type:ident, $value:expr) => {{
            let value = $value;
            let node = value.to_cst().expect("a hand-built value must synthesise");
            assert_eq!($type::from_cst(&node).expect("a synthesised CST must convert"), value);
        }};
    }
    reads_back!(Num, num("7"));
    reads_back!(
        Tag,
        Tag {
            text: "#host".to_string(),
            span: Span::unknown(),
        }
    );
    reads_back!(
        Tag,
        Tag {
            text: "HOST".to_string(),
            span: Span::unknown(),
        }
    );
    reads_back!(
        Quoted,
        Quoted {
            text: "hi".to_string(),
            span: Span::unknown(),
        }
    );
    reads_back!(
        Count,
        Count {
            value: -3,
            span: Span::unknown(),
        }
    );
    reads_back!(
        Ratio,
        Ratio {
            value: 1.5,
            span: Span::unknown(),
        }
    );
    reads_back!(
        Flag,
        Flag {
            value: true,
            span: Span::unknown(),
        }
    );
    reads_back!(
        Pick,
        Pick {
            value: PickValue::A,
            span: Span::unknown(),
        }
    );
}
"""

# The two entry points, over the config language: text in, AST out, text back. The pipeline they
# wrap — the depth check, the full-consumption check, the formatter's `None` — is invisible in the
# emitted source, and the round-trip law is about *text*, which nothing else exercises.
#
# Appended to `CONFIG_RUNTIME` rather than given a case of its own: the generation inputs would be
# the same grammar and the same sidecar, so a second case compiles a second copy of the config
# language's whole CST, parser and AST for the sake of one more entry point.
ENTRY_POINT_RUNTIME = """
// --- `parse_str` and `unparse_str`, over the same document ----------------------------------

/// The one-call parse: the pipeline `parse` and `config` above spell out by hand, plus the
/// depth and full-consumption checks.
fn from_text(text: &str) -> Config {
    ast::parse_str(text, Some("app.conf")).expect("the document must parse and convert")
}

fn rendered(value: &Config) -> String {
    ast::unparse_str(value, 80, 2).expect("a value read off a parse must render")
}

#[test]
fn one_call_turns_source_text_into_an_ast() {
    let parsed = from_text(TEXT);
    let Stanza::ServerDef(server) = &parsed.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    assert_eq!(server.name, "web");
    assert_eq!(server.settings["port"].value, Value::Number(8080));
}

#[test]
fn the_round_trip_law_holds_through_text() {
    let value = from_text(TEXT);
    assert_eq!(from_text(&rendered(&value)), value);
}

#[test]
fn a_mutated_value_renders_its_change_and_reads_back_as_itself() {
    let mut value = from_text(TEXT);
    let Stanza::ServerDef(server) = &mut value.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    server.name = "other".to_string();
    server.settings["port"].value = Value::Number(9090);
    let text = rendered(&value);
    assert!(text.contains("other"), "{text}");
    assert!(text.contains("9090"), "{text}");
    assert_eq!(from_text(&text), value);
}

#[test]
fn the_renderer_dimensions_reach_the_output() {
    // Narrow enough that the settings cannot sit on one line, wide enough that they can.
    let value = from_text(TEXT);
    let narrow = ast::unparse_str(&value, 1, 2).expect("a value must render at any width");
    let wide = ast::unparse_str(&value, 400, 2).expect("a value must render at any width");
    assert!(narrow.lines().count() > wide.lines().count(), "{narrow:?} vs {wide:?}");
}

#[test]
fn input_the_goal_rule_did_not_consume_is_the_parse_arm() {
    let error = ast::parse_str("server web { } oops", None).expect_err("a partial parse is not a parse");
    let ::fltk_ast_core::ParseToAstError::Parse(message) = &error else {
        panic!("unconsumed input is a parse failure, not a conversion failure");
    };
    assert!(message.starts_with("Syntax error at line 1"), "{message}");
    // `Display` is the parser's own diagnostic, unwrapped.
    assert_eq!(error.to_string(), *message);
}

#[test]
fn a_conversion_failure_is_the_ast_arm() {
    let wide = TEXT.replace("8080", "99999999999999999999");
    let error = ast::parse_str(&wide, None).expect_err("the number does not fit an i64");
    let ::fltk_ast_core::ParseToAstError::Ast(inner) = &error else {
        panic!("a coercion failure is a conversion failure");
    };
    assert!(inner.message.contains("i64"), "{}", inner.message);
    // The span is the terminal node's, so the arm carries a position the parse arm cannot.
    assert!(inner.span.line_col_inner().is_some(), "the failing terminal locates itself");
}

#[test]
fn text_no_terminal_accepts_is_refused_before_anything_is_rendered() {
    let mut value = from_text(TEXT);
    let Stanza::ServerDef(server) = &mut value.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    server.name = "Not An Identifier".to_string();
    let error = ast::unparse_str(&value, 80, 2).expect_err("the identifier terminal accepts no spaces");
    assert_eq!(
        error.message,
        "rule \\"identifier\\": text \\"Not An Identifier\\" is not something the rule could have matched"
    );
}
"""

# The serde frontend over the same document.
CONFIG_SERDE_RUNTIME = """
// --- the serde frontend, over the same language --------------------------------------------

use super::de;
use serde::Deserialize;
use std::collections::BTreeMap;

const SERVER_ONLY: &str = r#"server web {
  host = "localhost";
}
"#;

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Document {
    stanzas: Vec<Entry>,
}

#[derive(Debug, Deserialize, PartialEq)]
enum Entry {
    ServerDef(Server),
    MetricDef(Metric),
}

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Server {
    name: String,
    settings: BTreeMap<String, SettingValue>,
}

/// The element of a keyed region, minus the field that keys it.
#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct SettingValue {
    value: Val,
}

#[derive(Debug, Deserialize, PartialEq)]
enum Val {
    String(String),
    Number(i64),
    Flag(bool),
    List(ListValue),
}

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct ListValue {
    value: Vec<Val>,
}

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Metric {
    name: String,
    metric_kind: Kind,
    interval: Option<u32>,
}

#[derive(Debug, Deserialize, PartialEq)]
enum Kind {
    Counter,
    Gauge,
    Histogram,
}

fn document(text: &str) -> Document {
    de::from_str(text, Some("app.conf")).expect("the document must parse and deserialize")
}

fn refused(text: &str) -> ::fltk_serde_core::DeserializeError {
    let error = de::from_str::<Document>(text, Some("app.conf")).expect_err("the target must refuse this");
    match error {
        ::fltk_serde_core::ParseToTargetError::Deserialize(inner) => inner,
        ::fltk_serde_core::ParseToTargetError::Parse(message) => panic!("the text parses: {message}"),
    }
}

#[test]
fn one_call_turns_source_text_into_the_targets_the_consumer_declared() {
    assert_eq!(
        document(TEXT),
        Document {
            stanzas: vec![
                Entry::ServerDef(Server {
                    name: "web".to_string(),
                    settings: BTreeMap::from([
                        (
                            "host".to_string(),
                            SettingValue {
                                value: Val::String("localhost".to_string()),
                            },
                        ),
                        ("port".to_string(), SettingValue { value: Val::Number(8080) }),
                        ("debug".to_string(), SettingValue { value: Val::Flag(true) }),
                        (
                            "tags".to_string(),
                            SettingValue {
                                value: Val::List(ListValue {
                                    value: vec![Val::Number(1), Val::Number(2)],
                                }),
                            },
                        ),
                    ]),
                }),
                Entry::MetricDef(Metric {
                    name: "hits".to_string(),
                    metric_kind: Kind::Counter,
                    interval: Some(30),
                }),
            ],
        }
    );
}

#[test]
fn the_same_keyed_region_is_a_sequence_where_the_target_asks_for_one() {
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct Rows {
        name: String,
        settings: Vec<Row>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct Row {
        key: String,
        value: Val,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    struct RowDoc {
        stanzas: Vec<RowEntry>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    enum RowEntry {
        ServerDef(Rows),
    }

    let parsed: RowDoc = de::from_str(SERVER_ONLY, None).expect("the document must deserialize");
    let RowEntry::ServerDef(server) = &parsed.stanzas[0];
    assert_eq!(
        server.settings,
        vec![Row {
            key: "host".to_string(),
            value: Val::String("localhost".to_string()),
        }]
    );
}

#[test]
fn an_unknown_field_is_serdes_own_message_at_the_offending_child() {
    // Nothing here is ever built — the point is the refusal — so the whole target opts out of
    // the dead-code lint rather than each member of it.
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    #[serde(deny_unknown_fields)]
    struct JustName {
        name: String,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct NameDoc {
        stanzas: Vec<NameEntry>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    enum NameEntry {
        ServerDef(JustName),
    }

    let error = de::from_str::<NameDoc>(SERVER_ONLY, Some("app.conf")).expect_err("the target has no settings");
    // The message is serde's, the position is the CST's: the first setting the target has no
    // field for.
    assert_eq!(
        error.to_string(),
        "unknown field `settings`, expected `name` at line 2, column 3"
    );
}

#[test]
fn a_field_the_target_needs_and_the_source_omits_is_missing_at_the_node() {
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Strict {
        name: String,
        metric_kind: Kind,
        interval: u32,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct StrictDoc {
        stanzas: Vec<StrictEntry>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    enum StrictEntry {
        MetricDef(Strict),
    }

    let error = de::from_str::<StrictDoc>("metric hits : counter ;", None).expect_err("the interval is optional here");
    assert_eq!(error.to_string(), "missing field `interval` at line 1, column 1");
}

#[test]
fn a_scalar_target_runs_the_gate_its_type_names_over_the_source_text() {
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    enum Narrow {
        Number(u8),
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct NarrowSetting {
        value: Narrow,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct NarrowServer {
        name: String,
        settings: BTreeMap<String, NarrowSetting>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct NarrowDoc {
        stanzas: Vec<NarrowEntry>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    enum NarrowEntry {
        ServerDef(NarrowServer),
    }

    let error = de::from_str::<NarrowDoc>("server web { port = 8080; }", None).expect_err("8080 is no u8");
    let ::fltk_serde_core::ParseToTargetError::Deserialize(inner) = &error else {
        panic!("a coercion failure is a deserialize failure");
    };
    assert_eq!(
        inner.message,
        "rule \\"number\\": \\"8080\\" is not in range for u8 (0 to 255)"
    );
    assert_eq!(inner.span.text().as_deref(), Some("8080"), "positioned at the value itself");
}

#[test]
fn a_repeated_key_is_refused_by_the_frontend_rather_than_left_to_the_container() {
    // A `BTreeMap` would last-write-win; the map form answers the duplicate before the target
    // sees either element.
    let error = refused(&TEXT.replace("port = 8080;", "host = \\"other\\";"));
    assert_eq!(error.message, "duplicate setting key \\"host\\"");
    assert_eq!(error.related.len(), 1);
    assert_eq!(error.related[0].0, "previously defined here");
    assert_ne!(error.span, error.related[0].1);
}

#[test]
fn a_target_can_position_a_field_and_hold_a_subtree_as_cst() {
    #[derive(Debug, Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Located {
        name: ::fltk_serde_core::Spanned<String>,
        settings: BTreeMap<String, Held>,
    }
    #[derive(Debug, Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Held {
        value: ::fltk_serde_core::Raw<cst::Value>,
    }
    #[derive(Debug, Deserialize)]
    struct LocatedDoc {
        stanzas: Vec<LocatedEntry>,
    }
    #[derive(Debug, Deserialize)]
    enum LocatedEntry {
        ServerDef(Located),
    }

    let parsed: LocatedDoc = de::from_str(SERVER_ONLY, None).expect("the document must deserialize");
    let LocatedEntry::ServerDef(server) = &parsed.stanzas[0];
    assert_eq!(server.name.value(), "web");
    let position = server.name.span().line_col_inner().expect("a parsed span locates itself");
    assert_eq!((position.line + 1, position.col + 1), (1, 8));

    let held = &server.settings["host"].value;
    let value: Val = de::from_value_cst(held.node()).expect("a held node deserializes on demand");
    assert_eq!(value, Val::String("localhost".to_string()));
}

#[test]
fn a_field_declared_as_a_generated_ast_type_is_what_from_cst_builds() {
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct Typed {
        value: ast::Value,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct TypedServer {
        name: String,
        settings: BTreeMap<String, Typed>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    struct TypedDoc {
        stanzas: Vec<TypedEntry>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    enum TypedEntry {
        ServerDef(TypedServer),
        MetricDef(Metric),
    }

    let parsed: TypedDoc = de::from_str(TEXT, None).expect("the document must deserialize");
    let TypedEntry::ServerDef(server) = &parsed.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    let converted = Config::from_cst(&parse(TEXT)).expect("the same document converts");
    let Stanza::ServerDef(expected) = &converted.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    assert_eq!(server.settings["tags"].value, expected.settings["tags"].value);
    assert_eq!(server.settings["port"].value, ast::Value::Number(8080));
}

#[test]
fn an_ast_typed_field_can_be_positioned_like_any_other() {
    #[derive(Debug, Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Located {
        value: ::fltk_serde_core::Spanned<ast::Value>,
    }
    // `name` is there because the target must cover every field the source carries; only the
    // positioned value is read.
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    #[serde(deny_unknown_fields)]
    struct LocatedServer {
        name: String,
        settings: BTreeMap<String, Located>,
    }
    #[derive(Debug, Deserialize)]
    struct LocatedDoc {
        stanzas: Vec<LocatedEntry>,
    }
    #[derive(Debug, Deserialize)]
    enum LocatedEntry {
        ServerDef(LocatedServer),
    }

    let parsed: LocatedDoc = de::from_str(SERVER_ONLY, None).expect("the document must deserialize");
    let LocatedEntry::ServerDef(server) = &parsed.stanzas[0];
    let host = &server.settings["host"].value;
    assert_eq!(**host, ast::Value::String("localhost".to_string()));
    let position = host.span().line_col_inner().expect("a parsed span locates itself");
    assert_eq!((position.line + 1, position.col + 1), (2, 10));
}

#[test]
fn an_ast_type_at_another_rules_position_names_both_rules() {
    // The keyed region's elements are `setting` nodes, so `ast::Value` is not the type of what
    // is there — a target-shape disagreement, reported where it is.
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct MistypedServer {
        name: String,
        settings: BTreeMap<String, ast::Value>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct MistypedDoc {
        stanzas: Vec<MistypedEntry>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    enum MistypedEntry {
        ServerDef(MistypedServer),
    }

    let error = de::from_str::<MistypedDoc>(SERVER_ONLY, Some("app.conf")).expect_err("a setting is no value");
    assert_eq!(
        error.to_string(),
        "expected a `value` node for its AST type, found rule `setting` at line 2, column 3"
    );
}

#[test]
fn a_conversion_failure_under_an_ast_typed_field_keeps_its_own_position() {
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Typed {
        value: ast::Value,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct TypedServer {
        name: String,
        settings: BTreeMap<String, Typed>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct TypedDoc {
        stanzas: Vec<TypedEntry>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    enum TypedEntry {
        ServerDef(TypedServer),
    }

    // `number` coerces to i64 in this sidecar, and `from_cst` is what refuses the overflow: the
    // message and the span are the AST layer's own, not a second wording on this path.
    let error = de::from_str::<TypedDoc>("server web { port = 99999999999999999999; }", None)
        .expect_err("the number does not fit an i64");
    let ::fltk_serde_core::ParseToTargetError::Deserialize(inner) = &error else {
        panic!("a conversion failure is a deserialize failure");
    };
    assert!(inner.message.contains("i64"), "{}", inner.message);
    assert_eq!(inner.span.text().as_deref(), Some("99999999999999999999"));
}

#[test]
fn a_conversion_failure_keeps_its_own_span_under_a_node_that_covers_more_than_it() {
    // The element is the whole `port = ...;` statement and the overflow is one child of it, so
    // a frame that filled the span unconditionally would widen the diagnostic to the statement.
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ElementServer {
        name: String,
        settings: BTreeMap<String, ast::Setting>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ElementDoc {
        stanzas: Vec<ElementEntry>,
    }
    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    enum ElementEntry {
        ServerDef(ElementServer),
    }

    let error = de::from_str::<ElementDoc>("server web { port = 99999999999999999999; }", None)
        .expect_err("the number does not fit an i64");
    let ::fltk_serde_core::ParseToTargetError::Deserialize(inner) = &error else {
        panic!("a conversion failure is a deserialize failure");
    };
    assert_eq!(
        inner.span.text().as_deref(),
        Some("99999999999999999999"),
        "the AST layer's own position, not the setting the frame ran over"
    );
}

#[test]
fn an_ast_typed_field_reaches_every_container_the_model_has() {
    // The single-field case is above; these are the three containers whose serde frames sit
    // between the impl handing its conversion in and the frame that runs it.
    #[derive(Debug, Deserialize, PartialEq)]
    struct StanzaDoc {
        stanzas: Vec<ast::Stanza>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct ElementServer {
        name: String,
        settings: BTreeMap<String, ast::Setting>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    struct ElementDoc {
        stanzas: Vec<ElementEntry>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    enum ElementEntry {
        ServerDef(ElementServer),
    }
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct MaybeValue {
        value: Option<ast::Value>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct MaybeServer {
        name: String,
        settings: BTreeMap<String, MaybeValue>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    struct MaybeDoc {
        stanzas: Vec<MaybeEntry>,
    }
    #[derive(Debug, Deserialize, PartialEq)]
    enum MaybeEntry {
        ServerDef(MaybeServer),
    }

    // A collection of AST types: every stanza of the whole document, equal to what the AST
    // layer builds for the same parse.
    let listed: StanzaDoc = de::from_str(TEXT, None).expect("the document must deserialize");
    let whole = Config::from_cst(&parse(TEXT)).expect("the same document converts");
    assert_eq!(listed.stanzas, whole.stanzas);

    // A map whose value type is an AST type directly: the element node converts whole, key
    // field included, because that is what the element rule's AST type has.
    let converted = Config::from_cst(&parse(SERVER_ONLY)).expect("the same document converts");
    let Stanza::ServerDef(expected) = &converted.stanzas[0] else {
        panic!("the first stanza is a server definition");
    };
    let mapped: ElementDoc = de::from_str(SERVER_ONLY, None).expect("the document must deserialize");
    let ElementEntry::ServerDef(server) = &mapped.stanzas[0];
    assert_eq!(server.settings["host"], expected.settings["host"]);

    // An AST type under an `Option`, at a field the grammar always fills.
    let optional: MaybeDoc = de::from_str(SERVER_ONLY, None).expect("the document must deserialize");
    let MaybeEntry::ServerDef(server) = &optional.stanzas[0];
    assert_eq!(
        server.settings["host"].value,
        Some(ast::Value::String("localhost".to_string()))
    );
}
"""

# `parse_str` where the goal rule can fail to match at all, which the config language's
# zero-or-more goal cannot: the arm that reports the parser's `None`.
FOLD_ENTRY_POINT_RUNTIME = """
#[test]
fn a_text_the_goal_rule_cannot_match_is_a_parse_error() {
    let error = super::ast::parse_str("", None).expect_err("an expression needs an operand");
    assert!(
        matches!(error, ::fltk_ast_core::ParseToAstError::Parse(_)),
        "a start rule that matched nothing is a parse failure"
    );
}

#[test]
fn the_convenience_folds_the_chain_it_parsed() {
    let parsed = super::ast::parse_str("1+2", None).expect("the expression must parse and convert");
    assert_eq!(parsed, expr("1 + 2"));
}
"""

# A fold chain through the serde frontend: the nesting a target sees, and the two arms a tagged
# variant can refuse. Appended to the fold case because it is the same generation input.
FOLD_SERDE_RUNTIME = """
// --- the serde frontend, over the same chain ------------------------------------------------

use super::de;
use serde::Deserialize;

/// A chain of `expr`, externally tagged: the shape a fold rule serves.
#[derive(Debug, Deserialize, PartialEq)]
enum Sum {
    Operand(Product),
    Binary {
        op: AddOp,
        lhs: Box<Sum>,
        rhs: Box<Sum>,
    },
}

#[derive(Debug, Deserialize, PartialEq)]
enum Product {
    Operand(Atom),
    Binary {
        op: MulOp,
        lhs: Box<Product>,
        rhs: Box<Product>,
    },
}

/// `factor`, a sum rule: a number, or the erased paren wrapper holding a chain again.
#[derive(Debug, Deserialize, PartialEq)]
enum Atom {
    Num(i64),
    Paren(Box<Sum>),
}

#[derive(Debug, Deserialize, PartialEq)]
enum AddOp {
    Plus,
    Minus,
}

#[derive(Debug, Deserialize, PartialEq)]
enum MulOp {
    Times,
    Divide,
}

fn target(text: &str) -> Sum {
    de::from_str(text, None).expect("the expression must parse and deserialize")
}

fn atom(value: i64) -> Sum {
    Sum::Operand(Product::Operand(Atom::Num(value)))
}

#[test]
fn a_chain_reaches_a_derived_enum_with_the_nesting_the_fold_gives_it() {
    assert_eq!(target("7"), atom(7));
    assert_eq!(
        target("1+2*3"),
        Sum::Binary {
            op: AddOp::Plus,
            lhs: Box::new(atom(1)),
            rhs: Box::new(Sum::Operand(Product::Binary {
                op: MulOp::Times,
                lhs: Box::new(Product::Operand(Atom::Num(2))),
                rhs: Box::new(Product::Operand(Atom::Num(3))),
            })),
        }
    );
}

#[test]
fn a_transparent_wrapper_hands_the_target_what_it_holds() {
    assert_eq!(
        target("(1-2)"),
        Sum::Operand(Product::Operand(Atom::Paren(Box::new(Sum::Binary {
            op: AddOp::Minus,
            lhs: Box::new(atom(1)),
            rhs: Box::new(atom(2)),
        }))))
    );
}

#[test]
fn a_variant_the_target_declares_as_a_unit_one_is_refused_not_emptied() {
    // Every alternative carries something, so declaring one as a unit variant is a target-shape
    // disagreement — reported, rather than silently dropping what was parsed.
    #[derive(Debug, Deserialize)]
    enum Tagless {
        Operand,
    }

    let error = de::from_str::<Tagless>("7", None).expect_err("the operand carries a value");
    assert_eq!(
        error.to_string(),
        "variant \\"Operand\\" carries content, found a map, expected a unit variant at line 1, column 1"
    );
}

#[test]
fn a_generated_ast_type_is_a_target_like_any_other() {
    let served: super::ast::Expr = de::from_str("1+2*3", None).expect("the chain must deserialize");
    let converted = super::ast::parse_str("1+2*3", None).expect("the same text converts");
    assert_eq!(served, converted);
}

#[test]
fn a_chain_held_as_syntax_converts_through_its_own_entry_point_later() {
    let node = {
        let mut parser = super::parser::Parser::new("4*5", None, false);
        let parsed = parser.apply__parse_expr(0).expect("the expression must parse");
        parsed.result
    };
    let held: ::fltk_serde_core::Raw<super::cst::Expr> =
        de::from_expr_cst(&node).expect("`Raw` holds the node it is positioned at");
    let served: super::ast::Expr = de::from_expr_cst(held.node()).expect("the held node converts");
    assert_eq!(served, super::ast::parse_str("4*5", None).expect("the same text converts"));
}

#[test]
fn text_the_goal_rule_cannot_match_is_the_parse_arm_of_from_str() {
    let error = de::from_str::<Sum>("", None).expect_err("an expression needs an operand");
    let ::fltk_serde_core::ParseToTargetError::Parse(message) = &error else {
        panic!("a start rule that matched nothing is a parse failure");
    };
    assert!(message.starts_with("Syntax error at line 1"), "{message}");
}
"""

# The flattened wrapper's serialize direction: whether it is rebuilt at all, and which of the
# parent's fields lands in which of its item positions. Both are plain data in the emitted text
# that compiling cannot judge.
TASK_RUNTIME = """//! `to_cst` over hand-built task definitions, whose wrapper has no AST type.

use super::ast::{Setting, TaskDef, TimeUnitValue};
use super::cst;
use ::fltk_cst_core::{Shared, Span};

fn task(interval: Option<i64>, unit: Option<TimeUnitValue>) -> TaskDef {
    TaskDef {
        name: "nightly".to_string(),
        interval,
        unit,
        settings: vec![Setting {
            key: "retries".to_string(),
            value: 3,
            span: Span::unknown(),
        }],
        span: Span::unknown(),
    }
}

/// The labels of one synthesised node's children, in order.
fn labels(node: &Shared<cst::TaskDef>) -> Vec<Option<cst::TaskDefLabel>> {
    let guard = node.read();
    guard.children().iter().map(|(label, _)| label.clone()).collect()
}

#[test]
fn a_wrapper_with_nothing_to_carry_is_not_rebuilt() {
    let value = task(None, None);
    let node = value.to_cst().expect("a task with no schedule must synthesise");
    assert_eq!(
        labels(&node),
        vec![Some(cst::TaskDefLabel::Name), Some(cst::TaskDefLabel::Setting)]
    );
    assert_eq!(TaskDef::from_cst(&node).expect("a synthesised CST must convert"), value);
}

#[test]
fn a_populated_wrapper_is_rebuilt_where_the_grammar_spells_it() {
    let value = task(Some(5), Some(TimeUnitValue::Min));
    let node = value.to_cst().expect("a task with a schedule must synthesise");
    assert_eq!(
        labels(&node),
        vec![
            Some(cst::TaskDefLabel::Name),
            Some(cst::TaskDefLabel::Schedule),
            Some(cst::TaskDefLabel::Setting),
        ]
    );
    // Read back rather than walked by hand: the pairing of each parent field with a position of
    // the wrapper is what a positional `zip` could get wrong, and `from_cst` undoes exactly it.
    assert_eq!(TaskDef::from_cst(&node).expect("a synthesised CST must convert"), value);
}

#[test]
fn a_half_populated_wrapper_names_the_field_it_still_needs() {
    let error = task(Some(5), None)
        .to_cst()
        .expect_err("the wrapper cannot be rebuilt without its unit");
    assert!(
        error
            .message
            .starts_with("rule \\"schedule\\": the flattened wrapper needs a \\"unit\\" value"),
        "{}",
        error.message
    );
    let error = task(None, Some(TimeUnitValue::Hour))
        .to_cst()
        .expect_err("nor without its interval");
    assert!(error.message.contains("needs a \\"interval\\" value"), "{}", error.message);
}
"""

# Which item position each value lands in: a labeled literal at three arities, the branch of an
# alternation a field-enum variant belongs to, and the reserve a repeated position leaves the
# required one beside it. All of it is data in the emitted text that compiling cannot judge.
SHAPES_RUNTIME = """//! `to_cst` over a hand-built document of the positions that read a span child.

use super::ast::{Doc, DocA, Num, Other, StringLiteral, Word};
use super::cst;
use ::fltk_cst_core::{Shared, Span};

fn word(text: &str) -> Word {
    Word {
        text: text.to_string(),
        span: Span::unknown(),
    }
}

fn doc(a: DocA, stars: usize, is_pub: bool, part: Vec<Word>) -> Doc {
    Doc {
        bang: Span::unknown(),
        stars: vec![Span::unknown(); stars],
        r#pub: is_pub,
        a,
        b: Other {
            text: "HOST".to_string(),
            span: Span::unknown(),
        },
        part,
        s: StringLiteral {
            text: "hi".to_string(),
            span: Span::unknown(),
        },
        span: Span::unknown(),
    }
}

fn labels(node: &Shared<cst::Doc>) -> Vec<Option<cst::DocLabel>> {
    let guard = node.read();
    guard.children().iter().map(|(label, _)| label.clone()).collect()
}

/// Which rule the `a` child came from, which is what the field-enum variant decides.
fn a_child(node: &Shared<cst::Doc>) -> &'static str {
    let guard = node.read();
    let (_, child) = guard
        .children()
        .iter()
        .find(|(label, _)| matches!(label, Some(cst::DocLabel::A)))
        .expect("the alternation contributes exactly one child");
    match child {
        cst::DocChild::Num(_) => "num",
        cst::DocChild::Word(_) => "word",
        _ => "neither branch of the alternation",
    }
}

#[test]
fn every_position_appends_its_own_occurrences_in_grammar_order() {
    let value = doc(DocA::Num(Num {
        text: "42".to_string(),
        span: Span::unknown(),
    }), 2, true, vec![word("a"), word("b")]);
    let node = value.to_cst().expect("a hand-built document must synthesise");
    assert_eq!(
        labels(&node),
        vec![
            Some(cst::DocLabel::Bang),
            Some(cst::DocLabel::Stars),
            Some(cst::DocLabel::Stars),
            Some(cst::DocLabel::Pub),
            Some(cst::DocLabel::A),
            Some(cst::DocLabel::B),
            Some(cst::DocLabel::Part),
            Some(cst::DocLabel::Part),
            Some(cst::DocLabel::S),
        ]
    );
    assert_eq!(Doc::from_cst(&node).expect("a synthesised CST must convert"), value);
}

#[test]
fn a_presence_flag_left_unset_appends_nothing() {
    let value = doc(DocA::Word(word("x")), 0, false, vec![word("a")]);
    let node = value.to_cst().expect("a hand-built document must synthesise");
    assert_eq!(
        labels(&node),
        vec![
            Some(cst::DocLabel::Bang),
            Some(cst::DocLabel::A),
            Some(cst::DocLabel::B),
            Some(cst::DocLabel::Part),
            Some(cst::DocLabel::S),
        ]
    );
}

#[test]
fn the_branch_of_the_alternation_follows_the_variant_the_value_carries() {
    let numeric = doc(DocA::Num(Num {
        text: "42".to_string(),
        span: Span::unknown(),
    }), 0, false, vec![word("a")]);
    assert_eq!(a_child(&numeric.to_cst().expect("a hand-built document must synthesise")), "num");
    let textual = doc(DocA::Word(word("x")), 0, false, vec![word("a")]);
    assert_eq!(a_child(&textual.to_cst().expect("a hand-built document must synthesise")), "word");
}

#[test]
fn a_field_enum_over_node_payloads_answers_for_the_span_of_whichever_it_holds() {
    let placed = Word {
        text: "x".to_string(),
        span: Span::new_sourceless(3, 4),
    };
    let value = doc(DocA::Word(placed.clone()), 0, false, vec![word("a")]);
    assert_eq!(value.a.span(), &placed.span);
    let numeric = DocA::Num(Num {
        text: "42".to_string(),
        span: Span::new_sourceless(7, 9),
    });
    assert_eq!(numeric.span(), &Span::new_sourceless(7, 9));
}

#[test]
fn a_required_position_with_no_value_to_take_names_the_shortfall() {
    let value = doc(DocA::Word(word("x")), 0, false, Vec::new());
    let error = value.to_cst().expect_err("the first `part` position is not optional");
    assert_eq!(
        error.message,
        "rule \\"doc\\": the grammar needs 1 \\"part\\" value(s) at this position, but 0 were available"
    );
}
"""

# The Rust half of `MERGED_SIDECAR`'s custom coercion; its Python half lives with the fixture.
MERGED_SUPPORT = """
/// A `type: custom(...)` value type, with the parse and render halves the sidecar names.
#[derive(Debug, Clone, PartialEq)]
pub struct Cents(pub i64);

pub fn parse_cents(text: &str) -> Result<Cents, String> {
    text.parse::<i64>().map(Cents).map_err(|error| format!("not a count of cents: {error}"))
}

pub fn render_cents(value: &Cents) -> String {
    value.0.to_string()
}
"""

MERGED_RUNTIME = """//! `to_cst` where a trial picks the alternative, and a custom coercion renders the text.

use super::ast::{Amount, Choice, Doc, Import, Pick, Tagged};
use super::cst;
use super::Cents;
use ::fltk_cst_core::Span;

fn import(alias: Option<&str>) -> Import {
    Import {
        name: "core".to_string(),
        alias: alias.map(str::to_string),
        span: Span::unknown(),
    }
}

fn choice(a: Option<&str>, b: Option<&str>) -> Choice {
    Choice {
        a: a.map(str::to_string),
        b: b.map(str::to_string),
        span: Span::unknown(),
    }
}

fn cents(count: i64) -> Amount {
    Amount {
        value: Cents(count),
        span: Span::unknown(),
    }
}

fn doc(import: Import, choice: Choice) -> Doc {
    Doc {
        i: import,
        w: "wrapped".to_string(),
        t: Tagged {
            label: "tag".to_string(),
            n: Some(7),
            span: Span::unknown(),
        },
        m: cents(1234),
        c: choice,
        p: Pick {
            x: Some("here".to_string()),
            y: None,
            span: Span::unknown(),
        },
        span: Span::unknown(),
    }
}

fn import_labels(value: &Import) -> Vec<Option<cst::ImportLabel>> {
    let node = value.to_cst().expect("a populated import must synthesise");
    let guard = node.read();
    guard.children().iter().map(|(label, _)| label.clone()).collect()
}

#[test]
fn the_first_alternative_that_covers_the_populated_fields_wins() {
    assert_eq!(import_labels(&import(None)), vec![Some(cst::ImportLabel::Name)]);
    assert_eq!(
        import_labels(&import(Some("kernel"))),
        vec![Some(cst::ImportLabel::Name), Some(cst::ImportLabel::Alias)]
    );
}

#[test]
fn a_document_of_trialled_shapes_reads_back_as_the_value_it_was_built_from() {
    let values = [
        doc(import(None), choice(Some("left"), None)),
        doc(import(Some("kernel")), choice(None, Some("right"))),
    ];
    for value in values {
        let node = value.to_cst().expect("a hand-built document must synthesise");
        assert_eq!(Doc::from_cst(&node).expect("a synthesised CST must convert"), value);
    }
}

#[test]
fn a_value_no_alternative_covers_is_refused() {
    for value in [choice(None, None), choice(Some("left"), Some("right"))] {
        let error = value.to_cst().expect_err("one alternative has to carry every populated field");
        assert_eq!(error.message, "rule \\"choice\\": no alternative fits the populated fields");
    }
}

#[test]
fn a_custom_coercion_goes_out_and_comes_back_through_the_sidecars_functions() {
    let node = cents(1234).to_cst().expect("a count of cents renders");
    assert_eq!(node.read().span().text().as_deref(), Some("1234"));
    assert_eq!(
        Amount::from_cst(&node).expect("and parses back").value,
        Cents(1234)
    );
}

#[test]
fn a_custom_rendering_the_terminal_rejects_is_refused() {
    let error = cents(-5).to_cst().expect_err("the terminal carries digits only");
    assert_eq!(
        error.message,
        "rule \\"amount\\": text \\"-5\\" is not something the rule could have matched"
    );
}

#[test]
fn one_branch_of_an_alternation_has_to_carry_the_populated_fields() {
    let both = Pick {
        x: Some("here".to_string()),
        y: Some(7),
        span: Span::unknown(),
    };
    let error = both.to_cst().expect_err("no branch carries both");
    assert!(error.message.contains("cannot come from one branch"), "{}", error.message);
    let neither = Pick {
        x: None,
        y: None,
        span: Span::unknown(),
    };
    let error = neither.to_cst().expect_err("the alternation is not optional");
    assert!(error.message.contains("but none is populated"), "{}", error.message);
}

#[test]
fn a_flattened_wrapper_with_nothing_to_carry_collapses() {
    let absent = Tagged {
        label: "tag".to_string(),
        n: None,
        span: Span::unknown(),
    };
    let node = absent.to_cst().expect("a tag with no bracket must synthesise");
    let children = {
        let guard = node.read();
        guard.children().len()
    };
    assert_eq!(children, 1, "the wrapper is not rebuilt around nothing");
    assert_eq!(Tagged::from_cst(&node).expect("a synthesised CST must convert"), absent);
}
"""

# The hoist path through the serde frontend, over nodes the AST layer synthesised: a field two
# names away from the node it is served on, and the optional wrapper that empties both of them.
TASK_SERDE_RUNTIME = """
// --- the serde frontend, over the same wrapper ----------------------------------------------

use super::de;
use serde::Deserialize;

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct TaskTarget {
    name: String,
    interval: Option<i64>,
    unit: Option<Unit>,
    settings: Vec<SettingTarget>,
}

#[derive(Debug, Deserialize, PartialEq)]
enum Unit {
    Sec,
    Min,
    Hour,
}

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct SettingTarget {
    key: String,
    value: i64,
}

fn deserialized(value: &TaskDef) -> TaskTarget {
    let node = value.to_cst().expect("a hand-built task must synthesise");
    de::from_task_def_cst(&node).expect("a synthesised CST must deserialize")
}

#[test]
fn a_hoisted_field_is_read_down_the_wrapper_the_grammar_spells_it_in() {
    assert_eq!(
        deserialized(&task(Some(5), Some(TimeUnitValue::Min))),
        TaskTarget {
            name: "nightly".to_string(),
            interval: Some(5),
            unit: Some(Unit::Min),
            settings: vec![SettingTarget {
                key: "retries".to_string(),
                value: 3,
            }],
        }
    );
}

#[test]
fn an_absent_optional_wrapper_leaves_out_every_field_it_carried() {
    assert_eq!(
        deserialized(&task(None, None)),
        TaskTarget {
            name: "nightly".to_string(),
            interval: None,
            unit: None,
            settings: vec![SettingTarget {
                key: "retries".to_string(),
                value: 3,
            }],
        }
    );
}
"""

BOXED_LINK_GRAMMAR = (
    "expr := d:atom , ( , op:sub , d:atom)* ;\n"
    'sub := "[" . e:expr . "]" ;\n'
    "atom := id:ident , amount:money , tags:word* , note:word? ;\n"
    "ident := $/[0-9a-fA-F-]+/ ;\nmoney := $/[0-9.]+/ ;\nword := w:/[a-z]+/ ;\n"
)
BOXED_LINK_SIDECAR = (
    "rule expr  { fold_left: op; }\n"
    "rule ident { type: uuid; transparent; }\n"
    "rule money { type: decimal; transparent; }\n"
    "rule word  { transparent; }\n"
)

BOXED_LINK_RUNTIME = """//! Teardown of a chain whose link variant the recursion analysis boxes.

use super::ast::{Atom, Expr, ExprBinary, Sub};
use ::fltk_cst_core::Span;

fn atom() -> Atom {
    Atom {
        id: ::fltk_ast_core::Uuid::nil(),
        amount: ::fltk_ast_core::Decimal::ZERO,
        tags: Vec::new(),
        note: None,
        span: Span::unknown(),
    }
}

#[test]
fn a_chain_behind_a_boxed_link_variant_tears_down_without_recursing() {
    // Derived glue at this chain length is a stack overflow, which is a process abort — so
    // there is nothing to assert after the drop.
    const LINKS: usize = 150_000;
    let span = Span::unknown();
    let operands: Vec<(Atom, Span)> = (0..=LINKS).map(|_| (atom(), span.clone())).collect();
    let operators: Vec<Box<Sub>> = (0..LINKS)
        .map(|_| {
            Box::new(Sub {
                e: Box::new(Expr::Operand(atom())),
                span: span.clone(),
            })
        })
        .collect();
    let chain = ::fltk_ast_core::fold_left(
        "expr",
        &span,
        operands,
        operators,
        Expr::Operand,
        |op, lhs, rhs, span| {
            Expr::Binary(Box::new(ExprBinary {
                op,
                lhs: Box::new(lhs),
                rhs: Box::new(rhs),
                span,
            }))
        },
    )
    .expect("a long run of operands folds");
    assert!(matches!(chain, Expr::Binary(_)));
    drop(chain);
}
"""

UNION_LABEL_GRAMMAR = (
    "misfit := x:num , y:word | x:word ;\n"
    'opt := x:num? , y:word | x:word? , "!" ;\n'
    'rep := x:num* , y:word | x:word* , "?" ;\n'
    'deep := "(" . b:deep . ")" | b:word ;\n'
    "num := d:/[0-9]+/ ;\nword := w:/[a-z]+/ ;\n"
)
UNION_LABEL_SIDECAR = "rule misfit { product; }\nrule opt { product; }\nrule rep { product; }\nrule deep { product; }\n"

UNION_LABEL_RUNTIME = """//! Selection by the kind a union label carries, in each container it is spelled for.

use super::ast::{Deep, DeepB, Misfit, MisfitX, Num, Opt, OptX, Rep, RepX, Word};
use ::fltk_cst_core::Span;

fn word(text: &str) -> Word {
    Word {
        text: text.to_string(),
        span: Span::unknown(),
    }
}

fn num(text: &str) -> Num {
    Num {
        text: text.to_string(),
        span: Span::unknown(),
    }
}

#[test]
fn each_kind_selects_the_alternative_whose_position_accepts_it() {
    let values = [
        Misfit {
            x: MisfitX::Num(num("1")),
            y: Some(word("a")),
            span: Span::unknown(),
        },
        Misfit {
            x: MisfitX::Word(word("b")),
            y: None,
            span: Span::unknown(),
        },
    ];
    for value in values {
        let node = value.to_cst().expect("a hand-built value must synthesise");
        assert_eq!(Misfit::from_cst(&node).expect("a synthesised CST must convert"), value);
    }
}

#[test]
fn a_kind_the_fitting_alternative_cannot_accept_leaves_none_fitting() {
    // The populated names are the first alternative's, the kind is the second's, and no
    // alternative carries both — the terminal path of the trial.
    let value = Misfit {
        x: MisfitX::Word(word("b")),
        y: Some(word("a")),
        span: Span::unknown(),
    };
    let error = value.to_cst().expect_err("no alternative accepts that kind at that name");
    assert_eq!(
        error.message,
        "rule \\"misfit\\": no alternative fits the populated fields"
    );
}

#[test]
fn an_optional_union_field_constrains_nothing_while_it_is_absent() {
    let absent = Opt {
        x: None,
        y: Some(word("a")),
        span: Span::unknown(),
    };
    let node = absent.to_cst().expect("an absent optional must synthesise");
    assert_eq!(Opt::from_cst(&node).expect("a synthesised CST must convert"), absent);

    let present = Opt {
        x: Some(OptX::Word(word("b"))),
        y: None,
        span: Span::unknown(),
    };
    let node = present.to_cst().expect("a populated optional must synthesise");
    assert_eq!(Opt::from_cst(&node).expect("a synthesised CST must convert"), present);

    let misfit = Opt {
        x: Some(OptX::Word(word("b"))),
        y: Some(word("a")),
        span: Span::unknown(),
    };
    let error = misfit.to_cst().expect_err("the alternative carrying `y` takes a num at `x`");
    assert_eq!(error.message, "rule \\"opt\\": no alternative fits the populated fields");
}

#[test]
fn every_value_of_a_repeated_union_field_has_to_be_an_accepted_kind() {
    let all_words = Rep {
        x: vec![RepX::Word(word("a")), RepX::Word(word("b"))],
        y: None,
        span: Span::unknown(),
    };
    let node = all_words.to_cst().expect("a list of one kind must synthesise");
    assert_eq!(Rep::from_cst(&node).expect("a synthesised CST must convert"), all_words);

    for mixed in [
        vec![RepX::Word(word("a")), RepX::Num(num("1"))],
        vec![RepX::Num(num("1")), RepX::Word(word("a"))],
    ] {
        let value = Rep {
            x: mixed,
            y: None,
            span: Span::unknown(),
        };
        let error = value.to_cst().expect_err("no alternative places both kinds");
        assert_eq!(error.message, "rule \\"rep\\": no alternative fits the populated fields");
    }
}

#[test]
fn a_union_field_held_through_a_box_is_tested_where_it_lies() {
    let leaf = Deep {
        b: Box::new(DeepB::Word(word("a"))),
        span: Span::unknown(),
    };
    let node = leaf.to_cst().expect("the leaf spelling must synthesise");
    assert_eq!(Deep::from_cst(&node).expect("a synthesised CST must convert"), leaf);

    let nested = Deep {
        b: Box::new(DeepB::Deep(Box::new(leaf))),
        span: Span::unknown(),
    };
    let node = nested.to_cst().expect("the nested spelling must synthesise");
    assert_eq!(Deep::from_cst(&node).expect("a synthesised CST must convert"), nested);
}
"""

# A `multi` keyed collection whose element is the recursive type: the accumulating `from_cst`,
# the grouped synthesis, and the equality walk's key-then-run arm, which is the one shape a
# `Vec`-valued map makes the plain map arm unable to compile.
MULTI_TREE_GRAMMAR = 'doc := , node* ;\nnode := key:word , "{" , node* , "}" , ;\nword := w:/[a-z]+/ ;\n'
MULTI_TREE_SIDECAR = "rule word { transparent; }\nrule node { key: key multi; }\n"

MULTI_TREE_RUNTIME = """//! `key: <label> multi;` over a recursive element, run against real parses.

use super::ast::{Doc, Node};
use super::parser::Parser;

const TEXT: &str = "a { } b { } a { x { } }";

fn doc(text: &str) -> Doc {
    let mut parser = Parser::new(text, None, false);
    let parsed = parser.apply__parse_doc(0).expect("the document must parse");
    assert!(parsed.pos as usize == text.len(), "the parse must consume the whole document");
    Doc::from_cst(&parsed.result).expect("a parser-produced CST must convert")
}

#[test]
fn elements_sharing_a_key_accumulate_in_source_order() {
    let parsed = doc(TEXT);
    // Insertion order is where each key first occurred, and the run is source order within it.
    assert_eq!(parsed.node.keys().collect::<Vec<_>>(), vec!["a", "b"]);
    assert_eq!(parsed.node["a"].len(), 2);
    assert_eq!(parsed.node["b"].len(), 1);
    assert!(parsed.node["a"][0].node.is_empty());
    assert_eq!(parsed.node["a"][1].node["x"].len(), 1);
}

#[test]
fn the_key_stays_a_field_of_each_element() {
    let parsed = doc(TEXT);
    assert_eq!(parsed.node["a"][0].key, "a");
    assert_eq!(parsed.node["a"][1].key, "a");
}

#[test]
fn a_multi_map_of_a_recursive_element_compares_by_key_then_elementwise() {
    let parsed = doc(TEXT);
    assert_eq!(doc("  a { }  b { }  a { x { } }  "), parsed);
    // A difference inside one key's run, which only an elementwise comparison can see.
    assert_ne!(doc("a { } b { } a { y { } }"), parsed);
    // A shorter run under a key both values carry.
    assert_ne!(doc("a { } b { }"), parsed);
    // A key one value does not carry at all.
    assert_ne!(doc("a { } c { } a { x { } }"), parsed);
}

#[test]
fn a_parsed_value_synthesises_the_cst_it_was_read_from() {
    let parsed = doc(TEXT);
    let node = parsed.to_cst().expect("a parsed value must synthesise");
    assert_eq!(Doc::from_cst(&node).expect("a synthesised CST must convert"), parsed);
}

#[test]
fn a_key_with_no_element_cannot_be_rendered() {
    // The key lives on the element, so a group holding none has nothing to carry it.
    let mut node = ::fltk_ast_core::IndexMap::new();
    node.insert("a".to_string(), Vec::<Node>::new());
    let value = Doc {
        node,
        span: ::fltk_cst_core::Span::unknown(),
    };
    let error = value.to_cst().expect_err("an empty group is unrenderable");
    assert_eq!(error.message, "rule \\"node\\": the \\"a\\" key has no element to render it on");
}
"""

# The pure bring-your-own-structs mode: a serde module generated with no AST module beside it,
# which emits zero public types and is what the CLI's `--ast-mod-path`-less invocation produces.
# Every other serde case names an AST module, so nothing else compiles the
# no-AST form — and an unused import or a dangling `ast::` reference in it is a hard build
# failure in a consumer denying warnings.
NO_AST_GRAMMAR = 'doc := name:word , "=" , count:num , ";" , ;\nword := w:/[a-z]+/ ;\nnum := d:/[0-9]+/ ;\n'
NO_AST_SIDECAR = "rule word { transparent; }\nrule num  { transparent; }\n"

NO_AST_SERDE_RUNTIME = """//! A generated `de.rs` with no AST module behind it.

use super::de;
use serde::Deserialize;

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Doc {
    name: String,
    count: u16,
}

#[test]
fn a_serde_module_generated_without_an_ast_module_deserializes_on_its_own() {
    let doc: Doc = de::from_str("port = 8080;", None).expect("the document must parse and deserialize");
    assert_eq!(
        doc,
        Doc {
            name: "port".to_string(),
            count: 8080,
        }
    );
}

#[test]
fn its_errors_are_positioned_by_the_same_frames() {
    let error = de::from_str::<Doc>("port = 99999;", None).expect_err("99999 is no u16");
    assert_eq!(
        error.to_string(),
        "rule \\"num\\": \\"99999\\" is not in range for u16 (0 to 65535) at line 1, column 8"
    );
}
"""

# `docs/rust-serde-guide.md`'s worked example — the before/after that sells the layer's
# motivating shape — as generation input. A guide example is public instruction for out-of-tree
# consumers and rots silently: this one shipped a sidecar that failed at generation time.
# `tests/test_doc_guide_cli_examples.py` holds these two strings to what the guide prints,
# so the printed example is the compiled one.
SERDE_GUIDE_GRAMMAR = """channel_def    := "channel" : name:identifier , "{" , channel_option* , "}" , ;
channel_option := key:identifier , ":" , (value:boolean | value:word) , ";" , ;
identifier     := text:/[a-z_][a-z0-9_]*/ ;
word           := text:/[a-zA-Z0-9_.]+/ ;
boolean        := true:"true" | false:"false" ;
"""

SERDE_GUIDE_SIDECAR = """rule identifier    { transparent; }
rule word          { transparent; }
rule boolean       { bool: true; transparent; }
rule channel_option { key: key; }
"""

SERDE_GUIDE_RUNTIME = """//! The serde guide's worked example: a generic keyed region, keys named by the target.

use super::de;
use serde::Deserialize;

/// A keyed entry's value is the element minus the field that keys it — here, `value`.
#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct Value<T> {
    value: T,
}

#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct ChannelOptions {
    protocol: Value<String>,
    port: Value<u16>,
    verbose: Option<Value<bool>>,
}

/// The guide prints the options struct alone; the goal rule is the channel it sits in.
#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct ChannelDef {
    name: String,
    channel_option: ChannelOptions,
}

const TEXT: &str = "channel main {\\n    protocol: tcp;\\n    port: 8080;\\n    verbose: true;\\n}\\n";

#[test]
fn the_keys_the_target_names_are_read_out_of_the_generic_region() {
    let channel: ChannelDef = de::from_str(TEXT, Some("app.conf")).expect("the channel must deserialize");
    assert_eq!(
        channel,
        ChannelDef {
            name: "main".to_string(),
            channel_option: ChannelOptions {
                protocol: Value {
                    value: "tcp".to_string()
                },
                port: Value { value: 8080 },
                verbose: Some(Value { value: true }),
            },
        }
    );
}

#[test]
fn an_option_the_document_omits_is_none() {
    let text = "channel main {\\n    protocol: tcp;\\n    port: 8080;\\n}\\n";
    let channel: ChannelDef = de::from_str(text, None).expect("verbose is optional in the target");
    assert_eq!(channel.channel_option.verbose, None);
}

#[test]
fn a_misspelled_key_is_serdes_message_at_the_offending_keys_position() {
    let text = "channel main {\\n    protocol: tcp;\\n    port: 8080;\\n    prot: tcp;\\n}\\n";
    let error = de::from_str::<ChannelDef>(text, None).expect_err("`prot` is not a key of the target");
    assert_eq!(
        error.to_string(),
        "unknown field `prot`, expected one of `protocol`, `port`, `verbose` at line 4, column 5"
    );
}
"""

# A grammar with a rule name for every std item the two shadowable emitters spell, so a respelling
# of any construct this grammar instantiates fails the case at compile time: `option` and `result`
# for the generic types, `vec` for a keyed region, `box` for a recursive indirection, `string` for
# the terminal text member, `drop` for a fold rule (its `impl Drop` collides with `pub enum Drop`),
# `partial_eq` for the equality impls both modules write out, `iterator` / `into_iterator` / `into`
# for the accessor and mutator signatures in `cst.rs`, `clone` for a derive-list name, and a
# sidecar rename to `Debug` — the derive-list witness on the ast side, exercised via the rename path.
#
# Shadowing is module-wide, so declaring a type is all a rule has to do for every spelling of that
# name in the module to be under shadow; most of these rules therefore carry no runtime assertion
# and compilation is the whole test. `partial_eq` and `into` carry a single-node-typed label because
# only that label kind produces an `impl ::std::convert::Into<Shared<T>>` mutator signature.
#
# `tag` and `join` bear no std name: they are here because `ast.rs` has emission sites the std-named
# rules do not reach — a union label's field-enum converter, and the text sentinel a fold's
# iterative teardown writes back — and a site the grammar never instantiates is a site rustc never
# sees. What compilation still cannot witness (an emission site *no* grammar in the suite reaches,
# and the `#[cfg(feature = "python")]` half of `cst.rs`, which the gate crate never enables) is
# covered textually by `tests/test_rust_prelude_qualification.py`.
PRELUDE_GRAMMAR = """doc    := , vec , result , drop , box , ;
vec    := "vec" : "{" , clone* , "}" , ;
clone  := key:/[a-z]+/ , "=" , value:string , ";" , ;
result := "result" : ok:string . "!" | "result" : err:string : "why" : why:string ;
option := yes:"yes" | no:"no" ;
box    := name:string , child:box? ;
drop   := option , ( , op:string , option)* ;
string := text:/[a-z_][a-z0-9_]*/ ;
partial_eq := lhs:string , "==" , rhs:string ;
iterator := item:string+ ;
into_iterator := "runs" : "{" , into* , "}" , ;
into   := key:/[a-z]+/ , "=" , value:string , ";" , ;
tag    := item:string | item:iterator | item:/[!@#$]+/ ;
join   := term:/[a-z]+/ , ( , op:/[-+]/ , term:/[a-z]+/)* ;
"""

# `into` is keyed `multi`, so the map value is `IndexMap<K, ::std::vec::Vec<Into>>` — the spelling a
# singly-keyed region never emits; `tag` is a product over a union label, so its field-enum
# converter is emitted; `join` folds over text operands, so its teardown sentinel is a `String`.
PRELUDE_SIDECAR = """rule doc   { name: Debug; }
rule clone { key: key; }
rule into  { key: key multi; }
rule tag   { product; }
rule drop  { fold_left: op; }
rule join  { fold_left: op; }
"""

PRELUDE_RUNTIME = """//! A document of the grammar whose rule names are the std prelude's.

use super::ast;
use super::de;

const TEXT: &str = "vec { alpha = one ; beta = two ; } result ok_val! yes plus no name_a name_b\\n";

#[test]
fn a_grammar_named_after_the_prelude_parses_converts_and_deserializes() {
    let parsed = ast::parse_str(TEXT, Some("prelude.conf")).expect("the document must parse and convert");
    let deserialized: ast::Debug = de::from_str(TEXT, None).expect("the AST target must deserialize");
    assert_eq!(parsed, deserialized);

    // A keyed region owned by a type named `Vec`, over elements named `Clone`.
    assert_eq!(parsed.vec.clone.len(), 2);
    assert_eq!(parsed.vec.clone["alpha"].value.text, "one");
    assert_eq!(parsed.vec.clone["beta"].value.text, "two");

    // A sum whose matched alternative carries a payload struct.
    let ast::Result::Ok(ok) = &parsed.result else {
        panic!("the first alternative of `result` matched");
    };
    assert_eq!(ok.ok.text, "ok_val");

    // A fold chain whose operands are the value enum's node type.
    let ast::Drop::Binary(link) = &parsed.drop else {
        panic!("the chain carries one operator");
    };
    assert_eq!(link.op.text, "plus");
    let ast::Drop::Operand(lhs) = &*link.lhs else {
        panic!("the left side is a bare operand");
    };
    let ast::Drop::Operand(rhs) = &*link.rhs else {
        panic!("the right side is a bare operand");
    };
    assert_eq!(lhs.value, ast::OptionValue::Yes);
    assert_eq!(rhs.value, ast::OptionValue::No);

    // The recursive field its owner holds through an indirection.
    assert_eq!(parsed.r#box.name.text, "name_a");
    let child = parsed.r#box.child.as_ref().expect("the outer box carries a child");
    assert_eq!(child.name.text, "name_b");
    assert!(child.child.is_none());
}
"""

# `docs/ast-guide.md`'s quick start — the `calc` grammar and sidecar a new consumer copies first —
# as generation input. `tests/test_doc_guide_cli_examples.py` holds these two strings to what the
# guide prints and runs the Python half of the same quick start, so the printed example is the
# compiled one on both backends.
AST_GUIDE_GRAMMAR = """expr   := term:number , ( , op:add_op , term:number)* ;
add_op := plus:"+" | minus:"-" ;
number := val:/[0-9]+/ ;
"""

AST_GUIDE_SIDECAR = """rule number { type: i64; transparent; }
rule add_op { transparent; }
rule expr   { fold_left: op; }
"""

# The Rust the guide's quick start prints, as its own constant so that the gate compiles the printed
# bytes rather than a hand-written mirror of them: `AST_GUIDE_RUNTIME` wraps it in a function, and
# the join test in `tests/test_doc_guide_cli_examples.py` holds it to the guide's fenced block. A
# mirror can drift silently, which is the defect class the printed example exists to be free of.
AST_GUIDE_SNIPPET = """// pub enum Expr { Operand(i64), Binary(ExprBinary) }
// pub struct ExprBinary { pub op: AddOpValue, pub lhs: Box<Expr>, pub rhs: Box<Expr>, pub span: Span }

let value = ast::parse_str("1 + 2 - 3", Some("calc.txt"))?;
match value {
    ast::Expr::Binary(link) => println!("{:?} at {:?}", link.op, link.span),
    ast::Expr::Operand(n) => println!("{n}"),
}
"""

AST_GUIDE_RUNTIME = (
    """//! The AST guide's quick start: the snippet it prints, and the fold its type comments claim.

use super::ast;

/// The guide's printed snippet, verbatim, in the smallest wrapper that gives its `?` somewhere to
/// go. Every path, name and match arm it prints is checked by the compiler here.
fn the_printed_snippet() -> ::std::result::Result<(), ::fltk_ast_core::ParseToAstError> {
"""
    + AST_GUIDE_SNIPPET
    + """    Ok(())
}

#[test]
fn the_snippet_the_guide_prints_runs_over_the_input_it_prints() {
    the_printed_snippet().expect("the printed expression must parse and convert");
}

#[test]
fn the_printed_expression_folds_left_into_the_types_the_comment_names() {
    let value = ast::parse_str("1 + 2 - 3", Some("calc.txt")).expect("the quick start's expression must parse");

    // `pub enum Expr { Operand(i64), Binary(ExprBinary) }`, as the guide prints it.
    let ast::Expr::Binary(link) = &value else {
        panic!("two operators fold into a link");
    };
    assert_eq!(link.op, ast::AddOpValue::Minus);
    assert_eq!(link.span.text().as_deref(), Some("1 + 2 - 3"));

    // The `pub struct ExprBinary { … }` the comment prints, member by member: the annotations fail
    // to compile if a printed name or type is not the one the emitter produces. The comment is the
    // half of the snippet rustc would otherwise ignore.
    let _: &ast::ExprBinary = link;
    let _: &ast::AddOpValue = &link.op;
    let _: &::std::boxed::Box<ast::Expr> = &link.lhs;
    let _: &::std::boxed::Box<ast::Expr> = &link.rhs;
    let _: &::fltk_cst_core::Span = &link.span;

    // A left fold nests the earlier operator deeper, so the operands read 1, 2, 3 in source order.
    let ast::Expr::Binary(inner) = link.lhs.as_ref() else {
        panic!("the left side of a left fold is the deeper chain");
    };
    assert_eq!(inner.op, ast::AddOpValue::Plus);
    let ast::Expr::Operand(first) = inner.lhs.as_ref() else {
        panic!("the deepest left side is a bare operand");
    };
    let ast::Expr::Operand(second) = inner.rhs.as_ref() else {
        panic!("the inner right side is a bare operand");
    };
    let ast::Expr::Operand(third) = link.rhs.as_ref() else {
        panic!("the outer right side is a bare operand");
    };
    // The `Operand(i64)` payload the printed `pub enum Expr` claims.
    let _: i64 = *first;
    assert_eq!((*first, *second, *third), (1, 2, 3));
}

#[test]
fn the_snippets_other_arm_is_the_operand_the_coercion_carries() {
    let value = ast::parse_str("42", None).expect("one number is a whole expression");
    let ast::Expr::Operand(n) = value else {
        panic!("one operand does not fold into a link");
    };
    assert_eq!(n, 42_i64);
}
"""
)

CASES = [
    # A sum, a keyed collection, every scalar erasure, a coercion, a renamed field, and a
    # label spelled `type` (so `r#type` is exercised). Carries the entry-point tests too, which
    # need the same grammar behind a formatter.
    Case(
        "config",
        fixtures.CONFIG_GRAMMAR,
        fixtures.KEYED_SIDECAR,
        runtime=CONFIG_RUNTIME + ENTRY_POINT_RUNTIME + CONFIG_SERDE_RUNTIME,
        parser=True,
        unparser=True,
        serde=True,
    ),
    # Two precedence folds over an operand that reaches the whole expression again, so the chain
    # links, the by-value cycle and the bounded-stack equality all land in one module.
    Case(
        "fold",
        fixtures.FOLD_GRAMMAR,
        fixtures.FOLD_SIDECAR,
        runtime=FOLD_RUNTIME + FOLD_ENTRY_POINT_RUNTIME + FOLD_SERDE_RUNTIME,
        parser=True,
        serde=True,
    ),
    Case(
        "literal_labels",
        LITERAL_LABEL_GRAMMAR,
        runtime=LITERAL_LABEL_RUNTIME,
        parser=True,
        unparser=True,
    ),
    # The leaf node forms of the serialize direction, built by hand and read back.
    Case("serialize", fixtures.LEAF_GRAMMAR, fixtures.LEAF_SIDECAR, runtime=SERIALIZE_RUNTIME),
    # A flattened wrapper at an optional use site, hoisting two fields into its parent.
    Case(
        "task",
        fixtures.TASK_GRAMMAR,
        fixtures.TASK_SIDECAR,
        runtime=TASK_RUNTIME + TASK_SERDE_RUNTIME,
        serde=True,
    ),
    # Two alternatives one of which extends the other, plus the multi-alternative erased and
    # flattened reverse helpers and a custom coercion — the branches no other case compiles.
    Case(
        "merged",
        fixtures.MERGED_GRAMMAR,
        fixtures.MERGED_SIDECAR,
        runtime=MERGED_RUNTIME,
        support=MERGED_SUPPORT,
    ),
    # A sum whose rule holds one kind of child: every dispatch clause is a bare increment, so
    # nothing reads the child and binding it by name is an unused variable.
    Case("single_kind_sum", 's := a:word . "!" | b:word . c:word ;\nword := w:/[a-z]+/ ;\n'),
    # A sum whose rule holds several kinds: the dispatch tests the child, and the destructures
    # in the payload converters are refutable.
    Case("multi_kind_sum", "s := a:word . b:other | c:other ;\nword := w:/[a-z]+/ ;\nother := o:/[0-9]+/ ;\n"),
    # Labeled literals at both arities, a presence flag, a field enum that cannot hold every
    # child kind, and `text_from:` — the positions that read a span child.
    Case(
        "shapes",
        'doc := bang:"!" , stars:"*"* , pub:"pub"? , ( a:num | a:word ) , b:other'
        ' , part:word , ( "." . part:word )* , s:string_literal ;\n'
        "num := d:/[0-9]+/ ;\nword := w:/[a-z]+/ ;\nother := o:/[A-Z]+/ ;\n"
        'string_literal := "\\"" . content:/[^"\\\\]*/ . "\\"" ;\n',
        "rule string_literal { text_from: content; }\n",
        runtime=SHAPES_RUNTIME,
    ),
    # A self-reference at every arity: the boxed edges and the bounded-stack equality walk.
    Case("tree", "tree := name:word , child:tree? , kids:tree* ;\nword := w:/[a-z]+/ ;\n"),
    # A map whose element is the recursive type, compared by key lookup rather than by zipping.
    Case(
        "keyed_tree",
        "node := key:word , kid:node? , kids:node* ;\nword := w:/[a-z]+/ ;\n",
        "rule word { transparent; }\nrule node { key: key; }\n",
    ),
    # The same map accumulating instead: `Vec`-valued keys through `from_cst`, `to_cst` and the
    # equality walk, over an element type that reaches itself.
    Case(
        "multi_tree",
        MULTI_TREE_GRAMMAR,
        MULTI_TREE_SIDECAR,
        runtime=MULTI_TREE_RUNTIME,
        parser=True,
    ),
    # A flattened wrapper whose hoisted field closes the cycle: without the `Box` the containing
    # type is infinitely sized.
    Case(
        "cycle_flatten",
        'tree := name:word . wrap? ;\nwrap := "(" . t:tree . ")" ;\nword := w:/[a-z]+/ ;\n',
        "rule wrap { flatten; }\n",
    ),
    # A flattened wrapper hoisting a `multi` map, which is the one place the emitted parameter
    # type of a keyed field is written: a helper taking `&IndexMap<K, T>` where the field is
    # `&IndexMap<K, Vec<T>>` compiles nowhere else, so the compiler is the witness.
    Case(
        "multi_flatten",
        'doc := "doc" : box:group ;\ngroup := "{" , entry* , "}" ;\n'
        'entry := key:word , "=" , v:num , ";" , ;\nword := w:/[a-z]+/ ;\nnum := d:/[0-9]+/ ;\n',
        "rule word  { transparent; }\nrule num   { type: i64; transparent; }\n"
        "rule entry { key: key multi; }\nrule group { flatten; }\n",
    ),
    # The two builtins whose value type comes from the runtime's feature-gated re-exports.
    Case(
        "wide_builtins",
        "doc := id:ident , amount:money ;\nident := $/[0-9a-fA-F-]+/ ;\nmoney := $/[0-9.]+/ ;\n",
        "rule ident { type: uuid; }\nrule money { type: decimal; }\n",
    ),
    # A fold whose operator rule re-enters the fold, so the recursion analysis boxes the link
    # variant — the one `Drop` shape the other fold case cannot compile. Its operand is a struct
    # over the two feature-gated builtins, a `Vec` and an `Option`, which is likewise the only
    # input reaching the struct-witness renderer and the empty-container spellings under `cargo`.
    Case(
        "boxed_link_fold",
        BOXED_LINK_GRAMMAR,
        BOXED_LINK_SIDECAR,
        runtime=BOXED_LINK_RUNTIME,
    ),
    # One label carrying two kinds, at every container the selection conjunct is spelled for:
    # a bare member, an `Option`, a `Vec`, and one held through a `Box`. The compiled half of
    # kind-aware alternative selection, including the trial's terminal error.
    Case(
        "union_label",
        UNION_LABEL_GRAMMAR,
        UNION_LABEL_SIDECAR,
        runtime=UNION_LABEL_RUNTIME,
    ),
    # A serde module with no AST module beside it, which is the frontend's headline mode and the
    # one configuration no other case compiles.
    Case(
        "no_ast",
        NO_AST_GRAMMAR,
        NO_AST_SIDECAR,
        runtime=NO_AST_SERDE_RUNTIME,
        ast=False,
        serde=True,
        parser=True,
    ),
    # The serde guide's worked example, compiled and run as printed.
    Case(
        "serde_guide",
        SERDE_GUIDE_GRAMMAR,
        SERDE_GUIDE_SIDECAR,
        runtime=SERDE_GUIDE_RUNTIME,
        ast=False,
        serde=True,
        parser=True,
        goal="channel_def",
    ),
    # Rule names that shadow the std prelude, so every emitted std spelling has to be absolute.
    # The unparser is generated too: its emitter keeps std items bare on the argument that
    # `unparser.rs` declares no grammar-derived module-level item, and compiling it beside a
    # grammar that shadows every one of those names is what turns that argument into a witness.
    Case(
        "prelude",
        PRELUDE_GRAMMAR,
        PRELUDE_SIDECAR,
        runtime=PRELUDE_RUNTIME,
        parser=True,
        serde=True,
        unparser=True,
        goal="doc",
    ),
    # The AST guide's quick start, generated from the grammar and sidecar the guide prints and run
    # against the values its snippet destructures.
    Case(
        "ast_guide",
        AST_GUIDE_GRAMMAR,
        AST_GUIDE_SIDECAR,
        runtime=AST_GUIDE_RUNTIME,
        parser=True,
        goal="expr",
    ),
    # A marker product and a `custom(...)` rule reached through the `FromCst` trait.
    Case(
        "holder",
        'holder := amount:money , m:marker ;\nmoney := d:/[0-9]+/ ;\nmarker := $"!" . $"?" ;\n',
        'rule money { custom(rust: "crate::holder::Money", python: "app.Money"); }\n',
        support=(
            "\n"
            "/// A `custom(...)` rule's type: the generated converter reaches it through the trait,\n"
            "/// never by inherent method, so a type of the consumer's own works unchanged.\n"
            "#[derive(Debug, Clone, PartialEq)]\n"
            "pub struct Money(pub String);\n"
            "\n"
            "impl ::fltk_ast_core::FromCst<::fltk_cst_core::Shared<cst::Money>> for Money {\n"
            "    fn from_cst(node: &::fltk_cst_core::Shared<cst::Money>)"
            " -> Result<Self, ::fltk_ast_core::AstError> {\n"
            "        let guard = node.read();\n"
            '        Ok(Self(::fltk_ast_core::node_text(guard.span(), "money")?))\n'
            "    }\n"
            "}\n"
            "\n"
            "/// The reverse half of the same convention: a rule whose AST is generated needs both,\n"
            "/// because the generated product referencing it serializes through this one.\n"
            "impl ::fltk_ast_core::ToCst<::fltk_cst_core::Shared<cst::Money>> for Money {\n"
            "    fn to_cst(&self) -> Result<::fltk_cst_core::Shared<cst::Money>,"
            " ::fltk_ast_core::AstError> {\n"
            "        let mut node = cst::Money::new(::fltk_ast_core::source_span(&self.0));\n"
            "        node.push_child(\n"
            "            Some(cst::MoneyLabel::D),\n"
            "            cst::MoneyChild::Span(::fltk_ast_core::source_span(&self.0)),\n"
            "        );\n"
            "        Ok(node.into())\n"
            "    }\n"
            "}\n"
        ),
    ),
]


@pytest.fixture(scope="module")
def gate(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The generated gate crate's manifest; written once for the whole module."""
    directory = tmp_path_factory.mktemp("generated_rust_gate")
    return write_crate(directory, CASES)


@pytest.fixture(scope="module")
def clippy(gate: Path) -> subprocess.CompletedProcess[str]:
    return run_cargo("clippy", gate, gate.parent / "target", "--all-targets", "--", "-D", "warnings")


@pytest.fixture(scope="module")
def cargo_test(gate: Path, clippy: subprocess.CompletedProcess[str]) -> subprocess.CompletedProcess[str]:
    """The runtime half, ordered after clippy so a compile failure is reported once."""
    assert clippy.returncode == 0, clippy.stdout + clippy.stderr
    return run_cargo("test", gate, gate.parent / "target")


def test_the_generated_modules_compile_without_a_warning(clippy: subprocess.CompletedProcess[str]) -> None:
    assert clippy.returncode == 0, clippy.stdout + clippy.stderr


def test_every_declared_shape_is_in_the_crate(gate: Path) -> None:
    """A case that silently stopped being emitted would leave the gate quietly narrower."""
    assert len(CASES) == len({case.name for case in CASES}), "case names are the module names"
    declared = gate.parent.joinpath("src", "lib.rs").read_text()
    for case in CASES:
        assert f"pub mod {case.name};" in declared
        assert gate.parent.joinpath("src", case.name, "ast.rs").is_file() == case.ast
        assert gate.parent.joinpath("src", case.name, "de.rs").is_file() == case.serde
    assert any(case.serde and not case.ast for case in CASES), "the no-AST serde mode has a compiled witness"


def _ran(output: str, case: str) -> set[str]:
    """The Rust tests of one case that ran and passed, by name.

    ``cargo test`` reports success for a crate holding no tests at all, so a runtime module that
    stopped being emitted has to fail rather than pass silently.
    """
    prefix = f"test {case}::runtime::"
    return {
        line.removeprefix(prefix).removesuffix(" ... ok") for line in output.splitlines() if line.startswith(prefix)
    }


def test_the_converters_convert_a_real_parse_and_carry_text_in_and_out(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """The config language's converters, and the `parse_str` / `unparse_str` pipeline around them.

    One module: the two share a grammar, a sidecar and a document, so they share the compile.
    """
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "config") == {
        # `from_cst` and `to_cst` over a real parse.
        "a_keyed_collection_is_looked_up_by_its_key_field",
        "an_optional_coerced_field_and_a_value_enum_come_through",
        "two_values_converted_from_identical_text_at_different_offsets_are_equal",
        "a_difference_in_semantic_data_is_not_equal",
        "a_parsed_value_synthesises_the_cst_it_was_read_from",
        "a_mutated_value_round_trips_and_keeps_its_map_in_order",
        "text_the_rules_terminal_cannot_match_is_refused",
        # Sum dispatch over a hand-built node, which is the only way to reach either case.
        "a_child_no_alternative_accepts_under_its_label_matches_no_alternative",
        "an_unlabeled_child_is_not_counted_against_any_alternative",
        "a_repeated_key_reports_both_locations",
        # The entry points, either side of a round trip through text.
        "one_call_turns_source_text_into_an_ast",
        "the_round_trip_law_holds_through_text",
        "a_mutated_value_renders_its_change_and_reads_back_as_itself",
        "the_renderer_dimensions_reach_the_output",
        "input_the_goal_rule_did_not_consume_is_the_parse_arm",
        "a_conversion_failure_is_the_ast_arm",
        "text_no_terminal_accepts_is_refused_before_anything_is_rendered",
        # The serde frontend over the same document, against the emitted descriptions.
        "one_call_turns_source_text_into_the_targets_the_consumer_declared",
        "the_same_keyed_region_is_a_sequence_where_the_target_asks_for_one",
        "an_unknown_field_is_serdes_own_message_at_the_offending_child",
        "a_field_the_target_needs_and_the_source_omits_is_missing_at_the_node",
        "a_scalar_target_runs_the_gate_its_type_names_over_the_source_text",
        "a_repeated_key_is_refused_by_the_frontend_rather_than_left_to_the_container",
        "a_target_can_position_a_field_and_hold_a_subtree_as_cst",
        # Generated AST types as fields of hand-written targets.
        "a_field_declared_as_a_generated_ast_type_is_what_from_cst_builds",
        "an_ast_typed_field_can_be_positioned_like_any_other",
        "an_ast_type_at_another_rules_position_names_both_rules",
        "a_conversion_failure_under_an_ast_typed_field_keeps_its_own_position",
        "a_conversion_failure_keeps_its_own_span_under_a_node_that_covers_more_than_it",
        "an_ast_typed_field_reaches_every_container_the_model_has",
    }, cargo_test.stdout


def test_a_fold_rule_nests_its_operands_and_merges_their_spans(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "fold") == {
        "a_single_operand_stays_a_bare_operand",
        "a_left_fold_nests_the_earliest_operands_deepest",
        "the_tighter_precedence_level_folds_inside_the_looser_one",
        "each_link_span_covers_everything_below_it",
        "a_parenthesized_operand_closes_the_cycle_by_value",
        "spans_do_not_take_part_in_equality_but_operators_do",
        "an_operator_with_no_operand_pair_to_join_is_refused",
        "a_chain_unfolds_into_the_run_it_was_folded_from",
        "a_chain_nested_against_the_folds_direction_has_no_grammar_shape",
        "a_chain_of_two_hundred_thousand_links_tears_down_without_recursing",
        "a_text_the_goal_rule_cannot_match_is_a_parse_error",
        "the_convenience_folds_the_chain_it_parsed",
        # The same chain through the serde frontend.
        "a_chain_reaches_a_derived_enum_with_the_nesting_the_fold_gives_it",
        "a_transparent_wrapper_hands_the_target_what_it_holds",
        "a_variant_the_target_declares_as_a_unit_one_is_refused_not_emptied",
        "text_the_goal_rule_cannot_match_is_the_parse_arm_of_from_str",
        # The chain into the generated AST type instead of a hand-written enum.
        "a_generated_ast_type_is_a_target_like_any_other",
        "a_chain_held_as_syntax_converts_through_its_own_entry_point_later",
    }, cargo_test.stdout


def test_a_boxed_link_variant_carries_the_same_iterative_teardown(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """The `Drop` and witness rendering no other case compiles: a boxed link over a struct operand."""
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "boxed_link_fold") == {
        "a_chain_behind_a_boxed_link_variant_tears_down_without_recursing",
    }, cargo_test.stdout


def test_the_leaf_forms_synthesise_the_cst_they_were_read_from(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """`to_cst` on the terminal-only and enum-shaped forms: what it appends, and the round trip."""
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "serialize") == {
        "a_terminal_rules_text_comes_back_as_its_child_span",
        "a_synthesised_terminal_node_carries_its_text_as_its_own_span",
        "a_redirected_text_leaves_the_node_span_unknown_and_the_quotes_to_the_grammar",
        "the_alternative_the_text_matches_decides_the_children",
        "a_coercion_renders_through_the_canonical_renderer",
        "an_enum_shaped_value_appends_the_label_of_its_alternative",
        "a_boolean_value_appends_the_label_of_the_alternative_it_names",
        "text_the_terminal_cannot_match_is_refused",
        "every_leaf_form_reads_back_as_the_value_it_was_built_from",
    }, cargo_test.stdout


def test_a_flattened_wrapper_is_rebuilt_from_the_fields_hoisted_out_of_it(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "task") == {
        "a_wrapper_with_nothing_to_carry_is_not_rebuilt",
        "a_populated_wrapper_is_rebuilt_where_the_grammar_spells_it",
        "a_half_populated_wrapper_names_the_field_it_still_needs",
        # The hoisted fields read back through the serde frontend.
        "a_hoisted_field_is_read_down_the_wrapper_the_grammar_spells_it_in",
        "an_absent_optional_wrapper_leaves_out_every_field_it_carried",
    }, cargo_test.stdout


def test_a_multi_keyed_collection_accumulates_groups_and_compares_them_elementwise(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """`Vec`-valued keys through both directions, over an element type that reaches itself."""
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "multi_tree") == {
        "elements_sharing_a_key_accumulate_in_source_order",
        "the_key_stays_a_field_of_each_element",
        "a_multi_map_of_a_recursive_element_compares_by_key_then_elementwise",
        "a_parsed_value_synthesises_the_cst_it_was_read_from",
        "a_key_with_no_element_cannot_be_rendered",
    }, cargo_test.stdout


def test_each_field_value_reaches_the_item_position_the_grammar_gives_it(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "shapes") == {
        "every_position_appends_its_own_occurrences_in_grammar_order",
        "a_presence_flag_left_unset_appends_nothing",
        "the_branch_of_the_alternation_follows_the_variant_the_value_carries",
        "a_field_enum_over_node_payloads_answers_for_the_span_of_whichever_it_holds",
        "a_required_position_with_no_value_to_take_names_the_shortfall",
    }, cargo_test.stdout


def test_a_trial_picks_the_alternative_the_populated_fields_fit(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "merged") == {
        "the_first_alternative_that_covers_the_populated_fields_wins",
        "a_document_of_trialled_shapes_reads_back_as_the_value_it_was_built_from",
        "a_value_no_alternative_covers_is_refused",
        "a_custom_coercion_goes_out_and_comes_back_through_the_sidecars_functions",
        "a_custom_rendering_the_terminal_rejects_is_refused",
        "one_branch_of_an_alternation_has_to_carry_the_populated_fields",
        "a_flattened_wrapper_with_nothing_to_carry_collapses",
    }, cargo_test.stdout


def test_a_trial_picks_the_alternative_the_values_kinds_fit(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """The kind half of selection, compiled and run: a source assertion cannot say which
    alternative a value reaches, nor that the container spellings are valid Rust."""
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "union_label") == {
        "each_kind_selects_the_alternative_whose_position_accepts_it",
        "a_kind_the_fitting_alternative_cannot_accept_leaves_none_fitting",
        "an_optional_union_field_constrains_nothing_while_it_is_absent",
        "every_value_of_a_repeated_union_field_has_to_be_an_accepted_kind",
        "a_union_field_held_through_a_box_is_tested_where_it_lies",
    }, cargo_test.stdout


def test_a_serde_module_stands_on_its_own_without_an_ast_module(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """The bring-your-own-structs mode: no AST module, no generated public types, still a frontend."""
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "no_ast") == {
        "a_serde_module_generated_without_an_ast_module_deserializes_on_its_own",
        "its_errors_are_positioned_by_the_same_frames",
    }, cargo_test.stdout


def test_the_serde_guides_worked_example_works_as_printed(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """The guide's motivating before/after, generated from its own grammar and sidecar and run."""
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "serde_guide") == {
        "the_keys_the_target_names_are_read_out_of_the_generic_region",
        "an_option_the_document_omits_is_none",
        "a_misspelled_key_is_serdes_message_at_the_offending_keys_position",
    }, cargo_test.stdout


def test_a_grammar_whose_rule_names_shadow_the_prelude_compiles_and_runs(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """The compile witness for the absolute std spellings, plus one end-to-end run over them.

    Compiling is most of the point — a bare `Option<T>` in a module declaring `pub struct Option`
    is `E0107`, a bare `impl Drop` beside `pub enum Drop` is `E0404`, and a bare `String` member on
    the rule named `string` is an infinitely-sized type. The run is what says the qualification
    changed no behavior: the same document reaches the same value through both entry points.
    """
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "prelude") == {
        "a_grammar_named_after_the_prelude_parses_converts_and_deserializes",
    }, cargo_test.stdout


def test_the_ast_guides_quick_start_folds_as_the_guide_prints_it(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """The AST guide's first example, generated from its printed input and run.

    It is what a new consumer copies before anything else, and its printed type comments and match
    arms are a claim about the fold the sidecar produces — a claim only a run can check.
    """
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "ast_guide") == {
        "the_snippet_the_guide_prints_runs_over_the_input_it_prints",
        "the_printed_expression_folds_left_into_the_types_the_comment_names",
        "the_snippets_other_arm_is_the_operand_the_coercion_carries",
    }, cargo_test.stdout


def test_the_compiled_formatter_matches_a_labeled_literal_by_text(
    cargo_test: subprocess.CompletedProcess[str],
) -> None:
    """Labeled-literal trial matching on the shipped Rust formatter, which the byte-parity corpus cannot reach."""
    assert cargo_test.returncode == 0, cargo_test.stdout + cargo_test.stderr
    assert _ran(cargo_test.stdout, "literal_labels") == {
        "a_rival_regex_under_the_same_label_keeps_its_own_text",
        "the_literal_branch_still_renders_the_literal",
        "the_sequential_spelling_declines_the_child_it_cannot_spell",
        "a_sibling_spelling_of_one_label_is_accepted_and_canonicalized",
        "a_hand_built_span_no_position_accepts_fails_the_unparse",
        "a_synthesized_sourceless_span_still_renders_the_canonical_spelling",
    }, cargo_test.stdout
