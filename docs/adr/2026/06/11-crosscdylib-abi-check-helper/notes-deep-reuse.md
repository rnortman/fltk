Style: concise, precise, complete, unambiguous. No padding, no preamble.

## reuse-1: `py_type_obj_name` partially duplicates `py_type_name` + `py_attr_type_name`

File: `crates/fltk-cst-core/src/cross_cdylib.rs`, lines 117–142.

The file now has three private type-name helpers:

- `py_type_name(obj: &Bound<'_, PyAny>) -> String` — calls `.get_type().name()`, line 117.
- `py_attr_type_name(attr: &Bound<'_, PyAny>) -> String` — doc says "identical idiom to `py_type_name` but takes the attribute `Bound` directly"; calls `.get_type().name()`, line 137. These two are themselves near-duplicates of each other (same body, same input type; the distinction in naming is caller-intent, not implementation).
- `py_type_obj_name(ty: &Bound<'_, PyType>) -> String` — new in this diff; calls `.fully_qualified_name()`, line 129.

`py_type_name` and `py_attr_type_name` use `PyType::name()` (short, unqualified); `py_type_obj_name` uses `PyType::fully_qualified_name()` (module-prefixed where available). The three helpers share the same shape — call a name method, map to String, unwrap with fallback — but differ only in: input type (`PyAny` vs `PyType`) and which name method. `py_attr_type_name` is admitted by its own doc to duplicate `py_type_name` modulo input type.

**Existing functions:** `py_type_name` (line 117) and `py_attr_type_name` (line 137) predate this diff. The new `py_type_obj_name` (line 129) adds a third variant with the same structural pattern.

**Consequence:** Three nearly-identical private helpers where one unified helper accepting `&Bound<'_, PyAny>` (with an internal `.get_type()` call) and a flag or a separate `fully_qualified` variant would suffice. The accumulation is low-severity within a single private module today, but each added helper raises the chance that future error-message callsites pick the wrong one (e.g. using `py_type_name` where `py_type_obj_name` is wanted), producing inconsistent qualification level in error messages. The design document justified `py_type_obj_name` as needed for `check_abi_pair`'s SourceText subject derivation (§2) — the justification is sound, but the resulting three-function menagerie is worth noting.

No action required if the module stays this size and these remain private; worth consolidating if a fourth variant appears.
