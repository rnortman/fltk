# Design: `fltk._native` as runtime-only — relocate fegen CST/parser, drop the PoC

Status: Draft
Date: 2026-06-14
Spec: `request.md` (verbatim user request; substitutes for a requirements doc)
Explorations: `exploration.md` (current Rust structure), `exploration-python-backend.md` (the Python runtime-vs-codegen split this must mirror)

## 1. Root cause / context

The governing principle (request.md:8-13): `fltk._native` is the **runtime for all
fltk-generated parsers** and must contain **nothing grammar-specific** — no parsers,
no CST. The Python backend already obeys this: the runtime is the hand-written,
grammar-agnostic package `fltk/fegen/pyrt/` (span types, packrat, errors —
`exploration-python-backend.md:19-54`), and FLTK's *own* fegen grammar is 100%
codegenned into **separate** modules outside that package: `fltk/fegen/fltk_cst.py`,
`fltk_cst_protocol.py`, `fltk_parser.py`, `fltk_trivia_parser.py`
(`exploration-python-backend.md:59-79`). Direction is strictly generated → runtime;
the runtime never imports a `*_cst`/`*_parser` module
(`exploration-python-backend.md:93-119`).

The Rust `_native` cdylib violates this. Its generated `src/lib.rs` (lib.rs:1-28)
registers **two grammar-specific CST submodules** into the production runtime cdylib:

- `poc_cst` ← `src/cst_generated.rs` — a 3-rule throwaway toy grammar
  (`exploration.md:16-17,23-52`). Its only consumers are FLTK's own tests
  (`tests/test_rust_cst_poc.py:8`, `tests/test_module_split.py:46-50,239-291`).
- `fegen_cst` ← `src/cst_fegen.rs` — FLTK's real fegen grammar CST, 28 node structs
  (`exploration.md:18-19`).

Both are declared as data in `native_spec()` (gsm2lib_rs.py:174-182) and rendered by
`RustLibGenerator.generate()` into the `#[pymodule]` body (gsm2lib_rs.py:150-151).
This is the Python equivalent of compiling `fltk_cst.py` *into* `pyrt/` — exactly the
coupling the principle forbids.

The genuinely-runtime parts of `_native` are correctly placed and stay: the canonical
`Span`/`SourceText`/`UnknownSpan` registration plus the `UNKNOWN_SPAN` `PyOnceLock`
static (lib.rs:9-23; types defined in `crates/fltk-cst-core`, re-exported via
`src/span.rs:1-2`). The Python model agrees: the runtime backend (`pyrt/span.py`) is
exactly the place that owns the canonical span types
(`exploration-python-backend.md:194-201`). No parser is compiled into `_native` today
(root `Cargo.toml:14-16` lacks `fltk-parser-core`), which is already model-consistent
(`exploration.md:106-126`).

### A decisive, already-existing fact

The correctly-shaped fegen Rust artifact **already exists** and is the model target:
`tests/rust_cst_fegen/` is a standalone maturin extension `fegen_rust_cst` whose
`#[pymodule]` registers `cst` (from `src/cst.rs`) and `parser` (from `src/parser.rs`)
submodules (`tests/rust_cst_fegen/src/lib.rs:14-24`), built via the standard path
(`Makefile:198-199`), depending on `fltk-cst-core` + `fltk-parser-core` and pulling
`Span`/`SourceText` from `fltk._native` at runtime
(`tests/rust_cst_fegen/src/lib.rs:6-8`). Crucially, `tests/rust_cst_fegen/src/cst.rs`
is regenerated from `fegen.fltkg` and is required to **match** `src/cst_fegen.rs`
byte-for-byte (Makefile:265-267). So `src/cst_fegen.rs` inside `_native` is a redundant
duplicate of an artifact that *already lives in the right shape elsewhere*. The refactor
is therefore mostly deletion + rewiring, not new construction.

### Blast radius is tiny — there are no external consumers

The only out-of-tree consumer is the unpushed clockwork spike (request.md:16-19). It
depends on `_native` for exactly one thing: `fltk._native.Span` resolving to the Rust
type (`clockwork/dsl/clockwork_rust_roundtrip_test.py:26-43`). It never references
`fegen_cst` or `poc_cst` (confirmed: the only `_native` references in clockwork are
`Span`). Removing the CST submodules from `_native` does not touch clockwork.

