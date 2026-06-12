Concise. Precise. Complete. Unambiguous. No padding.

## quality-1

**File:line**: `fltk/fegen/gsm.py:339-355` (`validate_no_repeated_nil_items`)

**Issue**: The validator iterates only the top-level `alternative.items` of each rule. It does not recurse into sub-expressions (`Sequence[Items]` terms). A grammar like `rule := outer:( (r"a*".)+  )` — where the MULTIPLE item lives inside a sub-expression rather than directly in the rule's alternative — passes validation undetected. The bug path exists: `term_can_be_nil` correctly handles `Sequence` (returns True if any alternative can be nil), but `validate_no_repeated_nil_items` calls `term_can_be_nil(item.term, grammar)` only for items it visits — and it only visits items at one level of depth. Sub-expression items with `is_multiple()` are never visited.

**Consequence**: The validator gap partially survives the fix. Crafted grammars can still produce infinite-looping parsers at runtime by nesting the MULTIPLE+nullable combination inside a sub-expression. The loop guard is defense-in-depth, but the stated goal is validator rejection. Future grammar authors or grammar-generating tools will produce sub-expression forms routinely; the validator silently permits them.

**Fix**: Make `validate_no_repeated_nil_items` recurse into sub-expressions. Add a helper that validates an `Items` sequence and dispatches into sub-expressions when a term is `Sequence[Items]`:

```python
def _validate_items(items: Items, grammar: Grammar, rule_name: str, errors: list[str]) -> None:
    for item_idx, item in enumerate(items.items):
        if item.quantifier.is_multiple():
            if term_can_be_nil(item.term, grammar):
                errors.append(...)
        # Recurse into sub-expressions regardless of quantifier
        if isinstance(item.term, Sequence):
            for alt in item.term:
                _validate_items(alt, grammar, rule_name, errors)
```

Call this from `validate_no_repeated_nil_items` instead of the current flat loop.

---

## quality-2

**File:line**: `fltk/fegen/gsm2parser.py:568`, `fltk/fegen/gsm2parser.py:577`

**Issue**: `one_result_ref` is introduced as a named local variable used only in the guard condition (lines 568-574), while all subsequent references to `one_result` use fresh `loop.block.get_leaf_scope().lookup_as("one_result", iir.Var)` inline calls (lines 577, 582, 589). This inconsistency is cosmetic in current code but creates a maintenance hazard: future readers must determine whether the named variable and the inline lookups produce the same object or different ones. The lookup is idempotent (same scope, same name → same result), but this is non-obvious without reading `Scope.lookup_as`.

**Consequence**: Low immediate impact, but the naming inconsistency will propagate to anyone adding a new reference to `one_result` inside this function: they have three existing patterns to choose from (named var, inline lookup without `_mut`, inline lookup with `load_mut`), making the correct choice unclear.

**Fix**: Either use `one_result_ref` consistently for all accesses in the loop body, or remove it and inline the lookup in the guard as the other usages do. Consistent inline is the simpler path (matches the pattern used at 577, 582, 589):

```python
loop.block.if_(
    condition=iir.Equals(
        lhs=loop.block.get_leaf_scope().lookup_as("one_result", iir.Var).load().fld.pos.load(),
        rhs=result.get_param("pos").load(),
    ),
).block.break_()
```

Or promote all four usages to `one_result_ref`.
