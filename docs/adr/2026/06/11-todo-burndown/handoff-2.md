# TODO Burndown — Handoff for Session 2

Style: concise, precise, complete, unambiguous. No padding.

Continues `handoff.md`. This session ran design (all 11 items) → user gates → implementation of items 1–4. Items 5–11 + finalization remain.

## Git state

- Branch: `rust-idiomatic-cst-api`. **No pushes** (burndown policy; user pushes on their own).
- Baseline commit `ef315be` — "TODO burndown: ADR artifacts". Holds ALL items' **design-stage** docs (request, exploration, design, design-review notes/dispositions/verdicts for items 1–11). Per-item commits add only impl + pre-pass/deep-review docs.
- Completed items (one squashed commit each, ADR docs included):
  - item 1 parse-depth-limit → `32a6c4e`
  - item 2 consume-regex-anchor → `61f9384`
  - item 3 nullable-loop → `ef8288c`
  - item 4 error-msg-escape → `0cc7a7f`
- **Current HEAD: `0cc7a7f`.** This is the base for item 5.
- Working tree clean except this handoff (committed separately).

## CRITICAL: stashed #8 artifacts

#8 (rust-cst-debug-depth) design was **revised this session** (scope expanded to fold in former `rust-cst-drop-depth`: iterative/non-recursive node Drop + non-recursive Debug) and is **USER-APPROVED**. Its revised `design.md` (a modification vs baseline) plus its r2 review docs are **stashed**:

- `stash@{0}` = `WIP on rust-idiomatic-cst-api: 32a6c4e ...` — **this is #8's. Restore it when implementing #8.** Contains: modified `design.md`, `evaluation-drop-depth-reachability.md`, `notes-design-design-reviewer-r2.md`, `dispositions-design-r2.md`, `judge-verdict-design-r2.md` (all under `docs/adr/2026/06/11-rust-cst-debug-depth/`).
- `stash@{1}`, `stash@{2}` = `WIP on main: ...` — **pre-existing, UNRELATED. Do not touch.**

When you reach #8: identify the stash by message `WIP on rust-idiomatic-cst-api` (index may shift if other stashes are added), `git stash pop` it, then implement. The revised design + r2 docs land in #8's squashed commit (r1 design docs are already in baseline `ef315be`). The design gate is already cleared — go straight to implementation.

## Remaining queue (severity/dependency order)

| # | slug | base | notes |
|---|------|------|-------|
| 5 | rust-bindings-module-split | 0cc7a7f | biggest surface; #6 depends on it |
| 6 | rust-naming-shared | after 5 | pure refactor; sequence after/with 5 |
| 7 | rust-cst-accessor-clone-efficiency | after 6 | edits gsm2tree_rs.py templates |
| 8 | rust-cst-debug-depth | after 7 | **pop stash first** (above); design user-approved |
| 9 | crosscdylib-abi-check-helper | after 8 | one deliberate error-msg change (pinned in request.md) |
| 10 | registry-gc-eviction-tests | after 9 | Python-side tests only |
| 11 | cst-named-mutators | after 10 | new public API; edits gsm2tree_rs.py |

Items 7, 8, 11 all edit `gsm2tree_rs.py` templates — serialized implementation handles overlap (rebase-style coordination as they drain). Implementation is **strictly serialized**; design already done for all.

## Per-item process recipe (as run this session)

1. Spawn **one** `review-chain:implementer` mode `incremental` on current HEAD. It **self-loops through all increments to `done`** in a single spawn (do NOT spawn per-increment agents — that caused a concurrency scare). End the spawn prompt with the mandated verbatim line: `First two tool calls: parallel Read of input docs, then single Edit appending draft scope to log. No source reads, Grep, ls, or Bash before the log Edit.`
2. On `done`: **verify via git** (`git log <base>..HEAD`, `git status`). Implementers sometimes leave **Cargo.lock propagation uncommitted** — commit it as part of the item (items 1, 2 needed this).
3. Pre-pass: `slop-reviewer` + `scope-reviewer` in parallel (one message). If **both 0 findings → skip responder/judge**, go to deep. Else implementer respond (self-loops) → judge.
4. Deep: 7 reviewers in parallel (errhandling, correctness, security, test, reuse, quality, efficiency) → implementer respond (self-loops) → judge.
5. **Responders self-loop and often continue past the first `done` notification** (intermediate HEADs, including self-rework commits). ALWAYS re-check `git log` for the true final HEAD before spawning the judge, and **judge against that final HEAD**. If a judge was already spawned against a stale HEAD, re-run against the real final HEAD and overwrite the verdict (happened on items 3 and 4).
6. **Notifications mislabel task-ids and replay.** Trust git/filesystem, not notification labels. Read verdicts with `grep -ioE 'APPROVED|REWORK|ESCALATE' <verdict-file>`.
7. On deep APPROVED: squash = `git reset --soft <item-base>` → `git add docs/adr/2026/06/11-<slug>/` → `git commit` (clean message). Sanity-check no foreign adr dirs staged: `git diff --cached --name-only | grep '^docs/adr/' | grep -v '<slug>'`. The pre-commit hook runs `make check` (must pass).
8. New item base = the squash commit. Each item's implementation also removes its own TODO.md entry + `TODO(slug)` code comments (items 1–4 did this).

REWORK handling: one rework round (fresh responder + fresh judge "round 2 — APPROVED or ESCALATE only"). ESCALATE → surface to user. (None hit this session; all items APPROVED round 1.)

## Final step (task 12) — after item 11 squashed

Execute deferred actions from `handoff.md`, then the **single END user gate**:

- **TODO.md deletes** (approved in triage, not yet executed): `rust-str-lit-shared`, `abi-gate-test-consolidation`, `crosscdylib-abi-size-probe`, `rust-cst-children-list-view` (superseded by item 11). Remove each entry **and** its `TODO(slug)` code comments.
- `extend-children-owned`: keep in TODO.md, don't implement; consider noting "re-open only with profiling evidence".
- Optional rider: one-line SAFETY comment in `cross_cdylib.rs` re size-probe analysis (full version in `exploration-crosscdylib-abi-size-probe.md`).
- Optional rider: migration-doc line "`node.children` returns a snapshot on the Rust backend; mutate via the named mutator API."
- Note: item 4 deep review created **2 new acceptable TODOs** (in TODO.md + code comments) — leave them.
- These finalization edits can be their own commit, or folded per user preference at the END gate.

**END user gate:** user reviews all per-item commits (`git log ef315be..HEAD`, diffs) once, at the end. One commit per item. No squash-to-single-history beyond per-item. No push without separate explicit authorization.

## Reference

- `triage.md` — USER DECISION per item (authoritative intent).
- `handoff.md` — original kickoff handoff.
- Each item dir: `request.md` (= requirements), `exploration*.md`, `design.md`, review artifacts.
