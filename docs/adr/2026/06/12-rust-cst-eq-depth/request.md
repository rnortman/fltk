# Request: rust-cst-eq-depth — iterative PartialEq on generated Rust CST nodes

Style: concise, precise, no padding, no preamble. Self-contained; downstream agents see only this dir. Validated exploration: `exploration.md` (same dir) — adequate; skip the explore phase and proceed to requirements.

## Type of work

Bug fix (correctness/security hardening) in the Rust CST code generator, plus regeneration of in-tree generated fixtures.

## Background

`PartialEq` on generated Rust CST node structs recurses through `Shared<T>` children with no depth bound. Tree depth is attacker-controlled for parsers over untrusted input, so `==`/`assert_eq!` on a deep parser-produced tree exhausts the stack and aborts the process — uncatchable in Rust. Same root cause as the already-fixed Debug and Drop paths.

The recursion chain (all verified at HEAD 5d94733):
- Generator emits manual `impl PartialEq` comparing `self.span == other.span && self.children == other.children`: `fltk/fegen/gsm2tree_rs.py:798-803` (`_node_block`), with the `TODO(rust-cst-eq-depth)` comment at `gsm2tree_rs.py:790-797`.
- Child enum `PartialEq` compares `Shared<T>` variants: e.g. `tests/rust_parser_fixture/src/cst.rs:7165-7173` (`ExprChild`).
- `Shared<T>::PartialEq` at `crates/fltk-cst-core/src/shared.rs:93-109`: `ptr_eq` short-circuit, else `*self.read() == *other.read()` → delegates back to `T::eq`. No depth counter anywhere in the chain.

Prior-art fixes to mirror:
- Drop fix (the pattern to follow): `gsm2tree_rs.py:764-788` emits `impl Drop` draining children into a flat worklist; the per-grammar `DropWorklistItem` enum is emitted by `_drop_block` at `gsm2tree_rs.py:1934-1972`. Generated example: `crates/fltk-cst-spike/src/cst.rs:1066-1085`, enum at `cst.rs:3019-3047`.
- Debug fix: manual O(1) `impl Debug` at `gsm2tree_rs.py:748-755`.
- Existing depth tests to mirror: `tests/rust_parser_fixture/src/native_tests.rs` — `test_deep_tree_debug_non_recursive` (l.39), `test_deep_tree_drop_iterative` (l.59), deep-chain builder `build_deep_expr_chain()` (l.14), all at 100,000 depth.

## Fix shape (user-approved direction)

Emit an iterative `impl PartialEq` for generated node structs using an explicit worklist, following the `_drop_block` generator pattern.

**Load-bearing constraint surfaced by validation:** equality traverses TWO trees in lockstep. The worklist must hold *pairs* `(Shared<T>, Shared<T>)` — `DropWorklistItem` (single handles, mutating drain) cannot be reused as-is. A new pair-carrying worklist construct is needed. Unlike Drop, eq must not mutate either tree. The per-pair `ptr_eq` short-circuit (same allocation → equal without locking) should be preserved.

## Constraints / non-goals

- Equality *semantics* must be unchanged: same results as today (span + children, structural equality). Only the evaluation strategy changes. This is generated public API surface for out-of-tree consumers (see CLAUDE.md); no observable behavior change other than not crashing.
- `Shared<T>::PartialEq` in `crates/fltk-cst-core/src/shared.rs` may need adjustment as part of the design; keep `Shared<T>` generic and usable.
- Python backend out of scope: its `@dataclass __eq__` raises catchable `RecursionError` on deep trees — a known, milder, pre-existing asymmetry. Do not touch it.
- No other recursive-trait hazards exist (validated: Clone is shallow, Debug terminates O(1), no Hash/Ord/serde on node structs) — do not expand scope.
- Regenerated fixtures (`tests/rust_parser_fixture`, `tests/rust_cst_fegen`, `crates/fltk-cst-spike`, `src/cst_fegen.rs` etc.) follow the regen → `make fix` → commit flow.

## Verification expectations

- TDD per CLAUDE.md: failing tests first.
- New native tests mirroring the Debug/Drop depth tests: two structurally equal 100,000-deep chains compare `==` true without stack overflow; two unequal deep chains compare false; shared-subtree `ptr_eq` short-circuit still works. Use/extend `build_deep_expr_chain()`.
- Existing shallow eq tests keep passing (`tests/rust_cst_fixture/src/native_tests.rs:110,190`).
- Full suite: `uv run --group dev maturin develop && uv run pytest`; `make check` clean.
- On completion remove the TODO: `TODO.md` entry `rust-cst-eq-depth`, code comments at `gsm2tree_rs.py:790-793` and `shared.rs:93-97`.
