//! The `Doc` pretty-printing combinator tree.
//!
//! Direct port of `fltk/unparse/combinators.py`. The Python module defines a frozen
//! dataclass hierarchy with ~15 variants; here that hierarchy collapses into a single
//! `enum`. Children are `Rc`-wrapped so accumulator clones and resolve-pass rewrites
//! share structure cheaply, mirroring Python's frozen-dataclass sharing.

use std::rc::Rc;

/// A pretty-printing document combinator.
///
/// One enum variant per node type in `combinators.py`'s `Doc` hierarchy:
/// content nodes (`Text`, `Comment`), break/space primitives (`Line`, `Nbsp`,
/// `SoftLine`, `HardLine`), structural wrappers (`Group`, `Nest`, `Concat`,
/// `Join`), the empty document (`Nil`), and the spacing-control nodes
/// (`AfterSpec`, `BeforeSpec`, `SeparatorSpec`) consumed by spacing resolution.
///
/// `Clone` is cheap: cloning an `Rc<Doc>` field is a refcount bump, never a deep
/// copy. The custom [`Drop`] impl tears the tree down iteratively (see below);
/// the derived `Debug`/`PartialEq` still recurse, but they are debugging/test
/// aids off the happy path, and deep-tree hardening of those is out of scope for
/// this milestone (design §3, open question 1).
#[derive(Clone, Debug, PartialEq)]
pub enum Doc {
    /// Literal text content.
    Text(String),
    /// Comment content that should be re-indented when formatted.
    Comment(String),
    /// Soft line/space - can be a space or newline.
    Line,
    /// Non-breaking space - always renders as space, never as newline.
    Nbsp,
    /// Soft break - renders as nothing or newline, never as space.
    SoftLine,
    /// Hard line break - always a newline, plus `blank_lines` additional blanks.
    HardLine { blank_lines: u32 },
    /// Try to fit content on one line, otherwise break at all soft lines.
    Group(Rc<Doc>),
    /// Indent content by `indent` when breaking.
    Nest { indent: u32, content: Rc<Doc> },
    /// Concatenate multiple documents.
    Concat(Vec<Rc<Doc>>),
    /// Join multiple documents with a separator between each pair.
    Join {
        docs: Vec<Rc<Doc>>,
        separator: Rc<Doc>,
    },
    /// Empty document - produces no output.
    Nil,
    /// Spacing applied after the preceding content.
    AfterSpec { spacing: Rc<Doc> },
    /// Spacing applied before the following content.
    BeforeSpec { spacing: Rc<Doc> },
    /// Default separator spacing (fallback if no before/after specs override).
    SeparatorSpec {
        spacing: Option<Rc<Doc>>,
        preserved_trivia: Option<Rc<Doc>>,
        required: bool,
    },
}

// Iterative Drop: a derived/recursive drop would recurse through `Rc<Doc>` children
// one frame per tree level. `Doc` depth tracks CST depth, which is attacker-controlled
// for parsers over untrusted input, so a deep tree would abort the process via stack
// exhaustion (uncatchable) — the same hazard that forced iterative teardown in the
// Rust CST (`gsm2tree_rs.py`). Drain the subtree through an explicit worklist instead.
impl Drop for Doc {
    fn drop(&mut self) {
        // Worklist allocates lazily (Vec::new does not heap-allocate until first push);
        // leaf docs never push and never allocate.
        let mut worklist: Vec<Rc<Doc>> = Vec::new();
        take_children(self, &mut worklist);
        while let Some(rc) = worklist.pop() {
            // Only descend into a child we uniquely own; a shared child stays alive and
            // dropping its `Rc` here merely decrements the count.
            if let Ok(mut child) = Rc::try_unwrap(rc) {
                take_children(&mut child, &mut worklist);
                // `child`'s `Rc` fields are now empty/sentinel, so the compiler-generated
                // drop of `child` at end of scope terminates immediately.
            }
        }
    }
}

