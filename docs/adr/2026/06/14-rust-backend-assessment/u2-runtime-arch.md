# U2 — Runtime Crate Architecture Map

Scope: `crates/fltk-cst-core/src/*.rs`, `crates/fltk-parser-core/src/*.rs`, `src/*.rs`
(the `fltk-native` cdylib). All file:line citations are against HEAD
`c0182064`. Read in full; nothing below is inferred from headers alone.

This is the *runtime* layer: hand-written Rust that generated parsers and CST node
structs link against. It is the analogue of the Python backend's hand-written
`fltk/fegen/pyrt/` (`memo.py`, `terminalsrc.py`, `errors.py`) — see the module
docstrings that explicitly call themselves "Port of …" (`memo.rs:1`,
`terminalsrc.rs:1`, `errors.rs:1`).

---

## 0. Crate topology and the pyo3 boundary (the single most important structural fact)

Two runtime crates, deliberately split on the pyo3 axis:

- **`fltk-cst-core`** (`crates/fltk-cst-core/Cargo.toml`): CST runtime. `crate-type = ["rlib"]`.
  pyo3 is an **optional** dependency behind a **default-on** `python` feature
  (`Cargo.toml`: `pyo3 = { version = "0.29", features = ["abi3-py310"], optional = true }`,
  `default = ["python"]`, `python = ["dep:pyo3"]`). A third feature
  `test-introspection` (implies `python`) gates the registry `snapshot` helper.
- **`fltk-parser-core`** (`crates/fltk-parser-core/Cargo.toml`): parser runtime.
  `crate-type = ["rlib"]`. **No `python` feature at all.** The Cargo.toml comment is
  explicit: *"pyo3-freedom is structural absence, not a disabled feature. … This crate
  never links pyo3."* I verified this empirically: `cargo tree -p fltk-parser-core`
  shows **no pyo3 node** in the dependency graph. It depends on `fltk-cst-core` with
  `default-features = false` (i.e. pyo3-off) and on `regex-automata` (no `default-features`,
  explicit feature list).
- **`fltk-native`** (root `Cargo.toml`, `src/lib.rs`): the `cdylib` →
  Python extension module `fltk._native`. `default = ["extension-module"]` →
  `extension-module = ["python", "pyo3/extension-module"]`. Pulls `fltk-cst-core`
  with `default-features = false` and re-enables `python` via its own forwarding
  `python = ["fltk-cst-core/python"]`. This is the "canonical" cdylib (see §4).

**Is the no-pyo3 path real?** Yes, structurally:
- `fltk-parser-core` cannot link pyo3 — there is no feature to turn it on, and the
  dep graph confirms absence. A pure-Rust consumer can use the parser runtime with
  zero Python.
- `fltk-cst-core` with `--no-default-features` compiles out all pyo3 code via
  `#[cfg(feature = "python")]`. `lib.rs:1-10` gates `mod cross_cdylib;` (line 1-2),
  the `registry` module (line 7-8), and all the pyo3 re-exports (`lib.rs:12-15`)
  behind the feature. `span.rs` gates every `use pyo3::…` and every `#[pyclass]`/
  `#[pymethods]` block behind `#[cfg(feature = "python")]` (e.g. `span.rs:1-10`,
  `:37-38`, `:55`, `:81-82`, `:155`, `:240`, `:382-383`). The native `Span`/`SourceText`
  structs and all their *pure-Rust* methods (text/merge/intersect/len/…) remain
  available without pyo3.
- Caveat on completeness: `mod py_module;` in `lib.rs:6` is declared **unconditionally**,
  but the file's contents are individually gated — `user_facing_name` is
  `#[cfg(any(feature = "python", test))]` (`py_module.rs:1`) and the two public
  `register_submodule*` fns are `#[cfg(feature = "python")]` (`:90`, `:135`). So with
  pyo3 off the module compiles to (almost) nothing. This is fine but slightly subtle —
  a reviewer scanning `lib.rs` sees an ungated `mod py_module;` and has to chase the
  per-item cfgs to confirm.
- The Makefile feature matrix builds both `python` and `--no-default-features`
  (per repo facts); the cfg discipline above is what makes that matrix pass.

