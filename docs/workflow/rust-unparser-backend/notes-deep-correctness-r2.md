# Deep correctness review (r2) — Rust unparser backend, batch 2

Commit reviewed: e65e4f66bf2d466637df6f94744fa85abc7d239c (base d5914359bd41d526caacc18db82ef0f4c0d5c4b8)
Scope: `crates/fltk-unparser-core/src/render.rs`, `.../result.rs`, `.../lib.rs` (module wiring),
`fltk/unparse/gsm2unparser_rs.py` (generator scaffold), `tests/test_rust_unparser_generator.py`.

No findings.

## What was verified (parity with the Python source, the stated goal)

`render.rs` vs `fltk/unparse/renderer.py` — traced every arm:
- Root wrapped in `Group(doc)`; queue is front-expanded/front-consumed mirroring
  Python `pop(0)`/`insert(0, …)`.
- `Output::append_content`/`break_line` reproduce the Python nested-closure logic exactly,
  including the empty-text guards (`if text and at_beginning_of_line` / `if text`).
- Column width uses `chars().count()` == Python `len(str)` (code points). Match.
- `HardLine`: `0..=*blank_lines` == Python `range(1 + blank_lines)` (blank_lines+1 newlines).
- `Text`/`Comment` newline splitting + per-line re-indent matches; Rust `split('\n')` and Python
  `split("\n")` agree on empty-string (one empty element) and trailing-newline cases.
- `Group` fit check: `remaining_width = max_width - current_column` computed as `isize`;
  negative remaining correctly short-circuits in `fits` (`width < 0 => false`), matching Python.
- `fits` is a faithful port: per-line `column > width` checks, HardLine forces break,
  unhandled spec/Join nodes silently skip (Python `_fits` has no else either), and the
  `Group` sub-item is re-pushed Flat.
- Render-time `panic!` on `Join`/`AfterSpec`/`BeforeSpec`/`SeparatorSpec` corresponds to the
  Python `else: raise ValueError` (those four are exactly the unhandled types in Python `render`).
- Match is exhaustive over the `Doc` enum (doc.rs, batch 1) — every variant is handled.

`result.rs` vs `pyrt.py` `UnparseResult`: `new()` stores accumulator+new_pos; `doc()` delegates
to `accumulator.doc()`, matching the Python `.doc` property. Faithful.

`gsm2unparser_rs.py`: only emits header + unit struct + `new()` so far (batch scope). Memoization,
cst-mod-path import selection (suffix `cst` => direct, else aliased), and source-name escaping are
correct; no logic hazards.

## Considered and dismissed (not findings)
- Integer width arithmetic (`isize` column, `usize` current_column/indent): overflow only at
  unrealistic magnitudes (>2^63 columns / ~10^18 nest levels); Python is unbounded but the Rust
  path cannot be reached with feasible input. Not flagged.
- `fits` takes the queue by value (Python passes `test_queue.copy()`); no aliasing, queue is
  single-use. Equivalent.
