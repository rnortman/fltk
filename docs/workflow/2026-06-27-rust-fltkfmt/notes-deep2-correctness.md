# Correctness review — deep pass 2 (increments 4-6)

Commit reviewed: 0718645d66cec435752a28094f0cd7631712b058
Base: 762bbced1f5b44de2ad507db3a18a653c2ca585a
Scope: `crates/fltk-fmt-cli/src/lib.rs` (`run_main`, `run_inner`, `validate`,
`write_atomic`, `fully_consumed`, `fltk_formatter_main!`), `crates/fltkfmt/`.

## correctness-1

- **File:line**: `crates/fltk-fmt-cli/src/lib.rs:219-231` (the `fltk_formatter_main!`
  macro's parse → unparse pipeline).

- **What's wrong**: After `parser.$parse(0)` returns `Some`, the macro proceeds straight
  to the `fully_consumed` check and then unparses the tree. It never calls
  `parser.depth_exceeded()`. The parser-core contract requires that check.
  `crates/fltk-parser-core/src/memo.rs:158-164` states verbatim: *"Callers must check
  `depth_exceeded()` after parsing and discard the result if set — a result produced with
  the flag set is not the parse the grammar defines (e.g. a left-recursive rule's seed can
  surface as `Some` even when growth iterations were depth-rejected)."* The generated
  parser exposes `pub fn depth_exceeded(&self)` precisely for this (`parser.rs:117`, emitted
  for every grammar by `fltk/fegen/gsm2parser_rs.py:447`).

- **Why**: The depth limit can be hit on deeply nested / pathological / adversarial input.
  When it is, `apply__parse_grammar` does **not** reliably return `None`: per the contract
  above, a left-recursive rule's seed (the fegen grammar's `alternatives`/`items` are
  recursive) can surface as `Some` with a *wrong* CST. The macro's only depth-aware exit is
  indirect: if the wrong parse leaves non-whitespace unconsumed, `fully_consumed` returns
  false → `parser.error_message()` → which special-cases `depth_exceeded()`
  (`parser.rs:94-99`) and reports the limit → exit 2. But when the wrong/partial parse still
  reaches the end of input (`parsed.pos == src.chars().count()`, or only whitespace remains),
  `fully_consumed` returns true and the macro silently unparses the wrong tree. The Python
  backend — the path CLAUDE.md requires the Rust backend to stay behaviorally equivalent to —
  does the opposite: its generated apply binding checks `depth_exceeded()` *before* inspecting
  `Some`/`None` and raises `PyRecursionError` regardless
  (`fltk/fegen/gsm2parser_rs.py:991-996`).

- **Consequence**: For an input that drives the packrat parser past `max_depth`
  (`DEFAULT_MAX_DEPTH` = 1000) yet yields a fully-consuming `Some`, `fltkfmt` produces
  formatted output derived from a tree that "is not the parse the grammar defines" and exits
  `0` — silent wrong output. Under `--in-place` this overwrites the user's source file with
  the corrupted reformatting (the atomic write faithfully commits the wrong bytes), i.e.
  silent data corruption rather than the intended exit-2 error. It also diverges from the
  Python formatter, which errors on the same input.

- **Suggested fix**: In the macro, immediately after binding `parsed = parser.$parse(0)`
  (and on the `None` arm too, though `error_message()` already covers that), check
  `parser.depth_exceeded()` and, if true, return
  `Err(parser.error_message())` (which already renders the depth-limit diagnostic) before any
  `fully_consumed`/`read()`/unparse step. This restores the documented contract and matches
  the Python binding's unconditional depth check.

## Other areas examined — no finding

- `fully_consumed` (`lib.rs:74-79`): char-index arithmetic, the `pos < 0` guard, and the
  past-end vacuous-true behavior are all correct and consistent with `parsed.pos` being an
  `i64` char index (`memo.rs:19-21`; fixture asserts `parsed.pos == src.chars().count()`).
- `validate` flag matrix (`lib.rs:89-115`): `--in-place`+`--output`, `--in-place`+`--check`,
  `--in-place`+no-file, `--in-place`+`-`, and `--output`+multi-input are all rejected
  correctly; the stdin-counts-as-one logic for `--output` is right. (`--check`+`--output`
  silently lets `--check` win via branch order in `run_inner`, but the design deliberately
  does not list it as a conflict, so this is intended, not a bug.)
- `write_atomic` (`lib.rs:120-150`): temp-in-same-dir + rename is atomic on POSIX; temp name
  is per-(dir, basename, pid) so no collision across the files of one invocation; temp is
  removed on both write and rename failure (no leak); no-parent and no-file-name paths handled.
- `run_inner` (`lib.rs:255-347`): source ordering, per-input continue-on-error, and the
  worst-of-`{2,1,0}` exit-code aggregation are correct; `--check` compares against the raw
  file content and writes nothing; stdin display name and `filename: None` are wired
  correctly.
- Macro borrow/mutability shape (`lib.rs:219-241`): `mut parser`, the owned `ApplyResult`
  (no parser borrow), `parsed.result.read()` guard lifetime across `unparse`, and
  `&*guard: &cst::Grammar` matching `unparse_grammar(&cst::Grammar)` are all sound; the
  end-to-end smoke test in the log confirms it links and runs.
