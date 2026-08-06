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

CASES = [
    # A sum, a keyed collection, every scalar erasure, a coercion, a renamed field, and a
    # label spelled `type` (so `r#type` is exercised). Carries the entry-point tests too, which
    # need the same grammar behind a formatter.
    Case(
        "config",
        fixtures.CONFIG_GRAMMAR,
        fixtures.KEYED_SIDECAR,
        runtime=CONFIG_RUNTIME + ENTRY_POINT_RUNTIME,
        parser=True,
        unparser=True,
    ),
    # Two precedence folds over an operand that reaches the whole expression again, so the chain
    # links, the by-value cycle and the bounded-stack equality all land in one module.
    Case(
        "fold",
        fixtures.FOLD_GRAMMAR,
        fixtures.FOLD_SIDECAR,
        runtime=FOLD_RUNTIME + FOLD_ENTRY_POINT_RUNTIME,
        parser=True,
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
    Case("task", fixtures.TASK_GRAMMAR, fixtures.TASK_SIDECAR, runtime=TASK_RUNTIME),
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
    # A flattened wrapper whose hoisted field closes the cycle: without the `Box` the containing
    # type is infinitely sized.
    Case(
        "cycle_flatten",
        'tree := name:word . wrap? ;\nwrap := "(" . t:tree . ")" ;\nword := w:/[a-z]+/ ;\n',
        "rule wrap { flatten; }\n",
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
        assert gate.parent.joinpath("src", case.name, "ast.rs").is_file()


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
        "a_repeated_key_reports_both_locations",
        # The entry points, either side of a round trip through text.
        "one_call_turns_source_text_into_an_ast",
        "the_round_trip_law_holds_through_text",
        "a_mutated_value_renders_its_change_and_reads_back_as_itself",
        "the_renderer_dimensions_reach_the_output",
        "input_the_goal_rule_did_not_consume_is_the_parse_arm",
        "a_conversion_failure_is_the_ast_arm",
        "text_no_terminal_accepts_is_refused_before_anything_is_rendered",
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
