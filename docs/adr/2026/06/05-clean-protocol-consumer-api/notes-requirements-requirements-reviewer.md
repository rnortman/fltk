# Requirements review: Clean Protocol-Only Consumer API

> Concise. Precise. Complete. Unambiguous. Findings are observable-behavior level; no design dictation intended.

## requirements-1 — Contradiction between "no consumer cast" outcome and Open Question A default

Sections: In scope ("clean traversal/narrowing... **without** a CST-forced `typing.cast`"); System behavior §"Clean interleaved traversal"; AC 8; Open question `protocol-label-type-change` default **A**.

What's wrong: The doc mandates (AC 8, hard) that the interleaved walk yields each child "already narrowed to its concrete protocol child type" with no CST-forced cast — i.e. pyright must narrow the child after a label check, with the consumer importing **only** the protocol module. But exploration §3/§5 states twice (lines 184, 204, 208) that the casts at `:63`/`:75` are inherent to using `.children` directly and "would persist even with protocol-module enums unless the `children` type annotation were narrowed" — and that achieving narrowing requires a *new traversal primitive / more precise return type*, not merely adding enum values. Open question A's preferred Option A is purely additive (members gain runtime values, static type unchanged). Adding runtime values alone does **not** deliver AC 8. The requirements therefore assert an outcome (AC 8) whose only stated enabling mechanism (a narrowing traversal capability, In scope bullet 3) is unbounded, while the favored open-question resolution addresses a different problem (enum values for `==`).

Why: Request gating criterion: "No ... `cast` ... forced by the cst." Exploration line 208: "the `typing.cast` ... is inherent to the algorithm ... it would persist even with protocol-module enums unless the `children` type annotation were narrowed." Requirements In scope: "A clean traversal/narrowing capability ... Required as an outcome; its design is not specified here."

Consequence: A designer can satisfy Open Question A (additive enum values) and AC 6/7 and still completely fail AC 8 — the gating-criterion cast is not eliminable by the chosen mechanism. The two hard requirements (additive-only protocol change vs. cast-free narrowing walk) may be jointly unachievable without a new typed traversal surface that the doc has not committed to existing. Risk: build ships enum values, fltk2gsm still needs a cast or a workaround, gating criterion violated.

Suggested fix: State explicitly that AC 8 requires a *new typed traversal/narrowing surface on the protocol module* (capability-level, not design), distinct from the enum-value work, and that enum values alone are insufficient. Make this the load-bearing scope item, not a single In-scope bullet that reads as secondary.

## requirements-2 — Open question A "default A" may be technically impossible; doc presents it as the safe path

Section: Open questions `protocol-label-type-change`, Option A: "add runtime values while keeping the members' annotated type ... members go from no-value to having-a-value without changing their static type."

What's wrong: Exploration §1 (lines 28-35) explains the members are `ClassVar[object]` specifically because the natural `ClassVar[Label]` self-reference triggers pyright `reportUndefinedVariable`. "Add a runtime value while keeping the annotated type `object`" means the member is typed `object` — so to use it in `==` against a concrete Label the consumer needs nothing, fine. But for AC 8 the child-narrowing depends on the **traversal primitive's** types, not the Label member type, so Option A neither helps nor hurts narrowing. More importantly, the doc labels A "preferred / non-breaking" without confirming a value-carrying member typed `object` actually round-trips through the canonical-name bridge AND keeps the structural-mismatch test (`test_boundary_probe_documents_label_mismatch`) passing. The doc defers that test's fate entirely to Option B but Option A also changes the member from annotation-only to assigned — that is observable (`vars(Label)` / `hasattr` at runtime changes) and the doc itself (Constraints, line 78) calls it "a structural change to that public API." Calling A "additive and non-breaking" is asserted, not established.

Why: Requirements line 79: "must be **additive and non-breaking**." Line 78: "Changing per-node `Label` members from annotation-only ... to carrying runtime values is a structural change to that public API." These two co-located sentences are in tension; "structural change" + "non-breaking" need explicit reconciliation, not an assumed default.

Consequence: Designer adopts default A as settled, discovers the structural-mismatch test breaks or pyright cannot type the value-carrying member as `object` cleanly, and either silently flips to B (an accepted break that was never actually accepted) or ships a suppression inside the generated protocol module — which Constraints line 82 forbids. Either way a gating/constraint violation slips in under cover of "default assumed A."

Suggested fix: Demote A from "default assumed" to "must be validated in design; if A proves infeasible, B requires explicit user sign-off." Explicitly list the structural-mismatch test as in-play for A, not only B.

## requirements-3 — Gating criterion scoped to fltk2gsm.py only at the verifiable level; "user code" generality is unverifiable

Sections: Acceptance criteria 1-5, 8 (all phrased "`fltk2gsm.py` ..."); Gating criterion ("user code (and fltk2gsm.py is a model for user code)").

What's wrong: The verbatim gating criterion is about *user code* generally; fltk2gsm is named as a *model/proxy*. Every verifiable AC except 6/7/10 is bound to the single file fltk2gsm.py. That is reasonable as the concrete proof, but the doc nowhere states the general claim in a checkable way: "any protocol-only consumer performing {the equality comparison, the interleaved walk} can do so cleanly." A designer could special-case whatever fltk2gsm needs (e.g. expose exactly the one traversal shape `visit_items` uses) and pass all file-bound ACs while leaving the general protocol-only-consumer story incomplete — which is the actual request ("An above-the-parser consumer ... must be able to write clean code importing ONLY the generated protocol module").

