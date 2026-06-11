# Dispositions: design review round 1 — Phase 2 Rust Parser Generator

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Design: `design.md` (this directory). Notes: `notes-design-design-reviewer.md`. All three findings
fact-checked against source and confirmed accurate before disposing.

---

design-1:
- Disposition: Fixed
- Action: Added `source_name: str | None = None` constructor parameter (§2.1) and respecified the
  header (§2.2 item 1): CLI passes the grammar file name; `None` omits the "from `<source_name>`"
  clause so unit tests constructing from in-memory GSM need no fake filename.
- Severity assessment: Without the fix the implementer must either drop the filename (diverging from
  the design text and leaving §4.1's structural assertions ambiguous) or invent an unplanned
  constructor parameter mid-implementation. Confirmed: §2.1 carried no filename parameter and the
  `RustCstGenerator` precedent emits none.

design-2:
- Disposition: Fixed
- Action: §2.2 item 2 now makes `use std::sync::OnceLock;` and `use fltk_parser_core::regex::Regex;`
  conditional under the same predicate as the regex table, notes all other imports are
  unconditionally used, and records the zero-regex reachability argument (custom literal-only
  `_trivia` suppresses default injection, gsm.py:380-401; `\s+` enters only via trivia-rule
  separators, gsm2parser.py:641-650 — both verified against source).
- Severity assessment: For a zero-regex grammar the generated file would fail the design's own
  `-D warnings` clippy gate via `unused_imports`, violating the §2.7 invariant that generated `.rs`
  is clippy-clean under both lanes.

design-3:
- Disposition: Fixed
- Action: Restated the §3 out-of-range/negative-`pos` bullet as "never panics, never indexes out of
  bounds; non-nullable rules return `None`; nullable rules return `Some` with an empty span at any
  `pos`, identical to Python" (citing the `min == ZERO` no-progress-check emission,
  gsm2parser.py:581-585 — verified). §4.3 test scope split accordingly: assert `None` on a
  non-nullable rule, assert the empty match on a nullable rule (pinning Python-equivalent behavior).
- Severity assessment: A test implementing the old §4.3 literally against a nullable rule fails, or
  worse, the implementer "fixes" the generator to reject out-of-range `pos` and diverges from
  Python. The fixture grammar deliberately contains `?`/`*` items, so the ambiguity was live.
