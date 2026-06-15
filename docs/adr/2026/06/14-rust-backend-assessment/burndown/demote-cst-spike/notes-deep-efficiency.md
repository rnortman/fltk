# Deep efficiency review — demote-cst-spike

Commit reviewed: be08c47 (base e813764). Diff is a pure deletion/consolidation:
delete `crates/fltk-cst-spike/`, fold its tests into `tests/rust_poc_cst`, drop the
`criterion` bench, and prune the build/config references.

## efficiency-1 — Stale tracked `MODULE.bazel.lock` still pins the deleted crate + `criterion`

- File: `MODULE.bazel.lock` (tracked; 11 lines still match `fltk-cst-spike`/`criterion`,
  e.g. line ~482 `FILE:@@//crates/fltk-cst-spike/Cargo.toml ...`, plus `criterion-0.5.1`
  aliases generated into the hub BUILD).
- Problem: This lockfile is the generated, committed companion to `MODULE.bazel`. The
  change edited `MODULE.bazel`, `Cargo.toml`, and `Cargo.lock`, but the Bazel lock was
  not regenerated, so it still seeds the `@fltk_crates` hub from the now-deleted
  `crates/fltk-cst-spike/Cargo.toml` and still materializes `criterion` (the very dep
  the spec says "vanishes entirely, removing its leak into the downstream-facing Bazel
  crate hub"). The stated efficiency goal of the change — pulling `criterion` and its
  transitive tree out of the downstream Bazel hub — is not actually realized in the
  committed lock.
- Consequence: Bazel consumers (Clockwork and other out-of-tree users that resolve
  `@fltk_crates` from this lock) still fetch/build the `criterion` subtree and reference
  a `Cargo.toml` path that no longer exists. The leak the change set out to close remains
  open until the lock is regenerated; at best a stale-lock mismatch surfaces at the next
  `bazel mod` resolution. Cost shows up at downstream build/resolve time, not in-tree
  (hence not caught by the Makefile cargo lanes).
- Fix: Regenerate and commit the Bazel lock (`bazel mod deps --lockfile_mode=update`, or
  the project's equivalent regen command) so `fltk-cst-spike` and `criterion` drop out of
  it, matching the already-updated `Cargo.lock` and `MODULE.bazel`. If the lock is
  intentionally left for a separate Bazel-regen step, note that explicitly — otherwise the
  in-tree artifacts and the downstream-facing lock disagree.

## Notes (no finding)

- Folding the spike removed the `cp tests/rust_poc_cst/src/cst.rs crates/fltk-cst-spike/src/cst.rs`
  step from `gencode` and collapsed two byte-identical 3190-line `cst.rs` copies into one.
  That is a net reduction in duplicated build/codegen work, not a regression — correct
  direction.
- `spike_tests.rs` is wired under `#[cfg(test)] mod spike_tests;`, so it adds no per-build
  or runtime cost to the shipped `rust_poc_cst` artifact — test-only, as intended.
- Makefile prunes (`cargo-test-no-python`, `cargo-clippy-no-python` x2, `check-no-pyo3`
  positive-control block) remove now-redundant per-CI cargo invocations; the surviving
  fltk-cst-core / rust_poc_cst lanes still exercise the same python-off invariant. No
  coverage-for-cost regression.
