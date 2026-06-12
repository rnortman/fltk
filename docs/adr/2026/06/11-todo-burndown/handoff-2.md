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
- **Current HEAD: `0cc7a7f`.** This is the base for item 5. (Note: that HEAD is stale; there is a newer commit including this ADR doc and others.)
- Working tree clean except this handoff (committed separately).

## Remaining queue (severity/dependency order)

| # | slug | base | notes |
|---|------|------|-------|
| 5 | rust-bindings-module-split | 0cc7a7f | biggest surface; #6 depends on it |
| 6 | rust-naming-shared | after 5 | pure refactor; sequence after/with 5 |
| 7 | rust-cst-accessor-clone-efficiency | after 6 | edits gsm2tree_rs.py templates |
| 8 | rust-cst-debug-depth | after 7 | design user-approved |
| 9 | crosscdylib-abi-check-helper | after 8 | one deliberate error-msg change (pinned in request.md) |
| 10 | registry-gc-eviction-tests | after 9 | Python-side tests only |
| 11 | cst-named-mutators | after 10 | new public API; edits gsm2tree_rs.py |

Items 7, 8, 11 all edit `gsm2tree_rs.py` templates — serialized implementation handles overlap (rebase-style coordination as they drain). Implementation is **strictly serialized**; design already done for all.

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
