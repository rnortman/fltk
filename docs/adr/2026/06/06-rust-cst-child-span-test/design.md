# Design: rust-cst-child-span-test

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human. (Note retained per authoring protocol; applies to this doc.)

Scope: test-only. No source changes. See `request.md` for the spec and `exploration.md` for the source-cited contract; this doc does not restate them.

## Root cause / context

`fltk2gsm.Cst2Gsm` slices `self.terminals` using `.start`/`.end` read off the object returned
by a child accessor, in three visitors (`fltk/fegen/fltk2gsm.py:24-26`, `:145-147`, `:149-151`):

```python
span = identifier.child_name()        # visit_identifier
self.terminals[span.start : span.end]
```
(same shape for `child_value()` in `visit_literal` / `visit_regex`).

The returned object is **not** the Rust `fltk._native.Span` — that type intentionally omits
`.start`/`.end` (`src/span.rs:54-56`; `tests/test_rust_span.py:61-69` asserts `AttributeError`).
With the Rust fegen backend the nodes are Rust objects but the *children stored in them* are
pure-Python `fltk.fegen.pyrt.terminalsrc.Span` dataclasses (`start: int`, `end: int` as normal
fields). The Rust `child_name()`/`child_value()` accessors return whatever PyObject was appended,
unchanged (`cst_fegen.rs:3419-3443`, `:3656-3680`: `tup.get_item(1)?.unbind()`), so they hand
back the `terminalsrc.Span` verbatim.

Gap: no focused test asserts that a Rust-backed accessor returns an object exposing usable
`.start`/`.end`. The only coverage is the AC8 equality tests
(`tests/test_phase4_fegen_rust_backend.py:67-87`), which exercise the path indirectly. A
regression in accessor return *type* would surface as an `AttributeError` buried inside
`visit_identifier`, not as a localized failure pointing at the accessor. This design adds the
localized regression test and retires the TODO.

The premise of the original `TODO(rust-cst-child-span-test)` is corrected: the test asserts
`.start`/`.end` on the returned **`terminalsrc.Span`**, never on a Rust span. Asserting on a Rust
span would test a contract that deliberately does not exist.

## Proposed approach

One file touched: `tests/test_phase4_fegen_rust_backend.py` (already gated by
`pytest.importorskip("fegen_rust_cst")` at line 29; already imports `terminalsrc as tsrc` at
line 38 and `fegen_rust_cst` as the module object).

Add one test class, `TestChildSpanAccessorReturnsUsableSpan`, near the existing TODO (which is
removed). The test mirrors `TestAppendChildRoundtrip`
(`tests/test_fegen_rust_cst.py:132-144`): construct node → `append_<label>` a child → call
`child_<label>()` → assert on the result. The difference: the appended child is a real
`tsrc.Span(start, end)` and the assertion is on `.start`/`.end` rather than identity.

Cases (label/accessor pairs confirmed present in the fegen Rust CST surface via
`CLASS_LABEL_INFO` in `tests/test_fegen_rust_cst.py:36-52`):

- `fegen_rust_cst.Identifier` — `append_name(span)` then `child_name()` → matches
  `visit_identifier`'s `child_name()`.
- `fegen_rust_cst.Literal` — `append_value(span)` then `child_value()` → matches
  `visit_literal`'s `child_value()`.
- `fegen_rust_cst.RawString` — `append_value(span)` then `child_value()` → matches
  `visit_regex`'s `child_value()` (the regex node is `RawString`; cf. `visit_regex(self, regex:
  cst.RawString)` at `fltk2gsm.py:149`).

Each case:

1. `span = tsrc.Span(start=3, end=9)` (use distinct nonzero, non-equal values so a swapped or
   zeroed field fails).
2. `node = fegen_rust_cst.<Class>()`; `node.append_<label>(span)`.
3. `result = node.child_<label>()`.
4. Assert `result.start == 3` and `result.end == 9`.

Parametrize over the three `(class, append_method, child_method)` triples to keep one test body.

Optional strengthening (within scope, decided): also assert
`isinstance(result, tsrc.Span)` — pins the contract that the accessor returns the Python Span
type, making a future swap to a `.start`/`.end`-less type fail at a clear assertion rather than
relying on the attribute read alone.

Do **not** assert `result is span` as the primary check — identity is already covered by
`TestAppendChildRoundtrip`; this test's job is the `.start`/`.end` read contract that
`fltk2gsm` depends on.

## Edge cases / failure modes

- **`fegen_rust_cst` not built.** Module-level `importorskip` (line 29) skips the whole file.
  A CI lane where this file is entirely skipped is already flagged as a failure signal by the
  file's module docstring; no new handling needed.
- **Accessor on empty node.** Calling `child_<label>()` with nothing appended could return
  `None` or raise; not exercised — every case appends first. (The existing roundtrip tests
  append before reading; we follow that.)
- **Two backends, one module name.** The file uses the standalone `fegen_rust_cst` extension
  (separately built) rather than the embedded `fltk._native.fegen_cst`. The TODO and existing
  tests in this file use `fegen_rust_cst`; we stay consistent so the test runs under the same
  build gate.
- **Regression this catches:** an accessor changed to return the Rust `Span` (no `.start`) →
  `AttributeError` at `result.start`, or the `isinstance` assertion fails first — either way a
  clean, localized failure naming the accessor, instead of a stack trace inside a visitor.
- **What it deliberately does not catch:** end-to-end parse correctness (that is the AC8 tests'
  job, intentionally not duplicated here).

## Test plan

After this change, `tests/test_phase4_fegen_rust_backend.py` contains, in addition to the
existing AC6/AC8 tests:

- `TestChildSpanAccessorReturnsUsableSpan::test_child_accessor_span_start_end` — parametrized
  over `Identifier/name`, `Literal/value`, `RawString/value`; asserts `.start`/`.end` (and
  `isinstance(..., tsrc.Span)`) on the accessor result.

Verification:
- `uv run pytest tests/test_phase4_fegen_rust_backend.py` passes with `fegen_rust_cst` built;
  skips cleanly without it.
- Sanity (manual, not committed): temporarily make an accessor return a Rust `Span` and confirm
  the new test fails at its own assertion, not deep in a visitor.

Cleanup:
- Remove the `TODO(rust-cst-child-span-test)` comment block
  (`tests/test_phase4_fegen_rust_backend.py:111-113`).
- Remove the matching `rust-cst-child-span-test` entry from `TODO.md`.

## Open questions

None. The spec (`request.md`) is unambiguous on contract, location, and pattern; the
`isinstance` strengthening and the three-case parametrization are the only authored choices, and
both are conservative and within stated scope.
