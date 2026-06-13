# pyo3 0.23 → 0.29 Upgrade — Fix-Strategy Design

Requirement (verbatim): "upgrade pyo3 and make all existing tests/functionality pass."
Target pyo3 ≥0.29 (= 0.29.0 today); clear RUSTSEC-2025-0020 and RUSTSEC-2026-0177; remove the
`deny.toml` ignore entries; preserve cross-backend Python/Rust behavioral equivalence; no churn
to the generated CST's public symbol/annotation surface.

Inputs: failure catalog at `docs/designs/pyo3-upgrade/exploration.md` (§-references below are to
that file). All paths repo-root-relative.

Style note (applies to this doc): concise, precise, complete, unambiguous; audience is a smart
LLM/human implementer.

## 1. Context and strategy decision

The exploration cataloged the complete post-bump failure surface against pyo3 0.29.0:
29 errors in hand-written `crates/fltk-cst-core`, then 496 errors + 19 deprecation warnings in
`fltk-native` (almost all generated), grouped into classes A–G (exploration §3). The python-off
lanes are untouched (§7).

**Decision — single jump to 0.29, not six intermediate landings.** `TODO.md` (`pyo3-upgrade`
entry) suggested "incrementally version-by-version". The scout's catalog supersedes that advice:
every intermediate version still requires regenerating all committed fixtures (5× regen churn),
the hardest item (class A, `PyClassObject<T>` removal) has no intermediate-version migration
path, and no intermediate state is independently shippable. Instead, the plan sequences edits in
**migration-guide order within a single branch**, with compile checkpoints replacing version
checkpoints. Each fix below is annotated with the upstream migration step it implements
(0.24→0.25 etc.), so the implementer can cross-reference the pyo3 migration guide per category.

**Decision — bump `crates/fltk-cst-core` version 0.1.0 → 0.2.0.** `FLTK_CST_CORE_ABI`
(`cross_cdylib.rs:19`) is `"fltk-cst-core/<CARGO_PKG_VERSION>"`. A consumer cdylib built against
0.1.0/pyo3-0.23 mixed with the upgraded `fltk._native` must be rejected; the layout probe alone
might not fire (old `PyClassObject<T>` and new layout sizes can coincide — size equality is the
probe's documented weakness). Bumping the crate version makes the string marker reject the mix
deterministically with a clean `TypeError`. This is a deliberate, called-out compatibility
decision: out-of-tree consumers must rebuild their extension crates against the new fltk-cst-core
+ pyo3 0.29 (a Rust-build-time event); their **Python**-side annotations, symbols, and call sites
are unchanged.

**Public-API stance** (CLAUDE.md: generated CST is downstream public API):
- Python-visible surface: zero change. Class names, method names, label enums (`ClassName_Label`),
  `NodeKind`, `.pyi` stubs — all unchanged. `make gencode` must produce an empty diff on
  `fltk/_native/fegen_cst.pyi`.
- Generated Rust surface: `PyObject` → `Py<PyAny>` is a spelling change of the same type
  (`PyObject` was a type alias for `Py<PyAny>`); consumers regenerate their `.rs` from their
  grammars when they upgrade fltk, so no manual migration of generated files.
- Behavioral: `#[pyclass(from_py_object)]` (class G) opts into exactly the conversion behavior
  pyo3 ≤0.27 provided implicitly; no Python conversion gains or loses validity.

## 2. Fix design per failure class

Ownership tiers (exploration §4): tier 1 = hand-written crates, fixed by hand; tier 2 = the
Python generators `fltk/fegen/gsm2tree_rs.py` + `gsm2parser_rs.py`, fixed in emission templates;
tier 3 = committed generated outputs, **never hand-edited** — regenerated via
`make gencode` + `make fix`. The spike (`crates/fltk-cst-spike/src/cst.rs`) is tier 3: `gencode`
copies `src/cst_generated.rs` over it (Makefile:202), so it needs no hand migration; its
`lib.rs`/`spike_tests.rs` have no pyo3 surface (verified by grep).

### A. `PyClassObject<T>` removed — ABI layout probe (hand-written core only; no upstream step)

Sites: `crates/fltk-cst-core/src/span.rs:6,130,404`, `cross_cdylib.rs:199`.

**Fix: probe `size_of::<<T as pyo3::impl_::pyclass::PyClassImpl>::Layout>()`.**
Verified against vendored pyo3 0.29.0 source
(`~/.cargo/registry/src/.../pyo3-0.29.0`):
- `PyClassImpl` (`src/impl_/pyclass.rs:183`) has `type Layout: PyClassObjectLayout<Self>` —
  this is the struct pyo3 actually allocates for the class.
- The `#[pyclass]` macro assigns
  `type Layout = <Self::BaseNativeType as PyClassBaseType>::Layout<Self>`
  (`pyo3-macros-backend-0.29.0/src/pyclass.rs:3023`), which for plain (non-extends) classes is
  `PyStaticClassObject<Self>` (`src/pycell/impl_.rs:390`, `#[repr(C)]
  { ob_base, contents: PyClassObjectContents<T> }`).
- `pyo3::PyClass: PyClassImpl`, so `check_abi_pair<T: pyo3::PyClass>` compiles unchanged and `T`
  stays load-bearing (the scout proved a `0usize` stub is rejected by rustc — exploration §3.A).

Why the associated type rather than naming `PyStaticClassObject<T>` directly: it tracks whatever
layout pyo3 instantiates for `T`, so the probe keeps its purpose (detect pyo3-internal layout
skew) without re-encoding pyo3's layout-selection rules. Both probed classes (`SourceText`:
`frozen`; `Span`: `frozen, eq, hash`) are static-layout, non-subclassable, dict/weakref-free, so
semantics match the old probe: a pyo3 bump that changes the allocation layout changes the
integer.

