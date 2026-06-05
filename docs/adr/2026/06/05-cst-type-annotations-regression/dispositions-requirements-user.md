# Dispositions: user-note revision — CST type annotations regression

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Post-human-gate revision. Notes file: `notes-requirements-user.md` (authoritative chat directives). Two notes applied to `requirements.md`.

---

user-note-1 (backend-agnostic annotations / Python<->Rust swappability):
- Disposition: Fixed
- Action: Added new constraint **Backend-agnostic annotations above the selection level** (Constraints section) and new acceptance section **B6 — Backend-agnostic annotations preserve swappability** (System behavior, before User-visible surface). B6 requires a single backend-agnostic static CST-node type usable in annotations above the backend-selection level; that `fltk2gsm.py`'s `visit_*` annotations (B1) be written in that agnostic form; that switching the injected backend require no annotation edits; and that backend-specific accesses in agnostic code be flagged by pyright. Wired the agnostic type's Rust-side obligation through B3a/B4 scoping (Python backend satisfies unconditionally; Rust once its static surface exists).
- Severity assessment: High value. This elevates "dual-backend typeability" (prior weaker form: just typecheck for whichever backend is injected) into an explicit swappability guarantee at the *consumer* altitude — the user's actual intent. Without it the designer could satisfy the doc with a per-backend-keyed annotation that breaks swappability the moment the Rust backend is injected.

user-note-2 (fltk-cst-regen-squeeze ruled a NON-concern):
- Disposition: Fixed
- Action: Removed the `fltk-cst-regen-squeeze` open question entirely from the Open questions section (it was a TODO surfaced from prior round disposition `requirements-3`). Removed the "squeeze" framing from three load-bearing spots: (1) **B3 acceptance** — changed "No manual post-generation editing" to "No manual *type-correctness* editing," explicitly stating generator output not passing the formatter is normal and `make fix` post-regen is the established convention, not forbidden editing; (2) **Backward compat constraint** — clarified "must not reintroduce errors" means *type* errors surviving `make fix`, not transient ruff/formatter violations that `make fix` resolves, and that regenerate-then-`make fix` is an acceptable path; (3) **scope-of-regen open question** — removed the "collide with the out-of-scope style regression" framing, reducing it to a pure this-cycle-vs-defer timing question.
- Severity assessment: High. This reverses the prior round's TODO(fltk-cst-regen-squeeze), which had framed regenerating `fltk_cst.py` as a contract conflict between B3, Backward-compat, and Regression 2. The user rules there is no conflict: generated code failing the formatter is expected and `make fix` is the resolution. Leaving the squeeze framing in would have forced the designer to architect a sidecar-artifact workaround to avoid touching `fltk_cst.py` — unnecessary complexity the user has explicitly disclaimed.
- Note: the user states the convention itself (generator output need not pass the formatter; `make fix` resolves it) is being documented in CLAUDE.md separately. The requirements doc now references the convention but does not own documenting it.

---

## Carry-over (prior dispositions, not re-litigated)

`requirements-1`, `requirements-2`, `requirements-4`, `requirements-5`, `requirements-6` from `dispositions-requirements.md` stand unchanged; user notes did not touch them. `requirements-3` (TODO(fltk-cst-regen-squeeze)) is **superseded** by user-note-2: the TODO is resolved (ruled a non-concern) and removed from the requirements doc.