## 2. Proposed approach

Make `_native` runtime-only. Relocate the fegen CST+parser into a first-class,
permanently-committed standalone extension that mirrors `fltk/fegen/fltk_*`. Delete the
PoC-in-production wiring. Collapse the bespoke `native_spec()`/`gen-rust-native-lib`
path now that `_native` no longer carries grammar content.

The three decisions that shape the layout are settled (recorded here, not left open):
the relocated fegen crate **keeps** its importable name `fegen_rust_cst`; it **moves out
of `tests/` into a first-class `crates/fegen-rust/` crate**; and its generated `.pyi`
is routed to a stub package inside the `fltk` tree (`fltk/_stubs/fegen_rust_cst/cst.pyi`)
with a matching `[tool.pyright]` entry.

### 2.1 `fltk._native` after the refactor

`src/` contains only runtime wiring:

- `src/lib.rs` — `#[pymodule] fn _native` that registers **only** `Span`,
  `SourceText`, `UnknownSpan`, and sets the `UNKNOWN_SPAN` static. No `mod cst_*`, no
  `register_submodule` calls.
- `src/span.rs` — unchanged 2-line re-export of `fltk_cst_core::{SourceText, Span}`
  (span.rs:1-2).
- **Deleted:** `src/cst_generated.rs`, `src/cst_fegen.rs`.

Exported Python surface of `fltk._native`: `Span`, `SourceText`, `UnknownSpan` at top
level. No submodules. This is the exact runtime surface the clockwork roundtrip test and
`pyrt/span.py`'s backend selector require.

The hand-maintained stub `fltk/_native/__init__.pyi` stays (it already documents only
`SourceText`/`Span`/`UnknownSpan` — __init__.pyi:21-68). Its `poc_cst` comment block
(__init__.pyi:9-14) is **deleted because it becomes factually false**, not as cosmetic
header trimming: that block asserts the PoC classes live at `fltk._native.poc_cst`
(`src/lib.rs; cst_generated::register_classes`), and after §2.3 `poc_cst` is no longer a
submodule of `_native` at all. Leaving the comment would actively mislead. **`fltk/_native/fegen_cst.pyi`
is deleted** and its replacement moves with the relocated CST (§2.2).

### 2.2 Where the fegen CST + parser go

FLTK's own fegen grammar is codegenned into a **permanent, committed standalone Rust
extension** — the Rust analog of `fltk/fegen/fltk_cst.py` + `fltk_parser.py`. We
promote the existing `tests/rust_cst_fegen/` crate out of `tests/` into a first-class
location (`crates/fegen-rust/`) and treat it as FLTK's dogfooding fegen-in-Rust
extension.

Concretely:

- **Location:** move `tests/rust_cst_fegen/` → `crates/fegen-rust/` (a committed,
  non-test crate). Rationale: it is no longer "just a test fixture" — it is the
  canonical relocation target for the fegen CST/parser, the Rust peer of the committed
  Python `fltk/fegen/fltk_cst.py`/`fltk_parser.py`. Keeping it under `crates/` (a
  standalone-workspace crate, `tests/rust_cst_fegen/Cargo.toml:1-3`) signals "FLTK's own
  generated Rust grammar artifact," not "ad-hoc test scaffolding."
- **Shape:** unchanged from today — `#[pymodule] fn fegen_rust_cst` with `cst` and
  `parser` submodules (`tests/rust_cst_fegen/src/lib.rs:14-24`); `cst.rs` and
  `parser.rs` both codegenned; `native_parser_tests.rs` retained as the crate's native
  test module.
- **Module name:** keep `fegen_rust_cst` (the importable name asserted across
  `tests/test_module_split.py:31-44`). Renaming it is gratuitous churn with no benefit;
  the principle constrains *where grammar code lives*, not its module name. Backward-compat
  is waived, but the name is deliberately retained — no rename in this refactor.
