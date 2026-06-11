# Dispositions — Phase 2 Rust Parser Generator (Deep Review Round 2)

Commit reviewed: b95f772. Fixes in: 5780b71 (round 1), dbb9607 (round 2).

---

## errhandling-1

- Disposition: Fixed (round 2 rework)
- Action: `fltk/fegen/gsm2parser_rs.py:106–127` — validation walk replaced with recursive `_validate_term` helper that recurses into `list | tuple` sub-expression terms; `__init__` now catches dangling identifiers at every nesting depth. Added `test_dangling_identifier_at_top_level_raises` and `test_dangling_identifier_in_subexpression_raises` in `test_gsm2parser_rs.py`.
- Severity assessment: Round 1 fix missed identifiers nested inside sub-expression alternatives (list/tuple terms); a SUPPRESS-disposed or INCLUDE-disposed dangling identifier inside a sub-expression still raised a raw `KeyError` at `generate()` time, escaping the CLI handler.

## errhandling-2

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser_rs.py:581–583` — added explicit `else: raise NotImplementedError` after the `WS_REQUIRED` branch in `_gen_separator_code`.
- Severity assessment: A new `Separator` variant would have silently fallen through to the WS_REQUIRED code path, generating incorrect parser logic with no diagnostic.

## correctness-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser_rs.py:497` — changed `ws_pattern` from `r"[\s]+"` to `r"\s+"` (Python reference). Regenerated both `tests/rust_cst_fegen/src/parser.rs` and `tests/rust_parser_fixture/src/parser.rs`.
- Severity assessment: Pattern mismatch caused divergent error messages between Python and Rust backends at trivia-rule WS_REQUIRED separators, undermining the Phase 3 error-message parity requirement.

## correctness-2

- Disposition: Fixed (round 2 rework)
- Action: `fltk/fegen/test_data/rust_parser_fixture.fltkg` — extended `val` rule to `val := item:num | item:name | item:/[!@#$]+/`; the third alternative is span-typed, exercising the `ValChild::Span` append arm. Regenerated `cst.rs` (now includes `ValChild::Span` variant) and `parser.rs` (line 774: `result.append_item(cst::ValChild::Span(item0.result))`). Added `test_val_union_label_span` in `native_tests.rs`; updated existing `test_val_union_label_num` and `test_val_union_label_name` to assert the correct variant.
- Severity assessment: Round 1 fix covered the union-node arm (ValChild::Num, ValChild::Name) but not the union-span arm (ValChild::Span). A naming regression in the span variant of the append path could ship undetected; it now compiles and runs in the fixture test suite.

## correctness-3

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser_rs.py:178–185` — `generate()` now stores result in `self._generated` and returns early on subsequent calls.
- Severity assessment: Second call produced duplicate `fn` definitions (invalid Rust) with no error. Any caller that called `generate()` twice — including test helpers or future Phase 3 plumbing — would get silently corrupt output.

## correctness-4

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser_rs.py:596–598` — pass `path` (not `(*path, "one")`) to `_gen_consume_term` in `_gen_item_multiple`. Regenerated fixtures (function names in generated parsers changed).
- Severity assessment: No runtime behavior difference. Loss of auditability: side-by-side diff of Python vs Rust generated parsers showed phantom structural differences at every repeated sub-expression.

## correctness-5

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser_rs.py:716` — changed `isinstance(term, list)` to `isinstance(term, list | tuple)`.
- Severity assessment: Valid GSM input using a tuple for sub-expression alternatives (accepted by the Python backend per the GSM type spec) was rejected by the Rust backend with a misleading "Unknown term type" error.

## quality-1

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser_rs.py` — deleted `_label_enum_name` (dead method, never called).
- Severity assessment: Dead code that would confuse future contributors and could be mistakenly wired into generated Rust with the wrong symbol names.

## quality-2

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser_rs.py:78,236–239` — `self._source_name` now stores `None` as-is; `_gen_header` conditionally emits the `from` clause only when not `None`.
- Severity assessment: All programmatic uses (tests, library callers) without `source_name` got `"from \`<unknown>\`"` in the generated header, violating the design contract and misleading any tool that parses the header.

## quality-3

- Disposition: Fixed
- Action: Same as correctness-1 — ws_pattern aligned to `r"\s+"`.
- Severity assessment: Duplicate of correctness-1; no additional action.

## quality-4

- Disposition: Fixed
- Action: Same as test-1 — see test-1 below.
- Severity assessment: Duplicate of test-1; no additional action.

## security-1

- Disposition: TODO(parser-depth-limit)
- Action: Added `TODO(parser-depth-limit)` comment in `fltk/fegen/gsm2parser_rs.py` (`_gen_header`) and entry in `TODO.md`. Also added a warning in the generated file header (`//!` doc comment).
- Severity assessment: Deeply nested input causes process abort (SIGSEGV/abort) that cannot be caught, a harder failure than Python's catchable `RecursionError`. Downstream consumers parsing untrusted input are at risk. The fix (depth counter in generated `Parser`) is cross-phase work; deferring to avoid premature scope.

## security-2

- Disposition: TODO(nullable-loop)
- Action: Added `TODO(nullable-loop)` comment in `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`) and entry in `TODO.md`.
- Severity assessment: Attacker-crafted input landing a nullable repeated term can hang the parser at 100% CPU. Deliberately mirrors Python backend for cross-backend parity (design §3); both backends must be fixed together.

## test-1

- Disposition: Fixed
- Action: `fltk/fegen/test_gsm2parser_rs.py:608–622` — replaced vacuous `apply__parse_kw` existence check with body isolation and `push_child`/`append_` absence assertions.
- Severity assessment: Regression emitting `push_child` for SUPPRESS-disposed items would pass the old test. The SUPPRESS no-append invariant was untested.

