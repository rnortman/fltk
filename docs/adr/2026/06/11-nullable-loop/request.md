# Request: nullable-repetition infinite-loop guard + validator gap fix

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Bug fix, BOTH backends (Python + Rust) in lockstep. TDD mandatory.

**Origin:** TODO.md slug `nullable-loop`, user-approved triage (`docs/adr/2026/06/11-todo-burndown/triage.md` item 3).

**USER DIRECTION (verbatim, binding):** "Do: start TDD (failing test first) and do both Python and Rust backends. If we cannot construct a grammar that tricks the current parsers then we should revisit whether this is real or not."

Consequence: the FIRST implementation step is constructing a grammar that demonstrably hangs (or would hang) the current parsers, as a failing test. If no such grammar can be constructed end-to-end, STOP and escalate to the user — do not proceed to the fix on theory alone.

## Background

`+`/`*` repetition loops have no per-iteration progress guard:
- Rust: `gsm2parser_rs.py:674-694` (`_gen_item_multiple`), TODO comment at 669-673.
- Python: `gsm2parser.py:555-603` (`gen_item_parser_multiple`), IIR `while_` loop.

If the repeated term matches empty at a fixed position, the loop never advances → infinite loop, 100% CPU.

A validator exists — `gsm.validate_no_repeated_nil_items` (`gsm.py:340-356`, called from `classify_trivia_rules` at `gsm.py:299`) — but validation found a hole (see `exploration.md` in this dir, §2-3): `Item.can_be_nil` (`gsm.py:108-111`) returns `self.quantifier.is_optional()`, ignoring the term entirely. So a sub-expression containing a REQUIRED-quantifier item whose term is nullable (e.g. `Regex(r"a*")`, empty literal, or a nil-able rule reference) passes validation. Candidate trigger: `rule := (r"a*" .)+` — outer item `ONE_OR_MORE` over a sub-expression whose single inner item is `REQUIRED` with term `Regex(r"a*")`; validator returns no error; `consume_regex` returns a zero-length match every iteration.

Also: grammars constructed directly as `gsm.Grammar` objects can bypass `classify_trivia_rules` entirely — the generators do call it (`gsm2parser.py:33`, `gsm2tree_rs.py:48` via `RustCstGenerator.__init__`), so the bypass concern applies only to unusual construction paths.

## Fix shape

1. **Failing test first** (per user direction): a grammar that passes current validation and hangs both current backends. Use a timeout mechanism so the test fails fast rather than hanging CI.
2. **Progress guard, both backends lockstep:** break/exit when an iteration consumes nothing. Critical placement detail (exploration §5): the check must compare BEFORE the `pos = one_result.pos` update — after it, the comparison is vacuously true and breaks every iteration. Rust: insert before `gsm2parser_rs.py:677`'s emitted assignment. Python: the IIR may not have a `break` construct (unverified — check `fltk/iir/model.py`); an early-return / equivalent form is acceptable if semantics match the Rust guard.
3. **Validator gap fix:** make the nullability check term-aware so `validate_no_repeated_nil_items` rejects these grammars at grammar time (the root fix; the loop guard is defense-in-depth). Design decides exact shape (e.g. `Item.can_be_nil` considering the term when quantifier is REQUIRED, or a dedicated deep check in the validator).

## Constraints / non-goals

- Cross-backend parity: guard must produce identical parse results in both backends for any grammar that reaches it. For currently-valid grammars the guard is a no-op (terms that always advance never trigger it) — exploration §6.
- Do not change parse results for any grammar accepted today and terminating today.
- Validator tightening is a behavior change for (broken) grammars that previously slipped through — that is the point; note it in the design.

## Verification expectations

- The TDD test: pre-fix demonstrably hangs/times out, post-fix passes (loop terminates AND/OR validator rejects — test both layers separately: guard behavior with validation bypassed or at generator level, validator rejection at grammar level).
- Existing full test suite (both backends) + parity corpus unaffected.
- `make fix`; `uv run pytest` + `cargo test` clean.
