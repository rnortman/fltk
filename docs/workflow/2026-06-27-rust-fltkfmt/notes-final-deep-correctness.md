# Deep correctness review — rust-fltkfmt

Commit reviewed: f89c80930a8799aaf476077b572fea449e3024d2 (base 6f975ebf3e4e102c256397337a5d11a21cc1ab7f)
Scope: product files only (workflow records under docs/workflow/2026-06-27-rust-fltkfmt/ excluded).
Deferred TODO(fltkfmt-integration-tests) not flagged.

No findings.

Traced and cleared:
- `fltk-fmt-cli/src/lib.rs` `validate`: all flag-conflict branches consistent with dispatch
  order in `run_inner` (check > in_place > output > stdout); `--output` count logic
  (1 when files empty, else len) rejects multi-input correctly; stdin (`-`) + in_place rejected.
- `fully_consumed`: negative pos guarded before `as usize` wrap; past-end vacuously true;
  char-index (not byte) scan; matches its unit tests.
- `run_inner`: worst-of exit-code accumulation (2>1>0), per-source continue-on-error,
  in_place skip-when-unchanged, stdin-once iteration, display-name/filename plumbing all correct.
- `write_atomic`/`create_temp`: O_EXCL temp in same dir, perms copied from original,
  temp removed on write/rename failure, original left intact (verified by tests incl. EISDIR path).
- `fltk_formatter_main!` macro: depth_exceeded checked before inspecting Some/None (matches
  parser-core memo contract and Python RecursionError parity); partial-parse rejected via
  fully_consumed; unparse-None mapped to internal error; `parsed.result` (owned Shared/Arc)
  does not borrow `parser`, so post-parse `error_message()` calls are sound. API signatures
  (`apply__parse_grammar`, `depth_exceeded`, `error_message`, `ApplyResult.pos/.result`,
  `Shared::read`, `UnparseResult::doc`, `Renderer::render`, `RendererConfig`) all verified.
- Generator change in `gsm2unparser_rs.py` (`match`+`_=>{}` → `if let`, incl. or-patterns in
  `_has_preservable_trivia` and the single-vs-multi-variant split in `_count_newlines_in_trivia`)
  is semantically equivalent; committed `crates/fegen-rust/src/unparser.rs` reflects it.
- The `unparse__trivia`-None drop (no `else` arm) is pre-existing behavior; this diff only
  added a TODO comment above it — no behavior change introduced here.
