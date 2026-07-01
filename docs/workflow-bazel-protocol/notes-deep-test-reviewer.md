# Test review — workflow-bazel-protocol (base 3c244d1..224344d)

Scope: this diff touches only `rust.bzl`, `BUILD.bazel`, and docs (no Python
`tests/` files). The change is pure Bazel/Starlark; there is no
`bazel_skylib`/`analysistest` harness in this repo (not a `bazel_dep` in
`MODULE.bazel`) and CI (`.github/workflows/ci.yml`) never invokes `bazel
build`/`bazel test`. So the only regression coverage this diff can create is
the two BUILD.bazel smoke targets (`bootstrap_rust_srcs`, `bootstrap_native`),
per the design's own "Test plan" section. I verified both by actually running
`bazel build` (not just reading the implementation log).

## test-1

File: `BUILD.bazel:108-136` (smoke targets `bootstrap_rust_srcs` /
`bootstrap_native`), `rust.bzl` (`generate_rust_parser` macro,
`_build_pyo3_cdylib` python_extension=True wiring).

What's wrong: the two smoke targets that are supposed to be the regression
tests for this change do not build. Reproduced directly:

- `bazel build //:bootstrap_rust_srcs` fails: `gen-rust-parser` errors on
  `bootstrap.fltkg`'s block-comment regex (`Regex pattern ... is outside the
  portable subset`).
- `bazel build //:bootstrap_native` fails the same way (the `_srcs` action is
  shared); the cdylib/crate-assembly steps never run because their input
  (`parser.rs`) is never produced.
- Only `bazel build //:bootstrap_native_stub_srcs` — an internal,
  non-public `filegroup` created inside the macro's `python_extension = True`
  branch, isolating just the `stub_srcs` output group — succeeds.

I also checked out the base commit (3c244d1) into a worktree and reproduced
the identical `bootstrap_rust_srcs` failure there, confirming the underlying
`gen-rust-parser`/regex limitation is pre-existing (correctly disclosed as
`TODO(bazel-rust-smoke-bootstrap-regex)` in `TODO.md` and
`implementation-log.md`). That disclosure is honest, but it doesn't change the
test-coverage conclusion: **the pre-existing bug already meant the
crate-assembly / cdylib / py_library path (the actual new logic added by this
diff — `_build_pyo3_cdylib` invoked from the new macro, plus the new
`rust_srcs`/`stub_srcs` output-group → `native.filegroup` routing) has never
been exercised by any successful full build, before or after this change.**
This diff had the opportunity to fix that (an already-working Rust-compilable
grammar exists in-tree, `fltk/fegen/test_data/rust_parser_fixture.fltkg`,
used successfully elsewhere for Rust-backend fixtures) but instead filed a
TODO and shipped smoke targets whose comments overstate what's verified: the
`bootstrap_native` comment claims the target is "exercising the full Python
path — crate assembly + rust_shared_library cdylib + abi3 rename +
py_library" — but `bazel build //:bootstrap_native` does not succeed, so none
of that is actually exercised by the target as committed.

Consequence: a regression in the new macro's `python_extension = True`
branch — e.g. broken `rust_srcs`/`stub_srcs` filegroup wiring, the new `data`
param on `_build_pyo3_cdylib`, or the `<name>_srcs` vs `<name>` label
coexistence the design calls out as "the one non-obvious analysis-time
property of the single-name design" — would not be caught by `bazel build
//:bootstrap_native` today, because that build already fails for an unrelated
reason before reaching any of the new logic. The design's own regression
guard for the stub-dir bug is likewise only partially real: it only confirms
`stub_srcs` naming, not that the full public target (cdylib + py_library)
builds.

Fix: point `bootstrap_native` (and ideally `bootstrap_rust_srcs`) at a
grammar the Rust backend can fully compile — `rust_parser_fixture.fltkg` is
already proven to work — so `bazel build //:bootstrap_native` actually
succeeds end-to-end and exercises crate assembly, cdylib compilation, and
py_library wiring, not just the `stub_srcs` output group. Until that's done,
correct the BUILD.bazel comments so they don't claim end-to-end verification
that doesn't currently happen (state plainly that the full build fails and
only `bootstrap_native_stub_srcs` was confirmed).

## test-2

File: `rust.bzl` (`generate_rust_parser` macro `fail()` guards, python_extension
= False branch); `docs/workflow-bazel-protocol/implementation-log.md`
"Misconfiguration coverage" section.

What's wrong: the design's "Misconfiguration coverage" test-plan item (six
`fail()` guards: `protocol` without `protocol_module`, and — in pure-Rust
mode — `protocol_module`, `protocol`, `lib_rs`, `deps`, `crate_features`,
non-default `recursion_limit` each set) was verified by instantiating "a
throwaway bazel package... removed after; no repo change" and only two of the
six paths were actually exercised that way; the implementation log states the
other four ("the same `if cond: fail(...)` shape") "were eyeballed rather
than each separately exercised." No artifact of this verification exists in
the repository — it's a one-time manual check recorded in prose in
`implementation-log.md`/`dispositions-prepass.md`.

Consequence: none of these six guards has any reproducible test. A future
edit to the macro (reordering conditions, a typo in an attribute name inside
a `fail()` check, an accidental early `return`) could silently disable or
break a guard and nothing in the repository would notice — the one-time
manual verification is gone the moment the throwaway package was deleted.

Fix: commit a minimal negative-target smoke package (e.g. under a
`testonly`/`bazel-neg-tests` directory) with one target per misconfiguration
that is expected to fail at loading/analysis time, and note in
`implementation-log.md`/design that these are intentionally-failing
`bazel build` targets rather than something wired into `bazel test` (no
`bazel_skylib` `analysistest` dep exists yet). This turns "eyeballed" and
"throwaway, removed after" verification into something a future change can
actually re-run.