Bottom line: the pyo3/no-pyo3 split is a genuine architectural seam, not cosmetic.
The parser runtime's pyo3-freedom is enforced by *absence of a feature*, which is the
strongest possible guarantee (you cannot accidentally turn on what doesn't exist).

---

## 1. `shared.rs` — the `Shared<T>` ownership model

`Shared<T>` (`shared.rs:51`) is a newtype over `Arc<RwLock<T>>`. Every node-typed child
in a generated CST is stored as `Shared<ChildType>` so multiple Python handles and the
Rust side alias the *same* node (reference semantics matching the Python backend).

API surface (all the runtime exposes):
- `new` (`:55`), `read`/`write` (`:60`,`:65`), `ptr_eq` (`:73`), `arc_ptr` (`:80`,
  registry key), `strong_count` (`:88`, used by generated iterative `Drop`),
  `Clone` (shallow — refcount bump, `:93-98`), `PartialEq` (`:103-114`),
  `Debug` (`:116-120`), `From<T>` (`:122-126`).

Three load-bearing design decisions, all documented in the 47-line module doc and
worth scrutiny:

1. **Poison ignored.** `read`/`write` do `.unwrap_or_else(|e| e.into_inner())`
   (`:61`,`:66`). A panic while a writer guard is held poisons a `std::sync::RwLock`;
   `Shared` swallows the poison so one panic cannot permanently brick a node tree
   (`:38-40`). Trade-off: a node observed *during* a panic-in-progress may be in a
   logically-torn state, and `Shared` will hand it out anyway. For a single-threaded
   Python embedding this is benign; in a genuine multi-threaded Rust consumer it is a
   silent correctness hazard the docs do not fully call out.

2. **`PartialEq` ptr_eq short-circuit + reliance on *generated* iterative `eq`**
   (`:103-114`, doc `:14-36`). `Shared::eq` first does `ptr_eq` to handle `x == x`
   without locking — because `std::sync::RwLock` same-thread double **read**-lock *may
   deadlock when a writer is queued*. The deeper recursion-safety claim ("bounded stack
   regardless of tree depth") does **not** live in `shared.rs` — it depends on the
   *generated* `T::eq` being worklist-based (confirmed in `crates/fegen-rust/src/cst.rs:343-364`,
   `eq_shallow_enqueue` + a `Vec<EqWorklistItem>` worklist). So `Shared`'s safety
   contract is split across two files, one hand-written and one generated. **Documented
   residual hazard** (`shared.rs:27-36`): the ptr_eq short-circuit only fires when the
   *same* `Shared` sits at the *same position* on both sides. A position-shifted shared
   node in a DAG (B→A vs C→A) read-locks A while an outer guard is held → same-thread
   read re-entry → may deadlock if a concurrent writer is queued. Conclusion in the
   doc: "Deep `PartialEq` on a DAG is only deadlock-free in the absence of concurrent
   writers." This is an honest, precise statement of a real limitation — but it *is* a
   limitation, and it means `Shared<T>` is not a safe general-purpose concurrent type;
   it is safe under the GIL-serialized single-writer assumption the Python embedding
   provides.

3. **Cycles / `Debug`.** User-created reference cycles are possible (shared ownership),
   `PartialEq` loops forever via unbounded worklist growth (not stack overflow), `Debug`
   loops forever, and cycles leak (Arc doesn't break cycles) (`:42-47`). "Same contract
   as the Python backend." Generated `Debug` is *manual* and non-recursive
   (`cst.rs:305-317`) precisely to avoid attacker-controlled-depth stack abort — again,
   the safety property is in generated code, not `shared.rs`'s `Debug` impl (which *does*
   recurse via `fmt::Debug::fmt(&*self.read(), f)` at `:118` — but it only recurses one
   level because the contained `T`'s own `Debug` is the non-recursive generated one).

**`unsafe` count in `shared.rs`: zero.** It is entirely safe Rust over `Arc<RwLock<T>>`.

---

## 2. `registry.rs` — canonical-wrapper registry (handle identity, the "GC")

This is `#[cfg(feature = "python")]` only (`lib.rs:7-8`). It is **not** a Rust GC; it is a
**Python-object-identity cache**.

**Why it exists** (`registry.rs:1-13`): when Rust returns a node-typed child to Python it
must return the *same* Python object every time so Python `is`-identity is stable
(`a is b` must be `True` for two reads of the same node). Without caching, every wrap-out
would `Py::new` a fresh object and `a is b` would always be `False`.

**Mechanism.** Process-wide `PyOnceLock<Py<PyAny>>` (`:34`) holding a Python
`weakref.WeakValueDictionary` (`:38-42`), keyed by `Shared::arc_ptr()` (the `Arc` address
as `usize`) → weak ref to the canonical `Py<PyAny>` handle. Operations
(all require the GIL):
- `lookup` (`:50`), `register_if_absent` (`:66`, via Python `setdefault` + identity
  compare), `force_register` (`:92`, via `set_item` — overwrite), `get_or_insert_with`
  (`:106`, the wrap-out helper child accessors call), `snapshot`
  (`:142`, test-only, `cfg(any(test, feature="test-introspection"))`).

**Why the "GC" framing.** The WeakValueDictionary *is* the GC integration: weak values
auto-evict when Python GC's the handle (`:19-22`). The canonical handle holds the `Arc`
**strongly** (the `Shared<T>` lives inside the `PyNode` struct), so the Rust allocation
cannot be freed while a live Python handle exists, and the registry entry cannot
dangle. The **ABA-safety argument** (`:19-22`): address reuse is only possible after
*both* the handle and the `Arc` are dead, at which point the weak entry is already
evicted — so a recycled `Arc` address can never collide with a stale live entry.

**Soundness caveats I'd flag for the retrospective:**
- The whole invariant ("at most one live Python handle per allocation", `:13`) assumes
  **single-threaded Python**. `get_or_insert_with` has a race branch (`:117-128`) that
  it itself annotates "Single-threaded Python: this never races" / "unreachable in
  practice." With free-threaded / no-GIL CPython (a stated direction for the ecosystem;
  pyo3 0.29 has some support) this assumption weakens. The code *does* have a fallback
  (re-lookup the winner, or `PyRuntimeError`), so it degrades to an error rather than
  UB — but the comments reveal the design was reasoned about under a GIL it may not
  always have.
- `force_register`'s caller contract (`:86-91`) is a sharp edge: registering an address
  with an unrelated object **corrupts typed accessors** — a later `get_or_insert_with`
  hit returns the wrong-typed object to a caller that casts it. The mitigation is "only
  call from generated code / `to_py_canonical` where the pairing is guaranteed by
  construction." Confirmed: generated `to_py_canonical` does exactly
  `force_register(py, addr, …)` after minting a fresh `Shared`+handle
  (`cst.rs:553-582`). The safety here rests on generator correctness, not the type
  system.

**`unsafe` count in `registry.rs`: zero.** All Python interaction is via the safe pyo3
object protocol.

---

## 3. `span.rs` (cst-core) — the Span/SourceText value types

The data model:
- `SourceInner { text: String }` (`:46-48`) — heap allocation holding the source.
- `SourceText { inner: Arc<SourceInner> }` (`:55-58`), `#[pyclass(frozen)]` under the
  python feature. Thin-pointer wrapper deliberately chosen so `Option<Arc<SourceInner>>`
  is 8 bytes (vs 16 for `Arc<str>`), keeping `Span` at 24 bytes (`:40-45`,`:140-143`).
- `Span { start: i64, end: i64, source: Option<Arc<SourceInner>> }` (`:157-161`),
  `#[pyclass(frozen, eq, hash, from_py_object)]`. **Indices are Unicode codepoints, not
  bytes** (`:140-148`) — this is the cross-backend parity contract (Python str indexing).
  Cloning a span is a refcount bump, not a string copy.

Notable semantics:
- **Equality/hash use only `(start, end)`; source is excluded** (`:176-189`). So a
  sourceless sentinel `==` a source-bearing span at the same offsets. This is deliberate
  parity with the Python sentinel `UnknownSpan` and with `terminalsrc.Span` value
  semantics. It is also a footgun a downstream consumer could trip on (two spans into
  *different* sources compare equal) — but it's the documented contract.
- `text()` (`:286-327`) does a **single forward `char_indices()` pass** to translate the
  codepoint range to byte offsets (a prior impl rescanned from 0 per index; this is the
  optimized version). Handles empty/zero-length/OOB by returning `None`.
- `merge`/`intersect` (`:353`,`:367`) refuse to combine spans from *different* sources
  (`coerce_source` → `SpanError::SourceMismatch`, `:270-275`); Python-facing wrappers map
  that to `ValueError` (`:529-543`).
- `text_or_raise` (`:467-504`) is the raising variant with specific messages; it contains
  an `.expect(...)` (`:488`) guarded by a prior `is_none()` check — a deliberate
  "invariant" panic that should be unreachable.
- `kind` getter (`:574-590`) reaches back into Python:
  `import fltk.fegen.pyrt.terminalsrc; SpanKind.SPAN`, cached in a `PyOnceLock`
  (`:38`). The doc flags an **acyclicity invariant** (`:36`): `terminalsrc` must never
  import `fltk._native`, or this becomes an import cycle. That's a cross-language coupling
  that isn't enforced by anything except a design-time note — a latent fragility.

**`unsafe` count in `span.rs`: zero.** The pyo3 surface is `#[pymethods]`/`#[classattr]`,
all safe. The ABI `_fltk_cst_core_abi` / `_fltk_cst_core_abi_layout` classattrs
(`:103-130`, `:390-412`) are *defined* here (delegating to the `*_abi_layout_probe`
helpers `:136`,`:596`) but *consumed* in `cross_cdylib.rs` (§4). `lib.rs:30-76` has
compile-time guard tests that the probe is not a stub (floor check + classattr-body
match) — a nice anti-regression measure.

---

## 4. `cross_cdylib.rs` — the ABI sentinel mechanism (the riskiest file in the runtime)

This is **the** place the runtime contains `unsafe`. python-feature-gated
(`lib.rs:1-2`). 397 lines. It exists to solve one problem:

**The boundary it protects.** FLTK's whole point is out-of-tree consumers. An out-of-tree
consumer crate is its *own* cdylib that links its *own* copy of the `fltk-cst-core` rlib
and registers its *own* `Span`/`SourceText` pyclasses with pyo3. When such a consumer
produces a `Span` that must interoperate with the canonical `fltk._native.Span` (e.g. a
generated `cst.rs` reading a source-bearing span calls `span_to_pyobject`), pyo3's normal
`extract::<Span>()` / `downcast` **fails** — because the type object identity differs
across cdylibs (each cdylib has a distinct registered type). So there is no safe pyo3 path
to recover the native `Span`/`SourceText` from the foreign Python object. The code falls
back to `cast_unchecked` (reinterpret the `PyClassObject` memory as the local type) —
which is sound **only if both cdylibs link the same fltk-cst-core rlib at the same pyo3
version with the same struct layout.**

**The sentinel gate.** Because type identity can't be used, the gate is two
forgeable-from-Python classattrs exposed on the foreign type:
- `_fltk_cst_core_abi` = `concat!("fltk-cst-core/", env!("CARGO_PKG_VERSION"))`
  (`cross_cdylib.rs:19`, defined `span.rs:103-106`,`:390-393`). Catches version skew.
- `_fltk_cst_core_abi_layout` = `size_of::<<T as PyClassImpl>::Layout>()`
  (`span.rs:127-138`,`:409-412`). Catches pyo3-resolution / layout skew the version
  string can't (e.g. two builds at the same fltk-cst-core version but different pyo3
  minor that reshapes the pyclass allocation).

`check_abi_pair::<T>` (`:158-233`) validates both, with 7 explicit failure branches each
producing a `TypeError` (missing marker, non-str, string mismatch, missing layout,
non-int, layout mismatch). Errors are escaped via `escape_control_chars` (defense against
control chars in type names in error messages). On success the type is cached
(`FLTK_FOREIGN_SOURCE_TEXT_TYPE` `:35`, `FLTK_NATIVE_SPAN_TYPE` `:303`) so subsequent
calls are an O(1) pointer compare, not repeated `getattr`.

**The three `unsafe` blocks — the entire unsafe inventory of the runtime:**

| # | Location | Operation | Invariant it relies on |
|---|----------|-----------|------------------------|
| 1 | `cross_cdylib.rs:86` | `obj.cast_unchecked::<SourceText>()` (cache-hit fast path) | The cached foreign type pointer `is` the object's type → it's the *exact* class already ABI-validated on a prior call. Identity ⇒ same validated layout. |
| 2 | `cross_cdylib.rs:112` | `obj.cast_unchecked::<SourceText>()` (post-validation slow path) | `check_abi_pair::<SourceText>` just returned `Ok` → `_fltk_cst_core_abi` matches and layout size matches. |
| 3 | `cross_cdylib.rs:331` | `obj.cast_unchecked::<Span>()` (after `is_instance` against `fltk._native.Span`) | `get_span_type` already ran `check_abi_pair::<Span>` (once, at PyOnceLock init); `is_instance` confirms it's that canonical type. |

**What the unsafe relies on, stated precisely (the SAFETY comments are unusually candid,
`:98-115`, `:322-333`):** soundness needs both cdylibs to link the *same* fltk-cst-core
rlib at the *same* pyo3 version so `PyClassObject<T>` layout is identical and
`cast_unchecked` merely reinterprets the same bytes. `SourceText`/`Span` are
`#[pyclass(frozen)]` and not subclassable, so `PyClassImpl::Layout` collapses to
`{ffi::PyObject, T}` (`repr(C)`), and `Bound::get()` returns `&T` with no borrow-flag
check. Cross-cdylib Arc refcount/dealloc is safe because Rust's default global allocator
is the shared process-wide system allocator.

**What could go wrong (the residual risk the code itself admits):**
1. **Size-preserving layout skew is NOT caught.** The SAFETY comments (`:101-108`,
   `:325-330`, and the classattr docs `span.rs:117-126`,`:403-408`) state plainly: size
   equality is *necessary but not sufficient* for layout identity. A pyo3 build that
   reorders internal fields while preserving total size would pass the probe → UB. The
   code argues this is "not constructible without changing `ffi::PyObject` itself, which
   changes the size" — a *plausibility* argument, not a proof. The probe "narrows — not
   closes — the layout-skew window." This is an **accepted risk**, explicitly.
2. **Forgery → UB.** Both markers are plain Python-readable strings/ints, forgeable from
   pure Python. A hand-crafted class with the right `_fltk_cst_core_abi` and matching int
   but a *different* memory layout, passed to the underscore-private
   `Span._with_source_unchecked`, is **Undefined Behavior** (`:46-53`, `span.rs:439-443`).
   The defense is purely *by convention*: the only intended caller is `span_to_pyobject`
   passing genuine `source_as_py` output, and the method is "private by leading
   underscore." There is no runtime barrier — a determined or buggy Python caller reaches
   UB. The doc's justification (`:48-51`) is that calling an underscore method with a
   forged object is "out of contract." For a security-sensitive embedding this is a real
   soundness hole behind a naming convention.
3. The "stronger than isinstance" claim (`:52-53`) is true *for the skew it detects* —
   a mismatch yields a clean `TypeError` instead of silent UB. But (1) and (2) are the
   ways it can still go wrong.

**Fast/slow path structure** (`span_to_pyobject` `:257-297`): caches `IS_CANONICAL_CDYLIB`
(`:240`) — if this cdylib *is* `fltk._native`, `Py::new` directly (zero Python calls).
Otherwise the slow path builds a consumer-registered `SourceText` via `source_as_py` and
calls the cached `_with_source_unchecked` classmethod on the canonical type. Note
`get_source_text_type` (`:384`) is retained for *backward compat with
already-generated consumer cst.rs* and is explicitly **not** ABI-validated (`:380-383`) —
its doc says callers must not use it for `cast_unchecked`. That's a loaded gun left in the
public API for compat reasons.

**Assessment of this file:** the engineering is careful and the SAFETY comments are some
of the most honest I've seen — they name their own residual unsoundness. But the net
position is: the runtime's *only* unsafe is a cross-cdylib type pun gated by a
forgeable, size-only sentinel, whose soundness ultimately rests on (a) a build-discipline
invariant not mechanically enforced and (b) a Python-side naming convention. For a
near-drop-in single-cdylib `fltk._native` deployment the fast path never touches the
unsafe at all. The risk is concentrated entirely in the multi-cdylib out-of-tree
consumer scenario — which is precisely FLTK's stated primary use case.

---

## 5. `error.rs` / `escape.rs` (cst-core)

- **`error.rs`** (60 lines): `CstError` enum (`ChildCount`, `UnexpectedChildType`),
  `#[non_exhaustive]`, for GIL-free native accessors (`child_<lbl>`, `maybe_<lbl>`).
  Important note (`:9-11`): **generated Python pymethods do NOT route through this** —
  they construct `PyErr` directly to avoid churning Python error messages. So there are
  two error paths (native Rust vs Python-facing), a deliberate divergence to preserve the
  public Python error surface. Zero unsafe.
- **`escape.rs`** (223 lines): `escape_control_chars` — the canonical control/bidi/
  zero-width escaper, **byte-for-byte pinned** to the Python
  `fltk/fegen/pyrt/errors.py:escape_control_chars` (`:1-30`). The pin is maintained by
  duplicated literal test strings here and in `tests/test_pyrt_errors.py`. `fltk-parser-core`
  re-exports this exact impl (`errors.rs:89`) to keep one source of truth. `#[doc(hidden)]`
  module (`lib.rs:4`). Zero unsafe. Output is deliberately not round-trippable
  (`escape.rs:28`). This cross-language byte-pin is a parity-critical detail and is the
  kind of thing that silently drifts if either side is edited without the other.

---

## 6. `py_module.rs` (cst-core) — module-wiring helpers

The `register_submodule` / `register_submodule_with_parent_name` public helpers
(`:90`,`:135`) plus the `user_facing_name` heuristic (`:26-46`). Used by *generated*
`lib.rs` (e.g. `crates/fegen-rust/src/lib.rs:22-23` does
`register_submodule(m, "cst", cst::register_classes)`).

The substance is the **maturin double-nesting heuristic** (`user_facing_name`): maturin
produces `fegen_rust_cst/fegen_rust_cst.abi3.so` so pyo3 reports
`__name__ = "fegen_rust_cst.fegen_rust_cst"`; the helper strips the redundant inner
segment so `sys.modules` keys are clean (`fegen_rust_cst.cst`). It has a **documented
false-positive** (`:18-25`,`:220-228`): a genuine `a.b.b` layout is indistinguishable from
maturin double-nesting and gets wrongly stripped to `a.b`; the escape hatch is the
`_with_parent_name` variant. `register_submodule_impl` (`:147`) creates the submodule,
runs the registration closure, `add_submodule`, sets `__name__`, and inserts into
`sys.modules` (so `import parent.sub` works). One open `TODO(native-submodule-error-context)`
(`:86-89`) — errors don't name which submodule failed.

Zero unsafe. This is mundane plumbing; the only real risk is the heuristic false-positive,
which is bounded and has an escape hatch.

---

## 7. `fltk-parser-core` — the parser runtime (no pyo3)

### 7.1 `memo.rs` — packrat memoization with left-recursion (seed-grow)

Port of `memo.py`, Warth/Douglass/Millstein seed-grow variant (`:1-12`). The key
**structural change from Python** (`:4-7`): Python mutates a `Poison` object aliased
between stack frames; Rust instead keeps poison/recursion info *inside the cache entry*
and re-fetches the entry after the rule call returns (ownership-safe). Claimed
"observably equivalent."

Types: `ApplyResult<T>` (`:19`), `RecursionInfo` (`:28`), `MemoResult<T>` enum collapsing
Python's untyped union into `Poison(Option<RecursionInfo>) | Value(T) | Failure`
(`:45-49`), `MemoEntry<T>` (`:55`), `Cache<T> = HashMap<i64, MemoEntry<T>>` (`:62`).

`PackratState` (`:93-107`): `invocation_stack`, `recursions` (active growth cycles by
start pos), and the **DoS guard fields** `max_depth`/`depth`/`depth_exceeded`.

**The parse-depth limit (the parser DoS guard):**
- `DEFAULT_MAX_DEPTH = 1000` (`:74`). The doc-comment sizing rationale (`:64-73`) is
  detailed: ~5-7 native frames per rule application × 1000 ≈ 5-7k frames, fits an 8 MiB
  main-thread stack. **Explicit warning**: spawned Rust threads default to 2 MiB and
  async worker threads vary, so callers on smaller stacks must lower `max_depth` or grow
  the stack. There's even a warning *not to test the default from `cargo test`* (2 MiB
  test threads) — use pytest.
