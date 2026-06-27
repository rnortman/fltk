//! The immutable [`DocAccumulator`] document builder.
//!
//! Direct port of `fltk/unparse/accumulator.py`. The accumulator builds a `Doc`
//! incrementally while preventing consecutive trivia nodes and tracking open
//! group/nest/join nesting levels. It is an immutable persistent structure: every
//! mutator returns a new accumulator and [`Clone`] is cheap (refcount bumps only).
//!
//! Like the Python version, each level holds an `Rc`-linked chain of [`DocNode`]s
//! (most-recently-added first) plus a `last_was_trivia` flag, an optional `parent`
//! accumulator, and an optional `nesting_doc` placeholder that records which kind of
//! wrapper (`Group`/`Nest`/`Join`) this level is accumulating into.

use std::rc::Rc;

use crate::doc::{concat, Doc};

/// A node in the singly-linked chain of accumulated docs (newest at the head).
///
/// Port of `accumulator.py`'s `DocNode`. The chain is torn down iteratively (see the
/// [`Drop`] impl): a long flat sibling list at one nesting level tracks the number of
/// items added there, which is attacker-controlled for unparsers over untrusted input,
/// so a recursive drop of the `Rc<DocNode>` chain would risk an uncatchable stack
/// overflow — the same happy-path hazard that forced iterative teardown for [`Doc`]
/// (design §3).
#[derive(Debug)]
struct DocNode {
    doc: Doc,
    tail: Option<Rc<DocNode>>,
}

// Iterative Drop for the linked chain: drain `tail` through a loop so dropping the head
// node cannot recurse one stack frame per chain element. Each node's own `doc` field is
// dropped by the compiler-generated drop after this runs, and `Doc` has its own
// iterative `Drop`, so neither dimension recurses.
impl Drop for DocNode {
    fn drop(&mut self) {
        let mut current = self.tail.take();
        while let Some(rc) = current {
            // Only descend into a node we uniquely own; a node still shared with another
            // accumulator stays alive and merely has its refcount decremented here.
            match Rc::try_unwrap(rc) {
                Ok(mut node) => current = node.tail.take(),
                Err(_) => break,
            }
        }
    }
}

/// Immutable document accumulator with tree structure for nesting.
///
/// Port of `accumulator.py`'s `DocAccumulator`. Construct with [`DocAccumulator::new`]
/// (equivalently [`Default`]), then thread it by value through the generated unparser:
/// every mutator consumes `&self` and returns a fresh accumulator, and cloning is a
/// handful of refcount bumps.
#[derive(Clone, Debug, Default)]
pub struct DocAccumulator {
    head: Option<Rc<DocNode>>,
    last_was_trivia: bool,
    parent: Option<Rc<DocAccumulator>>,
    nesting_doc: Option<Doc>,
}

impl DocAccumulator {
    /// Create an empty accumulator with no open nesting.
    pub fn new() -> Self {
        DocAccumulator::default()
    }

    /// Whether the most recently added content was trivia (a separator/spacing node).
    ///
    /// Read by the generated separator processing (port of the
    /// `accumulator.last_was_trivia` read at `gsm2unparser.py:1266`).
    pub fn last_was_trivia(&self) -> bool {
        self.last_was_trivia
    }

    /// Add non-trivia content, returning a new accumulator.
    pub fn add_non_trivia(&self, doc: Doc) -> DocAccumulator {
        DocAccumulator {
            head: Some(Rc::new(DocNode {
                doc,
                tail: self.head.clone(),
            })),
            last_was_trivia: false,
            parent: self.parent.clone(),
            nesting_doc: self.nesting_doc.clone(),
        }
    }

    /// Add trivia content, returning a new accumulator.
    pub fn add_trivia(&self, doc: Doc) -> DocAccumulator {
        DocAccumulator {
            head: Some(Rc::new(DocNode {
                doc,
                tail: self.head.clone(),
            })),
            last_was_trivia: true,
            parent: self.parent.clone(),
            nesting_doc: self.nesting_doc.clone(),
        }
    }

    /// Merge another (already-flattened) accumulator, preserving its trivia state.
    ///
    /// Panics if `other` still has open nesting (a non-flattened accumulator), matching
    /// the Python `RuntimeError`; this fires only on generator bugs.
    pub fn add_accumulator(&self, other: &DocAccumulator) -> DocAccumulator {
        assert!(
            other.parent.is_none() && other.nesting_doc.is_none(),
            "Attempt to merge a non-flattened accumulator: {other:?}"
        );
        let other_doc = other.doc();
        // A NIL merge contributes no content, so it must not clobber our trivia state.
        let last_was_trivia = if matches!(other_doc, Doc::Nil) {
            self.last_was_trivia
        } else {
            other.last_was_trivia
        };
        DocAccumulator {
            head: Some(Rc::new(DocNode {
                doc: other_doc,
                tail: self.head.clone(),
            })),
            last_was_trivia,
            parent: self.parent.clone(),
            nesting_doc: self.nesting_doc.clone(),
        }
    }

