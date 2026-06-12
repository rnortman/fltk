/// Pure-Rust node construction/traversal/equality/identity tests.
///
/// These tests satisfy the ADR's core promise: generated CST node structs are usable
/// in standalone pure Rust — no GIL, no live Python interpreter, no pyo3 runtime.
///
/// Phase 1 changes validated here:
/// - Suffixless API: `new`, `span`, `children`, `push_child` (was `*_native`).
/// - `Shared<T>` child ownership (was `Box<T>`): clone is shallow, mutations propagate.
/// - Reference semantics: mutate via `child.write()`, observe through the parent.
/// - `extend_children` on data struct shares children (Arc clones).
/// - `ptr_eq`-based equality (handles `x == x` without deadlock).
///
/// Phase 2 additions:
/// - Label enum rename: `Entry_Label` → `EntryLabel`, `Identifier_Label` → `IdentifierLabel`.
/// - `Debug` on all generated types (NodeKind, label enums, child enums, node structs).
/// - `kind()` native accessor returning `NodeKind`.
/// - `child()` generic native accessor (exactly-one, CstError on count mismatch).
/// - `extend_children` native data-struct method (Arc-clone children from `other`).
/// - Per-label native read accessors: `children_<lbl>`, `child_<lbl>`, `maybe_<lbl>`.
/// - Per-label native write accessors: `append_<lbl>`, `extend_<lbl>`.
/// - `CstError` type from fltk-cst-core (ChildCount / UnexpectedChildType).
/// - Union-label accessors: `value_node` rule with `operand:identifier | operand:literal`
///   exercises all three union branches in generated code.
///
/// No `Python::with_gil`, no `pyo3::Python`, no interpreter init anywhere in this file.
#[cfg(test)]
mod tests {
    use fltk_cst_core::{CstError, Shared, Span};

    use crate::cst::{
        Entry, EntryChild, EntryLabel, Identifier, IdentifierChild, IdentifierLabel, Literal,
        NodeKind, ValueNode, ValueNodeChild,
    };

