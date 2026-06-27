# Quality review — rust-fltkfmt final pass

Commit reviewed: f89c80930a8799aaf476077b572fea449e3024d2

---

## quality-1

**File:** `crates/fltkfmt/Cargo.toml` — `fltk-unparser-core` direct dependency

The binary's `Cargo.toml` lists `fltk-unparser-core` as a direct dependency, but `src/main.rs` uses no `fltk_unparser_core::` path directly. The only code in the binary is a single `fltk_fmt_cli::fltk_formatter_main!` invocation; that macro resolves every type through `$crate::` (i.e., `fltk_fmt_cli::RendererConfig`, `fltk_fmt_cli::Renderer`, etc.), which are re-exports inside `fltk-fmt-cli`. The unparser-core types arrive through two transitive paths already: via `fltk-fmt-cli` and via `fegen-rust-cst --no-default-features`.

**Consequence:** A consumer copying this `Cargo.toml` as a template for their own formatter binary would include `fltk-unparser-core` in the belief that it is required; the redundant dep silently inflates the per-consumer boilerplate and creates a false impression of direct coupling. The correct template for a new formatter binary should list only `fegen-rust-cst`, `fltk-unparser-core` is absent, and `fltk-fmt-cli` — and it is the last one that carries the runtime.

**Fix:** Remove the `fltk-unparser-core` line from `crates/fltkfmt/Cargo.toml`. The binary compiles and runs correctly without it; the dependency remains in the graph transitively.

---

## quality-2

**File:** `fltk/unparse/gsm2unparser_rs.py`, `_gen_python_bindings` (~lines 1831–1853)

The three-line unparse prelude—

```python
lines.append("            let guard = node.shared().read();")
lines.append(f"            let Some(r) = self.inner.unparse_{rule.name}(&guard) else {{")
lines.append("                return Ok(None);")
lines.append("            };")
lines.append("            let resolved = resolve_spacing_specs(r.accumulator.doc());")
```

—is copy-pasted verbatim into both the `unparse_{rule}` (string-returning) and `unparse_{rule}_doc` (doc-returning) method generators inside the `for rule in self._grammar.rules:` loop. The two method bodies diverge only in the final lines (one renders to a `String`, the other wraps in `PyDoc`).

**Consequence:** Any future change to the prelude—adding a depth-exceeded guard before the `let Some(r)` line, changing the `Ok(None)` handling, or modifying how `resolve_spacing_specs` is called—must be applied in two places per rule, with no compiler or test to catch a one-side-only edit. The pattern will also propagate if a third per-rule method variant is added later.

**Fix:** Extract a private `_gen_py_unparse_prelude_lines(self, rule_name: str) -> list[str]` method returning the five common lines, and call it from both the string-method and doc-method generator paths.

---

## quality-3

**File:** `fltk/unparse/gsm2unparser_rs.py`, `_item_spacing_lines` (~lines 580–598)

The function branches on `position: Literal["before", "after"]` with an `if / elif` chain and no `else`, leaving `spacing` and `ctor` potentially unbound:

```python
if position == "before":
    spacing = ...
    ctor = "before_spec"
elif position == "after":
    spacing = ...
    ctor = "after_spec"
if spacing is None:   # UnboundLocalError if neither branch ran
    return []
```

The inline comment reads: "Pyright enforces it at every call site, and no else/runtime guard is needed." This is true for the current two callers under static analysis. It does not hold at runtime if `position` arrives as a computed string from a future call site, a parametrised test, or any path that bypasses the type annotation.

**Consequence:** Runtime failure would surface as `UnboundLocalError: local variable 'spacing' referenced before assignment`—a misleading error that names no configuration entry, no rule, and no position value. This pattern will propagate: any future `_item_*` method that dispatches on `position` is likely to copy the same if/elif structure. One accidental third call site with a wrong string silently exposes the gap.

**Fix:** Add an `else: raise ValueError(f"Unknown position: {position!r}")` branch immediately after the `elif`. The branch is unreachable under correct use, so no test regression; it makes the exhaustiveness contract explicit and produces a useful diagnostic if the contract is ever violated.

---

## quality-4

**File:** `crates/fltk-fmt-cli/src/lib.rs`, `validate` (~lines 115–124)

```rust
if args.output.is_some() {
    let count = if args.files.is_empty() {
        1   // ← this branch is dead: 1 > 1 is always false
    } else {
        args.files.len()
    };
    if count > 1 {
        return Err("error: --output requires exactly one input".to_string());
    }
}
```

Setting `count = 1` when `files.is_empty()` is intended to express "zero explicit files = one implicit stdin input," but `1 > 1` is always false, so the `is_empty()` branch never affects the validation outcome. The check `args.files.len() > 1` is identical in behavior.

**Consequence:** A reader encountering the `count` variable may spend time tracing the `is_empty()` path to determine whether it is load-bearing, and conclude (correctly, but non-obviously) that it is not. This is a low-cost maintenance debt on its own, but the pattern—dead branch preserved for "semantic clarity"—may recur in adjacent validation code.

**Fix:** Replace the `count` computation and comparison with `if args.files.len() > 1 { ... }`. If the "implicit stdin = 1 input" model is worth documenting, do so as an inline comment on the replaced line rather than as dead code.