- Enforcement in `apply` (`:182-201`): increments `depth` on entry, checks
  `depth_exceeded || depth >= max_depth` → sets the **sticky** `depth_exceeded` flag and
  returns `None`. Decrements `depth` after `apply_inner`.
- **Sticky-flag contract** (`:103-106`,`:139-146`,`:158-164`): once set,
  `depth_exceeded` is never cleared — the parser instance is *spent*. **Callers MUST check
  `depth_exceeded()` after parsing and discard the result if set**, because a depth-rejected
  growth iteration can leave a left-recursive seed surfacing as `Some` that is *not* the
  parse the grammar defines. This is a real, sharp caller obligation: a consumer who
  forgets the check can silently get a wrong (truncated) parse tree rather than an error.
  This is the single most important behavioral footgun in the parser runtime.
- **Panic/PanicException interaction** (`:84-91`): a memo-invariant panic inside
  `apply_inner` *skips* the `depth` decrement (it aborts parse state). pyo3 converts the
  Rust panic to `PanicException`; if a Python caller catches it and reuses the same
  parser, `depth` is stale. Contract: treat any `PanicException` as "instance spent."

**The deliberate panics.** Per the module doc (`:9-11`) all Python `assert`s are ported
as `assert!` (always-on, not `debug_assert!`) — "cheap algorithm invariants that should
fire loudly." There are *many* (`:276`,`:304`,`:332`,`:351`,`:373`,`:379`,`:459`,…) plus
two genuine `panic!`s: the "Untested corner case" (`:227`, a faithful port of the
memo.py:181-187 unreachable case) and an invariant-violation panic (`:233`). In the Python
binding these become `PanicException`. So: **a malformed/edge-case parse can panic the
parser**, which crosses into Python as a catchable-but-instance-spent `PanicException`.
For a parser fed untrusted input, "panic on an untested corner case" is a liveness
concern worth flagging — it's a faithful port of a Python `assert`/raise, but in Rust a
panic in a library is a heavier event.

