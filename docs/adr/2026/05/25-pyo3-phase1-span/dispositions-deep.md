Concise. Precise. No padding. Audience: smart human/LLM.

---

errhandling-1:
- Disposition: Fixed
- Action: `src/span.rs` `text_or_raise` now emits distinct messages per failure mode: "has no source", "has negative indices", "has inverted range", "is out of bounds for source of length N", "does not land on UTF-8 character boundaries". Lines 98-135.
- Severity assessment: Diagnostic obscurity — on-call would waste time when the actual failure is a boundary violation or out-of-bounds, not a missing source.

errhandling-2:
- Disposition: Fixed
- Action: `fltk/fegen/pyrt/terminalsrc.py` `text_or_raise` rewritten to diagnose each failure before raising: no source, negative indices, inverted range, out of bounds. Lines 25-37.
- Severity assessment: Same as errhandling-1 — misleading message for all non-sourceless failures.

errhandling-3:
- Disposition: Fixed
- Action: `fltk/fegen/pyrt/span.py:14-19` widens `except ImportError` to `except Exception` and emits `warnings.warn` on fallback. `fltk/fegen/pyrt/span_protocol.py:24` likewise widened to `except Exception`.
- Severity assessment: A partially-broken Rust build (ABI mismatch → OSError, missing symbol → AttributeError) would previously crash the import rather than falling back; now falls back with a warning.

