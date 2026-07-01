# Scope review notes — workflow-bazel-protocol

## scope-1

File: implementation-log.md (whole document); design.md "Test plan" bullet
"Misconfiguration coverage" (design.md:263-267).

Expected: design's test plan explicitly calls for covering two analysis-time
`fail()` paths — `python_extension = False` with `protocol_module` set, and
`protocol = True` with empty `protocol_module` — via an automated
analysis-failure harness if one exists, or, if none exists, documented as
manual `bazel build` expectations.

Actual: no `bazel_skylib`/`analysistest` harness exists anywhere in the repo
(confirmed by grep across `*.bzl`/`BUILD.bazel`/`MODULE.bazel`), and neither
BUILD.bazel nor implementation-log.md records a manual `bazel build` run
against either misconfigured case. The `fail()` guards themselves are present
in rust.bzl (both at the internal rule, rust.bzl:123-124, and duplicated in
the macro, rust.bzl:583-584, 589-600), so the code exists — only the
verification/documentation step from the test plan is missing. Grepping the
repo for `generate_rust_parser`/`python_extension` usage outside rust.bzl and
BUILD.bazel turns up nothing, confirming these paths are exercised nowhere.

Consequence: low — the guards are simple, direct `if cond: fail(...)`
statements, easy to eyeball for correctness, so the risk of a silently broken
guard is small. But the design called this out as an explicit test-plan item,
and its omission is undocumented (no TODO, no log entry saying "skipped
because X"), so a future reader has no record that this was considered and
consciously deferred vs. simply forgotten.

Suggested fix: add a short note to implementation-log.md (or a comment in
BUILD.bazel) recording either (a) manual `bazel build` output showing both
misconfigurations fail with the expected message, or (b) an explicit
statement that this was left unverified and why. This is a small
documentation/verification task, not new implementation — well within
respond-mode.

## Everything else

Diff was checked increment-by-increment against design.md §1-§4 and the Edge
cases / Test plan sections:

- Toggle rename `generate_protocol` -> `protocol` (design §1): done, matches.
- Internal rule split (`_generate_rust_srcs`), `extension_name` attribute,
  `OutputGroupInfo` with `rust_srcs`/`stub_srcs` groups (design §2): all
  present in rust.bzl and match the specified behavior, including the
  empty-depset self-gating for `stub_srcs`.
- Public `generate_rust_parser` macro, both modes, signature, and the
  `fail()` edge-case guards (design §2 "Edge cases"): all present and match.
- `fltk_pyo3_cdylib` -> private `_build_pyo3_cdylib`, BUILD.bazel `load()`
  updated to drop the public name, doc-string references updated, `lib.rs`
  hazard reframed as internal invariant (design §3): matches.
- BUILD.bazel in-tree targets rewritten to the macro, both pure-Rust and
  Python-extension (with `protocol_module`/`protocol` set) smoke targets
  present (design §4): matches.
- Pre-existing, out-of-scope `gen-rust-parser` regex-portability failure on
  `bootstrap.fltkg` (confirmed identical at base commit) is explicitly
  called out in implementation-log.md, BUILD.bazel comment, and TODO.md
  under `bazel-rust-smoke-bootstrap-regex` (both TODO.md entry and code
  comment present, per the project's TODO convention) — this is a properly
  justified, well-documented punt, not a finding.
- No bonus work beyond what design specifies (the `data` param added to
  `_build_pyo3_cdylib` is called out in the log and is the minimal extension
  needed to route `stub_srcs` onto the public `py_library`, per design §2
  "Stub exposure").

No aggregate scope gap large enough to warrant escalation — scope-1 is a
single small verification/documentation gap, well within respond-mode.
