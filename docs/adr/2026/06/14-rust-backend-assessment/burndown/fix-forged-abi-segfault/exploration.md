# Exploration: fix-forged-abi-segfault

## Scope

Survey of code relevant to designing the fix for `fix-forged-abi-segfault`: the `Span` class and
`_with_source_unchecked`, the pyo3/native boundary where the segfault arises, how genuine native
objects are constructed (including the multi-cdylib case), and existing subprocess test patterns
for crash regression tests.

---

## Code surface

### `Span` class and `_with_source_unchecked`

**File:** `crates/fltk-cst-core/src/span.rs`

`Span` is declared at line 155 as `#[pyclass(frozen, eq, hash, from_py_object)]`.  Its fields are
`start: i64`, `end: i64`, `source: Option<Arc<SourceInner>>`.

`_with_source_unchecked` is a `#[classmethod]` at lines 444–453:

```rust
fn _with_source_unchecked(
    _cls: &Bound<'_, PyType>,
    start: i64,
    end: i64,
    source: &Bound<'_, PyAny>,
) -> PyResult<Span> {
    Ok(Span::new_with_source(start, end, &extract_source_text(source)?))
}
```

It accepts `source` as `&Bound<'_, PyAny>` — any Python object — and delegates to
`extract_source_text` for the boundary check before the unchecked cast.

`SourceText` is declared at line 55 as `#[pyclass(frozen)]`.  Its only field is
`inner: Arc<SourceInner>`, where `SourceInner` (line 46) holds `text: String`.

`SourceText` exposes two ABI-marker classmethods (lines 103–131):
- `_fltk_cst_core_abi() -> &'static str` returns `FLTK_CST_CORE_ABI` (`"fltk-cst-core/<version>"`
  baked at compile time from `env!("CARGO_PKG_VERSION")`).
- `_fltk_cst_core_abi_layout() -> usize` returns
  `size_of::<<SourceText as PyClassImpl>::Layout>()`.

`Span` exposes the same two classmethods at lines 391–411.

### The ABI check: `extract_source_text` and `check_abi_pair`

**File:** `crates/fltk-cst-core/src/cross_cdylib.rs`

`FLTK_CST_CORE_ABI` (line 19): `concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"))`.

`extract_source_text` (lines 63–116) is the sole caller of the dangerous `cast_unchecked`:

**Fast path** (line 65): `obj.cast::<SourceText>()` — succeeds when `obj` is a `SourceText`
registered by this exact cdylib's pyo3 type-object registry.  Returns `Ok` immediately, no unsafe.

**Slow path** (lines 78–115):
1. Get `obj`'s type object (line 79: `obj.get_type()`).
2. Cache-hit check (lines 82–91): if `FLTK_FOREIGN_SOURCE_TEXT_TYPE` (a `PyOnceLock`) is
   populated and the cached type pointer matches `obj_type` by identity, perform
   `obj.cast_unchecked::<SourceText>()` (line 86) and return.
3. Cache-miss: call `check_abi_pair::<SourceText>(&obj_type, ...)` (line 93), which reads
   `_fltk_cst_core_abi` and `_fltk_cst_core_abi_layout` off the type object and validates both
   against compile-time constants.
4. If both pass, cache `obj_type` in `FLTK_FOREIGN_SOURCE_TEXT_TYPE` (line 97) and perform
   `obj.cast_unchecked::<SourceText>()` (line 112).

`check_abi_pair` (lines 158–233) performs seven sequential steps:
1. `getattr("_fltk_cst_core_abi")` — missing → `TypeError`.
2. `extract::<&str>()` — non-str → `TypeError`.
3. String equality against `FLTK_CST_CORE_ABI` — mismatch → `TypeError`.
4. Compute `size_of::<<T as PyClassImpl>::Layout>()` locally.
5. `getattr("_fltk_cst_core_abi_layout")` — missing → `TypeError`.
6. `extract::<usize>()` — non-int → `TypeError`.
7. Numeric equality — mismatch → `TypeError`.
If all pass, returns `Ok(())`.

### The segfault attack surface

The gate in `check_abi_pair` reads two attributes off the Python type object — both are plain
Python attributes readable from user code.  A pure-Python class can set both to the correct values
copied from a genuine `SourceText`:

