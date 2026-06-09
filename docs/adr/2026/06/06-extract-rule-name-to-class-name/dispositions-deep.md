test-1:
- Disposition: Fixed
- Action: tests/test_naming.py:43 — renamed to `test_lower_normalizes_mixed_case_input`; updated comment to say "Grammar identifiers are always lowercase; this covers programmatic callers."; added `assert snake_to_upper_camel("UPPER_CASE") == "UpperCase"` to make the `.lower()` effect unambiguous.
- Severity assessment: Minor clarity gap; no regression risk. The old comment described implementation rationale instead of the contract.

test-2:
- Disposition: Fixed
- Action: tests/test_naming.py:55-86 — added `test_unparser_generator_class_name_delegates_to_snake_to_upper_camel`; instantiates a minimal `UnparserGenerator` with a single-rule dummy grammar and asserts `class_name_for_rule_node("foo_bar") == "FooBar"` and `class_name_for_rule_node("no_ws") == "NoWs"`. Covers both the method delegation and the module-level list-comp (which uses the same `naming.snake_to_upper_camel` directly).
- Severity assessment: Medium; a regression to the unparser's `class_name_for_rule_node` (e.g., accidentally dropping `.lower()`) would not have been caught by any direct test; indirect roundtrip tests only.

test-3:
- Disposition: Won't-Do
- Action: no change
- Severity assessment: Informational only per the reviewer. `_rust_variant_name` is tested indirectly via `test_items_label_enum_present`; all grammar labels are lowercase so the behavioral unification is latent and untestable without non-grammar inputs. Reviewer explicitly said "no action required beyond test-1."
- Rationale (Won't-Do): The reviewer marked this informational and directed action to test-1. Adding a direct test of `_rust_variant_name` with uppercase inputs would test behavior on inputs the grammar rejects — vacuous coverage. The indirect test through generated source is appropriate for a private helper.
