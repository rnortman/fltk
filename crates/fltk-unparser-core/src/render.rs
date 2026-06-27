//! The Wadler-Lindig pretty-printer: the final stage of the formatting pipeline.
//!
//! Direct port of `fltk/unparse/renderer.py`. It turns a resolved [`Doc`] tree (no
//! spacing-control nodes left) into a string, making flat-vs-break decisions per
//! `Group` against the configured `max_width`. The Python renderer is already
//! iterative (a working queue, not the call stack); this port preserves that.

use std::collections::VecDeque;
use std::rc::Rc;

use crate::doc::Doc;

/// Configuration for the renderer.
///
/// Port of `RendererConfig` (`renderer.py:21`); defaults are `indent_width = 4`,
/// `max_width = 80`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RendererConfig {
    /// Spaces added per `Nest` level when breaking.
    pub indent_width: usize,
    /// Target line width that drives flat-vs-break group decisions.
    pub max_width: usize,
}

impl Default for RendererConfig {
    fn default() -> Self {
        Self {
            indent_width: 4,
            max_width: 80,
        }
    }
}

/// Rendering mode for a queued item. Port of `renderer.Mode`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Mode {
    /// Render soft line breaks as spaces / nothing.
    Flat,
    /// Render soft line breaks as newlines.
    Break,
}

/// One item on the rendering queue: `(indent, mode, doc)`. Port of `RenderItem`.
type RenderItem = (usize, Mode, Rc<Doc>);

/// Mutable output state shared by the two output helpers, `break_line` and
/// `append_content`. A dedicated struct (rather than free locals) lets both helpers
/// mutate `result`, `current_column`, and `at_beginning_of_line` without contending
/// for the same mutable borrows.
struct Output {
    result: String,
    current_column: usize,
    at_beginning_of_line: bool,
}

impl Output {
    fn new() -> Self {
        Self {
            result: String::new(),
            current_column: 0,
            at_beginning_of_line: true,
        }
    }

    /// Append a newline and mark that we are at the beginning of a line.
    fn break_line(&mut self) {
        self.result.push('\n');
        self.at_beginning_of_line = true;
        self.current_column = 0;
    }

    /// Append text, adding indentation if at the beginning of a line.
    ///
    /// Empty text neither emits indentation nor advances the column, matching the
    /// Python guard (`if text and at_beginning_of_line` / `if text`).
    fn append_content(&mut self, text: &str, indent: usize) {
        if text.is_empty() {
            return;
        }
        if self.at_beginning_of_line {
            for _ in 0..indent {
                self.result.push(' ');
            }
            self.current_column = indent;
            self.at_beginning_of_line = false;
        }
        self.result.push_str(text);
        // Code-point count, matching Python's `len(str)`.
        self.current_column += text.chars().count();
    }
}

/// Wadler-Lindig pretty-printer for combinator documents. Port of `Renderer`.
#[derive(Clone, Copy, Debug, Default)]
pub struct Renderer {
    config: RendererConfig,
}

impl Renderer {
    /// Create a renderer with the given configuration.
    pub fn new(config: RendererConfig) -> Self {
        Self { config }
    }

