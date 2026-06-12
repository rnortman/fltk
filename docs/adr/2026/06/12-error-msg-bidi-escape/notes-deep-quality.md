Style: concise, precise, complete, unambiguous. No padding, no preamble. Audience: smart LLM/human.

Commit reviewed: 65279b7

---

## quality-1

**File:line:** `crates/fltk-parser-core/src/errors.rs:314-340`

**Issue: copy-paste unit tests for `escape_control_chars` left in `errors.rs` after the canonical tests moved to `escape.rs`.**

`escape_control_chars_table` and `escape_control_chars_empty` in `errors.rs` (lines 314–340) are byte-identical to the same-named tests in `crates/fltk-cst-core/src/escape.rs:92–118`. The design doc states "Rust unit tests move with the implementation to `escape.rs`; `errors.rs` keeps its `format_error_message`-level tests (which exercise the re-export)." The implementation was moved; the unit tests were not deleted from `errors.rs`. The `format_error_message_no_raw_extended_set_in_output` and the new bidi golden/alignment tests were correctly added; the plain escape unit tests should have been deleted.

**Consequence:** Every future change to the escape spec requires updating three locations instead of two (escape.rs tests, errors.rs tests, Python tests). The purpose of moving the implementation was to eliminate intra-Rust duplication; the duplicated tests partially undo that. A future editor adding a new escape class to `escape.rs` tests is likely to miss `errors.rs`, creating silent divergence in the very test suite meant to catch spec drift.

**Fix:** Delete `fn escape_control_chars_table` and `fn escape_control_chars_empty` from `crates/fltk-parser-core/src/errors.rs`. The section comment `// ── escape_control_chars` (line 312) should be removed with them. The re-export is still exercised by the `format_error_message_*` tests that call `escape_control_chars` indirectly.

---

## quality-2

**File:line:** `crates/fltk-cst-core/src/lib.rs:4` and `crates/fltk-cst-core/src/escape.rs:64`

**Issue: `escape_control_chars` is now part of `fltk-cst-core`'s public API via `pub mod escape` without being in the stated public surface, and `fltk_cst_core::escape::escape_control_chars` is accessible to any downstream consumer of `fltk-cst-core`.**

`lib.rs` declares `pub mod escape;` (not `pub(crate)`), and `escape_control_chars` within is `pub`. This means `fltk_cst_core::escape::escape_control_chars` is a new public API path that did not exist before. The design only stated that the _parser-core_ re-export path is preserved; it did not intend to publish a second path via cst-core. Downstream consumers of `fltk-cst-core` directly (i.e., generated code that imports from cst-core but not parser-core) can now call `escape_control_chars` without going through `fltk-parser-core`, which is fine for now but establishes an unintended dependency surface. More concretely: since `cross_cdylib.rs` calls `crate::escape::escape_control_chars`, the `python`-feature-gated build requires `escape.rs` to compile without pyo3, which it does — but the `pub mod escape` is unconditionally exposed even when the `python` feature is off, making `escape_control_chars` a public API of the core CST library even for pure-Rust consumers who have no connection to parser errors.

**Consequence:** Future refactors of the escape spec that want to break or rename the function must account for two published Rust paths (`fltk_parser_core::escape_control_chars` and `fltk_cst_core::escape::escape_control_chars`) rather than one. This is a low-cost mistake now but increases the "preserved path" burden at the next API evolution point.

**Fix:** Change `pub mod escape;` to `pub(crate) mod escape;` in `crates/fltk-cst-core/src/lib.rs`. The `cross_cdylib.rs` import `use crate::escape::escape_control_chars;` resolves within the crate regardless of visibility. The `errors.rs` re-export `pub use fltk_cst_core::escape::escape_control_chars;` in parser-core still compiles because `pub(crate)` controls external visibility, not intra-crate access — but wait: `fltk-parser-core` is a _different_ crate, so `pub(crate)` would break the re-export. The correct fix is `pub(super)` is also wrong here. The actual fix is to make the function `pub` but the module `pub(crate)`, which makes the function reachable from parser-core via `fltk_cst_core::escape::escape_control_chars` (the `pub use` in errors.rs re-exports through the crate boundary — this requires the module and item to be `pub`). So the correct, minimal fix is: keep `pub mod escape` but do not add `escape_control_chars` to `fltk-cst-core`'s documented public API (no `pub use escape::escape_control_chars` in lib.rs), which is already the current state — the item is reachable but only via the `escape::` path, not promoted to the crate root. Document that `fltk_cst_core::escape` is an implementation-sharing module, not a public API. Alternatively, if downstream consumers should never call this directly: make the module `pub(crate)`, move the re-export helper into a bridge module, or restructure so parser-core owns the function and cst-core calls into it — but that would reverse the dependency direction. The pragmatic fix is a `#[doc(hidden)]` on `pub mod escape` in lib.rs to mark it as non-public-API without breaking the inter-crate `pub use`.
