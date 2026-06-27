test-1
File: fltk/unparse/gsm2unparser_rs.py:394 (`_gen_literal_term_body`, `else` branch)
What: The `else` branch of `_gen_literal_term_body` — reached when `item.disposition != gsm.Disposition.INCLUDE`, i.e., the INLINE (`!`) disposition — emits the literal text via `add_non_trivia` without consuming a CST position (`pos` not advanced). No test exercises this path. Every existing literal test uses either SUPPRESS (routed to `_gen_suppressed_item_body` before reaching this method) or INCLUDE (routed to the `if` branch).
Consequence: A refactor that accidentally unifies the INCLUDE and INLINE branches — advancing `pos + 1` in both — would produce incorrect emitted Rust code (double-advancing position for an INLINE literal that occupies no CST slot) with no test to detect it.
Fix: Add a test for a grammar with an inline literal (`r := !"x";`). Assert that `add_non_trivia(fltk_unparser_core::text("x"))` is present and that `pos + 1` is absent and `node.children()` is absent.

test-2
File: fltk/unparse/gsm2unparser_rs.py:486 (`_gen_suppressed_item_body`, final fallthrough)
What: The last `raise RuntimeError(...)` in `_gen_suppressed_item_body` — the branch reached when the required suppressed term is neither `Literal`, `Regex`, nor `Identifier` (e.g., a nested-alternative sub-expression term) — is untested. The existing unit tests cover the Literal (emit text), Regex (raise), Identifier (raise), and optional (pass-through) paths; the sub-expression path has no corresponding test.
Consequence: If this branch were silently converted to a pass-through (e.g., during a refactor adding a new term kind), no test would catch it. A suppressed required sub-expression would generate incorrect code rather than failing at generation time.
Fix: Add a unit test constructing `gsm.Item(disposition=SUPPRESS, term=<a gsm.Items / sub-expression>, quantifier=REQUIRED)` and asserting `pytest.raises(RuntimeError, match="cannot be recreated from CST")`. The `gsm.Items` type (nested alternatives) is the concrete non-Literal/Regex/Identifier term that reaches this branch.

test-3
File: fltk/unparse/gsm2unparser_rs.py:342 (`_gen_term_body`, `Regex` fallthrough)
What: The pass-through returned for non-suppressed, single-quantifier Regex terms (`isinstance(item.term, gsm.Regex)` in `_gen_term_body`) is untested. The existing tests cover: suppressed regex raising (`test_suppressed_required_regex_raises`), and multiple-quantifier literals staying as scaffold (`test_multiple_quantifier_literal_stays_scaffold`). But a single-quantifier INCLUDE or INLINE regex — e.g., `r := foo:/[0-9]+/;` — silently emits a pass-through body; no test verifies that behavior.
Consequence: A future increment that begins implementing regex term bodies might route single-quantifier regex terms to the literal body (which emits a fixed literal string instead of extracting the actual matched text), and no test would catch the misrouting.
Fix: Add a test for `r := foo:/[0-9]+/;` (labeled INCLUDE regex). Assert that the emitted source contains `Some(UnparseResult::new(acc, pos))` for item0 (pass-through, no pos advance) and that `node.children()` and `add_non_trivia` are absent from the item method body — or alternatively drive it via a `_gen_item_body` unit call and assert the returned list equals `["        Some(UnparseResult::new(acc, pos))"]`.
