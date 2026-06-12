Style: concise, precise, complete, unambiguous. No padding, no preamble.

## quality-1

**File:line:** `fltk/fegen/gsm2tree_rs.py:419` — `child_enum_name` placed inside the "Label enum" section (line 415-416 banner) rather than the "Child enum" section (line 513-514 banner).

**Issue:** The naming helper for the child value enum sits in the wrong section. The three label helpers — `_label_enum_rust_name`, `_label_enum_python_name`, `_label_enum_block` — all belong in "Label enum". `child_enum_name` belongs in "Child enum" alongside `_child_enum_block`.

**Consequence:** Future readers scanning for child-enum logic find it split across two sections (name derivation in "Label enum", block generation in "Child enum"). When the next naming helper is added — e.g. a `child_enum_variant_name` or a consuming-children helper — the wrong precedent encourages landing it in the same wrong section. Maintenance cost compounds as the class grows.

**Fix:** Move `child_enum_name` (lines 419-426) to just before `_child_enum_block` (currently line 517), i.e. right after the "Child enum" section banner at line 513-514. No behavior change; one relocation. The design placed it "adjacent to `_label_enum_rust_name`" citing the existing naming-helper block, but the child-enum section is the correct home.
