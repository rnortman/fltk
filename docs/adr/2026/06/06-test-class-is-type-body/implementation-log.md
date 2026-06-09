# Implementation Log: test-class-is-type-body

## Increment 1 — remove test_class_is_type, empty class, section banner, and TODO.md entry (commit 3a1cefe)

- `tests/test_fegen_rust_cst.py:68-82`: deleted `TestAllClassesImportable` class (method + `TODO(test-class-is-type-body)` comment + AC-7 section banner); `ALL_CLASSES`/`ALL_CLASS_IDS`/`CLASS_LABEL_INFO` untouched; 14-name import block untouched.
- `TODO.md:19-21`: deleted `test-class-is-type-body` slug entry.
- `uv run pytest tests/test_fegen_rust_cst.py` — 140 passed (14 no-signal cases removed, all remaining AC-8 tests green).
