# Judge verdict — deep review: pin-ci-actions

Concise. Precise. No padding. Audience: smart LLM/human. (Note carried per authoring protocol.)

Phase: deep. Base 74a4ac2..HEAD 83af76b. Round 1.
Notes: 7 reviewer files (errhandling, correctness, security, test, reuse, quality, efficiency); 3 findings total, 4 notes files report "No findings."
Note: reviewer notes cover 74a4ac2..c2c34bd; HEAD 83af76b is the responder's fix commit on top (touches only `ci.yml` + dispositions doc) — no unreviewed substantive change.

## Added TODOs walk

### security-1 — TODO(dependabot-branch-pin-gap), no anchor location

Q1 (worth doing): yes — Dependabot maps SHA-pin bumps via the ref comment; `# stable` is a branch, not a release/semver tag, so the `dtolnay/rust-toolchain` pin gets no automated bumps and silently rots (reviewer's consequence: vulnerable revision executes indefinitely; Rust toolchain frozen). Design's claim "the point Dependabot weekly bumps address" (`design.md:62`) is wrong for this action. Real maintenance gap.

Q2 (design/owner input required): no. The responder already chose reviewer option (c) — accept and document the gap. Executing that choice is mechanical and doable now: correct/annotate the ADR text, add the `TODO.md` entry, and put a `TODO(dependabot-branch-pin-gap)` comment at the anchor. The responder's stated obstacle — "dependabot.yml has no comment syntax" — is false: `dependabot.yml` is plain YAML; `#` comments are valid and routinely used in GitHub's own dependabot.yml examples. A clean anchor exists at the `dtolnay/rust-toolchain` step in `ci.yml` or in `dependabot.yml` itself.

Furthermore: the rot gap is created by this iteration — before pinning, `@stable` auto-tracked upstream; after pinning, nothing refreshes this SHA. Per rubric, a problem this iteration created cannot be silently deferred; it must be visibly fixed (documented + anchored) or escalated.

TODO-system violation: the project convention (CLAUDE.md "TODO System") requires both a `TODO.md` entry and a `TODO(slug)` comment in code. At HEAD, `dependabot-branch-pin-gap` appears only inside `dispositions-deep.md` — a review artifact nobody operating the repo will consult. No `TODO.md` entry, no code comment. As executed, this is a Won't-Do wearing a TODO label, with a garbled rationale ("Added ... would be ideal, but ... is not the right vehicle either").

Assessment: Q2 fails → do-now, and the TODO as filed violates the project TODO convention anyway. Disposition wrong.

## Other findings walk

### correctness-1 — Fixed

Claim: `dtolnay/rust-toolchain` step relies on the `stable`-branch-only `toolchain` default; a future bump to a `v1`/master SHA (where `toolchain` is `required: true`, no default) breaks the step; consequence is silent CI breakage or silent rot contradicting the design's maintenance claim.
Diff at `ci.yml:24-26` (commit 83af76b): `with: toolchain: stable` added to the step. Behavior now independent of which branch a future pinned SHA came from — the breakage half of the consequence is closed. The rot half is explicitly deferred to security-1 (judged above).
Assessment: fix addresses the named line and the actionable half of the finding; reviewer's own suggested fix was exactly this plus an ADR note. Accept Fixed; the ADR-note residue rides with security-1.

### security-2 — Fixed

Claim: no `permissions:` block (default write-scoped `GITHUB_TOKEN`) and `persist-credentials: true` default on checkout; consequence is a compromised action or malicious crate build-script exfiltrating a write-scoped token from `.git/config`.
Diff (commit 83af76b): `permissions: contents: read` at job level (`ci.yml:11-12`); `persist-credentials: false` on the checkout step (`ci.yml:15-16`). Workflow has no push/write steps, so read-only scope is sufficient.
Assessment: fix matches the reviewer's suggested remediation exactly. Accept.

## Disputed items

- **security-1 / TODO(dependabot-branch-pin-gap)**: disposition fails the rubric (Q2: doable now) and the project TODO convention (no `TODO.md` entry, no `TODO(slug)` code comment — slug exists only in the dispositions doc). Need either:
  1. Do it now: correct the design/ADR text claim that Dependabot covers all three pins, document the manual-refresh procedure (e.g. `git ls-remote refs/heads/stable` or `pinact`) where operators will find it; if a recurring tracking item is wanted, add the `TODO.md` entry plus a `# TODO(dependabot-branch-pin-gap): ...` YAML comment at the `dtolnay/rust-toolchain` step or in `dependabot.yml` (the "no comment syntax" claim is false); OR
  2. Re-disposition as Won't-Do with a rationale that meets the bar — but the bar is unlikely to be met given the design's misleading claim stands uncorrected.

## Approved

2 findings: 2 Fixed verified (correctness-1, security-2). 0 Won't-Do. 0 TODOs acceptable.

---

## Verdict: REWORK

One disposition wrong (security-1). Round 1.
