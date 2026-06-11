# Design review findings: crosscdylib-abi-check-helper

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Verified against `crates/fltk-cst-core/src/cross_cdylib.rs`, `crates/fltk-cst-core/src/lib.rs`, `tests/test_rust_span.py`, `TODO.md`, and pyo3 0.23.5 sources at base commit 7ddec4a. All cited line numbers in the design check out (ABI checks at 98–135 and 313–358, TODO comments at 36–37 / 81–82 / 304–307, SAFETY blocks at 140–150 and 268–273, `FLTK_CST_CORE_ABI` doc at 16–18, `py_type_name`/`py_attr_type_name` at 170–184, test classes/lines as cited). Helper feasibility (`T: PyClass`, `PyClassObject<T>` already used at lines 110/337), pyo3-gating of `cross_cdylib.rs` (`lib.rs:1–2`), `fully_qualified_name` availability in pyo3 0.23.5, the TODO.md entry, and the `build-test-user-ext` Makefile target all confirmed. Template-vs-test-assertion mapping in §Test plan verified line by line; the pass-unchanged/update split is correct under the design's templates. Requirements coverage is complete: helper extraction, pinned behavior change, caching out of scope, `PyTypeError` everywhere, SAFETY comment accuracy, 5-scenario subprocess updates, verification commands, TODO hygiene — all mapped.

## design-1: `{ty}` rendering claims are empirically false; the stated rationale for deriving `{ty}` collapses

**Section:** §2 "Unified error templates" — "`get_span_type` always checks the canonical import (where `fully_qualified_name()` yields `fltk._native.Span`, preserving current readability)"; §Edge cases — "Test fakes defined in `__main__` — `{ty}` renders as `__main__.FakeSpan`" and "For real skew (an actual old `fltk._native` build) `{ty}` renders `fltk._native.Span` as before"; §Test plan — "the fake's type is now rendered `__main__.FakeSpan`".

**What's wrong:** All three rendering claims are false.

- `Span` and `SourceText` are `#[pyclass(frozen)]` with no `module = "..."` argument (`crates/fltk-cst-core/src/span.rs:57,147`). Verified live against the built extension: `fltk._native.Span.__module__ == 'builtins'` and `fltk._native.SourceText.__module__ == 'builtins'`.
- pyo3 0.23.5 `fully_qualified_name()` returns bare `__qualname__` when `__module__` is `"builtins"` **or `"__main__"`** (`pyo3-0.23.5/src/types/typeobject.rs:170–174`; the Py_3_13 `PyType_GetFullyQualifiedName` path behaves identically, and abi3-py310 uses the pre-3.13 path anyway).

So: canonical `fltk._native.Span` renders `"Span"`, not `"fltk._native.Span"`; subprocess-test fakes in `__main__` render `"FakeSpan"`, not `"__main__.FakeSpan"`; and a consumer cdylib's `SourceText` (same `#[pyclass]` declaration pattern, e.g. the phase4 fixture) renders bare `"SourceText"` — indistinguishable from the canonical class.

**Consequence:**
- Span-path messages degrade vs current text: e.g. template 3 becomes `"Span ABI mismatch: Span reports ..."` — `{ty}` duplicates `{label}` and the `fltk._native.` qualifier present in every current Span-path message is lost. Same on the SourceText foreign-type path: `"SourceText ABI mismatch: SourceText reports ..."` carries no more information than hardcoding, despite §2 asserting derivation "is required for accuracy".
- The design's planned test assertions all still pass under bare rendering (none pin `{ty}` except the `"FakeSource"` extension to `test_with_source_unchecked_bogus_abi_marker_raises_type_error`, which passes only because under pytest that class's `__module__` is the test module name, not `__main__` — a different mechanism than the design describes). The implementation would therefore go green while silently not delivering what §2 promises; an implementer trusting the `__main__.FakeSpan` claim could also write a failing assertion.

**Suggested fix:** Either (a) render `{ty}` as `module.qualname` without the builtins/`__main__` stripping (compose from `ty.module()` + `ty.qualname()`, falling back per component) — note canonical types would then render `builtins.Span` unless `module = "fltk._native"` is also added to the `#[pyclass]` attrs (a separate, user-visible change; if taken, call it out); or (b) accept bare-name rendering, drop the false claims, and reconsider whether `{ty}` earns its place next to `{label}` (it still distinguishes genuinely foreign fakes like `FakeSpan`); or (c) keep a fully-qualified hardcoded label on the Span path (`type_label = "fltk._native.Span"`, accurate there since `get_span_type` only ever checks the canonical import) and bare derivation on the SourceText path. Whichever is chosen, §2, §Edge cases, and §Test plan must describe the actual rendering.

## design-2: wrong test name in §Test plan

**Section:** §Test plan — "`test_with_source_unchecked_str_raises_type_error` and `test_with_source_unchecked_no_marker_raises_type_error`".

**What's wrong:** No test named `test_with_source_unchecked_no_marker_raises_type_error` exists. The actual test is `test_with_source_unchecked_no_marker_attr_raises_type_error` (`tests/test_rust_span.py:303`).

**Consequence:** An implementer searching for the named test finds nothing and may add a new test instead of updating the existing one, leaving the stale `match="fltk._native.SourceText"` assertion at line 309 to fail post-refactor (caught at test time, but it breaks the TDD ordering the plan prescribes).

**Suggested fix:** Correct the name.
