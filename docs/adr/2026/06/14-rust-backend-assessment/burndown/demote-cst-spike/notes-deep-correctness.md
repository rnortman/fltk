# Deep correctness review — demote-cst-spike

Commit reviewed: be08c47 (base e813764). Focus: build/workspace correctness after the
`crates/fltk-cst-spike` deletion — workspace members, Makefile lanes, MODULE.bazel, deny.toml,
and that the ported tests build and run in `tests/rust_poc_cst`'s python-off lane.

## Verification performed (all green)

- Workspace members: `cargo metadata --no-deps` resolves to exactly `fltk-native`, `fltk-cst-core`,
  `fltk-parser-core`. Root `Cargo.toml` `members` no longer lists `crates/fltk-cst-spike`. Spike
  directory is gone. `cargo build -q` (full workspace) exits 0.
- Cargo.lock: no `fltk-cst-spike`/`fltk_cst_spike` entry remains (no dangling member).
- Ported tests: `tests/rust_poc_cst/src/spike_tests.rs` is byte-for-byte the spike's old test file;
  `lib.rs` adds `#[cfg(test)] mod spike_tests;`. The tests reference `crate::cst::{...}`, which now
  resolves to `tests/rust_poc_cst/src/cst.rs`. That `cst.rs` is byte-identical to the deleted
  `crates/fltk-cst-spike/src/cst.rs` (diff -q: identical), so every symbol the tests import exists.
- Python-off lane runs the tests: `cargo test --manifest-path tests/rust_poc_cst/Cargo.toml
  --no-default-features` → 43 passed, 0 failed. `--list` confirms all 43 are `spike_tests::*` (the
  full ported suite actually executes; none silently filtered). This lane pre-existed (Makefile:140),
  so the spike's python-off coverage is genuinely preserved at the destination.
- Python-on compile coverage preserved: `cargo test --manifest-path tests/rust_poc_cst/Cargo.toml
  --no-run` (default = extension-module/python) exits 0 — the test module compiles with python on,
  matching what the deleted spike's `--features python` clippy lane used to cover.
- Makefile: the three spike lines removed from `cargo-test-no-python`, `cargo-clippy-no-python`,
  and `check-no-pyo3` were standalone; the surrounding `&&`/`;`-chained recipe bodies remain valid
  (the deleted `check-no-pyo3` block was a self-contained `out=...; grep; grep` stanza, leaving the
  `@set -e; \` continuation intact for the `core=...` block that follows). `make check-no-pyo3`
  runs clean: "pyo3 absent from python-off graphs". The `cp` line in `gencode` is removed; the
  destination `cst.rs` is now the sole copy (regenerated directly at Makefile:268).
- MODULE.bazel: the `manifests` list is unchanged and already listed only root + cst-core +
  parser-core — the spike never had an explicit manifest entry; it entered the `@fltk_crates` hub
  only transitively via root `[workspace] members`. Dropping it from `members` is exactly what
  removes it (and its `criterion` dev-dep) from the hub. The rewritten membership comment now
  accurately describes the three-member workspace. `TODO(bazel-cst-spike-hub)` removed from both the
  comment and TODO.md.
- benches/traverse.rs + criterion: fully gone. No `[[bench]]`, `criterion`, or `traverse` reference
  remains in any live `*.toml` or `Cargo.lock` (the spike's `[[bench]]`/dev-dep lived only in the
  deleted crate manifest, so no dangling target). deny.toml comment updated to drop the spike.

## Findings

No correctness findings in the build/workspace lane. The deletion is internally consistent:
workspace resolves cleanly, the ported suite compiles and passes in both the python-off and
python-on lanes, and no dangling references to the removed crate/bench/dev-dep survive in any
build-relevant file.

## Out-of-lane note (not a build-correctness defect)

- `CHANGELOG.md:28` still names `crates/fltk-cst-spike/src/cst.rs` in a historical release entry's
  list of regenerated outputs. This is a past-release record, not a build input, and editing it
  would rewrite changelog history — flagged only for awareness; it does not affect any build.
- The stale git worktree at `.claude/worktrees/agent-ab295be24eef6e7ce/` still contains the old
  spike files. It is unrelated to this commit and not part of the tracked tree; ignore.
