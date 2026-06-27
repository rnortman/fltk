## Test reviewer notes — batch 5 (generator term-handling)

Commit reviewed: 5f7b5cb1d33150b1125daf6e0f19c4051ab28c30

---

**test-1**

File: `fltk/unparse/gsm2unparser_rs.py`, `_gen_term_body` final `raise ValueError` (line 441–442); test file: `tests/test_rust_unparser_generator.py`.

The new `raise ValueError` at the end of `_gen_term_body` replaced a silent pass-through for unrecognized term kinds (e.g. a future `Invocation` term). No test exercises this path. In previous batches, the analogous guards in `_gen_literal_term_body`, `_gen_identifier_term_body`, and `_gen_regex_term_body` are each covered by a dedicated `_rejects_non_*` unit test; `_gen_term_body`'s guard has no equivalent.

Consequence: if the guard is accidentally removed (or the routing changed to fall through to another branch), misrouted terms silently emit wrong Rust (a pass-through or the wrong sub-body). No test catches the regression.

Fix: add `test_term_body_rejects_unknown_term_kind` that constructs an `Item` with a term that is none of `Identifier`, `Literal`, `Regex`, or `list`, and asserts `_gen_term_body` raises `ValueError` matching `"Unrecognized term type"`.

---

**test-2**

File: `tests/test_rust_unparser_generator.py`, `test_regex_single_variant_reads_span_text_and_advances`, line 699.

`assert "_ => return None," not in src` is a file-global negative assertion. Every grammar generates a synthetic `_trivia` rule backed by a regex; if the `_trivia` rule's child enum ever acquired a second variant (e.g. due to a grammar change that adds a labeled element to trivia), the assertion would incorrectly pass or fail based on the trivia rule rather than the rule under test. All other negative assertions added in this batch were already scoped to `_method_body`; this one was not.

Consequence: the assertion could silently test the wrong rule, and a real regression (the `r` item mistakenly emitting a catch-all) would go undetected if the `_trivia` rule also happened to emit one.

Fix: scope to `_method_body(src, "unparse_r__alt0__item0")` and assert `"_ => return None," not in body`.

---

**test-3**

File: `tests/test_rust_unparser_generator.py`, `test_regex_inline_body_reads_span_without_advance` (line 753–766).

The test calls `gen._gen_regex_term_body("greeting", "Greeting", item)` using `_gen()` — a generator built from `greeting := "hello";`. The greeting rule's only item is a suppressed literal, so `num_child_variants("greeting")` returns 0 and `child_enum_name("Greeting")` is `"GreetingChild"`. The method then emits `cst::GreetingChild::Span(span) => span,` — but `GreetingChild` has no `Span` variant; in real Rust this would be a non-exhaustive match error. The test passes because its assertions (`"let text = span.text()?"`, no `pos + 1`) are present in the output regardless.

Consequence: the INLINE disposition path is "tested" with a generator that produces invalid Rust. If the span-binding code were broken specifically for the INLINE path (e.g. the match arm were dropped), the `"let text = span.text()?"` assertion would still fail and catch it; but a subtler error such as the wrong child enum name would not be caught. More importantly the test gives false confidence about the generated code's semantic correctness.

Fix: use `gen = RustUnparserGenerator(parse_grammar("r := foo:/[0-9]+/;"))` so `num_child_variants("r") == 1` and the child enum is `RChild` (has a real `Span` variant). Construct `item = gsm.Item(label=None, disposition=gsm.Disposition.INLINE, term=gsm.Regex("[0-9]+"), quantifier=gsm.REQUIRED)` and call `gen._gen_regex_term_body("r", "R", item)`. Add an assertion that `"cst::RChild::Span(span) => span,"` is present in the output, so the span-binding arm is verified along with the no-advance path.

---

**test-4**

File: `tests/test_rust_unparser_generator.py`, sub-expression tests (lines 788–899); production: `_gen_alts_dispatch` lines 499–501.

`_gen_alts_dispatch` terminates with `"        None"` after the alternative loop, ensuring the dispatch returns `None` when all alternatives fail. None of the sub-expression tests assert this terminator is present. The tests verify that alternatives are tried (`if let Some(r) = ...`) but not that the function body ends with the Rust `None` return on the exhausted-alternatives path.

Consequence: if the `None` line were accidentally omitted, the generated Rust would fail to compile (missing return value), but generator tests wouldn't catch it since they never check for this line and don't compile the output.

Fix: in one of the sub-expression end-to-end tests (e.g. `test_subexpr_item_delegates_to_alts_dispatch`), add `assert "        None\n    }" in src` or scope to the alts-dispatch body and check `"None"` is present there.

---

**test-5**

File: `tests/test_rust_unparser_generator.py`; production: `_gen_alternative_body` spacing integration.

The `_gen_alternative_body` method calls `_item_spacing_lines` for every item in an alternative, including sub-expression items. No test configures a spacing anchor whose label matches a sub-expression item and verifies the spacing lines are emitted around the `__alts` dispatch call. The existing spacing tests all use plain literal items (`foo:"x"`).

Consequence: a bug where spacing is silently skipped for sub-expression items (e.g. a guard that checks `isinstance(item.term, Literal)` before emitting spacing) would go undetected. The sub-expression and spacing paths are each tested in isolation but never in combination.

Fix: add a test with a grammar like `r := (a:"x" | b:"y");` and a `FormatterConfig` with `before:label:` configured (e.g. via `before:literal:x`), verify that `before_spec(...)` appears in the `unparse_r__alt0` body ahead of the `unparse_r__alt0__item0` call.
