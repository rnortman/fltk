/// Pure-Rust spike tests exercising CST construction, traversal, span text,
/// merge/intersect, and structural equality — no Python linked, no unsafe.
///
/// These tests must pass under `cargo test -p fltk-cst-spike` (python feature off).
///
/// Generated types lack `Debug`, so tests use `assert!` / `matches!` instead of
/// `assert_eq!`/`assert_ne!` when the tested value is a generated type.
/// This is a gap surfaced by the spike; see gaps.md.
use fltk_cst_core::{SourceText, Span, SpanError};

use crate::cst::{
    Identifier, IdentifierChild, Identifier_Label, Items, ItemsChild, Items_Label, Trivia,
    TriviaChild, Trivia_Label,
};

// ── helpers ──────────────────────────────────────────────────────────────────

fn make_source() -> SourceText {
    SourceText::from_str("hello world foo")
}

fn span(start: i64, end: i64, src: &SourceText) -> Span {
    Span::new_with_source(start, end, src)
}

// ── node construction ─────────────────────────────────────────────────────────

#[test]
fn identifier_new_native_empty_children() {
    let src = make_source();
    let node = Identifier::new_native(span(0, 5, &src));
    assert_eq!(node.children_native().len(), 0);
}

#[test]
fn identifier_span_native_roundtrip() {
    let src = make_source();
    let sp = span(0, 5, &src);
    let node = Identifier::new_native(sp.clone());
    assert!(node.span_native() == &sp);
}

// ── labeled child append ──────────────────────────────────────────────────────

#[test]
fn identifier_push_child_labeled() {
    let src = make_source();
    let name_span = span(0, 5, &src);
    let mut node = Identifier::new_native(span(0, 5, &src));
    node.push_child_native(Some(Identifier_Label::Name), IdentifierChild::Span(name_span.clone()));
    let children = node.children_native();
    assert_eq!(children.len(), 1);
    assert!(children[0].0 == Some(Identifier_Label::Name));
    match &children[0].1 {
        IdentifierChild::Span(s) => assert!(s == &name_span),
    }
}

#[test]
fn items_push_multiple_children_with_labels() {
    let src = make_source();
    let no_ws_span = span(5, 6, &src);
    let id_span = span(6, 11, &src);

    let mut id_node = Identifier::new_native(id_span.clone());
    id_node.push_child_native(Some(Identifier_Label::Name), IdentifierChild::Span(id_span.clone()));

    let mut items = Items::new_native(span(0, 11, &src));
    items.push_child_native(Some(Items_Label::NoWs), ItemsChild::Span(no_ws_span.clone()));
    items.push_child_native(Some(Items_Label::Item), ItemsChild::Identifier(Box::new(id_node)));

    let children = items.children_native();
    assert_eq!(children.len(), 2);
    assert!(children[0].0 == Some(Items_Label::NoWs));
    assert!(children[1].0 == Some(Items_Label::Item));
}

// ── traversal ────────────────────────────────────────────────────────────────

#[test]
fn traverse_items_children_down_to_leaf_spans() {
    let src = make_source();
    let sep_span = span(5, 6, &src);
    let id_span = span(6, 11, &src);

    let mut id_node = Identifier::new_native(id_span.clone());
    id_node.push_child_native(Some(Identifier_Label::Name), IdentifierChild::Span(id_span.clone()));

    let mut items = Items::new_native(span(0, 11, &src));
    items.push_child_native(Some(Items_Label::NoWs), ItemsChild::Span(sep_span.clone()));
    items.push_child_native(Some(Items_Label::Item), ItemsChild::Identifier(Box::new(id_node)));

    let mut leaf_texts: Vec<String> = Vec::new();
    for (_label, child) in items.children_native() {
        match child {
            ItemsChild::Span(s) => {
                if let Some(t) = s.text() {
                    leaf_texts.push(t);
                }
            }
            ItemsChild::Identifier(id) => {
                for (_lbl, sub) in id.children_native() {
                    match sub {
                        IdentifierChild::Span(s) => {
                            if let Some(t) = s.text() {
                                leaf_texts.push(t);
                            }
                        }
                    }
                }
            }
            ItemsChild::Trivia(_) => {}
        }
    }
    assert_eq!(leaf_texts, vec![" ", "world"]);
}

// ── span text reads ───────────────────────────────────────────────────────────

#[test]
fn span_text_in_bounds() {
    let src = make_source();
    assert_eq!(Span::new_with_source(0, 5, &src).text().as_deref(), Some("hello"));
    assert_eq!(Span::new_with_source(6, 11, &src).text().as_deref(), Some("world"));
}

#[test]
fn span_text_sourceless_is_none() {
    let sp = Span::new_sourceless(0, 5);
    assert_eq!(sp.text(), None);
}

#[test]
fn span_text_unknown_is_none() {
    assert_eq!(Span::unknown().text(), None);
}