/// Move every `Rc<Doc>` child of `doc` into `worklist`, leaving `doc`'s child slots
/// empty (taken `Vec`/`Option`, or a fresh `Nil`) so dropping `doc` cannot recurse.
///
/// Single-child slots are swapped with a freshly allocated `Rc::new(Doc::Nil)` rather
/// than a thread-local sentinel: `Drop` can run during thread-local destruction (e.g. a
/// `Doc` held in another `thread_local!` torn down later), where touching a `thread_local!`
/// panics, and a panic out of `drop` mid-unwind aborts the process. One trivial `Nil`
/// allocation per single-child node during teardown is negligible and matches the
/// no-TLS-in-drop precedent of the Rust CST's iterative teardown.
fn take_children(doc: &mut Doc, worklist: &mut Vec<Rc<Doc>>) {
    match doc {
        Doc::Group(content)
        | Doc::Nest { content, .. }
        | Doc::AfterSpec { spacing: content }
        | Doc::BeforeSpec { spacing: content } => {
            worklist.push(std::mem::replace(content, Rc::new(Doc::Nil)));
        }
        Doc::Concat(docs) => {
            worklist.append(docs);
        }
        Doc::Join { docs, separator } => {
            worklist.append(docs);
            worklist.push(std::mem::replace(separator, Rc::new(Doc::Nil)));
        }
        Doc::SeparatorSpec {
            spacing,
            preserved_trivia,
            ..
        } => {
            if let Some(s) = spacing.take() {
                worklist.push(s);
            }
            if let Some(t) = preserved_trivia.take() {
                worklist.push(t);
            }
        }
        Doc::Text(_)
        | Doc::Comment(_)
        | Doc::Line
        | Doc::Nbsp
        | Doc::SoftLine
        | Doc::HardLine { .. }
        | Doc::Nil => {}
    }
}

// ---- Helper constructors (port of the `combinators.py` module-level helpers) ----

/// Literal content rendered verbatim: never broken across lines or re-indented.
pub fn text(s: impl Into<String>) -> Doc {
    Doc::Text(s.into())
}

/// Create a comment node with re-indentable content.
pub fn comment(s: impl Into<String>) -> Doc {
    Doc::Comment(s.into())
}

/// Create a soft line break (space or newline).
pub fn line() -> Doc {
    Doc::Line
}

/// Create a non-breaking space.
pub fn nbsp() -> Doc {
    Doc::Nbsp
}

/// Create a soft break (nothing or newline).
pub fn softline() -> Doc {
    Doc::SoftLine
}

/// The identity element for [`concat`]: contributes no output and is dropped
/// during concatenation.
pub fn nil() -> Doc {
    Doc::Nil
}

/// Create a hard line break with `blank_lines` additional blank lines.
pub fn hardline(blank_lines: u32) -> Doc {
    Doc::HardLine { blank_lines }
}

/// Create a group that tries to fit content on one line.
pub fn group(content: Doc) -> Doc {
    Doc::Group(Rc::new(content))
}

/// Increase indentation by `indent` spaces while the enclosing group breaks;
/// a no-op when that group fits on one line.
pub fn nest(indent: u32, content: Doc) -> Doc {
    Doc::Nest {
        indent,
        content: Rc::new(content),
    }
}

/// Create a group with nested indentation (`group(nest(amount, content))`).
pub fn indent(amount: u32, content: Doc) -> Doc {
    group(nest(amount, content))
}

/// Join documents with a separator between each pair.
pub fn join(docs: Vec<Doc>, separator: Doc) -> Doc {
    Doc::Join {
        docs: docs.into_iter().map(Rc::new).collect(),
        separator: Rc::new(separator),
    }
}

