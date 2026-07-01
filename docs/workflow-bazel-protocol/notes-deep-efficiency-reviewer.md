# Efficiency review — workflow-bazel-protocol

Commit reviewed: 224344d844feeefa7acdb8f4eaa285322a70634d (base 3c244d1)
Files: rust.bzl, BUILD.bazel (plus docs/TODO — non-code).

No findings.

Rationale: the change is a Bazel Starlark refactor (split `generate_rust_parser`
rule into an internal `_generate_rust_srcs` rule + public macro; demote
`fltk_pyo3_cdylib` to `_build_pyo3_cdylib`). All cost is build-graph analysis /
action-execution time, not any runtime hot path. The diff adds and removes no
codegen actions — the same `gen-rust-cst` / `gen-rust-parser` genparser
invocations run as before. The macro instantiates a fixed number of targets (no
loops, no N+1). The two `filegroup`s (`_rust_srcs`, `_stub_srcs`) are cheap
provider views over a single `:name_srcs` target; Bazel executes that codegen
target once and the output groups do not re-run actions. In pure-Rust mode
`stub_outputs` stays empty, so no stub files are declared or produced.
