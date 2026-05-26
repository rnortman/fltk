Commit reviewed: 90074aa

test-1
File: tests/test_span.py (no specific line) / tests/test_rust_span.py (no specific line)
Missing coverage: `merge()` where one span has a source and the other does not — the design specifies that the result should carry that source and be usable for `text()`. `test_span.py` covers same-source merge and different-source raise, but not the asymmetric case. `test_rust_span.py` covers it (`test_merge_one_has_source`), so the pure-Python backend is the gap.
Consequence: A regression in pure-Python `merge()` source-propagation for the mixed-source case would go undetected.
Fix: Add `test_merge_one_has_source` to `tests/test_span.py`: `a = Span.with_source(0, 5, "hello world"); b = Span(3, 8); merged = a.merge(b); assert merged.has_source(); assert merged.text() == "hello w"`.

test-2
File: tests/test_span.py (no specific line)
Missing coverage: `intersect()` with a source — that the result carries the source and `text()` works on it. Present in `test_rust_span.py::TestIntersect::test_intersect_with_source`, absent from `test_span.py`.
Consequence: A bug in pure-Python `intersect()` source propagation would not be caught.
Fix: Add a test analogous to `test_rust_span.py::TestIntersect::test_intersect_with_source` to `tests/test_span.py`.

test-3
File: tests/test_span.py (no specific line)
Missing coverage: `Span(5, 5).is_empty()` returning `True` — i.e., zero-width span with non-negative indices. The test plan item 18 lists this, and `test_rust_span.py::TestIsEmpty::test_zero_width_is_empty` covers it for Rust. It is absent from `test_span.py`.
Consequence: A pure-Python `is_empty()` regression on the zero-width case would go undetected.
Fix: Add `assert Span(5, 5).is_empty() is True` in `test_span.py`. (The existing `test_is_empty_zero_width` does cover `Span(5, 5)` — on re-reading the file, this test exists. Disregard this finding.)

test-4
File: tests/test_span_protocol.py::TestBackendSelector
Quality issue: `test_span_resolves` asserts `_span_selector.Span is not None`. Since `Span` is a class, this is trivially `True` — it would pass even if the wrong object were imported or if the backend selector was broken in a non-None way. Similarly `test_unknown_span_resolves` only checks not-None.
Consequence: The selector tests do not verify that the correct backend is active. A misconfigured import (e.g., always returning the Python backend even when Rust is available) would not be caught.
Fix: When Rust is available, assert `_span_selector.Span is _fltk_native.Span`; when not available, assert `_span_selector.Span is PySpan`. For `UnknownSpan`, the existing `test_unknown_span_equals_neg1_neg1` gives some signal, but asserting the type (or `is`) would be more precise.

test-5
File: tests/test_span_protocol.py::TestProtocolConformanceRust
Quality issue: Both Rust tests assert only `isinstance(s, SpanProtocol)` and `isinstance(s, AnySpan)`. These are structural isinstance checks that verify the method *names* exist, not that they return correct results. A Rust `Span` that had the right method names but wrong behavior would pass.
Consequence: Protocol conformance tests are smoke tests. They detect missing methods but not behavioral regressions in the Rust backend.
Note: `test_rust_span.py` does cover behavior comprehensively; `test_span_protocol.py` is correctly narrow in scope. This is a mild redundancy gap, not a critical miss. No fix required — document as known limitation.

test-6
File: tests/test_span.py::test_merge_different_sources_raises / tests/test_rust_span.py::TestMerge::test_merge_different_sources_raises
Quality — both tests: The only assertion is that `ValueError` is raised. They do not assert any message content. The design specifies a specific message ("cannot merge spans from different sources"). This is a minor omission but means a refactor changing the exception type to something else (e.g., `RuntimeError`) would still pass the test.
Consequence: Exception type change silently passes.
Fix: Use `pytest.raises(ValueError, match="cannot merge spans from different sources")` in both tests.

test-7
File: tests/test_span.py (no specific line)
Missing coverage: `Span(-1, -1).len() == 0` — the `UnknownSpan` / negative-index case for `len()`. Listed as design test plan item 17. Present in `test_rust_span.py::TestLen::test_len_unknown`. In `test_span.py` there is `test_len_unknown` which asserts `Span(-1, -1).len() == 0`. On re-reading, this test exists. Disregard.

test-8
File: tests/test_span_protocol.py::TestBackendSelector::test_span_from_selector_satisfies_protocol
Quality: Constructs `_span_selector.Span(1, 5)` and asserts `isinstance(s, SpanProtocol)`. This is a structural isinstance check — same limitation as test-5. However, there is no call to any method on the resulting span, so this test verifies only that the selector's `Span` class has the right method names. A selector that returned a class with stub methods returning `None` would pass.
Consequence: No method behavior is tested through the selector. Behavioral correctness is covered by `test_span.py` and `test_rust_span.py`, so this is acceptable as a narrowly-scoped integration smoke test. Low severity; no fix required.

test-9
File: tests/test_rust_span.py::TestSourceTextOpaque::test_construction
Quality: `assert src is not None` after `src = SourceText("hello")`. This is vacuous — a non-raising constructor always produces a non-None result in Python. The test name says "construction" but asserts nothing about the object.
Consequence: A broken `SourceText` that returns a truthy sentinel object would pass. The test provides no regression protection.
Fix: Replace with a meaningful assertion: verify `src` is an instance of `SourceText`, or verify it can be passed to `Span.with_source` and produce a working span. The latter also collapses with existing tests so the simplest fix is `assert isinstance(src, SourceText)`.

test-10
File: tests/test_span.py (no specific line)
Missing coverage: `intersect()` with adjacent spans (`Span(1, 5).intersect(Span(5, 8)) is None`) — design edge case for zero-overlap at the boundary. Covered in `test_rust_span.py::TestIntersect::test_intersect_adjacent_returns_none`, absent from `test_span.py`.
Consequence: A pure-Python `intersect()` bug where `s >= e` check is off-by-one (e.g., `s > e`) would produce `Span(5, 5)` instead of `None` for adjacent spans and go undetected.
Fix: Add `assert Span(1, 5).intersect(Span(5, 8)) is None` to `test_span.py`.
