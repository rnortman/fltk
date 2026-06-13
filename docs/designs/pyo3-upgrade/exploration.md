# pyo3 0.23 → 0.29 Upgrade — Exploration / Failure-Surface Catalog

Scope: SCOUT ONLY. This catalogs the compiler/check failure surface produced by bumping
pyo3 to 0.29.0. No fix design. All file paths absolute-from-repo-root.

## 0. Ground truth corrections to the task brief

- **Newest pyo3 release: `0.29.0`** (crates.io `max_stable_version`/`newest_version`, June 2026).
  `>=0.29` ⇒ exactly `0.29.0` today.
- **There are SEVEN tracked Rust manifests, not six** (the brief's "six" + the previously
  unlisted `crates/fltk-parser-core/Cargo.toml`, which links no pyo3 — structural absence).
  pyo3-bearing manifests (the six the brief names) carry the `version = "0.23"` line:
  - `Cargo.toml` (root → crate `fltk-native`)
  - `crates/fltk-cst-core/Cargo.toml`
  - `crates/fltk-cst-spike/Cargo.toml`
  - `tests/rust_cst_fegen/Cargo.toml`
  - `tests/rust_cst_fixture/Cargo.toml`
  - `tests/rust_parser_fixture/Cargo.toml`
  `crates/fltk-parser-core/Cargo.toml` has NO pyo3 dep (do not add one).
