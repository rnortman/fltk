# Deep correctness review — final round, 87dbc0d..9a085e9

Scope reviewed: `fltk/lsp/engine.py` (§4.7), `fltk/lsp/highlight_cli.py` + `pyproject.toml`
scripts entry (§4.8), `fltk/lsp/fltklsp.fltklsp` dogfood fixture (§8), and the three new test
files. Verified against surrounding code: `plumbing.generate_parser`/`parse_text`/`ParseResult`
field usage, `classify.classify`'s grammar contract (engine correctly passes the
trivia-classified `ParserResult.grammar`, not the pre-trivia input grammar), `LspConfigError`'s
`ValueError` ancestry vs. the CLI's `except ValueError`, `prepare_analysis_grammar`'s
`ValueError` on `INLINE`, and every dogfood-spec anchor against `fltklsp.fltkg` (all resolve:
`rule`/`scope`/`def`/`ref`/`namespace`/`label` literals, `rule_name`/`part`/`value` labels,
global `";"`/`":"` literals). Hand-traced the dogfood test's nine span assertions against the
painter (rule-block literal/label matchers, global literal matchers, default fallback for the
bare `comment` identifier) — each yields exactly one token with the asserted bounds and type.
`_render`'s cursor/gap logic traced (correct given the classifier's sorted/non-overlapping/
in-bounds invariants; theme covers all 16 legend members and `none` never reaches output).
All 13 new tests pass; additionally probed empirically: self-highlighting the committed
dogfood spec (93 tokens, invariants hold, leading comment block painted `comment`), empty and
whitespace-only input (`tokens=[]`, `error=None` — the empty parse succeeds, correctly
distinguished from the `tokens=None` failure encoding), a `def`/`ref`/`namespace` sample
(def-keyword paint, `*` wildcard → default `operator`, dotted kinds → `property`), and the
`python -m` CLI end-to-end on the dogfood files (exit 0, correct SGR codes per theme).

No findings.

Out-of-lane observations passed over deliberately (error-handling reviewer's lane, noted only
so they aren't assumed unexamined): `FileNotFoundError` from a missing FILE/`--grammar`/`--lsp`
path escapes `highlight_cli.main`'s `except ValueError` (traceback rather than the designed
formatted-stderr path); `generate_parser`'s per-construction `sys.modules` entry is never
released (preexisting plumbing behavior, not introduced by this round).
