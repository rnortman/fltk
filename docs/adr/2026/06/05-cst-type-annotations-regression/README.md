# Add a ruff formatting gate to precommit; defer CST type-annotation restoration

Status: Accepted
Date: 2026-06-05

## Context

Two distinct, unrelated annotation regressions exist in the repo (full
archaeology in [`exploration.md`](./exploration.md); ruff-restoration analysis
in [`ruff-investigation.md`](./ruff-investigation.md)).

1. **Cosmetic style drift in committed generated files.** The three
   `fltk/unparse/unparsefmt_{cst,parser,trivia_parser}.py` files were regenerated
   in commit `7914e57` (2026-01-13) via `ast.unparse()`, which emits
   lint-noncompliant Python: single quotes, `typing.Optional[X]` instead of
   `X | None`, extraneous parens, over-long lines, no import grouping, no trailing
   newline. Commit `d1d3452` (2026-05-25) ran `ruff format` to restore readable
   multi-line layout and incidentally normalized the annotation style on these
   files, but nothing in the toolchain *enforces* that this stays fixed. A future
   regeneration would silently re-introduce the drift, and the precommit
   `make check` would not catch a formatting-only regression because it had no
   `ruff format --check` step. The code generators do **not** self-format; raw
   `ast.unparse()` output is the sole serialization path
   (`genparser.py:108,183`).

2. **Genuinely missing CST-node type annotations.** Commit `214dbe1`
   (2026-05-28, PyO3 Phase 4 DI refactor) intentionally removed CST-typed
   parameter annotations from ~11 `visit_*` methods in `fltk/fegen/fltk2gsm.py`
   (e.g. `def visit_grammar(self, grammar: cst.Grammar)` became
   `def visit_grammar(self, grammar)`). This was deliberate: `Cst2Gsm.__init__`
   gained a `cst: ModuleType = _default_cst` dependency-injection parameter so it
   can accept either the Python dataclass CST or a Rust-backed CST extension
   module, and there is no static type / protocol for the injected module, so the
   parameter annotations were no longer reachable names.

[`ruff-investigation.md`](./ruff-investigation.md) confirms by direct
experiment that ruff (`ruff format` + `ruff check --fix`) makes **only
cosmetic** changes and cannot restore the intentionally-removed `fltk2gsm.py`
annotations. Ruff therefore addresses item 1 but is irrelevant to item 2.

## Decision

Add a ruff **formatting** gate to the precommit path, target-only:

- `make fix` runs `ruff check --fix` followed by `ruff format` (autofix +
  reformat).
- `make check` (which the precommit hook runs) gains a `ruff format --check`
  step, so any formatting drift in committed files — generated or
  hand-written — fails precommit.

This is a **make-target-only** approach. The code generators are deliberately
left un-modified: they continue to emit raw `ast.unparse()` output and do
**not** self-format. The accepted tradeoff is that a future regeneration can
re-introduce style drift, which will then surface as a `make check` failure
until someone runs `make fix`. This keeps the generators simple and makes the
gate the single source of truth for style, at the cost of a manual `make fix`
step after each regeneration.

Running `make fix` once resolves the current cosmetic regression on the three
committed `fltk/unparse/unparsefmt_{cst,parser,trivia_parser}.py` files.

## Deferred (not decided here)

Restoring proper CST-node type annotations to `fltk/fegen/fltk2gsm.py` (item 2
above) is explicitly **out of scope** for this ADR. Ruff cannot do it, and the
annotations were removed by design, not by accident. Re-introducing static
typing across the `ModuleType`-injected CST boundary is a separate, larger
piece of work requiring its own design cycle — most likely generating type
stubs (or a `Protocol`) for the CST module so that `visit_*` parameters can be
annotated against either the Python or Rust backend. This is recorded as
deferred future work and is not decided by this ADR.

## Consequences

- Formatting drift in any committed file (generated or hand-written) now fails
  precommit via `ruff format --check` in `make check`; `make fix` is the
  one-command remedy.
- The three `unparsefmt_*` generated files become style-clean after a single
  `make fix` run.
- Generators remain unformatted by design: regeneration can re-introduce drift,
  which the gate catches but does not auto-fix — a deliberate
  simplicity-vs-automation tradeoff.
- The `fltk2gsm.py` CST-type-annotation loss remains in place. It is type-valid
  under pyright today (only the parameter annotations are absent) and is left
  for a future dedicated design effort.
