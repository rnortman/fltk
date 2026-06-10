# Design: preamble-helpers-into-cst-core

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human implementer.

Requirements: `request.md` (this dir). Exploration: `exploration.md` (this dir). This doc does not restate them; it specifies the change.

## 1. Context / root cause

`_preamble()` (`fltk/fegen/gsm2tree_rs.py`, the `_preamble` method; TODO comment at its head) emits five items — `FLTK_NATIVE_SPAN_TYPE`, `extract_span` (contains `unsafe { downcast_unchecked }`), `get_span_type`, `FLTK_NATIVE_SOURCE_TEXT_TYPE`, `get_source_text_type` — byte-identically into three committed generated files (`src/cst_fegen.rs:8-75`, `src/cst_generated.rs:8-75`, `tests/rust_cst_fixture/src/cst.rs:8-75`). Bug fixes to these helpers, including the unsafe path, currently propagate only by regeneration — worst case for out-of-tree consumers (see CLAUDE.md: generated output is public API). Direction decided at triage (request.md §Direction): move the five items into `fltk-cst-core`; functions `pub`, statics crate-private.

Soundness is settled by exploration.md §2-3: `fltk-cst-core` is an rlib; per-cdylib copies of `GILOnceCell` statics are correct and precedented (`SPAN_KIND_SPAN_CACHE`, `crates/fltk-cst-core/src/span.rs:12`); moving `extract_span` into the rlib strengthens the shared-rlib safety invariant.

## 2. Proposed approach

### 2.1 New module in `fltk-cst-core`

New file `crates/fltk-cst-core/src/cross_cdylib.rs` containing the five items, moved byte-for-byte from the current preamble except:

- `fn extract_span`, `fn get_span_type`, `fn get_source_text_type` become `pub fn`.
- The two statics become `pub(crate)` (request.md direction): external code must go through the accessors. Only the same-module accessor functions touch them.
- All doc comments and the full SAFETY / INVARIANT VIOLATION comment block on `extract_span` are preserved verbatim (request.md constraint).
- Module-local imports: `use crate::Span;`, `use pyo3::exceptions::PyTypeError;`, `use pyo3::prelude::*;`, `use pyo3::sync::GILOnceCell;`, `use pyo3::types::PyType;`. No new crate dependencies — pyo3 0.23 with the needed features is already a dependency (`crates/fltk-cst-core/Cargo.toml`).
- `get_source_text_type` keeps its inline `pyo3::exceptions::PyRuntimeError` path; `get_span_type` keeps its raw (unwrapped) import error. The error asymmetry is existing behavior; this change is behavior-preserving and does not touch it.

`crates/fltk-cst-core/src/lib.rs` adds:

```rust
mod cross_cdylib;
pub use cross_cdylib::{extract_span, get_source_text_type, get_span_type};
```

Public API additions to the crate are exactly these three functions (request.md constraint).

### 2.2 Shrink `_preamble()` in `gsm2tree_rs.py`

`_preamble()` emits only `use` lines:

```rust
use fltk_cst_core::{extract_span, get_source_text_type, get_span_type, Span};
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyTuple, PyType};
use pyo3::PyTypeInfo;
```

Rationale per line (verified against the body of `src/cst_fegen.rs` below the preamble):

- Helpers imported by name so every existing call site (`extract_span(py, ...)`, `get_span_type(py)`, `get_source_text_type(py)`) compiles unchanged — no edits to any other emission method in `gsm2tree_rs.py`.
- `use pyo3::sync::GILOnceCell;` dropped: zero uses in the post-preamble body of all three generated files (verified by grep on lines 78+ of each).
- `PyTypeError`/`PyValueError`: used in body (56/78 occurrences).
- `PyList`/`PyTuple`/`PyType`: used in body (92/28/28).
- `PyTypeInfo`: required for `::type_object(py)` method-call syntax in `Label()` classattrs.

