# Design: `unparser-source-helper` — single-source the unparser assembly pipeline

Requirements: `docs/adr/2026/07/01/01-unparser-source-helper/request.md` (spec) and the
`unparser-source-helper` entry in `TODO.md:39-41`.
Exploration: `docs/adr/2026/07/01/01-unparser-source-helper/exploration.md` (base commit 8fd5ecf).

## Root cause / context

`fltk/unparse/test_is_span_guard.py:56-84` (`_generate_unparser_source`) re-implements the
assembly pipeline of `plumbing.generate_unparser` (`fltk/plumbing.py:257-299`) line-for-line —
`create_default_context` → `add_trivia_rule_to_grammar` → `classify_trivia_rules` →
`gsm2unparser.generate_unparser` → `compiler.compile_class` → `ast.Module` assembly →
`ast.unparse` — because plumbing offers no way to obtain the generated module source before it is
`exec`'d (`fltk/plumbing.py:292`). The test needs the *source* (it inspects emitted span guards and
import structure), not an exec'd class.

Exploration confirms the duplication and that two cosmetic divergences already exist (redundant
re-application of the idempotent trivia steps; the `formatter_config or FormatterConfig()`
coalescing inlined away in the test). No behavioral drift yet, but any pipeline change must be
mirrored in two places — the classic drift foot-gun the TODO names.

`fltk.plumbing` is the documented out-of-tree entry point (`README.md:20`, module docstring). Per
CLAUDE.md, the fix must be purely additive: no renames, no signature changes to
`generate_unparser`.

## Proposed approach

### `fltk/plumbing.py`

Split `generate_unparser` into a shared assembly step plus the existing exec step.

1. **Private assembly helper** (single source of truth):

   ```python
   def _assemble_unparser_module(
       grammar: gsm.Grammar,
       cst_module_name: str,
       formatter_config: FormatterConfig | None,
   ) -> tuple[str, gsm.Grammar, FormatterConfig]:
       """Run the unparser assembly pipeline; return (source, grammar_with_trivia, formatter_config)."""
   ```

   Body is the current `fltk/plumbing.py:275-289` pipeline plus `ast.unparse(module)`, verbatim:
   context creation, `formatter_config or FormatterConfig()` coalescing, trivia
   addition/classification, `gsm2unparser.generate_unparser`, `compiler.compile_class`,
   `ast.Module` assembly with `ast.fix_missing_locations`, `ast.unparse`. It returns the
   trivia-classified grammar and coalesced config alongside the source so `generate_unparser`
   can build `UnparserResult` without recomputing either (avoids enshrining the redundant
   double-application the exploration flagged).