`apply` is a **free function**, not a method (`:182`), deliberately — to dodge the
triple-`&mut self` borrow that the Python call shape `self.packrat.apply(self.parse_X)`
would require. It takes `fn` pointers (`state`/`cache`/`rule` projectors) so the rule can
re-enter `apply` freely. `T: Clone` because cache hits clone the stored result; for
generated code `T = Shared<NodeT>` so a hit is an Arc-clone (reproducing Python's object
sharing). Zero unsafe.

### 7.2 `terminalsrc.rs` — terminal source + regex-anchoring DoS guard

Port of `terminalsrc.py` (`:1-6`). `TerminalSource` (`:38-47`) holds a `SourceText`
(Arc-shared) plus a **`cp_to_byte: Vec<usize>` table built once at construction**
(`:56-74`) — codepoint index → byte offset, with a `[len] = text.len()` sentinel. All
external positions are codepoint indices (`i64`); methods translate to bytes via the
table or binary search. `line_ends` is a lazy `OnceLock<Vec<i64>>` (`:46`,`:191-206`),
which keeps `&self` ergonomics and makes the struct `Sync`. Memory note (`:41-42`): 8
bytes/codepoint; acknowledged as acceptable for grammar-sized inputs (could be `u32` to
halve it — deferred).

**`consume_literal`** (`:110-126`): rejects `pos < 0` and `pos > len` (returns `None`).
**Deliberate divergence from Python** (`:33-37`,`:107-109`): Python wraps negative indices
(subscript semantics); this rejects them, because negatives are unreachable from generated
code and can't produce valid spans. Returns *source-bearing* spans (Python returned
sourceless) — fine because span equality ignores source.