/// Concatenate documents, flattening nested `Concat`s and dropping `Nil`s.
///
/// Port of `combinators.concat` (`combinators.py:172`): an empty result collapses
/// to `Nil`, a single survivor is returned directly, otherwise a `Concat` is built.
pub fn concat(docs: Vec<Doc>) -> Doc {
    let mut flattened: Vec<Rc<Doc>> = Vec::new();
    for mut doc in docs {
        // `Doc` implements `Drop`, so fields cannot be moved out of an owned value
        // (E0509). Splice a nested `Concat`'s children out via `&mut` (leaving it
        // empty, then dropped); push everything else other than `Nil`.
        if let Doc::Concat(inner) = &mut doc {
            flattened.append(inner);
        } else if !matches!(&doc, Doc::Nil) {
            flattened.push(Rc::new(doc));
        }
    }
    match flattened.len() {
        0 => Doc::Nil,
        1 => {
            let only = flattened.pop().expect("len checked == 1");
            // Unwrap when uniquely owned; clone only the rare shared single survivor
            // pulled out of a flattened nested `Concat`.
            Rc::try_unwrap(only).unwrap_or_else(|rc| (*rc).clone())
        }
        _ => Doc::Concat(flattened),
    }
}

/// Wrap `spacing` as a [`Doc::BeforeSpec`] control node: the spacing applies before
/// the following content and is resolved away at render time by
/// [`resolve_spacing_specs`](crate::resolve_spacing_specs).
pub fn before_spec(spacing: Doc) -> Doc {
    Doc::BeforeSpec {
        spacing: Rc::new(spacing),
    }
}

/// Wrap `spacing` as a [`Doc::AfterSpec`] control node: the spacing applies after
/// the preceding content and is resolved away at render time by
/// [`resolve_spacing_specs`](crate::resolve_spacing_specs).
pub fn after_spec(spacing: Doc) -> Doc {
    Doc::AfterSpec {
        spacing: Rc::new(spacing),
    }
}

