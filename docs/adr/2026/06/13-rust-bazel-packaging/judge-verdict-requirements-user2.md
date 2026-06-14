# Judge verdict — requirements (user notes, round 2)

Phase: requirements. Doc: `docs/adr/2026/06/13-rust-bazel-packaging/requirements.md`.
User notes (authoritative): `notes-requirements-user.md` ("User notes round 2",
three notes) + the round-1 "Bazel submodule" correction at the top of the same file.
Dispositions: `dispositions-requirements-user2.md`. Round 2 — APPROVED or ESCALATE only.

Doc phase: no Added-TODOs walk. Each user note is authoritative direction; the
job is to verify the claimed edits actually landed in `requirements.md` and that
they resolve the note's intent.

## Other findings walk

### user2-1 — "Bazel must build Rust" is not a differentiator; native-Rust is an assumed motivation — Fixed

User intent: stop presenting "Bazel needs to build Rust" as a per-option cost
(it is universal — a "Duh"), and record that a consumer adopts the Rust backend
in part *because* it wants to write its own native Rust.
Consequence if unfixed: requirements bias the downstream packaging-path design
by framing a universal precondition as a per-option downside.

Verified against `requirements.md`:
- Goals "Assumed motivation" paragraph, lines 15-19: states the consumer adopts
  the Rust backend in part to write its own native Rust alongside the PyO3
  bindings and the integration "should not preclude that." Matches claim.
- Design-space note, lines 210-216: "*every* path requires Clockwork's Bazel
  build to be able to build Rust — that is a baseline given, not a
  differentiator ... should not be weighed against any option," with the
  native-Rust motivation restated. Matches claim.
- Build-from-source option (A), lines 199-203: lists no "needs a Rust
  toolchain" downside — strawman framing removed. Matches claim.
- Constraints → "Toolchain (baseline given)", lines 176-179: reframed as a
  baseline present on every path, explicitly "not a factor that distinguishes
  one path from another." Matches claim.

Assessment: all four claimed sub-edits present and accurate; consequence
resolved. Accept.

### user2-2 — Regex / rust-regex-crate compatibility is incidental; assumption, not a gate — Fixed

User intent: do not "complain loudly" about clockwork.fltkg needing to work with
the rust regex crate; treat it as an incidental assumption and explicitly
out-of-scope, not a gating blocker.
Consequence if unfixed: a packaging/integration project mis-scoped into stalling
on a grammar-compatibility question the user has deprioritized.

Verified against `requirements.md`:
- Acceptance criterion 1, lines 72-75: no regex-compatibility precondition /
  "resolve first" parenthetical. Removed as claimed.
- Constraints → "Regex subset (assumption, not a gate)", lines 165-170: states
  the work *assumes* `clockwork.fltkg` is within the compatible subset and that
  any needed grammar/FLTK fix is "a separate, out-of-scope effort ... not a
  pass/fail gate." Matter-of-fact, not a complaint. Matches claim.
- Open questions, lines 187-245: no TODO(grammar-regex-subset) entry. Deleted as
  claimed.

Assessment: all three claimed sub-edits present; framing is incidental/out-of-
scope as the user asked; consequence resolved. Accept.

### user2-3 — Do not force a packaging-path decision in requirements; that is DESIGN — Fixed

User intent: requirements state "this is what must work"; the build-in-Bazel vs.
wheel/pip choice (and `rules_rust` placement) belongs to the designer and must
not be forced/ratified in the requirements doc.
Consequence if unfixed: inverts the requirements-vs-design separation, pre-empts
the designer, and asks the user to ratify a call they said is downstream.

Verified against `requirements.md`:
- Goals, lines 8-13: "*How* the Rust artifacts reach the consumer
  (build-from-source-in-Bazel vs. wheel/pip packaging, where `rules_rust` is
  registered) is a **design** decision to be resolved downstream — these
  requirements state what must work, not which packaging path is chosen."
  Replaces the prior "ratified decision on how FLTK should be consumed." Matches.
- In scope, lines 23 and 38-40: "obtains FLTK (the packaging/dependency
  mechanism is a design choice)"; the ADR deliverable now requires only that
  "whatever packaging/dependency mechanism and `rules_rust` placement the design
  ultimately lands on" be recorded — "(The *choice* is the designer's; this only
  requires that the chosen path be recorded.)" Matches claim.
- Open questions, lines 189-233: intro states the packaging/`rules_rust`
  decisions are "deliberately *not* forced here ... not as decisions the user
  must ratify before design begins"; the former decision-forcing TODO entries
  are replaced by a single non-binding "Design space" section that scopes
  options without selecting one. No "Proposed default to validate first /
  Confirm" ratification language survives for the packaging path. Matches claim.

Residual check: a single "Confirm" remains at line 244, but it is inside
TODO(equivalence-surface) — a pre-existing, separate question about
Rust-vs-Python CST equivalence strictness, untouched by and unrelated to this
note. It is a genuine open question, not a forced packaging-path decision.
Out of scope for user2-3; not a defect.

Assessment: all three claimed sub-edits present; the packaging-path decision is
no longer forced or put to the user for ratification; consequence resolved.
Accept.

### round-1 "Bazel submodule" correction — no further change (Fixed, carried)

Disposition asserts the earlier correction (FLTK is a *Bazel* submodule resolved
by `bazel_dep` + `git_override`, exposed as `@fltk//...`, not a git submodule)
remains correctly reflected and needs no round-2 change.
Verified: `exploration-clockwork.md` §1 (lines 5-8) carries the Bazel-submodule
framing with the not-a-git-submodule point demoted to a parenthetical;
`requirements.md` Design space (lines 199-203) describes the `@fltk//...` source
dep via `git_override`. This matches the round-1 verdict
(`judge-verdict-requirements-user.md`), which already APPROVED that fix as
source-accurate. No regression introduced by the round-2 edits. Accept.

## Approved

4 findings: 4 Fixed verified (3 round-2 notes + 1 carried round-1 correction).
Nothing disputed.

---

## Verdict: APPROVED

All three round-2 user notes are dispositioned Fixed and each claimed edit is
verified present and accurate in `requirements.md`: the universal "Bazel builds
Rust" precondition is reframed as a non-differentiating baseline with native-Rust
recorded as assumed motivation (user2-1); regex-crate compatibility is reframed
as an incidental, out-of-scope assumption rather than a gating blocker
(user2-2); and the packaging-path / `rules_rust`-placement choice is explicitly
returned to design and no longer forced or put to the user for ratification
(user2-3). The round-1 "Bazel submodule" correction remains correctly reflected.
No acceptance criterion or scope boundary was distorted; the lone residual
"Confirm" (equivalence-surface) is an unrelated pre-existing open question.
