# Dispositions — final deep QA pass (rust-fltkfmt)

Base: 6f975ebf3e4e102c256397337a5d11a21cc1ab7f
Reviewed HEAD: f89c80930a8799aaf476077b572fea449e3024d2

Verification run after fixes: `cargo test -p fltk-fmt-cli` (38 pass), `cargo clippy -p
fltk-fmt-cli --all-targets -D warnings` (clean), `cargo build` + `cargo clippy -D warnings`
for `crates/fltkfmt` (clean), `uv run pytest tests/test_rust_unparser_generator.py
fltk/unparse/` (577 pass), `uv run pytest tests/test_fltkfmt_parity.py` (16 pass),
`uv run ruff check` + `uv run pyright` on the changed generator (clean), and `make gencode`
+ `make fix` + `git diff` confirming the committed generated `unparser.rs` / `unparser.pyi`
are byte-identical (no drift from the generator edits).

---

## errhandling-1
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py` `_item_spacing_lines` — added an explicit
  `else: raise ValueError(...)` after the `if position == "before" / elif "after"` chain,
  naming the rule and item (mirroring `_item_disposition_success_lines`), and updated the
  comment. Generated output is unchanged (the branch is unreachable under correct use;
  regen confirmed byte-identical).
- Severity assessment: A wrong `position` reached `spacing`/`ctor` unbound, surfacing as an
  `UnboundLocalError` that named neither rule nor position — a confusing diagnostic for a
  generation-time contract violation. Generation-time only; no runtime/output impact.

## errhandling-2
- Disposition: TODO(unparser-none-path-diagnostics)
- Action: No code change. The TODO already exists at the cited site
  (`gsm2unparser_rs.py` ~line 1360, the `if let Some(trivia_result) = self.unparse__trivia`
  block with no `else`) and in `TODO.md`. Left as-is.
- Severity assessment: A comment present in source could be silently dropped from formatted
  output with no stderr signal *if* `_has_preservable_trivia` returns true but
  `unparse__trivia` returns `None`. In the `fltkfmt` pipeline (`capture_trivia=true`) every
  span carries source, so this is an invariant-violation path, not a reachable normal case.
  Pre-existing base-commit behavior — the correctness reviewer confirms this diff only added
  the TODO comment, introducing no behavior change. Properly fixing it requires a deliberate
  cross-backend policy decision applied to *both* the Rust generator and the Python unparser
  so the two backends stay behaviorally equivalent (CLAUDE.md: cross-backend equivalence is a
  hard requirement); a Rust-only `eprintln!` would diverge them. That is genuine net new
  cross-backend implementation, out of scope for a respond-mode patch, hence the deferral the
  TODO already records.

## errhandling-3
- Disposition: TODO(unparser-none-path-diagnostics)
- Action: No code change. Same TODO covers the `let text = span.text()?;` site
  (`gsm2unparser_rs.py` ~line 1082, `_gen_regex_term_body`, and the analogous span-text
  extraction paths). Left as-is.
- Severity assessment: A sourceless/sentinel span would propagate `None` to the public
  `unparse_*` entry point, surfacing in the CLI as a generic "internal error: unparser
  returned None" with no rule/label/span context. Invariant-violation path (spans always
  carry source in the fltkfmt pipeline), pre-existing, and the same cross-backend-parity
  argument as errhandling-2 applies: the fix belongs to a coordinated policy change across
  both backends, which the existing TODO tracks.

## security-1
- Disposition: Fixed
- Action: `crates/fltk-fmt-cli/src/lib.rs` `create_temp` — the temp file is now opened with
  `OpenOptions::mode(0o600)` on Unix (via `std::os::unix::fs::OpenOptionsExt`, `#[cfg(unix)]`)
  before `write_atomic` widens it to the source mode. Narrowing-then-widening inverts the
  failure direction: a failed `set_permissions` now leaves the temp private (`0o600`) instead
  of process-default `0o644`.
- Severity assessment: Closes a CWE-732 hardening gap where a private (`0o600`) `.fltkg`
  formatted with `--in-place` could have its contents silently widened to world-readable if
  the permission-copy step failed. Low likelihood (`set_permissions` on a fresh process-owned
  file rarely fails) and requires a local same-host actor; minor hardening, now removed.

## test-1
- Disposition: Fixed
- Action: `crates/fltk-fmt-cli/src/lib.rs` — `run_args_only` now returns the captured stderr
  alongside the exit code; all six flag-conflict tests assert exit 2 *and* that the usage
  message naming the relevant flag is written to stderr.
- Severity assessment: Without this, a regression that exits 2 silently (no stderr) would
  pass every conflict test, eroding the "usage error is reported" contract. Test-coverage gap.

## test-2
- Disposition: Fixed
- Action: Added `output_with_stdin_writes_to_file` — `--output` with no file args (stdin as
  the single input) writes the formatted content to the output file.
- Severity assessment: The `validate` count logic that treats zero files as one implicit
  stdin input was previously unexercised on the stdin path; a regression there would have
  gone undetected. Test-coverage gap.

## test-3
- Disposition: Fixed
- Action: Added `check_stdin_exits_1_when_input_would_change` and
  `check_stdin_exits_0_when_already_formatted` covering `--check` over stdin.
