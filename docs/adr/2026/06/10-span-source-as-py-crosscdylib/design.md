# Design: span-source-as-py-crosscdylib

Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human implementer.
Requirements: `request.md` (this dir). Facts: `exploration.md` (this dir). Base: 9db20de (post `preamble-helpers-into-cst-core`; cross-cdylib helpers live in `crates/fltk-cst-core/src/cross_cdylib.rs`, not the generated preamble).

## 1. Root cause / context

Per `request.md` and exploration Claims 1–3 (all verified): every span-returning accessor in generated Rust CST code copies the full source text twice per call — `source_full_text_str()` (`crates/fltk-cst-core/src/span.rs:168-170`, `arc.text.clone()`) then `SourceText::from_str` via `get_source_text_type(py)?.call1(...)` (`span.rs:39-45`, `text.to_owned()`). O(source length) per node read; 23 sites in `src/cst_fegen.rs`, 6 in `src/cst_generated.rs`, 10 in `tests/rust_cst_fixture/src/cst.rs`. The O(1) API `Span::source_as_py` (`span.rs:151-161`) exists but its result is a `SourceText` registered with the *calling* cdylib's pyo3 type registry, which `fltk._native.Span.with_source` (`span.rs:203-207`, pyo3-extracted `source: &SourceText`) rejects cross-cdylib.

**Additional consequence beyond allocation cost (verified live, 2026-06-10):** the copy destroys `Arc` identity, and Rust-side `Span::coerce_source` (`span.rs:178-185`) gates `merge`/`intersect` on `Arc::ptr_eq`. Two spans read back through accessors carry distinct fresh `Arc`s, so `node_a.span.merge(node_b.span)` raises `ValueError: cannot merge spans from different sources` **even for two reads of the same node's span**. Confirmed on the real accessor path: `g = fltk._native.fegen_cst.Grammar(span=Span.with_source(0,5,SourceText(t)))`; `g.span.merge(g.span)` raises today. The Python backend compares sources by string equality (`fltk/fegen/pyrt/terminalsrc.py:102-107`), so the same merge succeeds there — a cross-backend behavioral divergence (CLAUDE.md: cross-backend equivalence is a hard requirement for out-of-tree consumers). This fix repairs the accessor case and supplies the Python-observable for TDD (§4).

## 2. Proposed approach

All non-generated changes land in `fltk-cst-core` (`crates/fltk-cst-core/src/{span.rs, cross_cdylib.rs, lib.rs}`), per the sequencing note in `request.md`. Generator changes in `fltk/fegen/gsm2tree_rs.py`. No new generated helpers. `fltk._native` re-exports the core types unmodified (`src/span.rs` is exactly `pub use fltk_cst_core::{SourceText, Span};`), so `#[pymethods]` additions in core surface on `fltk._native.Span`/`SourceText` automatically — no `src/lib.rs` change needed.

### 2.1 Why the request's sketch needs one correction: the directionality problem

The sketch in `request.md` §Direction says the new entry point "verifies `isinstance` against the cached `fltk._native.SourceText` type object" before `downcast_unchecked`. That check cannot work for the case the fix exists for. The entry point executes inside `fltk._native` (classmethod dispatched through `fltk._native.Span`'s `PyTypeObject`; per-cdylib statics are `fltk._native`'s). An incoming consumer-cdylib `SourceText` has `ob_type` = the *consumer's* lazily-created `PyTypeObject` — a distinct type with no subclass relation to `fltk._native.SourceText` — so `isinstance` against the canonical type **rejects** exactly the cross-cdylib objects we must accept.

`extract_span`'s isinstance gate (`cross_cdylib.rs:15-48`) works only in the consumer→canonical direction: the consumer can import the one canonical type and check against it. The canonical→consumer direction has no type anchor — `fltk._native` cannot enumerate the type objects of arbitrary consumer cdylibs. The gate must therefore be something other than a type-object identity check.

### 2.2 ABI-marker gate (`extract_source_text`)