- **`.pyi` stub:** the fegen `.pyi` previously emitted to `fltk/_native/fegen_cst.pyi`
  (Makefile:259-262) must land somewhere pyright actually resolves, or it becomes dead and
  the protocol-conformance check it exists to perform is silently lost. pyright is configured
  `include = ["fltk", "*.py"]`, `stubPath = ""` (pyproject.toml:50,52), so it only checks
  stubs under the `fltk` package tree; a stub under `crates/fegen-rust/` is outside that tree
  and never resolved. The `gen-rust-cst --pyi-output` flag accepts an arbitrary path
  (genparser.py:281-296), but *resolution* is governed by pyright config, not the emit path.
  The stub is therefore emitted as a `fegen_rust_cst/cst.pyi` stub package **inside the
  `fltk` tree** at `fltk/_stubs/fegen_rust_cst/cst.pyi`, named to match the importable module
  `fegen_rust_cst.cst`, with the matching `stubPath`/`extraPaths` entry added to
  `[tool.pyright]` in `pyproject.toml`. That `pyproject.toml` edit is part of this design's
  acceptance, because without it the stub is dead and the `fltk.fegen.fltk_cst_protocol`
  conformance check no longer runs.

This makes the duplicate `src/cst_fegen.rs` (and the "must match
`tests/rust_cst_fegen/src/cst.rs`" coupling, Makefile:265-267) disappear: there is now
exactly one generated fegen CST, in one place.

### 2.3 What happens to `poc_cst` (test-fixture relocation)

`poc_cst` is pure test material (`exploration.md:23-52`) with no Python-model analog
(`exploration-python-backend.md:186-192`). It must leave `_native`. Two facts decide its
fate:

1. The PoC grammar (`fltk/fegen/test_data/poc_grammar.fltkg`) and the toy CST it
   generates are *the same grammar* already compiled, python-off, as
   `crates/fltk-cst-spike/src/cst.rs` via a `cp` from `src/cst_generated.rs`
   (Makefile:279-280).
2. The Python-visible PoC classes (`Identifier`, `Items`, `Trivia`) are consumed only by
   `tests/test_rust_cst_poc.py` and `tests/test_module_split.py`.

Decision: **relocate `poc_cst` into a dedicated test-fixture extension crate, not into
`_native` and not into the fegen crate.** Create `tests/rust_poc_cst/` — a standalone
maturin extension `poc_cst` (top-level module, no longer a submodule of `_native`) whose
`#[pymodule] fn poc_cst` wires the generated classes exactly as every existing fixture
does: `register_submodule(m, "cst", cst::register_classes)`
(matching `tests/rust_cst_fegen/src/lib.rs:21` and `tests/rust_cst_fixture/src/lib.rs:22`;
`register_classes` registers into the module it is handed — `src/cst_generated.rs:3177`).
The Python imports therefore become `from poc_cst.cst import Identifier, Items` etc. — a
`cst` submodule under the top-level `poc_cst` module. We deliberately do **not** register
the classes at top level: that would be a one-off wiring no other crate uses, contradicting
the "one grammar per extension, uniform shape" invariant this refactor establishes.

Rationale for a separate fixture crate rather than folding the PoC into the fegen crate:
the PoC's entire purpose is to be a *minimal, independent* CST exercise (label
semantics, span behavior — `tests/test_rust_cst_poc.py`), deliberately distinct from the
real fegen grammar. Co-locating it in the fegen crate would re-introduce two grammars in
one module — the same smell, smaller. A standalone fixture keeps the "one grammar per
extension" invariant the refactor is establishing, and gives the PoC tests a clean
top-level extension (`poc_cst`) with the uniform `.cst` submodule shape.

The `crates/fltk-cst-spike/` crate is unaffected in purpose (it exercises the python-off
lane — Makefile:134-147,279-280). Its `cp src/cst_generated.rs
crates/fltk-cst-spike/src/cst.rs` step (Makefile:280) is re-pointed to copy from the new
PoC fixture's generated `cst.rs`; the `cp` is **kept** as the byte-identity guarantee — see
§2.5.

### 2.4 `gsm2lib_rs.py` / `native_spec()` / CLI changes

`native_spec()` exists solely to encode the two-CST-plus-span `_native` layout
(gsm2lib_rs.py:167-182). Once `_native` is runtime-only, that layout is **no submodules
+ span types + UNKNOWN_SPAN static** — which the generic `LibSpec` already expresses via
its existing `register_span_types`/`unknown_span_static` flags
(gsm2lib_rs.py:56-60,106-145). So:

