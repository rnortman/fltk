# Deep error-handling review — bazel-neg-test-harness

Commit reviewed: 9afab45b0a456e56886cd9296c26285c3d62b777 (base 5eec3cd)
Scope: rust.bzl guard extraction, tests/bazel_rules/, MODULE.bazel skylib dep.

## Findings

No findings.

## Notes (verification performed, not defects)

- The refactor extracts guard *logic* into `_protocol_module_violation` and
  `_pure_rust_mode_violation` (return message-or-None) but preserves all three
  `fail()` firing sites: analysis-time rule impl (rust.bzl:181 via
  `_require_protocol_module`), loading-time macro coupling check (rust.bzl:644),
  and loading-time pure-Rust knob check (rust.bzl:649-658, `if msg != None:
  fail(msg)`). No error path was converted to a silent return; every
  misconfiguration is still reported with its exact user-facing message.
- Sentinel handling matches the original verbatim: `lib_rs != None` (None
  sentinel), `bool(protocol_module)` (empty-string default),
  `recursion_limit != _DEFAULT_RECURSION_LIMIT` (constant remains single owner).
  No case dropped, no branch made unreachable.
- The two `if msg != None: fail(msg)` wiring lines in the macro are the design's
  explicitly-accepted residual test gap. That is a test-coverage matter
  (test-reviewer's lane), not an error-handling defect: the error is still
  reported and responded to in production code.
- Test harness asserts failures correctly: `analysistest.make(expect_failure =
  True)` + `asserts.expect_failure(env, "...")` substring match against the real
  coupling message; unit tests assert exact strings. Intentional-failure target
  is `tags = ["manual"]` so `//...` wildcards skip it — no swallowed build error.
