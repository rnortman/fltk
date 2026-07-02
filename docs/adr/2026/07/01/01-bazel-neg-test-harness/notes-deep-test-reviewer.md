# Test review — bazel-neg-test-harness (base 5eec3cd7..HEAD 9afab45)

No findings.

## What this diff is

The diff *is* a test harness (skylib `unittest`/`analysistest` coverage for
`generate_rust_parser`'s misconfiguration guards in `rust.bzl`), plus a
behavior-preserving refactor of the guard logic into pure functions
(`_pure_rust_mode_violation`, `_protocol_module_violation`) to make it
testable. Reviewed both the harness itself and its coverage of the refactor.

## Coverage

- All 6 pure-Rust-mode knob checks: one unit test each, exact-message
  assertion, single-knob-set-away-from-default construction (doesn't
  over-constrain loop order). Plus an all-defaults → `None` case.
- Coupling check logic: 3 cases (`(True,"")`→message, `(True,"m")`→`None`,
  `(False,"")`→`None`).
- Analysis-time firing of the coupling guard inside `_generate_rust_srcs`:
  `analysistest` against a directly-instantiated internal-rule target
  (`neg_protocol_without_module`, `manual`-tagged), substring-asserting the
  message — the only way to exercise this path since the public macro's
  loading-time check shadows it.
- Second commit (9afab45, "respond(prepass)") fixes a real suite-wiring bug
  the prepass caught: `unittest.suite` only pulls unit tests into the named
  `test_suite`, so the analysistest was silently absent from
  `:rust_bzl_tests` (only reachable via `:all` or `//...`). Fix regroups unit
  tests into a `_unit_tests` sub-suite and wraps both under the top-level
  name. Verified this fix empirically (below).
- Explicitly accepted residual gap (documented in design.md, not hidden): the
  two `if msg != None: fail(msg)` call sites in the macro's loading-time path
  are unexercised — intentionally-failing targets can't sit in `BUILD.bazel`
  without breaking `bazel build //...`, and the rejected alternatives
  (deferred-fail rule, nested-Bazel `sh_test`) were reasoned through in the
  design. Not a hole introduced by omission.

## Empirical verification performed (not just reading)

- `bazel test //tests/bazel_rules:rust_bzl_tests`: 11/11 pass as claimed.
- Planted a regression (disabled the `protocol_module` knob check in
  `_pure_rust_mode_violation`) → `rust_bzl_tests_unit_tests_test_0` failed
  with a message naming exactly that knob. Reverted, suite green again.
- Planted a regression on the coupling condition itself (`_protocol_module_violation`
  body replaced with `if False: ...`) → both the coupling unit test *and* the
  analysistest failed (analysistest: "Expected failure of target_under_test,
  but found success"), confirming the post-9afab45 suite wiring actually
  exercises the analysistest, not just the unit tests. Reverted; working tree
  confirmed clean (`git diff --stat` empty) afterward.
- `bazel build //:bootstrap_rust_srcs //:bootstrap_native` and `bazel build
  //...` both succeed post-refactor (the `manual` tag correctly excludes
  `neg_protocol_without_module` from the wildcard).
- `bazel build //tests/bazel_rules:neg_protocol_without_module` directly:
  fails at analysis time with the exact expected message, confirming the
  fixture target fails for the reason the test claims, not some unrelated
  attribute error that the substring match would have masked.

## Quality

Every assertion carries a real expected value (exact string match for
messages, `None` for non-violations, substring match via
`asserts.expect_failure`) plus a descriptive per-test failure message — none
of the `assert(x !== undefined)`-style vacuousness. Tests are intentionally
*not* built via a Starlark loop/comprehension (skylib rules must bind to
top-level globals; the file's own comment explains why), avoiding a
late-binding closure bug. `default_recursion_limit` is threaded through
`rust_bzl_internals` rather than duplicated as a literal in the test file,
so the recursion-limit test can't silently drift from the production
constant.
