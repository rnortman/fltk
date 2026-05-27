# Design Review — Phase 2 Nested Enum PoC

Concise. Precise. Audience: smart LLM/human. Reviewer notes only.

Scope reviewed: `design.md` against `requirements.md`, `exploration.md`, `phase-plan.md`, and source
(`src/lib.rs`, `src/span.rs`, `Cargo.toml`/`Cargo.lock`, `fltk/fegen/fltk_cst.py`, `tests/test_rust_span.py`,
PyO3 0.23.5 + pyo3-macros-backend 0.23.5 sources in cargo registry).

Verified sound (no finding needed):
- PyO3 version is exactly 0.23.5 (Cargo.lock), matching all version-specific API claims.
- Central claim — `#[pyclass(eq)]` enum richcmp returns `NotImplemented` on cross-type / non-enum comparand,
  not a panic — confirmed by reading `pyclass.rs:1893` `pyclass_richcmp_simple_enum`: with `eq` and no `eq_int`,
  the generated `__richcmp__` `downcast::<Self>(other)` and on failure falls through to `Ok(py.NotImplemented())`.
  This correctly resolves exploration OQ-classattr/OQ-none-label-eq and supports AC-4 and AC-27. The "no eq_int"
  rationale (design "Label Enums") is correct.
- `#[classattr]` accepts exactly one optional `py: Python` arg and routes the return through `IntoPyObject`
  (pyo3-macros-backend `pymethod.rs:530 impl_py_class_attribute`); `Py<PyType>: IntoPyObject` (conversion.rs:321).
  So `#[classattr] fn Label(py) -> PyResult<Py<PyType>>` is valid. OQ-classattr-type-return resolved correctly.
