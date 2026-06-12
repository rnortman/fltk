Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 912b285

No findings.

---

Verification notes (in lieu of findings):

**`py_type_obj_name` vs `py_type_name` divergence is intentional and documented.** Two helpers
coexist: `py_type_name(obj: &Bound<PyAny>)` uses `.name()` (unqualified), `py_type_obj_name(ty:
&Bound<PyType>)` uses `.fully_qualified_name()`. The design §2 explains why the SourceText path
needs the qualified form and why the builtins/`__main__` stripping behavior is acceptable for
error messages on the failure path. Not a quality issue.

**`check_abi_pair` is module-private with two call sites — appropriate scope.** The helper's
`fn` visibility (no `pub`) is correct; it encapsulates an unsafe-adjacent safety gate and should
not become part of any public or crate-public surface.

**No redundant state introduced.** The caching architecture (`FLTK_FOREIGN_SOURCE_TEXT_TYPE`,
`FLTK_NATIVE_SPAN_TYPE`, `IS_CANONICAL_CDYLIB`, `WITH_SOURCE_UNCHECKED_METHOD`) is unchanged;
the refactor touches only the validation logic inside the slow-path and init-closure branches.

**TODO hygiene clean.** Three `TODO(crosscdylib-abi-check-helper)` comments deleted from the
production file; `TODO.md` entry removed; surviving `TODO(crosscdylib-abi-size-probe)` is
appropriate carry-forward (different work item, correctly scoped).

**Test assertions are specific and failure-pinning.** Updated tests use `exc_info.value` string
assertions (not just `match=` regex) to pin multiple substrings in the new unified template,
including the deliberate behavior-change site (`test_source_text_abi_string_missing_raises`).
The `FakeSource` derivation test (`test_with_source_unchecked_bogus_abi_marker_raises_type_error`)
now pins that the type name appears in the error, validating the `py_type_obj_name()` path.
