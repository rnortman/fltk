# Design: non-recursive Debug and Drop for generated CST node structs

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Requirements: `request.md` (this dir). Exploration: `exploration.md` (this dir).

Scope note: `request.md` covers Debug only. The Drop work (originally floated as a deferred `TODO(rust-cst-drop-depth)` in this design's round-1 open question) is folded into this design by user direction: fix both now, no new TODO.

## Root cause / context

Two unbounded recursions through the same ownership chain, both with attacker-controlled depth (tree depth is attacker-controlled for parsers over untrusted input); both end in stack exhaustion → uncatchable SIGSEGV process abort. The parse-depth-limit work does not eliminate either exposure: left-recursive seed-grow deepens the CST one level per `grow_seed` loop iteration at ~constant `apply` depth, so parser-produced tree depth scales with input length, not `max_depth` (`evaluation-drop-depth-reachability.md` §2 — supersedes the weaker `exploration.md` §5 argument, which wrongly bounded post-limit depth at ~`max_depth`).

**Debug.** `gsm2tree_rs.py:640` emits `#[derive(Clone, Debug)]` on every node data struct. The derived `Debug` formats `children: Vec<(label, ChildEnum)>`; node-typed enum variants hold `Shared<T>`, whose `Debug` (`crates/fltk-cst-core/src/shared.rs:98-102`) takes the read lock and delegates to `T::Debug`. Chain: `Shared<A> → A → Vec → ChildEnum → Shared<B> → …`, one set of stack frames per tree level. `{:?}` is ubiquitous (`assert_eq!`, `dbg!`, logging). Full validation in `exploration.md` §1-§5.

**Drop.** Dropping the last handle to a deep tree recurses through compiler-generated drop glue: `node → Vec<(label, ChildEnum)> → ChildEnum → Shared<T>` (Arc glue runs the inner drop when the count hits 0) `→ node → …`, again one frame set per level. This fires on *any* teardown — end of scope, Python handle GC, parser backtracking — so unlike Debug it cannot be avoided by "don't call `{:?}`". Pre-existing since Phase 1's `Shared` ownership model; surfaced while designing the deep-tree Debug test (the test's teardown would abort even after the Debug fix).

Out of scope (pre-existing, distinct, not user-authorized here): deep `PartialEq` recursion through the same chain.

## Proposed approach

### Debug: manual non-recursive impl (per request's preferred shape)

Replace `derive(Debug)` on node data structs with an emitted manual `impl fmt::Debug` printing span + child count. No change to `Shared<T>::Debug`. Child enums keep `derive(Debug)`: once node `Debug` is non-recursive, the enum's derived chain (`ChildEnum → Shared<T> → node manual Debug`) terminates after one node — constant depth.

The depth-capped-recursive alternative (recurse to depth N, then elide) is rejected: it requires threading a depth counter through `fmt` (no parameter for it — needs thread-local or wrapper types), and any N reintroduces O(branching^N) output blowup. The non-recursive form matches the proven `__repr__` model (`gsm2tree_rs.py:1500-1511`).

Emitted impl (per node struct):

```rust
// Manual Debug: prints span + child COUNT, never recursing into children.
// A derived Debug would recurse through Shared<T> children with no depth
// bound; tree depth is attacker-controlled for parsers over untrusted
// input, so `{:?}` on a deep tree would abort the process (stack
// exhaustion, uncatchable). Mirrors the Python __repr__'s content.
impl fmt::Debug for {class_name} {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("{class_name}")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}
```

Rendering decisions:
- `f.debug_struct` (not the `__repr__` string format): idiomatic Rust `Debug`, gets `{:#?}` pretty-printing for free, and remains non-recursive under both. `Span`'s own `Debug` is shallow (start/end/has_source — `spike_tests.rs:380-389`) and is reused via `.field("span", &self.span)`.
- `format_args!("<{} child(ren)>", …)` rather than a bare count: unambiguous that it is an elision marker, not a field value; matches `__repr__`'s `<{n} child(ren)>` wording.
- Example output: `Identifier { span: Span { start: 0, end: 5, has_source: true }, children: <1 child(ren)> }`.

### Drop: iterative worklist teardown

Break the drop-glue recursion with an emitted manual `impl Drop` on node structs, driven by a per-file worklist. Three pieces:

**1. `Shared::strong_count` (additive, `crates/fltk-cst-core/src/shared.rs`).** New method alongside `arc_ptr`:

```rust
/// Return the number of strong handles to this allocation (Arc::strong_count).
pub fn strong_count(&self) -> usize {
    Arc::strong_count(&self.0)
}
```

