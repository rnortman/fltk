Concise. Precise. Complete. Unambiguous. No padding.

---

errhandling-1

File: fltk/fegen/gsm.py:339-355 (`validate_no_repeated_nil_items`)

Path: Validator scans only `alternative.items` at one level of depth. A repeated item whose term is a non-sub-expression (Identifier, Literal, Regex) is handled. But a grammar with a REQUIRED outer item that wraps a sub-expression containing a `+`/`*` item with a nullable term is never examined by the validator's loop — the inner `+` item lives inside `Sequence[Items]` and the validator never recurses into it.

Why: The loop iterates `alternative.items`; for an item whose `quantifier` is `REQUIRED` (not `is_multiple()`), the item is skipped entirely. The sub-expression inside is never visited. Confirmed empirically: `rule := (r"a*"+)` with a REQUIRED outer item passes `validate_no_repeated_nil_items` cleanly.

Consequence: A grammar author who writes `rule := (nullable_repeat)+something` where the outer `+` wraps an atomic identifier (not a sub-expression) but a nested sub-expression in another item path contains a `+`/`*` over a nullable term will pass validation. The parse-time loop guard (§2.2/§2.3) catches it at runtime and terminates cleanly (confirmed above), so the failure mode is degraded parse output (loop exits immediately; `+` post-loop check returns None) rather than a hang. No silent corruption. On-call can diagnose from the parse failure, but the grammar author gets no design-time error pointing to the problematic nested item. The validator's stated invariant (no repeated-nil items anywhere in the grammar) is not enforced for items nested more than one sub-expression level below a non-multiple outer item.

What must change: `validate_no_repeated_nil_items` must recurse into sub-expression terms. When `item.term` is `Sequence[Items]`, recurse into each `Items.items` list and apply the same `is_multiple()` + `term_can_be_nil` check, continuing recursively for any further nested sub-expressions. The fix is purely additive (more errors reported, never fewer), and is bounded (sub-expression nesting is finite). The loop guard remains correct defense-in-depth regardless.

---

No other findings. The core changes are correct:

- `Item.can_be_nil`: the `term_can_be_nil` delegation is sound; recursion terminates via `Rule._computing_nil` for cycles and finite nesting for sub-expressions.
- Python loop guard (`gsm2parser.py:564-574`): placement before `pos` update is correct; `one_result_ref` is looked up from `loop.block.get_leaf_scope()` which holds the `while_` let-binding — same scope used by subsequent `lookup_as` calls for `pos` move and `result` append, consistent with the pre-existing pattern.
- `Block.break_()` (`iir/model.py:203-205`): identical pattern to `return_()`, compiler already lowers `Break` to `ast.Break()` at line 218-220.
- Rust guard (`gsm2parser_rs.py:708`): literal string insertion is load-bearing-placement correct.
- `Regex._test_regex_empty` silent-False on `re.error` (`gsm.py:151-153`): pre-existing, correct under-approximation (invalid regex fails at compile time before any loop runs).
- Subprocess monkeypatching in tests assigns `lambda _: None` to `gsm.validate_no_repeated_nil_items` and restores via `finally` — correct isolation; no error path leaves the monkeypatch live.
