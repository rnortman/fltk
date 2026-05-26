# Judge verdict — deep review

Phase: deep. Base 6121025..HEAD f2b48c42. Round 1.
Notes: 7 reviewer files; 22 findings total (errhandling 1-6, correctness 1-2, test 1-10, reuse 1-4, quality 1-3, efficiency 1-2, security 0).

## Added TODOs walk

### quality-2 — TODO(backend-with-source-signature) at fltk/fegen/pyrt/span.py:7
Q1 (worth doing): yes — callers using `Span.with_source(start, end, str)` through the selector will break at runtime when Rust is active; reviewer documents the failure mode. Design explicitly deferred this (open question 2, design line 553-554).
Q2 (design/owner input required): yes — two viable approaches (Python `SourceText` wrapper vs Rust accepting both types) have different API-surface and performance tradeoffs. This is a cross-backend construction-API design decision, not a mechanical fix.
Assessment: TODO acceptable. Both rubric questions answered yes. `TODO.md` entry present, `TODO(slug)` comment at the relevant location.

## Other findings walk

### errhandling-1 — Fixed
Claim: `text_or_raise` in Rust collapses five failure modes into one "has no source" message.
Diff: `src/span.rs:98-135` now has distinct branches: "has no source" (line 100), "has negative indices" (line 105), "has inverted range" (line 110), "is out of bounds for source of length N" (line 119), "does not land on UTF-8 character boundaries" (line 126). Each diagnoses the actual failure.
Assessment: fix addresses the finding. Accept.

### errhandling-2 — Fixed
Claim: same issue in Python `text_or_raise`.
Diff: `terminalsrc.py:25-37` now diagnoses: no source, negative indices, inverted range, out of bounds — four distinct messages matching the Python-side failure modes (no mid-codepoint case in Python backend, correct).
Assessment: fix addresses the finding. Accept.

### errhandling-3 — Fixed
Claim: `except ImportError` too narrow; ABI mismatch/OSError/AttributeError crashes instead of falling back.
Diff: `span.py:18` widened to `except Exception:` with `warnings.warn` on fallback. `span_protocol.py:24` similarly widened to `except Exception:`.
Assessment: fix addresses the finding. Accept.

### errhandling-4 — Won't-Do
Claim: `Py::new` error propagation via `?`. Reviewer stated "no fix needed, noted for completeness."
Rationale: reviewer self-acknowledged no defect.
Assessment: Won't-Do correct. Accept.

### errhandling-5 — Won't-Do
Claim: silent `None` on mid-codepoint — diagnosability concern subsumed by errhandling-1.
Rationale: reviewer stated no separate fix needed beyond errhandling-1. `text()` returning `None` is the documented API contract; `text_or_raise` now provides the diagnostic path.
Assessment: Won't-Do correct. Accept.

### errhandling-6 — Won't-Do
Claim: identity check in `merge` — reviewer confirmed no defect.
Rationale: reviewer self-confirmed correct.
Assessment: Won't-Do correct. Accept.

### correctness-1 — Fixed
Claim: `intersect` lacks the cross-source guard that `merge` has; silently returns wrong-document text.
Diff: `src/span.rs:56-65` — `coerce_source` helper shared by `merge` and `intersect`, raises on different sources. `terminalsrc.py:43-48` — `_coerce_source` helper shared by both methods. `intersect` in both backends now calls the coerce helper before computing the intersection. Tests added: `test_intersect_different_sources_raises` in both `test_span.py:173-177` and `test_rust_span.py:209-215`.
Assessment: fix addresses the finding. Accept.

### correctness-2 — Fixed
Claim: Python `merge`/`intersect` uses `is not` (identity) for source comparison; CPython interning makes this fragile and inconsistent with Rust's `Arc::ptr_eq`.
Diff: `terminalsrc.py:45` — `_coerce_source` now uses `self._source != other._source` (value equality). Rust retains `Arc::ptr_eq` (correct — distinct `Arc` allocations have consistent identity semantics).
Assessment: fix addresses the finding — Python backend now uses value equality, eliminating the interning-dependent behavior. Rust backend's `Arc::ptr_eq` is deterministic. Accept.

### test-1 — Fixed
Claim: missing `test_merge_one_has_source` in Python tests.
Diff: `test_span.py:149-155` — `test_merge_one_has_source` added, asserts `has_source()` and `text()` on merged result.
Assessment: fix addresses the finding. Accept.

### test-2 — Fixed
Claim: missing `intersect` source-propagation tests in Python.
Diff: `test_span.py:161-180` — `test_intersect_with_source`, `test_intersect_adjacent_returns_none`, `test_intersect_different_sources_raises` added.
Assessment: fix addresses the finding. Accept.