Soundness of the `== 1` check below: `Shared` exposes no `Weak` handles (the registry uses Python weakrefs keyed by `arc_ptr`, not `Arc::downgrade` — `registry.rs`), and cloning requires an existing handle, so a thread observing count 1 while holding a handle is the sole owner. This is the only `fltk-cst-core` change; `Shared::Debug`/`PartialEq` untouched (request constraint). Additive — no existing-user impact — but called out per CLAUDE.md as a deliberate public-surface addition.

**2. Per-file worklist enum + drain (new `_drop_block()` in the generator, emitted once per generated file, after the per-rule loop in `generate()`).** Module-private (no `pub`):

```rust
// Worklist item for iterative node teardown. See the per-node `impl Drop`.
enum DropWorklistItem {
    {ClassA}(Shared<{ClassA}>),
    {ClassB}(Shared<{ClassB}>),
    // … one variant per node class that appears as a node-typed child
}

impl DropWorklistItem {
    fn drain_into(self, worklist: &mut Vec<DropWorklistItem>) {
        match self {
            DropWorklistItem::{ClassA}(shared) => {
                if shared.strong_count() == 1 {
                    // Sole owner: steal the children so the node drops childless
                    // (its Drop early-returns) instead of recursing through drop glue.
                    let children = std::mem::take(&mut shared.write().children);
                    worklist.extend(children.into_iter().filter_map(|(_, c)| c.into_drop_item()));
                }
                // `shared` drops here: count==1 → childless node, trivial drop;
                // count>1 → refcount decrement only. Either way, no recursion.
            }
            // … uniform arm per worklist variant
        }
    }
}
```

Variant set — the **child-class union**: one variant per node class that appears as a node-typed variant in *any* child enum (computable from `_child_variants_for_rule` across all rules), one `drain_into` arm per variant, arms uniform. Never-child classes (e.g. `Items` in `cst_generated.rs`, `Grammar` in `cst_fegen.rs`, 11 of 21 classes in the parser fixture) get **no** variant: they can only be externally-dropped roots, whose own `impl Drop` drains their children directly, so a variant for them would never be constructed (only `into_drop_item` constructs variants) — and an unconstructed variant of a private enum trips `dead_code`, a hard failure under `make check`'s `cargo clippy -- -D warnings` gate (Makefile:51-54). Span-only classes that *do* appear as children keep their variant for arm uniformity: the steal harmlessly takes only span children, which contribute nothing to the worklist. Degenerate case: if the union is empty (flat grammar, no node-typed children anywhere), emit no `_drop_block` at all — no `Drop` impls or `into_drop_item` methods exist either (see piece 3), so nothing references it.

The write lock in `mem::take(&mut shared.write().children)` is a statement-scoped temporary guard on a sole-owned node: uncontended, released before worklist processing, never nested.

**3. Per-enum conversion + per-node `impl Drop` (in `_child_enum_block` / `_node_block`).**

On each child enum **whose class has an `impl Drop` or a `DropWorklistItem` variant** (its only two call sites: the class's own `Drop`, and the class's `drain_into` arm), an always-compiled (not python-gated), module-private method — omitted for span-only never-child classes, where it would be uncalled and itself trip `dead_code`:

```rust
impl {ClassName}Child {
    fn into_drop_item(self) -> Option<DropWorklistItem> {
        match self {
            Self::Span(_) => None,
            Self::{ChildCls}(s) => Some(DropWorklistItem::{ChildCls}(s)),
            // … per node-typed variant
        }
    }
}
```

On each node struct **that has at least one node-typed child variant** (per `_child_variants_for_rule`; span-only nodes cannot recurse on drop and get no `Drop` impl, avoiding a needless E0509 destructuring restriction):

```rust
// Iterative Drop: derived drop glue would recurse through Shared children
// one frame set per tree level (attacker-controlled depth → stack
// exhaustion, uncatchable abort). Drains the subtree via a worklist instead.
impl Drop for {class_name} {
    fn drop(&mut self) {
        if self.children.is_empty() {
            return; // also the recursion terminator for nodes drained by the worklist
        }
        let mut worklist: Vec<DropWorklistItem> = self
            .children
            .drain(..)
            .filter_map(|(_, child)| child.into_drop_item())
            .collect();
        while let Some(item) = worklist.pop() {
            item.drain_into(&mut worklist);
        }
    }
}
```

Termination/complexity: each node's children are stolen at most once (steal requires sole ownership, and the stealer owns the handle), so total work is O(nodes); the worklist holds owned handles only, max depth O(tree nodes) heap, O(1) stack. One worklist `Vec` allocation per externally-dropped subtree root; nodes drained by the worklist drop childless and hit the early return (no nested allocation). Empty/span-only `filter_map → collect` does not allocate (size hint 0, no pushes).

Naming: a grammar rule named `drop_worklist_item` would generate a colliding class name. This fails loudly (duplicate definition, compile error) — same pre-existing exposure class as the emitted `NodeKind` enum vs. a rule named `node_kind`; no new guard, consistent with precedent.

