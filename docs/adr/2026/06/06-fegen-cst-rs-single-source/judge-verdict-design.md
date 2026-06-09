# Judge verdict — design

Phase: design. Doc: `docs/adr/2026/06/06-fegen-cst-rs-single-source/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 3 findings + 2 nits.

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

## Findings walk

### design-1 — Fixed
Claim: design cites `TODO.md:23-25` for the `fegen-cst-rs-single-source` entry; those lines are actually the live `rust-cst-pyi` entry. Consequence: implementer deletes the wrong TODO entry; collateral removal of `rust-cst-pyi` is caught by nothing (the `grep -r 'fegen-cst-rs-single-source'` post-condition only catches the leftover).
Verified at source: `TODO.md:19` is `## fegen-cst-rs-single-source` (body `:21`); `:23` is `## rust-cst-pyi`. design.md "Root cause / context" (line 14) now identifies the entry by slug heading + `TODO.md:19-21`; "Edge cases / TODO bookkeeping" (line 57) cites `:19-21` and explicitly warns `:23-25` is the unrelated live `rust-cst-pyi` entry.
Assessment: fix addresses the consequence at both cited locations, identification by heading is drift-resistant. Accept.

### design-2 — Fixed
Claim: design said all three consumer test files gate via `importorskip`; `test_clean_protocol_consumer_api.py` uses try/except + `pytest.mark.skipif`. Consequence: minor description error, but test-plan step 2 accepted "pass" without excluding "all skipped" — a broken include-based build could masquerade as green.
Verified at source: `test_phase4_fegen_rust_backend.py:29` and `test_cross_backend_label_equality.py:24` use `pytest.importorskip`; `test_clean_protocol_consumer_api.py` uses `try:` (`:45`) + `pytest.mark.skipif` (`:53`). design.md line 12 now states the per-file mechanisms with cites; test-plan step 2 (line 64) requires building first and confirming the pytest summary shows passes, not skips.
Assessment: both the description and the test-plan hole are fixed. Accept. (Design's `:46-55` range for the try/except+skipif block is off by one at the top — `try:` is `:45` — but matches the reviewer's own citation and the anchor lines are correct; not disputed.)

### design-3 — Fixed
Claim: design inherited the stale "not a Cargo workspace" premise; root `Cargo.toml:1-3` now declares `[workspace] members = [".", "crates/fltk-cst-core"]` (since `4c8f0ad`), and the test crate is excluded only via an empty `[workspace]` opt-out table the design never mentioned. Consequence: implementer "cleaning up" the seemingly pointless opt-out breaks the build with no warning in the design.
Verified at source: root `Cargo.toml:1-3` declares the workspace; `tests/rust_cst_fegen/Cargo.toml:3` carries the empty `[workspace]` table with an explanatory comment. design.md now has a "Workspace note" paragraph (line 16) correcting the request/exploration premise, reinterpreting the constraint as "do not add test crates to any workspace; preserve the opt-out," and warning removal makes cargo error on a non-member crate inside a workspace directory. The non-changes sentence (line 36), the `use`-collision edge case (line 54, clippy scope now stated as root-workspace with the opt-out as exclusion mechanism), and test-plan step 4 (line 66) all reference the mechanism.
Assessment: fix covers premise correction, the unstated mechanism, and the warning. Accept.

### Nits — both fixed (no separate findings filed)
- `gencode` cite is now `Makefile:80-118`; Makefile is 118 lines. Verified.
- Test-plan step 3 no longer says "cpp-expanded"; states the by-construction property accurately. Verified.

## Spot-checks of surviving design claims

- md5 `4bff0dbe...` / 6857 lines for both copies — verified identical at source.
- `Makefile:108-109` carries the `TODO(fegen-cst-rs-single-source)` duplicate-regen step — verified.
- `tests/rust_cst_fegen/Cargo.toml` comment confirms the opt-out is intentional — verified.

## Disputed items

None.

## Approved

3 findings: 3 Fixed verified. 2 nits fixed.

---

## Verdict: APPROVED
