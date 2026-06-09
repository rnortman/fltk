# Design review findings: fegen-cst-rs-single-source

Reviewed `design.md` against `request.md`, `exploration.md`, the staleness update, and source at HEAD `af6e6f3`.

Verified correct (no finding): md5 `4bff0dbe...` / 6857 lines for both copies; `src/cst_fegen.rs:1-6` opens with `use` items (no inner attributes); `realpath --relative-to=tests/rust_cst_fegen/src src/cst_fegen.rs` → `../../../src/cst_fegen.rs`; `src/lib.rs:4` (`mod cst_fegen;`) and `:34` (`cst_fegen::register_classes`); `tests/rust_cst_fegen/src/lib.rs:12,13,15,21`; `tests/rust_cst_fegen/Cargo.toml:20` (`fltk-cst-core` dep); `Makefile:45-46` (clippy), `:64-65`, `:69-70`, `:105`, `:108-109` (gencode duplicate step + `TODO(slug)` comment); `make check` steps contain no `cargo fmt`; change 4 leaves the `tests/rust_cst_fixture` gencode step (`Makefile:106-107`) untouched per the "do NOT touch rust_cst_fixture" constraint; the design's correction that the `TODO(slug)` comment lives in the Makefile, not `cst.rs`, is right (grep: slug appears only in `TODO.md` and `Makefile:108` outside docs/adr). All request.md acceptance items map to design changes 1-4 and test-plan steps 1-5. Since `cst.rs` is currently byte-identical to `src/cst_fegen.rs` and already compiles as `mod cst`, the `include!` produces an identical token stream — compile success is near-certain, and cargo's dep-info tracking of `include!`d files means edits to `src/cst_fegen.rs` correctly trigger test-crate rebuilds, supporting the design's "necessarily changes the test crate's compiled output" claim.

## design-1: TODO.md line citation is wrong — points at the `rust-cst-pyi` entry

- **Where:** design.md "Root cause / context" (`TODO.md:23-25`) and "Edge cases / TODO bookkeeping" ("The `TODO.md` entry (`:23-25`) is removed in the same commit").
- **What's wrong:** At HEAD `af6e6f3` the `## fegen-cst-rs-single-source` entry is at `TODO.md:19-21`. Lines 23-25 are the `## rust-cst-pyi` entry (heading at `:23`, body at `:25`). The staleness update (`expl-staleness-...md`) carries the same wrong citation ("`TODO.md:23-25`: entry ... still present verbatim"), which the design inherited without verification.
- **Consequence:** An implementer trusting the cited lines deletes the wrong TODO entry — `rust-cst-pyi` (a live, unrelated deferred item) gets removed and `fegen-cst-rs-single-source` stays. The design's own post-condition (`grep -r 'fegen-cst-rs-single-source'` returns nothing) catches the leftover entry, but nothing catches the collateral deletion of `rust-cst-pyi`.
- **Fix:** Cite `TODO.md:19-21`, or better, identify the entry by slug heading rather than line number.

## design-2: "all three test files via importorskip" — one of the three uses a different gating mechanism

- **Where:** design.md "Root cause / context": "consumed by `tests/test_phase4_fegen_rust_backend.py`, `tests/test_clean_protocol_consumer_api.py`, `tests/test_cross_backend_label_equality.py` via `importorskip(\"fegen_rust_cst\")`."
- **What's wrong:** `test_phase4_fegen_rust_backend.py:29` and `test_cross_backend_label_equality.py:24` do use `pytest.importorskip`. `test_clean_protocol_consumer_api.py` does not — it uses a try/except import (`:46-50`) plus `pytest.mark.skipif` (`:53-55`), and some of its tests exercise `fegen_rust_cst` indirectly via `parse_grammar_file(..., rust_fegen_cst_module="fegen_rust_cst")` (`:340`). The claim is inherited verbatim from `request.md`/`exploration.md` without re-verification.
- **Consequence:** Minor; the gating behavior is equivalent (tests skip when the extension is unbuilt), so test-plan step 2 still works. But the design presents an unverified claim as fact in a doc that asserts HEAD re-verification; if the skipif marker were ever incomplete, "tests pass" could mean "tests silently skipped" — the test plan does not require confirming the three files actually *ran* (non-skipped) against the freshly built include-based extension.
- **Fix:** Correct the mechanism description; in test-plan step 2, add "confirm the runs are not skips (extension built first via `make build-fegen-rust-cst`)".

## design-3: stale "not a Cargo workspace" premise left uncorrected — root `Cargo.toml` is now a workspace

- **Where:** design.md relies on `exploration.md` ("The three Cargo crates ... are **not** in a Cargo workspace — no `[workspace]` key appears in any of them") and on request.md's load-bearing constraint phrased the same way; design.md:52/64 reason about clippy/cargo scope from crate independence.
- **What's wrong:** At HEAD, root `Cargo.toml:1-3` declares `[workspace] members = [".", "crates/fltk-cst-core"]` (introduced by `4c8f0ad`, last commit touching `Cargo.toml`). `tests/rust_cst_fegen/Cargo.toml:3` and the fixture crate carry an empty `[workspace]` table specifically to opt out of the root workspace. The staleness update did not flag this, and the design repeats neither correction.
- **Consequence:** Low for this change — the design's operative claims still hold (root `cargo check/clippy/test` cover only `fltk-native` + `fltk-cst-core`; the test crate stays excluded; no new workspace is introduced), but they hold *because of* the empty `[workspace]` opt-out, a mechanism the design never mentions. An implementer who "cleans up" the seemingly pointless empty `[workspace]` table in `tests/rust_cst_fegen/Cargo.toml` (it has only a brief comment) would break the build (cargo errors on a non-member crate inside a workspace directory), and nothing in the design warns against it. The request's "NOT a Cargo workspace" constraint is also now factually wrong as stated and should be read as "do not add the test crates to a workspace."
- **Fix:** Add one line to the design noting the root workspace exists, the test crate opts out via its empty `[workspace]` table (`tests/rust_cst_fegen/Cargo.toml:3`), and that this opt-out must be preserved.

## Nits (no separate findings)

- design.md:14 cites `gencode` as `Makefile:80-119`; the Makefile is 118 lines — target spans `:80-118`. Off-by-one, harmless.
- Test-plan step 3's phrase "cpp-expanded include" is loose (no C preprocessor involved); the step is correctly characterized as true by construction.