Why: Request: "An above-the-parser consumer of FLTK-generated CST must be able to write clean code importing ONLY the generated protocol module." Gating criterion: "user code ... must be *clean*." Requirements AC 8 / Clean interleaved traversal are stated generally ("A protocol-only consumer can ...") — good — but AC 1-5 are file-only.

Consequence: Risk of a fltk2gsm-shaped point solution that satisfies acceptance but does not generalize, so the next out-of-tree consumer still hits a CST-forced cast/suppression. The request's primary intent (general protocol-only consumers) under-delivered.

Suggested fix: Add an AC asserting the generalized property at the capability level (the narrowing-walk and the enum-value comparisons are available to *any* protocol-only consumer from the protocol module alone), with fltk2gsm as the worked instance — keeping it observable, not a test plan.

## requirements-4 — `nodekind-runtime-dep` default leaves a real design fork under-constrained vs. the no-regression constraint

Sections: Constraints "No runtime-cost regression"; Open question `nodekind-runtime-dep` default A.

What's wrong: This one is largely sound — Option A (protocol owns its runtime values, no eager backend import) is correctly aligned with the no-regression constraint and the backend-agnostic posture. The gap: the constraint says "merely importing the protocol module must not introduce a heavy/eager dependency that was previously absent," but Option A still requires the protocol module to gain a runtime `NodeKind`-equivalent and per-node runtime Label values where today (exploration line 46) there is *zero* runtime enum machinery. That is, by construction, a new (light) runtime cost. The constraint as written ("not absent before") could be read to forbid even the lightweight enum objects the feature requires. The threshold ("heavy/eager") is the intended bar but the absolute phrasing undercuts it.

Why: Constraints line 83: "merely importing the protocol module must not introduce a heavy/eager dependency that was previously absent." Exploration line 46: "At runtime, the protocol module has no `NodeKind` import."

Consequence: Ambiguity invites a reviewer to reject the feature's own necessary runtime footprint, or invites a designer to over-engineer laziness. Minor, but worth tightening.

Suggested fix: Reword to bar specifically eager import of a *concrete backend* and any non-trivial cost; explicitly permit the protocol module's own lightweight enum value objects.

## requirements-5 (minor) — AC 9 behavioral-equivalence under "both backends" may exceed current fltk2gsm reality

Section: AC 9 "produces the same GSM output as before for the same inputs, under both backends."

What's wrong: AC 9 and the System-behavior closing bullet require fltk2gsm to behave identically "under both backends." Exploration does not establish that fltk2gsm.py is currently run against the Rust backend at all (it imports `fltk_cst`, the Python concrete module, line 8). If fltk2gsm has never consumed Rust-backend CST, "same as before under the Rust backend" has no "before" baseline and silently expands scope to making fltk2gsm Rust-capable. The cross-backend *equality* contract (AC 7) is the legitimately in-scope cross-backend claim; cross-backend *execution of fltk2gsm* may be unintended scope creep.

Why: AC 9: "under both backends." Exploration line 107: `from fltk.fegen import fltk_cst as cst` — the concrete Python module; no evidence fltk2gsm runs on Rust today.

Consequence: A designer may read AC 9 as "make fltk2gsm run on Rust-produced CST and prove output parity," pulling backend-portability work into a cleanup task. Or the criterion is unverifiable (no Rust baseline) and gets quietly dropped.

Suggested fix: Scope AC 9 to the backend fltk2gsm actually consumes (parity vs. pre-change behavior). Keep cross-backend guarantees confined to AC 7 (the equality/hash contract), which is the part the request's cross-backend concern actually targets.

## requirements-6 (minor) — "no CST-forced suppressions" is correctly carried, but the exemption boundary is asserted not tested

Sections: Gating criterion clause; Out of scope (S101); AC 3.

What's wrong: The S101-on-assert carve-out is correct and well-justified (CST-independent). No defect in the carve-out itself. The residual risk the doc does not flag: the *elimination* path for the casts might re-introduce a different suppression (e.g. a `# type: ignore` on a new narrowing call) that IS CST-forced — and AC 3/4/5 catch that only if the verifier reads "forced by CST" strictly. The doc relies on a human/agent judgment ("forced by the CST surface") that is inherently fuzzy at the boundary. This is acceptable but the doc should name the failure mode: a design that trades a `cast` for a `# pyright: ignore` has not satisfied the gating criterion.

Why: Gating criterion: "no `noqa` or other pyright/ruff suppressions forced by the cst." AC 3: "zero CST-forced ... suppressions."

Consequence: Without naming it, a designer could "eliminate the cast" by swapping it for an ignore comment and claim AC 2 (zero casts) while violating the spirit of AC 3.

Suggested fix: Add a sentence: eliminating a cast by substituting any other CST-forced suppression (`# type: ignore`, `# pyright: ignore`) does not satisfy the criterion.

## Big picture

The project is a good idea and faithfully tracks the request: protocol-only clean consumption is a real public-API quality goal consistent with CLAUDE.md's "generated output is public API." The cleanliness criterion is reproduced verbatim and threaded into most sections. The doc correctly stays out of design (no module/function dictation) and the out-of-scope fencing (equality contract, runtime_checkable, S101) is disciplined.

The one structural weakness is requirements-1/-2: the doc treats "add enum runtime values" (the easy, additive part) and "make the interleaved walk narrow without a cast" (the hard part exploration says needs a *new typed traversal surface*) as roughly co-equal in-scope items, while exploration is emphatic that enum values alone do NOT remove the `:63`/`:75` casts. Because the cast elimination is the explicitly named gating example in the request, the doc's center of gravity is misplaced: the load-bearing, possibly-infeasible-under-Option-A requirement is under-emphasized relative to the straightforward enum-value requirement. Fix requirements-1/-2 and the spec is sound.
