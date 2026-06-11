# Exploration: nullable-loop TODO adversarial validation

Concise. Precise. Token-dense — no fluff, full information. No preamble. No padding.

---

## Claim under review

> `_gen_item_multiple` emits a `while let` loop with no per-iteration progress guard. For a
> grammar where the repeated term can match empty at a fixed position, the loop never advances
> and runs forever. This deliberately mirrors the Python backend for cross-backend parity, but
> both backends should add `if one_result.pos == pos { break; }` in lockstep.

---

## 1. Loop code — what is actually emitted

**`gsm2parser_rs.py:674-694`** (`_gen_item_multiple`):

```python
lines.append("        while let Some(one_result) = {")
lines.append(f"            {consume_expr}")
lines.append("        } {")
lines.append("            pos = one_result.pos;")
...
lines.append("        }")
```

The `TODO(nullable-loop)` comment is at line 669–673 of `gsm2parser_rs.py`. There is **no** `if one_result.pos == pos { break; }` guard.

**`gsm2parser.py:555-603`** (`gen_item_parser_multiple`):

```python
loop = result.block.while_(
    condition=consume_term.expr,
    let=iir.Var(name="one_result", ...),
)
loop.block.assign(
    target=result.get_param("pos").store(),
    expr=loop.block.get_leaf_scope().lookup_as("one_result", iir.Var).load_mut().fld.pos.move(),
)
```

No progress guard is emitted. The Python backend generates `while (one_result := <consume_term_expr>) is not None: pos = one_result.pos; ...` with no `if pos_unchanged: break`.

Both claims in the TODO are factually correct about the absence of a guard.

---

## 2. Is the infinite loop actually reachable?

**`gsm.py:340-356`** (`validate_no_repeated_nil_items`):

```python
def validate_no_repeated_nil_items(grammar: Grammar) -> None:
    for rule in grammar.rules:
        for alt_idx, alternative in enumerate(rule.alternatives):
            for item_idx, item in enumerate(alternative.items):
                if item.quantifier.is_multiple():  # + or *
                    if term_can_be_nil(item.term, grammar):
                        errors.append(...)
    if errors:
        raise ValueError("Repeated potentially-nil items found:\n" + ...)
```

This validation is called at `gsm.py:299` from `classify_trivia_rules`. The Rust path calls `classify_trivia_rules` via:

- `gsm2tree_rs.py:48`: `grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))`
- `gsm2parser_rs.py:82`: `self._cst = RustCstGenerator(grammar)` — `RustCstGenerator.__init__` calls `classify_trivia_rules` at `gsm2tree_rs.py:48`

The Python path calls it directly: `gsm2parser.py:33`: `grammar = gsm.classify_trivia_rules(grammar)`.

**`term_can_be_nil`** (`gsm.py:166-173`) checks:
- `Identifier`: delegates to `Rule.can_be_nil` → checks all alternatives recursively
- `Literal`: nil only if `value == ""`
- `Regex`: actually calls `re.compile(pattern).match("") is not None`
- `Sequence[Items]` (parenthesized sub-expression): nil if ANY alternative `Items.can_be_nil`

**`Item.can_be_nil`** (`gsm.py:108-111`):
```python
def can_be_nil(self, grammar: "Grammar") -> bool:
    return self.quantifier.is_optional()
```
This ignores the term entirely — an item is considered nil iff its quantifier allows zero matches.

**`Items.can_be_nil`** (`gsm.py:77-98`): an alternative `Items` is nil if ALL items are nil (quantifier-only check) AND all separators are nil.

**Critical subtlety**: `term_can_be_nil` checks the term directly, while `Items.can_be_nil` checks items via `Item.can_be_nil` which ignores the term. So for a repeated sub-expression (parenthesized alternatives), the check path is:

```
item.quantifier.is_multiple() → True
term_can_be_nil(item.term, grammar) where item.term is Sequence[Items]
  → any(items.can_be_nil(grammar) for items in term)
  → Items.can_be_nil checks item.can_be_nil for each inner item
  → Item.can_be_nil returns self.quantifier.is_optional()
```