**`consume_regex`** — **this is the regex-anchoring DoS guard** (`:128-166`):
- Uses `regex-automata` (`Regex`, `Anchored`, `Input`). It builds
  `Input::new(text).anchored(Anchored::Yes).span(byte_pos..text.len())` (`:147-149`).
- **`Anchored::Yes`** guarantees any returned match begins exactly at `byte_pos`, so a
  **non-match fails immediately without scanning the rest of the haystack** (`:136-138`).
  This is the anti-DoS property: without anchoring, a `consume_regex` at every position
  could become an O(n) unanchored scan per call → O(n²) parse. Anchoring makes each call
  start-pinned.
- Crucially it passes the **full haystack** with a `span` start (not a `text[pos..]`
  slice) so `\b`/`\B` lookbehind assertions resolve against the char *before* `byte_pos`,
  reproducing Python's `re.match(pattern, string, pos=byte_pos)` exactly (`:133-137`).
  There are dedicated tests for this context-sensitivity (`:368-389`) — a sliced-haystack
  impl would silently mis-handle word boundaries.
- The deeper DoS resilience (catastrophic backtracking immunity) comes from the
  **engine choice**: `regex-automata` with the explicit feature set in Cargo.toml
  (`nfa-backtrack`, `nfa-pikevm`, `hybrid`, `dfa-onepass`, …). This is a finite-automaton
  engine family with linear-time guarantees, not a backtracking PCRE — so pathological
  patterns can't blow up exponentially the way Python's `re` (or a naive backtracker) can.
  That engine choice is the *real* regex-DoS defense; anchoring is the per-call
  short-circuit on top of it.
