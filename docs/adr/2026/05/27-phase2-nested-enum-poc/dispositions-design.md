# Dispositions — Phase 2 Nested Enum PoC Design Review

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

design-1:
- Disposition: Fixed
- Action: In `append_name` snippet (design "Per-Label Methods"), changed `label.into_any()` (yields `Py<PyAny>`) to `into_pyobject(py)?.into_any()` (yields `Bound<'_, PyAny>`), making both array elements `Bound<'_, PyAny>` so `PyTuple::new` compiles. In `__eq__` snippet, replaced `other.is_instance(Identifier::type_object(py))?` with `other.is_instance_of::<Identifier>()` — avoids the `&Bound<PyAny>` vs `Bound<PyType>` mismatch and is more idiomatic.
- Severity assessment: Snippets as written would not compile. Implementer copying verbatim hits type errors immediately. Underlying approach is sound; remediation is straightforward type normalization.

design-2:
- Disposition: Fixed
- Action: In `extend` snippet (design "Generic Methods"), changed `children.iter()?` to `children.try_iter()?`. The `iter()` method is deprecated since PyO3 0.23.0 (any.rs:692).
- Severity assessment: Build-time deprecation warning. No runtime impact. Clean code hygiene fix.

design-3:
- Disposition: Won't-Do
- Action: No change.
- Severity assessment: None — this is a confirmation that inter-type node equality correctly returns `NotImplemented`, not a defect. The reviewer explicitly states "This is a confirmation, not a defect."
- Rationale: The reviewer confirms the design is correct. `Items` vs `Identifier` falls into the `!is_instance_of` branch and returns `NotImplemented`. Requirements (AC-23) only exercise same-type equality. No gap exists. Making any change here would add complexity for a non-existent problem.

design-4:
- Disposition: Fixed
- Action: In "Construction (`#[new]`)" section, rewrote the `UnknownSpan` justification to clarify that AC-22 requires equality (`==`), not identity (`is`). The import approach provides both but identity is a bonus, not a requirement.
- Severity assessment: Misleading wording could cause an implementer to believe identity is mandatory, leading to unnecessary debugging if a future refactor breaks identity while preserving equality. The semantic correctness was never in doubt.

design-5:
- Disposition: Fixed
- Action: In "`#[classattr]` Label Attachment" section, corrected the citation from "line 536" to "`pymethod.rs:530`, `impl_py_class_attribute`" — naming the file and fixing the line number.
- Severity assessment: Negligible. The substantive claim is correct. An implementer relying on the citation would find the right code within a few lines regardless.
