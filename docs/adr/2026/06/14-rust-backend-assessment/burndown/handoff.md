# Burndown session handoff

Resume point for burning down `docs/adr/2026/06/14-rust-backend-assessment/recommended-actions-eli5.md`
(companion: `recommended-actions.md`). Written at a deliberate stopping point: the **regex-grammar-spike
design is approved by the review chain and awaiting USER review**. Read this top-to-bottom before resuming.

---

## 1. Mission

Burn down the recommended-actions items. The ELI5 file carries the user's authoritative **STATUS** notes
(dispositions). Items with STATUS = REJECTED/DEFER/IGNORE are out; items with no STATUS or STATUS = "do
differently" are candidates. The user's STATUS edits are committed in the base commit (see §3).

## 2. User's custom workflow rules (deviations from the standard review-chain workflow)

- **Skip requirements.** The ELI5 + `recommended-actions.md` ARE the spec. Design cycles run explore → design
  → design-review chain → eli5 → user gate. (ELI5 skipped for purely-internal spike/layout designs unless asked.)
- **Up to 3 design cycles in parallel.** A design entering implementation frees a design slot.
- **Implementation is STRICTLY SERIALIZED** — one burndown item in the implement→review→squash lane at a time.
- **Stop at human gates.** Design approval is the user's; agent approval (judge) ≠ user approval.
- **Autonomous squash.** After an item passes its full review chain (deep review APPROVED for designed items;
  pre-pass+deep for fast-tracks), squash it to ONE commit **including that item's working-dir docs**, WITHOUT
  waiting for a per-item ship gate. The user reviews ALL commits at the end. Only escalations stop this.
- **NO push** without separate, explicit per-repo/branch authorization. Never force-push. ("approved squash" ≠
  "approve push").
- **Model overrides:** default/inherit everywhere EXCEPT where the user explicitly asked for opus (see §6).
- **Incremental implementation mode** is opt-in; the user requested it for the spike AND for fix-forged-abi-segfault.
- Fast-track = skip the design cycle entirely; implement from an inline spec, then full pre-pass + deep review.

## 3. Git state

- Branch: `main`. Base commit (pre-burndown): **`205c36b`** ("Dispositions on recommended actions…" — this commit
  contains the user's STATUS edits; do NOT look for them as uncommitted).
- Current HEAD: **`a4b35b8`**. Two items already shipped as squashed commits on top of base:
  - `9f96d43` — cst-generated-header
  - `a4b35b8` — remove-dead-duplicate-crate (−17.5k lines)
- **Nothing pushed.** User will review all commits at the end before any push is even discussed.
- Untracked (uncommitted) working state:
  - `docs/fltk-grammar-reference.md` (persistent, approved, awaiting commit decision — see §5)
  - `docs/adr/2026/06/14-rust-backend-assessment/burndown/{fix-forged-abi-segfault,regex-portability-lint,fltk-grammar-reference,regex-grammar-spike}/`
  - `…/burndown/document-scope-boundary/` exists but is empty.
- Base advances as each item squashes. Reviewers diff `base..HEAD` for the item's own base.

## 4. Per-item status

| Item | State | Next action |
|---|---|---|
| `cst-generated-header` | **DONE** — squashed `9f96d43` | (end-review only) |
| `remove-dead-duplicate-crate` | **DONE** — squashed `a4b35b8` | (end-review only) |
| `fix-forged-abi-segfault` | **Design USER-APPROVED.** Awaiting implementation. | Implement: **serialized + incremental** mode. Confirm OQ1 first (below). |
| `regex-grammar-spike` | **Design review-chain APPROVED; awaiting USER review** (this stopping point) | User gate → then **incremental** impl (default sonnet; **opus** for the adversarial increment). |
| `regex-portability-lint` | Design (grammar-based) judge-APPROVED; `regex.fltkg` drafted + separately review-APPROVED; `design.md` reconciled. **ELI5 is STALE.** No final user impl-approval yet. | Gated behind the spike (spike proves the grammar). Then: regen ELI5, user gate, implement. |
| `document-scope-boundary` | Fast-track. **Blocked on user's canonical-version decision.** | User picks version (wheel `0.1.1` / `fltk-native` `0.1.0` / runtime crates `0.2.0`) + confirm consumer-guide pin → git/Bazel pin. Then fast-track impl. |
| `demote-cst-spike` | Blocked (depends on DEFERRED `perf-harness`). | Hold. |
| Others (`gencode-drift-gate`, `cargo-deny-in-ci`, `differential-property-harness`, `perf-harness`, `clockwork-committed-pin-proof`, `ship-opt-in-first-consumer`, `emission-ir-decision`) | OUT per user STATUS (rejected/deferred/ignored). | None. |

### fix-forged-abi-segfault OQ1 (resolve before implementing)
Design left one open judgment call **OQ1**: close the residual forge gap via a PyCapsule-based identity token
vs. a narrower fix. (A secondary hardening was already deferred to `TODO(forged-abi-extract-span-uniformity)`.)
The user said "approved" but did not explicitly answer OQ1 — confirm the user's choice (or the design's stated
default) at implementation start.

