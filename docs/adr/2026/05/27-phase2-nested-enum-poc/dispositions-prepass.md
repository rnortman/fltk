# Dispositions: Prepass Review — Phase 2 Nested Enum PoC

## slop-1

- Disposition: Fixed
- Action: Remove section-header comments `// Generic methods`, `// Per-label methods for NAME`, `// Per-label methods for ITEM`, `// Per-label methods for NO_WS`, `// Per-label methods for WS_ALLOWED`, `// Per-label methods for WS_REQUIRED`, and `// Dunder methods` from `src/cst_poc.rs` (lines 93, 131, 269, 307, 381, 455, 529, 603). The method names are self-evident; these comments narrate structure rather than convey behavior or intent.
- Severity assessment: Minor noise. Accumulates as a signal of LLM-generated scaffolding; does not affect correctness.

---

## slop-2

- Disposition: Fixed
- Action: Replace `// Phase 2 PoC: CST node types` at `src/lib.rs:20` with `// CST node types` — describes what the block registers without embedding a task-phase reference.
- Severity assessment: The phase reference becomes misleading once the code is no longer a PoC. No correctness impact.

---

## slop-3

- Disposition: TODO(rust-cst-macro)
- Action: Add `// TODO(rust-cst-macro): per-node boilerplate (append/extend/children/child/maybe per label, __eq__, __hash__, __repr__, new, Label classattr) should be extracted into a proc-macro or generic helper before Phase 3 code generation targets this pattern.` at top of `src/cst_poc.rs` (after the `use` imports, before the first struct). Add matching entry to `TODO.md`.
- Severity assessment: The duplication (two structurally identical node types, ~500 of 629 lines repeated) is intentional for a PoC but must not carry forward to generated code. Without a TODO marking the abstraction point, a future reader (or code generator author) has no signal that this pattern requires extraction. The PoC ADR context doesn't substitute for an in-code marker.
