# Deep efficiency review — batch 5 (rust-unparser-backend)

Commit reviewed: 5f7b5cb1d33150b1125daf6e0f19c4051ab28c30 (base f9ed936)
Scope: `crates/fltk-unparser-core/src/{doc.rs,lib.rs}`, `fltk/unparse/gsm2unparser_rs.py`
(regex term body, sub-expression dispatch, before/after-item spacing).

No findings.

Checked and cleared:
- Spacing emission (`_item_spacing_lines`): emits nothing in the default-config case
  (`get_before/after_spacing` return `None` → `[]`), so unconfigured grammars add zero
  per-unparse runtime work; configured spacing adds one Rc per spec, matching Python parity.
- `before_spec`/`after_spec` (doc.rs): single Rc alloc each, no deep copy.
- Regex body: one unavoidable `span.text()` String alloc moved into `Doc::Text`; no redundant
  `span.text()` or `node.children()` calls (prelude binds `children` once per item method).
- Sub-expression `__alts` dispatch: established cheap clone-then-move backtracking
  (no clone on the single-alt / last-alt path).
- Generator-time variant lookups (`num_child_variants`, `child_enum_name`) are memoized via
  `_child_variants_cache`; no repeated grammar walks.
- Pre-existing `add_accumulator`/`doc()` clone cost is unchanged in this diff (addressed in
  deep-r1); out of scope here.
