# Design review findings: native-span-init-error-context

Verified against base commit c03a801. Claims checked directly: gsm2lib_rs.py line
citations (172, 182, 193-196, 199-202) — all correct; committed `src/lib.rs:6,13,16`
drift — real (generator emits no `LineColPos`); sibling wrap pattern at
`crates/fltk-cst-core/src/py_module.rs:155-159` — exact match, including the
closure-block + fully-qualified `pyo3::exceptions::PyRuntimeError` shape; pyo3 0.29
`prelude.rs` (48 lines) contains no `exceptions` re-export — fully-qualified path claim
holds; `Makefile:275-277` gencode invocation, `fix` = ruff-only (84-86), no drift step in
`check-common` (39-51) — all correct; `_write_output_file` (`genparser.py:313-327`) is a
bare `write_text(src)` and `generate()` ends with `"\n"`, so the byte-for-byte drift-pin
premise is sound; `Path(__file__).parents[2]` from `fltk/fegen/test_gsm2lib_rs.py`
resolves to the repo root — correct; the drift-pin spec matches `_span_only_spec()`
(test_gsm2lib_rs.py:201-208) and the CLI's `no_cst` branch (`genparser.py:828-834`);
clockwork's only `gen-rust-lib` consumer (`clockwork/dsl/BUILD.bazel`, `fltk_pyo3_cdylib`
at ~76-81) does not use `register_span_types` — grep over the clockwork checkout confirms
zero `register_span_types` hits. Requirements coverage: all four request items (drift
fix, map_err wrap, regen, pin both with tests) plus the TODO.md/inline-comment sync map
to design sections 1-4. No internal contradictions; the one judgment call (comment
normalization) is explicitly decided and cheap to reverse.

## design-1: Test plan misses `test_gen_rust_lib_span_only_output` in `fltk/fegen/test_genparser.py`

- **Section:** "Test plan" — "All in `fltk/fegen/test_gsm2lib_rs.py`" and "Unchanged
  tests ... keep passing — they assert substrings the change preserves."
- **What's wrong:** The plan enumerates updates only in `test_gsm2lib_rs.py`. But
  `fltk/fegen/test_genparser.py::test_gen_rust_lib_span_only_output` (span-only CLI
  test, ~line 1564) asserts the exact old use line:
  `assert "use span::{SourceText, Span};" in src`. After the §1 drift fix the emitted
  line becomes `use span::{LineColPos, SourceText, Span};`, so this assertion fails.
- **Why:** Verified by reading the test at
  `fltk/fegen/test_genparser.py:1541-1581`; the file's own header says it covers the
  gen-rust-lib CLI subcommand, a surface the design changes.
- **Consequence:** An implementer following the test plan verbatim lands the generator
  change with a red test in `make test` / `make check` — either the change is blocked at
  the precommit gate or the implementer has to diagnose and patch an unplanned file
  mid-implementation. The design's "unchanged tests keep passing" claim is false as
  stated.
- **Suggested fix:** Add to the "Updated" list: `test_gen_rust_lib_span_only_output`
  (use-line update, optionally also `m.add_class::<LineColPos>()`), and optionally
  `assert "LineColPos" not in src` in `test_gen_rust_lib_standard_output` to mirror the
  planned `test_standard_output_no_span_types` update.

## design-2: Drift consequence overstated — "silently ... breaking the native module for every consumer of `Span.line_col` results" / "Nothing catches this automatically"

- **Section:** "Context / root cause" §1.
- **What's wrong:** Two overstatements. (a) A post-regen drop of `LineColPos` would
  *not* survive the existing gates silently: `make test` depends on
  `build-test-fixtures` → `build-native` (Makefile:94-97, 194-195), which rebuilds
  `fltk._native` from the regenerated `src/lib.rs`, and `tests/test_rust_span.py:11`
  does `from fltk._native import LineColPos` at module import — an immediate, loud
  ImportError in `make test`, which `make check` (the precommit hook) runs. What is true
  is narrower: nothing catches the *committed generator/output divergence itself* until
  someone regenerates. (b) Dropping `m.add_class::<LineColPos>()` would not break
  `Span.line_col()` *results* — pyo3 creates `#[pyclass]` type objects lazily on first
  instantiation, so returned `LineColPos` instances still work; what breaks is the
  module attribute / import surface (`fltk._native.LineColPos`, declared in
  `fltk/_native/__init__.pyi:14`).
- **Why:** Makefile:94-97/194-195, tests/test_rust_span.py:11,1096; pyo3 `add_class` is
  attribute exposure, not a precondition for instantiating a registered-elsewhere-or-not
  pyclass.
- **Consequence:** The design doc is the ADR-adjacent justification record; as written
  it misrecords what the existing safety net was, which could later be cited to justify
  further "we have no gate" work. It does not change what gets built here — the drift
  fix and the unit-level drift pin remain well justified (they catch the divergence at
  string level, without cargo or a rebuild, and before a commit is even attempted).
- **Suggested fix:** Reword to: the divergence is invisible until regen; after regen the
  drop would be caught by `make check` via the `test_rust_span` import, but only after a
  full native rebuild — the drift pin moves detection to a pure-Python unit test.

## design-3: Stale prose surfaces mentioning only "Span/SourceText" not updated (minor)

- **Section:** §1 "Teach the generator about `LineColPos`" — the change list covers the
  emitted use line, emitted comment, and add_class only.
- **What's wrong:** Two non-emitted description surfaces also say "Span/SourceText" and
  become inaccurate after the fix: `LibSpec.register_span_types` docstring
  (`gsm2lib_rs.py:99`: "emit Span/SourceText class registration") and the CLI help for
  `--register-span-types` (`genparser.py`, gen_rust_lib option help: "Emit
  Span/SourceText class registration and span module import"). The gen-rust-lib
  docstring's "Runtime-only path" prose is generic and fine.
- **Why:** Read both at the cited locations; neither is in the design's change list.
- **Consequence:** Minor doc rot only — an out-of-tree `gen-rust-lib` user reading
  `--help` would not learn that `LineColPos` must now be exported from their
  `mod span;`, which is exactly the edge case the design itself calls out for
  `--register-span-types` consumers.
- **Suggested fix:** Include both one-line doc updates in §1.
