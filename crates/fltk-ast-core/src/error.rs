use std::fmt;

use fltk_cst_core::Span;

/// A CST could not be converted to its AST form, or an AST value could not be
/// serialized back to a CST.
///
/// `span` locates the failure; `related` carries secondary locations, such as the earlier
/// element a duplicate key collides with. Values built by hand carry
/// [`Span::unknown`] spans, so `related` and the message are the whole of the diagnostic
/// there.
///
/// This is the Rust counterpart of `fltk.fegen.pyrt.astrt.AstError`: the two backends refuse
/// the same inputs and write their messages from the same templates, but the offending value
/// is quoted by each language's own debug formatting (`{:?}` here, `!r` there), so the two
/// spellings are not byte-identical. Only rendered *output* is required to match byte for
/// byte; diagnostics are not.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AstError {
    /// What went wrong, naming the rule and label involved.
    pub message: String,
    /// Where it went wrong.
    pub span: Span,
    /// Secondary locations, each with its own explanation.
    pub related: Vec<(String, Span)>,
}

impl AstError {
    /// An error at one location.
    pub fn new(message: impl Into<String>, span: Span) -> Self {
        Self {
            message: message.into(),
            span,
            related: Vec::new(),
        }
    }

    /// An error with secondary locations, such as `("previously defined here", span)`.
    pub fn with_related(message: impl Into<String>, span: Span, related: Vec<(String, Span)>) -> Self {
        Self {
            message: message.into(),
            span,
            related,
        }
    }
}

impl fmt::Display for AstError {
    /// The message, followed by a 1-based `line`/`column` when the span resolves one.
    ///
    /// Sourceless and unknown spans resolve nothing, so a hand-built value's error is the
    /// bare message. Related locations are not rendered — a caller that wants them walks
    /// [`related`](Self::related), as a diagnostic renderer does.
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.span.line_col_inner() {
            Some(pos) => write!(f, "{} at line {}, column {}", self.message, pos.line + 1, pos.col + 1),
            None => write!(f, "{}", self.message),
        }
    }
}

impl std::error::Error for AstError {}

/// The failure of a `parse_str` convenience: source text either does not parse, or parses
/// to a CST the converter rejects.
///
/// The `Parse` arm carries the generated parser's own formatted diagnostic, which is a
/// string rather than a structured error because that is what the parser produces.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseToAstError {
    /// The source text is not in the language.
    Parse(String),
    /// The text parsed, but the CST does not convert.
    Ast(AstError),
}

impl fmt::Display for ParseToAstError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseToAstError::Parse(message) => write!(f, "{message}"),
            ParseToAstError::Ast(error) => write!(f, "{error}"),
        }
    }
}

impl std::error::Error for ParseToAstError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            ParseToAstError::Parse(_) => None,
            ParseToAstError::Ast(error) => Some(error),
        }
    }
}

impl From<AstError> for ParseToAstError {
    fn from(error: AstError) -> Self {
        ParseToAstError::Ast(error)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use fltk_cst_core::SourceText;

    #[test]
    fn display_names_a_resolvable_position_one_based() {
        let source = SourceText::from_str("first\nsecond", None);
        let error = AstError::new("rule 'x': bad", Span::new_with_source(6, 12, &source));
        assert_eq!(error.to_string(), "rule 'x': bad at line 2, column 1");
    }

    #[test]
    fn display_of_an_unknown_span_is_the_bare_message() {
        let error = AstError::new("rule 'x': bad", Span::unknown());
        assert_eq!(error.to_string(), "rule 'x': bad");
    }

    #[test]
    fn display_of_a_sourceless_span_is_the_bare_message() {
        let error = AstError::new("rule 'x': bad", Span::new_sourceless(3, 7));
        assert_eq!(error.to_string(), "rule 'x': bad");
    }

    #[test]
    fn related_locations_are_carried_but_not_rendered() {
        let source = SourceText::from_str("a b", None);
        let error = AstError::with_related(
            "duplicate 'setting' key 'a'",
            Span::new_with_source(2, 3, &source),
            vec![("previously defined here".to_string(), Span::new_with_source(0, 1, &source))],
        );
        assert_eq!(error.related.len(), 1);
        assert_eq!(error.related[0].0, "previously defined here");
        assert_eq!(error.related[0].1.start(), 0);
        assert_eq!(error.to_string(), "duplicate 'setting' key 'a' at line 1, column 3");
    }

    #[test]
    fn new_leaves_related_empty() {
        assert!(AstError::new("x", Span::unknown()).related.is_empty());
    }

    #[test]
    fn ast_error_is_a_std_error() {
        fn as_error(error: &dyn std::error::Error) -> String {
            error.to_string()
        }
        assert_eq!(as_error(&AstError::new("boom", Span::unknown())), "boom");
    }

    #[test]
    fn parse_arm_displays_the_parser_diagnostic() {
        let error = ParseToAstError::Parse("expected ';' at line 1".to_string());
        assert_eq!(error.to_string(), "expected ';' at line 1");
        assert!(std::error::Error::source(&error).is_none());
    }

    #[test]
    fn ast_arm_displays_and_sources_the_ast_error() {
        let error: ParseToAstError = AstError::new("rule 'x': bad", Span::unknown()).into();
        assert_eq!(error.to_string(), "rule 'x': bad");
        assert_eq!(
            std::error::Error::source(&error).map(ToString::to_string),
            Some("rule 'x': bad".to_string())
        );
    }
}
