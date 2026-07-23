//! Port of `fltk/fegen/pyrt/errors.py` — farthest-failure tracking and error formatting.
//!
//! `ErrorTracker` records the farthest position any terminal attempt failed at,
//! along with the set of expected tokens at that position. `format_error_message`
//! produces a human-readable error string in the same format as Python's
//! `format_error_message`.

use std::collections::HashMap;
use std::fmt::Write as FmtWrite;

use crate::terminalsrc::TerminalSource;

/// Whether a terminal is a literal string or a regex pattern.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TokenType {
    Literal,
    Regex,
}

/// Context for a single failed terminal attempt, recorded in `ErrorTracker`.
///
/// `token: &'static str` — all callers are generated parsers (and tests) whose
/// literals and regex patterns are `'static`, making `ParseContext` `Copy` and
/// keeping the hot failure path (every failed terminal attempt) allocation-free.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ParseContext {
    pub rule_id: u32,
    pub token_type: TokenType,
    pub token: &'static str,
}

/// Tracks the farthest parse failure position and the expected tokens at that position.
///
/// Port of `errors.py:26-49`.
///
/// `longest_parse_len == -1` is the initial value (errors.py:26). `Default` is
/// implemented manually (not derived) to encode this invariant; callers cannot
/// accidentally initialise with the derive-default `0`.
#[derive(Debug)]
pub struct ErrorTracker {
    /// Farthest failure position. `-1` initial value = no failure recorded yet.
    pub longest_parse_len: i64,
    pub expected_context: Vec<ParseContext>,
}

impl Default for ErrorTracker {
    fn default() -> Self {
        ErrorTracker { longest_parse_len: -1, expected_context: Vec::new() }
    }
}

impl ErrorTracker {
    /// Record a failed literal match at `pos` for `rule_id`.
    ///
    /// - `pos < longest_parse_len` → ignored.
    /// - `pos == longest_parse_len` → appended.
    /// - `pos > longest_parse_len` → replaces the list and updates the position.
    pub fn fail_literal(&mut self, pos: i64, rule_id: u32, literal: &'static str) {
        self.fail(pos, ParseContext { rule_id, token_type: TokenType::Literal, token: literal });
    }

    /// Record a failed regex match at `pos` for `rule_id`.
    ///
    /// Same replace/append/ignore semantics as `fail_literal`.
    pub fn fail_regex(&mut self, pos: i64, rule_id: u32, regex: &'static str) {
        self.fail(pos, ParseContext { rule_id, token_type: TokenType::Regex, token: regex });
    }

    fn fail(&mut self, pos: i64, ctx: ParseContext) {
        if pos < self.longest_parse_len {
            return;
        }
        if pos == self.longest_parse_len {
            self.expected_context.push(ctx);
        } else {
            self.expected_context = vec![ctx];
            self.longest_parse_len = pos;
        }
    }
}

/// Escape control, bidi-control, line-separator, and zero-width characters.
///
/// Implementation lives in `fltk_cst_core::escape::escape_control_chars`; re-exported
/// here to preserve the public path `fltk_parser_core::errors::escape_control_chars`.
///
/// See `crates/fltk-cst-core/src/escape.rs` for the full escape specification and
/// the cross-backend pin note.
pub use fltk_cst_core::escape::escape_control_chars;

