 Design: cst-python-feature-gate

Style: concise, precise, no padding. Audience: smart LLM/human implementing this change.
Sources: `requirements.md`, `exploration.md`, `request.md` (same dir). Requirements are not restated; this doc cites them.

## 1. Context / root cause

Everything in the Rust CST backend is pyo3-entangled even though the core data model is pure Rust:

- `crates/fltk-cst-core/Cargo.toml:15` — unconditional `pyo3` dependency.
- `crates/fltk-cst-core/src/span.rs` — `Span`/`SourceText` are `#[pyclass]`; `text`, `merge`, `intersect`, `has_source`, `len`, `is_empty` live only inside `#[pymethods]` (span.rs:204-433); `coerce_source` (span.rs:194) returns `PyResult` solely because its callers are pymethods.
- `crates/fltk-cst-core/src/cross_cdylib.rs` — entirely Python-boundary code; sole location of `unsafe` (lines 68, 169).
- Generated CST files (`fltk/fegen/gsm2tree_rs.py`) — unconditional pyo3 preamble (`_preamble()`, gsm2tree_rs.py:244), `#[pyclass]`/`#[pymethods]` on every node/enum, pyo3-only `to_pyobject`/`extract_from_pyobject`, `register_classes`.

A pure-Rust application (roadmap mode 2) or a Rust parser backend (mode 3, phase 2) cannot today build against this code without pulling in pyo3. The native surface already exists (`new_native`, `push_child_native`, `span_native`, `children_native`, structural `PartialEq`; see `tests/rust_cst_fixture/src/native_tests.rs`) — what is missing is the ability to compile *without* the pyo3 surface, plus native equivalents for the Span operations locked inside `#[pymethods]`.

## 2. Proposed approach

### 2.1 Feature gate on `fltk-cst-core`

Feature name **`python`**, **default-on**. Positive polarity is mandatory, not just idiomatic: `fltk-cst-core` is a shared rlib, and Cargo feature unification requires features to be additive — a negative feature (`no-python`) would let one consumer in a build graph disable pyo3 surface another consumer needs.

`crates/fltk-cst-core/Cargo.toml`:

```toml
[dependencies]
pyo3 = { version = "0.23", features = ["abi3-py310"], optional = true }

[features]
default = ["python"]
python = ["dep:pyo3"]
```

`src/lib.rs`:

```rust
#[cfg(feature = "python")]
mod cross_cdylib;
mod span;

#[cfg(feature = "python")]
pub use cross_cdylib::{extract_source_text, extract_span, get_source_text_type, get_span_type, span_to_pyobject};
pub use span::{SourceText, Span, SpanError};
```

`cross_cdylib.rs` compiles out wholesale (including `FLTK_CST_CORE_ABI` — its only python-off-safe item has no python-off consumer), structurally eliminating all `unsafe` per requirements Constraint 3.

`src/span.rs` split:

| Item | Mode |
|---|---|
| `SourceInner`, `SourceText` struct + `from_str`, `Span` struct, `unknown`, `new_sourceless`, `new_with_source`, `start`, `end`, `source_full_text_str`, `PartialEq`/`Eq`/`Hash`/`Clone` | both (unchanged) |
| `text`, `has_source`, `len`, `is_empty`, `merge`, `intersect`, `coerce_source` (native, see 2.2) | both (newly native) |
| `#[pyclass]` attrs (via `cfg_attr`), both `#[pymethods]` blocks, `SPAN_KIND_SPAN_CACHE`, `source_as_py`, `kind` getter, pyo3 `use` lines | python only |

Mechanics: `#[cfg_attr(feature = "python", pyclass(frozen, eq, hash))]` on `Span` (the unconditional `PartialEq`/`Hash` impls satisfy `eq, hash`), `#[cfg_attr(feature = "python", pyclass(frozen))]` on `SourceText`, `#[cfg(feature = "python")]` on each `#[pymethods]` impl block, the `GILOnceCell` static, `source_as_py`, and the pyo3/cross_cdylib `use` lines.

### 2.2 Native Span API (mode-independent)

Per requirements §1 "Native surface is mode-independent", all of the following live in the plain `impl Span` block, available identically in both modes:

