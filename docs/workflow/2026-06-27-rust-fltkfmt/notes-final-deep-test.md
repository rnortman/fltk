# Test review: rust-fltkfmt final pass

Commit reviewed: f89c80930a8799aaf476077b572fea449e3024d2

## Coverage summary

The `fltk-fmt-cli` Rust test suite is thorough. `fully_consumed` has seven targeted
tests (exact length, trailing whitespace, non-whitespace, char vs byte, multibyte,
negative, past-end). `FmtArgs` parsing is well covered. `run_inner` integration tests
with stub `format_fn`s cover default mode, multi-file concatenation, `--check` both
ways, `--in-place` write+atomic, all six flag-conflict rejections, read error with
continued processing, format error with filename prefix, stdin paths, filename
propagation to `format_fn`, multi-file check accumulation, and both `write_atomic`
success and rename-failure cleanup branches.

`test_fltkfmt_parity.py` is the cross-backend guarantee: it builds the real binary via
`cargo` and compares byte-for-byte output against the Python pipeline at two render
configs across the full `.fltkg` corpus. Correctly declared non-skippable. `functools.cache`
placement is correct and efficient.

The `test_rust_unparser_generator.py` changes correctly update assertions to match the
`if let` emission shape (replacing single-arm `match` + `_ => {}` catch-all that would
trip clippy's `single_match` lint). The updated tests continue to pin the multi-variant
case that the single-variant test does not cover.

`TODO(fltkfmt-integration-tests)` is accepted-deferred and excluded from this review.

## Findings

**test-1**
File: `crates/fltk-fmt-cli/src/lib.rs` — the six flag-conflict tests
(`in_place_without_file_is_rejected`, `in_place_with_stdin_sentinel_is_rejected`,
`in_place_with_output_is_rejected`, `in_place_with_check_is_rejected`,
`check_with_output_is_rejected`, `output_with_multiple_inputs_is_rejected`).

These all route through `run_args_only`, which silently discards both `out` and `err`.
The design says conflicts should exit 2 "with a usage message" to stderr; only the exit
code is asserted. A regression that silently exits 2 (no stderr write) would pass every
one of these tests.

Fix: expand each call to capture `err` and assert it is non-empty (or that it contains
the key flag name, e.g. `"--in-place"`). Alternatively, add one representative
conflict test that inspects the message and leave the rest as exit-code-only — but the
"message is written" invariant must be covered somewhere.

---

**test-2**
File: `crates/fltk-fmt-cli/src/lib.rs` — `--output` with stdin (no file arguments).

`validate()` explicitly allows this combination (`count = 1` when `args.files.is_empty()`).
`output_writes_to_file` only exercises `--output` with a file argument. The stdin path
through `--output` (the branch where `sources = ["-"]` and the result goes to `out_path`
rather than stdout) has no test.

Consequence: a regression in the `validate` count logic (e.g. changing the `1` sentinel
to `0`) would silently make valid `--output` + stdin invocations return exit 2, and no
test would catch it.

Fix: add a test that supplies `["fltkfmt", "-o", out_path, "-"]` (or no files at all)
with stdin bytes in the buffer and asserts `out_path` contains the formatted output.

---

**test-3**
File: `crates/fltk-fmt-cli/src/lib.rs` — `--check` with stdin.

`validate()` does not restrict `--check` to file-only mode; stdin is a valid input
source for `--check`. The check tests (`check_exits_1_when_input_would_change`,
`check_exits_0_when_already_formatted`, `check_multi_file_reports_only_changed_and_exits_1`)
all use file arguments. The stdin tests (`stdin_default_writes_transformed_to_stdout`,
`stdin_read_error_exits_2_with_stdin_display`) use default mode.

Consequence: a regression in the `--check` branch that only breaks the stdin code path
(e.g. wrongly comparing the formatted output against an empty string rather than the
stdin content) would go undetected.

Fix: add a test with `["fltkfmt", "--check", "-"]` and stdin bytes that the stub would
change; assert exit 1. Add a second with an identity stub; assert exit 0 and that
stdout is empty.

---

**test-4**
File: `crates/fltk-fmt-cli/src/lib.rs`, `run_inner` lines ~418-425 — `--in-place`
skip when content is already formatted.

`run_inner` skips the `write_atomic` call when `formatted == content`. The existing
`in_place_rewrites_file_and_leaves_no_temp` test always passes a stub that changes
content, so only the rewrite branch is exercised.

Consequence: a regression removing the `if formatted != content` guard (always calling
`write_atomic`) silently causes unnecessary mtime bumps and file churn on stable trees
but would not be caught.

Fix: add a test using the `identity` stub with `--in-place`; after `run_inner`, verify
the file contents are unchanged and (optionally, by checking the modification time or
directory entry count over multiple runs) confirm no temp file appeared.

---

**test-5**
File: `crates/fltk-fmt-cli/src/lib.rs` — `--in-place` with a format error.

`format_error_exits_2_with_filename_prefix` verifies exit 2 and stderr content for
format errors, but only in default stdout mode. In `--in-place` mode the `Err` branch
does `continue` (skipping `write_atomic`), so the original file should remain untouched.
This invariant — the exact atomicity guarantee that `--in-place` is meant to provide —
has no test.

Consequence: a regression that calls `write_atomic` even on `Err` (or partially writes
before erroring out) would not be caught; the atomicity guarantee of `--in-place` could
be silently broken.

Fix: add a test using the `fail` stub with `--in-place` on a file; assert exit 2, the
original file content is unchanged, and no temp file remains in the directory.
