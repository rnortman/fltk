# Dispositions — deep review, unparser-source-helper (round 1)

Commit: 44bc2d69fb74815602b932054d4cd581612b77f7 (base 007401ed)

test-1:
- Disposition: Fixed
- Action: Rewrote `TestUnparserSource.test_generate_unparser_execs_its_output` into
  `test_generate_unparser_matches_source_output` (fltk/test_plumbing.py:258-287). It now
  execs the string returned by `generate_unparser_source`, drives the same CST through the
  resulting `Unparser`, and asserts the rendered output equals `generate_unparser`'s output
  on the same `(grammar, cst_module_name)` inputs — directly pinning the "same source, same
  behavior" single-source contract. Removed the duplicate round-trip of
  `test_unparse_simple_expression`.
- Severity assessment: The suite claimed to guard the source/exec single-sourcing contract
  but did not; a regression reintroducing a separate pipeline in `generate_unparser` would
  land silently — the exact drift this change exists to prevent.

quality-1:
- Disposition: Fixed
- Action: Same fix as test-1 (fltk/test_plumbing.py:258-287). The rewritten test no longer
  duplicates `test_unparse_simple_expression` and its docstring now matches what it verifies
  (cross-check of both public entry points).
- Severity assessment: Duplicate test with a misleading docstring — maintenance weight and
  false sense of coverage for the contract central to this change.

test-2:
- Disposition: Fixed
- Action: Added `test_source_reflects_formatter_config` (fltk/test_plumbing.py:289-311),
  which passes a non-default `FormatterConfig` (`global_ws_allowed=Nbsp()`) to
  `generate_unparser_source`, execs the result, and asserts the rendered output is "a b"
  (default `NIL` would yield "ab") — proving the `formatter_config` argument is threaded
  through into the emitted source.
- Severity assessment: Low — both entry points share `_assemble_unparser_module`, but there
  was previously zero direct evidence that `generate_unparser_source` threads a supplied
  `formatter_config`; a bug ignoring the parameter would have gone uncaught.
