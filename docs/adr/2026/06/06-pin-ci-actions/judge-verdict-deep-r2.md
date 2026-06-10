# Judge verdict — deep review round 2: pin-ci-actions

Concise. Precise. No padding. Audience: smart LLM/human. (Note carried per authoring protocol.)

Phase: deep. Base 74a4ac2..HEAD ebbafcd. Round 2 (APPROVED or ESCALATE only).
Scope: round-1 verdict (`judge-verdict-deep.md`) disputed exactly one item — security-1. The other two findings (correctness-1, security-2) were verified Fixed in round 1 and are unchanged at ebbafcd (re-confirmed: `permissions: contents: read`, `persist-credentials: false`, `with: toolchain: stable` all present in `ci.yml` at HEAD). Rework commit ebbafcd touches only `ci.yml` (inert YAML comment), `TODO.md`, and `design.md` — no unreviewed substantive change beyond the disputed item's remediation.

## Added TODOs walk

### security-1 — TODO(dependabot-branch-pin-gap), re-judged after rework

Round-1 failure: slug existed only in the dispositions doc — no `TODO.md` entry, no code anchor, design's misleading Dependabot claim uncorrected; the documentation work was do-now.

Verified at ebbafcd (diff 83af76b..ebbafcd):
- `# TODO(dependabot-branch-pin-gap): ...` comment at `ci.yml:24-28`, anchored on the `dtolnay/rust-toolchain` step, stating the Dependabot blind spot and the manual-refresh procedure (`git ls-remote .../refs/heads/stable`, or `pinact`). Matches round-1 option 1 verbatim.
- `TODO.md` entry `## dependabot-branch-pin-gap` present with slug, deferral context, refresh procedure, and location reference. Slug join key now satisfied both ways per CLAUDE.md TODO System.
- `design.md:62` corrected: now states Dependabot covers `actions/checkout` and `astral-sh/setup-uv` but not branch-pinned `dtolnay/rust-toolchain`, cross-referencing the TODO. The misleading "the point Dependabot weekly bumps address" claim is gone.

Rubric re-applied to the TODO as it now stands:
- Q1 (worth doing): yes — the pin rots without automated bumps; the residual item is the recurring manual SHA refresh (or future automation), which round 1 explicitly sanctioned as a tracking item.
- Q2 (design/owner input required): the do-now portion (document + anchor + correct design text) is now done; what remains is recurring operational refresh with no one-shot "done" — automating it (scheduled workflow, pinact bot) would be a design choice. Acceptable as a standing tracked item; this is exactly the form round-1 option 1 prescribed.

Minor, non-blocking: `dispositions-deep-r2.md` says the entry was placed "after `pyright-batch-tests`"; it actually sits after `span-source-as-py-crosscdylib`. Placement is immaterial; entry content is correct.

Assessment: disposition acceptable. Round-1 dispute resolved.

## Other findings walk

None re-opened. correctness-1 and security-2 were verified Fixed in round 1; fixes remain intact at HEAD (inspected `ci.yml` at ebbafcd).

## Approved

3 findings: 2 Fixed verified (round 1, intact at HEAD), 1 TODO acceptable (security-1, reworked). 4 of 7 notes files report no findings.

---

## Verdict: APPROVED

The single round-1 dispute was remediated exactly as specified; all dispositions acceptable.
