# Exploration: TODO(bazel-neg-test-harness)

Base commit: 8fd5ecf ("bazel: unify generate_rust_parser into a single macro with pure-Rust + Python modes").

## TODO occurrences (all locations)

- `TODO.md:109` — `## \`bazel-neg-test-harness\`` heading, followed by the full prose description quoted in the task (through `TODO.md:111` as a single paragraph).
- `BUILD.bazel:138-142` — the only in-code `TODO(bazel-neg-test-harness)` comment, located immediately after the `bootstrap_native` target (`BUILD.bazel:130-136`) and before a blank line ending the file section at `BUILD.bazel:143`. Exact text:
  ```
  # TODO(bazel-neg-test-harness): the generate_rust_parser macro's six pure-Rust
  # misconfiguration fail() guards (and the protocol/protocol_module coupling) are
  # only verified manually today (no bazel_skylib analysistest dep in MODULE.bazel).
  # Intentionally-failing targets cannot live here — they would break `bazel build
  # //...`. Add an analysistest harness that asserts analysis failure per guard.
  ```
- No other `TODO(bazel-neg-test-harness)` code comments exist anywhere in the tree (only the one BUILD.bazel hit from a repo-wide grep). All other hits are prose references in `docs/workflow-bazel-protocol/judge-verdict-deep.md:9,29,104`, `docs/workflow-bazel-protocol/dispositions-deep.md:50`, and `docs/adr/2026/07/01-bazel-rust-parser-unification/README.md:222`, plus this exploration doc and a sibling exploration doc (`exploration-bazel-rules-rust.md:49`) that mentions it only in passing as "still live."

## Do the fail() guards still exist post-8fd5ecf?

Yes, in `rust.bzl`. Exactly two `fail(` call sites in the file (`grep -n "fail(" rust.bzl` returns two matches):

1. `rust.bzl:41` — inside `_require_protocol_module(protocol, protocol_module)` (`rust.bzl:32-41`): `fail("generate_rust_parser: protocol = True requires a non-empty protocol_module.")`. This helper is called from two places: the internal rule impl `_generate_rust_srcs_impl` at `rust.bzl:140` (analysis-time), and the public macro `generate_rust_parser` at `rust.bzl:604` (macro-evaluation-time, fires before the pure-Rust-mode knob loop). Both call sites share the identical guard/message via this one function — this is the "protocol → protocol_module coupling" guard the TODO references.

2. `rust.bzl:622-623` — inside a `for attr_name, is_set in python_only_knobs:` loop in `generate_rust_parser`'s pure-Rust branch (`rust.bzl:606-634`): `fail("generate_rust_parser: {} is only valid with python_extension = True.".format(attr_name))`. This single `fail()` statement fires once per offending knob; the loop iterates a list of exactly six `(attr_name, is_set)` tuples defined at `rust.bzl:613-620`: `protocol_module`, `protocol`, `lib_rs`, `deps`, `crate_features`, `recursion_limit`.

So: the guard *count* matches the TODO's claim ("six pure-Rust... knobs, plus the protocol → protocol_module coupling") — 6 + 1 = 7 distinct misconfiguration conditions — but the current implementation is not six separate `if/fail` statements; commit 8fd5ecf's predecessor (per `dispositions-deep.md:40-47`, disposition `quality-2`) refactored what was described as "six near-identical `fail()` guards" into the single templated loop shown above. The TODO's BUILD.bazel wording ("six pure-Rust misconfiguration fail() guards") and TODO.md wording ("the six pure-Rust-mode python-extension-only knobs") both still accurately describe the six *conditions* checked, even though there is now only one `fail()` call site (shared/templated) implementing all six, not six independent guard call sites.

## Is bazel_skylib already a MODULE.bazel dependency?

No. `MODULE.bazel:5-6` lists exactly two `bazel_dep` entries: `rules_python` (1.5.0) and `rules_rust` (0.70.0). There is no `bazel_dep(name = "bazel_skylib", ...)` anywhere in `MODULE.bazel`, and no `analysistest` load or usage anywhere in the tree (`grep -rn "analysistest|bazel_skylib|skylib"` across `MODULE.bazel`, `BUILD.bazel`, and all `*.bzl` files returns only the two BUILD.bazel comment lines that *mention* the missing dependency, at `BUILD.bazel:140,142`). No `bazel_skylib` repo/directory exists anywhere on the filesystem under a shallow search either (no external repo fetched/vendored). This confirms the TODO's "no bazel_skylib analysistest dep in MODULE.bazel" premise is currently true, unchanged by 8fd5ecf.

## Is the "failing targets can't be committed as-is" claim accurate?

Not independently verifiable from this repo's source, since `bazel_skylib` is not present in the tree — there is no in-repo `analysistest` example to point to. This is an external-knowledge claim about `bazel_skylib`'s `analysistest` module (its documented purpose is exactly to assert `fail()`/analysis-time failures without ever putting a failing target in the normal build graph, via `analysistest.make(expect_failure = True)`), not something confirmable by grepping this repository. The narrower, in-repo-verifiable half of the claim — that a target which unconditionally calls `fail()` at analysis or loading time would break any `bazel build` command that transitively includes it, including `bazel build //...` — follows directly from Bazel's documented behavior of `fail()` and is consistent with how the existing guards are described as firing "during the loading phase" (`docs/workflow-bazel-protocol/implementation-log.md:200-201`). No file in this repo currently exercises or contradicts this.

## Supporting provenance (design/process record, not code)

- `docs/workflow-bazel-protocol/implementation-log.md:196-216` ("Misconfiguration coverage" section): records that no `bazel_skylib`/`analysistest` harness exists in-tree, and that only two of the guard conditions were empirically exercised by hand against a throwaway package — `protocol_module` set with `python_extension = False`, and `protocol = True` with empty `protocol_module` — while the remaining four pure-Rust-only knobs (`lib_rs`, `deps`, `crate_features`, non-default `recursion_limit`) were "eyeballed rather than each separately exercised," on the grounds of identical `if cond: fail(...)` shape (note: this log predates the quality-2 refactor into the shared loop, per `dispositions-deep.md:40-47`, so its "if cond: fail(...)" description of the four eyeballed knobs is now implemented as the shared loop rather than four separate ifs).
- `docs/workflow-bazel-protocol/judge-verdict-deep.md:9-33` (finding `test-2`): judge's contemporaneous review of this exact TODO, addressed to `BUILD.bazel` near `bootstrap_native`; concluded "TODO acceptable," citing the design's Test-plan pre-acceptance of manual verification as a fallback and noting the analysistest route "does not exist yet."
- `docs/workflow-bazel-protocol/dispositions-deep.md:50-58`: the disposition entry for `test-2`, plus the adjacent `quality-2` disposition (`dispositions-deep.md:40-47`) documenting the six-guards → single-loop refactor referenced above.
- `docs/adr/2026/07/01-bazel-rust-parser-unification/README.md:210-225`: ADR section "Automated negative-test coverage is deferred," restating the same deferral and pointing at `TODO(bazel-neg-test-harness)`.
