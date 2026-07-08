# Implementation log — formatter blank-line preservation

## Increment 1 — two-part fix + full test plan

Single coherent increment: one bug fix with two co-required components (fixing either alone
leaves the pinned gear-demo test red) plus the §5 test plan and the mandated generated-code
regeneration.

Shipped:

- **Component A (config layer):** `fltk/unparse/fmt_config.py:503-509` —
  `_process_trivia_preserve_statement` now mutates `config.trivia_config` in place (creates a
  default `TriviaConfig` if absent, then sets `preserve_node_names`) instead of replacing the
  object, so a previously parsed `preserve_blanks` survives regardless of statement order.
- **Component B Python (runtime helper):** `fltk/unparse/pyrt.py:80-98` — new
  `count_whitespace_newlines(child, terminals)`: span child → `count_span_newlines`; node child
  → its span-text newline count iff the text is non-empty and all-whitespace, else 0.
- **Component B Python (generator):** `fltk/unparse/gsm2unparser.py:1033-1050` — the
  `_count_newlines_in_trivia` loop body is now an unconditional
  `count += pyrt.count_whitespace_newlines(child, self.terminals)` (no `is_span` conditional);
  docstring at `:970-977` updated.
- **Component B Rust (generator):** `fltk/unparse/gsm2unparser_rs.py:1501-1560` —
  `_gen_count_newlines_in_trivia_method` now emits an exhaustive `match` with the `Span` arm
  (unchanged) plus one whitespace-only counting arm per node-typed `TriviaChild` variant
  (`node.read()` → `guard.span().text_str()` → count iff `!t.is_empty() && t.chars().all(char::is_whitespace)`).
- **TODO(rule-preserve-blanks):** `TODO.md` entry + comments at
  `gsm2unparser.py:1170`/`:1355` and `gsm2unparser_rs.py:1566` (pre-existing unconsumed
  rule-level `preserve_blanks`, out of scope per design).
- **Regen:** `crates/fegen-rust/src/unparser.rs` regenerated (fegen trivia is multi-variant, so
  the counter changed); the two fixture unparsers are byte-identical (Span-only) and unchanged;
  `.pyi` stubs re-normalized by `make fix`.
- **Tests:**
  - `fltk/unparse/test_fmt_config.py` — `TestTriviaConfigDirectiveOwnership` (tests 1-3).
  - `fltk/unparse/test_pyrt.py` — `TestCountWhitespaceNewlines` (test 6: span / whitespace node /
    comment node / empty-span node).
  - `fltk/unparse/test_unparser.py` — parsed-config clobbering-order direct-span (test 4);
    custom-trivia node-whitespace survives (5a); comment-terminator not counted (5b).
  - `tests/test_rust_unparser_generator.py` — rewrote the former `_multi_variant_uses_if_let`
    test into `_node_variant_whitespace_arm` (Span arm unchanged + node arm) and added
    `_all_node_variants_no_span_arm` (test 8) and `_preserve_blanks_from_parsed_clobbering_config`
    (test 7).
  - `fltk/lsp/test_gear_demo.py` — created
    `test_formatting_preserves_blank_lines_between_items` (test 9); idempotency test unchanged (10).
- Deviation: the design referenced an existing `test_formatting_preserves_leading_comment` in the
  gear suite; that test does not exist in the tree, so leading-comment preservation is asserted
  inside the new blank-line test instead.
