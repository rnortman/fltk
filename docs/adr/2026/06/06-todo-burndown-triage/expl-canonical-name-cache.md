# Fact-check: TODO `canonical-name-cache`

Date: 2026-06-06. Source: adversarial code read of current `main`.

---

## Claim 1: `_emit_rust_cross_backend_eq_hash` emits a per-call `PyString` allocation in `__hash__`

**Verified true.**

`gsm2tree_rs.py:151–179` defines `_emit_rust_cross_backend_eq_hash`. Lines 175–179 emit:

```rust
fn __hash__(&self, py: Python<'_>) -> PyResult<isize> {
    pyo3::types::PyAnyMethods::hash(
        pyo3::types::PyString::new(py, self.__repr__()).as_any()
    )
}
```

`pyo3::types::PyString::new` allocates a Python string object on every call. This is confirmed in the generated output: `src/cst_generated.rs:54–58` (NodeKind), `src/cst_generated.rs:98–102` (Identifier_Label). The fixture crate mirrors it: `tests/rust_cst_fixture/src/cst.rs:63–66`, `107–110`, `350–353`, `769–772`, etc. The fegen cst also: `src/cst_fegen.rs` shows the same pattern at multiple sites.

The `__repr__` call (e.g. `NodeKind::Identifier => "NodeKind.IDENTIFIER"`) returns a `&'static str` — no allocation — but `PyString::new` wraps it into a heap-allocated Python string object on each `__hash__` invocation.

---

## Claim 2: `GILOnceCell` is available/imported in the generated crate

**Verified true, but only used for `UNKNOWN_SPAN_CACHE`, not for hash caching.**

`gsm2tree_rs.py:125` emits `use pyo3::sync::GILOnceCell;` in the crate header. This appears verbatim in `src/cst_generated.rs:3` and the fixture crates (`tests/rust_cst_fixture/src/cst.rs:3`, `tests/rust_cst_fegen/src/cst.rs:3`).

The only module-level `GILOnceCell` static currently emitted is `UNKNOWN_SPAN_CACHE: GILOnceCell<PyObject>` (`gsm2tree_rs.py:131`, `src/cst_generated.rs:9`). No `GILOnceCell<isize>` statics exist anywhere in the generated or hand-written Rust (`src/cst_generated.rs`, `src/cst_fegen.rs`, `src/lib.rs`, `src/span.rs`).

pyo3 version in use: `0.23` (`Cargo.toml:15`). `GILOnceCell<T>` in pyo3 0.23.5 requires `T: Send + Sync` for `Sync`, `T: Send` for `Send` (`pyo3-0.23.5/src/sync.rs:158–159`). `isize` satisfies both. The `get_or_init` method (`pyo3-0.23.5/src/sync.rs:187`) takes `Python<'_>` and a closure, so `GILOnceCell<isize>` is a valid, callable type — no API obstacle.

---

## Claim 3: Per-variant caching of the `isize` is correct given salted hash is per-process-stable

**Verified true, with correct scoping.**

CPython's SipHash-2-4 string hash uses a 128-bit seed set once at process startup (`sys.hash_info` shows `seed_bits=128`, `algorithm='siphash24'`). Within a single process, `hash(str)` is deterministic: the same string always returns the same `isize`. Caching `hash("NodeKind.IDENTIFIER")` as an `isize` in a `GILOnceCell<isize>` static is correct for the lifetime of the process. The cached value is not valid across process boundaries, but that is the correct scope for a module-level static.

The cross-backend hash agreement requirement (AC4) is that `hash(rust_variant) == hash(python_variant)` when they represent the same logical value. The Python side computes `hash(self._fltk_canonical_name)` where `_fltk_canonical_name` is a plain `str` attribute (`gsm2tree.py:131`). The Rust side computes `hash(PyString::new(py, self.__repr__()))`. Because `__repr__()` and `_fltk_canonical_name` return the same string (e.g. `"NodeKind.IDENTIFIER"`), and CPython's `str.__hash__` is purely a function of the string contents and the per-process seed, the two results are identical. The `isize` from either path is stable per-process, so caching the Rust result is valid.

AC4 is tested at `tests/test_cross_backend_label_equality.py:95–108`.

---

## Claim 4: Proposed amortization is feasible in codegen

**Feasible with one static per variant.**

`GILOnceCell<T>` is a module-level singleton type; it cannot be parameterized by a runtime value. To cache one `isize` per enum variant, the codegen would need to emit one `static` per variant, e.g.:

```rust
static HASH_NODEKIND_IDENTIFIER: GILOnceCell<isize> = GILOnceCell::new();
static HASH_NODEKIND_ITEMS: GILOnceCell<isize> = GILOnceCell::new();
```

and then dispatch in `__hash__` via match. An alternative is a fixed-size array of `GILOnceCell<isize>` indexed by a numeric discriminant; Rust enum discriminants can be cast to `usize` with `as`. Either approach is mechanically expressible in the codegen at `gsm2tree_rs.py:_emit_rust_cross_backend_eq_hash`. The `_emit_rust_cross_backend_eq_hash` method already generates per-type (not per-variant) statics for `UNKNOWN_SPAN_CACHE`, so the pattern is established.

Scale: `src/cst_generated.rs` has 9 enum variant occurrences (3 NodeKind + 1 Identifier_Label, 1 Items_Label, 1 Items_NodeKind_Label — counted by `#[pyo3(name = ...]`). The fegen cst fixture has 46. The number of statics is linear in the number of enum members across the grammar.

---

## Claim 5: Python-side `_fltk_canonical_name` is a plain attribute, not a property

**Verified true.**

`gsm2tree.py:100–132` (`_emit_cross_backend_eq_hash`) explicitly documents that it "Assumes each member has a plain string attribute `_fltk_canonical_name` (not a property)" and the Python `__hash__` emits `return hash(self._fltk_canonical_name)` — reading a pre-computed `str` with no string construction. The assignments happen in `_emit_node_kind_canonical_name_assignments` (line 145) and `_emit_label_canonical_name_assignments` (line 158), which emit post-class statements like `NodeKind.ITEMS._fltk_canonical_name = "NodeKind.ITEMS"`.

---

## Summary of verdict

All factual claims in the TODO are accurate:

| Claim | Status |
|---|---|
| Per-call `PyString` allocation in Rust `__hash__` | True (`gsm2tree_rs.py:177`, `cst_generated.rs:56`) |
| `GILOnceCell` available/imported in generated crate | True (`gsm2tree_rs.py:125`); not yet used for hash |
| Cached `isize` is process-scope-correct | True (CPython hash seed is per-process-stable) |
| Amortization via `GILOnceCell<isize>` per variant is feasible | True; requires N statics per grammar (one per enum variant) |
| Python side uses plain attribute, not property | True (`gsm2tree.py:131`) |

The TODO is self-described as perf-only / defer-until-bottleneck. The allocation is real and happens on every `__hash__` call for every Rust-backed `NodeKind` or Label enum member. No in-tree benchmark measures this cost.
