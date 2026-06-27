# Deep efficiency review — batch 10 (§4 test code)

Commit reviewed: fa22e182702d3ea1c1ec5e464345ab006941c9e9 (base 028583414d5943b6e134a78c922868f45cb59361)

Scope: test code in the diff —
`tests/test_rust_unparser_parity_fixture.py`, `tests/unparser_parity.py`,
`tests/rust_parser_fixture/src/native_tests.rs`, plus `lib.rs`/`Makefile`/`unparser_default.rs`
wiring. `unparser_default.rs` is pure generator output (header says "Do not edit"); its
emission patterns belong to the generator batch, not this one — not re-reviewed here.

## efficiency-1 — parity corpus re-parses both backends on the render-config axis

File: `tests/test_rust_unparser_parity_fixture.py:171-204` (the two `@pytest.mark.parametrize`
stacks), via `_py_cst` (`:87`) and `_rust_node` (`:93`).

Problem: each test is parametrized over `_CORPUS` (42 entries) **and** `_CONFIGS`
(`(80,4)`, `(8,2)`). Both `_py_cst(text, rule)` and `_rust_node(text, rule)` are called once
per `(rule, text, config)` cell, but the parse result depends only on `(rule, text)` — the
render width/indent (`_CONFIGS`) feeds only resolve/render, never the parse. So each
`(rule, text)` is parsed once per config and once per test function (`_fltkfmt` and
`_default` both reparse the same inputs), i.e. ~4× per backend when 1× would do. The
generated parser/unparser classes are already cached in module globals, but the per-input
CSTs are not. This differs from the established `test_rust_parser_parity_fixture.py`
precedent, whose re-parse axis (`capture_trivia`) genuinely changes the parse output —
here the second axis does not.

Consequence: redundant Python+Rust parses (~228 of ~304 are duplicates). Cost shows up as
extra test-suite wall time; with the current tiny inputs (a few chars each) it is
negligible, and it only starts to bite if the corpus grows large or gains
longer/deeper-recursion inputs. Low magnitude, but a genuine repeated-computation pattern
in the lane.

Fix direction: memoize the parsed CSTs by key. A small module-level dict keyed by
`(backend, rule, text)` wrapping `_py_cst`/`_rust_node` (the CSTs are read-only to the
unparser, so sharing across cells is safe) collapses the parse work back to 1× per backend
per `(rule, text)`. Alternatively move the parse into a `(rule, text)`-scoped fixture so the
config axis reuses it.

## Clean

- `tests/unparser_parity.py`: per-call `unparser_class(text)` construction is necessary
  (terminals differ per input); no redundant work.
- `tests/rust_parser_fixture/src/native_tests.rs`: `render_native!` builds a fresh parser
  per case (independent tests), `Unparser::new()` is a zero-field unit struct; nothing
  hot-path or repeated. Deep-tree (100k) tests are pre-existing, not in this diff.
- `lib.rs` / `Makefile` wiring: no efficiency concerns.
