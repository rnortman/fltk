# Judge verdict — design review

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Phase: design. Doc: `docs/adr/2026/06/10-rust-parser-codegen/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 8 findings, all dispositioned Fixed.

## Findings walk

### design-1 — Fixed
Claim: parser holds input text twice (`String` in `TerminalSource` + separate `SourceText`); consequence is doubled peak memory and constructible span-source/parsed-text mismatch.
Source check: `SourceText` is `Arc<SourceInner>` holding the text (span.rs:57-60) — duplication claim was real.
Doc now: §3.1 — `TerminalSource` "holds a `SourceText` (the single owner of the input text ...) plus a codepoint-index table derived from it. The parser's spans are built against `&SourceText` obtained *from* the `TerminalSource` ... no second copy." §3.2 parser-fields sentence updated to match (`TerminalSource` owns the `SourceText`; no separate field).
Assessment: fix matches the reviewer's proposed remedy exactly; both consequences (memory, mismatch) eliminated by construction. Accept.

### design-2 — Fixed
Claim: "slice + match at offset 0" is not equivalent to Python `re.match(pos=...)`; `\b`/`\B` see pre-`pos` context in Python but not in a slice; consequence is silent cross-backend divergence for out-of-tree grammars.
Source check: terminalsrc.py:177-181 confirmed — `re.compile(regex).match(self.terminals, pos=pos)`, full-string context.
Doc now: §3.1 — `Regex::find_at(full_text, byte_pos)` + `match.start() == byte_pos`, with the look-behind-context rationale and the perf-not-correctness caveat; §4 regex-drift bullet extended to record why slicing was rejected. `find_at` on the full haystack does preserve assertion context in the `regex` crate — the technical claim is sound.
Assessment: fix is the reviewer's first proposed remedy, fully specified. Accept.

### design-3 — Fixed
Claim: generated code naming `regex::Regex` forces every consumer crate to carry a version-coherent `regex` dep; consequence is type-mismatch compile errors for out-of-tree consumers.
Doc now: §3.1 — `fltk-parser-core` does `pub use regex;`; generated code references `fltk_parser_core::regex::Regex` exclusively; "consumer crates need no direct `regex` dependency and runtime/generated-code version coherence is structural."
Assessment: exactly the proposed fix; coherence now structural. Accept.

### design-4 — Fixed
Claim: no-panic posture contradicted by unvalidated `pos` at pure-Rust entry points; consequence is panic/unwind-across-cdylib for the first-class native API.
Doc now: §3.1 — "Out-of-range `pos` in any `consume_*` returns `None` (parse failure), never panics or indexes out of bounds." §4 Panics bullet restated as a contract covering native entry points (out-of-range/negative `pos` → `None`; Python boundary additionally raises `ValueError`); §4 i64 bullet references the bounds-checked lookup.
Assessment: contract is now stated, internally consistent, and covers both entry paths. Accept.

### design-5 — Fixed
Claim: §5 item 3 (parity on farthest-failure position) unimplementable against §3.3's string-only error surface; consequence is string-scraping or undesigned mid-implementation API addition.
Doc now: §3.3 adds `error_position() -> int | None` (farthest-failure codepoint position, `None` if no failure); §5 item 3 asserts position equality via that accessor plus `error_message()` equality.
Assessment: the reviewer's first proposed remedy, adopted; test plan item 3 now implementable. Accept.

### design-6 — Fixed
Claim: "generation-time validation is impossible from Python" overstated; `fltk._native` binding makes it a cost tradeoff; consequence is a durable ADR recording a cheap improvement as impossible.
Doc now: §3.1 parenthetical — "generation-time validation from Python is deferred — it would require adding a `regex` dependency and binding to `fltk._native`; the generated `#[test]` suffices."
Assessment: wording matches the proposed fix. Accept.

### design-7 — Fixed
Claim: `extend_children(&other)` does not "consume" the argument; consequence is an implementer designing a wrong by-value ownership variant.
Source check: `extend_children(&mut self, other: &Self)` at cst.rs:339 — borrows and Arc-clones children. Claim accurate.
Doc now: §3.2 — "the parent calls `extend_children(&result)`, which Arc-clones the children, and the by-value local is then dropped."
Assessment: rationale now describes the actual API. Accept.

### design-8 — Fixed
Claim: §2 misattributed Path 1 as the synthesis's recommendation; synthesis.md:3 says "No recommendations"; Path 1 was Analysis 1's.
Doc now: §2 — "The 2026-05-25 synthesis ... made no recommendation itself; it presented Path 1 (IIR backend, ... — Analysis 1's recommendation) as the lowest-LoC option ...".
Assessment: attribution corrected; LoC figures retained (reviewer confirmed them accurate). Accept.

## Disputed items

None.

## Approved

8 findings: 8 Fixed verified.

---

## Verdict: APPROVED

All eight dispositions are verified fixes applied in `design.md`; each addresses the reviewer's stated consequence at the cited section, and the three load-bearing source claims (SourceText `Arc` structure, Python `re.match(pos=...)` semantics, `extend_children` signature) check out against the code.
