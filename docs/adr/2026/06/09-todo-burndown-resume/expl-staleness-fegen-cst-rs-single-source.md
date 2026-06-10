# Staleness check: `fegen-cst-rs-single-source` design

Concise. Precise. Token-dense. No fluff. Audience: smart LLM/human.

Verified against HEAD `af6e6f3`. Key intervening commit: `4c8f0ad` ("Rust CST holds native Span and children — no Python objects").

---

## TODO slug — still live

`TODO.md:23-25`: entry `fegen-cst-rs-single-source` still present verbatim, same description as when design was written.

`Makefile:108`: `TODO(fegen-cst-rs-single-source)` code comment is live:
```makefile
# Rust: tests/rust_cst_fegen/src/cst.rs (fegen.fltkg — TODO(fegen-cst-rs-single-source): duplicate of cst_fegen.rs)
$(MAKE) gen-rust-cst GRAMMAR=fltk/fegen/fegen.fltkg RS_OUT=tests/rust_cst_fegen/src/cst.rs
```

This contradicts the design's "Edge cases" claim (`design.md:52`) that "no such comment exists — grep found the slug only in `TODO.md:39`." A `TODO(slug)` comment **does** exist, placed in the Makefile by commit `4c8f0ad`. The design's assertion that removing the code comment is a no-op is no longer correct; the Makefile comment must also be removed when completing the TODO.

---

## Core root-cause claim — still valid

Both files still exist as independent committed copies:
- `src/cst_fegen.rs` — 6857 lines
- `tests/rust_cst_fegen/src/cst.rs` — 6857 lines
- `md5sum`: both `4bff0dbe6a6f16af70f386b3cb55c262`; `diff` exits 0

The files are still byte-identical and independently committed.

Commit `4c8f0ad` introduced `make gencode` (`Makefile:104-109`) which regenerates **both** files independently — `src/cst_fegen.rs` then `tests/rust_cst_fegen/src/cst.rs` — from the same grammar. The structural drift risk is preserved: regenerating only one (via `make gen-rust-cst RS_OUT=src/cst_fegen.rs`) leaves the other stale. `gencode` regenerates both, but only if invoked; the foot-gun described in the design is still present.

---

## File/line references — what changed in 4c8f0ad

### `src/lib.rs`

Design cited `src/lib.rs:5` for `mod cst_fegen;` and `src/lib.rs:44` for `cst_fegen::register_classes(&fegen_sub)?;`.

Current HEAD:
- `src/lib.rs:4`: `mod cst_fegen;` (was `:5` — shifted by one due to header changes)
- `src/lib.rs:34`: `cst_fegen::register_classes(&fegen_sub)?;` (was `:44` — significantly shifted; `src/lib.rs` restructured in `4c8f0ad`)

The line numbers cited in the design are stale but the code they reference still exists, just at different lines.

### `tests/rust_cst_fegen/src/lib.rs`

Design (and exploration) cited `lib.rs:11` for `mod cst;` and `lib.rs:15` for `cst::register_classes(m)?;`.

Current HEAD:
- `tests/rust_cst_fegen/src/lib.rs:15`: `mod cst;`
- `tests/rust_cst_fegen/src/lib.rs:21`: `cst::register_classes(m)?;`

Commit `4c8f0ad` added `use fltk_cst_core::{SourceText, Span};` and two `m.add_class` calls, shifting line numbers. The module structure (still `mod cst;` → `cst::register_classes(m)?;`) is unchanged.

### `tests/rust_cst_fegen/Cargo.toml`

Commit `4c8f0ad` added `fltk-cst-core = { path = "../../crates/fltk-cst-core", default-features = false }` at line 20. The design (`design.md:50`) notes that `lib.rs:9` already has `use pyo3::prelude::*;` and the included module gets its own — still true. An additional wrinkle: `tests/rust_cst_fegen/src/lib.rs:12` now also has `use fltk_cst_core::{SourceText, Span};`; `src/cst_fegen.rs:1` has `use fltk_cst_core::Span;`. These live in different scopes (`lib` root vs. `cst` module), no conflict — design's analysis still valid.

