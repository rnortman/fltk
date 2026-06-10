# Test Review Notes — span-source-as-py-crosscdylib

Commit reviewed: 588d55f

---

## test-1

**File:line** `tests/test_rust_span.py:TestAbiMarkerClassattr` (entire class, ~80 lines)

**What's wrong** The fast path of `span_to_pyobject` — the branch taken when `Span::type_object(py).is(&span_type)` (same cdylib) — is not directly exercised by any test. `TestArcSharingNodeSpan` in `test_fegen_rust_cst.py` comes closest: it constructs `Grammar` nodes (from `fltk._native.fegen_cst`, which IS `fltk._native`) and reads `.span`, going through the fast path of `span_to_pyobject`. However, `TestAbiMarkerClassattr.test_with_source_unchecked_canonical_source_text` (lines 255–259) calls `Span._with_source_unchecked` directly — that exercises `extract_source_text` fast path but not `span_to_pyobject` at all. No test name or docstring names the `span_to_pyobject` fast path as its observable target. If the fast-path branch were replaced by always taking the slow path (e.g. a refactor removing the `type_object.is` check), every existing test would still pass because the slow path also produces a correctly source-bearing span — the O(1) vs. O(N) difference is not observable through correctness tests, and Arc identity on the fast path would only matter under the fegen nodes path (`TestArcSharingNodeSpan`), which already passes with the old code too (since `fltk._native.fegen_cst` IS `fltk._native`).

**Consequence** The fast-path optimisation (`Span::type_object(py).is(&span_type)`) has no dedicated correctness gate. A future refactor that silently removes or mis-routes the fast path (e.g. always going through `_with_source_unchecked`) would not be caught. The O(1) property is unverified by tests — it's performance, not correctness — but the fast-path-specific Arc-identity guarantee (that `Py::new` with the local type rather than through a `call_method1` round-trip produces the exact same `Arc` clone) is also unverified.

**Fix** Add a test in `TestAbiMarkerClassattr` (or a new class) that uses a node from `fltk._native.fegen_cst` (same cdylib as `fltk._native`): construct `Grammar(span=Span.with_source(0, 5, src))`, read `.span` twice, and assert both `has_source()` and `s1.merge(s2)` succeeds. Name it explicitly as the same-cdylib fast-path case. This is distinct from `TestArcSharingNodeSpan.test_node_span_read_twice_merges` only in the name/docstring focus — but the existing test in `test_fegen_rust_cst.py` already covers this behavior; the gap is in `test_rust_span.py`'s class which is focused on `_with_source_unchecked` and has no same-cdylib `span_to_pyobject` case at all.

---

## test-2

**File:line** `tests/test_rust_span.py:TestAbiMarkerClassattr.test_with_source_keeps_exact_behavior` (lines 285–294)

**What's wrong** The test imports `phase4_roundtrip_cst` and calls `phase4.SourceText(...)`, then checks that `Span.with_source(0, 5, foreign_st)` raises `TypeError`. However, the assertion only calls `pytest.raises(TypeError)` with no `match` argument. It also contains a misleading comment "This test uses phase4_roundtrip_cst if available; otherwise skips" followed by `pytest.importorskip` — so the test will be skipped when the fixture is not built. More substantively: the assertion only checks that *some* `TypeError` is raised; it does not verify the error mentions "SourceText" or that it is specifically the pyo3 registry check (not some other failure mode in `with_source`). The test is fragile: any `TypeError` raised for any reason (e.g. wrong argument count) would pass it.

**Consequence** If `with_source` were broadened to accept foreign `SourceText` (breaking the stated invariant), no clear failure would be caught by this test alone if a `TypeError` was still raised for some other path. More likely: if the test produces no output because the fixture is not built in a routine `uv run pytest` run without `make build-test-user-ext`, the behavior this test pins goes entirely unverified.

**Fix** Add `match="SourceText"` (or similar) to `pytest.raises(TypeError, match=...)` so the error is specific. Consider adding a comment that this test requires `make build-test-user-ext` and that a CI lane where this test is skipped should be treated as a gap rather than a pass.

---

## test-3

**File:line** `tests/test_rust_span.py:TestAbiMarkerClassattr` — no test for `_fltk_cst_core_abi` marker on an instance vs. the class

