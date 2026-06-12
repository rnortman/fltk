# Efficiency review — rust-cst-debug-depth (deep)

Reviewed: 8c10cea..2f9b05e (HEAD 2f9b05e). Design: `design.md` (this dir).

Style note: concise, precise, complete, unambiguous; no padding. All docs in this workflow follow this style.

## efficiency-1: emitted `Drop` heap-allocates the worklist even when nothing is stolen — avoidable on the parser backtracking hot path

- **Where**: `fltk/fegen/gsm2tree_rs.py:753-775` (emitted `impl Drop` in `_node_block`); generated instances e.g. `tests/rust_parser_fixture/src/cst.rs:5580` (`Expr`), `src/cst_fegen.rs`, etc.
- **Problem**: the emitted `drop` eagerly collects all node-typed children into the worklist:
  ```rust
  let mut worklist: Vec<DropWorklistItem> = self.children.drain(..)
      .filter_map(|(_, child)| child.into_drop_item())
      .collect();
  ```
  `collect` heap-allocates as soon as one node-typed child exists — regardless of whether any child is sole-owned. In the common backtracking case the children are *not* stolen: e.g. `tests/rust_parser_fixture/src/parser.rs:497-516` (`parse_expr__alt0`) appends a memoized `Shared<Expr>` lhs, then drops the partial node whenever item1/item2 fails. The memo table holds a handle (`strong_count > 1`), so `drain_into` does nothing but decrement — yet the Vec was allocated, filled, popped, and freed. This fires on every failed alternative that had already appended a node-typed child, at every input position a left-recursive/multi-alt rule is tried, plus on every Python handle GC of such a node.
- **Consequence**: one malloc + free (plus item conversion churn) per discarded partial node during parsing — per-parse cost that scales with input length × failed-alternative density. Pre-change drop glue did zero allocations on this path. Design accepts "one worklist Vec allocation per externally-dropped subtree root" (`design.md` §Drop, Termination/complexity), but in a parse run *every discarded partial is such a root*, so the accepted constant multiplies into the hot loop.
- **Fix**: make the worklist lazy — allocate only when a steal actually yields grandchildren. Strictly fewer allocations, same O(nodes) bound, no other behavior change:
  ```rust
  fn drop(&mut self) {
      if self.children.is_empty() { return; }
      let mut worklist: Vec<DropWorklistItem> = Vec::new(); // no alloc until first steal pushes
      for (_, child) in self.children.drain(..) {
          if let Some(item) = child.into_drop_item() {
              item.drain_into(&mut worklist);
          }
      }
      while let Some(item) = worklist.pop() {
          item.drain_into(&mut worklist);
      }
  }
  ```
  With this shape the no-steal case (shared/memoized children) and the span-only case allocate nothing; deep owned chains allocate once, as today. One emitted-template change in `_node_block` + regen.

## efficiency-2: generator recomputes `_child_variants_for_rule` per rule (now 4 call sites) and does O(U) list-membership per rule

- **Where**: `fltk/fegen/gsm2tree_rs.py` — call sites at lines 268 (new union pre-pass in `_child_class_union`), 546, 697, 1183; membership test `class_name in child_union` (a `list`) at line ~593 in `_child_enum_block`.
- **Problem**: the diff adds a fourth full recomputation of `_child_variants_for_rule` per rule (the union pre-pass), and the per-rule `in child_union` scan is O(union size) on a list.
- **Consequence**: codegen-time only; negligible at current grammar sizes (tens of rules), grows as O(rules × model-walk) + O(rules × union) for large grammars. No runtime impact on generated code.
- **Fix**: memoize `_child_variants_for_rule` (`functools.lru_cache` on `rule_name` or a dict built once), and pass the union as a `set` (or also a `frozenset`) for membership. Optional given current scale.

No other findings. Checked: Debug impl (non-recursive, no locks on own fields, `format_args!` is zero-alloc); `Shared::strong_count` (single atomic load); per-steal `write()` lock (uncontended single CAS per finally-freed node — dwarfed by the free itself, accepted in design); worklist peak memory (O(frontier) heap replacing O(depth) stack — inherent); `mem::take` (no alloc); empty-children `collect` (no alloc, as design claims); test runtimes (100k-node builds/parses are design-mandated depths); spike test assertions (bounded strings).
