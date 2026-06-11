Style: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Commit reviewed: 807d56a (base: 63e6b76). Scope: Phase 0 only (ABI sentinel hardening, Span/SourceText).

---

## errhandling-1

**File:line**: `crates/fltk-cst-core/src/cross_cdylib.rs:245`

**Broken path**: `get_span_type` — `span_type.getattr(pyo3::intern!(py, "_fltk_cst_core_abi"))?`

**Why**: A missing `_fltk_cst_core_abi` attribute on `fltk._native.Span` propagates a raw `PyAttributeError` via `?` with no wrapping. The code comment says "A missing or non-string attr means the canonical Span was built without the marker — treat it as a mismatch", but the code does not do that: `?` on a missing attr escapes as `AttributeError: type object 'Span' has no attribute '_fltk_cst_core_abi'`, with no mention of ABI, version skew, or `fltk-cst-core`. Only the non-string branch (line 246–255) produces a diagnostic `TypeError`; the absent-attr branch does not.

**Consequence**: Version skew where the remote `fltk._native` was built before `_fltk_cst_core_abi` was added silently surfaces as a confusing `AttributeError` instead of the intended `TypeError` naming both ABI strings. On-call sees a Python attribute error with no indication that a cdylib version mismatch is the cause. The same `GILOnceCell` will retry on the next call, so the error is not silenced, but it is mis-diagnosed every time.

**Fix**: Replace `?` with an explicit `.map_err` that converts `AttributeError` (absent attr) into a `TypeError` with the same diagnostic message as the version-skew case, e.g. `"Span ABI mismatch: fltk._native.Span has no _fltk_cst_core_abi (old build missing sentinel), this module expects {FLTK_CST_CORE_ABI:?}"`.

---

## errhandling-2

**File:line**: `crates/fltk-cst-core/src/cross_cdylib.rs:268`

**Broken path**: `get_span_type` — `span_type.getattr(pyo3::intern!(py, "_fltk_cst_core_abi_layout"))?`

**Why**: Identical issue to errhandling-1 but for the layout probe. If `_fltk_cst_core_abi_layout` is absent (ABI string matched but layout attr is missing — possible during a partial upgrade where the string sentinel was added before the layout probe), `?` propagates a raw `AttributeError` with no diagnostic context. The comment says "A missing or non-int attr is also treated as a mismatch" — the code does not honour this for the absent case.

**Consequence**: A partial-upgrade scenario (string attr present, layout attr absent) emits an opaque `AttributeError` instead of the designed `TypeError` naming the layout expectation. On-call cannot distinguish "attribute absent" from any other Python attribute error at the call site.

**Fix**: `.map_err` converting absent-attr to a `TypeError`: `"fltk._native.Span._fltk_cst_core_abi_layout missing (old build); this module expects layout {expected_layout}"`. Mirror this fix to the `_fltk_cst_core_abi` getattr on the same function for consistency.

---

## errhandling-3

**File:line**: `crates/fltk-cst-core/src/cross_cdylib.rs:71`

**Broken path**: `extract_source_text` slow path — `obj_type.getattr(pyo3::intern!(py, "_fltk_cst_core_abi_layout"))?`

**Why**: At this point the ABI string has matched (`s == FLTK_CST_CORE_ABI`), so the object is plausibly a genuine `SourceText` from a cdylib that has the string attr but not the layout attr (partial upgrade). The `?` propagates a raw `AttributeError` with no context. Every other branch in this function returns a `TypeError` with a clear diagnostic; this branch is inconsistent and informationally useless.

**Consequence**: A foreign `SourceText` whose type has `_fltk_cst_core_abi` set correctly but lacks `_fltk_cst_core_abi_layout` (partial upgrade) raises `AttributeError` instead of `TypeError`. The caller (`Span::_with_source_unchecked`) passes this up; downstream catches `TypeError` not `AttributeError`, so error-handling code may miss it. On-call sees an undifferentiated attribute error with no indication of which field was absent or why.

**Fix**: Replace `?` with `.map_err` producing a `TypeError` consistent with the other branches: `"expected fltk._native.SourceText: _fltk_cst_core_abi_layout attribute missing (old build without layout probe)"`.

---

*Phase 1 findings begin here. Commit reviewed: 47c28fd (base: 31161d9). Scope: Phase 1 — handle/data split, Shared<T> ownership, child identity, _native collision removal.*

---

## errhandling-4

**File:line**: `fltk/fegen/gsm2tree_rs.py:557` (generator template); all generated hand-in sites — representative: `src/cst_fegen.rs:223`, `src/cst_fegen.rs:232`, `src/cst_generated.rs:408`, `crates/fltk-cst-spike/src/cst.rs:408`, `crates/fltk-cst-spike/src/cst.rs:417`; ~54 sites total across `src/cst_fegen.rs`, `src/cst_generated.rs`, `crates/fltk-cst-spike/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`.

**Broken path**: Every `extract_from_pyobject` hand-in site — `let _ = registry::register_if_absent(py, addr, obj);` — silently drops a `PyResult<bool>`.

**Why**: `register_if_absent` returns `PyResult<bool>`. The `bool` is correctly ignorable: `true` means this handle was registered as canonical, `false` means a canonical already existed — either way the caller's `Shared<T>` is valid and nothing further is needed. However, the `Err` variant is also dropped via `let _ = ...`. If `register_if_absent` returns `Err` (e.g. `MemoryError` from `WeakValueDictionary.setdefault`, or any future code path in `get_registry` that can fail), the error is swallowed and the caller returns `Ok(Self::NodeType(shared))`. The registry entry is not created. On the next wrap-out of the same `Shared`, `get_or_insert_with` misses the registry entry, allocates a new `PyNode` handle, and returns it — silently breaking the at-most-one-live-handle invariant. Python `is`-identity between two reads of the same child is now `False` with no error raised. The generator emits this pattern unconditionally, so the bug is replicated across all ~54 hand-in sites and will appear in every future generated file.

**Consequence**: A Python exception during registry insertion (rare but possible: `MemoryError`, or any change to `get_registry` that can fail) is swallowed. The caller and its caller both see `Ok`, the child append succeeds, and the tree appears correct. The identity invariant breaks silently: `node.child_foo() is node.child_foo()` returns `False` for affected nodes, corrupting any downstream code that caches or de-duplicates nodes by identity. On-call has no signal that anything went wrong; the only symptom is unexpected `is`-identity failures far from the insertion site.

**Fix**: Replace `let _ = registry::register_if_absent(py, addr, obj);` with `registry::register_if_absent(py, addr, obj)?;` at all 54 hand-in sites and in the generator template (`gsm2tree_rs.py` line 557). The `?` propagates any Python error from the registry call, causing `extract_from_pyobject` to return `Err`, which surfaces as a Python exception to the caller. The `bool` return value is still not needed — `?` on `PyResult<bool>` discards the `Ok(bool)` and only propagates `Err`; rewrite as `registry::register_if_absent(py, addr, obj).map(|_| ())?;` or simply `let _registered = registry::register_if_absent(py, addr, obj)?;` to make the intent explicit without consuming the result.

---

*Phase 2 findings begin here. Commit reviewed: fb8852f (base: 7e39dfb). Scope: Phase 2 — idiomatic native surface (Debug, per-label accessors, CstError, label rename, Rustdoc).*

No findings.
