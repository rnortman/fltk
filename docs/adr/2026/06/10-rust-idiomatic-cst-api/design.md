# Design: Rust-Idiomatic CST API with Shared Identity (feasibility + path forward)

Style: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Charter: evaluate feasibility of the user request, then chart a phased path. This doc seeds an ADR
(context / decision / consequences). No requirements doc exists; the verbatim user request plus the user's
answers A1–A3 (recorded in §7) and the scope directive (below) are the requirements basis.

Companions: `exploration.md` (fact survey for the rename/idiomatic-API work) and
`exploration-identity-abi.md` (fact survey for the two TODOs pulled into scope), same directory.

**Scope directive (user, this revision)**: pull `TODO(rust-cst-child-node-identity)` and
`TODO(crosscdylib-abi-sentinel)` into scope. These are connected to the mixed Rust/Python
same-CST-across-the-barrier goal (R3); integrating them now avoids churning the native API surface twice.

---

## 1. Context (ADR: Context)

The `cst-python-feature-gate` change (commit 63e6b76) made the generated Rust CST compilable without Python
via a cargo `python` feature. Three connected problems remain:

1. **`_native` suffixes** on every node method (`new_native`, `span_native`, `children_native`,
   `push_child_native` — `fltk/fegen/gsm2tree_rs.py` `_node_block`, lines 571–595). pyo3 `#[pymethods]` and
   plain `impl` blocks coexist on one struct; the generator gave the *Python* layer the natural Rust names
   and suffixed the native layer — backwards relative to R1.
2. **Clone-on-boundary child semantics** (`TODO(rust-cst-child-node-identity)`). Children are `Box<Child>` in
   the native Vec; every Python read of a node-typed child does `Py::new(py, (**n).clone())`
   (gsm2tree_rs.py:488). Python `is`-identity is unstable across reads and mutation of a read child does not
   propagate to the parent. The Python backend (`gsm2tree.py`) stores plain object references: identity is
   stable, mutation propagates, `extend_children` shares subtrees. The Rust backend diverges from the Python
   backend on exactly the semantics R3 needs — cross-backend behavioral equivalence (CLAUDE.md) argues for
   fixing the Rust side to match, not for documenting the divergence.
3. **ABI sentinel gaps** (`TODO(crosscdylib-abi-sentinel)`). `extract_span`'s cross-cdylib slow path is gated
   by `isinstance` only — version skew turns a packaging error into UB via `downcast_unchecked`
   (`crates/fltk-cst-core/src/cross_cdylib.rs:147–176`). The `SourceText` path has an ABI string check, but
   its derivation (`CARGO_PKG_VERSION` alone) does not cover pyo3-resolution skew. Every generated node
   method that touches spans (constructor, span getter/setter, `append`, `append_<lbl>`, `extend_<lbl>`)
   routes through these functions (exploration-identity-abi.md §"Connection"), so the new API rests on this
   foundation.

The user's requirements, restated:

- **R1**: No `_native` suffixes. Rust consumers get idiomatic, efficient, natural Rust APIs; it must not feel
  like sneaking under a Python layer.
- **R2**: Python consumers keep a normal Python API (must not regress).
- **R3**: Mixed Rust/Python applications work with *the same CST* on both sides, passing CST objects through
  the language barrier. Per A1 (§7), this means **shared mutable identity**: a child read from Python is the
  same object on every read, and mutations are visible from both languages. Slightly less idiomatic / more
  explicitly-exposed Python machinery in the Rust code is acceptable for the mixed case.
- **R4**: The CST API is the foundation for future generated Rust parsers; get the CST right first.

Per A2 (§7), cross-cdylib **node** passing is never needed (different grammars never share node classes), so
the sentinel work is scoped to the `Span`/`SourceText` paths in `fltk-cst-core` — hardening what every
generated node method already calls, not extending markers to node types.

### Breaking-change posture

Per CLAUDE.md, generated symbols are public API for out-of-tree consumers and absence of in-tree usage is not
proof of safety. Assessment for this change set:

- The Rust-only (`python`-off) surface shipped days ago (commit 63e6b76). The realistic out-of-tree adoption
  window is effectively zero; the only in-tree users of `*_native` are tests and generated outputs
  (`tests/rust_cst_fixture/src/native_tests.rs`, `crates/fltk-cst-spike/src/spike_tests.rs`).
- The user — the project owner — is explicitly directing the change, including the larger ownership
  restructure. This is the "deliberate, called-out decision" CLAUDE.md requires, recorded by this ADR. The
  Rust-surface break (Box → shared ownership) will never again be this cheap; after the parser generator
  exists it becomes prohibitively expensive.
- The **Python-visible API surface does not change**: names, signatures, `.pyi` stubs are untouched. Python
  *semantics* change only where the Rust backend currently diverges from the Python backend (identity,
  mutation propagation) — and they change *toward* the Python backend's behavior, i.e. toward cross-backend
  equivalence, which is the CLAUDE.md-stated goal.

