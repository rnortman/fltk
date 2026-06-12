# Efficiency review — crosscdylib-abi-check-helper

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Diff reviewed: `1963894..912b285` (HEAD `912b285c770c0244c2c51d618548dab1845ac26f`).

## efficiency-1: `subject` computed eagerly on the SourceText success path

- `crates/fltk-cst-core/src/cross_cdylib.rs:93` — `check_abi_pair::<SourceText>(&obj_type, "SourceText", &py_type_obj_name(&obj_type))?;`
- Problem: `py_type_obj_name` calls `fully_qualified_name()` (Python-level attribute access on `__module__`/`__qualname__` plus string construction) and allocates a `String` before `check_abi_pair` runs — i.e. on every slow-path invocation, including the success case. The pre-refactor code derived the type name only inside error construction (`py_type_name(obj)` lived in the final `Err(...)` format). The refactor moved this work from error-path-only to unconditional. `subject` is consumed only by the six error templates; on `Ok(())` the string is dead.
- Consequence: per-validation cost on the cross-cdylib SourceText path. With one foreign consumer cdylib it fires once per process (slow path is shielded by the `FLTK_FOREIGN_SOURCE_TEXT_TYPE` pointer-compare cache) — negligible. With two or more distinct foreign `SourceText` types in one process, the single-slot cache permanently misses for all but the first type (pre-existing architecture, declared out of scope), and this change then adds an extra Python C-API round-trip plus a heap allocation to **every** source-bearing span read for the uncached type(s) — the module's own comment calls this "the normal path when generated consumer code reads a source-bearing span". Cost is new relative to base; it bites exactly when the already-known single-slot ceiling bites, making that ceiling slightly worse.
- Fix: make `subject` lazy. E.g. change the parameter to `subject: &dyn Fn() -> String` (Span path: `&|| "fltk._native.Span".to_string()`; SourceText path: `&|| py_type_obj_name(&obj_type)`) and call it only inside the `map_err`/`Err` arms. Alternatively a two-variant enum (`Subject::Path(&'static str) | Subject::Derived(&Bound<PyType>)`) rendered on demand. Either keeps the six templates' output byte-identical.

No other findings. Error `format!`s sit inside `map_err` closures (error-path-only — correct); `intern!` keeps attr-name strings cached; `check_abi_pair` monomorphizes twice (trivial); Span path uses a static `&str` subject (no allocation); caching architecture and `GILOnceCell` semantics unchanged from base.