    /// Start a new group nesting level.
    pub fn push_group(&self) -> DocAccumulator {
        DocAccumulator {
            head: None,
            last_was_trivia: false,
            parent: Some(Rc::new(self.clone())),
            nesting_doc: Some(Doc::Group(Rc::new(Doc::Nil))), // placeholder
        }
    }

    /// Start a new nest nesting level.
    pub fn push_nest(&self, indent: u32) -> DocAccumulator {
        DocAccumulator {
            head: None,
            last_was_trivia: false,
            parent: Some(Rc::new(self.clone())),
            nesting_doc: Some(Doc::Nest {
                indent,
                content: Rc::new(Doc::Nil), // placeholder
            }),
        }
    }

    /// Start a new join nesting level.
    pub fn push_join(&self, separator: Doc) -> DocAccumulator {
        DocAccumulator {
            head: None,
            last_was_trivia: false,
            parent: Some(Rc::new(self.clone())),
            nesting_doc: Some(Doc::Join {
                docs: Vec::new(), // placeholder
                separator: Rc::new(separator),
            }),
        }
    }

    /// End the current group level, wrapping its content in a `Group`.
    ///
    /// Panics if the current level is not a group (improperly nested tree).
    pub fn pop_group(&self) -> DocAccumulator {
        assert!(
            matches!(self.nesting_doc, Some(Doc::Group(_))),
            "Improperly nested tree: Expected Group but have {:?}",
            self.nesting_doc
        );
        self.pop()
    }

    /// End the current nest level, wrapping its content in a `Nest`.
    ///
    /// Panics if the current level is not a nest (improperly nested tree).
    pub fn pop_nest(&self) -> DocAccumulator {
        assert!(
            matches!(self.nesting_doc, Some(Doc::Nest { .. })),
            "Improperly nested tree: Expected Nest but have {:?}",
            self.nesting_doc
        );
        self.pop()
    }

    /// End the current join level, converting its content into the join's docs list.
    ///
    /// Panics if the current level is not a join (improperly nested tree).
    pub fn pop_join(&self) -> DocAccumulator {
        assert!(
            matches!(self.nesting_doc, Some(Doc::Join { .. })),
            "Improperly nested tree: Expected Join but have {:?}",
            self.nesting_doc
        );
        let parent = self
            .parent
            .as_ref()
            .expect("Invariant failed: attempt to pop unnested accumulator");
        let separator = match self.nesting_doc.as_ref() {
            Some(Doc::Join { separator, .. }) => separator.clone(),
            _ => unreachable!("checked above"),
        };
        // Join wants the level's content as a list of docs: a Concat is its element
        // list, a lone NIL is the empty list, anything else is a single element.
        // `Doc` implements `Drop`, so fields can't be moved out of an owned value
        // (E0509); splice them out through `&mut` instead (the residual is dropped).
        let mut content = self.doc();
        let docs: Vec<Rc<Doc>> = match &mut content {
            Doc::Concat(inner) => std::mem::take(inner),
            Doc::Nil => Vec::new(),
            other => vec![Rc::new(std::mem::replace(other, Doc::Nil))],
        };
        let wrapped = Doc::Join { docs, separator };
        if self.last_was_trivia {
            parent.add_trivia(wrapped)
        } else {
            parent.add_non_trivia(wrapped)
        }
    }

    /// End the current group/nest level, wrapping content and returning the parent.
    fn pop(&self) -> DocAccumulator {
        let parent = self
            .parent
            .as_ref()
            .expect("Invariant failed: attempt to pop unnested accumulator");
        let content = self.doc();
        let wrapped = match self.nesting_doc.as_ref() {
            Some(Doc::Group(_)) => Doc::Group(Rc::new(content)),
            Some(Doc::Nest { indent, .. }) => Doc::Nest {
                indent: *indent,
                content: Rc::new(content),
            },
            _ => panic!("Invariant failed: attempt to pop unnested accumulator"),
        };
        if self.last_was_trivia {
            parent.add_trivia(wrapped)
        } else {
            parent.add_non_trivia(wrapped)
        }
    }

