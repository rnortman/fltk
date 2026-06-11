Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: 807d56a → Phase 0 findings below the first separator.
Commit reviewed: 47c28fd → Phase 1 findings below the second separator.
Scope: Phase 1 (handle/data split + Shared<T> ownership; child identity; _native collision removal).
Phases 2–4 deferred — missing Phase 2–4 work is not a finding.

---

## test-1 (Phase 0)

**File:** `tests/test_rust_span.py:549–557` (`TestSpanToPyobjectCaching.test_source_text_abi_layout_mismatch_raises`)

**What's wrong:** This test sets a correct `_fltk_cst_core_abi` string and a wrong `_fltk_cst_core_abi_layout = 999999`, then calls `Span._with_source_unchecked(0, 5, FakeSource())` expecting `TypeError` matching `"layout mismatch"`. However, `extract_source_text` only reaches the layout check after the ABI string matches (`s == FLTK_CST_CORE_ABI`). The `FakeSource` class does not set `_fltk_cst_core_abi`, so `obj_type.getattr("_fltk_cst_core_abi")` raises `AttributeError` and the function falls through to the final generic `"expected fltk._native.SourceText, got ..."` error — never reaching the layout comparison. The assertion `pytest.raises(TypeError, match="layout mismatch")` therefore asserts behavior that the production code cannot reach on that input; if the code were broken in the layout-check branch, this test would still pass.

**Consequence:** The SourceText layout-mismatch error path (`cross_cdylib.rs:83–89`) is entirely uncovered. A bug introduced there (wrong comparison direction, wrong error message, skipped branch) would not be caught.

**Fix:** Add `_fltk_cst_core_abi = SourceText._fltk_cst_core_abi` to `FakeSource` so the ABI string check passes and execution reaches the layout comparison. Alternatively, dedicate a separate test that covers the non-int `_fltk_cst_core_abi_layout` error path on `SourceText` (`cross_cdylib.rs:72–82`), mirroring `test_with_source_unchecked_non_str_marker_raises_type_error` for the layout attr. The existing test for the non-int layout type error (`cross_cdylib.rs:78–82`: `"_fltk_cst_core_abi_layout attribute is {attr_type}, not int"`) has no coverage at all for `SourceText`.

---

## test-2 (Phase 0)

**File:** `tests/test_rust_span.py:549–557` and production `cross_cdylib.rs:57–116`

**What's wrong:** The new `extract_source_text` slow path has two new error branches with no tests: (a) the non-int `_fltk_cst_core_abi_layout` type error (`cross_cdylib.rs:72–82`, message `"_fltk_cst_core_abi_layout attribute is {attr_type}, not int"`), and (b) a successful slow-path extraction after both checks pass — i.e., a foreign-cdylib `SourceText` object that presents correct `_fltk_cst_core_abi` and `_fltk_cst_core_abi_layout` and succeeds. The existing `test_with_source_unchecked_foreign_cdylib_works` exercises the success case only indirectly through `phase4_roundtrip_cst` (which may be skipped). Separately, the Span-gate tests have a `test_with_source_unchecked_non_str_marker_raises_type_error` (for the `_fltk_cst_core_abi` non-str case on SourceText, `cross_cdylib.rs:102–111`) but no analog tests for the `_fltk_cst_core_abi_layout` non-int case or the version-string mismatch on the new SourceText slow-path restructuring.

**Consequence:** The SourceText path received the same structural changes as the Span path but got no new error-path tests. A regression in the layout-check branch for `SourceText` produces no test signal.

**Fix:** Add three targeted in-process tests for `extract_source_text` via `Span._with_source_unchecked`:

1. `_fltk_cst_core_abi` present + correct, `_fltk_cst_core_abi_layout` is a non-int (e.g. `"not-an-int"`) → `TypeError` matching `"_fltk_cst_core_abi_layout attribute is"`.
2. `_fltk_cst_core_abi` present + correct, `_fltk_cst_core_abi_layout` = correct value → succeeds (mirrors the Span gate success case; skippable via `phase4_roundtrip_cst` if a real foreign SourceText is needed, but an in-process fake with both attrs correct is sufficient and avoids the skip).
3. `_fltk_cst_core_abi` present + correct, `_fltk_cst_core_abi_layout` wrong int (the test-1 fix, restated).

