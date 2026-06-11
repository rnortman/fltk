# Design: unify the duplicated cross-cdylib ABI pair check

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Requirements: `request.md` (this dir). Exploration: `exploration.md` (this dir).

## Root cause / context

Two sites in `crates/fltk-cst-core/src/cross_cdylib.rs` perform the identical two-step ABI gate (string marker `_fltk_cst_core_abi`, then layout int `_fltk_cst_core_abi_layout`) guarding `downcast_unchecked`:

- `extract_source_text` slow path, lines 98–135 (function at line 66). The whole check sits inside `if let Ok(marker) = obj_type.getattr(...)`, so a missing marker silently falls through to the generic `"expected fltk._native.SourceText, got {type}"` error at lines 163–166.
- `get_span_type` GILOnceCell init closure, lines 313–358 (function at line 292). Missing marker produces a specific `map_err` message ("has no _fltk_cst_core_abi marker (pre-sentinel build)").

Five error strings differ in wording between the paths plus the structural missing-marker divergence (full text comparison in `exploration.md`). This is the safety gate for two `unsafe` downcasts; duplicated security-primitive logic invites silent divergence under future edits. `TODO(crosscdylib-abi-check-helper)` marks three comment sites (`cross_cdylib.rs:36–37`, `81–82`, `304–307`) plus the `TODO.md` entry.

## Proposed approach

All changes in `crates/fltk-cst-core/src/cross_cdylib.rs` plus test updates in `tests/test_rust_span.py` and the `TODO.md` entry removal.

### 1. New private helper

```rust
/// Validate the cross-cdylib ABI pair (`_fltk_cst_core_abi` string marker, then
/// `_fltk_cst_core_abi_layout` == size_of::<PyClassObject<T>>()) on `ty`.
/// `type_label` is the logical class name ("SourceText" | "Span") used in error prefixes.
/// `subject` identifies the checked type in error bodies; the caller supplies it
/// (lookup path or derived type name — see §2).
/// Ok(()) means `ty` is safe to treat as this module's `T` for `downcast_unchecked`,
/// subject to the documented forgery / size-preserving-skew residuals.
fn check_abi_pair<T: PyClass>(ty: &Bound<'_, PyType>, type_label: &str, subject: &str) -> PyResult<()>
```

Logic (exactly the current two-step sequence, no semantic weakening):

1. `getattr(intern!(py, "_fltk_cst_core_abi"))` — missing → error (template 1).
2. `extract::<&str>()` — non-str → error (template 2).
3. `!= FLTK_CST_CORE_ABI` → error (template 3).
4. `expected_layout = size_of::<pyo3::impl_::pycell::PyClassObject<T>>()`.
5. `getattr(intern!(py, "_fltk_cst_core_abi_layout"))` — missing → error (template 4).
6. `extract::<usize>()` — non-int → error (template 5).
7. `!= expected_layout` → error (template 6).
8. `Ok(())`.

`py` comes from `ty.py()`. All errors are `PyTypeError` (unchanged). Private to the module — both call sites live here; no new public API.

### 2. Unified error templates

`{label}` = `type_label`; `{subject}` = caller-supplied identification of the checked type. The two paths supply it differently, and the difference is principled:

- **Span path:** hardcoded `"fltk._native.Span"`. `get_span_type` checks whatever object sits at the lookup path `fltk._native.Span` — the lookup path is the accurate identifier (truthful even when that attribute is monkeypatched, as the subprocess gate tests do) and matches current Span-path messages. Deriving the name from the type object is **not** viable here: `Span`/`SourceText` are `#[pyclass(frozen)]` with no `module = ...` argument (`crates/fltk-cst-core/src/span.rs:57,147`), so their `__module__` is `"builtins"`, and pyo3 0.23.5's `fully_qualified_name()` strips a `"builtins"` or `"__main__"` module and returns bare `__qualname__` (`pyo3-0.23.5/src/types/typeobject.rs`, non-Py_3_13 path; abi3-py310 uses that path). The canonical class would render as bare `"Span"`, losing the `fltk._native.` qualifier present in every current message. Adding `module = "fltk._native"` to the `#[pyclass]` attrs would change the classes' user-visible `__module__`/repr surface — out of scope for this refactor; if wanted, it is a separate deliberate change.
- **SourceText path:** derived from the caller-supplied `obj_type` via `ty.fully_qualified_name()` with fallback `"<unknown type>"` (new small helper `py_type_obj_name(&Bound<'_, PyType>) -> String`, same idiom as the existing `py_type_name` / `py_attr_type_name` at lines 170–184). Derivation is required here because `extract_source_text` validates arbitrary foreign types. Actual renderings under the stripping rule above: plain `str` → `"str"`; a consumer cdylib's `SourceText` (same `#[pyclass]` pattern, `__module__ == "builtins"`) → bare `"SourceText"` (duplicates `{label}`; failure-path only, acceptable); pytest-defined fakes → qualified by the test module and enclosing qualname (e.g. `test_rust_span.…<locals>.FakeSource` — module is the test module, not `builtins`/`__main__`, so it is **not** stripped).

