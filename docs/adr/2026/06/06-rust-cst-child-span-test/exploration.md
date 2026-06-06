# Exploration: `rust-cst-child-span-test` TODO validity check

## Summary verdict

The TODO claim is **partially wrong** on a critical factual point: the Rust `fltk._native.Span`
intentionally does NOT expose `.start`/`.end` as Python attributes. The proposed test as written
(asserting `.start`/`.end` accessible) cannot pass against the Rust backend and would be testing
a contract that does not exist for Rust spans. The TODO is therefore either misdescribing the
required contract or proposing a test against the Python-only Span backend. Details below.

---

## 1. Does the focused test exist?

No focused test exists. Evidence:

- `tests/test_phase4_fegen_rust_backend.py:111-112` contains only the TODO comment:
  ```python
  # TODO(rust-cst-child-span-test): add a focused test that calls child_name() / child_value()
  # on a Rust-backed fegen node and asserts .start/.end are accessible and correct.
  ```
- No test in any file under `tests/` calls `child_name()` or `child_value()` on a Rust-backed
  fegen node and then accesses `.start`/`.end` on the result.
- The `test_fegen_rust_cst.py` `TestAppendChildRoundtrip` class (`tests/test_fegen_rust_cst.py:132-144`)
  calls `append_{label}` then `child_{label}` and checks identity (`retrieved is child`), but
  does not assert `.start`/`.end`.

## 2. Does `fltk2gsm.Cst2Gsm.visit_identifier/visit_literal/visit_regex` require `.start`/`.end`?

Yes, unconditionally. In `fltk/fegen/fltk2gsm.py`:

- `visit_identifier` (line 24-26):
  ```python
  def visit_identifier(self, identifier: cst.Identifier) -> gsm.Identifier:
      span = identifier.child_name()
      return gsm.Identifier(self.terminals[span.start : span.end])
  ```
- `visit_literal` (line 145-147):
  ```python
  def visit_literal(self, literal: cst.Literal) -> gsm.Literal:
      span = literal.child_value()
      return gsm.Literal(ast.literal_eval(self.terminals[span.start : span.end]))
  ```
- `visit_regex` (line 149-151):
  ```python
  def visit_regex(self, regex: cst.RawString) -> gsm.Regex:
      span = regex.child_value()
      return gsm.Regex(self.terminals[span.start : span.end])
  ```

All three call `span.start` and `span.end` on whatever `child_name()` / `child_value()` returns.

## 3. What do the Rust `child_name()` / `child_value()` accessors return?

The Rust methods (e.g. `cst_fegen.rs:3419-3443` for `Identifier.child_name`,
`cst_fegen.rs:3656-3680` for `RawString.child_value`) return a `PyObject` extracted from the
child tuple at index 1 (`tup.get_item(1)?.unbind()`). The return type is an opaque `PyObject`;
the Rust code does not constrain what type is stored there — whatever was inserted via
`append_name`/`append_value` is returned.

In the actual parser, children are `Span` objects (from `terminalsrc.TerminalSource.match`).
The question is whether those spans expose `.start`/`.end`.

## 4. Does the Rust `fltk._native.Span` expose `.start`/`.end` as Python attributes?

**No.** This is explicitly documented in `src/span.rs:54-56`:

> `start` and `end` are intentionally not exposed as Python attributes — all text access goes
> through `text()` / `text_or_raise()`.

The Rust `Span` struct (`src/span.rs:63-68`) is declared `#[pyclass(frozen, eq, hash)]`.
The `start: i64` and `end: i64` fields carry `pub(crate)` visibility and have no `#[getter]`
wrapper. The only `#[getter]` in the file (`src/span.rs:260`) is for `kind`.

This is confirmed by `tests/test_rust_span.py:61-69`:
```python
def test_no_start_attribute(self):
    with pytest.raises(AttributeError):
        _ = s.start

def test_no_end_attribute(self):
    with pytest.raises(AttributeError):
        _ = s.end
```

And by `tests/test_phase4_rust_fixture.py:181-183`:
> "The Rust fltk._native.Span intentionally does NOT expose .start/.end as Python attributes.
> The API Contract for span-read as used by fltk2gsm.py does not require .start/.end..."

## 5. How does `fltk2gsm` work at all with the Rust backend?

The fegen parser produces spans using `terminalsrc.TerminalSource`, which returns
`terminalsrc.Span` objects (the pure-Python dataclass, `fltk/fegen/pyrt/terminalsrc.py:33-36`).
Python `terminalsrc.Span` is a dataclass with `start: int` and `end: int` fields (both
exposed as normal Python attributes).

When the Rust fegen CST backend (`fegen_rust_cst`) is used, the CST *nodes* (Grammar, Rule,
Identifier, etc.) are Rust objects, but the *children stored inside them* are still
`terminalsrc.Span` instances — Python objects stored in the Rust `Py<PyList>` children list.
The Rust `child_name()` / `child_value()` methods return these Python Span objects unchanged.

So `span.start` and `span.end` in `fltk2gsm.py` are accessed on `terminalsrc.Span` (Python),
not on `fltk._native.Span` (Rust). The TODO claim that `.start`/`.end` must be accessible on
"Rust-backed CST child-accessor results" is true only in the sense that the results are
`terminalsrc.Span` Python objects; the Rust backend is not involved for the span objects
themselves.

## 6. Is a focused test feasible?

Yes, a focused test is feasible, but the assertion must be against `terminalsrc.Span` objects
(not `fltk._native.Span`). A working fixture:

- Import `fegen_rust_cst.Identifier` and `fegen_rust_cst.RawString` / `fegen_rust_cst.Literal`
  (already exercised in `tests/test_fegen_rust_cst.py`; the classes are importable via
  `fltk._native.fegen_cst` and the separately-built `fegen_rust_cst` module).
- Append a `terminalsrc.Span` as a child via `append_name()`.
- Call `child_name()` and assert `.start`/`.end` on the returned `terminalsrc.Span`.

The `tests/test_phase4_fegen_rust_backend.py` file already skips when `fegen_rust_cst` is not
built (`pytest.importorskip` at line 29), making it the correct location for such a test.

## 7. AC8 indirect coverage

`TestAC8RealCst2GsmRustBackend.test_simple_grammar_rust_equals_python`
(`tests/test_phase4_fegen_rust_backend.py:67-71`) and its peers do exercise the
`visit_identifier` / `visit_literal` / `visit_regex` paths against the Rust backend. A
regression in `child_name()` or `child_value()` returning the wrong value would cause the
`python_result == rust_result` assertion to fail. However, a regression that changed what
*type* of object is returned by `child_name()` (e.g. returning a Rust Span that lacks `.start`)
would surface only as an `AttributeError` inside `visit_identifier`, not as a clean equality
failure, making root-cause diagnosis harder.

## Conclusion

The TODO is valid in asserting the test gap is real and diagnostically useful, but the claim
that `.start`/`.end` must be accessible on Rust-backed child-accessor results is misleading:
the actual objects returned are `terminalsrc.Span` (Python), which have `.start`/`.end` as
normal dataclass fields. A correct focused test would call `child_name()` on a Rust-backed
`Identifier` node with a `terminalsrc.Span` child appended, then assert `result.start` and
`result.end`.
