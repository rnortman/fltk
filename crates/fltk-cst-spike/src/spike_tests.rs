/// Pure-Rust spike tests exercising CST construction, traversal, span text,
/// merge/intersect, and structural equality — no Python linked, no unsafe.
///
/// These tests must pass under `cargo test -p fltk-cst-spike` (python feature off).
///
/// Phase 1 API: suffixless names (`new`, `span`, `children`, `push_child`),
/// `Shared<T>` child ownership (Arc-based reference semantics).
///
/// Phase 2 API: label enum rename (`Identifier_Label` → `IdentifierLabel`, etc.),
/// `Debug` on all generated types, `kind()`, per-label native accessors, `CstError`.
use fltk_cst_core::{CstError, Shared, SourceText, Span, SpanError};

use crate::cst::{
    Identifier, IdentifierChild, IdentifierLabel, Items, ItemsChild, ItemsLabel, NodeKind, Trivia,
    TriviaChild, TriviaLabel,
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
    node.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(name_span.clone()));
    let children = node.children();
    assert_eq!(children.len(), 1);
    assert!(children[0].0 == Some(IdentifierLabel::Name));
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
    id_node.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(id_span.clone()));

    let mut items = Items::new(span(0, 11, &src));
    items.push_child(Some(ItemsLabel::NoWs), ItemsChild::Span(no_ws_span.clone()));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(Shared::new(id_node)));

    let children = items.children();
    assert_eq!(children.len(), 2);
    assert!(children[0].0 == Some(ItemsLabel::NoWs));
    assert!(children[1].0 == Some(ItemsLabel::Item));
}

// ── traversal ────────────────────────────────────────────────────────────────

#[test]
fn traverse_items_children_down_to_leaf_spans() {
    let src = make_source();
    let sep_span = span(5, 6, &src);
    let id_span = span(6, 11, &src);

    let mut id_node = Identifier::new(id_span.clone());
    id_node.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(id_span.clone()));

    let mut items = Items::new(span(0, 11, &src));
    items.push_child(Some(ItemsLabel::NoWs), ItemsChild::Span(sep_span.clone()));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(Shared::new(id_node)));

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
        node.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(span(0, 5, &src)));
        node
    };
    assert!(make_node() == make_node());
}

#[test]
fn unequal_trees_compare_unequal() {
    let src = make_source();
    let mut a = Identifier::new(span(0, 5, &src));
    a.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(span(0, 5, &src)));
    let mut b = Identifier::new(span(0, 5, &src));
    b.push_child(
        Some(IdentifierLabel::Name),
        IdentifierChild::Span(span(0, 3, &src)), // different span end
    );
    assert!(a != b);
}

#[test]
fn different_label_makes_unequal() {
    // Unlabeled vs labeled children should differ
    let src = make_source();
    let mut a = Items::new(span(0, 5, &src));
    a.push_child(Some(ItemsLabel::NoWs), ItemsChild::Span(span(0, 1, &src)));
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
    trivia.push_child(Some(TriviaLabel::Content), TriviaChild::Span(content_span.clone()));
    let children = trivia.children();
    assert_eq!(children.len(), 1);
    assert!(children[0].0 == Some(TriviaLabel::Content));
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
    id_node.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(span(0, 5, &src)));
    let id_shared = Shared::new(id_node);

    let mut items = Items::new(span(0, 11, &src));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(id_shared.clone()));

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
    items_a.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(id_shared.clone()));

    let mut items_b = Items::new(span(0, 5, &src));
    items_b.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(id_shared.clone()));

    match (&items_a.children()[0].1, &items_b.children()[0].1) {
        (ItemsChild::Identifier(a), ItemsChild::Identifier(b)) => {
            assert!(a.ptr_eq(b), "same Shared pushed to two nodes must be ptr_eq");
        }
        _ => panic!("expected Identifier children"),
    }
}

// ── Phase 2: Debug smoke test ─────────────────────────────────────────────────

#[test]
fn debug_node_kind_and_label_enums() {
    let kind = NodeKind::Identifier;
    let _ = format!("{kind:?}");

    let lbl = IdentifierLabel::Name;
    let _ = format!("{lbl:?}");

    let items_lbl = ItemsLabel::Item;
    let _ = format!("{items_lbl:?}");

    let trivia_lbl = TriviaLabel::Content;
    let _ = format!("{trivia_lbl:?}");
}

