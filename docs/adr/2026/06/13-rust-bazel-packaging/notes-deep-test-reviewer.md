# Test Review Notes — Rust Bazel Packaging

Commit reviewed: HEAD 36eda0d (fltk), 45bc7fe (clockwork).
Acceptance bar (per requirements §4): packaged Bazel-built Rust parser + PyO3 bindings produce SOME parse result in-context. NOT correctness, NOT Python/Rust equivalence.

---

test-1
File: clockwork/dsl/BUILD.bazel:81–84
Clockwork's `py_test` wrapper (tools/rules/python.bzl:190) unconditionally calls `fail()` at analysis time when `use_pytest = True` (the default) and the target lacks `py_pytest_main`/`__test__`/`main` boilerplate. The `clockwork_rust_roundtrip_test` target supplies only `srcs` and `deps` — none of the required pytest wiring. Every other py_test in the repo (clockwork/dsl/proto/tests, clockwork/logging/readers/tests) has a `py_pytest_main(name = "__test__")` sibling and the triple of `srcs`/`deps`/`main` pointing at it.
Consequence: the test target fails at Bazel analysis phase — `bazel test //clockwork/dsl:clockwork_rust_roundtrip_test` never runs the test code; it errors at load time. AC #4 is never exercised.
Fix: either add `use_pytest = False` to the `py_test` call (and supply a custom main, or convert the functions to a `__main__` block), or add the required `py_pytest_main` + pytest dependency boilerplate matching the pattern in `clockwork/dsl/proto/tests/BUILD.bazel`.

---

test-2
File: clockwork/dsl/clockwork_rust_roundtrip_test.py:15–29 (`test_fltk_native_span_is_rust_path`)
The `warnings.catch_warnings` block wraps `import fltk._native`. The fallback `warnings.warn` is emitted by `fltk/fegen/pyrt/span.py` (line 15) when span.py is imported and `fltk._native` fails to load. `import fltk._native` does not import `span.py`; span.py is never touched in this test path. Therefore `span_fallback_warnings` is always empty regardless of whether `fltk._native` is on the path or not. The assert on line 26 (`len(span_fallback_warnings) == 0`) is always true and cannot distinguish the broken-packaging scenario from the working one.
Consequence: the warning-based check is vacuous. If `fltk._native` is absent, the test fails for a different reason (unhandled `ImportError` from the bare `import fltk._native as fltk_native`), so the overall test still catches the absent-`.so` case, but via uncontrolled exception propagation rather than the stated assertion. This makes the failure mode opaque and masks the actual design-level invariant being checked (AC #3). If the import is ever wrapped in a try/except by a future refactor, the vacuous check would let a broken setup pass silently.
Fix: remove the `warnings.catch_warnings` block entirely. Instead, after a plain `import fltk._native as fltk_native`, assert `hasattr(fltk_native, "Span")` (already present on line 32) and additionally assert `type(fltk_native.Span).__module__ != "fltk.fegen.pyrt.terminalsrc"` or do `import fltk._native; import fltk.fegen.pyrt.span as span_mod; assert span_mod.Span is fltk_native.Span` to verify the Rust type was actually selected by the span module. That checks the real invariant (Rust path active) without the spurious warning machinery.

---

test-3
File: fltk/BUILD.bazel:98–105 (missing)
Design §5.4 states FLTK should have an in-tree target exercising both `generate_rust_parser` AND `fltk_pyo3_cdylib` against a fixture grammar so FLTK's own CI covers the new public Bazel surface. Only `generate_rust_parser` is exercised (`bootstrap_rust_srcs`); `fltk_pyo3_cdylib` has no in-FLTK invocation. The entire crate-source-assembly genrule, abi3-rename genrule, and `py_library` wrapper logic in `fltk_pyo3_cdylib` are untested in FLTK's CI — they are only tested transitively by Clockwork's build, which has its own broken pytest wiring (test-1).
Consequence: a bug in `fltk_pyo3_cdylib`'s Starlark (e.g. wrong genrule `cmd`, wrong `crate_root` reference, wrong `imports` on the wrapping `py_library`) would not be caught by FLTK CI at all. The macro is new public Bazel surface; regressions to it are invisible until a downstream consumer breaks.
Fix: add a `fltk_pyo3_cdylib` call to `fltk/BUILD.bazel` using an existing fixture grammar and a minimal hand-written `lib.rs` (analogous to `tests/rust_parser_fixture/src/lib.rs`), producing a build target that FLTK CI can verify compiles. A `py_test` in FLTK that imports the resulting module and asserts it produces a parse result would close the loop fully, but a build-only smoke target is sufficient to cover the macro logic the current diff leaves dark.
