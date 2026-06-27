# Deep efficiency review — rust-unparser-backend batch 4

Commit reviewed: 66657a3e192b152178fb179099987c9942de2285 (base 014bbda9).
Scope: generator code in the diff (`fltk/unparse/gsm2unparser_rs.py`,
`fltk/fegen/gsm2tree_rs.py`, `fltk/unparse/gsm2unparser.py`). Runtime crate
`crates/fltk-unparser-core` is not in this diff range — not reviewed.

## Emitted runtime code (the hot path) — assessed clean

The per-rule / per-alternative / per-item Rust that gets emitted is tight and
faithful to the parser-backend precedent:

- `node.children()` re-fetched per `__item{M}` is free — the CST `children()`
  is `self.children.as_slice()` (`gsm2tree_rs.py:1155-1156`), a pointer+len, no
  allocation. The method-per-item structure means it can't be hoisted, but there
  is nothing to hoist.
- `acc.clone()` for optional items (`gsm2unparser_rs.py:280`) and for non-last
  alternative attempts (`:225`) are the design-sanctioned cheap Rc-bump clones of
  the persistent `DocAccumulator`.
- `add_accumulator(&child_result.accumulator)` (`:375`) merges by reference — no
  child-accumulator deep copy at the generator's call site.
- The generator already minimizes emitted code: single-variant / unlabeled
  Span-child validation drops the tuple binding and the `match` entirely
  (`_gen_validate_span_child`, `:442-452`), emitting just the bounds check. No
  vacuous matches or dead bindings.

The one unavoidable per-unparse heap allocation — `fltk_unparser_core::text("…")`
allocating a `String` for every literal occurrence on every unparse — is dictated
by the runtime crate's `Doc::Text(String)` / `text(&str)` API, which is outside
this diff. Not actionable here; flag only if the crate API is revisited.

## efficiency-1 — `_child_variants_for_rule` recomputed per item (generator-time)

File: `fltk/unparse/gsm2unparser_rs.py:363`, `:442` (callers of
`self._cst.num_child_variants(rule_name)`); `fltk/fegen/gsm2tree_rs.py:293-308`
(`_child_variants_for_rule`), `:805` (`num_child_variants`).

Problem: `num_child_variants(rule_name)` calls `_child_variants_for_rule(rule_name)`,
which iterates `model.types`, calls `class_name_for_rule_node` per entry, and
`sorted()`s the result — every time. `_gen_identifier_term_body` and
`_gen_validate_span_child` each call it once per item, so within a single rule the
same `rule_name` is re-walked and re-sorted once per identifier item and once per
INCLUDE-literal item across all its alternatives. `_child_variants_for_rule` is
also already called repeatedly per rule by the CST generator itself
(`gsm2tree_rs.py:442`, `:817`, `:997`, `:1763`) with no caching.

Consequence: pure generator-time CPU during `make gencode` / codegen. One-shot per
build and small per call (grammars have modest type counts), so impact is low and
scales only with grammar size, not with parsed input. Worth fixing because it is
trivially eliminable and the fix also helps the existing CST-generator callers.

Fix: memoize `_child_variants_for_rule` on `RustCstGenerator` keyed by `rule_name`
(a `dict` cache or `functools.cache` on a `rule_name`-only signature). The result
is a pure function of the immutable rule model, so caching is safe.

## Other categories

- Missed concurrency: N/A — single-threaded tree walk; sub-rule handles are
  read-locked one at a time, no parallelizable independent work.
- Recurring no-op updates / existence checks (TOCTOU) / unbounded memory /
  listener leaks: none introduced. The `if pos >= children.len()` guard before
  indexing is a legitimate panic-to-`None` conversion, not a TOCTOU pre-check;
  release builds elide the second bounds check.
