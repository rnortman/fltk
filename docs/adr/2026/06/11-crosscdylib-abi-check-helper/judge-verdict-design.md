# Judge verdict — design review

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Phase: design. Doc: `docs/adr/2026/06/11-crosscdylib-abi-check-helper/design.md` (revised in place). Round 1.
Notes: `notes-design-design-reviewer.md` (2 findings). Dispositions: `dispositions-design.md`.

## Findings walk

### design-1 — Fixed
Claim: all three `{ty}` rendering claims in the prior draft were false (pyo3 0.23.5 `fully_qualified_name()` strips `builtins`/`__main__`; `Span`/`SourceText` have `__module__ == "builtins"`), so the stated rationale for deriving `{ty}` collapsed; consequence is degraded label-duplicating messages shipped green, or a failing assertion written from the false `__main__.FakeSpan` claim.

Independently verified the underlying facts:
- `pyo3-0.23.5/src/types/typeobject.rs` non-Py_3_13 `fully_qualified_name()` path: `if module_str == "builtins" || module_str == "__main__" { qualname }` — stripping behavior is exactly as the reviewer and revised design state.
- `crates/fltk-cst-core/src/span.rs:57,147`: `#[cfg_attr(feature = "python", pyclass(frozen))]` / `pyclass(frozen, eq, hash)` — no `module = ...` argument on either class.

Verified the fix in the revised design (variant of reviewer's suggested fix (c)):
- §1: helper signature gains `subject: &str` — `check_abi_pair<T: PyClass>(ty, type_label, subject)`.
- §2: Span path hardcodes `"fltk._native.Span"` (lookup-path identifier, truthful under monkeypatching); SourceText path derives via `py_type_obj_name` with documented actual renderings (`str` → `"str"`, foreign cdylib `SourceText` → bare `"SourceText"`, pytest fakes → test-module-qualified, not stripped). The false claims are gone; the stripping rule is stated with the pyo3 citation; adding `module = "fltk._native"` is explicitly rejected as an out-of-scope user-visible change.
- §Edge cases: the false `__main__.FakeSpan` bullet replaced with the accurate hardcoded-subject description, noting derivation would render bare `"FakeSpan"` (subprocess fakes live in `__main__`, stripped) — consistent with the verified pyo3 behavior.
- §Test plan: `test_missing_layout_attr_raises_type_error`'s `"fltk._native.Span" in msg` assertion (`tests/test_rust_span.py:611`) holds under the hardcoded subject; the `"FakeSource"` extension's mechanism corrected to test-module qualname (`FakeSource` defined at `tests/test_rust_span.py:324` inside a test method — `__module__` is the test module, not stripped, so `"FakeSource"` appears in the qualname). Both check out against the actual test file.

Assessment: fix addresses the consequence; revised claims match verified pyo3 and pyclass source. Accept.

### design-2 — Fixed
Claim: §Test plan named a nonexistent test `test_with_source_unchecked_no_marker_raises_type_error`; consequence is a duplicate test and a stale `match="fltk._native.SourceText"` assertion failing post-refactor.

Verified: `tests/test_rust_span.py:298` is `test_with_source_unchecked_str_raises_type_error`, `:303` is `test_with_source_unchecked_no_marker_attr_raises_type_error`. Revised §Test plan (second bullet) uses the correct name with line numbers 298, 303.

Assessment: fix is exact. Accept.

## Disputed items

None.

## Approved

2 findings: 2 Fixed verified.

---

## Verdict: APPROVED
