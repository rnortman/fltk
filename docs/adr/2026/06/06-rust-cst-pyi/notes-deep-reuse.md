Style: concise, precise, no padding. Audience: smart LLM/human.

---

## reuse-1

**File:line:** `fltk/fegen/gsm2tree_rs.py:339-341`

**What's duplicated:** `_node_kind_python_name(class_name)` returns `class_name.upper()`. This is exactly what `CstGenerator.node_kind_member_name(rule_name)` computes (`gsm2tree.py:95-97`): `self.class_name_for_rule_node(rule_name).upper()`. `RustCstGenerator` already holds `self._py_gen` (a `CstGenerator`) and has `class_name` in hand from `_rule_info()`, so it could call `self._py_gen.node_kind_member_name(rule_name)` (or just inline `.upper()` on the already-computed `class_name` without a wrapper method at all).

**Existing function:** `CstGenerator.node_kind_member_name` — `fltk/fegen/gsm2tree.py:95-97`.

**Consequence:** `_node_kind_python_name` is a private wrapper that wraps a trivial expression (`class_name.upper()`), not the authoritative method. If the naming convention ever changes in `CstGenerator.node_kind_member_name` (e.g., different casing scheme), `_node_kind_python_name` silently diverges, causing the `.pyi` stub to emit `NodeKind` member names that disagree with both the `.rs` Rust-level names (which use `_node_kind_python_name` too, via `_node_kind_block`) and the protocol module (which uses `node_kind_member_name`). The three generators would then produce mismatched `NodeKind` member names across `.rs`, `.pyi`, and protocol, breaking conformance checks. The three-method split (`_node_kind_variant_name`, `_node_kind_python_name`, `_node_kind_canonical_name`) internalizes this logic in `RustCstGenerator` rather than delegating to the single source of truth in `CstGenerator`.

---

## reuse-2

**File:line:** `fltk/fegen/gsm2tree_rs.py:197-228` (the per-label quintet loop inside `generate_pyi`)

**What's duplicated:** The loop emits five per-label methods (`append_<l>`, `extend_<l>`, `children_<l>`, `child_<l>`, `maybe_<l>`) for each label. `CstGenerator._emit_label_quintet` (`gsm2tree.py:560-607`) exists precisely to emit this quintet in a shared, parameterized form, with `annotation_for` and `body_for` callbacks to customize annotation strings and method bodies. `generate_pyi` hand-rolls the same five-method pattern as a string-building loop instead of calling `_emit_label_quintet`.

**Existing function:** `CstGenerator._emit_label_quintet` — `fltk/fegen/gsm2tree.py:560-607`.

**Consequence:** `_emit_label_quintet` is the single authoritative place that defines the quintet names and their parameter signatures. If a sixth accessor is ever added to the quintet (or a method is renamed), `generate_pyi`'s hand-rolled loop does not automatically pick it up, producing a stub that misses the new method and silently fails the stub-vs-runtime direction of the B4 test. The caller would need to separately update both `_emit_label_quintet` and the string-building loop in `generate_pyi`. Note: `_emit_label_quintet` operates on `ast.FunctionDef`s (AST), while `generate_pyi` operates on strings, so calling it directly is not a one-liner — the string-vs-AST boundary is the structural reason the loop was written inline. The reuse opportunity is real but requires either (a) unparsing the `ast.FunctionDef`s, or (b) extracting the method-name / parameter-shape logic into a shared lower-level helper that both callers use.

---

No further findings.
