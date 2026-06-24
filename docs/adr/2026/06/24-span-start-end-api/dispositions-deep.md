# Deep Review Dispositions — span-start-end-api

Round 1. Base 1f75363, reviewed HEAD 1144c7f, fixes at a3c5231.

Six review notes reported no findings (error-handling, correctness, security,
reuse, quality, efficiency). Only the test review (notes-deep-test) raised
findings; all three are dispositioned below.

---

test-1:
- Disposition: Fixed
- Action: Added `test_object_missing_start_end_is_not_protocol`
  (tests/test_span_protocol.py, in `TestProtocolHasStartEnd`). A class exposing
  only `text()` (no `start`/`end`) is asserted `not isinstance(..., SpanProtocol)`,
  pinning `start`/`end` as real structural requirements rather than mere class
  attributes that `hasattr` finds. The prior `hasattr(SpanProtocol, "start")`
  check is retained.
- Severity assessment: Low. The existing positive isinstance tests already
  proved both backends conform; the gap was a missing negative (structural
  exclusion) test, so an accidental drop of `start`/`end` from the structural
  requirement set could go uncaught. The new test closes that.

test-2:
- Disposition: Fixed
- Action: Added `test_start_end_codepoint_indices_interior_multibyte`
  (tests/test_span_protocol.py, in `TestProtocolHasStartEnd`). Uses `Span(3, 4)`
  over "café" — 'é' is codepoint index 3 but byte offset 4 — and asserts
  `text() == "é"` on both backends. This exercises codepoint-vs-byte slicing at
  an interior multibyte position, which the original (0,4) span did not.
- Severity assessment: Low-to-moderate. The original cross-backend test agreed
  on boundary values but its start=0 did not discriminate byte- from
  codepoint-indexing for an interior position; a byte-indexed regression at a
  multibyte offset could slip through. Note: the reviewer's stated mechanism
  ("a byte-indexed backend would return start==4") is inaccurate — `with_source`
  echoes the constructor `start`/`end` verbatim and does not translate units, so
  `.start` is always 3 here. The real discriminator is `text()`, which is what
  the added test asserts; the test comment records this correction.

test-3:
- Disposition: Fixed
- Action: Added `test_selector_span_exposes_start_end`
  (tests/test_span_protocol.py, in `TestBackendSelector`). Constructs
  `_span_selector.Span(1, 5)`, asserts `isinstance(..., SpanProtocol)` and
  `start == 1`, `end == 5`, directly exercising the selector-module path real
  downstream consumers use.
- Severity assessment: Low. Backend-specific classes were already covered for
  `start`/`end`, and `test_span_from_selector_satisfies_protocol` covered the
  selector isinstance check; the gap was asserting `.start`/`.end` values on a
  selector-produced span. The new test covers the actual downstream access
  pattern.

---

Test count: 42 → 45 (all pass with the Rust extension present). `make check`
(check + cargo-deny) passed at commit time.
