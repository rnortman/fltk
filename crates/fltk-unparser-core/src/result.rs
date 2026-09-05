//! The [`UnparseResult`] returned by each generated per-rule unparse method.
//!
//! Direct port of `fltk/unparse/pyrt.py`'s `UnparseResult`. A generated
//! `unparse_{rule}` method walks a CST node, accumulating formatting output into a
//! [`DocAccumulator`] and advancing a positional index over the node's children; on
//! success it returns the accumulator plus the new position so the caller can resume
//! its own walk from where this one stopped.

use crate::doc::Doc;
use crate::DocAccumulator;

/// Result from unparsing a CST node: the accumulated `Doc` plus the new position.
///
/// Port of `pyrt.py`'s `UnparseResult`. `accumulator` holds the [`Doc`] result and
/// trivia state for the consumed children; `new_pos` is the index after the children
/// this unparse consumed from the node's child list.
///
/// `cursor` is the *source* counterpart of `new_pos`: the codepoint offset, in the
/// enclosing rule node's source, that the consumed items reach. It decides which gap a
/// `Trivia` child was written in, so a separator standing for an empty gap does not take
/// the trivia that belongs to a later one. `None` means the offset is not known — the
/// tree's positions have stopped being positions in one source (a sourceless or
/// foreign-source child, or an unreconstructible optional item) — and the generated code
/// falls back to consuming trivia in child order.
#[derive(Clone, Debug)]
pub struct UnparseResult {
    /// The accumulator holding the `Doc` result and trivia state.
    pub accumulator: DocAccumulator,
    /// The position after consuming children from the CST node.
    pub new_pos: usize,
    /// The source offset the consumed items reach, or `None` when it is not known.
    pub cursor: Option<i64>,
}

impl UnparseResult {
    /// Construct a result from an accumulator and the new position, with no known cursor.
    pub fn new(accumulator: DocAccumulator, new_pos: usize) -> Self {
        UnparseResult {
            accumulator,
            new_pos,
            cursor: None,
        }
    }

    /// Construct a result from an accumulator, the new position, and the source cursor.
    pub fn with_cursor(accumulator: DocAccumulator, new_pos: usize, cursor: Option<i64>) -> Self {
        UnparseResult {
            accumulator,
            new_pos,
            cursor,
        }
    }

    /// Convenience accessor for the accumulated `Doc` (port of `UnparseResult.doc`).
    pub fn doc(&self) -> Doc {
        self.accumulator.doc()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::doc::{concat, text};

    #[test]
    fn new_stores_accumulator_and_pos() {
        let acc = DocAccumulator::new().add_non_trivia(text("a"));
        let result = UnparseResult::new(acc, 3);
        assert_eq!(result.new_pos, 3);
        assert_eq!(result.cursor, None);
        assert_eq!(result.accumulator.doc(), text("a"));
    }

    #[test]
    fn with_cursor_stores_the_source_offset() {
        let acc = DocAccumulator::new().add_non_trivia(text("a"));
        let result = UnparseResult::with_cursor(acc, 3, Some(7));
        assert_eq!(result.new_pos, 3);
        assert_eq!(result.cursor, Some(7));
    }

    #[test]
    fn doc_convenience_matches_accumulator_doc() {
        let acc = DocAccumulator::new()
            .add_non_trivia(text("a"))
            .add_non_trivia(text("b"));
        let result = UnparseResult::new(acc, 2);
        assert_eq!(result.doc(), concat(vec![text("a"), text("b")]));
    }

    #[test]
    fn doc_of_empty_accumulator_is_nil() {
        let result = UnparseResult::new(DocAccumulator::new(), 0);
        assert_eq!(result.doc(), Doc::Nil);
    }
}
