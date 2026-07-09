# Test review — round 1

## test-1: `raw_string` → `macro` highlighting is never asserted

`fltk/fegen/fegen.fltklsp` (new) deliberately paints regex bodies (`raw_string.value`) as
`macro` — the design doc calls this out explicitly as a non-obvious choice ("the legend has no
`regexp` type, so e.g. `macro`", design.md:54, 57). `test_highlight_fltkg` in
`fltk/lsp/test_grammar_lsp.py:76-89` even puts a regex literal in its sample text
(`bar := /[a-z]+/ ;`) but asserts only `foo` (rule def), `name` (label), `"lit"` (string), and
`:=` (operator) — never `[a-z]+` or `/[a-z]+/`.

Consequence: if the `raw_string` scope statement in `fegen.fltklsp` were deleted, mistyped
(wrong anchor path, wrong token name), or regressed to the default `variable`/`regexp` paint, no
test would fail. This is exactly the kind of "implementation detail... pinned by tests" the design
promises (design.md:58) but doesn't deliver for this specific mapping.

Fix: in `test_highlight_fltkg`, add `assert tt(result.tokens, text, "[a-z]+") == "macro"` (or
assert on the full `/[a-z]+/` span if that's what `raw_string.value` covers).

## test-2: `fegen.fltklsp` operator/punctuation legend mostly unverified

`fegen.fltklsp` declares two global literal groups: `scope ":=", "|", "/", "%", "$", "!", "?",
"+", "*": operator;` and `scope ";", ".", ",", ":", "(", ")": punctuation;` (8 + 6 literals). The
only member of either group exercised by a test is `:=` (`test_highlight_fltkg`,
`test_grammar_lsp.py:88`); the sample text does contain `,` and `;` but neither is asserted.

Consequence: a literal accidentally left out of a group, moved to the wrong group (e.g. `,`
painted `operator` instead of `punctuation`), or a typo in the literal text would ship silently —
these are hand-authored token lists in a new file, exactly where transcription slips happen, and
nothing else in the suite touches them.

Fix: extend `test_highlight_fltkg`'s sample text to include one more literal from each group not
already implied by the grammar's own required syntax (e.g. add a second rule using `|` or a
quantifier), and assert at least one punctuation literal (`,` or `;`) and one more operator.

## Otherwise solid

- `test_grammar_lsp.py`'s registry-integrity, formatting-round-trip, and def/ref-resolution tests
  make real assertions (parsed-symbol kinds, resolved-reference targets, idempotent formatting)
  rather than smoke-only "didn't throw" checks.
- The CLI tests (unknown language, `--help`, path resolution) and the e2e pytest-lsp session
  (clean-doc tokens + a triggered diagnostic on a breaking edit) exercise real new code paths
  (`grammar_cli.py`) with meaningful assertions.
- `server_cli.py`'s `main`→`serve` extraction is a behavior-preserving refactor; the existing
  `test_server_cli.py` suite (unchanged, not shown in this diff) already covers `serve`'s
  fail-fast paths, so no new server_cli tests were needed — correctly not duplicated in
  `test_grammar_lsp.py`.
- `test_dogfood.py`'s new test for the extended `fltklsp.fltklsp` (`def rule_name: type;`) checks
  both the parsed `def_matchers` and an actual `analyze()` producing the expected symbol —
  not vacuous.