## 5. The persistent FLTK grammar reference

- `docs/fltk-grammar-reference.md` — authoritative `.fltkg` syntax/semantics/constraints reference. Built from two
  **opus** explorations (`…/burndown/fltk-grammar-reference/exploration-syntax.md`, `exploration-detailed.md`),
  written by a designer, then run through a full design-review chain → **APPROVED**.
- It is NOT tied to a burndown squash. **Uncommitted.** Pending user decision: commit standalone? include the two
  explorations or keep them as scratch? (Asked; not yet answered.)
- Key facts it establishes (these corrected the regex design): FLTK **supports left recursion** (packrat
  seed-grow, left-associative, base case required); alternation = PEG ordered first-match; `!` INLINE accepted
  syntactically but unimplemented (NotImplementedError both generators); Python `re` vs Rust `regex-automata`
  is a real semantic boundary; grammars are parsed as **UTF-8 / Unicode codepoints**.

## 6. Model overrides used (and the rule)

Default/inherit everywhere. User-mandated opus so far: (a) the two grammar-reference explorers; (b) the
**adversarial-testing increment** of the spike implementation. When you spawn the spike's adversarial increment,
pass `model: "opus"` on that implementer; all other spike increments and all other agents = default.

## 7. Next design pick (start post-handoff, in parallel)

REMOVED because I did not like the pick. We need to pick a different one.

## 8. Implementation lane plan (serialized; all not-yet-started)

Lane is currently **IDLE**. Queue/sequence is the user's call. Known pending implementations:
1. `fix-forged-abi-segfault` — incremental, after OQ1 confirmed. (Phase A blocker; likely first.)
2. `regex-grammar-spike` — incremental (opus adversarial increment), after user approves spike design.
3. `document-scope-boundary` — fast-track, after version decision.
4. `regex-portability-lint` — after the spike validates the grammar; regen ELI5 + user gate first.

Get explicit user go-ahead before starting ANY implementation (hard rule). When you do incremental spawns, end
each implementer prompt with the verbatim recency line about first-two-tool-calls (see orchestrator workflow,
incremental section).

## 9. Pending USER decisions (consolidated)

1. **Approve the spike design** (`…/regex-grammar-spike/design.md`) — the gate we stopped at.
2. **Grammar reference commit** preference (§5).
3. **fix-forged-abi-segfault OQ1** + green-light to start its serialized incremental impl.
4. **document-scope-boundary** canonical version + consumer-guide pin style.
5. Confirm/redirect the **next-design pick**.
6. Sequencing of the serialized implementation lane.

## 10. Conventions / gotchas

- Orchestrator reads/writes NO workflow artifacts; consumes ≤3-line summaries + paths. (This handoff and verbatim
  user-directive transcriptions are the only self-writes.)
- All subagents one-shot; spawn fresh each time. Review chain = parallel reviewers → responder → judge; REWORK =
  one rework round then APPROVED/ESCALATE.
- **Commit hygiene during implementation:** implementers stage ONLY their own changed files. Other items' untracked
  working docs AND `docs/fltk-grammar-reference.md` must stay OUT of any item's commit.
- Squash mechanics that worked: `git reset --soft <item-base>` → `git add <item working dir>` → `git commit
  --no-verify` (the code tree was already gate-passed by the implementer's own commits; `--no-verify` avoids a
  redundant multi-minute precommit run; markdown docs don't affect the gate).
- User-feedback at a design gate → transcribe verbatim to `notes-design-user.md`, then designer respond (with
  user-notes path so agents can't override the user) → judge → regen ELI5 if design changed. Full re-review is
  opt-in.
- `~/tps/clockwork` exists locally (out-of-tree). Per user: never hard-code its path in committed code; the spike's
  extraction tool is a general CLI taking any `.fltkg` path as an arg.

## 11. Task list mapping (TaskCreate IDs)

1 fix-forged-abi-segfault (in_progress) · 2 regex-portability-lint (in_progress) · 3 cst-generated-header (done) ·
4 remove-dead-duplicate-crate (done) · 5 document-scope-boundary (pending) · 6 grammar reference + regex.fltkg
review (done) · 7 regex-grammar-spike (pending — design done, awaiting user).
