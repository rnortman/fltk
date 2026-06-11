# Judge verdict — pre-pass

Style: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Phase: pre-pass (Phase 0 of design.md — Span/SourceText boundary hardening). Base 63e6b76..HEAD 807d56a. Round 1.
Notes: notes-prepass-slop.md (4 findings), notes-prepass-scope.md (no findings). Dispositions: dispositions-prepass.md.

## Added TODOs walk

### TODO(rust-cst-children-list-view) at fltk/fegen/gsm2tree_rs.py:688 + TODO.md entry
Not a finding disposition — added by the diff (replaces the resolved `crosscdylib-abi-sentinel` entry); rubric applies to every added TODO.
Q1 (worth doing): yes — real backend divergence (Rust `children` getter returns a per-call snapshot list, Python backend returns the live internal list); design §7 Q4 records it and USER A4 explicitly directed adding this TODO.
Q2 (design/owner input required): yes — closing it requires a live sequence-proxy pyclass (new generated API surface); design §7 Q4 defers it as additive with the user's confirmation.
Not created/worsened this iteration: the snapshot getter predates this range (gsm2tree_rs.py `_children_getter`, pinned at tests/test_rust_cst_poc.py:47).
TODO system: slug entry in TODO.md and `TODO(slug)` comment at the relevant generator site — join key intact.
Assessment: acceptable.

Removed TODO check: `TODO(crosscdylib-abi-sentinel)` removed from TODO.md and from code comments. Justified — design §4.1 resolves it as scoped by A2; the layout-probe mechanism survived verification (`pyo3::impl_::pycell::PyClassObject` nameable and const-sized; used at span.rs `_fltk_cst_core_abi_layout` classattrs), so the "narrowed residual TODO" contingency in §4.1 item 2 does not trigger. No lingering slug references in source (only historical ADR docs).

## Other findings walk

### slop-1 — Fixed
Claim: `extract_source_text` layout check wrapped in `if let Ok` — absent or non-usize `_fltk_cst_core_abi_layout` silently skipped the check and proceeded to `downcast_unchecked`; SAFETY comment claimed both attrs checked. Consequence: documented safety guarantee not enforced; layout gate silently bypassed under exactly the skew it exists to catch.
Diff (807d56a, cross_cdylib.rs:70-89): `if let Ok(layout_attr)` → unconditional `getattr(...)?` (missing attr → Err) + `extract::<usize>().map_err(TypeError)?` (non-int → TypeError naming the actual type), mismatch → TypeError. SAFETY comment now matches enforced behavior.
Disposition pushback verified: responder correctly narrowed the finding — at ed73343, a missing `_fltk_cst_core_abi` *string* in `extract_source_text` fell through the outer `if let` to the hard `Err("expected fltk._native.SourceText, got ...")`; only the layout sub-check was silently skippable. The fixed part is exactly the part that was real.
Runtime: `test_source_text_abi_layout_mismatch_raises` passes (correct string + wrong layout → TypeError).
Assessment: fix complete. Accept.

### slop-2 — Fixed
Claim: `get_span_type` ABI string check wrapped in `if let Ok` — absent or non-str `_fltk_cst_core_abi` skipped the gate entirely and returned `Ok`, letting `extract_span`'s `downcast_unchecked` proceed unverified; doc comment's "fails here once with a clear TypeError" was false. This was the primary safety gate.
Diff (807d56a, cross_cdylib.rs:241-285): both checks unconditional — `getattr(...)?` for string and layout, `extract().map_err(TypeError)?`, mismatch → TypeError naming both values. Absence now fails the `GILOnceCell` init (fail-closed), with an inline comment recording "absent = old build = wrong ABI = mismatch, not pass" — the reviewer's exact requirement.
Runtime: subprocess tests `test_abi_string_mismatch_raises_type_error` and `test_layout_mismatch_raises_type_error` pass; control run passes.
Minor residual (nit, non-blocking): a *missing* attr propagates the raw `AttributeError` via `?` rather than a TypeError naming both ABI strings, so the doc comment's "clear TypeError" is imprecise for the absent-attr sub-case. Fail-closed property holds either way; the error names the missing marker attr. Does not make the disposition wrong.
Assessment: consequence (UB bypass) fully closed. Accept.

### slop-3 — Fixed
Claim: `IS_CANONICAL_CDYLIB` doc comment falsely asserted "same `GILOnceCell` epoch as `FLTK_NATIVE_SPAN_TYPE`"; cells are populated by separate `get_or_try_init` calls. Consequence: misleads init-ordering audits.
Diff (807d56a, cross_cdylib.rs:130-131): parenthetical replaced with the reviewer's suggested accurate wording — "Initializing this cell calls `get_span_type`, which populates `FLTK_NATIVE_SPAN_TYPE` as a side effect." Matches the code (`IS_CANONICAL_CDYLIB.get_or_try_init` closure calls `get_span_type`).
Assessment: accept.

### slop-4 — Fixed
Claim: ten test-method docstrings in `TestSpanAbiMarkerClassattr` (4) and `TestAbiLayoutClassattr` (6) were verbatim restatements of method names — machine-boilerplate tell.
Diff (807d56a, tests/test_rust_span.py): 10 lines removed; both classes' methods now docstring-free; class-level docstrings (which carry design-section references, non-restatement) retained.
Assessment: accept.

Scope reviewer: no findings; nothing to adjudicate.

## Disputed items

None.

## Approved

4 findings: 4 Fixed verified (all confirmed at the diff and at runtime — tests/test_rust_span.py 75/75 pass, including the three subprocess ABI-gate tests). 1 added TODO acceptable; 1 resolved TODO removal justified.

---

## Verdict: APPROVED
