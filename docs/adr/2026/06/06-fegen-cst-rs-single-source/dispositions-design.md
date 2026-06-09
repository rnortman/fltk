# Dispositions: design review round 1 — `fegen-cst-rs-single-source`

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Notes file: `notes-design-design-reviewer.md`. All three findings fact-checked against HEAD `af6e6f3` source before disposition; all three verified accurate.

design-1:
- Disposition: Fixed
- Action: Verified at HEAD: `TODO.md:19-21` is the `## fegen-cst-rs-single-source` entry; `:23-25` is `rust-cst-pyi`. Corrected both citations in design.md — "Root cause / context" (now cites the entry by slug heading + `TODO.md:19-21`) and "Edge cases / TODO bookkeeping" (now identifies the entry by heading, corrects to `:19-21`, and explicitly warns that `:23-25` is the unrelated live `rust-cst-pyi` entry).
- Severity assessment: Real collateral-damage risk: an implementer trusting the cited lines would delete the live `rust-cst-pyi` TODO entry, and no existing check catches that deletion (the `grep -r 'fegen-cst-rs-single-source'` post-condition only catches the leftover, not the collateral removal).

design-2:
- Disposition: Fixed
- Action: Verified at HEAD: `test_clean_protocol_consumer_api.py:46-55` uses try/except import + `pytest.mark.skipif`, not `importorskip`; the other two files use `pytest.importorskip` (`test_phase4_fegen_rust_backend.py:29`, `test_cross_backend_label_equality.py:24`). Corrected the consumption description in "Root cause / context" (per-file mechanism with line cites) and amended test-plan step 2 to require building first and confirming the pytest summary shows passes, not skips.
- Severity assessment: Description error was behaviorally equivalent (all three skip when unbuilt), but the unverified claim plus a test plan that accepted "pass" without excluding "all skipped" could let a broken include-based build masquerade as green. Step 2 now closes that hole.

design-3:
- Disposition: Fixed
- Action: Verified at HEAD: root `Cargo.toml:1-3` declares `[workspace] members = [".", "crates/fltk-cst-core"]` (introduced by `4c8f0ad`); `tests/rust_cst_fegen/Cargo.toml:3` carries an empty `[workspace]` opt-out with a comment. Added a "Workspace note" paragraph to "Root cause / context" correcting the stale request/exploration premise, reinterpreting the request constraint as "do not add the test crates to any workspace; preserve the empty `[workspace]` opt-out," and warning that removing the opt-out breaks the build. Updated the "Proposed approach" non-changes sentence, the `use`-collision edge case (clippy scope is now root-workspace, exclusion is via the opt-out), and test-plan step 4 to reference the mechanism.
- Severity assessment: Without this, the design's clippy/cargo-scope claims held only by an unstated mechanism, and an implementer "cleaning up" the seemingly pointless empty `[workspace]` table would get a cargo error (non-member crate inside a workspace directory) with nothing in the design warning against it.

Nits (reviewer filed no separate findings; both fixed anyway):
- `gencode` cite corrected to `Makefile:80-118` (Makefile is 118 lines).
- Test-plan step 3's "cpp-expanded include" phrasing replaced with an accurate by-construction statement (no preprocessor involved).

Cleanup-editor pass re-run after edits (terminology normalized to "root-workspace"; step 1/step 2 build-command redundancy resolved).
