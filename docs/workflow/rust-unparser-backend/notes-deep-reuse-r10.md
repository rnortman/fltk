## reuse-1

**File:line**: `tests/unparser_parity.py:32–47` (`unparse_python`)

**What's duplicated**: The instantiate → dispatch → `resolve_spacing_specs` pipeline inside `unparse_python` duplicates the same pipeline already encapsulated in `fltk.plumbing.unparse_cst` (`fltk/plumbing.py:317–333`). Concretely: `unparser_result.unparser_class(text)`, `getattr(unparser, f"unparse_{rule}")(cst)`, and `resolve_spacing_specs(result.accumulator.doc)` are all present verbatim in `unparse_cst`. The `resolve_spacing_specs` import (`tests/unparser_parity.py:17`) is pulled in directly from `fltk.unparse.resolve_specs` rather than through the plumbing layer, which already re-exports it internally.

**Existing function**: `fltk.plumbing.unparse_cst` — `fltk/plumbing.py:302`. Accepts `(unparser_result, cst, terminals, rule_name)`, runs the same pipeline, and returns the resolved `Doc`. The only behavioral difference from `unparse_python` is that `unparse_cst` raises `ValueError("Unparsing failed")` when the unparser returns `None`, while `unparse_python` returns `None` to preserve the parity-comparable outcome.

**Consequence**: The two pipelines will drift independently. If `unparse_cst`'s internal steps change (e.g., the accumulator API or the resolve step), `unparse_python` will silently stay behind, causing the parity test to compare Python output rendered via a stale pipeline against Rust output — a false-positive or false-negative parity result. The fix is to implement `unparse_python` over `unparse_cst`:

```python
try:
    doc = unparse_cst(unparser_result, py_cst, text, rule)
    return render_doc(doc, RendererConfig(indent_width=indent_width, max_width=max_width))
except ValueError:
    return None
```

This removes the direct `resolve_spacing_specs` import and keeps the Python-backend rendering path in sync with the production path automatically.
