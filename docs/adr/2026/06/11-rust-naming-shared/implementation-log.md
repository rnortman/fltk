## Increment 1 — add `child_enum_name` to `RustCstGenerator` and wire all four call sites (commit 6893aa9)

- `gsm2tree_rs.py:419-427`: added `@staticmethod child_enum_name(class_name: str) -> str` adjacent to `_label_enum_rust_name`.
- `gsm2tree_rs.py:517`: `_child_enum_block` → `enum_name = self.child_enum_name(class_name)`.
- `gsm2tree_rs.py:641`: `_node_block` → `enum_name = self.child_enum_name(class_name)`.
- `gsm2tree_rs.py:1086`: `_label_type_info` → `enum_name = self.child_enum_name(self._py_gen.class_name_for_rule_node(rule_name))`.
- `gsm2parser_rs.py:193-194`: `_child_enum_name` body replaced with `return self._cst.child_enum_name(self._class_name(rule_name))`; TODO comment removed.
- `TODO.md`: removed `## rust-naming-shared` entry.
- Generated Rust files byte-identical (`git diff --exit-code -- '*.rs'` clean after `make gencode`).
- All 1399 tests pass; `make check` passes.
