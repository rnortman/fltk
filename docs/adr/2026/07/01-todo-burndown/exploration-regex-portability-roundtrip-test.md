# Exploration: TODO(regex-portability-roundtrip-test)

Base commit: 8fd5ecf. Facts only, file:line grounded, no prescriptions.

## TODO text (verbatim, ground truth)

`TODO.md:54-56`:

> ## `regex-portability-roundtrip-test`
>
> Design §7 specifies a "positive-control round-trip" test that pins the committed
> `regex_parser.py` as having been generated from a clean `regex.fltkg` — either by
> regenerating into a temp dir and comparing, or by asserting the committed parser
> re-classifies all admitted/excluded test cases identically. The whole-tree
> completeness test partially discharges this (grammar drift that changes
> classification on in-tree patterns surfaces there), but it does not catch drift
> that reclassifies no currently-committed pattern. Add a round-trip gate, e.g. a
> test that generates the parser into a temp dir and byte-compares it to the
> committed `regex_parser.py`, or extends the completeness test to include all
> unit-test `_PORTABLE_PATTERNS` / `_NON_PORTABLE_PATTERNS` cases as an oracle.
> Location: `tests/test_regex_portability.py` (new test function),
> `fltk/fegen/regex_parser.py` (committed artifact being guarded).

Code-side comment, `tests/test_regex_portability.py:485-489`:

```
# TODO(regex-portability-roundtrip-test): add a round-trip gate that pins the
# committed regex_parser.py as having been generated from a clean regex.fltkg,
# e.g. regenerate into a temp dir and byte-compare, or run all _PORTABLE_PATTERNS /
# _NON_PORTABLE_PATTERNS through both the committed parser and a freshly generated one.
# See design §7 "positive-control round-trip" and TODO.md.
```

Exactly one `TODO(regex-portability-roundtrip-test)` occurrence found in the tree
(`grep -rn "regex-portability-roundtrip-test"` across `*.py/*.md/*.fltkg`): the
`TODO.md` entry and this one code comment. No second/duplicate marker exists.

## Does a round-trip/regen-compare gate already exist?

No regen-and-compare test exists anywhere in the tree today. `grep` for
`regenerat|byte-compar|filecmp|tempfile.TemporaryDirectory` across `tests/*.py`
matches only `tests/test_regex_portability.py` itself (the file holding this TODO's
`tempfile.TemporaryDirectory` use, which is for the unrelated
`test_genparser_cli_exits_nonzero_on_non_portable_grammar` subprocess test at
`tests/test_regex_portability.py:456-482`, not a round-trip gate).

However, the **lighter oracle form** described in the TODO's second option ("extends
the completeness test to include all unit-test `_PORTABLE_PATTERNS` /
`_NON_PORTABLE_PATTERNS` cases as an oracle") is **already implemented**, just not
under that name:
- `test_portable_pattern_returns_no_issue` (`tests/test_regex_portability.py:159-166`)
  parametrizes `_PORTABLE_PATTERNS` (defined at lines 72-156) through
  `check_regex_portable`, which calls the committed `regex_parser.Parser`
  (`fltk/fegen/regex_portability.py:37,89-90`).
- `test_non_portable_pattern_returns_issue` (`tests/test_regex_portability.py:225-237`)
  does the same for `_NON_PORTABLE_PATTERNS` (lines 173-222).

This is exactly the "committed parser re-classifies all admitted/excluded test cases"
half of the TODO's disjunction — both lists already run against the committed parser
on every test run. What is *not* present is the other half: nothing regenerates
`regex_parser.py` from `regex.fltkg` into a temp dir and compares it (by bytes or by
re-running the same pattern lists through the fresh copy) against the committed file.
This matches a prior finding in
`docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-portability-lint/judge-verdict-deep.md:14-25`
(test-4 disposition write-up), which explicitly states: "The *lighter* oracle form
the reviewer suggested … is **already present** … What remains genuinely uncovered
is the **regen-into-temp-dir byte-compare**, which depends on whether the
generator/`make gencode` should be invoked inside the test environment — an
environmental tradeoff the design itself flags as open."

The original design doc's §7 (`docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-portability-lint/design.md:621-626`)
states the same gate, verbatim:

> **Positive-control round-trip for the committed validator parser (§6 drift):** a
> test that pins the committed `regex_subset_parser.py` actually came from a clean
> `regex_subset.fltkg` — e.g. regenerate the parser into a temp dir and assert it
> matches the committed file, or (lighter) assert the committed parser re-parses the
> in-tree corpus and the admitted/excluded unit sets identically.

(Naming note: the design doc predates the implementation's renaming of
`regex_subset.fltkg`/`regex_subset_parser.py` to `regex.fltkg`/`regex_parser.py` —
see `tests/test_regex_portability.py:14-16` docstring, which documents this rename
explicitly.)

