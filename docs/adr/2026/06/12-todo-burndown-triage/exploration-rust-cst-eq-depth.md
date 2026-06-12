# Exploration: `rust-cst-eq-depth` TODO adversarial validation

Repo HEAD: 5d94733. Style: concise, token-dense, fact-anchored. No prescriptions.

---

## 1. Is `PartialEq` currently derived or manual on generated node structs?

**Manual, not derived.** The generator emits an explicit `impl PartialEq for {class_name}` block.

Generator site: `gsm2tree_rs.py:798-803` (`_node_block`):
```python
lines.append(f"impl PartialEq for {class_name} {{")
lines.append("    fn eq(&self, other: &Self) -> bool {")
lines.append("        self.span == other.span && self.children == other.children")
```

This is **not** `#[derive(PartialEq)]`. The data struct only carries `#[derive(Clone)]` (`gsm2tree_rs.py:730`). The `PartialEq` is a separate manually-coded `impl` block, preceded at `gsm2tree_rs.py:790-797` by the TODO comment:
```
# TODO(rust-cst-eq-depth): this derived PartialEq recurses through Shared<T> children
# with no depth bound; tree depth is attacker-controlled, so assert_eq! on a deep
# parser-produced tree aborts (stack exhaustion, uncatchable). Fix: emit iterative
# impl PartialEq following the same _drop_block worklist pattern.
```

The TODO comment calls it "derived" but the emitted code is a manual `impl`. The recursion hazard is real regardless: `self.children == other.children` recurses into `Vec<(label, ChildEnum)>`, and `ChildEnum::PartialEq` (also a manual `impl`) compares `Shared<T>` variants which delegate to `Shared<T>::PartialEq`.

Verified in generated output at:
- `crates/fltk-cst-spike/src/cst.rs:217-221` (`Identifier`, span-only: `children == children` on `Vec<(Option<IdentifierLabel>, IdentifierChild)>`)
- `crates/fltk-cst-spike/src/cst.rs:1087-1091` (`Items`, recursive: same pattern, `ItemsChild` holds `Shared<Identifier>`, `Shared<Trivia>`)
- `tests/rust_parser_fixture/src/cst.rs:7295-7299` (`Expr`, self-recursive: `ExprChild::Expr(Shared<Expr>)` at line 7162)

The `ExprChild` enum at `tests/rust_parser_fixture/src/cst.rs:7160-7163`:
```rust
pub enum ExprChild {
    Atom(Shared<Atom>),
    Expr(Shared<Expr>),  // ← Shared<Expr> inside Expr → recursion
}
```
Its `PartialEq` (`cst.rs:7165-7173`) compares `Shared<Expr>` pairs via `a == b`, which invokes `Shared<Expr>::PartialEq`.

---

## 2. `Shared<T>::PartialEq` — does it look as claimed?

`crates/fltk-cst-core/src/shared.rs:93-109`:
```rust
// TODO(rust-cst-eq-depth): this PartialEq delegates to T::eq, which for generated node
// structs recurses through Shared<T> children with no depth bound; ...
impl<T: PartialEq> PartialEq for Shared<T> {
    fn eq(&self, other: &Self) -> bool {
        if self.ptr_eq(other) {
            return true;
        }
        *self.read() == *other.read()
    }
}
```

