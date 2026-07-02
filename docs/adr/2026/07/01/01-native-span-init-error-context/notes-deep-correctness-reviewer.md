# Deep correctness review — native-span-init-error-context

Reviewed: f8f34288..b60f8c78 (`git diff f8f34288ff30e175021866746fa3b28e6a65485c..b60f8c7873249598fc4486b49a676b3c35e9a1cb`)

No findings.

Verification performed:

- **Brace escaping** (`fltk/fegen/gsm2lib_rs.py:204`): the f-string emits `{{e}}` → literal `{e}` in the Rust `format!` string; `{spec.module_name}` interpolates at generation time. Confirmed the committed `src/lib.rs:20` carries `_native module init: failed to create UnknownSpan sentinel: {e}` exactly.
- **Injection into the emitted Rust string literal**: `spec.module_name` is validated by `RustLibGenerator.__init__` → `LibSpec.validate()` → `_validate_rust_ident` (`gsm2lib_rs.py:17,128,147`), so it cannot contain quotes or braces that would corrupt the emitted `format!` literal.
- **Emitted Rust compiles**: `cargo check -q` clean at HEAD; the `map_err` closure shape is byte-similar to the compile-proven sibling pattern in `crates/fltk-cst-core/src/py_module.rs:97-101,155-159` (PyErr `Display` in `format!` is established usage).
- **Drift-pin test path** (`fltk/fegen/test_gsm2lib_rs.py:310`): `Path(__file__).parents[2]` from `fltk/fegen/test_gsm2lib_rs.py` → repo root; `src/lib.rs` located correctly. Skip-if-absent guard behaves as designed.
- **Drift pin holds**: ran `uv run pytest fltk/fegen/test_gsm2lib_rs.py` — 52 passed, including `test_committed_lib_rs_matches_generator` (committed `src/lib.rs` is byte-for-byte generator output for the Makefile spec: `--module-name _native --register-span-types --unknown-span-static --no-cst --no-parser`, matching Makefile:276-277).
- **Negative assertion soundness**: `"Span::unknown())?.into_any()" not in src` correctly excludes the old unwrapped form; the new multi-line emission cannot false-match it. `"LineColPos" not in src` in the standard-spec tests is sound (standard spec emits no span content).
- **Blank-line/ordering logic** in `generate()` (span block ↔ submodule separator, `add_class` ordering Span/SourceText/LineColPos) matches committed output — verified by the byte-equality pin.
- **TODO system sync**: `TODO(native-span-init-error-context)` comment removed and `TODO.md` entry removed in the same change; no stale references remain (grep clean).