1. Missing marker: `"{label} ABI mismatch: {subject} has no _fltk_cst_core_abi marker (not a {label} from a compatible fltk-cst-core build, or a pre-sentinel build); this module expects {FLTK_CST_CORE_ABI:?}"`
2. Non-str marker: `"{label} ABI mismatch: {subject}._fltk_cst_core_abi is {attr_type}, not str"`
3. String mismatch: `"{label} ABI mismatch: {subject} reports {s:?}, this module expects {FLTK_CST_CORE_ABI:?} (fltk-cst-core version skew between cdylibs)"`
4. Missing layout attr: `"{label} ABI mismatch: {subject} has no _fltk_cst_core_abi_layout (partial-upgrade build); this module expects layout {expected_layout}"`
5. Non-int layout attr: `"{label} ABI mismatch: {subject}._fltk_cst_core_abi_layout is {attr_type}, not int"`
6. Layout mismatch: `"{label} ABI layout mismatch: {subject} reports layout {reported_layout}, this module expects {expected_layout} (pyo3-resolution skew between cdylibs)"`

With `subject = "fltk._native.Span"`, Span-path templates 3, 4, and 6 reproduce the current Span-path text verbatim and templates 2 and 5 reproduce it modulo the added `"Span ABI mismatch: "` prefix; templates preserve every substring the existing subprocess gate tests pin: `"ABI mismatch"`, `"pre-sentinel build"`, `"partial-upgrade"`, `"layout mismatch"`, `"fltk._native.Span"`, the reported/expected values, and `FLTK_CST_CORE_ABI` (so `"fltk-cst-core/"` remains greppable). Template 1's "not a {label} from a compatible build, or a pre-sentinel build" wording covers both realities behind a missing marker: an unrelated object (e.g. plain `str` passed to `_with_source_unchecked`) and an old canonical build.

### 3. Call-site changes

**`get_span_type`** — replace lines 304–358 (the TODO comment block and both inline checks) with:

```rust
check_abi_pair::<Span>(&span_type, "Span", "fltk._native.Span")?;
```

inside the existing `get_or_try_init` closure, after the import/getattr/downcast of `span_type`. The import-failure `PyRuntimeError` (lines 295–303) is untouched. Caching architecture (once per process) unchanged.

**`extract_source_text`** — replace lines 98–166 (the `if let Ok(marker)` nest plus the trailing generic error) with:

```rust
check_abi_pair::<SourceText>(&obj_type, "SourceText", &py_type_obj_name(&obj_type))?;
let _ = FLTK_FOREIGN_SOURCE_TEXT_TYPE.get_or_init(py, || obj_type.clone().unbind());
// SAFETY: ... (existing block, updated to cite check_abi_pair)
let st = unsafe { obj.downcast_unchecked::<SourceText>() };
Ok(SourceText { inner: st.get().inner.clone() })
```

Fast path (lines 68–72) and pointer-compare cache hit (lines 87–96) unchanged. Caching architecture (per-cache-miss check, single-slot foreign-type cell) unchanged — out of scope per request.

The generic `"expected fltk._native.SourceText, got {type}"` error at lines 163–166 becomes unreachable and is deleted. This is the **deliberate, user-approved behavior change**: an object whose type lacks `_fltk_cst_core_abi` now gets template 1 (`PyTypeError`, names the missing marker and the actual type) instead of the generic message. Strictly more informative; exception type unchanged. Pinned by tests (§Test plan).

`py_type_name` (line 170) loses its `extract_source_text` caller but is retained — `extract_span` (line 277) still uses it.

### 4. Comment and TODO hygiene

