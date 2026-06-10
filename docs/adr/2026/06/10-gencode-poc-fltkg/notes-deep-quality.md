# Quality Review — gencode-poc-fltkg (815c95f)

## quality-1

**File:line**: `tests/test_gsm2tree_rs.py:1183-1191` (the `fltkg_grammar` fixture)

**Issue**: The fixture re-implements the `.fltkg`-to-GSM parse pipeline inline instead of calling the existing `genparser._parse_grammar_raw(path)` (or its public-facing wrapper). `genparser._read_and_parse_grammar` already does exactly: open file, construct `TerminalSource`, call `fltk_parser.Parser`, assert full parse, construct `Cst2Gsm`, return `visit_grammar`. The fixture duplicates that logic — including skipping trivia processing, which is the correct behavior for comparison against `_make_poc_grammar()` — but omits the full-parse position check (`result.pos != len(terminals.terminals)`) and the structured error formatting on failure.

**Consequence**: Two code paths that must stay in sync with the real parse pipeline. If the pipeline changes (e.g. `apply__parse_grammar` is renamed, or an encoding step is added), `genparser._read_and_parse_grammar` is updated but the test fixture is silently left behind, causing a false-negative drift guard or a confusing test failure unrelated to grammar drift. The position check omission means a partial parse would pass `assert result is not None` and silently compare an incomplete GSM.

**Fix**: Replace the inline fixture body with a call to `genparser._parse_grammar_raw(fltkg_path)`. That function is already a thin wrapper over `_read_and_parse_grammar` that skips trivia processing — exactly the right input for comparison against `_make_poc_grammar()`. The leading underscore indicates internal but it is used from within the same package in production; a test call is equally appropriate, or `_parse_grammar_raw` can be promoted to a public export if preferred. Either way, the inline reimplementation should be removed.

---

## quality-2

**File:line**: `tests/test_gsm2tree_rs.py:1198-1228` (`test_identifier_rule_items` and `test_items_rule_items`)

**Issue**: The two test methods are copy-paste duplicates. The bodies are identical — both call `_make_poc_grammar()`, look up a rule by name from both grammars, assert alternative counts, then loop over items comparing the same four fields. Only the rule name string (`"identifier"` vs `"items"`) and the docstring differ.

**Consequence**: The spec required "compare meaningfully (rule-by-rule, item fields)" — a loop over rules would satisfy that and is the natural generalization. Instead, two near-identical methods exist. Adding a third rule to the PoC grammar requires a third copy-pasted method; the pattern propagates. A bug fix (e.g. adding comparison of a missing field) must be applied in two places.

**Fix**: Replace both per-rule methods with one parameterized test or a single helper that iterates over all rules:

```python
def _assert_rules_equal(self, fltkg_grammar: gsm.Grammar, rule_name: str) -> None:
    expected = _make_poc_grammar()
    fltkg_rule = fltkg_grammar.identifiers[rule_name]
    expected_rule = expected.identifiers[rule_name]
    assert len(fltkg_rule.alternatives) == len(expected_rule.alternatives)
    for fltkg_alt, expected_alt in zip(fltkg_rule.alternatives, expected_rule.alternatives, strict=True):
        assert fltkg_alt.sep_after == expected_alt.sep_after
        for fi, ei in zip(fltkg_alt.items, expected_alt.items, strict=True):
            assert fi.label == ei.label
            assert fi.disposition == ei.disposition
            assert fi.term == ei.term
            assert fi.quantifier == ei.quantifier

@pytest.mark.parametrize("rule_name", ["identifier", "items"])
def test_rule_items(self, fltkg_grammar: gsm.Grammar, rule_name: str) -> None:
    self._assert_rules_equal(fltkg_grammar, rule_name)
```

Or, since `test_rule_names_match` already asserts the rule list, simply loop over all rule names in the single test body.

---

No other quality findings.