- **Delete `native_spec()`** (gsm2lib_rs.py:167-182) and the
  `gen-rust-native-lib` CLI command (genparser.py:446-473). The `_native` lib.rs is now
  produced by the generic `gen-rust-lib` path with a span-only spec.
- **Generalize `gen-rust-lib`** to express the runtime-only `_native` shape. Today
  `gen-rust-lib` only offers `--module-name` + `--no-parser` and always emits a `cst`
  submodule via `LibSpec.standard()` (genparser.py:400-443, gsm2lib_rs.py:62-74). Add
  flags so a caller can request span registration and the UNKNOWN_SPAN static, and can
  request **zero** submodules:
  - `--register-span-types` → `LibSpec.register_span_types=True`
  - `--unknown-span-static` → `LibSpec.unknown_span_static=True`
  - `--no-cst` (or a `--submodules` selection) → omit the default `cst` submodule
  `_native`'s lib.rs is then generated by
  `gen-rust-lib src/lib.rs --module-name _native --register-span-types
  --unknown-span-static --no-cst --no-parser`.
- **`LibSpec.validate()`** already permits zero submodules when span types or the
  UNKNOWN_SPAN static are registered (gsm2lib_rs.py:81-83) — so a submodule-less,
  span-only `_native` spec is already legal; no validation change needed.
- **`LibSpec.standard()`** is unchanged: downstream consumers (clockwork) keep getting
  `cst`+`parser` (gsm2lib_rs.py:62-74). The standard path never referenced
  `native_spec()` (`exploration.md:128-143`).
- The `RustLibGenerator.generate()` engine is unchanged — it is already fully
  data-driven (`exploration.md:128-138`); only the spec fed to it changes.

Tests that pin the old shape are updated: `fltk/fegen/test_gsm2lib_rs.py` (not
`tests/test_gsm2lib_rs.py` — the file lives in the `fltk/fegen/` package). Deleting
`native_spec()` is a **hard dependency** for that file's top-level import
(`fltk/fegen/test_gsm2lib_rs.py:7` does `from fltk.fegen.gsm2lib_rs import LibSpec,
RustLibGenerator, Submodule, native_spec`) — `native_spec` must be dropped from that import
or the whole module fails to collect under pytest. The `test_native_spec_*` block is the
range ~129-246 (eight functions: `…_contains_span_module`, `…_contains_py_once_lock`,
`…_registers_span_classes`, `…_adds_unknown_span_attribute`, `…_unknown_span_static`,
`…_unknown_span_once_init_message`, `…_poc_cst_registration`, `…_fegen_cst_registration`,
`…_fn_name`, `…_declaration_and_registration_order`, `…_output_ends_with_newline`), all of
which are deleted; the file gains assertions for the new span-only `gen-rust-lib` flags.

### 2.5 Standard-consumer codegen path

Unaffected in substance. `gen-rust-cst`, `gen-rust-parser`, and the `LibSpec.standard()`
branch of `gen-rust-lib` are how downstream consumers (and the relocated fegen/PoC
crates) generate their artifacts (genparser.py:265-443). The relocated fegen crate
regenerates via the *standard* commands rather than the deleted native command.

`Makefile` `gencode` rewiring (Makefile:235-289):

- **Delete** the `gen-rust-native-lib src/lib.rs` line (Makefile:253-254); replace with
  the generalized `gen-rust-lib ... --register-span-types --unknown-span-static --no-cst
  --no-parser` invocation from §2.4.
- **Delete** the `gen-rust-cst ... src/cst_generated.rs` line (Makefile:255-257) and the
  `gen-rust-cst ... src/cst_fegen.rs --pyi-output fltk/_native/fegen_cst.pyi` line
  (Makefile:258-262).
- **Repoint** fegen CST generation to the relocated crate. The existing
  `gen-rust-cst GRAMMAR=fegen.fltkg RS_OUT=tests/rust_cst_fegen/src/cst.rs`
  (Makefile:267) becomes `RS_OUT=crates/fegen-rust/src/cst.rs`, and gains the
  `--protocol-module fltk.fegen.fltk_cst_protocol --pyi-output fltk/_stubs/fegen_rust_cst/cst.pyi`
  flags formerly attached to the `cst_fegen.rs` step — i.e. the one surviving fegen-CST
  generation does the protocol/pyi work. The `--pyi-output` target is the pyright-resolved
  stub-package location from §2.2 (`fltk/_stubs/fegen_rust_cst/cst.pyi`), **not** a path under
  `crates/fegen-rust/` that pyright does not check.