```rust
pub fn text(&self) -> Option<String>                      // body moved from pymethods
pub fn has_source(&self) -> bool
pub fn len(&self) -> i64
pub fn is_empty(&self) -> bool
pub fn merge(&self, other: &Span) -> Result<Span, SpanError>
pub fn intersect(&self, other: &Span) -> Result<Span, SpanError>   // disjoint → Ok(Span::unknown()), matching Python semantics
fn coerce_source(&self, other: &Span) -> Result<Option<Arc<SourceInner>>, SpanError>
```

New public error type (resolves requirements open question 1 — dedicated enum, most forward-compatible for phase 2):

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[non_exhaustive]
pub enum SpanError {
    SourceMismatch,
}
// + impl Display, impl std::error::Error
```

Rust does not allow two inherent methods with the same name, so the `#[pymethods]` block keeps the Python-visible names via rename attributes — Python surface is byte-identical:

```rust
#[pyo3(name = "text")]      fn py_text(&self) -> Option<String> { self.text() }
#[pyo3(name = "merge")]     fn py_merge(&self, other: &Span) -> PyResult<Span> {
    self.merge(other).map_err(|_| PyValueError::new_err("cannot merge spans from different sources"))
}
// same pattern: py_intersect, py_has_source, py_len, py_is_empty
```

The error message string is preserved exactly (current text at span.rs:196-198); existing Python tests pin it. `text_or_raise` stays pymethods-only (its value is the Python exception messages; native callers use `text()`). `kind` stays pymethods-only per requirements open question 3 (Python-side discriminant; a native need, if any, goes in the gaps report). Naming precedent for the `py_` wrappers: existing `py_new`/`get_start`/`get_end` in the same file. No collision with the reserved generated-API names (`*_native`).

### 2.3 Generator: single cfg-gated output (mechanism C1)

Dual-output (C2) is rejected: it doubles the artifact surface out-of-tree consumers must manage, forks the regen workflow (`make gencode` idempotency would span two files per grammar), and buys nothing — the cfg-gated split is clean because the native/pyo3 boundary in generated code is already block-shaped (whole `impl` blocks, whole attributes).

Changes in `fltk/fegen/gsm2tree_rs.py`, all localized to emission methods:

- **`_preamble()`** (line 244):
  ```rust
  use fltk_cst_core::Span;
  #[cfg(feature = "python")]
  use fltk_cst_core::{extract_span, get_span_type, span_to_pyobject};
  #[cfg(feature = "python")]
  use pyo3::exceptions::{PyTypeError, PyValueError};
  #[cfg(feature = "python")]
  use pyo3::prelude::*;
  #[cfg(feature = "python")]
  use pyo3::types::{PyList, PyTuple, PyType};
  #[cfg(feature = "python")]
  use pyo3::PyTypeInfo;
  ```
- **`_node_kind_block()` / `_label_enum_block()`**: `#[pyclass(...)]` → `#[cfg_attr(feature = "python", pyclass(...))]`; each variant's `#[pyo3(name = "...")]` → `#[cfg_attr(feature = "python", pyo3(name = "..."))]`; the `#[pymethods]` impl block gets a `#[cfg(feature = "python")]` line above it. `#[derive(Clone, PartialEq, Eq, Hash)]` and `#[allow(non_camel_case_types)]` stay unconditional. (`cfg`/`cfg_attr` resolve before proc-macro expansion, so in python-off mode the `pyo3(...)` variant attrs vanish before anything would try to interpret them.)
- **`_child_enum_block()`**: enum definition and manual `PartialEq` unconditional; the `impl <Class>Child { to_pyobject, extract_from_pyobject }` block gated with `#[cfg(feature = "python")]`.
- **`_node_block()`**: `#[pyclass]` → `#[cfg_attr(feature = "python", pyclass)]`; struct, `PartialEq`, `Clone`, native impl block unconditional; `#[pymethods]` impl block gated.
- **`_register_classes_fn()`**: entire fn gated.

No generator CLI/flag changes; `generate()` and `generate_pyi()` signatures unchanged. The `.pyi` output is unaffected (Python surface unchanged).

Default-mode output is **functionally identical, not byte-identical** (cfg lines are added) — requirements accept this explicitly ("byte-identical preferred where achievable; functional identity required"). The cfg approach cannot be byte-identical by construction.

### 2.4 Consumer-crate feature plumbing

