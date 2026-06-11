# Adversarial validation: TODO(extend-children-owned)

Concise. Precise. No fluff. Audience: LLM/human reviewer.

---

## Claim under review

> `extend_children(&Self)` clones every child Arc even though the donor node is
> immediately dropped after the call (inline-to-parent sub-expression and `+`/`*`
> loop paths). A consuming variant `extend_children_owned(other: Self)` using
> `Vec::append` would avoid the atomic inc+dec pairs per child on the parse hot
> path. Blocked on `gsm2tree_rs.py` adding the method to the generated CST node
> API. Location: `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`,
> `_gen_append_code`), `fltk/fegen/gsm2tree_rs.py` (generated `impl <Node>`
> blocks).

---

## Verified facts

### 1. `extend_children` signature — confirmed `&Self`, clones via iterator

`gsm2tree_rs.py:726-728` generates for every node struct:

```rust
pub fn extend_children(&mut self, other: &Self) {
    self.children.extend(other.children.iter().cloned());
}
```

The `cloned()` call on `other.children.iter()` clones each `(label, child)` tuple.
Labels are `Option<LabelEnum>` (Copy or cheap Clone). Children are `(Option<LabelEnum>, XxxChild)`
where `XxxChild` enum variants holding node-typed children contain `Shared<T>` = `Arc<RwLock<T>>`.
Cloning `Shared<T>` calls `Arc::clone`, which is the atomic reference-count increment.
(`crates/fltk-cst-core/src/shared.rs:78-83`)

Span-typed children (`XxxChild::Span(Span)`) clone the `Span`, which internally clones an `Arc<SourceText>`.
Both paths do at least one atomic inc-per-child.

### 2. Call sites — exhaustive list

All `extend_children` calls in generated parsers (as of the current committed fixtures):

**`tests/rust_cst_fegen/src/parser.rs`** (15 occurrences total, 11 `extend_children` calls):
- Line 144: `result.extend_children(&item0.result)` — single-item (non-loop), inline sub-expression from
  `parse_grammar__alt0`. `item0` is local; goes out of scope after the `if let` block.
- Line 299: `result.extend_children(&one_result.result)` — loop body (`while let Some(one_result) = {...}`),
  `parse_alternatives__alt0__item1`. `one_result` is the loop variable, dropped at top of each iteration.
- Line 322: `result.extend_children(&item1.result)` — single-item, `parse_alternatives__alt0`.
- Line 488, 607, 716, 1186, 1200: similar single-item and loop patterns.

**`tests/rust_parser_fixture/src/parser.rs`** (4 occurrences):
- Line 373: single-item, `parse_items__alt0`
- Line 436: single-item, `parse_zero_items__alt0`
- Line 911: single-item, `parse_grouped__alt0`
- Line 1007: single-item, `parse_rec_via_sub__alt0`

**Generator source** (`gsm2parser_rs.py`):
- Line 687 (`_gen_item_multiple`): loop body — `result.extend_children(&one_result.result);`
- Line 805 (`_gen_append_code`): non-loop inline sub-expr — `return f"result.extend_children(&{item_var}.result);"`

### 3. Is the donor always dropped immediately? — mostly yes, with nuance

**Loop path** (`_gen_item_multiple`, line 687): the generated pattern is:

```rust
while let Some(one_result) = {
    /* consume_expr */
} {
    pos = one_result.pos;
    result.extend_children(&one_result.result);
}
```

`one_result` is the `while let` binding. Its type is `ApplyResult<cst::NodeType>` where
`ApplyResult<T> { pos: i64, result: T }` (`fltk-parser-core/src/memo.rs:19`). `one_result.result`
is `cst::NodeType` — a plain struct (not `Shared<T>`), owned on the stack. `one_result` is dropped
at the end of each loop iteration. So yes: the donor is a stack-local by-value node, dropped after
`extend_children` returns each iteration.

**Non-loop inline path** (`_gen_append_code`, line 805): the generated pattern is:

```rust
if let Some(item0) = self.parse_xxx(pos) {
    pos = item0.pos;
    result.extend_children(&item0.result);
}  // item0 dropped here
```

`item0.result` is again `cst::NodeType` (plain struct, by value), dropped at closing `}`.
The donor is local and goes out of scope immediately after.

**In no case** is the donor behind a `Shared<T>` or any lock at the point of the `extend_children` call.
The inline/multiple-return functions return `Option<ApplyResult<cst::NodeType>>` (unshared by-value node),
not `Option<ApplyResult<Shared<cst::NodeType>>>`. Only memoized top-level rule parsers return
`Option<ApplyResult<Shared<cst::NodeType>>>` — those never call `extend_children`.