Replace the isinstance gate with a marker baked into the shared rlib, so every cdylib compiling the same `fltk-cst-core` exposes the same value:

- `crates/fltk-cst-core/src/cross_cdylib.rs`: `pub const FLTK_CST_CORE_ABI: &str = concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"));`
- `crates/fltk-cst-core/src/span.rs`, `#[pymethods] impl SourceText`: `#[classattr] fn _fltk_cst_core_abi() -> &'static str { FLTK_CST_CORE_ABI }`. Every registered `SourceText` type (canonical or consumer) carries it.
- `crates/fltk-cst-core/src/cross_cdylib.rs`:

```rust
/// Extract a native `SourceText` (O(1): clones the inner `Arc`) from a Python object,
/// accepting a `SourceText` registered by this cdylib or by any other cdylib that links
/// the same fltk-cst-core rlib (gated by the `_fltk_cst_core_abi` class marker).
pub fn extract_source_text(obj: &Bound<'_, PyAny>) -> PyResult<SourceText> {
    // Fast path: locally-registered SourceText.
    if let Ok(st) = obj.downcast::<SourceText>() {
        return Ok(SourceText { inner: st.get().inner.clone() });
    }
    // Slow path: foreign-cdylib SourceText. Gate on the ABI marker classattr.
    let py = obj.py();
    if let Ok(marker) = obj.get_type().getattr(pyo3::intern!(py, "_fltk_cst_core_abi")) {
        if let Ok(s) = marker.extract::<&str>() {
            if s == FLTK_CST_CORE_ABI {
                // SAFETY: see §2.2 soundness argument (mirrors extract_span, cross_cdylib.rs:25-36).
                let st = unsafe { obj.downcast_unchecked::<SourceText>() };
                return Ok(SourceText { inner: st.get().inner.clone() });
            }
            return Err(PyTypeError::new_err(format!(
                "SourceText ABI mismatch: object reports {s:?}, this module expects \
                 {FLTK_CST_CORE_ABI:?} (fltk-cst-core version skew between cdylibs)"
            )));
        }
    }
    Err(PyTypeError::new_err(format!(
        "expected fltk._native.SourceText, got {type_name}" // type-name retrieval as in extract_span (cross_cdylib.rs:40-47)
    )))
}
```

`SourceText { inner: ... }` construction is in-crate (field is `pub`), O(1).

