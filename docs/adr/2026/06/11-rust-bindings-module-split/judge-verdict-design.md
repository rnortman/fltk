# Judge verdict — design review

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Phase: design. Doc: `docs/adr/2026/06/11-rust-bindings-module-split/design.md`. Round 1.
Notes: `notes-design-design-reviewer.md` (4 findings). Dispositions: `dispositions-design.md` (all Fixed).

## Findings walk

### design-1 — Fixed
Claim: §1's "drop is confirmed safe" was false; `tests/test_rust_span.py` constructs `phase4_roundtrip_cst`'s module-local `Span`/`SourceText` (~10 tests incl. the full `TestSpanPathAbiGate` suite); consequence is broken version-skew coverage or an improvised mid-implementation fixture redesign.
Evidence: test usages independently verified — `phase4.SourceText("hello world")` at `test_rust_span.py:340/350/360`, subprocess script `cst.Config(span=cst.Span(0, 5))` at ~454-455, `phase4.Span(3, 7)` / `phase4.Span.with_source(...)` at ~636-647. Design now: §1 Verification rewritten to report these dependents explicitly with the no-substitute-path rationale; §2.4 retitled "(scoped)" — drop limited to `rust_cst_fegen`/`rust_parser_fixture`, `rust_cst_fixture` keeps both at top level with corrected comment; §2.1 lists the two top-level exceptions; §2.10 row asserts the keep; §4.5 asserts `phase4_roundtrip_cst.Span`/`.SourceText` present; §4.7 adds `test_rust_span.py` incl. the five subprocess scripts (`phase4.cst.Config` move, constructor refs unchanged).
Assessment: fix matches the reviewer's suggested scoping exactly and every consequential section was updated consistently. Accept.

### design-2 — Fixed
Claim: §1 item 1 falsely stated `extract_span` accepts only the canonical type; the false premise drove design-1's blanket drop and would have propagated wrong setter behavior into comments/help text/docstrings.
Evidence: fast paths independently verified — `obj.extract::<Span>()` in `extract_span` (`cross_cdylib.rs`, "Fast path: locally-registered Span type") and `obj.downcast::<SourceText>()` in `extract_source_text`. Design §1 item 1 now states extraction accepts both local and canonical instances, registration's real effect is the Python-side constructor for module-local instances, and the fixture comment "states the wrong reason" (the softened framing the reviewer asked for). Corrected framing carried into §2.4's replacement comment text.
Assessment: rewrite matches the code. Accept. (Disposition's note that the false claim originated in request.md is accurate context, correctly handled by not editing the upstream doc.)

### design-3 — Fixed
Claim: `SourceText` reserved-name entry rested on a false compile-conflict claim; consequence is rejecting a valid grammar and enshrining a wrong rationale in error message and tests.
Evidence: structural argument independently verified — cst.rs preamble (`gsm2tree_rs.py` `_preamble`) imports `CstError`/`Span`/`Shared` but not `SourceText`; parser.rs emits `use fltk_cst_core::{Shared, SourceText, Span};` (`gsm2parser_rs.py:274`) in a separate module. Design: `SourceText` dropped from `_RESERVED_CLASS_NAMES` (§2.6) and from §4.1's parametrization; §2.6 documents the exclusion with the structural argument; §4.2 adds a positive generation test for a `source_text` rule; `Shared`/`Span` entry descriptions tightened ("cst.rs and parser.rs" — both preambles, verified); §3 bullet states `source_text` is valid.
Assessment: reviewer's first option taken. The reviewer's "verify by compiling" ask was met at the source-structural level rather than via rustc; the argument is sound and now independently confirmed, so a compile test is not required for approval. Accept. Nit (non-blocking): adding a `source_text` rule to `collision_fixture.fltkg` (§2.9) would give compile-level proof for free.

### design-4 — Fixed
Claim: §2.8 said the gsm2tree_rs.py:142-143 comment is "emitted"; it is generator-source only.
Evidence: lines 142-143 verified as a Python comment between `lines.append` calls, never written to stubs. §2.8 reworded ("a Python comment in the generator itself; it is not emitted into stubs — stub content is unchanged"); §2.10 row aligned.
Assessment: Accept.

## Disputed items

None.

## Approved

4 findings: 4 Fixed verified.

---

## Verdict: APPROVED
