# Slop review — 490bccf..261fa5e

## slop-1

- File: `fltk/fegen/gsm2parser_rs.py:241-248`
- Quote: `# Regex table is generated AFTER bodies so we know all patterns. # But header already decided if OnceLock/Regex is needed. # We add regex table here ... # Since generate() calls _gen_header() before bodies, let's just emit ... # The pattern: header checks self._regex_patterns AFTER bodies are generated. # Actually: generate() calls _gen_rule() for all rules FIRST ...`
- What's wrong: Eight-line thought-log comment that narrates the author's own confusion and corrects itself mid-comment. "Let's just emit", "The pattern:", "Actually:" read as live problem-solving, not documentation.
- Consequence: Looks like the LLM forgot to clean up its scratch notes before committing — exactly what triggers a reviewer's confidence drop.
- Fix: Replace with a single sentence: `# generate() calls _gen_rule() for all rules before calling _gen_constants(), so self._regex_patterns is complete here.`

## slop-2

- File: `fltk/fegen/test_gsm2parser_rs.py:1797-1821` (`test_optional_item_no_return_none`)
- Quote: `# The alt function for optional should not have return None after the if-let / # We check it generates (no else return None for the item) / # There IS a return None at the end of the alternatives dispatcher / assert "pub fn apply__parse_opt(" in src`
- What's wrong: The test's docstring claims to check that no `else return None` is emitted for optional items, but the single assertion only checks that `apply__parse_opt(` exists in the source — it does not verify the absence of `return None` in the item branch. The comment is more informative than the assertion.
- Consequence: Test does not actually exercise what the docstring says. A regression where the optional item gains an unwanted `else { return None; }` would not be caught.
- Fix: Add `assert "} else {" not in src.split("parse_opt__alt0__item0")[1].split("parse_opt__alt0")[0]` or equivalent assertion that verifies the generated alt body lacks the required-item `else` branch.

## slop-3

- File: `fltk/fegen/test_gsm2parser_rs.py:1823-1845` (`test_zero_or_more_quantifier`)
- Quote: `assert "pub fn apply__parse_zom(" in src`
- What's wrong: Test name and docstring say it verifies `*` quantifier behavior (no `if pos == span_start` guard), but the only assertion checks the apply wrapper exists. Contrast with `test_one_or_more_quantifier` which correctly asserts the guard string.
- Consequence: The `*` vs `+` distinction — the one observable behavioral difference in the generated loop — is untested. Swapping `is_required()` logic would not be caught.
- Fix: Add `assert "if pos == span_start" not in src` (scoped to the zom function body) to pin the absence of the one-or-more guard.

No findings for the Makefile additions, generated `.rs` files, or `native_tests.rs` — those are mechanical/generated with appropriate test coverage and clean comment style.
