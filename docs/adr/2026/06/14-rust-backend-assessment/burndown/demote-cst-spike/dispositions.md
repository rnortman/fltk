# Dispositions — demote-cst-spike respond round 1

## errhandling

No findings.

## correctness

No findings.

## security

No findings.

## test-1
- Disposition: Fixed
- Action: Added `#![cfg_attr(not(feature = "python"), forbid(unsafe_code))]` to `tests/rust_poc_cst/src/lib.rs:9`. Matches the attribute present in the deleted `crates/fltk-cst-spike/src/lib.rs`. Python-off tests (43) still pass.
- Severity assessment: Without this attribute, a future unsafe block introduced in `cst.rs` or `spike_tests.rs` in the python-off configuration would compile silently; the regression would be invisible to both `cargo test` and CI.

## test-2
- Disposition: Won't-Do
- Action: no change
- Severity assessment: The two clippy passes (cargo-clippy with default features = python-on, cargo-clippy-no-python with --no-default-features = python-off) together provide full coverage of both configurations. No coverage is actually lost.
- Rationale (Won't-Do): The finding itself says this is "informational rather than a blocking finding" with "no coverage actually lost." The structural split (python-on in cargo-clippy, python-off in cargo-clippy-no-python) is already explicit in the target names and is clarified by the quality-2 comment fix applied to cargo-clippy-no-python. Adding anything further here would actively harm clarity by creating a redundant note in a second location that could drift independently.

## reuse

No findings.

## quality-1
- Disposition: Fixed
- Action: Replaced stale `cargo test -p fltk-cst-spike` invocation in `tests/rust_poc_cst/src/spike_tests.rs:4-5` with the current correct command `cargo test --manifest-path tests/rust_poc_cst/Cargo.toml --no-default-features`.
- Severity assessment: A developer following the old command gets a confusing cargo error ("package ID specification `fltk-cst-spike` did not match any packages"); the correct invocation is now visible at the point of use.

## quality-2
- Disposition: Fixed
- Action: Added comment after the `tests/rust_poc_cst` line in the `cargo-clippy-no-python` Makefile target (Makefile:148) stating "python-on clippy for rust_poc_cst is covered by cargo-clippy (default features = extension-module)". Makes the coverage split explicit rather than relying on implicit knowledge.
- Severity assessment: Without the comment, a future auditor of cargo-clippy-no-python may incorrectly conclude the python-on path is unchecked and add a redundant or wrong invocation.

## efficiency-1
- Disposition: Fixed
- Action: Regenerated `MODULE.bazel.lock` via `bazel mod deps --lockfile_mode=update`. The lock shrank by ~620 lines; `grep` confirms zero remaining matches for `fltk-cst-spike` or `criterion`. The stated goal of the change — removing criterion and the spike from the downstream-facing Bazel crate hub — is now realized in the committed lockfile.
- Severity assessment: Until fixed, the `@fltk_crates` Bazel hub still materialized `criterion` and referenced the now-deleted `crates/fltk-cst-spike/Cargo.toml` path, meaning downstream Bazel consumers would hit a stale-lock resolution failure and the criterion dep leak the change set out to close would remain open.
