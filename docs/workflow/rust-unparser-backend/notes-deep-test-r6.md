# Test Review — Batch 6 (generator term-handling)

Commit reviewed: ae90f84671cf03d4b6e2aeed244bab3df1b1d633

---

## test-1

**File:line** `tests/test_rust_unparser_generator.py` — quantified-loop section (~line 922)

**What's wrong** No test covers a quantified regex term's `__inner` method. The three `__inner` term kinds exercised are: literal (`test_quantified_loop_emits_inner_method_with_literal_term_body`), identifier (`test_quantified_identifier_inner_recurses_into_ref_rule`), and sub-expression (`test_quantified_subexpr_inner_delegates_to_nested_alts`). There is no test for a grammar like `r := foo:/[0-9]+/+;` or `r := foo:/[0-9]+/*;`. The `_gen_inner_methods` dispatch falls through to `_gen_term_body`, which then reaches `_gen_regex_term_body`. This is a distinct path from the three currently tested.

**Consequence** A regression that broke regex body generation inside `_gen_inner_methods` — for example, if `_gen_term_body` were mis-dispatched for a quantified regex, or if `_gen_regex_term_body` raised for a regex item with no label when reached via `__inner` — would go undetected. The `__inner` for a regex is the production path for whitespace-sensitive tokenised content that appears zero-or-more/one-or-more times, so the gap covers real grammar shapes.

**Fix** Add a test `test_quantified_regex_inner_reads_span_text()` that generates `r := foo:/[0-9]+/+;`, extracts `_method_body(src, "unparse_r__alt0__item0__inner")`, and asserts `span.text()`, `add_non_trivia(fltk_unparser_core::text(text))`, and `Some(UnparseResult::new(acc, pos + 1))` are present.

---

## test-2

**File:line** `tests/test_rust_unparser_generator.py` — disposition section (~line 1498)

**What's wrong** `test_omit_skips_before_spacing` verifies that an `Omit` disposition suppresses the `before_spec` emission. The production gate is `is_normal = isinstance(item_disposition, Normal)` followed by `if is_normal: lines.extend(self._item_spacing_lines(..., "before", ...))`, which applies identically to `RenderAs`. No test verifies that a `RenderAs` item with a configured before-spacing also produces no `before_spec`.

**Consequence** If the condition were changed from `is_normal` (False for both `Omit` and `RenderAs`) to a narrower `isinstance(item_disposition, Omit)` check, `RenderAs` items would incorrectly emit a `before_spec` ahead of their substituted `add_non_trivia`. The existing `Omit` test would still pass, leaving the `RenderAs` regression undetected.

**Fix** Add a test that constructs a `RenderAs` disposition config that also carries a SPACING operation (or a separate `before:label` SPACING anchor on the same item), generates the source, and asserts `before_spec` is absent from the alt body while the substitution `add_non_trivia` is present.

---

## test-3

**File:line** `tests/test_rust_unparser_generator.py` — `test_item_routes_to_quantified_loop_predicate` parametrize list (~line 1047)

**What's wrong** The parametrized test covers `(SUPPRESS, ONE_OR_MORE, False)` but not `(SUPPRESS, ZERO_OR_MORE, False)`. The predicate is `item.disposition != SUPPRESS and item.quantifier.is_multiple()`, so `SUPPRESS + ZERO_OR_MORE` should return `False`. The body-routing in `_gen_item_body` checks `SUPPRESS` first and would not misroute even if the predicate returned `True`, but `_gen_item_method` uses the same predicate to decide whether to emit `__inner` sibling methods — and there the SUPPRESS check does not precede it. A buggy predicate that returned `True` for `SUPPRESS + ZERO_OR_MORE` would cause spurious dead `__inner` methods to be emitted.

**Consequence** A refactoring that reordered the `is_multiple()` and `!= SUPPRESS` checks — for example, short-circuiting on `is_multiple()` first — could cause `SUPPRESS + ZERO_OR_MORE` items to emit an `__inner` method, generating dead Rust that Rust's dead-code linter would flag only at compile time, not at generation time.

**Fix** Add `(gsm.Disposition.SUPPRESS, gsm.ZERO_OR_MORE, False)` to the parametrize list of `test_item_routes_to_quantified_loop_predicate`.
