# Exploration: `TODO(forged-abi-extract-span-uniformity)`

Facts and source ground truth only. No prescriptions.

## 1. TODO.md entry (verbatim ground truth)

`TODO.md:37-44`:

```
## `forged-abi-extract-span-uniformity`

`check_instance_layout` is generic and could be applied to `extract_span` for uniformity.
Currently `extract_span` is not reachable by forged objects (it is gated by `is_instance`
against the non-subclassable canonical `fltk._native.Span` type, plus `check_abi_pair::<Span>`
in `get_span_type`), so adding `check_instance_layout` there would add no rejection power.
Revisit only if a future change makes `extract_span` reachable by non-canonical types.
Location: `crates/fltk-cst-core/src/cross_cdylib.rs` (`extract_span`).
```

## 2. Code-level `TODO(slug)` markers found

Repo-wide grep for the literal string `TODO(forged-abi-extract-span-uniformity)` (excluding
the `.claude/worktrees/` scratch tree, which mirrors this exploration's own working copy)
returns exactly **one** code-comment hit:

- `crates/fltk-cst-core/src/cross_cdylib.rs:417-421`, directly above `extract_span`:

  ```rust
  /// TODO(forged-abi-extract-span-uniformity): `check_instance_layout` could be applied here
  /// for uniformity with `extract_source_text`.  Currently adds no rejection power: this path
  /// is gated by `is_instance` against the non-subclassable canonical `Span` type (plus
  /// `check_abi_pair::<Span>` in `get_span_type`), so no forged object can reach its
  /// `cast_unchecked`.  Revisit if this path ever becomes reachable by non-canonical types.
  ```

All other repo hits for the slug are prose references in `docs/adr/2026/06/14-rust-backend-assessment/burndown/` design/judge/handoff/notes artifacts for the `fix-forged-abi-segfault` item, none of which add a second code-level marker.

## 3. Verifying the stated gates against current code

### 3.1 `extract_span` itself — `crates/fltk-cst-core/src/cross_cdylib.rs:422-450`

```rust
pub fn extract_span(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<Span> {
    if let Ok(span_ref) = obj.extract::<Span>() {          // line 424: fast path
        return Ok(span_ref);
    }
    let native_span_type = get_span_type(py)?;              // line 432
    if obj.is_instance(&native_span_type)? {                 // line 433: the stated gate
        let span = unsafe { obj.cast_unchecked::<Span>() };  // line 443
        return Ok(span.borrow().clone());
    }
    Err(PyTypeError::new_err(...))
}
```

This matches the TODO's description: the slow path is gated by `obj.is_instance(&native_span_type)` where `native_span_type` comes from `get_span_type`.

### 3.2 `get_span_type` — `crates/fltk-cst-core/src/cross_cdylib.rs:461-478`

```rust
pub fn get_span_type(py: Python<'_>) -> PyResult<Bound<'_, PyType>> {
    FLTK_NATIVE_SPAN_TYPE
        .get_or_try_init(py, || {
            let span_type = py
                .import("fltk._native")
                .and_then(|m| m.getattr("Span"))              // name-based, mutable lookup
                .and_then(|s| s.cast_into::<PyType>()...)?;
            check_abi_pair::<Span>(&span_type, "Span", || "fltk._native.Span".to_string())?;
            Ok(span_type.unbind())
        })
        .map(|t| t.bind(py).clone())
}
```

`FLTK_NATIVE_SPAN_TYPE` is a `PyOnceLock` (`cross_cdylib.rs:409`) populated lazily, on whichever call reaches `get_span_type` first. Confirmed via grep across `crates/fltk-cst-core/src/*.rs` and `crates/fegen-rust/src/cst.rs`: every call site of `get_span_type` (in `span_to_pyobject`, `extract_span`, and dozens of generated setters/getters in `cst.rs`) is a lazy, on-demand call; there is no eager/forced initialization anywhere (no call at module-import time, no `#[pymodule]` init hook touching it).

`check_abi_pair` (`cross_cdylib.rs:185-260`) validates exactly two things on the type it is given: the `_fltk_cst_core_abi` string classattr and the `_fltk_cst_core_abi_layout` int classattr (steps 1-7). Both are plain Python class attributes — settable by any Python class definition, as `check_abi_pair`'s own doc comment (`cross_cdylib.rs:171-184`) and the crash-analysis in `design.md:89-104` ("anything readable from Python is replayable from Python") state generically for this exact attribute pair.

### 3.3 `Span`'s non-subclassability — `crates/fltk-cst-core/src/span.rs:290`

```rust
#[cfg_attr(feature = "python", pyclass(frozen, eq, hash, from_py_object))]
#[derive(Clone)]
pub struct Span { ... }
```

No `subclass` flag is present, confirming the TODO's "non-subclassable canonical `Span` type" claim: pyo3 pyclasses without `subclass` cannot be subclassed either from Python or from another `#[pyclass(extends = Span)]`.

## 4. Does the "adds no rejection power" claim hold?

The TODO's chain of reasoning is: `is_instance` against `native_span_type` + `Span` non-subclassable + `check_abi_pair::<Span>` already run in `get_span_type` ⇒ anything that passes `is_instance` **is** the genuine canonical `Span`, so `check_instance_layout` would reject nothing that isn't already rejected.

This chain implicitly assumes `native_span_type` (the value `get_span_type` returns) is always the genuine canonical `fltk._native.Span` type object. That assumption is not established by anything in `get_span_type` or `check_abi_pair`:

- `get_span_type`'s lookup (`cross_cdylib.rs:465-467`) resolves `fltk._native.Span` **by name from a live module namespace**, which is an ordinary, mutable Python attribute — reassignable by any code that runs before the `PyOnceLock` first resolves it (`native.Span = <something else>` is a plain attribute set, no special privilege required).
- `check_abi_pair::<Span>` (`cross_cdylib.rs:474`) does not verify that the object it is given is a genuine pyo3-allocated type; it only reads the two forgeable classattrs described in §3.2. A plain Python class that defines matching `_fltk_cst_core_abi`/`_fltk_cst_core_abi_layout` values passes `check_abi_pair` unconditionally.
- This is a materially different situation from `extract_source_text`/`check_instance_layout`'s existing use, where the checked type is always `obj.get_type()` — the **actual runtime type of the untrusted object itself**, not a value resolved through a separate mutable name lookup. `extract_span`'s reference type (`native_span_type`) and the untrusted object's own type are two independent things that `is_instance` merely compares to each other; nothing pins `native_span_type` to the genuine `Span` class.

The project's own test suite already demonstrates, for the sibling `span_to_pyobject` direction, that pre-first-call reassignment of `fltk._native.Span` is a real, exercised condition:

- `tests/test_rust_span.py:539-561` (`test_abi_string_mismatch_raises_type_error`) and `tests/test_rust_span.py:577-599` (`test_layout_mismatch_raises_type_error`), both in class `TestSpanPathAbiGate` (`tests/test_rust_span.py:487-498`), run in **fresh subprocesses** and execute `native.Span = FakeSpan` (a plain Python class carrying attacker-chosen `_fltk_cst_core_abi`/`_fltk_cst_core_abi_layout` values) *before* any span crosses a cdylib boundary, i.e. before `get_span_type`'s `PyOnceLock` is populated. The test comments (`tests/test_rust_span.py:490-491`) note this is necessary because "the ABI check fires once in `get_span_type`'s `PyOnceLock` init, which is not resettable within a live process."
- These two tests only assert that `check_abi_pair` fires a `TypeError` when the patched `FakeSpan`'s classattrs are *wrong*. Neither test (nor any other test found via `grep -rn "extract_span\|is_instance" tests/*.py`) constructs a `FakeSpan` whose classattrs are *correct* and then passes a genuine instance of that `FakeSpan` into `extract_span` (e.g. via a generated node's span setter, `crates/fegen-rust/src/cst.rs:599` et al.).

