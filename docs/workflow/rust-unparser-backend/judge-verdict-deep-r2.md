# Judge verdict — deep review (batch 2)

Phase: deep. Base d5914359..HEAD 33930a6e. Round 1.
Notes: 7 reviewer files. 4 reported no findings (errhandling, correctness, security, efficiency). 8 findings dispositioned (test-1..5, reuse-1, quality-1, quality-2) — all Fixed.
Fixes landed in commit 33930a6 (`respond(deep-r2)`); reviewers worked against e65e4f66.

## Added TODOs walk

No TODO dispositions and no `scope-N` findings this round. All eight findings are Fixed. Nothing to walk here.

## Other findings walk

### test-1 — Fixed
Claim: `render.rs:990` — the unresolved-spec/join render panic arm (`Join`/`AfterSpec`/`BeforeSpec`/`SeparatorSpec`) is exercised only via `Doc::AfterSpec`; a refactor narrowing the arm compiles and goes undetected until a runtime path hits it. Consequence: silent regression.
Diff at `render.rs:998` (`unresolved_before_spec_panics`) and `:1006` (`unresolved_join_panics`), both `#[should_panic(expected = "Unknown document type in renderer")]`. Verified the literal panic string at `render.rs:189` matches the `expected` substring exactly, so the tests are non-vacuous (a non-panic or wrong message fails them). Three of four variants now pinned directly; SeparatorSpec by symmetry.
Assessment: fix addresses the consequence at the named arm. Accept.

### test-2 — Fixed
Claim: no Rust test covers the sibling-groups width axis (`test_multiple_subgroups_algorithm_limitation` in Python); a cross-sibling width-accumulation defect in `fits` would slip through. Existing tests cover only the parent/child nesting axis. Consequence: port-level defect uncaught.
Diff at `render.rs:1012` (`sibling_groups_break_when_combined_too_wide`): outer group of three sibling sub-groups, combined flat width 25 > max_width 24. Asserts `"short one\nalso short\ntiny"` — the embedded newlines prove the outer broke while sub-groups rendered flat, so the assertion is non-vacuous. Helpers (`group`/`concat`/`text`/`line`/`render_with`) confirmed imported from `crate::doc` and present; 109 Rust tests pass per disposition.
Assessment: covers the named axis; meaningful assertion. Accept.

### test-3 — Fixed
Claim: `test_generate_emits_header_and_struct` does not assert `#![allow(non_snake_case)]` is emitted; dropping it surfaces only at a later compile increment. Consequence: late-binding regression.
Diff at `test_rust_unparser_generator.py:27` adds the assert. Verified the generator emits the attribute at `gsm2unparser_rs.py:89`. Assertion matches.
Assessment: Accept.

### test-4 — Fixed
Claim: `assert "use fltk_unparser_core::{" in src` confirms only the import block opens, not any of the six required symbols. Consequence: a dropped/misspelled symbol passes the test, fails at a later compile.
Diff at `test_rust_unparser_generator.py:23-24` loops over all six symbols (`DocAccumulator`, `Doc`, `UnparseResult`, `RendererConfig`, `Renderer`, `resolve_spacing_specs`). Verified all six are emitted at `gsm2unparser_rs.py:92-95`.
Assessment: Accept.

### test-5 — Fixed
Claim: only `source_name` tested is `greeting.fltkg`, exercising no escaping; a Windows path or quote would produce a silently wrong doc-comment. Consequence: uncaught escaping regression.
Diff at `test_rust_unparser_generator.py:41` (`test_generate_source_name_is_escaped`): passes `path\to\grammar.fltkg`, asserts the doubled-backslash form `path\\to\\grammar.fltkg` in the header. Verified `rust_str_lit` doubles backslashes and `_gen_header` applies it at `gsm2unparser_rs.py:83`; assertion is correct and exercises the escaping path.
Assessment: Accept.

### reuse-1 — Fixed
Claim: `gsm2unparser_rs.py:99-103` duplicates the CST-import decision (`use {path};` vs `use {path} as cst;`) already present at `gsm2parser_rs.py:305-309`. Consequence: structural duplication that drifts if the import rule changes.
Diff extracts `cst_module_import(cst_mod_path)` to module level in `gsm2parser_rs.py:78`; both `_gen_header` methods now call it (`gsm2parser_rs.py:319`, `gsm2unparser_rs.py:99`). Home choice (gsm2parser_rs, no new shared module) is ADR-consistent (`2026/06/11-rust-naming-shared` §"Not changed") and co-locates with `rust_str_lit`. Generator output byte-identical per disposition.
Assessment: duplication removed at the named lines; placement justified. Accept.

### quality-1 — Fixed
Claim: `gsm2unparser_rs.py:23` imports the private `_rust_str_lit` from `gsm2parser_rs` in production code; the underscore signals non-public surface, and a rename breaks the importer at import time with no compile-time signal. Consequence: silent coupling break.
Disposition applied reviewer Option 1: renamed `_rust_str_lit` → `rust_str_lit` (public). Verified all call sites updated in the diff (4 in `gsm2parser_rs.py`, the import in `gsm2unparser_rs.py:23`, the test import + names in `test_gsm2parser_rs.py`, prose ref in `gsm2tree_rs.py:152`). Grep of the main tree confirms no stale `_rust_str_lit` symbol remains (only `test_rust_str_lit_*` function names). CLAUDE.md public-API concern does not apply: `rust_str_lit` is a generator-internal codegen helper, not a generated artifact consumed out-of-tree, and broadening private→public is non-breaking.
Assessment: dependency legitimized, fully propagated. Accept.

### quality-2 — Fixed
Claim: `render.rs:77-88` `Output::append_content` guards its body with two separate `!text.is_empty()` checks (a literal port of the Python double `if text:`); second guard is dead work on the empty path and invites a third on extension. Consequence: readability / maintainability.
Diff replaces with a single early `return` on empty text, then unconditional indentation + content. Behavior-neutral by inspection: non-empty text executes both blocks identically to before; empty text does nothing in both forms. Render tests pass.
Assessment: idiomatic, behavior-preserving. Accept.

## Disputed items

None.

## Approved

8 findings: 8 Fixed verified. (4 reviewers reported no findings — nothing to dispose.)

---

## Verdict: APPROVED

All eight Fixed dispositions verified against the diff and surrounding code; assertions confirmed non-vacuous; rename fully propagated with no out-of-tree-consumer impact. No TODOs, no Won't-Do, no `scope-N` deferrals.
