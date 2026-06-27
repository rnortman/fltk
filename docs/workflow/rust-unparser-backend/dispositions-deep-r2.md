# Dispositions — deep review, round 2

Scope reviewed: `crates/fltk-unparser-core/src/{render,result,lib}.rs` (batch 2),
`fltk/unparse/gsm2unparser_rs.py` (generator scaffold),
`tests/test_rust_unparser_generator.py`.

`notes-deep-errhandling-r2.md`, `notes-deep-correctness-r2.md`,
`notes-deep-security-r2.md`, and `notes-deep-efficiency-r2.md` reported no findings;
nothing to dispose there.

After fixes: `cargo test -p fltk-unparser-core` (109 passed), `cargo clippy -p
fltk-unparser-core --all-targets` clean, `cargo fmt -p fltk-unparser-core --check`
clean; `uv run pytest tests/test_rust_unparser_generator.py
fltk/fegen/test_gsm2parser_rs.py` (66 passed); `ruff`/`pyright` clean on touched
Python files. Generator output verified byte-identical (regenerated parser fixture
content unchanged).

---

test-1:
- Disposition: Fixed
- Action: `crates/fltk-unparser-core/src/render.rs` — added `#[should_panic(expected =
  "Unknown document type in renderer")]` tests `unresolved_before_spec_panics`
  (`Doc::BeforeSpec`) and `unresolved_join_panics` (`Doc::Join`), mirroring
  `unresolved_spec_panics`. The four-variant render-time panic arm was previously
  exercised only via `Doc::AfterSpec`.
- Severity assessment: Test gap, not a code bug. A refactor narrowing the match arm
  (dropping a variant) would compile and go undetected until a runtime path hit it;
  the new tests pin three of the four variants directly (SeparatorSpec covered by
  symmetry).

test-2:
- Disposition: Fixed
- Action: `render.rs` — added `sibling_groups_break_when_combined_too_wide`, an outer
  group of three sibling sub-groups whose combined flat width (25) exceeds `max_width`
  (24), asserting the outer breaks while each sub-group renders flat. Mirrors the Python
  `test_multiple_subgroups_algorithm_limitation`.
- Severity assessment: Test gap. Cross-sibling width accumulation in `fits` had no
  direct coverage (existing tests cover only the parent/child nesting axis); a queue
  state-propagation defect across siblings would have slipped through.

test-3:
- Disposition: Fixed
- Action: `tests/test_rust_unparser_generator.py:test_generate_emits_header_and_struct`
  — added `assert "#![allow(non_snake_case)]" in src`.
- Severity assessment: Test gap. The attribute is required by later increments' emitted
  `unparse_{rule}__alt{N}__item{M}` names; dropping it would only surface at compile
  time in a later increment, not in the batch-2 generator tests.

test-4:
- Disposition: Fixed
- Action: same test — assert each of the six imported `fltk_unparser_core` symbols
  (`DocAccumulator`, `Doc`, `UnparseResult`, `RendererConfig`, `Renderer`,
  `resolve_spacing_specs`) appears in the source, not just that the import block opens.
- Severity assessment: Test gap. A dropped/misspelled import symbol would otherwise pass
  these tests and fail only at a later compile increment.

test-5:
- Disposition: Fixed
- Action: same file — new `test_generate_source_name_is_escaped` passes a backslash
  source name (`path\to\grammar.fltkg`) and asserts the doubled-backslash escaped form
  appears in the `//!` header line, exercising `rust_str_lit`'s escaping path.
- Severity assessment: Test gap. The only prior `source_name` case (`greeting.fltkg`)
  contained no escapable characters, so a regression in header escaping (e.g. a Windows
  path) was uncovered.

reuse-1:
- Disposition: Fixed
- Action: extracted the CST-import decision (`use {path};` vs `use {path} as cst;`) into
  a shared module-level helper `cst_module_import(cst_mod_path)` in
  `fltk/fegen/gsm2parser_rs.py`; both `gsm2parser_rs._gen_header` and
  `gsm2unparser_rs._gen_header` now call it instead of holding independent copies of the
  four-line block. No separate shared-utility module was created (ADR
  `2026/06/11-rust-naming-shared` §"Not changed" forbids that; `gsm2parser_rs` is the
  home, consistent with where `rust_str_lit` lives). Generator output byte-identical.
- Severity assessment: Real but low — structural duplication of a trivial decision; the
  two copies could drift if the import rule ever changes. Extraction is cost-free here
  (no hot-path concern, unlike the r1 concat/concat_rc case), so Fixed rather than
  deferred.

quality-1:
- Disposition: Fixed
- Action: applied the reviewer's recommended Option 1 — renamed
  `gsm2parser_rs._rust_str_lit` → `rust_str_lit` (public), making the existing
  cross-module import in `gsm2unparser_rs.py` an intentional, visible dependency instead
  of reaching into a private symbol. Updated all call sites (`gsm2parser_rs.py`,
  `gsm2unparser_rs.py`), the test import + names (`fltk/fegen/test_gsm2parser_rs.py`),
  and the prose reference at `gsm2tree_rs.py:152`. Design §2.2 names `_rust_str_lit`
  literally; this rename preserves the design's reuse intent and is recorded in
  `implementation-log.md` (Review round — deep r2). No shared module created (ADR-
  consistent). `_rust_str_lit` is an internal codegen helper, not a generated public
  symbol, so the rename has no out-of-tree-consumer impact (CLAUDE.md public-API concern
  is about generated artifacts).
- Severity assessment: Real coupling smell — a production module importing another
  module's single-underscore private helper would break silently at import time on any
  rename of the private symbol, with no compile-time signal. The fix is a low-cost,
  behavior-neutral rename that legitimizes the dependency.

quality-2:
- Disposition: Fixed
- Action: `render.rs` `Output::append_content` — replaced the two separate
  `!text.is_empty()` guards (a literal port of the Python closure's two `if text:`
  blocks) with a single early `return` on empty text, then unconditional indentation +
  content emission. Behavior unchanged (all render tests pass).
- Severity assessment: Low — readability/maintainability. The second guard was dead work
  on the empty-text path and invited a third redundant guard on future extension; the
  early-return form is the idiomatic Rust shape and removes the ambiguity.