/// Produce a Python-equivalent error message from an `ErrorTracker`.
///
/// Port of `errors.py:52-71`.
///
/// Control characters and bidi/zero-width chars in `line_text` are escaped
/// using `escape_control_chars` (see `crates/fltk-cst-core/src/escape.rs`) —
/// `\xHH` for C0/DEL/C1, `\uXXXX` for bidi/LS/PS/zero-width — matching Python's
/// `escape_control_chars` byte-for-byte. The caret pad is computed from the escaped
/// prefix so it aligns with the escaped output.
///
/// Output format:
/// ```text
/// Syntax error at line {line+1} col {col+1}:
/// {line_text}
/// {' ' * col}^
/// Expected:
///   From rule "{name}":
///     {LITERAL|REGEX}: {py_repr(token)}
/// ```
///
/// Porting decisions:
/// - `rule_names: &[&str]` replaces Python's `rule_name_lookup` callable.
///   Out-of-range id → `"<unknown rule {id}>"` (no panic).
/// - `col == -1` (the `longest_parse_len == -1` case) → no leading spaces before `^`
///   (matches Python's `' ' * -1 == ''`).
/// - Within-rule token ordering: Python's `defaultdict(set)` iteration is
///   hash-nondeterministic. Rust groups by `rule_id` in first-occurrence order and
///   deduplicates within each group in first-occurrence order — deterministic output.
///   Phase 3's parity comparator must treat within-rule expected-token lines as an
///   unordered set when Python's output has ≥2 distinct tokens per rule group.
/// - Token strings are formatted with `py_repr_str` (Python `str.__repr__` semantics),
///   not Rust `{:?}`.
pub fn format_error_message(
    tracker: &ErrorTracker,
    terminals: &TerminalSource,
    rule_names: &[&str],
) -> String {
    let (line, col, line_text) = match terminals.pos_to_line_col(tracker.longest_parse_len) {
        Some(lc) => {
            let line_text = lc.line_span.text().unwrap_or_default();
            (lc.line, lc.col, line_text)
        }
        None => {
            // Unreachable: longest_parse_len ∈ [-1, len] by construction.
            // Fall back gracefully rather than panicking.
            let expected_block = build_expected_block(&tracker.expected_context, rule_names);
            return format!("Syntax error at unknown position\nExpected:\n{expected_block}");
        }
    };

    let split = col.max(0_i64) as usize;
    // split is a codepoint index; find its byte offset to slice &str safely.
    let split_bytes = line_text.char_indices().nth(split).map_or(line_text.len(), |(b, _)| b);
    let escaped_prefix = escape_control_chars(&line_text[..split_bytes]);
    let escaped_suffix = escape_control_chars(&line_text[split_bytes..]);
    let pad = escaped_prefix.chars().count();
    let spaces = " ".repeat(pad);
    let mut result = format!(
        "Syntax error at line {} col {}:\n{}{}\n{}^\nExpected:\n",
        line + 1,
        col + 1,
        escaped_prefix,
        escaped_suffix,
        spaces
    );
    result.push_str(&build_expected_block(&tracker.expected_context, rule_names));
    result
}

/// Build the `Expected:\n  From rule "...":\n    ...\n` block.
fn build_expected_block(contexts: &[ParseContext], rule_names: &[&str]) -> String {
    // Group contexts by rule_id in first-occurrence order, deduplicating within each group.
    let mut rule_order: Vec<u32> = Vec::new();
    let mut rule_contexts: HashMap<u32, Vec<ParseContext>> = HashMap::new();

    for ctx in contexts {
        let entry = rule_contexts.entry(ctx.rule_id).or_insert_with(|| {
            rule_order.push(ctx.rule_id);
            Vec::new()
        });
        // Dedup in first-occurrence order (mirrors Python's set, but deterministic).
        if !entry.contains(ctx) {
            entry.push(*ctx);
        }
    }

    let mut result = String::new();
    for rule_id in rule_order {
        let name = rule_names
            .get(rule_id as usize)
            .copied()
            .map(|s| s.to_owned())
            .unwrap_or_else(|| format!("<unknown rule {rule_id}>"));
        result.push_str(&format!("  From rule \"{name}\":\n"));
        for ctx in &rule_contexts[&rule_id] {
            let type_name = match ctx.token_type {
                TokenType::Literal => "LITERAL",
                TokenType::Regex => "REGEX",
            };
            result.push_str(&format!("    {}: {}\n", type_name, py_repr_str(ctx.token)));
        }
    }
    result
}

