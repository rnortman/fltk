reuse-1

File:line: `tests/test_phase4_fegen_rust_backend.py:115-123` (`_CHILD_SPAN_PARAMS` parametrize data).

What's duplicated: The three `(class, append_method, child_method)` triples for `Identifier/append_name/child_name`, `Literal/append_value/child_value`, `RawString/append_value/child_value` are hand-enumerated here. The same three entries already exist in `CLASS_LABEL_INFO` at `tests/test_fegen_rust_cst.py:55-57` (the rows where `child_factory` is `_span`, i.e. terminal/Span children). `CLASS_LABEL_INFO` is already used by `TestAppendChildRoundtrip.test_append_and_child_roundtrip` (`:132-139`) to exercise the same `append_<label>`/`child_<label>` method pairs.

Existing: `CLASS_LABEL_INFO` in `tests/test_fegen_rust_cst.py:43-61`. The three relevant rows are at lines 55-57. The catalogue is importable — `from tests.test_fegen_rust_cst import CLASS_LABEL_INFO` (or a shared conftest/helper) would avoid the parallel list.

Consequence: the two lists will diverge silently. If a label is renamed in the generated Rust CST (e.g. `name` → `identifier` for `Identifier`), `CLASS_LABEL_INFO` is the authoritative record and gets updated; `_CHILD_SPAN_PARAMS` is a separate copy that will rot. A maintainer updating one is unlikely to notice the other because they live in different test files covering different concerns (unit vs. integration). The new tests would then fail or miss the updated method while silently testing a stale name.

Note: the new tests assert a meaningfully distinct contract (`.start`, `.end`, `.text()`, `has_source()`, `isinstance`, type-rejection) — they are genuine extensions, not redundant tests. Only the parametrize data is the duplication; the assertion bodies have no equivalent in `test_fegen_rust_cst.py`.
