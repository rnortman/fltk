## reuse-1

**File:line** `crates/fltk-cst-core/src/cross_cdylib.rs:79-86` and `cross_cdylib.rs:154-161`

**What's duplicated** The type-name retrieval and `PyTypeError` construction at the error exit of both `extract_source_text` and `extract_span` are identical four-line blocks:

```rust
let type_name = obj
    .get_type()
    .name()
    .map(|n| n.to_string())
    .unwrap_or_else(|_| "<unknown type>".to_string());
Err(PyTypeError::new_err(format!("expected fltk._native.<Type>, got {type_name}")))
```

**Existing function/utility** None — no shared helper exists yet. The pattern was introduced once in the pre-existing `extract_span` and then copied verbatim into the new `extract_source_text` added by this diff.

**Consequence** If the `<unknown type>` fallback text, the `format!` style, or the error-message schema changes in one function (e.g. to include module-qualified type names or to use `pyo3::intern!` for the attribute lookup), the other diverges silently. Given that `extract_source_text` and `extract_span` live side-by-side in the same 205-line file, a shared private helper (e.g. `fn py_type_name(obj: &Bound<'_, PyAny>) -> String`) would eliminate the copy at negligible cost.
