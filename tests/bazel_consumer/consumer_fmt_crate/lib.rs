//! Crate root for the consumer-lane pure-Rust unparser target.
//!
//! The generated modules address each other as siblings (`super::cst`), so they are
//! submodules of this root; `out_dir` lands them beside this file.

pub mod ast;
pub mod cst;
pub mod parser;
pub mod unparser;

use fltk_unparser_core::{resolve_spacing_specs, Renderer, RendererConfig};

/// Parse `src` as a `sum` and render it through the format spec baked into the unparser.
///
/// `None` means the text did not parse; a rendering failure is impossible for a tree the
/// generated unparser covers.
pub fn format_sum(src: &str) -> Option<String> {
    let mut parser = parser::Parser::new(src, Some("consumer.txt"), true);
    let parsed = parser.apply__parse_sum(0)?;
    let guard = parsed.result.read();
    let unparsed = unparser::Unparser::new().unparse_sum(&guard)?;
    let resolved = resolve_spacing_specs(unparsed.doc());
    Some(
        Renderer::new(RendererConfig {
            indent_width: 4,
            max_width: 80,
        })
        .render(&resolved),
    )
}

/// Round-trip `src` through the generated AST instead of the CST: text in, typed value,
/// text out.
pub fn format_sum_via_ast(src: &str) -> Option<String> {
    let value = ast::parse_str(src, Some("consumer.txt")).ok()?;
    ast::unparse_str(&value, 80, 4).ok()
}

#[cfg(test)]
mod tests {
    use super::{format_sum, format_sum_via_ast};

    /// The spacing anchors in `consumer_unparser.fltkfmt` put one space on each side of
    /// `+`, so unformatted input renders differently from how it was written — which is
    /// what distinguishes a working baked spec from an unparser echoing source text.
    #[test]
    fn unformatted_input_renders_with_the_baked_spacing() {
        assert_eq!(format_sum("1+2").as_deref(), Some("1 + 2"));
    }

    /// Already-formatted input is a fixed point: formatting twice changes nothing.
    #[test]
    fn formatting_is_idempotent() {
        let once = format_sum("1  +2").expect("the fixture text must parse");
        let twice = format_sum(&once).expect("formatter output must re-parse");
        assert_eq!(once, twice);
    }

    #[test]
    fn unparseable_input_is_none() {
        assert!(format_sum("+").is_none());
    }

    /// The AST path renders through the same baked spec the CST path does, so the two agree.
    #[test]
    fn the_ast_entry_points_render_through_the_same_spec() {
        assert_eq!(format_sum_via_ast("1+2").as_deref(), Some("1 + 2"));
        assert_eq!(format_sum_via_ast("1+2"), format_sum("1+2"));
    }
}
