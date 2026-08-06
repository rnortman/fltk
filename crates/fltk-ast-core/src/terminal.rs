use std::sync::OnceLock;

use fltk_cst_core::{SourceText, Span};
use regex_automata::meta::Regex;

use crate::error::AstError;

/// One grammar terminal, compiled for whole-text matching.
pub struct TerminalPattern {
    pattern: String,
    regex: Regex,
}

impl TerminalPattern {
    /// Compile a grammar terminal.
    ///
    /// The pattern comes from a grammar the parser generator has already accepted, so an
    /// unsupported one is a generator bug rather than a user error, and this panics on it.
    ///
    /// The compiled form is `\A(?:<pattern>)\z`, which is what makes matching a *full* match
    /// rather than a prefix one: an alternation whose first branch matches a shorter prefix
    /// (`a|ab` against `"ab"`) must still match the whole text, as Python's
    /// `re.fullmatch` does.
    pub fn new(pattern: &str) -> Self {
        let whole = format!(r"\A(?:{pattern})\z");
        let regex = Regex::new(&whole).unwrap_or_else(|e| {
            panic!("terminal pattern {pattern:?} is not supported by regex_automata::meta::Regex: {e}")
        });
        Self {
            pattern: pattern.to_string(),
            regex,
        }
    }

    /// The terminal as the grammar spells it, for diagnostics.
    pub fn pattern(&self) -> &str {
        &self.pattern
    }

    /// Whether the terminal matches the whole of `text`.
    pub fn matches(&self, text: &str) -> bool {
        self.regex.is_match(text)
    }

    /// The compiled automaton, for a caller that needs capture groups rather than a yes or no.
    ///
    /// Crate-private: a regex type is no part of this crate's surface — generated code names
    /// terminals as patterns and reaches them through this type — and only the terminal-only
    /// split ([`crate::TerminalShape`]) needs more than a match test.
    pub(crate) fn regex(&self) -> &Regex {
        &self.regex
    }
}

impl std::fmt::Debug for TerminalPattern {
    /// The grammar's spelling; the compiled automaton has no useful rendering.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("TerminalPattern").field("pattern", &self.pattern).finish()
    }
}

/// One grammar terminal, compiled on first use.
///
/// [`new`](LazyTerminal::new) is `const`, so a generated converter declares its terminals as
/// `static` items in its own body and pays for the compilation only if something actually
/// serializes through that position.
#[derive(Debug)]
pub struct LazyTerminal {
    pattern: &'static str,
    compiled: OnceLock<TerminalPattern>,
}

impl LazyTerminal {
    /// Declare one terminal, without compiling it.
    pub const fn new(pattern: &'static str) -> Self {
        Self {
            pattern,
            compiled: OnceLock::new(),
        }
    }

    /// The compiled terminal.
    pub fn get(&self) -> &TerminalPattern {
        self.compiled.get_or_init(|| TerminalPattern::new(self.pattern))
    }
}

/// Check that a field's text is something the grammar's terminal could have matched.
///
/// Serialization runs every regex-backed text through this — field strings, coercion
/// renderings, `custom` unparse output, `text_from` targets — so that an AST value which
/// serializes at all serializes to text that re-parses to the same value.
pub fn validate_terminal<'a>(
    text: &'a str,
    pattern: &TerminalPattern,
    rule: &str,
    label: &str,
) -> Result<&'a str, AstError> {
    if pattern.matches(text) {
        return Ok(text);
    }
    Err(AstError::new(
        format!(
            "rule {rule:?}: the {label:?} text {text:?} does not match the terminal /{}/",
            pattern.pattern()
        ),
        Span::unknown(),
    ))
}

/// A span carrying its own single-token source, for a synthesized regex child.
///
/// The returned span is self-describing: consumers can extract its text without a separate
/// whole-document source.
pub fn source_span(text: &str) -> Span {
    let source = SourceText::from_str(text, None);
    // Span offsets are codepoint indices, not byte offsets.
    let length = i64::try_from(text.chars().count()).expect("terminal text length exceeds i64");
    Span::new_with_source(0, length, &source)
}

