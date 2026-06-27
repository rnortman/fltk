# Dispositions — deep3 review (rust-fltkfmt increments 7-8)

Commit with fixes: c2caadb9b5ecfec082fb48986a3bade3a1b85e80
Base: 78eacab318a0d30e43a469dee2269b29cef0875d

Note: `errhandling-1` and `test-1` are the same finding reported by two reviewers
(the `proc.stdout.decode` error mode); disposed together below.

## errhandling-1 / test-1

- Disposition: Fixed
- Action: `tests/test_fltkfmt_parity.py:138` — `proc.stdout.decode("utf-8")` →
  `proc.stdout.decode("utf-8", "replace")`, matching the stderr decode on the
  return-code assertion above. Non-UTF-8 binary output now flows through the
  `assert py_out == rust_out` comparison (rendering bad bytes as `replace` markers
  with full `[file w= i=]` context) instead of raising a bare `UnicodeDecodeError`.
- Severity assessment: Low. Only bites if `fltkfmt` ever emits invalid UTF-8 (a
  formatter/memory bug); when it does, the change is the difference between a
  context-free traceback and a diagnosable assertion naming the corpus file and config.

## test-2

- Disposition: Fixed
- Action: `tests/test_fltkfmt_parity.py:53-54` — rewrote the `_CONFIGS` comment to
  "Wide (80/2, which is also the CLI default) and narrow (40/4) ...", removing the
  "plus the CLI default" phrasing that falsely implied a third config.
- Severity assessment: Trivial. Documentation-only; no behavior. Removed reader
  confusion about the coverage set.

## reuse-1

- Disposition: Fixed
- Action: Added `render_config_ids(configs)` to `tests/unparser_parity.py:21-30`
  (the existing shared parity-helper module). Both parity modules now derive their
  config IDs through it: `tests/test_fltkfmt_parity.py:57` and
  `tests/test_rust_unparser_parity_fixture.py:169` (imports updated at
  test_fltkfmt_parity.py:31 and test_rust_unparser_parity_fixture.py:41). The
  per-module `_CONFIGS` lists (which legitimately differ) stay local; only the ID
  format string is now single-sourced.
- Severity assessment: Low. Prevents silent divergence of test-ID format strings
  across the two modules that could break CI test-ID filters.

## quality-1

- Disposition: Fixed
- Action: `tests/test_fltkfmt_parity.py:74-82` — `_py_unparser_result` now binds
  `parser_result = _py_parser_result()` once and reads `.grammar`/`.cst_module_name`
  off it, instead of calling the cached function twice. Kept `parser_result.grammar`
  (not `_grammar()`); the post-generation grammar is what the original used and may
  differ from the pre-generation grammar, so substituting `_grammar()` would risk a
  semantic change.
- Severity assessment: Trivial now (cache hit), but guards against a latent doubling
  of parser generation if `@functools.cache` were ever removed in a refactor.

## efficiency-1

- Disposition: Fixed
- Action: `tests/test_fltkfmt_parity.py:85-99` — added `@functools.cache def _py_doc(text)`
  performing parse + unparse (config-independent), and reduced `_py_format` to a single
  `render_doc(_py_doc(text), cfg)`. The heavy pure-Python parse/unparse now runs once
  per input instead of once per (input, config), halving the Python-side work at the
  current 2 configs. Verified safe: `Renderer.render` (renderer.py:47-145) reads the
  Doc read-only and wraps it in a fresh `Group`, never mutating it, so rendering the
  cached Doc under multiple configs is correct. `fltkg.read_text()` left as-is (the
  reviewer flagged its cost as negligible next to the parse).
- Severity assessment: Low. Test-suite wall time only; reduces redundant parse/unparse
  passes, scaling with the number of render configs.

## correctness, security

- No findings reported.
