# Dispositions — deep review round 1 (native-span-init-error-context)

Base: f8f34288ff30e175021866746fa3b28e6a65485c
HEAD after fixes: bdf164212e1915a71ff8d30a154fcccb92e69f78

Reviewers with no findings: error-handling, correctness, security, reuse, efficiency.

test-1:
- Disposition: Fixed
- Action: Added `test_unknown_span_creation_error_message_interpolates_module_name`
  (`fltk/fegen/test_gsm2lib_rs.py:236-251`) using a `module_name="my_ext"`,
  `unknown_span_static=True` spec; asserts the message reads
  `my_ext module init: failed to create UnknownSpan sentinel: {e}` and that the
  `_native ...` form is absent. This distinguishes correct `spec.module_name`
  interpolation from a coincidentally-correct hardcoded `_native` constant.
- Severity assessment: Valid coverage gap. A regression hardcoding `_native`
  would have passed the whole suite, silently breaking every out-of-tree
  `gen-rust-lib` consumer's error message. Low blast radius (import-time OOM
  message text) but a real hole in the one test that pins the message.

quality-1:
- Disposition: Fixed
- Action: Reworked `test_committed_lib_rs_matches_generator`
  (`fltk/fegen/test_gsm2lib_rs.py:319-331`) to skip only when genuinely outside
  a checkout (no `pyproject.toml` at repo root) and to `assert lib_rs.exists()`
  with a message naming the pin when inside a checkout. A future relocation of
  `src/lib.rs` now produces a red test naming the drift pin instead of a silent
  permanent skip.
- Severity assessment: Valid. The drift gate is the change's whole prevention
  mechanism; a fail-open skip on file relocation would silently recreate the
  original detection gap while the suite stays green. Fix restores fail-closed
  behavior for the in-checkout case.

Verification: `uv run pytest fltk/fegen/test_gsm2lib_rs.py` — 53 passed
(was 52; +1 new test). Full `make check` gate passed on commit.
