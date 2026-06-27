# Test review — increments 4-6 (rust-fltkfmt)

Base: 762bbced1f5b44de2ad507db3a18a653c2ca585a
HEAD: 0718645d66cec435752a28094f0cd7631712b058

---

## test-1 — stdin code path is entirely uncovered

**File:line** `crates/fltk-fmt-cli/src/lib.rs:276-312` (`run_inner`, stdin branch)

**What's wrong**

Every `run_inner` integration test supplies at least one real file path. The branch where
`files.is_empty()` (or `files == ["-"]`) triggers stdin reading — `vec![Path::new("-")]`,
`is_stdin(source) == true`, `stdin.read_to_string(&mut buf)`, display name `"<stdin>"`,
`filename = None` — is never reached by any test. The mock `&mut dyn Read` stream is always
wired to `b""` and never read.

**Consequence**

A regression in any of: the display-name assignment (`"<stdin>"`), the `None` filename
passed to `format_fn`, the read path from the injected stream, or the exit-code handling
on a stdin read error would not be caught. The stdin path is an explicit design requirement
and an equally likely production entry point as file input.

**Fix**

Add at least two tests that pass `FmtArgs` with empty `files` (or `files=["-"]`):
one that puts content in the mock stdin buffer and asserts the transformed output on
stdout with exit 0; one that tests a stdin read error (inject a reader that returns
`Err`) and asserts exit 2 with `"<stdin>"` in stderr.

---

## test-2 — `fltkfmt` has zero integration tests; design §4 end-to-end behaviors are entirely unverified

**File:line** `crates/fltkfmt/` (no `tests/` directory)

**What's wrong**

The design §4 specifies four integration tests for `fltkfmt` that require the real Rust
parser + unparser:

- **Idempotency**: `format(format(x)) == format(x)` for a corpus of `.fltkg` snippets
  including `fegen.fltkg` itself.
- **Golden/canonical**: formatting `fltk/fegen/fegen.fltkg` at width 80 / indent 2
  produces a stable expected output.
- **Trailing-newline robustness**: same input with and without a trailing newline (and
  with trailing blank lines) formats successfully to the same result.
- **Parse-error path**: malformed input yields a non-zero exit and a message that names
  the synthetic filename with a line/col position.

None of these exist. The implementation log records this as a deliberate deferral to a
later increment.

**Consequence**

The only proof that the end-to-end pipeline (Rust parser → Rust unparser → resolve →
render) is correct is a manual smoke test logged as "formats `fegen.fltkg` to stdout,
exit 0." Idempotency failures, format regressions on real `.fltkg` input, and
trailing-newline handling defects are invisible until the integration tests land. This is
the strongest correctness requirement for the binary (formatting a formatter is self-
applicable; a non-idempotent formatter breaks the CI drift guard).

**Fix**

The deferral is already tracked. Flag that the integration test increment is a hard
prerequisite before the binary is gated into `make check`.

---

## test-3 — Macro expansion error paths have no test coverage

**File:line** `crates/fltk-fmt-cli/src/lib.rs:219-244` (macro body, error branches)

**What's wrong**

The `fltk_formatter_main!` macro contains two non-trivial error branches that are never
exercised by any test:

1. `fully_consumed(src, parsed.pos)` returns false → partial parse, returns
   `Err(parser.error_message())`.
2. `Unparser::new().$unparse(&*guard)` returns `None` → maps to an internal error string.

The `run_inner` unit tests bypass the macro entirely (they inject a stub `format_fn`). The
only macro consumer is `fltkfmt/src/main.rs`, which has no tests (see test-2).

**Consequence**

A defect in either error branch — wrong error message, a path-qualification bug in the
macro body causing a compile-time error in a future consumer, or the partial-parse guard
never triggering — would not be caught. The partial-parse branch is particularly important:
a parser that returns `Some(parsed)` with `parsed.pos < len` would silently format a
partial tree unless this guard fires and is tested.

**Fix**

The `fltkfmt` parse-error integration test (design §4) will exercise these paths when it
lands. Until then this gap exists. The partial-parse path could additionally be covered by
a `fltk-fmt-cli` unit test that wires a `format_fn` which mimics the macro's behavior using
a controlled `fully_consumed` return.

---

## test-4 — `write_atomic` error branches are untested

**File:line** `crates/fltk-fmt-cli/src/lib.rs:135-149` (`write_atomic`)

**What's wrong**

`write_atomic` has two cleanup branches: (a) write/flush fails → remove temp file and
return error; (b) rename fails → remove temp file and return error. Both branches clean up
the sibling temp file before propagating the error. The `in_place_rewrites_file_and_leaves_no_temp`
test covers only the success path; no test induces either failure.

**Consequence**

If the temp-file cleanup logic were broken (e.g., wrong variable passed to `remove_file`,
or `Err` returned before the `remove_file` call), no test detects it. The atomicity
guarantee — "a crash leaves the original intact" — is the primary correctness invariant
of the `--in-place` mode but is verified only on the happy path.

**Fix**

Add a test for the write-failure branch by targeting a path inside a read-only or
nonexistent directory. Add a test for the rename-failure branch by targeting a read-only
file. Alternatively, introduce an injectable write/rename seam so failure can be injected
without filesystem manipulation.

---

## test-5 — The filename argument passed to `format_fn` is never asserted

**File:line** `crates/fltk-fmt-cli/src/lib.rs:314` (`filename` construction in `run_inner`)

**What's wrong**

`run_inner` sets `filename = if stdin_source { None } else { Some(&display) }` before
calling `format_fn`. All three stub format_fns (`upper`, `identity`, `fail`) accept
`_filename: Option<&str>` and ignore the argument. No test captures or asserts the value
actually received.

**Consequence**

If the code were changed to always pass `None` (losing the filename from the format
context, which matters for error messages returned by the real format_fn), or to pass
`Some("hardcoded")` instead of the actual path, no test would detect the regression. The
filename is load-bearing for the design requirement that parser error messages name the
input file.

**Fix**

Add a stub `format_fn` that records the `filename` argument (e.g., via a `Cell<Option<&'static str>>` or a `std::sync::Mutex<Vec<_>>`). Use it in at least two tests: one asserting file input delivers `Some(<path>)` and one asserting stdin delivers `None`.

---

## test-6 — Multi-file `--check` worst-of accumulation is untested

**File:line** `crates/fltk-fmt-cli/src/lib.rs:324-327` (`--check` branch in `run_inner`)

**What's wrong**

Both `--check` tests (`check_exits_1_when_input_would_change`,
`check_exits_0_when_already_formatted`) use a single file. The `worst = worst.max(1)`
accumulation across multiple files with mixed outcomes — some would change, some already
formatted — is not covered. The multi-outcome accumulation test that does exist
(`read_error_exits_2_but_other_inputs_still_processed`) exercises the error path (`worst.max(2)`),
not the check-diff path.

**Consequence**

If the `worst.max(1)` accumulation were broken for `--check` (e.g., an early `return` that
exits after the first file, or `worst` reset per iteration), no test detects it. The
"continues across all inputs, returns worst" contract is the defined behavior for all modes.

**Fix**

Add a test that provides two files: one already formatted (identity) and one that would
change (upper). Assert exit 1, the path of the would-change file appears in stderr, and
the path of the already-formatted file does not.