---

## 2. Feasibility Verdict (summary)

| Requirement | Verdict | Basis |
|---|---|---|
| R1 — drop `_native`, natural Rust names | **Feasible, low risk** | handle/data split (§4) dissolves the name collision entirely; no `#[pyo3(name=...)]` gymnastics needed for nodes |
| R1 — *idiomatic* Rust surface (per-label accessors, `Debug`, iterators, error types) | **Feasible, moderate effort** | additive codegen; all info already in `CstGenerator.rule_models` |
| R2 — Python API unchanged | **Feasible, verifiable** | pymethods move to a handle pyclass with the same Python names; pytest suite + empty `.pyi` diff are the gates; only deliberate semantic changes are identity/mutation, which converge on the Python backend |
| R3 — same CST both sides, same cdylib | **Feasible — in scope** | `Shared<T>` child ownership + canonical wrapper registry (§4.2); resolves `TODO(rust-cst-child-node-identity)` |
| R3 — shared mutable identity | **Feasible, structural — in scope (Phase 1)** | children become `Shared<T>` (`Arc<RwLock<T>>` newtype); Python handles wrap the same `Shared`; registry restores `is`-stability |
| R3 — cross-cdylib node passing | **Permanently out of scope (A2)** | grammars never share node classes; recorded as an ADR consequence |
| Sentinel — span/source boundary soundness | **Feasible, in scope (Phase 0)** | add ABI gate to the `Span` path, strengthen derivation on both paths, cache boundary lookups; resolves `TODO(crosscdylib-abi-sentinel)` as scoped |
| R4 — parser-ready construction API | **Feasible; improved** | `new`/`push_child`/`extend_children` on the data struct, GIL-free; `extend_children` becomes refcount bumps instead of deep clones |

**Recommendation on workflow**: no requirements-first restart, even at the larger scope. The two questions
that previously gated the structural work (§7 Q1, Q2) are now answered by the user (A1, A2); the requirements
basis is R1–R4 + A1/A2 + the scope directive, all recorded here. One narrow new question (§7 Q4,
children-list live view) has a recommended default and gates only the Phase 3 documentation wording, not the
implementation phases. Remaining unknowns are implementation-verification items with explicit verify-first
gates (§5), not requirements ambiguity.

---

## 3. Decision (ADR: Decision)

Restructure each generated node into an always-compiled **data struct** carrying the natural-named Rust API
and a python-gated **handle pyclass** carrying the Python API, with children owned as `Shared<T>`
(`Arc<RwLock<T>>` newtype) and a canonical-wrapper registry restoring stable Python identity. This aligns the
Rust backend's reference semantics with the Python backend, resolves `TODO(rust-cst-child-node-identity)`,
and eliminates the name collision that forced the `_native` suffixes. Independently, harden the
`Span`/`SourceText` cross-cdylib boundary (ABI sentinel on the `Span` path, strengthened derivation,
boundary-lookup caching), resolving `TODO(crosscdylib-abi-sentinel)` as scoped by A2. Cross-cdylib node
passing is permanently out of scope. Same-cdylib is the supported mixed-language pattern.

---

## 4. Proposed Approach

Changes land in: the generator (`fltk/fegen/gsm2tree_rs.py`), `crates/fltk-cst-core` (new `Shared<T>`,
wrapper registry, `cross_cdylib.rs` hardening, `CstError`), the five committed generated outputs
(`src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fixture/src/cst.rs`,
`tests/rust_cst_fegen/src/cst.rs`, `crates/fltk-cst-spike/src/cst.rs` — the spike CST is *not* hand-written;
`make gencode` copies `src/cst_generated.rs` over it, Makefile:131–132), and Rust/Python tests. Only
`spike_tests.rs` and `native_tests.rs` are hand-maintained. Regen path: `make gencode` currently covers only
**four** of the five outputs (Makefile:121–132) — `tests/rust_cst_fegen/src/cst.rs` is regenerated by no
target (only built, `build-fegen-rust-cst` Makefile:89–90) and its crate is excluded from the root workspace,
so staleness is invisible to root `cargo check`. Phase 1 extends `gencode` with a
`gen-rust-cst GRAMMAR=fltk/fegen/fegen.fltkg RS_OUT=tests/rust_cst_fegen/src/cst.rs` step so all five outputs
regenerate from one target; without this, a stale `fegen_rust_cst` extension would let the §6 item 3
cross-backend gates pass against old clone-semantics code. Then regen → `make fix` → commit per CLAUDE.md.

### 4.0 Core model: data struct + handle pyclass + `Shared<T>`

**`Shared<T>`** — new pyo3-free newtype in `fltk-cst-core`:

