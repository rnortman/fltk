Style: concise, precise, complete, unambiguous. No padding, no preamble.

# Judge verdict — deep review of error-msg-escape

Phase: deep. Base ef8288c..HEAD f72cb5d (supersedes prior verdict against intermediate 654d066; rework commit 6a13823 included). Round 1.
Notes: errhandling (no findings), correctness, security, test, quality, efficiency. `notes-deep-reuse.md` was listed as input but does not exist on disk; quality/efficiency notes cover that ground; treated as no-findings.
11 findings across 9 dispositions (quality-1/efficiency-1 and quality-2/efficiency-2 merged by responder; efficiency-3 split Fixed + TODO).
Verification: `cargo test` in `crates/fltk-parser-core` 55 passed (incl. 9 new escape/format tests); `uv run pytest tests/test_pyrt_errors.py` 15 passed; `tests/test_rust_parser_parity_fixture.py` 82 passed (incl. both new FAIL corpus entries).

## Added TODOs walk

### security-1 — TODO(error-msg-bidi-escape) at errors.rs:88-89 and errors.py:66-67
Q1 (worth doing): yes — U+2028/U+2029 log-splitting is the same asset class the `\r` escape closes; bidi reordering spoofs the rendered failing line. Real, lower-impact-than-ESC vector on the same untrusted-input flow.
Q2 (design/owner input required): yes — two-digit `\xHH` representation cannot encode ≥U+2028 (reviewer's own note); needs a new representation spec, cross-backend repinning of goldens/parity, and a scope extension beyond the user-approved C0+DEL+C1 bound (design.md A1). Genuine design cycle + owner sign-off.
Not iteration-created: passthrough of these codepoints is preexisting; this iteration strictly narrowed the raw-control surface. Both TODO comments present; `TODO.md` entry present with threat description.
Assessment: TODO acceptable.

### efficiency-3 (partial) — TODO(error-msg-escape-zero-copy) at errors.rs:90-91 and errors.py:68
Q1 (worth doing): plausibly — `escape_control_chars` is public cross-backend API; the remaining `to_owned()` copy on clean input is real, modest waste a `Cow<'_, str>` return would eliminate.
Q2 (design/owner input required): yes — changes a public Rust API signature (`String` → `Cow`); efficiency reviewer itself flagged the signature decision as one to keep deliberate. The non-signature-changing part (early-return fast path) was done now, not deferred — correct split.
Both TODO comments present; `TODO.md` entry present (renamed from `error-msg-escape-fast-path`, narrowed to the Cow variant).
Assessment: TODO acceptable.

## Other findings walk

### correctness-1 — Fixed
Claim: comment in `format_error_message_caret_alignment_with_escaped_prefix` derived `line_ends=[7], line_span=[0,7)` for the 6-codepoint string `"ab\x1bcd\n"`; consequence is maintainers extending the test from an arithmetically impossible derivation.
Diff at `errors.rs:387`: comment now reads `line_ends=[5], line_span=[0,5)="ab\x1bcd"`. Verified: `\n` at codepoint index 5; `"ab\x1bcd"` is 5 chars = `[0,5)`. Assertions unchanged (were already correct).
Assessment: fix correct and complete. Accept.

### test-1 — Won't-Do (finding incorrect)
Claim: Python no-raw-controls test input `"\x00\x01\x1b\r\x7fabc\n"` lacks any C1 codepoint, so the C1 branch of the `format_error_message` integration path is uncovered.
Rationale: U+009B is present in the source as raw UTF-8; the viewer rendered it invisibly.
Verified by hexdump of `tests/test_pyrt_errors.py:103`: bytes `c2 9b` (U+009B) sit between `\x7f` and `abc` — at HEAD **and** at the reviewed commit 8da7924. The finding's premise is false; coverage is symmetric with the Rust test (`\u{009b}` at `errors.rs:443`).
Assessment: responder right; finding is a false positive from byte-display ambiguity. Accept Won't-Do.

### test-2 — Fixed
Claim: `test_format_error_message_col_minus_one` and `test_format_error_message_empty_input` used only `startswith`/`in` smoke assertions; consequence is regressions on the line-text line going uncaught.
Diff at `tests/test_pyrt_errors.py:118-134`: both tests now assert full golden equality. col-minus-one golden `"Syntax error at line 1 col 0:\nab\n^\nExpected:\n"` — re-derived: col=-1 → header col 0; `"abc"` sentinel quirk → `line_span=[0,2)`, line_text `"ab"`; pad 0. Comment corrected to `line_span=[0,2)` in rework 6a13823. Empty-input golden likewise correct. Both pass.
Assessment: fix addresses the finding. Accept.

### test-3 — Fixed
Claim: design-specified edge case "error column at a control char" (caret on the `\` of its escape) untested in both backends.
Diff: `test_format_error_message_caret_at_control_char` added at `tests/test_pyrt_errors.py:87-97` and `errors.rs:398-412`. Line `"ab\x1bcd\n"`, col 2 (ESC): prefix `"ab"` → pad 2, asserts `lines[1] == "ab\\x1bcd"` and `lines[2] == "  ^"`. Matches reviewer's prescribed case exactly; both pass.
Assessment: accept.

### test-4 — Won't-Do
Claim: informational only — Rust table-test comment doesn't note `\n` is in-set but unreachable at the call site. Reviewer itself wrote "No action required for this item beyond noting it."
Assessment: nit with no consequence; reviewer pre-conceded. Won't-Do sound. Accept.

### quality-1 / efficiency-1 — Fixed
Claim: `Vec<char>` collect + two `String` collects to split at a codepoint index — three avoidable allocations and an obscured codepoint-index invariant; consequence is waste plus a latent byte-index-slice hazard for future maintainers.
Diff at `errors.rs:164-167`: `line_text.char_indices().nth(split).map_or(line_text.len(), |(b, _)| b)` then direct `&str` slices into `escape_control_chars`; comment states the codepoint-index invariant. `map_or(line_text.len(), ...)` reproduces the old `split.min(chars.len())` clamp (correctness reviewer established `col ≤ len(line_text)`, so the clamp is never lossy). Matches the reviewers' prescribed fix; all goldens and parity pass.
Assessment: accept.

### quality-2 / efficiency-2 — Fixed
Claim: `format!` temp `String` per escaped char in `escape_control_chars` and (pre-existing copy-source) `py_repr_str`; consequence is one allocation per control char in public API.
Diff: `write!(out, "\\x{:02x}", cp).unwrap()` at `errors.rs:106` (escape loop) and `errors.rs:246` (`py_repr_str`); `use std::fmt::Write as FmtWrite` added at `errors.rs:9`. Both sites converted as the reviewers asked.
Assessment: accept.

### efficiency-3 (Fixed part) — early-return fast path
Claim: both backends rebuilt control-free lines char-by-char — a common-case regression vs. the old direct slice; consequence is O(line) per-char cost on every formatted error.
Diff: Rust `if !s.chars().any(|c| needs_escape(c as u32)) { return s.to_owned(); }` (`errors.rs:99-101`) with `needs_escape` extracted and shared with the escape loop; Python `any(...)` pre-scan returning `text` unchanged (`errors.py:70-71`) — walrus short-circuit verified correct (`cp` assigned in first conjunct, reused by DEL/C1 checks). Output semantics unchanged; ASCII-clean goldens and parity pass.
Assessment: accept. (TODO remainder judged in TODOs walk above.)

## Disputed items

None.

## Approved

11 findings / 9 dispositions: 6 Fixed verified (correctness-1, test-2, test-3, quality-1/efficiency-1, quality-2/efficiency-2, efficiency-3 fast path), 2 Won't-Do sound (test-1, test-4), 2 TODOs acceptable (error-msg-bidi-escape, error-msg-escape-zero-copy).

---

## Verdict: APPROVED

All dispositions acceptable; fixes verified against HEAD f72cb5d by code inspection and test execution (cargo 55 pass, pytest unit 15 pass, parity 82 pass).
