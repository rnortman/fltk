# Judge verdict — deep review (burndown: remove-dead-duplicate-crate)

Phase: deep (skip-design fast-track). Base 9f96d43..HEAD 5bc28c3. Round 1.
Spec: ELI5/companion section `remove-dead-duplicate-crate` in `docs/adr/2026/06/14-rust-backend-assessment/`.
Notes: 7 reviewer files. 4 findings (all quality lens); errhandling / correctness / security / test / reuse / efficiency all "No findings."

Change shape: pure deletion of `tests/rust_cst_fegen/` (6 tracked files, ~17.5K lines) + three text fixups (CHANGELOG.md, `crates/fegen-rust/Cargo.toml` provenance comment, `docs/rust-cst-extension-guide.md`). No added TODOs in the diff → no TODO walk.

## Other findings walk

### quality-1 — Won't-Do
Reviewer claim: `.PHONY` (Makefile:4) and `build-test-fixtures` dep list (Makefile:94) still list `build-fegen-rust-cst`. Consequence: none stated — the reviewer's own text says "That is intentional and correct... No issue here; confirming it is not stale."
Disposition: Won't-Do, "self-resolved by reviewer."
Evidence: `git show 5bc28c3:Makefile` line 4 and line 94 both list `build-fegen-rust-cst`; the target at line 205 builds `crates/fegen-rust/` (the survivor), so the references are live and correct.
Assessment: finding states no consequence and the reviewer self-retracts. Per process, a finding with no consequence → responder wins by default. Won't-Do correct. Accept.

### quality-2 — Won't-Do
Reviewer claim: a worktree artifact (`agent-ab295be24eef6e7ce/TODO.md:9`) references `tests/rust_cst_fegen` in the `pyo3-upgrade` entry. Consequence: none on main — reviewer states "The main-branch TODO.md has no such reference. No issue on main."
Disposition: Won't-Do, "stale branch artifact, not on main."
Evidence: `git grep rust_cst_fegen 5bc28c3` outside `docs/adr/**` returns NO MATCHES — confirming main-tree `TODO.md` carries no such reference at HEAD. The cited path is a `.claude/worktrees/...` artifact, out of scope and not part of this commit's tree.
Assessment: changing a main-branch file to "fix" a worktree artifact would be incorrect (false premise that there is anything to fix on main). Won't-Do correct. Accept.

### quality-3 — Fixed
Reviewer claim: replacement CHANGELOG text used `etc.` which hid five `gencode` outputs (`rust_poc_cst/cst.rs`, `rust_parser_fixture/{cst,parser,collision_cst,collision_parser}.rs`, `fltk-cst-spike/cst.rs`). Consequence: a reader auditing gencode coverage cannot tell which outputs are covered; vagueness reproduces the same drift pattern this burndown item exists to fix. Real (low-severity should-fix), consequence stated.
Disposition: Fixed — CHANGELOG.md:22-28, replaced `etc.` with an explicit list of eight Rust outputs plus a pointer to the Makefile `gencode` target as the authoritative list.
Evidence (diff at CHANGELOG.md): new text reads "`make gencode` regenerates all Rust outputs in sync (see `gencode` target in Makefile for the full list; includes ...)" followed by the eight paths. Cross-checked the eight against `Makefile` gencode body (lines 270-288): all eight present and correctly named. The reviewer expressly sanctioned this exact alternative ("or drop it and say 'all Rust outputs (see `make gencode` in Makefile for the full list)'").
Note (not a defect): gencode actually emits two more Rust artifacts the inline list omits — `src/lib.rs` (`_native` span-only wiring, Makefile:266) and `crates/fegen-rust/src/parser.rs` (via `build-fegen-rust-parser`, Makefile:277). Under a strict exhaustive-list reading this would be incomplete. But the responder did not commit to an exhaustive list: the operative phrasing is "all Rust outputs ... see `gencode` target in Makefile for the full list ... includes". The Makefile is named as the single authoritative source and "includes" marks the inline set as illustrative. This is precisely the reviewer's accepted fix form, so the residual omission does not constitute drift-by-changelog and is not a basis for REWORK.
Assessment: fix addresses the stated consequence at the named line; authoritative pointer closes the audit gap. Accept.

### quality-4 — Fixed
Reviewer claim: post-deletion the extension guide pointed only at `tests/rust_cst_fixture/` as "the example," dropping the richer `crates/fegen-rust/` reference (which carries a `.pyi` stub and the `extension-module`/`python` feature split). Consequence: users entering via the guide miss the more complete, realistic reference. Real (low-severity should-fix/nit), consequence stated.
Disposition: Fixed — docs/rust-cst-extension-guide.md:174-178, added a sentence pointing at `crates/fegen-rust/` (built via `make build-fegen-rust-cst`) as a more complete example with `.pyi` stub and feature split; pluralized the trailing "These are FLTK-internal."
Evidence (diff at rust-cst-extension-guide.md): added text claims `.pyi` stub and `extension-module`/`python` feature split. Verified both against ground truth: `git ls-tree 5bc28c3` shows `fltk/_stubs/fegen_rust_cst/cst.pyi` (and `__init__.pyi`); `crates/fegen-rust/Cargo.toml` `[features]` declares `default = ["extension-module"]`, `extension-module = ["python", "pyo3/extension-module"]`, `python = ["dep:pyo3", ...]`. Both cited Makefile targets exist: `build-test-user-ext` (Makefile:198), `build-fegen-rust-cst` (Makefile:205). The stale `tests/rust_cst_fegen/` reference is removed.
Assessment: claims in the new doc text are factually accurate; fix addresses the consequence. Accept.

## Disputed items

None.

## Approved

4 findings: 2 Fixed verified (quality-3, quality-4), 2 Won't-Do sound (quality-1, quality-2). 0 TODOs (none added). Six lenses returned no findings.

Spec compliance (independent of findings): spec asked to delete the duplicate directory and fix stale refs in CHANGELOG and the extension guide. Verified at HEAD — directory fully removed (`git grep rust_cst_fegen` outside ADR docs returns nothing), both named docs fixed, plus the stale Cargo.toml provenance comment. ADR history hits correctly left untouched (immutable record).

---

## Verdict: APPROVED

All four dispositions acceptable: two Won't-Do rest on correct false-premise / no-consequence grounds; two Fixed verified against the Makefile, Cargo.toml features, and stub paths. Deletion is complete and matches spec. No TODOs introduced, nothing deferred.
