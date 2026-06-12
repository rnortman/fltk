# Security review — rust-cst-accessor-clone-efficiency (74adcf8..1eb2580)

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

No findings.

Checked, all clean:

- **Lock discipline (deadlock/DoS surface).** All new under-guard code in `fltk/fegen/gsm2tree_rs.py` (`_generic_child`, `children_<label>`, `child_<label>`, `maybe_<label>`) and in the regenerated outputs (verified against `src/cst_generated.rs`) is pure Rust: `len`, `children[0]` indexing, label-enum `PartialEq`, `Child::clone` (Arc refcount bump / `Span` copy). `format!`, `PyValueError::new_err`, `to_pyobject`, `into_pyobject` all execute after the guard drops. No GIL-acquisition or Python callback under a node lock, so no new lock-order deadlock path. Clones collected under the guard are dropped outside it; `Child` drop is pure Rust.
- **Bounds/panic safety.** `guard.children[0]` gated by `n == 1`. The `.expect` in `child_<label>` is unreachable (count and first computed atomically under one guard); even if hit, pyo3 maps pymethod panics to `PanicException` — no memory unsafety.
- **Error-message content.** Only `usize` counts interpolated; `format!` strings are compile-time literals. No untrusted-string interpolation, no information leak beyond child counts already exposed via `len(node.children)`.
- **Trust boundary.** Untrusted parse input influences only child counts and labels; both reach nothing more dangerous than an integer in a `ValueError` message. No new path.
- **Guard hold time.** Read guard now spans O(children) label compares instead of an O(children) full-Vec clone — equal or shorter hold; no new writer-starvation exposure.
- **Pre-existing, unchanged in kind.** `{label}` / `{label_enum_name}::{rust_variant}` interpolation of grammar-derived identifiers into generated Rust source and error literals predates this diff; grammar files are developer-controlled generator input, and this change adds no new interpolation sites.

Commit reviewed: 1eb2580.
