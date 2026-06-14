# Deep correctness review — remove-dead-duplicate-crate

Commit reviewed: f1e1fef (base 9f96d43dc613308332d00bdf7d2436a2abca5416)
Scope: deletion of `tests/rust_cst_fegen/` + fix of stale refs in CHANGELOG.md,
`crates/fegen-rust/Cargo.toml` comment, and `docs/rust-cst-extension-guide.md`.

## Verdict

No findings.

## What was verified (logic / data-flow / invariant traces)

1. **Deleted crate was genuinely dead — no build/data-flow edge severed.**
   - Not in root workspace `members` (base root `Cargo.toml` lists only `.`,
     `crates/fltk-cst-core`, `crates/fltk-cst-spike`, `crates/fltk-parser-core`).
   - Deleted `tests/rust_cst_fegen/Cargo.toml` declared its own empty `[workspace]`
     (standalone, excluded from root). Its comment claimed "see Makefile
     build-fegen-rust-cst", but that Makefile target (line 205-206) `cd`s into
     `crates/fegen-rust`, NOT the deleted dir — concretely confirming it had
     fallen off every lane.
   - No Makefile target, no Bazel BUILD/.bzl, no gencode step references it at base.

2. **"byte-identical copy" claim is imprecise but harmless.** The deleted
   `src/cst.rs` differed from canonical `crates/fegen-rust/src/cst.rs` by exactly
   the 2-line generated-do-not-edit header (the `cst-generated-header` fix landed
   on canonical only). The surviving copy is the strictly-more-correct one; the
   stale copy carried no unique logic. Deletion loses nothing.

3. **Name-collision hazard real and resolved.** Both crates declared
   `name = "fegen-rust-cst"` / `[lib] name = "fegen_rust_cst"`. At HEAD the module
   name `fegen_rust_cst` is produced by exactly one crate (`crates/fegen-rust`).
   All `fegen_rust_cst` references (Makefile, lib.rs, py_module.rs, stubs,
   plumbing.py, tests) now resolve unambiguously to the survivor.

4. **No dangling references introduced.** At HEAD, `git grep rust_cst_fegen`
   outside `docs/adr/**` returns NONE. Remaining hits live only in the immutable
   2026/05/28 ADR history docs — correctly left untouched (ADRs are immutable
   historical record, not active refs). The three non-historical refs the spec
   named (CHANGELOG, fegen-rust Cargo.toml comment, extension guide) were all fixed.

5. **New CHANGELOG factual claim is accurate.** Edit now asserts `make gencode`
   regenerates `crates/fegen-rust/src/cst.rs` and `tests/rust_cst_fixture/src/cst.rs`.
   gencode target confirms both: line 274 (fegen-rust cst.rs) and line 272
   (rust_cst_fixture cst.rs). The old claim it replaced ("regenerates
   tests/rust_cst_fegen/src/cst.rs") was already stale at base — base Makefile had
   no such step. The edit corrects a false statement rather than introducing one.

6. **Deletion is complete.** `git ls-tree f1e1fef -- tests/rust_cst_fegen` is empty;
   no orphaned files remain under the deleted path.

Deletion-only change with three doc edits; control flow / data flow of the
build graph remains consistent. Clean.