    /// Build the final `Doc` for this level (the head chain flattened into a `concat`).
    pub fn doc(&self) -> Doc {
        let mut docs: Vec<Doc> = Vec::new();
        // Walk the chain by borrow: only `node.doc` needs an owned clone (for `concat`).
        // Cloning the `Rc<DocNode>` links to traverse would bump/drop a refcount per node
        // on this hot path (`doc()` runs per `add_accumulator`/`pop`/`pop_join`).
        let mut current = &self.head;
        while let Some(node) = current {
            docs.push(node.doc.clone());
            current = &node.tail;
        }
        docs.reverse();
        concat(docs)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::doc::text;

    #[test]
    fn empty_accumulator_is_nil() {
        assert_eq!(DocAccumulator::new().doc(), Doc::Nil);
    }

    #[test]
    fn add_non_trivia_preserves_order() {
        let acc = DocAccumulator::new()
            .add_non_trivia(text("a"))
            .add_non_trivia(text("b"));
        assert_eq!(acc.doc(), concat(vec![text("a"), text("b")]));
    }

    #[test]
    fn add_trivia_sets_flag() {
        let acc = DocAccumulator::new().add_non_trivia(text("a"));
        assert!(!acc.last_was_trivia);
        let acc = acc.add_trivia(text(" "));
        assert!(acc.last_was_trivia);
    }

    #[test]
    fn last_was_trivia_accessor_reflects_state() {
        let acc = DocAccumulator::new();
        assert!(!acc.last_was_trivia());
        let acc = acc.add_non_trivia(text("a"));
        assert!(!acc.last_was_trivia());
        let acc = acc.add_trivia(text(" "));
        assert!(acc.last_was_trivia());
    }

    #[test]
    fn add_accumulator_merges_content_and_trivia_state() {
        let base = DocAccumulator::new().add_non_trivia(text("a"));
        let other = DocAccumulator::new().add_trivia(text("b"));
        let merged = base.add_accumulator(&other);
        assert!(merged.last_was_trivia);
        assert_eq!(merged.doc(), concat(vec![text("a"), text("b")]));
    }

    #[test]
    fn add_accumulator_nil_keeps_self_trivia_state() {
        let base = DocAccumulator::new().add_trivia(text("t"));
        let merged = base.add_accumulator(&DocAccumulator::new());
        // The merged-in NIL contributes nothing, so trivia state stays as base's.
        assert!(merged.last_was_trivia);
        assert_eq!(merged.doc(), text("t"));
    }

    #[test]
    #[should_panic(expected = "non-flattened")]
    fn add_accumulator_rejects_open_nesting() {
        let _ = DocAccumulator::new().add_accumulator(&DocAccumulator::new().push_group());
    }

    #[test]
    fn push_pop_group_wraps_content() {
        let acc = DocAccumulator::new()
            .push_group()
            .add_non_trivia(text("a"))
            .add_non_trivia(text("b"))
            .pop_group();
        assert_eq!(
            acc.doc(),
            Doc::Group(Rc::new(concat(vec![text("a"), text("b")])))
        );
    }

    #[test]
    fn push_pop_nest_wraps_content_with_indent() {
        let acc = DocAccumulator::new()
            .push_nest(4)
            .add_non_trivia(text("a"))
            .pop_nest();
        assert_eq!(
            acc.doc(),
            Doc::Nest {
                indent: 4,
                content: Rc::new(text("a")),
            }
        );
    }

    #[test]
    fn push_pop_join_collects_docs() {
        let acc = DocAccumulator::new()
            .push_join(text(","))
            .add_non_trivia(text("a"))
            .add_non_trivia(text("b"))
            .pop_join();
        assert_eq!(
            acc.doc(),
            Doc::Join {
                docs: vec![Rc::new(text("a")), Rc::new(text("b"))],
                separator: Rc::new(text(",")),
            }
        );
    }

    #[test]
    fn push_pop_join_single_element() {
        let acc = DocAccumulator::new()
            .push_join(text(","))
            .add_non_trivia(text("a"))
            .pop_join();
        assert_eq!(
            acc.doc(),
            Doc::Join {
                docs: vec![Rc::new(text("a"))],
                separator: Rc::new(text(",")),
            }
        );
    }

    #[test]
    fn push_pop_join_empty() {
        let acc = DocAccumulator::new().push_join(text(",")).pop_join();
        assert_eq!(
            acc.doc(),
            Doc::Join {
                docs: vec![],
                separator: Rc::new(text(",")),
            }
        );
    }

    #[test]
    fn pop_propagates_trivia_state_to_parent() {
        // A group whose last addition was trivia pops back as trivia in the parent.
        let acc = DocAccumulator::new()
            .push_group()
            .add_trivia(text(" "))
            .pop_group();
        assert!(acc.last_was_trivia);
    }

    #[test]
    #[should_panic(expected = "Expected Group")]
    fn pop_group_rejects_wrong_nesting() {
        let _ = DocAccumulator::new().push_nest(2).pop_group();
    }

    #[test]
    #[should_panic(expected = "Expected Join")]
    fn pop_join_rejects_wrong_nesting() {
        let _ = DocAccumulator::new().push_group().pop_join();
    }

    #[test]
    #[should_panic(expected = "Expected Nest")]
    fn pop_nest_rejects_wrong_nesting() {
        let _ = DocAccumulator::new().push_group().pop_nest();
    }

    #[test]
    fn deep_node_chain_drops_without_stack_overflow() {
        // A recursive drop of the Rc<DocNode> chain would overflow the stack at this
        // depth; the iterative Drop must drain it.
        let mut acc = DocAccumulator::new();
        for _ in 0..200_000 {
            acc = acc.add_non_trivia(text("x"));
        }
        drop(acc);
    }
}
