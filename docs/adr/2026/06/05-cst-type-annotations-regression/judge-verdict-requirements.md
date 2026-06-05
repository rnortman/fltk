# Judge verdict — requirements review

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Phase: requirements. Doc: `requirements.md`. Round 1.
Notes: 1 reviewer file; 6 findings (requirements-1 … requirements-6).

## Other findings walk

### requirements-3 — TODO(fltk-cst-regen-squeeze)
Reviewer claim: B2/B3/B4 acceptance is stated for "the CST backend(s) `fltk2gsm` depends on"; that default backend is `fltk_cst.py`, clean and never regenerated. B3 wants toolchain-generated artifacts, but regenerating `fltk_cst.py` reintroduces Regression-2 style violations, breaking Backward-compat / `make check`. Consequence: designer forced to silently pick one of three paths with different scope/contract implications, risking an accidental `make check` break or out-of-scope expansion.
Disposition: TODO — captured as open question **fltk-cst-regen-squeeze** in `requirements.md` (lines 104-108), laying out options (i) sidecar generated artifact [proposed default], (ii) minimal style fix, (iii) one-off hand-edit; marked "needs user decision."

Rubric Q1 (worth doing): yes — the squeeze is real and confirmed. Verified in tree: `plumbing.py` default path runs `Cst2Gsm` against the Python CST; Rust path injects `cst=pr.cst_module`; no `.pyi`/stub generator exists; `fltk_cst.py` clean. B3 ("no manual post-generation editing"), Backward-compat ("regenerating must not reintroduce errors"), and the out-of-scope Regression-2 fix genuinely collide. Surfacing it before design is correct.
Rubric Q2 (design/owner input required): yes — resolution is a load-bearing product-owner call. The three options carry different contract implications (entangle Regression 2 vs. accept a hand-edit deviation vs. add a sidecar file). This is not mechanically doable now; it needs the user to pick a path before design can proceed. The doc itself flags "needs user decision."
Furthermore (iteration-created check): this iteration did not create the squeeze — `fltk_cst.py`'s clean-but-unregenerated state and the style-emission gap predate this cycle. The TODO surfaces a pre-existing tension, not a defect this cycle introduced and hid. No silent-deferral violation.
Assessment: YES to both → TODO acceptable as a requirements-doc open question routed to user. Properly slugged, properly placed (open question with the squeeze spelled out + default + escalation path). The slug names a requirements open question, not a code site; for a requirements-phase deferral that is the right artifact, not a code `TODO(slug)` comment. Accept.

### requirements-1 — Fixed
Claim: B4 acceptance demands a Rust-backed CST whose present existence/wiring exploration doesn't confirm; reads as mandatory-now, risking over-build of a full Rust `.pyi` + compile-import harness.
Disposition: added **B3a — Rust backend status (precondition, confirmed)**; scoped B4 Rust-surface checks to mandatory-only-if-Rust-stub-generation-in-scope; Python-backend checks remain mandatory.
Verification: B3a present in doc (lines 54-58) and records the verified facts — Rust ext exists (`fltk/_native.abi3.so` confirmed in tree), injected on opt-in path (`plumbing.py` `Cst2Gsm(..., cst=pr.cst_module)` confirmed), no stub generator (confirmed: no in-tree `.pyi`, no emission in `gsm2tree_rs.py`). B2 acceptance (line 44) and B4 acceptance (line 67) edited to gate Rust checks on B3a scope. The disposition correctly *sharpens* the reviewer: existence claim softened ("exists but unstubbed"), scope-balloon risk preserved and addressed.
Assessment: fix addresses the consequence — the untestable-as-written / over-build risk is resolved by the precondition section and the conditional acceptance. Accept.

### requirements-2 — Fixed
Claim: "Dual-backend parity" constraint over-constrains toward a single shared static type, a near-design-decision; request only needs per-backend writable/checkable annotations.
Disposition: rewrote constraint as **Dual-backend typeability** (line 89), weaker request-faithful form; single-shared-type demoted to *preferred*.
Verification: line 89 now reads "Dual-backend typeability (weaker than a single shared type): `visit_*` annotations must typecheck for whichever backend is injected at the DI boundary … not a hard requirement … Do not invest in unifying … unless design judges it the cleanest path." Matches the suggested fix exactly.
Assessment: consequence (designer over-investing in nominal unification) defused. Accept.

### requirements-4 — Fixed
Claim: B1 example `<CstType>.Grammar` prejudges mechanism (a) Protocol-attribute form, contradicting the `mechanism` open question's neutrality.
Disposition: B1 example made mechanism-neutral.
Verification: B1 (lines 30) now reads "exact spelling per chosen mechanism — e.g. a bare imported `Grammar`, or an attribute-on-Protocol like `<CstType>.Grammar`; B1 does not prejudge this — see open question `mechanism`." Neutrality restored, both mechanisms named.
Assessment: anchoring risk removed. Accept.

### requirements-5 — Fixed
Claim: no-runtime-cost vs Protocol mechanism — TYPE_CHECKING/PEP-563 interaction underspecified; a Protocol-typed param referencing TYPE_CHECKING-only imports raises NameError without deferred annotations.
Disposition: extended No-runtime-cost constraint to permit PEP 563 / string-form annotations and require TYPE_CHECKING-only imports not raise NameError under `ModuleType` injection.
Verification: constraint (line 87) now states annotations "may rely on PEP 563 deferred evaluation … or string-form annotations; runtime evaluation … is not required and must not be forced — so a `TYPE_CHECKING`-only Protocol/stub import used in an annotation must not raise `NameError` under the runtime `cst: ModuleType` injection." Pins the interaction precisely.
Assessment: under-specified interaction now pinned. Accept.

### requirements-6 — Fixed (big-picture affirmation)
Claim: no structural defect; project is sound. One residual premise risk: Rust-backend present existence/wiring unconfirmed.
Disposition: no structural change requested; residual risk resolved via B3a + routed through `fltk-cst-regen-squeeze` and `rust-stub-source`.
Verification: the residual premise (Rust existence) is now factually settled by B3a (verified in tree). Reviewer's premise affirmed; the one actionable sub-point folds into requirements-1/-3, both handled.
Assessment: nothing to fix; routing is correct. Accept.

## Disputed items

None.

## Approved

6 findings: 5 Fixed verified against the doc + working tree, 1 TODO (fltk-cst-regen-squeeze) acceptable as a user-routed requirements open question.

---

## Verdict: APPROVED

All six dispositions acceptable. The five Fixed edits are present in `requirements.md` and address each finding's stated consequence; verified against working tree where load-bearing (Rust ext exists + injected, no stub generator, Python CST default — all confirmed). The single TODO passes both rubric questions (worth doing; needs user decision before design) and is correctly surfaced as a spelled-out open question with a proposed default and escalation path, not silently deferred. The squeeze it defers is pre-existing, not iteration-created.