- **Worktree branch note:** the agent worktree was checked out on a stale branch
  (`worktree-agent-...`, HEAD `5d5bf07`) that predates the multi-crate split + `deny.toml`.
  Scout reset the worktree to the repo branch `rust-idiomatic-cst-api` content
  (HEAD `2919733`, the same the user's main checkout is on) via a local `scout-pyo3` branch
  before doing any work. All findings below are against `2919733`.

## 1. Steps performed (the scaffolding bump that reveals the surface)

1. Bumped `pyo3 = { version = "0.23", ... }` → `"0.29"` in all six pyo3-bearing manifests.
   Features (`abi3-py310`, `extension-module`, `optional`, `python` feature) left intact.
2. `cargo update -p pyo3`: resolved `pyo3 0.23.5 → 0.29.0` (+ `pyo3-ffi/-macros/-build-config`
   0.29.0; pulled `target-lexicon 0.13.5`; dropped `indoc`/`memoffset`/`unindent`).
3. Removed the two `[advisories] ignore` entries (`RUSTSEC-2025-0020`, `RUSTSEC-2026-0177`)
   and the `TODO(pyo3-upgrade)` comment from `deny.toml`.
4. Fix-forwarded the hand-written core crate ONLY (mechanical renames + stubs, NOT a real fix)
   to peel back cascades and expose the generated-code layer. See §5.

`make check` runs (Makefile `check` target, in order):
`lint` (ruff) · `format-check` (ruff) · `typecheck` (pyright) · `test` (pytest) ·
`cargo-check` · `cargo-clippy` (`-D warnings`, also fegen+parser_fixture manifests) ·
`cargo-test` · `cargo-test-no-python` · `cargo-clippy-no-python` (`-D warnings`) ·
`check-no-pyo3` · `cargo-deny` (root + 3 tests/* manifests, shared `deny.toml`).
`uv run pytest` requires `maturin develop` to have built `fltk._native` first; the build is
the wall the upgrade currently hits — pytest cannot run until `fltk-native` compiles.

## 2. The pyo3 0.23→0.29 migration steps that apply (from upstream migration guide)

| Step | Headline change (relevant subset) | Hits this codebase as |
|---|---|---|
| 0.23→0.24 | (none relevant) | — |
| 0.24→0.25 | **`PyObject` type alias DEPRECATED** (use `Py<PyAny>`). **`GILOnceCell` → `PyOnceLock`** (free-threaded init). `GILProtected` deprecated. | `PyObject` everywhere; `GILOnceCell` in core. |
| 0.25→0.26 | **`.downcast()`/`.downcast_into()`/`.downcast_unchecked()` + `DowncastError` → `.cast()`/`.cast_into()`/`.cast_unchecked()` + `CastError`**. `PyTypeCheck` now `unsafe trait`. | `downcast*` in core + generated. |
| 0.26→0.27 | `FromPyObject` reworked: gains `'a` lifetime, arg `&Bound`→`Borrowed<'a,'py,PyAny>`; container types need `FromPyObjectOwned`. | low/none direct; watch custom extract impls. |
| 0.27→0.28 | **Automatic `FromPyObject` for `#[pyclass]` + `Clone` DEPRECATED** → opt in `#[pyclass(from_py_object)]` / opt out `skip_from_py_object`. `Py<T>`-from-raw-ptr deprecated. multi-phase pymodule init. | `Span` (`#[pyclass(frozen, eq, hash)]` + `derive(Clone)`) → deprecation warning ⇒ **clippy `-D warnings` failure**. Also every generated `#[pyclass]` that is `Clone` + uses `extract::<Self>()`. |
| 0.28→0.29 | `pyo3_build_config` needs direct pyo3 dep. `PyClassInitializer` tuple init deprecated. Windows `raw-dylib`. Soundness fixes incl. **`PyCFunction::new_closure` Sync bound** (= RUSTSEC-2026-0177). | RUSTSEC fix is what the bump buys; no direct new_closure use found. |

**NOT in the migration guide (internal, the hard one):** pyo3 dropped the monolithic
`pyo3::impl_::pycell::PyClassObject<T>` struct. In 0.29 `impl_::pycell` re-exports only
`PyClassObjectBase`, `PyStaticClassObject`, `PyVariableClassObject`, `PyVariableClassObjectBase`,
`PyClassObjectContents`, `PyClassMutability`, `GetBorrowChecker`. There is **no drop-in
`PyClassObject<T>`** and no documented migration. This is FLTK's cross-cdylib ABI layout probe
(`size_of::<PyClassObject<T>>()`) — see §3.A.

Also confirmed by inspecting the vendored 0.29.0 source:
- `pyo3::sync::GILOnceCell` is now `pub(crate)` (private); public replacement `pyo3::sync::PyOnceLock`
  (`sync.rs:50`, `sync/once_lock.rs`), API-compatible (`new`/`get`/`get_or_init`/`get_or_try_init`).
- `PyObject` is **not exported anywhere** in 0.29 (prelude exports neither `PyObject` nor a type
  alias; no `pub type PyObject`/`pub use ... PyObject` survives). Use `Py<PyAny>`.
- prelude also no longer carries `IntoPy`/`ToPyObject` (gone) — only `IntoPyObject`/`FromPyObject`.

## 3. Failure catalog (grouped by API → migration concern → location class)

Counts below are post-bump, BEFORE any fix (root workspace `cargo check`), except where noted
the count is after core was fix-forwarded to expose the generated layer.

### A. `PyClassObject<T>` removed — ABI layout probe (HARDEST; hand-written core only)
- **API broke:** `use pyo3::impl_::pycell::PyClassObject;` and
  `std::mem::size_of::<PyClassObject<T>>()`.
- **Maps to:** pyo3 internal `impl_::pycell` refactor (no public migration path).
- **Sites (ALL hand-written `crates/fltk-cst-core/`):**
  - `src/span.rs:6` import; `src/span.rs:130` (`size_of::<PyClassObject<SourceText>>()`),
    `src/span.rs:404` (`size_of::<PyClassObject<Span>>()`) — the `_fltk_cst_core_abi_layout`
    `#[classattr]` probes.
  - `src/cross_cdylib.rs:199` (`size_of::<PyClassObject<T>>()` inside `check_abi_pair::<T>`),
    consuming the only use of generic `T` in that fn.
- **Why it's not a rename:** the probe's whole purpose is to detect pyo3 layout skew across
  cdylibs (design §2.1–2.2). There is no single 0.29 type whose `size_of` equals the old
  `{ffi::PyObject, T}` collapsed layout. A real fix must choose a new layout-equivalent
  expression (likely `PyStaticClassObject<...>`/`PyClassObjectContents<T>` composition) or
  redesign the probe. Scout stubbed it to `0usize` to proceed; that made `check_abi_pair`'s
  `<T>` unused ⇒ `error: type parameter T goes unused` — i.e. the stub is not viable, the
  real fix MUST keep T load-bearing. **Generated CST does NOT emit this probe** (0 sites in
  `src/cst_fegen.rs`, fixtures) — it is purely a core-internal concern.

### B. `PyObject` → `Py<PyAny>` (HIGHEST volume; pervasive, generated + hand-written)
- **API broke:** type name `PyObject` (alias removed). `E0425 cannot find type PyObject`.
- **Maps to:** 0.24→0.25 PyObject-alias deprecation/removal.
- **Volume:** core: 10 sites. Full root workspace after core fixed: **317** in `fltk-native`
  (`src/cst_fegen.rs` ~enormous, `src/cst_generated.rs`). Spike `--features python`: 55.
  Each fixture `cst.rs` is in the same family (raw grep `PyObject|GILOnceCell|.downcast`:
  `tests/rust_cst_fixture/src/cst.rs` 130, `tests/rust_cst_fegen/src/cst.rs` 275,
  `tests/rust_parser_fixture/src/cst.rs` 378, `tests/rust_parser_fixture/src/collision_cst.rs`
  105, `src/cst_generated.rs` 58, `crates/fltk-cst-spike/src/cst.rs` 58).
- **Hand-written sites:** `crates/fltk-cst-core/src/{registry.rs,span.rs,cross_cdylib.rs}`
  (`registry.rs` uses `PyObject` heavily as the registry value type;
  `span.rs:40,568,570` SpanKind cache; `cross_cdylib.rs:244,256` method cache + return type).
- **Generator sites (must change emission):** `fltk/fegen/gsm2tree_rs.py` lines
  426,752,1144,1176,1205,1221,1234,1270,1320,1334,1396,1471,1502,1525… (emits
  `PyResult<PyObject>` returns, `Option<PyObject>` params, `let label_obj: PyObject`).
  `fltk/fegen/gsm2parser_rs.py:853,861` (`result: PyObject` field + `clone_ref` getter).

### C. `IntoPyObject`-migration ambiguity: `E0034 multiple applicable items ("multiple `wrap` found")`
- **API broke:** pyo3 `#[pymethods]`/`#[classattr]` macro expansion can't disambiguate its
  `IntoPyObjectConverter<Result<T,E>>` vs `IntoPyObjectConverter<T>` `wrap` impls for methods
  declared `-> PyResult<PyObject>` (and `-> PyResult<Option<PyObject>>`). Surfaces once
  `PyObject` is an unresolved/foreign return type under the new converter machinery.
- **Maps to:** the `IntoPyObject` trait migration (0.24→0.25 made `IntoPyObject` the conversion
  trait; the converter autoref-spec is what now collides).
- **Volume:** **127** in `fltk-native` (all generated, `src/cst_fegen.rs`/`cst_generated.rs`);
  21 in spike `--features python`. Representative sites: `src/cst_fegen.rs:608` (`fn Label`),
  `:702` (`fn child`), `:783` (`remove_at`), `:940` (`child_rule`), `:966` (`maybe_rule`).
  Each is a generated `#[pymethods]` fn returning `PyResult<PyObject>` /
  `PyResult<Option<PyObject>>`. Expect this to move/shrink once B is resolved (the converter
  picks an impl unambiguously when the return type is concretely known), but the generator's
  return-type spelling and the `into_pyobject(py)?.to_owned().unbind()` /
  `.into_any().unbind()` conversion idiom (6+ occurrences in `gsm2tree_rs.py`,
  e.g. lines 428,433,1207,1336,1504,2032) is the migration's center of gravity.

### D. `downcast*` → `cast*`
- **API broke:** `.downcast()`, `.downcast_into()`, `.downcast_unchecked()` (E0599; compiler
  literally suggests `cast`/`cast_into`).
- **Maps to:** 0.25→0.26 downcast→cast rename.
- **Hand-written core:** `cross_cdylib.rs:65` (`obj.downcast::<SourceText>`),
  `:86,:111` (`downcast_unchecked::<SourceText>`), `:330` (`downcast_unchecked::<Span>`),
  `:354,:388` (`s.downcast_into::<PyType>`); `registry.rs:145` (`d.downcast_into::<PyDict>`).
- **Generated:** 17 in `fltk-native`, 3 in spike. Generator emission:
  `gsm2tree_rs.py:1071` (`obj.bind(py).downcast::<{py_handle}>()`), plus the
  `extract_from_pyobject`/cross-cdylib helper templates.
- **Cascade note:** `cast_into::<T>().map_err(|e| e.into())` and `.map(|t| t.bind(py)...)`
  closures lose inference when the `?`/`map_err` arm changes ⇒ feeds class E.

### E. `E0282 type annotations needed` (cascade off C/D, not independent)
- **Maps to:** inference loss in `.map_err(|e| e.into())` / `.map(|t| ...)` / `.map(|obj| ...)`
  closures whose surrounding expression type became unknown once the method/return type broke.
- **Volume:** core 8; full workspace 34 (+6 spike). Sites e.g. `cross_cdylib.rs:354:68,
  388:68, 364:15, 395:15, 330` region; `span.rs:582` (`.map(|obj| obj.clone_ref(py))`).
  These should largely evaporate once B/C/D are done; catalog them as *derived*, fix last.

### F. `GILOnceCell` private → `PyOnceLock`
- **API broke:** `use pyo3::sync::GILOnceCell;` (E0603 struct private); `GILOnceCell<…>` types;
  `GILOnceCell::new()`.
- **Maps to:** 0.24→0.25 `GILOnceCell`→`PyOnceLock`.
- **Hand-written only:** `crates/fltk-cst-core/src/{registry.rs:28,34; span.rs:10,40;
  cross_cdylib.rs:4,35,239,244,303,372}`. Generators do **not** emit `GILOnceCell`
  (only a stale doc-comment mention `gsm2tree_rs.py:424` "GILOnceCell is deferred";
  `fltk/fegen/test_genparser.py:75` comment). API is drop-in (`get`/`get_or_try_init` unchanged).

### G. `FromPyObject` auto-derive deprecation (clippy `-D warnings` BLOCKER, separate from build)
- **API broke (warning, but `-D warnings` ⇒ hard error in `cargo-clippy`):**
  `#[pyclass]` on a `Clone` type now warns
  *"FromPyObject implementation … is changing to an opt-in option. Use
  `#[pyclass(from_py_object)]` … or `#[pyclass(skip_from_py_object)]`."*
- **Maps to:** 0.27→0.28.
- **Confirmed sites:** `crates/fltk-cst-core/src/span.rs:149` (`Span`,
  `#[pyclass(frozen, eq, hash)]` + `#[derive(Clone)]`, and `extract::<Span>()` is used in
  `cross_cdylib.rs:312` so the impl is load-bearing → must opt **in** with
  `#[pyclass(from_py_object)]`, not skip). Every generated CST `#[pyclass]` that derives
  `Clone` is a candidate; `fltk-native` emitted **19** such warnings,
  i.e. ~one per generated node class — the generator (`gsm2tree_rs.py` `#[pyclass(...)]`
  emission) must add the opt-in/opt-out attribute. This step does NOT block `cargo check`,
  but DOES block `make check` via `cargo-clippy` / `cargo-clippy-no-python` (`-D warnings`).

## 4. Layering / who-owns-what (critical for sequencing the real fix)

Three tiers, all with the SAME B/C/D/E surface, but DIFFERENT ownership:

1. **Hand-written core** — `crates/fltk-cst-core/src/{span.rs, registry.rs, cross_cdylib.rs}`
   (+ trivially `py_module.rs`, which already uses fully-qualified `pyo3::…` and `prelude::*`
   and is clean). Carries classes A (PyClassObject probe) and F (GILOnceCell) **exclusively**.
   Must be migrated by hand. **This compiles first and gates everything else** (every other
   crate depends on it: `extract_span`, `get_span_type`, `span_to_pyobject`, `registry`).
2. **Python generators** — `fltk/fegen/gsm2tree_rs.py` (CST) and `fltk/fegen/gsm2parser_rs.py`
   (parser). Emit classes B/C/D/G. The committed generated outputs are regenerated FROM these,
   so the fix belongs in the generator templates, then `make gen-rust-cst`/regen targets +
   `make fix` re-emit. **Public-API caution:** these outputs are downstream public API; the
   migration must preserve generated symbol names, signatures, and the `PyObject`-typed surface
   meaning (callers see `Py<PyAny>` where they saw `PyObject` — these are the same type, so
   annotation churn is internal to generated `.rs`, not downstream Python — but verify the
   `#[pyclass(from_py_object)]` choice doesn't change which Python conversions succeed).
3. **Committed generated / fixture outputs** (regenerated by tier 2, do not hand-edit):
   `src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fegen/src/cst.rs`,
   `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_parser_fixture/src/{cst.rs,collision_cst.rs}`,
   and the generated `parser.rs` files (`tests/rust_cst_fegen/src/parser.rs`,
   `tests/rust_parser_fixture/src/parser.rs`, `collision_parser.rs` — minimal surface, ~2 sites
   each from the `PyApplyResult{result: PyObject}` template).
   **Special case — `crates/fltk-cst-spike/src/cst.rs`**: committed, generator-style POC that is
   maintained in-tree (not regenerated by a make target found here). Same B/C/D/G surface
   (58 raw sites; 85 errors under `--features python`). Likely needs hand-migration in lockstep
   with the generator template, OR confirm whether a regen path exists for it.

## 5. Cascade / fix-forward record (what scout changed to reveal lower layers)

To expose the generated layer behind the core-crate wall, scout applied MECHANICAL,
NON-AUTHORITATIVE edits to the three core files (these are scaffolding, NOT the design):
- `GILOnceCell`→`PyOnceLock` (import + types + `::new()`); `PyObject`→`Py<PyAny>`;
  `downcast`/`downcast_into`/`downcast_unchecked`→`cast`/`cast_into`/`cast_unchecked`.
- Stubbed both `size_of::<PyClassObject<T>>()` probes to `0usize` and dropped the
  `impl_::pycell::PyClassObject` import. **This stub is known-wrong** (it neutralizes the ABI
  skew guard and made `check_abi_pair`'s `<T>` unused → `error: type parameter T goes unused`,
  proving the probe can't just be deleted). It exists only so the dependent crates compile far
  enough to enumerate their errors.
After these edits `fltk-cst-core` compiled (1 deprecation warning = class G); the root
workspace then surfaced the 496-error `fltk-native` layer (classes B/C/D/E + 1 stray F + G×19).
These edits live only in the scout's `scout-pyo3` worktree branch and are NOT authoritative.

**Cascade ordering observed:** A+F+the original broken `GILOnceCell` import in core caused the
spurious cascade where `PyObject` "cannot find type" errors multiplied (the broken `use` line
poisoned name resolution). Fixing imports first collapses a chunk of E0425/E0282 noise. Real
sequence should be: **core (A,F,B,D) → generators (B,C,D,G) → regen committed outputs → spike →
clippy(G) → cargo-deny (already cleared by the bump) → pytest.**

## 6. cargo-deny status

Removing the two ignores is correct and sufficient on the advisory axis: RUSTSEC-2025-0020
(PyString::from_object overflow, fixed 0.24.1) and RUSTSEC-2026-0177 (PyCFunction::new_closure
Sync, fixed 0.29.0) are both resolved by 0.29.0. No `PyCFunction::new_closure` / `PyString::
from_object` call sites found in-tree, so no code change is needed for the advisories themselves —
only the version bump. `cargo-deny` runs against root + the 3 `tests/*` manifests; each has its
own `Cargo.lock` and must resolve pyo3 0.29.0 (run `cargo update -p pyo3` per manifest / let
maturin rebuild). License/bans/sources axes are unaffected by the bump.

## 7. Quick-reference: error totals at the two checkpoints

- Root `cargo check`, core unfixed: **29 errors, all in `crates/fltk-cst-core`**
  (10 PyObject · 8 type-annotation · 3 GILOnceCell-private · 3 downcast_unchecked ·
  2 downcast_into · 1 downcast · 1 PyClassObject import · 1 PyClassObject-type).
- Root `cargo check`, core fix-forwarded: **496 errors in `fltk-native`**
  (317 PyObject · 127 E0034-wrap · 34 type-annotation · 17 downcast · 1 GILOnceCell) **+ 19
  FromPyObject deprecation warnings**. Spike `--features python`: 85 (55+21+6+3).
- python-OFF lanes build clean (`fltk-cst-core --no-default-features`, `fltk-parser-core`):
  the entire surface is `feature = "python"`-gated; `check-no-pyo3` is unaffected.
