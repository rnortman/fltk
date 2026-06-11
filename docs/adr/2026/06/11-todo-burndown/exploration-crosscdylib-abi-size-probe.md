# Adversarial Validation: `TODO(crosscdylib-abi-size-probe)`

Style note: concise, dense, no fluff. Audience: engineer deciding whether to act on this TODO.

---

## Subject

`TODO.md` entry `crosscdylib-abi-size-probe`. Verbatim claim audited below.
Code location: `crates/fltk-cst-core/src/cross_cdylib.rs`.

---

## Code Surface

**`FLTK_CST_CORE_ABI`** — `cross_cdylib.rs:19`
```rust
pub const FLTK_CST_CORE_ABI: &str = concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"));
```
This string is `"fltk-cst-core/0.1.0"` at present (Cargo.toml version `0.1.0`).

**`_fltk_cst_core_abi_layout` classattrs** — `span.rs:127-129` (SourceText), `span.rs:399-401` (Span)
Both emit `std::mem::size_of::<PyClassObject<T>>()`.

**Probe validation** — `cross_cdylib.rs:109-135` (SourceText path, `extract_source_text`), `cross_cdylib.rs:336-358` (Span path, `get_span_type`).
Both check string equality then integer equality. Mismatch → `PyTypeError`. Match → `downcast_unchecked`.

**`downcast_unchecked` call sites** — `cross_cdylib.rs:151` (SourceText), `cross_cdylib.rs:274` (Span).

---

## Is the Residual Risk Real As Described?

**Claim: "size equality does not prove identical field layout; a pyo3 build that reorders fields while preserving total size passes the probe."**

This is generically true as a statement about size probes. However, for the specific types (`SourceText: pyclass(frozen)`, `Span: pyclass(frozen, eq, hash)`) the scenario is extremely narrow:

`PyClassObject<T>` is defined at `pyo3-0.23.5/src/pycell/impl_.rs:278-290`:
```rust
#[repr(C)]
pub struct PyClassObject<T: PyClassImpl> {
    pub(crate) ob_base: <T::BaseType as PyClassBaseType>::LayoutAsBase,
    pub(crate) contents: PyClassObjectContents<T>,
}

pub(crate) struct PyClassObjectContents<T: PyClassImpl> {
    pub(crate) value: ManuallyDrop<UnsafeCell<T>>,
    pub(crate) borrow_checker: <T::PyClassMutability as PyClassMutability>::Storage,
    pub(crate) thread_checker: T::ThreadChecker,
    pub(crate) dict: T::Dict,
    pub(crate) weakref: T::WeakRef,
}
```

For `frozen` + no dict/weakref + `Send` + base `PyAny`:
- `ob_base` = `PyClassObjectBase<ffi::PyObject>` = `{ ffi::PyObject }` (repr(C) wrapper).
- `borrow_checker` = `EmptySlot(())` (pycell/impl_.rs:97) — ZST.
- `thread_checker` = `SendablePyClass<T>(PhantomData<T>)` (impl_/pyclass.rs:1060) — ZST.
- `dict` = `PyClassDummySlot` (impl_/pyclass.rs:72) — ZST.
- `weakref` = `PyClassDummySlot` — ZST.

Net: `PyClassObjectContents<T>` collapses to `ManuallyDrop<UnsafeCell<T>>` (only non-ZST). `PyClassObject<T>` = `{ ffi::PyObject, T }` (repr(C), both non-ZST, order fixed by repr(C)). There are no non-ZST fields to reorder within pyo3's own structs; a "size-preserving field reorder" would require swapping `ffi::PyObject` and `T`, which changes the observable repr(C) layout and is not an internal pyo3 change. ZST additions/removals do not change size or memory layout.

**Concrete conclusion:** The "reorder while preserving size" scenario the TODO describes is not currently constructible for `SourceText` and `Span` as defined. The residual the TODO is guarding against would only arise if pyo3 added a non-ZST field to the layout without changing `sizeof`. That would be a pyo3 ABI break; in practice it would be accompanied by a pyo3 minor or major version bump that the probe treats as a size change (detecting the break) or the field is zero-initialized (not changing alignment/offset of `T`) — a narrow, contrived scenario.

**The real risk vector is a different one not named in the TODO:** a consumer cdylib that resolves to a different pyo3 version whose `ffi::PyObject` is sized differently. Specifically, free-threaded Python (Py_GIL_DISABLED) adds `ob_tid`, `_padding`, `ob_mutex`, `ob_gc_bits`, `ob_ref_local`, `ob_ref_shared` to `ffi::PyObject` (object.rs:105-126), substantially changing its size. The probe **does** catch this (different `size_of` integer). So GIL vs. free-threaded is already detected.

---

## Is the Proposed Fix Feasible — How Would a Build Script Get the Resolved pyo3 Version?

### DEP_ env var route

`DEP_<LINKS>_<KEY>` vars are emitted by build scripts of crates that have a `links` manifest key. Relevant facts:

- `pyo3` crate (`0.23.5`): **no `links` key** — confirmed via `cargo metadata` and direct inspection of its `Cargo.toml`. Therefore no `DEP_PYO3_*` env vars exist.
- `pyo3-ffi` crate (`0.23.5`): **`links = "python"`** — emits `cargo:PYO3_CONFIG=<InterpreterConfig>`, available downstream as `DEP_PYTHON_PYO3_CONFIG`. Contents: Python interpreter version, lib path, build flags — **not** the pyo3 crate version (pyo3-build-config/src/impl_.rs:619-627).
- `pyo3-build-config` crate (`0.23.5`): **no `links` key**.

