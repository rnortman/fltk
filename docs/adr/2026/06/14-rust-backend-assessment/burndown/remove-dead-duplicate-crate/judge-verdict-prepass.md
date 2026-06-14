# Judge verdict — burndown pre-pass (fast-track)

Item: `remove-dead-duplicate-crate`.
Spec: `recommended-actions.md:139` / `recommended-actions-eli5.md:160` (companion ELI5).
Base 9f96d43..HEAD f1e1fef. Round 1.
Notes: 2 reviewer files (`notes-prepass-slop.md`, `notes-prepass-scope.md`) — both "No findings."
Dispositions: "No findings from either reviewer. No fixes required, no commit." (HEAD is a single commit; the "no commit" wording in the disposition is stale relative to f1e1fef but immaterial.)

This is a deletion change with a clean review. Per role, "no findings" is not accepted at face value — it is verified adversarially against the spec and the diff before approval.

## Other findings walk

No reviewer findings to adjudicate. In their place, an independent verification that the responder's empty disposition is *correct* (i.e. the reviewers were not lazy and the change is sound):

### V1 — Right copy deleted, canonical crate intact
Diff (`git show --name-status f1e1fef`): the 6-file orphan `tests/rust_cst_fegen/{Cargo.lock,Cargo.toml,src/{cst,lib,parser,native_parser_tests}.rs}` is fully `D`-deleted. Canonical `crates/fegen-rust/` retains all 6 sibling files at HEAD (`ls-tree`). Spec instruction was `git rm -r tests/rust_cst_fegen/`; executed exactly.
Assessment: correct target deleted, no collateral damage. Sound.

### V2 — No dangling live references
`git grep "rust_cst_fegen" f1e1fef -- . ':(exclude)docs/*'` → zero hits. No Makefile, Cargo, cargo-deny, gencode, CI, BUILD.bazel, or Python reference to the deleted path remains. (The Makefile's `build-fegen-rust-cst` target and the `fegen_rust_cst` pymodule name survive legitimately — they belong to the canonical `crates/fegen-rust/`, which produces that module; the spec's named "name collision" was between the two dirs, and removing one resolves it.)
Assessment: no orphaned build/code edges. Sound.

### V3 — Stale-reference fixes correct, not just present
Spec named exactly two live files to fix.
- `CHANGELOG.md:22` at base claimed `make gencode now regenerates tests/rust_cst_fegen/src/cst.rs` (confirmed stale via `git show base:CHANGELOG.md`). HEAD rewrites it to `crates/fegen-rust/src/cst.rs` and `tests/rust_cst_fixture/src/cst.rs` — both exist at HEAD (`ls-tree`).
- `docs/rust-cst-extension-guide.md:174` dropped the `tests/rust_cst_fegen/` + `make build-fegen-rust-cst` example, keeping `tests/rust_cst_fixture/` + `make build-test-user-ext`. The fixture dir exists; the make target exists at `Makefile:198`.
Assessment: both corrected references resolve to real artifacts. Sound.

### V4 — In-scope extra (Cargo.toml comment) is appropriate
`crates/fegen-rust/Cargo.toml` dropped the comment line `# Promoted from tests/rust_cst_fegen/ — canonical first-class fegen Rust artifact.` Removing a comment that points at a now-deleted path is a fourth stale reference, squarely within "fix the stale references it left behind." Not scope creep.
Assessment: sound, arguably required for completeness.

## Disputed items

None. The empty disposition is the correct outcome; the reviewers were not lazy.

### Note (non-blocking, no action required)
The spec's motivation text calls the orphan `cst.rs` "IDENTICAL to `crates/fegen-rust/`." At the base commit the two `cst.rs` blobs are NOT byte-identical (`6022adde…` vs `4aa1a8d5…`); only `parser.rs` is identical (`b4c10ec2…` both). So the orphan had actually drifted from canonical. This is a minor inaccuracy in the spec's *rationale*, not a defect in the responder's work — it strengthens the case for deletion (stale duplicate, not just duplicate) and does not change the correct action. Recorded for the human's awareness only; nothing to rework.

## Approved

0 reviewer findings (both reviewers clean, independently verified). Deletion verified correct on 4 axes: right copy removed, canonical crate intact, zero live dangling references, both spec-named stale references (plus one in-scope Cargo.toml comment) correctly fixed to existing artifacts. Remaining `tests/rust_cst_fegen` mentions are confined to immutable historical ADR dirs (`docs/adr/...`), correctly left untouched per ADR immutability policy.

---

## Verdict: APPROVED
