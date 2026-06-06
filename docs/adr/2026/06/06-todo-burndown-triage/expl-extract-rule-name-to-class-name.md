# TODO Burndown: extract-rule-name-to-class-name

Adversarial verification of TODO slug `extract-rule-name-to-class-name` against actual code as of 2026-06-06.

## Claim vs. Reality

### File locations

The TODO comment cites `gsm2unparser.py` inside `fltk/fegen/`. That path does not exist.
The actual file is `fltk/unparse/gsm2unparser.py` (1894 lines). The cited line numbers (638, 1888) resolve correctly in the actual path.

### Four copies: do they exist?

Yes, all four implementations exist:

1. `fltk/fegen/gsm2tree.py:46-47` — `CstGenerator.class_name_for_rule_node`:
   ```python
   def class_name_for_rule_node(self, rule_name: str) -> str:
       return "".join(part.capitalize() for part in rule_name.lower().split("_"))
   ```

2. `fltk/unparse/gsm2unparser.py:638-639` — `UnparserGenerator.class_name_for_rule_node`:
   ```python
   def class_name_for_rule_node(self, rule_name: str) -> str:
       return "".join(part.capitalize() for part in rule_name.lower().split("_"))
   ```

3. `fltk/unparse/gsm2unparser.py:1888` — inline list-comp (module-level function):
   ```python
   class_names = ["".join(part.capitalize() for part in rule_name.lower().split("_")) for rule_name in rule_names]
   ```

4. `fltk/fegen/gsm2tree_rs.py:25-27` — `_rust_variant_name`:
   ```python
   def _rust_variant_name(label: str) -> str:
       """Label -> CamelCase Rust enum variant. 'no_ws' -> 'NoWs'."""
       return "".join(part.capitalize() for part in label.split("_"))
   ```

The TODO comment is embedded at `gsm2tree_rs.py:18-22` and cites the wrong path for gsm2unparser.py but the line numbers are correct for the actual path.

### Behavioral identity

Copies 1, 2, 3 are **byte-for-byte identical** in the transform expression: `rule_name.lower().split("_")` then `capitalize` each part then join.

Copy 4 (`_rust_variant_name`) differs by **omitting `.lower()`** on the input. Consequence: if a label contains uppercase letters, copies 1-3 normalize to lowercase first, then capitalize the first letter of each segment; copy 4 preserves uppercase mid-segment (e.g. `"MixedLabel"` → copy 1-3: `"Mixedlabel"`, copy 4: `"MixedLabel"`). In practice grammar rule names are lowercase snake_case (enforced by the identifier grammar at `fltk/fegen/fegen.fltkg`), so this divergence has no current observable effect on rule-name inputs. For label inputs (which `_rust_variant_name` processes), the same constraint applies.

### Edge case behavior (all four, same result for valid inputs)

- Consecutive underscores (`a__b`): empty-string segments from `split("_")` produce empty-string after `capitalize()`, so consecutive underscores are silently collapsed — `"a__b"` → `"AB"`.
- Leading underscore (`_foo`): leading empty segment collapses — `"_foo_bar"` → `"FooBar"`.
- Trailing underscore (`foo_`): trailing empty segment collapses — `"foo_"` → `"Foo"`.
- Digits mid-segment (`rule1_test`): `capitalize()` on `"rule1"` gives `"Rule1"` (digits don't affect it). `"a1b2c3"` → `"A1b2c3"`.
- Digit-starting segment (`"1starts"`): `capitalize()` gives `"1starts"` (no change when first char is non-alpha). A rule name starting with a digit is not a valid identifier per the grammar.

All four copies have identical edge-case behavior on valid grammar inputs.

### Proposed fix shape: is it feasible?

Yes. Extracting to a shared helper in `fltk/fegen/gsm2tree.py` or a new `fltk/fegen/naming.py` is mechanically straightforward.

**Coupling note**: `gsm2tree_rs.py` already imports from `fltk.fegen.gsm2tree` (`from fltk.fegen.gsm2tree import CstGenerator` at line 12), so a helper placed in `gsm2tree.py` introduces no new import edge for `gsm2tree_rs.py`.

`fltk/unparse/gsm2unparser.py` does not currently import from `fltk.fegen.gsm2tree`. A helper in `gsm2tree.py` would add a new cross-package import (`fltk.unparse` → `fltk.fegen`). A helper in a new `fltk/fegen/naming.py` would be a cleaner boundary; `gsm2tree.py` and `gsm2tree_rs.py` could also import from there rather than the reverse.

### Blockers

None structural. The `_rust_variant_name` function omits `.lower()` — a shared helper must decide which behavior is canonical. Since all call sites currently pass lowercase-only inputs, either form is safe, but they must match.

### Is this papering over a deeper problem?

No. The duplication is purely mechanical — four independent reimplementations of the same one-liner that drifted apart only in the `.lower()` detail. There is no design flaw being masked.

## Summary of Discrepancies in TODO Claim

| Claim | Actual |
|---|---|
| `gsm2unparser.py` in `fltk/fegen/` | File is at `fltk/unparse/gsm2unparser.py` |
| Line 638 for `UnparserGenerator.class_name_for_rule_node` | Correct (wrong directory, right line) |
| Line 1888 for inline list-comp | Correct (wrong directory, right line) |
| "four independent copies" | Confirmed: four copies exist |
| Behavioral identity (digit handling, consecutive underscores) | Copies 1-3 identical; copy 4 omits `.lower()` — diverges only on uppercase input, which does not occur in practice |
| `gsm2tree_rs.py:18` as location of TODO comment | Correct: comment is at lines 18-22 |
