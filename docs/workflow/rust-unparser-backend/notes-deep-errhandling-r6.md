# Error-handling review — batch 6

Commit reviewed: ae90f84671cf03d4b6e2aeed244bab3df1b1d633

---

## errhandling-1

**File:line**: `fltk/unparse/gsm2unparser_rs.py:523`

**Broken error path**: `_item_anchor_lines`, `JOIN_BEGIN` branch — missing-separator guard raises `RuntimeError("JOIN_BEGIN operation missing required separator")` with no identifying context.

**Why**: `rule_name`, `position` ("before"/"after"), and `item` (label or term type) are all in scope at the raise site but are not included in the message. Two lines below, the `except ValueError` wrapper for an unsupported separator Doc correctly names rule/position/item. The missing-separator case — which is also a configuration error — gives an anonymous message.

Compare: line 209 in `_gen_rule_entry` has the same gap for the rule-level JOIN_BEGIN path, but that is pre-existing and not in the diff.

**Consequence**: When a `JOIN_BEGIN` operation is configured without a separator, on-call gets `RuntimeError: JOIN_BEGIN operation missing required separator` with no indication of which rule, which item, or which anchor position (`before`/`after`) triggered it. Diagnosing requires reading the stack trace all the way back through `_item_anchor_lines` and then cross-referencing `FormatterConfig` by hand.

**What must change**: Expand the message to match the pattern already used in the surrounding `except ValueError` clause:

```python
item_id = f"label={item.label!r}" if item.label else f"term={type(item.term).__name__}"
msg = (
    f"Rule {rule_name!r} {position}-anchor JOIN_BEGIN for {item_id} "
    f"is missing the required separator"
)
raise RuntimeError(msg)
```

---

## errhandling-2

**File:line**: `fltk/unparse/gsm2unparser_rs.py:403`

**Broken error path**: `_item_disposition_success_lines` — the exhaustiveness guard at the bottom is `assert isinstance(item_disposition, Normal)`, which Python strips under `python -O`.

**Why**: If a new disposition type is added (e.g., `ConditionalRenderAs`) that is not `Normal`, `Omit`, or `RenderAs`, the code reaches line 403. With assertions enabled it raises `AssertionError` (no context — rule/item/disposition type are lost). With `-O` the assert disappears entirely and execution falls through to the `return [f"{indent}acc = r.accumulator;", ...]` line, silently treating the unknown disposition as `Normal` and emitting incorrect Rust.

The codebase has an explicit, documented policy against using `assert` for internal routing invariants: `_gen_identifier_term_body`, `_gen_literal_term_body`, and `_gen_regex_term_body` all use `raise RuntimeError` specifically because `-O` strips `assert` ("Use an explicit raise (not assert, which `python -O` strips)").

**Consequence**: Under `python -O`, an unknown or misrouted disposition silently emits `acc = r.accumulator;` (Normal accumulator merge), corrupting the generated Rust in a way that is invisible at generation time and only caught later — if at all — during Rust compilation or at runtime.

**What must change**: Replace the `assert` with an explicit `raise` that survives `-O` and names the offending disposition, consistent with the codebase pattern:

```python
# Unreachable with the current Normal | Omit | RenderAs union, but use an explicit
# raise (not assert, which `python -O` strips) so an unknown disposition type
# fails loudly at generation time instead of silently emitting Normal-disposition Rust.
msg = (
    f"Internal error: unrecognized disposition type {type(item_disposition).__name__!r} "
    f"for rule {rule_name!r} item "
    f"{'label=' + repr(item.label) if item.label else 'term=' + type(item.term).__name__}"
)
raise RuntimeError(msg)
```