/// Build a [`Doc::SeparatorSpec`] control node — the default inter-token separator,
/// resolved away at render time by
/// [`resolve_spacing_specs`](crate::resolve_spacing_specs).
///
/// Port of the Python unparser's `_create_separator_spec`
/// (`fltk/unparse/gsm2unparser.py:446`): either `spacing` or `preserved_trivia` may
/// be absent (`None`), and `required` marks a WS-required separator (one that must
/// not collapse away entirely). Both optional fields are `Rc`-wrapped on the way in,
/// matching `group`/`nest`/`before_spec`/`after_spec`.
pub fn separator_spec(spacing: Option<Doc>, preserved_trivia: Option<Doc>, required: bool) -> Doc {
    Doc::SeparatorSpec {
        spacing: spacing.map(Rc::new),
        preserved_trivia: preserved_trivia.map(Rc::new),
        required,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn text_holds_content() {
        assert_eq!(text("abc"), Doc::Text("abc".to_string()));
    }

    #[test]
    fn comment_holds_content() {
        assert_eq!(comment("// x"), Doc::Comment("// x".to_string()));
    }

    #[test]
    fn primitives_construct() {
        assert_eq!(line(), Doc::Line);
        assert_eq!(nbsp(), Doc::Nbsp);
        assert_eq!(softline(), Doc::SoftLine);
        assert_eq!(nil(), Doc::Nil);
    }

    #[test]
    fn hardline_carries_blank_lines() {
        assert_eq!(hardline(0), Doc::HardLine { blank_lines: 0 });
        assert_eq!(hardline(2), Doc::HardLine { blank_lines: 2 });
    }

    #[test]
    fn concat_empty_is_nil() {
        assert_eq!(concat(vec![]), Doc::Nil);
        assert_eq!(concat(vec![Doc::Nil, Doc::Nil]), Doc::Nil);
    }

    #[test]
    fn concat_drops_nils() {
        assert_eq!(concat(vec![Doc::Nil, text("a"), Doc::Nil]), text("a"));
    }

    #[test]
    fn concat_single_returns_element() {
        assert_eq!(concat(vec![text("a")]), text("a"));
    }

    #[test]
    fn concat_multiple_builds_concat() {
        assert_eq!(
            concat(vec![text("a"), text("b")]),
            Doc::Concat(vec![Rc::new(text("a")), Rc::new(text("b"))])
        );
    }

    #[test]
    fn concat_flattens_nested() {
        let inner = concat(vec![text("a"), text("b")]); // Concat[a, b]
        let outer = concat(vec![inner, text("c")]);
        assert_eq!(
            outer,
            Doc::Concat(vec![
                Rc::new(text("a")),
                Rc::new(text("b")),
                Rc::new(text("c")),
            ])
        );
    }

    #[test]
    fn group_nest_join_construct() {
        assert_eq!(group(text("a")), Doc::Group(Rc::new(text("a"))));
        assert_eq!(
            nest(4, text("a")),
            Doc::Nest {
                indent: 4,
                content: Rc::new(text("a"))
            }
        );
        assert_eq!(
            indent(2, text("a")),
            Doc::Group(Rc::new(Doc::Nest {
                indent: 2,
                content: Rc::new(text("a"))
            }))
        );
        assert_eq!(
            join(vec![text("a"), text("b")], text(",")),
            Doc::Join {
                docs: vec![Rc::new(text("a")), Rc::new(text("b"))],
                separator: Rc::new(text(",")),
            }
        );
    }

    #[test]
    fn deep_group_chain_drops_without_stack_overflow() {
        // A recursive Drop would overflow the (test-thread) stack at this depth; the
        // iterative Drop must drain it without aborting.
        let mut doc = text("leaf");
        for _ in 0..200_000 {
            doc = group(doc);
        }
        drop(doc);
    }

    #[test]
    fn deep_concat_chain_drops_without_stack_overflow() {
        let mut doc = text("leaf");
        for _ in 0..200_000 {
            doc = Doc::Concat(vec![Rc::new(doc)]);
        }
        drop(doc);
    }

    #[test]
    fn deep_join_chain_drops_without_stack_overflow() {
        let mut doc = text("leaf");
        for _ in 0..200_000 {
            doc = Doc::Join {
                docs: vec![Rc::new(doc)],
                separator: Rc::new(text(",")),
            };
        }
        drop(doc);
    }

    #[test]
    fn deep_nest_chain_drops_without_stack_overflow() {
        // Nest is a single-child variant draining through the same `take_children` arm
        // as Group; verify it too survives a 200k-deep teardown.
        let mut doc = text("leaf");
        for _ in 0..200_000 {
            doc = nest(4, doc);
        }
        drop(doc);
    }

    #[test]
    fn deep_afterspec_chain_drops_without_stack_overflow() {
        let mut doc = text("leaf");
        for _ in 0..200_000 {
            doc = Doc::AfterSpec {
                spacing: Rc::new(doc),
            };
        }
        drop(doc);
    }

    #[test]
    fn deep_beforespec_chain_drops_without_stack_overflow() {
        let mut doc = text("leaf");
        for _ in 0..200_000 {
            doc = Doc::BeforeSpec {
                spacing: Rc::new(doc),
            };
        }
        drop(doc);
    }

    #[test]
    fn separator_spec_wraps_optional_fields() {
        // Spacing present, no preserved trivia, required (the trivia-rule branch shape).
        assert_eq!(
            separator_spec(Some(hardline(1)), None, true),
            Doc::SeparatorSpec {
                spacing: Some(Rc::new(Doc::HardLine { blank_lines: 1 })),
                preserved_trivia: None,
                required: true,
            }
        );
        // Preserved trivia present, no spacing, not required (the non-trivia-rule shape).
        assert_eq!(
            separator_spec(None, Some(text("x")), false),
            Doc::SeparatorSpec {
                spacing: None,
                preserved_trivia: Some(Rc::new(text("x"))),
                required: false,
            }
        );
    }

    #[test]
    fn before_after_spec_wrap_spacing() {
        assert_eq!(
            before_spec(line()),
            Doc::BeforeSpec {
                spacing: Rc::new(Doc::Line)
            }
        );
        assert_eq!(
            after_spec(nbsp()),
            Doc::AfterSpec {
                spacing: Rc::new(Doc::Nbsp)
            }
        );
    }
}
