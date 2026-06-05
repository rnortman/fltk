# Judge verdict — requirements (user-note revision)

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: requirements (doc). Doc: `requirements.md`. Round 1 (user-notes revision).
Authoritative input: `notes-requirements-user.md` (2 directives). Dispositions: `dispositions-requirements-user.md`.
Role this round: verify the revision faithfully applied the user's rulings; do not re-litigate the user's calls.

## Findings walk

### user-note-1 — backend-agnostic annotations preserve Python↔Rust swappability — Fixed
User directive: annotations above the backend-selection level must be backend-agnostic so backends stay swappable.
Disposition claim: new Constraint + new section B6, with the agnostic type's Rust obligation wired through B3a/B4 scoping.
Doc verification:
- New Constraint **Backend-agnostic annotations above the selection level** present (`requirements.md:101`), demanding a static CST-node type that names no concrete backend, satisfied by both Python and Rust.
- New section **B6** present (`requirements.md:77–85`), positioned before **User-visible surface** (`:87`) as claimed. Its four acceptance bullets cover: a backend-agnostic static type usable on `Cst2Gsm`/future consumers (`:82`); B1 annotations written in that agnostic form, not naming `fltk_cst.Grammar`-concrete (`:83`); switching the injected backend requires no annotation edits (`:79`, `:84`); backend-specific access in agnostic code flagged by pyright (`:85`).
- Rust scoping wired: `:84` — "Python backend must satisfy the agnostic type unconditionally; the Rust backend must satisfy it once its static surface is produced (B3a)." Consistent with B3a's deferral permission (`:58`) and B4's Rust-conditional mandate (`:67`); no contradiction introduced.
Assessment: directive faithfully applied. This elevates the prior weaker "dual-backend typeability" (typecheck for whichever backend is injected, `:99`) into an explicit swappability guarantee at the consumer altitude — the user's stated intent. The weaker constraint is retained as the non-hard-requirement floor, not in conflict with B6. Accept.

### user-note-2 — fltk-cst-regen-squeeze ruled a NON-concern — Fixed
User directive: the regen "squeeze" is a non-concern — `make fix` after regen resolves formatter output; generating code that fails the formatter is normal; capture this (CLAUDE.md, separately).
Disposition claim: removed the `fltk-cst-regen-squeeze` open question; de-framed three load-bearing spots; doc references the convention but does not own documenting it.
Prior-round context (`dispositions-requirements.md`, `requirements-3`): the squeeze was a TODO framing regen of `fltk_cst.py` as a three-way contract conflict (B3 "no manual post-generation editing" vs Backward-compat vs out-of-scope Regression-2 style). The user authoritatively overrules that framing. Verified the prior disposition existed and was load-bearing, so removal is a genuine reversal, not a silent drop.
Doc verification:
- Open question removed: Open questions (`:106–114`) now hold `mechanism`, `di-boundary-escape`, `rust-stub-source`, `scope-of-regen` only. No `fltk-cst-regen-squeeze`. ✓
- B3 acceptance de-framed: `:52` reads "No manual *type-correctness* editing," explicitly stating generator output not passing the formatter is normal and `make fix` post-regen does not count as manual editing. ✓
- Backward-compat de-framed: `:104` clarifies "must not reintroduce errors" = *type* errors surviving `make fix`, not transient ruff/formatter violations; regenerate-then-`make fix` is an acceptable path. ✓
- scope-of-regen reduced: `:114` is now a pure this-cycle-vs-defer timing question; the "collide with out-of-scope style regression" framing is gone. ✓
- Ownership: doc references the `make fix` convention but does not claim to document it (`:52`, `:104`); consistent with the user's note that CLAUDE.md owns it separately. Not adjudicated here (out of this doc's scope).
Assessment: directive faithfully applied. Leaving the squeeze framing would have forced a sidecar-artifact workaround the user explicitly disclaimed. Accept.

## Carry-over (not re-litigated)

`requirements-1` (B3a, `:54–58`), `requirements-2` (Dual-backend typeability, `:99`), `requirements-4` (mechanism-neutral B1, `:30`), `requirements-5` (PEP 563 / `TYPE_CHECKING` constraint, `:97`) verified present and unchanged by this revision. `requirements-6` carried no structural edit. `requirements-3` correctly superseded by user-note-2. Dispositions' carry-over claim accurate.

## Disputed items

None.

## Approved

2 user directives: both Fixed-verified against the doc. 5 prior dispositions carried over intact.

---

## Verdict: APPROVED

Both authoritative user notes faithfully applied. B6 + Constraint added with correct B3a/B4 Rust scoping and no internal contradiction; squeeze open question removed and all three framing spots de-framed; carry-over dispositions intact.