`#[cfg(feature = "python")]` in generated code keys on the feature of the **crate the generated file is compiled into**. Every crate compiling generated CST code must therefore declare a `python` feature that (a) registers the cfg key (else `unexpected_cfgs` fires under `-D warnings`) and (b) forwards to `fltk-cst-core/python`.

In-tree updates:

- **Root `Cargo.toml` (fltk-native)** — holds `src/cst_generated.rs`, `src/cst_fegen.rs`:
  ```toml
  [features]
  default = ["extension-module"]
  extension-module = ["python", "pyo3/extension-module"]
  python = ["fltk-cst-core/python"]
  ```
  `pyo3` stays a non-optional dep (its `lib.rs` is unconditionally a `#[pymodule]`); building fltk-native python-off is unsupported and never exercised — the python-off lane uses `-p` package selection (§2.6).
- **`tests/rust_cst_fixture/Cargo.toml`** and **`tests/rust_cst_fegen/Cargo.toml`**: same three-line feature shape (these already have `extension-module` + `default-features = false` on fltk-cst-core; without the forwarding feature, the new default-on `python` feature of fltk-cst-core would be stripped and their builds would break).

**Out-of-tree consumers** — two baselines exist, and they differ:

- *Fixture-pattern consumers* (`tests/rust_cst_fixture/Cargo.toml:20`: `fltk-cst-core` dep with `default-features = false`): migration is adding the feature block above once (declare `python`, forward `fltk-cst-core/python`).
- *Guide-following consumers*: the published template (`docs/rust-cst-extension-guide.md:41-57`) lists **pyo3 as the only dependency** — no `fltk-cst-core` entry — and line 30 claims "The generated file has no link-time dependency on FLTK's crate. It depends on PyO3 only." That is already stale at HEAD: the generated preamble has imported `fltk_cst_core` since the preamble-helpers work (`gsm2tree_rs.py:246`), so a guide-built manifest already fails on regeneration with unresolved `fltk_cst_core` imports, independent of this change. Their migration is: add the `fltk-cst-core` dependency (`default-features = false`, `features = ["python"]` or a forwarding feature) **and** the feature block.

Failure modes are loud, not silent: unresolved `fltk_cst_core` imports (missing dep), `unexpected_cfgs` warning naming the `python` cfg, then hard compile errors (`register_classes` not found from their `#[pymodule]` init). The guide gets a corrected template plus a migration note (§2.7). This is a deliberate, called-out one-time manifest change — see Open question 1.

### 2.5 Spike crate: `crates/fltk-cst-spike`

New workspace member (root `Cargo.toml` `members += "crates/fltk-cst-spike"`), resolving requirements open question 2. Chosen over a `#[cfg(test)]` module in fltk-cst-core because the spike must compile a **generated** CST file (which fltk-cst-core cannot host without inverting the dependency) and over a fixture-style out-of-workspace crate because workspace membership puts it under plain `cargo test`/`clippy` with no bespoke build plumbing.

```toml
[package]
name = "fltk-cst-spike"
# rlib, never published as an extension

[features]
default = []                                  # python OFF by default — this crate's point
python = ["dep:pyo3", "fltk-cst-core/python"] # registers the cfg key; enables dual-mode compile check

[dependencies]
fltk-cst-core = { path = "../fltk-cst-core", default-features = false }
pyo3 = { version = "0.23", features = ["abi3-py310"], optional = true }
```

`src/lib.rs`:

```rust
#![cfg_attr(not(feature = "python"), forbid(unsafe_code))]
pub mod cst;          // generated from poc_grammar.fltkg
#[cfg(test)]
mod spike_tests;
```