    /// Render a document into a string. Port of `Renderer.render` (`renderer.py:47`).
    pub fn render(&self, doc: &Doc) -> String {
        let mut out = Output::new();

        // Queue of items to process. Items expand at the *front* (push_front) and are
        // taken from the front (pop_front), mirroring Python's `pop(0)`/`insert(0, …)`.
        // The root is wrapped in a Group so the top level gets a fit check, exactly as
        // the Python renderer does. The wrapping clone is shallow (one node; children
        // are Rc-bumped).
        let mut queue: VecDeque<RenderItem> = VecDeque::new();
        queue.push_back((0, Mode::Flat, Rc::new(Doc::Group(Rc::new(doc.clone())))));

        while let Some((indent, mode, doc)) = queue.pop_front() {
            match &*doc {
                Doc::Nil => {}
                // Text and Comment render identically here (both newline-aware,
                // re-indenting on each embedded newline); they diverge only in how
                // resolution/accumulation treats them, not in rendering.
                Doc::Text(content) | Doc::Comment(content) => {
                    for (i, line) in content.split('\n').enumerate() {
                        if i > 0 {
                            out.break_line();
                        }
                        out.append_content(line, indent);
                    }
                }
                Doc::Line => {
                    if mode == Mode::Flat {
                        out.append_content(" ", indent);
                    } else {
                        out.break_line();
                    }
                }
                Doc::SoftLine => {
                    // Nothing in flat mode; newline in break mode.
                    if mode == Mode::Break {
                        out.break_line();
                    }
                }
                Doc::Nbsp => {
                    // Non-breaking space always renders as a space.
                    out.append_content(" ", indent);
                }
                Doc::HardLine { blank_lines } => {
                    // 1 + blank_lines newlines (`0..=blank_lines` yields blank_lines + 1).
                    for _ in 0..=*blank_lines {
                        out.break_line();
                    }
                }
                Doc::Concat(docs) => {
                    // Push in reverse so children pop in order.
                    for d in docs.iter().rev() {
                        queue.push_front((indent, mode, d.clone()));
                    }
                }
                Doc::Nest {
                    indent: nest_indent,
                    content,
                } => {
                    let new_indent = indent + (*nest_indent as usize) * self.config.indent_width;
                    queue.push_front((new_indent, mode, content.clone()));
                }
                Doc::Group(content) => {
                    // Negative remaining width is meaningful: `fits` short-circuits to
                    // false on it, distinct from a remaining width of exactly zero.
                    let remaining_width =
                        self.config.max_width as isize - out.current_column as isize;
                    let mut test_queue: VecDeque<RenderItem> = VecDeque::new();
                    test_queue.push_back((indent, Mode::Flat, content.clone()));
                    let chosen = if self.fits(remaining_width, test_queue) {
                        Mode::Flat
                    } else {
                        Mode::Break
                    };
                    queue.push_front((indent, chosen, content.clone()));
                }
                // Spacing-control nodes and Join must be resolved away before rendering;
                // reaching one here is a generator/pipeline bug (the Python renderer
                // raises ValueError on these).
                Doc::Join { .. }
                | Doc::AfterSpec { .. }
                | Doc::BeforeSpec { .. }
                | Doc::SeparatorSpec { .. } => {
                    panic!(
                        "Unknown document type in renderer; spacing specs and joins must be \
                         resolved before rendering"
                    );
                }
            }
        }

        out.result
    }

