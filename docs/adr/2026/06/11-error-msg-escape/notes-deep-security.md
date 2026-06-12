# Security review — error-msg-escape

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 8da7924 (base ef8288c).

Scope checked: `crates/fltk-parser-core/src/errors.rs`, `crates/fltk-parser-core/src/lib.rs`, `fltk/fegen/pyrt/errors.py`, new/changed tests.

Verified sound (no findings):

- Escape sets byte-identical cross-backend: C0 except TAB, DEL, C1; `\xHH` lowercase two-digit. Rust `(cp <= 0x1F && cp != 0x09) || cp == 0x7F || (0x80..=0x9F)` ≡ Python predicate.
- The primary vector (ESC/ANSI, raw `\r` log forging) is closed; tests assert no raw controls survive in formatted output (both backends).
- `line_text` is the only untrusted-input flow into the message and is escaped end-to-end (prefix + suffix covers whole line). `Expected:` block (`py_repr_str`, rule names) is grammar-author-controlled — not the untrusted boundary; preexisting C1 divergence there is documented and out of scope per design.
- Rust slicing is codepoint-safe (`chars()` collect) and clamped (`split.min(chars.len())`) — no panic on out-of-range col; Python slicing inherently safe. `col == -1` corner preserved via `max(col, 0)`.
- Caret pad from escaped prefix, codepoint-counted both sides — no desync between rendered line and caret that could hide the error position.

## security-1

- **File:line:** `crates/fltk-parser-core/src/errors.rs:87-101` (`escape_control_chars`) and `fltk/fegen/pyrt/errors.py:59-73` (same function).
- **Issue:** Escape set stops at U+009F. Unicode bidi controls (U+202A–U+202E, U+2066–U+2069), line/paragraph separators (U+2028, U+2029), and zero-width characters pass through unescaped into the quoted error line.
- **Trust boundary / data flow:** Untrusted parse input → failing-line slice (`line_text`) → `escape_control_chars` → formatted error message → consumer's terminal / log / UI.
- **Consequence:** An attacker controlling parse input can (a) use RLO/bidi embedding to visually reorder the rendered error line in bidi-aware terminals and UIs — spoofing what the failing input appears to say and misaligning the caret's apparent target; (b) use U+2028/U+2029 to split log lines in viewers and JS-based log pipelines that treat them as line terminators — log forging, the same asset class the `\r` escape was added to protect. Conditions: consumer surfaces parse errors for untrusted input in a bidi-aware or U+2028-sensitive display/log path. Lower impact than the closed ESC vector (no command execution), but the log-forging variant is the same threat the fix targets.
- **Suggested fix:** Either extend the escape set to Unicode `Cf` format chars + U+2028/U+2029 (needs cross-backend pinning: Python would emit `‮`-style 4-digit escapes — representation must be specified, the existing two-digit `\xHH` no longer suffices), or record an explicit accepted-risk disposition. Note the design's escape-set widening was user-approved as C0+DEL+C1 only (design.md A1), so this is a scope-extension decision, not an implementation bug.

No other findings.
