# Requirements review — CST type annotations regression

Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

Reviewed: requirements.md against request + exploration.md + ruff-investigation.md. Did not read code.

Overall: strong doc. Faithful to request spirit (make annotations *possible* + pyright-checkable; tightening + ADR explicitly out of scope, matching request verbatim). Stays at requirements altitude on mechanism (Protocol vs .pyi left to design). Findings below are mostly scope-edge clarifications, not structural defects.

---

## requirements-1 — B4 acceptance demands a Rust-backed CST that exploration does not confirm exists yet

Section: B4 acceptance ("For the Rust-backed CST, the surface pyright sees matches the actual PyO3 runtime surface"), plus Goals line 7, B2 line 44, Constraint "Dual-backend parity" (line 82).

What's wrong: The doc treats the Rust/PyO3 CST as a present, consumable backend that `fltk2gsm.py` annotations must typecheck against *now*. Exploration says `gsm2tree_rs.py` generates `.rs` from GSM, but does not confirm a compiled, importable Rust CST module exists that `Cst2Gsm` is actually run against, nor that any stub generator exists (open question `rust-stub-source` line 94 admits "it does not mention an existing stub generator"). The request lists "the Rust/pyo3 CST work" as in-scope surface, but the gating B1 acceptance only names `Cst2Gsm` constructed with "a non-default (e.g. Rust-backed) CST module" — the Rust path may be aspirational this cycle.

Why: B4 acceptance ("every label accessor ... present at runtime on a CST node is present in the static surface ... A deliberately-wrong access ... is flagged") requires a concrete Rust runtime surface to verify against. If no compiled Rust CST is wired in yet, this acceptance is untestable as written and forces building a full Rust stub generator this cycle.

Consequence: Designer may over-build a Rust `.pyi` generation pipeline (and the test harness to compile+import the extension) when the achievable, in-spirit deliverable is: a shared static type both backends *will* satisfy, validated today only against the Python backend. Risk of large wasted scope on the Rust half.

Suggested fix: Add an explicit precondition/decision: does a compiled Rust CST module exist and get injected this cycle? If not, scope Rust to "the shared static type is defined such that the future Rust backend can satisfy it; B4 verification runs against the Python backend, Rust stub generation may be a thin or deferred increment." Pull this into the `scope-of-regen` / `rust-stub-source` open questions explicitly rather than leaving B4 reading as mandatory now.

---

## requirements-2 — "Dual-backend parity" constraint may over-constrain the design toward a single shared type

Section: Constraints, "Dual-backend parity" (line 82): "the Python dataclass CST and the Rust/PyO3 CST must be describable by the same consumer-facing static type (or by interchangeable types)".

What's wrong: Requiring one shared consumer-facing static type is a near-design-decision. The request only asks that annotations be *writable and pyright-checkable* across whichever backend is injected. A valid design could annotate `fltk2gsm` against a Protocol that the Python dataclass CST structurally satisfies, without ever proving the Rust type satisfies the *same* nominal type (esp. given requirements-1 uncertainty). "(or by interchangeable types)" softens it but the headline still pushes a unification requirement.

Why: Goals (line 7) frame the bar as "an annotation can be written that names the CST node type, and pyright resolves it ... without Any-degradation." That is satisfiable per-backend; it does not strictly require a single cross-backend type.

Consequence: Designer may invest in reconciling Python-dataclass and PyO3 surfaces into one Protocol/alias hierarchy — non-trivial, and possibly blocked by requirements-1 — when a lighter per-backend or structural-Protocol solution meets the request.

Suggested fix: Restate as the weaker, request-faithful form: "fltk2gsm's `visit_*` annotations must typecheck for whichever backend is injected at the DI boundary." Keep single-shared-type as a *preferred* design option, not a hard constraint.

---

## requirements-3 — Open question `scope-of-regen` is load-bearing but left unanswered, and its default may not satisfy B2/B4 acceptance

Section: Open questions `scope-of-regen` (line 95); interacts with B2/B3/B4 acceptance.

What's wrong: B2/B3/B4 acceptance is stated for "the CST backend(s) `fltk2gsm` depends on." `fltk2gsm` consumes the **fltk grammar** CST (`fltk_cst.py`), which per ruff-investigation is CLEAN and was last regenerated 2025-07-22, manually cleaned, never regenerated since. If the chosen mechanism emits a *new* typing artifact (Protocol/.pyi) from the generator, satisfying B3 ("regenerating ... (re)produces the typing artifacts") for `fltk_cst.py` requires regenerating it — which the default proposes to defer for `unparsefmt_*` but is ambiguous for `fltk_cst.py`. Regenerating `fltk_cst.py` risks reintroducing the Regression-2 style violations (single quotes, `typing.Optional`) that B5/backward-compat forbids, because the generator still emits style-wrong code (out of scope to fix).