- Runtime APIs used all exist with the claimed signatures: `PyList::empty(py) -> Bound` (list.rs:130),
  `PyTuple::new<'py,T,U>(...) -> PyResult<Bound>` (tuple.rs:94, fallible — matches design's `?`),
  `type_object(py) -> Bound<PyType>` (type_object.rs:50), `is_instance(&Bound<PyAny>)` (any.rs:875),
  `Python::NotImplemented`/`None` (marker.rs:736/750), `Py::clone_ref`/`into_bound`, `Bound<PyList>::iter`/`append`.
- Python `Identifier` (fltk_cst.py:754-795) and `Items` (172-309) match the design's reproductions exactly,
  including label sets, method names, error-message wording ("Expected one name child but have {n}"), and that
  `Identifier.children_name` has no `cast` (one child type) while `Items` per-label uses `cast` (multi-type).
- Requirements coverage: all 27 acceptance criteria map 1:1 to test classes in the Test Plan table. In Scope /
  Out of Scope items each appear in the design. No scope creep: design correctly excludes `register_classes`
  (Phase 3), CST wiring (Phase 4/5), `.pyi` stubs, Span attribute exposure.
- `src/lib.rs` existing registration block matches the design's "Existing registrations" verbatim, so the
  diff context is accurate.

---

## design-1 — Sample Rust snippets pass heterogeneous element types to `PyTuple::new` (won't compile as written)

Section: "Per-Label Methods (Pattern)" — `append_name` (design.md:201-206); also "Generic methods" `extend`
(design.md:165-174); `__eq__` `is_instance` call (design.md:288).

What's wrong: `PyTuple::new<'py, T, U>` requires a single element type `T: IntoPyObject` for the whole iterator
(`elements: impl IntoIterator<Item = T>`, tuple.rs:94-101). The `append_name` snippet builds
`[label.into_any(), child.into_bound(py)]` where `label.into_any()` is `Py<PyAny>` and `child.into_bound(py)` is
`Bound<'_, PyAny>` — two different types in one array literal, which is a type error. The `extend` snippet has the
same shape (`label_val.clone_ref(py).into_bound(py)` is `Bound`, paired with `child` which is `Bound` from
iteration — that pair is actually homogeneous, but `child_result?` from `children.iter()?` yields `Bound<PyAny>`
while the design's generic `append` pairs `Py<PyAny>` `label_val` with `PyObject` `child`, which is homogeneous;
the inconsistency is `append_name`). Separately, `__eq__` calls
`other.is_instance(Identifier::type_object(py))` but `is_instance` takes `&Bound<'_, PyAny>` (any.rs:875) and
`type_object` returns an owned `Bound<'_, PyType>` — needs `&...into_any()` (or just `other.is_instance_of::<Identifier>()`).

Why: verified against tuple.rs:94-101, any.rs:875, conversion.rs:321 (Py IntoPyObject) and instance.rs:577
(`into_any` on Bound).

Consequence: the snippets as literally transcribed will not compile; an implementer copying them verbatim hits
type errors. The underlying approach is sound — both `Py<PyAny>` and `Bound<PyAny>` implement `IntoPyObject`, so
making both elements the same kind (e.g. both via `into_bound_py_any(py)`, or both `PyObject`) compiles. This is a
fidelity bug in "verified" code, not an architectural flaw. Low remediation cost.

Suggested fix: normalize tuple element types in each snippet (build both as `Bound<'_, PyAny>` or both as
`PyObject`); use `is_instance_of::<Identifier>()` in `__eq__`.

---

## design-2 — `extend` uses deprecated `PyAnyMethods::iter()`

Section: "Generic Methods" — `extend` (design.md:167): `let iter = children.iter()?;`.

What's wrong: in PyO3 0.23.5, `PyAnyMethods::iter()` is deprecated since 0.23.0 with note "use `try_iter`
instead" (any.rs:692). It still compiles and runs.

Why: any.rs:686-693 — `try_iter` is the non-deprecated name; `iter` carries `#[deprecated(since="0.23.0")]`.

Consequence: a deprecation warning at build time. No `#![deny(warnings)]` exists in `src/*.rs` and there is no
clippy/deny config, so the build will not fail — purely cosmetic. (Note: `Bound<PyList>::iter()`, used in
`children_name`/`child_name`/`maybe_name`, is a different, non-deprecated inherent method — those are fine.)

Suggested fix: use `children.try_iter()?` in `extend`.

---

## design-3 — `__eq__` returns NotImplemented for *subclass* comparands; minor over-broadness vs requirement

Section: "`__eq__`" (design.md:286-298).

What's wrong: the design gates equality on `other.is_instance(Identifier)` (true for subclasses) but then does
`other.extract::<PyRef<Identifier>>()`. This is internally consistent and fine. The only subtlety: requirement
(System Behavior "Equality": "Comparison with non-node types returns NotImplemented") is satisfied, and AC-23 only
exercises same-type. No contradiction. Flagging only to confirm there is no gap: `Items` vs `Identifier`
comparison falls into the `!is_instance` branch and returns `NotImplemented`, which Python resolves to `False` —
consistent with AC-4-style inter-class discrimination expectations (though AC does not test node-level
cross-type equality).

Why: requirements.md:94 and AC-23; design.md:288-291.

Consequence: none functional. This is a confirmation, not a defect. Included so the judge sees cross-type node
equality was checked and is covered.

---

## design-4 — AC-22 default-span claim relies on identity, but `==` is what the test asserts; both hold — confirm wording

Section: "Construction (`#[new]`)" / "`UnknownSpan` default via import" (design.md:123-125); AC-22
(requirements.md:155).

What's wrong: design states the default span is "the exact same Python object as `fltk._native.UnknownSpan`,
satisfying `node.span == UnknownSpan` via identity." AC-22 asserts equality (`==`), not identity. Rust `Span` is
`#[pyclass(frozen, eq, hash)]` comparing only `(start, end)` (span.rs:64-68), so `Span(-1,-1) == UnknownSpan` is
`True` regardless of identity. The import approach does yield the same object, so identity also holds.

Why: span.rs:56-77 (eq on start/end only); requirements.md:155 ("`node.span` equal to `fltk._native.UnknownSpan`").

Consequence: none — AC passes either way. Noted because the design's justification ("via identity") is stronger
than required and could mislead an implementer into thinking identity is mandatory (it is not). A hardcoded
`Span{start:-1,end:-1}` default would also pass AC-22. The import approach is still preferable (avoids
re-implementing the sentinel) and is correctly chosen.

---

## design-5 — Minor: cited backend source line numbers slightly imprecise

Section: "Label Enums" (design.md:66 cites `pyclass.rs:1893-1971`); "`#[classattr]` Label Attachment"
(design.md:143 cites "`impl_py_class_attribute`, line 536").

What's wrong: `pyclass_richcmp_simple_enum` is at `pyclass.rs:1893` (correct start). `impl_py_class_attribute`
is in `pymethod.rs:530`, not at the "line 536" implied location and not in the file named; the cited "536" is
close to the function (530) but the design does not name the file. Both functions exist and behave as the design
claims.

Why: pyclass.rs:1893 and pymethod.rs:530 (grep-confirmed).

Consequence: negligible — the substantive claims are correct and verifiable; only the citation precision is off.
An implementer relying on these citations will still find the right code. No action required beyond awareness.
