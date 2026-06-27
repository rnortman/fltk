# Judge verdict — deep review

Phase: deep. Base 7723f7e..HEAD fcf153c. Round 1.
Notes: 7 reviewer files (errhandling, correctness, security, test, reuse, quality, efficiency); 8 findings.
Security and efficiency: no findings. No TODOs added in this diff; no `scope-N` findings.

## Added TODOs walk

None. `git --no-pager diff base..HEAD | grep TODO/FIXME/XXX` returns nothing; no disposition is `TODO(slug)`. Section omitted of content by absence.

## Other findings walk

### errhandling-1 — Fixed
Claim: `gen_rust_unparser`'s `--format-config` handler caught only `(ValueError, FileNotFoundError)`; `parse_format_config_file` (`plumbing.py:247-253`) pre-checks `.exists()` then opens bare, so `PermissionError`/`IsADirectoryError` propagate. Consequence: raw traceback instead of the CLI's clean `Error: …` / exit-1 contract.
Diff at `genparser.py:455`: handler widened to `except (ValueError, OSError) as e:`. `FileNotFoundError` is an `OSError` subclass, so the existing not-found message (raised before `open()`) still surfaces cleanly. Regression test `test_cli_format_config_unreadable_exits_cleanly` (directory `--format-config` → `SystemExit(1)` + `Error:`) — runs green.
Assessment: fix addresses the consequence at the named line; test pins it. Accept.

### correctness-1 — Fixed
Claim: `_node_param`'s `re.search(r"\bnode\b", line)` over rendered body text false-matches `node` inside an emitted string literal (required-suppressed / INLINE `"node"` → `text("node")`), naming an unused `node` param. Consequence: generated unparser fails clippy `unused_variables` under `-D warnings` for any grammar with a `"node"` literal; fixture masks it.
Diff at `gsm2unparser_rs.py:161-191`: `_node_param` (now `@classmethod`) blanks string-literal content via `_RUST_STR_LITERAL_RE = r'"[^"\\]*(?:\\.[^"\\]*)*"'` (standard escaped-string regex; generator emits no raw strings — literals route through `rust_str_lit`) before the `\bnode\b` scan. A genuine `node.children()` use is never inside a string literal, so blanking is lossless. Test `test_suppressed_node_literal_names_param_underscore` (`kw := "node";` → `_node:` param, `text("node")` still emitted) — green.
Assessment: fix is correct and complete; test pins both directions. Accept.

### correctness-2 — Fixed
Claim: `Doc` imported unconditionally but referenced only by bare `Doc::` constructors from `_doc_to_rust_expr`; a separator-less/spacing-less grammar emits none → unused-import failure under `-D warnings`. Diverges from parser backend's conditional Regex/OnceLock import.
Diff: `_doc_to_rust_expr` (`:1610-1611`) sets `self._uses_doc_type` for `Nil|Nbsp|Line|SoftLine|HardLine` (the only bare-`Doc::` arms; `Text`/`Concat` use fully-qualified `fltk_unparser_core::` paths, and `Concat` recurses so nested `Line` still trips the flag — verified against the full function). `generate()` (`:78-86`) builds struct/rule-methods/python-bindings first (only those call `_doc_to_rust_expr`; grep confirms no call from `_gen_header`), then `_gen_header` last, placing it first in file order. Header (`:114-118`) emits `Doc` import only when `_uses_doc_type`. Tests `test_doc_import_omitted_when_no_doc_expr` / `test_doc_import_present_when_doc_expr_emitted` — both green.
Assessment: flag tracking matches emission exactly; reorder is sound. Accept.

### test-1 — Fixed
Claim: `test_empty_alternative_body_is_passthrough` asserted only body content, not the `_node` signature; inverting `"node" if alt.items else "_node"` (`:389`) would pass Python tests and fail only a Rust `-D warnings` build.
Diff at `test_rust_unparser_generator.py:463`: added `assert "fn unparse_r__alt0(&self, _node: &cst::R, pos: usize, acc: DocAccumulator)" in body`. Now pins the empty-alt `_node` naming. Test green.
Assessment: gap closed at the named site. Accept.

### test-2 — Fixed
Claim: the quantified-INLINE-literal inner-method `_node_param` call site (`:765-769`) was uncovered; hardcoding `node` would fail only under Rust `-D warnings`.
Diff: added `test_quantified_inline_literal_inner_uses_underscore_node`. Reviewer's suggested grammar `r := !"x"+;` is not constructible (CST builder asserts INLINE ⇒ Identifier — disposition states this); implementer builds the `gsm.Item` directly and calls `_gen_inner_methods`, mirroring the existing unit term-body tests, asserting the `__inner` signature uses `_node`. Test green.
Assessment: the direct-construction substitution exercises the exact uncovered call site and assertion; the accommodation is justified and documented. Accept.

### reuse-1 — Fixed
Claim: the 4-line `output_file.write_text` try/except duplicated byte-for-byte across `gen_rust_cst`/`gen_rust_parser`/`gen_rust_unparser`/`gen_rust_lib`; diff added the third instance.
Diff (`genparser.py:272-284`): extracted `_write_output_file(output_file, src)`; all four sites now call it. Pure extraction, message/exit unchanged; the distinct `.pyi`-stub write (own message) correctly left as-is. 33 CLI tests green.
Assessment: single maintenance point achieved. Accept.

### reuse-2 — Fixed
Claim: the 3-line `--cst-mod-path` validation duplicated in `gen_rust_parser` and (new) `gen_rust_unparser`.
Diff (`genparser.py:385-395`): extracted `_validate_cst_mod_path(cst_mod_path)`; both sites call it. Pure extraction, behavior unchanged. CLI tests (incl. `test_gen_rust_unparser_invalid_cst_mod_path`) green.
Assessment: accept.

### quality-1 — Fixed (duplicate of correctness-1)
Same root cause and fix as correctness-1; resolved by the same string-literal blanking + same regression test. Correctly identified as a duplicate.
Assessment: accept.

## Disputed items

None.

## Approved

8 findings: 7 Fixed verified (errhandling-1, correctness-1, correctness-2, test-1, test-2, reuse-1, reuse-2), 1 Fixed-duplicate (quality-1). Security + efficiency: 0 findings. No TODOs, no Won't-Do, no scope-N.

---

## Verdict: APPROVED

Every disposition is Fixed and verifies against the diff and the test suite (14 targeted generator tests + 33 CLI tests run green; flag/regex/reorder reasoning checked against source). No disputed items.
