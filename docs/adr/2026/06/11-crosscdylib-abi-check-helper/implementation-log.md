## Increment 1 — extract `check_abi_pair` helper, unify both call sites, hygiene (commit 790f70d)

- `crates/fltk-cst-core/src/cross_cdylib.rs`: new private `check_abi_pair<T: PyClass>` helper implementing the 7-step ABI pair check with unified error templates parameterized by `type_label` and `subject`.
- `crates/fltk-cst-core/src/cross_cdylib.rs`: new `py_type_obj_name` helper (uses `fully_qualified_name()` with fallback `"<unknown type>"`).
- `extract_source_text` slow path (was lines 98–166): replaced `if let Ok(marker)` nest + trailing generic error with `check_abi_pair::<SourceText>(&obj_type, "SourceText", &py_type_obj_name(&obj_type))?`. Behavior change: missing-marker case now raises template 1 instead of generic "expected fltk._native.SourceText, got {type}".
- `get_span_type` GILOnceCell closure (was lines 304–358): replaced 45-line inline check with `check_abi_pair::<Span>(&span_type, "Span", "fltk._native.Span")?`.
- SAFETY comment in `extract_source_text` updated to cite `check_abi_pair`. SAFETY comment in `extract_span` updated to reference `check_abi_pair` via `get_span_type`.
- `FLTK_CST_CORE_ABI` doc comment reworded: "checked together at GILOnceCell init time" → "checked together by `check_abi_pair`".
- `FLTK_FOREIGN_SOURCE_TEXT_TYPE` doc comment: removed stale `TODO(crosscdylib-abi-check-helper)` note.
- `tests/test_rust_span.py`: updated 6 tests to pin new unified message templates; added `FakeSource` type-name assertion to `test_with_source_unchecked_bogus_abi_marker_raises_type_error`; added `partial-upgrade` and `not int` assertions; updated `test_source_text_abi_string_missing_raises` docstring to call out the deliberate behavior change.
- `TODO.md`: removed `crosscdylib-abi-check-helper` entry.
- All 1414 tests pass; `cargo test -p fltk-cst-core --no-default-features` passes; ruff/pyright clean.