- Match-end byte offset → codepoint index via `cp_to_byte.partition_point` binary search
  (`:160`), with a `debug_assert` that the end is a char boundary (`:161-164`).

**`pos_to_line_col`** (`:180-228`): bisect over lazily-computed `line_ends`; domain
`[-1, len]`, with `pos == len` decremented to `len-1` (faithful to terminalsrc.py:187-188)
and `-1` accepted as the `ErrorTracker.longest_parse_len` sentinel. Out-of-domain →
`None` (Python raised `ValueError`; here unreachable from own call sites).

`re_compile` parity, `\b`/`\B` context, multibyte offset handling all have unit tests
(`:231-519`). Zero unsafe. Uses `assert!`/`debug_assert!` for invariants.

### 7.3 `errors.rs` — farthest-failure tracking + message formatting

Port of `errors.py` (`:1-6`). `TokenType` (`:15`), `ParseContext`
(`:25-30`, `Copy`, `token: &'static str` so the hot failure path is allocation-free —
all literals/patterns from generated code are `'static`). `ErrorTracker` (`:40-50`,
manual `Default` so `longest_parse_len = -1` not `0`) implements the farthest-failure
heuristic: `fail` (`:69-79`) ignores failures behind the farthest pos, appends at the
same pos, replaces on advance.

