# Security review — rust-bazel-packaging

Commits reviewed: fltk fafa6d7..36eda0d, clockwork ece332a..45bc7fe

Scope of change: Bazel/Rust packaging only. New `rust.bzl` (a rule +
a macro), per-crate `BUILD.bazel` files, `MODULE.bazel` additions
(rules_rust dep, crate_universe hub, rust toolchain registration), and
a Clockwork-side cdylib target + roundtrip py_test. No application
runtime code, no network-facing endpoints, no auth surfaces, no
secret handling, no deserialization of untrusted data. The only
"untrusted input" in scope (grammar files, target names) is
repo-author-controlled build configuration; running Bazel already
implies executing this code locally. No external attacker trust
boundary is crossed by this diff.

No findings.

## Notes (non-findings, considered and cleared)

- `fltk_pyo3_cdylib` genrule shell `cmd` (rust.bzl ~line 215) loops
  over `$(locations rs_srcs)` and `cp`s by `basename`. Label/location
  expansions are Bazel-controlled paths, not attacker strings; macro
  args (`name`, `lib_rs`, `rs_srcs`) are BUILD-author-supplied. No
  injection boundary — this is the same trust level as any BUILD file.
- Dependency sourcing is pinned: `fltk` via git commit SHA;
  `rules_rust` via BCR SINGLE_VERSION_OVERRIDE (0.70.0); rust toolchain
  1.87.0 download-prebuilt (rules_rust verifies its own SHAs);
  third-party crates via checked-in `Cargo.lock` through
  crate_universe `from_cargo`. No unpinned/mutable fetches introduced.
- `native_py` / cdylib `py_library` set `imports = ["."]` and ship a
  `.so` on the import path. Standard packaging; no world-writable or
  over-permissive resource created.
- No secrets in the diff.