### `src/cst_fegen.rs` opening lines — include! feasibility

Design `design.md:44` and `exploration.md:74` verify that `src/cst_fegen.rs` starts with `use` items, not `#![...]` inner attributes, making `include!` valid. Current HEAD: `src/cst_fegen.rs:1-6`:
```rust
use fltk_cst_core::Span;
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::sync::GILOnceCell;
use pyo3::types::{PyList, PyTuple, PyType};
use pyo3::PyTypeInfo;
```
Starts with `use`, no inner attributes. The `include!` feasibility claim still holds.

### Makefile `gen-rust-cst` target

Design cited `Makefile:54-55` for the `gen-rust-cst` target. Current HEAD:
- `Makefile:69-70`: `gen-rust-cst` target (line numbers shifted due to expansion of Makefile by `4c8f0ad`)

### `tests/rust_cst_fegen/Cargo.toml` `build-fegen-rust-cst` target

Design/exploration cited `Makefile:49-50` for `build-fegen-rust-cst`. Current HEAD:
- `Makefile:64-65`: same target, same content.

---

## What 4c8f0ad changed in the generated CST sources

- `src/cst_fegen.rs`: grew from 5080 → 6857 lines. Generator (`gsm2tree_rs.py`) now emits native `fltk_cst_core::Span` struct field, native `Vec<(Option<Label>, Child)>` children, GIL-free constructors, native equality (`PartialEq`), span setters with cross-cdylib `GILOnceCell` cache, and `SpanProtocol` impl. The file still starts with `use` statements (no inner attributes); `include!` feasibility unchanged.
- `tests/rust_cst_fegen/src/cst.rs`: updated identically (same content, same hash). Still an independent committed copy.
- `tests/rust_cst_fegen/src/lib.rs`: now registers `Span` and `SourceText` classes (lines 19-20); `mod cst;` and `cst::register_classes(m)?;` retained.

---

## Test files

`tests/test_phase4_fegen_rust_backend.py`, `tests/test_clean_protocol_consumer_api.py`, `tests/test_cross_backend_label_equality.py` all still exist and still gate on `pytest.importorskip("fegen_rust_cst", ...)`. Design's test plan (step 2) still valid.

---

## Summary of design applicability

The design is applicable as written, with these specific corrections:

1. **Line numbers stale**: `src/lib.rs:5` → `:4`; `src/lib.rs:44` → `:34`; `tests/rust_cst_fegen/src/lib.rs:11` → `:15`; `lib.rs:15` → `:21`; `Makefile:54-55` → `:69-70`; `Makefile:49-50` → `:64-65`. All referenced code still exists at shifted lines.

2. **`TODO(slug)` code comment now exists** (contrary to `design.md:52`): `Makefile:108` contains `TODO(fegen-cst-rs-single-source)`. The Makefile line must be cleaned up (or restructured) when completing the TODO — it is not a no-op.

3. **Generated file size changed**: both files grew from 5080 → 6857 lines. The byte-identity claim, the drift risk, and the `include!` fix are all unaffected.

4. **`fltk-cst-core` dependency added** to `tests/rust_cst_fegen/Cargo.toml`. `src/cst_fegen.rs:1` now `use fltk_cst_core::Span;`. The test crate already has this dep (`:20`). No `include!` blocker.

5. **`make gencode`** (`Makefile:73-109`, added by `4c8f0ad`) regenerates both copies from the same grammar sequentially — the structural fix (eliminate one copy) is still the right approach and `gencode` does not eliminate the foot-gun.

All design decisions (use `include!`, relative path `../../../src/cst_fegen.rs`, leave `lib.rs` unchanged, no Cargo workspace) remain valid. The one-line replacement of `tests/rust_cst_fegen/src/cst.rs` is the correct fix. The Makefile `gencode` step for `tests/rust_cst_fegen/src/cst.rs` (`Makefile:108-109`) must also be removed or replaced to complete the TODO cleanly.
