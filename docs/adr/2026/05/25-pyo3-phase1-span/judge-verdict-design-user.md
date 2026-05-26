# Judge verdict — design review (user notes)

Phase: design. Doc: `docs/adr/2026/05/25-pyo3-phase1-span/design.md`. Round 1.
Notes: `notes-design-user.md` (3 findings, authoritative).

## Findings walk

### note-1 — Two swappable backends (Fixed)
Claim: previous design replaced Python Span with Rust; must retain pure-Python and deliver two swappable backends.
Evidence: design.md "Key architectural constraint" (line 13) states two swappable backends. Architecture section (lines 19-32) shows `terminalsrc.py` retained with updated API, `fltk._native` as Rust backend, `span.py` as selector. File Changes table confirms `terminalsrc.py` is *updated*, not replaced. Test plan splits into per-backend test files (`test_span.py` for Python, `test_rust_span.py` for Rust). Existing tests gate on pure-Python backend unchanged.
Assessment: fix is complete. Accept.

### note-2 — SpanProtocol + union alias (Fixed)
Claim: need a Protocol class for type annotations and a union alias for isinstance.
Evidence: design.md lines 36-59 define `SpanProtocol` as `@runtime_checkable` `typing.Protocol` with `start`, `end`, `text`, `text_or_raise`, `has_source`. `AnySpan = Union[_pymod.Span, _RustSpan]` with `ImportError` fallback. Rationale for both forms (Protocol for annotations, union for hot-path isinstance) is stated. `test_span_protocol.py` tests conformance and isinstance for both backends.
Assessment: fix is complete. Accept.

### note-3 — Throwing variant of text() (Fixed)
Claim: add a method that throws instead of returning None, with a better name than "ensure_text."
Evidence: `text_or_raise()` defined in both Python backend (lines 85-89) and Rust backend (lines 278-281). Returns `str`, raises `ValueError`. Name rationale at lines 111: user rejected "ensure_text"; `text_or_raise` follows `x_or_raise` convention. Added to `SpanProtocol` (line 49). Tests 9-10 in both backend test plans cover sourceless-raises and source-bearing-returns.
Assessment: fix is complete. Accept.

## Approved

3 findings: 3 Fixed verified.

---

## Verdict: APPROVED
