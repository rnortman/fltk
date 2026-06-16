#[cfg(feature = "python")]
mod cross_cdylib;
mod error;
#[doc(hidden)] // implementation-sharing module; not a public API — use fltk_parser_core::escape_control_chars
pub mod escape;
mod py_module;
#[cfg(feature = "python")]
pub mod registry;
mod shared;
mod span;

#[cfg(feature = "python")]
pub use cross_cdylib::{extract_source_text, extract_span, get_source_text_type, get_span_type, span_to_pyobject};
#[cfg(feature = "python")]
pub use py_module::{register_submodule, register_submodule_with_parent_name};
pub use error::CstError;
pub use shared::Shared;
pub use span::{resolve_line_col, LineColPos, SourceText, Span, SpanError};

/// Guard tests for the ABI layout probe — require `python` feature, GIL-free (compile-time sizes).
///
/// These tests assert two properties:
/// 1. The probe value is >= `size_of::<ffi::PyObject>() + size_of::<T>()` (floor check).
///    A constant-stub shortcut (returning 0 or any value < that floor) fails here,
///    preventing the scout's known-wrong `0usize` stub from silently passing.
/// 2. The probe value equals the value returned by the `_fltk_cst_core_abi_layout` classattr
///    bodies (`span_abi_layout_probe` / `source_text_abi_layout_probe`).  This guards against
///    replacing those bodies with hardcoded constants: the test recomputes independently and
///    the classattr body must match (correctness-2).
#[cfg(all(test, feature = "python"))]
mod abi_probe_tests {
    use super::span::{source_text_abi_layout_probe, span_abi_layout_probe};
    use super::{SourceText, Span};
    use pyo3::impl_::pyclass::PyClassImpl;

    #[test]
    fn span_probe_above_floor() {
        let probe = std::mem::size_of::<<Span as PyClassImpl>::Layout>();
        let floor = std::mem::size_of::<pyo3::ffi::PyObject>() + std::mem::size_of::<Span>();
        assert!(
            probe >= floor,
            "Span layout probe {probe} < floor {floor}; the probe stub is broken"
        );
    }

    #[test]
    fn span_probe_matches_classattr_body() {
        let probe = std::mem::size_of::<<Span as PyClassImpl>::Layout>();
        let classattr = span_abi_layout_probe();
        assert_eq!(
            probe, classattr,
            "Span layout probe {probe} != classattr body {classattr}; classattr is a stub"
        );
    }

    #[test]
    fn source_text_probe_above_floor() {
        let probe = std::mem::size_of::<<SourceText as PyClassImpl>::Layout>();
        let floor =
            std::mem::size_of::<pyo3::ffi::PyObject>() + std::mem::size_of::<SourceText>();
        assert!(
            probe >= floor,
            "SourceText layout probe {probe} < floor {floor}; the probe stub is broken"
        );
    }

    #[test]
    fn source_text_probe_matches_classattr_body() {
        let probe = std::mem::size_of::<<SourceText as PyClassImpl>::Layout>();
        let classattr = source_text_abi_layout_probe();
        assert_eq!(
            probe, classattr,
            "SourceText layout probe {probe} != classattr body {classattr}; classattr is a stub"
        );
    }
}

#[cfg(test)]
mod resolve_line_col_tests {
    use super::*;
    use std::sync::OnceLock;

    fn make_cache() -> OnceLock<Vec<i64>> {
        OnceLock::new()
    }

    #[test]
    fn resolve_first_line() {
        let text = "hello\nworld";
        let cache = make_cache();
        let lc = resolve_line_col(text, 1, &cache).unwrap();
        assert_eq!(lc.line, 0);
        assert_eq!(lc.col, 1);
        assert_eq!(lc.line_span.start(), 0);
        assert_eq!(lc.line_span.end(), 5);
    }

    #[test]
    fn resolve_second_line() {
        let text = "hello\nworld";
        let cache = make_cache();
        let lc = resolve_line_col(text, 6, &cache).unwrap();
        assert_eq!(lc.line, 1);
        assert_eq!(lc.col, 0);
        assert_eq!(lc.line_span.start(), 6);
        // sentinel is `len` (11) so the line_span covers the full final line.
        assert_eq!(lc.line_span.end(), 11);
    }

    #[test]
    fn resolve_last_char() {
        let text = "hello\nworld";
        let cache = make_cache();
        let lc = resolve_line_col(text, 10, &cache).unwrap();
        assert_eq!(lc.line, 1);
        assert_eq!(lc.col, 4);
    }

    #[test]
    fn resolve_empty_input() {
        // Empty source: len=0, sentinel pushed as -1. pos=-1 expected to return col=-1.
        let text = "";
        let cache = make_cache();
        let lc = resolve_line_col(text, -1, &cache).unwrap();
        assert_eq!(lc.line, 0);
        assert_eq!(lc.col, -1);
    }

