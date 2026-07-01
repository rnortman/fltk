# Deep-review dispositions — workflow-bazel-protocol

Round 1. Base 3c244d1 · fixes at HEAD 9aac952.
No-finding lanes: correctness, security, efficiency.

---

errhandling-1:
- Disposition: Fixed
- Action: `rust.bzl` — expanded the `generate_rust_parser` macro `**kwargs` Args
  doc to state that in pure-Rust mode extra kwargs forward to the internal
  `_generate_rust_srcs` rule and an unrecognized one surfaces a generic Bazel
  "no such attribute" error naming that internal rule (rather than the curated
  `python_extension` guidance). Reviewer itself rated the code change optional
  and recommended exactly this documentation; `**kwargs` is intentionally
  open-ended and cannot be enumerated.
- Severity assessment: Degraded error-message quality on an already fail-fast
  path (nothing is swallowed). Consequence is a downstream author seeing an
  internal rule name instead of `python_extension` guidance for a rare
  fat-fingered passthrough.

errhandling-2:
- Disposition: Fixed
- Action: `BUILD.bazel` — repointed both smoke targets from `bootstrap.fltkg`
  (block-comment regex outside the Rust portable subset) to
  `fltk/fegen/test_data/rust_parser_fixture.fltkg` (fully Rust-compilable).
  `bazel build //:bootstrap_native` now completes end-to-end, so the guard that
  materializes `bootstrap_native/cst.pyi` + `__init__.pyi` is actually live, not
  inert. Verified: full build succeeds, stub package + `.abi3.so` materialize.
- Severity assessment: The stub-dir regression guard this change advertised could
  not run, so a re-break of the exact bug being fixed would go unreported. Now
  the guard executes on any real build of the target.

test-1:
- Disposition: Fixed
- Action: `BUILD.bazel` (same repoint as errhandling-2). Confirmed via
  `bazel build //:bootstrap_rust_srcs //:bootstrap_native`: pure-Rust target emits
  only `cst.rs`/`parser.rs`; extension target builds crate assembly →
  `rust_shared_library` cdylib → abi3 rename → `py_library`, with the crate root
  containing exactly `lib.rs`/`cst.rs`/`parser.rs` (no `.pyi`/`.py` leak) and the
  stub package + `cst_protocol.py` present under `bootstrap_native/`. Comments
  updated to state the grammar is fully Rust-compilable; the now-resolved
  `bazel-rust-smoke-bootstrap-regex` TODO was removed from `TODO.md` and its
  BUILD.bazel comment dropped.
- Severity assessment: Before this, the new macro's `python_extension = True`
  branch (output-group routing, `_srcs` vs `name` label coexistence, cdylib
  wiring) had never been exercised by a successful build. It now is.

test-2:
- Disposition: TODO(bazel-neg-test-harness)
- Action: TODO comment added in `BUILD.bazel` near the `bootstrap_native` target;
  entry added to `TODO.md`. Deferred, not fixed, because the design's Test plan
  explicitly accepted manual verification when no harness exists ("If no harness
  exists, these are documented as manual `bazel build` expectations rather than
  automated tests"), and the repo has no `bazel_skylib` `analysistest` dep.
  Committing intentionally-failing targets as the reviewer suggested would break
  `bazel build //...` (wildcard builds), which is why a proper analysistest
  harness — able to assert analysis failure without a failing target in the graph
  — is the correct vehicle. That is net-new test infrastructure beyond a
  respond-mode patch.
- Severity assessment: The six guards have no reproducible regression test; a
  future edit could silently disable one. Mitigated: the guards were re-verified
  live this round (see quality-2) and the gap is now tracked with a concrete
  remediation path.

reuse-1:
- Disposition: Fixed
- Action: `rust.bzl` — extracted `_require_protocol_module(protocol,
  protocol_module)` (single condition + message) and called it from both the
  macro (early clear message) and `_generate_rust_srcs_impl` (analysis-time
  guard), removing the verbatim copy. Verified both call paths still `fail()`
  with the identical message via bazel.
- Severity assessment: Two verbatim copies of the coupling check could drift
  (condition, coupling, or message) if edited in one place only. Now one owner.

quality-1:
- Disposition: Fixed
- Action: `rust.bzl` — hoisted module-level `_DEFAULT_RECURSION_LIMIT = 512`;
  used it for both `_build_pyo3_cdylib` and `generate_rust_parser` signature
  defaults and for the pure-Rust `recursion_limit != _DEFAULT_RECURSION_LIMIT`
  guard, so the guard tracks the default automatically.
- Severity assessment: The literal `512` was the source of truth in three
  independent sites; raising the default while missing the guard would make it
  misfire. Now single-owner.

quality-2:
- Disposition: Fixed
- Action: `rust.bzl` — replaced the six near-identical `fail()` guards with a
  single `python_only_knobs` list of `(attr_name, is_set)` pairs looped over one
  shared message template. Default-sentinel cases (`lib_rs != None`,
  `recursion_limit != _DEFAULT_RECURSION_LIMIT`) are normalized to booleans
  alongside the truthy ones. Messages are byte-identical to before; verified the
  `deps` guard fires with the exact expected text via bazel.
- Severity assessment: Linear maintenance cost and message-drift risk as
  extension-only knobs grow; adding a knob is now one tuple.

quality-note (out-of-lane, expected-to-fail smoke target):
- Not a numbered finding; resolved incidentally by the errhandling-2 / test-1
  repoint — `bazel build //:bootstrap_native` now succeeds end-to-end, so the
  guard is reachable through a standard build rather than only the internal
  `_stub_srcs` subtarget.
