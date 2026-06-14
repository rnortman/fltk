# User decisions on design open questions

These are the user's authoritative resolutions of the design's open questions.
Fold them into design.md, removing the open-question hedges and stating the chosen
path as decided.

1. OQ-1 (rename relocated fegen CST module): **No rename yet.** Keep the existing
   import name.
2. OQ-2 (promote fegen parser/CST crate out of tests/): **Yes — move it out of
   tests/ into a real `crates/` crate.**
3. OQ-3 (.pyi stub location for the relocated module): **Option A** — keep
   codegenning the CST `.pyi`, route its output to a stub package inside the `fltk`
   tree (`fltk/_stubs/fegen_rust_cst/cst.pyi`) and add the matching
   `stubPath`/`extraPaths` entry to `[tool.pyright]`.
