# User direction (post-checkpoint)

1. correctness-1 (Rust parse path regressed because §2.2's strict native-Span setter landed before §2.5's parser migration): this just means the work is unfinished. The fix is to FINISH — implement §2.5. Do not paper over with permanent xfail.

2. scope-5 / §2.1↔§2.8 wording: CONFIRMED there is no out-of-tree-consumer trap. `fltk-cst-core` provides only the pyo3-runtime-free RUNTIME types (Span, SourceText) that generated code depends on via `use fltk_cst_core::Span;`. Generated node structs live wherever RS_OUT points: FLTK's own grammars -> src/cst_*.rs; out-of-tree consumers -> their own crate (depending on fltk-cst-core as a library). The `tests/rust_cst_fixture/` crate is the existence proof. The §2.1 phrasing "node structs live in fltk-cst-core" is imprecise/misleading and must be corrected. Forcing out-of-tree consumers to generate inside our crate would violate CLAUDE.md and is NOT the design.
   - Fix §2.1 and §2.8 so they are consistent: generated structs are emitted to the consumer-chosen RS_OUT path and depend only on `fltk-cst-core`; FLTK's own in-tree generated files stay where the build wires them.
   - Retarget the §4 pure-Rust (no-Python, no-GIL) acceptance test at the fixture crate (or an equivalent standalone pure-Rust crate) rather than at FLTK's extension-compiled cst_*.rs.

3. The `backend-with-source-signature` change is to be pulled into THIS work as a prerequisite and implemented here (it already has a design at docs/adr/2026/06/06-backend-with-source-signature/). Reflect that §2.5 depends on it and it lands first.