---

## test-3 (Phase 0)

**File:** `tests/test_rust_span.py:630–650` (`TestSpanToPyobjectCaching`)

**What's wrong:** `test_repeated_span_reads_are_correct` exercises the `IS_CANONICAL_CDYLIB == true` (fast) path because `Grammar` lives in `fltk._native` (same cdylib). `test_repeated_span_reads_from_consumer_cdylib` exercises the cached slow path for a sourceless span (`phase4.Span(3, 7)` → `None` branch of `span_to_pyobject`, `cross_cdylib.rs:174–180`). There is no caching smoke test for the **source-bearing** slow path: `WITH_SOURCE_UNCHECKED_METHOD` is only populated when `source_as_py` returns `Some(...)`, and that branch (`cross_cdylib.rs:163–173`) has no multi-call correctness assertion in the consumer cdylib context.

**Consequence:** If `WITH_SOURCE_UNCHECKED_METHOD.get_or_try_init` cached a stale or wrong method object, repeated source-bearing span reads from a consumer cdylib would silently return wrong spans on calls 2+. The caching correctness for the `Some` arm is unverified.

**Fix:** Add a test that reads a source-bearing span from the consumer cdylib fixture multiple times and asserts both the span coordinates and `has_source()` on each result. Skippable via `pytest.importorskip("phase4_roundtrip_cst")`.

---

## test-4 (Phase 0)

**File:** `tests/test_rust_span.py:458–525` (`TestSpanPathAbiGate`)

**What's wrong:** All three subprocess tests patch `native.Span = FakeSpan` — replacing the `fltk._native.Span` attribute — and rely on `phase4_roundtrip_cst` importing `fltk._native` to reach `get_span_type`. The patching mechanism works only if `phase4_roundtrip_cst` calls `get_span_type` (i.e. reads a node span) *after* the patch is applied and before any other `get_span_type` call in the same process. The subprocess scripts import `phase4_roundtrip_cst` after the patch, but they do not verify that `fltk._native` is not imported by `phase4_roundtrip_cst` itself at import time (a module-level `from fltk._native import Span` in the fixture would cache the real class before the patch). This is a latent fragility: if the fixture's import behavior changes, the test silently becomes a no-op (the gate never fires, `result.returncode == 0` because the subprocess succeeds without triggering the error, and `"OK"` is absent from stdout, making `assert "OK" in result.stdout` the actual guard). The guard is present and would catch this, but the failure message would be opaque.

**Consequence:** Fragile test that could silently transition from "gate fires" to "gate never fires" if the fixture import order changes, with an opaque failure message. Not a false-pass risk (the `"OK"` assertion guards it), but a fragile-breakage risk.

**Fix:** In the subprocess scripts, add a check after the patch: `assert type(native.Span).__name__ == "FakeSpan"` (or equivalent) to confirm the patch is in effect before driving the crossing. This makes the subprocess script self-diagnosing. Minor, but recommended given the scripts already have inline assert logic.

---

## test-5 (Phase 0)

**File:** `tests/test_rust_span.py:560–592` (`TestSpanPathAbiGate.test_abi_string_mismatch_raises_type_error`)

**What's wrong:** The subprocess script patches `native.Span = FakeSpan` where `FakeSpan._fltk_cst_core_abi_layout` is set to the *correct* layout (`native.Span._fltk_cst_core_abi_layout`). This means the test only verifies the ABI *string* check fires when the string is wrong — it does not test that the string check fires *before* the layout check (i.e. that the string check is not accidentally skipped). This is fine for what it tests, but the assertion `"fltk-cst-core/" in msg` (line 587) asserts a substring of the *expected* ABI string. The production error message at `cross_cdylib.rs:257–261` is: `"Span ABI mismatch: fltk._native.Span reports {s:?}, this module expects {FLTK_CST_CORE_ABI:?} ..."`. The assertion `"fltk-cst-core/" in msg` would pass even if the reported and expected strings were swapped in the message. Both substrings (`"wrong/0.0.0"` and `"fltk-cst-core/"`) are checked; this is acceptable. No finding on the assertion strength.

