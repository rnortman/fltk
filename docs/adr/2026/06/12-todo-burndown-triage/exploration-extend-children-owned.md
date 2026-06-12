# Adversarial validation: TODO(extend-children-owned)

Concise. Precise. No fluff. Audience: LLM/human reviewer.
HEAD 5d94733. A prior exploration of this same TODO was written at
`docs/adr/2026/06/11-todo-burndown/exploration-extend-children-owned.md`; this
document re-validates from source rather than re-using those conclusions.

---

## Claim under review (verbatim from TODO.md:13)

> `extend_children(&Self)` clones every child Arc even though the donor node is
> immediately dropped after the call (inline-to-parent sub-expression and `+`/`*`
> loop paths). A consuming variant `extend_children_owned(other: Self)` using
> `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot
> path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node
> API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`,
> `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>`
> blocks). Re-open only with profiling evidence.

---

## Verified facts

### 1. `extend_children` signature and clone semantics — accurate

`fltk/fegen/gsm2tree_rs.py:871-873` emits for every generated node struct:

```rust
pub fn extend_children(&mut self, other: &Self) {
    self.children.extend(other.children.iter().cloned());
}
```

`other.children` is a `Vec<(Option<LabelEnum>, XxxChild)>`. `XxxChild` variants
holding CST nodes contain `Shared<T>` = `Arc<RwLock<T>>` (`crates/fltk-cst-core`).
`iter().cloned()` calls `Clone` on each element, invoking `Arc::clone` (atomic
refcount increment) per node-typed child. Span-typed children hold `Span` which
contains `Option<Arc<SourceTextInner>>` — also cloned. Both paths perform at least
one atomic increment per child.

The claim "clones every child Arc" is accurate.

### 2. Call site locations — accurate

Generator: `fltk/fegen/gsm2parser_rs.py`
- Line 712 (`_gen_item_multiple`, loop body): `result.extend_children(&one_result.result);`
- Line 830 (`_gen_append_code`, non-loop inline): `return f"result.extend_children(&{item_var}.result);"`

These are the two locations cited. No other call sites exist in the generator.

Generated fixtures confirm the pattern:
- `tests/rust_cst_fegen/src/parser.rs:327,557,1216` — loop path (`while let Some(one_result)`)
- `tests/rust_cst_fegen/src/parser.rs:171,350,516,636,745,1230` — non-loop inline path (`if let Some(itemN)`)
- `tests/rust_parser_fixture/src/parser.rs:373,436,911,1007` — non-loop inline path

### 3. Is the donor always dropped immediately? — yes, with no exceptions found

**Loop path** (generated at `gsm2parser_rs.py:698-718`): pattern is
```rust
while let Some(one_result) = { consume_expr } {
    if one_result.pos <= pos { break; }
    pos = one_result.pos;
    result.extend_children(&one_result.result);
}
```
`one_result` is the `while let` binding, type `ApplyResult<cst::NodeType>` — a
plain (non-`Shared`) struct on the stack. It is dropped at the closing `}` of
each iteration. Confirmed at `tests/rust_cst_fegen/src/parser.rs:319-331`:
`parse_alternatives__alt0__item1` returns `Option<ApplyResult<cst::Alternatives>>`,
where `one_result.result` is `cst::Alternatives` (bare struct, not `Shared<>`).

**Non-loop inline path** (generated at `gsm2parser_rs.py:533-550`): pattern is
```rust
if let Some(itemN) = self.parse_xxx(pos) {
    pos = itemN.pos;
    result.extend_children(&itemN.result);
}  // itemN dropped here
```
`itemN.result` is again `cst::NodeType` (bare struct). Dropped at `}`.

**Key structural fact**: Only memoized top-level rule wrappers (`_emit_apply_wrapper`,
`gsm2parser_rs.py:466-481`) return `Option<ApplyResult<Shared<cst::NodeType>>>`.
Inline/loop helpers (produced by `_gen_item_multiple`, `_gen_alternative`,
`_gen_subexpr_term`) return `Option<ApplyResult<cst::NodeType>>` — no `Shared<>`.
The `extend_children` call sites are exclusively in the latter class of functions.
No case exists where the donor is behind a `Shared<T>` or lock at the point of call.

The "immediately dropped" claim is accurate. No retained donors exist anywhere in
the generated call graph.

### 4. Is the `Vec::append` fix feasible? — yes

A consuming variant `extend_children_owned(mut other: Self)` using
`self.children.append(&mut other.children)` would move all elements without any
per-element `Clone`. Since all existing call sites own the donor by value inside an
`ApplyResult<cst::NodeType>`, the consuming call would compile directly with no
`Arc::try_unwrap` or other fallibility.

The borrow-checker comment in the generated code (`gsm2tree_rs.py:868-870`) concerns
self-extend (`node.extend_children(node)`) at the data-struct level — not a constraint
on the parser call sites, which never self-extend.

### 5. Stated blocker — accurate

TODO says "Blocked on `gsm2tree_rs.py` adding the method to the generated CST node
API." Confirmed: `gsm2tree_rs.py` emits the native `impl NodeType` block
(`_node_impl_block` → `extend_children` emission at lines 863-873). No consuming
variant is emitted anywhere. Grep for `extend_children_owned` across the entire repo
(including generated `.rs` files) returns zero hits. The blocker is real and accurate.

### 6. Unstated blockers

None found. If `impl Drop` for nodes were added (see `docs/adr/2026/06/11-rust-cst-debug-depth/design.md:170`),
`E0509` ("cannot move out of a type that implements `Drop`") would forbid moving
fields out of a node struct by value — but `extend_children_owned` would take the
whole `other: Self` by value (no partial field move), so `E0509` does not apply. The
debug-depth ADR explicitly verified this: "the future `extend-children-owned` TODO is
compatible (it would `Vec::append` through `&mut`, not move fields)."

### 7. Is this a symptom of a deeper problem?

The root mismatch: `extend_children` was designed for general-purpose use (including
Python-side `extend_children` on `PyHandle` objects, which hold `Shared<T>`), so
it takes `&Self`. The parser-internal call sites have a strictly narrower contract
(always by-value, always immediately dropped) that is not exploited. The TODO
correctly characterizes the pattern.

### 8. Profiling evidence in-tree

`crates/fltk-cst-spike/benches/traverse.rs` exists (Criterion benchmark). It
measures uncontended `RwLock` read per child (~7.9 ns, recorded 2026-06-10) and
tree build (~58 ns per child, dominated by Arc/RwLock allocation). It does **not**
measure `extend_children`, clone-per-child cost, or parse throughput. There is no
in-tree profiling measurement of `extend_children` overhead, parser throughput, or
any workload that would quantify the cost of the atomic inc+dec pairs at issue.

The "Re-open only with profiling evidence" clause is consistent with the in-tree
state: no such evidence exists.

---

## Verdict

All factual claims in the TODO are accurate:
- Signature, clone semantics, and Arc-per-child cost: confirmed.
- Both cited generator locations (`_gen_item_multiple:712`, `_gen_append_code:830`) are correct.
- Donor is always a by-value stack-local, never behind `Shared<T>`, dropped immediately.
- `Vec::append`-based fix is structurally feasible at all existing call sites.
- The stated blocker (adding the consuming variant in `gsm2tree_rs.py`) is real and the only blocker.
- No profiling evidence for the cost exists in-tree; "re-open only with profiling evidence" is appropriate.
