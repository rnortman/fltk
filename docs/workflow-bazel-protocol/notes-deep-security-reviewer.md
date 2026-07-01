# Security review — workflow-bazel-protocol

Commit reviewed: 224344d844feeefa7acdb8f4eaa285322a70634d (base 3c244d1)
Scope: BUILD.bazel, rust.bzl (Bazel/Starlark build-layer refactor), plus docs/TODO.

## Findings

No findings.

## Rationale

The diff is a pure Bazel authoring-surface refactor:
- Renames the `generate_rust_parser` rule to a private `_generate_rust_srcs`
  rule and introduces a public `generate_rust_parser` macro; renames
  `fltk_pyo3_cdylib` to private `_build_pyo3_cdylib`.
- Renames the `generate_protocol` bool attr to `protocol`.
- Adds an `extension_name` attr and `OutputGroupInfo` (`rust_srcs` /
  `stub_srcs`) routing via two `native.filegroup`s.
- Rewrites the two in-tree smoke targets in BUILD.bazel.

No runtime trust boundary is touched. All interpolated string values
(`name`, `extension_name`, `protocol_module`, `cst_mod_path`) originate from
BUILD-file authors, who already have full build-execution authority — not an
untrusted-input boundary. The genrule `cmd` body that assembles the crate is
unchanged (only surrounding doc comments changed); no new shell interpolation
of external/untrusted data was introduced. `fail()` guards (protocol without
protocol_module; python-extension-only knobs set in pure-Rust mode) tighten,
not loosen, misconfiguration handling.

No injection, secrets, auth/authz, crypto, path-traversal, SSRF,
deserialization, timing, or over-permissive-default surface appears in the
changed code.
