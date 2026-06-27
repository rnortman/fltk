# Deep review dispositions — batch 8 (rust-unparser-backend)

Commit reviewed: 69fa04efa8bdb0524c0b3f9c4a4026da66d0c941
Fixes committed on top; new HEAD reported to orchestrator.

No `scope-N` findings, so no scope-aggregate escalation.

---

errhandling-1:
- Disposition: Fixed
- Action: `fltk/fegen/genparser.py` `gen_rust_unparser` — widened the `--format-config`
  handler from `except (ValueError, FileNotFoundError)` to `except (ValueError, OSError)`
  (FileNotFoundError is an OSError subclass, so the not-found message still applies). Added
  regression test `test_cli_format_config_unreadable_exits_cleanly`
  (`tests/test_rust_unparser_generator.py`) asserting a directory `--format-config` exits 1
  with a clean `Error:` (SystemExit), not a raw traceback.
- Severity assessment: Real but minor — only affects the edge case of a `--format-config`
  path that exists but is unreadable / is a directory; produced a raw traceback instead of
  the CLI's clean exit-1 contract. Verified empirically: `IsADirectoryError` now yields
  `SystemExit(1)` + `Error: …`.

correctness-1:
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py` `_node_param` (now a `@classmethod`) — blanks
  Rust string-literal *content* via `_RUST_STR_LITERAL_RE` before the `\bnode\b` scan, so a
  re-emitted `text("node")` no longer false-matches and names an unused `node` param. Added
  regression test `test_suppressed_node_literal_names_param_underscore`.
- Severity assessment: Real build-break — a downstream grammar with a required-suppressed
  (or, under `python -O`, INLINE) literal whose text is/contains the word `node` generated an
  unparser that failed clippy `unused_variables` under `-D warnings`. Confirmed empirically:
  `kw := "node";` emitted `node:` (now `_node:`). The in-tree fixture has no such literal, so
  `make check` masked it.

correctness-2:
- Disposition: Fixed
- Action: `fltk/unparse/gsm2unparser_rs.py` — `_doc_to_rust_expr` now sets `self._uses_doc_type`
  whenever it emits a bare `Doc::` constructor (Nil/Nbsp/Line/SoftLine/HardLine); `generate()`
  builds the body sections before the header so the flag is set first; `_gen_header` gates the
  `use fltk_unparser_core::Doc;` import on that flag (always importing `DocAccumulator` /
  `UnparseResult`). Matches the parser backend gating its Regex/OnceLock import. Updated
  `test_generate_emits_header_and_struct` and added
  `test_doc_import_omitted_when_no_doc_expr` / `test_doc_import_present_when_doc_expr_emitted`.
- Severity assessment: Real build-break — a separator-less / spacing-less grammar (e.g.
  `r := a:/x/ . b:/y/;`) emitted no `Doc::` yet imported `Doc`, failing clippy `unused_imports`
  under `-D warnings`. Confirmed empirically before/after. Fixture (WS separators) still
  imports `Doc`; both fixture clippy lanes (python-on and python-off) pass `-D warnings`.

test-1:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_generator.py` `test_empty_alternative_body_is_passthrough`
  — added `assert "fn unparse_r__alt0(&self, _node: &cst::R, ...)" in body` so the
  empty-alternative `_node` parameter naming is actually asserted.
- Severity assessment: Test gap — inverting/dropping the `"node" if alt.items else "_node"`
  branch would have passed Python tests and surfaced only as a Rust `-D warnings` failure.

test-2:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_generator.py` — added
  `test_quantified_inline_literal_inner_uses_underscore_node`, calling `_gen_inner_methods`
  with a hand-built INLINE-literal multiple-quantified item (the reviewer's `r := !"x"+;`
  grammar is not constructible — the CST builder asserts INLINE => Identifier — so a direct
  unit call is used, mirroring the other term-body unit tests) and asserting the `__inner`
  signature uses `_node`.
- Severity assessment: Test gap — the quantified-INLINE inner `_node_param` call site was
  uncovered; hardcoding `node` there would fail only under a Rust `-D warnings` build.

reuse-1:
- Disposition: Fixed
- Action: `fltk/fegen/genparser.py` — extracted `_write_output_file(output_file, src)` and
  replaced the four byte-identical `output_file.write_text(...)` try/except blocks in
  `gen_rust_cst` / `gen_rust_parser` / `gen_rust_unparser` / `gen_rust_lib`. (The distinct
  `.pyi`-stub write block, with its own message, is left as-is.)
- Severity assessment: Maintainability — duplication the diff extended to four sites; one
  maintenance point now. Pure extraction, behavior unchanged; full suite + CLI tests pass.

reuse-2:
- Disposition: Fixed
- Action: `fltk/fegen/genparser.py` — extracted `_validate_cst_mod_path(cst_mod_path)` and
  replaced the two identical `--cst-mod-path` validation blocks in `gen_rust_parser` /
  `gen_rust_unparser`.
- Severity assessment: Maintainability — same as reuse-1; pure extraction, behavior unchanged.

quality-1:
- Disposition: Fixed (duplicate of correctness-1)
- Action: Resolved by the `_node_param` string-literal blanking fix above
  (`fltk/unparse/gsm2unparser_rs.py`); same root cause and same regression test.
- Severity assessment: Same as correctness-1 — clippy `unused_variables` build-break for a
  `"node"` literal.

security (notes-deep-security-r8): no findings.
efficiency (notes-deep-efficiency-r8): no findings.
