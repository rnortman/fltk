## Increment 2 — generator changes: EqWorklistItem, eq_shallow_enqueue, iterative PartialEq (commit 44458c5)

- `fltk/fegen/gsm2tree_rs.py`: added `_eq_block(child_union)` method (emits `EqWorklistItem` enum + `compare` impl, one pair-variant per child-union class, module-private, mirroring `_drop_block`); added `_emit_eq_arm` helper; added `eq_shallow_enqueue` emission in `_child_enum_block` (under same `needs_drop_item` condition as `into_drop_item`; `_worklist` for span-only union members); replaced recursive `PartialEq` in `_node_block` with iterative driver for classes with node-typed children; span-only classes keep one-liner with depth-safe comment; wired `_eq_block` call in `generate()` next to `_drop_block`; updated doc comment ("Equality is iterative: bounded stack at any depth.").
- `crates/fltk-cst-core/src/shared.rs`: removed `TODO(rust-cst-eq-depth)` comment; updated `# Equality` doc section noting the iterative node-struct T::eq and smaller lock footprint; updated `# Reference cycles` to note worklist-growth vs. stack-overflow distinction.
- `TODO.md`: removed `rust-cst-eq-depth` entry.
- All generated outputs regenerated via `make gencode` + `make fix`: `src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_parser_fixture/src/cst.rs`, `tests/rust_parser_fixture/src/collision_cst.rs`, `crates/fltk-cst-spike/src/cst.rs`, plus Python-side outputs.
- All 6 EQ tests pass (EQ-1/2 previously aborting, EQ-3/4/6 already passing, EQ-5 previously aborting); `make check` clean.

## Increment 1 — failing depth tests in native_tests.rs (commit 005134b)

- `tests/rust_parser_fixture/src/native_tests.rs:14-34`: refactored `build_deep_expr_chain()` into `build_deep_expr_chain_with_leaf_span(leaf_span: Span)` + `build_deep_expr_chain()` wrapper calling it with `Span::unknown()`. Existing debug/drop depth tests untouched.
- `native_tests.rs:197-314` (approx): added 6 new tests — EQ-1 (`test_deep_tree_eq_iterative_equal`), EQ-2 (`test_deep_tree_eq_iterative_unequal`), EQ-3 (`test_deep_shared_subtree_eq_ptr_eq_short_circuit`), EQ-4 (`test_multi_child_eq_worklist`), EQ-5 (`test_parser_produced_deep_tree_eq`), EQ-6 (`test_eq_variant_mismatch_unequal`).
- Pre-fix status: EQ-1/2/5 abort with stack overflow; EQ-3/4/6 pass already (shallow or ptr_eq path sufficient). EQ-1 abort confirmed empirically.
- Deviation: design §5 says "all six new tests must fail"; EQ-3, EQ-4, and EQ-6 pass pre-fix because they rely on paths that don't recurse deeply. This is correct behavior — they are regression tests verifying the semantics hold after the fix, not demonstrations of the bug.