```python
class Forge:
    _fltk_cst_core_abi = SourceText._fltk_cst_core_abi       # correct string
    _fltk_cst_core_abi_layout = SourceText._fltk_cst_core_abi_layout  # correct int
```

An instance of `Forge` passes all seven steps of `check_abi_pair` and proceeds to
`obj.cast_unchecked::<SourceText>()` at line 112.  `cast_unchecked` reinterprets the CPython
`PyObject*` memory at the `Forge` instance's address as a `PyStaticClassObject<SourceText>` —
which has a different layout — producing a type-confusion read of arbitrary memory: SIGSEGV.

The assessment (`recommended-actions.md`) records this as verified live 4/4.

### The `_fltk_cst_core_abi_layout` probe: what it checks and what it does not

`PyStaticClassObject<T>` for `#[pyclass(frozen)]` without `dict`/`weakref` reduces to
`{ffi::PyObject, T}` (repr(C)).  The layout probe is `size_of` of this struct.

For a forged pure-Python object (`Forge` above), Python allocates a `PyObject` header followed by
the instance dict and slot storage for `Forge`'s own layout — not the layout of
`PyStaticClassObject<SourceText>`.  The probe value (`size_of` of the genuine struct) passes
because the probe only checks a numeric attribute on the type object, not the actual allocation
size of the instance.  The forged class sets the attribute to the correct integer, so the numeric
check passes even though no genuine `PyStaticClassObject<SourceText>` is in memory.

The document (`cross_cdylib.rs` lines 98–111) explicitly acknowledges this as an accepted residual
risk in the "forgery" bullet of the SAFETY comment: "a hand-crafted class could set both attrs to
the right values and still have a mismatched layout — UB."

### The multi-cdylib (genuine foreign object) case

`span_to_pyobject` (lines 257–297) is the legitimate caller that drives the cross-cdylib slow path:

1. It initialises `IS_CANONICAL_CDYLIB` by comparing `Span::type_object(py)` against
   `get_span_type(py)?` (lines 258–261).  When this cdylib is NOT `fltk._native`, it takes the
   slow path.
2. For a source-bearing span, it calls `span.source_as_py(py)?` (line 270), which returns a
   `Py<SourceText>` constructed via `Py::new(py, SourceText { inner: arc.clone() })` — a genuine
   `SourceText` instance registered in the consumer cdylib's type-object registry.
3. It then calls the cached `_with_source_unchecked` method (lines 272–285), passing the genuine
   consumer-cdylib `SourceText` as `source`.
4. `_with_source_unchecked` → `extract_source_text` → slow path: `obj.cast::<SourceText>()`
   fails (different cdylib type-object), ABI pair is validated, genuine `SourceText` passes
   (because its `_fltk_cst_core_abi` classattr is set by the same Rust `#[classattr]` macro
   from the same rlib), and `cast_unchecked` is safe because both cdylibs link the same rlib
   with identical struct layout.

The key difference between the genuine case and the forged case: a genuine foreign
`SourceText` was allocated by pyo3's `Py::new(py, SourceText { ... })`, so its CPython memory
block genuinely has the `PyStaticClassObject<SourceText>` layout.  The forged case has no such
allocation.

**What an adequate native-instance check must do:** accept objects whose CPython memory block was
genuinely allocated as a `PyStaticClassObject<SourceText>` (regardless of which cdylib registered
the type-object), and reject objects whose type merely has the correct attribute values but whose
CPython memory block has a different layout.  The current attribute-only check cannot do this;
see "Open factual questions" for what mechanism could.

### How genuine native objects are constructed

**Same-cdylib case (fast path):**
`SourceText` constructed via `Span.with_source(_cls, start, end, source)` (line 429) or
`SourceText.__new__(text)` (line 88).  pyo3 `Py::new` allocates a `PyStaticClassObject<SourceText>`
with the local type-object pointer; `obj.cast::<SourceText>()` succeeds.

**Cross-cdylib case:**
`Span::source_as_py` (lines 241–251) calls `Py::new(py, SourceText { inner: arc.clone() })`.
This allocates a new `PyStaticClassObject<SourceText>` in the consumer cdylib's type-object space.
The new object's CPython memory is genuinely laid out as `PyStaticClassObject<SourceText>`;
`cast_unchecked` on it is safe.