Tracing that untested combination through the current code: if `fltk._native.Span` is reassigned to a plain-Python `FakeSpan` (matching `_fltk_cst_core_abi`/`_fltk_cst_core_abi_layout` values, no `__slots__` padding) before `get_span_type` is first called, then:

1. `check_abi_pair::<Span>(&FakeSpan, ...)` (`cross_cdylib.rs:474`) passes — it only reads the two attacker-settable classattrs.
2. `get_span_type`'s `PyOnceLock` (`cross_cdylib.rs:462-478`) caches `FakeSpan` as `native_span_type`.
3. In `extract_span`, `obj.is_instance(&native_span_type)` (`cross_cdylib.rs:433`) is satisfied by any instance of `FakeSpan` — trivially, since the "reference type" and the object's actual type are now the same attacker-authored class. `Span`'s non-subclassability (§3.3) restricts what a genuine `fltk._native.Span` instance can be; it says nothing about a case where the name `fltk._native.Span` itself has been reassigned away from the genuine class.
4. `cast_unchecked::<Span>()` (`cross_cdylib.rs:443`) then reinterprets the plain-Python `FakeSpan` instance's memory as `PyStaticClassObject<Span>`.

Were `check_instance_layout` applied — either to `native_span_type` inside `get_span_type`, or to `obj.get_type()` inside `extract_span` (the two coincide in this scenario, since `is_instance` only passed because `obj`'s actual type equals `native_span_type`) — it would read `__basicsize__` via the immutable `type.__basicsize__` descriptor (`cross_cdylib.rs:314-330`) on the attacker-authored `FakeSpan` and reject it whenever its `tp_basicsize` does not match `size_of::<Span::Layout>()`, i.e. in the un-padded case. This traces as adding real rejection power in this specific scenario, which appears to be in tension with the TODO's and `design.md:217-219`'s ("Consequently the basicsize gate adds **no rejection power** on the `extract_span` path: there is no forged object that reaches its `cast_unchecked`") blanket claim of zero rejection power — that claim is verified true only under the additional, unstated assumption that `fltk._native.Span` has not been reassigned by the time `get_span_type` first resolves it.

## 5. Is this a "revisit-if" note with no actionable work?

As literally worded ("Revisit only if a future change makes `extract_span` reachable by non-canonical types"), the TODO frames its own trigger condition as a *future* code change. §4 traces a path to `extract_span`'s `cast_unchecked` via a *pre-existing* mechanism (`fltk._native.Span` reassignment before first `get_span_type` call) that requires no future code change — the reachability described there exists in the code as of this exploration (base commit `8fd5ecf`), not contingent on a change yet to be made. No test in the repository currently exercises this specific combination (reassign `fltk._native.Span` to a classattr-matching forge, then pass a genuine instance of that forge into `extract_span`'s slow path) to observe empirically whether it produces a crash, matching the same class of forgery `design.md:1-105` documents and the `fix-forged-abi-segfault` item was created to close for `extract_source_text`.