/// Reproduce Python 3 `str.__repr__` for the subset of strings that appear as grammar tokens.
///
/// Rules:
/// - Prefer single-quote wrapping; switch to double quotes iff the string contains `'` but not `"`.
/// - Escape: `\\` → `\\\\`, the active quote → `\'` or `\"`, `\n` → `\\n`, `\r` → `\\r`,
///   `\t` → `\\t`, other bytes < 0x20 and 0x7f as `\\xHH`.
/// - Non-ASCII chars are emitted raw (Python escapes non-printable Unicode, but grammar
///   tokens are printable; golden tests pin the domain; divergence outside tested domain
///   is documented here and acceptable).
fn py_repr_str(s: &str) -> String {
    let has_single = s.contains('\'');
    let has_double = s.contains('"');
    let quote = if has_single && !has_double { '"' } else { '\'' };

    let mut out = String::with_capacity(s.len() + 2);
    out.push(quote);
    for ch in s.chars() {
        match ch {
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if c == quote => {
                out.push('\\');
                out.push(c);
            }
            c if (c as u32) < 0x20 || c as u32 == 0x7f => {
                write!(out, "\\x{:02x}", c as u32).unwrap();
            }
            c => out.push(c),
        }
    }
    out.push(quote);
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn py_repr_simple() {
        assert_eq!(py_repr_str("hello"), "'hello'");
    }

    #[test]
    fn py_repr_backslash() {
        // Python: repr(r'\s+') == "'\\\\s+'"  (single quotes, backslash doubled)
        assert_eq!(py_repr_str(r"\s+"), r"'\\s+'");
    }

    #[test]
    fn py_repr_single_quote_in_string() {
        // String contains single quote but not double → switch to double quotes
        assert_eq!(py_repr_str("it's"), r#""it's""#);
    }

    #[test]
    fn py_repr_double_quote_in_string() {
        // String contains double quote → keep single quotes and escape
        assert_eq!(py_repr_str(r#"say "hi""#), r#"'say "hi"'"#);
    }

    #[test]
    fn py_repr_both_quotes_in_string() {
        // Both single and double quotes → single-quote wrapping, escape the single quote.
        assert_eq!(py_repr_str("it's a \"mix\""), r#"'it\'s a "mix"'"#);
    }

    #[test]
    fn py_repr_control_characters() {
        assert_eq!(py_repr_str("\t"), r"'\t'");
        assert_eq!(py_repr_str("\r"), r"'\r'");
        assert_eq!(py_repr_str("\x01"), r"'\x01'");
        assert_eq!(py_repr_str("\x7f"), r"'\x7f'");
    }

    // ── ErrorTracker ─────────────────────────────────────────────────────────

    #[test]
    fn fail_literal_replace_on_advance() {
        let mut t = ErrorTracker::default();
        t.fail_literal(0, 0, "a");
        t.fail_literal(5, 1, "b");
        assert_eq!(t.longest_parse_len, 5);
        assert_eq!(t.expected_context.len(), 1);
        assert_eq!(t.expected_context[0].token, "b");
    }

    #[test]
    fn fail_literal_append_at_same_pos() {
        let mut t = ErrorTracker::default();
        t.fail_literal(3, 0, "a");
        t.fail_literal(3, 1, "b");
        assert_eq!(t.longest_parse_len, 3);
        assert_eq!(t.expected_context.len(), 2);
    }

    #[test]
    fn fail_literal_ignore_behind() {
        let mut t = ErrorTracker::default();
        t.fail_literal(5, 0, "a");
        t.fail_literal(3, 1, "b");
        assert_eq!(t.longest_parse_len, 5);
        assert_eq!(t.expected_context.len(), 1);
        assert_eq!(t.expected_context[0].token, "a");
    }

    #[test]
    fn fail_regex_transition() {
        let mut t = ErrorTracker::default();
        t.fail_regex(2, 0, r"\s+");
        assert_eq!(t.longest_parse_len, 2);
        assert_eq!(t.expected_context[0].token_type, TokenType::Regex);
    }

    // escape_control_chars unit tests live in crates/fltk-cst-core/src/escape.rs.
    // The format_error_message tests below exercise the re-export indirectly.

    #[test]
    fn format_error_message_with_controls_in_line() {
        // Failing line contains \x1b[31m and \r; error at col 0.
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("\x1b[31mabc", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(0, 0, "x");
        let msg = format_error_message(&t, &ts, &["rule"]);
        assert!(msg.contains("\\x1b[31m"), "ESC should be escaped: {msg:?}");
        assert!(!msg.contains('\x1b'), "raw ESC must not appear in message: {msg:?}");
        let lines: Vec<&str> = msg.lines().collect();
        assert_eq!(lines[2], "^", "caret should be at col 0: {msg:?}");
    }

    #[test]
    fn format_error_message_caret_alignment_with_escaped_prefix() {
        // Line: "ab\x1bcd", error at col 3 (the 'c').
        // Prefix = "ab\x1b" (3 chars) → escaped "ab\\x1b" (6 chars) → pad = 6.
        use crate::terminalsrc::TerminalSource;
        // Need a newline so the sentinel quirk doesn't cut the 'c' and 'd'.
        // Use "ab\x1bcd\n" — line_ends=[5], line_span=[0,5)="ab\x1bcd".
        let ts = TerminalSource::new("ab\x1bcd\n", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(3, 0, "x"); // col=3
        let msg = format_error_message(&t, &ts, &["rule"]);
        let lines: Vec<&str> = msg.lines().collect();
        // line 1: header
        // line 2 (index 1): escaped line text
        // line 3 (index 2): caret line
        assert_eq!(lines[1], "ab\\x1bcd", "escaped line: {msg:?}");
        assert_eq!(lines[2], "      ^", "pad=6 spaces then ^: {msg:?}");
    }

    #[test]
    fn format_error_message_caret_at_control_char() {
        // Error column is itself a control character: caret lands on the '\' of its escape.
        // Line: "ab\x1bcd\n", error at col 2 (the ESC).
        // Prefix = "ab" (2 chars, no controls) → escaped_prefix = "ab" → pad = 2.
        // Escaped line = "ab\\x1bcd"; caret line = "  ^".
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("ab\x1bcd\n", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(2, 0, "x"); // col=2, the ESC
        let msg = format_error_message(&t, &ts, &["rule"]);
        let lines: Vec<&str> = msg.lines().collect();
        assert_eq!(lines[1], "ab\\x1bcd", "escaped line: {msg:?}");
        assert_eq!(lines[2], "  ^", "pad=2 spaces then ^: {msg:?}");
    }

    #[test]
    fn format_error_message_no_raw_controls_in_output() {
        // Assert no raw codepoint < U+0020 (other than \t, stripped by lines()) and no
        // U+007F, U+0080–U+009F appear in the formatted message when the input has controls.
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("\x00\x01\x1b\r\x7f\u{009b}abc\n", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(0, 0, "x");
        let msg = format_error_message(&t, &ts, &["rule"]);
        for ch in msg.chars() {
            let cp = ch as u32;
            assert!(
                !(cp < 0x20 && cp != 0x09 && cp != 0x0a)
                    && cp != 0x7F
                    && !(0x80..=0x9F).contains(&cp),
                "raw control char U+{cp:04X} found in message: {msg:?}"
            );
        }
    }

    #[test]
    fn format_error_message_no_raw_extended_set_in_output() {
        // Assert no raw codepoint from the full extended escape set appears in the
        // formatted message when the input contains one char from every class.
        use crate::terminalsrc::TerminalSource;
        let input = "\x00\x1b\r\x7f\u{009b}\u{061c}\u{200b}\u{200e}\u{2028}\u{202e}\u{2060}\u{2066}\u{feff}abc\n";
        let ts = TerminalSource::new(input, None);
        let mut t = ErrorTracker::default();
        t.fail_literal(0, 0, "x");
        let msg = format_error_message(&t, &ts, &["rule"]);
        for ch in msg.chars() {
            // Use escape_control_chars as oracle: if a char would be escaped, it must not
            // appear raw in the output. LF (U+000A) is in the escape set but appears raw as
            // the message's line separator — carve it out explicitly.
            if ch == '\n' {
                continue;
            }
            let escaped = escape_control_chars(&ch.to_string());
            assert!(
                escaped == ch.to_string(),
                "raw escaped-set char U+{:04X} found in message: {msg:?}",
                ch as u32
            );
        }
    }

    #[test]
    fn format_error_message_bidi_golden() {
        // Failing line contains U+202E (RLO bidi override); error at col 0.
        // Escaped line = "\\u202e123"; caret at col 0 → no pad.
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("\u{202e}123", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(0, 0, "x");
        let msg = format_error_message(&t, &ts, &["rule"]);
        let lines: Vec<&str> = msg.lines().collect();
        assert!(lines[1].starts_with("\\u202e"), "escaped line starts with \\u202e: {msg:?}");
        assert_eq!(lines[2], "^", "caret at col 0: {msg:?}");
        assert!(!msg.contains('\u{202e}'), "raw U+202E must not appear: {msg:?}");
    }

    #[test]
    fn format_error_message_bidi_caret_alignment() {
        // Line: U+202E (RLO) + "abc\n"; error at col 1 (the 'a').
        // Prefix = "\u{202e}" (1 codepoint) → escaped "\\u202e" (6 chars) → pad = 6.
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("\u{202e}abc\n", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(1, 0, "x"); // col=1, the 'a'
        let msg = format_error_message(&t, &ts, &["rule"]);
        let lines: Vec<&str> = msg.lines().collect();
        assert_eq!(lines[1], "\\u202eabc", "escaped line: {msg:?}");
        assert_eq!(lines[2], "      ^", "pad=6 spaces (\\u202e = 6 chars): {msg:?}");
    }

    // ── format_error_message golden tests ────────────────────────────────────
    // Expected strings verified against Python's format_error_message output.

    #[test]
    fn format_error_message_basic() {
        use crate::terminalsrc::TerminalSource;
        // "hello world" (11 chars, no newline): sentinel = len = 11, line_span = [0,11) = "hello world"
        let ts = TerminalSource::new("hello world", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(5, 0, "!");
        let msg = format_error_message(&t, &ts, &["expr"]);
        // Golden: Python produces exactly this format.
        // Line 1, col 6 (pos 5, col+1 = 6). Line text = text[0..11] = "hello world".
        let expected = "Syntax error at line 1 col 6:\nhello world\n     ^\nExpected:\n  From rule \"expr\":\n    LITERAL: '!'\n";
        assert_eq!(msg, expected, "got: {msg:?}");
    }

    #[test]
    fn format_error_message_minus_one_pos() {
        // longest_parse_len == -1: line 1, col 0, no spaces before ^.
        // pos_to_line_col(-1) on "abc" → line=0, col=-1.
        // col+1 = 0. spaces = "".repeat(0) = "".
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("abc", None);
        let t = ErrorTracker::default(); // longest_parse_len = -1
        let msg = format_error_message(&t, &ts, &[]);
        assert!(msg.starts_with("Syntax error at line 1 col 0:\n"), "got: {msg:?}");
        assert!(msg.contains("\n^\n"), "got: {msg:?}");
    }

    #[test]
    fn format_error_message_empty_input() {
        // Empty input + pos=-1: line 1, col 0, empty line.
        // pos_to_line_col(-1) on "" → line=0, col=-1. line_span = Span(0, -1). text = None → "".
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("", None);
        let t = ErrorTracker::default();
        let msg = format_error_message(&t, &ts, &[]);
        assert!(msg.starts_with("Syntax error at line 1 col 0:\n"), "got: {msg:?}");
        // Line text is empty, so the line is just "\n^\n".
        assert!(msg.contains("\n^\n"), "got: {msg:?}");
    }

    #[test]
    fn format_error_message_regex_token_backslash() {
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("   ", None);
        let mut t = ErrorTracker::default();
        t.fail_regex(0, 0, r"\s+");
        let msg = format_error_message(&t, &ts, &["ws_rule"]);
        // py_repr_str(r"\s+") = r"'\\s+'"
        assert!(msg.contains(r"    REGEX: '\\s+'"));
    }

    #[test]
    fn format_error_message_multi_rule() {
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("x", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(0, 0, "a");
        t.fail_literal(0, 1, "b");
        let msg = format_error_message(&t, &ts, &["rule_a", "rule_b"]);
        assert!(msg.contains("  From rule \"rule_a\":\n"));
        assert!(msg.contains("  From rule \"rule_b\":\n"));
    }

    #[test]
    fn format_error_message_dedup_within_rule() {
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("x", None);
        let mut t = ErrorTracker::default();
        // Same token twice for same rule should appear once.
        t.fail_literal(0, 0, "a");
        t.fail_literal(0, 0, "a");
        let msg = format_error_message(&t, &ts, &["rule_a"]);
        let count = msg.matches("LITERAL: 'a'").count();
        assert_eq!(count, 1, "dedup failed: literal 'a' appeared {count} times");
    }

    #[test]
    fn format_error_message_unknown_rule_id() {
        use crate::terminalsrc::TerminalSource;
        let ts = TerminalSource::new("x", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(0, 99, "z"); // rule_id 99 is out of range
        let msg = format_error_message(&t, &ts, &["only_rule"]);
        assert!(msg.contains("<unknown rule 99>"), "got: {msg}");
    }

    #[test]
    fn format_error_message_multiline() {
        use crate::terminalsrc::TerminalSource;
        // "abc\nxyz": pos 4 = 'x', line 1, col 0.
        let ts = TerminalSource::new("abc\nxyz", None);
        let mut t = ErrorTracker::default();
        t.fail_literal(4, 0, "Q");
        let msg = format_error_message(&t, &ts, &["rule_a"]);
        // line 2 (1-based), col 1 (1-based).
        // "abc\nxyz": len=7, line_ends=[3, 7] (3=newline, 7=sentinel=len).
        // line_span=[4,7)="xyz" (full last line).
        let expected =
            "Syntax error at line 2 col 1:\nxyz\n^\nExpected:\n  From rule \"rule_a\":\n    LITERAL: 'Q'\n";
        assert_eq!(msg, expected, "got: {msg:?}");
    }
}