#[test]
fn debug_child_enums_and_node_structs() {
    let src = make_source();
    let span_child = IdentifierChild::Span(span(0, 5, &src));
    let span_child_dbg = format!("{span_child:?}");
    assert!(
        span_child_dbg.contains("Span"),
        "IdentifierChild::Span Debug must contain 'Span': {span_child_dbg}"
    );

    let items_child = ItemsChild::Identifier(Shared::new(Identifier::new(span(0, 5, &src))));
    let items_child_dbg = format!("{items_child:?}");
    assert!(
        items_child_dbg.contains("Identifier"),
        "ItemsChild::Identifier Debug must contain 'Identifier': {items_child_dbg}"
    );
    assert!(
        items_child_dbg.contains("child(ren)"),
        "ItemsChild::Identifier Debug must contain 'child(ren)' (one-level delegation through Shared works): {items_child_dbg}"
    );

    let node = Identifier::new(span(0, 5, &src));
    let node_dbg = format!("{node:?}");
    assert!(
        node_dbg.contains("span"),
        "Identifier Debug must contain 'span': {node_dbg}"
    );
    assert!(
        node_dbg.contains("<0 child(ren)>"),
        "Identifier Debug must contain '<0 child(ren)>': {node_dbg}"
    );

    let shared_node = Shared::new(Identifier::new(span(0, 5, &src)));
    let shared_dbg = format!("{shared_node:?}");
    assert!(
        shared_dbg.contains("span"),
        "Shared<Identifier> Debug must contain 'span': {shared_dbg}"
    );
    assert!(
        shared_dbg.contains("<0 child(ren)>"),
        "Shared<Identifier> Debug must contain '<0 child(ren)>': {shared_dbg}"
    );
}

#[test]
fn span_debug_format() {
    let src = make_source();
    let s = span(0, 5, &src);
    let dbg = format!("{s:?}");
    assert!(dbg.contains("start"), "Span Debug must contain 'start': {dbg}");
    assert!(dbg.contains("end"), "Span Debug must contain 'end': {dbg}");
    assert!(dbg.contains("has_source"), "Span Debug must contain 'has_source': {dbg}");
    assert!(dbg.contains("true"), "source-bearing span → has_source: true");
}

// ── Phase 2: kind() accessor ──────────────────────────────────────────────────

#[test]
fn kind_returns_correct_discriminant() {
    let src = make_source();
    assert_eq!(Identifier::new(span(0, 5, &src)).kind(), NodeKind::Identifier);
    assert_eq!(Items::new(span(0, 5, &src)).kind(), NodeKind::Items);
    assert_eq!(Trivia::new(span(0, 5, &src)).kind(), NodeKind::Trivia);
}

// ── Phase 2: per-label native read accessors ──────────────────────────────────

#[test]
fn children_lbl_span_returns_all() {
    let src = make_source();
    let mut id = Identifier::new(span(0, 5, &src));
    let s1 = span(0, 3, &src);
    let s2 = span(3, 5, &src);
    id.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(s1.clone()));
    id.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(s2.clone()));
    let got: Vec<_> = id.children_name().collect();
    assert_eq!(got.len(), 2);
    assert_eq!(*got[0], s1);
    assert_eq!(*got[1], s2);
}

#[test]
fn child_lbl_exactly_one_ok() {
    let src = make_source();
    let mut id = Identifier::new(span(0, 5, &src));
    let s = span(0, 5, &src);
    id.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(s.clone()));
    assert_eq!(*id.child_name().unwrap(), s);
}

#[test]
fn child_lbl_zero_is_child_count_error() {
    let src = make_source();
    let id = Identifier::new(span(0, 5, &src));
    match id.child_name() {
        Err(CstError::ChildCount { found: 0, .. }) => {}
        other => panic!("expected ChildCount(0), got {other:?}"),
    }
}

#[test]
fn maybe_lbl_none_is_ok_none() {
    let src = make_source();
    let id = Identifier::new(span(0, 5, &src));
    assert_eq!(id.maybe_name().unwrap(), None);
}

#[test]
fn maybe_lbl_one_is_ok_some() {
    let src = make_source();
    let mut id = Identifier::new(span(0, 5, &src));
    let s = span(0, 5, &src);
    id.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(s.clone()));
    assert_eq!(*id.maybe_name().unwrap().unwrap(), s);
}

// ── Phase 2: per-label write accessors ───────────────────────────────────────

#[test]
fn append_lbl_span_adds_labeled_child() {
    let src = make_source();
    let mut id = Identifier::new(span(0, 5, &src));
    let s = span(0, 5, &src);
    id.append_name(s.clone());
    assert_eq!(id.children().len(), 1);
    assert_eq!(id.children()[0].0, Some(IdentifierLabel::Name));
    match &id.children()[0].1 {
        IdentifierChild::Span(got) => assert_eq!(*got, s),
    }
}

#[test]
fn append_lbl_node_adds_labeled_child() {
    let src = make_source();
    let id_node = Identifier::new(span(0, 5, &src));
    let id_shared = Shared::new(id_node);
    let mut items = Items::new(span(0, 5, &src));
    items.append_item(id_shared.clone());
    assert_eq!(items.children().len(), 1);
    assert_eq!(items.children()[0].0, Some(ItemsLabel::Item));
    match &items.children()[0].1 {
        ItemsChild::Identifier(got) => assert!(got.ptr_eq(&id_shared)),
        _ => panic!("expected Identifier"),
    }
}

