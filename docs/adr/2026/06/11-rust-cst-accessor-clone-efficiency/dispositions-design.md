# Dispositions: design review round 1 — rust-cst-accessor-clone-efficiency

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Notes reviewed: `notes-design-design-reviewer.md` (1 finding).

design-1:
- Disposition: Fixed
- Action: Reworded the "Clippy gate" bullet in design.md "Edge cases / failure modes". Verified the finding against `Makefile:51-54` (`cargo-clippy`: workspace + `tests/rust_cst_fegen` + `tests/rust_parser_fixture`), `Makefile:65-71` (`cargo-clippy-no-python`: adds no other crates), `Cargo.toml:2` (workspace members: root, fltk-cst-core, fltk-cst-spike, fltk-parser-core), and `Makefile:106` (`tests/rust_cst_fixture` built only via `maturin develop`). The bullet now states the exact clippy coverage, notes `tests/rust_cst_fixture` is compile-checked only via maturin/pytest, and keeps the mitigation argument (templates are label-agnostic and identical across grammars, so any lint surfaces in the clippy-gated outputs).
- Severity assessment: Documentation inaccuracy only; no design-shape change. Risk was an implementer believing a clippy pass proves `tests/rust_cst_fixture/src/cst.rs` lint-clean when no such gate exists.
