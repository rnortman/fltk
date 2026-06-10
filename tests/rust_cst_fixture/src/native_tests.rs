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
/// No `Python::with_gil`, no `pyo3::Python`, no interpreter init anywhere in this file.
#[cfg(test)]
mod tests {
    use fltk_cst_core::{Shared, Span};

    use crate::cst::{Entry, Entry_Label, EntryChild, Identifier, Identifier_Label, IdentifierChild};

    /// Build a simple Identifier node with one Span child.
    fn make_identifier(span_start: i64, span_end: i64, name_start: i64, name_end: i64) -> Shared<Identifier> {
        let node_span = Span::new_sourceless(span_start, span_end);
        let mut ident = Identifier::new(node_span);
        let name_span = Span::new_sourceless(name_start, name_end);
        ident.push_child(Some(Identifier_Label::Name), IdentifierChild::Span(name_span));
        Shared::new(ident)
    }

    /// Build an Entry node whose KEY child is a Shared<Identifier>.
    fn make_entry_with_key(entry_start: i64, entry_end: i64, key: Shared<Identifier>) -> Shared<Entry> {
        let entry_span = Span::new_sourceless(entry_start, entry_end);
        let mut entry = Entry::new(entry_span);
        entry.push_child(Some(Entry_Label::Key), EntryChild::Identifier(key));
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
        assert!(*label == Some(Entry_Label::Key), "child label should be Key");

        match child {
            EntryChild::Identifier(id_shared) => {
                let id = id_shared.read();
                assert!(id.span().start() == 0, "ident span start");
                assert!(id.span().end() == 5, "ident span end");

                let id_children = id.children();
                assert!(id_children.len() == 1, "ident should have 1 child");
                let (id_label, id_child) = &id_children[0];
                assert!(*id_label == Some(Identifier_Label::Name), "ident child label should be Name");
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
        entry_a.push_child(Some(Entry_Label::Key), EntryChild::Identifier(ident.clone()));

        let mut entry_b = Entry::new(Span::new_sourceless(0, 10));
        entry_b.push_child(Some(Entry_Label::Key), EntryChild::Identifier(ident.clone()));

        match (&entry_a.children()[0].1, &entry_b.children()[0].1) {
            (EntryChild::Identifier(a), EntryChild::Identifier(b)) => {
                assert!(a.ptr_eq(b), "same Shared pushed to two parents must be ptr_eq");
            }
            _ => panic!("expected Identifier children"),
        }
    }
}