    #[test]
    fn resolve_multibyte_col() {
        // "café\nworld": 'é' is one codepoint
        let text = "café\nworld";
        let cache = make_cache();
        let lc = resolve_line_col(text, 3, &cache).unwrap();
        assert_eq!(lc.line, 0);
        assert_eq!(lc.col, 3);
    }

    #[test]
    fn span_line_col_inner_negative_start_returns_none() {
        let src = SourceText::from_str("hello", None);
        let s = Span {
            start: -1,
            end: -1,
            source: Some(src.inner.clone()),
        };
        // Deliberate divergence from pos_to_line_col: start < 0 → None.
        assert_eq!(s.line_col_inner(), None);
    }

    #[test]
    fn span_line_col_inner_sourceless_returns_none() {
        let s = Span::new_sourceless(0, 5);
        assert_eq!(s.line_col_inner(), None);
    }

    #[test]
    fn span_line_col_inner_normal_position() {
        let src = SourceText::from_str("hello\nworld", None);
        let s = Span::new_with_source(6, 6, &src);
        let lc = s.line_col_inner().unwrap();
        assert_eq!(lc.line, 1);
        assert_eq!(lc.col, 0);
        // line_span should be source-bearing
        assert!(lc.line_span.has_source());
        assert_eq!(lc.line_span.text(), Some("world".to_string()));
    }

    #[test]
    fn span_line_col_inner_eof_clamp() {
        let src = SourceText::from_str("abc", None);
        let s_eof = Span::new_with_source(3, 3, &src);
        let s_last = Span::new_with_source(2, 2, &src);
        let lc_eof = s_eof.line_col_inner().unwrap();
        let lc_last = s_last.line_col_inner().unwrap();
        assert_eq!(lc_eof.line, lc_last.line);
        assert_eq!(lc_eof.col, lc_last.col);
    }

    #[test]
    fn span_line_col_inner_out_of_bounds_returns_none() {
        let src = SourceText::from_str("abc", None);
        let s = Span::new_with_source(100, 100, &src);
        assert_eq!(s.line_col_inner(), None);
    }

    #[test]
    fn span_filename_inner_present() {
        let src = SourceText::from_str("hello", Some("test.fltkg"));
        let s = Span::new_with_source(0, 5, &src);
        assert_eq!(s.filename_inner(), Some("test.fltkg"));
    }

    #[test]
    fn span_filename_inner_absent() {
        let src = SourceText::from_str("hello", None);
        let s = Span::new_with_source(0, 5, &src);
        assert_eq!(s.filename_inner(), None);
    }