```rust
pub struct Shared<T>(Arc<RwLock<T>>);   // std RwLock; poisoning ignored via PoisonError::into_inner
impl<T> Shared<T> {
    pub fn new(value: T) -> Self;
    pub fn read(&self) -> RwLockReadGuard<'_, T>;    // poison-transparent
    pub fn write(&self) -> RwLockWriteGuard<'_, T>;  // poison-transparent
    pub fn ptr_eq(&self, other: &Self) -> bool;
}
// Clone = shallow (Arc clone). PartialEq = ptr_eq short-circuit, then deep (read-locks both,
// compares values). The short-circuit is load-bearing, not an optimization: without it,
// comparing a Shared against itself (x == x from Python — CPython calls __eq__ even for
// identical operands, and the registry makes repeated reads the same object — or a DAG
// compare where one Shared sits at the same position on both sides) read-locks the same
// std RwLock twice on one thread, which std documents may deadlock when a writer is queued.
// Debug = delegates through read(). From<T> for Shared<T>. No Hash impl: node structs derive no
// Rust Hash, and generated nodes are deliberately unhashable Python-side (__hash__ raises
// TypeError, gsm2tree_rs.py:925-931) — preserved unchanged.
```

**Data struct** (always compiled; the Rust-native API; unchanged Rust type name, e.g. `Identifier`):

```rust
pub struct Identifier {
    span: Span,
    children: Vec<(Option<Identifier_Label>, IdentifierChild)>,  // Identifier_Label until the
}                                                                // Phase 2 rename (§4.3 item 5)
// Child enums: node-typed variants become Shared<T> instead of Box<T>:
//   ItemsChild { Span(Span), Identifier(Shared<Identifier>), Trivia(Shared<Trivia>) }
```

Derived `Clone` on the data struct becomes **shallow with respect to node children** (Arc clones) — this is
the reference semantics the Python backend already has; called out in rustdoc.

**Handle pyclass** (python-gated; carries every pymethod; Python class name unchanged):

```rust
#[cfg(feature = "python")]
#[pyclass(frozen, weakref, name = "Identifier")]
pub struct PyIdentifier { inner: Shared<Identifier> }

impl PyIdentifier {
    pub fn shared(&self) -> &Shared<Identifier>;   // mixed-app bridge: handle -> native world
    // mixed-app bridge, native -> Python: GIL-bound and registry-routed (wrap-out path) —
    // looks up the canonical handle for `s`, creating + registering one only on miss.
    pub fn to_py_canonical(py: Python<'_>, s: &Shared<Identifier>) -> PyResult<Py<PyIdentifier>>;
}
```

There is deliberately **no** bare `from_shared(s) -> Self` constructor: a bare handle struct cannot
participate in the registry (registration needs the Python heap object, which exists only after `Py::new`),
so such a path would mint unregistered aliases and silently break `is`-stability in exactly the mixed
Rust/Python scenario R3 serves. Every native→Python crossing — generated wrap-out, mixed-app code, the future
parser hand-off (§4.5) — goes through `to_py_canonical` (or the equivalent generated wrap-out helper).

All existing pymethods (`new`, `span` getter/setter, `kind`, `Label` classattr, `children`, `append`,
`extend`, `extend_children`, `child`, per-label quintet, `__eq__`, `__hash__`, `__repr__`) move to the handle
with **identical Python names, signatures, and `.pyi` output**; bodies lock `inner`. `frozen` works because
the handle has no mutable fields — all mutation goes through the `RwLock` (and removes pyo3 runtime borrow
checking from the picture). `weakref` is required by the registry and is additive (Python-backend dataclass
nodes already support weakrefs).

**Consequence for naming (R1)**: with pymethods on a separate struct, the plain `impl` on the data struct has
no colliding names. The `_native` suffixes are simply dropped — `new`, `span`, `children`, `push_child` —
with no `#[pyo3(name=...)]`/`py_` machinery needed for nodes. (The span.rs `py_` inversion remains correct
for `Span` itself, a frozen value type where one struct serves both layers.) This also removes the
previously-planned dependency on unverified `#[getter(name)]`/`#[setter(name)]` attribute forms: the handle's
getters/setters keep pyo3's bare name-inference forms already proven in the generator (gsm2tree_rs.py:647–653).

**Canonical wrapper registry** (python-gated helper in `fltk-cst-core`): a per-process
`GILOnceCell`-held weak-value map (e.g. Python `weakref.WeakValueDictionary`) keyed by `Arc` address
(`usize`), value = the canonical handle object. Two operations, both GIL-holding:

- **wrap-out** (`children` getter, `child`, per-label accessors, child-enum `to_pyobject`): look up the
  child's `Shared` address; hit → return the existing handle (refcount bump); miss → create the handle,
  register, return.
- **hand-in** (`append`, `extend`, `extend_children`, per-label mutators, `new` with node children if ever
  applicable): extract the handle's `Shared` (clone the Arc) for storage, and register the handle as
  canonical for that address if absent.