The TODO's disposition history is recorded at
`docs/adr/2026/06/14-rust-backend-assessment/burndown/regex-portability-lint/dispositions-respond-round1.md:71-75`
(test-4): disposition "TODO(regex-portability-roundtrip-test)", action "Added
`TODO(regex-portability-roundtrip-test)` in `TODO.md` and a comment in
`tests/test_regex_portability.py` before the whole-tree completeness check."

## Byte-compare feasibility given the regen → `make fix` → commit workflow

Empirically tested live against the current tree (base commit 8fd5ecf):

1. Running the raw generator (`uv run python -m fltk.fegen.genparser generate
   --protocol fltk/fegen/regex.fltkg regex fltk.fegen.regex_cst --output-dir
   <tmpdir>`) produces a `regex_parser.py` that is **1648 lines**, vs. the committed
   file's **2436 lines**. A raw `diff` against the committed file has **2817 differing
   lines** — almost entirely formatting (missing blank lines, unwrapped long lines,
   `typing.Optional[X]` vs. `X | None`, etc.), not semantic content. A naive
   byte-compare of raw-generator-output vs. committed file would fail on every run,
   confirming CLAUDE.md's statement that "Generated code … is not expected to pass
   ruff formatting checks straight out of the generator."
2. Running `ruff format` alone (no `ruff check --fix`) on the fresh output still
   leaves **1066 differing lines** against the committed file — `ruff format` does
   not rewrite `typing.Optional[X]` to `X | None` or other `ruff check --fix`-only
   rules (e.g. pyupgrade-family fixes); those come from `ruff check --fix` in the
   `make fix` target (`Makefile:84-86`: `ruff check --fix .` then `ruff format .`).
3. Running the full `make fix` sequence (`ruff check --fix` then `ruff format`) on
   the fresh output — the exact sequence CLAUDE.md prescribes after regenerating —
   makes the freshly generated file **byte-identical (0-line diff)** to the committed
   `fltk/fegen/regex_parser.py`. `ruff check --fix` reported "710 errors (342 fixed,
   368 remaining)" (residual errors are unfixable-in-place lints like `E501` line-too-
   long on generated lines — these remain as unfixed lint findings in the committed
   file too, not blockers to the diff converging to zero).

Conclusion (fact, not prescription): a byte-compare gate is feasible **only if** it
applies the same `ruff check --fix` + `ruff format` normalization the `make fix`
target applies before comparing; a byte-compare of unnormalized generator output
against the committed (post-`make fix`) file would fail spuriously on every run
regardless of grammar/generator correctness.

## `_PORTABLE_PATTERNS` / `_NON_PORTABLE_PATTERNS` shape

Both are flat `list[str]` module-level constants in `tests/test_regex_portability.py`:
- `_PORTABLE_PATTERNS` (`tests/test_regex_portability.py:72-156`): 60 raw regex-body
  strings, grouped by comment into categories (character classes, class shorthands,
  alternation, anchors, word boundary, groups, quantifiers/bounded, escaped
  metacharacters, three "in-tree patterns from fegen.fltkg" literal patterns,
  leading/trailing/solo-dash-in-class cases, empty groups/branches, control/unicode
  escapes, bare closer literals, non-leading caret in class, shorthand-as-class-
  member, escape-range endpoints, the escaped-bracket near-miss, dot metacharacter,
  lazy quantifiers, non-capturing group variations, flag-scoped groups).
- `_NON_PORTABLE_PATTERNS` (`tests/test_regex_portability.py:173-222`): 33 raw
  regex-body strings, grouped by comment (POSIX classes, Unicode properties, set
  operations, lookahead/lookbehind, backreferences/named groups, empty character
  class, range-with-shorthand-endpoint, class assertions/anchors, bare `{` literal,
  divergent escapes including `\Z`/`\0`/`\07`/`[\0]`, verbose flag, flag negation,
  interior literal dash, `&&` set-intersection look-alikes).

Both lists are already consumed as pytest `@pytest.mark.parametrize` inputs at
`tests/test_regex_portability.py:159` and `:225` respectively, run against
`check_regex_portable` (`fltk/fegen/regex_portability.py:60`), which in turn
constructs `fltk.fegen.regex_parser.Parser` (imported at
`fltk/fegen/regex_portability.py:37`) — i.e., the committed parser module, not a
freshly generated one.

## Related TODO cross-reference

`tests/test_regex_portability.py:505-509` and `TODO.md:50-52` document a second,
distinct TODO — `TODO(regex-portability-target-list-drift)` — about
`_RUST_PARSER_TARGET_GRAMMARS` (`tests/test_regex_portability.py:512-516`) being
hand-copied from the `Makefile`'s `gencode` recipe grammar list
(`Makefile:269-289`, `gen-rust-parser`-target grammars enumerated at lines ~276,
279, 284-285). That comment explicitly says to "tie this to the
`gencode-drift-gate` family" — a different TODO family from
`regex-portability-roundtrip-test`, not to be conflated with it.
