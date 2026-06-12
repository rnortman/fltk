# Request: error-msg-bidi-escape — extend error-message escaping to bidi/invisible chars; fix divergent third copy

Style: concise, precise, no padding, no preamble. Self-contained; downstream agents see only this dir. Validated exploration: `exploration.md` (same dir) — adequate; skip the explore phase and proceed to requirements.

## Type of work

Security hardening across both backends, in two parts. User-approved direction (flagged: do not second-guess): **do both parts (a) and (b) as one project** — this is the reframed version of the original TODO, which covered only part (b).

## Background

Parse-error messages quote the failing input line. `escape_control_chars` sanitizes that quote, but the escape set stops at U+009F (C0 except TAB, DEL, C1). Verified at HEAD 5d94733:

- Canonical Rust: `crates/fltk-parser-core/src/errors.rs:94-113` (`needs_escape`: `(cp <= 0x1F && cp != 0x09) || cp == 0x7F || (0x80..=0x9F)`), representation `\xHH` (two hex digits, codepoint scalar).
- Python: `fltk/fegen/pyrt/errors.py:52-79` — identical logic and representation.
- Cross-backend pinning is by duplicated literal strings, not a shared spec: Rust unit tests at `errors.rs:338-362`, Python at `tests/test_pyrt_errors.py:13-47` (header comment declares the cross-pin), parity comparator `tests/parser_parity.py:99-116` asserts byte-equal headers. Original escape decision: `docs/adr/2026/06/11-error-msg-escape/design.md` (esp. l.33: "all escaped codepoints are ≤ U+009F, so two digits always suffice").

**Problem 1 (part b — the original TODO):** bidi overrides (U+202A–U+202E, U+2066–U+2069), line/paragraph separators (U+2028, U+2029), and zero-width chars pass through unescaped. Attacker-controlled parse input can visually reorder the rendered error line in bidi-aware terminals/UIs or split log lines in viewers treating LS/PS as terminators. Same asset class as the previously closed ESC-injection vector, lower severity. Source line-splitting uses only `\n` in both backends (`terminalsrc.py:190`, `terminalsrc.rs:198`), so these chars reach `escape_control_chars` inline — verified.

**Problem 2 (part a — found during validation, worse than the TODO knew):** a third, private, divergent copy exists: `escape_control_chars_for_msg` at `crates/fltk-cst-core/src/cross_cdylib.rs:123-138`, used for type/attribute names in CST-bridge error messages. Divergences from canonical:
1. Escapes TAB (no `cp != 0x09` exclusion).
2. Encodes C1 chars as per-UTF-8-byte escapes (`\xc2\x80` for U+0080) instead of one codepoint escape (`\x80`).
3. Its comment (l.128-129) claims single-`\xHH`-per-codepoint behavior — the comment is wrong.
4. Zero test coverage.

## Fix shape (user-approved direction)

**(a)** Bring the `cross_cdylib.rs` copy into line with canonical behavior and fix the wrong comment. Whether to deduplicate code or keep a pinned-by-tests copy is a design decision: note `fltk-cst-core` and `fltk-parser-core` are separate crates — the design must respect existing dependency direction and must not invent a new cross-crate dependency solely for this. Add test coverage for this function either way.

**(b)** Extend the escape set in BOTH backends to: bidi controls U+202A–U+202E and U+2066–U+2069, line/paragraph separators U+2028/U+2029, and zero-width characters (exact zero-width set — e.g. U+200B–U+200F, U+FEFF — is a requirements/design decision; pick deliberately and document). This forces a new escape spelling for codepoints > 0xFF since `\xHH` is two digits; something like `\u{XXXX}` (exact spelling is a design decision, but it must be identical across backends). Existing `\xHH` output for the current C0/DEL/C1 set should be preserved unless the design argues otherwise (changing it churns every pinned test literal and downstream-visible message text for no gain).

## Load-bearing constraints

- Cross-backend byte-identical output is a pinned project property: Rust and Python `escape_control_chars` must produce identical strings for identical input. All three pin points must be repinned together: `errors.rs` unit tests, `tests/test_pyrt_errors.py`, `tests/parser_parity.py` corpus.
- Known interaction (verified): the parity comparator uses Python `str.splitlines()` (`tests/parser_parity.py:56`), which treats U+2028/U+2029 as line terminators — today an unescaped LS/PS in a quoted line would distort the comparison's line structure. After part (b), escaped output contains no raw LS/PS, dissolving the hazard; a test should cover this case.
- Error-message text is downstream-visible behavior (CLAUDE.md: out-of-tree consumers). Escaping *more* characters is the deliberate, called-out change here; do not change anything else about message format.
- TAB remains unescaped in canonical line-quoting behavior (deliberate, pre-existing); part (a) aligns the third copy to canonical, which includes the TAB exclusion.

## Non-goals

- No new escaping for other Unicode ranges (confusables, etc.).
- No changes to error-message structure, caret placement logic, or line-splitting semantics.
- No public API signature changes (`escape_control_chars` stays `&str -> String`; see rejected TODO `error-msg-escape-zero-copy`).

## Verification expectations

- TDD per CLAUDE.md: failing tests first.
- New cross-pinned tests in both backends for every newly escaped codepoint class (bidi, LS/PS, zero-width), plus parity-corpus FAIL entries exercising bidi chars end-to-end through real parse errors.
- Tests for `escape_control_chars_for_msg` covering TAB, C1, and the new set.
- Full suite: `uv run --group dev maturin develop && uv run pytest`; `make check` clean.
- On completion remove the TODO: `TODO.md` entry `error-msg-bidi-escape` and `TODO(error-msg-bidi-escape)` code comments at both cited locations (`errors.rs`, `errors.py`).
