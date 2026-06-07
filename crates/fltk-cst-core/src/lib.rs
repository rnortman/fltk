mod span;

pub use span::{SourceText, Span};

#[cfg(test)]
mod tests {
    use super::*;

    // §4 item 1 (Span portion): pure-Rust GIL-free Span construction and equality.
    // The full node-subtree test (§4 item 1) lives in
    // tests/rust_cst_fixture/src/native_tests.rs, exercising generated node structs
    // (Entry, Identifier, etc.) via pub fn new_native/push_child_native/span_native/children_native.

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
}
