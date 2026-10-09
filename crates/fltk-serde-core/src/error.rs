use std::cell::RefCell;
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
    ///
    /// Inside a [`positioned_error`] call, a `custom` whose message equals the diagnostic that
    /// call handed off returns that diagnostic whole — span and `related` included — and
    /// consumes it, so a second same-text `custom` in the same call is unpositioned again.
    fn custom<T: fmt::Display>(message: T) -> Self {
        let message = message.to_string();
        if let Some(error) = take_frame(&message) {
            return error;
        }
        DeserializeError::new(message, Span::unknown())
    }
}

thread_local! {
    /// One stack per thread. Deserialization is single-threaded within a call, and a frame
    /// is live only between [`positioned_error`]'s push and the return of the `E::custom`
    /// call inside it. A stack rather than a slot because an error type's `custom` may itself call
    /// [`positioned_error`] before building its own result, and the outer frame must survive.
    static HANDOFF: RefCell<Vec<DeserializeError>> = const { RefCell::new(Vec::new()) };
}

/// Return `error` — message, span and `related` intact — as the `D::Error` of whatever
/// Deserializer a generic `Deserialize` impl is running under.
///
/// A generic impl reaches its error type only through [`serde::de::Error::custom`], which
/// takes a message and nothing else. This hands the whole diagnostic to that call:
///
/// - Under FLTK's Deserializer (`E` is [`DeserializeError`]) the result *is* `error`. A known
///   span survives every enclosing frame, since [`positioned`](DeserializeError::positioned)
///   fills only an unknown one; an unknown span is positioned by the enclosing frame as usual.
/// - Under any other error type the result is `E::custom(message)` with the plain message
///   text: the position is dropped and the text is kept.
///
/// An error type whose own `custom` wraps `DeserializeError::custom` with the same text gets
/// the positioned diagnostic inside its wrapper. One that builds and discards a
/// `DeserializeError` with the same text inside its `custom` consumes the diagnostic, and
/// what it returns carries no position.
pub fn positioned_error<E: serde::de::Error>(error: DeserializeError) -> E {
    let message = error.message.clone();
    let depth = HANDOFF.with(|handoff| {
        let mut stack = handoff.borrow_mut();
        stack.push(error);
        stack.len() - 1
    });
    let _guard = Reclaim { depth };
    E::custom(message)
}

/// Truncates the handoff stack to the depth its frame pushed at, on every exit path including
/// a panic out of `E::custom` — so an unconsumed frame never outlives its call, and a nested
/// call's exit leaves the outer frame in place.
///
/// The push / truncate-on-drop / pop-if-top discipline here is the same as the inward
/// channel's (`provide`, `Unwind` and `take_if` in `channel.rs`); a fix to one applies to both.
struct Reclaim {
    depth: usize,
}

impl Drop for Reclaim {
    fn drop(&mut self) {
        HANDOFF.with(|handoff| handoff.borrow_mut().truncate(self.depth));
    }
}

/// Pop the innermost handed-off diagnostic iff there is one and its message is `message`.
fn take_frame(message: &str) -> Option<DeserializeError> {
    HANDOFF.with(|handoff| {
        let mut stack = handoff.borrow_mut();
        if stack.last().is_some_and(|frame| frame.message == message) {
            stack.pop()
        } else {
            None
        }
    })
}

