# Test review notes — gencode-poc-fltkg (815c95f)

Concise, precise, no padding.

---

## test-1

**File:line** `tests/test_gsm2tree_rs.py:1198–1228` (`test_identifier_rule_items`, `test_items_rule_items`)

**What's wrong — missing field in item-level comparison.** Both tests compare `label`, `disposition`, `term`, and `quantifier` on each `Item` — the full public field set. However the `Items` container has a fourth field `initial_sep` (defaults to `NO_WS`, but can be `WS_ALLOWED` or `WS_REQUIRED` when a rule opens with a leading separator). Neither test asserts `fltkg_alt.initial_sep == expected_alt.initial_sep`. The current grammar has no leading separators so both sides are `NO_WS` — the omission does not produce a false positive today — but a future grammar change that adds a leading separator on the `items` rule would go undetected.

**Consequence.** A divergence in `initial_sep` between the `.fltkg` file and `_make_poc_grammar()` passes the drift-guard silently. The drift-guard's stated purpose is to detect exactly this kind of silent divergence; the gap partially defeats it.

**Fix.** Add `assert fltkg_alt.initial_sep == expected_alt.initial_sep` after the `sep_after` assertion in both rule tests. Alternatively, replace the manual field-by-field comparison with a single `assert fltkg_alt == expected_alt` (dataclass `__eq__` is defined on `Items`, `Rule`, and `Grammar` — it would catch `initial_sep`, `is_trivia_rule`, and any future field additions automatically).

---

## test-2

**File:line** `tests/test_gsm2tree_rs.py:1193–1228` (all three test methods)

**What's wrong — redundant three-test structure where one parameterized test (or one direct equality) would suffice.** The rule-names test and the two per-rule tests each call `_make_poc_grammar()` independently (three separate constructions). More importantly, `Rule`, `Items`, and `Item` all have dataclass `__eq__`, so `fltkg_grammar == _make_poc_grammar()` would be a single, complete, unforgeable equality assertion. The current approach is verbose and incomplete (see test-1 for the `initial_sep` gap); a whole-Grammar equality would catch every field now and in the future without needing to enumerate them.

**Consequence.** Not a correctness regression today, but the verbosity invites future maintainers to add new fields to `Item`/`Items`/`Rule` without updating the drift-guard, creating silent gaps over time.

**Fix.** Replace the three test methods with one:

```python
def test_fltkg_grammar_equals_make_poc_grammar(self, fltkg_grammar: gsm.Grammar) -> None:
    """The parsed .fltkg grammar is field-for-field identical to _make_poc_grammar()."""
    assert fltkg_grammar == _make_poc_grammar()
```

`Grammar.__eq__` compares `rules` (a sequence) and `identifiers` (a mapping); `Rule.__eq__` compares `name`, `alternatives`, and `is_trivia_rule` (the `compare=False` fields are excluded); `Items.__eq__` compares `items`, `sep_after`, and `initial_sep`; `Item.__eq__` compares all four fields. One assertion — nothing slips through.

---

## test-3

**File:line** `tests/test_gsm2tree_rs.py:1178–1191` (`fltkg_grammar` fixture)

**What's wrong — parse pipeline in the fixture does not match the actual `gen-rust-cst` code path.** `gen-rust-cst` calls `_parse_grammar_raw` → `_read_and_parse_grammar` → `fltk_parser.Parser(...).apply__parse_grammar` + `Cst2Gsm.visit_grammar`. The fixture re-implements that same sequence inline instead of calling `_parse_grammar_raw` (or the public `genparser._read_and_parse_grammar`). If `_read_and_parse_grammar` gains pre-processing steps (e.g. validation, normalization) the fixture will silently diverge from the actual regeneration path, producing false green results.

**Consequence.** The drift-guard's secondary purpose is to confirm the `.fltkg` file round-trips through the actual tool pipeline; if the pipeline changes and the fixture isn't updated, the guard gives false confidence.

**Fix.** Import and call `fltk.fegen.genparser._parse_grammar_raw` (or expose a thin public helper) in the fixture body, rather than re-implementing the four-line pipeline. The fixture should be a thin adapter:

```python
from fltk.fegen.genparser import _parse_grammar_raw
fltkg_path = pathlib.Path(__file__).parent.parent / "fltk" / "fegen" / "test_data" / "poc_grammar.fltkg"
return _parse_grammar_raw(fltkg_path)
```

This makes the drift-guard structurally coupled to the production path.

---

No other findings.