#[test]
fn extend_lbl_adds_multiple() {
    let src = make_source();
    let mut id = Identifier::new(span(0, 5, &src));
    let spans = [span(0, 3, &src), span(3, 5, &src)];
    id.extend_name(spans);
    assert_eq!(id.children().len(), 2);
}

// ── Phase 2: native extend_children ──────────────────────────────────────────

#[test]
fn native_extend_children_appends_arc_clones() {
    let src = make_source();
    let id_shared = Shared::new(Identifier::new(span(0, 5, &src)));
    let mut src_items = Items::new(span(0, 5, &src));
    src_items.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(id_shared.clone()));

    let mut dst_items = Items::new(span(0, 5, &src));
    dst_items.extend_children(&src_items);

    assert_eq!(dst_items.children().len(), 1);
    match &dst_items.children()[0].1 {
        ItemsChild::Identifier(got) => assert!(got.ptr_eq(&id_shared), "must be Arc clone"),
        _ => panic!("expected Identifier"),
    }
}

// ── Phase 2: node-typed label accessors (Items.item) ─────────────────────────

#[test]
fn child_item_exactly_one_ok() {
    // test-15: spike tests for child_item on the node-typed label.
    let src = make_source();
    let id_shared = Shared::new(Identifier::new(span(0, 5, &src)));
    let mut items = Items::new(span(0, 5, &src));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(id_shared.clone()));
    match items.child_item() {
        Ok(got) => assert!(got.ptr_eq(&id_shared)),
        other => panic!("expected Ok, got {other:?}"),
    }
}

#[test]
fn child_item_zero_returns_child_count_error() {
    // test-15: zero children → ChildCount error.
    let src = make_source();
    let items = Items::new(span(0, 5, &src));
    match items.child_item() {
        Err(CstError::ChildCount { found: 0, .. }) => {}
        other => panic!("expected ChildCount(0), got {other:?}"),
    }
}

#[test]
fn child_item_unexpected_child_type() {
    // test-13: push a Span variant under the node-typed `item` label; child_item returns
    // UnexpectedChildType (count is 1, type check fails).
    let src = make_source();
    let mut items = Items::new(span(0, 5, &src));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Span(span(0, 5, &src)));
    match items.child_item() {
        Err(CstError::UnexpectedChildType { label: "item" }) => {}
        other => panic!("expected UnexpectedChildType(item), got {other:?}"),
    }
}

#[test]
fn child_item_count_error_beats_type_error() {
    // test-13 / design §4.3 item 2: two children with the right label, wrong type →
    // ChildCount wins over UnexpectedChildType.
    let src = make_source();
    let mut items = Items::new(span(0, 5, &src));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Span(span(0, 3, &src)));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Span(span(3, 5, &src)));
    match items.child_item() {
        Err(CstError::ChildCount { found: 2, .. }) => {}
        other => panic!("expected ChildCount(2), got {other:?}"),
    }
}

#[test]
fn maybe_item_two_returns_child_count_error() {
    // test-16: two children → ChildCount("0 or 1") error.
    let src = make_source();
    let id1 = Shared::new(Identifier::new(span(0, 5, &src)));
    let id2 = Shared::new(Identifier::new(span(5, 10, &src)));
    let mut items = Items::new(span(0, 10, &src));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(id1));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(id2));
    match items.maybe_item() {
        Err(CstError::ChildCount { label: "item", expected: "0 or 1", found: 2 }) => {}
        other => panic!("expected ChildCount(2), got {other:?}"),
    }
}

#[test]
fn children_item_skips_off_type_variant() {
    // test-14: children_<lbl> skips off-type variants; children() provides the lossless view.
    let src = make_source();
    let id_shared = Shared::new(Identifier::new(span(0, 5, &src)));
    let mut items = Items::new(span(0, 10, &src));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Identifier(id_shared.clone()));
    items.push_child(Some(ItemsLabel::Item), ItemsChild::Span(span(5, 10, &src)));
    // children_item() skips the Span variant
    let typed: Vec<_> = items.children_item().collect();
    assert_eq!(typed.len(), 1, "off-type Span variant should be skipped");
    assert!(typed[0].ptr_eq(&id_shared));
    // children() shows both
    assert_eq!(items.children().len(), 2, "untyped view must be lossless");
}

// ── Phase 2: CstError Display ─────────────────────────────────────────────────

#[test]
fn cst_error_display() {
    let e = CstError::ChildCount {
        label: "name",
        expected: "1",
        found: 0,
    };
    assert!(e.to_string().contains("name"));

    let e2 = CstError::UnexpectedChildType { label: "item" };
    assert!(e2.to_string().contains("item"));
}
