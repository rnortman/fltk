# Test review — cst-generator-cleanup (2dd27f0..b72aea6)

Concise. Precise. No padding.

---

## test-1

**File:line** `tests/test_gsm2tree_py.py` — `TestLabelFreeConcreteClass` class

**What's wrong** The `extend_children` method is not covered. The label-free concrete class tests check `children`, `append`, `extend`, and `child`, but `extend_children` (`gsm2tree.py:263-269`) is emitted unconditionally for every node (label-free and label-bearing) and its signature/body changed in this diff via the `label_annotation` variable—`extend_children`'s `other` parameter is typed with the forward-ref `'{class_name}'`, which is independent of labels, but no test asserts this method is present and correctly shaped on a label-free node.

**Consequence** If `extend_children` were accidentally omitted or mis-annotated for label-free nodes, no test would catch it. The omission is adjacent to the code paths that were changed.

**Fix** Add `test_extend_children_present` to `TestLabelFreeConcreteClass` using `_find_function(klass, "extend_children")`, assert it is not `None`, and assert its `ast.unparse` contains `other: 'Foo'` and returns `None`.

---

## test-2

**File:line** `tests/test_gsm2tree_py.py:329-336` — `test_all_appears_near_top`

**What's wrong** The test for slop-2 (the dynamic `__all__` insert-position fix) uses a magic constant of 10 statements to check "near the top." This does not verify the core invariant that was fixed: `__all__` must appear immediately after the last import / `TYPE_CHECKING` block, not just somewhere in the first 10 stmts. A regression that silently pushed `__all__` to statement index 7 (past some newly-added class) would still pass.

More specifically, the test grammar (`_make_simple_grammar`) has two labeled rules, so the generated protocol module is small. The "first 10 stmts" bound is not tight enough to catch a misplacement that lands `__all__` after the first class definition.

**Consequence** If the structural search regresses (e.g., hard-coded index creeps back), the test passes as long as `__all__` lands anywhere before the 11th statement. The behavioral invariant being tested—`__all__` follows immediately after imports—is unverified.

**Fix** After locating `__all__` in `module.body`, assert that the statement at `idx - 1` is an `ast.ImportFrom`, `ast.Import`, or a `typing.TYPE_CHECKING` `ast.If` block. This directly encodes the structural contract. Alternatively, assert that all statements before `__all__` are imports/TYPE_CHECKING blocks and all statements after are class defs or `__all__`-style assignments.

---

## test-3

**File:line** `tests/test_gsm2tree_py.py` — `TestLabelBearingConcreteClassUnchanged`

**What's wrong** `test_per_label_methods_present` (line 211-215) only checks for the presence of five method names via `_find_function`. It does not assert the correctness of the extracted `_emit_label_quintet` helper's output: no test checks that the quintet bodies are non-empty, that `maybe_name` returns `Optional[...]`, that `child_name` returns the labeled type, or that `children_name` returns `Iterator[...]`. The test is a smoke test ("methods exist") not a behavior test ("methods have correct signatures"). This was the primary structural change in sub-task C.

**Consequence** A regression in `_emit_label_quintet` that emits the wrong return type for `child_<l>` or `maybe_<l>` would not be caught. The existing `test_cst_protocol.py:test_protocol_node_has_required_members` also only checks presence, not signature correctness, for protocol classes.

**Fix** In `TestLabelBearingConcreteClassUnchanged`, for at least `child_name` and `maybe_name`, add assertions on `child_fn.returns` (the annotation AST node). Specifically: `child_name` return annotation should equal the per-label child annotation (not `Optional[...]`), and `maybe_name` return annotation should start with `typing.Optional[`. Use `_annotation_source` which already exists in the test module.

---

## test-4

**File:line** `tests/test_gsm2tree_py.py` — no test covers the `_emit_label_quintet` `ValueError` path (slop-1 fix from b72aea6)

**What's wrong** The slop-1 fix added an explicit `raise ValueError(f"Unknown method: {method!r}")` to `concrete_body_for` and to the analogous path. The ValueError is an unreachable-in-production path, but the value of the explicit guard is precisely that callers passing a bad method name get a diagnostic rather than silent wrong behavior. There is no test that invokes `_emit_label_quintet` with an unrecognized method name to confirm the error fires.

**Consequence** The guard is verified only by code inspection. If it were accidentally removed or the method-name check were broken (e.g., a typo in a string comparison), no test would catch the regression. This is low-risk for the guard itself, but it is a fixed slop item that the ADR notes as intentional—its test should be as intentional.

**Fix** Add a small test (can be a module-level function, not a class) that constructs a `CstGenerator` over `_make_labeled_grammar()`, defines a `body_for` that delegates to `_emit_label_quintet` directly with `method="nonexistent_method"`, and asserts `pytest.raises(ValueError, match="Unknown method")`. This requires exposing `_emit_label_quintet` to the test, which is already possible since it's a method on the public `CstGenerator`.