Update the four probe sites, the `check_abi_pair` step-4 expression, and the doc comments in
`span.rs`/`cross_cdylib.rs` that name `PyClassObject<T>` (the "{ffi::PyObject, T} collapsed
layout" accepted-risk paragraphs — reword to reference `PyClassImpl::Layout` /
`PyStaticClassObject`). Continue using `pyo3::impl_::` paths; instability of that namespace is
already an accepted, documented property of the probe.

Guard test (new, tier-1 Rust unit test in fltk-cst-core, `python` feature): assert the probe
value for `Span` and `SourceText` is `>= size_of::<pyo3::ffi::PyObject>() + size_of::<T>()`.
This makes the scout's known-wrong `0usize` stub (and any future "just return a constant"
shortcut) a test failure, not merely a code-review catch.

### B. `PyObject` → `Py<PyAny>` (0.24→0.25 deprecation; removed by 0.29; all tiers)

Pure spelling change of one type alias. Mechanical token replacement `PyObject` → `Py<PyAny>`:
- Tier 1: `crates/fltk-cst-core/src/{registry.rs,span.rs,cross_cdylib.rs}` (registry value type,
  `SPAN_KIND_SPAN_CACHE`, `WITH_SOURCE_UNCHECKED_METHOD`, fn signatures incl. public
  `span_to_pyobject`, `registry::lookup`, `registry::get_or_insert_with`'s closure type);
  `src/lib.rs` (`UNKNOWN_SPAN` cache).
- Tier 2: `gsm2tree_rs.py` emission strings (`PyResult<PyObject>` returns, `Option<PyObject>`
  label params, `let label_obj: PyObject`, `to_pyobject` signature, `_eq_method`,
  `_label_classattr`, `_generic_*`, `_per_label_methods` — exploration §3.B lists line anchors);
  `gsm2parser_rs.py:853,861` (`PyApplyResult.result` field + getter).
- Tier 3: regenerated.

`registry`/`span_to_pyobject` signatures are fltk-cst-core public Rust API consumed by generated
code; since the type is identical, previously-generated consumer `.rs` that still spells
`PyObject` only breaks when the consumer themselves moves to pyo3 0.29 — that is pyo3's
documented break, not ours, and regeneration fixes it.

### C. `E0034 multiple applicable items ("multiple wrap found")` (IntoPyObject converter; derived from B)

127 sites, all generated, all `#[pymethods]` fns returning `PyResult<PyObject>` /
`PyResult<Option<PyObject>>`. Diagnosis (exploration §3.C): the macro's
`IntoPyObjectConverter` autoref specialization cannot disambiguate when the return type contains
an **unresolved** name. Once B lands (return types concretely `Py<PyAny>`), `Py<PyAny>` and
`Option<Py<PyAny>>` both have unambiguous `IntoPyObject` impls in 0.29 and the converter resolves.

**Plan: no independent fix. Verify class C count drops to 0 after B.** Fallback if residuals
remain on a specific signature shape: change that emission to return the bare type instead of
`PyResult<...>` where infallible (e.g. `_label_classattr` could return `Py<PyAny>` directly) —
Python surface unchanged. Do not restructure conversion idioms preemptively: the existing emitted
idioms (`into_pyobject(py)?.to_owned().unbind().into_any()` for `bool`,
`.into_pyobject(py)?.into_any().unbind()` for pyclass enums) remain valid under 0.29's
`IntoPyObject`.

### D. `downcast*` → `cast*` (0.25→0.26 rename; tiers 1 + 2)

Mechanical: `.downcast::<T>()` → `.cast::<T>()`, `.downcast_into::<T>()` → `.cast_into::<T>()`,
`.downcast_unchecked::<T>()` → `.cast_unchecked::<T>()` (same `unsafe` contract; SAFETY comments
stay valid — update their wording from "downcast_unchecked" to "cast_unchecked").
- Tier 1: `cross_cdylib.rs:65,86,111,330,354,388`, `registry.rs:145` (snapshot).
- Tier 2: `gsm2tree_rs.py` `to_py_canonical` emission (~line 1071) and any other emitted
  `downcast` (grep the generator for `downcast` after editing; also `registry.rs` snapshot is
  tier 1, generated `_registry_snapshot` merely calls it).
- Error types: `DowncastError`/`DowncastIntoError` → `CastError`/`CastIntoError`; existing
  `.map_err(|e| e.into())` sites keep compiling (both implement `Into<PyErr>`), modulo class-E
  inference fallout.

### E. `E0282 type annotations needed` (cascade; fix last, by hand, tier 1 only)

34 workspace sites, derived from B/C/D inference loss in `.map_err(|e| e.into())` /
`.map(|t| ...)` closures. Expected to largely evaporate once B–D land. Residuals: annotate the
closure parameter or use turbofish at the smallest scope (e.g.
`.map_err(PyErr::from)` instead of `|e| e.into()` where that restores inference). Residuals in
**generated** files indicate a generator-template bug — fix the template, regenerate; never
hand-patch tier 3.

### F. `GILOnceCell` → `PyOnceLock` (0.24→0.25; hand-written only)

Drop-in (same `new`/`get`/`get_or_init`/`get_or_try_init` shapes, confirmed against vendored
0.29 `src/sync.rs`). Sites: `crates/fltk-cst-core/src/{registry.rs:28,34; span.rs:10,40;
cross_cdylib.rs:4,35,239,244,303,372}` and `src/lib.rs:3,17` (`UNKNOWN_SPAN`). Generators emit
none; update the two stale doc-comment mentions (`gsm2tree_rs.py:424` docstring,
`fltk/fegen/test_genparser.py:75`) opportunistically.

### G. `FromPyObject` auto-derive deprecation → `#[pyclass(from_py_object)]` (0.27→0.28; clippy `-D warnings` blocker)

Every `Clone` `#[pyclass]` whose `extract::<Self>()` is load-bearing opts **in**:
- Tier 1: `Span` (`span.rs:149`) → `#[cfg_attr(feature = "python", pyclass(frozen, eq, hash,
  from_py_object))]`. Load-bearing: `extract::<Span>()` at `cross_cdylib.rs:312`.
- Tier 2 (`gsm2tree_rs.py`): the `NodeKind` pyclass attr (`_node_kind_block`) and the label-enum
  pyclass attr (`_label_enum_block`) gain `from_py_object`. Load-bearing extracts:
  `extract::<{type_name}>()` in `_emit_rust_cross_backend_eq_hash` (NodeKind + label enums) and
  `extract::<{rust_enum_name}>()` in `_label_from_pyobject_match`. This accounts for the 19
  warnings in `fltk-native`: 2 NodeKinds + 17 label enums across the two compiled grammars —
  `src/cst_fegen.rs` (1 NodeKind + 14 label enums) and `src/cst_generated.rs` (PoC grammar,
  1 NodeKind + 3 label enums). Step-5 verification target: warnings clear in BOTH files, not
  just `cst_fegen.rs`.
- NOT affected: node handle pyclasses (`Py{CN}` — not `Clone`; extracted via `PyRef`, which
  needs no `FromPyObject` opt-in), `SourceText` (not `Clone`), `PyParser`/`PyApplyResult`
  (not `Clone`).
- `skip_from_py_object` is used nowhere: every affected class's extract path is load-bearing,
  and opting in preserves 0.23-observable behavior exactly (no Python-conversion semantics
  change — addresses the exploration's §4 caution).
- `from_py_object` on unit enums is supported: the option is parsed by the shared
  `PyClassPyO3Option` set and the opt-in `FromPyObject` impl is emitted by the
  `PyClassImplsBuilder` path common to struct and `impl_simple_enum` codegen (verified in
  vendored `pyo3-macros-backend-0.29.0/src/pyclass.rs`).

### Non-events (verified absent, no work)

- `PyCFunction::new_closure`, `PyString::from_object`, `Py::from_borrowed_ptr`-style raw-ptr
  constructors, custom `FromPyObject` impls, `IntoPy`/`ToPyObject` trait usage,
  `PyClassInitializer` tuple init: zero in-tree call sites (grep over `src/`, `crates/`,
  `tests/*/src/`, generators).
- `pyo3_build_config` direct-dep requirement (0.28→0.29): no `build.rs` exists in any manifest.
- 0.26→0.27 `FromPyObject` lifetime rework: no custom impls; `extract::<&str>()` (borrowing
  extract, abi3-py310) remains supported.
- `crates/fltk-parser-core`: no pyo3 dep — do not add one (exploration §0).
- 0.27→0.28 multi-phase `#[pymodule]` init: no code change, but watch the
  `py_module.rs` submodule/`sys.modules` registration heuristics during pytest (see §4 risks).

## 3. Ordered execution plan

Each step ends at a named checkpoint; do not proceed past a red checkpoint. Order follows the
cascade record (exploration §5): broken imports poison name resolution, so imports/types first.

1. **Scaffolding bump.** Set `pyo3 = { version = "0.29", ... }` in the six pyo3-bearing
   manifests (root `Cargo.toml`, `crates/fltk-cst-core`, `crates/fltk-cst-spike`,
   `tests/rust_cst_fegen`, `tests/rust_cst_fixture`, `tests/rust_parser_fixture`), features
   untouched. `cargo update -p pyo3` in each of the four lockfile-bearing workspaces (root +
   3 `tests/*`). Remove the two `[advisories] ignore` entries and the `TODO(pyo3-upgrade)`
   comment from `deny.toml`. Bump `crates/fltk-cst-core` version to `0.2.0`.
   *Checkpoint: `make cargo-deny` green (advisory axis clear); `cargo check` red as cataloged.*
2. **Hand-written core, tier 1** (`crates/fltk-cst-core`), in this order: F (imports +
   `PyOnceLock` types) → B (`Py<PyAny>`) → D (`cast*`) → A (layout probe; write the §2.A guard
   test alongside the fix — its red state is the post-bump build failure itself, since the test
   references 0.29 layout types) → G (`Span` `from_py_object`) → E residuals. Update affected doc
   comments (probe paragraphs; the `py_type_obj_name` note pinned to "pyo3 0.23.5"
   prefix-stripping behavior — re-verify against 0.29 via the existing error-message gate tests
   and reword).
   *Checkpoint: `cargo check -p fltk-cst-core` (both feature lanes) and
   `cargo clippy -p fltk-cst-core --all-features -- -D warnings` green;
   `cargo test -p fltk-cst-core` green.*
3. **Hand-written `fltk-native`**: `src/lib.rs` (F + B for `UNKNOWN_SPAN`). `src/span.rs` has no
   affected surface (verified by grep).
   *Checkpoint: `cargo check` errors now exclusively in tier-3 generated files.*
4. **Generators, tier 2**: `gsm2tree_rs.py` (B, D, G per §2; stale GILOnceCell docstring) and
   `gsm2parser_rs.py` (B). Update generator unit-test expectations (`tests/test_gsm2tree_rs.py`
   and friends) that assert emitted snippets containing `PyObject`/`downcast`/pyclass-attr
   strings — TDD: flip these expectations first, watch them fail, then edit the generators.
5. **Regenerate tier 3**: `make gencode` (covers `src/cst_fegen.rs`, `src/cst_generated.rs`, all
   `tests/*` fixture `cst.rs`/`parser.rs`/`collision_*.rs`, spike `cst.rs` via `cp`) then
   `make fix`. Inspect `git diff`: only mechanical B/D/G churn in `.rs`; **zero diff** in
   `fltk/_native/fegen_cst.pyi` and all generated `.py` (public-surface guard).
   *Checkpoint: `cargo check` green workspace-wide; class C count is 0 (else apply §2.C
   fallback in the generator and re-run from step 4).*
6. **Clippy + remaining lanes**: `make cargo-clippy`, `cargo-clippy-no-python`,
   `cargo-test`, `cargo-test-no-python`, `check-no-pyo3` (python-off lanes were never broken;
   this confirms no regression).
7. **Python integration**: `uv run --group dev maturin develop`, then the three fixture
   extension builds (`make build-test-user-ext build-fegen-rust-cst build-rust-parser-fixture`),
   then `uv run pytest`. Cross-backend equivalence = the existing parity suites
   (`tests/test_cst_mutators_parity.py`, `tests/test_rust_parser_parity_*.py`,
   `tests/test_cross_backend_label_equality.py`, `tests/test_phase4_*.py`,
   `tests/test_rust_span.py` gate tests) — these ARE the acceptance tests; no new parity tests
   are needed because no behavior is intended to change.
8. **Bookkeeping**: remove the `pyo3-upgrade` entry from `TODO.md`; grep for any remaining
   `TODO(pyo3-upgrade)` markers (the deny.toml one went in step 1). Update
   `docs/rust-cst-extension-guide.md` — the out-of-tree consumer build recipe — whose Cargo.toml
   template pins both versions this upgrade changes: `fltk-cst-core = { version = "0.1", ... }`
   (line 59) → `"0.2"` and `pyo3 = { version = "0.23", ... }` (line 63) → `"0.29"`; add a note
   that existing consumer extension crates must be rebuilt against fltk-cst-core 0.2 + pyo3 0.29
   (the §1 ABI marker deterministically rejects old builds with a `TypeError`). Full
   `make check` green is the done condition.

Whack-a-mole expectation: steps 2–5 will surface stragglers not in the catalog (the catalog was
taken behind a wall of earlier errors). Triage rule: hand-written file → fix in place;
generated file → fix the generator and re-run step 5. Never hand-edit tier 3.

## 4. Edge cases / failure modes

- **Class C survives B.** Most likely shape: `PyResult<Option<Py<PyAny>>>` in `maybe_<label>`.
  Mitigation in §2.C (concretize or de-`PyResult` the specific emission). Detect at step-5
  checkpoint.
- **Layout-probe value collision across pyo3 versions.** Old 0.23 builds report
  `size_of::<PyClassObject<T>>`; new builds report `size_of::<PyClassImpl::Layout>`. If equal,
  the layout check alone passes under mixed-version skew — covered by the fltk-cst-core 0.2.0
  string-marker bump (§1), which fires first (check_abi_pair step 3 precedes step 7).
- **`cast_into` error-type inference breaks `?`/`map_err` chains** (class E). Localized
  annotations; the two `downcast_into::<PyType>().map_err(|e| e.into())` sites in
  `cross_cdylib.rs` are the known candidates.
- **Error-message drift.** `fully_qualified_name()` prefix-stripping (documented against pyo3
  0.23.5 at `cross_cdylib.rs:133`) may differ in 0.29; the subprocess gate tests in
  `tests/test_rust_span.py` pin message content and will catch it. If drifted, prefer updating
  the comment + test expectations to match 0.29 output (message text is diagnostics, not API) —
  unless the drift breaks the escaping guarantees (bidi/control-char escaping must be preserved;
  re-check `escape_control_chars` call sites still receive the raw name).
- **Multi-phase pymodule init (0.28) interacting with `py_module.rs` submodule registration**
  (`sys.modules` insertion heuristic, maturin double-nesting). No code change planned; failure
  would appear as import-time test failures in step 7. If it appears: consult the 0.27→0.28
  migration guide section on multi-phase init before touching the heuristic.
- **Fixture lockfiles drift**: each `tests/*` workspace has its own `Cargo.lock`; forgetting one
  leaves cargo-deny red or builds a stale pyo3. Step 1 updates all four explicitly; `make
  cargo-deny` checks all four.
- **Stub regression on the ABI probe**: prevented by the new §2.A guard test.

## 5. Test plan

After implementation the following exist/pass:

- **New**: fltk-cst-core Rust unit test (python feature) asserting, for `Span` and `SourceText`,
  probe value `>= size_of::<ffi::PyObject>() + size_of::<T>()` and equal to the value the
  `_fltk_cst_core_abi_layout` classattr exposes (guards probe realism; kills constant-stub
  shortcuts).
- **Updated**: generator unit tests (`tests/test_gsm2tree_rs.py`, parser-generator tests) whose
  expected emitted snippets mention `PyObject`/`downcast`/pyclass attributes — updated
  red-first (step 4).
- **Updated only if drifted**: `tests/test_rust_span.py` gate-test message expectations (§4).
- **Unchanged, must pass**: entire existing pytest suite including cross-backend parity and
  cross-cdylib gate tests; all `make check` steps (lint, format-check, typecheck, test,
  cargo-check, cargo-clippy ×2, cargo-test ×2, check-no-pyo3, cargo-deny with zero advisory
  ignores).
- **Meta-check**: `make gencode && git diff --stat` after the branch is complete shows no drift
  (committed generated code matches generator output); `fegen_cst.pyi` and generated `.py`
  byte-identical to pre-upgrade.

## 6. Open questions

None requiring user judgment. Two deliberate decisions are called out for visibility rather than
asked as questions, since the evidence is one-sided: (a) single-jump-to-0.29 supersedes the
TODO.md "version-by-version" guidance (§1); (b) fltk-cst-core 0.1.0 → 0.2.0 version bump as the
deterministic cross-cdylib skew guard (§1).
