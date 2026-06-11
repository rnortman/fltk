# Design review findings: rust-bindings-module-split

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Reviewed: `design.md` against `request.md`, `exploration.md`, and source at base commit 7ddec4a. All cited file:line references were checked; the ones not listed below verified clean (registration sites, `cross_cdylib.rs` span routing functions, `gsm2tree_rs.py` validation/preamble/register_classes, `gsm2parser_rs.py` bindings/TODO/chokepoint at line 82, `plumbing.py:105-110`/`264`, `genparser.py` help text and ValueError handling, Makefile targets, `TODO.md:88`, ADR 06/06 design.md:58, `test_rust_cst_poc.py` top-level PoC imports, `_EXPECTED_CLASSES`, pyo3 0.23.5, no emitter writes lib.rs, sys.modules parent-import side-effect import mechanics, collision-fixture Rust-compile feasibility).

---

## design-1 — §1 "Drop is confirmed safe" is false: tests/test_rust_span.py depends on module-local Span/SourceText of phase4_roundtrip_cst

**Quote (§1, Verification):** "Grep over `tests/`, `fltk/`, `docs/`: no access to `fegen_rust_cst.Span`, `rust_parser_fixture.Span`, `phase4_roundtrip_cst.Span`, or `.SourceText` on any generated consumer module. ... Drop is confirmed safe."

**What's wrong:** The grep missed aliased access. `tests/test_rust_span.py` uses the module-local registrations of `phase4_roundtrip_cst` (the `tests/rust_cst_fixture` crate) extensively:
- `phase4.SourceText("hello world")` — lines 340, 350, 360 (foreign-cdylib `_with_source_unchecked` tests).
- `phase4.Span(3, 7)`, `phase4.SourceText(...)`, `phase4.Span.with_source(...)` — lines 636, 646-647 (`TestSpanToPyobjectCaching` consumer-cdylib tests).
- Five subprocess scripts: `import phase4_roundtrip_cst as cst; node = cst.Config(span=cst.Span(0, 5))` — lines 454-455, 485-486, 523-524, 563-564, 603-604 (`TestSpanPathAbiGate`, the entire ABI-gate suite).

These are not mechanically updatable imports: constructing a *foreign-cdylib* `Span`/`SourceText` instance from Python — the precondition for every cross-cdylib ABI-gate and slow-path test — is only possible through the consumer module's registered classes. §2.4's drop from `tests/rust_cst_fixture/src/lib.rs` removes the only constructor path.

**Why (source-backed):** request.md line 16: "Verify first that no test or doc relies on the module-local attributes." The verification was performed and reported, but its result is wrong. Test plan §4.7 lists eight test files for import updates; `test_rust_span.py` is absent, confirming the design believes it is unaffected.

**Consequence:** Implementation following §2.4 as written breaks ~10 tests including the whole cross-cdylib ABI-gate suite (version-skew safety coverage), or the implementer improvises an unplanned fixture redesign mid-implementation. Violates request verification expectation "All existing tests pass with updated imports."

**Suggested fix:** Scope the drop: remove Span/SourceText from `rust_cst_fegen` and `rust_parser_fixture` (no dependents found), but keep them in `rust_cst_fixture` deliberately — it is the dedicated cross-cdylib test fixture and needs a Python-side constructor for foreign instances. Replace the wrong lib.rs comment with a correct one ("registered so tests can construct foreign-cdylib instances; not required for span extraction"). Update §4.5 and §4.7 accordingly (add `tests/test_rust_span.py` handling).

---

## design-2 — §1 item 1 misstates extract_span behavior; "vestigial" premise overdrawn

**Quote (§1, item 1):** "`extract_span` accepts only the canonical type (`cross_cdylib.rs:256-268`). The `m.add_class::<Span>()` in consumer modules exposes a *different* type whose instances the module's own setters reject."

**What's wrong:** Both claims are false. `extract_span` (`cross_cdylib.rs:256-281`) has a fast path — `obj.extract::<Span>()` at line 258 — that accepts the *locally registered* Span of the executing cdylib before falling back to the canonical-type check. Same for `extract_source_text` (`downcast::<SourceText>()`, line 68). So a consumer module's own setters *accept* its module-local Span instances. Empirical proof: `test_rust_span.py:455` (`cst.Config(span=cst.Span(0, 5))` on `phase4_roundtrip_cst`) passes today.

