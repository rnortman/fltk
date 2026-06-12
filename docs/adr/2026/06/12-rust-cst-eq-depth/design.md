# Design: rust-cst-eq-depth — iterative PartialEq on generated Rust CST nodes

Style: concise, precise, no padding. Audience: implementer LLM/human. Inputs: `request.md`, `exploration.md` (same dir). Implementation base: b02cb8f (all line citations verified there; treat function names as authoritative over line numbers).

## 1. Root cause / context

`impl PartialEq for {Node}` emitted by `_node_block` (`fltk/fegen/gsm2tree_rs.py:798-803`) compares `self.span == other.span && self.children == other.children`. The children comparison recurses: `Vec<(label, ChildEnum)>::eq` → `ChildEnum::eq` (manual impl, `gsm2tree_rs.py:577-588`) → `Shared<T>::eq` (`crates/fltk-cst-core/src/shared.rs:98-109`) → `*self.read() == *other.read()` → `T::eq` again. One stack frame set per tree level, no depth bound. Tree depth is attacker-controlled (left-recursive grammars build depth ∝ input length — see `tests/rust_parser_fixture/src/native_tests.rs:150`), so `==`/`assert_eq!` on a deep parser-produced tree aborts the process via stack exhaustion — uncatchable in Rust.

Same root cause as the already-fixed Debug (`gsm2tree_rs.py:748-755`, O(1) manual impl) and Drop (`gsm2tree_rs.py:764-788` + `_drop_block` worklist at `gsm2tree_rs.py:1926-1964`) paths.

Load-bearing difference from Drop (per `request.md`): equality traverses **two** trees in lockstep, so the worklist must carry **pairs** `(Shared<T>, Shared<T>)`, and must not mutate either tree. `DropWorklistItem` (single handles, mutating drain) cannot be reused.

## 2. Proposed approach

### 2.1 Architecture

Make the generated node struct's `T::eq` the iterative driver. Everything above it then terminates at constant stack depth without modification:

- `Shared<T>::eq` (shared.rs) — **unchanged code**: `ptr_eq` short-circuit, then `*self.read() == *other.read()` → the now-iterative `T::eq`. One delegation frame, no further recursion. (Same termination argument as Debug: `Shared<T>::Debug` delegates to the O(1) manual node `Debug`.)
- `ChildEnum::eq` — **unchanged code**: node-variant arms delegate to `Shared<T>::eq` → iterative `T::eq`. Stays public-surface-compatible for downstream Rust callers comparing child enum values.
- Handle `__eq__` pymethod (`_eq_method`, `gsm2tree_rs.py:1859-1880`) — **unchanged**: delegates to `Shared<T>::eq`.

Inside the driver, node-typed child pairs are **never** compared via `ChildEnum::eq` (that would start a nested full deep-compare per child → O(n²) time). They are enqueued onto the pair worklist instead. `Span` variants compare directly (O(1)).

### 2.2 Generated constructs (all in the per-grammar cst.rs, module-private except where noted)

**(a) `EqWorklistItem` enum** — new, emitted once per file by a new `_eq_block(child_union)` method placed next to `_drop_block`, keyed on the same `child_union` (`_child_class_union()`, `gsm2tree_rs.py:267-278`), skipped when the union is empty. Module-private, mirroring `DropWorklistItem`:

```rust
enum EqWorklistItem {
    Expr(Shared<Expr>, Shared<Expr>),
    Atom(Shared<Atom>, Shared<Atom>),
    // ... one pair-variant per child-union class
}
```

Never-child root classes get no variant (their own `eq` seeds the worklist directly; an unused variant would trip `dead_code` under `-D warnings` — same rationale as `DropWorklistItem`).

**(b) `EqWorklistItem::compare`** — uniform arms emitted via a `_emit_eq_arm` helper (mirroring `_emit_drain_arm`, `gsm2tree_rs.py:1907-1924`):

```rust
impl EqWorklistItem {
    /// Compare one node pair shallowly; enqueue node-typed child pairs.
    /// Returns false on the first mismatch (span, child count, label, variant, Span value).
    fn compare(self, worklist: &mut Vec<EqWorklistItem>) -> bool {
        match self {
            EqWorklistItem::Expr(a, b) => {
                let ga = a.read();
                let gb = b.read();
                if ga.span != gb.span || ga.children.len() != gb.children.len() {
                    return false;
                }
                for ((la, ca), (lb, cb)) in ga.children.iter().zip(gb.children.iter()) {
                    if la != lb || !ca.eq_shallow_enqueue(cb, worklist) {
                        return false;
                    }
                }
                true
            }
            // ... identical arm per variant
        }
    }
}
```