**The actual finding:** the test does not assert that `expected_layout` (the value this module expects) appears in the error message on a *layout* mismatch (test_layout_mismatch_raises_type_error, line 519–521). `test_layout_mismatch_raises_type_error` only checks `"999999"` (the reported value) and `"layout mismatch"` case-insensitively, but not that the expected layout value is also present. The production error message (`cross_cdylib.rs:280–284`) is: `"Span ABI layout mismatch: fltk._native.Span reports layout {reported_layout}, this module expects {expected_layout} ..."` — it includes both values. A bug that omitted `expected_layout` from the message would not be caught. This is a weak assertion.

**Consequence:** A regression that drops the expected-layout value from the error message passes the test, leaving users with a less diagnostic error.

**Fix:** Add `assert str(Span._fltk_cst_core_abi_layout) in msg` to the subprocess script's assertion block in `test_layout_mismatch_raises_type_error`.

---

No findings on the `gsm2tree_rs.py` docstring addition (purely a comment) or the TODO.md entry swap (`crosscdylib-abi-sentinel` removed, `rust-cst-children-list-view` added). Both are correct and non-testable.

---

## test-6 (Phase 1)

**File:** `tests/test_gsm2tree_rs.py` — `TestNodeStructure` / `TestCfgFeatureGate`

**What's wrong:** No test asserts that the generator emits the `PyX` handle struct body. `test_identifier_struct_present` checks `pub struct Identifier {` (data struct), and `test_node_struct_pyclass_gated` checks `#[pyclass(frozen, weakref, name = "Identifier")]` and `module.add_class::<PyIdentifier>()` — but nothing asserts that the generator emits `pub struct PyIdentifier { pub inner: Shared<Identifier>, }`. The emitted handle struct is the core Phase 1 artifact; its shape is tested only transitively through compile success.

**Consequence:** A generator regression that emits the handle with wrong field name/type (e.g. `data: Arc<Identifier>`) would pass all string-match tests but produce broken output.

**Fix:** Add a test asserting `"pub struct PyIdentifier {\n    pub inner: Shared<Identifier>,"` is present in `poc_source` (and analogously for Items/Trivia).

---

## test-7 (Phase 1)

**File:** `tests/test_gsm2tree_rs.py` — `TestNodeStructure` / `TestCfgFeatureGate`

**What's wrong:** No test asserts that `to_py_canonical` is emitted by the generator, nor that it calls `registry::get_or_insert_with`. This function is the wrap-out entry point; calling `Py::new` directly inside it (the Phase 0 bug) would break is-stable identity without failing any current generator string-match test.

**Consequence:** A generator that emits `to_py_canonical` but calls `Py::new` directly would break identity but pass all current generator tests. Only runtime identity tests would catch it, and only indirectly.

**Fix:** Add a test asserting `"pub fn to_py_canonical("` and `"registry::get_or_insert_with("` appear in `poc_source`.

---

## test-8 (Phase 1)

**File:** `tests/test_gsm2tree_rs.py` — `TestNodeStructure` / `TestCfgFeatureGate`

**What's wrong:** No test asserts that `registry::force_register` is called inside the `#[new]` constructor. The `py_new` path is what gives newly-constructed Python nodes their canonical registration; without it, `n = Node(); node.append(n); accessor() is n` can fail on the first read if hand-in (via `register_if_absent`) does not cover the case where `py_new` never registered the handle.

**Consequence:** A generator that omits `force_register` in `#[new]` would allow the invariant to hold only in the hand-in direction; `n = Node(); read_without_any_append() is n` would fail, but tests that go through `append` first might still pass.

**Fix:** Assert `"registry::force_register("` appears in `poc_source`.

---

## test-9 (Phase 1)

**File:** `tests/test_phase4_rust_fixture.py` — `TestPhase1IdentityAndMutation`