- The "must match `src/cst_fegen.rs`" comment (Makefile:265-266) is deleted; there is
  no second copy to match.
- **Add** a `gen-rust-cst poc_grammar.fltkg → tests/rust_poc_cst/src/cst.rs` line for
  the new PoC fixture (the fixture is the canonical generated copy of the PoC grammar), and
  **repoint the spike `cp` (Makefile:280) to copy from `tests/rust_poc_cst/src/cst.rs`**.
  Rationale: the spike (`crates/fltk-cst-spike`) is python-**off** (`crate-type=["rlib"]`,
  `default=[]`, no pyo3 — Cargo.toml:9,14) and exists solely to compile the same generated
  CST in the python-off configuration; the PoC fixture is python-**on**. Two copies of the
  PoC CST must therefore coexist. The current `cp` (Makefile:280) guarantees they are
  **byte-identical at zero cost**. Regenerating each independently via two `gen-rust-cst`
  invocations would replace that guarantee with a diff-gate that only holds if both
  invocations use identical flags — the very fragility this refactor eliminates for the
  fegen grammar. So the `cp` is **kept** (fixture canonical, spike copies from it), not
  dropped. (This is the one grammar where the "exactly one generated CST per grammar" goal
  cannot be fully reached — python-on and python-off builds genuinely need two compiled
  copies; the `cp` keeps them a single source of truth.)

Build targets:

- `Makefile:build-fegen-rust-cst` (Makefile:198-199) and `build-fegen-rust-parser`
  (Makefile:217-219) update their paths from `tests/rust_cst_fegen` to
  `crates/fegen-rust`.
- A new `build-poc-cst` target builds `tests/rust_poc_cst` and is added to
  `build-test-fixtures` (Makefile:94) so `make test` builds it before pytest.
- `make check` sub-targets that reference `tests/rust_cst_fegen` by path —
  `cargo-clippy` (Makefile:129), `cargo-test-no-python` (Makefile:139),
  `cargo-clippy-no-python` (Makefile:147), `check-no-pyo3` (Makefile:166-168),
  `cargo-deny` (Makefile:177) — are repointed to `crates/fegen-rust`. New `tests/rust_poc_cst`
  entries are added to the python-off clippy/test lanes to keep coverage parity with the
  spike. For `cargo-deny` specifically (Makefile:174-177), `tests/rust_poc_cst` is a
  **standalone workspace** with its own `Cargo.lock` (like the other fixtures), so it is
  **not** covered by the root deny check; an explicit **fifth** line
  `cargo deny --manifest-path tests/rust_poc_cst/Cargo.toml check --config deny.toml` must be
  added alongside the existing four (root, rust_cst_fegen→crates/fegen-rust, rust_cst_fixture,
  rust_parser_fixture). Omitting it silently drops the new crate from the supply-chain gate.

### 2.6 Bazel wiring

The Bazel `:native` target globs `src/**/*.rs` (BUILD.bazel:34-53). After deleting
`src/cst_generated.rs`/`src/cst_fegen.rs`, the glob naturally yields a runtime-only
crate — **no BUILD rule change required for the source set**. Required edits:

- Update the `crate_features` comment (BUILD.bazel:39-42) which currently justifies the
  `python` feature by "register_classes symbols in cst_generated.rs / cst_fegen.rs."
  After the refactor the `python` feature is still needed (it gates the `Span`/`SourceText`
  pyclass registration via `fltk-cst-core/python`), but the comment's rationale must be
  rewritten to cite the span-type registration, not the deleted CST modules.
- `:native` / `:native_so` / `:native_py` (BUILD.bazel:34-75) otherwise unchanged:
  consumers still depend on `:native_py` for `import fltk._native` →
  `Span`/`SourceText`/`UnknownSpan`. This is exactly what clockwork's `fltk_pyo3_cdylib`
  relies on (rust.bzl:151-153; `clockwork/dsl/BUILD.bazel:75-96`).

