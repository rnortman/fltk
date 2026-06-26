# Test Review Notes

Commit range: `49e9701..ab38ec7`
Reviewer: deep-test-reviewer

---

## test-1

**File:line**: `fltk/unparse/test_is_span_guard.py` (whole file) + `fltk/test_plumbing.py:244–280`

**What's wrong**: No combined native-present unparse round-trip regression test exists.

The design §4 / delta D6 called for a test that: (a) skips unless `fltk._native` is importable, (b) parses a small input and asserts `type(node.span) is terminalsrc.Span`, then (c) runs `unparse_cst` / `render_doc` and asserts success. This combined test is the only guard for the original bug: with native present, `is_span` in the old code rejected `terminalsrc.Span` children, causing `unparse_cst` to raise `ValueError("Unparsing failed")`.

As implemented, the properties are split across separate files that never run together:
- `test_python_parser_span_backend.py::test_not_native_span_when_native_present` covers (a)+(b): asserts `type(cst.span) is not NativeSpan` when native is present. It does NOT unparse.
- `test_plumbing.py::TestUnparsing::test_unparse_simple_expression` and siblings cover (c): they unparse but carry no native-present precondition. They pass trivially in a native-absent environment (the bug never manifests there).
- `test_is_span_guard.py::TestIsSpanHelper::test_accepts_terminalsrc_span` verifies `is_span(terminalsrc.Span(...))` returns `True`, but this is a unit test of the helper, not an end-to-end regression.

**Consequence**: In a CI environment without native (or a future pure-Python distribution build), the §2.6 regression path is never exercised. A change that broke `is_span` (e.g., accidentally reverting to probe-bound behavior) would pass the full test suite in a native-absent environment and only fail in native-present CI, with no test explicitly gating that condition. The core bug that motivated this entire design would be silently reintroduced.

**Fix**: Add a test (e.g., in `test_is_span_guard.py` or `test_python_parser_span_backend.py`) that skips unless `fltk._native` is importable, generates a Python parser + unparser for a small grammar, parses a short input, asserts `type(result.cst.span) is terminalsrc.Span`, then calls `unparse_cst` / `render_doc` and asserts the expected text is returned. This is exactly the test the design §4 specified as "the case that raises `ValueError("Unparsing failed")` on the §2.1-only tree."

---

## test-2

**File:line**: `fltk/fegen/test_cst_protocol.py:560–594`

**What's wrong**: The committed-source "no native / no selector" source-level assertions cover only one file pair.

`test_committed_protocol_source_names_no_native_no_selector` and `test_committed_cst_source_imports_no_native_no_selector` check only `fltk_cst_protocol.py` and `fltk_cst.py`. The other committed regenerated file pairs — `bootstrap_cst.py`, `bootstrap_cst_protocol.py`, `regex_cst.py`, `regex_cst_protocol.py`, `toy_cst.py`, `toy_cst_protocol.py`, `unparsefmt_cst.py`, `unparsefmt_cst_protocol.py` — are not explicitly asserted. As verified by grep, all eight files are correctly updated at HEAD. But the tests only prove it for two of them.

The implementation log (increment 18) justifies this as a "stronger and deterministic guarantee": a module that never names a symbol is trivially stub-stable for it. That argument is correct, but it only applies to modules that are actually checked. The generator (`gsm2tree.py`) emits all files from the same code path, so a regression there would produce the same defect in all files. The current tests would only catch it for `fltk_cst.py` / `fltk_cst_protocol.py`.

**Consequence**: A generator regression that reintroduces a native import or the span selector into the generated files would be caught only for the two asserted files. The other six committed artifacts would silently regress. The first symptom would be a `make check` pyright failure (for anything that actually resolves through the selector), but there would be no pytest-level guard in the interim.

**Fix**: Extend the two assertions to cover all committed generated file pairs: add the bootstrap, regex, toy, and unparsefmt CST/protocol pairs to the existing checks, or parameterize over all generated-artifact paths in `fltk/fegen/` and `fltk/unparse/` that end in `_cst.py` / `_cst_protocol.py`.

---

## test-3

**File:line**: `fltk/fegen/test_cst_protocol.py:546–557` (rationale comment) + `fltk/fegen/pyrt/test_span_protocol_assignability.py` (whole file)

