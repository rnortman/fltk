Style note: concise, precise, complete, unambiguous. No padding.

Commit reviewed: f1423a2

---

## Findings

### test-1

File: `tests/test_phase4_fegen_rust_backend.py`, `TestRustParserSelfHosting._assert_rust_parser_equals_python`

`parse_grammar(text)` at line 260 is called without `rust_fegen_cst_module`, which is the pure-Python path — correct per the design. However, the helper constructs `fltk2gsm.Cst2Gsm(text)` with the raw `str`, then calls `result.result` (a `fegen_rust_cst.Grammar` handle) directly on `visit_grammar`. The Rust parser's `apply__parse_grammar` returns a `ParseResult` whose `.result` field is typed `Any` in the Python layer, just as the Python path's result is (plumbing.py:147-148 shows the `cast`). The test never checks the *type* of `result.result` before handing it to `Cst2Gsm.visit_grammar`. If the Rust parser were to return a node of an unexpected type (e.g. due to a future binding change), the error would propagate as an `AttributeError` deep inside `Cst2Gsm` rather than at the parse boundary, making the failure diagnostic opaque.

Consequence: a type mismatch between what `apply__parse_grammar` returns and what `visit_grammar` expects produces a confusing internal traceback rather than a clear assertion at the entry point. Regressions in the node accessor surface won't be caught until `Cst2Gsm` breaks internally.

Fix: add `assert isinstance(result.result, fegen_rust_cst.Grammar), type(result.result)` immediately after the `result.pos` assertion. This pins the return type at the test boundary and makes future regressions immediately obvious.

---

### test-2

File: `tests/test_phase4_fegen_rust_backend.py`, `TestRustParserSelfHosting.test_fegen_grammar_self_hosted`

`_FEGEN_FLTKG_PATH.read_text()` uses the platform default encoding. Every other usage of this path in the file (`parse_grammar_file(_FEGEN_FLTKG_PATH)` in `TestAC8RealCst2GsmRustBackend`) goes through `parse_grammar_file`, which opens the file internally and does not specify an encoding either — but that is existing code and consistent. The new test directly reads the file with `Path.read_text()` without `encoding="utf-8"`. On a non-UTF-8 locale (rare but possible in CI), the read could produce garbled text, causing a mysterious parse failure rather than a clear encoding error.

Consequence: flaky failure on non-UTF-8 CI environments; when it fails the error is a parse failure, not an encoding error, making diagnosis hard.

Fix: `_FEGEN_FLTKG_PATH.read_text(encoding="utf-8")`.

---

## No further findings.

The three tests in `TestRustParserSelfHosting` are well-structured: they share logic cleanly via `_assert_rust_parser_equals_python`, assert both the failure condition (`result is None`) and the partial-consume condition (`result.pos == len(text)`) with diagnostics, and the `gsm_rust == gsm_python` equality assertion is meaningful (dataclass equality over a rich semantic model, not an identity check). The `check-no-pyo3` Makefile additions use the established positive-control-before-negative-assertion pattern correctly. The overall coverage gap the design identifies (Rust-parser path previously unexercised end-to-end) is addressed by the three new test cases.
