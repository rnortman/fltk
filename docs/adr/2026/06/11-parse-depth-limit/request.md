# Request: parse depth limit (merged apply-depth-limit + parser-depth-limit)

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** New feature (safety limit) in the Rust parser runtime + generated-parser configuration surface.

**Origin:** TODO.md slugs `apply-depth-limit` and `parser-depth-limit`, merged into one work item per user-approved triage (`docs/adr/2026/06/11-todo-burndown/triage.md` item 2, USER DECISION: Do). This work resolves BOTH slugs.

## Background

Generated Rust parsers are recursive-descent. Recursion path: `apply__parse_X` → `apply` (`crates/fltk-parser-core/src/memo.rs:102`) → `parse_X` → alt/item helpers → `apply__parse_Y`. Depth is proportional to input nesting, unbounded. Stack overflow in the cdylib is SIGSEGV → uncatchable process abort. Python backend raises catchable `RecursionError` (CPython default ~1000 limit); Rust backend is strictly worse for untrusted input — a hard process-kill DoS.

Validation findings (see `exploration-apply-depth-limit.md`, `exploration-parser-depth-limit.md` in this dir):
- ALL cross-rule recursion flows through `apply` in `memo.rs` — verified; intra-rule helpers add only constant frames per level (~5 frames/level total). One counter in the runtime covers everything; no generated-wrapper counter needed.
- `PackratState` (`memo.rs:68-74`) has `invocation_stack` whose `.len()` approximates depth, but it briefly double-counts during left-recursion seed-growing (pushes at `memo.rs:200` and `memo.rs:247`); a dedicated `call_depth` counter is cleaner. `grow_seed`'s `rule(parser, start_pos)` call at `memo.rs:332` must also be covered.
- Zero configuration infrastructure exists: `PackratState::default()` is the only construction path; generated `Parser` struct (`gsm2parser_rs.py:329` `_gen_parser_struct`) has no config fields; `Parser::new`/`from_source_text` (`gsm2parser_rs.py:353-370`) take no limit param.
- No error channel exists: `apply` returns `Option<ApplyResult<T>>`; `None` = parse failure with no reason. `ErrorTracker` (`errors.rs:39-43`) is the natural place for a depth-exceeded flag.
- TODO.md cites `_gen_apply_wrapper`; actual method is `_emit_apply_wrapper` (`gsm2parser_rs.py:443`).

## Fix shape

- Dedicated depth counter + configurable `max_depth` in `PackratState`, checked in `apply` (covering the `grow_seed` path too). Default limit constant chosen by design (Python-equivalent ~1000 rule-depth is the natural baseline; ~5 Rust frames/level against 8 MiB stack gives wide margin).
- Depth-exceeded must surface **distinguishably** from "input doesn't match grammar" (error-tracker flag or equivalent — design decides exact channel) and must reach the Python binding as a catchable error, not an abort.
- Generated parser exposes limit configuration (constructor param or setter — design decides), threaded by `gsm2parser_rs.py`.
- Update the now-stale hazard warnings: `memo.rs:83-90` doc comment, generated-header template `gsm2parser_rs.py:258-263`.

## Constraints / non-goals

- Python backend behavior unchanged (RecursionError is the accepted Python-side behavior; do not add a Python-side limit).
- Cross-backend parity: a depth-exceeded failure is a new Rust-only failure mode. Design must consider the parity comparator (`tests/parser_parity.py`) — depth-exceeded should not be triggerable by the existing parity corpus (limit default far above corpus nesting).
- Out-of-tree consumers: additive API only; no renames of existing generated symbols.

## Verification expectations

- Test: parser with small configured limit returns a distinguishable failure (not abort) on input nested past the limit; same input parses fine with a larger limit.
- Test: default limit does not trip on existing test grammars/corpora.
- Cannot test the pre-fix abort (kills the test process) — do not try.
- Regenerate all generated fixtures; `make fix`; full `uv run pytest` + `cargo test` clean.
