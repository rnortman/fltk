# Efficiency review — increments 7-8 (rust-fltkfmt)

Commit reviewed: 25cd5dcab7489fc1cb05c6c3e29009a170130d0f (base 78eacab)
Scope of diff: `Makefile` (4 check-common lines), `tests/test_fltkfmt_parity.py` (new),
implementation-log.md (notes only).

## efficiency-1 — Python reference reparses/reunparses each grammar once per render config

File: `tests/test_fltkfmt_parity.py:80-85` (`_py_format`), driven by the
`_CORPUS` × `_CONFIGS` parametrization (lines 53-58, 119-121).

The problem: `_py_format` runs the full `parse_text` → `unparse_cst` → `render_doc`
pipeline on every parametrized case. The test matrix is 8 grammars × 2 configs = 16
cases, but `parse_text` (the pure-Python packrat parse, `plumbing.py:169-200`) and
`unparse_cst` (`plumbing.py:302`) depend only on the file `text`, not on
`max_width`/`indent_width` — only `render_doc` consumes the config. So for each grammar
the parse+unparse is executed twice (once per config) when one would suffice; 8 of the
16 parse+unparse passes are pure redundancy. The grammar/parser/unparser *generation*
is already `functools.cache`d (lines 60-83), but the per-input parse and unparse are not.
`fltkg.read_text()` (line 124) is likewise re-read per config (each of the 8 files read
twice), though that cost is negligible next to the parse.

Consequence: test-suite wall time on every `pytest tests/test_fltkfmt_parity.py` (and
every full-suite run / CI). The pure-Python FLTK parser is the heaviest step here;
parsing the larger grammars (e.g. `fegen.fltkg`) a second time per file roughly doubles
the Python-side work of this module for no added coverage. Bites on each test run; grows
linearly if more render configs are added to `_CONFIGS`.

Fix direction: split the config-independent stage from rendering. Add a helper such as
`@functools.cache def _py_doc(text: str)` returning the unparsed `Doc` (and a cached
`fltkg.read_text()`), then have `_py_format` only call `render_doc(_py_doc(text), cfg)`
per config. `render_doc` must not mutate the shared `Doc`; the renderer already treats
the doc as read-only input, so a cached doc is safe to render under multiple configs.

## Makefile (no findings)

The four added lines (`cargo-test-no-python`, `cargo-clippy-no-python`, `check-no-pyo3`,
`cargo-deny`) follow the existing per-standalone-crate pattern. `cargo test` and
`cargo clippy --all-targets` are separate build profiles (expected, consistent with the
sibling crates); `cargo tree`/`cargo deny` are metadata-only. No new inefficiency beyond
the established convention. The pytest `cargo build` fixture (session-scoped, incremental)
does not duplicate the Makefile `cargo test` build cost within a single hot path.
