# demote-cst-spike — user decision + scope pointer

Captured by the orchestrator. This is a **fast-track** (no design cycle): implement from the
`demote-cst-spike` entry in `recommended-actions.md` (lines ~155-167) + the user directive below.
Then full pre-pass + deep review, then squash. Queued in the serialized impl lane (behind the spike
and fix-forged-abi-segfault).

## User directives (verbatim, 2026-06-14)

> Wait, demote-cst-spike says it's blocked on the perf harness but that's BS. It has nothing to do with
> perf measurement. We just need to fix that one.

> Delete the traverse.rs benchmark.

## Scope (per recommended-actions.md + a source-grounded survey)

- The "blocked on perf-harness" dependency is **spurious** — confirmed actionable now. perf-harness builds a
  new end-to-end harness; it does not consume the spike's bench. No real handoff.
- `crates/fltk-cst-spike/src/cst.rs` is **byte-identical** to `tests/rust_poc_cst/src/cst.rs`, kept in sync by
  a literal `cp` in the Makefile. Fold the spike into `tests/rust_poc_cst`, delete the standalone crate and its
  root-workspace membership, kill the `cp`.
- **Delete `benches/traverse.rs` outright** (per user directive) — do NOT relocate it; the `criterion` dev-dep
  then vanishes entirely, removing its leak into the downstream-facing Bazel crate hub.
- Resolves `TODO(bazel-cst-spike-hub)`.
- Likely file footprint (implementer to confirm): delete `crates/fltk-cst-spike/`; edit root `Cargo.toml`
  (`[workspace] members`), `Makefile` (spike test/clippy/cargo-tree/`cp` lanes), `MODULE.bazel`, `deny.toml`,
  `TODO.md` (remove the resolved `bazel-cst-spike-hub` entry), `Cargo.lock`. Preserve the python-off compile/test
  coverage the spike exercised (the destination `tests/rust_poc_cst` already has its own python-off lane).
- Analogous to the already-shipped `remove-dead-duplicate-crate` (commit a4b35b8), which deleted the *other*
  duplicate (`tests/rust_cst_fegen/`).
