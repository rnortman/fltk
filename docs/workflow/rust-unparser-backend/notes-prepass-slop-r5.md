## slop-1

**File:** `fltk/unparse/gsm2unparser_rs.py` — `_item_spacing_lines`, the `if position == "before": ... else:` block

**Quote:**
```python
if position == "before":
    spacing = self._formatter_config.get_before_spacing(rule_name, item)
    ctor = "before_spec"
else:
    spacing = self._formatter_config.get_after_spacing(rule_name, item)
    ctor = "after_spec"
```

**What's wrong:** `position` is a stringly-typed discriminant with a bare `else:` that silently treats any value other than `"before"` as `"after"` semantics. A typo (`"after "`, `"After"`, or any garbage) produces after-spacing silently — no `ValueError`, no assertion.

**Consequence:** A caller passing an invalid position string would get wrong (after) spacing emitted with no diagnostic. Given the method is already private and only called with literals, the risk is low now, but the pattern is visibly sloppy and would embarrass a reviewer who spots the else-catches-all.

**Suggested fix:** Use `elif position == "after": ... else: raise ValueError(f"position must be 'before' or 'after', got {position!r}")`, or replace the parameter with a `Literal["before", "after"]` annotation (which at least flags the constraint to type checkers) and keep the explicit `elif`/`raise`.

---

## slop-2

**File:** `crates/fltk-unparser-core/src/doc.rs` — docstrings for `before_spec` and `after_spec`

**Quote:**
```rust
/// Wrap a spacing doc as a `BeforeSpec` control node (port of the Python unparser's
/// `_create_before_spec`): spacing applied before the following content, resolved away
/// by `resolve_spacing_specs`. The `Rc` wrapping mirrors `group`/`nest`.
```

**What's wrong:** The docstrings lead with provenance narrative ("port of the Python unparser's `_create_before_spec`") and explain an implementation choice by cross-referencing the porting context ("The `Rc` wrapping mirrors `group`/`nest`"). These are notes to the author about what was ported and why — not a description of the contract, invariants, or non-obvious behavior a caller needs to know.

**Consequence:** Public API docs (these are `pub fn`) that open with "port of X" read as an LLM's session notes attached to the wrong artifact. Downstream consumers of `fltk-unparser-core` shouldn't need to know `_create_before_spec` existed. The implementation-choice note about `Rc` belongs in a code comment inside the function body, not the doc comment.

**Suggested fix:** Lead with what the function does and what the caller should know: e.g. `/// Construct a [`Doc::BeforeSpec`] node wrapping `spacing`. The spacing is applied before the following content and resolved at render time by [`resolve_spacing_specs`].` Move the `Rc`-mirroring note to an inline comment if it matters at all.
