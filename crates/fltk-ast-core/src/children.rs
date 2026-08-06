//! Reading a CST node's labeled children, for the generated `from_cst` converters.
//!
//! Generated code collects the children carrying one label into a slice — the label enum is
//! per-rule, so the filtering is emitted, not generic — and then asks these helpers what the
//! field's arity allows. Each helper has a counterpart of the same name in
//! `fltk.fegen.pyrt.astrt`, and a CST the one backend refuses must be refused by the other for
//! the same stated reason: the message templates are one text, differing only where each
//! language spells a `Debug`/`repr` of an interpolated value (`{label:?}` renders `"key"` where
//! Python's `{label!r}` renders `'key'`). That correspondence is enforced by
//! `tests/test_ast_error_message_parity.py`, which reads the templates out of this file.
//!
//! A parser-produced CST satisfies every arity by construction; these failures are reachable
//! from a hand-built or mutated one.

use std::fmt::Debug;

use fltk_cst_core::Span;

use crate::error::AstError;

/// The single child of a required label.
pub fn one<'a, C>(children: &[&'a C], rule: &str, label: &str, span: &Span) -> Result<&'a C, AstError> {
    match children {
        [single] => Ok(single),
        _ => Err(AstError::new(
            format!(
                "rule {rule:?}: expected exactly one {label:?} child, found {}",
                children.len()
            ),
            span.clone(),
        )),
    }
}

/// The child of an optional label, or `None`.
pub fn optional<'a, C>(children: &[&'a C], rule: &str, label: &str, span: &Span) -> Result<Option<&'a C>, AstError> {
    match children {
        [] => Ok(None),
        [single] => Ok(Some(single)),
        _ => Err(at_most_one(children.len(), rule, label, span)),
    }
}

/// Whether an optional labeled literal is present.
pub fn presence<C>(children: &[&C], rule: &str, label: &str, span: &Span) -> Result<bool, AstError> {
    match children {
        [] => Ok(false),
        [_single] => Ok(true),
        _ => Err(at_most_one(children.len(), rule, label, span)),
    }
}

fn at_most_one(found: usize, rule: &str, label: &str, span: &Span) -> AstError {
    AstError::new(
        format!("rule {rule:?}: expected at most one {label:?} child, found {found}"),
        span.clone(),
    )
}

/// The source text of a span child.
///
/// `span` is the containing node's span, which is where the failure is reported: a sourceless
/// child span has no position of its own to point at.
pub fn text(child: &Span, rule: &str, label: &str, span: &Span) -> Result<String, AstError> {
    child.text_str().map(str::to_string).ok_or_else(|| {
        AstError::new(
            format!("rule {rule:?}: the {label:?} span carries no source text"),
            span.clone(),
        )
    })
}

/// The source text a node's own span covers, which is what a terminal-only rule carries.
pub fn node_text(span: &Span, rule: &str) -> Result<String, AstError> {
    span.text_str()
        .map(str::to_string)
        .ok_or_else(|| AstError::new(format!("rule {rule:?}: node span carries no source text"), span.clone()))
}

/// A child of a kind the label cannot hold.
///
/// Reachable only from a hand-built CST: the parser puts a child of the grammar's own term
/// under each label.
pub fn unexpected_child(rule: &str, label: &str, span: &Span) -> AstError {
    AstError::new(
        format!("rule {rule:?}: label {label:?} has a child of unexpected kind"),
        span.clone(),
    )
}

/// Two elements of a keyed collection carrying one key.
///
/// The two-span diagnostic a hand-written resolver writes: the offending element's span, and
/// the earlier element's as `related`.
pub fn duplicate_key<K: Debug>(rule: &str, key: &K, span: &Span, previous: &Span) -> AstError {
    AstError::with_related(
        format!("duplicate {rule} key {key:?}"),
        span.clone(),
        vec![("previously defined here".to_string(), previous.clone())],
    )
}

#[cfg(test)]
mod tests {
    use fltk_cst_core::SourceText;

    use super::*;

    fn span() -> Span {
        Span::unknown()
    }

    /// A stand-in for a generated child enum's payload; the helpers are generic over it.
    #[derive(Debug, PartialEq)]
    struct Child(u8);

    #[test]
    fn a_required_label_needs_exactly_one_child() {
        let child = Child(1);
        assert_eq!(one(&[&child], "entry", "key", &span()), Ok(&child));
        assert_eq!(
            one::<Child>(&[], "entry", "key", &span()).unwrap_err().message,
            "rule \"entry\": expected exactly one \"key\" child, found 0"
        );
        assert_eq!(
            one(&[&child, &child], "entry", "key", &span()).unwrap_err().message,
            "rule \"entry\": expected exactly one \"key\" child, found 2"
        );
    }

    #[test]
    fn an_optional_label_takes_none_or_one() {
        let child = Child(1);
        assert_eq!(optional::<Child>(&[], "entry", "tag", &span()), Ok(None));
        assert_eq!(optional(&[&child], "entry", "tag", &span()), Ok(Some(&child)));
        assert_eq!(
            optional(&[&child, &child], "entry", "tag", &span())
                .unwrap_err()
                .message,
            "rule \"entry\": expected at most one \"tag\" child, found 2"
        );
    }

    #[test]
    fn presence_is_whether_the_keyword_was_written() {
        let child = Child(1);
        assert_eq!(presence::<Child>(&[], "decl", "pub", &span()), Ok(false));
        assert_eq!(presence(&[&child], "decl", "pub", &span()), Ok(true));
        assert!(presence(&[&child, &child], "decl", "pub", &span()).is_err());
    }

    #[test]
    fn text_comes_off_the_span_that_carries_its_source() {
        let source = SourceText::from_str("hello", None);
        let child = Span::new_with_source(1, 4, &source);
        assert_eq!(text(&child, "word", "w", &span()), Ok("ell".to_string()));
        assert_eq!(node_text(&child, "word"), Ok("ell".to_string()));
    }

    #[test]
    fn a_sourceless_span_carries_no_text_to_convert() {
        let child = Span::new_sourceless(0, 3);
        assert_eq!(
            text(&child, "word", "w", &span()).unwrap_err().message,
            "rule \"word\": the \"w\" span carries no source text"
        );
        assert_eq!(
            node_text(&child, "word").unwrap_err().message,
            "rule \"word\": node span carries no source text"
        );
    }

    #[test]
    fn an_unexpected_child_names_the_rule_and_the_label() {
        assert_eq!(
            unexpected_child("wrap", "a", &span()).message,
            "rule \"wrap\": label \"a\" has a child of unexpected kind"
        );
    }

    #[test]
    fn a_duplicate_key_carries_both_locations() {
        let source = SourceText::from_str("aa", None);
        let first = Span::new_with_source(0, 1, &source);
        let second = Span::new_with_source(1, 2, &source);
        let error = duplicate_key("setting", &"host", &second, &first);
        assert_eq!(error.message, "duplicate setting key \"host\"");
        assert_eq!(error.span, second);
        assert_eq!(error.related, vec![("previously defined here".to_string(), first)]);
    }
}
