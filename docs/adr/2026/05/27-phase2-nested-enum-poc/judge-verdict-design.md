# Judge verdict — design review

Phase: design. Artifact: `design.md`. Round 1.
Notes: 1 reviewer file; 5 findings.

## Other findings walk

### design-1 — Fixed
Claim: `append_name` snippet mixes `Py<PyAny>` and `Bound<'_, PyAny>` in a `PyTuple::new` call (heterogeneous element types, won't compile); `__eq__` passes owned `Bound<PyType>` where `&Bound<PyAny>` is expected. Consequence: snippets won't compile as written.
Evidence: `append_name` (design.md:202) now reads `Identifier_Label::Name.into_pyobject(py)?.into_any()` yielding `Bound<'_, PyAny>`, paired with `child.into_bound(py)` also `Bound<'_, PyAny>` -- homogeneous. `__eq__` (design.md:288) now reads `other.is_instance_of::<Identifier>()` -- idiomatic, no type mismatch.
Assessment: fix addresses both sub-issues at the named locations. Accept.

### design-2 — Fixed
Claim: `extend` uses deprecated `PyAnyMethods::iter()` (deprecated since PyO3 0.23.0). Consequence: deprecation warning at build time.
Evidence: design.md:167 now reads `children.try_iter()?`.
Assessment: fix is correct. Accept.

### design-3 — Won't-Do
Claim: cross-type node equality returns `NotImplemented` via the `!is_instance_of` branch. Consequence: none -- reviewer explicitly states "This is a confirmation, not a defect."
Rationale: no change needed.
Assessment: reviewer self-identifies this as a non-defect confirmation. Won't-Do is the only correct disposition. Accept.

### design-4 — Fixed
Claim: design justifies `UnknownSpan` default "via identity" but AC-22 asserts equality (`==`), not identity (`is`). Consequence: could mislead implementer into thinking identity is mandatory.
Evidence: design.md:125 now reads "AC-22 requires equality, not identity; this approach also provides identity as a bonus." Correctly frames the requirement.
Assessment: wording now matches the requirement's actual constraint. Accept.

### design-5 — Fixed
Claim: cited source line for `impl_py_class_attribute` was "line 536" without naming the file; actual location is `pymethod.rs:530`. Consequence: negligible -- substantive claims correct.
Evidence: design.md:143 now reads "`pymethod.rs:530`, `impl_py_class_attribute`" -- file named, line corrected.
Assessment: citation corrected. Accept.

## Approved

5 findings: 4 Fixed verified, 1 Won't-Do sound.

---

## Verdict: APPROVED
