## slop-1

**File:** `fltk/unparse/gsm2unparser_rs.py` — `_item_anchor_lines`, the `for op in anchor_config.operations` loop

**Quote:**
```python
if op.operation_type == OperationType.SPACING:
    continue
if op.operation_type == OperationType.GROUP_BEGIN:
    ...
elif op.operation_type == OperationType.NEST_BEGIN:
    ...
elif op.operation_type == OperationType.GROUP_END:
    ...
elif op.operation_type == OperationType.NEST_END:
    ...
elif op.operation_type == OperationType.JOIN_BEGIN:
    ...
elif op.operation_type == OperationType.JOIN_END:
    ...
```
(No `else` branch.)

**What's wrong:** Any `OperationType` value not in the handled set (e.g. `RULE_START`/`RULE_END`, mentioned in the same diff in the docstring for the rule-level path, or any future extension) silently produces no output — no exception, no warning, no lines. The push or pop is just omitted.

**Consequence:** A misconfigured item-level anchor (or a future op type applied to an item anchor) will silently corrupt the generated Rust (unbalanced push/pop stack) with no diagnostic. Silent data-loss bugs in code generators are the hardest kind to debug.

**Fix:** Add an `else: raise ValueError(f"Unsupported OperationType in item anchor: {op.operation_type!r}")` after the elif chain. `SPACING` is already explicitly skipped; everything else should either be handled or loud.

---

## slop-2

**File:** `fltk/unparse/gsm2unparser_rs.py` — `_gen_item_method` and `_gen_item_body`

**Quote (docstring of `_item_routes_to_quantified_loop`):**
> this single predicate keeps the body-routing and sibling-emission decisions from drifting

**Actual code in `_gen_item_body`:**
```python
if item.disposition == gsm.Disposition.SUPPRESS:
    return self._gen_suppressed_item_body(item)
if item.quantifier.is_multiple():        # <-- inline re-implementation, not the predicate
    return self._gen_quantified_loop_body(item_prefix, item)
```

**What's wrong:** The anti-drift guarantee stated in the docstring is not enforced. `_gen_item_body` has its own inline `item.quantifier.is_multiple()` check rather than calling `_item_routes_to_quantified_loop`. The predicate is only used in `_gen_item_method` (to decide whether to emit the `__inner` sibling). If the routing condition in `_gen_item_body` is ever changed (e.g. another disposition is excluded), `_item_routes_to_quantified_loop` won't automatically follow.

**Consequence:** The docstring promises single-source-of-truth for routing; the code silently violates it. A maintainer who reads the docstring and changes only the predicate will produce mismatched sibling emission vs. body routing — generating `__inner` methods for items that the body does not actually loop.

**Fix:** `_gen_item_body` should call `self._item_routes_to_quantified_loop(item)` for the branch guard instead of inlining the equivalent check. That makes the docstring's claim true.

---

## slop-3

**File:** `fltk/unparse/gsm2unparser_rs.py` — `_item_anchor_config`

**Quote:**
```python
if position == "before":
    ...
    return anchor_config
# position == "after"
if item.label:
```

**What's wrong:** The comment `# position == "after"` is a tautological annotation. The function's type signature is `position: Literal["before", "after"]`; after the `if position == "before"` block returns, the only remaining value is "after". The comment restates what the type system already asserts.

**Consequence:** LLM writing tell — a comment that explains the obvious rather than the intent. Reads as generated rather than authored.

**Fix:** Remove the comment, or replace it with something that carries meaning if the fallthrough is surprising (e.g. `# "after" path — no literal fallback for labeled items`).
