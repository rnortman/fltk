# Judge verdict — deep review

Phase: deep. Base 1f75363fd198f3264aa9ade30a9455d0cabc521d..HEAD a3c5231b780841df793287911704a2b523f893c8. Round 1.
Notes: 7 reviewer files. Six reported no findings (error-handling, correctness, security, reuse, quality, efficiency); the test review raised 3 findings (test-1, test-2, test-3), all dispositioned Fixed.
Spec: expose `.start`/`.end` on the Span protocol; remove stale byte-vs-codepoint rationale; both backends conform.

## Added TODOs walk

No TODOs added in this diff (verified against `git diff` — only two `@property` stubs and 4 tests added; the one pre-existing TODO touched in context is `TODO(py-span-linecol-cache)` at `terminalsrc.py:133`, unchanged by this diff). Section omitted per process.

## Other findings walk

### test-1 — Fixed
Claim (notes-deep-test): `hasattr(SpanProtocol, "start")` (test_span_protocol_includes_start_end) only checks the attribute name exists on the Protocol class object; it does not verify `SpanProtocol` works as a runtime-checkable structural gate. A non-conforming object (lacking start/end) being rejected by `isinstance` is untested.
Consequence stated: if `SpanProtocol` is redefined to drop start/end as structural requirements but keeps them as class attributes some other way, the hasattr check passes while isinstance enforcement silently breaks — regression uncaught.
Severity: should-fix (a real test-coverage gap on the central invariant this iteration introduces; not a blocker since positive isinstance tests already exist).
Disposition: Fixed — added `test_object_missing_start_end_is_not_protocol`, a class exposing only `text()`, asserting `not isinstance(_NoStartEnd(), SpanProtocol)`.
Evidence: diff at `tests/test_span_protocol.py` adds the negative test inside `TestProtocolHasStartEnd`; the prior `hasattr` check retained. The added test is exactly the structural-exclusion pattern the finding's Fix prescribed. Verified passing (`test_object_missing_start_end_is_not_protocol PASSED`).
Assessment: fix addresses the consequence — a structural drop of start/end would now flip this negative test. Accept.

### test-2 — Fixed
Claim (notes-deep-test): `test_start_end_are_codepoint_indices_cross_backend` uses span (0,4) over "café"; start=0 does not discriminate byte- from codepoint-indexing at an interior multibyte position. Reviewer's proposed mechanism: a byte-indexed backend would return `start==4` for a span started at `é`.
Consequence stated: the codepoint-not-byte invariant is not exercised for an interior multibyte position; a byte-indexed Rust regression would slip through.
Severity: should-fix (the spec's central semantic claim deserves a discriminating test; the existing (0,4) test is non-discriminating for an interior position).
Disposition: Fixed — added `test_start_end_codepoint_indices_interior_multibyte` using Span(3,4) over "café", asserting `text() == "é"` on both backends.
Evidence + reviewer-mechanism correction (verified against ground truth):
- Rust `new_with_source` (`span.rs:354-360`) stores `start`/`end` verbatim into the struct; `get_start`/`get_end` (`span.rs:~745`) return those raw fields. No unit translation. So `.start` echoes the constructor arg 3 on both backends regardless of byte-vs-codepoint — the reviewer's "byte-indexed backend would return start==4" is wrong, exactly as the responder states.
- The real discriminator is `text()`: Rust `text()` (`span.rs:421-458`) walks `char_indices()` to translate codepoint→byte offsets. A byte-indexed misread of (3,4) would slice the wrong region; a codepoint-indexed read yields "é". Crate doc (`span.rs:277-282`) defines start/end as codepoint indices.
- The added test asserts `py.text() == rs.text() == "é"`, the correct discriminator, and the test comment records the correction. Verified passing.
Responder accepted the finding's intent (interior multibyte coverage) while correcting its faulty mechanism and fixing via the right assertion. Rationale is source-backed and correct.
Assessment: fix closes the real gap with the correct discriminator. The reviewer's stated mechanism was inaccurate; the responder's correction is right and the fix still addresses the underlying coverage concern. Accept.

### test-3 — Fixed
Claim (notes-deep-test): `test_py_span_exposes_start_end_via_protocol` is Python-only; `_span_selector.Span` (the selector module downstream consumers use) is never tested for `.start`/`.end` values via the protocol — only an isinstance check (`test_span_from_selector_satisfies_protocol`) existed.
Consequence stated: if the selector re-export were broken in a way that stripped start/end (proxy/wrapper), it would not be caught; the actual downstream access pattern (annotate `SpanProtocol`, read `.start` on a selector-produced span) is untested.
Severity: nit-to-should-fix (selector resolves to one of two already-covered backends, so the marginal risk is low; the finding itself concedes "unlikely but possible"). Still a reasonable coverage add.
Disposition: Fixed — added `test_selector_span_exposes_start_end` in `TestBackendSelector`: `_span_selector.Span(1, 5)`, asserts isinstance + `start == 1`, `end == 5`.
Evidence: diff matches the finding's prescribed Fix verbatim (selector module path, isinstance + value asserts). Verified passing.
Assessment: fix exercises the named downstream path. Accept.

## Disputed items

None. All three Fixed dispositions verified against ground truth (diff + Rust/Python span source + test run). The six no-finding reviews are consistent with the diff being a pure protocol-surface + docstring + test change (no runtime behavior, no trust boundary, no new error paths, no reinvented accessors). The reuse note's pre-existing `gsm2parser.py:541,749` workaround observation is explicitly out-of-scope (not produced by this diff) and was not dispositioned — correctly so.

Spec conformance confirmed: `.start`/`.end` added as `@property` to `SpanProtocol`; stale "byte indices in Rust" rationale removed from the class docstring and the `len()` docstring; both backends conform (45/45 tests pass with Rust extension present).

## Approved

3 findings: 3 Fixed verified. (Six reviews reported no findings — not re-walked beyond consistency check above.)

---

## Verdict: APPROVED

All three Fixed dispositions verified at the named lines against ground truth; tests pass on both backends. The responder's correction of test-2's faulty reviewer mechanism is source-accurate and the fix still closes the real coverage gap.