Claim is accurate. `*self.read() == *other.read()` calls `T::eq` (the generated node struct's `PartialEq`), which compares `self.children == other.children`, recursing back into child enum `PartialEq` → next `Shared<T>::PartialEq`, etc. No depth counter anywhere in this chain.

The `ptr_eq` short-circuit fires only when the two `Shared<T>` handles point to the same allocation (`Arc::ptr_eq`). It does not prevent recursion on distinct-allocation equal trees.

---

## 3. How were Debug and Drop fixed? Is the same pattern applicable to PartialEq?

### Debug fix

Generator (`gsm2tree_rs.py:748-755`) emits a manual `impl fmt::Debug for {class_name}` that prints only `span` + `children.len()` — a non-recursive O(1) operation:
```rust
impl fmt::Debug for Identifier {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("Identifier")
            .field("span", &self.span)
            .field("children", &format_args!("<{} child(ren)>", self.children.len()))
            .finish()
    }
}
```
`crates/fltk-cst-spike/src/cst.rs:208-215` shows the generated output. The `Shared<T>::Debug` at `shared.rs:111-115` still delegates to `T::Debug` — safe only because the node struct's manual `Debug` terminates at constant depth (child enum `#[derive(Clone, Debug)]` delegates to `Shared<T>::Debug`, but `T::Debug` terminates there instead of recursing further).

### Drop fix

`gsm2tree_rs.py:764-788` emits `impl Drop for {class_name}` (only when `child_classes` is non-empty). The pattern:
1. Drain `self.children` into a flat `Vec<DropWorklistItem>`.
2. Loop: pop from worklist, call `drain_into(&mut worklist)` which steals children of sole-owner nodes and pushes them onto the worklist.
3. Terminates when worklist is empty.

A separate `DropWorklistItem` enum (emitted once per grammar by `_drop_block`, `gsm2tree_rs.py:1934-1972`) has one variant per class that appears as a child. The `drain_into` method on it checks `strong_count() == 1` (sole ownership) before stealing.

`crates/fltk-cst-spike/src/cst.rs:1066-1085` shows the generated `impl Drop for Items`. The `DropWorklistItem` enum is at `cst.rs:3019-3047`.

### Applicability of Drop pattern to PartialEq

The Drop pattern is a **single-tree worklist** — it processes one tree at a time, stealing children only when sole owner. PartialEq compares **two trees simultaneously**, requiring pairwise traversal: at each level, the left subtree child at index `i` must be compared against the right subtree child at index `i`.

This is a **real structural difference**:
- Drop can process one node at a time from a worklist of `Shared<T>` handles.
- PartialEq must maintain a worklist of **pairs** `(Shared<T>, Shared<T>)`, one from each tree at each corresponding position.
- For nodes with multiple children (N-ary nodes), the worklist must push all N child pairs for comparison.
- Short-circuit on `ptr_eq` still applies per pair (same pointer → equal, no locking needed).

The claim in the TODO that "the same generator pattern used for `impl Drop`" applies to PartialEq is directionally correct (worklist instead of recursion), but the worklist item type must carry pairs, not single handles. This is a real complication in the implementation, not a correctness blocker for the hazard claim.

---

## 4. Other recursive trait impls on `Shared<T>` or generated node structs

From `shared.rs`:
- `Clone` (`shared.rs:86-91`): **shallow** — only `Arc::clone`, no recursion. Safe.
- `Debug` (`shared.rs:111-115`): delegates to `T::Debug`. Safe only because the manual node `Debug` terminates at O(1) depth (see §3 above). The child enum's `#[derive(Debug)]` does recurse into `Shared<T>::Debug`, but terminates at the manual node impl. Equivalent chain: `Shared<A>::Debug → A::Debug (manual, terminates)`.
- `PartialEq` (`shared.rs:98-109`): recursive through `T::eq` with no bound. **The live hazard.**
- `Hash`: **not implemented** on `Shared<T>` (grep over `shared.rs` returns nothing). Node structs do not derive `Hash` either (confirmed: generated node structs only carry `#[derive(Clone)]`; `Hash` is derived only on `NodeKind`, `LabelEnum`, and child enums — all of which are flat enums or hold `Span` (Copy), so no recursion hazard). `crates/fltk-cst-spike/src/cst.rs`: `IdentifierChild`, `ItemsChild`, `TriviaChild` have `#[derive(Clone, Debug)]` on child enums, **no Hash**; `NodeKind` and label enums have `#[derive(Clone, Debug, PartialEq, Eq, Hash)]` but are flat (no `Shared<T>` members).
- `Serialize`/`Deserialize`, `Ord`, `PartialOrd`: not implemented anywhere.

**Summary of hazardous recursive traits**: Only `PartialEq` via `Shared<T>::PartialEq`.

---

## 5. Tests for the Debug/Drop fixes that a PartialEq fix would mirror

All depth tests live in `tests/rust_parser_fixture/src/native_tests.rs`:

| Test | Function | What it pins |
|---|---|---|
| 1 | `test_deep_tree_debug_non_recursive` (line 39) | `format!("{:?}", root.read())` on 100,000-level chain completes; output < 256 bytes |
| 2 | `test_deep_tree_drop_iterative` (line 59) | `drop(root)` on 100,000-level chain completes |
| 3 | `test_shared_subtree_survives_parent_drop` (line 68) | Shared subtree not stolen when `strong_count > 1` |
| 4b | `test_multi_child_drop_worklist` (line 118) | Multi-child drain (each node has 2 node-typed children) |
| 5 | `test_parser_produced_deep_tree_debug_and_drop` (line 150) | Parser-produced tree at 100,000 depth |

There is **no analogous deep-eq test**. `tests/rust_cst_fixture/src/native_tests.rs` has `shared_deep_eq_distinct_allocations` (line 190) and `equal_subtrees_compare_equal` (line 110), but these use shallow trees (depth 1-2). No test calls `==` on a 100,000-level chain.

A PartialEq fix would mirror test 1/2 structure: build a deep chain using `build_deep_expr_chain()` (already available at `native_tests.rs:14`), then call `a == b` on two equal deep chains and assert true without stack overflow.

---

## 6. Python backend: recursion hazard status

Python-generated node classes are `@dataclasses.dataclass` (`gsm2tree.py:237`). The `@dataclass` decorator auto-generates `__eq__` that compares fields (`kind`, `span`, `children`). Comparing `children` lists recurses into Python objects.

**Key difference from Rust**: Python `RecursionError` (raised at `sys.getrecursionlimit()`, default 1000) is a **catchable exception** — it propagates up the call stack like any other exception. Rust stack exhaustion is an uncatchable `SIGSEGV`/abort.

Python `__eq__` on a tree of depth > ~500 (allowing for call overhead) will raise `RecursionError`. This is observable and catchable, not a process abort. No `sys.setrecursionlimit` increase is present in the generated code or the fltk library (`grep` over `fltk/fegen/` returns nothing). The Python hazard exists (surprising `RecursionError` on deep parser-produced trees) but is categorically less severe: catchable, not an abort.

**Cross-backend equivalence**: The TODO's fix scope is the Rust backend only. Python `__eq__` behavior (raises `RecursionError`) is not equivalent to the Rust fix (iterative, no bound). A downstream consumer using Python `==` on deep trees would still get `RecursionError`. This is a known asymmetry, not introduced by this TODO.

---

## 7. TODO slug/comment placement accuracy

- `TODO.md:27-29`: entry present, accurately describes the hazard and locations.
- `crates/fltk-cst-core/src/shared.rs:93-97`: `// TODO(rust-cst-eq-depth)` comment present above `impl<T: PartialEq> PartialEq for Shared<T>`.
- `fltk/fegen/gsm2tree_rs.py:790-793`: `# TODO(rust-cst-eq-depth)` comment present above the emitted `impl PartialEq`.

Both code-site comments exist. The TODO.md entry was added by the `rust-cst-debug-depth` dispositions (`docs/adr/2026/06/11-rust-cst-debug-depth/dispositions-deep.md:72-75`), which also added both code-site comments.

---

## 8. Factual verdict on the TODO claim

All five sub-claims verified against source:

1. **"PartialEq on generated node structs recurses through Shared<T> children with no depth bound"** — TRUE. `Expr::PartialEq` at `cst.rs:7295` → `ExprChild::PartialEq` at `cst.rs:7165` → `Shared<Expr>::PartialEq` at `shared.rs:98` → `Expr::PartialEq`. No depth counter.

2. **"assert_eq! or any equality check on a deep parser-produced tree aborts the process (stack exhaustion, uncatchable)"** — TRUE in principle. Rust stack overflow from unbounded recursion is an uncatchable signal/abort. The depth at which it occurs depends on frame size and stack limit (default 8 MiB on Linux). 100,000 levels abort Debug before the fix; same depth would abort eq. No test currently demonstrates this (no deep-eq test exists).

3. **"Same root cause as the fixed Debug/Drop paths"** — TRUE. The recursion chain (`PartialEq` → `children ==` → `Vec<ChildEnum>` → `Shared<T>::PartialEq` → lock + recurse) is structurally identical to the pre-fix Debug chain.

4. **"Fix: emit iterative impl PartialEq on node structs following the same generator pattern used for impl Drop"** — DIRECTIONALLY TRUE with a real complication: PartialEq traverses two trees simultaneously, requiring a worklist of pairs `(Shared<T>, Shared<T>)` rather than single handles. Drop steals children; PartialEq cannot mutate either tree. The worklist structure is applicable but not identical to `DropWorklistItem`.

5. **"Locations: gsm2tree_rs.py (_node_block, _drop_block pattern), shared.rs (PartialEq impl)"** — ACCURATE. `_node_block` at `gsm2tree_rs.py:692` emits the recursive `impl PartialEq`; `_drop_block` at `gsm2tree_rs.py:1934` provides the worklist pattern; `shared.rs:98` holds the `Shared<T>::PartialEq`.

---

## Open factual questions

- What is the actual stack frame size for a `Shared<Expr>::eq` call on x86-64 (release vs debug)? Would 100,000 depth actually abort, or is the frame small enough to survive? (No measurement in-repo. The Debug fix design uses 100,000 as the test depth based on the Debug abort being empirically observed — `native_tests.rs:9` — but no equivalent measurement for eq exists.)
- The TODO.md fix description says "same pattern" for `_drop_block` — does this mean reusing `DropWorklistItem` as the pair carrier, or a new `EqWorklistItem<T>`? Not addressed in any existing doc.
