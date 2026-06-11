# Dispositions: design review round 1 — Rust Parser Codegen

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Findings from `notes-design-design-reviewer.md`, fact-checked against source at 5d05d7f. All eight verified accurate; all eight Fixed in `design.md`.

design-1:
- Disposition: Fixed
- Action: §3.1 `TerminalSource` bullet rewritten — `TerminalSource` holds the `SourceText` (single owner; `Arc<SourceInner>` confirmed at span.rs:58-66) and derives the codepoint table from it; spans are built against `&SourceText` obtained from the `TerminalSource`. §3.2 parser-fields sentence updated to match (no separate `SourceText` field).
- Severity assessment: Verified — `SourceText` wraps `Arc<SourceInner>` holding the full text, so the original design doubled peak memory and permitted span-source/parsed-text mismatch. Real correctness+memory defect.

design-2:
- Disposition: Fixed
- Action: §3.1 `consume_regex` respecified as `Regex::find_at(full_text, byte_pos)` + `match.start() == byte_pos` (the `regex` crate's `find_at` preserves look-behind context for `\b`/`\B` and matches Python's pos-is-not-slicing `^` semantics); §4 regex-drift bullet extended to record why slicing was rejected.
- Severity assessment: Verified — terminalsrc.py:177-181 uses `re.match(pos=pos)`, which keeps full-string context; the slice design silently diverged for `\b`/`\B` patterns in out-of-tree grammars, uncatchable by the in-tree parity corpus. Highest-impact finding of the round.

design-3:
- Disposition: Fixed
- Action: §3.1 regex-handling bullet — `fltk-parser-core` does `pub use regex;`; generated code references `fltk_parser_core::regex::Regex` exclusively; consumers need no direct `regex` dep, version coherence structural.
- Severity assessment: Verified — `&Regex` across crates with independently resolved `regex` versions is a type mismatch; out-of-tree consumers (the primary audience per CLAUDE.md) would hit confusing compile errors.

design-4:
- Disposition: Fixed
- Action: §3.1 — out-of-range `pos` in any `consume_*` returns `None`, never panics. §4 Panics bullet restated as a contract covering pure-Rust entry points (parse failure on bad pos; Python boundary additionally raises `ValueError`); §4 i64 bullet updated to reference the bounds-checked lookup.
- Severity assessment: Verified — the prior text validated only at the Python boundary while declaring a no-panic posture, leaving the first-class pure-Rust entry undefined; unwind-across-cdylib abort is a real consumer-facing failure.

design-5:
- Disposition: Fixed
- Action: §3.3 adds `error_position() -> int | None` (farthest-failure codepoint position) to `PyParser`; §5 item 3 now asserts position equality via that accessor plus `error_message()` equality.
- Severity assessment: Verified — test plan item 3 was unimplementable against the §3.3 API without string-scraping; one scalar getter resolves it without exposing tracker internals.

design-6:
- Disposition: Fixed
- Action: §3.1 parenthetical reworded — generation-time validation from Python is deferred (requires a `regex` dep + `fltk._native` binding), not impossible.
- Severity assessment: Accurate but minor — record-quality defect in the future ADR rationale; no behavioral impact.

design-7:
- Disposition: Fixed
- Action: §3.2 result-types bullet reworded — by-value return; parent `extend_children(&result)` Arc-clones children; local dropped. (Signature `extend_children(&mut self, other: &Self)` confirmed, tests/rust_cst_fegen/src/cst.rs:339.)
- Severity assessment: Accurate — "consumes" misdescribed a borrowing API and could have steered an implementer toward a wrong ownership variant; wording-level fix.

design-8:
- Disposition: Fixed
- Action: §2 opening reworded — synthesis.md made no recommendation (confirmed, synthesis.md:3); Path 1 was Analysis 1's recommendation, presented as the lowest-LoC option.
- Severity assessment: Accurate but minor — misattribution in a decision record; LoC figures quoted were correct.

Post-fix, design.md was re-passed through cleanup-editor; one residual ambiguity in §3.3 tightened.
