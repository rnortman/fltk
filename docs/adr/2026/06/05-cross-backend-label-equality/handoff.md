# Handoff — CST type-annotation work (resume point, 2026-06-05)

Two related work streams in flight. Orchestrator (review-chain) workflow. Concise; resume from here.

## Git state
- Branch: **`cst-annotations-label-eq`** @ `2258b08` (HEAD attached). Created this session to anchor commits that were stranded on a detached HEAD (a `git checkout 1e67ed4` had detached it; `main` still sits at `1e67ed4`, behind).
- `main` = `1e67ed4`; `origin/main` = `f1e2a98`. **Nothing pushed.** No push without separate explicit user auth for a named repo+branch. No force-push, ever.
- **Base commits (matters for squash/PR):**
  - **Session-work base = `214dbe1`** (Phase 4). Our session's commits are **`214dbe1..HEAD` (16 commits)** — this is the range to squash if squashing *our* work.
  - **`f1e2a98` = `origin/main` = merge-base** = upstream/PR base. `f1e2a98..HEAD` = 21 commits.
  - Between them sit **5 pre-existing pyo3 commits `6121025..214dbe1`** ("Phase 0–4: Selectable Python/Rust CST backends"). **NOT our work** — present (uncommitted) at session start. Do **not** squash these into our commits; leave them as their own body of work.
- Untracked: both ADR dirs' working docs (requirements/design/dispositions/verdicts/notes/investigations/logs) are uncommitted.
- `make check` is **GREEN** at `2258b08` (lint, format-check, pyright, 783 pytest, cargo check/clippy/test).

## Stream A — Annotation regression + trivia fix  (ADR: docs/adr/2026/06/05-cst-type-annotations-regression/)
- **Status: COMPLETE, fully reviewed.** Restores CST-node type annotations via generated per-grammar `Protocol` (`fltk_cst_protocol.py`, bare names matching concrete classes), TYPE_CHECKING-imported into `fltk2gsm.py` with a boundary cast. Deep review APPROVED (round 2). Post-review user-driven changes (dropped the `*Node` suffix; fixed the Rust-backend `capture_trivia` divergence at source + removed the `Cst2Gsm` trivia filter) each verified, make check green.
- Commits (oldest→newest): `2ca7522` make fix/format-check gate · `dbbe0fe` ADR docs · `a2822d5` regen→make-fix convention (CLAUDE.md) · `3ffe12d`→`1e67ed4` annotation impl + deep review fixes · `8cc63e2` public-API CLAUDE.md · `498753f` drop `*Node` suffix · `d2e7757` ruff format fix · `a5cffc5` trivia-divergence fix.
- **PENDING ship-gate decisions (put to user):** (1) squash vs keep history (see Git-state base-commit note — our range is `214dbe1..HEAD`, do not fold in the Phase 0–4 commits); (2) commit the untracked ADR docs; (3) push (needs explicit auth).
- **Deferred future work:** `TODO(rust-cst-pyi)` (in `TODO.md`, committed `60a9019`) — generate Rust `.pyi` stubs so the Rust backend's CST classes are type-checkable (the larger project the annotation cycle explicitly scoped out; needs its own design cycle).

## Stream B — Cross-backend Label equality + NodeKind discriminant  (ADR: docs/adr/2026/06/05-cross-backend-label-equality/)
- **Status: requirements APPROVED (judge + user); design APPROVED (review chain); all §6 decisions settled. NOT IMPLEMENTED.**
- **Base for implementation: `2258b08`** (current HEAD).
- **Next step:** get user go/no-go to implement (+ single-shot vs incremental) → spawn `review-chain:implementer` with `design.md` + `requirements.md` + working dir + base `2258b08` → pre-pass (slop+scope) → deep review (7) → ship gate. Standard orchestrator workflow.

### Settled mechanism (see design.md §2)
- Canonical-name-keyed `__eq__`/`__hash__` co-emitted by BOTH generators (Python `gsm2tree.py` + Rust `gsm2tree_rs.py`), covering two enum families: existing per-node `Label` enums + a NEW `NodeKind` enum (one member per node type). Canonical forms: `"<Class>.Label.<NAME>"` and `"NodeKind.<NAME>"` (disjoint by construction).
- Rust uses a hand-written **plain `__eq__`** (not `__richcmp__` — validated precedent) + `__hash__` via `PyAnyMethods::hash` over a `PyString` (per-process salted-hash agreement). Same-type fast paths on both sides for the hot same-backend filter.
- New per-node discriminant `kind: Literal[NodeKind.<Rule>]` for narrowing **homogeneous** node-Protocol unions. Generator-emitted for every grammar (framework feature for out-of-tree consumers).
- **`self.cst` fully removed from `fltk2gsm.py`** (AC10, in-tree proof): label compares → static module-level `cst.X.Label.Y` (cross-backend-equal via the new `__eq__`); the two `isinstance(item, self.cst.Item)` sites → delete conjunct + `typing.cast("cst.Item", item)` (NOT a kind-guard — the `visit_items` union is `Item | Trivia | Span` and `Span` has no `kind`, verified pyright-failing). Drop the `Cst2Gsm` `cst=` param. Both backends must yield identical `gsm.Grammar` (`test_*_rust_equals_python`).

### Settled §6 decisions (all = design's proposed defaults)
1. `canonical_name` — internal marker only (not public API).
2. Python `repr`/`str` — left unchanged (eq/hash is the contract; key decoupled from repr).
3. String equality (`label == "..."`) — stays `False` (no string coercion).
4. Cross-grammar collision — **accept** (no grammar-id in canonical key). NB: orchestrator had earlier off-handedly said "qualify"; reversed to match approved design — qualification would risk *same-grammar* cross-backend equality (the actual goal). User may still veto.
5. `Cst2Gsm.__init__(cst=)` — **drop** the parameter (update `plumbing.py:176` call site).

### Read on resume (Stream B)
`design.md`, `requirements.md`, `notes-design-user.md` (settled direction), `exploration.md`, `isinstance-vs-label-investigation.md`, `items-child-union-investigation.md`, judge/dispositions/notes. Background in Stream A dir: `trivia-divergence-rootcause-v2.md`, `node-suffix-investigation.md`.

## Build / test
- `make check` = precommit gate (also the git hook). Generated code: regen → **`make fix`** → commit (normal; not a bug). Rust ext before Rust tests: `make build-native`, `make build-fegen-rust-cst`. Parity: `tests/test_phase4_fegen_rust_backend.py` (`test_*_rust_equals_python`), `fltk/test_plumbing.py`; protocol/pyright fixtures in `fltk/fegen/test_cst_protocol.py`.

## User preferences / process notes (avoid repeating mistakes)
- **FLTK is a framework/library consumed by OUT-OF-TREE apps.** Generated CST classes, parsers, label/NodeKind enums, accessors, type annotations = PUBLIC API. (Top-level CLAUDE.md section.) Never reason as if only in-tree consumers exist; "no in-tree consumer" is NOT evidence a change is safe/unneeded.
- **Do not over-escalate.** Decide non-issues with sensible defaults; only bring genuine forks. Over-escalation caused friction.
- Generated code failing the formatter before `make fix` is normal/expected. Trivia/Span in the internal children union is correct (runtime `capture_trivia` vs compile-time types) — not a wart, not a TODO.
- Orchestrator stays a traffic cop: spawn one-shot subagents, consume short summaries, don't read/write artifacts beyond coordination + handoff/notes. Verify implementer "green" claims independently (one prior false "make check green").