**Soundness argument** (mirrors `extract_span`'s SAFETY comment, `cross_cdylib.rs:25-36`; must be written out at the `unsafe` site):
- Both cdylibs MUST link the same `fltk-cst-core` rlib (same pyo3 version, same struct layout). Then `PyClassObject<SourceText>` layout is identical across cdylibs and `downcast_unchecked` merely reinterprets the same in-memory representation. `SourceText` is `#[pyclass(frozen)]` and `Sync` (`Arc<SourceInner{String}>`), so `Bound::get()` returns `&SourceText` without a borrow-flag check.
- `Arc` refcount mutation and eventual deallocation across cdylibs is already accepted by the existing design: `extract_span` clones `Span` (containing the source `Arc`) across the boundary today; Rust's default global allocator is the shared process-wide system allocator.
- **Contract delta vs `extract_span`:** the marker is forgeable from Python (a hand-written class could set `_fltk_cst_core_abi`), whereas isinstance is not. Forged input ⇒ UB. Acceptable because (a) the only caller is the private `Span._with_source_unchecked` (§2.3), itself called only by generated code passing `source_as_py` results; (b) direct Python calls to an underscore-private method with forged objects are out of contract — document in the SAFETY comment and the method docstring. Conversely the marker is *stronger* than `extract_span` under version skew: mismatched rlib versions produce a clean `TypeError` naming both ABI strings instead of proceeding to UB. This partially implements the `crosscdylib-abi-sentinel` idea for the `SourceText` path; do **not** resolve that TODO — instead place a `TODO(crosscdylib-abi-sentinel)` comment at the marker check noting the planned unification (sentinel for `extract_span`/`get_span_type`, strengthening the derivation per §3: fold in pyo3 version and/or a layout hash — `CARGO_PKG_VERSION` alone does not cover pyo3-resolution skew), and extend the `TODO.md` entry's location list accordingly.
- **Marker carrier: string classattr, deliberately.** A `PyCapsule` classattr (capsule name = ABI string) was considered — pure Python cannot *construct* capsules, so it looks unforgeable — and rejected: the marker must be readable from `fltk._native` (the foreign module doing the check), and anything readable is *replayable* from pure Python (`class Fake: _fltk_cst_core_abi = fltk._native.SourceText._fltk_cst_core_abi` passes a capsule-name gate exactly as a copied string passes the string gate). The only non-replayable gate is type identity, which §2.1 shows is unavailable in this direction. A capsule therefore adds API surface (capsule creation, `CStr` name handling, opaque `.pyi` typing) without removing the pure-Python-reachable UB; the string keeps the marker debuggable and the mismatch message trivially constructible. Fail-safe hardening that narrows forgery to `TypeError` (e.g. sanity-checking the foreign type's `__basicsize__` against `size_of::<PyClassObject<SourceText>>()` before the cast) is delegated to `crosscdylib-abi-sentinel`, which owns the gate mechanism.
- `SourceText` is not Python-subclassable (`#[pyclass(frozen)]` without `subclass`), so no inherited-marker-with-extended-layout case exists.

### 2.3 New entry point: `fltk._native.Span._with_source_unchecked`

`crates/fltk-cst-core/src/span.rs`, `#[pymethods] impl Span`, directly after `with_source`:

```rust
/// Private cross-cdylib constructor (generated-code use only): like `with_source`,
/// but accepts a `SourceText` registered by another fltk-cst-core-linking cdylib.
/// "unchecked" = bypasses pyo3's registry-based type check; an ABI-marker check
/// still gates the cast. Passing a forged marker-bearing object is UB.
#[classmethod]
#[pyo3(signature = (start, end, source))]
fn _with_source_unchecked(
    _cls: &Bound<'_, PyType>,
    start: i64,
    end: i64,
    source: &Bound<'_, PyAny>,
) -> PyResult<Span> {
    Ok(Span::new_with_source(start, end, &extract_source_text(source)?))
}
```

- Returned `Span` is converted by pyo3 using the *executing* cdylib's type cache; generated code always invokes it via `get_span_type(py)` (= `fltk._native.Span`), so the result is the canonical `fltk._native.Span` — satisfying the hard constraint stated in every emitted span getter ("Return a fltk._native.Span so consumers always get the canonical type", e.g. `src/cst_fegen.rs:633-634`).
- Public `with_source` is untouched (signature, behavior, error text). Name and underscore-privacy per `request.md` constraint.
- Considered and rejected: broadening public `with_source` to accept cross-cdylib `SourceText` — violates the "exact behavior and signature" constraint and would expose the unsafe path on a public method.

### 2.4 Construction helper: `span_to_pyobject`

`crates/fltk-cst-core/src/cross_cdylib.rs`:

```rust
/// Build the canonical `fltk._native.Span` PyObject from a native `Span`.
/// O(1) in source length; preserves Arc-sharing of the source.
pub fn span_to_pyobject(py: Python<'_>, span: &Span) -> PyResult<PyObject> {
    let span_type = get_span_type(py)?;
    // Fast path: this cdylib IS fltk._native (type objects are pointer-identical),
    // so local registration is canonical registration — construct directly, zero Python calls.
    if Span::type_object(py).is(&span_type) {
        return Py::new(py, span.clone()).map(|p| p.into_any());
    }
    match span.source_as_py(py)? {
        Some(st) => span_type
            .call_method1("_with_source_unchecked", (span.start(), span.end(), st))
            .map(|b| b.unbind()),
        None => span_type.call1((span.start(), span.end())).map(|b| b.unbind()),
    }
}
```

- Fast path soundness: `is()` pointer-identity of type objects ⇒ `Py::new` registers with the canonical type. `Span` is `Clone`; source clone is an `Arc` refcount bump. Covers both source-bearing and sourceless spans. In-tree (`fltk._native`'s own generated code, the majority path) this drops from 2+ Python-level calls plus two O(N) copies to zero Python calls.
- Slow path (consumer cdylibs: `tests/rust_cst_fixture`, `tests/rust_cst_fegen`, real out-of-tree crates): one O(1) `Py::new` (`source_as_py`) + one Python method call + one classattr getattr. Sourceless arm unchanged in semantics from today's `call1`.
- Exports: `lib.rs` re-exports `span_to_pyobject` and `extract_source_text` alongside `extract_span` (consumer-side symmetry; `extract_source_text` also serves future incoming-`SourceText` needs).

### 2.5 Generator changes (`fltk/fegen/gsm2tree_rs.py`)

1. `_preamble` (line 244-252): import becomes `use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject, Span};` — `get_source_text_type` dropped (no remaining generated callers after 2-3 below).
2. `_span_getter_setter` (line 626-654): getter body collapses to `span_to_pyobject(py, &self.span)` (keep the canonical-type comment, updated). Setter unchanged.
3. `_child_enum_block` (line 406-506): `to_pyobject` Span arm becomes `Self::Span(s) => span_to_pyobject(py, s),`. Drop the `span_type` parameter from `to_pyobject` (it was used only by the Span arm); adjust the `py_param`/unused-name logic accordingly (`py` is needed iff any variant exists). `extract_from_pyobject` keeps its `span_type` parameter (still used with `extract_span`).
4. `to_pyobject` call-site updates: `_children_getter`, `_generic_child`, and the `children_/child_/maybe_` emitters in `_per_label_methods` no longer fetch `span_type` (they fetched it solely for `to_pyobject`). `_generic_append`, `_generic_extend`, and `append_/extend_` emitters keep `get_span_type` for `extract_from_pyobject`.
5. Update emitted comments ("construct a canonical fltk._native.SourceText from the full text string" → describes the O(1) shared-source path).

### 2.6 Retained legacy API

Keep `Span::source_full_text_str` and `get_source_text_type` (no `#[deprecated]` — consumer crates build with `-D warnings`): previously-generated consumer `cst.rs` files still call them; removal would break consumer builds on fltk upgrade before regeneration. Update both docstrings to point at `span_to_pyobject` and note retention is for compatibility with previously-generated code. No TODO entry needed (harmless retained API; removal can ride a future deliberate breaking cycle).

### 2.7 Bookkeeping

- `span.rs`: delete the `TODO(span-source-as-py-crosscdylib)` block in `source_as_py`'s doc (lines 141-150); rewrite the cross-cdylib paragraph to describe `span_to_pyobject` as the cross-cdylib path. (`gsm2tree_rs.py` has no slug comments — verified by grep.)
- `TODO.md`: remove the `span-source-as-py-crosscdylib` entry; extend `crosscdylib-abi-sentinel`'s location list with `extract_source_text` and a note that the `SourceText` ABI marker (`FLTK_CST_CORE_ABI`) is the seed mechanism to unify with — and that it does not cover pyo3-resolution skew (§3), which the strengthened derivation must address.
- `fltk/_native/__init__.pyi`: add `_fltk_cst_core_abi: typing.ClassVar[str]` to `SourceText` and `_with_source_unchecked` classmethod to `Span` (docstring: internal, generated-code use only) — required for pyright on tests that call them directly. Stub tests filter underscore names (`tests/test_fltk_native_stub.py:142,157`), no conflict.
- Regenerate + rebuild: `make gencode` (covers `src/cst_generated.rs`, `src/cst_fegen.rs` + `fltk/_native/fegen_cst.pyi`, `tests/rust_cst_fixture/src/cst.rs`), `make fix`, then `make build-native build-test-user-ext build-fegen-rust-cst`. After regen, `source_full_text_str`/`get_source_text_type` call sites in generated files drop to 0.

### 2.8 File-change summary

| File | Change |
|---|---|
| `crates/fltk-cst-core/src/cross_cdylib.rs` | + `FLTK_CST_CORE_ABI`, `extract_source_text`, `span_to_pyobject`; `TODO(crosscdylib-abi-sentinel)` at marker check |
| `crates/fltk-cst-core/src/span.rs` | + `SourceText::_fltk_cst_core_abi` classattr, `Span::_with_source_unchecked`; doc updates; remove slug TODO |
| `crates/fltk-cst-core/src/lib.rs` | export `span_to_pyobject`, `extract_source_text` |
| `fltk/fegen/gsm2tree_rs.py` | §2.5 items 1–5 |
| `src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs`, `fltk/_native/fegen_cst.pyi` | regenerated |
| `fltk/_native/__init__.pyi` | stub additions |
| `TODO.md` | remove slug entry; extend `crosscdylib-abi-sentinel` |
| new tests | §4 |

## 3. Edge cases / failure modes

- **Version skew between cdylibs**: `fltk-cst-core` version mismatch → clean `TypeError` naming both ABI strings. Improvement over the status quo for the `SourceText` path; the `extract_span` path is unchanged and remains `crosscdylib-abi-sentinel`'s job. Limitations — cases where the marker matches but layouts differ (→ UB): (a) **pyo3-resolution skew**, the likeliest real-world class: consumer crates are standalone workspaces resolving `pyo3 = { version = "0.23", ... }` independently (`tests/rust_cst_fixture/Cargo.toml`; real out-of-tree crates likewise), and `PyClassObject<SourceText>` layout is a pyo3 internal with no cross-release stability guarantee, so two cdylibs can both report `fltk-cst-core/0.1.0` over different layouts; (b) two builds of the same `fltk-cst-core` version with local edits and no bump. And `fltk-cst-core` is `0.1.0`, effectively never bumped, so even the covered class is weak in practice. The §2.2 soundness invariant ("same pyo3 version, same struct layout") is the real contract; the marker is a partial detector, not a guarantee. Strengthening the derivation (pyo3 version, layout hash) is owned by `crosscdylib-abi-sentinel`; the emitted TODO comment must name pyo3-resolution skew explicitly (§2.2).
- **Forged marker** → UB (§2.2 contract delta). Private entry point; out of contract; documented at the `unsafe` site and in the method docstring.
- **Observable behavior change (intended)**: accessor-derived spans of the same parse previously raised `ValueError` on `merge`/`intersect`; they now succeed. No contract depends on the raise: it diverged from the Python backend (which succeeds via string-equality `_coerce_source`) and from the documented contract ("different sources" — same parse is one source); the raise was an artifact of the copying. No existing test asserts the *accessor-path* raise. (`tests/test_rust_span.py:173-179` `test_merge_different_sources_raises` constructs two distinct same-text `SourceText("hello")` objects directly — the residual-divergence case below, not the accessor path; it stays green: user-constructed `SourceText`s remain distinct `Arc`s, so `coerce_source` still raises.) This satisfies `request.md`'s "confirm no observable contract depends on the copying", and the change is a cross-backend-equivalence fix, not a regression.
- **Residual divergence (out of scope, unchanged)**: two *user-constructed* same-text `SourceText`s still fail `Arc::ptr_eq` on Rust merge while the Python backend succeeds (string equality). Pre-existing, untouched by this work, and actively pinned as intended Rust behavior by `test_merge_different_sources_raises` (same text, distinct objects). Any future cross-backend-equivalence pass on this divergence must revisit that test, not assume the behavior is untested.
- **Sourceless spans**: unchanged semantics on both paths (fast path clones `source: None`; slow path keeps today's `call1`). Satisfies the non-goal.
- **`fltk._native` not importable in a consumer process**: `get_span_type` error behavior unchanged from today.
- **Multiple consumer cdylibs in one process**: marker check is per-object and stateless; no cross-consumer registry needed.
- **Exotic objects passed to the private method** (metaclass `__getattr__` tricks, marker of wrong type): every failure lands on the `TypeError` paths before any `unsafe`.
- **Error-message change in generated accessors**: none for valid inputs; the only newly reachable error is the ABI-mismatch `TypeError`, which previously manifested as silent O(N) copying.

## 4. Test plan

TDD: items 1–3 are written first and must fail (red) against base, except where noted.

1. **In-tree Arc-sharing observable** (extend `tests/test_fegen_rust_cst.py`): build a `fltk._native.fegen_cst` node (submodule importability verified; registered in `sys.modules` at `src/lib.rs:36-48`) with `span=Span.with_source(...)`; read `.span` twice; `s1.merge(s2)` succeeds with expected bounds and `.text()`. Same via the `to_pyobject` path: append a span child, read it back through `children`/`child_<label>` twice, merge with the node's `.span`. Red today (`ValueError`, verified §1). Exercises the §2.4 fast path.
2. **Cross-cdylib observable — the case the fix exists for** (extend `tests/test_phase4_rust_fixture.py`): identical merge assertions through `phase4_roundtrip_cst` nodes (foreign cdylib → `_with_source_unchecked` marker path). Red today.
3. **Entry-point contract tests** (new class, `tests/test_rust_span.py`):
   - `fltk._native.Span._with_source_unchecked(0, 5, fltk._native.SourceText("hello world"))` → `.text() == "hello"` (fast extract path).
   - Same with `phase4_roundtrip_cst.SourceText(...)` (foreign-registered) → works; two spans built from the *same* foreign `SourceText` merge successfully (proves shared `Arc` crossed the boundary).
   - `fltk._native.Span.with_source(0, 5, phase4_roundtrip_cst.SourceText(...))` still raises `TypeError` (pins public `with_source` behavior; documents why the private entry point exists).
   - Negative gates (no `unsafe` reached): plain `str` argument → `TypeError`; object whose class sets `_fltk_cst_core_abi = "bogus/0.0.0"` → `TypeError` mentioning ABI mismatch.
4. **Existing suites green**: `tests/test_phase4_fegen_rust_backend.py` (`TestChildSpanAccessorContract` — runs against `fegen_rust_cst`, a foreign cdylib, so it exercises the new slow path end-to-end), `tests/test_fegen_rust_cst.py`, `tests/test_rust_span.py`, cross-backend equivalence tests.
5. **Gates**: `make build-native build-test-user-ext build-fegen-rust-cst` (fixture tests `importorskip` — they must actually run, not skip), `uv run pytest`, `uv run ruff check . && uv run pyright`, `cargo clippy -- -D warnings`, `make gencode` idempotent (empty `git diff` after a second run). Slug grep gate, scoped as in the `preamble-helpers-into-cst-core` precedent (repo-wide grep is unsatisfiable: this ADR dir's own name and immutable historical ADRs contain the slug): `grep -rn 'span-source-as-py-crosscdylib' --include='*.py' --include='*.rs' --include='*.pyi' .` returns nothing, and the slug is absent from `TODO.md`.

No Rust-level `cargo test` for Arc identity is required: the merge observable is Python-visible, which `request.md` §Verification prefers.

## 5. Open questions

None. Decisions the request delegated, resolved above: isinstance gate replaced by ABI-marker gate with explicit soundness argument (§2.1–2.2, correcting the sketch's directionality); entry point named `_with_source_unchecked`, additive and private (§2.3); public `with_source` untouched; legacy O(N) APIs retained for already-generated consumer code (§2.6); ABI string derivation = `CARGO_PKG_VERSION` now, strengthening owned by `crosscdylib-abi-sentinel` (§3).
