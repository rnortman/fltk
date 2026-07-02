# Design: `fltkfmt` integration tests (closing `TODO(fltkfmt-integration-tests)`)

Requirements: `docs/adr/2026/07/01/01-fltkfmt-integration-tests/request.md`
Exploration: `docs/adr/2026/07/01/01-fltkfmt-integration-tests/exploration.md`
Original test-plan source: `docs/workflow/2026-06-27-rust-fltkfmt/design.md` §4, "`fltkfmt`
integration tests" bullet (design.md:285-294).

## 1. Root cause / context

The `fltkfmt` binary crate (`crates/fltkfmt/`) has zero tests of any kind — no `tests/`
directory, no `#[cfg(test)]` module (`crates/fltkfmt/src/main.rs` is 23 lines: doc comment,
the TODO, and one `fltk_fmt_cli::fltk_formatter_main!` invocation). The original design
specified four integration tests for it (idempotency, golden, trailing-newline, parse-error);
they were user-accepted as a deferral under `TODO(fltkfmt-integration-tests)`
(the `## fltkfmt-integration-tests` section in `TODO.md`; `crates/fltkfmt/src/main.rs:13-16`)
and never picked up.

Per the exploration, the TODO's other half — `make check` gating — already happened in
commit `1e9e402`: `Makefile:141` (`cargo-test-no-python`) already runs
`cargo test -q --manifest-path crates/fltkfmt/Cargo.toml` on every `make check` and
`make check-ci`. So landing tests in `crates/fltkfmt/tests/` auto-gates them with **zero
Makefile changes**.

What existing coverage does *not* provide (`tests/test_fltkfmt_parity.py`): the parity
pytest feeds only well-formed corpus files through a single format pass and asserts
byte-parity with Python. It never double-formats (idempotency), never pins expected bytes
(golden), never varies trailing newlines, and never exercises the error paths. The
`fltk_fmt_cli` macro's parse-failure and partial-parse branches
(`crates/fltk-fmt-cli/src/lib.rs:283-333`, the `fltk_formatter_main!` expansion) are
executable only through a real consumer binary like `fltkfmt` — the `fltk-fmt-cli` unit
tests use stub `format_fn`s and cannot reach them.

## 2. Proposed approach

### 2.1 New file: `crates/fltkfmt/tests/cli.rs`

One Cargo integration-test file driving the built binary as a subprocess. No new
dependencies (dev- or otherwise): `std::process::Command` plus the standard
`env!("CARGO_BIN_EXE_fltkfmt")` (Cargo builds the bin and injects its path for integration
tests of the owning package). This matches the crate's role — it *is* a CLI — and keeps the
crate's "standalone, minimal template" property (`crates/fltkfmt/Cargo.toml` top comment)
intact.

Path handling: repo-root-relative fixtures resolved from `env!("CARGO_MANIFEST_DIR")`
(`crates/fltkfmt` → repo root is `../..`), so tests are cwd-independent. Outputs compared
as raw bytes (`Vec<u8>` from `Output::stdout`), not lossily-decoded strings.

