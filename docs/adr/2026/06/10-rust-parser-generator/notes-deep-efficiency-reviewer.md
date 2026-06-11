# Efficiency review — Phase 2 Rust parser generator

Reviewed: `490bccf..b95f772` (HEAD b95f772). Design: `docs/adr/2026/06/10-rust-parser-generator/design.md`.
Style note: concise, precise, complete, unambiguous; no padding. Audience: smart LLM/human.

Scope note: `memo.rs` / `terminalsrc.rs` costs (SipHash `HashMap` cache, unanchored `consume_regex` scan — already `TODO(consume-regex-anchor)`) are Phase 1 base code, not in this diff; not re-raised.

## efficiency-1: `extend_children(&owned)` clones children from a value that is immediately dropped

- `fltk/fegen/gsm2parser_rs.py:613` and `:730` emit `result.extend_children(&{item_var}.result);` for inline-to-parent items (sub-expressions and `+`/`*` loops). E.g. generated `tests/rust_cst_fegen/src/parser.rs:293,522,1180` (inside `while let` loops, per iteration) and `:138,316,...` (per item).
- `extend_children(&Self)` is `self.children.extend(other.children.iter().cloned())` (e.g. `tests/rust_parser_fixture/src/cst.rs:309-311`). Each clone is an Arc refcount bump for node children and an `Arc<SourceTextInner>` bump for span children (`Span` is `Clone` via `source: Option<Arc<_>>`, `crates/fltk-cst-core/src/span.rs:148-149`). The source `{item_var}.result` is owned and dropped right after — so every inlined child pays an atomic inc + atomic dec + the donor `Vec`'s drop, where a move (`Vec::append`) would pay nothing.
- **Consequence**: per-child, per-loop-iteration cost on the parse hot path for every grammar using sub-expressions or repetition (fegen itself: 10 `extend_children` sites). Atomic RMW pairs scale with input size × inlined-child count; pure waste, the donor is dead.
- **Fix**: the call sites own the donor — emit a consuming append instead. Add a consuming variant to the gsm2tree_rs-generated node API (e.g. `extend_children_owned(other: Self)` / `take_children() -> Vec<_>` implemented with `Vec::append`) and have `_gen_append_code` / `_gen_item_multiple` emit `result.extend_children_owned({item_var}.result);`. Until the CST API grows that method, this is blocked on gsm2tree_rs; flagging so it lands rather than ossifying.

## efficiency-2: placeholder span Arc-clones the source on every alternative attempt, including failures

- `fltk/fegen/gsm2parser_rs.py:433-436` (and `:601-604` for multiple-item parsers) emit
  `let mut result = cst::X::new(Span::new_with_source(pos, -1, self.terminals.source_text()));`
  at the top of every `parse_X__altN` body — before the first item is even tried. `Span::new_with_source` clones the source Arc (`crates/fltk-cst-core/src/span.rs:211-217`). Every success path overwrites it via `result.set_span(Span::new_with_source(...))` (second Arc bump; placeholder dropped = dec); no path returns a node without `set_span`, so the placeholder's source is never observed.
- **Consequence**: one atomic inc+dec pair per alternative attempt. Alternative bodies are not memoized (only `apply__parse_<rule>` is), so attempts are O(positions × alternatives) over a parse, and in alternative chains most attempts fail at item0 — the placeholder Arc traffic is the bulk of a failed attempt's cost. Per-parse hot path, scales with input length and grammar branching.
- **Fix**: emit `Span::unknown()` (exists precisely as the "node constructed without a real span" sentinel, span.rs:184-194) or `Span::new_sourceless(pos, -1)` for the placeholder; keep the final source-bearing `set_span` unchanged. One-line generator change, no observable behavior change, removes ~63 Arc-clone sites in the two committed parsers (23 in `rust_parser_fixture`, 40 in `rust_cst_fegen`).

No other findings. Generator-side (Python) code paths are one-shot codegen, costs negligible; regex table dedup, conditional helper emission, and lazy `OnceLock` regex compilation are all done correctly.