    #[test]
    fn span_filename_inner_sourceless() {
        let s = Span::new_sourceless(0, 5);
        assert_eq!(s.filename_inner(), None);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Pure-Rust GIL-free Span construction and equality tests.
    // Full node-subtree tests live in tests/rust_cst_fixture/src/native_tests.rs,
    // exercising generated node structs via new/push_child/span/children.

    #[test]
    fn span_unknown_sourceless_gil_free() {
        let s = Span::unknown();
        assert!(s.start() == -1);
        assert!(s.end() == -1);
    }

    #[test]
    fn span_new_sourceless_gil_free() {
        let s = Span::new_sourceless(3, 7);
        assert!(s.start() == 3);
        assert!(s.end() == 7);
    }

    #[test]
    fn span_new_with_source_gil_free() {
        let src = SourceText::from_str("hello world", None);
        let s = Span::new_with_source(6, 11, &src);
        assert!(s.start() == 6);
        assert!(s.end() == 11);
    }

    #[test]
    fn span_equality_value_semantics_gil_free() {
        let s1 = Span::new_sourceless(3, 7);
        let s2 = Span::new_sourceless(3, 7);
        let s3 = Span::new_sourceless(3, 8);
        assert!(s1 == s2);
        assert!(s1 != s3);
    }

    #[test]
    fn span_equality_ignores_source_gil_free() {
        // Value semantics: sourceless sentinel equals source-bearing span at same offsets.
        let src = SourceText::from_str("hello world", None);
        let sourceless = Span::new_sourceless(3, 7);
        let source_bearing = Span::new_with_source(3, 7, &src);
        assert!(sourceless == source_bearing);
    }

    // Tests for the native (non-Python) Span API

    #[test]
    fn span_text_sourceless_returns_none() {
        let s = Span::new_sourceless(0, 5);
        assert_eq!(s.text(), None);
    }

    #[test]
    fn span_text_in_bounds_ascii() {
        let src = SourceText::from_str("hello world", None);
        let s = Span::new_with_source(6, 11, &src);
        assert_eq!(s.text(), Some("world".to_string()));
    }

    #[test]
    fn span_text_non_ascii_codepoints() {
        // "café" is 4 codepoints but 5 UTF-8 bytes (é = 2 bytes)
        let src = SourceText::from_str("café au lait", None);
        let s = Span::new_with_source(0, 4, &src);
        assert_eq!(s.text(), Some("café".to_string()));
    }

    #[test]
    fn span_text_empty_span() {
        let src = SourceText::from_str("hello", None);
        let s = Span::new_with_source(2, 2, &src);
        assert_eq!(s.text(), Some("".to_string()));
    }

    #[test]
    fn span_text_negative_indices_returns_none() {
        let src = SourceText::from_str("hello", None);
        let s = Span {
            start: -1,
            end: 3,
            source: Some(src.inner.clone()),
        };
        assert_eq!(s.text(), None);
    }

    #[test]
    fn span_text_inverted_returns_none() {
        let src = SourceText::from_str("hello", None);
        let s = Span::new_with_source(4, 2, &src);
        assert_eq!(s.text(), None);
    }

    #[test]
    fn span_text_oob_returns_none() {
        let src = SourceText::from_str("hi", None);
        let s = Span::new_with_source(0, 10, &src);
        assert_eq!(s.text(), None);
    }

    #[test]
    fn span_has_source_true_false() {
        let src = SourceText::from_str("x", None);
        assert!(Span::new_with_source(0, 1, &src).has_source());
        assert!(!Span::new_sourceless(0, 1).has_source());
        assert!(!Span::unknown().has_source());
    }

    #[test]
    fn span_len_basic() {
        let s = Span::new_sourceless(3, 7);
        assert_eq!(s.len(), 4);
    }

    #[test]
    fn span_len_sentinel() {
        assert_eq!(Span::unknown().len(), 0);
    }

    #[test]
    fn span_is_empty_true_false() {
        assert!(Span::unknown().is_empty());
        assert!(Span::new_sourceless(5, 5).is_empty());
        assert!(!Span::new_sourceless(3, 7).is_empty());
    }

    #[test]
    fn span_text_zero_to_zero() {
        // Edge case: start=0, end=0 should return Some("") even on a non-empty source.
        let src = SourceText::from_str("hello", None);
        let s = Span::new_with_source(0, 0, &src);
        assert_eq!(s.text(), Some("".to_string()));
    }

    #[test]
    fn span_merge_same_source_ok() {
        let src = SourceText::from_str("hello world", None);
        let a = Span::new_with_source(0, 5, &src);
        let b = Span::new_with_source(6, 11, &src);
        let merged = a.merge(&b).unwrap();
        assert_eq!(merged.start(), 0);
        assert_eq!(merged.end(), 11);
        assert_eq!(merged.text(), Some("hello world".to_string()));
    }

    #[test]
    fn span_merge_distinct_sources_err() {
        let src1 = SourceText::from_str("hello", None);
        let src2 = SourceText::from_str("hello", None);
        let a = Span::new_with_source(0, 5, &src1);
        let b = Span::new_with_source(0, 5, &src2);
        assert!(a.merge(&b) == Err(SpanError::SourceMismatch));
    }

    #[test]
    fn span_merge_sourceless_plus_sourced_carries_source() {
        let src = SourceText::from_str("hello world", None);
        let a = Span::new_sourceless(0, 5);
        let b = Span::new_with_source(6, 11, &src);
        let merged = a.merge(&b).unwrap();
        assert!(merged.has_source());
        assert_eq!(merged.start(), 0);
        assert_eq!(merged.end(), 11);
    }

    #[test]
    fn span_intersect_overlap_ok() {
        let src = SourceText::from_str("hello world", None);
        let a = Span::new_with_source(0, 7, &src);
        let b = Span::new_with_source(3, 11, &src);
        let inter = a.intersect(&b).unwrap();
        assert_eq!(inter.start(), 3);
        assert_eq!(inter.end(), 7);
        assert_eq!(inter.text(), Some("lo w".to_string()));
    }

    #[test]
    fn span_intersect_disjoint_returns_unknown() {
        let src = SourceText::from_str("hello world", None);
        let a = Span::new_with_source(0, 3, &src);
        let b = Span::new_with_source(5, 11, &src);
        let inter = a.intersect(&b).unwrap();
        // disjoint → unknown sentinel (-1, -1)
        assert!(inter == Span::unknown());
    }

    #[test]
    fn span_intersect_distinct_sources_err() {
        let src1 = SourceText::from_str("hello", None);
        let src2 = SourceText::from_str("world", None);
        let a = Span::new_with_source(0, 5, &src1);
        let b = Span::new_with_source(0, 5, &src2);
        assert!(a.intersect(&b) == Err(SpanError::SourceMismatch));
    }

    #[test]
    fn span_error_display() {
        assert_eq!(
            SpanError::SourceMismatch.to_string(),
            "cannot merge spans from different sources"
        );
    }
}
