# Dispositions: design review round 1 — preamble-helpers-into-cst-core

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Design: `design.md` (this dir). Notes: `notes-design-design-reviewer.md`. Both findings fact-checked against source before disposition.

design-1:
- Disposition: Fixed
- Action: Verified true — Makefile `fix` target runs only `ruff check --fix` + `ruff format`; the formatting tail of `gencode` is also ruff-only; zero `rustfmt`/`cargo fmt` hits in Makefile or `.github/`. Committed `.rs` is raw `generate()` output (request.md MD5 is of the generator string). Replaced the §2.2 closing paragraph with the true invariant: no formatter touches generated `.rs`; committed `.rs` = generator output byte-for-byte; idempotency rests on generator determinism (`TestDeterministicOutput`) + the §4 double-run check; explicit "do not run `cargo fmt`" warning. Rewrote the corresponding §3 bullet (formatter-induced drift, manual-`cargo fmt` failure mode) and clarified in §2.3 that `make fix` after `make gencode` covers Python files only.
- Severity assessment: The design's stated mechanism for the gencode-idempotency verification criterion was factually wrong; a literal implementer could have run `cargo fmt` manually and failed the request's explicit "git diff empty on second run" gate.

design-2:
- Disposition: Fixed
- Action: Verified true — repo grep finds the slug in 4+ immutable historical ADR docs (`docs/adr/2026/06/06-fegen-cst-rs-single-source/*`, `docs/adr/2026/06/10-todo-burndown/*`, `docs/adr/2026/06/10-span-source-as-py-crosscdylib/*`) plus this task's own ADR dir, whose name is the slug. Live join points are exactly `fltk/fegen/gsm2tree_rs.py:245` and `TODO.md`. Rewrote §4 gate item 4 to `grep -rn 'preamble-helpers-into-cst-core' --include='*.py' --include='*.rs' .` returning nothing plus slug absence from `TODO.md`, with a parenthetical explaining why request.md's repo-wide form is unsatisfiable (ADR immutability per CLAUDE.md).
- Severity assessment: As written the gate was unpassable on day one; an implementer would either stall or edit immutable ADR documents to satisfy it.

Cleanup-editor not re-invoked: four localized paragraph/bullet replacements, no structural or interface change to the design.
