# TODO Adversarial Validation: crosscdylib-abi-check-helper

File: `crates/fltk-cst-core/src/cross_cdylib.rs`

## Claimed locations vs. actual

### `extract_source_text` claimed lines 57–100

The function signature is at line 66. The two-step ABI check begins at line 98 and runs to line 162. Lines 57–65 are the doc-comment's safety/soundness block. The fast path (local downcast, lines 68–72) and cache-hit path (lines 87–96) precede the ABI check. The actual check spans lines 98–162, not 57–100.

### `get_span_type` claimed lines ~255–300

The function signature is at line 292. The ABI check runs from line 313 to line 358, inside the `GILOnceCell::get_or_try_init` closure. The claimed ~255–300 is off; the function begins at 292 and the check body is 313–358.

## Is the duplication real?

Yes. Two independent blocks perform the identical logical sequence:

1. `getattr("_fltk_cst_core_abi")` → error if missing, extract as `&str`, error if not str, compare to `FLTK_CST_CORE_ABI`, error if mismatch.
2. Compute `expected_layout = size_of::<PyClassObject<T>>()`.
3. `getattr("_fltk_cst_core_abi_layout")` → error if missing, extract as `usize`, error if not int, compare to `expected_layout`, error if mismatch.

`extract_source_text` check: lines 98–135.
`get_span_type` check: lines 313–358.

## Error-message wording divergence — verified

The TODO claims wording diverges. Verified against actual text:

**Missing ABI string attr:**
- `extract_source_text` (line 98): reaches the outer `Err` at line 163–166 (`"expected fltk._native.SourceText, got {}"`) — it uses `if let Ok(marker)` without an error on `getattr` failure.
- `get_span_type` (lines 315–320): `map_err(|_| PyTypeError::new_err("Span ABI mismatch: fltk._native.Span has no _fltk_cst_core_abi marker (pre-sentinel build); ..."))`

This is a genuine structural divergence: `extract_source_text` uses `if let Ok` so a missing `_fltk_cst_core_abi` attr silently falls through to the generic "expected SourceText, got X" error; `get_span_type` uses `map_err` with a specific message naming the missing attr.

**ABI string mismatch:**
- `extract_source_text` (lines 101–105): `"SourceText ABI mismatch: object reports {s:?}, this module expects {FLTK_CST_CORE_ABI:?} (fltk-cst-core version skew between cdylibs)"`
- `get_span_type` (lines 328–332): `"Span ABI mismatch: fltk._native.Span reports {s:?}, this module expects {FLTK_CST_CORE_ABI:?} (fltk-cst-core version skew between cdylibs)"`

Wording differs: "object reports" vs. "fltk._native.Span reports"; type label differs ("SourceText" vs. "Span").

**Missing layout attr:**
- `extract_source_text` (lines 115–120): `"expected fltk._native.SourceText: _fltk_cst_core_abi_layout missing (old build without layout probe); this module expects layout {expected_layout}"`
- `get_span_type` (lines 341–345): `"Span ABI mismatch: fltk._native.Span has no _fltk_cst_core_abi_layout (partial-upgrade build); this module expects layout {expected_layout}"`

Wording diverges significantly. `extract_source_text` says "missing (old build without layout probe)"; `get_span_type` says "has no _fltk_cst_core_abi_layout (partial-upgrade build)".

**Non-int layout attr:**
- `extract_source_text` (lines 122–127): `"expected fltk._native.SourceText: _fltk_cst_core_abi_layout attribute is {}, not int"`
- `get_span_type` (lines 346–349): `"fltk._native.Span._fltk_cst_core_abi_layout is {}, not int"`

Prefixes differ.

**Layout mismatch:**
- `extract_source_text` (lines 130–134): `"SourceText ABI layout mismatch: object reports layout {reported_layout}, this module expects {expected_layout} (pyo3-resolution skew between cdylibs)"`
- `get_span_type` (lines 353–357): `"Span ABI layout mismatch: fltk._native.Span reports layout {reported_layout}, this module expects {expected_layout} (pyo3-resolution skew between cdylibs)"`

