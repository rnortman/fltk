# Test review: native-span-init-error-context

## test-1

- File: `fltk/fegen/test_gsm2lib_rs.py:228-234` (`test_span_only_wraps_unknown_span_creation_error`)
- What's wrong: The only test asserting the interpolated error message
  (`f'"{spec.module_name} module init: failed to create UnknownSpan sentinel: {{e}}"'`,
  `fltk/fegen/gsm2lib_rs.py:204`) uses `_span_only_spec()`
  (`fltk/fegen/test_gsm2lib_rs.py:203-210`), which hardcodes `module_name="_native"`. No
  test combines `unknown_span_static=True` with any other `module_name` value. The other
  spec that uses a different module name, `_span_types_no_unknown_span_spec()`
  (`module_name="my_ext"`, `test_gsm2lib_rs.py:357-364`), sets `unknown_span_static=False`
  and so never reaches the message-formatting line at all.
- Consequence: A regression that hardcodes the literal string `"_native module init: ..."`
  instead of interpolating `spec.module_name` would pass every test in the suite, since
  the one spec that exercises this code path happens to use `module_name="_native"`. The
  test can't distinguish "correctly parameterized" from "coincidentally correct constant."
- Fix: Add a case (e.g. a small variant of `_span_only_spec()` with
  `module_name="my_ext"` and `unknown_span_static=True`) and assert the message begins
  with `"my_ext module init: failed to create UnknownSpan sentinel: {e}"`, proving the
  module name is actually substituted rather than hardcoded.

Everything else lines up well with the design's test plan: the drift-pin test
(`test_committed_lib_rs_matches_generator`) does a byte-for-byte comparison against the
committed `src/lib.rs` and correctly skips outside a checkout; the negative assertion
`"Span::unknown())?.into_any()" not in src` guards against the old unwrapped form
surviving; and all three new/updated call sites (`test_gsm2lib_rs.py`,
`test_genparser.py`) were updated consistently for the `LineColPos` registration and use-line
changes. Ran `uv run pytest fltk/fegen/test_gsm2lib_rs.py fltk/fegen/test_genparser.py`:
117 passed, including the drift pin against the actual committed `src/lib.rs`.