### Generator changes (`fltk/fegen/gsm2tree_rs.py`) — summary

1. `_preamble()` (~line 261): add `use std::fmt;` (unconditional — every node block emits a `Debug` impl). `std::mem::take` is used fully qualified, no import.
2. `_node_block()` (~lines 638-646):
   - Delete the `TODO(rust-cst-debug-depth)` comment (lines 638-639).
   - Emit `#[derive(Clone)]` instead of `#[derive(Clone, Debug)]`.
   - Immediately after the struct definition, before the `PartialEq` impl, emit the manual `Debug` impl; after it, the `impl Drop` (when the class has node-typed child variants).
   - Extend the struct's doc comment: Debug output is non-recursive (span + child count; traverse via `children()` to inspect subtrees); teardown is iterative (bounded stack at any depth).
3. `_child_enum_block()` (~line 488): emit the always-compiled `into_drop_item` impl after the `PartialEq` impl (before the python-gated block), gated on the class having a `Drop` impl or a worklist variant (piece 3). Child enums keep `#[derive(Clone, Debug)]` — see "Untouched" below.
4. New `_drop_block()` emitting `DropWorklistItem` + `drain_into` with one variant/arm per child-class-union member (piece 2), appended in `generate()` after the per-rule loop (Rust is order-independent; forward references from `into_drop_item` are fine). Skipped entirely when the union is empty. Requires a pre-pass over all rules' `_child_variants_for_rule` results before per-rule emission, or computing the union first; either is a trivial restructure of `generate()`.

Untouched, with rationale:
- Node `Clone` derive — unchanged (constraint); `Clone` is shallow (Arc clones), not recursive.
- Child enums (`_child_enum_block`, line 504): keep `#[derive(Clone, Debug)]`. Derived enum `Debug` → `Shared<T>::Debug` → node manual `Debug` = constant depth. A variant-name-only impl would lose useful one-level info for no safety gain.
- `NodeKind` / label enums (lines 356, 364, 445, 453): fieldless, `derive(Debug)` trivially bounded, no drop glue.
- `Shared<T>` `Debug`/`PartialEq` in `fltk-cst-core` — unchanged (constraint; the cycle-acceptance contract at `shared.rs:36-40` stays accurate as written). Only the additive `strong_count` is new.
- Python `__repr__` (`_repr_method`) — unchanged (constraint).
- Handle pyclasses — unchanged; their `Shared<T>` field now benefits from iterative teardown automatically (node `Drop` touches no Python state and needs no GIL).

### Regeneration

`make gencode` regenerates all six outputs: `src/cst_generated.rs`, `src/cst_fegen.rs`, `crates/fltk-cst-spike/src/cst.rs` (copied from `cst_generated.rs`), `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_parser_fixture/src/cst.rs`. Then `make fix`, commit (per CLAUDE.md regen workflow).

### TODO bookkeeping

Remove the `rust-cst-debug-depth` entry from `TODO.md` (lines 84-86) and the generator comment (covered above). No other `TODO(rust-cst-debug-depth)` sites exist (grep-verified). Do **not** file `rust-cst-drop-depth` — user decision: the Drop fix lands here instead.

### Compatibility note

Rust convention treats `Debug` output as unstable; this is a format change, not an API break. Per CLAUDE.md, call it out for out-of-tree consumers in the commit message: any downstream code string-matching `{:?}` output of node structs will see span + child count instead of a full tree dump. The `Drop` impl adds no public symbols (`DropWorklistItem`/`into_drop_item` are module-private) except `Shared::strong_count` (additive). Sibling deallocation order changes (worklist LIFO vs. field-order drop glue) — unobservable, since no type in the tree has a side-effectful `Drop` beyond deallocation. `impl Drop` forbids moving fields out of node structs (E0509): grep-verified that no in-tree or generated code destructures a node struct by value (only `ApplyResult` in `crates/fltk-parser-core/tests/memo_toy.rs`, not a CST node), and the future `extend-children-owned` TODO is compatible (it would `Vec::append` through `&mut`, not move fields). Python-visible surface (`__repr__`, accessors, equality) is byte-identical.

## Edge cases / failure modes