    /// Check whether `items` fit in `width` remaining columns when rendered flat.
    ///
    /// Port of `Renderer._fits` (`renderer.py:147`). A negative `width` never fits.
    /// Everything is measured flat: `mode` is carried on each item but never
    /// consulted, and `indent` is threaded for `Nest` sub-items without affecting the
    /// column count. Unhandled node types (spacing specs, joins) contribute zero
    /// width; `fits` is intentionally lenient about them rather than asserting they
    /// were resolved.
    fn fits(&self, width: isize, mut items: VecDeque<RenderItem>) -> bool {
        if width < 0 {
            return false;
        }

        let mut column: isize = 0;

        while let Some((indent, mode, doc)) = items.pop_front() {
            match &*doc {
                Doc::Nil => {}
                Doc::Text(content) | Doc::Comment(content) => {
                    for (i, line) in content.split('\n').enumerate() {
                        if i > 0 {
                            // Newline resets the column to 0.
                            column = 0;
                        }
                        column += line.chars().count() as isize;
                        if column > width {
                            return false;
                        }
                    }
                }
                Doc::Line => {
                    column += 1; // Space in flat mode.
                    if column > width {
                        return false;
                    }
                }
                Doc::SoftLine => {
                    // Nothing in flat mode.
                }
                Doc::Nbsp => {
                    column += 1;
                    if column > width {
                        return false;
                    }
                }
                Doc::HardLine { .. } => return false, // Forces a break.
                Doc::Concat(docs) => {
                    for d in docs.iter().rev() {
                        items.push_front((indent, mode, d.clone()));
                    }
                }
                Doc::Nest {
                    indent: nest_indent,
                    content,
                } => {
                    let new_indent = indent + (*nest_indent as usize) * self.config.indent_width;
                    items.push_front((new_indent, mode, content.clone()));
                }
                Doc::Group(content) => {
                    items.push_front((indent, Mode::Flat, content.clone()));
                }
                // Mirrors the Python helper: unhandled types are simply skipped (no
                // contribution to width), never raised on.
                Doc::Join { .. }
                | Doc::AfterSpec { .. }
                | Doc::BeforeSpec { .. }
                | Doc::SeparatorSpec { .. } => {}
            }
        }

        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::doc::{comment, concat, group, hardline, line, nbsp, nest, nil, softline, text};

    fn render_with(config: RendererConfig, doc: Doc) -> String {
        Renderer::new(config).render(&doc)
    }

    fn render_default(doc: Doc) -> String {
        Renderer::default().render(&doc)
    }

    #[test]
    fn simple_text() {
        assert_eq!(render_default(text("hello world")), "hello world");
    }

    #[test]
    fn empty_doc() {
        assert_eq!(render_default(nil()), "");
    }

    #[test]
    fn hardline_renders_newline() {
        let doc = concat(vec![text("line1"), hardline(0), text("line2")]);
        assert_eq!(render_default(doc), "line1\nline2");
    }

    #[test]
    fn hardline_with_blanks() {
        let doc = concat(vec![text("line1"), hardline(2), text("line2")]);
        assert_eq!(render_default(doc), "line1\n\n\nline2");
    }

    #[test]
    fn group_fits() {
        let doc = group(concat(vec![text("short"), line(), text("text")]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 80
                },
                doc
            ),
            "short text"
        );
    }

