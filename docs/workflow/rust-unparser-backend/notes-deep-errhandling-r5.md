## errhandling-1

**File:line**: `fltk/unparse/gsm2unparser_rs.py`, `_item_spacing_lines`, line ~349

**Broken error path**: `_doc_to_rust_expr(spacing)` raises `ValueError("Unknown Doc type: ...")` for
unsupported Doc types — `Group`, `Nest`, `Join`, and `Comment` are all producible from a `.fltkfmt`
file (via `group(...)`, `nest(...)`, `join(...)` combinators in a spacing context, routed through
`_doc_literal_cst_to_doc`).  The call is unguarded:

```python
spec_expr = f"fltk_unparser_core::{ctor}({self._doc_to_rust_expr(spacing)})"
```

The exception propagates uncaught through `_gen_alternative_body` → `_gen_alternative` → `_gen_rule`
→ `_gen_rule_methods` → `generate()` to the caller.

**Why**: `_item_spacing_lines` has `rule_name`, `item`, and `position` in scope but does not wrap
the `ValueError`.  The resulting message names only the Doc type (`"Unknown Doc type: Group(…)"`),
losing which rule, which item (label or term kind), and whether the bad config is before- or
after-spacing.

The established pattern for the same call in `_gen_rule_entry` (same file) wraps it:

```python
except ValueError as exc:
    msg = f"Rule {rule_name!r} JOIN_BEGIN separator uses unsupported Doc type: {exc}"
    raise ValueError(msg) from exc
```

**Consequence**: When a user supplies a `FormatterConfig` with a `Group`/`Nest`/`Join` doc as item
spacing (directly, programmatically, or via a `.fltkfmt` file that uses combinators in a spacing
position), `generate()` raises a bare `ValueError` whose message gives no indication of which rule
or item triggered it.  On-call cannot find the offending config entry without a stack trace; at
the module boundary (if exceptions are caught and logged as messages only) the error is
undiagnosable.

**What must change**: Wrap the `_doc_to_rust_expr(spacing)` call in `_item_spacing_lines` in a
`try/except ValueError` and re-raise with context, mirroring `_gen_rule_entry`:

```python
try:
    doc_expr = self._doc_to_rust_expr(spacing)
except ValueError as exc:
    item_id = f"label={item.label!r}" if item.label else f"term={type(item.term).__name__}"
    msg = f"Rule {rule_name!r} {position}-spacing for {item_id} uses unsupported Doc type: {exc}"
    raise ValueError(msg) from exc
spec_expr = f"fltk_unparser_core::{ctor}({doc_expr})"
```