The relocated `crates/fegen-rust` and `tests/rust_poc_cst` crates are standalone
workspaces built by maturin (Makefile), not by the root Bazel build today; no new Bazel
targets are required for them. (`rust.bzl`'s `fltk_pyo3_cdylib` is for *downstream*
consumers generating their own grammar, and is untouched.)

### 2.7 The clockwork spike update

Clockwork needs **no source change**. Its only `_native` dependency is
`fltk._native.Span` (clockwork/dsl/clockwork_rust_roundtrip_test.py:26-43), which
`_native` still exports. Its own grammar CST/parser come from `generate_rust_parser` +
`fltk_pyo3_cdylib` (clockwork/dsl/BUILD.bazel:67-96), which use the unchanged
`gen-rust-cst`/`gen-rust-parser`/`gen-rust-lib --module-name clockwork_native` path.

Verification step (not a code change): after the refactor, rebuild clockwork's
`clockwork_native` and run `clockwork_rust_roundtrip_test` to confirm
`fltk._native.Span` still resolves and the generated parser still parses. This is the
acceptance gate for "no external breakage."

## 3. Edge cases / failure modes

- **`pyrt/span.py` backend selector.** It imports `Span`/`SourceText`/`UnknownSpan` from
  `fltk._native`, warning on failure (`exploration-python-backend.md:37-40`). Removing
  the CST submodules does not remove those three names, so the selector keeps working.
  *Mitigation:* the existing `test_module_split.py` §4.6 assertions
  `test_native_still_has_span/source_text/unknown_span` (test_module_split.py:264-274)
  remain green and pin this.
- **Stale `_native.abi3.so`.** If `src/cst_fegen.rs` is deleted but the old `.so` is not
  rebuilt, `import fltk._native.fegen_cst` would still appear to work from a cached
  build. *Mitigation:* `build-test-fixtures` is a prerequisite of `test`
  (Makefile:94-97), so `make test`/`make check` always rebuild `_native` before pytest.
- **Tests that import the old paths.** `tests/test_rust_cst_poc.py:8` and
  `tests/test_module_split.py:46-50,239-291` import `fltk._native.poc_cst` /
  `fltk._native.fegen_cst`. These **must** be updated to the new import paths
  (`from poc_cst.cst import ...`; `import fegen_rust_cst.cst`) or they will error. The §4.6
  block's "absent from top level" assertions stay meaningful (the PoC classes are now in
  a different module entirely).
- **`fegen_rust_cst` already imported in `test_module_split.py`.** The file already
  imports `fegen_rust_cst.cst`/`.parser` (test_module_split.py:31-44) — those assertions
  are unaffected by the crate's *filesystem* move since the importable module name is
  preserved (§2.2).
- **`.pyi` resolution by pyright config, not just import name.** pyright resolves stubs by
  import name (genparser.py:288-296), **but only within its configured search tree** —
  `include = ["fltk", "*.py"]`, `stubPath = ""` (pyproject.toml:50,52). The `--pyi-output`
  flag (genparser.py:281-296) controls where the file is *written*, not whether pyright
  *looks* there. A stub written under `crates/fegen-rust/` is outside the `fltk` tree and is
  never resolved → the protocol-conformance check silently dies. *Mitigation:* §2.2 routes
  the stub to the pyright-resolved `fltk/_stubs/fegen_rust_cst/cst.pyi` stub package on the
  search path and requires the matching `pyproject.toml` `[tool.pyright]` edit; the test
  plan's pyright run (part of `make check`) would fail loudly if the stub were unresolved,
  since the protocol assertions in the stub would no longer be type-checked.
- **cargo-deny / clippy path drift.** Several `make check` steps name
  `tests/rust_cst_fegen/Cargo.toml` by path (Makefile:129,139,147,166-168,177). Missing
  any one when repointing to `crates/fegen-rust` silently drops a coverage lane. *Mitigation:*
  §2.5 enumerates every such line; the test plan re-runs full `make check`.