Arms access private `span`/`children` fields directly — legal, same module. Both read guards are held only for the duration of one arm (dropped at arm end); pushes under the guards are plain `Vec` pushes + `Arc` clones, no lock acquisition. Arms are structurally identical across variants, which is exactly the uniformity property `_emit_drain_arm` documents; span-only union members (e.g. `Trivia`) use the same arm shape and simply never enqueue.

**(c) `ChildEnum::eq_shallow_enqueue`** — new inherent method emitted in `_child_enum_block` alongside `into_drop_item` (`gsm2tree_rs.py:591-613`), under the **same emission condition** (`child_classes` non-empty OR `class_name in child_union` — same call-graph shape: own `eq` seeds; `compare` arms continue):

```rust
impl ExprChild {
    /// Shallow structural equality for one child pair.
    /// Span pair: compare now. Node pair: ptr_eq → equal (skip);
    /// else enqueue for the worklist. Variant mismatch: false.
    fn eq_shallow_enqueue(&self, other: &Self, worklist: &mut Vec<EqWorklistItem>) -> bool {
        match (self, other) {
            (Self::Atom(a), Self::Atom(b)) => {
                if !a.ptr_eq(b) {
                    worklist.push(EqWorklistItem::Atom(a.clone(), b.clone()));
                }
                true
            }
            (Self::Expr(a), Self::Expr(b)) => { /* same shape */ }
            // Span arm when has_span: (Self::Span(a), Self::Span(b)) => a == b,
            _ => false, // only when num_variants > 1 (same guard as existing PartialEq emission)
        }
    }
}
```

The per-pair `ptr_eq` short-circuit is preserved here (request constraint): same allocation → equal with no locking and no enqueue.

For span-only union members (`child_classes` empty, class in `child_union` — e.g. `Num`, `Name`, `Trivia`), the body has only the Span arm and never touches `worklist`. Emit the parameter as `_worklist` in that case to survive the `-D warnings` clippy gates (Makefile lines 53-54, 67-71), following the generator's existing conditional-underscore convention (`py_param`/`_py` at `gsm2tree_rs.py:624`, `extract_py_param`/`_span_type` at `:646-652`).

**(d) Node struct `impl PartialEq`** — `_node_block` emission at `gsm2tree_rs.py:790-803` is replaced, split by the same predicate Drop uses (`child_classes` non-empty):

*Classes with node-typed children* — iterative driver:

```rust
impl PartialEq for Expr {
    fn eq(&self, other: &Self) -> bool {
        if self.span != other.span || self.children.len() != other.children.len() {
            return false;
        }
        // Worklist allocated lazily (Vec::new does not heap-allocate until first
        // push); shallow trees and all-ptr_eq children never allocate.
        let mut worklist: Vec<EqWorklistItem> = Vec::new();
        for ((la, ca), (lb, cb)) in self.children.iter().zip(other.children.iter()) {
            if la != lb || !ca.eq_shallow_enqueue(cb, &mut worklist) {
                return false;
            }
        }
        while let Some(item) = worklist.pop() {
            if !item.compare(&mut worklist) {
                return false;
            }
        }
        true
    }
}
```

The seed level needs no locks: `self`/`other` are already borrowed. Label comparison works for both `Option<LabelEnum>` and the label-less `Option<()>` type.

*Span-only classes* (no node-typed children — e.g. `Num`, `Trivia`): keep the existing one-line `self.span == other.span && self.children == other.children`. Their `ChildEnum` has only a `Span` variant, so this is already non-recursive. Mirrors the Drop precedent (span-only nodes get no `impl Drop`). Add an emitted comment stating why it is depth-safe.

The replaced emission also drops the `TODO(rust-cst-eq-depth)` generator comment (`gsm2tree_rs.py:790-793`) and replaces the explanatory comment about recursion/DAG locking with one describing the iterative scheme.

### 2.3 Generator wiring (`fltk/fegen/gsm2tree_rs.py`)