`format_error_message` (`:123-158`) reproduces Python's error-message format
**byte-equivalently** including: caret alignment computed from the *escaped* prefix
(`:141-147`), control-char escaping via the shared `escape_control_chars`, and
`py_repr_str` (`:205-230`) reproducing Python 3 `str.__repr__` quoting rules for tokens.
Determinism note (`:111-121`): Python's `defaultdict(set)` iteration is hash-random; Rust
groups by `rule_id` in **first-occurrence order** and dedups within group — *more*
deterministic than Python, with a documented caveat that the parity comparator must treat
multi-token rule groups as unordered sets. Extensive golden tests (`:232-543`). Zero
unsafe.

---

## 8. `fltk-native` (root `src/`)

`src/lib.rs` (22 lines) is now **runtime-only** (post-commit `c018206`,
"refactor _native to runtime-only"). The `#[pymodule] _native` (`:11-22`) registers only
`Span`, `SourceText`, and an `UnknownSpan` sentinel (a `Span::unknown()` stored in a
`PyOnceLock<Py<PyAny>>` `:9`,`:18-21`). All grammar-specific CST was removed from
`fltk._native`; per-grammar code is now generated into separate cdylibs (e.g.
`crates/fegen-rust/`). `src/span.rs` (2 lines) just re-exports `SourceText`/`Span` from
`fltk-cst-core`. So `fltk._native` is the *canonical* cdylib whose `Span`/`SourceText`
type objects every consumer cdylib targets via the cross_cdylib ABI machinery (§4).