`forbid(unsafe_code)` is conditional on python-off because pyo3's proc macros may expand to `unsafe` in python-on builds; the guarantee being enforced ("no unsafe in the python-off configuration", requirements Constraint 3) is exactly the python-off configuration, and there the forbid is unconditional within the build. fltk-cst-core's own `unsafe` is out of reach structurally (cross_cdylib.rs compiled out when the spike's graph resolves fltk-cst-core without `python`).

`src/cst.rs`: generated from `fltk/fegen/test_data/poc_grammar.fltkg` via a new `make gencode` step (`make gen-rust-cst GRAMMAR=fltk/fegen/test_data/poc_grammar.fltkg RS_OUT=crates/fltk-cst-spike/src/cst.rs`), committed like all generated code. No `--pyi-output` (no Python module). PoC grammar (`Identifier`, `Items`, `Trivia`) is the request's named grammar; it has labeled children, span children, and node children — sufficient for all required exercises.

`spike_tests.rs` exercises (requirements §3, all with **source-bearing** spans built from `SourceText::from_str`):
node construction (`new_native`), labeled child append (`push_child_native`), traversal (`children_native`, matching on child enum variants down to leaf spans), span text reads (`span.text()` asserted against expected source substrings), `merge`/`intersect` (same-source merge, source-mismatch `Err(SpanError::SourceMismatch)`, sourceless+sourced coercion, disjoint intersect → unknown sentinel), and structural equality (equal/unequal subtrees). No parsing. Anything found awkward goes in the gaps report, not in code fixes.

### 2.6 Makefile / CI

CI (`.github/workflows/ci.yml`) is unchanged — it runs `make check`, which gains steps, satisfying both the CI requirement and the "reproducible via the standard local entrypoint" requirement (§5) at once.

New Makefile targets, appended to the `check` step list:

```make
# python-off lane: feature isolation requires -p selection (see §3, unification)
cargo-test-no-python:
	cargo test -q -p fltk-cst-core --no-default-features
	cargo test -q -p fltk-cst-spike

cargo-clippy-no-python:
	cargo clippy -q -p fltk-cst-core --no-default-features -- -D warnings
	cargo clippy -q -p fltk-cst-spike -- -D warnings
	cargo clippy -q -p fltk-cst-spike --features python -- -D warnings   # dual-mode compile of identical generated output

check-no-pyo3:
	@set -e; \
	out="$$(cargo tree -p fltk-cst-spike --edges normal,build)"; \
	echo "$$out" | grep -q fltk-cst-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-cst-core"; exit 1; }; \
	! echo "$$out" | grep -q pyo3 || { echo "FAIL: pyo3 present in fltk-cst-spike python-off dependency graph"; exit 1; }; \
	core="$$(cargo tree -p fltk-cst-core --no-default-features --edges normal,build)"; \
	echo "$$core" | grep -q fltk-cst-core || { echo "FAIL: check-no-pyo3 broken: cargo tree output lacks fltk-cst-core"; exit 1; }; \
	! echo "$$core" | grep -q pyo3 || { echo "FAIL: pyo3 present in fltk-cst-core --no-default-features graph"; exit 1; }
```

`check-no-pyo3` is hardened against vacuous passes: a naive `if cargo tree | grep -q pyo3` takes grep's pipeline exit status, so a *failing* `cargo tree` (renamed package, manifest/lock rot) yields empty output → no match → green gate, defeating requirements §3's "automated, not eyeballed" exactly in the rot scenario. Instead: `set -e` fails the recipe if `cargo tree` itself fails (command-substitution assignment propagates the status), and a positive control (`grep -q fltk-cst-core`) proves the tree was actually produced before the negative assertion runs. The second pair runs the literal requirements-§1 acceptance command (`cargo tree -p fltk-cst-core --no-default-features` shows no pyo3); the spike tree covers it transitively, but the acceptance criterion is asserted directly rather than by inference.

`check` steps become: `lint format-check typecheck test cargo-check cargo-clippy cargo-test cargo-test-no-python cargo-clippy-no-python check-no-pyo3`.

The `--features python` clippy run on the spike is what validates requirement §2 ("generated code compiles in both modes") on the *same* generated file; python-on coverage of the other generated files continues via the existing builds (`build-native`, fixture extensions) and the default `cargo-clippy`/`cargo-test`. The "clippy -D warnings in both feature modes" verification gate maps to: existing `cargo-clippy` (python-on, workspace) + `cargo-clippy-no-python` (python-off + spike-python-on).

### 2.7 Documentation

- `docs/rust-cst-extension-guide.md`: corrected Cargo.toml template — add the missing `fltk-cst-core` dependency (`path`/version, `default-features = false`, `features = ["python"]` or forwarding feature) *and* the feature block from §2.4; delete or correct the stale line-30 claim "It depends on PyO3 only" (false since the preamble-helpers work — see §2.4). Migration note covers both §3 consumer paths: upgrade-then-regenerate and upgrade-without-regenerating (manifest fix first, independent of regeneration).
- `crates/fltk-cst-core/Cargo.toml` comment block (lines 10-13) updated to describe the `python` feature and the downstream `default-features = false, features = ["python"]` (or forwarding-feature) pattern.

### 2.8 Gaps report

`docs/adr/2026/06/10-cst-python-feature-gate/gaps.md`, written while implementing the spike. Findings only, no fixes (requirements §4). Section skeleton: span construction ergonomics; span text access cost (e.g. `text()` returns `Option<String>` — a parser likely wants borrowed `&str` / byte offsets); trivia handling; error/diagnostic types; node-building ergonomics for a parser (e.g. no builder, `Box` allocation per child); anything else surfaced. May be short; must exist.

## 3. Edge cases / failure modes

- **Workspace feature unification.** Under plain `cargo test` (whole workspace), fltk-native's `python` requirement unifies into fltk-cst-core, so the spike's test binary links a python-on fltk-cst-core even though the spike's own cfg gates are off. This is fine for compilation/tests (python-on core is a strict superset) but means the "no pyo3" property only holds under `-p` isolation — which is precisely how `cargo-test-no-python` and `check-no-pyo3` invoke cargo (resolver 2: `-p` resolves features for the selected package's graph only). Both behaviors verified empirically with a scratch workspace replicating this feature topology: `cargo tree -p spike` shows no optional dep despite a python-on sibling member, and a full workspace build compiles the core crate once, unified python-on. The mechanical check therefore tests the real claim; plain workspace-wide builds do not.
- **Out-of-tree consumer upgrades fltk-cst-core without regenerating.** Likely the first-contact case: dependency upgrade precedes regeneration. With the documented `default-features = false` dep (fixture pattern; `crates/fltk-cst-core/Cargo.toml:13` comment), the upgrade resolves the new default-on `python` feature **off**; their committed, ungated, previously-generated `cst.rs` then fails — `extract_span`/`get_span_type`/`span_to_pyobject` gated out of `lib.rs`, `Span` no longer a pyclass. Loud, but the unresolved-import diagnostics land inside generated code the consumer didn't touch and don't point at the manifest. The §2.7 migration note must therefore state: on upgrading fltk-cst-core, add `features = ["python"]` (or the forwarding feature) to the dep — before or independent of regenerating.
- **Out-of-tree consumer regenerates without declaring the feature.** `unexpected_cfgs` warning + hard error on the missing `register_classes`. Loud and actionable; covered by the guide's migration note. No silent behavior change is possible: either the feature is declared default-on (today's behavior) or the build fails.
- **Consumer declares `python` in their crate but forgets `fltk-cst-core/python` forwarding.** Their crate's pymethods compile but fltk-cst-core's `Span` is not a pyclass → compile error in generated code referencing `Span` in pyo3 positions. Still loud; the documented feature block forwards correctly.
- **`cfg_attr` + pyo3 attribute interplay.** `cfg`/`cfg_attr` are resolved before proc-macro expansion, so `#[cfg_attr(feature = "python", pyo3(name = "..."))]` on enum variants is stripped in python-off builds before anything could reject the unknown `pyo3` attribute, and present (as plain `#[pyo3(...)]`) when the `pyclass` macro on the enum expands. Both attrs share one cfg, so they are never inconsistent.
- **`pyclass(eq, hash)` on `Span`** requires `PartialEq`/`Hash`; those impls are unconditional, so python-on expansion is unaffected by the `cfg_attr` rewrite.
- **Python-visible behavior drift in Span.** The `py_*` rename-wrapper pattern keeps names, signatures, semantics, and error messages identical; the full pytest suite (and existing merge/intersect tests) pins this. `__repr__`, getters, constructors untouched.
- **Clippy noise in new modes.** Python-off fltk-cst-core: all remaining items are `pub` or used; no dead code expected. `Span::len`/`is_empty` pair satisfies `clippy::len_without_is_empty`. The spike's `--features python` build compiles `register_classes` as unused-but-`pub` — no warning. Any residual lint is fixed at implementation; `-D warnings` in all lanes prevents rot.
- **maturin / wheel builds.** maturin builds fltk-native with default features → `extension-module` → `python`; byte-for-byte today's dependency activation. `default = ["python"]` on fltk-cst-core additionally protects any consumer that does *not* pass `default-features = false`.
- **Fixture-crate lockfiles.** Making pyo3 optional and adding features changes no dependency versions, so the standalone fixture `Cargo.lock` files stay byte-identical. Building all three extensions in CI (as today) confirms.
- **`make gencode` idempotency** with the new spike step: same generator, deterministic output, committed file; `git diff` after regen stays the cheat-detector.

