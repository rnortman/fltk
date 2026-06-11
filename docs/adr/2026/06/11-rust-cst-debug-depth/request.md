# Request: non-recursive Debug for generated CST node structs

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

**Type:** Hardening fix — generator template edit in `fltk/fegen/gsm2tree_rs.py` + regeneration.

**Origin:** TODO.md slug `rust-cst-debug-depth`, user-approved triage (`docs/adr/2026/06/11-todo-burndown/triage.md` item 8, USER DECISION: Do).

## Background

`gsm2tree_rs.py:640` emits `#[derive(Clone, Debug)]` on every generated node data struct (TODO comment immediately above). `Shared<T>`'s `Debug` (`crates/fltk-cst-core/src/shared.rs:98-102`) acquires the read lock and delegates to `T::Debug`, so the derived chain `Shared<A> → A → Vec → ChildEnum → Shared<B> → …` recurses through the whole tree with no depth bound. Tree depth is attacker-controlled for parsers over untrusted input; `{:?}` on a deep tree = stack exhaustion = uncatchable SIGSEGV process abort. `{:?}` is ubiquitous (`assert_eq!` failure output, `dbg!`, logging). The cycle case is design-accepted (`shared.rs:36-40`); this is the acyclic unbounded-depth case, introduced by Phase 2 of the idiomatic-CST work.

Validation facts (see `exploration.md` in this dir):
- The parse-depth-limit work (`docs/adr/2026/06/11-parse-depth-limit/`) bounds parsed-tree depth but does NOT make this safe: the limit is configurable, and Debug recursion consumes fresh stack at print time.
- The Python-facing `__repr__` (`_repr_method`, `gsm2tree_rs.py:1500-1511`) is the model: span start/end + children COUNT, no recursion. It is unaffected by this change.
- Child enums also carry `derive(Clone, Debug)` (`_child_enum_block`); the enum's Debug delegates to `Shared<T>` for node variants.
- Only in-tree `{:?}` users on nodes: three smoke tests in `crates/fltk-cst-spike/src/spike_tests.rs:364-378`; they must be updated.
- Rust convention treats `Debug` output as unstable — format change is not an API break. Per CLAUDE.md, note it for out-of-tree consumers anyway.

## Fix shape

Replace `derive(Debug)` on node data structs with an emitted manual `impl fmt::Debug` that prints span + child count (mirroring `_repr_method`'s content), breaking recursion at the node level. Design decides the exact rendering and whether child enums keep `derive(Debug)` (safe once node Debug is non-recursive, since the chain breaks at the node) or get a variant-name-only impl. Prefer breaking recursion at the node struct rather than changing the generic `Shared<T>` impl in `fltk-cst-core` (which would affect all `Shared` users).

Alternative shapes (depth-capped recursive Debug, i.e. recurse to depth N then elide) are acceptable if the design argues for them; the triage-approved default is the simple non-recursive span+count form.

## Constraints / non-goals

- `__repr__` (Python side) unchanged.
- `Clone` derive unchanged.
- No change to `fltk-cst-core`'s `Shared<T>` Debug unless the design shows it is strictly better and harmless to other users.
- Remove the TODO comment at `gsm2tree_rs.py:638-640` and the TODO.md entry.

## Verification expectations

- Test: programmatically build (or parse, if depth-limit work landed first) a deep tree and `format!("{:?}")` it — completes without overflow, bounded output size.
- Update `spike_tests.rs:364-378` smoke tests for the new output.
- Regenerate all outputs; `make fix`; `uv run pytest` + `cargo test` clean.
