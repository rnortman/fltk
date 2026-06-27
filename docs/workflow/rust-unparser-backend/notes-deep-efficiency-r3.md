# Deep efficiency review — rust-unparser-backend batch 3

Commit reviewed: e6a682cb883db43d6df2cc7215cb982121934254 (base d622ff7905362ebc71b3f232cae8b801db9bdd0f)
Scope: `fltk/unparse/gsm2unparser_rs.py` (rule-entry + alt/item dispatch scaffold, `_doc_to_rust_expr`) and `tests/test_rust_unparser_generator.py`.

No findings.

(Reviewed both the generator code and the Rust it emits. The emitted dispatch threads
`DocAccumulator` by value using cheap refcount-bump clones — documented at
`accumulator.rs:6` — and clones minimally: only non-last alternatives and optional
items clone, the last alternative / required items move. RULE_START pushes are applied
once before the alternative loop, not per attempt. The generator resolves each rule's
class name once per rule and reuses it down the call chain; `_doc_to_rust_expr` recurses
only over `Concat`. No redundant computation, no hot-path bloat, no unbounded growth.)
