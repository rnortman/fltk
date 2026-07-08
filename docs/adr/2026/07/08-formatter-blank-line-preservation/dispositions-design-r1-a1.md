# Dispositions — design review r1 (formatter blank-line preservation)

Design: `docs/adr/2026/07/08-formatter-blank-line-preservation/design.md` (revised in place)
Notes: `docs/adr/2026/07/08-formatter-blank-line-preservation/notes-design-design-reviewer-r1.md`

All three findings were independently fact-checked by execution before revising. Key
verifications: (1) both generators' `_count_newlines_in_trivia` count only direct `Span`
children (`gsm2unparser.py:1034-1049`; `gsm2unparser_rs.py:1525-1543`); (2) gear's whitespace is
a named `ws` node (`examples/gear/gear.fltkg:45-46`); (3) with `preserve_blanks = 1` forced onto
the parsed gear config (equivalent to the config fix), rendering still collapsed all blank lines
— the reviewer's residual-failure claim reproduces exactly; (4) a prototype of the proposed
second component (whitespace-only node counting, patched onto the generated gear unparser) made
all four blank-line assertions pass, preserved the leading comment, stayed idempotent, and the
output reparsed. Rust CST nodes expose `span()` (`gsm2tree_rs.py:1182`), so the mirrored Rust
change is expressible.

design-1:
- Disposition: Fixed
- Action: Design rewritten around the two-part root cause. New §1b documents the
  node-wrapped-whitespace blindness with the verified evidence chain; new §2 "Component B"
  specifies whitespace-aware counting in **both** generators (Python via a new pyrt helper
  following the `count_span_newlines`/`is_span` delegation pattern; Rust via per-variant match
  arms over `span().text_str()` with whitespace-only guard), including the comment-terminator
  trap the reviewer flagged (non-whitespace nodes contribute nothing). New §2 "End-to-end
  verification" records that the full fixed pipeline was prototyped and turns the pinned test's
  assertions green before sign-off, and that component A alone was confirmed insufficient.
- Severity assessment: Critical — as written, the design did not meet its own acceptance
  criterion; an implementer following it exactly would ship a half-fix with the pinned test
  still red. The reviewer's execution-backed analysis was accurate in every checked particular.

design-2:
- Disposition: Fixed
- Action: Test plan (§5) extended with nested-trivia coverage for both backends: item 5
  (Python rendering tests on a custom-trivia grammar, `_trivia := (ws | line_comment)+` with
  `ws := chars:/\s+/`, config from parsed text — 5a pins blank survival, 5b pins that comment
  terminator newlines don't manufacture phantom blanks), item 6 (pyrt helper unit tests), and
  item 8 (Rust generated-source pins for the whitespace-only node arm, extending
  `test_count_newlines_in_trivia_*`). §3 restated so each pin's scope is explicit — item 7
  (parsed-config Rust test) pins only component A's reach; items 5/8 pin component B per
  backend.
- Severity assessment: Without these, a Python-only fix or later regression in nested-trivia
  counting would pass the entire engine suite and surface only in the gear integration test,
  and a Rust-side divergence would be invisible entirely — contrary to the cross-backend
  equivalence goal.

design-3:
- Disposition: Fixed
- Action: §2 "What is deliberately NOT changed" reworded — the generators are now touched, but
  only inside `_gen_count_newlines_in_trivia_method` and its Rust mirror; the branch-emission
  ladders, trivia-rule branch, resolver, and server remain untouched. §3 restated as "shared
  config layer (component A, identical by construction) + mirrored generator change (component
  B, parity comments + mirrored tests)". §4 extended with consumer class (b): custom-trivia
  grammars with `preserve_blanks > 0` see blank lines start surviving after regeneration
  regardless of statement order — documented directive semantics delivered, still a bug fix,
  normal regen flow, no generated-symbol or annotation changes (`_count_newlines_in_trivia` is
  private to the generated unparser).
- Severity assessment: The ADR would have recorded a decision rationale ("config-only fix,
  generators untouched by construction") that is false for the change actually required, and
  the out-of-tree impact statement would have omitted an affected consumer class.