Soundness of the invariant "at most one live canonical handle per `Shared`": `py_new` mints a fresh
`Shared` per call (no aliasing at birth); every path that produces a handle for an existing `Shared` goes
through wrap-out / `to_py_canonical` (which reuses) or hand-in (which registers the first handle seen) — no
handle-producing path bypasses the registry (no bare `from_shared` exists; see above). Weak values
auto-evict on handle death; address reuse is only possible after both the handle and the `Arc` are dead, at
which point the entry is already evicted (the canonical handle holds the `Arc` strongly) — no ABA.

**Lock discipline (codegen rule)**: generated pymethods take locks in narrow scopes and **never construct or
call Python objects while holding a node lock** — snapshot what is needed (Arc clones of children, `Span`
clone), drop the guard, then build Python objects. Generated native methods never touch the GIL. This
excludes GIL↔lock ordering deadlocks by construction (deep `PartialEq` holds guards across recursion but
calls no Python — its same-lock re-entry hazard is handled by the `ptr_eq` short-circuit above; see §5);
the residual hazard (mixed-app user code acquiring the GIL while holding a `write()` guard) is documented in
Phase 3's docs.

### 4.1 Phase 0 — Span/SourceText boundary hardening (cst-core only; independent, lands first)

Resolves `TODO(crosscdylib-abi-sentinel)` as scoped by A2 (Span/SourceText only; no node markers). All in
`crates/fltk-cst-core` (`cross_cdylib.rs`, `span.rs`):

