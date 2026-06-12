# Error-handling review — rust-generated-ident-collisions (d2abc80..4f66083)

## errhandling-1

**File:** `fltk/fegen/gsm2tree_rs.py:2137` (and the emit path that materialises the name)

**Broken path:** `EqWorklistItem` is emitted as a module-level `enum EqWorklistItem` by `_eq_block` but is absent from `_RESERVED_CLASS_NAMES`. The invariant-enforcement `assert` only guards the `Py`/`Child`/`Label` suffix/prefix families; it does not check that every module-level generated name that is NOT a per-rule derivative is listed as reserved.

**Why it vanishes:** A grammar rule named `eq_worklist_item` passes every check in `__init__` — it does not collide with any entry in `_RESERVED_CLASS_NAMES`, and it cannot collide with another rule's per-rule derivatives — so `RustCstGenerator.__init__` raises no error. Generation proceeds and emits both `pub struct EqWorklistItem { … }` (the rule's node struct) and `enum EqWorklistItem { … }` (the worklist enum), producing a Rust duplicate-definition compile error with no diagnostic from FLTK.

**Consequence:** Silent bad output. `cargo build` fails with an opaque Rust E0428 (`EqWorklistItem` defined multiple times in module scope). The FLTK generator reports success; the build system error does not name any FLTK source location. On-call cannot distinguish a generator bug from user error without reading the raw Rust output. `DropWorklistItem` was added to the reserved set in this diff (correctly) but `EqWorklistItem` was missed.

**Fix:** Add `"EqWorklistItem": "the generated EqWorklistItem eq-worklist enum"` to `_RESERVED_CLASS_NAMES`. Then add `"eq_worklist_item"` to the reserved-name test parameterisation in `TestReservedClassNameRejection.test_reserved_class_name_rejected`.

---

## errhandling-2

**File:** `fltk/fegen/gsm2tree_rs.py:142-143`

**Broken path:** In the cross-rule claims loop, the guard `if model is not None and model.labels` uses `.get(rule.name)` to retrieve the model. Because `CstGenerator.__init__` populates `rule_models` for every rule in `grammar.rules` before `RustCstGenerator.__init__` runs its cross-rule check, `.get()` can never return `None` for any rule that passed the earlier per-rule loop. The `is not None` branch is therefore dead, and any future refactor that genuinely allows a missing model entry would silently skip claiming the `{CN}Label` identifier for that rule — causing the cross-rule check to miss a `{CN}Label` collision that `generate()` would later materialise.

**Why it matters for error observability:** This is not a crash risk today, but the defensive guard creates a false sense of safety. If `rule_models` ever becomes sparse (e.g. a grammar pre-filter that removes some models), the collision check will silently produce false-negatives (no error raised) while `generate()` still emits the label enum and collides. The correct guard at this site is `model.labels` alone; if `model` could legitimately be absent, a `RuntimeError` (matching the pattern in `_rule_info`) should be raised, not silently skipped.

**Consequence:** Under the current code this does not cause missed detections. Under a future refactor that makes `rule_models` sparse, label-enum collisions go undetected until `cargo build` fails with an opaque error.

**Fix:** Replace `model = self._py_gen.rule_models.get(rule.name)` / `if model is not None and model.labels` with a direct lookup and assertion, consistent with `_rule_info`'s pattern:
```python
model = self._py_gen.rule_models[rule.name]  # invariant: always present
if model.labels:
    claims.setdefault(self._label_enum_rust_name(cn), []).append(...)
```
If absence should be tolerated, raise `RuntimeError` rather than silently skipping.
