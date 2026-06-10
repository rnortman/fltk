/// Pure-Rust spike tests exercising CST construction, traversal, span text,
/// merge/intersect, and structural equality — no Python linked, no unsafe.
///
/// These tests must pass under `cargo test -p fltk-cst-spike` (python feature off).
///
/// Phase 1 API: suffixless names (`new`, `span`, `children`, `push_child`),
/// `Shared<T>` child ownership (Arc-based reference semantics).
use fltk_cst_core::{Shared, SourceText, Span, SpanError};

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
fn identifier_new_empty_children() {
    let src = make_source();
    let node = Identifier::new(span(0, 5, &src));
    assert_eq!(node.children().len(), 0);
}

#[test]
fn identifier_span_roundtrip() {
    let src = make_source();
    let sp = span(0, 5, &src);
    let node = Identifier::new(sp.clone());
    assert!(node.span() == &sp);
}

// ── labeled child append ──────────────────────────────────────────────────────

#[test]
fn identifier_push_child_labeled() {
    let src = make_source();
    let name_span = span(0, 5, &src);
    let mut node = Identifier::new(span(0, 5, &src));
    node.push_child(Some(Identifier_Label::Name), IdentifierChild::Span(name_span.clone()));
    let children = node.children();
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

    let mut id_node = Identifier::new(id_span.clone());
    id_node.push_child(Some(Identifier_Label::Name), IdentifierChild::Span(id_span.clone()));

    let mut items = Items::new(span(0, 11, &src));
    items.push_child(Some(Items_Label::NoWs), ItemsChild::Span(no_ws_span.clone()));
    items.push_child(Some(Items_Label::Item), ItemsChild::Identifier(Shared::new(id_node)));

    let children = items.children();
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

    let mut id_node = Identifier::new(id_span.clone());
    id_node.push_child(Some(Identifier_Label::Name), IdentifierChild::Span(id_span.clone()));

    let mut items = Items::new(span(0, 11, &src));
    items.push_child(Some(Items_Label::NoWs), ItemsChild::Span(sep_span.clone()));
    items.push_child(Some(Items_Label::Item), ItemsChild::Identifier(Shared::new(id_node)));

    let mut leaf_texts: Vec<String> = Vec::new();
    for (_label, child) in items.children() {
        match child {
            ItemsChild::Span(s) => {
                if let Some(t) = s.text() {
                    leaf_texts.push(t);
                }
            }
            ItemsChild::Identifier(id_shared) => {
                let id = id_shared.read();
                for (_lbl, sub) in id.children() {
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
        let mut node = Identifier::new(span(0, 5, &src));
        node.push_child(Some(Identifier_Label::Name), IdentifierChild::Span(span(0, 5, &src)));
        node
    };
    assert!(make_node() == make_node());
}

#[test]
fn unequal_trees_compare_unequal() {
    let src = make_source();
    let mut a = Identifier::new(span(0, 5, &src));
    a.push_child(Some(Identifier_Label::Name), IdentifierChild::Span(span(0, 5, &src)));
    let mut b = Identifier::new(span(0, 5, &src));
    b.push_child(
        Some(Identifier_Label::Name),
        IdentifierChild::Span(span(0, 3, &src)), // different span end
    );
    assert!(a != b);
}

#[test]
fn different_label_makes_unequal() {
    // Unlabeled vs labeled children should differ
    let src = make_source();
    let mut a = Items::new(span(0, 5, &src));
    a.push_child(Some(Items_Label::NoWs), ItemsChild::Span(span(0, 1, &src)));
    let mut b = Items::new(span(0, 5, &src));
    b.push_child(None, ItemsChild::Span(span(0, 1, &src)));
    assert!(a != b);
}

// ── Trivia node basic test ────────────────────────────────────────────────────

#[test]
fn trivia_construction_and_traversal() {
    let src = make_source();
    let content_span = span(11, 15, &src);
    let mut trivia = Trivia::new(span(11, 15, &src));
    trivia.push_child(Some(Trivia_Label::Content), TriviaChild::Span(content_span.clone()));
    let children = trivia.children();
    assert_eq!(children.len(), 1);
    assert!(children[0].0 == Some(Trivia_Label::Content));
    match &children[0].1 {
        TriviaChild::Span(s) => assert_eq!(s.text().as_deref(), Some(" foo")),
    }
}

// ── Reference semantics (Phase 1) ─────────────────────────────────────────────

/// Shared<T> clone is shallow: mutations visible through the clone.
#[test]
fn shared_clone_is_shallow() {
    let src = make_source();
    let node = Identifier::new(span(0, 5, &src));
    let shared_a = Shared::new(node);
    let shared_b = shared_a.clone();

    shared_a.write().set_span(span(10, 15, &src));
    assert!(shared_b.read().span() == &span(10, 15, &src));
    assert!(shared_a.ptr_eq(&shared_b));
}

/// Shared::eq short-circuit: x == x is true without deadlock.
#[test]
fn shared_self_eq_no_deadlock() {
    let src = make_source();
    let node = Identifier::new(span(0, 5, &src));
    let shared = Shared::new(node);
    assert!(shared == shared, "x == x must be true without deadlock");
}

/// Mutation via Shared<T>.write() is visible through a parent that holds a clone.
#[test]
fn mutation_propagates_through_parent() {
    let src = make_source();

    let mut id_node = Identifier::new(span(0, 5, &src));
    id_node.push_child(Some(Identifier_Label::Name), IdentifierChild::Span(span(0, 5, &src)));
    let id_shared = Shared::new(id_node);

    let mut items = Items::new(span(0, 11, &src));
    items.push_child(Some(Items_Label::Item), ItemsChild::Identifier(id_shared.clone()));

    // Mutate via the shared ref.
    id_shared.write().set_span(span(99, 199, &src));

    // Observe through the parent.
    match &items.children()[0].1 {
        ItemsChild::Identifier(id_in_parent) => {
            assert_eq!(id_in_parent.read().span().start(), 99);
        }
        _ => panic!("expected Identifier child"),
    }
}

/// Two Shared<T> holding children from the same source share identity (Arc clones, not copies).
#[test]
fn shared_children_share_identity_after_push_child() {
    let src = make_source();
    let id_shared = Shared::new(Identifier::new(span(0, 5, &src)));

    // Push the same Shared<Identifier> into two Items nodes.
    let mut items_a = Items::new(span(0, 5, &src));
    items_a.push_child(Some(Items_Label::Item), ItemsChild::Identifier(id_shared.clone()));

    let mut items_b = Items::new(span(0, 5, &src));
    items_b.push_child(Some(Items_Label::Item), ItemsChild::Identifier(id_shared.clone()));

    match (&items_a.children()[0].1, &items_b.children()[0].1) {
        (ItemsChild::Identifier(a), ItemsChild::Identifier(b)) => {
            assert!(a.ptr_eq(b), "same Shared pushed to two nodes must be ptr_eq");
        }
        _ => panic!("expected Identifier children"),
    }
}