- Severity assessment: The `--check` stdin code path had no coverage; a stdin-specific
  regression in the check branch would have been silent. Test-coverage gap.

## test-4
- Disposition: Fixed
- Action: Added `in_place_identity_skips_rewrite_and_leaves_no_temp` — `--in-place` with an
  identity stub leaves the file unchanged and writes no temp (the `formatted == content`
  skip guard).
- Severity assessment: A regression removing the skip-when-unchanged guard would cause
  needless mtime churn on stable trees; now caught. Test-coverage gap.

## test-5
- Disposition: Fixed
- Action: Added `in_place_format_error_leaves_original_and_no_temp` — `--in-place` with a
  failing stub exits 2, leaves the original file byte-for-byte intact, and leaves no temp.
- Severity assessment: This is the exact atomicity guarantee `--in-place` exists to provide;
  it previously had no test, so a regression writing on the `Err` path would have been
  silent. Test-coverage gap.

## reuse-1
- Disposition: TODO(unparser-pyi-doc-stub-shared)
- Action: Added a `TODO(unparser-pyi-doc-stub-shared)` comment in
  `fltk/unparse/gsm2unparser_rs.py` `generate_pyi` (at the `class Doc:` emission) and a
  matching entry in `TODO.md`.
- Severity assessment: The grammar-independent `Doc` stub (3 lines) is emitted verbatim into
  every per-grammar `unparser.pyi`; a `Doc.render` signature change must be mirrored across
  all committed stubs, growing linearly with grammar count. Currently two copies. Deferred
  rather than fixed now because centralizing it changes the *structure* of the generated
  `.pyi` public surface (each downstream consumer's stub would import a shared `Doc` module),
  making it a deliberate public-API decision — and CLAUDE.md flags generated artifacts as
  out-of-tree public API — not an incidental refactor. Low current cost; tracked for a
  deliberate change.

## quality-1
- Disposition: Fixed
- Action: `crates/fltkfmt/Cargo.toml` — removed the redundant direct `fltk-unparser-core`
  dependency (it remains in the graph transitively via `fegen-rust-cst` and `fltk-fmt-cli`),
  and updated the comment to describe the minimal formatter-binary template. Verified the
  binary still builds, clippies clean, `--check`s `fegen.fltkg`, and passes the 16-case
  cross-backend parity suite.
- Severity assessment: The binary is the reference template downstream consumers copy to make
  their own formatter; the redundant dep taught a false direct-coupling and inflated per-
  consumer boilerplate. The design's own rule ("add [transitive crates] explicitly only if a
  named type requires it (the macro names neither)") supports removal; this is the deliberate,
  called-out resolution of the slight inconsistency with the design's literal dep list.
  Maintainability/clarity, no behavior change.

## quality-2
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py` — extracted
  `_gen_py_unparse_prelude_lines(rule_name)` and call it from both the string-returning and
  Doc-returning PyO3 method generators, replacing the verbatim 5-line duplication. Regen
  confirmed the committed generated `.rs` is byte-identical.
- Severity assessment: The duplicated prelude had to be edited in two places per future
  change (e.g. adding a depth-exceeded guard), with no compiler/test catching a one-sided
  edit. DRY/maintainability; no output change.

## quality-3
- Disposition: Fixed (same change as errhandling-1)
- Action: See errhandling-1 — the `else: raise` added to `_item_spacing_lines` resolves this
  finding too.
- Severity assessment: Identical to errhandling-1: turns a future `UnboundLocalError` into a
  diagnosable explicit raise. Generation-time only.

## quality-4
- Disposition: Fixed
- Action: `crates/fltk-fmt-cli/src/lib.rs` `validate` — replaced the dead-branch `count`
  computation (`if files.is_empty() { 1 } else { len }; if count > 1`, where `1 > 1` is
  always false) with `args.output.is_some() && args.files.len() > 1`, preserving identical
  behavior, and documented the "zero files = one implicit stdin input" model in a comment.
- Severity assessment: Dead-branch maintenance debt that made a reader trace a non-load-
  bearing path. No behavior change.

## efficiency-1
- Disposition: Won't-Do
- Action: No change.
- Severity assessment: Multi-file formatting is sequential. The reviewer itself records this
  as "a conscious, documented design choice ... Recorded for completeness; not an action item
  given the accepted design and the tiny-file workload." Design §3 ("Concurrency / `Send`")
  deliberately keeps the pipeline single-threaded because `fltk_unparser_core::Doc` uses `Rc`
  internally and is not `Send`; a correct parallelization would have to run each file's whole
  pipeline through its final `String` on its own worker and reassemble by index for ordered
  stdout output — a substantial change for marginal gain on ms-scale `.fltkg` files where
  per-process and I/O fixed costs dominate. Parallelizing against the explicit design choice
  would harm simplicity for no realistic benefit.
- Rationale (Won't-Do): The design froze a single-threaded pipeline for a sound technical
  reason (`Doc: !Send`, `Rc`-based) recorded in §3, and the reviewer agrees it is not an
  action item; introducing threading would contradict the accepted design and add complexity
  with no payoff for the target workload.

---

Note: `notes-final-deep-correctness.md` reported no findings (entries traced and cleared),
so it has no disposition entry.
