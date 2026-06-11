//! Port of `fltk/fegen/pyrt/terminalsrc.py` — terminal-source and position utilities.
//!
//! `TerminalSource` holds a `SourceText` (the single owner of the input) plus a
//! codepoint-to-byte-offset table built once at construction. All external positions
//! are codepoint indices (`i64`), matching Python's string-indexing semantics.

use fltk_cst_core::{Span, SourceText};
use regex_automata::meta::Regex;
use regex_automata::{Anchored, Input};
use std::sync::OnceLock;

/// Line-and-column position within a source text.
///
/// Mirrors `LineColPos` in `terminalsrc.py`. `line` and `col` are 0-based
/// codepoint indices; `line_span` covers the entire line (exclusive of the `\n`).
/// `line_span` is source-bearing (improvement over Python's sourceless span;
/// equality-compatible because `Span` equality ignores source).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LineColPos {
    pub line: i64,
    pub col: i64,
    pub line_span: Span,
}

/// Terminal source for a packrat parser.
///
/// Holds the input text as a `SourceText` (Arc-shared) plus a codepoint→byte-offset
/// table (`cp_to_byte`) built once at construction. All parser positions are
/// codepoint indices (`i64`); methods translate to byte offsets internally.
///
/// # Note on negative positions
///
/// Python's `TerminalSource.consume_*` wraps negative indices (subscript semantics).
/// This implementation explicitly rejects `pos < 0` (returns `None`) because negative
/// positions are unreachable from generated code and the wrap-around behaviour cannot
/// produce valid `Span` objects in the Rust representation. `pos_to_line_col` accepts
/// `pos == -1` (the initial `ErrorTracker.longest_parse_len` sentinel) and `pos ∈ [0, len]`.
pub struct TerminalSource {
    source: SourceText,
    /// cp_to_byte[i] = byte offset of codepoint i; cp_to_byte[len] = text.len() sentinel.
    // Memory note: 8 bytes/codepoint (usize). Acceptable for grammar-sized inputs.
    // If memory ever matters, u32 offsets would halve it — not done now.
    cp_to_byte: Vec<usize>,
    /// Lazy codepoint indices of `\n` plus a final sentinel, matching terminalsrc.py:189-192.
    /// `OnceLock` keeps the `&self` API and makes the struct `Sync`.
    line_ends: OnceLock<Vec<i64>>,
}

impl TerminalSource {
    /// Construct from a `&str` (copies once into a new `SourceText`).
    pub fn new(text: &str) -> Self {
        Self::from_source_text(SourceText::from_str(text))
    }

    /// Construct from an existing `SourceText` (no copy; borrows text via the §2.2 accessor).
    pub fn from_source_text(source: SourceText) -> Self {
        let text = source.text();
        // Build cp_to_byte: cp_to_byte[i] is the byte index of the i-th codepoint.
        // The final entry cp_to_byte[len] = text.len() acts as a sentinel for slicing.
        let mut cp_to_byte: Vec<usize> = Vec::with_capacity(text.len() + 1);
        for (byte_idx, _) in text.char_indices() {
            cp_to_byte.push(byte_idx);
        }
        cp_to_byte.push(text.len()); // sentinel
        // For multibyte input, capacity was over-reserved (one slot per byte, but only
        // one entry per codepoint). Release the excess to avoid persistent overhead
        // proportional to byte count rather than codepoint count.
        cp_to_byte.shrink_to_fit();
        TerminalSource {
            source,
            cp_to_byte,
            line_ends: OnceLock::new(),
        }
    }

    /// Return a reference to the underlying `SourceText`.
    ///
    /// Used at generated-code span-construction sites (`Span::new_with_source`).
    pub fn source_text(&self) -> &SourceText {
        &self.source
    }

    /// Return the underlying source as a `&str`.
    pub fn text(&self) -> &str {
        self.source.text()
    }

    /// Return the number of codepoints in the source (Python's `terminals_len`).
    pub fn len(&self) -> i64 {
        // cp_to_byte has len+1 entries (sentinel), so codepoint count = cp_to_byte.len() - 1.
        (self.cp_to_byte.len() as i64) - 1
    }