**What's wrong**: The "pyright-stability regression" (D6's stated central test) was replaced by source-level assertions without directly testing the transitive closure of that invariant.

The delta D6 test plan specifies: "Assert that running pyright over a representative generated parser+CST+protocol triad yields identical results with the `fltk/_native/__init__.pyi` stub present vs. absent." The implementation log (increment 18 deviation) replaces this with source-level "never names the symbol" checks, reasoning that "a module that never names a symbol is trivially stub-stable for it."

This argument holds for the direct name lookup, but not for transitive dependencies. The generated pipeline modules now import `fltk.fegen.pyrt.span_protocol` (which they DID NOT previously import) for the `SpanProtocol` annotation. `span_protocol.py` itself has a native-dependent block at lines 113–118:

```python
try:
    from fltk._native import Span as _RustSpan
    AnySpan = _pymod.Span | _RustSpan
except Exception:
    AnySpan = _pymod.Span
```

Currently `AnySpan` is not used by the generated pipeline (verified by grep), so pyright's resolution of `SpanProtocol` itself is stub-independent. But if `TODO(spanprotocol-native-linecol)` is resolved — the design's own tracked next step, which involves unifying `LineColPos` across backends — `span_protocol.py` is the natural place to introduce native-referencing elements. If `SpanProtocol`'s own definition then became native-dependent (e.g., a `TYPE_CHECKING` import of `fltk._native.LineColPos`), the generated pipeline's pyright results would become stub-sensitive while the existing source-level assertions (which only check that the generated files themselves don't name `fltk._native`) would continue to pass.

**Consequence**: A future `span_protocol.py` change that makes `SpanProtocol`'s structural type stub-dependent would silently break the R2 isolation property for all generated pipeline modules that import `SpanProtocol`, without any test failing. This is exactly the failure mode the differential pyright run would catch and the source-level assertion cannot.

**Fix**: Add a test that runs pyright over a generated parser+CST+protocol triad with `fltk/_native/__init__.pyi` present, then with it temporarily renamed/removed, and asserts the resulting diagnostics and inferred span types are identical. The `tests/pyright_test_utils._run_pyright_over_dir` harness already exists and is used in `test_cst_protocol.py`; the novel piece is toggling the stub file. Alternatively, add a structural check that `SpanProtocol`'s `__protocol_attrs__` or the `span_protocol` module's own imports contain no native reference — which would at least fail quickly when the transitive assumption breaks.

---

## test-4

**File:line**: `fltk/fegen/test_cst_protocol.py:578–594` (`test_committed_cst_source_imports_no_native_no_selector`)

**What's wrong**: The concrete CST source check is asymmetric with the protocol check.

`test_committed_protocol_source_names_no_native_no_selector` does a full-text `"fltk._native" not in PROTOCOL_MODULE.read_text()` assertion — the string must appear nowhere. `test_committed_cst_source_imports_no_native_no_selector` only checks for a standalone `import fltk._native` line. The concrete CST module legitimately contains `sys.modules.get("fltk._native")` as a runtime string inside `_get_native_span_type()`, and the test comment explains this scoping: "the sole fltk._native reference is the runtime `_get_native_span_type()` lookup."

However, the import-only check would miss an annotation that contains `fltk._native.Span` as a lazy string (under `from __future__ import annotations`, annotations become string constants, not imports). A generator regression that added `fltk._native.Span` as an annotation without adding an `import fltk._native` line would pass this test while failing pyright (unresolved reference). The annotation string `"fltk._native.Span"` would appear in the source but not as a standalone import line.

**Consequence**: A generator regression introducing a native annotation in the concrete CST (without a corresponding import) would not be caught by the test suite's pytest-level guard. It would be caught by `make check`/pyright, but with less granularity than a purposeful annotation-level check. The asymmetry also makes it harder for a reader to understand what exactly is and is not being asserted.

**Fix**: Add a check alongside the import check: verify that the string `"fltk._native"` does not appear in the concrete CST source in any annotation context. At minimum, add a comment explaining why the import-level check is intentionally scoped (which is currently only implied by the docstring phrase "the sole fltk._native reference"). Alternatively, assert that the only `fltk._native` occurrences are inside `sys.modules.get(...)` calls (e.g., `CONCRETE_MODULE.read_text().count('"fltk._native"') == 1` for the one known runtime usage), making the boundary explicit.