/// How many handed-off diagnostics are live on this thread. Test-only: the invariant every
/// path has to restore is that this is zero once the outermost [`positioned_error`] returns.
#[cfg(test)]
pub(crate) fn handoff_depth() -> usize {
    HANDOFF.with(|handoff| handoff.borrow().len())
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

    /// A diagnostic with a source-backed span and one related location, over its own source.
    fn held_diagnostic(message: &str) -> (SourceText, DeserializeError) {
        let source = SourceText::from_str("first\nsecond", None);
        let error = DeserializeError::with_related(
            message,
            Span::new_with_source(6, 12, &source),
            vec![("first here".to_string(), Span::new_with_source(0, 5, &source))],
        );
        (source, error)
    }

    /// An error type whose `custom` panics: the window must still close on unwind.
    #[derive(Debug)]
    struct Panicky;

    impl fmt::Display for Panicky {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            f.write_str("panicky")
        }
    }

    impl std::error::Error for Panicky {}

    impl serde::de::Error for Panicky {
        fn custom<T: fmt::Display>(message: T) -> Self {
            panic!("custom refused {message}")
        }
    }

    /// An error type wrapping FLTK's, whose `custom` hands off an inner diagnostic of its own
    /// before building the outer one.
    #[derive(Debug)]
    struct Wrapping {
        inner: DeserializeError,
        outer: DeserializeError,
    }

    impl fmt::Display for Wrapping {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            write!(f, "{}", self.outer)
        }
    }

    impl std::error::Error for Wrapping {}

    impl serde::de::Error for Wrapping {
        fn custom<T: fmt::Display>(message: T) -> Self {
            let inner = positioned_error::<DeserializeError>(DeserializeError::with_related(
                "inner diagnostic",
                Span::new_sourceless(1, 2),
                vec![("inner related".to_string(), Span::new_sourceless(3, 4))],
            ));
            Wrapping {
                inner,
                outer: DeserializeError::custom(message),
            }
        }
    }

    /// An error type whose `custom` builds FLTK's error twice from the same text.
    #[derive(Debug)]
    struct Twice {
        first: DeserializeError,
        second: DeserializeError,
    }

    impl fmt::Display for Twice {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            write!(f, "{}", self.first)
        }
    }

    impl std::error::Error for Twice {}

    impl serde::de::Error for Twice {
        fn custom<T: fmt::Display>(message: T) -> Self {
            let message = message.to_string();
            Twice {
                first: DeserializeError::custom(&message),
                second: DeserializeError::custom(&message),
            }
        }
    }

    /// An error type whose `custom` builds FLTK's error from unrelated text before building it
    /// from the message it was handed, recording how many frames are live in between.
    #[derive(Debug)]
    struct Unrelated {
        note: DeserializeError,
        live_after_note: usize,
        main: DeserializeError,
    }

    impl fmt::Display for Unrelated {
        fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
            write!(f, "{}", self.main)
        }
    }

    impl std::error::Error for Unrelated {}

    impl serde::de::Error for Unrelated {
        fn custom<T: fmt::Display>(message: T) -> Self {
            let note = DeserializeError::custom("unrelated");
            let live_after_note = handoff_depth();
            Unrelated {
                note,
                live_after_note,
                main: DeserializeError::custom(message),
            }
        }
    }

    #[test]
    fn positioned_error_round_trips_span_and_related_under_the_fltk_error_type() {
        let (_source, held) = held_diagnostic("duplicate name `a`");
        let returned: DeserializeError = positioned_error(held.clone());
        assert_eq!(returned, held);
        assert_eq!(handoff_depth(), 0);
    }

    #[test]
    fn positioned_error_under_a_foreign_error_type_keeps_the_message_only() {
        let (_source, held) = held_diagnostic("duplicate name `a`");
        let returned: serde_json::Error = positioned_error(held);
        assert_eq!(returned.to_string(), "duplicate name `a`");
        assert_eq!(handoff_depth(), 0);
    }

    #[test]
    fn the_handoff_stack_is_empty_after_a_panic_inside_the_window() {
        let (_source, held) = held_diagnostic("duplicate name `a`");
        let outcome = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            positioned_error::<Panicky>(held);
        }));
        assert!(outcome.is_err());
        assert_eq!(handoff_depth(), 0);
        assert_eq!(DeserializeError::custom("duplicate name `a`").span, Span::unknown());
    }

    #[test]
    fn a_nested_handoff_inside_the_window_keeps_the_outer_diagnostic() {
        let (_source, held) = held_diagnostic("outer diagnostic");
        let returned: Wrapping = positioned_error(held.clone());
        assert_eq!(returned.inner.message, "inner diagnostic");
        assert_eq!(returned.inner.span, Span::new_sourceless(1, 2));
        assert_eq!(
            returned.inner.related,
            vec![("inner related".to_string(), Span::new_sourceless(3, 4))]
        );
        assert_eq!(returned.outer, held);
        assert_eq!(handoff_depth(), 0);
    }

    #[test]
    fn a_same_message_custom_after_the_window_is_unpositioned() {
        let (_source, held) = held_diagnostic("duplicate name `a`");
        let _: DeserializeError = positioned_error(held);
        let later = DeserializeError::custom("duplicate name `a`");
        assert_eq!(later.span, Span::unknown());
        assert!(later.related.is_empty());
    }

    #[test]
    fn an_unconsumed_frame_is_reclaimed_on_return() {
        // A foreign error type that never takes the frame: the guard must drop it.
        let (_source, held) = held_diagnostic("duplicate name `a`");
        let _: serde_json::Error = positioned_error(held);
        assert_eq!(handoff_depth(), 0);
        assert_eq!(DeserializeError::custom("duplicate name `a`").span, Span::unknown());
    }

    #[test]
    fn an_unknown_span_through_the_handoff_still_takes_the_frame_position() {
        let source = SourceText::from_str("abc", None);
        let related = vec![("first here".to_string(), Span::new_with_source(0, 1, &source))];
        let handed = DeserializeError::with_related("boom", Span::unknown(), related.clone());
        let returned: DeserializeError = positioned_error(handed);
        assert_eq!(returned.span, Span::unknown());
        let outer = Span::new_with_source(0, 3, &source);
        let positioned = returned.positioned(outer.clone());
        assert_eq!(positioned.span, outer);
        assert_eq!(positioned.related, related);
    }

    #[test]
    fn a_sourceless_span_through_the_handoff_survives_positioning() {
        let returned: DeserializeError = positioned_error(DeserializeError::new("boom", Span::new_sourceless(3, 7)));
        let positioned = returned.positioned(Span::new_sourceless(0, 1));
        assert_eq!(positioned.span, Span::new_sourceless(3, 7));
    }

    #[test]
    fn a_second_same_text_custom_inside_the_window_does_not_consume_twice() {
        let (_source, held) = held_diagnostic("duplicate name `a`");
        let returned: Twice = positioned_error(held.clone());
        assert_eq!(returned.first, held);
        assert_eq!(returned.second.span, Span::unknown());
        assert!(returned.second.related.is_empty());
        assert_eq!(handoff_depth(), 0);
    }

    #[test]
    fn a_different_message_custom_inside_the_window_leaves_the_frame_alone() {
        let (_source, held) = held_diagnostic("duplicate name `a`");
        let returned: Unrelated = positioned_error(held.clone());
        assert_eq!(returned.note.message, "unrelated");
        assert_eq!(returned.note.span, Span::unknown());
        assert!(returned.note.related.is_empty());
        assert_eq!(returned.live_after_note, 1);
        assert_eq!(returned.main, held);
        assert_eq!(handoff_depth(), 0);
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
