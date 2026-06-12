# Reuse review — commit range d2abc80..4f66083

## reuse-1

**File:line** `fltk/fegen/gsm2tree_rs.py:727` and `:757` and `:2186`

**What's duplicated** Inline `f"Py{child_cls}"` / `f"Py{class_name}"` string construction appears three times in `_child_enum_block` (lines 727, 757) and `_register_classes_fn` (line 2186) after `py_handle_name` was introduced as the single source of truth at line 605.

**Existing function** `RustCstGenerator.py_handle_name` — `fltk/fegen/gsm2tree_rs.py:605`.

**Consequence** The diff itself introduces the consolidation at the `_node_block` call site (line 805) and in the cross-rule claims check (line 140), but leaves three prior emission sites still inlining the formula. If the naming scheme changes (e.g., prefix changes from `Py` to something else), these three sites will diverge from the declared single source of truth and silently produce mismatched handle names in the emitted Rust.

---

## reuse-2

**File:line** `tests/test_gsm2tree_rs.py:1542–1560`

**What's duplicated** `_make_single_rule_grammar(rule_name)` constructs a single labeled rule (label `"value"`, regex `[a-z]+`, NO_WS). `_make_two_rule_grammar` (lines 1619–1647, added in this diff) contains an identical inner helper `_make_rule` that produces the same structure, and `_make_single_rule_grammar` itself is just the one-rule specialization of that inner helper.

**Existing function** `_make_single_rule_grammar` — `tests/test_gsm2tree_rs.py:1542`. Alternatively, `make_labeled_grammar` in `tests/gsm2tree_helpers.py:46` constructs a single labeled-regex rule of the same shape (different fixed name `"bar"`, label `"name"`).

**Consequence** `_make_two_rule_grammar`'s inner `_make_rule` and `_make_single_rule_grammar` produce structurally identical rules. Any future change to the canonical minimal-rule shape (e.g., adding a quantifier, changing the regex) must be applied in both places independently or the two test families silently drift. The simpler fix is to implement `_make_two_rule_grammar` by calling `_make_single_rule_grammar` for each rule, eliminating the inner duplicate entirely.
