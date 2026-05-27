# Efficiency review — Phase 3 Rust CST generator

Commit reviewed: af7dc6e (base 6f82c48)
Scope: gsm2tree_rs.py (dev-time generator), src/cst_generated.rs / src/cst_fegen.rs (committed generated output, runs per CST-node access), src/lib.rs (per-process module init), test files.

## efficiency-1: generated label accessors do a Python rich-comparison per child element

File: emitted by `gsm2tree_rs.py:280-356` (`children_{label}`, `child_{label}`, `maybe_{label}`); visible in `src/cst_generated.rs` (e.g. lines 119-187, 336-668) and `src/cst_fegen.rs`.

Problem: every label accessor iterates the full `children` list and calls `tup.get_item(0)?.eq(&label_obj)?` — a Python-level rich-comparison (`PyObject::eq`) — on each element. `children_{label}` always scans the entire list (no early exit even when it conceptually could not). The label is a `frozen` enum variant; identity comparison would suffice but the code routes through `__eq__`. Each element also pays two `get_item` calls plus a `downcast::<PyTuple>`.

Consequence: cost is O(children) Python comparisons per accessor call. Any consumer that walks a CST (compiler pass, visitor, pretty-printer) calls these accessors per node; on a large source file this is the dominant per-node cost and sets the scale ceiling. The label set per rule is fixed and small, so the comparison is pure overhead vs. a discriminant check.

Important caveat: this is a faithful byte-for-byte reproduction of the hand-written Phase 2 code (`6f82c48:src/cst_poc.rs:147-210`), which the design (`design.md:217`, "follows the Phase 2 template exactly") and requirement AC-6 (pass `test_rust_cst_poc.py` unmodified) mandate. The pattern is inherited, not introduced by this diff. Flagging as the structural scale ceiling for the generated output, not as a regression.

Direction (future, out of this phase's scope): the label is a known frozen enum; replace the per-element `.eq()` with `is`-identity (`PyAny::is`) or compare against the interned variant object once, and/or store children grouped by label so accessors are O(matches) not O(all children). Either keeps the public API identical. Defer until a profiling need exists; not actionable inside the "match Phase 2 exactly" constraint.

## efficiency-2: generator recomputes per-rule model/class_name/labels in register_classes pass

File: `fltk/fegen/gsm2tree_rs.py:50-55` (generate loop) and `:404-411` (`_register_classes_fn`).

Problem: `generate()` loops over `self.grammar.rules` computing `model = rule_models[rule.name]`, `class_name`, `labels = sorted(...)`. `_register_classes_fn()` repeats the identical three lookups + `sorted()` for every rule. The body computations (`_label_enum_block`, `_node_block`, `_per_label_methods`) build large string lists for every label, every call.

Consequence: dev-time generator invocation only. Generated `.rs` files are committed artifacts (no build-time generation hook — confirmed: no Makefile/pyproject/cargo reference invokes the generator). Cost is a single one-off run per regeneration; negligible. Recording for completeness, not worth fixing.

Direction (only if generator ever moves on-path): compute `(class_name, labels)` per rule once into a list, consume in both the emit loop and register_classes.

## src/lib.rs module init

`_native` init (lines 13-47) does class registration, submodule creation, and a `sys.modules` insertion. One-time per process at `import fltk._native`. No redundant work; the `sys.modules` set and submodule are each done once and are required for the submodule import path. No finding.

## No other findings

No N+1, no missed concurrency (generation is inherently sequential string assembly), no unbounded-growth/memory leak, no recurring no-op state updates, no TOCTOU existence checks, no over-broad reads (fegen.fltkg read once in a module-scoped test fixture).
