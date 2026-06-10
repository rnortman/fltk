## slop-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py` — `_label_from_pyobject_match` now takes a `method_name: str` parameter (default `"append"` to preserve existing call sites that don't override); `_generic_extend` passes `method_name="extend"`. Error strings at the two call sites now read `{class_name}.extend:` when emitted by the extend method. Regenerated `crates/fltk-cst-spike/src/cst.rs`, `src/cst_generated.rs`, `src/cst_fegen.rs`, and `tests/rust_cst_fixture/src/cst.rs` with `make fix` applied.
- Severity assessment: Diagnostic error messages named the wrong method; downstream consumers debugging label-type errors from `extend` calls would see a misleading `append` attribution. Low urgency but ships incorrect diagnostics.

---

## slop-2

- Disposition: Fixed
- Action: `fltk/fegen/gsm2tree_rs.py` — removed the three-line `// Return a fltk._native.Span...` comment block from the `_span_method` (or equivalent) template emitting the `span` getter, and removed the two-line `// span_to_pyobject: O(1) Arc clone...` comment from the `to_pyobject` Span arm template. Regenerated all four generated files; `make fix` applied.
- Severity assessment: Purely cosmetic; repeated boilerplate comments are noise in diffs and code review. No behavioral effect.

---

## slop-3

- Disposition: Fixed
- Action: `crates/fltk-cst-core/src/lib.rs:58` — replaced `// --- Native Span API tests (§4 item 2 from design) ---` with `// Tests for the native (non-Python) Span API`. Also updated the nearby comment at line 13 from `// §4 item 1 (Span portion): ...` to `// Pure-Rust GIL-free Span construction and equality tests.` for consistency.
- Severity assessment: Comments referencing external design document sections age poorly and read as scaffolding. No behavioral effect.
