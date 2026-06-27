# Deep efficiency review — batch 6 (rust-unparser-backend)

Commit reviewed: ae90f84671cf03d4b6e2aeed244bab3df1b1d633 (base 663b2734)
Scope: `fltk/unparse/gsm2unparser_rs.py` (generator); emitted Rust runtime perf is the
priority. New in this batch: item-level anchor push/pop, quantified `+`/`*` loop +
`__inner` method, and item-level Omit/RenderAs disposition handling.

## No findings.

Checked, nothing actionable:

- **Quantified loop (`_gen_quantified_loop_body`).** `acc.clone()` per iteration and
  `node.children().len()` in the loop condition are both cheap: `DocAccumulator` is an
  Rc-linked chain whose `Clone` is a refcount bump (crate `doc.rs:18`, `accumulator.rs`),
  and `children()` is a zero-cost slice accessor (`self.children.as_slice()`,
  `gsm2tree_rs.py:1167`). The per-iteration clone is load-bearing: it lets the failed-
  occurrence break path keep the last-successful `acc` (Rust can't recover a moved value),
  same pattern as the optional-item path. `match_count` (usize, `+` only) vs a bool is
  sub-nanosecond and LLVM-collapsible — not worth a change.

- **Disposition handling (`_item_disposition_success_lines`).** Omit/RenderAs items clone
  `acc` into the item call and discard the returned accumulator. For an Omit'd
  rule-reference this means the child subtree is fully unparsed into a `Doc` that is then
  dropped — genuinely wasted O(subtree) work. NOT flagged: it is load-bearing for
  cross-backend parity. The recursive child unparse can return `None` (e.g. a required
  sourceless span) and that failure must propagate `?`, exactly as the Python backend does;
  skipping the recursion would turn a Python-`None` case into a Rust-`Some`, a failure-mode
  divergence. The parity contract is rendered-string equality, but the Some/None outcome
  must also match, so this cannot be a clean Rust-only optimization. Out of scope per
  design §2.2 (parity changes are both-backends decisions).

- **Item anchors (`_item_anchor_lines`).** Emits only push/pop accumulator state
  transitions, all cheap Rc-based, only when a label/literal anchor is configured (returns
  `[]` in the common default-config case). No per-render overhead added when unconfigured.

- **Concurrency / memory.** The unparse walk is an inherently sequential accumulator-
  threaded tree walk; no independent ops to parallelize. No unbounded structures or leaks
  introduced — accumulator/Doc growth tracks output size, as required.