#[test]
fn span_has_source_and_len_and_is_empty() {
    let src = make_source();
    let sourced = Span::new_with_source(0, 5, &src);
    assert!(sourced.has_source());
    assert_eq!(sourced.len(), 5);
    assert!(!sourced.is_empty());

    let empty_sp = Span::new_with_source(5, 5, &src);
    assert!(empty_sp.is_empty());
    assert_eq!(empty_sp.len(), 0);

    let sentinel = Span::unknown();
    assert!(!sentinel.has_source());
    assert_eq!(sentinel.len(), 0);
    assert!(sentinel.is_empty());
}

// ── span merge ────────────────────────────────────────────────────────────────

#[test]
fn merge_same_source_ok() {
    let src = make_source();
    let a = span(0, 5, &src);
    let b = span(6, 11, &src);
    let merged = a.merge(&b).expect("same source merge should succeed");
    assert_eq!(merged.start(), 0);
    assert_eq!(merged.end(), 11);
    assert!(merged.has_source());
    assert_eq!(merged.text().as_deref(), Some("hello world"));
}

#[test]
fn merge_different_sources_err() {
    let src1 = SourceText::from_str("hello");
    let src2 = SourceText::from_str("world");
    let a = Span::new_with_source(0, 5, &src1);
    let b = Span::new_with_source(0, 5, &src2);
    assert!(matches!(a.merge(&b), Err(SpanError::SourceMismatch)));
}

#[test]
fn merge_sourceless_with_sourced_carries_source() {
    let src = make_source();
    let sourced = span(0, 5, &src);
    let sourceless = Span::new_sourceless(6, 11);
    let merged = sourced.merge(&sourceless).expect("sourceless+sourced merge should succeed");
    assert!(merged.has_source());
    assert_eq!(merged.start(), 0);
    assert_eq!(merged.end(), 11);
}

// ── span intersect ────────────────────────────────────────────────────────────

#[test]
fn intersect_overlapping_ok() {
    let src = make_source();
    let a = span(0, 7, &src);
    let b = span(3, 11, &src);
    let result = a.intersect(&b).expect("overlapping intersect should succeed");
    assert_eq!(result.start(), 3);
    assert_eq!(result.end(), 7);
    assert_eq!(result.text().as_deref(), Some("lo w"));
}

#[test]
fn intersect_disjoint_returns_unknown_sentinel() {
    let src = make_source();
    let a = span(0, 5, &src);
    let b = span(6, 11, &src);
    let result = a.intersect(&b).expect("disjoint intersect should succeed (not Err)");
    // Design §2.2: disjoint → Ok(Span::unknown())
    assert!(result == Span::unknown());
}

#[test]
fn intersect_different_sources_err() {
    let src1 = SourceText::from_str("hello");
    let src2 = SourceText::from_str("world");
    let a = Span::new_with_source(0, 3, &src1);
    let b = Span::new_with_source(1, 4, &src2);
    assert!(matches!(a.intersect(&b), Err(SpanError::SourceMismatch)));
}

// ── structural equality ───────────────────────────────────────────────────────

#[test]
fn equal_trees_compare_equal() {
    let src = make_source();
    let make_node = || {
        let mut node = Identifier::new_native(span(0, 5, &src));
        node.push_child_native(
            Some(Identifier_Label::Name),
            IdentifierChild::Span(span(0, 5, &src)),
        );
        node
    };
    assert!(make_node() == make_node());
}

#[test]
fn unequal_trees_compare_unequal() {
    let src = make_source();
    let mut a = Identifier::new_native(span(0, 5, &src));
    a.push_child_native(
        Some(Identifier_Label::Name),
        IdentifierChild::Span(span(0, 5, &src)),
    );
    let mut b = Identifier::new_native(span(0, 5, &src));
    b.push_child_native(
        Some(Identifier_Label::Name),
        IdentifierChild::Span(span(0, 3, &src)), // different span end
    );
    assert!(a != b);
}

#[test]
fn different_label_makes_unequal() {
    // Unlabeled vs labeled children should differ
    let src = make_source();
    let mut a = Items::new_native(span(0, 5, &src));
    a.push_child_native(Some(Items_Label::NoWs), ItemsChild::Span(span(0, 1, &src)));
    let mut b = Items::new_native(span(0, 5, &src));
    b.push_child_native(None, ItemsChild::Span(span(0, 1, &src)));
    assert!(a != b);
}

// ── Trivia node basic test ────────────────────────────────────────────────────

#[test]
fn trivia_construction_and_traversal() {
    let src = make_source();
    let content_span = span(11, 15, &src);
    let mut trivia = Trivia::new_native(span(11, 15, &src));
    trivia.push_child_native(Some(Trivia_Label::Content), TriviaChild::Span(content_span.clone()));
    let children = trivia.children_native();
    assert_eq!(children.len(), 1);
    assert!(children[0].0 == Some(Trivia_Label::Content));
    match &children[0].1 {
        TriviaChild::Span(s) => assert_eq!(s.text().as_deref(), Some(" foo")),
    }
}
