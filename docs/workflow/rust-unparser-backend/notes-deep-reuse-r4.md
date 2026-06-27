## reuse-1

**File:line**: `fltk/fegen/gsm2tree_rs.py:839` and `:1764`

**What's duplicated**: Both sites compute the total child-enum variant count by inlining `(1 if has_span else 0) + len(child_classes)` / `len(child_class_names) + (1 if has_span else 0)`, which is exactly what the new `num_child_variants` method (added at line 796 in this diff) computes. The new method's own docstring says it was created "so callers need not duplicate the len(child_classes) + has_span arithmetic over _child_variants_for_rule," yet two in-class sites were not updated to call it.

**Existing function/utility**: `RustCstGenerator.num_child_variants` — `fltk/fegen/gsm2tree_rs.py:796`

**Consequence**: The new method does not deliver the consolidation its docstring promises. Future arithmetic changes (e.g., a new child variant category) would require updating three places instead of one. The inline sites in `_child_enum_block` (line 839) and the label-accessor helper (line 1764) will drift independently from the public method.

---

## reuse-2

**File:line**: `fltk/unparse/gsm2unparser_rs.py:474–490` and `fltk/unparse/gsm2unparser.py:516–530`

**What's duplicated**: Three generation-time `RuntimeError` raises for required-suppressed items are textually duplicated across both backends: the regex message, the identifier message, and the unknown-term-type fallback message. The bodies are character-for-character identical after this diff (the Python backend had a typo "lable" corrected here to match the Rust backend spelling).

**Existing function/utility**: `UnparserGenerator._gen_suppressed_quantified_item_body` — `fltk/unparse/gsm2unparser.py:485`. This is the Python-backend analogue; there is no shared helper yet.

**Consequence**: The typo divergence ("lable" vs. "label") that this diff corrects is the direct result of maintaining duplicate message strings. A shared module-level helper (e.g., `_raise_required_suppressed_error(item)` in `fltk/unparse/gsm2unparser_rs.py` or a common utility) would make future message changes atomic across both backends.
