## quality-1

**File:line**: `tests/test_rust_unparser_parity_fixture.py:2657–2695` (diff lines)

**Issue**: Four module-level globals (`_grammar`, `_py_parser_result`, `_py_unparser_result`, `_py_unparser_result_default`) each paired with an identically-structured `_*_cached()` function that does `global _x; if _x is None: _x = ...; return _x`. The pattern is copy-pasted four times with only the variable name and initializer expression changed.

The directly analogous file `tests/test_rust_parser_parity_fixture.py` (existing, not in this diff) consolidates its two cached values into a single `_get_py_parser_class(capture_trivia: bool)` accessor that dispatches on a parameter — one function, zero exposed globals in the calling API.

**Consequence**: Every new baked-config variant requires adding a fifth global plus a fifth `_cached()` function. The pattern will propagate unchanged because it looks "consistent" with the other four. The `functools.cache` standard idiom exists precisely to eliminate this boilerplate.

**Fix**: Replace the four global-plus-function pairs with four `@functools.cache`-decorated plain functions (drop the `_cached` suffix; callers use the function name directly). All four module-level `None` sentinels go away. The declaration order already expresses the dependency chain, so no structural change is needed:

```python
import functools

@functools.cache
def _grammar():
    return parse_grammar_file(_FIXTURE_FLTKG)

@functools.cache
def _py_parser_result():
    return generate_parser(_grammar(), capture_trivia=True)

@functools.cache
def _py_unparser_result():
    cfg = parse_format_config_file(_FIXTURE_FLTKFMT)
    return generate_unparser(_grammar(), _py_parser_result().cst_module_name, cfg)

@functools.cache
def _py_unparser_result_default():
    return generate_unparser(_grammar(), _py_parser_result().cst_module_name)
```

---

## quality-2

**File:line**: `tests/test_rust_unparser_parity_fixture.py:2782–2815` (diff lines)

**Issue**: `test_unparse_parity_fltkfmt` and `test_unparse_parity_default` are structurally identical 12-line functions. They differ in exactly two values: which `Unparser()` class is instantiated (`rust_parser_fixture.unparser.Unparser()` vs `rust_parser_fixture.unparser_default.Unparser()`) and which cached Python unparser result is fetched. The `tests/test_rust_parser_parity_fixture.py` analog handles the analogous two-config situation with a single `test_parity` function parametrized over `capture_trivia=[False, True]`.

**Consequence**: Adding a third baked config (e.g. a project-specific `.fltkfmt` config in a downstream test) requires copy-pasting a third identical function body. The fix to quality-1 (using `@functools.cache`) enables the fix here cleanly.

**Fix**: Introduce a config parametrization dimension and merge into one function. For example:

```python
_BACKEND_CONFIGS = [
    ("fltkfmt", _py_unparser_result, lambda: rust_parser_fixture.unparser.Unparser()),
    ("default", _py_unparser_result_default, lambda: rust_parser_fixture.unparser_default.Unparser()),
]

@pytest.mark.parametrize("_cfg,py_result_fn,rust_unparser_fn", _BACKEND_CONFIGS, ids=["fltkfmt", "default"])
@pytest.mark.parametrize("max_width,indent_width", _CONFIGS, ids=_CONFIG_IDS)
@pytest.mark.parametrize("rule,text", _CORPUS, ids=_CORPUS_IDS)
def test_unparse_parity(rule, text, max_width, indent_width, _cfg, py_result_fn, rust_unparser_fn):
    py_cst = _py_cst(text, rule)
    rust_node = _rust_node(text, rule)
    assert_unparse_parity(
        py_result_fn(),
        py_cst,
        rust_unparser_fn(),
        rust_node,
        rule, text,
        indent_width=indent_width,
        max_width=max_width,
    )
```

(The `lambda` wrappers are needed because `rust_parser_fixture` isn't importable at module level when the fixture isn't built, so class references must be deferred.)