This mirrors the Python backend's `pyrt` (hand-written runtime) vs codegen split — the
commit message states this parallel explicitly. Architecturally clean: the runtime cdylib
carries no grammar.

---

## 9. Full `unsafe` inventory (runtime crates) — exhaustive

Total unsafe blocks across all of `fltk-cst-core/src`, `fltk-parser-core/src`, `src/`:
**3**, all in `cross_cdylib.rs`, all `cast_unchecked` of a Python object to a local
pyclass across the cdylib boundary:

1. `cross_cdylib.rs:86` — `cast_unchecked::<SourceText>` on cache-hit (relies on: cached
   foreign-type pointer identity ⇒ already ABI-validated class).
2. `cross_cdylib.rs:112` — `cast_unchecked::<SourceText>` after `check_abi_pair` Ok
   (relies on: ABI string + layout-size match between cdylibs).
3. `cross_cdylib.rs:331` — `cast_unchecked::<Span>` after `is_instance` on the
   ABI-validated `fltk._native.Span` (relies on: same).

Shared invariant for all three: **both cdylibs link the same `fltk-cst-core` rlib at the
same pyo3 version with identical pyclass layout.** Residual unsoundness (admitted in
SAFETY comments): size-preserving layout reorder is not detected; pure-Python forgery of
the markers reaches UB through the underscore-private `_with_source_unchecked`. The unsafe
is *never reached* on the fast (single-cdylib `fltk._native`) path.

`fltk-parser-core` and the native `src/` contain **zero** unsafe. `shared.rs`,
`registry.rs`, `span.rs`, `error.rs`, `escape.rs`, `py_module.rs`, `memo.rs`,
`terminalsrc.rs`, `errors.rs` — all zero unsafe.

---

## 10. Net architectural read (for the retrospective)

- The runtime is **well-factored along the right seam**: pyo3-bearing CST runtime vs
  pyo3-free parser runtime, with the parser runtime's purity enforced by feature
  *absence*. The no-pyo3 path is real.
- **The unsafe surface is tiny and concentrated** (3 blocks, one file) and its SAFETY
  documentation is unusually honest about its own residual unsoundness. That honesty is a
  strength, but the residuals are real and live exactly in FLTK's primary multi-cdylib
  use case: a size-only ABI probe + a by-convention private method is the thing standing
  between a version/build skew and UB. The mitigations are not mechanically enforced.
- **Several correctness/safety contracts are split between hand-written runtime and
  generated code** (iterative `Drop`/`eq`/non-recursive `Debug` for stack safety; the
  `force_register` address/handle pairing; `to_py_canonical`). The runtime is only safe
  *given a correct generator*. A reviewer cannot judge `Shared`/`registry` safety from the
  runtime alone.
- **Two sharp caller obligations in the parser runtime** that a drop-in consumer can
  silently violate: (a) must check `depth_exceeded()` and discard the result if set;
  (b) must treat any `PanicException` as instance-spent. Both are documented only in Rust
  doc-comments, not enforced by the API shape.
- **Cross-language byte-pins** (`escape_control_chars`, `format_error_message`,
  `py_repr_str`, `Span.kind` reaching into `terminalsrc`) are parity-critical and drift
  silently if one side is edited alone; they rely on duplicated golden tests, not a single
  source of truth.

None of these are obviously fatal; all are the kind of thing a production-readiness review
must weigh deliberately rather than wave through.
