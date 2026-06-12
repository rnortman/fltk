# Implementation log: rust-cst-debug-depth

Style: concise, precise, complete, unambiguous. No padding, no preamble.

---

## Increment 1 — Shared::strong_count + manual Debug impl in generator (commit 41a0316)

- `crates/fltk-cst-core/src/shared.rs:78-88`: added `Shared::strong_count()` returning `Arc::strong_count`; additive, used by Drop impl in next increment.
- `fltk/fegen/gsm2tree_rs.py:284`: added `use std::fmt;` to `_preamble()`.
- `fltk/fegen/gsm2tree_rs.py:662-710`: deleted `TODO(rust-cst-debug-depth)` comment; changed `#[derive(Clone, Debug)]` to `#[derive(Clone)]`; appended manual `impl fmt::Debug` emitting span + child count (non-recursive).
- `TODO.md`: removed `rust-cst-debug-depth` entry.
- Regenerated all 6 outputs: `src/cst_generated.rs`, `src/cst_fegen.rs`, `crates/fltk-cst-spike/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_parser_fixture/src/cst.rs`, `tests/rust_parser_fixture/src/collision_cst.rs`.
- `crates/fltk-cst-spike/src/spike_tests.rs:365-399`: upgraded smoke test from discard-only to content assertions — node output contains "span" and "<0 child(ren)>"; child-enum output for `ItemsChild::Identifier` contains "Identifier" and "child(ren)".
- All checks passed: `make check` (lint, typecheck, test, cargo-check, cargo-clippy, cargo-test, cargo-test-no-python, cargo-clippy-no-python, check-no-pyo3).

## Increment 2 — iterative Drop impl in generator + tests 1-5 (commit 06eb95f)

- `fltk/fegen/gsm2tree_rs.py:259-291`: added `_child_class_union()` computing the set of node classes that appear as node-typed children in any child enum; drives variant selection for `_drop_block`.
- `fltk/fegen/gsm2tree_rs.py:293-317`: updated `generate()` to pre-compute `child_union`, pass it to `_child_enum_block`, and call new `_drop_block()` after the per-rule loop.
- `fltk/fegen/gsm2tree_rs.py:540-558` (in `_child_enum_block`): emit `into_drop_item` on child enums when `class_name in child_union` OR `child_classes` non-empty. Span-only union members (Num, Name, Trivia) get a method returning `None` for all variants because `drain_into` calls it on their children.
- `fltk/fegen/gsm2tree_rs.py:721-742` (in `_node_block`): emit `impl Drop` with worklist-based teardown when `child_classes` non-empty; span-only nodes get no Drop impl (no recursion possible, no E0509 restriction).
- `fltk/fegen/gsm2tree_rs.py` (new `_drop_block`): emit private `DropWorklistItem` enum + `drain_into` with one variant/arm per child-class-union member; skipped entirely when union is empty.
- Regenerated 7 outputs: `src/cst_generated.rs`, `src/cst_fegen.rs`, `crates/fltk-cst-spike/src/cst.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_parser_fixture/src/cst.rs`, `tests/rust_parser_fixture/src/collision_cst.rs`.
- `tests/rust_parser_fixture/src/native_tests.rs:8-166`: added `build_deep_expr_chain()` helper + tests 1-5: deep-tree Debug (non-recursive, bounded output), deep-tree Drop (iterative, completes), shared-subtree survival (`strong_count > 1` prevents steal), `Shared::strong_count` unit test (via test 4 in native_tests.rs), parser-produced deep-tree (100 000-level left-recursive chain via actual parse).
- `crates/fltk-cst-core/src/shared.rs:119-130`: added `#[cfg(test)]` module with `test_strong_count_new_clone_drop` (test 4 in core).
- All checks passed: `make check`.
