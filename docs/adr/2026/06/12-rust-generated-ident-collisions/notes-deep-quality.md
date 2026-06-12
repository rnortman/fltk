Style: concise, precise, no padding, no preamble. Audience: smart LLM/human.

## quality-1 — Three `f"Py{...}"` inline sites not converted to `py_handle_name`

`fltk/fegen/gsm2tree_rs.py:727`, `:757`, `:2186`

The stated purpose of `py_handle_name` is "single source of truth … used in the cross-rule collision check and at the handle definition site in `_node_block`." The docstring explicitly says "definition site." But three additional emission sites still inline `f"Py{child_cls}"` / `f"Py{class_name}"`:

- Line 727: `to_pyobject` in `_child_enum_block` (reference site — constructing the handle by type name)
- Line 757: `extract_from_pyobject` in `_child_enum_block` (reference site — type-checking and extracting)
- Line 2186: `_module_init_block` (registration site — `module.add_class::<PyCN>()`)

The design doc (§2) calls out the drift risk: "remaining inline `Py{...}` interpolations (referenced-handle usages … and the module-init site) stay as-is; the drift test in the test plan guards them." So the author traded a complete consolidation for test-guarded drift tolerance. The consequence is that a future rename of the handle naming scheme must be applied in four places (three inline plus `py_handle_name`), with the drift test as the only guard that the inline sites were updated. The test catches the problem only after a change breaks consistency — it does not prevent the divergence. The fix is trivial: replace the three inline `f"Py{child_cls}"` / `f"Py{class_name}"` locals with `self.py_handle_name(child_cls)` / `self.py_handle_name(class_name)` at each site.

**Consequence:** Every future renaming of the handle scheme requires a multi-site surgical edit; the inline pattern will propagate to any new emission sites added later.

## quality-2 — Prediction-vs-output drift test accesses private internals (`_py_gen`, `_label_enum_rust_name`)

`tests/test_gsm2tree_rs.py:1793-1808`

The drift-guard test reaches into `gen._py_gen.class_name_for_rule_node(...)`, `gen._py_gen.rule_models.get(...)`, and calls `RustCstGenerator._label_enum_rust_name(cn)` directly. `_py_gen` and `_label_enum_rust_name` are implementation details; neither is part of the public API of `RustCstGenerator`. The test thereby couples itself to the private delegation structure. If `_py_gen` is ever inlined, renamed, or the delegation inverted, the test breaks for reasons unrelated to what it is testing. `_label_enum_rust_name` has an analogue public path via the existing `child_enum_name` pattern (both are static helpers for naming); it could be made public like `child_enum_name` and `py_handle_name` are.

**Consequence:** Refactoring `RustCstGenerator`'s internal delegation silently breaks the drift guard; the guard is the primary protection against `py_handle_name` divergence, so losing it undetected is a real risk.

Fix: expose `class_name_for_rule_node` and `label_enum_name` (analogous to `child_enum_name`/`py_handle_name`) as public methods/statics on `RustCstGenerator`, and rewrite the test in terms of those. Alternatively, if `_label_enum_rust_name` is not intended to be part of the stable surface, expose a thin public wrapper just for the naming contract (same pattern as `child_enum_name`).