This is confirmed by the function signatures in the generated files:
- Inline/loop helpers return `Option<ApplyResult<cst::Grammar>>` (bare struct).
- Memoized wrappers return `Option<ApplyResult<Shared<cst::Grammar>>>`.

`_gen_item_multiple` at line 663: `fn {fn_info.name}(&mut self, mut pos: i64) -> Option<ApplyResult<cst::{parent_class_name}>>` — no `Shared<>`.

### 4. Is the donor behind a lock/Shared wrapper that complicates consuming?

No. At every `extend_children` call site in generated parser code, the donor is a bare
`cst::NodeType` on the stack inside an `ApplyResult<cst::NodeType>`. It is not wrapped in
`Shared<T>`. Moving it (consuming) is structurally possible. The borrow checker comment
in the generated code (`gsm2tree_rs.py:723-724`) references the data-struct-level self-extend
concern — not a wrapping constraint.

### 5. `Vec::append` semantics if consuming variant existed

`Vec::append(&mut self, other: &mut Vec<T>)` moves all elements from `other` into `self`,
leaving `other` empty, with zero per-element allocations. It would avoid all atomic inc+dec
pairs on the `Shared<T>` children. Children holding `Span` (which contains `Arc<SourceText>`)
would also avoid those atomic ops.

### 6. Perf context — how significant?

Benchmark record (`crates/fltk-cst-spike/benches/traverse.rs:25-29`):
- Uncontended `RwLock` read per child: ~7.9 ns (x86_64, release, single thread).
- Each `Arc::clone` (atomic inc): typically 1–3 ns uncontended on modern x86_64.
- Each `Arc::drop` (atomic dec + possible dealloc): similar or slightly more.

The claimed "8ns benchmark context" refers to the per-child RwLock read cost, not the Arc
clone/drop cost. The Arc inc+dec pair (~2–6 ns combined) is a fraction of the lock cost,
but it fires on every child of every inline sub-expression and every loop iteration. Whether
this is measurable depends on child density in grammars; for small nodes (1–3 children), the
difference is 2–18 ns per `extend_children` call. For a real parse of a large grammar file,
the hot path calls `extend_children` many times; aggregate impact is non-trivial but likely
below 5% of total parse time without profiling evidence.

### 7. Stated blocker — accurate?

The TODO (`gsm2parser_rs.py:681-685`) says: "Blocked on `gsm2tree_rs.py` adding the method
to the generated CST API." This is accurate: `gsm2tree_rs.py` generates the `impl NodeType`
block (`_node_block` → `_native_per_label_methods`, line 729-730) and currently only emits
`extend_children(&mut self, other: &Self)`. A consuming variant would need to be added to the
same emission block in `gsm2tree_rs.py`. No such method exists in any generated file
(`src/cst_generated.rs`, `src/cst_fegen.rs`, `tests/rust_cst_fegen/src/cst.rs`,
`tests/rust_parser_fixture/src/cst.rs`).

### 8. Any additional blockers not stated?

One non-obvious constraint: `extend_children_owned(other: Self)` on the data struct is callable
only if the caller possesses an owned `T` (not `Shared<T>`). At the current call sites this is
always true (callers hold `ApplyResult<T>` by value). But if a future call site holds `Shared<T>`,
consuming would require `Arc::try_unwrap` (succeeds only if refcount == 1, else returns `Err`),
making ownership-consuming semantics conditionally unavailable. At present this is not a blocker
since all existing call sites own the donor by value.

No other blockers are present beyond the stated one.

### 9. Deeper structural issue?

The root pattern is: generated inline/`+`/`*` helpers return a by-value `cst::NodeType`, but the
API provided (`extend_children`) does not exploit that ownership. The mismatch exists because
`extend_children` was designed for general use (including from Python handles and from
`Shared<T>`-holding callers), while the parser-internal call sites have a strictly narrower
contract (always by-value, always immediately dropped). The TODO captures this correctly.

---

## Summary verdict

All factual claims in the TODO are accurate:
- `extend_children` does take `&Self` and does clone Arcs via `iter().cloned()`.
- The donor is a stack-local by-value `cst::NodeType`, not behind a lock, and is dropped
  immediately after the call at every generated call site.
- `Vec::append` on a consuming variant would avoid the atomic pairs.
- The only stated blocker (adding the method in `gsm2tree_rs.py`) is real and correct.
- No unstated blockers exist for the current call sites.
- Perf impact: real but modest (sub-5% estimated); measurable only with grammar-scale profiling.