1. **ABI gate on the `Span` path**: add a `_fltk_cst_core_abi` classattr to `Span` (parallel to
   `SourceText`'s existing one) and verify it once in `get_span_type`'s `GILOnceCell` init — version skew
   then fails the *first* span boundary crossing with a clear `TypeError` naming both ABI strings, instead of
   proceeding to `downcast_unchecked` UB. `extract_span`'s slow path is unchanged structurally
   (`isinstance` against the now-validated canonical type, then `downcast_unchecked`) but is sound because
   the cached type object passed the gate.
2. **Strengthened derivation on both paths**: the current `FLTK_CST_CORE_ABI`
   (`"fltk-cst-core/" + CARGO_PKG_VERSION`) does not detect pyo3-resolution skew. Strengthen by adding
   layout-probe classattrs compared numerically at the same init points — e.g.
   `_fltk_cst_core_abi_layout = size_of::<PyClassObject<Span>>()` (and the `SourceText` analog) — and/or
   folding the resolved pyo3 version into the string. **Verify-first**: whether
   `pyo3::impl_::pycell::PyClassObject` is nameable/const-sized in pyo3 0.23, and whether the pyo3 version is
   accessible at build time, must be confirmed on a spike before committing to a mechanism; the requirement
   is that at least one verified mechanism closes the skew gap on both paths. If no mechanism survives
   verification, the residual gap gets a narrowed TODO — but the `Span`-path gate (item 1) lands regardless.
3. **Boundary caching**: cache the "this cdylib is canonical `fltk._native`" bool and the bound
   `_with_source_unchecked` classmethod in `GILOnceCell`s, so `span_to_pyobject`/`extract_span` stop
   re-deriving process-constant facts per call (cross_cdylib.rs:114 TODO). This is on the hot path of every
   generated span getter/setter.

No generator changes; no Python-surface changes. Phase 0 has no dependency on Phases 1–2 and de-risks the
foundation everything else calls.

### 4.2 Phase 1 — Ownership restructure + suffix removal (R1 core + R3; resolves identity TODO)

Generator changes (`_node_block`, child-enum emitters, pymethod emitters) plus the `Shared`/registry
primitives in cst-core (§4.0):

- Child enums: `Box<T>` → `Shared<T>` variants; `to_pyobject` goes through the wrap-out registry path
  (replacing `Py::new(py, (**n).clone())`, gsm2tree_rs.py:488); `extract_from_pyobject` clones the `Shared`
  out of the handle and registers it (hand-in).
- Node structs: pymethods move to the generated handle pyclass; the plain `impl` keeps exactly today's four
  methods, renamed suffixless:

  ```rust
  impl Identifier {
      pub fn new(span: Span) -> Self                                            // was new_native
      pub fn span(&self) -> &Span                                               // was span_native
      pub fn children(&self) -> &[(Option<Identifier_Label>, IdentifierChild)]  // was children_native
      pub fn push_child(&mut self, label: ..., child: ...)                      // was push_child_native
  }
  // Label-enum type spelled Identifier_Label at this phase; renamed IdentifierLabel in Phase 2 (§4.3 item 5).
  ```

- `register_classes` registers the handle types (same Python names).
- **Python-visible semantic changes** (deliberate; each converges on the Python backend):
  - Child reads are `is`-stable and mutation propagates parent↔child across reads and across languages
    (was: fresh clone per read). The five tests relaxed `is`→`==`
    (`tests/test_phase4_rust_fixture.py:242,276,291,350,371`) are restored to `is`.
  - `append`/`extend`/`extend_children` store *references* (was: deep copies on extraction): mutating a node
    after appending it is visible through the parent — exactly the Python backend's list-of-references
    behavior.
  - Self-extend (`node.extend_children(node)`) duplicates the children entries (snapshot the Vec first when
    `ptr_eq`) — matching the Python backend, where today's Rust backend raises a pyo3 borrow error.
  - Nodes gain `__weakref__` (additive).
- **Reserved label names**: the label validation pass (gsm2tree_rs.py:52–63) gains a table-driven
  reserved-name check rejecting labels whose per-label methods collide with fixed method names. Today that is
  exactly `children` (`extend_<lbl>` with `lbl = "children"` emits a second `fn extend_children` — a latent
  uncompilable-output bug in the *current* generator, `_per_label_methods` line 829 vs
  `_generic_extend_children` line 778). Rejection is a generation-time error naming the label and method.
- Consumers updated in the same change: `native_tests.rs`, `spike_tests.rs`, regenerated outputs, the
  identity tests above. `TODO(rust-cst-child-node-identity)` removed from TODO.md. CHANGELOG entry recording
  the Rust-API break and the Python semantic convergence.

May land as two commits (handle split with `_native` names intact, then the mechanical rename) for
reviewability; one phase either way.

### 4.3 Phase 2 — Idiomatic native surface (R1 "idiomatic and efficient", R4)

Additive to the data struct's plain `impl`; all derivable from `CstGenerator.rule_models`
(`model.labels[label]` per-label type sets — used today by `generate_pyi`). Signatures are designed once,
against `Shared` ownership — the reason this phase follows Phase 1.

1. **`Debug`** on all generated types (node structs, child enums, label enums, `NodeKind`) and a manual
   `Debug` for `Span` in cst-core (`Span { start, end, has_source }`; source text elided — it can be the
   whole input). `Shared<T>`'s `Debug` delegates through `read()`. Closes the gap noted in
   `spike_tests.rs:5-7`.

2. **Per-label native accessors**, mirroring the Python quintet. Read side, with `R` the per-label return
   type — `&Span` for span-typed labels, `&Shared<T>` for single-node-typed labels (caller `.read()`s /
   `.write()`s), `&NodeNameChild` for union-typed labels:

   ```rust
   pub fn children_<lbl>(&self) -> impl Iterator<Item = R> + '_
   pub fn child_<lbl>(&self) -> Result<R, CstError>          // exactly one, else Err
   pub fn maybe_<lbl>(&self) -> Result<Option<R>, CstError>  // zero or one, else Err
   ```

   Count semantics match the Python methods exactly (cross-backend equivalence), defined over **label
   matches, not well-typed matches** — same as the Python quintet (gsm2tree_rs.py:846–907, which never
   inspects variant types). Precisely:

   - `child_<lbl>` / `maybe_<lbl>`: count children whose label matches. Count violation →
     `CstError::ChildCount` with that label-match count (mirroring Python's `"Expected one <lbl> child but
     have N"`), **checked before any type check** — `ChildCount` always wins when both errors apply. Only
     when the count is valid is the surviving child type-checked (single-typed labels only); an off-type
     variant then yields `CstError::UnexpectedChildType`. Python has no counterpart to the type error because
     its accessors return the dynamically-typed child as-is; the divergence exists only on trees already
     malformed via the generic mutators, and only as a typed-return necessity.
   - `children_<lbl>` (single-typed label): **skips** off-type variants stored under the label — documented
     in rustdoc, with `children()` (the untyped slice) named as the lossless view.
   - Union-typed labels: pure label filtering, identical to Python.

   No accessor ever panics on a malformed tree.

   Write side: `append_<lbl>(child: impl Into<Shared<T>>)` (single-node labels; accepts `T` or an existing
   `Shared<T>`), `append_<lbl>(span: Span)` (span-only labels), `append_<lbl>(child: NodeNameChild)`
   (union labels), `extend_<lbl>(...)` analogously.

3. **Generic native accessors/mutators** for parity with the Python surface and parser needs:

   ```rust
   pub fn kind(&self) -> NodeKind
   pub fn set_span(&mut self, span: Span)
   pub fn child(&self) -> Result<&(Option<Label>, Child), CstError>   // exactly-one, like Python `child`
   pub fn extend_children(&mut self, other: &Self)                    // shares children (Arc clones) —
                                                                      // matches Python-backend reference
                                                                      // copy; the future Rust parser's
                                                                      // inline_to_parent path, now cheaper
                                                                      // than the old deep clone
   ```

   `extend_children(&mut self, other: &Self)` cannot alias (`&mut` + `&` of the same node won't borrow-check
   at the data-struct level); the handle pymethod handles the `ptr_eq` self-extend case (§4.2).

4. **`CstError`** — small `#[non_exhaustive]` enum in `fltk-cst-core` (pyo3-free): variants approximately
   `ChildCount { label, expected, found }` and `UnexpectedChildType { label }`. Implements `Display` +
   `Error`. Generated pymethods do *not* route through it (they keep direct `PyErr` construction); keeping
   the layers separate avoids churning Python error messages.

5. **Label enum rename, Rust-side only**: `Identifier_Label` → `IdentifierLabel`
   (`#[pyclass(name = "Identifier_Label")]` preserves the Python class name; `__repr__` strings unchanged).
   Drops `#[allow(non_camel_case_types)]`; consistent with `IdentifierChild`. Python consumers never spell
   this name directly (they use the `node.Label` classattr — exploration.md Open Q2).

6. **Rustdoc** on every generated public item, including the shallow-`Clone` and reference-semantics notes.

### 4.4 Phase 3 — Mixed Rust/Python pattern: document (R3)

What this design commits to, documented in the ADR and the generated-crate workflow README:

- A mixed app builds **one cdylib** containing its generated CST (`python` feature on) and its own Rust code.
  Rust constructs/traverses via the data-struct API; the same trees cross to Python as handle objects
  (`PyIdentifier::to_py_canonical` outbound, `.shared()` inbound), with stable identity and shared mutation
  in both directions. Handle types and `Shared` are the "explicitly-exposed Python machinery" the user
  pre-approved for mixed code; pure-Rust paths never see pyo3.
- Cross-cdylib node passing: **permanently unsupported** (A2) — different grammars produce distinct node
  classes; there is nothing to share. Span/SourceText crossing is supported and hardened (Phase 0).
- Mixed-app lock rule: do not acquire the GIL while holding a `Shared` guard (§4.0 lock discipline).
- Known remaining divergence from the Python backend: the `children` *list object* is a per-call snapshot,
  not a live view (§7 Q4 — recommended default: documented divergence + new narrow TODO slug
  `rust-cst-children-list-view`).

### 4.5 Phase 4 — out of scope, shaped by this design

Generated Rust parsers (R4) target exactly the Phase 1–2 data-struct API: `new`, `push_child`,
`extend_children`, `set_span`, wrapping in `Shared` as nodes are linked. No pyo3 in the parser's hot path; a
single registry-routed `to_py_canonical` wrap at the top when handing the finished tree to Python. No parser
work in this design beyond ensuring these methods exist.

---

## 5. Edge Cases / Failure Modes

- **Out-of-tree consumer already on `_native` names, `Box`-based child matching, or `Identifier_Label`.**
  Breaking; accepted per §1 (window ≈ zero, owner-directed, CHANGELOG'd, this ADR is the record). No
  deprecated aliases for a days-old surface.
- **Python surface drift during the handle split.** Risk: a pymethod misnamed or mis-signatured on the
  handle. Gates: the existing pytest suite (all edits enumerated and strengthening-only — the five `is`
  restorations), plus `.pyi` regen producing an empty diff, plus pyright.
- **Lock recursion / re-entrancy.** std `RwLock` same-thread read-read can deadlock when a writer is queued,
  and write-then-read always deadlocks. Generated method bodies follow the snapshot-then-drop-guard rule
  (§4.0): no Python calls, no nested node access, while holding a guard. Deep `PartialEq` is the one
  generated path that inherently holds guards across recursion and cannot follow that rule; its same-lock
  re-entry cases (`x == x`, shared subtree at the same position on both sides) are eliminated by the
  `ptr_eq` short-circuit in `Shared::eq` (§4.0) — residual same-lock re-entry under `eq` requires a true
  cycle, already documented out of contract. `ptr_eq` self-extend handled explicitly. Mixed-app native code
  can still misuse guards — documented rule, same class of contract as any `RwLock` API.
- **Poisoning.** A panic while a guard is held poisons a std `RwLock`; `Shared` deliberately ignores poison
  (`PoisonError::into_inner`) so one panic cannot brick a tree. Alternative (parking_lot: no poisoning,
  faster) noted; std chosen to keep generated crates dependency-light. Revisit only if Phase 1 benchmarks
  (§6 item 8) demand it.
- **Reference cycles.** Shared ownership makes user-created cycles possible (append an ancestor into a
  descendant): `__eq__`/`PartialEq`/the new `Debug` recurse infinitely, and `Arc` cycles leak. (Rust
  `__repr__` does not recurse — it prints span + child count only, gsm2tree_rs.py:933–943, moved unchanged;
  the *Python backend's* dataclass repr does recurse.) The Python backend has the same eq/repr hazard
  (dataclass recursion); no cycle detection added — documented.
  Shared *acyclic* subtrees (DAGs) are well-defined; deep ops may revisit shared subtrees.
- **Registry correctness.** Invariant argument in §4.0 (single canonical handle; weak-value eviction; no
  ABA). Residual: a handle that dies between reads means a later read mints a *new* handle — `is` holds only
  among temporally-overlapping references, which is also exactly Python-backend behavior (the object you
  compare must still be alive). Test pins this (§6 item 4).
- **pyo3 attribute/internal-type quirks.** The handle split removes the need for unverified
  `#[getter(name)]`/`#[setter(name)]` forms (bare inference forms suffice, proven at gsm2tree_rs.py:647–653).
  Remaining verify-first items: `#[pyclass(frozen, weakref)]` together (expected fine; not yet used in-tree)
  and the Phase 0 layout-probe (`PyClassObject` nameability) — each verified on a spike before the dependent
  phase commits to it; Phase 0 item 1 lands regardless of the probe outcome.
- **Name collisions from labels.** Labels are validated `[_a-z][_a-z0-9]*` (gsm2tree_rs.py:52–63). The single
  fixed-name collision is label `children` → `extend_children` (latent today); handled by the reserved-label
  check (§4.2). No other prefix/fixed-name pair collides, and no keyword can appear as a full method name
  because every generated per-label name is prefixed.
- **Typed accessor vs. runtime variant mismatch** (generic `append`/`push_child` accepts any child-enum
  variant under any label). Resolved by the precedence rules in §4.3 item 2; never a panic.
- **Spike test drift.** `crates/fltk-cst-spike/src/cst.rs` is overwritten by `make gencode` and cannot drift;
  `spike_tests.rs`/`native_tests.rs` are hand-written — compile failure against the regenerated CST is the
  signal, not silent drift. `forbid(unsafe_code)` python-off (spike lib.rs:1) still holds: `Shared` and the
  data-struct API contain no unsafe.
- **ABI gate false confidence.** `FLTK_CST_CORE_ABI` is version-derived and `fltk-cst-core` has never left
  0.1.0 (Cargo.toml:3) — the string gate alone is only as strong as version discipline. That is precisely why
  Phase 0 item 2 (layout/pyo3-version component) is in scope and not deferred again.

---

## 6. Test Plan

After implementation, the following exist (TDD: written first, failing against current generator output):

1. **Rust, python-off** (extends `native_tests.rs`, mirrored in spike tests):
   - Existing native tests rewritten against suffixless names and `Shared`-bearing child enums (compile
     failure of old names/shapes *is* the rename test).
   - Reference semantics: mutate via `child.write()`, observe through the parent; `extend_children` shares
     (`ptr_eq` across both parents); derived `Clone` is shallow (mutation visible through the clone) — pinned
     so the semantics are deliberate, not accidental. `Shared` self-compare (`x == x`) and same-`Shared`-at-
     same-position DAG compare return `true` without deadlock (pins the `ptr_eq` short-circuit, §4.0).
   - Per-label accessors: span label → `&Span`; single-node label → `&Shared<T>`; union label → child enum;
     `child_`/`maybe_` count-error paths; `children_` iterator order = insertion order.
   - `UnexpectedChildType` via generic `push_child` storing an off-type variant under a single-typed label;
     **mixed precedence case**: two children under a single-typed label, one off-type → `child_<lbl>` returns
     `ChildCount { found: 2 }` (not `UnexpectedChildType`); `children_<lbl>` yields exactly the well-typed
     item while `children()` shows both.
   - `Debug` smoke test; `kind()`, `set_span()`, native `extend_children` (label preservation), native
     `child()`.
2. **Rust, both feature states**: `cargo test`/`clippy -D warnings` python-off and python-on (Makefile checks
   lines 52–58 + `check-no-pyo3` stay green — `Shared` is pyo3-free).
3. **Python semantics (R2 + R3)**: existing pytest suite passes with **only** the enumerated identity
   restorations (`tests/test_phase4_rust_fixture.py:242,276,291,350,371` back to `is`); new tests for:
   identity stability across repeated reads; mutation propagation Python→Python, Python→native, and
   native→Python through the same tree; post-append aliasing (mutate after `append`, parent sees it);
   self-extend duplicates children. New cross-backend equivalence tests run the same identity/mutation
   scenarios against both backends (new test module if no shared harness exists).
4. **Wrapper canonicalization**: two reads → `is`; `py_new` → `append` → read-back → `is` the original
   object; after the only handle is dropped and GC'd, a re-read yields a new handle whose mutations still
   propagate (same underlying node); **both-directions bridge**: native `to_py_canonical` on a `Shared`
   that Python has already read through wrap-out → `is` the existing handle, and two `to_py_canonical`
   calls on the same `Shared` → `is` (pins that the mixed-app bridge is registry-routed, §4.0); Python
   `x == x` on a handle returns `True` (no deadlock/hang).
5. **Stub stability**: regenerated `.pyi` diff is empty; `uv run pyright` clean.
6. **cst-core**: sentinel tests. The Span and SourceText gates have different shapes and need different test
   mechanisms:
   - **Span path** (init-time gate, §4.1 item 1): the ABI check runs once, against the canonical
     `fltk._native.Span` type object, in `get_span_type`'s `GILOnceCell` init — a fake span-like *object*
     never reaches it (it fails the ordinary `isinstance`, cross_cdylib.rs:156, with the pre-existing
     generic TypeError), and the `GILOnceCell` is not resettable from Python, so the mismatch path is
     unreachable in the shared pytest process. Test in a **subprocess** (fresh interpreter; the repo already
     batches subprocess tests, cf. commit 3217a14): patch/remove `fltk._native.Span._fltk_cst_core_abi` via
     an import shim *before* the first span boundary crossing, then drive a crossing through the consumer
     cdylib fixture (`rust_cst_fixture`) and assert a `TypeError` naming both ABI strings; control run
     (unpatched subprocess) passes.
   - **SourceText path** (per-object gate, cross_cdylib.rs:59–77): the existing in-process fake-marker test
     shape (absent/mismatched `_fltk_cst_core_abi` on the object's type → `TypeError` naming both strings;
     matching marker passes).
   - Layout-probe classattr present and compared on both paths (if the probe survives verification; same
     subprocess mechanism for the Span side); caching smoke test (`span_to_pyobject` correct across repeated
     calls). `CstError` `Display`; `Span` `Debug` format.
7. **Generator unit test**: reserved label `children` rejected at generation time with an error naming the
   label and the colliding method.
8. **Benchmark sanity** (informational gate, spike crate): build + traverse micro-benchmark before/after the
   `Box`→`Shared` switch; expectation is uncontended-lock overhead within the same order of magnitude. A
   surprising regression reopens the parking_lot question (§5) before Phase 2 builds on the new ownership.

---

## 7. Open Questions

**Q1 — Mixed-app mutation semantics.** *Resolved (USER A1: pull shared identity/mutability into this
design).* Incorporated as Phase 1 (§4.0, §4.2): `Shared<T>` ownership + canonical wrapper registry; snapshot
semantics are gone.

**Q2 — Cross-cdylib node passing.** *Resolved (USER A2: never needed; co-resident grammars don't share node
classes).* Incorporated: node ABI markers permanently out of scope; sentinel work scoped to `Span`/
`SourceText` (Phase 0); recorded in §8.

**Q3 — ADR acceptance / workflow.** *Resolved (USER A3: no restart; revision incorporated).* Updated
recommendation in §2: no requirements-first restart at the larger scope either — A1/A2 answered the gating
questions; remaining unknowns are verify-first implementation items.

**Q4 — `children` list as live view (new).** Python backend: `node.children` is the node's actual list;
in-place list mutation edits the tree. Rust backend (before and after this design): the getter returns a
fresh snapshot list per call (gsm2tree_rs.py:682–700; pinned at `tests/test_rust_cst_poc.py:47`); list
mutation is a silent no-op on the tree. Element identity is fixed by this design; the *list object* is not.
Closing it would need a live sequence-proxy pyclass — additional surface, deferrable, additive later.
**Recommended default**: keep snapshot lists; document the divergence in Phase 3 docs; add narrow
`TODO(rust-cst-children-list-view)`. Confirm or direct inclusion now.

USER A4: Add TODO for the live list view.

---

## 8. Consequences (ADR: Consequences)

- The suffixless data-struct API becomes the stable public Rust surface that generated parsers (Phase 4) and
  out-of-tree Rust consumers build against; the Box→`Shared` ownership break lands inside the same
  zero-adoption window as the rename — the next window will not be this cheap.
- The Rust backend's observable semantics (child identity, mutation propagation, extend/append aliasing,
  self-extend) converge on the Python backend's: cross-backend behavioral equivalence improves, and the five
  relaxed identity tests are restored. Remaining known divergence: children-list live view (§7 Q4).
- `TODO(rust-cst-child-node-identity)` is resolved by Phase 1. `TODO(crosscdylib-abi-sentinel)` is resolved
  by Phase 0 as scoped by A2 (Span/SourceText; cross-cdylib nodes permanently out) — with a possible narrowed
  residual only if the derivation-strengthening probe fails verification.
- Native traversal pays an uncontended `RwLock` read + `Arc` indirection per node-child access (was: `Box`
  deref); Python repeat reads get *cheaper* (registry hit vs clone + `Py::new` per read);
  `extend_children`/parser `inline_to_parent` gets cheaper (refcount bumps vs deep clone). Benchmarked
  (§6 item 8).
- Per-label native accessors return `&Shared<T>` (lock-mediated) rather than the `&T` a `Box` model would
  allow — the deliberate R1 cost of buying R3's shared identity; union labels and spans are unaffected.
- Derived `Clone` on data structs is shallow; trees are reference structures in both backends. User-created
  cycles become possible and are documented, not detected — same contract as the Python backend.
- Anyone who adopted the days-old `*_native`/`Box`-matching/`Identifier_Label` Rust names must update
  (mechanical; CHANGELOG'd). Python consumers see no API change; semantic changes are strictly
  convergence-toward-Python-backend.
- Mixed-language apps get a documented, supported pattern — same-cdylib, shared identity, both directions —
  with cross-cdylib node passing recorded as permanently unsupported rather than ambiguously deferred.
- Span boundary crossings fail loud (`TypeError` with ABI diagnostics) instead of risking UB under version
  skew, and stop re-deriving process-constant lookups per call.
