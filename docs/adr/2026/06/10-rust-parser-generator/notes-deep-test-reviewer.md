Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

## test-1

**File:** `fltk/fegen/test_gsm2parser_rs.py` — `test_suppress_disposition_no_append`

**What's wrong:** Vacuous assertion. The test generates a grammar with a SUPPRESS-disposed literal and asserts only `"pub fn apply__parse_kw(" in src` — i.e., that the rule exists. It never verifies that the suppressed item produces no append/push_child call in the generated body. The comment in the test ("Let's verify the generate succeeds and no append for the suppressed item") describes the intent but the assertion doesn't fulfill it.

**Consequence:** A regression that emits `result.push_child(...)` for SUPPRESS-disposed items would pass this test. The suppression path in `_gen_append_code_for_consumed` (line 767) would be silently broken.

**Fix:** After `src.split("fn parse_kw__alt0(", 1)`, isolate the body and assert neither `push_child` nor `append_` appears in it.

---

## test-2

**File:** `fltk/fegen/test_gsm2parser_rs.py` — no test for `source_name=None` header variant

**What's wrong:** `test_source_name_in_header` checks that a provided `source_name` appears in the header comment. The design (§2.2) specifies that when `source_name=None`, the `"from \`<source_name>\`"` clause is omitted (and the constructor defaults `self._source_name` to `"<unknown>"` rather than omitting the clause — line 74). There is no test confirming the `None`/no-source-name path produces a coherent header that doesn't say `"from \`<unknown>\`"` verbatim or otherwise expose the fallback string to consumers.

**Consequence:** If the design intent (omit clause when `None`) diverges from the implementation (emit `"<unknown>"`), no test catches it. Out-of-tree consumers constructing `RustParserGenerator` without `source_name` would see a misleading header.

**Fix:** Add a test: `RustParserGenerator(grammar)` with no `source_name` — assert `"<unknown>"` does not appear in the header, or assert the header matches the expected omit-clause form.

---

## test-3

**File:** `tests/rust_cst_fegen/src/native_parser_tests.rs` — no `capture_trivia=true` parse of `fegen.fltkg`

**What's wrong:** `test_parse_fegen_fltkg` runs only with `capture_trivia=false`. The design (§4 item 3) explicitly calls for testing "both `capture_trivia` settings" on the real fegen grammar. The `capture_trivia=true` path exercises every trivia-capture code site in the generated fegen parser; omitting it leaves those paths untested against a non-trivial, real grammar.

**Consequence:** A bug in the trivia-capture branch (the `if self.capture_trivia { result.push_child(...) }` blocks) would not be caught by the fegen integration test. Only the fixture's `test_capture_trivia_tree_delta` would detect it, and only for the small fixture grammar.

**Fix:** Add `test_parse_fegen_fltkg_with_capture_trivia` that mirrors `test_parse_fegen_fltkg` with `Parser::new(src, true)` and asserts parse completes to `terminals().len()`.

---

## test-4

**File:** `tests/rust_cst_fegen/src/native_parser_tests.rs` — no trivia/comment parsing assertions

**What's wrong:** The two tests parse syntactically minimal input (`"grammar := rule+ ;"`) and the full `fegen.fltkg`, asserting only that parse succeeds and `pos == terminals().len()`. Neither test exercises the fegen grammar's trivia rule with actual whitespace/comment input and checks tree shape via CST accessors. The design (§4 item 3) calls for "parse fegen-grammar snippets (a rule, alternatives with `|`, comments/trivia) asserting tree shape via CST accessors." The comments/trivia assertion is absent.

**Consequence:** The fegen `_trivia` rule and its interaction with the generated parser is never structurally verified. A bug in trivia-rule separator handling (the `consume_regex` path in `_gen_separator_code` for `is_trivia_rule=True`) would be invisible in these tests.

**Fix:** Add a test parsing a snippet that contains an inline comment (e.g., `"// a comment\nrule := /x/ ;"`) with `capture_trivia=true` and assert the root node's trivia children are present.

---

## test-5

**File:** `fltk/fegen/test_gsm2parser_rs.py` — no test that `consume_literal` is absent when grammar has no literals

**What's wrong:** The design (§2.2) states `consume_literal` is emitted only when the grammar has at least one literal (to avoid `dead_code` clippy failures). `test_literal_generates_consume_literal` verifies the positive case. There is no test for the negative case: a regex-only grammar must not emit `consume_literal`.

**Consequence:** If the generator unconditionally emits `consume_literal`, the generated code fails `-D warnings` clippy in pure-regex grammars. No test would catch this.

