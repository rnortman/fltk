//! Canonical escape-control-chars implementation shared across both Rust crates.
//!
//! `escape_control_chars` produces the same byte-for-byte output as
//! `fltk/fegen/pyrt/errors.py:escape_control_chars`. The cross-language pin is
//! maintained by duplicated literal strings in:
//!   - `#[cfg(test)]` below
//!   - `tests/test_pyrt_errors.py`
//!
//! ## Escape specification
//!
//! Per-character mapping; identical output in both backends:
//!
//! | Range | Class | Representation |
//! |---|---|---|
//! | U+0000–U+001F except U+0009 (TAB) | C0 controls | `\xHH` (2 lowercase hex digits) |
//! | U+007F | DEL | `\xHH` |
//! | U+0080–U+009F | C1 controls | `\xHH` |
//! | U+061C | ALM (Bidi_Control) | `\uXXXX` (4 lowercase hex digits) |
//! | U+200B–U+200F | ZWSP, ZWNJ, ZWJ, LRM, RLM | `\uXXXX` |
//! | U+2028–U+202E | LS, PS, LRE, RLE, PDF, LRO, RLO | `\uXXXX` |
//! | U+2060 | Word Joiner | `\uXXXX` |
//! | U+2066–U+2069 | LRI, RLI, FSI, PDI | `\uXXXX` |
//! | U+FEFF | ZWNBSP/BOM | `\uXXXX` |
//!
//! Everything else (including TAB and all other printable/non-printable Unicode)
//! passes through unchanged.
//!
//! Backslash is not escaped; output is not round-trippable (deliberate, preexisting).
//! No set member lies in U+00A0–U+00FF or above U+FFFF, so `\xHH` and `\uXXXX`
//! cover the full set exactly with no overlap.

use std::fmt::Write as FmtWrite;

/// Whether a codepoint must be escaped.
#[inline(always)]
fn needs_escape(cp: u32) -> bool {
    // C0 (except TAB), DEL, C1
    (cp <= 0x1F && cp != 0x09)
        || cp == 0x7F
        || (0x80..=0x9F).contains(&cp)
        // ALM
        || cp == 0x061C
        // ZWSP, ZWNJ, ZWJ, LRM, RLM
        || (0x200B..=0x200F).contains(&cp)
        // LS, PS, LRE, RLE, PDF, LRO, RLO
        || (0x2028..=0x202E).contains(&cp)
        // Word Joiner
        || cp == 0x2060
        // LRI, RLI, FSI, PDI
        || (0x2066..=0x2069).contains(&cp)
        // ZWNBSP/BOM
        || cp == 0xFEFF
}