**Verdict:** The `DEP_*` route for obtaining the resolved pyo3 crate version does not exist without changes to pyo3 itself.

### Cargo.lock parsing route

`CARGO_WORKSPACE_DIR` is available in build scripts since Rust 1.77 (confirmed available: Rust 1.94 in use). A build script can open `$CARGO_WORKSPACE_DIR/Cargo.lock` and parse the `[[package]] name = "pyo3"` entry to extract its `version`.

**Feasibility constraints:**
1. `Cargo.lock` may be absent. Libraries (not binaries) are not required to check in their lock file. An out-of-tree consumer publishing as a library may have no `Cargo.lock` in the workspace root.
2. When fltk-cst-core is built as a dependency of an out-of-tree consumer, `CARGO_WORKSPACE_DIR` points to that consumer's workspace root — so the parsed `Cargo.lock` would contain the consumer's resolved pyo3 version. This is the correct lock for the purpose. However, (1) applies.
3. Cargo.lock format is TOML, not formally versioned as a public API, but stable in practice. Parsing requires either a TOML library (additional build-dep) or regex matching.
4. Multiple `[[package]]` entries for `pyo3` are possible if Cargo resolves two semver-incompatible versions simultaneously (e.g., 0.22.x and 0.23.x in the same workspace). A build script would need to identify which one fltk-cst-core links against.
5. `cargo:rerun-if-changed` semantics: the build script would need to declare `CARGO_WORKSPACE_DIR/Cargo.lock` as a rerun trigger.

---

## Other Inputs Affecting `PyClassObject<T>` Layout

The TODO mentions only the pyo3 version. Additional layout inputs:

1. **`Py_GIL_DISABLED`** (free-threaded Python, 3.13t): changes `ffi::PyObject` size significantly (adds ~40 bytes of atomics and thread fields — object.rs:105-126). The size probe catches this. `pyo3-build-config` correctly sets `Py_GIL_DISABLED` based on the interpreter and does NOT set `Py_LIMITED_API` when GIL is disabled (impl_.rs:192-194).

2. **`Py_TRACE_REFS`** (`py_sys_config = "Py_TRACE_REFS"`): adds two pointer fields to `PyObject` (object.rs:101-104), changing size. The size probe catches this.

3. **pyo3 `unsendable` feature** (per-class flag): changes `thread_checker` from ZST `SendablePyClass` to non-ZST `ThreadCheckerImpl` (which holds a `ThreadId`). `SourceText` and `Span` are both `Send`, so this does not apply to them. If it did, it would change size and the probe would catch it.

4. **pyo3 `dict` feature** (per-class, `#[pyclass(dict)]`): changes `T::Dict` from ZST `PyClassDummySlot` to a pointer-sized slot. Neither `SourceText` nor `Span` uses `dict`. Would change size; probe catches.

5. **rustc version**: `repr(C)` structs have deterministic layout; rustc version does not affect `repr(C)` field offsets. Not a variable here.

6. **abi3 / `Py_LIMITED_API`**: does NOT affect `PyClassObject` struct layout (the cfg(Py_LIMITED_API) guard in pycell/impl_.rs:252-272 is inside `tp_dealloc`, not in struct field definitions). Confirmed by inspection.

**Unmentioned by the TODO:** `Py_GIL_DISABLED` and `Py_TRACE_REFS` are the concrete inputs that change layout in practice. Both are caught by the size probe.

---

## Blockers the TODO Did Not Mention

1. **DEP_ route is blocked by pyo3 not having a `links` key.** The TODO's phrasing "via build script reading the Cargo lock or `DEP_*` env var" presents both as equivalent options. They are not: the `DEP_*` route requires an upstream pyo3 change (adding `links = "pyo3"` to pyo3's Cargo.toml and emitting version metadata from pyo3's build.rs). Without that, only Cargo.lock parsing is available.

2. **Cargo.lock parsing fails for library consumers without a lock file.** If absent, the build script either silently omits the pyo3 version from the ABI string (degrading back to the current probe-only state) or hard-errors (breaking the build for legitimate consumers). Neither is clean; the build script must handle the absent-lock case explicitly.

3. **The Cargo.lock identifies resolved pyo3 version, but the build script cannot verify which of potentially multiple resolved pyo3 versions its own rlib linked against**, without additional bookkeeping. Cargo's SemVer unification usually prevents multiple 0.23.x entries, but 0.22.x vs 0.23.x could coexist.

---

## Is This Papering Over a Deeper Problem?

The deeper problem is that Rust's cross-cdylib safety boundary for generics over internal types is inherently un-enforceable at runtime — `downcast_unchecked` is fundamentally unsafe and any runtime probe is a heuristic. The ABI string + size probe is the closest approximation available without language support.

The pyo3 version-in-ABI-string fix would close the specific "same fltk-cst-core version, different pyo3 version, same size" window. Given the analysis above, this window is a contrived scenario for the specific types used (frozen, no dict/weakref, Send). The practically exploitable risk is same-version-different-Python (GIL vs. free-threaded), and the probe already catches that via size change.

The fix is cosmetic in terms of real-world safety improvement for the current type definitions. It would become material if `SourceText` or `Span` gained non-ZST layout variables controllable independently of pyo3 version.

---

## Open Factual Questions

- Does pyo3 expose its crate version as `cargo:rustc-env=PYO3_VERSION` or any similar mechanism that a dependent build script could use without parsing Cargo.lock? Inspection of pyo3 0.23.5's build.rs shows it does not. Upstream change required.
- What is the expected behavior when fltk-cst-core's build script cannot find or parse `Cargo.lock`? The TODO does not specify a fallback policy.
