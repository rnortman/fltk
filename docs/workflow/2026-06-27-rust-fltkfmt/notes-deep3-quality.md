# Quality review — increments 7-8 (rust-fltkfmt)

Commit reviewed: 25cd5dcab7489fc1cb05c6c3e29009a170130d0f

---

## quality-1

**File:line**: `tests/test_fltkfmt_parity.py:77-80`

**Issue**: `_py_unparser_result()` calls the cached `_py_parser_result()` twice within one function body — once for `.grammar` and once for `.cst_module_name`:

```python
return plumbing.generate_unparser(
    _py_parser_result().grammar,
    _py_parser_result().cst_module_name,
    formatter_config=_format_config(),
)
```

The mirrored test (`tests/test_rust_unparser_parity_fixture.py:60-62`) avoids the double call by passing `_grammar()` directly for the grammar argument and calling `_py_parser_result()` only once for `cst_module_name`. The two calls are cheap (both are cached), but the double invocation reads as though two separate parser generations happen, and it diverges from the pattern the mirrored test established.

**Consequence**: A future reader checking whether `_py_unparser_result` depends on `_py_parser_result` at all must trace both call sites to see they land on the same cache hit. If the `@functools.cache` decorator were ever removed from `_py_parser_result` (e.g., during a refactor to a conftest fixture), the double call silently becomes two full parser generations — a latent regression that the mirrored test would not share.

**Fix**: Bind the result once before extracting attributes:

```python
@functools.cache
def _py_unparser_result():
    result = _py_parser_result()
    return plumbing.generate_unparser(
        result.grammar,
        result.cst_module_name,
        formatter_config=_format_config(),
    )
```

This matches the intention, costs nothing, and aligns the function structure with the mirrored test.