## 4. Test plan

TDD ordering: generator-output tests first, then generator change; native-API tests first, then span.rs change; spike tests are themselves the validation artifact.

1. **Generator output tests** (`tests/test_gsm2tree_rs.py` — extend, and update existing exact-string assertions at lines 175-185, 438-441, 482-486 that pin the old preamble):
   - Preamble: `use fltk_cst_core::Span;` unconditional; the three-helper import and every pyo3 import preceded by `#[cfg(feature = "python")]`.
   - `#[cfg_attr(feature = "python", pyclass...)]` present on NodeKind, label enums, node structs; raw `#[pyclass` absent.
   - Every `#[pymethods]` occurrence immediately preceded by `#[cfg(feature = "python")]`; same for `register_classes` and the child-enum conversion `impl`.
   - Native impl blocks, child enum definitions, `PartialEq`/`Clone`, derives: unconditional (no cfg line above).
   - Variant `#[pyo3(name = ...)]` attrs wrapped in `cfg_attr` (update assertions at lines 221-235, 609-648).
2. **fltk-cst-core native unit tests** (extend the existing `tests` module in `crates/fltk-cst-core/src/lib.rs`; run in both lanes):
   - `text()`: sourceless → None; in-bounds slice; codepoint (non-ASCII) translation; empty span; negative/inverted/OOB → None.
   - `merge`: same source Ok; `Arc`-distinct sources → `Err(SpanError::SourceMismatch)`; sourceless+sourced → Ok carrying the source.
   - `intersect`: overlap Ok; disjoint → Ok(unknown sentinel); mismatch Err.
   - `has_source`/`len`/`is_empty` basic semantics (including sentinel span).
