# Dispositions — prepass review (slop + scope)

## slop-1

- Disposition: Fixed
- Action: Deleted the `fltk-pyo3-cdylib-smoke` section from `TODO.md` (TODO.md lines 13–17). Done items must be removed; strikethrough closure notes are not the project convention.
- Severity assessment: Cosmetic noise in the master TODO list; a human maintainer must sift past it to find real open work. Low severity but clear-cut fix.

---

## slop-2

- Disposition: Fixed
- Action: Added validation guard in `LibSpec.validate()` (`fltk/fegen/gsm2lib_rs.py`, after line 83): if `unknown_span_static=True` and `register_span_types=False`, raises `ValueError` with a message naming the dependency. Added covering test `test_unknown_span_static_without_register_span_types_raises_value_error` in `fltk/fegen/test_gsm2lib_rs.py`.
- Severity assessment: Without the guard a caller can construct a `LibSpec` that passes validation but generates Rust that does not compile (`Span` not in scope). The failure is silent until the Bazel/cargo build errors with a cryptic rustc message. Medium severity.

---

## slop-3

- Disposition: Fixed (partial) / Won't-Do (pub mod parser part)
- Action:
  - `#[cfg(test)]` added to `mod native_parser_tests;` declaration in `crates/fegen-rust/src/lib.rs` line 16. This is correct: the declaration without the guard compiled an effectively-empty module in release builds, which is nonstandard. Fixed.
  - `pub mod parser` **not** changed to `mod parser`. See rationale below.
- Severity assessment: The `mod native_parser_tests` missing `#[cfg(test)]` was nonstandard; low severity (the inner `#[cfg(test)] mod tests { … }` block already excluded the test code from release builds, so no actual test code leaked). The `pub mod parser` issue is not a bug.
- Rationale (Won't-Do for pub mod parser): Removing `pub` from `mod parser;` breaks the `--no-default-features` clippy lane. In that mode the `#[pymodule]` fn body is behind `#[cfg(feature = "python")]` and is not compiled, so the `parser` module's usage of CST types is the only thing keeping those types "reachable." With `pub mod parser` the module is part of the crate's public API surface, anchoring the CST types as non-dead-code; with `mod parser` clippy fires `-D dead-code` errors on every CST struct, enum, and method in `src/cst.rs`. Verified by toggling: `pub mod parser` → clean clippy; `mod parser` → dozens of dead-code errors. The `pub` is therefore load-bearing for the no-python lane, not an accidental exposure. For a cdylib the distinction is irrelevant to downstream Rust consumers anyway — cdylibs do not expose a Rust API surface.

---

## scope (notes-prepass-scope.md)

- Disposition: Won't-Do (no finding to resolve; scope reviewer found no issues)
- Action: No change. The scope notes confirmed the clockwork changes are minimal, correct, and within §2.7's claimed scope. No omissions were identified.
- Severity assessment: N/A — no defect found.