**What's wrong:** No test covers the `children_<label>()` accessor path for identity. All existing identity tests use `children[0][1]` (the generic snapshot path) or `child_<label>()`. The `children_<label>()` method also calls `get_or_insert_with` through `to_pyobject`, but is not exercised for is-stability. A `children_<label>` accessor that missed the `get_or_insert_with` call would not be caught by any existing test.

**Consequence:** A generated `children_entry` that calls `Py::new` directly (instead of `get_or_insert_with`) would break identity on that accessor path, undetected.

**Fix:** Add a test: `node.append_entry(entry); assert node.children_entry()[0] is entry` using a node type with a node-typed label child (e.g. `Config`/`Entry`).

---

## test-10 (Phase 1)

**File:** `crates/fltk-cst-core/src/registry.rs` — no unit tests

**What's wrong:** `registry.rs` is a new module with four public functions. None has a Rust unit test. The `snapshot` helper is `#[cfg(test)]` but is never called from any `#[test]` in this module. ABA-safety, `register_if_absent` boolean semantics, and `get_or_insert_with` miss→register→return are verified only indirectly through Python integration tests.

**Consequence:** A logic inversion in `register_if_absent` (returning `!result.is(handle)`) would require Python-level identity tests to detect; the failure point would be opaque.

**Fix:** Add `#[cfg(test)]` unit tests in `registry.rs` covering: `lookup` on missing key → `None`; `force_register` then `lookup` → same object; `register_if_absent` absent → `true`; `register_if_absent` present → `false` and existing object unchanged; `get_or_insert_with` hit → `make_handle` not called; `get_or_insert_with` miss → `make_handle` called once and result registered.

---

## test-11 (Phase 1)

**File:** `tests/test_phase4_rust_fixture.py` — `TestPhase1IdentityAndMutation.test_extend_children_duplicates_entries`

**What's wrong:** The test asserts `first is second` (the two entries from the self-extended node alias the same `Shared`) but does not assert `first is ident`. If the registry evicted the `ident` handle between construction and the extend (possible in principle), two new handles could be created that are `is`-equal to each other but not to the original `ident`. The test would pass while silently failing to verify that the original handle survives.

**Consequence:** A registry bug that evicts handles prematurely (e.g. a WeakValueDictionary key error) would produce two mutually-`is`-equal new handles but not equal to `ident`; the test passes.

**Fix:** Add `assert first is ident` after the `first is second` assertion in `test_extend_children_duplicates_entries`.

---

## test-12 (Phase 1)

**File:** `tests/test_phase4_rust_fixture.py` — `TestPhase1IdentityAndMutation`

**What's wrong:** No Python-level test covers the shared-ownership-across-two-parents scenario: one child appended to two separate parents, mutation visible through both parent accessors. The Rust unit tests cover this (`shared_child_in_two_parents_is_ptr_eq`, `mutation_propagates_through_shared_child`), but the Python surface is untested. A bug in `extract_from_pyobject` that deep-copies instead of Arc-clones would pass all current Python tests (all tests append to one parent only).

**Consequence:** The Arc-clone semantics of hand-in are unverified at the Python level. A deep-copy regression would be caught only by Rust unit tests, not by any Python test.

**Fix:** Add a Python test: create `ident`, `append_key(ident)` to `entry_a` and `entry_b`, mutate `ident.span`, assert both `entry_a.child_key().span == new_span` and `entry_b.child_key().span == new_span`.

---

## test-13 (Phase 2)

**File:** `crates/fltk-cst-spike/src/spike_tests.rs`, `tests/rust_cst_fixture/src/native_tests.rs`

**What's wrong:** `CstError::UnexpectedChildType` is never returned by an actual accessor call in any test. Both test files construct the variant manually only for `Display` testing. The design plan (§6 item 1) explicitly requires: "UnexpectedChildType via generic `push_child` storing an off-type variant under a single-typed label." The reachable path requires a multi-variant child enum with a single-typed label accessor — e.g. `child_item()` on `Items` (spike) when exactly one `ItemsChild::Span(...)` is stored under `ItemsLabel::Item`, or `child_op()` / `maybe_op()` on `Operator` in the fixture grammar.