errhandling-4:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Correct propagation; `?` on `Py::new` converts OOM/GIL failure to a clean Python `ImportError`. Noted for completeness by reviewer.
- Rationale (Won't-Do): Reviewer explicitly marked this "no fix needed, noted for completeness." Changing correct error propagation would make the failure silent.

errhandling-5:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Silent `None` on mid-codepoint is a valid API choice; diagnosability concern is subsumed by errhandling-1's fix to `text_or_raise`.
- Rationale (Won't-Do): Reviewer stated this requires no separate fix beyond errhandling-1. `text()` returning `None` silently is the documented contract; callers needing diagnostics use `text_or_raise`.

errhandling-6:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: None — reviewer confirmed no defect, noted for completeness.
- Rationale (Won't-Do): Identity check in `merge` is intentional design; reviewer confirmed correct.

correctness-1:
- Disposition: Fixed
- Action: Both backends now raise `ValueError("cannot merge spans from different sources")` in `intersect` when both operands carry different sources. Rust: `coerce_source` helper at `src/span.rs:56-65` shared by `merge` and `intersect`. Python: `_coerce_source` helper at `terminalsrc.py:43-48` shared by both. Tests added: `test_intersect_different_sources_raises` in both test files.
- Severity assessment: Latent correctness bug — `intersect` of spans from different documents silently returned text from the wrong document. Wired capability with no production callers in Phase 1, but test coverage exists and callers will rely on it.

correctness-2:
- Disposition: Fixed
- Action: `fltk/fegen/pyrt/terminalsrc.py` `_coerce_source` now uses `self._source != other._source` (value equality) instead of `self._source is not other._source` (identity). This matches the design's intent ("merging spans from different documents is a bug") without being fragile w.r.t. CPython string interning. `src/span.rs` retains `Arc::ptr_eq` (correct — two `SourceText` handles are always distinct allocations).
- Severity assessment: Cross-backend behavioral inconsistency: Python `merge` would succeed or fail based on CPython interning luck for same-content sources; Rust always raises. Would cause surprising failures when the parse path is wired.

test-1:
- Disposition: Fixed
- Action: Added `test_merge_one_has_source` to `tests/test_span.py:149-155` — merges a source-bearing span with a sourceless span, asserts result has source and correct text.
- Severity assessment: Missing coverage for a distinct code path in Python `merge` source propagation.

test-2:
- Disposition: Fixed
- Action: Added `test_intersect_with_source` and `test_intersect_adjacent_returns_none` and `test_intersect_different_sources_raises` to `tests/test_span.py:161-180`.
- Severity assessment: Missing coverage for source propagation in Python `intersect`.

test-3:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: None — reviewer self-retracted; test already exists.
- Rationale (Won't-Do): Reviewer confirmed the test exists in `test_span.py`.

test-4:
- Disposition: Fixed
- Action: `tests/test_span_protocol.py::TestBackendSelector` now asserts `_span_selector.Span is _fltk_native.Span` when Rust is available, and `is PySpan` otherwise. Same for `UnknownSpan` type check. Lines 41-53.
- Severity assessment: The old tests were trivially true and wouldn't catch a broken backend selector.

test-5:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Mild — protocol conformance tests are intentionally narrow smoke tests; behavioral correctness is covered by the backend-specific test files.
- Rationale (Won't-Do): Reviewer explicitly said "no fix required" and behavioral coverage exists in `test_rust_span.py`.

test-6:
- Disposition: Fixed
- Action: `tests/test_span.py::test_merge_different_sources_raises` and `tests/test_rust_span.py::TestMerge::test_merge_different_sources_raises` now use `pytest.raises(ValueError, match="cannot merge spans from different sources")`.
- Severity assessment: Minor — exception type change would silently pass the old tests.

test-7:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: None — reviewer self-retracted; test exists.
- Rationale (Won't-Do): Reviewer confirmed `test_len_unknown` exists.

test-8:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Low — narrowly-scoped integration smoke test; behavioral coverage in the backend-specific test files.
- Rationale (Won't-Do): Reviewer explicitly said "no fix required."

test-9:
- Disposition: Fixed
- Action: `tests/test_rust_span.py::TestSourceTextOpaque::test_construction` now asserts `isinstance(src, SourceText)` instead of `src is not None`.
- Severity assessment: The old assertion was vacuous and provided no regression protection.

test-10:
- Disposition: Fixed
- Action: Added `test_intersect_adjacent_returns_none` to `tests/test_span.py:163-164`.
- Severity assessment: Off-by-one in the `s >= e` boundary check would produce `Span(5,5)` instead of `None` for adjacent spans and go undetected.

reuse-1:
- Disposition: Fixed
- Action: `tests/test_rust_span.py:5` — replaced `import fltk._native as _native_module` + `pytest.importorskip(...)` with a single `_native_module = pytest.importorskip(...)`. The bare import on line 5 would fail before the guard fired when the extension is absent.
- Severity assessment: The skip guard was functionally broken on machines without the Rust extension built.

reuse-2:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Low — three idioms for the same skip condition. `hasattr` variant in `test_span_protocol.py` is correct and works because `fltk._native` is always importable (the `.so` is present); `hasattr` on the module is the right check since the module exists but `Span` may not.
- Rationale (Won't-Do): Each test file has a slightly different requirement: `test_rust_span.py` needs the module as a variable; `test_span_protocol.py` needs per-test skipping. Forcing one idiom would require restructuring both files for minimal benefit. Documented divergence is acceptable.

reuse-3:
- Disposition: Fixed
- Action: `fltk/fegen/pyrt/terminalsrc.py:43-48` — extracted `_coerce_source(self, other)` method shared by `merge` and `intersect`, eliminating duplicated source-selection expression.
- Severity assessment: Low — two sites in the same class; extracted as part of the correctness-1 fix.

reuse-4:
- Disposition: Fixed
- Action: `src/span.rs:56-65` — extracted `coerce_source(&self, other: &Span)` in a plain `impl Span` block (not `#[pymethods]`), shared by `merge` and `intersect`.
- Severity assessment: Low — mirrors reuse-3; extracted as part of correctness-1 fix.

quality-1:
- Disposition: Fixed
- Action: Same as correctness-2 — Python `_coerce_source` uses `!=` (value) instead of `is not` (identity). `terminalsrc.py:45`.
- Severity assessment: See correctness-2 — fragile identity check causes spurious errors based on CPython interning.

quality-2:
- Disposition: TODO(backend-with-source-signature)
- Action: `TODO.md` entry added; `fltk/fegen/pyrt/span.py` docstring documents the asymmetry and references the TODO.
- Severity assessment: Silent runtime breakage for callers using `Span.with_source(start, end, str)` through the backend selector when Rust is active. Will surface during Phase 2 wiring.

quality-3:
- Disposition: Fixed
- Action: `fltk/fegen/pyrt/span.py:12` — `SourceText: type | None = None` gives correct static type so callers can narrow with `if SourceText is not None`.
- Severity assessment: Without the annotation, pyright inferred `None` (not `type | None`), making type narrowing impossible for callers.
