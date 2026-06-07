/// Pure-Rust node construction/traversal/equality tests (§4 item 1 acceptance).
///
/// These tests satisfy the ADR's core promise: generated CST node structs are usable
/// in standalone pure Rust — no GIL, no live Python interpreter, no pyo3 runtime.
///
/// No `Python::with_gil`, no `pyo3::Python`, no interpreter init anywhere in this file.
#[cfg(test)]
mod tests {
    use fltk_cst_core::Span;

    use crate::cst::{
        Entry, Entry_Label, EntryChild, Identifier, Identifier_Label, IdentifierChild,
    };

    /// Build a simple Identifier node with one Span child.
    fn make_identifier(span_start: i64, span_end: i64, name_start: i64, name_end: i64) -> Identifier {
        let node_span = Span::new_sourceless(span_start, span_end);
        let mut ident = Identifier::new_native(node_span);
        let name_span = Span::new_sourceless(name_start, name_end);
        ident.push_child_native(Some(Identifier_Label::Name), IdentifierChild::Span(name_span));
        ident
    }

    /// Build an Entry node whose KEY child is an Identifier.
    fn make_entry_with_key(entry_start: i64, entry_end: i64, key: Identifier) -> Entry {
        let entry_span = Span::new_sourceless(entry_start, entry_end);
        let mut entry = Entry::new_native(entry_span);
        entry.push_child_native(Some(Entry_Label::Key), EntryChild::Identifier(Box::new(key)));
        entry
    }

    // ── Construction and span access ─────────────────────────────────────────

    #[test]
    fn construct_identifier_with_span_child() {
        let ident = make_identifier(0, 5, 0, 5);
        // span_native() is the GIL-free Rust accessor
        assert!(ident.span_native().start() == 0, "span start should be 0");
        assert!(ident.span_native().end() == 5, "span end should be 5");
    }

    #[test]
    fn construct_entry_with_identifier_child() {
        let ident = make_identifier(0, 5, 0, 5);
        let entry = make_entry_with_key(0, 10, ident);
        assert!(entry.span_native().start() == 0, "entry span start should be 0");
        assert!(entry.span_native().end() == 10, "entry span end should be 10");
    }

    // ── Traversal (parent → child) ────────────────────────────────────────────

    #[test]
    fn walk_entry_to_identifier_child_span() {
        let ident = make_identifier(0, 5, 0, 5);
        let entry = make_entry_with_key(0, 10, ident);

        let children = entry.children_native();
        assert!(children.len() == 1, "entry should have 1 child");

        let (label, child) = &children[0];
        assert!(*label == Some(Entry_Label::Key), "child label should be Key");

        match child {
            EntryChild::Identifier(id_box) => {
                assert!(id_box.span_native().start() == 0, "ident span start");
                assert!(id_box.span_native().end() == 5, "ident span end");

                let id_children = id_box.children_native();
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
        let a = make_entry_with_key(0, 10, make_identifier(0, 5, 0, 5));
        let b = make_entry_with_key(0, 10, make_identifier(0, 5, 0, 5));
        assert!(a == b, "equal subtrees should be equal");
    }

    #[test]
    fn differing_node_span_compares_unequal() {
        let a = make_entry_with_key(0, 10, make_identifier(0, 5, 0, 5));
        let b = make_entry_with_key(0, 99, make_identifier(0, 5, 0, 5)); // different entry span
        assert!(a != b, "different entry span should be unequal");
    }

    #[test]
    fn differing_child_span_compares_unequal() {
        let a = make_entry_with_key(0, 10, make_identifier(0, 5, 0, 5));
        let b = make_entry_with_key(0, 10, make_identifier(0, 7, 0, 7)); // different ident span
        assert!(a != b, "different child span should be unequal");
    }

    #[test]
    fn unknown_span_default_for_new_native() {
        let ident = Identifier::new_native(Span::unknown());
        assert!(ident.span_native().start() == -1, "unknown span start should be -1");
        assert!(ident.span_native().end() == -1, "unknown span end should be -1");
        assert!(ident.children_native().is_empty(), "new_native should have no children");
    }
}
