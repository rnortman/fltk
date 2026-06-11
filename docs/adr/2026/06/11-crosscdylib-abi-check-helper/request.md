# Request: unify the duplicated cross-cdylib ABI pair check

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Refactor (security-primitive consolidation) in `crates/fltk-cst-core/src/cross_cdylib.rs`, with one deliberate error-message behavior change.

**Origin:** TODO.md slug `crosscdylib-abi-check-helper`, user-approved triage (`docs/adr/2026/06/11-todo-burndown/triage.md` item 9, USER DECISION: Do).

## Background

Two sites perform the identical two-step ABI gate (string marker `_fltk_cst_core_abi`, then layout int `_fltk_cst_core_abi_layout`) guarding `downcast_unchecked`:
- `extract_source_text`: check at `cross_cdylib.rs:98-135` (function starts line 66) — wrapped in `if let Ok(marker) = getattr(...)`, so a MISSING marker silently falls through to the generic "expected fltk._native.SourceText, got X" error at lines 163-166.
- `get_span_type`: check at `cross_cdylib.rs:313-358` (function starts line 292) — uses `map_err` with a specific "has no _fltk_cst_core_abi marker" message.

Validated divergences (full text comparison in `exploration.md`, this dir): FIVE error strings differ in wording between the paths ("object reports" vs "fltk._native.Span reports"; "old build without layout probe" vs "partial-upgrade build"; differing prefixes on the non-int case), plus the structural missing-marker divergence above. The TODO's line numbers were stale; the ones above are verified.

Helper feasibility verified: only `T` (for `size_of::<PyClassObject<T>>()`) and a type-label string vary. `fn check_abi_pair<T: PyClass>(ty: &Bound<'_, PyType>, type_label: &str) -> PyResult<()>` works; both `SourceText` and `Span` are `PyClass`.

## Fix shape

Extract the helper; call from both sites; uniform message templates parameterized by type label. ~40 duplicated lines → one helper + two calls.

**Deliberate behavior change (user-approved via triage):** `extract_source_text`'s missing-marker case changes from the generic "expected fltk._native.SourceText, got {type}" to a specific "no ABI marker (pre-sentinel build)" style error — strictly more informative; both are `PyTypeError`. Call this out in design and pin with a test; do not slip it in silently.

## Constraints / non-goals

- The two sites' caching architectures stay as-is and are OUT of scope: `get_span_type` checks the canonical imported type once per process (`GILOnceCell`); `extract_source_text` checks caller-supplied types per cache miss with a single-slot foreign-type cache (`cross_cdylib.rs:76` area). The helper unifies check logic only.
- Error type stays `PyTypeError` everywhere.
- SAFETY comments referencing the checks (`extract_source_text` / `extract_span`) must remain accurate post-refactor.
- This is the safety gate for `unsafe` downcasts — reviewers should hold it to the highest scrutiny; no semantic weakening of either check.

## Verification expectations

- The 5-scenario subprocess gate tests (`tests/test_rust_span.py` `TestSpanPathAbiGate`, lines 417-600: control, string mismatch, layout mismatch, missing marker, missing layout attr) updated for unified messages and passing.
- New/updated assertions pin the changed missing-marker message on the SourceText path.
- `cargo test -p fltk-cst-core --no-default-features` + full Python suite; `make fix`.
