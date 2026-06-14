quality-1

File: Makefile:4, Makefile:94

`build-fegen-rust-cst` was updated by this commit to build from `crates/fegen-rust/` (correct)
and kept as a valid Makefile target. However, the `.PHONY` line (line 4) and the
`build-test-fixtures` dependency list (line 94) still list `build-fegen-rust-cst`. That is
intentional and correct — the target still exists and builds `crates/fegen-rust/`. No issue
here; confirming it is not stale.

---

quality-2

File: TODO.md — no entry; worktree agent-ab295be24eef6e7ce/TODO.md:9 references
`tests/rust_cst_fegen` in the `pyo3-upgrade` entry ("Bump pyo3 across all six manifests
(root, `crates/fltk-cst-core`, `crates/fltk-cst-spike`, `tests/rust_cst_fegen`,
`tests/rust_cst_fixture`, `tests/rust_parser_fixture`)").

The worktree copy of TODO.md is a stale branch artifact and does not affect the main-branch
working tree. The main-branch TODO.md has no such reference. No issue on main.

---

quality-3

File: CHANGELOG.md:23

The updated CHANGELOG line reads:

  `make gencode` regenerates all Rust outputs in sync (`crates/fegen-rust/src/cst.rs`,
  `tests/rust_cst_fixture/src/cst.rs`, etc.).

The `etc.` hides five additional outputs that `make gencode` actually regenerates:
`tests/rust_poc_cst/src/cst.rs`, `tests/rust_parser_fixture/src/cst.rs`,
`tests/rust_parser_fixture/src/parser.rs`,
`tests/rust_parser_fixture/src/collision_cst.rs`,
`tests/rust_parser_fixture/src/collision_parser.rs`, and
`crates/fltk-cst-spike/src/cst.rs`. The pre-deletion text listed only
`tests/rust_cst_fegen/src/cst.rs` (now gone) as the canonical example of "all five Rust
outputs", so the new text fixes the false claim about the deleted path but substitutes
loose `etc.` for precision.

**Consequence:** A reader trying to audit gencode coverage cannot tell from the changelog
which outputs are covered. The vagueness also makes it harder to notice when a future
commit drops an output from `gencode` without updating the changelog — the same drift
pattern this burndown item was created to fix.

**Fix:** Expand the parenthetical to list the actual set, or drop it and say "all Rust
outputs (see `make gencode` in Makefile for the full list)."

---

quality-4

File: docs/rust-cst-extension-guide.md:174

The updated guide section now reads:

  `tests/rust_cst_fixture/` follows this exact pattern and serves as a working example.
  Build it with `make build-test-user-ext`.

The `build-test-user-ext` target (Makefile:198) builds `tests/rust_cst_fixture/` with
`maturin develop` — accurate. However, `crates/fegen-rust/` is now the higher-fidelity
example of what a real fegen-grammar user extension looks like (it uses the fegen grammar
itself, has a `.pyi` stub, and covers the `python` feature flag). Pointing only at the
fixture crate as "the example" undersells a more realistic reference.

**Consequence:** Users following the guide as the entry point to building their own
extension miss the more complete example. Low immediate harm, but the guide was already
noting two examples pre-deletion; the removal leaves only the simpler one without
acknowledging the richer one exists.

**Fix:** Add a sentence noting that `crates/fegen-rust/` (built via `make build-fegen-rust-cst`)
is also a working example, one that includes a `.pyi` stub and the `extension-module`/`python`
feature split.

---

No other quality findings. The deletion itself is clean: no remaining tracked references
to `tests/rust_cst_fegen/` in Makefile, deny.toml, TODO.md, or any non-ADR source file
on the main branch. The stale comment that was removed from `crates/fegen-rust/Cargo.toml`
("Promoted from tests/rust_cst_fegen/") is correctly gone.
