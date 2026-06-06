# Reuse Review — Cross-Backend Label Equality + NodeKind

Commit reviewed: c57f888

---

## reuse-1

**File:** `fltk/fegen/gsm2tree.py:99-130` (`_node_kind_enum`) vs `fltk/fegen/gsm2tree.py:157-181` (inside `py_class_for_model`)

Both sites build the same four AST nodes — a `_fltk_canonical_name` property, an `__eq__` with the same five `pygen.stmt` lines, and a `__hash__` — via identical `pygen.function` / `pygen.stmt` calls. The only difference is the canonical-name string template: `"NodeKind.{self.name}"` vs `f"{class_name}.Label.{{self.name}}"`. No shared helper was extracted.

**Existing pattern that could be used:** `pygen.function` + `pygen.stmt` are already the building blocks. A private method `_emit_cross_backend_eq_hash(enum_klass, canonical_name_expr: str)` that appends the canonical-name property, `__eq__`, and `__hash__` to a `ast.ClassDef` would serve both call sites with the canonical string as the only parameter.

**Consequence:** If the equality contract changes — e.g. a bug in the `NotImplemented` return, or a same-type fast-path adjustment — the fix must be applied in two places in `gsm2tree.py`. The two copies will diverge over time as maintenance on one site (e.g. perf work on the Label hot path) is not mirrored to the other.

---

## reuse-2

**File:** `fltk/fegen/gsm2tree_rs.py:183-206` (inside `_node_kind_block`) vs `fltk/fegen/gsm2tree_rs.py:256-280` (inside `_label_enum_block`)

The Rust emission of `_fltk_canonical_name` getter, `__eq__`, and `__hash__` is copy-pasted between the two methods. Lines 184-206 and 257-280 are textually identical except for the own-type extract call (`other.extract::<NodeKind>()` vs `other.extract::<{enum_name}>()`), which is parameterisable.

**Existing pattern:** both methods already build a `lines: list[str]` and call `lines.append(...)`. A private helper `_emit_rust_cross_backend_eq_hash(lines, type_name: str)` appending the 18 fixed lines with `type_name` substituted in the own-type fast path would eliminate the duplicate.

**Consequence:** Identical to reuse-1 but on the Rust-emission side. The Rust `__eq__` logic and the Python `__eq__` logic must stay in sync (design §2.3 explicitly cross-references §2.2); having each also duplicated internally doubles the divergence surface. A bug fix or PyO3-API update touching the `into_pyobject(py)?.to_owned().unbind().into_any()` chain must be applied twice.

---

No other reuse issues found. `fltk/fegen/fltk_cst.py` and `src/cst_fegen.rs` contain per-rule repetition of the same blocks, but those are generator outputs — duplication there is inherent and correct.
