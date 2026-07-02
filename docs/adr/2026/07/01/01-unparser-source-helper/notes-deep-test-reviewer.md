# Test review: unparser-source-helper

## test-1

**File:line**: `fltk/test_plumbing.py:258-269` (`TestUnparserSource.test_generate_unparser_execs_its_output`)

**What's wrong**: The docstring claims this test "pins the exec contract" (i.e. that
`generate_unparser` execs exactly the source `generate_unparser_source` returns), but the test
body never calls `generate_unparser_source` — it only calls `generate_unparser` and checks the
final rendered string. It is materially the same setup as the pre-existing
`TestUnparsing.test_unparse_simple_expression` (`fltk/test_plumbing.py:275-293`, same grammar
text `expr := hello:"hello" , world:"world";`, same `generate_unparser` call), just asserting the
rendered string instead of the `Doc` structure. Nothing in the new suite actually cross-checks
that `generate_unparser_source(...)`'s returned source and what `generate_unparser(...)` execs
produce equivalent results from the same inputs — the two new tests exercise each function in
isolation.

**Consequence**: The refactor's whole purpose is to eliminate a two-implementation drift risk by
making `generate_unparser` and `generate_unparser_source` share `_assemble_unparser_module`. A
regression where `generate_unparser` stops routing through `_assemble_unparser_module` (e.g.
someone reintroduces an inline copy of the pipeline in `generate_unparser`, or the two entry
points silently diverge — different trivia handling, different config coalescing, extra
transformation applied to one but not the other) would not be caught by this test suite:
`test_source_defines_unparser_class_when_exec` only exercises `generate_unparser_source` in
isolation, `test_generate_unparser_execs_its_output` only exercises `generate_unparser` in
isolation (and duplicates existing coverage while doing so), and no test compares their outputs
for the same `(grammar, cst_module_name, formatter_config)` triple.

**Fix**: Replace (or add alongside) `test_generate_unparser_execs_its_output` a test that manually
execs `generate_unparser_source(grammar, cst_module_name, config)`'s output, unparses the same CST
with the resulting `Unparser` class, and asserts the rendered output equals what
`generate_unparser(grammar, cst_module_name, config)` produces via `unparse_cst` for the same
inputs — directly pinning the "same source, same behavior" contract the design describes, rather
than testing each entry point's pre-existing behavior independently. If the redundant
`Doc`-structure assertion in `TestUnparsing.test_unparse_simple_expression` is meant to stay
separate, drop the duplicate round-trip from `TestUnparserSource` and replace it with the
cross-check above.

## test-2

**File:line**: `fltk/test_plumbing.py:242-256` (`TestUnparserSource`)

**What's wrong**: No test passes a non-`None` `formatter_config` to `generate_unparser_source`.
Both new tests rely on the default-`None` coalescing path (`formatter_config or
FormatterConfig()`), which is also the only path exercised in `fltk/unparse/test_is_span_guard.py`
(design explicitly notes it "exercises the shared `None`-coalescing path"). Existing
`generate_unparser` tests (`TestUnparserGeneration.test_generate_unparser_with_formatter`,
`test_generate_unparser_with_trivia_config`) cover the explicit-config path only for
`generate_unparser`, not for `generate_unparser_source`.

**Consequence**: Because both entry points share `_assemble_unparser_module`, the risk is low, but
there is currently zero direct evidence that `generate_unparser_source` even accepts/threads a
supplied `formatter_config` through to the emitted source — a bug that silently ignored the
`formatter_config` parameter in `generate_unparser_source` specifically (e.g. a typo swapping
which local variable feeds `gsm2unparser.generate_unparser`) would not be caught by any test in
this diff.

**Fix**: Add a case (or extend an existing test) that calls `generate_unparser_source` with a
non-default `FormatterConfig` (e.g. one that changes whitespace handling as in
`test_generate_unparser_with_formatter`) and asserts the resulting source reflects it — either by
exec'ing and rendering, or by asserting on an observable difference in the emitted source/behavior
versus the default-config case.
