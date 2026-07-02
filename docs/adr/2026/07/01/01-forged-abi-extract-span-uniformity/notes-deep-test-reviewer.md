# test-reviewer notes: forged-abi-extract-span-uniformity

Reviewed diff a330940..aa9a5f2 against design.md. Single production change
(`check_instance_layout::<Span>` added to `get_span_type`'s `PyOnceLock` init in
`crates/fltk-cst-core/src/cross_cdylib.rs`) plus doc-comment rewrites in
`cross_cdylib.rs`/`span.rs`. Test change: new `TestForgedSpanRejected` class in
`tests/test_rust_span.py`, mirroring `TestForgedSourceTextRejected` with tests (a)-(d) exactly
as specified in design §4.

## Verification performed

- Ran the new class at HEAD in the main repo venv: all 4 tests pass; full `tests/test_rust_span.py`
  (119 tests, phase4 fixture built) passes with no regressions to `TestSpanPathAbiGate`,
  `TestSpanToPyobjectCaching`, or `TestForgedSourceTextRejected`.
- Built an isolated worktree at the base commit (a330940), copied only the new test file in,
  built the Rust extension there (`maturin develop` for `fltk-native` and `fegen_rust_cst`), and
  ran `TestForgedSpanRejected` directly against the base venv's interpreter (bypassing `uv run`,
  which in this sandbox silently resolved to the main repo's already-fixed venv rather than the
  worktree's own — a harness gotcha, not a test defect). Confirmed genuine TDD red state: (a)
  `test_forged_span_via_reassignment_raises_type_error` and (b)
  `test_forged_span_metaclass_property_raises_type_error` both SIGSEGV (returncode -11) at base,
  exactly as design §4 predicts, and both pass cleanly once the base `cross_cdylib.rs`/`span.rs`
  are swapped for the HEAD versions and rebuilt in the same worktree. (c)
  `test_genuine_native_span_accepted_cross_cdylib` passes at both base and HEAD (correct — it's
  a no-false-rejection check, not a regression check). This rules out the tests being vacuous:
  they demonstrably distinguish the fixed from the unfixed code, including catching the actual
  UB (not just a coincidental exception).
- Spot-checked the pinned error-message assertions (`"__basicsize__" in msg or "not a genuine
  Span" in msg`, `"metaclass" in msg or "Meta" in msg`) against the real `check_instance_layout`
  message text in `cross_cdylib.rs` (`"{type_label} instance layout check failed: ... not a
  genuine {type_label} allocation ..."` and the metaclass-guard message) — they match, and are
  specific enough to not also match `check_abi_pair`'s messages (avoiding the false-positive risk
  the design's test plan explicitly calls out).

## Coverage assessment

- The one new production code path (the `check_instance_layout::<Span>` call and its two
  possible outcomes: reject-on-basicsize-mismatch, reject-on-custom-metaclass) is exercised by
  (a) and (b) respectively, both via subprocess isolation appropriate for a path whose regression
  mode is SIGSEGV.
- No-false-rejection on the accept branch is covered by (c) (cross-cdylib genuine Span) and
  pinned precondition-wise by (d) (`Span.__basicsize__ == Span._fltk_cst_core_abi_layout`, plus a
  foreign-cdylib check gated behind the optional `phase4_roundtrip_cst` fixture).
- Existing coverage that the change could regress (gate-ordering / pinned `check_abi_pair`
  messages in `TestSpanPathAbiGate`, `TestSpanToPyobjectCaching`, `TestForgedSourceTextRejected`)
  was left unmodified and passes unchanged — verified by running the full file.
- `span_to_pyobject` and generated `cst.rs` call sites are not given a dedicated new forged-input
  test, but this is appropriate: they don't accept untrusted Python input the way `extract_span`
  does, and the design's note about their "wider blast radius" is about the same first-call gate
  already covered by (a)/(b), not a distinct code path.

## Quality assessment

Assertions are behavioral, not vacuous: each forge test asserts the specific exception type,
the specific message content (narrow enough to distinguish the new gate from the pre-existing
`check_abi_pair` gate), and `returncode` to explicitly catch SIGSEGV recurrence rather than
treating any non-zero exit as generic failure. Test (c) asserts on the actual returned span's
`repr`. Test (d) is a precondition pin with a clear "if this breaks, the gate would reject
genuine spans" rationale, matching its `TestForgedSourceTextRejected` analog. No mocking of the
subject under test — the forgery happens via real Python class definitions patched into
`fltk._native`, and the subprocess isolation is justified (SIGSEGV would otherwise take down the
whole suite) rather than a reach for isolation's own sake. Docstrings state what's being pinned
and why, not just "test X works".

## Findings

No findings.
