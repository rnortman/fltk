# TODO Burndown: `rust-cst-shared-rlib`

Concise. Precise. Token-dense — no fluff, full information.

## Claim verification

The TODO claim has two factual assertions:

1. **"span is an opaque PyObject"** — TRUE.
   - `fltk/fegen/gsm2tree_rs.py:296`: generated node structs declare `span: PyObject,`.
   - `fltk/fegen/gsm2tree_rs.py:331-342`: `_new_method` stores span as `PyObject`; sentinel
     obtained at runtime via `py.import("fltk._native")?.getattr("UnknownSpan")?.unbind()`.
   - `fltk/fegen/gsm2tree_rs.py:551`: equality check uses `.bind(py).eq(...)` — pure Python
     protocol; no Rust-typed `Span` is involved.
   - `src/lib.rs:18`: `pub(crate) static UNKNOWN_SPAN: GILOnceCell<PyObject>` — even the
     sentinel stored in FLTK's own crate is `PyObject`, not the typed `Span`.

2. **"no Rust-level linkage between the user's crate and FLTK's crate is needed"** — TRUE.
   - `Cargo.toml:8`: `crate-type = ["cdylib"]` — cdylib only; no rlib output.
   - Generated extensions fetch `fltk._native.UnknownSpan` via Python import at runtime
     (`gsm2tree_rs.py:337`), not by linking `crate::UNKNOWN_SPAN` at the Rust level.
   - `src/lib.rs:10-15`: comment confirms `crate::UNKNOWN_SPAN` is no longer read by
     generated code; retained only for backward compat with any external code that may hold a
     reference.
   - `src/span.rs:63-69`: `Span` is a `#[pyclass(frozen, eq, hash)]` with typed Rust fields
     (`start: i64`, `end: i64`, `source: Option<Arc<SourceInner>>`), but this type is never
     exposed to generated extension crates at the Rust type level — only as a Python object.

## Trigger condition

The TODO self-describes its trigger: "Revisit when user extensions need to link Rust-level
shared types." No such need exists today:

- No generated extension code references the Rust `Span` type; all span access is through
  the PyO3 `PyObject` interface.
- `fltk-cst-common` rlib does not exist; no Cargo workspace is in use (`Cargo.toml:8` is
  `cdylib` only).
- There are no in-tree user grammar extensions that link against `fltk._native` at the Rust
  level.

## Classification

**Speculative future-revisit with no current trigger.** The TODO is correctly placed at
`fltk/fegen/gsm2tree_rs.py:119-121` (the `_preamble` method) and at `src/lib.rs:16-17`. Both
placements are accurate to the code state. The TODO is not actionable now; it becomes
actionable only if/when a user extension requires a Rust-typed `Span` (or other shared Rust
type) at link time rather than through the Python object protocol.

## Open factual questions

None. The code state fully matches the TODO's stated rationale and deferral condition.
