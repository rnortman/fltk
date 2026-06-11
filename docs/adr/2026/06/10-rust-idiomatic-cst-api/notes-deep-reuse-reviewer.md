Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

# Reuse review — Phase 0 (ABI sentinel hardening, Span/SourceText)

Commit reviewed: 807d56a. Scope: Phase 0 only.

---

## reuse-1 — Duplicated `attr_type` extraction snippet (3 sites in `cross_cdylib.rs`)

**Files:lines**

- `crates/fltk-cst-core/src/cross_cdylib.rs:72–82` (`extract_source_text`, layout_attr non-int error)
- `crates/fltk-cst-core/src/cross_cdylib.rs:102–111` (`extract_source_text`, abi-marker non-str error)
- `crates/fltk-cst-core/src/cross_cdylib.rs:269–278` (`get_span_type`, layout_attr non-int error)

Also appears (pre-existing, not new) at lines 103–107 (abi-marker non-str branch in `extract_source_text`).

**What's duplicated**

The three-line idiom:
```rust
attr.get_type()
    .name()
    .map(|n| n.to_string())
    .unwrap_or_else(|_| "<unknown>".to_string())
```
The private helper `py_type_name` at line 120 already does exactly this for `obj` itself but takes a `Bound<'_, PyAny>` at the object level, not at the attribute level — so callers that need the type name of an *attribute value* reimplement it inline rather than reusing the helper.

**Existing function**

`py_type_name` — `crates/fltk-cst-core/src/cross_cdylib.rs:120–125`. It calls `obj.get_type().name()…` identically; only the receiver differs (`obj` vs `attr_val.get_type()`).

**Consequence**

The inline copies and `py_type_name` diverge if the fallback string or formatting changes. Three new copies were added in this commit alone; Phase 1–2 will introduce more sentinel-adjacent paths where the same pattern will likely be copied again. A single private helper (`fn py_attr_type_name(attr: &Bound<'_, PyAny>) -> String`) would subsume both `py_type_name` and all inline copies, eliminating the divergence point.

---

## reuse-2 — Duplicated ABI-pair-check sequence (`get_span_type` vs `extract_source_text` slow path)

**Files:lines**