**The `PyOnceLock` cache (`FLTK_FOREIGN_SOURCE_TEXT_TYPE`):**
After the first validated cross-cdylib call, the consumer cdylib's type object is cached.
Subsequent calls use a type-object pointer identity check (`cached_type.bind(py).is(&obj_type)`)
at line 83, then perform `cast_unchecked` directly without re-validating the ABI pair.
A forged object whose type is the exact same Python class object as the cached genuine type would
bypass even the ABI check and reach `cast_unchecked` via the cache-hit branch (lines 82–91).

---

## Schemas/contracts

### `SourceText` (Rust struct, Python-visible)

```rust
pub struct SourceText {
    pub inner: Arc<SourceInner>,
}
pub struct SourceInner {
    pub(crate) text: String,
}
```

Python layout (pyo3 frozen pyclass, no dict/weakref): `PyStaticClassObject<SourceText>` =
`{ ffi::PyObject header, SourceText }` (repr(C)).

### ABI marker contract

- `_fltk_cst_core_abi`: `str`, value `"fltk-cst-core/<semver>"`, same across all cdylibs linking
  the same rlib version.
- `_fltk_cst_core_abi_layout`: `int`, value `size_of::<<T as PyClassImpl>::Layout>()`, same across
  all cdylibs built with the same pyo3 version and the same `T`.

Both are classmethods decorated `#[classattr]` and accessible as Python class attributes.

### Python `Span` (Python-backend equivalent)

`fltk/fegen/pyrt/terminalsrc.py` lines 48–150: `@dataclass(frozen=True, eq=True, slots=True)`.
Fields: `start: int`, `end: int`, `_source: str | None`, `kind`.  No `_with_source_unchecked`;
the Python backend's `with_source` classmethod (line 130) does a plain `isinstance` check and
raises `TypeError` for non-`SourceText`/`str` input — always memory-safe.

---

## Invariants/constraints

**`_with_source_unchecked` is underscore-private by convention only.**  There is no access
control preventing Python user code from calling it.  It is a `#[classmethod]`, so it is
callable as `Span._with_source_unchecked(start, end, obj)` from any Python code that imports
`fltk._native.Span`.

**`check_abi_pair` gates the ABI pair but not the CPython allocation layout.**  Its `Ok(())` return
means only: the type object has the correct string attribute and the correct integer attribute.
It does not mean: instances of that type were allocated by pyo3 as `PyStaticClassObject<T>`.

**`FLTK_FOREIGN_SOURCE_TEXT_TYPE` cache bypasses `check_abi_pair` on hits.**  On a cache hit at
lines 82–91, the only check is type-object pointer identity.  If the cached type is the genuine
consumer cdylib's `SourceText`, this is safe.  If by some path a forged type were cached first,
subsequent instances of that forged type would reach `cast_unchecked` without any attribute check.

**`SourceText` is not Python-subclassable** (`#[pyclass(frozen)]` without `subclass`).
This prevents the subclass-with-extended-layout attack but does not prevent constructing a
separate Python class with the correct attributes.

**`IS_CANONICAL_CDYLIB` controls which branch of `span_to_pyobject` is taken.**  When this
cdylib IS `fltk._native`, `Py::new` is used directly and `_with_source_unchecked` is never
called on the outward direction.  The unchecked cast arises only on the inward direction
(`_with_source_unchecked` called from Python or from consumer-cdylib generated code).

---

## Existing subprocess test patterns

All subprocess tests follow the same pattern, established in `tests/test_rust_span.py` class
`TestSpanPathAbiGate` (lines 476–753):

```python
@staticmethod
def _run_script(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
```
(line 489–497, with `# noqa: S603`)

Test scripts are inline strings passed as `-c script`.  The subprocess prints `"OK"` on success;
the test asserts `result.returncode == 0` and `"OK" in result.stdout`.

For crash-detection (SIGSEGV), the convention would be `result.returncode != 0` or specifically
`result.returncode == -signal.SIGSEGV` (value `-11` on Linux).  The existing tests do not yet
cover this case; no current test runs a script that is expected to segfault and asserts a non-zero
exit code.

The `test_nullable_loop_guard.py` pattern (lines 241–255) shows the same `subprocess.run`
shape with a `TimeoutExpired` guard for hang detection — a parallel to crash detection.