### test-3 — Won't-Do
Claim: missing `Span(5,5).is_empty()` test. Reviewer self-retracted: test exists.
Assessment: Won't-Do correct. Accept.

### test-4 — Fixed
Claim: backend selector tests were trivially true (`is not None`).
Diff: `test_span_protocol.py:42-53` — `test_span_resolves_to_correct_backend` now asserts `_span_selector.Span is _fltk_native.Span` when Rust available, `is PySpan` otherwise. `test_unknown_span_resolves_to_correct_backend` asserts `type(...)` matches the active backend.
Assessment: fix addresses the finding. Accept.

### test-5 — Won't-Do
Claim: protocol conformance tests only check `isinstance`, not behavior. Reviewer noted "no fix required."
Rationale: behavioral coverage exists in `test_rust_span.py`; protocol tests are intentionally narrow smoke tests.
Assessment: Won't-Do correct. Accept.

### test-6 — Fixed
Claim: merge-different-sources tests didn't assert message content.
Diff: `test_span.py:141` and `test_rust_span.py:181` — both now use `pytest.raises(ValueError, match="cannot merge spans from different sources")`.
Assessment: fix addresses the finding. Accept.

### test-7 — Won't-Do
Claim: missing `len()` test for `Span(-1,-1)`. Reviewer self-retracted: test exists.
Assessment: Won't-Do correct. Accept.

### test-8 — Won't-Do
Claim: selector smoke test only checks `isinstance`. Reviewer said "no fix required."
Rationale: behavioral coverage in backend-specific test files.
Assessment: Won't-Do correct. Accept.

### test-9 — Fixed
Claim: `test_construction` for `SourceText` used vacuous `is not None` assertion.
Diff: `test_rust_span.py:222` — now asserts `isinstance(src, SourceText)`.
Assessment: fix addresses the finding. Accept.

### test-10 — Fixed
Claim: missing adjacent-span intersection test in Python.
Diff: `test_span.py:163-164` — `test_intersect_adjacent_returns_none` added.
Assessment: fix addresses the finding. Accept.

### reuse-1 — Fixed
Claim: bare `import fltk._native` before `importorskip` defeats the skip guard.
Diff: `test_rust_span.py:5` — single line `_native_module = pytest.importorskip("fltk._native", reason="Rust extension not available")`. No bare import.
Assessment: fix addresses the finding. Accept.

### reuse-2 — Won't-Do
Claim: three different skip idioms across test files.
Rationale: each file has different requirements (module-level variable vs per-test skip). `hasattr` in `test_span_protocol.py` is correct because `fltk._native` is always importable (the stub module exists); `hasattr` on the module checks whether the extension actually populated the `Span` name.
Inspection: `test_span_protocol.py:10` uses `_rust_available = hasattr(_fltk_native, "Span")` — this is appropriate because the file tests both Python and Rust paths and needs per-test skipping, not module-level skip.
Assessment: Won't-Do acceptable. The divergence is justified by different usage patterns. Accept.

### reuse-3 — Fixed
Claim: duplicated source-fallback expression in Python `merge` and `intersect`.
Diff: `terminalsrc.py:43-48` — `_coerce_source` method extracted, shared by both methods.
Assessment: fix addresses the finding. Accept.

### reuse-4 — Fixed
Claim: duplicated `or_else` expression in Rust `merge` and `intersect`.
Diff: `src/span.rs:56-65` — `coerce_source` helper in `impl Span`, shared by both methods.
Assessment: fix addresses the finding. Accept.

### quality-1 — Fixed
Claim: Python `merge` uses `is not` (identity) instead of `!=` (value) for source comparison.
Diff: same as correctness-2 — `terminalsrc.py:45` uses `!=`.
Assessment: fix addresses the finding. Accept.

### quality-3 — Fixed
Claim: `SourceText = None` gives pyright type `None` instead of `type | None`.
Diff: `span.py:14` — `SourceText: type | None = None` with explicit annotation.
Assessment: fix addresses the finding. Accept.

### efficiency-1, efficiency-2 — (no disposition needed)
Reviewer noted no action required for both. Neither appears in dispositions as a finding requiring response. Confirmed: no change needed.

### security — no findings
Security reviewer found no issues. Confirmed.

## Approved

22 findings: 13 Fixed verified, 7 Won't-Do sound, 1 TODO acceptable, 1 non-actionable (efficiency awareness items, no disposition required).

---

## Verdict: APPROVED
