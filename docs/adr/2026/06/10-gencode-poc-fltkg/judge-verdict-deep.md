# Judge verdict — deep review (gencode-poc-fltkg)

Phase: deep. Base 6d42885..HEAD 8e599f4 (review commit 815c95f + fix commit 8e599f4). Round 1.
Notes: 3 reviewer files; 7 findings (2 correctness, 3 test, 2 quality). All dispositioned Fixed.
Style: concise, precise, no padding.

## Added TODOs walk

No TODOs added in the diff; no TODO dispositions. (TODO.md entry `gencode-poc-fltkg` removed per spec; `git grep gencode-poc-fltkg` outside the ADR dir returns nothing.)

## Other findings walk

### correctness-1 — Fixed
Claim: drift-guard fixture checked only `result is not None`, accepting partial parses the real `gen-rust-cst` path rejects; consequence is a false-green guard for trailing-garbage perturbations, violating request.md §Verification.
Diff at `tests/test_gsm2tree_rs.py:1177-1183`: fixture body replaced with `from fltk.fegen.genparser import _parse_grammar_raw` + `return _parse_grammar_raw(fltkg_path)`. Verified `_parse_grammar_raw` delegates to `_read_and_parse_grammar`, which rejects partial parses via `if not result or result.pos != len(terminals.terminals)` (`genparser.py:50`) and raises `typer.Exit(1)` — a perturbed file now fails the fixture loudly instead of comparing a truncated GSM.
Assessment: fix addresses the consequence at the named location. Accept.

### correctness-2 — Fixed
Claim: `Items.initial_sep` uncompared; a leading-separator divergence between `.fltkg` and `_make_poc_grammar()` passes the guard silently (empirically demonstrated by the reviewer).
Diff at `tests/test_gsm2tree_rs.py:1198`: `assert fltkg_alt.initial_sep == expected_alt.initial_sep` added, first assertion in the per-alternative loop; parametrized over both rules (`identifier`, `items`), so coverage matches the two original per-rule tests.
Assessment: exact fix the finding requested. Accept.

### test-1 — Fixed
Same `initial_sep` gap as correctness-2; same fix verified above. Accept.

### test-2 — Fixed
Claim: three-test structure verbose; reviewer proposed whole-Grammar `assert fltkg_grammar == _make_poc_grammar()`.
Responder collapsed the two per-rule methods into one `@pytest.mark.parametrize("rule_name", ["identifier", "items"])` test (`tests/test_gsm2tree_rs.py:1191-1206`) and rejected whole-Grammar `__eq__` with rationale: `Grammar.rules` is a `list` in the parsed path vs `tuple` in `_make_poc_grammar()`.
Verified: `Cst2Gsm.visit_grammar` builds `rules = [...]` (list, `fltk2gsm.py:15`); `_make_poc_grammar` builds `rules=(identifier_rule, items_rule)` (tuple, `tests/test_gsm2tree_rs.py:66`); `[..] == (..)` is False in Python, so the reviewer's proposed single-assertion form would fail spuriously. Responder's rejection of the specific mechanism is sourced and correct; the dedup intent of the finding is satisfied by the parametrized form, which also keeps `strict=True` zips and explicit length asserts.
Assessment: fix addresses the consequence (single place for future field additions); rejected sub-suggestion correctly refuted. Accept.

### test-3 — Fixed
Claim: fixture re-implemented the pipeline inline instead of calling `_parse_grammar_raw`, risking silent divergence from the production regen path.
Same fix as correctness-1, verified above: fixture is now a thin adapter over the exact function `gen-rust-cst` uses (raw, pre-trivia — correct per request.md, since `RustCstGenerator` applies trivia internally).
Assessment: structurally coupled to the production path as requested. Accept.

### quality-1 — Fixed
Same finding as test-3/correctness-1 (duplication + missing position check). Same verified fix; the inline `fltk2gsm`/`fltk_parser`/`terminalsrc` usage is gone from the fixture. Accept.

### quality-2 — Fixed
Same finding as test-2 (copy-paste per-rule methods). Verified the committed form matches the reviewer's proposed parametrize shape. Accept.

## Cross-checks

- `uv run pytest tests/test_gsm2tree_rs.py::TestPocGrammarFltkg` at HEAD: 3 passed.
- `src/cst_generated.rs` untouched in 6d42885..8e599f4 (diff stat covers only Makefile, TODO.md, `__init__.pyi` comment, new `.fltkg`, test file) — byte-identity constraint holds.
- Disposition line numbers are within ±2 of actual (fixture 1177-1183 vs claimed 1181-1183; `initial_sep` at 1198 vs claimed 1200); immaterial.

## Disputed items

None.

## Approved

7 findings: 7 Fixed verified (correctness-1/test-3/quality-1 share one fix; correctness-2/test-1 share one fix; test-2/quality-2 share one fix).

---

## Verdict: APPROVED

All dispositions verified against the diff and the code; the one rejected reviewer sub-suggestion (whole-Grammar `__eq__`) was refuted with verified evidence.
