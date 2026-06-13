# Judge verdict — deep review

Phase: deep. Base 604dab1..HEAD 2f4b3da. Round 2 (APPROVED or ESCALATE only).
Spec reference: ADR `docs/adr/2026/06/12-cargo-deny-ci-install/README.md`.
Notes: 7 reviewer files; 4 findings dispositioned (security-1, security-2, reuse-1, quality-1).
Pre-noted: removal of cargo-deny from CI is a user-decided ADR trade-off, not a defect.

Round-1 verdict was REWORK on security-2 (deferred a do-now, iteration-created one-line fix). This round re-judges the round-1 disputed items against the new HEAD.

## Added TODOs walk

No TODO-dispositioned findings remain at this HEAD. The round-1 `TODO(antidrift-structural)` was removed and its work landed; `TODO(check-capture-macro)` was removed and reuse-1 is now Won't-Do. Both re-judged under their findings below. (Stale `TODO.md` bookkeeping noted in Disputed.)

## Other findings walk

### security-2 — Fixed (was TODO, round-1 REWORK driver)
Round-1 finding: parallel-dependency structure (`check` and `check-ci` both depend on `check-common` independently) lets a future step added directly to `check` silently never run in CI; verdict required the one-line structural fix `check: check-ci`.
Disposition: Fixed — `check: check-ci` applied.
Evidence: Makefile:61 (live) reads `check: check-ci`; recipe (62-70) then runs only the `cargo-deny` block. `check-ci: check-common` at Makefile:76. Dependency chain is now `check → check-ci → check-common`, so any step added to `check-ci`/`check-common` is inherited by `check`, and the divergence is the single `cargo-deny` recipe line on `check`. Correctness review (commit edb782c trace, still valid at this HEAD) confirms behavior identical: prereqs ordered before recipe even under `-j`; `check-common` failure aborts before `cargo-deny`. No `TODO(...)` comment remains in the Makefile (grep clean).
Assessment: this is exactly the do-now fix the round-1 verdict prescribed; structurally enforces the one-sanctioned-divergence relationship. Accept.

### security-1 — Won't-Do (unchanged)
Claim: CI no longer enforces `deny.toml` (RustSec advisories, license allow-list, unknown-source bans); a PR/dependency bump can introduce an advisory-bearing or disallowed crate and pass CI green. Local hook is bypassable, not run on merge commits, absent for contributors lacking the tool.
Consequence: real and correctly stated — genuine supply-chain coverage gap at the PR/merge trust boundary.
Rationale: explicitly accepted ADR trade-off (Consequences section); the ADR weighed all three CI-install options and declined them. Reviewer states "Flagged so the security cost is explicit, not to block."
Assessment: Won't-Do correct. Documents the cost of a user-decided trade-off; prompt directs this decision is not a defect; reviewer did not ask to block. Accept (unchanged from round 1).

### reuse-1 — Won't-Do (was TODO at round 1)
Claim: 8-line mktemp/capture/print/cleanup idiom duplicated between `check-common` for-loop body (Makefile:41-49) and the `check` cargo-deny recipe (62-69); divergence would yield inconsistent failure-output formatting. Reviewer self-rated "awareness rather than urgency."
Disposition: Won't-Do — Make `define`/`call` macro adds indirection that obscures each recipe; cost (readability) exceeds benefit (dedup of a 2-site, never-diverged idiom).
Assessment: genuine cosmetic nit, no correctness/coverage risk. Round 1 already flagged it as "nit-level" and "not independently load-bearing." For a nit, Won't-Do does not require the active-harm bar that a should-fix/blocker would; the responder's readability-vs-indirection rationale is a sound engineering judgment for a Makefile, not hand-waving. The duplication is two adjacent sites visible on one screen. Accept.

### quality-1 — Fixed (unchanged)
Claim: `check-common` recipe comment "DO NOT ADD STEPS HERE DIRECTLY" inverted the anti-drift rule; most-local guidance contradicted the authoritative block comment.
Diff at Makefile:36-38 (live): now "Shared base… / ADD new steps here by appending the target name to the `steps` string below. / DO NOT add new steps directly to `check` or `check-ci` — they inherit via this target." Verified against HEAD.
Assessment: removes the contradiction, points the editor at the correct location. Accept (unchanged from round 1).

## Disputed items

None blocking. One bookkeeping note (not escalation-worthy, not a wrong disposition on any reviewer finding):

- **TODO.md drift**: `TODO.md:15-21` still carries entries for `antidrift-structural` (now done — work landed in commit 2f4b3da) and `check-capture-macro` (now Won't-Do per reuse-1). Per the project TODO system, slug entries join to `TODO(slug)` code comments; both code comments were removed but the `TODO.md` entries were not. These are now orphaned. No reviewer raised TODO.md hygiene, and this does not invalidate any disposition — it is post-merge cleanup (delete the `antidrift-structural` entry as completed; delete or convert `check-capture-macro` per the Won't-Do). Surfaced for the orchestrator/owner to sweep; does not gate approval.

## Approved

4 findings: 2 Fixed verified (security-2, quality-1), 2 Won't-Do sound (security-1, reuse-1). All round-1 disputed items (security-2, reuse-1) resolved.

---

## Verdict: APPROVED

The round-1 REWORK driver (security-2) is fixed with exactly the prescribed one-line structural change (`check: check-ci`, Makefile:61), verified live. security-1 and quality-1 carry over correctly. reuse-1's Won't-Do is sound for a cosmetic, never-diverged, 2-site nit. The only residual is orphaned `TODO.md` entries (bookkeeping), which is non-blocking and noted for cleanup. HEAD 2f4b3da.