3. **Python regression** (existing suite, default mode): `uv run --group dev maturin develop && uv run pytest` — pins merge/intersect Python behavior incl. the `ValueError` message, `kind`, getters, full generated-code Python surface. No new Python tests needed; absence of diffs is the assertion.
4. **Spike tests** (`crates/fltk-cst-spike/src/spike_tests.rs`): the exercises in §2.5; pass under `cargo test -p fltk-cst-spike` (python off).
5. **Mode/lane checks** (Makefile, run by `make check` locally and in CI):
   - `cargo-test-no-python`, `cargo-clippy-no-python` (includes spike `--features python` compile), `check-no-pyo3` (mechanical `cargo tree` assertion).
6. **Verification gates** (request): full default-mode suite green; `ruff check` + `pyright`; clippy `-D warnings` both modes (§2.6 mapping); `make gencode` idempotent (regen all, `git diff` clean after `make fix`); `gaps.md` exists.

## 5. Open questions

1. **Out-of-tree consumer manifest migration (confirm/veto).** The chosen design requires existing out-of-tree consumer crates to add a three-line `[features]` block (and `fltk-cst-core/python` forwarding) the next time they upgrade fltk — with or without regenerating — a hard compile error until they do (§2.4, §3). For guide-following consumers the churn is larger: the published template never declared the `fltk-cst-core` dependency at all and is already stale at HEAD (its "depends on PyO3 only" claim broke with the preamble-helpers work, before this change); their migration is dependency addition + feature block, and §2.7 fixes the guide regardless of the polarity decision here. This is in tension with requirements' "out-of-tree regeneration with current settings behaves identically by default", but is anticipated by requirements' User-visible surface ("generated-code consumers' Cargo manifests as documented usage") and is comparable to the CLAUDE.md-sanctioned "update import statements" level of churn. The alternative — negative-polarity cfg in generated code only (`#[cfg(not(feature = "fltk-no-python"))]`) — avoids the hard error but still triggers `unexpected_cfgs` warnings on undeclared keys, introduces a second, negative feature name alongside fltk-cst-core's positive `python`, and leaves consumers' python surface enabled by lint-warned accident rather than declaration. Recommendation: accept the one-time manifest addition as a deliberate, documented change. Needs user sign-off because it touches the breaking-change policy.

USER ANSWER: There are no Rust-using out of tree consumers yet, only Python consumers. This is not an issue.
