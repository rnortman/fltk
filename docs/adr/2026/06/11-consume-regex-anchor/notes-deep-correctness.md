# Deep correctness review — consume-regex-anchor

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Reviewed: `32a6c4e..097ea96`.

No findings.

Verification performed (not just diff-read):

- Equivalence of old (`find_at` + `m.start() != byte_pos` reject) vs new (`Anchored::Yes` + `Input::span(byte_pos..len)`): `regex` 1.12's `find_at` is itself an unanchored `meta::Regex` search over `Input::span(start..len)`, so `\A`/`^`/`$`/`\b`/`\B` context resolution goes through identical regex-automata code in both versions; the only delta is anchoring, and anchored matches contractually begin at `input.start()` with the same leftmost-first selection. Accepted-match sets and selected ends are identical.
- Config parity checked in vendored sources: `regex-1.12.3/src/builders.rs:53-54,76` sets `nfa_size_limit(Some(10<<20))`, `hybrid_cache_capacity(2<<20)`, `utf8_empty(true)`; `regex-automata-0.4.14/src/meta/regex.rs:3104,3135,3151` shows those are exactly `meta::Config`'s defaults. `meta::Regex::new(pattern)` is config-identical to `regex::Regex::new(pattern)`.
- `debug_assert_eq!(m.start(), byte_pos)` replacing the runtime reject is sound: under `Anchored::Yes` a non-span-start match is contractually impossible; the assert documents rather than guards.
- `pos == len`: `cp_to_byte[len]` sentinel = `text.len()`; `Input::span(len..len)` is valid and `utf8_empty` (default on in both old and new) preserves empty-match-can't-split-codepoint behavior. byte_pos is always a char boundary (cp_to_byte entries), so no empty-match-in-codepoint hazard at search start either.
- Byte→codepoint end conversion (`partition_point` + boundary `debug_assert`) unchanged.
- `meta::Regex` is `Send + Sync` — generated `OnceLock<Regex>` cells remain correct.
- `cargo test -p fltk-parser-core`: 30/30 terminalsrc tests pass, including new `consume_regex_context_before_pos` (`\B` sees pre-span context) and `consume_regex_empty_match_at_end`.
- Fixture lockfiles drop `regex` and retain `regex-automata 0.4.14`; generated parsers reference only the re-export. Consistent.

Out of lane, noted without finding: generated test panic message still says "not supported by the regex crate" while compiling via `regex_automata::meta::Regex` — same syntax/`regex-syntax` parser, so the message is not misleading in substance; wording is quality-reviewer territory.
