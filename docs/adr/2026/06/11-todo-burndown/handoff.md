# TODO Burndown — Handoff for Workflow Kickoff

Style: concise, precise, complete, unambiguous. No padding, no preamble.

State: triage complete and user-arbitrated (`triage.md`, USER DECISION lines). ADR dirs prepared for all accepted items: each contains a self-contained `request.md` plus the validated exploration(s). **No workflows have been started.** Base commit at preparation time: `7ddec4a` (branch `rust-idiomatic-cst-api`; note uncommitted artifacts from the prior idiomatic-CST review also sit in the working tree).

## How to kick off (next session)

Per `docs/blocked-todo-burndown-workflow.md` Phase 5-7: for each item, spawn the standard chain starting at requirements (explorations are already adequate — skip the explore stage; `request.md` + `exploration*.md` are the inputs). Explore/requirements/design may run in parallel across items; **implementation strictly serialized**. Burndown policy: skip ship-gate, no pushes ever, squash each item to a single commit on main including its ADR docs (watch for untracked files — `git reset --soft` is not sufficient).

## Work items (suggested implementation order: severity-first)

| # | ADR dir | Item | Notes |
|---|---------|------|-------|
| 1 | `docs/adr/2026/06/11-parse-depth-limit/` | Depth limit (merged apply+parser TODOs) | Process-kill DoS. Resolves 2 TODO slugs. |
| 2 | `docs/adr/2026/06/11-consume-regex-anchor/` | Anchored regex matching | CPU DoS (O(R×N²)). |
| 3 | `docs/adr/2026/06/11-nullable-loop/` | Loop guard + validator gap | **TDD mandatory; escalate to user if no triggering grammar can be constructed.** Both backends. |
| 4 | `docs/adr/2026/06/11-error-msg-escape/` | Escape C0 in error messages | Both backends lockstep; parity comparator constraint. |
| 5 | `docs/adr/2026/06/11-rust-bindings-module-split/` | Split cst/parser pyo3 modules | USER REFRAME of parser-bindings-name-collision. Biggest design surface in the batch. |
| 6 | `docs/adr/2026/06/11-rust-naming-shared/` | Shared child-enum naming | Sequence after/with #5 (user direction). Pure refactor. |
| 7 | `docs/adr/2026/06/11-rust-cst-accessor-clone-efficiency/` | Pymethod accessor clones | Corrected fix shape in request.md (lock invariant). |
| 8 | `docs/adr/2026/06/11-rust-cst-debug-depth/` | Non-recursive node Debug | Generator template edit. |
| 9 | `docs/adr/2026/06/11-crosscdylib-abi-check-helper/` | Unify ABI gate check | One deliberate error-message change, pinned in request.md. |
| 10 | `docs/adr/2026/06/11-registry-gc-eviction-tests/` | Registry GC/eviction/ABA tests | REFRAMED: Python-side tests only; no Rust unit-test infra. |
| 11 | `docs/adr/2026/06/11-cst-named-mutators/` | Named mutators, both backends | NEW item replacing rust-cst-children-list-view. New public API — design naming deliberately. |

Items 1-4 are independent of each other. Item 6 depends on item 5. Items 7, 8, 11 all edit `gsm2tree_rs.py` templates — parallel design is fine, serialized implementation handles the overlap; expect rebase-style coordination in whatever order they drain.

## Deferred actions (NOT yet done — do alongside/after the batch)

- **TODO.md edits pending.** Deletes approved but not executed: `rust-str-lit-shared`, `abi-gate-test-consolidation`, `crosscdylib-abi-size-probe`, `rust-cst-children-list-view` (superseded by item 11). Each has TODO(slug) code comments to remove too. `extend-children-owned`: user said keep in TODO.md, don't do (consider updating its entry to note "re-open only with profiling evidence" per triage item 13).
- Optional rider from triage item 15: one-line SAFETY comment in `cross_cdylib.rs` noting the size-probe analysis (full version in `exploration-crosscdylib-abi-size-probe.md`).
- Optional rider from triage item 12: migration-doc line "`node.children` returns a snapshot on the Rust backend; mutate via the named mutator API."
- TODO slugs resolved by work items: items 1 (×2 slugs), 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 — each implementation removes its TODO.md entry + code comments as part of its commit.

## Reference docs in this dir

- `triage.md` — recommendations + USER DECISION per item (authoritative for intent).
- `exploration-<slug>.md` — adversarial validations (copies placed in each work-item dir).
- `exploration-accessor-clone-archaeology.md` — history of what the idiomatic-CST work did/didn't fix (copy in item 7's dir).