- `crates/fltk-cst-core/src/cross_cdylib.rs:241–285` (`get_span_type` GILOnceCell init — checks ABI string then layout on the canonical type)
- `crates/fltk-cst-core/src/cross_cdylib.rs:57–100` (`extract_source_text` slow path — same two-step check on the foreign object's type)

**What's duplicated**

Both blocks perform the identical logical sequence:
1. `getattr(_fltk_cst_core_abi)` → extract `&str` → compare to `FLTK_CST_CORE_ABI`, error on mismatch or non-str.
2. `getattr(_fltk_cst_core_abi_layout)` → extract `usize` → compare to local `size_of::<PyClassObject<T>>()`, error on mismatch or non-int.

The only variation is: (a) the type name in error messages (`"Span"` vs `"SourceText"`), (b) the `expected_layout` constant (monomorphised per type), and (c) the error-message prefix (attribute path vs `"expected fltk._native.SourceText:"`).

**Existing function**

No shared helper exists. The `get_span_type` block was added in this commit as a near-copy of the `extract_source_text` pattern introduced in the prior commit.

**Consequence**

The two blocks are already slightly inconsistent in error message wording (compare `"Span ABI mismatch: fltk._native.Span reports …"` vs `"SourceText ABI mismatch: object reports …"`). As Phase 1–2 land and further types potentially gain sentinel checks, the per-type boilerplate will multiply and the subtle wording divergences will compound. A generic helper — e.g. `fn check_abi_pair<T: PyClass>(ty: &Bound<'_, PyType>, type_label: &str) -> PyResult<()>` — would consolidate the logic and enforce uniform error messages.

---

# Reuse review — Phase 1 (handle/data split, Shared<T>, _native removal)

Commit reviewed: 47c28fd. Scope: Phase 1 only (Phases 2–4 deferred; missing Phase 2–4 work is not a finding).

---

## reuse-3 — `_eq_method` expands `Shared::PartialEq` inline instead of delegating to it

**Files:lines**

- Generator: `fltk/fegen/gsm2tree_rs.py:1058–1074` (`_eq_method`)
- All generated files: 14 copies in `src/cst_fegen.rs`, 14 in `tests/rust_cst_fegen/src/cst.rs`, 6 in `tests/rust_cst_fixture/src/cst.rs`, 3 in `crates/fltk-cst-spike/src/cst.rs` — 37 copies total.

Representative generated snippet (e.g. `src/cst_fegen.rs:548–555`):
```rust
if self.inner.ptr_eq(&other_handle.inner) {
    return Ok(true.into_pyobject(py)?.to_owned().unbind().into_any());
}
let eq = *self.inner.read() == *other_handle.inner.read();
```

**Existing function**

`Shared<T>::PartialEq` — `crates/fltk-cst-core/src/shared.rs:75–86`. Performs exactly the same sequence: `ptr_eq` short-circuit, then `*self.read() == *other.read()`. The generator could emit the single line:
```rust
let eq = self.inner == other_handle.inner;
```
and the impl would be identical in behavior.

**Consequence**

The correctness of the ptr_eq short-circuit (required to avoid same-lock RwLock re-entry) is now maintained in two places: `Shared::PartialEq` and the 37 generated `__eq__` bodies. Any change to the short-circuit logic — e.g., switching from `std::sync::RwLock` to `parking_lot` (which allows same-thread re-entrant reads) — must be applied to `Shared::PartialEq` AND the generator's `_eq_method`. In the current form, a developer who updates only `Shared` leaves every generated `__eq__` stale.

---

## reuse-4 — `Shared<T>` semantics tests duplicated across two crates with no unit tests in `fltk-cst-core`

**Files:lines**

- `crates/fltk-cst-spike/src/spike_tests.rs:290–341` — `shared_clone_is_shallow`, `shared_self_eq_no_deadlock`, `mutation_propagates_through_parent`, `shared_children_share_identity_after_push_child`
- `tests/rust_cst_fixture/src/native_tests.rs:73–151` — `clone_is_shallow_mutation_visible_through_clone`, `shared_self_eq_no_deadlock`, `mutation_propagates_through_shared_child`, `shared_child_in_two_parents_is_ptr_eq`, `shared_deep_eq_distinct_allocations`

**Existing function**

`Shared<T>` itself — `crates/fltk-cst-core/src/shared.rs`. The type has no `#[cfg(test)]` block. The behaviors under test (`Clone` shallow semantics, `PartialEq` ptr_eq short-circuit, write visibility through clones) are properties of `Shared<T>` alone, not of any particular generated node struct.

**Consequence**

Every new generated-code crate that writes integration-style tests is likely to add a third copy. The two existing copies already diverge: `spike_tests.rs` lacks `shared_deep_eq_distinct_allocations`; `native_tests.rs` lacks an explicit `shared_children_share_identity_after_push_child` name match. Moving these tests into a `#[cfg(test)]` module in `shared.rs` (or a dedicated `crates/fltk-cst-core/src/shared_tests.rs`) would make `fltk-cst-core` the canonical test location and eliminate duplication pressure on downstream crates.

---

# Reuse review — Phase 2 (idiomatic native Rust CST surface)

Commit reviewed: fb8852f. Scope: Phase 2 only.

---

## reuse-5 — `child_<lbl>` generator body duplicated across `single_node_cls` and `&Span` branches

**File:line:** `fltk/fegen/gsm2tree_rs.py:1158–1196` (`_native_per_label_methods`, `child_<lbl>` section)

The `if single_node_cls:` branch (lines 1158–1177) and the `elif ref_type == "&Span":` branch (lines 1178–1196) emit structurally identical Rust code. Both produce:

1. `let matching: Vec<_> = self.children.iter().filter(…).collect();`
2. `if matching.len() != 1 { return Err(CstError::ChildCount { label, expected: "1", found: … }); }`
3. `match &matching[0].1 { <variant>(s) => Ok(s), [_ => UnexpectedChildType] }`

The sole variation is the child-enum match arm variant name: `{enum_name}::{single_node_cls}(s)` vs `{enum_name}::Span(s)`. The `_label_type_info` helper (line 1036) already knows the match-arm variant as a string and could thread it into a shared `_emit_child_one_body(…, match_variant: str, need_unexpected_arm: bool)` helper.

**Consequence:** A structural change to the collect-check-match pattern (e.g. avoiding the `Vec` allocation, adding a new `CstError` variant) must be applied to both branches independently; divergence accumulates silently.

---

## reuse-6 — `maybe_<lbl>` generator body duplicated across `single_node_cls` and `&Span` branches

**File:line:** `fltk/fegen/gsm2tree_rs.py:1223–1262` (`_native_per_label_methods`, `maybe_<lbl>` section)

Identical structural duplication as reuse-5. The `if single_node_cls:` branch (lines 1223–1242) and `elif ref_type == "&Span":` branch (lines 1243–1262) emit:

1. `let matching: Vec<_> = self.children.iter().filter(…).collect();`
2. `if matching.len() > 1 { return Err(CstError::ChildCount { expected: "0 or 1", … }); }`
3. `match matching.first() { None => Ok(None), Some((_, <variant>(s))) => Ok(Some(s)), [Some(_) => UnexpectedChildType] }`

Only the match arm variant name differs.

**Consequence:** Same as reuse-5; additionally, if `child_<lbl>` and `maybe_<lbl>` are refactored together into a shared body helper, the two remaining branches in `maybe_<lbl>` (node vs span) would also collapse, reducing the surface area that must stay synchronized.

---

## reuse-7 — `children_<lbl>` iterator body duplicated across `single_node_cls` and `&Span` branches

**File:line:** `fltk/fegen/gsm2tree_rs.py:1101–1141` (`_native_per_label_methods`, `children_<lbl>` section)

The `if single_node_cls:` branch (lines 1101–1122) and the `elif ref_type == "&Span":` branch (lines 1123–1141) both emit:

```
self.children.iter()
    .filter(|(lbl, _)| *lbl == Some({label_enum_name}::{rust_variant}))
    [.filter_map(|(_, child)| match child { <Variant>(s) => Some(s), _ => None, })
     | .map(|(_, child)| match child { <Variant>(s) => s })]
```

The `need_wildcard` conditional selecting between `filter_map` and `map` (to satisfy `clippy::unnecessary_filter_map`) is identical in both branches; only the child enum variant name in the match arm differs. The docstring follows the same template with different type names.

**Consequence:** The clippy-appeasing `filter_map`/`map` selection and any future change to the iterator chain (e.g. adding lifetime annotations, switching to `flat_map`) must be applied in both branches. The two branches already diverge in the first docstring line (`"Return an iterator over \`Shared<X>\` children…"` vs `"Return an iterator over \`Span\` children…"`) but the body is currently identical — that symmetry is not enforced by the code structure.

---

## reuse-8 — `TODO(rust-cst-accessor-clone-efficiency)` scope omits native `child_<lbl>` / `maybe_<lbl>` methods that have the same O(n) allocation

**File:line:** `fltk/fegen/gsm2tree_rs.py:1386, 1409, 1439` (TODO comments in `_per_label_methods`); `fltk/fegen/gsm2tree_rs.py:1162–1164, 1181–1183, 1226–1228, 1245–1247` (native methods with the same pattern, no TODO)

The existing `TODO(rust-cst-accessor-clone-efficiency)` tracks the O(n) Vec-clone in Python bridge methods (`_per_label_methods`). The native (GIL-free) `child_<lbl>` and `maybe_<lbl>` generated by `_native_per_label_methods` use a structurally identical `let matching: Vec<_> = self.children.iter().filter(…).collect()` pattern without a corresponding TODO. The `PyIdentifier::child` pymethod in the spike (added this phase, `crates/fltk-cst-spike/src/cst.rs` ~line 497) also carries the TODO comment, but the spike's native `child_name` / `maybe_name` methods (lines 230–285 in the spike) do not.

**Consequence:** When `TODO(rust-cst-accessor-clone-efficiency)` is resolved, the fix will be applied only to the Python bridge methods it annotates. The native accessor methods — which are the primary Rust API surface — will remain on the O(n) path. The fix in both contexts is the same: check `len` under the read guard and clone only the matching entry rather than the full Vec.