**What's wrong** `SourceText._fltk_cst_core_abi` is a `#[classattr]`, so it is accessible as `SourceText._fltk_cst_core_abi` (class-level) AND typically as `instance._fltk_cst_core_abi`. `extract_source_text`'s slow path reads `obj.get_type().getattr("_fltk_cst_core_abi")` — it reads off the *type*, not the instance. The existing test `test_source_text_abi_classattr_exists` checks `hasattr(SourceText, "_fltk_cst_core_abi")` (class-level). No test verifies that the marker is accessible *via the type of an instance* (i.e., the path `obj.get_type().getattr(...)` as actually called in `extract_source_text`). These are equivalent for a non-subclassed `#[classattr]`, but the test as written only verifies the class-direct access, not the `type(instance).attr` path that the production code takes.

**Consequence** Negligible risk given that pyo3 `#[classattr]` always attaches to `ob_type`, but: the test documents the contract from the wrong angle. If `extract_source_text` were changed to read `obj.getattr(...)` (instance attribute) instead of `obj.get_type().getattr(...)`, the existing tests would still pass while the semantics shifted.

**Fix** Add `assert hasattr(type(src), "_fltk_cst_core_abi")` and `assert type(src)._fltk_cst_core_abi == SourceText._fltk_cst_core_abi` to `test_source_text_abi_classattr_exists` or a new test, explicitly exercising the `type(instance)` access path to match what `extract_source_text` does.

---

## test-4

**File:line** `tests/test_fegen_rust_cst.py:TestArcSharingNodeSpan` — sourceless span through `span_to_pyobject` not exercised

**What's wrong** `span_to_pyobject`'s sourceless arm (`None => span_type.call1((span.start(), span.end())).map(|b| b.unbind())`) is not directly tested here. `TestConstructionDefaultSpan.test_default_span_is_unknown` (line 75) constructs nodes with default `UnknownSpan` (internally `Span::unknown()`, which is sourceless), and `test_explicit_span` reads back an explicitly-set sourceless span — both exercise the same-cdylib fast path (`Py::new`) on a sourceless span. However no test reads back a sourceless span through the *slow path* (cross-cdylib, as in `phase4_roundtrip_cst` nodes). The `test_cross_cdylib_span_merge_after_accessor` in `test_phase4_rust_fixture.py` always uses a parse result, so the spans are always source-bearing. There is no test that sets a sourceless span on a cross-cdylib node and reads it back via `.span`.

**Consequence** The `None` arm of `span_to_pyobject`'s `match` (slow path, sourceless) is exercised only indirectly by `test_ac1_construction_default_span` in `test_phase4_rust_fixture.py` (which reads `node.span == UnknownSpan` after default construction — same as the base commit). If the sourceless slow-path arm were broken (e.g. calling `_with_source_unchecked` with `None` instead of falling through to `call1`), no test would catch it for the cross-cdylib case.

**Fix** Add a test in `TestAC7BothBackends` or `TestAC5ApiContract` that explicitly constructs a node with a sourceless span (either default or `Entry(span=Span(0, 5))`), reads back `.span` through the cross-cdylib accessor, and asserts `has_source() is False` and `== Span(0, 5)`. This pins the sourceless slow-path arm.

---

## test-5

**File:line** `tests/test_rust_span.py:TestAbiMarkerClassattr.test_with_source_unchecked_bogus_abi_marker_raises_type_error` (line 276–283)

**What's wrong** The test raises an object whose class sets `_fltk_cst_core_abi = "bogus/0.0.0"` and checks `pytest.raises(TypeError, match="ABI mismatch")`. This correctly exercises the version-mismatch path in `extract_source_text`. However, there is no test for the third branch: an object that has *no* `_fltk_cst_core_abi` attribute at all and is not a locally-registered `SourceText`. The design §3 specifies this falls through to `PyTypeError::new_err(format!("expected fltk._native.SourceText, got {type_name}"))`. The only test for non-SourceText objects is `test_with_source_unchecked_str_raises_type_error` (a plain `str`), which lands on the first fast-path rejection (`obj.downcast::<SourceText>()` fails) and then the getattr for `_fltk_cst_core_abi` returns `Err` (strings don't have it), so it falls through to the final `TypeError`. The error message for the string case is "expected fltk._native.SourceText, got str" but this is not asserted — only that *some* `TypeError` is raised.

**Consequence** The final branch of `extract_source_text` (no `_fltk_cst_core_abi` attribute, not locally-registered) produces a `TypeError` with the type name, but no test verifies the message content. If the error message were changed to something less informative (omitting the type name), no test would catch it.

**Fix** Add `match="fltk._native.SourceText"` (or `match="got str"`) to `pytest.raises(TypeError)` in `test_with_source_unchecked_str_raises_type_error`. Also add a test for the no-marker-attribute path explicitly: an arbitrary Python object with no `_fltk_cst_core_abi` (not just a plain string, which has fast-path-rejected typing anyway) to verify the "expected fltk._native.SourceText, got ..." message is emitted.
