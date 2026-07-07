# test-reviewer notes — round slice: AnalysisEngine (§4.7), fltk-highlight CLI (§4.8), dogfood fixture (§8)

Scope: `fltk/lsp/engine.py`, `fltk/lsp/highlight_cli.py`, `fltk/lsp/fltklsp.fltklsp`,
`fltk/lsp/test_engine.py`, `fltk/lsp/test_highlight_cli.py`, `fltk/lsp/test_dogfood.py`
(diff 87dbc0d..9a085e9). `classify.py`/`lsp_config.py`/`analysis.py` predate this diff
(reviewed in a prior round) and are out of scope except where a matcher/field is needed to
specify a fix.

## test-1

File: `fltk/lsp/test_dogfood.py::test_dogfood_spec_highlights_a_sample`

The dogfood fixture `fltk/lsp/fltklsp.fltklsp` defines rule blocks for `rule_config`,
`scope_stmt`, `def_stmt`, `ref_stmt`, `namespace_stmt`, `qualifier`, `dotted_name`,
`literal`, plus a global literal-anchor scope on `";", ":"`. The sample text used by the
highlighting test (`'rule def_stmt {\n  scope "name", label:comment: keyword.static;\n}\n'`)
only ever contains a `rule { }` block wrapping a single `scope` statement with a `label:`
qualifier. It never contains an actual `def`, `ref`, or `namespace` statement, never uses
the `rule:` qualifier, and never asserts a token type for any `;` or `:` character.

Consequence: three of the five statement-keyword rule blocks (`def_stmt`, `ref_stmt`,
`namespace_stmt`), the qualifier block's `"rule"` literal paint, and the entire global
punctuation scope are committed as part of this round's dogfood fixture but never exercised
end-to-end. A typo or wrong-tier resolution bug in any of those five paint rules would pass
this test suite silently, despite the stated purpose of the fixture ("dogfoods the
`.fltklsp` addressing surface ... end-to-end on a real, non-trivial spec").

Fix: extend the sample (or add a second sample) to include a `def ...;` and/or `ref ...;`
statement, a `namespace;` statement, an anchor using the `rule:` qualifier, and a bare `;`
or `:` character position, with `_token_type` assertions for each against their expected
paint (`keyword` / `punctuation`).

## test-2

File: `fltk/lsp/test_highlight_cli.py` (all four tests); production code:
`fltk/lsp/highlight_cli.py:69` (`sgr = f"1;{code}" if "declaration" in token.modifiers else code`).

No CLI test uses an `.fltklsp` spec containing a `def` statement, so no test ever produces a
token carrying the `declaration` modifier, and the bold-rendering branch in `_render` is
never taken. Def-site paint is a live, user-confirmed round-1 feature (design §4.6/§9-2) and
this branch is new code in this round's file.

Consequence: a bug in the bold-prefix formatting (e.g. wrong SGR code, wrong modifier
string, swapped branches) would not be caught by any test.

Fix: add a CLI test with a spec containing `rule <r> { def <anchor>: <kind>; }`, target text
containing that def site, and assert the rendered stdout contains the `\x1b[1;<code>m` bold
prefix around the def-site segment (and not the plain `\x1b[<code>m` form).

## test-3

Files: `fltk/lsp/test_engine.py`, `fltk/lsp/test_highlight_cli.py`.

Every test constructs one `AnalysisEngine` and calls `.highlight()` exactly once. The
design's stated raison d'être for `AnalysisEngine` (§4.7) is "grammar+specs → parser+config
once, then text → tokens many times" — the entire point of the seam is safe reuse across
calls. No test calls `highlight()` twice on the same instance with different texts.

Consequence: any accidental cross-call state (e.g. a mutable cache, a stateful iterator held
on `self`, or a parser/table object mutated in place) would go undetected, even though reuse
is the documented purpose of the class and the exact usage pattern the M2 server will impose.

Fix: add a test that builds one `AnalysisEngine`, calls `highlight()` with two different
texts (ideally one that succeeds and one that fails to parse), and asserts both results are
independently correct — including that a prior parse failure doesn't corrupt a subsequent
successful classification, and vice versa.

## test-4

File: `fltk/lsp/test_highlight_cli.py`; production code: `fltk/lsp/highlight_cli.py:85-89`.

`main`'s `except ValueError` is documented (inline comment) to cover "grammar/.fltklsp load
errors." Only the `.fltklsp`-load-error side is tested (`test_bad_lsp_spec_exits_1`, an
unknown `rule` name). No test supplies a malformed or nonexistent `--grammar` file. Also
untested: a nonexistent `--lsp` file — `AnalysisEngine.from_paths` calls
`lsp_path.read_text()` directly (`engine.py:71`), which raises `FileNotFoundError`, a type
`except ValueError` does not catch, so that path would surface as an unhandled traceback
rather than the design's promised "formatted message to stderr, exit 1" (§6 edge cases,
"FILE parse errors").

Consequence: half of the claimed error-handling surface of the CLI's single catch clause is
unverified, and the untested nonexistent-`--lsp`-file case looks likely to violate the
design's own stated contract — a regression here (or a pre-existing gap) would ship
unnoticed.

Fix: add CLI tests for (a) a syntactically-invalid or nonexistent `--grammar` path and (b) a
nonexistent `--lsp` path, each asserting exit code 1, empty stdout, and a non-empty,
formatted stderr message.

## test-5

File: `fltk/lsp/test_dogfood.py::test_dogfood_spec_loads_against_its_own_grammar`.

`assert len(resolved.global_child_matchers) == 2` only checks a count. It does not check
which two matchers resolved, what literal text they match, or what paint they carry.

Consequence: this assertion is satisfied by any two global matchers regardless of
correctness — e.g. if the global anchor accidentally resolved to the wrong literal(s) or the
wrong paint (`punctuation` vs. something else), the count would still be 2 and the test
would still pass.

Fix: assert on the matcher contents directly, e.g.
`{m.match for m in resolved.global_child_matchers} == {lsp_config.ByLiteralText(";"), lsp_config.ByLiteralText(":")}`
and that each matcher's paint token is `"punctuation"`.

## Otherwise solid

`test_engine.py` and `test_highlight_cli.py` are largely real behavioral tests (not smoke
tests): they check specific token types at specific substrings, use golden exact-string ANSI
output for the CLI defaults case, exercise the `!`-grammar rejection path with a real
inline-bearing grammar, exercise both `from_paths` branches (with/without an `.fltklsp`
file), and exercise the `start_rule=None` fallback. No vacuous assertions, no
over-mocking (`AnalysisEngine`/CLI are exercised end-to-end against real grammars/parsers),
no brittle implementation-detail assertions.
