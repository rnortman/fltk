# Reuse Review — Phase 3 Python Bindings + Parity

Commit reviewed: b107645. Base: b668897.

---

## reuse-1

**File:line**: `tests/test_rust_parser_parity_fegen.py:92-118` and `tests/test_rust_parser_parity_fixture.py:109-133`

**What's duplicated**: The `test_parity` function body — parser construction, method dispatch (`getattr(p, f"apply__parse_{rule}")`), `TerminalSource` construction, and the full SUCCESS/PARTIAL/FAIL dispatch block — is reproduced almost verbatim in both modules. The SUCCESS and FAIL branches are byte-identical. The PARTIAL branch diverges only in that the fixture version adds a `if expected.pos == 0 and py_result is None` guard, which is a deliberate behavioural difference but implemented inline rather than through a shared path.

**Existing utility**: `tests/parser_parity.py` — the module introduced in this same diff to hold `assert_cst_equal`, `assert_error_equiv`, `_parse_error_message`, `_assert_messages_equiv`, and the `SUCCESS`/`PARTIAL`/`FAIL` sentinels. It is exactly the right home for a `run_corpus_entry(py_p, rust_p, ts, rule, text, expected)` helper (or similar name) that encodes the shared dispatch. The fixture-specific PARTIAL guard would either be passed as a flag or handled by the caller after calling the shared function.

**Consequence**: Any change to the parity contract — e.g. tightening the PARTIAL assertion, adding a `capture_trivia` assertion, or changing how FAIL error-equiv is invoked — must be made in two places. Given that a third grammar is plausible (the design anticipates future grammars), the duplication compounds. The `parser_parity` module's stated purpose is exactly this kind of shared infrastructure; leaving the dispatch loop out of it is an incomplete extraction.

---

No further findings.