No formatter touches generated `.rs`: `make fix` and the formatting tail of `make gencode` (Makefile) run ruff only — Python files. Committed `.rs` files are byte-identical to raw `generate()` output (request.md's MD5 is of the generator string). So the `use` block is committed exactly as `_preamble()` emits it: pick one ordering (the block above), keep it stable. gencode idempotency rests on generator determinism (already covered by `TestDeterministicOutput`) plus the double-run check in §4. Do not run `cargo fmt` on regenerated files — it would diverge committed files from generator output and break the double-run check.

Delete the `TODO(preamble-helpers-into-cst-core)` comment at the head of `_preamble()` and the corresponding `TODO.md` section.

### 2.3 Regeneration

`make gencode` then `make fix` (`make fix` normalizes the regenerated Python files only; it never touches `.rs` — §2.2); commit all three regenerated files. `tests/rust_cst_fegen/src/cst.rs` is an `include!` of `src/cst_fegen.rs` — no change needed there. Both fixture crates already depend on `fltk-cst-core` (`tests/rust_cst_fixture/Cargo.toml:20`, `tests/rust_cst_fegen/Cargo.toml` equivalent), so the new imports resolve.

### 2.4 Files touched

| File | Change |
|---|---|
| `crates/fltk-cst-core/src/cross_cdylib.rs` | new — five moved items |
| `crates/fltk-cst-core/src/lib.rs` | `mod` + `pub use` for the three fns |
| `crates/fltk-cst-core/src/span.rs` | `TODO(span-source-as-py-crosscdylib)` comment wording updated (§3) |
| `fltk/fegen/gsm2tree_rs.py` | `_preamble()` shrunk; TODO comment removed |
| `TODO.md` | entry removed |
| `tests/test_gsm2tree_rs.py` | preamble assertions updated (§4) |
| `src/cst_fegen.rs`, `src/cst_generated.rs`, `tests/rust_cst_fixture/src/cst.rs` | regenerated |

## 3. Edge cases / failure modes

- **Old generated code against new `fltk-cst-core`** (request.md constraint: must keep compiling). The inline helper copies reference only `fltk_cst_core::Span` and pyo3 — no crate internals. The change is purely additive to the crate's public API; old code uses a non-glob import (`use fltk_cst_core::Span;`), so the new `pub` names cannot collide or shadow. Old code compiles unchanged. Verify mechanically during implementation: after changing the crate but before regenerating, build the fixture crate (old generated code + new crate) and confirm it compiles.
- **`GILOnceCell` use-line removal breaks a generated file.** Verified zero body uses in all three generated files; any future generator change reintroducing a use fails loudly at build (`maturin develop` + `cargo test` in §4).
- **Name capture in generated code.** Imported helper names are snake_case module-scope; generated module-scope items are PascalCase structs/enums plus `register_classes`. Generated methods live inside `impl` blocks and cannot shadow module-scope imports. No collision path.
- **Formatter-induced drift on generated `.rs`.** No Rust formatter exists in the repo's flow (§2.2); committed `.rs` must equal generator output byte-for-byte. The failure mode is a human/agent manually running `cargo fmt` on regenerated files — the next `make gencode` then produces a non-empty diff. Guarded by the §4 double-run check.
- **Safety invariant.** Unchanged in content, strengthened in structure: `extract_span` and `Span` now live in the same compilation unit, so "both cdylibs link the same fltk-cst-core rlib" covers the helper itself (exploration.md §3). The SAFETY comment moves with the code, verbatim.
- **Per-cdylib static duplication.** Not a failure mode — intended semantics, identical to current behavior (exploration.md §2). Each cdylib caches the same `fltk._native` type objects independently.
- **`span-source-as-py-crosscdylib` interaction.** Out of scope (request.md non-goal). The `TODO(span-source-as-py-crosscdylib)` comment at `crates/fltk-cst-core/src/span.rs:148` references "generator preamble"; after this change `extract_source_text` should land in `cross_cdylib.rs` directly. Update that TODO comment's wording ("generator preamble" → "fltk-cst-core cross_cdylib module") as part of this change — a two-word doc fix, not scope creep, and it prevents the successor task from re-introducing preamble emission.

## 4. Test plan

TDD ordering: update generator-output assertions first (they fail against current `_preamble()`), then change the generator, then regenerate.

**Updated tests** (`tests/test_gsm2tree_rs.py`):

- `TestPreamble.test_required_use_declarations`: assert the new five-line `use` block (§2.2); assert `use pyo3::sync::GILOnceCell;` **absent**.
- `TestPreamble.test_preamble_at_start`: first line is the new `fltk_cst_core` combined import.
- New `TestPreamble.test_helpers_not_emitted`: assert `fn extract_span`, `fn get_span_type`, `fn get_source_text_type`, `FLTK_NATIVE_SPAN_TYPE`, `FLTK_NATIVE_SOURCE_TEXT_TYPE`, and `py.import("fltk._native")` each absent from generated source (the import-count check in the current `test_get_span_type_helper_emitted` tightens from `<= 2` to `== 0`).
- `test_get_span_type_helper_emitted` (quality-1): the positive assertion (helper emitted) inverts — the guarantee becomes "no local helper, no per-method init block"; keep the `let span_type = FLTK_NATIVE_SPAN_TYPE.get_or_try_init` negative assertion; fold into or rename alongside `test_helpers_not_emitted`.
- `test_preamble_in_fegen_source`, `test_minimal_grammar_has_preamble`: drop the `GILOnceCell` use-line assertion; flip `FLTK_NATIVE_SPAN_TYPE` from present to absent; add the combined `fltk_cst_core` import assertion.

**Unchanged contract tests**: `tests/test_phase4_rust_fixture.py` and the fixture-crate tests exercise cross-cdylib `extract_span` at runtime — pass before and after with no edits (request.md verification). The helpers themselves get no new Rust unit tests: they require a live Python runtime with `fltk._native` importable, which the fixture tests already provide end-to-end.

**Verification gate** (request.md):

1. `uv run --group dev maturin develop` → `uv run pytest` green; `cargo test` for the crates; `uv run ruff check . && uv run pyright` clean.
2. `make gencode && make fix` → commit; second `make gencode && make fix` → `git diff` empty.
3. `grep -c 'fn extract_span' src/cst_fegen.rs` = 0; same for the other two generated files; helpers defined exactly once, in `crates/fltk-cst-core/src/cross_cdylib.rs`.
4. `grep -rn 'preamble-helpers-into-cst-core' --include='*.py' --include='*.rs' .` returns nothing, and the slug is absent from `TODO.md`. (This scopes request.md's repo-wide grep to the TODO system's actual join points — code comments + master list. The slug necessarily survives in `docs/adr/`, including this task's own directory name; ADRs are immutable per CLAUDE.md, so a repo-wide grep can never be empty.)

## 5. Open questions

None.
