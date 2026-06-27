## reuse-1

**File:line:** `fltk/unparse/gsm2unparser_rs.py:447–480` (`_item_anchor_config`)

**What's duplicated:** The per-item anchor-config lookup — try the LABEL selector first; for "before" fall back to LITERAL when LABEL yields nothing; for "after" use LABEL-only for labeled items and LITERAL for unlabeled ones — is already expressed in three other places:

- `fltk/unparse/gsm2unparser.py:1480–1486` — "before" path inlined inside `_gen_anchor_operations_before_item`
- `fltk/unparse/gsm2unparser.py:1525–1530` — "after" path inlined inside `_gen_anchor_operations_after_item`
- `fltk/unparse/fmt_config.py:289–298` — `FormatterConfig._get_spacing` implements the same LABEL-then-LITERAL chain for both positions (minus the "after" asymmetry)
- `fltk/unparse/fmt_config.py:341–349` — `FormatterConfig.get_item_disposition` repeats the same "before" LABEL-then-LITERAL chain

**Existing function/utility:** `FormatterConfig._get_spacing` (`fmt_config.py:289`) and `FormatterConfig.get_item_disposition` (`fmt_config.py:341`).

**Consequence:** The new `_item_anchor_config` correctly extracts the lookup into a helper, but the helper lives in the Rust generator rather than in `FormatterConfig` where both backends share it. The lookup pattern will now drift in three independent places: the Python backend's two inline copies, `FormatterConfig._get_spacing`/`get_item_disposition`, and the Rust `_item_anchor_config`. A `FormatterConfig.get_item_anchor_config(rule_name, item, position)` method would unify all four sites and make the before/after selector asymmetry a single, tested definition.

---

## reuse-2

**File:line:** `tests/test_rust_unparser_generator.py:1428–1437` (`_disposition_config`)

**What's duplicated:** `_disposition_config` builds a `FormatterConfig` with a single `before:label:{selector_value}` `AnchorConfig` entry. `_anchor_op_config` (introduced in the same diff at line 1214) does almost exactly the same thing — `FormatterConfig()` + `anchor_configs[key] = AnchorConfig(...)` — but takes `(position, selector_type, selector_value, operations)` tuples and omits `disposition`.

**Existing function/utility:** `_anchor_op_config` (`tests/test_rust_unparser_generator.py:1214`).

**Consequence:** Both helpers share the identical `FormatterConfig()` + dict-key construction pattern. `_disposition_config` could call `_anchor_op_config` if `_anchor_op_config` accepted an optional `disposition` per entry, but as written neither delegates to the other. The two will diverge independently if the key format or `AnchorConfig` constructor signature changes.