- Delete the three `TODO(crosscdylib-abi-check-helper)` comments (lines 36–37, 81–82, 304–307) and the `TODO.md` entry (the slug's work is done by this change).
- Update the SAFETY comment above the slow-path `downcast_unchecked` in `extract_source_text` (lines 140–150) to cite `check_abi_pair` as the validator; the forgery and size-preserving-skew caveats and `TODO(crosscdylib-abi-size-probe)` reference carry over verbatim.
- `extract_span`'s SAFETY comment (lines 268–273) cites `get_span_type`'s verification — still accurate (the verification now lives in `check_abi_pair` called by `get_span_type`); adjust wording to mention the helper.
- `FLTK_CST_CORE_ABI` doc comment line 16–18 says both markers are "checked together at `GILOnceCell` init time" — true only for the Span path; reword to "checked together by `check_abi_pair`" (fixes a preexisting imprecision: the SourceText path checks per cache miss, not at cell init).

## Edge cases / failure modes

- **Missing marker on SourceText path** — behavior change, template 1, `PyTypeError`. Approved; pinned by test.
- **Plain non-SourceText object (e.g. `str`)** — same missing-marker path; template 1's "not a {label} from a compatible fltk-cst-core build" clause keeps the message truthful for this case. `{subject}` renders `"str"`.
- **`fully_qualified_name()` failure** (SourceText path only) — fallback `"<unknown type>"`; error still raised with full ABI context.
- **Subprocess test fakes patched over `fltk._native.Span`** — the Span path's `{subject}` is the hardcoded lookup path `"fltk._native.Span"`, so the fake's own name never appears; the existing `"fltk._native.Span"` assertion in `test_missing_layout_attr_raises_type_error` passes unchanged. (Deriving the name would render bare `"FakeSpan"`: the fakes live in `__main__`, which `fully_qualified_name()` strips — another reason for the hardcoded subject, §2.)
- **Concurrent first calls** — unchanged: `GILOnceCell` semantics on both cells are untouched; `get_or_init` race in `extract_source_text` remains benign (both racers validated the same type).
- **No semantic weakening** — the helper performs the same check sequence (§1 steps 1–7) in the same order with the same comparison operands; the only observable deltas are error strings. Reviewer checklist: confirm step order and that `expected_layout` is computed from the helper's `T`, not a fixed type.
- **`--no-default-features` build** — `cross_cdylib.rs` is pyo3-gated; the pure-Rust build compiles without the helper. Covered by the cargo verification step.

## Test plan

TDD order: update/extend Python assertions first (they fail against current code where messages change), then refactor, then green.

Updated assertions in `tests/test_rust_span.py`:

- `TestSpanPathAbiGate` (subprocess, lines 417–616): all five tests pass unchanged — `test_control_no_patch_passes`, `test_abi_string_mismatch_raises_type_error`, `test_layout_mismatch_raises_type_error`, `test_missing_abi_marker_raises_type_error` ("pre-sentinel build", "fltk-cst-core/" preserved), and `test_missing_layout_attr_raises_type_error` (its `"fltk._native.Span" in msg` assertion holds because the Span path's `{subject}` is the hardcoded lookup path, §2).
- `test_with_source_unchecked_str_raises_type_error` and `test_with_source_unchecked_no_marker_attr_raises_type_error` (lines 298, 303): `match="fltk._native.SourceText"` no longer matches; update to pin the new template (`"SourceText ABI mismatch"` and `"_fltk_cst_core_abi marker"`).
- `test_source_text_abi_string_missing_raises` (line 686): currently `match="expected fltk._native.SourceText"`. Becomes the **primary pin of the behavior change**: assert `PyTypeError` with `"_fltk_cst_core_abi marker"`, `"SourceText ABI mismatch"`, and `"pre-sentinel build"` in the message; docstring updated to state this pins the deliberate change from the generic error (cite this ADR dir).
- `test_source_text_abi_layout_missing_raises`: `match="_fltk_cst_core_abi_layout missing"` → `"has no _fltk_cst_core_abi_layout"` (plus `"partial-upgrade"`).
- `test_source_text_abi_layout_non_int_raises`: `match="_fltk_cst_core_abi_layout attribute is"` → `"_fltk_cst_core_abi_layout is"` (plus `"not int"`).
- `test_source_text_abi_layout_mismatch_raises`, `test_with_source_unchecked_non_str_marker_raises_type_error`: pass unchanged (pinned substrings preserved).
- `test_with_source_unchecked_bogus_abi_marker_raises_type_error`: existing `match="ABI mismatch"` still passes; extend with an assertion that `"FakeSource"` appears in the message, pinning the `{subject}` derivation on the SourceText path (renders via the class's qualname under its test-module `__module__`, §2 — not stripped, unlike `builtins`/`__main__`).

Verification commands: `cargo test -p fltk-cst-core --no-default-features`; `uv run --group dev maturin develop` then `make build-test-user-ext` (subprocess gate tests require the phase4 fixture; a lane where they all skip is a gap, not a pass) and `uv run pytest`; `make fix`; `uv run ruff check . && uv run pyright` for the touched test file.

## Open questions

None. The one judgment call (missing-marker message change on the SourceText path) was pre-approved in triage and is pinned by test rather than left discretionary.
