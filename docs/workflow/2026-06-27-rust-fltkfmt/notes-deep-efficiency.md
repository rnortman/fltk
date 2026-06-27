# Deep efficiency review — rust-fltkfmt increments 1-3

Commit reviewed: 1b48755794ecca64a81f799fc91550904ea0970c (base 61fc5e89…)
Scope: increments 1-3 only (fegen Rust unparser generation + wiring, `fltk-fmt-cli`
crate with `fully_consumed`, `FmtArgs`). `run_main`, the `fltk_formatter_main!` macro,
and the `fltkfmt` binary land in later increments and are not in this diff.

## efficiency-1 (minor; pre-existing pattern, parity-bound)

- File: `crates/fegen-rust/src/unparser.rs:59-72` (generated), produced by
  `fltk/unparse/gsm2unparser_rs._gen_trivia_processing` /
  `_gen_has_preservable_trivia_method` / `_gen_count_newlines_in_trivia_method`.
- Problem: the non-trivia separator branch scans a trivia node's children twice in the
  common (no-comment) case: `_has_preservable_trivia(&trivia_node)` walks every child
  looking for a `LineComment`/`BlockComment` (the `if` condition), and when that is false
  the `else` calls `_count_newlines_in_trivia(&trivia_node)`, which walks the same children
  again to sum newlines. Plain-whitespace separators (the common case) therefore take two
  passes. A single loop could compute "has comment" and "newline count" together and then
  branch, halving the scan.
- Consequence: per-format CPU, scaling with token count × trivia size. In practice
  negligible: trivia between two tokens is small and bounded, `children()` is an O(1) slice
  borrow (`cst.rs:398`), so this is a small constant per separator, not a scaling ceiling.
- Why I am not pushing a fix: this is pre-existing generator logic (this diff only changed
  the clippy `match` → `if let` shape, not the two-pass structure), it mirrors the Python
  backend, and cross-backend behavioral/output parity is a hard project requirement. A
  merged single-pass would be output-identical but should be applied to **both** backends to
  preserve structural parity; given the negligible cost, leaving it as-is is reasonable.
  Recorded so the team can make an informed call, not as a blocker.

## Clean (no efficiency findings)

- `crates/fltk-fmt-cli/src/lib.rs` `fully_consumed`: `src.chars().skip(pos).all(is_whitespace)`
  re-decodes from the string start (char iteration can't random-access UTF-8), so it is
  O(n) over the file. This is invoked once per file by the (future) CLI, dwarfed by the
  parse + unparse of that same file, and the char-index semantics make a byte-offset
  shortcut incorrect. Not a hot path; no change warranted.
- `FmtArgs` (clap derive), the generator clippy fix, and the Cargo/Makefile/lib.rs wiring
  introduce no runtime work.
- The generated quantified-loop pattern (`while current_pos < node.children().len()` +
  per-attempt `acc.clone()`) is cheap: `children()` is an O(1) slice borrow and
  `DocAccumulator::clone` is two `Rc` refcount bumps (`accumulator.rs:56-59`). Pre-existing,
  unchanged by this diff.