- **Zero children**: Debug prints `children: <0 child(ren)>` (spike-test assertion); Drop early-returns (where emitted — span-only classes have no `Drop` impl at all).
- **Never-child root classes** (no `DropWorklistItem` variant): their own `impl Drop` seeds the worklist from their children directly; no variant for the root itself is ever needed.
- **`{:#?}` alternate flag**: `debug_struct` handles it; still non-recursive.
- **Lock behavior (Debug)**: node `Debug` reads own fields directly (no lock — `impl` is on the data struct, `&self`). Formatting a `Shared<T>` or a child enum still takes exactly one read lock (in `Shared::Debug`), one level deep — strictly less locking than before.
- **Shared child (`strong_count > 1`)**: not stolen; the subtree stays intact for the other owner(s). The last owner's eventual drop tears it down iteratively (covered by test 3).
- **Concurrent droppers**: the `strong_count == 1` check has a benign race — if another thread drops its handle between our read (>1, skip steal) and our decrement, the final Arc-glue drop runs that node's own `Drop`, which is itself iterative. Nesting depth is bounded by the number of *concurrently racing droppers*, not tree depth; single-threaded teardown never nests.
- **Cycles**: unchanged — an Arc cycle keeps every count ≥ 2, so no steal occurs and the cycle leaks, exactly as documented (`shared.rs:36-40`). The worklist always terminates (steal-at-most-once per node). Debug on a self-referential tree no longer loops at all (formatting stops at the first node); the `shared.rs` cycle caveat remains accurate as written since it describes `Shared`, not the nodes.
- **Panic/poison safety**: the Drop path calls only `mem::take`, `Vec` ops, and `write()` (which ignores poison) — no panicking operations introduced inside `drop`.
- **Pre-fix test behavior**: both deep-tree tests under current codegen abort the process (SIGSEGV), killing the cargo test harness — they cannot be committed failing-but-green. TDD demonstration = run each once pre-fix, observe abort, then land tests+fix together.

## Test plan

After the change, in `tests/rust_parser_fixture/src/native_tests.rs` unless noted, using `ExprChild::Expr(Shared<Expr>)` from `expr := lhs:expr . "+" . rhs:atom | atom:atom` — the simplest directly self-recursive node type (other recursive types exist: `lval`/`rval` mutual recursion and `rec_via_sub` in the same grammar, `Shared<Alternatives>` in `tests/rust_cst_fegen`; `Expr` is chosen, not forced). Chain construction is iterative: build leaf-up, each parent `push_child`es the previous level's `Shared<Expr>`; only the root binding is retained.

Depth rationale (applies to tests 1-2): under the old codegen each tree level costs *multiple* stack frames (~5-10 frames/level for both the derived-Debug chain and the drop-glue chain), i.e. several hundred bytes to >1 KiB per level in debug builds — 100 000 levels comfortably exceeds the 8 MiB default stack, proving each fix is load-bearing. Do not lower the depth based on a per-frame (rather than per-level) estimate.

1. **New: deep-tree Debug test.** Build a 100 000-level `Expr` chain; `format!("{:?}", root)` completes; assert output contains `child(ren)` and is small (< 256 bytes — bounded regardless of depth). Natural end-of-scope drop additionally exercises the iterative `Drop`. Pre-fix: aborts at `format!`.
2. **New: deep-tree Drop test.** Build a 100 000-level `Expr` chain; `drop(root)`; test completes. Isolates the Drop fix from the Debug fix. Pre-fix: aborts at drop.
3. **New: shared-subtree survival test.** Build `parent → child → grandchild`; retain a second `Shared` handle to `child`; `drop(parent)`; assert through the retained handle that `child` still has its grandchild (`children().len() == 1` — proves the `strong_count > 1` branch does not steal); then drop the retained handle (frees the subtree iteratively).
4. **New: `Shared::strong_count` unit test** in `crates/fltk-cst-core` (count 1 after `new`, 2 after `clone`, back to 1 after drop).
5. **New: parser-produced deep-tree test** (per `evaluation-drop-depth-reachability.md` §4's recommendation), in the parser fixture's test suite: parse `"1" + "+1"*100_000` (~200 KiB) with the default `max_depth`; assert the parse succeeds; `format!("{:?}", root)` completes with bounded output; natural drop completes. Pins reachability-via-parsing (left-recursive seed-grow) in CI, so the manual-construction tests 1-2 cannot later be dismissed as unrealistic. (Tests 1-2 stay: they isolate each fix from parser behavior.)
6. **Updated: spike smoke tests** (`crates/fltk-cst-spike/src/spike_tests.rs:364-378`): keep the four `format!` calls compiling; upgrade from discard-only to content assertions — node output contains `"span"` and `"<0 child(ren)>"`; child-enum output for `ItemsChild::Identifier` contains `"Identifier"` and `"child(ren)"` (one-level delegation through `Shared` works).
7. **Existing suites clean**: `make gencode && make fix`, then `uv run --group dev maturin develop`, `uv run pytest` (Python `__repr__`/parity tests unaffected), `cargo test` across workspace + fixture crates (`make cargo-test`, `make test-rust-parser-fixture`, etc. — `make check` covers the full gate).

## Open questions

None. The round-1 open question (file `TODO(rust-cst-drop-depth)` for the recursive-Drop exposure?) was resolved by the user: do not file it — the Drop fix is in scope here (see "Drop: iterative worklist teardown").
