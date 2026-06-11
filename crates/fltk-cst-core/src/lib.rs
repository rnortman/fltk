#[cfg(feature = "python")]
mod cross_cdylib;
mod error;
#[cfg(feature = "python")]
pub mod registry;
mod shared;
mod span;

#[cfg(feature = "python")]
pub use cross_cdylib::{extract_source_text, extract_span, get_source_text_type, get_span_type, span_to_pyobject};
pub use error::CstError;
pub use shared::Shared;
pub use span::{SourceText, Span, SpanError};

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
        let src = SourceText::from_str("hello world");
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
        let src = SourceText::from_str("hello world");
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
        let src = SourceText::from_str("hello world");
        let s = Span::new_with_source(6, 11, &src);
        assert_eq!(s.text(), Some("world".to_string()));
    }

    #[test]
    fn span_text_non_ascii_codepoints() {
        // "café" is 4 codepoints but 5 UTF-8 bytes (é = 2 bytes)
        let src = SourceText::from_str("café au lait");
        let s = Span::new_with_source(0, 4, &src);
        assert_eq!(s.text(), Some("café".to_string()));
    }

    #[test]
    fn span_text_empty_span() {
        let src = SourceText::from_str("hello");
        let s = Span::new_with_source(2, 2, &src);
        assert_eq!(s.text(), Some("".to_string()));
    }

    #[test]
    fn span_text_negative_indices_returns_none() {
        let src = SourceText::from_str("hello");
        let s = Span {
            start: -1,
            end: 3,
            source: Some(src.inner.clone()),
        };
        assert_eq!(s.text(), None);
    }

    #[test]
    fn span_text_inverted_returns_none() {
        let src = SourceText::from_str("hello");
        let s = Span::new_with_source(4, 2, &src);
        assert_eq!(s.text(), None);
    }

    #[test]
    fn span_text_oob_returns_none() {
        let src = SourceText::from_str("hi");
        let s = Span::new_with_source(0, 10, &src);
        assert_eq!(s.text(), None);
    }

    #[test]
    fn span_has_source_true_false() {
        let src = SourceText::from_str("x");
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
        let src = SourceText::from_str("hello");
        let s = Span::new_with_source(0, 0, &src);
        assert_eq!(s.text(), Some("".to_string()));
    }

    #[test]
    fn span_merge_same_source_ok() {
        let src = SourceText::from_str("hello world");
        let a = Span::new_with_source(0, 5, &src);
        let b = Span::new_with_source(6, 11, &src);
        let merged = a.merge(&b).unwrap();
        assert_eq!(merged.start(), 0);
        assert_eq!(merged.end(), 11);
        assert_eq!(merged.text(), Some("hello world".to_string()));
    }

    #[test]
    fn span_merge_distinct_sources_err() {
        let src1 = SourceText::from_str("hello");
        let src2 = SourceText::from_str("hello");
        let a = Span::new_with_source(0, 5, &src1);
        let b = Span::new_with_source(0, 5, &src2);
        assert!(a.merge(&b) == Err(SpanError::SourceMismatch));
    }

    #[test]
    fn span_merge_sourceless_plus_sourced_carries_source() {
        let src = SourceText::from_str("hello world");
        let a = Span::new_sourceless(0, 5);
        let b = Span::new_with_source(6, 11, &src);
        let merged = a.merge(&b).unwrap();
        assert!(merged.has_source());
        assert_eq!(merged.start(), 0);
        assert_eq!(merged.end(), 11);
    }

    #[test]
    fn span_intersect_overlap_ok() {
        let src = SourceText::from_str("hello world");
        let a = Span::new_with_source(0, 7, &src);
        let b = Span::new_with_source(3, 11, &src);
        let inter = a.intersect(&b).unwrap();
        assert_eq!(inter.start(), 3);
        assert_eq!(inter.end(), 7);
        assert_eq!(inter.text(), Some("lo w".to_string()));
    }

    #[test]
    fn span_intersect_disjoint_returns_unknown() {
        let src = SourceText::from_str("hello world");
        let a = Span::new_with_source(0, 3, &src);
        let b = Span::new_with_source(5, 11, &src);
        let inter = a.intersect(&b).unwrap();
        // disjoint → unknown sentinel (-1, -1)
        assert!(inter == Span::unknown());
    }

    #[test]
    fn span_intersect_distinct_sources_err() {
        let src1 = SourceText::from_str("hello");
        let src2 = SourceText::from_str("world");
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
