# Scope review — `bazel-neg-test-harness`

Base: 5eec3cd7abfa39c75fa5ffafc7b241ae96e4416b
HEAD: 175bed4628b51697f0c1422ebb33cac11fd8fc02
Design: `docs/adr/2026/07/01/01-bazel-neg-test-harness/design.md`
Implementation report: none found (no `notes-implementation*`/`implementation-log.md` in
this ADR dir) — per protocol, absence means "no deviations claimed." Diff does not
materially diverge from the design, consistent with that.

## Checklist vs. design.md

- §1 MODULE.bazel: `bazel_dep(name = "bazel_skylib", version = "1.8.2", dev_dependency =
  True)` added — present, matches (placeholder resolved to a concrete BCR version as
  instructed).
- §2 rust.bzl: `_pure_rust_mode_violation` and `_protocol_module_violation` extracted
  verbatim per design; `_require_protocol_module` keeps its name and both call sites
  (rust.bzl:181, rust.bzl:644); macro's pure-Rust branch now
  `msg = _pure_rust_mode_violation(...); if msg != None: fail(msg)` — present.
  `rust_bzl_internals` struct exported at bottom of rust.bzl with all four designed
  members (`pure_rust_mode_violation`, `protocol_module_violation`,
  `generate_rust_srcs`, `default_recursion_limit`) — present. The struct-instantiation
  approach (design's primary path, not the alias fallback) was used directly in
  `tests/bazel_rules/BUILD.bazel`, implying the pre-flight legality check passed;
  consistent with no implementation report surfacing a fallback.
- §3 tests/bazel_rules/: `dummy.fltkg`, `rust_bzl_tests.bzl`, `BUILD.bazel` all present
  and match the designed shape — 6 per-knob unit tests + 1 all-defaults unit test + 3
  coupling-logic unit tests (10 skylib `unittest` functions) + 1 `analysistest`
  wrapping `:neg_protocol_without_module` (tagged `manual`). Verified locally:
  `bazel test //tests/bazel_rules:rust_bzl_tests` → 10/10 pass; the analysistest target
  (`rust_bzl_tests_coupling_analysis_test`) → pass.
- §4 Cleanup: `TODO(bazel-neg-test-harness)` comment removed from `BUILD.bazel`;
  `bazel-neg-test-harness` entry removed from `TODO.md` — both present, matching diff.
- MODULE.bazel.lock: mechanical regeneration from the new `bazel_dep`; not a scope
  concern.

No bonus work beyond what §1-§4 call for. No silent omissions found. No unjustified
punts found — the one open judgment call flagged in the design (struct vs. alias
fallback) resolved in the implementation's favor without needing the fallback, and
nothing about that requires a called-out note since the primary path itself was the
design's expectation.

## Findings

No findings.