So a sub-expression `(a? | b?)` where ALL inner alternatives consist solely of optional items would be detected as nullable and rejected. An alternative `(a? b?)` (one alternative, both items optional) would also be detected: `Items.can_be_nil` returns True since all items satisfy `quantifier.is_optional()`.

**Conclusion**: The validation at `gsm.py:340-356` catches nullable terms **at the item level only** (not deeply: it examines direct items of each alternative). For a sub-expression term `[Items(...)]`, it correctly recurses into the alternatives' items via `Items.can_be_nil`. The validation **does** reach the specific case the TODO describes ("an inner alternative whose items are all optional").

**However**, the validation is only called from `classify_trivia_rules` (`gsm.py:299`). Code that constructs a `Grammar` object directly and passes it to `ParserGenerator` or `RustParserGenerator` **without** calling `classify_trivia_rules` (or calling it but then mutating grammar objects) would bypass validation. There is no enforcement that validated grammars are the only ones that flow into the generators.

---

## 3. Does the `Item.can_be_nil` ignore-term design cause a gap?

`Item.can_be_nil` returns `self.quantifier.is_optional()` regardless of the term (`gsm.py:108-111`). This means `Items.can_be_nil` (used by `term_can_be_nil` for sub-expressions) **cannot detect** the case where a sub-expression item is required (`quantifier=REQUIRED`) but its term (e.g. a `Regex(r"a*")`) can match empty. Such an item would be `Item.can_be_nil → False` even though the regex matches empty.

Concrete gap: the grammar `rule := (a* .)+` where `a*` has `quantifier=REQUIRED` — `Item.can_be_nil` returns False (required), so `Items.can_be_nil` returns False, so `term_can_be_nil` returns False, so `validate_no_repeated_nil_items` does NOT reject it. But at parse time, `consume_regex(pos, r"a*")` returns `ApplyResult { pos: pos, result: span }` (zero-length match) on every iteration, causing the infinite loop.

This gap exists for all term types that can match empty but are wrapped in `quantifier=REQUIRED`: regexes with `*`/`?`/`{0,...}`, empty literals `""`, and referenced rules that can themselves be nil.

For `Identifier` terms: `Identifier.can_be_nil` does check if the referenced rule can be nil (`gsm.py:118-121`). But `Item.can_be_nil` ignores it — only `term_can_be_nil(item.term, ...)` in `validate_no_repeated_nil_items` sees the term directly, bypassing `Item.can_be_nil`.

The validation at `validate_no_repeated_nil_items` correctly uses `term_can_be_nil(item.term, grammar)` (not `item.can_be_nil(grammar)`) — so it IS checking the term for the outer repeated item. This is the correct check. The gap via `Item.can_be_nil` only matters inside `Items.can_be_nil` when evaluating sub-expressions; but for the outer repeated item itself, the validator calls `term_can_be_nil` directly.

**Revised conclusion**: The outer-item check in `validate_no_repeated_nil_items` is correct — it calls `term_can_be_nil(item.term, grammar)` which properly checks the actual term's nullability. The gap is in sub-expressions: a sub-expression `(r"a*")` with inner `quantifier=REQUIRED` would not be caught because `Items.can_be_nil` calls `Item.can_be_nil` (which ignores the term), and `term_can_be_nil` is not used there.

**Concrete triggering grammar**:
```
rule := (r"a*" .)+
```
- outer item: `quantifier=ONE_OR_MORE`, term is `[Items(items=[Item(term=Regex(r"a*"), quantifier=REQUIRED)], sep_after=[NO_WS])]`
- `validate_no_repeated_nil_items`: `term_can_be_nil([Items(...)], grammar)` → `any(items.can_be_nil(grammar) for items in term)` → `Items.can_be_nil` → `item.can_be_nil(grammar)` for inner item → `Item.can_be_nil` → `REQUIRED.is_optional()` → **False**
- Validation passes. But at parse time, `Regex(r"a*")` matches empty → infinite loop.

