use std::fmt;

use fltk_ast_core::AstError;
use fltk_cst_core::Span;

/// A target type could not be deserialized from a CST.
///
/// `span` locates the failure; `related` carries secondary locations, such as the earlier
/// entry a duplicate map key collides with.
///
/// serde's derive raises unknown-field, missing-field and invalid-type errors through
/// [`serde::de::Error::custom`], which carries no position: those arrive here with
/// [`Span::unknown`] and the generated Deserializer fills the position in with
/// [`positioned`](Self::positioned) as the error passes back out through the frame that knows
/// where it happened. The message text of such an error is serde's; the position is fltk's.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeserializeError {
    /// What went wrong.
    pub message: String,
    /// Where it went wrong, or [`Span::unknown`] if nothing has positioned it yet.
    pub span: Span,
    /// Secondary locations, each with its own explanation.
    pub related: Vec<(String, Span)>,
}

impl DeserializeError {
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

    /// Fill in the position, but only if the error does not have one already.
    ///
    /// An error raised deep in a value keeps the precise span it was raised with; an outer
    /// frame's coarser span applies only to an error that arrived unpositioned.
    pub fn positioned(mut self, span: Span) -> Self {
        if self.span == Span::unknown() {
            self.span = span;
        }
        self
    }
}

impl fmt::Display for DeserializeError {
    /// The message, followed by a 1-based `line`/`column` when the span resolves one.
    ///
    /// Unpositioned and sourceless errors render as the bare message. Related locations are
    /// not rendered — a caller that wants them walks [`related`](Self::related).
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.span.line_col_inner() {
            Some(pos) => write!(f, "{} at line {}, column {}", self.message, pos.line + 1, pos.col + 1),
            None => write!(f, "{}", self.message),
        }
    }
}

impl std::error::Error for DeserializeError {}

impl serde::de::Error for DeserializeError {
    /// serde's own errors arrive unpositioned; the generated Deserializer positions them.
    fn custom<T: fmt::Display>(message: T) -> Self {
        DeserializeError::new(message.to_string(), Span::unknown())
    }
}

impl From<AstError> for DeserializeError {
    /// The scalar gates and the AST converters report [`AstError`]; the same message, span
    /// and secondary locations are the deserialize failure.
    fn from(error: AstError) -> Self {
        DeserializeError {
            message: error.message,
            span: error.span,
            related: error.related,
        }
    }
}

/// The failure of a `from_str` entry point: source text either does not parse, or parses to a
/// CST the target type does not accept.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseToTargetError {
    /// The source text is not in the language.
    Parse(String),
    /// The text parsed, but it does not deserialize into the target type.
    Deserialize(DeserializeError),
}

impl fmt::Display for ParseToTargetError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseToTargetError::Parse(message) => write!(f, "{message}"),
            ParseToTargetError::Deserialize(error) => write!(f, "{error}"),
        }
    }
}

impl std::error::Error for ParseToTargetError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            ParseToTargetError::Parse(_) => None,
            ParseToTargetError::Deserialize(error) => Some(error),
        }
    }
}

impl From<DeserializeError> for ParseToTargetError {
    fn from(error: DeserializeError) -> Self {
        ParseToTargetError::Deserialize(error)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use fltk_cst_core::SourceText;
    use serde::de::Error as _;

    #[test]
    fn display_names_a_resolvable_position_one_based() {
        let source = SourceText::from_str("first\nsecond", None);
        let error = DeserializeError::new("unknown field `prot`", Span::new_with_source(6, 12, &source));
        assert_eq!(error.to_string(), "unknown field `prot` at line 2, column 1");
    }

    #[test]
    fn display_of_an_unpositioned_error_is_the_bare_message() {
        assert_eq!(
            DeserializeError::new("unknown field `prot`", Span::unknown()).to_string(),
            "unknown field `prot`"
        );
    }

    #[test]
    fn custom_produces_an_unpositioned_error() {
        let error = DeserializeError::custom("missing field `port`");
        assert_eq!(error.message, "missing field `port`");
        assert_eq!(error.span, Span::unknown());
        assert!(error.related.is_empty());
    }

    #[test]
    fn positioned_fills_an_unknown_span() {
        let source = SourceText::from_str("abc", None);
        let error = DeserializeError::custom("boom").positioned(Span::new_with_source(0, 3, &source));
        assert_eq!(error.span.start(), 0);
        assert_eq!(error.to_string(), "boom at line 1, column 1");
    }

    #[test]
    fn positioned_leaves_a_known_span_alone() {
        let source = SourceText::from_str("hello world", None);
        let inner = Span::new_with_source(6, 11, &source);
        let outer = Span::new_with_source(0, 11, &source);
        let error = DeserializeError::new("boom", inner).positioned(outer);
        assert_eq!(error.span.start(), 6);
    }

    #[test]
    fn positioned_treats_a_sourceless_span_as_known() {
        // Only the unknown sentinel is fillable: a sourceless span is a real position that a
        // hand-built value carries, and overwriting it would move the error.
        let error = DeserializeError::new("boom", Span::new_sourceless(3, 7)).positioned(Span::new_sourceless(0, 1));
        assert_eq!(error.span.start(), 3);
    }

    #[test]
    fn related_locations_are_carried_but_not_rendered() {
        let source = SourceText::from_str("a b", None);
        let error = DeserializeError::with_related(
            "duplicate `setting` key `a`",
            Span::new_with_source(2, 3, &source),
            vec![("previously defined here".to_string(), Span::new_with_source(0, 1, &source))],
        );
        assert_eq!(error.related.len(), 1);
        assert_eq!(error.related[0].0, "previously defined here");
        assert_eq!(error.to_string(), "duplicate `setting` key `a` at line 1, column 3");
    }

    #[test]
    fn an_ast_error_converts_whole() {
        let source = SourceText::from_str("abcd", None);
        let ast = AstError::with_related(
            "rule 'n': not a u16",
            Span::new_with_source(0, 4, &source),
            vec![("here".to_string(), Span::unknown())],
        );
        let error: DeserializeError = ast.into();
        assert_eq!(error.message, "rule 'n': not a u16");
        assert_eq!(error.span.start(), 0);
        assert_eq!(error.related.len(), 1);
    }

    #[test]
    fn parse_arm_displays_the_parser_diagnostic() {
        let error = ParseToTargetError::Parse("expected ';' at line 1".to_string());
        assert_eq!(error.to_string(), "expected ';' at line 1");
        assert!(std::error::Error::source(&error).is_none());
    }

    #[test]
    fn deserialize_arm_displays_and_sources_the_inner_error() {
        let error: ParseToTargetError = DeserializeError::new("boom", Span::unknown()).into();
        assert_eq!(error.to_string(), "boom");
        assert_eq!(
            std::error::Error::source(&error).map(ToString::to_string),
            Some("boom".to_string())
        );
    }
}
