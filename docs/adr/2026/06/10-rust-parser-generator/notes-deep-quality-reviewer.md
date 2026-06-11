Style: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

---

**quality-1**

File: `fltk/fegen/gsm2parser_rs.py:157–158`

```python
def _label_enum_name(self, rule_name: str) -> str:
    return self._class_name(rule_name) + "Label"
```

Dead method. `_label_enum_name` is defined but never called anywhere in `gsm2parser_rs.py` or its tests. The generator uses `_child_enum_name` for append sites and `_label_type_info` for type decisions; `_label_enum_name` is a vestige that was apparently scaffolded alongside its two siblings but never wired in.

**Consequence:** Dead code silently accumulates. Future contributors encountering it will either assume it is used somewhere (introducing confusion and potentially cargo-culting it into new code paths where it is wrong) or spend time tracing whether it is actually dead. The `LabelEnum` naming it implies (`GrammarLabel`, etc.) belongs to the Python CST layer, not the Rust layer; if someone mistakenly wires it into generated Rust, the symbol names will be wrong.

**Fix:** Delete the method. If the `LabelEnum` suffix is later needed for an accessor context, re-add it with the correct Rust name at that point.

---

**quality-2**

File: `fltk/fegen/gsm2parser_rs.py:74`

```python
self._source_name = source_name or "<unknown>"
```

Design §2.1 states `source_name=None` should omit the `"from \`<source_name>\`"` clause entirely (`"When None, the 'from <source_name>' clause is omitted"`). The implementation instead substitutes the string `<unknown>` and always emits the clause. The generated header for unit-test-constructed generators (which pass no `source_name`) therefore says `"from \`<unknown>\`"` rather than omitting the clause.

**Consequence:** The design contract for consumers building `RustParserGenerator` directly (e.g., test helpers, programmatic use) is violated. The string `<unknown>` leaks into the generated file's doc comment in all non-CLI invocations. If a downstream tool parses the header comment (e.g., to detect whether a file is generated and from what), it will see a misleading literal rather than a recognizable absence. The design also notes the `source_name` parameter should let tests avoid fake filenames — the substitution defeats that.

**Fix:** In `_gen_header`, branch on `self._source_name is None`: emit the full clause only when it is not `None`, and store the raw `source_name` value (including `None`) in `self._source_name` without substituting a default. Update `test_source_name_in_header` to also verify that `source_name=None` omits the clause.

---

**quality-3**

File: `fltk/fegen/gsm2parser_rs.py:492–494` vs. `fltk/fegen/gsm2parser.py:643`

Rust generator uses `r"[\s]+"` as the hardcoded separator pattern inside trivia rules; Python generator uses `r"\s+"`. These are semantically equivalent but are different pattern strings. Phase 3 requires error-message parity: the error tracker records the literal pattern string, and `format_error_message` emits it verbatim. Any trivia rule that uses a WS_REQUIRED separator (rare but valid) and fails will produce different error messages from the Python and Rust backends.

**Consequence:** Phase 3 parity assertion will either be broken for this case, or will need a special-case carve-out. The divergence is invisible in the current test suite because the fixture tests only test WS_REQUIRED in non-trivia rules, and the fegen grammar's trivia rule has only `NO_WS` separators internally. The discrepancy will surface late (Phase 3), where the context to diagnose it will be harder to reconstruct.

**Fix:** Align to one pattern. The natural choice is `r"[\s]+"` (matching the default `_trivia` rule term from `gsm.add_trivia_rule_to_grammar:394`), since the Rust generator already uses that and it deduplicates with the trivia rule's own regex entry in the table. Change `gsm2parser.py:643` from `r"\s+"` to `r"[\s]+"`, or (less invasive) accept that the Python generator uses `\s+` and change the Rust generator to match. Either direction is fine; the fix is to make them identical, and to add a test that fires if they drift again (e.g., a test that parses the same WS_REQUIRED-in-trivia grammar with both backends and asserts equal error messages on failure).

---

**quality-4**

File: `fltk/fegen/test_gsm2parser_rs.py:608–618`

```python
def test_suppress_disposition_no_append() -> None:
    """SUPPRESS disposition must not generate append code."""
    grammar = _make_literal_grammar()
    gen = RustParserGenerator(grammar)
    src = gen.generate()
    assert "pub fn apply__parse_kw(" in src
```

The test's asserted invariant ("no append code for suppressed item") is not tested. The test only asserts that the `apply__` wrapper exists, which is true for any rule regardless of its item dispositions. The description promises to verify that `SUPPRESS` produces no `push_child`/`append_` for the suppressed item, but the assertion body does not do that.

**Consequence:** The SUPPRESS no-append invariant has no test coverage. A regression (e.g., accidentally emitting `push_child` for suppressed items) would not be caught, while the test would still pass. The test gives false confidence.

**Fix:** Add an assertion on the generated source: locate the `kw` rule body and verify it contains no `push_child` or `append_` call. The same pattern used in `test_optional_item_no_return_none` and `test_zero_or_more_quantifier` (splitting on function name boundaries and checking the body substring) applies here.