    #[test]
    fn group_breaks() {
        let doc = group(concat(vec![
            text("very"),
            line(),
            text("long"),
            line(),
            text("text"),
        ]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 10
                },
                doc
            ),
            "very\nlong\ntext"
        );
    }

    #[test]
    fn nested_groups_inner_stays_together() {
        let inner = group(concat(vec![text("a"), line(), text("b")]));
        let outer = group(concat(vec![
            text("outer"),
            line(),
            inner,
            line(),
            text("end"),
        ]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 10
                },
                outer
            ),
            "outer\na b\nend"
        );
    }

    #[test]
    fn nest_indentation() {
        let doc = concat(vec![
            text("function {"),
            nest(1, concat(vec![hardline(0), text("body")])),
            hardline(0),
            text("}"),
        ]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 2,
                    max_width: 80
                },
                doc
            ),
            "function {\n  body\n}"
        );
    }

    #[test]
    fn group_with_nest_breaks_and_indents() {
        let doc = group(concat(vec![
            text("{"),
            nest(
                1,
                concat(vec![
                    line(),
                    text("item1"),
                    text(","),
                    line(),
                    text("item2"),
                ]),
            ),
            line(),
            text("}"),
        ]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 15
                },
                doc
            ),
            "{\n    item1,\n    item2\n}"
        );
    }

    #[test]
    fn softline_flat_and_break() {
        let doc = group(concat(vec![text("a"), softline(), text("b")]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 80
                },
                doc.clone()
            ),
            "ab"
        );
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 1
                },
                doc
            ),
            "a\nb"
        );
    }

    #[test]
    fn nbsp_stays_space_even_when_broken() {
        let doc = group(concat(vec![text("a"), nbsp(), text("b")]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 1
                },
                doc
            ),
            "a b"
        );
    }

    #[test]
    fn complex_nested() {
        let doc = concat(vec![
            text("function foo("),
            group(nest(
                1,
                concat(vec![
                    softline(),
                    text("arg1: string,"),
                    line(),
                    text("arg2: number"),
                ]),
            )),
            text(") {"),
            nest(
                1,
                concat(vec![
                    hardline(0),
                    text("return arg1 + arg2;"),
                    nest(1, concat(vec![hardline(0), text("deep;")])),
                ]),
            ),
            hardline(0),
            text("}"),
        ]);
        let expected =
            "function foo(\n  arg1: string,\n  arg2: number) {\n  return arg1 + arg2;\n    deep;\n}";
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 2,
                    max_width: 25
                },
                doc
            ),
            expected
        );
    }

    #[test]
    fn parent_breaks_before_child() {
        let inner = group(concat(vec![text("short"), line(), text("text")]));
        let outer = group(concat(vec![
            text("prefix"),
            line(),
            inner,
            line(),
            text("suffix"),
        ]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 20
                },
                outer
            ),
            "prefix\nshort text\nsuffix"
        );
    }

    #[test]
    fn broken_child_forces_parent_break() {
        let inner = group(concat(vec![
            text("very"),
            line(),
            text("long"),
            line(),
            text("inner"),
            line(),
            text("group"),
        ]));
        let outer = group(concat(vec![text("("), line(), inner, line(), text(")")]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 15
                },
                outer
            ),
            "(\nvery\nlong\ninner\ngroup\n)"
        );
    }

    #[test]
    fn group_nest_group_indent_when_fits_and_breaks() {
        let inner_fits = group(concat(vec![text("fits"), line(), text("inline")]));
        let outer_fits = group(nest(2, inner_fits));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 20
                },
                outer_fits
            ),
            "        fits inline"
        );

        let inner_breaks = group(concat(vec![
            text("this"),
            line(),
            text("definitely"),
            line(),
            text("exceeds"),
            line(),
            text("the"),
            line(),
            text("limit"),
        ]));
        let outer_breaks = group(nest(2, inner_breaks));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 20
                },
                outer_breaks
            ),
            "        this\n        definitely\n        exceeds\n        the\n        limit"
        );
    }

    #[test]
    fn respects_width_with_midline_group() {
        let group_content = group(concat(vec![text("medium"), line(), text("text")]));
        let doc = concat(vec![text("long prefix "), group_content]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 20
                },
                doc
            ),
            "long prefix medium\ntext"
        );
    }

    #[test]
    fn unbreakable_content_exceeds_width() {
        let doc = text("this_is_a_very_long_identifier_with_no_spaces");
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 10
                },
                doc
            ),
            "this_is_a_very_long_identifier_with_no_spaces"
        );
    }

    #[test]
    fn unbreakable_group_content() {
        let unbreakable_group = group(text("unbreakable_long_identifier"));
        let doc = concat(vec![text("prefix "), unbreakable_group]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 20
                },
                doc
            ),
            "prefix unbreakable_long_identifier"
        );
    }

    #[test]
    fn nested_groups_with_unbreakable_content() {
        let inner = group(text("very_long_unbreakable_name"));
        let outer = group(concat(vec![
            text("start"),
            line(),
            inner,
            line(),
            text("end"),
        ]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 15
                },
                outer
            ),
            "start\nvery_long_unbreakable_name\nend"
        );
    }

    #[test]
    fn negative_remaining_width_breaks_group() {
        let doc = concat(vec![
            text("0123456789"),
            group(concat(vec![text("a"), line(), text("b")])),
        ]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 10
                },
                doc
            ),
            "0123456789a\nb"
        );
    }

    #[test]
    fn zero_width_breaks_everything() {
        let doc = group(concat(vec![text("a"), line(), text("b")]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 0
                },
                doc
            ),
            "a\nb"
        );
    }

    #[test]
    fn hardline_with_negative_remaining_width() {
        let doc = concat(vec![text("12345"), hardline(0), text("next")]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 5
                },
                doc
            ),
            "12345\nnext"
        );
    }

    #[test]
    fn nil_and_empty_text_with_zero_width() {
        let cfg = RendererConfig {
            indent_width: 4,
            max_width: 0,
        };

        let breakable = group(concat(vec![text("a"), line(), text("b")]));
        assert_eq!(render_with(cfg, breakable), "a\nb");

        let unbreakable = group(concat(vec![text("a"), nil(), text("b")]));
        assert_eq!(render_with(cfg, unbreakable), "ab");

        let empty_only = group(concat(vec![nil(), text(""), nil()]));
        assert_eq!(render_with(cfg, empty_only), "");

        let nil_with_breaks = group(concat(vec![text("a"), nil(), line(), nil(), text("b")]));
        assert_eq!(render_with(cfg, nil_with_breaks), "a\nb");

        let empty_text_with_breaks = group(concat(vec![
            text("a"),
            text(""),
            line(),
            text(""),
            text("b"),
        ]));
        assert_eq!(render_with(cfg, empty_text_with_breaks), "a\nb");
    }

    #[test]
    fn exact_width_with_softline_and_nil() {
        let inner_group = group(concat(vec![softline(), nil(), text("")]));
        let outer_group = group(concat(vec![
            text("some"),
            line(),
            text("stuff"),
            line(),
            text("more"),
            inner_group,
        ]));
        let result = render_with(
            RendererConfig {
                indent_width: 4,
                max_width: 15,
            },
            outer_group,
        );
        assert_eq!(result, "some stuff more");
        assert_eq!(result.len(), 15);
    }

    #[test]
    fn exact_width_boundary_conditions() {
        let cfg = RendererConfig {
            indent_width: 4,
            max_width: 10,
        };

        let exact_fit = group(concat(vec![text("1234567890")]));
        assert_eq!(render_with(cfg, exact_fit), "1234567890");

        let one_over = group(concat(vec![text("12345678901")]));
        assert_eq!(render_with(cfg, one_over), "12345678901");

        let inner = group(concat(vec![text("a"), softline(), text("bc")]));
        let outer = group(concat(vec![text("prefix "), inner]));
        assert_eq!(render_with(cfg, outer), "prefix abc");
    }

    #[test]
    fn text_with_newlines_width_calculation() {
        let doc = group(concat(vec![text("line1\nab"), line(), text("xyz")]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 10
                },
                doc
            ),
            "line1\nab xyz"
        );
    }

    #[test]
    fn comment_with_newlines_width_calculation() {
        let doc = group(concat(vec![comment("// a\n// b"), line(), text("xyz")]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 10
                },
                doc
            ),
            "// a\n// b xyz"
        );
    }

    #[test]
    fn comment_reindentation() {
        let doc = nest(2, comment("/*\n * Line 1\n * Line 2\n */"));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 80
                },
                doc
            ),
            "        /*\n         * Line 1\n         * Line 2\n         */"
        );
    }

    #[test]
    fn text_preserves_exact_formatting() {
        let doc = nest(2, text("```\ndef foo():\n    pass\n```"));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 80
                },
                doc
            ),
            "        ```\n        def foo():\n            pass\n        ```"
        );
    }

    #[test]
    fn comment_empty_lines_no_indent() {
        let doc = nest(1, comment("/*\n\n * text\n\n */"));
        let result = render_with(
            RendererConfig {
                indent_width: 4,
                max_width: 80,
            },
            doc,
        );
        assert_eq!(result, "    /*\n\n     * text\n\n     */");
        let lines: Vec<&str> = result.split('\n').collect();
        assert_eq!(lines[1], "");
        assert_eq!(lines[3], "");
    }

    #[test]
    fn mixed_text_and_comment() {
        let doc = concat(vec![
            text("before"),
            comment("// comment\n// more"),
            text("\nafter"),
        ]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 2,
                    max_width: 20
                },
                doc
            ),
            "before// comment\n// more\nafter"
        );
    }

    #[test]
    fn nested_comment_indentation() {
        let doc = concat(vec![
            text("{\n"),
            nest(1, comment("// First\n// Second")),
            text("\n}"),
        ]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 2,
                    max_width: 80
                },
                doc
            ),
            "{\n  // First\n  // Second\n}"
        );
    }

    #[test]
    fn group_with_multiline_comment_breaks() {
        let doc = group(concat(vec![
            text("x = "),
            comment("/* a\n * b */"),
            text(";"),
        ]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 15
                },
                doc
            ),
            "x = /* a\n * b */;"
        );
    }

    #[test]
    fn comment_relative_indentation_preserved() {
        let doc = nest(1, comment("/*\n    indented\n        more indented\n*/"));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 80
                },
                doc
            ),
            "    /*\n        indented\n            more indented\n    */"
        );
    }

    #[test]
    fn text_with_multiple_newlines() {
        let doc = group(concat(vec![text("line1\n\n\nline2"), line(), text("end")]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 20
                },
                doc
            ),
            "line1\n\n\nline2 end"
        );
    }

    #[test]
    fn comment_first_line_not_reindented() {
        let doc = concat(vec![text("x = "), nest(1, comment("/* start\n * end */"))]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 80
                },
                doc
            ),
            "x = /* start\n     * end */"
        );
    }

    #[test]
    fn break_at_nest_boundaries() {
        let doc = concat(vec![
            text("outer"),
            nest(1, concat(vec![hardline(0), text("inner"), hardline(0)])),
            text("after"),
        ]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 20
                },
                doc
            ),
            "outer\n    inner\nafter"
        );

        let doc2 = concat(vec![
            text("outer"),
            nest(1, concat(vec![hardline(0), text("inner")])),
            hardline(0),
            text("after"),
        ]);
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 20
                },
                doc2
            ),
            "outer\n    inner\nafter"
        );
    }

    #[test]
    fn default_config_is_4_and_80() {
        assert_eq!(
            RendererConfig::default(),
            RendererConfig {
                indent_width: 4,
                max_width: 80
            }
        );
    }

    #[test]
    #[should_panic(expected = "Unknown document type in renderer")]
    fn unresolved_spec_panics() {
        let doc = Doc::AfterSpec {
            spacing: Rc::new(Doc::Line),
        };
        let _ = render_default(doc);
    }

    #[test]
    #[should_panic(expected = "Unknown document type in renderer")]
    fn unresolved_before_spec_panics() {
        let doc = Doc::BeforeSpec {
            spacing: Rc::new(Doc::Line),
        };
        let _ = render_default(doc);
    }

    #[test]
    #[should_panic(expected = "Unknown document type in renderer")]
    fn unresolved_join_panics() {
        let doc = Doc::Join {
            docs: vec![Rc::new(Doc::Text("a".to_string()))],
            separator: Rc::new(Doc::Line),
        };
        let _ = render_default(doc);
    }

    /// Sibling groups whose *combined* flat width exceeds `max_width` force the outer
    /// group to break, even though each sub-group would fit alone. Mirrors the Python
    /// `test_multiple_subgroups_algorithm_limitation`; guards the cross-sibling width
    /// accounting in `fits`.
    #[test]
    fn sibling_groups_break_when_combined_too_wide() {
        let g1 = group(concat(vec![text("short"), line(), text("one")])); // "short one" = 9
        let g2 = group(concat(vec![text("also"), line(), text("short")])); // "also short" = 10
        let g3 = group(concat(vec![text("tiny")])); // "tiny" = 4
                                                    // "short one also short tiny" = 25 chars, max_width 24 -> outer must break.
        let outer = group(concat(vec![g1, line(), g2, line(), g3]));
        assert_eq!(
            render_with(
                RendererConfig {
                    indent_width: 4,
                    max_width: 24
                },
                outer
            ),
            "short one\nalso short\ntiny"
        );
    }
}
