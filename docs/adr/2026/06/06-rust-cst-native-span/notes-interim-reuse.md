## reuse-1 — `_rust_variant_name` duplicates `CstGenerator.class_name_for_rule_node` and `UnparserGenerator.class_name_for_rule_node`

**File:line:** `fltk/fegen/gsm2tree_rs.py:25–27`

**What's duplicated:** `_rust_variant_name` applies the same underscore-to-CamelCase transform (`"".join(part.capitalize() for part in ...)`) that already exists verbatim in:
- `CstGenerator.class_name_for_rule_node` — `fltk/fegen/gsm2tree.py:47`
- `UnparserGenerator.class_name_for_rule_node` — `fltk/unparse/gsm2unparser.py:639`
- Inline list-comp — `fltk/unparse/gsm2unparser.py:1888`

The TODO comment at `gsm2tree_rs.py:18–22` already names this gap.

**Consequence:** Four independent copies of the same one-liner. If the transform ever needs to change (e.g., to handle digits, leading underscores, or reserved keywords), all four sites diverge independently.

---

## reuse-2 — `FLTK_NATIVE_SPAN_TYPE` init block copy-pasted 11 times in generated code

**File:line:** `fltk/fegen/gsm2tree_rs.py:501, 548, 573, 618, 664, 691, 709, 731, 753, 786` (and the preamble at line 161)

**What's duplicated:** The identical 6-line `get_or_try_init` block that loads `fltk._native.Span` into `FLTK_NATIVE_SPAN_TYPE` appears at the top of every method that needs a span type: `span` getter, `children`, `append`, `extend`, `child`, `children_<label>`, `child_<label>`, `maybe_<label>`, `append_<label>`, `extend_<label>`. The hand-written `src/cst_generated.rs` and `tests/rust_cst_fixture/src/cst.rs` contain the same repetition in the generated output.

**Existing pattern:** The `extract_span` free function (emitted once in the preamble, `gsm2tree_rs.py:153–179`) already encapsulates cross-cdylib span extraction into a single reusable helper. An analogous `fn get_native_span_type(py: Python<'_>) -> PyResult<Bound<'_, PyType>>` helper could be emitted once and called everywhere, eliminating 10 duplicate blocks per generated file.

**Consequence:** Any change to the import path, the downcast, or the cache strategy requires editing the generator template in 11 places and re-verifying all callers. The current pattern also prevents any future migration to `fltk-cst-core` exposing this helper (each call site is self-contained with no seam to redirect).
