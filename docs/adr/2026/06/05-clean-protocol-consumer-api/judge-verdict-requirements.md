# Judge verdict — requirements review

> Concise. Precise. Complete. Unambiguous.

Phase: requirements. Doc: `requirements.md`. Round 1.
Notes: 1 reviewer file (requirements-requirements-reviewer); 6 findings, all dispositioned Fixed.
Ground truth: `exploration.md`, gating criterion (verbatim, reproduced in both notes and doc).

## Other findings walk

### requirements-1 — Fixed
Claim: doc treats "add enum runtime values" (additive) and "make the interleaved walk narrow without a cast" (hard) as co-equal in-scope items, while exploration §3/§5 (lines 204, 208) states the `:63`/`:75` casts are inherent to walking `.children` directly and persist with enum values alone — narrowing needs a *new typed traversal surface*. Consequence: designer ships enum values, passes AC 6/7, still fails AC 8 (gating-example cast not eliminated); two hard requirements jointly unmet.
Source-back: exploration line 208 ("the `typing.cast` ... is inherent to the algorithm ... would persist even with protocol-module enums unless the `children` type annotation were narrowed"); line 204 same.
Fix verified: `requirements.md:24` In-scope bullet now marked **(Load-bearing.)**, declares a *new typed traversal/narrowing surface* "distinct ... from the enum-value work," cites exploration §3 line 208 / §5 line 204, states enum values alone do not eliminate the casts. `requirements.md:62` (System behavior §"Clean interleaved traversal") adds the matching bullet: narrowing "delivered by the load-bearing typed traversal/narrowing surface ... **not** by enum runtime values."
Assessment: fix addresses the consequence at the cited mechanism; center-of-gravity correction the reviewer asked for is in place. Accept. (High severity, correctly graded.)

### requirements-2 — Fixed
Claim: Option A presented as "default assumed / safe," but Constraints calls the no-value→has-value transition "a structural change to that public API" — "structural change" + "non-breaking" co-located and unreconciled; A not confirmed to keep `test_boundary_probe_documents_label_mismatch` passing. Consequence: designer treats A as settled, hits the structural-mismatch test or an `object`-typing problem, silently flips to B (an unaccepted break) or ships an in-module suppression (Constraints-forbidden).
Source-back: exploration line 192 (structural-change framing), line 200 (T2b test `test_boundary_probe_documents_label_mismatch` asserts concrete-not-assignable-to-protocol).
Fix verified: `requirements.md:109` replaces "Default assumed: A" with "**Status: A is the target, but NOT a settled default — it must be validated in design.**"; names the two validation conditions ((1) `object`-typed member round-trips the canonical-name bridge, (2) T2b test kept passing — "in play for A, not only B"); requires explicit user sign-off before any A→B fallback; forbids silent flip.
Assessment: matches the reviewer's suggested fix verbatim in substance. Accept. (High severity, correctly graded.)

### requirements-3 — Fixed
Claim: AC 1-5 are bound to `fltk2gsm.py` only; request asks for *any* protocol-only consumer to write clean code from the protocol module alone. Consequence: a fltk2gsm-shaped point solution passes file-bound ACs while the general request intent under-delivers.
Source-back: request quote "An above-the-parser consumer ... must be able to write clean code importing ONLY the generated protocol module."
Fix verified: `requirements.md:102` adds AC 11 — capabilities proven on fltk2gsm (AC 1-5, 8) are "general protocol-module properties, not a point solution," available to "*any* protocol-only consumer," fltk2gsm "the worked instance, not a special case." Stated as an observable property, not a test plan.
Assessment: fix delivers the generalized capability-level AC. Accept. (Medium, correctly graded.)

### requirements-4 — Fixed
Claim: "No runtime-cost regression" worded absolutely ("dependency that was previously absent") could forbid the feature's own necessary lightweight enum objects; exploration line 46 confirms zero runtime enum machinery today. Consequence: ambiguity invites rejecting the feature's footprint or over-engineering laziness. Reviewer flags this minor.
Source-back: exploration line 46 ("At runtime, the protocol module has no `NodeKind` import").
Fix verified: `requirements.md:88` reworded to "no eager *concrete-backend* import / no heavy dependency," explicitly permitting "the protocol module's own lightweight enum value objects ... the bar is 'no eager concrete-backend import / no heavy dependency,' not 'zero new runtime objects.'"
Assessment: threshold-correct rewording. Accept. (Low, correctly graded.)

### requirements-5 — Fixed
Claim: AC 9 "produces the same GSM output ... under both backends" has no Rust baseline — fltk2gsm consumes the concrete Python module (`from ... import fltk_cst`), never runs on Rust CST; "under both backends" silently expands scope to Rust-portability. Consequence: designer pulls backend-portability into a cleanup task, or the criterion is unverifiable and quietly dropped.
Source-back: exploration line 107 (`from fltk.fegen import fltk_cst as cst`), line 212 (NodeKind/Label only; no Rust execution).
Fix verified: `requirements.md:35` Out-of-scope bullet excludes making fltk2gsm *execute* against Rust CST (no Rust baseline). `requirements.md:100` AC 9 rescoped to "the backend it actually consumes (the Python concrete backend)"; cross-backend guarantee confined to AC 7 (equality/hash). The legitimate cross-backend claim (AC 7 equality) is preserved.
Assessment: scope correctly narrowed; legitimate cross-backend equality retained. Accept. (Medium, correctly graded.)

### requirements-6 — Fixed
Claim: S101 carve-out is correct, but the cast-elimination path could re-introduce a *different* CST-forced suppression (`# type: ignore` / `# pyright: ignore`); doc should name that a cast traded for an ignore does not satisfy the gate. Consequence: designer "eliminates" the cast by swapping for an ignore, claims AC 2 (zero casts), violates the spirit of AC 3.
Source-back: gating criterion "no `noqa` or other pyright/ruff suppressions forced by the cst"; AC 3 "zero CST-forced ... suppressions."
Fix verified: `requirements.md:15` adds "**Substitution does not satisfy the criterion.**" under the gating section; mirrored at `requirements.md:63` (System behavior §"Clean interleaved traversal").
Assessment: failure mode named in both the gating section and the relevant behavior section. Accept. (Low-Medium, correctly graded.)

## Disputed items

None. All six findings carry a real, source-backed consequence (no bogus-reviewer cases); all six dispositions are Fixed and each fix is present in the revised `requirements.md` and addresses the stated consequence. No Won't-Do to test; no doc-phase TODO walk.

## Approved

6 findings: 6 Fixed verified (requirements-1..6). No findings deweighted, none disputed.

---

## Verdict: APPROVED

All six reviewer findings carry stated, exploration-grounded consequences; all six Fixed dispositions verified present in `requirements.md` and addressing those consequences. The two load-bearing corrections (requirements-1 center-of-gravity to the narrowing surface; requirements-2 demoting Option A from settled default to design-validated with user sign-off) are the structurally important ones and both landed. Requirements spec is sound.
