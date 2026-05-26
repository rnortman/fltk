# Judge verdict — deep review

Phase: deep. Base f1e2a98..HEAD b54d599. Round 1.
Notes: 7 reviewer files; 12 findings total (correctness-1..4, security-1..3, quality-1..2, efficiency-1..2). Error-handling, test, reuse reviewers: no findings.

## Added TODOs walk

### correctness-1 / quality-1 / efficiency-1 — TODO(ci-maturin-rebuild) at `.github/workflows/ci.yml:26`

Three reviewers independently flagged the redundant `maturin develop` step. Dispositioned as a single TODO.

Q1 (worth doing): Yes — the explicit step pays an extra Rust compile on every CI run and documents a false dependency chain.

Q2 (design/owner input required): No. The fix is mechanical: either delete the step or unify the `--group` sets. The disposition itself describes exactly what to do ("remove the explicit step and rely on the re-sync, or unify the group sets"). No design cycle, no product owner input. The responder's "verify behavior with a CI timing run" caveat is reasonable caution but does not elevate this to a design question — it is a one-line CI config change with an obvious rollback.

Furthermore: this iteration introduced the redundant step. Per rubric, problems this iteration created cannot be silently deferred.

Assessment: Q2 fails. Do-now. Disposition wrong.

### security-1 — TODO(pin-ci-actions) at `.github/workflows/ci.yml:12,15,22`

Q1 (worth doing): Yes — mutable action refs are a real supply-chain risk; reviewer spelled out the trust boundary (runner token, artifact tampering).

Q2 (design/owner input required): Yes — choosing which SHAs to pin to, whether to adopt Dependabot, and the maintenance cadence for SHA updates are operational decisions. The action `dtolnay/rust-toolchain` deliberately does not publish version tags, so the SHA choice requires checking the repo. Not mechanical.

Assessment: TODO acceptable.

### security-2 — TODO(tests-outside-package)

Disposition says "Single TODO(tests-outside-package) covers both [security-2 and quality-2]. See quality-2 disposition." But quality-2 is dispositioned as Fixed (file moved to `tests/`). The slug `tests-outside-package` does not appear in `TODO.md` or any code comment (`grep` confirms zero matches). The underlying issue is resolved by the fix in quality-2. The disposition label is incoherent — it references a TODO that was never created because the fix made it unnecessary.

Assessment: The issue is actually fixed (verified: `fltk/test_native.py` renamed to `tests/test_native.py` in commit b54d599). The disposition label is wrong but the outcome is correct. Treating as effectively Fixed. No rework needed — the code is right; only the disposition text is confused.

### design-originated TODO: `bazel-rules-rust` at `MODULE.bazel:5`

Not a reviewer finding, but present in the diff as a new TODO. Quick rubric check:

Q1: Yes — Bazel builds currently cannot build the Rust extension.
Q2: Yes — Bazel Rust integration requires choosing `rules_rust` version, configuring toolchains, and deciding how the cdylib fits into the Bazel dependency graph. Genuine design work.

Assessment: TODO acceptable.

## Other findings walk

### correctness-2 — Won't-Do
Claim: Rust-less machines cannot run `make check` at all (lint, typecheck, test all fail). Consequence: developers without Rust are locked out of all checks.
Rationale: "Deliberate trade-off documented in design.md and CLAUDE.md."
Inspection: Design.md "Edge Cases / Failure Modes" section explicitly calls this out as deliberate. CLAUDE.md documents `rustup` as a prerequisite. Reviewer also marked this as "an accepted invariant, not a defect."
Assessment: Rationale matches the documented design intent. Accept.

### correctness-3 — Won't-Do
Claim: Stale coverage `source_pkgs`/`paths` reference `src/fltk` which does not exist. Consequence: none — paths are no-ops.
Rationale: "Predate this diff, out of scope."
Inspection: Reviewer confirmed "no behavior change." The stale config predates this diff.
Assessment: No consequence, reviewer confirmed non-issue. Accept.

### correctness-4 — Won't-Do
Claim: Informational verification of PyO3 lifetime semantics and `#[pymodule]` naming. No defect claimed.
Rationale: "Informational verification finding; no action warranted."
Inspection: Reviewer explicitly confirmed no defect.
Assessment: Not a finding requiring action. Accept.

### security-3 — Won't-Do
Claim: New Rust/Python dependency trees added. Consequence: informational — expanded trust boundary for in-process cdylib.
Rationale: "Lockfiles carry checksums; no known-vulnerable versions."
Inspection: Reviewer marked this as informational, no known vulnerabilities, checksums intact. The dependency expansion is inherent to the PyO3 design.
Assessment: Informational finding, no actionable defect. Accept.

### quality-2 — Fixed
Claim: `fltk/test_native.py` ships in the wheel, leaking test code into the installed package. Consequence: abstraction boundary violation; future test files with side effects would ship to users.
Diff: `fltk/test_native.py` renamed to `tests/test_native.py` (100% similarity, confirmed in diff d650cfa..b54d599). `pyproject.toml` `python-packages = ["fltk"]` excludes `tests/`.
Assessment: Fix addresses the finding. Accept.

### efficiency-2 — Won't-Do
Claim: No release/opt profile pinned in Cargo.toml. Consequence: none for Phase 0; debug builds are intentional.
Rationale: "Design explicitly chooses debug profile. Reviewer marked this as not actionable in this diff."
Inspection: Design.md line 130 confirms debug builds for development. Reviewer explicitly noted "Not actionable in this diff."
Assessment: Informational, no action needed. Accept.

## Disputed items

- **correctness-1 / quality-1 / efficiency-1 — TODO(ci-maturin-rebuild)**: Fails Q2 (mechanical CI config change, no design input needed) and falls under "this iteration created the problem." Need: remove the redundant step or unify group sets, and delete the TODO. Alternatively, provide a concrete reason the step cannot be removed without a design cycle.

## Approved

11 findings (counting the 3 merged as 1): 1 Fixed verified, 4 Won't-Do sound, 1 TODO acceptable (pin-ci-actions), 1 TODO acceptable (bazel-rules-rust), 1 incoherent label but actually fixed (security-2/tests-outside-package).

---

## Verdict: REWORK

One disposition wrong: the triple-merged TODO(ci-maturin-rebuild) fails the TODO rubric (Q2: no design cycle required; this iteration introduced the redundant step). Round 1.