**Why:** Code at `crates/fltk-cst-core/src/cross_cdylib.rs:257-260, 67-72`. The exploration did not cover this (it analyzed registration order, not extraction paths); the design introduced the claim.

**Consequence:** This false premise is what made §2.4's blanket drop look free (design-1), and it would propagate into the "corrected" fixture comment, genparser help text, and docstrings, documenting behavior that is wrong (consumers would be told setters accept only `fltk._native.Span` when local instances also work). The related claim that the `rust_cst_fixture/src/lib.rs:6-7` comment is "factually wrong" is itself an overstatement: registration is not needed for *extraction* (the lazy type-object point is correct), but it is what makes local instances constructible, and those instances do flow through the setter fast path.

**Suggested fix:** Correct §1 item 1: extract paths accept local-type instances via the fast path; registration's real effect is exposing a constructor for module-local instances, which (a) on main parse paths is never needed (returned spans are canonical) but (b) the cross-cdylib test fixture relies on.

---

## design-3 — §2.6 `SourceText` reserved-name entry justified by a false claim

**Quote (§2.6):** "`SourceText` is included even though cst-only generation would compile: a grammar valid for cst-only but invalid once a parser is generated is a trap."

**What's wrong:** A rule named `source_text` does not make parser generation uncompilable. The rule-derived `pub struct SourceText` is emitted in cst.rs (`mod cst`); parser.rs's `use fltk_cst_core::{Shared, SourceText, Span}` (`gsm2parser_rs.py:274`) is in a different module, and all rule references in parser.rs are `cst::`-qualified — no E0255, no conflict. (Contrast `span`/`shared`/`cst_error`, where the struct lands in the *same* module as the cst.rs `use` preamble, `gsm2tree_rs.py:263-265` — those E0255 claims are correct, as is the `node_kind` struct-vs-enum conflict.) Post-split there is no Python-level collision either: after §2.4, no fixed `SourceText` is registered in any generated submodule.

**Consequence:** The check rejects a grammar that compiles and works on both sides, imposing a new, unnecessary restriction on downstream grammar authors; §4.1's parametrized test (`source_text` → ValueError) enshrines the wrong behavior with a wrong rationale in the error message ("imported by generated parser.rs").

**Suggested fix:** Either drop `SourceText` from `_RESERVED_CLASS_NAMES` and from §4.1's parametrization, or keep it with an honest rationale (deliberate conservatism / parallel with Span) — but verify by compiling a `source_text` grammar before deciding. Note `Shared` is also imported by parser.rs, so the entry descriptions could be tightened while there.

---

## design-4 — §2.8 ".pyi safety comment emitted at gsm2tree_rs.py:142-143" — not emitted

**Quote (§2.8):** "Update ... the safety comment emitted at `gsm2tree_rs.py:142-143`."

**What's wrong:** Lines 142-143 are a comment in the generator's own source (between the `lines.append("# ruff: noqa: N802")` and `lines.append("from __future__ import annotations")` calls); it is never written into the generated .pyi. Minor wording error.

**Consequence:** Implementer searches generated stubs for a comment that doesn't exist; trivial time loss, possible confusion about whether stub content changes (the design elsewhere says stub content is unchanged — updating a generator-source comment is consistent with that, an emitted comment would not be).

**Suggested fix:** Say "the generator-source comment at gsm2tree_rs.py:142-143".

---

No other findings. Requirements coverage is otherwise complete: collision fixture + headline test (§2.9/§4.3) map to the request's primary acceptance criterion and are Rust-compile-feasible (cst-side `Parser`/`ApplyResult` structs and `Py*` handles live in `mod cst`, all parser.rs references are qualified); `node_kind` decision + tests (§2.6/§4.1) satisfy the residual-collision requirement; topology (§2.1-2.3), `fltk._native` restructure (§2.5), plumbing semantics (§2.7), and parity expectations (§4.8) are grounded and internally consistent; scope is disciplined (no transitional aliases, pairwise-collision work correctly deferred to a TODO).