**Fix:** Add a test: generate for `_make_simple_grammar()` (regex-only) and assert `"consume_literal"` is not in `src`.

---

## test-6

**File:** `fltk/fegen/test_gsm2parser_rs.py` — no test for multi-alternative rule generating correct `if let` chain

**What's wrong:** No Python-level test verifies that a multi-alternative rule body emits multiple `if let Some(altN)` branches in order. `test_union_label_append_uses_child_enum` exercises the union-label append path but the union is defined by two alternatives; it does not assert the ordering or count of `if let` branches in the generated `parse_val` body.

**Consequence:** A regression that emits only the first alternative (or duplicates it) in a multi-alternative rule would not be caught at the generator-unit level. The Rust fixture tests catch it only if the right input exercises the second alternative.

**Fix:** Add a test: generate the union-label grammar, isolate the `parse_val` body, assert it contains two `if let Some(alt0)` and `if let Some(alt1)` blocks in that order.

---

## test-7

**File:** `tests/rust_parser_fixture/src/native_tests.rs` — indirect left-recursion tests assert base cases only; no mutual-recursion depth test

**What's wrong:** `test_lval_base_case` and `test_rval_base_case` each parse a single-token input. Neither test exercises actual mutual left recursion (e.g., `"42?"` for `rval -> lval -> rval` or `"foo!"` for `lval -> rval -> lval`). The design (§4 item 3) calls for "indirect left recursion" tests; the base-case-only tests confirm the non-recursive fallbacks but not the recursive paths.

**Consequence:** A broken indirect left-recursion wiring (e.g., wrong rule_id in the apply wrapper or incorrect cache field reference between mutually recursive rules) would not be detected by these tests.

**Fix:** Add tests parsing `"42?"` (assert `rval` consumes 3 codepoints with `inner` label set) and `"foo!"` (assert `lval` consumes 4 codepoints with `inner` label set), verifying actual mutual-recursive descent.

---

## test-8

**File:** `tests/rust_parser_fixture/src/native_tests.rs` — `test_expr_left_associativity` asserts structure but not span values

**What's wrong:** The left-associativity test for `"1+2+3"` checks node label presence (`child_lhs().is_ok()`, etc.) but never asserts the span values of the inner/outer nodes. A parser that builds the right tree shape but assigns wrong spans (byte-indexed instead of codepoint-indexed, or off-by-one at the `+` literal) would pass.

**Consequence:** Span correctness for left-recursive grammars is untested at the structural level. This is the most complex code path in the generator and deserves span assertions.

**Fix:** Add `assert_eq!(r.pos, 5)` already present; additionally assert `outer.span().start() == 0 && outer.span().end() == 5`; assert `inner.span().start() == 0 && inner.span().end() == 3`; assert `innermost.span().start() == 0 && innermost.span().end() == 1`.

---

## test-9

**File:** `tests/rust_parser_fixture/src/native_tests.rs` — `test_parse_stmt_no_ws_fails` does not verify `error_position`

**What's wrong:** The WS_REQUIRED failure test asserts `result.is_none()` but does not check `parser.error_position()` or `parser.error_message()`. The design (§3 edge case list) documents that WS_REQUIRED failure at a specific position is meaningful; without asserting `error_position()` the test cannot distinguish "failed because no whitespace" from "failed because the rule isn't matching at all."

**Consequence:** A regression where WS_REQUIRED doesn't update the error tracker (i.e., silent failure with no recorded position) passes this test. `test_error_position_on_failure` in the same file tests a different rule and doesn't cover this code path.

**Fix:** After asserting `result.is_none()`, add `assert!(parser.error_position().is_some())` and optionally assert the position equals 3 (after `"foo"`), confirming the error tracker advanced correctly.

---

## test-10

**File:** `fltk/fegen/test_gsm2parser_rs.py` — `test_ws_required_separator_has_else_return_none` conflates WS_REQUIRED and required-item `return None`

**What's wrong:** The assertion `assert "} else {" in src` and `assert "return None;" in src` are also satisfied by the required-item else-branch that every required item emits. The test doesn't isolate the separator-specific else-branch, so it would pass even if WS_REQUIRED separators were silently downgraded to WS_ALLOWED (no else-return), as long as the grammar has any required item.

**Consequence:** The WS_REQUIRED else-return path in `_gen_separator_code` could regress (dropping the else-branch from the separator) without this test catching it.

**Fix:** Isolate the `parse_pair__alt0` body, then specifically check that the trivia `if let` block for the separator has an else-branch: e.g., verify the separator region contains both `apply__parse__trivia` and `return None;` in the same block, or assert the pattern `"} else {\n            return None;\n        }"` appears after the `apply__parse__trivia` call.
