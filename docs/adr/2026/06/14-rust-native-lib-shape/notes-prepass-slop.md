# Prepass slop review — codegen-rust-lib-boilerplate + clockwork drop

Commits reviewed:
- fltk: 7200d9c..86082b5
- clockwork: 6ede250..ea34388

---

## slop-1

**File:** `TODO.md`

**Quote:**
```
+~~Done: `bootstrap_native` target added to `BUILD.bazel` using `bootstrap_rust_srcs` and no `lib_rs`, exercising the generated-lib.rs branch of `fltk_pyo3_cdylib` in FLTK CI.~~
+
+(Closed — wired in codegen-rust-lib-boilerplate.)
```

**What's wrong:** Strikethrough markdown in a TODO entry is an LLM tracking artifact. The TODO system protocol (per CLAUDE.md) says done items should be removed from TODO.md, not struck through with an explanatory closure note. This reads as the AI talking to itself about what it just finished rather than clean repo maintenance.

**Consequence:** Leaves noise in the master TODO list that a human maintainer must sift through; conflicts with the project's own stated convention that TODOs track concrete remaining work, not completed work.

**Fix:** Delete the `fltk-pyo3-cdylib-smoke` section entirely from TODO.md since it is closed.

---

## slop-2

**File:** `fltk/fegen/gsm2lib_rs.py`, line ~99 (in `LibSpec.validate`)

**Quote:**
```python
if not self.submodules and not self.register_span_types and not self.unknown_span_static:
    msg = "LibSpec.submodules must not be empty when no span types or UNKNOWN_SPAN are registered"
    raise ValueError(msg)
```

**What's wrong:** The validation condition silently permits a `LibSpec` with `unknown_span_static=True` but `register_span_types=False` (or vice versa). The generated output in this case would declare `UNKNOWN_SPAN` (which references `Span::unknown()`) without importing `use span::{SourceText, Span}`, or would import span types without ever initializing `UNKNOWN_SPAN`. There is no guard or comment acknowledging that these flags are intended to be used together.

**Consequence:** A caller can construct a `LibSpec(module_name="x", submodules=(), unknown_span_static=True, register_span_types=False)` that passes validation but generates Rust that won't compile (`Span` not in scope). The bug is invisible until the downstream Bazel build fails with a cryptic rustc error.

**Fix:** Add a validation check: if `unknown_span_static` is True, `register_span_types` must also be True (and document why in the error message). Or document explicitly that the flags are independent and the caller is responsible for consistency, but that would be a weaker fix.

---

## slop-3

**File:** `crates/fegen-rust/src/lib.rs`, lines 14–16

**Quote:**
```rust
mod cst;
pub mod parser;
mod native_parser_tests;
```

**What's wrong:** `native_parser_tests` is declared as a `mod` at the crate root without a `#[cfg(test)]` gate. This means the module is compiled into the release cdylib artifact, not just in test builds. The module file itself (`crates/fegen-rust/src/native_parser_tests.rs`) wraps its content in `#[cfg(test)] mod tests { … }`, so the functions are excluded — but the module declaration still compiles the file and processes the `use crate::parser::Parser;` path in the module scope unconditionally. The `pub mod parser;` is also `pub`, which exposes the parser module from the cdylib's public API surface unnecessarily.

**Consequence:** The `#[cfg(test)]` guard on the inner `mod tests` block does protect the test code from being emitted in release builds, but the outer `mod native_parser_tests;` declaration with no cfg guard is nonstandard and confusing — it looks like dead module scaffolding. The `pub mod parser;` exposes an internal generated module as public API of the shared library, which a downstream Rust consumer could link against unintentionally.

**Fix:** Add `#[cfg(test)]` to the `mod native_parser_tests;` declaration. Change `pub mod parser;` to `mod parser;` unless there is a specific reason the parser module needs to be `pub` from the cdylib root.

---

No further findings.