## test-2

- Disposition: Fixed
- Action: `fltk/fegen/test_gsm2parser_rs.py` — added `test_source_name_none_omits_from_clause` asserting `"<unknown>"` absent and correct header present.
- Severity assessment: The design/implementation divergence on `source_name=None` was uncaught; quality-2 fix without a test would be unprotected.

## test-3

- Disposition: Fixed
- Action: `tests/rust_cst_fegen/src/native_parser_tests.rs` — added `test_parse_fegen_fltkg_with_capture_trivia` that parses the real fegen grammar with `capture_trivia=true` and asserts parse completion and more children than `capture_trivia=false`.
- Severity assessment: Trivia-capture code paths in the fegen parser were untested against a non-trivial grammar. Bugs in `if self.capture_trivia { result.push_child(...) }` blocks would be invisible.

## test-4

- Disposition: Fixed
- Action: `tests/rust_cst_fegen/src/native_parser_tests.rs` — added `test_parse_snippet_with_comment_trivia` parsing a snippet with a line comment and asserting unlabeled trivia children present.
- Severity assessment: The fegen `_trivia` rule and its interaction with the parser was never structurally verified; bugs in trivia-rule separator handling were invisible.

## test-5

- Disposition: Fixed
- Action: `fltk/fegen/test_gsm2parser_rs.py` — added `test_no_consume_literal_in_regex_only_grammar`.
- Severity assessment: Unconditional emission of `consume_literal` in pure-regex grammars would fail `-D warnings` clippy without any test catching it first.

## test-6

- Disposition: Fixed
- Action: `fltk/fegen/test_gsm2parser_rs.py` — added `test_multi_alternative_rule_emits_multiple_if_let_branches` asserting alt0/alt1 presence and ordering in the `parse_val` body.
- Severity assessment: A regression emitting only the first alternative would not be caught at the generator-unit level.

## test-7

- Disposition: Fixed (round 2 rework)
- Action: `tests/rust_parser_fixture/src/native_tests.rs` — added `test_rval_mutual_recursion_positive` (`rval("foo?")` → pos 4, `child_inner().is_ok()`) and `test_lval_mutual_recursion_positive` (`lval("42!")` → pos 3, `child_inner().is_ok()`). These are the positive mutual-recursion cases where the grammar successfully consumes across the mutual boundary. Existing base-case tests (`test_rval_indirect_left_recursion_base_only`, `test_lval_indirect_left_recursion_wires_correctly`) retained.
- Severity assessment: Round 1 tests pinned only base-case outcomes; a regression that broke mutual-recursive consumption (growth not propagating across the lval/rval pair) would pass undetected. The new positive tests require both rules to successfully consume through the mutual boundary.

## test-8

- Disposition: Fixed
- Action: `tests/rust_parser_fixture/src/native_tests.rs` — added span assertions to `test_expr_left_associativity`: outer span 0..5, inner span 0..3, innermost span 0..1.
- Severity assessment: A parser that builds correct tree shape but uses byte offsets instead of codepoint offsets (or has off-by-one span errors) would pass the old test.

## test-9

- Disposition: Fixed
- Action: `tests/rust_parser_fixture/src/native_tests.rs:test_parse_stmt_no_ws_fails` — added `assert!(parser.error_position().is_some())`.
- Severity assessment: A regression where WS_REQUIRED doesn't update the error tracker would pass the old test (which only checked `result.is_none()`).

## test-10

- Disposition: Fixed (round 2 rework)
- Action: `fltk/fegen/test_gsm2parser_rs.py:test_ws_required_separator_has_else_return_none` — constrained the `else_idx` and `return_idx` searches to precede `item1_idx = alt0_body.find("if let Some(item1)")`. Both the `} else {` and `return None;` must be found before the item1 if-let, ensuring they belong to the trivia block, not item1's required-item else-return.
- Severity assessment: Round 1 fix verified the trivia call exists but the else-return search was still satisfiable by item1's required-item else under a WS_ALLOWED downgrade. The bound now makes a downgrade detectable.

## reuse-1

- Disposition: TODO(rust-str-lit-shared)
- Action: Added `TODO(rust-str-lit-shared)` comment in `fltk/fegen/gsm2parser_rs.py` (module level) and entry in `TODO.md`.
- Severity assessment: Escaping divergence between generators is latent; active only if rule names/labels contain backslash, double-quote, or control characters (currently unreachable in practice).

## reuse-2

- Disposition: TODO(rust-naming-shared)
- Action: Added `TODO(rust-naming-shared)` comment in `fltk/fegen/gsm2parser_rs.py` (`_child_enum_name`) and entry in `TODO.md`.
- Severity assessment: Naming convention mismatch (e.g., from a rename in one generator but not the other) would produce parser code referencing nonexistent CST enum names, caught only at `cargo` build time in the consumer.

## efficiency-1

- Disposition: TODO(extend-children-owned)
- Action: Added `TODO(extend-children-owned)` comment in `fltk/fegen/gsm2parser_rs.py` (`_gen_item_multiple`) and entry in `TODO.md`.
- Severity assessment: Per-child, per-loop-iteration atomic inc+dec pairs on the parse hot path; waste scales with input size × inlined-child count. Fix blocked on CST API adding a consuming variant.

## efficiency-2

- Disposition: Fixed
- Action: `fltk/fegen/gsm2parser_rs.py` — both `_gen_alternative` and `_gen_item_multiple` now emit `cst::X::new(Span::unknown())` for the placeholder span instead of `Span::new_with_source(pos, -1, ...)`. Regenerated fixtures.
- Severity assessment: Each (typically failing) alternative attempt paid an Arc clone + Arc drop for the placeholder source, O(positions × alternatives) over a parse. One-line fix, no observable behavior change.