    /// Return `true` if the source is empty.
    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    /// Try to consume a literal string starting at codepoint position `pos`.
    ///
    /// Port of `terminalsrc.py:168-175`.
    ///
    /// Returns `Some(span)` on success, `None` on mismatch, out-of-range, or `pos < 0`.
    /// The returned span is source-bearing (improvement over Python's sourceless spans;
    /// span equality ignores source so parity comparisons are unaffected).
    ///
    /// Empty-literal behaviour: `0 <= pos <= len` yields `Some(empty span)`; `pos > len`
    /// yields `None`. `pos < 0` always yields `None` (deliberate divergence from Python's
    /// negative-index wrapping — negative positions are unreachable from generated code).
    pub fn consume_literal(&self, pos: i64, literal: &str) -> Option<Span> {
        if pos < 0 || pos > self.len() {
            return None;
        }
        let byte_pos = self.cp_to_byte[pos as usize];
        let text = self.text();
        let mut literal_cp_len: i64 = 0;
        let mut text_chars = text[byte_pos..].chars();
        for lit_ch in literal.chars() {
            let text_ch = text_chars.next()?;
            if text_ch != lit_ch {
                return None;
            }
            literal_cp_len += 1;
        }
        Some(Span::new_with_source(pos, pos + literal_cp_len, &self.source))
    }

    /// Try to match a compiled regex at codepoint position `pos`.
    ///
    /// Port of the `consume_regex` design (controlling design §3.1).
    ///
    /// Performs an anchored search over the full haystack with the search span starting at
    /// the byte offset corresponding to `pos`. The full haystack is passed (not a slice
    /// from `pos`) so that `\b`/`\B` assertions resolve against the character before
    /// `byte_pos`, exactly reproducing Python's `re.match(pattern, string, pos=byte_pos)`
    /// semantics. `Anchored::Yes` guarantees any returned match begins at `byte_pos`;
    /// non-matches fail immediately without scanning the rest of the haystack.
    ///
    /// `pos == len` is valid — a pattern like `a*` matches empty at end-of-input.
    /// `pos < 0` or `pos > len` returns `None`.
    pub fn consume_regex(&self, pos: i64, regex: &Regex) -> Option<Span> {
        if pos < 0 || pos > self.len() {
            return None;
        }
        let byte_pos = self.cp_to_byte[pos as usize];
        let text = self.text();
        let input = Input::new(text)
            .anchored(Anchored::Yes)
            .span(byte_pos..text.len());
        let m = regex.search(&input)?;
        debug_assert_eq!(
            m.start(),
            byte_pos,
            "anchored search must start at the search span start"
        );
        // Convert the match end byte offset back to a codepoint index via binary search.
        // Regex match boundaries are always UTF-8 char boundaries, so the search hits an
        // exact entry in cp_to_byte.
        let end_byte = m.end();
        let end_cp = self.cp_to_byte.partition_point(|&b| b < end_byte);
        debug_assert!(
            self.cp_to_byte.get(end_cp) == Some(&end_byte),
            "regex match end {end_byte} is not a char boundary in cp_to_byte"
        );
        Some(Span::new_with_source(pos, end_cp as i64, &self.source))
    }