- **PoC fixture python-off coverage / two-copy identity.** The spike crate exists to
  guarantee the toy CST compiles python-off (Makefile:134-147), while the PoC fixture is
  python-on; both need a compiled copy of the same generated CST. *Mitigation:* the spike
  keeps `cp`-ing from the fixture's `cst.rs` (§2.5), so the two are byte-identical by
  construction — not by a diff-gate. `gencode` regenerates the fixture from
  `poc_grammar.fltkg` and the spike copies it; `git diff` after `make gencode`
  (Makefile:233-234) is then a backstop, not the primary guarantee.

## 4. Test plan

After the refactor, the suite proves the principle and the no-breakage claim:

- **`_native` is runtime-only (new/updated).** Assert `fltk._native` exposes `Span`,
  `SourceText`, `UnknownSpan` and **no** `fegen_cst`/`poc_cst` attributes and **no**
  `cst`-like submodules. Extend `test_module_split.py` §4.6: flip
  `test_fegen_cst_still_accessible` (test_module_split.py:280-283) and the `poc_cst`
  reachability/sys.modules cases (test_module_split.py:246-291) to assert *absence* from
  `_native`, and add explicit "no submodules registered on `_native`" coverage.
- **fegen CST/parser in the relocated crate (updated).** `test_module_split.py` §4.4-§4.5
  (test_module_split.py:128-209) already verify `fegen_rust_cst.cst`/`.parser` import
  mechanics and span-absence; these stay green after the crate move (import name
  preserved). The crate's own `native_parser_tests.rs` runs under
  `cargo-test-no-python` against `crates/fegen-rust`.
- **PoC fixture relocation (updated).** `tests/test_rust_cst_poc.py` retargets to
  `from poc_cst.cst import Identifier, Items` (the `cst` submodule wiring of §2.3) and keeps
  its label/span/equality assertions (test_rust_cst_poc.py:8+). New `poc_cst.cst`
  import-mechanics coverage replaces the old `fltk._native.poc_cst` submodule assertions.
- **`gen-rust-lib` span-only path (updated).** `fltk/fegen/test_gsm2lib_rs.py` drops the
  `test_native_spec_*` cases (and the `native_spec` name from its line-7 import) and adds:
  generating with `--register-span-types
  --unknown-span-static --no-cst --no-parser` emits a lib.rs with the span/UNKNOWN_SPAN
  block and **zero** `register_submodule` lines; `LibSpec.standard()` still emits
  `cst`(+`parser`).
- **gencode drift gate (existing).** `make gencode && git diff --exit-code` proves the
  committed `src/lib.rs`, the relocated `crates/fegen-rust/src/{cst,parser}.rs`, the fegen
  `.pyi` stub at `fltk/_stubs/fegen_rust_cst/cst.pyi`, and the PoC fixture `cst.rs` (with the
  spike's `cp`-derived copy) are exactly what the generators produce (Makefile:233-234).
- **Full gate.** `make check` passes (all repointed clippy/test/deny/no-pyo3 lanes).
- **External no-breakage (manual, clockwork).** Rebuild clockwork `clockwork_native`;
  `clockwork_rust_roundtrip_test` passes (`fltk._native.Span` resolves; parser parses) —
  §2.7.

## 5. Decisions (formerly open questions)

These were open questions in the draft; the user has resolved them, and the design body
above reflects the resolutions.

- **Relocated fegen CST module name — keep `fegen_rust_cst`.** No rename in this refactor.
  Backward-compat is waived, but the existing importable name is deliberately retained
  (§2.2); the principle constrains *where* grammar code lives, not its module name.
- **Crate location — promote to `crates/fegen-rust/`.** The fegen crate moves out of
  `tests/` into a first-class `crates/` crate, the Rust peer of committed
  `fltk/fegen/fltk_cst.py`/`fltk_parser.py` (§2.2). Makefile, `make check` lanes, Bazel
  notes, and cargo-deny coverage are all repointed accordingly (§2.5, §2.6).
- **Relocated fegen `.pyi` location — Option A.** The CST `.pyi` is still codegenned and
  its output is routed to a stub package inside the `fltk` tree,
  `fltk/_stubs/fegen_rust_cst/cst.pyi`, with the matching `stubPath`/`extraPaths` entry
  added to `[tool.pyright]` in `pyproject.toml` (§2.2, §2.5). Without that `pyproject.toml`
  edit the stub is dead and the `fltk.fegen.fltk_cst_protocol` conformance check stops
  running, so the edit is part of this design's acceptance.
