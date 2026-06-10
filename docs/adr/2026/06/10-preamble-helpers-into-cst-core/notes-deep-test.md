# Test review: preamble-helpers-into-cst-core

Commit reviewed: 5e29293

---

## test-1

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs` (entire file) / `crates/fltk-cst-core/src/lib.rs`

**What's wrong — missing coverage:** No Rust unit tests exist for `extract_span`, `get_span_type`, or `get_source_text_type` in `cross_cdylib.rs`. The design doc acknowledges this ("they require a live Python runtime with `fltk._native` importable"), but the indirect coverage is weaker than it appears. The fixture-crate tests (`test_phase4_rust_fixture.py`) exercise `extract_span` only via the `set_span` setter with a valid, same-module `Span` object. That means only the **fast path** of `extract_span` (`obj.extract::<Span>()` succeeds) is exercised. The **slow path** — cross-cdylib isinstance check + `downcast_unchecked` — is not covered by any in-tree test. That path contains `unsafe` code.

**Consequence:** A regression in the slow-path logic (wrong isinstance check, wrong borrow, wrong type object lookup) would not be caught by CI. The `unsafe` block in particular makes correctness failures potentially silently wrong (memory confusion) rather than a panic, so the gap is not just a missing assertion — it's unverified safety-critical code.

**Fix:** Add a test in `test_phase4_rust_fixture.py` (or a dedicated `test_cross_cdylib.py`) that sets a node's span to a `fltk._native.Span` object obtained from a *different* generated module (i.e., from the `fltk._native` module itself, not from the fixture crate's local registration). This triggers the slow path. Assert the span round-trips correctly. If a two-crate test fixture is impractical, at minimum document the gap and add a negative-path test: pass a non-Span Python object (e.g., an integer or string) to `set_span` and assert `TypeError` is raised with the expected message "expected fltk._native.Span, got ...". The negative path is trivially exercisable with the existing fixture.

---

## test-2

**File:** `tests/test_gsm2tree_rs.py:503-514` (`TestPreamble.test_helpers_not_emitted`)

**What's wrong — quality:** The test asserts that the helpers are absent from generated source using negative substring checks (`assert "fn extract_span" not in poc_source`). This is correct intent, but the check for `py.import("fltk._native")` being absent (`import_count == 0`) is over-specific: it is an implementation detail of the *current* helper bodies, not an independent contract. If a future generator legitimately emits `py.import("fltk._native")` for some other purpose unrelated to these helpers, this test becomes a false failure. More importantly, the test gives no signal about *whether the helpers are being consumed* — it only verifies they are not emitted. An accidental reversion that re-emits the helper bodies would need the existing negative assertions to catch it, but a generator that emits neither the helpers nor the `use` import of them would also pass all these negative tests while being broken.

**Consequence:** Possible false failures on future intentional `fltk._native` imports in generated code. The test does not independently verify that the functions are actually reachable in generated code (the `use` import check in `test_required_use_declarations` covers that, so the gap is limited but real).

**Fix:** Split the `py.import("fltk._native")` count check into a separate test or comment explaining it is scoped to the preamble-helpers absence only. The negative assertion on `import_count == 0` is acceptable as a regression guard; just add a comment that the condition is "no preamble-helper imports, not 'no fltk._native usage at all'". No code change required if acceptable as-is — this is a documentation/intent clarity issue.

---

## test-3

**File:** No test file — gap in `tests/test_phase4_rust_fixture.py` or `tests/test_rust_span.py`

**What's wrong — missing coverage:** The error path of `extract_span` — when a non-Span object is passed as the span argument — has no test. `extract_span` raises `PyTypeError` with a specific message ("expected fltk._native.Span, got \<typename\>") when both the fast path and slow path fail. This is new library code with an explicit user-visible error message. No test verifies it is raised at all, let alone with the correct message.

**Consequence:** A bug that silently accepts wrong-typed arguments (or raises the wrong exception type) for `set_span` would not be caught. Downstream consumer code relying on the `TypeError` for input validation has no test backstop.

**Fix:** In `test_phase4_rust_fixture.py` (existing `TestApiContract` class or a new class), add:

```python
def test_set_span_wrong_type_raises_typeerror(self):
    Entry = _rust_pr.cst_module.Entry
    node = Entry()
    with pytest.raises(TypeError):
        node.span = 42  # integer, not a Span
```

Optionally assert the error message contains "expected fltk._native.Span".
