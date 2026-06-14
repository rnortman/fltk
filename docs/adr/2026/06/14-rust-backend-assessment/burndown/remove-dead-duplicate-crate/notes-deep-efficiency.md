# Deep efficiency review — `remove-dead-duplicate-crate`

Base: `9f96d43dc613308332d00bdf7d2436a2abca5416`
HEAD: `f1e1fef110c3114305f7664e91f2d9d14455fafc`

## Scope of the change

Pure deletion + doc fixup:

- Removed `tests/rust_cst_fegen/` (`Cargo.lock`, `Cargo.toml`, `src/cst.rs` 15515 lines,
  `src/lib.rs`, `src/parser.rs`, `src/native_parser_tests.rs`) — a git-tracked,
  name-colliding (`fegen-rust-cst` / `fegen_rust_cst`) duplicate of `crates/fegen-rust/`
  that was on zero build/test/deny/gencode lanes.
- Dropped a stale "Promoted from tests/rust_cst_fegen/" comment in
  `crates/fegen-rust/Cargo.toml`.
- Fixed stale references in `CHANGELOG.md` and `docs/rust-cst-extension-guide.md`.

No runtime, generator, parser, or build-recipe logic changed. The diff touches no
startup path, per-request/per-render path, polling loop, data structure, or concurrency
surface — nothing in the efficiency lane to regress.

## Verification performed

- `git ls-tree -r f1e1fef -- tests/rust_cst_fegen/` returns empty: deletion complete in
  the commit; only an untracked/gitignored `target/` build-artifact dir lingers on disk.
- `git grep rust_cst_fegen f1e1fef` (excluding this ADR tree): all surviving matches are
  in immutable historical ADR docs under `docs/adr/...`, none in any active
  build/test/gencode/deny lane. Current-tree `Makefile` references `crates/fegen-rust/`
  exclusively (`build-fegen-rust-cst`, `gencode` step at `Makefile:274`).
- Test consumers (`tests/test_phase4_fegen_rust_backend.py`, `tests/test_fegen_rust_cst.py`,
  etc.) `importorskip("fegen_rust_cst")` — the Python module name produced by
  `make build-fegen-rust-cst`, which builds the live `crates/fegen-rust/`. Deleting the
  duplicate directory does not change the module those tests resolve.

## Findings

No findings.

This deletion is strictly net-positive for efficiency: it removes ~17K LoC of
never-built checked-in source plus a `Cargo.lock`, reducing clone/checkout cost and repo
size, and eliminates a latent module-shadowing hazard. No wasted work, no missed
concurrency, no hot-path bloat, no no-op updates, no existence-check or memory issues are
introduced.