/// [`source_span`] over a text the grammar's terminal accepts.
pub fn text_span(text: &str, pattern: &TerminalPattern, rule: &str, label: &str) -> Result<Span, AstError> {
    Ok(source_span(validate_terminal(text, pattern, rule, label)?))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_terminal_matches_the_whole_text_only() {
        let digits = TerminalPattern::new("[0-9]+");
        assert!(digits.matches("42"));
        assert!(!digits.matches("42x"));
        assert!(!digits.matches("x42"));
        assert!(!digits.matches(""));
    }

    #[test]
    fn a_shorter_first_branch_does_not_shadow_a_whole_match() {
        // Leftmost-first matching alone would report `a` here and leave `b` unconsumed.
        let pattern = TerminalPattern::new("a|ab");
        assert!(pattern.matches("ab"));
        assert!(pattern.matches("a"));
        assert!(!pattern.matches("abc"));
    }

    #[test]
    fn an_anchor_bearing_pattern_still_matches() {
        let pattern = TerminalPattern::new("^[a-z]+$");
        assert!(pattern.matches("abc"));
        assert!(!pattern.matches("abc1"));
    }

    #[test]
    fn a_leading_flag_applies_to_the_wrapped_pattern() {
        let pattern = TerminalPattern::new("(?i)[a-z]+");
        assert!(pattern.matches("AbC"));
        assert!(!pattern.matches("Ab1"));
    }

    #[test]
    fn non_ascii_classes_match_by_codepoint() {
        let pattern = TerminalPattern::new("[À-ÿ]+");
        assert!(pattern.matches("Àé"));
        assert!(!pattern.matches("Àa"));
    }

    #[test]
    fn the_pattern_is_recoverable_for_diagnostics() {
        assert_eq!(TerminalPattern::new("[0-9]+").pattern(), "[0-9]+");
        assert_eq!(
            format!("{:?}", TerminalPattern::new("[0-9]+")),
            "TerminalPattern { pattern: \"[0-9]+\" }"
        );
    }

    #[test]
    #[should_panic(expected = "is not supported by")]
    fn an_uncompilable_pattern_panics() {
        TerminalPattern::new("[0-9");
    }

    #[test]
    fn validation_hands_back_accepted_text() {
        let pattern = TerminalPattern::new("[0-9]+");
        assert_eq!(validate_terminal("42", &pattern, "number", "val"), Ok("42"));
    }

    #[test]
    fn validation_names_rule_label_pattern_and_text() {
        let pattern = TerminalPattern::new("[0-9]+");
        let error = validate_terminal("12x", &pattern, "number", "val").unwrap_err();
        assert_eq!(
            error.message,
            "rule \"number\": the \"val\" text \"12x\" does not match the terminal /[0-9]+/"
        );
        assert_eq!(error.span, Span::unknown());
    }

    #[test]
    fn a_lazily_declared_terminal_compiles_once_and_matches() {
        static DIGITS: LazyTerminal = LazyTerminal::new("[0-9]+");
        let first: *const TerminalPattern = DIGITS.get();
        assert!(DIGITS.get().matches("42"));
        assert!(!DIGITS.get().matches("4x"));
        assert_eq!(first, DIGITS.get() as *const TerminalPattern, "the compiled form is cached");
    }

    #[test]
    fn a_synthesized_span_carries_its_own_text() {
        let span = source_span("host");
        assert_eq!(span.start(), 0);
        assert_eq!(span.end(), 4);
        assert_eq!(span.text().as_deref(), Some("host"));
        assert!(span.has_source());
    }

    #[test]
    fn a_synthesized_span_is_measured_in_codepoints() {
        // "café" is four codepoints and five UTF-8 bytes; a byte length would not resolve.
        let span = source_span("café");
        assert_eq!(span.end(), 4);
        assert_eq!(span.text().as_deref(), Some("café"));
    }

    #[test]
    fn an_empty_synthesized_span_is_source_bearing() {
        let span = source_span("");
        assert_eq!(span.end(), 0);
        assert_eq!(span.text().as_deref(), Some(""));
    }

    #[test]
    fn text_span_validates_before_building() {
        let pattern = TerminalPattern::new("[a-z]+");
        assert_eq!(text_span("host", &pattern, "identifier", "name").unwrap().end(), 4);
        let error = text_span("h0st", &pattern, "identifier", "name").unwrap_err();
        assert!(error.message.contains("does not match the terminal /[a-z]+/"));
    }
}
