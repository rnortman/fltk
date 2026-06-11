# Request: split generated Rust-backend Python bindings into separate cst and parser modules

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Redesign/refactor of the generated pyo3 module layout. Reframed from TODO.md slug `parser-bindings-name-collision` per user decision.

**USER DIRECTION (verbatim, binding):** "Reframe: The core problem here is that we shoved everything in one module. That is a design mistake. We should mimic the Python backend: separate parser and cst modules. Redesign/refactor and this problem goes away."

The original TODO's reserved-name-check fix is superseded by this reframe; do not implement the check as the primary fix (a small residual check may still be needed — see below).

## Background

Currently one pyo3 module receives everything: `Span`, `SourceText`, `NodeKind`, one label enum + one node class per rule, `ApplyResult`, `Parser` — registration pattern at `tests/rust_cst_fegen/src/lib.rs:17-23` and `src/lib.rs:20-21`; emitters: `gsm2parser_rs.py:813-923` (`_gen_python_bindings` → `register_classes`), `gsm2tree_rs.py:1517-1531` (`cst::register_classes`). pyo3 `add_class` → `setattr` overwrites silently; a rule named `parser`/`apply_result` makes its CST class (or the fixed class) unreachable, no error anywhere (validated: no Rust compile error — duplicates live in different Rust modules). The Python backend is immune because it emits separate `fltk_cst.py` / `fltk_parser.py` modules.

Additional validated facts (see `exploration.md` in this dir, plus follow-up session findings):
- **Span/SourceText module-local registrations in generated consumer modules are near-vestigial.** `span_to_pyobject` (`crates/fltk-cst-core/src/cross_cdylib.rs:208-237`) routes span construction through the canonical `fltk._native.Span` unless the current cdylib IS `fltk._native`; `extract_span` (`cross_cdylib.rs:256-268`) accepts only the canonical type. The module-local `Span` class registered by a consumer module is a *different* Python type whose instances are (on main paths) never created — `isinstance(node.span, consumer_module.Span)` is `False` for spans the module itself returns. Likely correct move: DROP `add_class::<Span/SourceText>()` from generated consumer modules and document `fltk._native` as the import location. Verify first that no test or doc relies on the module-local attributes. `fltk._native` itself (canonical home, `src/lib.rs`) keeps its registrations.
- **Residual collisions the split does NOT fix:** `NodeKind` is registered in the same cst module as per-rule classes (`gsm2tree_rs.py:1517-1531`, NodeKind first) — a rule named `node_kind` still silently clobbers it. Design must address: separate namespace for NodeKind, or a minimal reserved-name check (precedent: `_RESERVED_LABELS`, `gsm2tree_rs.py:24-26`, raising `ValueError` in `RustCstGenerator.__init__`).
- pyo3 submodule mechanics: a single cdylib can register submodules, but extension submodules have Python-import-system caveats (`sys.modules` registration needed for `from x.y import z` to work). Design must settle the exact module topology (true submodules vs. sibling attribute-modules vs. other) and how the generated lib.rs template changes.

## Fix shape

Mimic the Python backend's separation: CST node classes (+ label enums + NodeKind) importable as one module; `Parser`/`ApplyResult` as another. Exact topology, naming, and `register_classes` signatures are design questions. Drop vestigial Span/SourceText registrations from generated consumer modules if verification confirms nothing depends on them.

## Constraints / non-goals

- **CLAUDE.md compat rule:** downstream import-statement updates are explicitly permitted; type-annotation or call-site churn is NOT. Class names themselves must not change.
- The self-hosted `fltk._native` module's assembly (`src/lib.rs`) is also affected; keep it canonical for Span/SourceText.
- `rust-naming-shared` (`docs/adr/2026/06/11-rust-naming-shared/`) is sequenced after/with this work per user decision — coordinate but keep commits separable.
- Non-goal: any change to the Python backend.

## Verification expectations

- New test: a grammar with rules named `parser` and `apply_result` generates, compiles, and both the CST classes and the parser are reachable.
- Decision + test for `node_kind` residual (rejection or namespace fix).
- All existing tests pass with updated imports; parity tests unaffected.
- Regenerate fixtures; `make fix`; `uv run pytest` + `cargo test` clean.
