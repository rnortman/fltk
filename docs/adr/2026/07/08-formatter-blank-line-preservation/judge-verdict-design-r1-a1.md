# Judge verdict — design review

Phase: design. Doc: `docs/adr/2026/07/08-formatter-blank-line-preservation/design.md` (revised in place). Round 1.
Notes: `notes-design-design-reviewer-r1.md` — 3 findings, all dispositioned Fixed.

Ground-truth spot checks against the checkout (all pass):
- `fmt_config.py` `_process_trivia_preserve_statement` replaces `config.trivia_config = TriviaConfig(preserve_node_names=node_names)` while `_process_preserve_blanks_statement` mutates in place — the 1a clobbering asymmetry is real. `TriviaConfig.preserve_blanks: int = 0` with the docstring §4 cites.
- `examples/gear/gear.fltkfmt` lists `preserve_blanks: 1;` before `trivia_preserve: LineComment;` — the clobbered order.
- `examples/gear/gear.fltkg:45-47`: `_trivia := ( ws | line_comment )+ ;` / `ws := chars:/\s+/ ;` / `line_comment := ... . nl:"\n" ;` — node-wrapped whitespace and the comment-terminator trap are both as described.
- Python generator emits an `is_span` conditional (direct-span-only counting); Rust generator matches only the `Span` variant of the `TriviaChild` enum — the 1b blindness exists in both backends.
- `pyrt.py` has the `count_span_newlines`/`is_span` delegation pattern Component B extends; Rust CST nodes expose `span()` (`gsm2tree_rs.py`), so the mirrored Rust arm is expressible.

## Findings walk

### design-1 — Fixed
Claim: implementing the design exactly leaves the pinned test `test_formatting_preserves_blank_lines_between_items` red — the generated `_count_newlines_in_trivia` counts only direct `Span` children, and gear's blank lines live in `Ws` node children. Consequence: the design's own acceptance criterion is unmet; an implementer ships a half-fix. Execution-backed by the reviewer.
Revised design: §1b documents the node-wrapped-whitespace defect with the verified evidence chain (including why fegen-shaped grammars mask it and why idempotency tests can't catch it); §2 Component B specifies whitespace-aware counting for **both** generators — Python via a pyrt helper following the existing delegation pattern, Rust via per-variant match arms over `span().text_str()` with a whitespace-only guard — and explicitly handles the `line_comment` terminator trap the reviewer flagged ("nodes containing any non-whitespace contribute nothing"; degrades to today's behavior, never over-counts). §2 "End-to-end verification" records the full two-component prototype turning all four blank-line assertions green, preserving the leading comment, staying idempotent, reparsing — and that component A alone was re-run and confirmed insufficient.
Assessment: the finding's substance (second component + comment-terminator care + run the fixed pipeline before sign-off) is fully incorporated, with the runtime-vs-generation-time classification judgment call stated and justified. Accept.

### design-2 — Fixed
Claim: no engine-level test in either backend covers nested-trivia (`Trivia → Ws → Span`) newline counting; a Python-only fix or later regression would pass the whole engine suite, and a Rust divergence would be invisible. Consequence: cross-backend equivalence goal untested for gear-shaped grammars.
Revised design: §5 item 5 adds Python rendering tests on a custom-trivia grammar exactly of the shape the reviewer prescribed, config from parsed text — 5a pins blank survival (fails today via 1b alone, even non-clobbering order), 5b pins that an unpreserved comment's terminator newline is not counted as blank-line evidence; item 6 adds pyrt helper unit tests (span / whitespace node / comment node / empty-span node); item 8 adds Rust generated-source pins for the whitespace-only node arm extending the existing `test_count_newlines_in_trivia_*` tests. §3 now scopes item 7 honestly: it pins only component A's reach into the Rust generator; items 5/8 pin component B per backend — exactly the over-claim the reviewer called out.
Assessment: coverage gap closed in both backends and at the helper level; the mis-scoped pin claim corrected. Accept.

### design-3 — Fixed
Claim: "generators untouched", "by construction cannot diverge", and §4's statement-order-only impact analysis are invalidated once the fix touches both generators; the ADR would record a false rationale and omit an affected out-of-tree consumer class.
Revised design: §2 "What is deliberately NOT changed" now confines the untouched claim to the branch-emission ladders, trivia-rule branch, resolver, and server — the generators change only inside `_gen_count_newlines_in_trivia_method` and its Rust mirror. §3 restates equivalence as "shared config layer (component A, identical by construction) + mirrored generator change (component B, parity comments + mirrored tests)". §4 now enumerates consumer class (a) (statement-order clobbering) and class (b) (custom-trivia grammars with `preserve_blanks > 0`, order-independent), argues both are documented directive semantics being delivered (docstring at `fmt_config.py:55-58` verified), and notes `_count_newlines_in_trivia` is private to the generated unparser — no symbol/annotation churn, consistent with the CLAUDE.md out-of-tree API policy.
Assessment: internal consistency restored; the impact analysis now covers the consumer class the fix actually affects. Accept.

## Notes beyond the findings

- §2 defers rule-level `preserve_blanks` as `TODO(rule-preserve-blanks)`. Rubric: Q1 yes — a parsed-but-unconsumed config field is a real gap worth closing (or removing); Q2 yes — consuming it means wiring rule-aware reads through both generators' branch emission, a mirrored design decision, and it is a pre-existing gap this iteration neither created nor worsened (gear uses no rule-level directive). Acceptable deferral; the design correctly pairs the TODO.md entry with code-site comments per the project TODO convention.
- The second adjacent gap (blank line split across a comment terminator on the unpreserved path) is explicitly *not* a TODO, with a sound rationale: no known grammar/config hits it and "done" needs a semantics decision. Consistent with the "no vague-aspiration TODOs" rule.
- §6 "Open questions: None" is now honest — the two judgment calls are resolved and argued in the body rather than hidden.

## Approved

3 findings: 3 Fixed verified (design rewritten around the two-part root cause; all reviewer-cited evidence re-verified against the checkout; prototype-backed end-to-end confirmation recorded in the design).

---

## Verdict: APPROVED

All three dispositions are correct and the revised design incorporates each finding's substance, not just its letter. No disputed items.
