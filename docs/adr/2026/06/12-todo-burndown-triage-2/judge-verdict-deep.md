# Judge verdict — deep review

Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

Phase: deep. Base a48f820..HEAD a993259. Round 2 (APPROVED or ESCALATE only).
Notes: 7 reviewer files (errhandling, correctness, security, quality, efficiency: no findings); 5 findings total (test-1..4, reuse-1). Round 1 disputed only reuse-1; the four test fixes were verified and accepted in round 1 and the round-2 diff (e2e510c..a993259) does not touch the test file.

## Added TODOs walk

None remaining. The single round-1 TODO (reuse-1 / `TODO(gsm-item-walker)`) was promoted to Fixed; walked below.

## Other findings walk

### reuse-1 — Fixed (was TODO; round-1 REWORK trigger)
Claim: `_collect_underscore_only_label_errors` and `_collect_repeated_nil_errors` duplicated the Items-traversal skeleton, created by this iteration.
Diff at commit a993259 (`gsm.py`): `_for_each_item(items, visitor)` extracted at gsm.py:291-302 (depth-first, recurses into every `Sequence[Items]` alternative regardless of quantifier — matches both originals). Both collectors refactored onto it: label collector ignores `_idx`; nil collector's closure receives `item_idx` and the error message `f"Rule '{rule_name}' item {item_idx}: ..."` is preserved verbatim (verified at gsm.py:418-430). Enumerate-within-each-nested-`Items` semantics identical to the original per-level recursion. `Callable` import added. `TODO(gsm-item-walker)` comment and `TODO.md` entry both removed (grep confirms zero hits). `test_name_validation.py` + `test_nil_validation.py`: 28/28 pass.
Assessment: exactly the rework the round-1 verdict required — extraction now, traversal owned once, bookkeeping complete. Accept.

### test-1 — Fixed (verified round 1, unchanged)
`plumbing.parse_text(parser_result, "hello", rule_name="root")` + success assertion added to the `_foo` regression test, matching design test-plan item 8. Accept.

### test-2 — Fixed (verified round 1, unchanged)
`test_rule_named_empty_string_raises` pins the empty-string-name rejection via the `snake_to_upper_camel("") == ""` predicate. Accept.

### test-3 — Fixed (verified round 1, unchanged)
`test_plumbing_rejects_label_underscore` pins plumbing-level rejection of label `_`. Accept.

### test-4 — Fixed (verified round 1, unchanged)
Both label-error tests now assert "label" and "underscore" appear in the message. Accept.

## Disputed items

None.

## Approved

5 findings: 5 Fixed verified (4 from round 1, reuse-1 in round 2).

---

## Verdict: APPROVED

All dispositions acceptable. Round-1 disputed item (reuse-1) fully resolved at commit a993259.
