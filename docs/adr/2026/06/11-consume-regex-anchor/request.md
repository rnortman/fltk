# Request: anchored regex matching in consume_regex

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Bug fix (complexity-DoS) in the Rust parser runtime + generated-code regex table.

**Origin:** TODO.md slug `consume-regex-anchor`, user-approved triage (`docs/adr/2026/06/11-todo-burndown/triage.md` item 1, USER DECISION: Do).

## Background

`consume_regex` (`crates/fltk-parser-core/src/terminalsrc.rs:154`) uses `regex::Regex::find_at(text, byte_pos)`, which is unanchored: on a non-match at `byte_pos` it scans the rest of the haystack before failing; the start-position check at `terminalsrc.rs:155-158` then discards forward matches — correctness is fine, but the scan cost is already paid. Worst case O(rules × n²) CPU (packrat bounds calls to O(R×N); each failing call can cost O(N)). Python's `re.match(pos=...)` anchors and fails immediately. Complexity DoS for untrusted input.

Validation findings (see `exploration.md` in this dir):
- Fix verified feasible: `regex_automata::meta::Regex` with `Input::new(text).anchored(Anchored::Yes).span(byte_pos..text.len())` — anchored rejection with the full haystack still visible, preserving `\b`/`\B` resolution at `byte_pos > 0`. (The TODO's "look-behind" wording is a misnomer; the `regex` crate has no look-behind. `\b`/`\B` is the real concern — see `terminalsrc.rs:133` comment.)
- No within-`regex`-crate fix exists: `\A` anchors to haystack byte 0, not span start.
- `regex-automata 0.4.x` is already a transitive dep (via `regex = "1"`); must be added as a direct dep of `fltk-parser-core`.
- Generated-code ripple: `gsm2parser_rs.py:271` emits `use fltk_parser_core::regex::Regex;`; `gsm2parser_rs.py:307-317` emits `REGEX_CELLS: [OnceLock<Regex>; N]` and `regex_at(idx)`. The regex type in `consume_regex`'s signature, the re-export, the cells, and the construction sites all change together.

## Fix shape

Switch `consume_regex` to `regex_automata::meta::Regex` with an anchored span search. Update `fltk-parser-core`'s re-export and `gsm2parser_rs.py`'s emitted type/construction accordingly. Regenerate fixtures.

## Constraints / non-goals

- Parse results must be byte-identical to before (only wasted scan work is eliminated). The Python backend is untouched.
- Pattern syntax compatibility: `meta::Regex` supports the same syntax as `regex::Regex`; design should confirm flag/config parity (unicode, etc.) so existing grammar regexes compile identically.
- This changes types inside the generated parser file and `fltk-parser-core`'s API; it does NOT change any Python-visible or CST-node API surface.

## Verification expectations

- All existing tests incl. parity corpus pass unchanged (behavioral equivalence).
- New test pinning anchored semantics: a pattern that matches later in the input but not at `byte_pos` fails (already true today — keep as regression guard) — plus, if cheap, a coarse perf demonstration is welcome but NOT required as an assertion (no flaky timing tests).
- Regenerate generated fixtures; `make fix`; `uv run pytest` + `cargo test` clean.
