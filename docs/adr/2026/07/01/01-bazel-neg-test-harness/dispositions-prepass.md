# Dispositions — prepass, round 1

slop-1:
- Disposition: Fixed
- Action: `tests/bazel_rules/rust_bzl_tests.bzl:137-170` — reworked
  `rust_bzl_test_suite` so the analysistest is included in the top-level named
  suite. The unit tests are now grouped via `unittest.suite` into a
  `<name>_unit_tests` sub-suite, and a top-level `native.test_suite(name = <name>,
  tests = [":<name>_unit_tests", ":<name>_coupling_analysis_test"])` wraps both.
  Verified: `bazel test //tests/bazel_rules:rust_bzl_tests` now runs 11/11 tests
  (previously 10/10, silently skipping the analysistest).
- Severity assessment: Confirmed against the vendored skylib source
  (`lib/unittest.bzl:350-362`): `unittest.suite` builds `native.test_suite` with an
  explicit `tests=` list of only the passed unit-test rules, so the sibling
  analysistest target was not a member of `:rust_bzl_tests`. A regression in the
  one analysis-time coupling guard (the harness's original motivating case) would
  not have been caught by the named suite — only by `bazel test //...` or naming the
  analysistest target directly. The design's own test plan §1 uses `:all` (which
  would include it), but the named suite is the documented entrypoint and its
  docstring claimed it included the analysistest, so the gap was real and cheap to
  close.
