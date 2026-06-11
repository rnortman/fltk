# Dispositions: design review round 1 — crosscdylib-abi-check-helper

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Notes: `notes-design-design-reviewer.md`. Design: `design.md` (revised in place).

design-1:
- Disposition: Fixed
- Action: Independently verified the finding before fixing: pyo3 0.23.5 `fully_qualified_name()` (non-Py_3_13 path in `typeobject.rs`) returns bare `__qualname__` when `__module__` is `"builtins"` or `"__main__"`; live check against the built extension confirms `fltk._native.Span.__module__ == 'builtins'` (and `SourceText`); `span.rs:57,147` confirm `#[pyclass(frozen)]` with no `module = ...`. All three rendering claims in the prior draft were false as the reviewer stated. Adopted a variant of suggested fix (c): helper signature gains a third parameter `subject: &str` (`check_abi_pair<T: PyClass>(ty, type_label, subject)`); Span path passes hardcoded `"fltk._native.Span"` (the lookup path is the accurate identifier — truthful under monkeypatching, preserves the qualifier in every current Span-path message, and keeps the `"fltk._native.Span"` pin in `test_missing_layout_attr_raises_type_error` passing unchanged); SourceText path derives `subject` via `py_type_obj_name` / `fully_qualified_name()` with documented bare-name renderings (`str` → `"str"`, foreign cdylib `SourceText` → bare `"SourceText"`, pytest fakes → test-module-qualified qualname). Rewrote §2 (rendering rationale, actual stripping behavior, explicit rejection of adding `module = "fltk._native"` as out-of-scope user-visible change), §3 call sites, §Edge cases (replaced the false `__main__.FakeSpan` bullet), §Test plan (subprocess tests now all pass unchanged; `"FakeSource"` extension's mechanism corrected to test-module qualname). Cleanup-editor pass re-run.
- Severity assessment: High for a design doc gating unsafe-downcast error reporting: an implementer following the draft would have shipped degraded, label-duplicating messages while all planned tests went green (silent non-delivery of §2's promise), or written a failing assertion from the false `__main__.FakeSpan` claim.

design-2:
- Disposition: Fixed
- Action: Verified `tests/test_rust_span.py:303` — actual name is `test_with_source_unchecked_no_marker_attr_raises_type_error`. Corrected in §Test plan (second bullet), with line numbers (298, 303) added for both tests in that bullet.
- Severity assessment: Low-moderate: a dangling test name breaks the prescribed TDD ordering and invites a duplicate test, leaving the stale `match="fltk._native.SourceText"` assertion to fail post-refactor; caught at test time but wastes an implementation round-trip.