2. **New public function** (the TODO's proposed shape):

   ```python
   def generate_unparser_source(
       grammar: gsm.Grammar,
       cst_module_name: str,
       formatter_config: FormatterConfig | None = None,
   ) -> str:
   ```

   Thin wrapper: returns the source element of `_assemble_unparser_module(...)`. Docstring
   mirrors `generate_unparser`'s (same trivia-capture note, same args) and states it returns the
   generated unparser module source without executing it, and that `generate_unparser` execs
   exactly this source.

3. **Refactor `generate_unparser`** to call `_assemble_unparser_module`, `exec` the returned
   source into `exec_globals`, and build `UnparserResult` from the returned grammar/config exactly
   as today (`fltk/plumbing.py:294-299`). Signature, return type, and observable behavior are
   unchanged: same pipeline steps in the same order, same `exec` semantics, same `UnparserResult`
   fields (including `trivia_config=formatter_config.trivia_config or TriviaConfig()`).

The public surface gains one function; nothing is renamed, removed, or re-annotated. This is the
additive-only category the requirements and CLAUDE.md call safe.

### `fltk/unparse/test_is_span_guard.py`

Replace the helper body with a call to the new plumbing function:

```python
def _generate_unparser_source(grammar_path: Path) -> str:
    grammar = parse_grammar_file(grammar_path)
    parser_result = generate_parser(grammar, capture_trivia=True)
    try:
        return generate_unparser_source(parser_result.grammar, parser_result.cst_module_name)
    finally:
        sys.modules.pop(parser_result.cst_module_name, None)
```

- The grammar-file → `generate_parser` prelude stays: it is test-specific (produces
  `cst_module_name`), not part of the duplicated pipeline (exploration §"Does the duplication
  exist"). Passing `parser_result.grammar` (already trivia-processed) into
  `generate_unparser_source` matches plumbing's own production call pattern
  (`generate_parser` → `generate_unparser(parser_result.grammar, ...)`); the trivia steps are
  idempotent (`fltk/fegen/gsm.py:480-481`, `348-379`).
- Omitting `formatter_config` exercises the shared `None`-coalescing path, eliminating the
  second divergence the exploration flagged (inlined `FormatterConfig()`).
- Remove the now-dead imports (`gsm`, `create_default_context`, `compiler`, `gsm2unparser`,
  `FormatterConfig`); keep `ast` (used by `TestLazySpanAnnotations`), `terminalsrc`, `sys`,
  `pyrt`. Import `generate_unparser_source` from `fltk.plumbing` alongside the existing imports.
- Delete the `TODO(unparser-source-helper)` comment and the "Mirrors plumbing..." docstring
  paragraph; the docstring now simply says it wraps `plumbing.generate_unparser_source` for a
  grammar file path.

### `TODO.md`

Remove the `unparser-source-helper` entry (`TODO.md:39-41`); the code comment goes with it.
The slug then has zero occurrences in code and the master list, per the TODO system's join-key
rule. (The historical references in `docs/adr/2026/06/26-pure-python-span-native-probe/` are
immutable review artifacts and stay, per the exploration.)

## Edge cases / failure modes

- **Drift between source and exec'd class**: eliminated by construction — `generate_unparser`
  execs the exact string the assembly helper produced; there is no second pipeline.
- **`UnparserResult.grammar` identity**: today it is the grammar produced by the in-function
  trivia steps; after the refactor it is the same object returned by the shared helper. No
  observable change.
- **Behavior when `formatter_config=None`**: coalescing moves into the shared helper; both
  entry points get identical treatment. `generate_unparser`'s observable behavior is unchanged.
- **Test helper no longer literally mirrors plumbing**: intended — it now *is* plumbing. If the
  pipeline gains steps (new imports, reordered trivia), the test picks them up automatically.
- **Downstream (out-of-tree) impact**: additive only. `generate_unparser`'s
  signature/return/exceptions are untouched; a new name is added to a module without `__all__`,
  which cannot shadow or break existing imports.
- **exec-globals leakage**: `exec_globals` handling stays inside `generate_unparser` exactly as
  today; `generate_unparser_source` performs no exec, so callers wanting inspection get a pure
  function of its inputs.

## Test plan

After the change:

- `fltk/unparse/test_is_span_guard.py` — its 4 existing call sites of
  `_generate_unparser_source` (lines 91, 95, 112, 133) become end-to-end tests of
  `generate_unparser_source`: they assert real properties of the returned source (span-guard
  helper usage, no probe-bound isinstance, future-import placement, TYPE_CHECKING-guarded
  protocol import). No new tests needed there.
- New test in `fltk/test_plumbing.py`: `generate_unparser_source` returns source that, when
  exec'd, defines an `Unparser` class — and `generate_unparser` on the same
  (grammar, cst_module_name, config) inputs produces a working unparser (existing behavior),
  pinning the "generate_unparser execs its output" contract. Written first (TDD): it fails
  before the change because `fltk.plumbing` has no `generate_unparser_source` (`ImportError`
  at collection if imported at module top, `AttributeError` if accessed via the module).
- Regression: existing `generate_unparser` consumers (`fltk/test_plumbing.py`,
  `fltk/test_plumbing_integration.py`, `fltk/unparse/test_unparser.py` and the other
  `fltk/unparse/test_*.py` suites, `tests/test_fltkfmt_parity.py`) run unchanged and gate the
  refactor of the exec path.
- `make check` gates lint/type cleanliness and the TODO.md/comment removal consistency.

## Open questions

None. The requirements' proposed shape is unambiguous and the exploration confirms it is additive;
the only latitude exercised is the private `_assemble_unparser_module` helper to avoid recomputing
the trivia grammar, which is an internal detail invisible to consumers.
