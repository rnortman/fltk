# Deep efficiency review — rust-unparser-backend (batch 1)

Commit reviewed: 285064a9a37c76f56f6fa1b44d4c553c34f49bcc (base 8a29f254).
Scope: `crates/fltk-unparser-core/src/{doc,accumulator,resolve}.rs` (+ Cargo wiring).
Renderer + generator + PyO3 wrapper are not in this batch; not reviewed.

The code is a careful, faithful port of `accumulator.py` / `resolve_specs.py` /
`combinators.py`, with `Rc` threading deliberately used to share unchanged subtrees.
Findings below are Rust-specific avoidable costs or scale patterns, not parity gaps.

---

## efficiency-1 — `DocAccumulator::doc()` clones an `Rc` per chain node instead of borrowing

File: `crates/fltk-unparser-core/src/accumulator.rs:240-249`

```rust
let mut current = self.head.clone();          // :242
while let Some(node) = current {
    docs.push(node.doc.clone());
    current = node.tail.clone();              // :245
}
```

The chain walk bumps and later drops a refcount for every `DocNode` it visits
(`self.head.clone()` plus one `node.tail.clone()` per node) purely to traverse.
The Python original (`accumulator.py:121-124`) walks by reference rebinding with no
copy at all, so the Rust port does ~2N refcount ops the Python does not. Only
`node.doc.clone()` (producing an owned `Doc` for `concat`) is actually required.

Consequence: per-call constant-factor overhead proportional to N = number of docs
accumulated at this nesting level. N is grammar/input-driven (items at one level,
attacker-controlled for untrusted input — the same hazard the iterative `Drop`
comment flags). `doc()` is on the unparse hot path: it runs once per
`add_accumulator`, `pop`, and `pop_join`, i.e. once per rule/level as the generated
unparser walks the whole CST. The Python `doc` property even carries a
`# TODO: This should be memoized for performance.` — this path is a known hot spot,
and the port adds refcount churn on top of it.

Fix: traverse by borrow, leaving only the necessary `doc` clone:
```rust
let mut current = &self.head;
while let Some(node) = current {
    docs.push(node.doc.clone());
    current = &node.tail;
}
```

---

## efficiency-2 — Join separator is re-resolved once per gap, not once per join

File: `crates/fltk-unparser-core/src/resolve.rs:121-125` (expansion) and
`:386`, `:413`, `:482`, `:622` (per-gap resolution)

`expand_joins` turns an M-element `Join` into M-1 `SeparatorSpec`s, each holding the
*same* `separator` (`preserved_trivia: Some(separator.clone())`, an `Rc` clone of one
shared node). During resolution every one of those specs hits a
`resolve_rc(trivia)` call (`mutate_after_sep` :386, `mutate_sep_before` :413,
`mutate_standalone_sep` :482, `resolve_spacing` :622), so the identical separator
subtree is run through the full 4-pass pipeline M-1 times. Resolution is
deterministic and the input is byte-identical each time, so the M-1 results are all
equal — the repeats are pure waste. (Faithful to Python, which also calls
`resolve_spacing_specs(sep_spec.preserved_trivia)` per gap.)

Consequence: cost scales with the number of join elements. For `join from X to Y`
over a large repeated list (e.g. thousands of statements), the separator is resolved
thousands of times. Each resolution is small but allocates several `VecDeque`/`Vec`
working buffers (`resolve_concat_patterns`), so the constant factor is non-trivial at
scale; this is the unparser's per-render cost for any large joined sequence. Bounded
in practice because separators are restricted to simple docs (the generator rejects
group/nest/join separators), but still O(M) redundant pipeline runs.

Fix direction: resolve the join separator once and reuse it. Since all the
`preserved_trivia` slots share one `Rc`, a small cache keyed on `Rc::as_ptr` (or
resolving `separator` once in `expand_joins` and storing the resolved form) eliminates
the repeats without changing output. Parity is preserved because each repeat yields
the same value today.

---

## efficiency-3 — `extract_boundary_specs` shifts the Vec front in a loop

File: `crates/fltk-unparser-core/src/resolve.rs:197-216`

```rust
trailing_specs.insert(0, docs.pop().expect("last() was Some"));   // :204
...
leading_specs.push(docs.remove(0));                               // :212
```

`docs.remove(0)` shifts every remaining element left (O(n) each); `insert(0, …)`
shifts the growing `trailing_specs` (O(t) each). Building l leading specs is O(l·n)
and t trailing specs is O(t²). (Matches Python's `docs.pop(0)` / `insert(0, …)`, so
not a regression — but it is a recognizable anti-pattern that Rust makes cheap to
avoid.)

Consequence: n is the child count of the Concat level being processed (can be large
for big sequences/lists); l and t are the counts of consecutive boundary specs at the
ends (usually small). So typically near-linear, but super-linear at any level that
accumulates many leading/trailing specs. `extract_boundary_specs` runs once per
Concat level across the whole tree.

Fix: collect the trailing run by popping from the end then `.reverse()` once
(O(t) total), and take the leading run with `split_off`/`drain(..k)` (O(n) total)
instead of repeated front removals.

---

## efficiency-4 — `resolve_spacing_specs` clones the whole top node only to discard it

File: `crates/fltk-unparser-core/src/resolve.rs:39-42`

```rust
let resolved = resolve_rc(&Rc::new(doc.clone()));
```

`doc.clone()` shallow-clones the top node (for a top-level `Concat` of width W, that
is a W-`Rc` `Vec` allocation + W refcount bumps). `resolve_rc` immediately calls
`expand_joins`, which for a `Concat` builds a fresh `concat_rc(...)` and drops the
clone — so the cloned top `Vec` is never used. Python passes the doc by reference with
no copy.

Consequence: one wasted O(W) allocation+refcount pass per top-level
`resolve_spacing_specs` call (once per unparse). Negligible relative to the four full
tree passes that follow; only visible at very wide top-level Concats. Lowest-value
item here — listing for completeness.

Fix (optional): have the top-level pass borrow `&Doc` into the first `expand_joins`
step without materializing an owned `Rc` of the root, or accept that this is in the
noise and leave it.