- `generate()` (`gsm2tree_rs.py:280-302`): emit `_eq_block(child_union)` next to `_drop_block(child_union)` (same skip-when-empty handling).
- `_node_block` doc/struct doc-comment: extend the "Teardown is iterative" line (`gsm2tree_rs.py:729`) with an equality counterpart ("Equality is iterative: bounded stack at any depth.") for classes with node-typed children.
- No changes to `.pyi`/protocol emission: equality is not part of the annotation surface; `__eq__`/`__hash__` pymethods are untouched.

### 2.4 `crates/fltk-cst-core/src/shared.rs`

No code change. `Shared<T>` stays generic (`T: PartialEq`), usable for non-CST `T`. Doc changes only:

- Remove the `TODO(rust-cst-eq-depth)` comment (lines 93-97).
- Update the `# Equality` doc section (lines 14-30): the ptr_eq short-circuit text stands; rewrite the DAG-limitation paragraph — generated node `eq` is now iterative, holding at most two read-guard *pairs* simultaneously (the root pair inside `Shared::eq` + the current worklist item's pair) instead of one pair per tree level. The position-shifted-sharing caveat itself remains: a worklist item may re-lock a node whose root guard is still held, and `std::sync::RwLock` same-thread read re-entry may deadlock with a queued writer. Comparison contract is still "deadlock-free absent concurrent writers" — unchanged semantics, smaller lock footprint.
- `# Reference cycles` section (lines 37-40): "PartialEq … will loop infinitely on a cycle" stays true in spirit; reword to note eq now loops via unbounded worklist growth rather than unbounded stack (still nontermination, still "do not create cycles").

### 2.5 Regeneration + bookkeeping

- Regenerate all generated outputs via `make gencode`, then `make fix`, then commit (the intended flow per CLAUDE.md). Covered outputs: `src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fixture/src/cst.rs`, `tests/rust_cst_fegen/src/cst.rs`, `tests/rust_parser_fixture/src/cst.rs`, `tests/rust_parser_fixture/src/collision_cst.rs`, `crates/fltk-cst-spike/src/cst.rs` (cp of `cst_generated.rs`), plus the Python-side outputs gencode also rebuilds.
- Remove the `rust-cst-eq-depth` entry from `TODO.md` and both code-site TODO comments (`gsm2tree_rs.py:790-793`, `shared.rs:93-97`).

## 3. Semantics preserved (public-API argument)

Out-of-tree consumers observe equality through: Rust `==` on node structs / `Shared<T>` / child enums, and Python `==` via `__eq__`. For all of these:

- **Result**: structural equality over (span, children-with-labels), identical to today. The iterative driver checks exactly the same conjuncts (span eq, length eq, per-index label eq, per-index child variant + value eq) that the recursive version checks, in a different evaluation order. Equality is a pure boolean conjunction with no side effects, so traversal order (stack-pop ≈ rightmost-first vs. recursive leftmost-first) is unobservable.
- **Trait surface**: no impl added or removed; no type renamed; `EqWorklistItem` and `eq_shallow_enqueue` are module-private. `PartialEq`-only (no `Eq`) — unchanged.
- **ptr_eq behavior**: same-allocation pairs still short-circuit (in `Shared::eq` at the root, in `eq_shallow_enqueue` per child pair).
- **Concurrent-mutation nuance**: the recursive version held read guards for the whole ancestor path, so a writer could not modify an already-locked ancestor mid-comparison; the iterative version releases each pair's guards before comparing descendants, so writers can interleave at more points. Results under concurrent mutation were never specified or deterministic (writers could always mutate not-yet-visited subtrees); absent concurrent writers, results are identical. Not a semantic change to any documented contract.

## 4. Edge cases / failure modes

| Case | Behavior |
|---|---|
| 100k-deep equal chains, distinct allocations | `true`, bounded stack; worklist peaks at O(pending pairs) heap (≤ one pair per level for a chain) |
| Deep chains differing at the leaf | `false` after full traversal; bounded stack |
| Variant mismatch at any position | `false` (wildcard arm, only emitted when >1 variant — same unreachable-pattern guard as the existing `PartialEq` emission, `gsm2tree_rs.py:576,584`) |
| Label mismatch / count mismatch | `false` before any child descent at that level |
| Same `Shared` at same position both sides | ptr_eq skip — equal without locking or enqueue |
| Position-shifted DAG sharing + queued writer | May deadlock (same-thread read re-entry) — pre-existing documented limitation, unchanged contract, smaller lock window (§2.4) |
| Reference cycles (both trees cyclic, distinct allocations) | Nontermination via worklist growth instead of stack overflow — same "do not create cycles" contract (shared.rs docs) |
| Early `false` return with non-empty worklist | Worklist drops; items hold Arc clones of nodes still owned by the live trees (`strong_count ≥ 2`), so their drop is a refcount decrement — no steal, no deep teardown |
| Flat grammar (empty child union) | `_eq_block` emits nothing; all nodes are span-only and keep the one-line eq; no dead code under `-D warnings` |
| Memory | Worklist ≤ O(min(|A|,|B|)) pairs; replaces O(depth) stack with heap — same trade Drop made |

## 5. Test plan (TDD: write first, observe failure, then fix)

New tests in `tests/rust_parser_fixture/src/native_tests.rs`, mirroring the Debug/Drop depth tests (depth constant `DEEP_TREE_DEPTH = 100_000`):

1. **`test_deep_tree_eq_iterative_equal`** — build two structurally equal 100k chains (two calls to the chain builder), `assert!(a == b)`. Pre-fix failure mode: process abort (stack exhaustion) — the test "fails" by crashing the harness, which is the demonstrable-bug step.
2. **`test_deep_tree_eq_iterative_unequal`** — two 100k chains differing only at the deepest leaf span → `assert!(a != b)`. Forces full-depth traversal on the `false` path. Requires extending the builder: refactor `build_deep_expr_chain()` (`native_tests.rs:14`) into `build_deep_expr_chain_with_leaf_span(span: Span)`; keep the original as a `Span::unknown()` wrapper so the existing Debug/Drop depth tests (`native_tests.rs:39,59`) are untouched.
3. **`test_deep_shared_subtree_eq_ptr_eq_short_circuit`** — two distinct root nodes each holding the *same* `Shared` 100k chain as their child → equal; exercises the per-pair ptr_eq skip (no traversal of the shared chain).
4. **`test_multi_child_eq_worklist`** — mirror `test_multi_child_drop_worklist` (`native_tests.rs:118`): two equal ~100-level trees where each level has two node-typed children (lhs:Expr + rhs:Atom) → equal; then an unequal variant (one rhs differs) → unequal. Exercises worklists holding multiple pending pairs.
5. **`test_parser_produced_deep_tree_eq`** — parse `"1" + "+1"*100_000` twice (two `Parser` instances), `assert!(a.result == b.result)`. Pins reachability from real parsing, mirroring `test_parser_produced_deep_tree_debug_and_drop` (`native_tests.rs:150`).
6. **`test_eq_variant_mismatch_unequal`** — shallow, **same label / different variant** so the comparison reaches the wildcard arm of `eq_shallow_enqueue` rather than short-circuiting on the label check (`la != lb` precedes the enqueue call in the driver, §2.2d). Use the union-label `val` rule: parse-or-build `Val` with `item:num` (`ValChild::Num`) vs. `Val` with `item:name` (`ValChild::Name`) under the same `item` label → unequal. (Alternative: `push_child(Some(ExprLabel::Lhs), ExprChild::Atom(..))` vs. `ExprChild::Expr(..)` — `push_child` performs no type checking, `gsm2tree_rs.py:840-845`.)

Existing tests that must keep passing unchanged (regression net for semantics):
- `tests/rust_cst_fixture/src/native_tests.rs:110` (`equal_subtrees_compare_equal`), `:119`, `:128` (span inequalities), `:183` (`shared_self_eq_no_deadlock`), `:190` (`shared_deep_eq_distinct_allocations`).
- Python-side pytest suite (handle `__eq__` parity / cross-backend tests).

Run gates: `cargo test --manifest-path tests/rust_parser_fixture/Cargo.toml` (red→green), then `uv run --group dev maturin develop && uv run pytest`, then `make check` clean.

## 6. Open questions

None. The two open factual questions in `exploration.md` are resolvable without user judgment: (1) exact eq stack-frame size is moot — 100k is the established depth at which the structurally identical Debug chain aborted, and the tests will demonstrate the abort empirically pre-fix; (2) "reuse `DropWorklistItem` vs. new construct" is settled by the request's load-bearing constraint — a new pair-carrying `EqWorklistItem` (§2.2a).
