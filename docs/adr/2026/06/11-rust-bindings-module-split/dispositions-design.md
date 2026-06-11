# Dispositions: design review round 1 — rust-bindings-module-split

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Notes reviewed: `notes-design-design-reviewer.md`. All four findings fact-checked against source at `tests/test_rust_span.py`, `crates/fltk-cst-core/src/cross_cdylib.rs`, `fltk/fegen/gsm2parser_rs.py`, `fltk/fegen/gsm2tree_rs.py`. All four verified accurate.

design-1:
- Disposition: Fixed
- Action: Verified — `tests/test_rust_span.py` constructs `phase4.SourceText` (lines 340, 350, 360), `phase4.Span`/`Span.with_source` (caching tests, ~636-647), and `cst.Span(0, 5)` in five ABI-gate subprocess scripts (454-455 et seq.). Scoped the drop per the suggested fix: §2.4 retitled "(scoped)" — `rust_cst_fegen` and `rust_parser_fixture` drop Span/SourceText; `rust_cst_fixture` keeps both at the extension top level with a corrected comment. §1 verification section rewritten to report the dependents honestly. §4.5 adjusted (fixture exception asserted present); §4.7 adds `tests/test_rust_span.py` including the subprocess-script updates (`phase4.cst.Config`, `phase4.Span` unchanged). §2.1 and §2.10 table updated for consistency.
- Severity assessment: As written, implementation would have broken ~10 tests including the entire cross-cdylib ABI-gate suite (version-skew safety coverage) or forced an improvised mid-implementation fixture redesign. Highest-impact finding of the round.

design-2:
- Disposition: Fixed
- Action: Verified — `extract_span` fast path `obj.extract::<Span>()` at `cross_cdylib.rs:258`; `extract_source_text` `downcast::<SourceText>()` at `cross_cdylib.rs:68`. §1 item 1 rewritten: extraction accepts both local and canonical instances; registration's real effect is exposing a Python-side constructor for module-local instances (never needed on main paths, load-bearing for the cross-cdylib fixture); the fixture comment's claim is "the wrong reason" rather than wholesale wrong. The corrected framing propagates into §2.4's replacement comment text. (Note: the false "accepts only the canonical type" claim originated in request.md line 16, not the design — the design repeated it without verifying. Corrected regardless; the requirements doc is upstream and not edited here.)
- Severity assessment: The false premise was the direct cause of design-1's blanket drop and would have propagated into the fixture comment, genparser help text, and docstrings, documenting wrong setter behavior for consumers.

design-3:
- Disposition: Fixed
- Action: Verified — cst.rs preamble (`gsm2tree_rs.py:263-267`) does not import `SourceText`; parser.rs's `use fltk_cst_core::{Shared, SourceText, Span}` (`gsm2parser_rs.py:274`) is in a different module from the cst structs, all rule references `cst::`-qualified. Took the reviewer's first option: dropped `SourceText` from `_RESERVED_CLASS_NAMES` and from §4.1's parametrization; §2.6 now documents the exclusion with the structural argument; §4.2 gains a positive generation test for a `source_text` rule (cheap, generator-level — serves as the compile-feasibility check the reviewer asked for at the source level; the structural argument makes a full rustc compile test unnecessary). Tightened the `Shared` entry description to "imported by generated cst.rs and parser.rs" per the reviewer's side note. §3 edge-case bullet updated.
- Severity assessment: Would have rejected a valid grammar, imposing a new unnecessary restriction on downstream grammar authors and enshrining a wrong rationale in the error message and tests.

design-4:
- Disposition: Fixed
- Action: §2.8 reworded to "the generator-source comment at `gsm2tree_rs.py:142-143` (a Python comment in the generator itself; it is not emitted into stubs — stub content is unchanged)". §2.10 table row wording aligned.
- Severity assessment: Minor wording error; trivial implementer time loss searching generated stubs for a nonexistent comment.

Cleanup-editor pass applied after edits (consistency: §2.1 "only submodules" exception list, §2.10 terminology).