All subprocess tests that require the cross-cdylib fixture (`phase4_roundtrip_cst`) use
`pytest.importorskip` before spawning the subprocess:
```python
phase4 = pytest.importorskip(
    "phase4_roundtrip_cst",
    reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
)
del phase4  # only needed for skip check; real work is in subprocess
```
(pattern at lines 525–529, 531–532, etc.)

A crash-regression test for `_with_source_unchecked` does NOT require `phase4_roundtrip_cst`
because the segfault is reproducible using only `fltk._native` and a pure-Python forged class —
no cross-cdylib fixture needed.  The forged class sets `_fltk_cst_core_abi` and
`_fltk_cst_core_abi_layout` to the correct values copied from `SourceText`, then passes an
instance to `Span._with_source_unchecked`.

---

## Open factual questions

**Q1: What pyo3 mechanism, if any, can test whether a `Bound<'_, PyAny>` points to memory
genuinely allocated as `PyStaticClassObject<T>` without relying on type-object identity?**

The pyo3 `obj.cast::<T>()` (used in the fast path at line 65) relies on type-object identity:
it checks `obj.get_type() is T::type_object(py)`.  For the cross-cdylib case, type-object
identity is not available (different cdylib, different `type_object` pointer).  The current
design accepts this gap and documents it as an out-of-contract usage path.

The fix spec says the check must be "strict enough to reject fakes but not so strict that it
rejects legitimate Rust objects created by a different compiled copy of the library."  This is
the core design question.

Known options:
- `is_instance` against the known type object (`get_span_type` path, line 321) — safe for `Span`
  because `Span` is never subclassable and `is_instance` is equivalent to type identity for
  non-subclassable pyo3 types.  But the `_with_source_unchecked` path for `SourceText` cannot
  use `is_instance` against the local `SourceText::type_object(py)` (that is the fast path,
  which has already failed) nor against a cached foreign type (which would also fail for a forged
  object of yet another type).
- A size probe at the CPython C-API level (`Py_SIZE` / `ob_size`) or `sys.getsizeof` — may
  distinguish the genuine pyo3 allocation from the forged one, but the values are not part of
  pyo3's stable API.
- A PyCapsule stored on genuine `SourceText` instances (not just the class) — forgeable in
  principle but requires genuine Rust code to set; Python cannot forge a capsule containing a
  real Rust pointer without already having one.
- Accept the residual: document the forgery as permanently out-of-contract, add the crash
  regression test (which confirms a fix works), and make `_with_source_unchecked` raise
  `TypeError` via a different mechanism that does not depend solely on the forged attributes.

**Q2: What does "a real native-instance check" mean concretely in pyo3 terms?**

The assessment (`recommended-actions.md`) says: "a checked-but-not-identity downcast; a
same-type identity check is too strict for the multi-cdylib case."  The question is what
"checked" means in pyo3 without type-object identity.  The `obj.cast::<T>()` fast path IS the
checked downcast (it is not `cast_unchecked`); it fails for cross-cdylib objects precisely
because pyo3's type registry is per-cdylib.  There is no pyo3 API for a "same-rlib, different
cdylib" isinstance check.

**Q3: Does `is_instance` against the fltk._native.SourceText type object (fetched via
`get_source_text_type`) reject forged Python objects?**

`is_instance` against a type checks Python's type hierarchy: `type(obj).__mro__`.  A forged class
with no inheritance from `fltk._native.SourceText` would NOT be an instance, so this would
correctly reject fakes.  However, `get_source_text_type` (line 384) is documented as explicitly
NOT ABI-validated and carries this comment: "Callers MUST NOT use it for `cast_unchecked` —
restrict use to `isinstance` checks only."  An `is_instance` check against the canonical
`fltk._native.SourceText` type object would reject forged classes AND reject genuine
consumer-cdylib `SourceText` objects (because the consumer cdylib registers its own `SourceText`
type object, not `fltk._native.SourceText`).  This would break the cross-cdylib legitimate case.

**Q4: Where exactly is the segfault reproducible?**

The segfault occurs at line 112 (`obj.cast_unchecked::<SourceText>()`) or equivalently at
line 86 (cache-hit branch) when the object is a forged Python class instance.  The
assessment notes it is also reproducible on the ABI-string-passes + ABI-layout-passes path
(the attributes are copied from a genuine `SourceText`), which is what the fix must close.
A test that reaches line 86 via a cached forged type has never been written; all existing
tests verify `TypeError` is raised before reaching either unsafe line.
