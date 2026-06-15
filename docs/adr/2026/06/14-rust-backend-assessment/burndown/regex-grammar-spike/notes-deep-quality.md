# Quality review — regex-grammar-spike

Commit reviewed: 8828282

## quality-1

**File:** `fltk/fegen/regex_corpus.py:67-83`

`classify_pattern`'s docstring says it drives the parser directly "to avoid importing the
full plumbing stack (which carries heavy codegen imports) from a module that may be imported
at test-collection time." But `parse_grammar_file` is imported from `fltk.plumbing` at the
top of the same module (line 34), unconditionally. If plumbing is heavy, the savings claimed
by the direct-parser path are already undone at import time — the comment is a stale
justification for an optimization that was never completed.

**Consequence:** Future maintainers will read the docstring and believe the module is
import-weight-conscious. If someone later tries to split collect/classify from the CLI (a
natural next step), they may preserve or even strengthen a layout that gives no real benefit,
carrying the confusion forward.

**Fix:** Either (a) move the `parse_grammar_file` import inside `_run_cli` so the heavy import
is genuinely deferred (and the claim becomes true), or (b) simply remove the justification
from `classify_pattern`'s docstring — it is only needed to explain the API shape, which needs
no explanation if the claimed reason is absent.

---

## quality-2

**File:** `fltk/fegen/regex_corpus.py:58` (calling `gsm._for_each_item`)

`collect_regexes` calls `gsm._for_each_item`, a private function (name-mangled with a leading
underscore, living only inside `gsm.py`). This is the only cross-module call to that
function. Within `gsm.py` itself it is used three times for internal validation passes
(`_collect_underscore_only_label_errors`, `_collect_repeated_nil_errors`,
`_mark_trivia_reachable_in_items`).

**Consequence:** `_for_each_item` carries no public-API contract. Any internal refactor of
`gsm.py`'s walk machinery will break `regex_corpus.py` silently (mypy/pyright won't flag
private-name access from other modules as an error; the break shows up at runtime or in the
next `make check`). Because `regex_corpus.py` is the first in-tree cross-module caller, it
also sets a precedent: the next consumer of the walk sees this pattern and repeats it.

**Fix:** Promote `_for_each_item` to a public name (`for_each_item`) in `gsm.py` — it is
already well-documented and useful. Alternatively, add a public `iter_regexes(grammar)` to
`gsm.py` that encapsulates the walk, so callers never need to touch the structural walk API
at all. Either direction gives the caller a stable, tested contract.

---

## quality-3

**File:** `tests/test_regex_grammar_corpus.py:185-199` (`test_regex_fltkg_self_referential`)

The self-referential count pin `assert len(patterns) == 12` is a magic number with no
derivation comment. The only guidance given is "If this count changes, update the expected
value and review the new pattern." A maintainer adding a new terminal to `regex.fltkg` will
see a failing count and update it without knowing whether the change is correct.

**Consequence:** The count assertion's value as a change-detector degrades over time:
reviewers learn to bump it reflexively rather than investigating what changed and why. The
pattern is mildly contagious — similar tests in future grammars will copy this shape. This
is especially fragile here because the count is emergent from a generated artifact
(`regex_cst.py` / `regex_parser.py`) that is itself committed, so the expected count might
quietly become wrong after a Makefile-level regen without any test failure.

**Fix:** Replace the raw count assertion with an `assert_no_new_patterns` approach: persist
the set of distinct patterns (e.g. as a frozenset literal in the test or a `patterns.txt`
fixture file), assert the observed set equals the expected set, and print a diff on failure.
This way a regression names the offending pattern rather than only the count. At minimum, add
a comment that lists the 12 expected patterns inline so a future reader can verify the count
without reading `regex.fltkg`.

---

## quality-4

**File:** `tests/test_regex_grammar_corpus.py:23`

`test_regex_grammar_corpus.py` imports `_run_cli` (a private function) directly from
`fltk.fegen.regex_corpus`:

```python
from fltk.fegen.regex_corpus import _run_cli, classify_pattern, collect_regexes
```

The function is used in `test_cli_entry_point_accepts_in_tree_grammar` to smoke-test the
CLI without spawning a subprocess. That goal is legitimate, but importing a private symbol
into a test file makes the test structurally dependent on the module's internal layout and
signals to future readers that calling `_run_cli` directly is an intended pattern.

**Consequence:** If `_run_cli` is later renamed, inlined, or refactored (e.g. to accept a
`Path` directly instead of an `argv` list), the test breaks without any type-system warning.
More broadly, a test that imports private symbols to reach internal behavior is harder to
refactor than one that exercises the public interface.

**Fix:** Rename `_run_cli` to `run_cli` (making it public), or expose a thin public
`main(argv)` function. The function's behavior is already externally documented (the CLI
command in `design.md` and in the module docstring), so there is no encapsulation rationale
for the leading underscore.

---

## quality-5

**File:** `tests/test_regex_grammar_corpus.py:57-60` (module-level grammar parsing)

`_FEGEN_CORPUS` and `_REGEX_CORPUS` are built by calling `parse_grammar_file` at module
import time (pytest collection time):

```python
_FEGEN_CORPUS: list[tuple[str, str]] = _corpus_cases(_FEGEN_FLTKG)
_REGEX_CORPUS: list[tuple[str, str]] = _corpus_cases(_REGEX_FLTKG)
```

This is necessary to satisfy `pytest.mark.parametrize`, which requires the parameter list to
be known at collection time. However, it means a parse failure (missing file, grammar
syntax error, import error from `fltk._native` not yet built) surfaces as a collection error
rather than a test failure, producing an obscure traceback rather than a named failing test.

**Consequence:** A developer who has not yet run `maturin develop` sees a confusing
collection-time `ImportError` or `FileNotFoundError` rather than a clear test failure with
context. This is also true today for the adversarial suite (which imports
`fltk.fegen.regex_corpus` at collection time, and that module imports `regex_parser` which
depends on `_native`), but the corpus test compounds it by also running I/O at import.

**Fix:** Use `pytest.fixture` + `pytest.param` with `indirect=True`, or use a
`pytest_generate_tests` hook that defers grammar loading to test setup. If keeping the
current approach for parametrize compatibility, at minimum wrap `_corpus_cases` calls in a
`try/except` that re-raises as `pytest.skip` with a clear message (`"fltk._native not built
— run maturin develop first"`), so collection-time failures produce readable output rather
than raw tracebacks. This is a low-severity usability issue but the pattern is likely to be
copied by the next grammar that adds a corpus test.