    /// Map a codepoint position to its line and column, with the line's span.
    ///
    /// Port of `terminalsrc.py:183-205` bisect logic.
    ///
    /// Domain: `pos ∈ [-1, len]`.
    /// - `pos == len`: decremented to `len - 1` (Python: terminalsrc.py:187-188).
    /// - `pos == -1`: the `ErrorTracker.longest_parse_len` initial sentinel; valid.
    /// - `pos < -1` or `pos > len`: returns `None` (≈ Python's `ValueError`; these are
    ///   unreachable from this runtime's own call sites).
    ///
    /// `line_ends` is computed lazily on first call and cached.
    /// `line_span` is source-bearing (equality-compatible with sourceless spans).
    pub fn pos_to_line_col(&self, pos: i64) -> Option<LineColPos> {
        let len = self.len();
        if pos < -1 || pos > len {
            return None;
        }
        // Apply the end-of-input decrement (terminalsrc.py:187-188).
        let pos = if pos == len { pos - 1 } else { pos };

        // Lazily compute line_ends: codepoint indices of '\n' chars, plus a final
        // sentinel of len-1 (or -1 for empty input) if not newline-terminated.
        // Mirrors terminalsrc.py:189-192.
        let line_ends = self.line_ends.get_or_init(|| {
            let text = self.text();
            // chars().enumerate() yields (codepoint_index, char) directly — no byte→codepoint
            // conversion needed (unlike char_indices which yields byte offsets).
            let mut ends: Vec<i64> = text
                .chars()
                .enumerate()
                .filter(|(_, c)| *c == '\n')
                .map(|(cp_idx, _)| cp_idx as i64)
                .collect();
            // Add sentinel if the text doesn't end with '\n' (or is empty).
            if ends.last() != Some(&(len - 1)) {
                ends.push(len - 1);
            }
            ends
        });

        // bisect_left equivalent: find leftmost index where line_ends[idx] >= pos.
        let idx = line_ends.partition_point(|&e| e < pos);
        assert!(idx < line_ends.len(), "bisect invariant: idx must be in range");

        let (col, line_span) = if idx > 0 {
            let col = pos - line_ends[idx - 1] - 1;
            let line_start = line_ends[idx - 1] + 1;
            let line_end = line_ends[idx];
            (col, Span::new_with_source(line_start, line_end, &self.source))
        } else {
            let col = pos;
            let line_end = line_ends[0];
            (col, Span::new_with_source(0, line_end, &self.source))
        };

        Some(LineColPos {
            line: idx as i64,
            col,
            line_span,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── consume_literal ──────────────────────────────────────────────────────

    #[test]
    fn consume_literal_ascii_match() {
        let ts = TerminalSource::new("hello world");
        let span = ts.consume_literal(6, "world").unwrap();
        assert_eq!(span.start(), 6);
        assert_eq!(span.end(), 11);
    }

    #[test]
    fn consume_literal_ascii_mismatch() {
        let ts = TerminalSource::new("hello");
        assert!(ts.consume_literal(0, "world").is_none());
    }

    #[test]
    fn consume_literal_exhaustion() {
        let ts = TerminalSource::new("hi");
        assert!(ts.consume_literal(1, "igo").is_none());
    }

    #[test]
    fn consume_literal_empty_literal_mid() {
        // Empty literal always succeeds for valid positions.
        let ts = TerminalSource::new("abc");
        let span = ts.consume_literal(1, "").unwrap();
        assert_eq!(span.start(), 1);
        assert_eq!(span.end(), 1);
    }

    #[test]
    fn consume_literal_empty_literal_at_len() {
        let ts = TerminalSource::new("abc");
        let span = ts.consume_literal(3, "").unwrap();
        assert_eq!(span.start(), 3);
        assert_eq!(span.end(), 3);
    }

    #[test]
    fn consume_literal_pos_eq_len_nonempty() {
        // pos == len with non-empty literal → fail (no chars available).
        let ts = TerminalSource::new("abc");
        assert!(ts.consume_literal(3, "a").is_none());
    }

    #[test]
    fn consume_literal_out_of_range() {
        let ts = TerminalSource::new("abc");
        assert!(ts.consume_literal(10, "a").is_none());
    }

    #[test]
    fn consume_literal_negative_pos() {
        let ts = TerminalSource::new("abc");
        // Negative positions always fail (deliberate divergence from Python).
        assert!(ts.consume_literal(-1, "a").is_none());
    }

    #[test]
    fn consume_literal_multibyte_match() {
        // "café" — 4 codepoints, 5 UTF-8 bytes
        let ts = TerminalSource::new("café latte");
        let span = ts.consume_literal(0, "café").unwrap();
        assert_eq!(span.start(), 0);
        assert_eq!(span.end(), 4);
    }

    #[test]
    fn consume_literal_multibyte_at_offset() {
        // Match starting at a codepoint offset after a multibyte character.
        let ts = TerminalSource::new("café latte");
        let span = ts.consume_literal(5, "latte").unwrap();
        assert_eq!(span.start(), 5);
        assert_eq!(span.end(), 10);
    }

    #[test]
    fn consume_literal_multibyte_in_literal() {
        let ts = TerminalSource::new("naïveté");
        let span = ts.consume_literal(2, "ïveté").unwrap();
        assert_eq!(span.start(), 2);
        assert_eq!(span.end(), 7);
    }

    // ── consume_regex ────────────────────────────────────────────────────────

    #[test]
    fn consume_regex_simple_match() {
        let ts = TerminalSource::new("hello world");
        let re = Regex::new(r"\w+").unwrap();
        let span = ts.consume_regex(0, &re).unwrap();
        assert_eq!(span.start(), 0);
        assert_eq!(span.end(), 5);
    }

    #[test]
    fn consume_regex_anchor_rejection() {
        // Pattern matches at pos+2 but not at pos → None.
        let ts = TerminalSource::new("  hello");
        let re = Regex::new(r"\w+").unwrap();
        assert!(ts.consume_regex(0, &re).is_none());
    }

    #[test]
    fn consume_regex_word_boundary_accept() {
        // \b at the start of "hello" should match.
        let ts = TerminalSource::new("hello world");
        let re = Regex::new(r"\bhello\b").unwrap();
        let span = ts.consume_regex(0, &re).unwrap();
        assert_eq!(span.start(), 0);
        assert_eq!(span.end(), 5);
    }

    #[test]
    fn consume_regex_word_boundary_reject_mid_word() {
        // Anchored to position 3 inside "hello" — \b should not match there.
        let ts = TerminalSource::new("hello world");
        let re = Regex::new(r"\bhello\b").unwrap();
        // Position 3 is mid-word ("lo"); \b pattern won't match starting here.
        assert!(ts.consume_regex(3, &re).is_none());
    }

    #[test]
    fn consume_regex_empty_match_at_end() {
        // `a*` matches empty string at end-of-input.
        let ts = TerminalSource::new("x");
        let re = Regex::new(r"a*").unwrap();
        let span = ts.consume_regex(1, &re).unwrap();
        assert_eq!(span.start(), 1);
        assert_eq!(span.end(), 1);
    }

    #[test]
    fn consume_regex_context_before_pos() {
        // \B at position 1 inside "hello" requires seeing the 'h' before pos=1.
        // A slice-the-haystack implementation would lose that context and fail.
        // Input::span with full haystack preserves it.
        let ts = TerminalSource::new("hello");
        let re = Regex::new(r"\Bello").unwrap();
        let span = ts.consume_regex(1, &re).unwrap();
        assert_eq!(span.start(), 1);
        assert_eq!(span.end(), 5);
    }

    #[test]
    fn consume_regex_word_boundary_reject_mid_word_via_context() {
        // \b at pos=1 inside "hello" requires seeing a non-word char before pos=1.
        // The 'h' at pos=0 is a word char, so \b fails and the match returns None.
        // A sliced-haystack implementation would place \b at start-of-string and
        // incorrectly match "ello" — this test catches that regression.
        let ts = TerminalSource::new("hello");
        let re = Regex::new(r"\bello").unwrap();
        assert!(ts.consume_regex(1, &re).is_none());
    }

    #[test]
    fn consume_regex_no_match_at_end() {
        // pos == len with a pattern that requires at least one char → None (not a bounds error).
        let ts = TerminalSource::new("x");
        let re = Regex::new(r"\w+").unwrap();
        // pos=1 is valid (len=1) but \w+ can't match at end-of-input.
        assert!(ts.consume_regex(1, &re).is_none());
    }

    #[test]
    fn consume_regex_out_of_range() {
        let ts = TerminalSource::new("abc");
        let re = Regex::new(r"a*").unwrap();
        assert!(ts.consume_regex(10, &re).is_none());
    }

    #[test]
    fn consume_regex_negative_pos() {
        let ts = TerminalSource::new("abc");
        let re = Regex::new(r"a").unwrap();
        assert!(ts.consume_regex(-1, &re).is_none());
    }

    #[test]
    fn consume_regex_multibyte_end_offset() {
        // Match ends after a multibyte sequence; byte→codepoint binary search must be exact.
        let ts = TerminalSource::new("café");
        let re = Regex::new(r"café").unwrap();
        let span = ts.consume_regex(0, &re).unwrap();
        assert_eq!(span.start(), 0);
        assert_eq!(span.end(), 4);
    }

    // ── pos_to_line_col ──────────────────────────────────────────────────────

    #[test]
    fn pos_to_line_col_first_line() {
        let ts = TerminalSource::new("hello\nworld");
        let lc = ts.pos_to_line_col(1).unwrap();
        assert_eq!(lc.line, 0);
        assert_eq!(lc.col, 1);
        assert_eq!(lc.line_span.start(), 0);
        assert_eq!(lc.line_span.end(), 5);
    }

    #[test]
    fn pos_to_line_col_second_line() {
        let ts = TerminalSource::new("hello\nworld");
        let lc = ts.pos_to_line_col(6).unwrap();
        assert_eq!(lc.line, 1);
        assert_eq!(lc.col, 0);
        assert_eq!(lc.line_span.start(), 6);
        assert_eq!(lc.line_span.end(), 10);
    }

    #[test]
    fn pos_to_line_col_last_line() {
        let ts = TerminalSource::new("hello\nworld");
        let lc = ts.pos_to_line_col(10).unwrap();
        assert_eq!(lc.line, 1);
        assert_eq!(lc.col, 4);
    }

    #[test]
    fn pos_to_line_col_pos_eq_len() {
        // pos == len → decremented to len-1
        let ts = TerminalSource::new("abc");
        let lc = ts.pos_to_line_col(3).unwrap();
        let lc2 = ts.pos_to_line_col(2).unwrap();
        assert_eq!(lc.line, lc2.line);
        assert_eq!(lc.col, lc2.col);
    }

    #[test]
    fn pos_to_line_col_trailing_newline() {
        // "abc\n": len=4, ends_with('\n') so no sentinel added; line_ends = [3].
        let ts = TerminalSource::new("abc\n");
        let lc0 = ts.pos_to_line_col(0).unwrap();
        assert_eq!(lc0.line, 0);
        assert_eq!(lc0.col, 0);
        // pos=3 is the '\n' itself — line 0, col 3.
        let lc3 = ts.pos_to_line_col(3).unwrap();
        assert_eq!(lc3.line, 0);
        assert_eq!(lc3.col, 3);
        // pos=4 == len → decremented to 3; same result as pos=3.
        let lc4 = ts.pos_to_line_col(4).unwrap();
        assert_eq!(lc4.line, lc3.line);
        assert_eq!(lc4.col, lc3.col);
    }

    #[test]
    fn pos_to_line_col_sentinel_minus_one() {
        // -1 is a valid sentinel (initial ErrorTracker.longest_parse_len).
        let ts = TerminalSource::new("abc");
        let lc = ts.pos_to_line_col(-1).unwrap();
        // -1 is decremented to -2... wait no: -1 is already accepted as valid sentinel.
        // The decrement is only applied for pos==len; -1 is in domain [-1,len].
        // With pos=-1, bisect_left on line_ends for (-1): all line_ends >= -1 unless
        // line_ends = [-1] (sentinel for empty). For non-empty: line_ends[-1] > -1, idx=0.
        assert_eq!(lc.line, 0);
        // col = pos = -1 (Python returns col=-1 here too)
        assert_eq!(lc.col, -1);
    }

    #[test]
    fn pos_to_line_col_empty_input() {
        let ts = TerminalSource::new("");
        // pos=-1: sentinel for empty input
        let lc = ts.pos_to_line_col(-1).unwrap();
        assert_eq!(lc.line, 0);
        assert_eq!(lc.col, -1);
    }

    #[test]
    fn pos_to_line_col_out_of_domain() {
        let ts = TerminalSource::new("abc");
        assert!(ts.pos_to_line_col(-2).is_none());
        assert!(ts.pos_to_line_col(4).is_none());
    }

    #[test]
    fn pos_to_line_col_multibyte_col() {
        // "café\nworld": 'é' is one codepoint; col counts codepoints, not bytes.
        let ts = TerminalSource::new("café\nworld");
        let lc = ts.pos_to_line_col(3).unwrap(); // 'é'
        assert_eq!(lc.line, 0);
        assert_eq!(lc.col, 3);
    }
}
