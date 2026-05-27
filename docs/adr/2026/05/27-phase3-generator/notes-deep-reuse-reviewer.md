Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

Commit reviewed: af7dc6e

---

## reuse-1

**File**: `fltk/fegen/gsm2tree_rs.py:16-18`

**What's duplicated**: `_rust_variant_name` is `"".join(part.capitalize() for part in label.split("_"))` — identical to `CstGenerator.class_name_for_rule_node` (`fltk/fegen/gsm2tree.py:46-47`): `"".join(part.capitalize() for part in rule_name.lower().split("_"))`. The `.lower()` difference is immaterial for labels, which are already lowercase by grammar invariant. The new code adds a free function instead of reusing (or extracting) the existing method.

**Existing**: `CstGenerator.class_name_for_rule_node` at `fltk/fegen/gsm2tree.py:46-47`.

**Consequence**: Four independent definitions of the same transform now exist (see reuse-2, reuse-3). Any change to capitalization behavior — digits, consecutive underscores, leading underscores — must be applied in all four places separately.

---

## reuse-2

**File**: `fltk/unparse/gsm2unparser.py:638-639`

**What's duplicated**: `UnparserGenerator.class_name_for_rule_node` is a verbatim copy of `CstGenerator.class_name_for_rule_node` (`fltk/fegen/gsm2tree.py:46-47`): same body, same name, same purpose. Pre-dates this diff; this diff adds a third variant rather than extracting a shared helper.

**Existing**: `CstGenerator.class_name_for_rule_node` at `fltk/fegen/gsm2tree.py:46-47`.

**Consequence**: Bug fixes or behavioral changes to the transform require locating all copies manually. There is no canonical location.

---

## reuse-3

**File**: `fltk/unparse/gsm2unparser.py:1888`

**What's duplicated**: Inline list-comp `["".join(part.capitalize() for part in rule_name.lower().split("_")) for rule_name in rule_names]` — fourth copy of the same transform, not behind a named function.

**Existing**: `CstGenerator.class_name_for_rule_node` at `fltk/fegen/gsm2tree.py:46-47`.

**Consequence**: Same as reuse-2. Divergence risk is higher because the logic is inline rather than named; a reader searching for all transform sites can miss it.

---

## Remediation

Extract `def rule_name_to_class_name(rule_name: str) -> str` as a module-level function in `fltk/fegen/gsm2tree.py` (or a new `fltk/fegen/naming.py`). Replace all four sites. `_rust_variant_name` becomes a thin call to it (without `.lower()` guard, or with — the behavior is identical for valid label names).