Why: Constraint "Backward compat" (line 85): "regenerating them must not reintroduce errors." Out-of-scope item (line 20) excludes the style-emission fix. These collide if `fltk_cst.py` must be regenerated to get its typing artifact.

Consequence: Either (a) designer regenerates `fltk_cst.py`, reintroducing ruff violations and breaking `make check` / backward-compat, or (b) designer hand-adds the typing artifact for `fltk_cst.py` without regenerating, violating B3's "no manual post-generation editing" / "generated by the toolchain." A real squeeze the doc doesn't resolve.

Suggested fix: Resolve explicitly: confirm whether `fltk_cst.py` (the backend fltk2gsm actually depends on) is regenerated this cycle. If the typing artifact must come from the toolchain but regeneration trips Regression 2, acknowledge that the minimal style-emission fix needed to keep `fltk_cst.py` clean may be unavoidably pulled in (the doc's own line 20 escape hatch: "unless design finds the type work cannot proceed without touching it"). Flag to user.

---

## requirements-4 — B1 example annotation `<CstType>.Grammar` leans toward the (a) Protocol mechanism

Section: B1 (line 30): "`visit_grammar(self, grammar: <CstType>.Grammar)`"; Open question `mechanism` (lines 89-92).

What's wrong: Minor altitude slip. The example `<CstType>.Grammar` (attribute-on-a-type access) implicitly presumes the CST module is typed as a single object/Protocol with member classes — mechanism (a). Mechanism (b) (direct `.pyi` + shared alias) would annotate as a bare imported `Grammar`, not `<CstType>.Grammar`. The example subtly prejudges the open question it claims to leave to design.

Why: `mechanism` open question (line 92) says "Design decides ... Proposed default: leave to design." The B1 example contradicts the neutrality.

Consequence: Designer may anchor on the Protocol-attribute form, foreclosing the simpler direct-import stub form. Low impact but worth neutralizing.

Suggested fix: Make the example mechanism-neutral, e.g. "names the CST Grammar node type (exact spelling per chosen mechanism)" rather than `<CstType>.Grammar`.

---

## requirements-5 — No-runtime-cost constraint vs. Protocol mechanism: TYPE_CHECKING guard interaction underspecified

Section: Constraints "No runtime cost / no runtime import cycles" (line 80); B1 acceptance (line 36, annotation valid under runtime `ModuleType` injection).

What's wrong: If mechanism (a) annotates `self.cst` with a Protocol, the annotation is evaluated against a `ModuleType` value at runtime. The doc requires zero runtime cost and `TYPE_CHECKING`-guarding, but does not state that `from __future__ import annotations` (or string annotations) is assumed — without it, a Protocol-typed parameter annotation referencing `TYPE_CHECKING`-only imports raises `NameError` at runtime. This is a real constraint on the design that the doc gestures at but doesn't pin.

Why: Constraint line 80 + B1 line 36 together imply annotations must be both present and runtime-harmless under DI; the resolution mechanism (deferred annotations) is unstated.

Consequence: Minor — designer likely handles it, but an under-specified interaction could yield a solution that typechecks but breaks import, or vice versa. Worth one sentence.

Suggested fix: Add: "Annotations may rely on PEP 563 deferred evaluation / string form; runtime evaluation of CST-type annotations is not required."

---

## requirements-6 (big-picture) — Project is a good idea; one premise check

Section: overall.

What's wrong: Nothing structural. The project restores genuinely-lost static safety on a CST visitor and is squarely what the request asks. The deferred-LATER framing (no pyright tightening, no ADR) is internally consistent and matches request verbatim. The redirect notes (lines 97-100) correctly surface the two ways the user might have meant more scope (Regression 2 style fix; pyright tightening). Good adversarial hygiene already present in the doc.

One residual premise risk worth surfacing to the user: the whole Rust-backend half (requirements-1/-2) rests on a backend whose present existence/wiring exploration does not confirm. If the Rust CST is not yet injectable, ~half the doc's constraints (dual-backend parity, B4 Rust-surface accuracy, rust-stub-source) describe work that cannot be validated this cycle and should be explicitly deferred — otherwise the cycle balloons.

Consequence: Without confirming Rust-backend status, scope estimate and acceptance testability are unreliable.

Suggested fix: Before design, get a one-line answer from user: "Is a compiled Rust CST module injected into `Cst2Gsm` today, or is it still source-generation-only?" Routes requirements-1/-2/-3.