This is a **real gap** in the validation. The TODO claim that the fix should be at the generator level is verified as necessary because validation does not fully close the window.

---

## 4. Python backend: same loop, same absence of guard

`gsm2parser.py:555-603` (`gen_item_parser_multiple`) emits the `while_` loop via IIR with no progress guard. The claim is correct: both backends are symmetric.

---

## 5. Proposed fix correctness: variable names and scope

**Rust backend** (`gsm2parser_rs.py:674-694`):

```
while let Some(one_result) = { consume_expr } {
    pos = one_result.pos;
    ...
}
```

The proposed guard `if one_result.pos == pos { break; }` is correct in principle. But: `pos` is updated on `gsm2parser_rs.py:677` (`pos = one_result.pos`). The guard must be checked **before** updating `pos`. The correct placement is:

```
while let Some(one_result) = { consume_expr } {
    if one_result.pos == pos { break; }
    pos = one_result.pos;
    ...
}
```

If placed after `pos = one_result.pos`, the condition `one_result.pos == pos` is always true (same value), breaking on every iteration. The TODO text says `if one_result.pos == pos { break; }` without specifying placement; the placement matters.

**Python backend** (`gsm2parser.py:563-566`):

The IIR `while_` loop exposes `loop.block`. At IIR level `loop.block.assign(target=result.get_param("pos").store(), expr=...)` is the first statement inside the loop body. A progress guard would need to be emitted as an `if` before that assignment:

```python
loop.block.if_(
    condition=iir.Equals(lhs=one_result_var.fld.pos.load(), rhs=result.get_param("pos").load()),
).block.return_(iir.Failure(...))  # or break
```

The IIR does not appear to have a `break` statement — checking `iir/model.py` would confirm. If IIR has no `break`, the Python backend fix would differ in form (early return on no-progress) from the Rust backend (break).

---

## 6. Would the fix change parse results for working grammars?

For any grammar where repeated items always advance position (which is all grammars the validator currently accepts in the non-gap cases), `one_result.pos != pos` on every iteration, and the break is never taken. The fix is **a no-op for currently-accepted grammars** where the term cannot be nil.

For grammars that slip through the validation gap (sub-expression with required-quantifier nullable inner term), the fix would terminate the loop rather than infinite-loop. Parse results would change from "hang" to "returns after zero iterations" — which may or may not be the semantically correct parse, but is strictly better than non-termination.

---

## 7. Blockers and parity comparator

The TODO text says "both backends should add the guard in lockstep." No parity comparator mechanism is present in the codebase (no cross-backend differential test harness found). Adding the guard to one backend and not the other would not break any existing test, but would create a correctness divergence for the gap case.

---

## 8. Summary of findings

| Claim | Verdict |
|---|---|
| Loop in `_gen_item_multiple` has no progress guard | **True** — `gsm2parser_rs.py:674-694` |
| Python backend has same loop with no guard | **True** — `gsm2parser.py:555-603` |
| Deliberately mirrors Python for parity | **True** — TODO comment `gsm2parser_rs.py:669-673` |
| Infinite loop reachable via "inner alternative with all optional items" | **Partially blocked**: `validate_no_repeated_nil_items` catches the all-optional-quantifier case. **Not blocked**: required-quantifier inner item with nullable term (e.g. `Regex(r"a*")` with `quantifier=REQUIRED` inside a sub-expression). |
| Validation (`validate_no_repeated_nil_items`) fully closes the window | **False** — `Items.can_be_nil` uses `Item.can_be_nil` which ignores the term; sub-expressions with required-but-nullable inner terms slip through. |
| Proposed `if one_result.pos == pos { break; }` is correct | **Placement-dependent** — must precede the `pos = one_result.pos` assignment at `gsm2parser_rs.py:677`; TODO text does not specify position. |
| Fix would change results for currently-working grammars | **No** — guard condition never triggers when term always advances. |
| IIR `break` availability for Python backend | **Unknown** — not checked; may require different fix form (early return instead of break). |