/// Escape control, bidi-control, line-separator, and zero-width characters.
///
/// Codepoints ≤ U+009F in the escape set → `\xHH` (lowercase, exactly 2 hex digits).
/// Codepoints > U+00FF in the escape set → `\uXXXX` (lowercase, exactly 4 hex digits).
///
/// Cross-backend pinned: output is byte-identical with the Python implementation in
/// `fltk/fegen/pyrt/errors.py:escape_control_chars`.
///
/// See module-level doc for the full escape specification.
pub fn escape_control_chars(s: &str) -> String {
    // Fast path: escape-free input — return a copy without rebuilding char-by-char.
    if !s.chars().any(|c| needs_escape(c as u32)) {
        return s.to_owned();
    }
    let mut out = String::with_capacity(s.len());
    for ch in s.chars() {
        let cp = ch as u32;
        if needs_escape(cp) {
            if cp <= 0x9F {
                write!(out, "\\x{:02x}", cp).unwrap();
            } else {
                write!(out, "\\u{:04x}", cp).unwrap();
            }
        } else {
            out.push(ch);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── Existing C0/DEL/C1 rows (moved verbatim from errors.rs; unchanged literals
    //    prove \xHH output is byte-for-byte preserved) ───────────────────────────

    #[test]
    fn escape_control_chars_table() {
        // C0 controls (except TAB) → \xHH
        assert_eq!(escape_control_chars("\x00"), "\\x00");
        assert_eq!(escape_control_chars("\x1b"), "\\x1b");
        assert_eq!(escape_control_chars("\r"), "\\x0d");
        assert_eq!(escape_control_chars("\n"), "\\x0a");
        // DEL → \x7f
        assert_eq!(escape_control_chars("\x7f"), "\\x7f");
        // C1 → \xHH (two-digit)
        assert_eq!(escape_control_chars("\u{009b}"), "\\x9b");
        assert_eq!(escape_control_chars("\u{0080}"), "\\x80");
        assert_eq!(escape_control_chars("\u{009f}"), "\\x9f");
        // TAB passes through
        assert_eq!(escape_control_chars("\t"), "\t");
        // Printable ASCII passes through
        assert_eq!(escape_control_chars("hello"), "hello");
        // Multibyte (non-C1) passes through
        assert_eq!(escape_control_chars("→"), "→");
        // Mixed
        assert_eq!(escape_control_chars("ab\x1bcd"), "ab\\x1bcd");
    }

    #[test]
    fn escape_control_chars_empty() {
        assert_eq!(escape_control_chars(""), "");
    }

    // ── New rows: bidi embedding/override ────────────────────────────────────

    #[test]
    fn escape_bidi_embedding_override() {
        // LRE U+202A
        assert_eq!(escape_control_chars("\u{202a}"), "\\u202a");
        // RLE U+202B
        assert_eq!(escape_control_chars("\u{202b}"), "\\u202b");
        // PDF U+202C
        assert_eq!(escape_control_chars("\u{202c}"), "\\u202c");
        // LRO U+202D
        assert_eq!(escape_control_chars("\u{202d}"), "\\u202d");
        // RLO U+202E
        assert_eq!(escape_control_chars("\u{202e}"), "\\u202e");
    }

    // ── New rows: bidi isolates ───────────────────────────────────────────────

    #[test]
    fn escape_bidi_isolates() {
        // LRI U+2066
        assert_eq!(escape_control_chars("\u{2066}"), "\\u2066");
        // RLI U+2067
        assert_eq!(escape_control_chars("\u{2067}"), "\\u2067");
        // FSI U+2068
        assert_eq!(escape_control_chars("\u{2068}"), "\\u2068");
        // PDI U+2069
        assert_eq!(escape_control_chars("\u{2069}"), "\\u2069");
    }

    // ── New rows: implicit bidi marks (ALM, LRM, RLM) ────────────────────────

    #[test]
    fn escape_bidi_implicit_marks() {
        // LRM U+200E
        assert_eq!(escape_control_chars("\u{200e}"), "\\u200e");
        // RLM U+200F
        assert_eq!(escape_control_chars("\u{200f}"), "\\u200f");
        // ALM U+061C
        assert_eq!(escape_control_chars("\u{061c}"), "\\u061c");
    }

    // ── New rows: line/paragraph separators ──────────────────────────────────

    #[test]
    fn escape_line_paragraph_separators() {
        // LS U+2028
        assert_eq!(escape_control_chars("\u{2028}"), "\\u2028");
        // PS U+2029
        assert_eq!(escape_control_chars("\u{2029}"), "\\u2029");
    }

    // ── New rows: zero-width characters ──────────────────────────────────────

    #[test]
    fn escape_zero_width_chars() {
        // ZWSP U+200B
        assert_eq!(escape_control_chars("\u{200b}"), "\\u200b");
        // ZWNJ U+200C
        assert_eq!(escape_control_chars("\u{200c}"), "\\u200c");
        // ZWJ U+200D
        assert_eq!(escape_control_chars("\u{200d}"), "\\u200d");
        // Word Joiner U+2060
        assert_eq!(escape_control_chars("\u{2060}"), "\\u2060");
        // ZWNBSP/BOM U+FEFF
        assert_eq!(escape_control_chars("\u{feff}"), "\\ufeff");
    }

    // ── Boundary passthroughs (must NOT be escaped) ───────────────────────────

    #[test]
    fn passthrough_boundary_chars() {
        // U+200A hair space — not in escape set
        assert_eq!(escape_control_chars("\u{200a}"), "\u{200a}");
        // U+2010 hyphen — not in escape set
        assert_eq!(escape_control_chars("\u{2010}"), "\u{2010}");
        // U+2027 hyphenation point — not in escape set (boundary before LS range)
        assert_eq!(escape_control_chars("\u{2027}"), "\u{2027}");
        // U+202F narrow no-break space — not in escape set (boundary after RLO range)
        assert_eq!(escape_control_chars("\u{202f}"), "\u{202f}");
        // U+205F math space — not in escape set
        assert_eq!(escape_control_chars("\u{205f}"), "\u{205f}");
        // U+2065 — not in escape set (boundary before LRI range)
        assert_eq!(escape_control_chars("\u{2065}"), "\u{2065}");
        // U+206A — not in escape set (boundary above LRI/PDI range U+2066-U+2069)
        assert_eq!(escape_control_chars("\u{206a}"), "\u{206a}");
        // U+FFFD replacement character — not in escape set
        assert_eq!(escape_control_chars("\u{fffd}"), "\u{fffd}");
        // Astral char U+1F600 (emoji) — not in escape set
        assert_eq!(escape_control_chars("\u{1f600}"), "\u{1f600}");
        // TAB — explicitly excluded from C0
        assert_eq!(escape_control_chars("\t"), "\t");
    }

    // ── Mixed \xHH and \uXXXX in same string ─────────────────────────────────

    #[test]
    fn escape_mixed_xhh_and_uxxxx() {
        // \x1b (C0 ESC) + U+202E (RLO) + plain text
        assert_eq!(escape_control_chars("\x1b\u{202e}abc"), "\\x1b\\u202eabc");
        // C1 (\x80) + bidi mark (LRM) + tab (passthrough) + text
        assert_eq!(escape_control_chars("\u{0080}\u{200e}\tabc"), "\\x80\\u200e\tabc");
    }
}