Wording differs: "object reports" vs. "fltk._native.Span reports".

## Proposed helper feasibility: `fn check_abi_pair<T: PyClass>`

The varying parameters across the two call sites are:
- `type_label: &str` — `"SourceText"` vs. `"Span"` (for error messages)
- `T` — `SourceText` vs. `Span` (for `size_of::<PyClassObject<T>>()`)

Both `SourceText` and `Span` implement `PyClass` (they are `#[pyclass]`). `size_of::<PyClassObject<T>>()` requires `T: PyClass` (used as a type parameter to `PyClassObject`). This is feasible as a generic function.

The helper would take `ty: &Bound<'_, PyType>` and `type_label: &str`, compute `expected_layout` from `T`, and perform both checks. Return type `PyResult<()>`.

Structural gap: `extract_source_text`'s missing-attr handling. Currently at line 98 it uses `if let Ok(marker) = obj_type.getattr(...)` — the entire ABI block is inside an `if let Ok`. If the helper mirrors `get_span_type`'s `map_err` approach, calling the helper from `extract_source_text` would change the observable error when `_fltk_cst_core_abi` is absent (from "expected SourceText, got X" to a specific attr-missing error). This is a behavioral change to error messages, not just a refactor.

## Structural observation: `extract_source_text` vs. `get_span_type` differ in invocation context

`get_span_type` checks the canonical `fltk._native.Span` type once at `GILOnceCell` init — it checks a type it retrieved from an import, before any downcast. The check runs once per process lifetime.

`extract_source_text` checks a caller-supplied object's type on every cache miss — it checks whatever type `obj.get_type()` returns. The check can run for multiple distinct foreign types (if multiple consumer cdylibs each have their own `SourceText`). The `FLTK_FOREIGN_SOURCE_TEXT_TYPE` cache only holds one type, so a second distinct foreign `SourceText` type would re-run the ABI check every call (no second-slot cache). This is noted in the comment at line 29 ("handles the case where multiple foreign cdylibs each register their own SourceText class") but the cache only covers one.

A helper would share the check logic but cannot unify these two caching strategies.

## What the helper call sites would look like

```rust
// get_span_type, inside get_or_try_init:
check_abi_pair::<Span>(&span_type, "fltk._native.Span")?;

// extract_source_text, slow path:
check_abi_pair::<SourceText>(&obj_type, "fltk._native.SourceText")?;
```

The `extract_source_text` call site would need to be restructured: the current `if let Ok(marker)` pattern (which treats missing attr as "not a SourceText, show generic error") would need to become an unconditional call that returns a specific error on missing attr. That is a detectable change in error text for the case where an unrecognized object with no `_fltk_cst_core_abi` attr is passed — the error would change from `"expected fltk._native.SourceText, got MyType"` to `"SourceText ABI mismatch: ... has no _fltk_cst_core_abi marker ..."`. Both are `PyTypeError`; the distinction matters only for error message readability.

## Summary of facts

| Claim | Verified? | Notes |
|---|---|---|
| Duplication exists | Yes | Lines 98–135 and 313–358 |
| Cited line ranges accurate | No | `extract_source_text` check is 98–162, not 57–100; `get_span_type` check is 313–358, not ~255–300 |
| Error wording diverges | Yes | 5 distinct error strings differ across the two paths |
| Generic helper over `PyClass` is feasible | Yes | `T: PyClass` is sufficient to specialize `size_of::<PyClassObject<T>>()` |
| Refactor is a net win | Depends | Reduces ~40 lines to 2 call sites + ~20-line helper; but requires behavioral change at `extract_source_text` missing-attr path |
| Deeper structural difference missed by TODO | Yes | `get_span_type` checks a fixed imported type once; `extract_source_text` checks caller-supplied types with a single-slot cache — the helper unifies logic but not the caching architecture |
