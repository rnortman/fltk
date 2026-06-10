# Judge verdict — design review

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Phase: design. Doc: `docs/adr/2026/06/10-preamble-helpers-into-cst-core/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer.md`); 2 findings. Doc phase — no added-TODOs walk.

## Findings walk

### design-1 — Fixed
Claim: §2.2's "post-`make fix` (rustfmt-normalized) form" instruction was ungrounded — no rustfmt/cargo-fmt exists anywhere in the flow; consequence: a literal implementer runs `cargo fmt` manually, committed `.rs` diverges from generator output, and the request's explicit "second `make gencode` → `git diff` empty" gate fails.
Underlying facts independently verified: Makefile `fix` target runs only `ruff check --fix` + `ruff format`; grep for `rustfmt`/`cargo fmt` across Makefile and `.github/` returns zero hits. Reviewer's consequence is real; severity should-fix-to-blocker (wrong mechanism for an explicit verification criterion).
Fix verified in design.md: §2.2 closing paragraph now states the true invariant — no formatter touches generated `.rs`, committed `.rs` byte-identical to raw `generate()` output, idempotency rests on generator determinism (`TestDeterministicOutput`) plus the §4 double-run check, with an explicit "Do not run `cargo fmt` on regenerated files" warning. §2.3 clarifies `make fix` normalizes regenerated Python only. §3 bullet rewritten as "Formatter-induced drift on generated `.rs`" naming the manual-`cargo fmt` failure mode, guarded by the §4 double-run check. No residual "rustfmt-normalized" language anywhere in the doc.
Assessment: fix addresses the consequence completely and consistently across §2.2/§2.3/§3. Accept.

### design-2 — Fixed
Claim: §4 gate item 4 (`grep -rn 'preamble-helpers-into-cst-core'` returns nothing, inherited verbatim from request.md) was mechanically unsatisfiable — the slug lives in immutable historical ADR docs and in this task's own ADR directory name; consequence: gate fails on day one; implementer stalls or edits immutable ADRs.
Underlying facts independently verified: repo grep finds the slug in `docs/adr/2026/06/06-fegen-cst-rs-single-source/*`, `docs/adr/2026/06/10-todo-burndown/*`, `docs/adr/2026/06/10-span-source-as-py-crosscdylib/*`, and this task's own ADR dir. Live join points are exactly `fltk/fegen/gsm2tree_rs.py` (the `TODO(slug)` comment) and `TODO.md` — matching CLAUDE.md's TODO-system definition (code comments + master list). Reviewer's consequence is real; severity should-fix (unexecutable verification gate).
Fix verified in design.md §4 item 4: grep scoped to `--include='*.py' --include='*.rs'` plus slug absence from `TODO.md`, with a parenthetical grounding why request.md's repo-wide form can never be empty (ADR immutability per CLAUDE.md). The scoped form is satisfiable once the implementation removes the TODO comment and `TODO.md` entry — both already listed in §2.4's files-touched table.
Assessment: fix is the reviewer's proposed remedy, verified executable. Accept.

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified.

---

## Verdict: APPROVED

All dispositions acceptable. Design's verification gates are now grounded against the repo; no open disputes.
