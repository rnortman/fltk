Concise. Precise. No padding.

---

test-1:
- Disposition: Fixed
- Action: Added `test_extend_children_present` to `TestLabelFreeConcreteClass` asserting the method exists, the `other` param is typed `'Foo'`, and return is `None`. `tests/test_gsm2tree_py.py:186-195`.
- Severity assessment: Without coverage, a regression silently omitting or mis-typing `extend_children` on label-free nodes would go undetected. Low operational risk; test gap was adjacent to the changed code path.

test-2:
- Disposition: Fixed
- Action: Replaced the first-10-stmts magic-constant check with a structural assertion that the statement immediately preceding `__all__` is an import or `typing.TYPE_CHECKING` block. `tests/test_gsm2tree_py.py:360-398`.
- Severity assessment: The previous test could pass with `__all__` silently misplaced to statement index 7 (past a class def). The new check encodes the actual structural contract.

test-3:
- Disposition: Fixed
- Action: Added `test_child_name_return_annotation` (asserts bare child type, not Optional) and `test_maybe_name_return_annotation` (asserts `typing.Optional[...]`) to `TestLabelBearingConcreteClassUnchanged`. `tests/test_gsm2tree_py.py:217-236`.
- Severity assessment: A regression in `_emit_label_quintet` emitting the wrong return type for `child_<l>` or `maybe_<l>` would previously go undetected. Moderate risk given sub-task C was the primary structural change.

test-4:
- Disposition: Fixed
- Action: Added `test_emit_label_quintet_unknown_method_raises` using `monkeypatch` to inject a call to `body_for("nonexistent_method", ...)` during `py_class_for_model`, verifying the production closure raises `ValueError` with "Unknown method". `tests/test_gsm2tree_py.py:412-441`.
- Severity assessment: Guard is unreachable in production but its purpose is to give a diagnostic on future misspellings; test confirms it fires. Low risk if absent, but tests the explicit intentional fix.

reuse-1:
- Disposition: TODO(test-grammar-helpers-conftest)
- Action: Added TODO entry in `TODO.md` and `# TODO(test-grammar-helpers-conftest)` comments at `tests/test_gsm2tree_py.py:24` and `tests/test_gsm2tree_rs.py:127`.
- Severity assessment: Duplicate boundary-condition grammars in separate files can drift silently, masking asymmetries between Python and Rust generator behavior. Low urgency; a conftest extraction is a cross-file refactor better handled as a standalone increment.

reuse-2:
- Disposition: TODO(test-grammar-helpers-conftest)
- Action: Same TODO slug; `# TODO(test-grammar-helpers-conftest)` comment added at `tests/test_gsm2tree_rs.py:475`.
- Severity assessment: Inline `CstGenerator` construction duplicates `_make_generator`; a constructor-signature change would require two edits. Contained to one site; acceptable to defer.

quality-1:
- Disposition: Fixed
- Action: Changed `body_for` parameter type in `_emit_label_quintet` from `Callable[[str, str], ...]` to `Callable[[Literal["append", "extend", "children", "child", "maybe"], str], ...]`. Added `Literal` to imports. `fltk/fegen/gsm2tree.py:8,551-553`.
- Severity assessment: Without the Literal constraint, pyright gives no feedback on misspelled method names; the only signal is a runtime ValueError during code generation. Zero logic change; annotation-only tightening.

quality-2:
- Disposition: Fixed
- Action: Replaced `pygen.stmt(f"__all__ = {public_names!r}")` with explicit `ast.Assign(targets=[ast.Name(...)], value=ast.List(elts=[ast.Constant(name) for name in public_names]))`. `fltk/fegen/gsm2tree.py:523-531`.
- Severity assessment: The repr-interpolation pattern was the sole site in the generator bypassing structural AST construction; inconsistent and fragile under name contents containing quotes or non-identifiers. Not a current bug but a maintenance hazard inconsistent with project conventions.