**Consequence:** The `UnexpectedChildType` arm in every generated `child_<lbl>` / `maybe_<lbl>` accessor is dead from a test coverage perspective. A regression that removes or inverts that branch (returning `Ok` instead of `Err` for a wrong-type child when count is 1) would pass all tests.

**Fix:** In `spike_tests.rs`, add a test that calls `items.push_child(Some(ItemsLabel::Item), ItemsChild::Span(...))` (storing a `Span` variant under the node-typed `item` label) and asserts `items.child_item()` returns `Err(CstError::UnexpectedChildType { label: "item" })`. Mirror in `native_tests.rs` using `Operator`/`Entry` with a node-typed label.

---

## test-14 (Phase 2)

**File:** `crates/fltk-cst-spike/src/spike_tests.rs`, `tests/rust_cst_fixture/src/native_tests.rs`

**What's wrong:** `children_<lbl>` (single-typed label) is documented to "skip off-type variants stored under the label" (design §4.3 item 2), implemented as `filter_map` in the generated accessor (e.g. `cst.rs:877–880`). No test stores an off-type variant under a multi-variant label and asserts the iterator skips it. Existing tests only exercise the happy path where all stored variants have the expected type. The companion invariant ("lossless view via `children()`") is also untested.

**Consequence:** A regression changing `filter_map` to `map` (panic on wrong-type variant) or dropping the filter entirely (yielding wrong-type items) passes all tests.

**Fix:** Add a test that pushes one `ItemsChild::Identifier(...)` and one `ItemsChild::Span(...)` under `ItemsLabel::Item`, then asserts `items.children_item().count() == 1` (skip behavior) while `items.children().len() == 2` (lossless via untyped accessor). Mirror in `native_tests.rs`.

---

## test-15 (Phase 2)

**File:** `crates/fltk-cst-spike/src/spike_tests.rs`

**What's wrong:** The spike tests cover `children_name` / `child_name` / `maybe_name` for the `Identifier` grammar rule (span-typed label), but have no tests for `child_item()`, `maybe_item()`, or `children_item()` as named accessor calls on `Items` (node-typed, multi-variant child enum label). The §6 item 1 plan explicitly says spike tests should mirror `native_tests.rs`; `native_tests.rs` has `child_lbl_exactly_one_ok`, `child_lbl_zero_returns_child_count_error`, `child_lbl_two_returns_child_count_error`, and `maybe_lbl_*` variants. The benchmark (`traverse.rs`) uses `children_item()` but that is not a test.

**Consequence:** If the generator produces incorrect accessor code for `ItemsLabel::Item` (the node-typed label case), the spike test suite would not catch it. Low severity given `native_tests.rs` covers the same code pattern on a different grammar, but spike coverage is an explicit design goal.

**Fix:** Add `child_item_exactly_one_ok`, `child_item_zero_returns_child_count_error`, and `maybe_item_two_returns_child_count_error` tests to `spike_tests.rs`, mirroring the `child_lbl_*` and `maybe_lbl_*` tests already present for `children_name`.

---

## test-16 (Phase 2)

**File:** `crates/fltk-cst-spike/src/spike_tests.rs`

**What's wrong:** `maybe_lbl` is tested in spike_tests only for the zero-child (`None`) and one-child (`Some`) happy paths. The two-child error path (`Err(CstError::ChildCount { expected: "0 or 1", found: 2 })`) exists in `native_tests.rs` (line 415–423) but not in `spike_tests.rs`.

**Consequence:** The expected-quantity string `"0 or 1"` in `maybe_<lbl>` error messages is not pinned by spike tests. A generator that emits `"1"` instead of `"0 or 1"` for `maybe_<lbl>` would pass spike tests while failing `native_tests.rs`. The specific string also appears in `ChildCount::expected` which affects user-visible error messages.

**Fix:** Add `maybe_lbl_two_returns_child_count_error` to `spike_tests.rs` matching the pattern in `native_tests.rs` (push two children under the same label, assert `Err(CstError::ChildCount { label: "name", expected: "0 or 1", found: 2 })`).

