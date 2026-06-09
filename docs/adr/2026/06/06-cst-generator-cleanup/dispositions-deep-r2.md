Concise. Precise. No padding.

---

reuse-1:
- Disposition: Fixed
- Action: Extracted `make_zero_label_grammar`, `make_labeled_grammar`, and `make_generator` to `tests/gsm2tree_helpers.py`. Updated `tests/test_gsm2tree_py.py` to import from shared module (removed local definitions). Removed TODO comment from `test_gsm2tree_py.py`. Removed TODO.md entry for `test-grammar-helpers-conftest`.
- Severity assessment: Shared module eliminates drift risk between Python/Rust generator boundary-condition tests; constructor-signature changes now propagate to both test files from one definition.

reuse-2:
- Disposition: Fixed
- Action: Same extraction as reuse-1. Also replaced inline `CstGenerator(grammar=dummy_grammar, py_module=..., context=...)` at `tests/test_gsm2tree_rs.py:test_rule_name_to_class_name_mapping` with `_make_generator(make_labeled_grammar())` using the shared helpers. Removed TODO comment. Updated `TestEmptyLabelEnumOmitted` assertions from "Token"/"token" to "Foo"/"foo" to match the shared grammar's rule name.
- Severity assessment: Single definition of `make_generator` means a constructor-signature change now requires one edit rather than two.
