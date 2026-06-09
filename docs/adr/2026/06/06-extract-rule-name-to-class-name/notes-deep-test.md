# Test Review: extract-rule-name-to-class-name

Commit reviewed: 8ddd61f. Concise, precise, complete, unambiguous. No padding.

---

## test-1

**File:line:** `tests/test_naming.py:43–45`

**What's wrong:** `test_lower_applied_to_mixed_case` asserts `snake_to_upper_camel("MixedLabel") == "Mixedlabel"`. This is documented as the design-chosen canonical form (`.lower()` applied), but the test name and comment say "copy 4 divergence unified here" — implying the value of this test is proving that the new shared helper applies `.lower()` where the old copy 4 did not. The assertion is correct and meaningful; however there is no complementary test confirming that a label containing an uppercase letter that _would_ have been handled differently by copy 4 now produces the same output as copies 1–3. The single input `"MixedLabel"` exercises the `.lower()` path but not the specific divergence scenario: copy 4 was called with labels like `"no_ws"` (already lowercase), so the behavioral unification is latent and never actually exercised in a way that distinguishes copy 4's old output from the new one. Consequence: if `_rust_variant_name` were accidentally reverted to omit `.lower()`, no test would fail on inputs that actually appear in production grammar (all grammar labels are lowercase snake_case per `_IDENTIFIER_RE`). The test would still pass. The fix to the behavioral divergence is untestable without uppercase label inputs — which the grammar rejects — so this is a documentation gap not a test gap. However the test name should reflect the contract ("`.lower()` canonicalizes mixed-case input") rather than the consolidation rationale, and a comment should note that this behavior only matters for non-grammar inputs (programmatic callers). Not a regression risk; minor clarity issue.

**Consequence:** No regression risk on real grammar inputs. A future caller that passes non-snake labels could silently rely on copy-4 behavior if this function is copy-pasted again. The test doesn't verify copy 4 specifically was fixed.

**Fix:** Rename to `test_lower_normalizes_mixed_case_input`. Add a comment: "Grammar identifiers are always lowercase; this covers programmatic callers." Optionally add a second case such as `snake_to_upper_camel("UPPER_CASE") == "UpperCase"` to make the `.lower()` effect unambiguous.

---

## test-2

**File:line:** `tests/test_gsm2tree_rs.py:450–479`

**What's wrong:** `test_rule_name_to_class_name_mapping` constructs a `CstGenerator` and calls `gen.class_name_for_rule_node(rule_name)` for each fegen rule name, asserting the expected class name. This tests the `CstGenerator.class_name_for_rule_node` delegation path. However, there is no analogous test verifying that `UnparserGenerator.class_name_for_rule_node` and the module-level `generate_unparser` list-comp (the third call site, `gsm2unparser.py:1824`) also delegate correctly. The unparser's `class_name_for_rule_node` is exercised indirectly by `test_phase4_rust_fixture.py` (which calls `generate_unparser` and then exercises the roundtrip), but no test directly asserts the class names produced by `UnparserGenerator.class_name_for_rule_node` against known values.

**Consequence:** If `UnparserGenerator.class_name_for_rule_node` were accidentally reverted to the old inline expression (which happens to be byte-identical to the canonical form), no test would catch it. More concretely, the inline list-comp at `gsm2unparser.py:1824` is separately updated; a regression there (e.g., dropping `.lower()`) would not be caught by any direct test. The roundtrip tests in `test_phase4_rust_fixture.py` exercise the generated unparser but don't assert specific class name strings.

**Fix:** Add a test that calls `UnparserGenerator.class_name_for_rule_node` directly (mirroring `test_rule_name_to_class_name_mapping`) against a representative set of rule names, confirming delegation to `naming.snake_to_upper_camel`. Or, since both `CstGenerator` and `UnparserGenerator.class_name_for_rule_node` are one-liners that delegate identically, at minimum add a smoke assertion on `UnparserGenerator` using one input (e.g. `"foo_bar"` → `"FooBar"`). The module-level list-comp doesn't need a separate test if `UnparserGenerator.class_name_for_rule_node` is covered, since it uses the same function directly.

---

## test-3

**File:line:** `tests/test_gsm2tree_rs.py` — no test for `_rust_variant_name`

**What's wrong:** `_rust_variant_name` in `gsm2tree_rs.py` is private but is tested indirectly: `test_items_label_enum_present` asserts `"    NoWs,"` in the generated source, which is produced by `_rust_variant_name("no_ws")`. This is adequate for the happy path. But no test exercises `_rust_variant_name` with a label name that would have produced a _different_ result under old copy 4 vs. the new unified form. Given that all grammar labels are lowercase, this is low risk. No action required beyond what test-1 notes about the behavioral unification being latent.

**Consequence:** None on current grammar inputs. Already noted in test-1.

**Fix:** None required beyond test-1.

---

## Summary

Two actionable findings (test-1 minor clarity, test-2 missing direct coverage of `UnparserGenerator.class_name_for_rule_node` and the module-level list-comp in `gsm2unparser.py`). test-3 is informational only. The unit tests in `test_naming.py` are substantive, well-named (except test-1), and cover the documented contract completely. No vacuous assertions, no over-mocking, no implementation-detail brittleness.