A small helper runs the binary with given args and optional stdin bytes, returning
`(status, stdout, stderr)`; each test asserts on those. Temp files for the parse-error and
trailing-newline tests go under `std::env::temp_dir()` with a pid+counter-unique name (same
pattern as `fltk-fmt-cli`'s `temp_dir` test helper, `lib.rs:576-584`).

### 2.2 The four tests

**Test 1 — Idempotency** (`format_format_is_format`). Corpus: the same 8 `.fltkg` files
pinned in `tests/test_fltkfmt_parity.py:42-51` (`bootstrap.fltkg`, `fegen.fltkg`,
`fltk.fltkg`, `regex.fltkg`, and the four `test_data/` grammars), duplicated as a pinned
Rust list (no practical way to share a list between pytest and a Rust test; a comment on
each list cross-references the other). Configs: both parity configs — default `(w=80,
i=2)` and narrow `(w=40, i=4)` — so break/flat layout decisions are exercised. For each
file × config: run `fltkfmt <file> -w W -i I` → `out1` (assert exit 0); run the binary
again with `out1` piped to stdin, same config → `out2` (assert exit 0); assert
`out2 == out1` byte-for-byte, with the file name and config in the failure message. One
`#[test]` fn looping the corpus (std Rust has no parametrization; per-case context lives
in assert messages). Feeding pass 2 via stdin also exercises the binary's stdin input
path end-to-end, which no existing test does with a real grammar.

**Known exception, verified against the current binary (full 8×2 sweep run):** exactly one
case is *not* idempotent today — `fltk/fegen/test_data/rust_parser_fixture.fltkg` at
`w=40 i=4`. Pass 1 emits a grouped alternation as
`( inner:rec_via_sub . "+"` / `| inner:atom ) .`; pass 2 re-breaks it into a 4-line
`(` … `)` block; pass 3 == pass 2, so pass 2 is a fixed point. (File-vs-stdin input mode is
not the cause.) This is a real formatter non-idempotency bug — presumably present in both
backends, given single-pass parity holds — and fixing formatter behavior is out of scope
for this test addition. The test therefore carves out this one case **explicitly and
loudly** rather than shrinking the corpus: for it, assert `out2 != out1` and `out3 == out2`
(convergence by pass 2), with a `TODO(formatter-group-idempotency)` comment at the
carve-out and a matching `TODO.md` entry describing the bug. Pinning `out2 != out1` means
any future formatter fix trips the assertion, forcing removal of the carve-out and TODO
instead of letting them linger stale.

**Test 2 — Golden / canonical** (`golden_fegen_fltkg`). Run
`fltkfmt fltk/fegen/fegen.fltkg` at the defaults (w=80, i=2, passed explicitly so the test
doesn't silently drift if CLI defaults change); assert stdout is byte-identical to a
committed fixture `crates/fltkfmt/tests/golden/fegen.fltkg.golden`. The fixture is
generated once during implementation by running the binary itself (its correctness on this
exact input/config is already independently guaranteed by the parity pytest's
`fegen.fltkg` × 80/2 case, which pins it to the Python reference). Verified: the current
binary's 80/2 output for `fegen.fltkg` is byte-identical to the source file itself — the
file is already canonically formatted — so the initial fixture equals today's
`fegen.fltkg`; it is still a separate committed file so the anchor survives future edits
to the source. The test's failure message includes the regeneration command:
`cargo run --manifest-path crates/fltkfmt/Cargo.toml -- fltk/fegen/fegen.fltkg -w 80 -i 2 > crates/fltkfmt/tests/golden/fegen.fltkg.golden`
(run from repo root; the explicit `-w 80 -i 2` matches the test's pinned config, so the
regen command cannot drift with CLI defaults while the test stays pinned). Value over the
parity test: a pinned-bytes anchor that runs without Python and catches *simultaneous*
drift of both backends (parity only detects the backends disagreeing).

**Test 3 — Trailing-newline robustness** (`trailing_newline_handling_is_stable`). Base input:
`fegen.fltkg`'s text (the file ends with exactly one `\n`). Variants, each piped via
stdin: (a) trailing newline stripped entirely, (b) exactly one trailing `\n`, (c) three
trailing `\n`s (trailing blank lines). Assertions, pinning behavior **verified against the
current binary and confirmed byte-identical in the Python backend**:

- all three variants exit 0;
- (a) and (b) produce byte-identical output, ending in a single `\n`;
- (c) produces (b)'s output plus exactly one extra `\n` — trailing blank lines are
  *collapsed to one preserved blank line*, not stripped — and re-formatting (c)'s output
  is a fixed point (idempotent).

Note: the original design's wording (design.md:291-293) expected the blank-lines variant
to format "to the same result" as the others. Measured behavior in *both* backends
disagrees (trivia capture preserves one trailing blank line), and cross-backend parity is
the governing contract, so this test pins the real, parity-consistent behavior rather than
the original wording. Changing formatter behavior is out of scope for a test addition.

**Test 4 — Parse-error path** (`parse_errors_report_filename_and_position`). Two inputs,
chosen to drive both macro error branches (both verified against the current binary: each
exits 2 with a `<path>: Syntax error at line N col M:` + caret + expected-tokens message):

- *Unparseable from the start*: `"%%% not a grammar\n"` — `grammar := , rule+` requires
  ≥1 rule, no rule can start here, so `apply__parse_grammar` returns `None` → the macro's
  parse-`None` branch (`lib.rs:309-311`). Reports line 1 col 1.
- *Valid prefix + garbage*: `"a := \"x\";\n???\n"` — one complete rule parses, the
  garbage can't start a second rule, so the parse returns `Some` with non-whitespace
  unconsumed → the `fully_consumed` partial-parse branch (`lib.rs:315-317`). Reports
  line 2 col 1.

Each is written to a temp file with a distinctive name; assertions per case: exit code is
exactly 2 (the documented `run_inner` error code, `lib.rs:339-341` — stronger than the
original design's "non-zero"), stdout is empty, and stderr contains (i) the temp file's
path (the CLI's `display: msg` prefixing, `lib.rs:405`) and (ii) `"Syntax error at line "`
and `" col "` (the `format_error_message` shape,
`crates/fltk-parser-core/src/errors.rs:100-160`). We do not pin the full error text —
expected-token sets may legitimately change with the grammar — only the
filename + line/col contract the original design specified.

Which internal branch fires for a given input is not externally observable (both print
`parser.error_message()` with the same prefix and exit 2); the two inputs are chosen so
that, per the grammar and the macro's control flow, each branch is exercised. The test
documents this in comments rather than pretending to assert branch identity.

### 2.3 TODO closure

- Delete the `TODO(fltkfmt-integration-tests)` comment block from
  `crates/fltkfmt/src/main.rs:13-16`.
- Delete the `## fltkfmt-integration-tests` section from `TODO.md`, located by its slug
  header (line numbers drift with unrelated TODO churn; the header is the stable anchor).
- Add a new `## formatter-group-idempotency` entry to `TODO.md`, paired with the
  `TODO(formatter-group-idempotency)` comment at Test 1's carve-out (see §2.2) — the
  formatter non-idempotency bug discovered while verifying this design.

All per the TODO-system convention (slug entries and code comments stay in sync).

### 2.4 Explicit non-changes

- **No Makefile changes.** `cargo-test-no-python` (`Makefile:141`) already runs this
  crate's tests; new tests under `crates/fltkfmt/tests/` are gated automatically.
- **No changes to `crates/fltkfmt/src/main.rs`** beyond deleting the TODO comment, and no
  changes to `fltk-fmt-cli` or any generated code. This is a pure test addition; no public
  API surface moves, so the out-of-tree-consumer compatibility rules are untouched.
- **No Bazel wiring** — Bazel doesn't build the Rust side (`TODO(bazel-rules-rust)`).
- **`unparse`-returns-`None` branch is not end-to-end triggerable.** The TODO comment says
  the tests "cover the … unparse-None error branches"; strictly, that branch
  (`lib.rs:321-326`) fires only on a CST/unparser shape mismatch, which a correctly
  generated parser+unparser pair cannot produce from any input — there is no input that
  parses successfully but unparses to `None`. These tests compile and link the branch in a
  real consumer (which is what "need a real consumer like this binary" was about) and
  execute every *reachable* macro branch; the unreachable-by-construction branch stays
  covered only by its explicit `match` arm. The test file notes this in a comment so a
  future reader doesn't hunt for a missing test.

## 3. Edge cases / failure modes

- **Golden staleness**: any change to `fegen.fltkg`, `fegen.fltkfmt`, the generated
  unparser, or the renderer will fail the golden test. Intended — that is the test's job —
  and the failure message carries the one-line regeneration command. Regenerating is a
  deliberate, diff-reviewable act (the `.golden` file changes in the same commit).
- **Corpus drift vs the parity pytest**: the two pinned lists (pytest and Rust) can
  diverge if someone adds a grammar to one and not the other. Mitigated by
  cross-referencing comments on both lists; divergence degrades coverage but never
  produces a false pass.
- **Debug-build parse depth**: the corpus files all parse fine under `cargo test`'s debug
  profile today (the parity pytest already builds and runs the debug binary on the same
  corpus), so no `set_max_depth` handling is needed.
- **Parallel test execution**: Cargo runs `#[test]` fns in threads; all temp files use
  unique names (pid + atomic counter) and each test cleans up after itself, so there is no
  cross-test interference. Reading the shared corpus files is read-only.
- **Error-message evolution**: parse-error assertions bind only to the stable
  `"Syntax error at line "`/`" col "` skeleton and the filename prefix — grammar changes
  that alter expected-token lists won't break the test; a change that removes line/col
  reporting (a genuine regression for users) will.
- **Non-UTF-8 in outputs**: comparisons are on raw bytes; no decode step can panic or
  silently lossy-replace.
- **Known non-idempotent case going stale**: the `rust_parser_fixture.fltkg` × 40/4
  carve-out pins today's buggy behavior (`out2 != out1`, `out3 == out2`); if the formatter
  bug is fixed, that pin fails and the carve-out + `TODO(formatter-group-idempotency)` get
  removed in the same change. It can never silently mask a regression in the other 15
  cases, which keep the strict `out2 == out1` assertion.

## 4. Test plan

After this change, `cargo test --manifest-path crates/fltkfmt/Cargo.toml` (and hence
`make check` / `make check-ci`, with no Makefile edits) runs, in
`crates/fltkfmt/tests/cli.rs`:

1. `format_format_is_format` — 8-file corpus × 2 configs, second pass byte-identical to
   the first; both passes exit 0. One documented exception:
   `rust_parser_fixture.fltkg` × 40/4 is pinned as converging at pass 2
   (`out2 != out1`, `out3 == out2`) under `TODO(formatter-group-idempotency)`.
2. `golden_fegen_fltkg` — `fegen.fltkg` at 80/2 matches the committed
   `tests/golden/fegen.fltkg.golden` byte-for-byte.
3. `trailing_newline_handling_is_stable` — 0/1/3 trailing newlines on `fegen.fltkg` via
   stdin: all exit 0; 0- and 1-newline outputs identical; 3-newline output is that plus
   exactly one `\n`, and is itself a formatting fixed point.
4. `parse_errors_report_filename_and_position` — unparseable input and valid-prefix+garbage
   input each exit 2 with empty stdout and a stderr containing the input path and
   `Syntax error at line … col …`.

Plus one committed fixture: `crates/fltkfmt/tests/golden/fegen.fltkg.golden`.

TDD note: these tests are the deliverable itself (pure test addition); the "red" state is
the current absence of the `tests/` directory. Each test should be seen passing against
the current binary before the TODO entries are deleted.

## 5. Open questions

None. Three deliberate choices flagged for visibility (all cheap to change later):

- **A formatter non-idempotency bug was found while verifying this design** (see §2.2
  Test 1): `rust_parser_fixture.fltkg` at 40/4 changes between pass 1 and pass 2 (grouped
  alternation re-breaks), converging at pass 2. The design pins current behavior and
  defers the formatter fix under `TODO(formatter-group-idempotency)` — fixing formatter
  layout is a behavior change to both backends and out of scope for a test addition. If
  the user prefers fixing the formatter first, Test 1 simply drops the carve-out.
- Golden covers only `fegen.fltkg` at 80/2, per the original design's wording ("the
  canonical `fltk/fegen/fegen.fltkg` … at width 80 / indent 2"). Widening to more
  files/configs would add fixtures without adding much signal beyond what idempotency +
  parity already give.
- Exit-code assertion is `== 2` (the `run_inner` contract) rather than the original
  design's weaker "non-zero", so an accidental exit-code remap would be caught.