    /// Build a simple Identifier node with one Span child.
    fn make_identifier(span_start: i64, span_end: i64, name_start: i64, name_end: i64) -> Shared<Identifier> {
        let node_span = Span::new_sourceless(span_start, span_end);
        let mut ident = Identifier::new(node_span);
        let name_span = Span::new_sourceless(name_start, name_end);
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(name_span));
        Shared::new(ident)
    }

    /// Build an Entry node whose KEY child is a Shared<Identifier>.
    fn make_entry_with_key(entry_start: i64, entry_end: i64, key: Shared<Identifier>) -> Shared<Entry> {
        let entry_span = Span::new_sourceless(entry_start, entry_end);
        let mut entry = Entry::new(entry_span);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(key));
        Shared::new(entry)
    }

    // ── Construction and span access ─────────────────────────────────────────

    #[test]
    fn construct_identifier_with_span_child() {
        let ident_shared = make_identifier(0, 5, 0, 5);
        let ident = ident_shared.read();
        // `span()` is the GIL-free Rust accessor (suffixless)
        assert!(ident.span().start() == 0, "span start should be 0");
        assert!(ident.span().end() == 5, "span end should be 5");
    }

    #[test]
    fn construct_entry_with_identifier_child() {
        let ident = make_identifier(0, 5, 0, 5);
        let entry_shared = make_entry_with_key(0, 10, ident);
        let entry = entry_shared.read();
        assert!(entry.span().start() == 0, "entry span start should be 0");
        assert!(entry.span().end() == 10, "entry span end should be 10");
    }

    // ── Traversal (parent → child) ────────────────────────────────────────────

    #[test]
    fn walk_entry_to_identifier_child_span() {
        let ident = make_identifier(0, 5, 0, 5);
        let entry_shared = make_entry_with_key(0, 10, ident);
        let entry = entry_shared.read();

        let children = entry.children();
        assert!(children.len() == 1, "entry should have 1 child");

        let (label, child) = &children[0];
        assert!(*label == Some(EntryLabel::Key), "child label should be Key");

        match child {
            EntryChild::Identifier(id_shared) => {
                let id = id_shared.read();
                assert!(id.span().start() == 0, "ident span start");
                assert!(id.span().end() == 5, "ident span end");

                let id_children = id.children();
                assert!(id_children.len() == 1, "ident should have 1 child");
                let (id_label, id_child) = &id_children[0];
                assert!(*id_label == Some(IdentifierLabel::Name), "ident child label should be Name");
                match id_child {
                    IdentifierChild::Span(s) => {
                        assert!(s.start() == 0, "name span start");
                        assert!(s.end() == 5, "name span end");
                    }
                }
            }
            _ => panic!("expected Identifier child"),
        }
    }

    // ── Equality ──────────────────────────────────────────────────────────────

    #[test]
    fn equal_subtrees_compare_equal() {
        let a_ident = make_identifier(0, 5, 0, 5);
        let b_ident = make_identifier(0, 5, 0, 5);
        let a = make_entry_with_key(0, 10, a_ident);
        let b = make_entry_with_key(0, 10, b_ident);
        assert!(a == b, "equal subtrees should be equal");
    }

    #[test]
    fn differing_node_span_compares_unequal() {
        let a_ident = make_identifier(0, 5, 0, 5);
        let b_ident = make_identifier(0, 5, 0, 5);
        let a = make_entry_with_key(0, 10, a_ident);
        let b = make_entry_with_key(0, 99, b_ident); // different entry span
        assert!(a != b, "different entry span should be unequal");
    }

    #[test]
    fn differing_child_span_compares_unequal() {
        let a_ident = make_identifier(0, 5, 0, 5);
        let b_ident = make_identifier(0, 7, 0, 7); // different ident span
        let a = make_entry_with_key(0, 10, a_ident);
        let b = make_entry_with_key(0, 10, b_ident);
        assert!(a != b, "different child span should be unequal");
    }

    #[test]
    fn unknown_span_default_for_new() {
        let ident = Identifier::new(Span::unknown());
        assert!(ident.span().start() == -1, "unknown span start should be -1");
        assert!(ident.span().end() == -1, "unknown span end should be -1");
        assert!(ident.children().is_empty(), "new should have no children");
    }

    // ── Reference semantics (Phase 1) ─────────────────────────────────────────

    /// Mutate a child via write() and observe through the parent's child reference.
    #[test]
    fn mutation_propagates_through_shared_child() {
        let ident_shared = make_identifier(0, 5, 0, 5);
        let entry_shared = make_entry_with_key(0, 10, ident_shared.clone());

        // Mutate the identifier's span via the native setter.
        ident_shared.write().set_span(Span::new_sourceless(99, 199));

        // Observe through the parent's children slice.
        let entry = entry_shared.read();
        match &entry.children()[0].1 {
            EntryChild::Identifier(id_shared) => {
                assert_eq!(id_shared.read().span().start(), 99, "mutation should be visible through parent");
            }
            _ => panic!("expected Identifier child"),
        }
    }

    /// Clone of a Shared<T> is shallow: same underlying data.
    #[test]
    fn clone_is_shallow_mutation_visible_through_clone() {
        let ident_shared = make_identifier(0, 5, 0, 5);
        let ident_clone = ident_shared.clone();

        ident_shared.write().set_span(Span::new_sourceless(42, 84));

        assert_eq!(
            ident_clone.read().span().start(),
            42,
            "clone should share the same data"
        );
        assert!(ident_shared.ptr_eq(&ident_clone), "clone should be ptr_eq");
    }

    /// ptr_eq self-compare returns true without deadlock (Shared::eq short-circuit).
    #[test]
    fn shared_self_eq_no_deadlock() {
        let ident_shared = make_identifier(0, 5, 0, 5);
        assert!(ident_shared == ident_shared, "x == x must be true without deadlock");
    }

    /// Two distinct Shared pointing to equal-valued trees compare equal (deep eq).
    #[test]
    fn shared_deep_eq_distinct_allocations() {
        let a = make_identifier(0, 5, 0, 5);
        let b = make_identifier(0, 5, 0, 5);
        assert!(!a.ptr_eq(&b), "distinct allocations");
        assert!(a == b, "same value → equal");
    }

    /// Same Shared<T> pushed to two parents is ptr_eq on both sides.
    #[test]
    fn shared_child_in_two_parents_is_ptr_eq() {
        let ident = make_identifier(0, 5, 0, 5);

        let mut entry_a = Entry::new(Span::new_sourceless(0, 10));
        entry_a.push_child(Some(EntryLabel::Key), EntryChild::Identifier(ident.clone()));

        let mut entry_b = Entry::new(Span::new_sourceless(0, 10));
        entry_b.push_child(Some(EntryLabel::Key), EntryChild::Identifier(ident.clone()));

        match (&entry_a.children()[0].1, &entry_b.children()[0].1) {
            (EntryChild::Identifier(a), EntryChild::Identifier(b)) => {
                assert!(a.ptr_eq(b), "same Shared pushed to two parents must be ptr_eq");
            }
            _ => panic!("expected Identifier children"),
        }
    }

    // ── Phase 2: Debug (item 1) ───────────────────────────────────────────────

    /// Smoke test: all generated types implement Debug (compile-time check + runtime output).
    #[test]
    fn debug_smoke_all_generated_types() {
        // NodeKind
        let kind = NodeKind::Identifier;
        let _ = format!("{kind:?}");

        // Label enums
        let lbl = IdentifierLabel::Name;
        let _ = format!("{lbl:?}");

        let entry_lbl = EntryLabel::Key;
        let _ = format!("{entry_lbl:?}");

        // Child enums
        let child_span = IdentifierChild::Span(Span::new_sourceless(0, 5));
        let _ = format!("{child_span:?}");

        let child_ident = EntryChild::Identifier(Shared::new(Identifier::new(Span::new_sourceless(0, 5))));
        let _ = format!("{child_ident:?}");

        // Node structs (via Shared<T>'s Debug delegate)
        let ident_shared = make_identifier(0, 5, 0, 5);
        let _ = format!("{ident_shared:?}");

        // Span Debug (manual impl in cst-core)
        let s = Span::new_sourceless(3, 7);
        let dbg = format!("{s:?}");
        assert!(dbg.contains("start"), "Span Debug should contain 'start': {dbg}");
        assert!(dbg.contains("end"), "Span Debug should contain 'end': {dbg}");
        assert!(dbg.contains("has_source"), "Span Debug should contain 'has_source': {dbg}");
    }

    // ── Phase 2: kind() native accessor (item 3) ──────────────────────────────

    #[test]
    fn kind_returns_correct_node_kind() {
        let ident = Identifier::new(Span::unknown());
        assert_eq!(ident.kind(), NodeKind::Identifier);

        let entry = Entry::new(Span::unknown());
        assert_eq!(entry.kind(), NodeKind::Entry);
    }

    // ── Phase 2: generic child() accessor (item 3) ────────────────────────────

    #[test]
    fn generic_child_exactly_one_succeeds() {
        let ident_shared = make_identifier(0, 5, 0, 5);
        let entry_shared = make_entry_with_key(0, 10, ident_shared);
        let entry = entry_shared.read();
        let result = entry.child();
        assert!(result.is_ok(), "exactly one child should succeed");
        let (label, _child) = result.unwrap();
        assert_eq!(*label, Some(EntryLabel::Key));
    }

    #[test]
    fn generic_child_zero_returns_count_error() {
        let entry = Entry::new(Span::unknown());
        match entry.child() {
            Err(CstError::ChildCount { found: 0, .. }) => {}
            other => panic!("expected ChildCount(0), got {other:?}"),
        }
    }

    #[test]
    fn generic_child_two_returns_count_error() {
        let mut entry = Entry::new(Span::unknown());
        let k1 = make_identifier(0, 3, 0, 3);
        let k2 = make_identifier(3, 6, 3, 6);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k1));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k2));
        match entry.child() {
            Err(CstError::ChildCount { found: 2, .. }) => {}
            other => panic!("expected ChildCount(2), got {other:?}"),
        }
    }

    // ── Phase 2: native extend_children (item 3) ─────────────────────────────

    #[test]
    fn native_extend_children_shares_arcs() {
        let ident_shared = make_identifier(0, 5, 0, 5);
        let mut source_entry = Entry::new(Span::new_sourceless(0, 10));
        source_entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(ident_shared.clone()));

        let mut dest_entry = Entry::new(Span::new_sourceless(0, 10));
        dest_entry.extend_children(&source_entry);

        assert_eq!(dest_entry.children().len(), 1, "dest should have 1 child after extend");
        match &dest_entry.children()[0].1 {
            EntryChild::Identifier(id_in_dest) => {
                // Should be ptr_eq with the original — Arc clone, not deep copy.
                assert!(id_in_dest.ptr_eq(&ident_shared), "extend_children must share the Arc");
            }
            _ => panic!("expected Identifier child"),
        }
    }

    #[test]
    fn native_extend_children_preserves_labels() {
        let ident = make_identifier(0, 5, 0, 5);
        let mut src = Entry::new(Span::unknown());
        src.push_child(Some(EntryLabel::Key), EntryChild::Identifier(ident));

        let mut dst = Entry::new(Span::unknown());
        dst.extend_children(&src);

        assert_eq!(dst.children()[0].0, Some(EntryLabel::Key), "label must be preserved");
    }

    // ── Phase 2: per-label native read accessors (item 2) ────────────────────

    #[test]
    fn children_lbl_span_returns_all_matching() {
        let mut ident = Identifier::new(Span::unknown());
        let s1 = Span::new_sourceless(0, 3);
        let s2 = Span::new_sourceless(3, 6);
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(s1.clone()));
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(s2.clone()));
        let results: Vec<_> = ident.children_name().collect();
        assert_eq!(results.len(), 2);
        assert_eq!(*results[0], s1);
        assert_eq!(*results[1], s2);
    }

    #[test]
    fn children_lbl_node_returns_matching_shared() {
        let ident1 = make_identifier(0, 5, 0, 5);
        let ident2 = make_identifier(5, 10, 5, 10);
        let mut entry = Entry::new(Span::unknown());
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(ident1.clone()));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(ident2.clone()));
        let results: Vec<_> = entry.children_key().collect();
        assert_eq!(results.len(), 2);
        assert!(results[0].ptr_eq(&ident1));
        assert!(results[1].ptr_eq(&ident2));
    }

    #[test]
    fn child_lbl_exactly_one_span_ok() {
        let mut ident = Identifier::new(Span::unknown());
        let s = Span::new_sourceless(0, 5);
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(s.clone()));
        let got = ident.child_name().unwrap();
        assert_eq!(*got, s);
    }

    #[test]
    fn child_lbl_zero_returns_child_count_error() {
        let ident = Identifier::new(Span::unknown());
        match ident.child_name() {
            Err(CstError::ChildCount { label: "name", expected: "1", found: 0 }) => {}
            other => panic!("expected ChildCount(0), got {other:?}"),
        }
    }

    #[test]
    fn child_lbl_two_returns_child_count_error() {
        let mut ident = Identifier::new(Span::unknown());
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(Span::new_sourceless(0, 3)));
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(Span::new_sourceless(3, 6)));
        match ident.child_name() {
            Err(CstError::ChildCount { label: "name", expected: "1", found: 2 }) => {}
            other => panic!("expected ChildCount(2), got {other:?}"),
        }
    }

    #[test]
    fn child_lbl_count_error_takes_priority_over_type_error() {
        // Two children with the right label but potentially wrong types → ChildCount wins.
        let mut entry = Entry::new(Span::unknown());
        let ident1 = make_identifier(0, 5, 0, 5);
        let ident2 = make_identifier(5, 10, 5, 10);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(ident1));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(ident2));
        // child_key expects exactly one; two → ChildCount, not UnexpectedChildType
        match entry.child_key() {
            Err(CstError::ChildCount { found: 2, .. }) => {}
            other => panic!("expected ChildCount(2), got {other:?}"),
        }
    }

    #[test]
    fn maybe_lbl_zero_returns_none() {
        let ident = Identifier::new(Span::unknown());
        assert_eq!(ident.maybe_name().unwrap(), None);
    }

    #[test]
    fn maybe_lbl_one_returns_some() {
        let mut ident = Identifier::new(Span::unknown());
        let s = Span::new_sourceless(0, 5);
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(s.clone()));
        let got = ident.maybe_name().unwrap().unwrap();
        assert_eq!(*got, s);
    }

    #[test]
    fn maybe_lbl_two_returns_child_count_error() {
        let mut ident = Identifier::new(Span::unknown());
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(Span::new_sourceless(0, 3)));
        ident.push_child(Some(IdentifierLabel::Name), IdentifierChild::Span(Span::new_sourceless(3, 6)));
        match ident.maybe_name() {
            Err(CstError::ChildCount { label: "name", expected: "0 or 1", found: 2 }) => {}
            other => panic!("expected ChildCount(2), got {other:?}"),
        }
    }

    // ── Phase 2: per-label write accessors (item 2) ──────────────────────────

    #[test]
    fn append_lbl_span_adds_typed_child() {
        let mut ident = Identifier::new(Span::unknown());
        let s = Span::new_sourceless(0, 5);
        ident.append_name(s.clone());
        let children = ident.children();
        assert_eq!(children.len(), 1);
        assert_eq!(children[0].0, Some(IdentifierLabel::Name));
        match &children[0].1 {
            IdentifierChild::Span(got) => assert_eq!(*got, s),
        }
    }

    #[test]
    fn append_lbl_node_adds_typed_child() {
        let ident_shared = make_identifier(0, 5, 0, 5);
        let mut entry = Entry::new(Span::unknown());
        entry.append_key(ident_shared.clone());
        assert_eq!(entry.children().len(), 1);
        assert_eq!(entry.children()[0].0, Some(EntryLabel::Key));
        match &entry.children()[0].1 {
            EntryChild::Identifier(got) => assert!(got.ptr_eq(&ident_shared)),
            _ => panic!("expected Identifier"),
        }
    }

    #[test]
    fn append_lbl_accepts_bare_value_via_into() {
        // append_<lbl>(impl Into<Shared<T>>) — pass a raw value, not a Shared.
        let ident = Identifier::new(Span::new_sourceless(0, 5));
        let mut entry = Entry::new(Span::unknown());
        entry.append_key(ident); // Identifier → Shared<Identifier> via From<T>
        assert_eq!(entry.children().len(), 1);
    }

    #[test]
    fn extend_lbl_adds_multiple_children() {
        let mut ident = Identifier::new(Span::unknown());
        let spans = [Span::new_sourceless(0, 3), Span::new_sourceless(3, 6)];
        ident.extend_name(spans);
        assert_eq!(ident.children().len(), 2);
    }

    // ── Phase 2: CstError Display (item 4) ───────────────────────────────────

    #[test]
    fn cst_error_child_count_display() {
        let e = CstError::ChildCount {
            label: "name",
            expected: "1",
            found: 0,
        };
        let s = e.to_string();
        assert!(s.contains("name"), "Display should mention label: {s}");
        assert!(s.contains("0"), "Display should mention found count: {s}");
    }

    #[test]
    fn cst_error_unexpected_child_type_display() {
        let e = CstError::UnexpectedChildType { label: "key" };
        let s = e.to_string();
        assert!(s.contains("key"), "Display should mention label: {s}");
    }

    #[test]
    fn child_lbl_unexpected_child_type_returned_by_accessor() {
        // test-13: push an off-type variant (Literal) under a single-typed label (Key expects
        // Identifier); child_key() must return UnexpectedChildType when count is exactly 1.
        let lit = Shared::new(Literal::new(Span::unknown()));
        let mut entry = Entry::new(Span::unknown());
        entry.push_child(Some(EntryLabel::Key), EntryChild::Literal(lit));
        match entry.child_key() {
            Err(CstError::UnexpectedChildType { label: "key" }) => {}
            other => panic!("expected UnexpectedChildType(key), got {other:?}"),
        }
    }

    #[test]
    fn child_lbl_count_error_beats_type_error_with_wrong_types() {
        // test-13 / design §4.3 item 2: two children with wrong type → ChildCount wins.
        let lit1 = Shared::new(Literal::new(Span::unknown()));
        let lit2 = Shared::new(Literal::new(Span::new_sourceless(1, 2)));
        let mut entry = Entry::new(Span::unknown());
        entry.push_child(Some(EntryLabel::Key), EntryChild::Literal(lit1));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Literal(lit2));
        match entry.child_key() {
            Err(CstError::ChildCount { found: 2, .. }) => {}
            other => panic!("expected ChildCount(2), got {other:?}"),
        }
    }

    #[test]
    fn children_key_skips_off_type_variant() {
        // test-14: children_<lbl> skips off-type variants; children() is the lossless view.
        let ident_shared = make_identifier(0, 5, 0, 5);
        let lit = Shared::new(Literal::new(Span::unknown()));
        let mut entry = Entry::new(Span::unknown());
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(ident_shared.clone()));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Literal(lit));
        // children_key() skips the Literal variant
        let typed: Vec<_> = entry.children_key().collect();
        assert_eq!(typed.len(), 1, "off-type Literal child should be skipped");
        assert!(typed[0].ptr_eq(&ident_shared));
        // children() shows both
        assert_eq!(entry.children().len(), 2, "untyped view must be lossless");
    }

    // ── Phase 2: Span Debug (item 1) ─────────────────────────────────────────

    #[test]
    fn span_debug_format_contains_fields() {
        let s = Span::new_sourceless(3, 7);
        let dbg = format!("{s:?}");
        assert!(dbg.contains("3"), "should contain start value");
        assert!(dbg.contains("7"), "should contain end value");
        assert!(dbg.contains("false"), "sourceless span → has_source: false");
    }

    #[test]
    fn span_debug_with_source_has_source_true() {
        use fltk_cst_core::SourceText;
        let src = SourceText::from_str("hello");
        let s = Span::new_with_source(0, 5, &src);
        let dbg = format!("{s:?}");
        assert!(dbg.contains("true"), "source-bearing span → has_source: true");
    }

    // ── Union-label accessor tests (quality-2 fix) ──────────────────────────
    //
    // `value_node := operand:identifier | operand:literal` is a union-labeled rule:
    // `operand` maps to {Identifier, Literal}.  The generated accessors return/accept
    // the whole `ValueNodeChild` enum rather than a typed `Shared<T>`.

    fn make_value_node_with_identifier() -> ValueNode {
        let mut n = ValueNode::new(Span::unknown());
        let ident = make_identifier(0, 3, 0, 3);
        n.append_operand(ValueNodeChild::Identifier(ident));
        n
    }

    fn make_value_node_with_literal() -> ValueNode {
        let mut n = ValueNode::new(Span::unknown());
        let lit = Shared::new(Literal::new(Span::new_sourceless(4, 7)));
        n.append_operand(ValueNodeChild::Literal(lit));
        n
    }

    #[test]
    fn child_union_lbl_returns_identifier_variant() {
        // child_operand() on a node with one Identifier child returns Ok(&ValueNodeChild::Identifier).
        let n = make_value_node_with_identifier();
        let result = n.child_operand();
        assert!(result.is_ok(), "expected Ok, got {result:?}");
        assert!(
            matches!(result.unwrap(), ValueNodeChild::Identifier(_)),
            "expected Identifier variant"
        );
    }

    #[test]
    fn child_union_lbl_returns_literal_variant() {
        // child_operand() on a node with one Literal child returns Ok(&ValueNodeChild::Literal).
        let n = make_value_node_with_literal();
        let result = n.child_operand();
        assert!(result.is_ok(), "expected Ok, got {result:?}");
        assert!(
            matches!(result.unwrap(), ValueNodeChild::Literal(_)),
            "expected Literal variant"
        );
    }

    #[test]
    fn child_union_lbl_zero_returns_child_count_error() {
        // child_operand() with no operand child → ChildCount(found=0).
        let n = ValueNode::new(Span::unknown());
        match n.child_operand() {
            Err(CstError::ChildCount { label: "operand", found: 0, .. }) => {}
            other => panic!("expected ChildCount(0), got {other:?}"),
        }
    }

    #[test]
    fn child_union_lbl_two_returns_child_count_error() {
        // child_operand() with two operand children → ChildCount(found=2).
        let mut n = ValueNode::new(Span::unknown());
        let ident1 = make_identifier(0, 1, 0, 1);
        let ident2 = make_identifier(2, 3, 2, 3);
        n.append_operand(ValueNodeChild::Identifier(ident1));
        n.append_operand(ValueNodeChild::Identifier(ident2));
        match n.child_operand() {
            Err(CstError::ChildCount { label: "operand", found: 2, .. }) => {}
            other => panic!("expected ChildCount(2), got {other:?}"),
        }
    }

    #[test]
    fn maybe_union_lbl_none_when_no_operand() {
        // maybe_operand() with no operand child → Ok(None).
        let n = ValueNode::new(Span::unknown());
        assert_eq!(n.maybe_operand().unwrap(), None);
    }

    #[test]
    fn maybe_union_lbl_some_with_literal() {
        // maybe_operand() with one Literal child → Ok(Some(&ValueNodeChild::Literal)).
        let n = make_value_node_with_literal();
        let result = n.maybe_operand();
        assert!(result.is_ok(), "expected Ok, got {result:?}");
        assert!(
            matches!(result.unwrap(), Some(ValueNodeChild::Literal(_))),
            "expected Some(Literal variant)"
        );
    }

    #[test]
    fn maybe_union_lbl_two_returns_child_count_error() {
        // maybe_operand() with two operand children → ChildCount("0 or 1").
        let mut n = ValueNode::new(Span::unknown());
        let ident1 = make_identifier(0, 1, 0, 1);
        let lit = Shared::new(Literal::new(Span::new_sourceless(2, 3)));
        n.append_operand(ValueNodeChild::Identifier(ident1));
        n.append_operand(ValueNodeChild::Literal(lit));
        match n.maybe_operand() {
            Err(CstError::ChildCount { label: "operand", expected: "0 or 1", found: 2 }) => {}
            other => panic!("expected ChildCount(2, '0 or 1'), got {other:?}"),
        }
    }

    #[test]
    fn children_union_lbl_returns_all_variants() {
        // children_operand() yields both Identifier and Literal children; order is preserved.
        let mut n = ValueNode::new(Span::unknown());
        let ident = make_identifier(0, 1, 0, 1);
        let lit = Shared::new(Literal::new(Span::new_sourceless(2, 3)));
        n.append_operand(ValueNodeChild::Identifier(ident));
        n.append_operand(ValueNodeChild::Literal(lit));
        let children: Vec<_> = n.children_operand().collect();
        assert_eq!(children.len(), 2, "both operand children must appear");
        assert!(matches!(children[0], ValueNodeChild::Identifier(_)));
        assert!(matches!(children[1], ValueNodeChild::Literal(_)));
    }

    #[test]
    fn extend_union_lbl_appends_all_children() {
        // extend_operand() bulk-appends; total operand count equals items supplied.
        let mut n = ValueNode::new(Span::unknown());
        let ident1 = make_identifier(0, 1, 0, 1);
        let ident2 = make_identifier(2, 3, 2, 3);
        n.extend_operand(vec![
            ValueNodeChild::Identifier(ident1),
            ValueNodeChild::Identifier(ident2),
        ]);
        assert_eq!(n.children_operand().count(), 2);
        assert_eq!(n.children().len(), 2);
    }

    // ── §4.4 Native mutators: insert_child / remove_child / replace_child / clear_children ──

    #[test]
    fn insert_child_at_head() {
        let mut entry = Entry::new(Span::unknown());
        let k1 = make_identifier(0, 3, 0, 3);
        let k2 = make_identifier(3, 6, 3, 6);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k1));
        // Insert k2 at index 0 — should become the first child.
        entry.insert_child(0, Some(EntryLabel::Key), EntryChild::Identifier(k2.clone()));
        assert_eq!(entry.children().len(), 2);
        match &entry.children()[0].1 {
            EntryChild::Identifier(got) => assert!(got.ptr_eq(&k2), "k2 should be first child"),
            _ => panic!("expected Identifier"),
        }
    }

    #[test]
    fn insert_child_at_tail() {
        let mut entry = Entry::new(Span::unknown());
        let k1 = make_identifier(0, 3, 0, 3);
        let k2 = make_identifier(3, 6, 3, 6);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k1));
        // Insert at index == len → append.
        entry.insert_child(1, Some(EntryLabel::Key), EntryChild::Identifier(k2.clone()));
        assert_eq!(entry.children().len(), 2);
        match &entry.children()[1].1 {
            EntryChild::Identifier(got) => assert!(got.ptr_eq(&k2), "k2 should be last child"),
            _ => panic!("expected Identifier"),
        }
    }

    #[test]
    fn insert_child_at_middle() {
        let mut entry = Entry::new(Span::unknown());
        let k1 = make_identifier(0, 1, 0, 1);
        let k2 = make_identifier(1, 2, 1, 2);
        let kmid = make_identifier(10, 11, 10, 11);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k1));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k2));
        // Insert at index 1 — should go between k1 and k2.
        entry.insert_child(1, Some(EntryLabel::Key), EntryChild::Identifier(kmid.clone()));
        assert_eq!(entry.children().len(), 3);
        match &entry.children()[1].1 {
            EntryChild::Identifier(got) => assert!(got.ptr_eq(&kmid), "kmid should be at index 1"),
            _ => panic!("expected Identifier"),
        }
    }

    #[test]
    fn insert_child_preserves_label() {
        let mut ident = Identifier::new(Span::unknown());
        let s = Span::new_sourceless(0, 5);
        ident.insert_child(0, Some(IdentifierLabel::Name), IdentifierChild::Span(s.clone()));
        assert_eq!(ident.children()[0].0, Some(IdentifierLabel::Name));
    }

    #[test]
    fn insert_child_none_label() {
        let mut ident = Identifier::new(Span::unknown());
        let s = Span::new_sourceless(0, 5);
        ident.insert_child(0, None, IdentifierChild::Span(s));
        assert_eq!(ident.children()[0].0, None);
    }

    #[test]
    #[should_panic]
    fn insert_child_out_of_range_panics() {
        let mut entry = Entry::new(Span::unknown());
        let k = make_identifier(0, 3, 0, 3);
        // index 5 on an empty node → Vec::insert panics.
        entry.insert_child(5, Some(EntryLabel::Key), EntryChild::Identifier(k));
    }

    #[test]
    fn remove_child_returns_correct_entry() {
        let mut entry = Entry::new(Span::unknown());
        let k1 = make_identifier(0, 3, 0, 3);
        let k2 = make_identifier(3, 6, 3, 6);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k1));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k2.clone()));
        // Remove index 1 (k2).
        let (lbl, child) = entry.remove_child(1);
        assert_eq!(lbl, Some(EntryLabel::Key));
        match child {
            EntryChild::Identifier(got) => assert!(got.ptr_eq(&k2)),
            _ => panic!("expected Identifier"),
        }
        assert_eq!(entry.children().len(), 1);
    }

    #[test]
    fn remove_child_head() {
        let mut entry = Entry::new(Span::unknown());
        let k1 = make_identifier(0, 3, 0, 3);
        let k2 = make_identifier(3, 6, 3, 6);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k1.clone()));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k2));
        let (_, child) = entry.remove_child(0);
        match child {
            EntryChild::Identifier(got) => assert!(got.ptr_eq(&k1)),
            _ => panic!("expected Identifier"),
        }
        assert_eq!(entry.children().len(), 1);
    }

    #[test]
    #[should_panic]
    fn remove_child_out_of_range_panics() {
        let mut entry = Entry::new(Span::unknown());
        entry.remove_child(0); // empty → panics
    }

    #[test]
    fn replace_child_updates_entry() {
        let mut entry = Entry::new(Span::unknown());
        let k_old = make_identifier(0, 3, 0, 3);
        let k_new = make_identifier(5, 8, 5, 8);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k_old.clone()));
        let (old_lbl, old_child) = entry.replace_child(0, Some(EntryLabel::Key), EntryChild::Identifier(k_new.clone()));
        // Old entry returned.
        assert_eq!(old_lbl, Some(EntryLabel::Key));
        match old_child {
            EntryChild::Identifier(got) => assert!(got.ptr_eq(&k_old)),
            _ => panic!("expected old Identifier"),
        }
        // New child is now in place.
        assert_eq!(entry.children().len(), 1);
        match &entry.children()[0].1 {
            EntryChild::Identifier(got) => assert!(got.ptr_eq(&k_new)),
            _ => panic!("expected new Identifier"),
        }
    }

    #[test]
    fn replace_child_preserves_length() {
        let mut entry = Entry::new(Span::unknown());
        let k1 = make_identifier(0, 3, 0, 3);
        let k2 = make_identifier(3, 6, 3, 6);
        let k3 = make_identifier(6, 9, 6, 9);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k1));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k2));
        entry.replace_child(0, Some(EntryLabel::Key), EntryChild::Identifier(k3));
        assert_eq!(entry.children().len(), 2, "replace must preserve length");
    }

    #[test]
    fn replace_child_label_none_clears_label() {
        let mut entry = Entry::new(Span::unknown());
        let k = make_identifier(0, 3, 0, 3);
        let k2 = make_identifier(3, 6, 3, 6);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k));
        entry.replace_child(0, None, EntryChild::Identifier(k2));
        assert_eq!(entry.children()[0].0, None, "label=None should clear the label");
    }

    #[test]
    #[should_panic]
    fn replace_child_out_of_range_panics() {
        let mut entry = Entry::new(Span::unknown());
        let k = make_identifier(0, 3, 0, 3);
        entry.replace_child(0, Some(EntryLabel::Key), EntryChild::Identifier(k)); // empty → panics
    }

    #[test]
    fn clear_children_empties_node() {
        let mut entry = Entry::new(Span::unknown());
        let k1 = make_identifier(0, 3, 0, 3);
        let k2 = make_identifier(3, 6, 3, 6);
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k1));
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k2));
        entry.clear_children();
        assert!(entry.children().is_empty(), "clear_children must empty the node");
    }

    #[test]
    fn clear_children_on_empty_is_no_op() {
        let mut entry = Entry::new(Span::unknown());
        entry.clear_children(); // should not panic
        assert!(entry.children().is_empty());
    }

    #[test]
    fn clear_children_released_child_still_accessible_via_shared() {
        let k1 = make_identifier(0, 3, 0, 3);
        let mut entry = Entry::new(Span::unknown());
        entry.push_child(Some(EntryLabel::Key), EntryChild::Identifier(k1.clone()));
        entry.clear_children();
        // k1 Arc clone still alive; node still readable.
        assert_eq!(k1.read().span().start(), 0);
    }
}
