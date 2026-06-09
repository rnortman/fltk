# Dispositions — rust-cst-child-span-test deep review

Style: concise, precise, complete, unambiguous. No padding. Audience: smart LLM/human.

## correctness-1

- Disposition: Fixed
- Action: Move `tsrc.Span(3, 9)` construction outside the `pytest.raises` block and add `match="unsupported child type"` to the `raises` call. File:line `tests/test_phase4_fegen_rust_backend.py:162-167`.
- Severity assessment: The test's stated contract is that `append_<label>` rejects non-`Span` children loudly. With the span constructed inside the `raises` block and no `match=`, a `TypeError` from the constructor or method lookup would make the test pass vacuously — defeating the contract pin in exactly the future-drift scenarios it is designed to catch.
- Rationale: Verified against source. `tsrc.Span` is a frozen dataclass (`terminalsrc.py:48`); `tsrc.Span(3, 9)` constructs cleanly today, so the test is currently non-vacuous. But the design explicitly frames test 3 as a "deliberate contract pin" against silent drift; a vacuous future pass contradicts that stated purpose. Fix: `bad = tsrc.Span(3, 9)` before the block; `with pytest.raises(TypeError, match="unsupported child type"):` around only the `getattr(node, append_method)(bad)` call.

---

## test-1

- Disposition: Won't-Do
- Action: no change
- Severity assessment: `child_method` is intentionally unused in `test_append_rejects_terminalsrc_span` — the test exercises the append rejection path only. The `noqa: ARG002` suppression is the correct mechanism; the design explicitly scopes test 3 to the append direction. This is not a gap.
- Rationale (Won't-Do): The parameter is present because the parametrize fixture is shared across all three tests in the class; removing it from the signature would break the parametrize binding. The `noqa` is the right resolution. Changing this would require splitting the parametrize fixture or adding a dummy use, both worse than the status quo.

---

## test-2

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Nil. The `result.start == 3` integer equality assertion is sufficient to confirm that `.start`/`.end` are plain `int` values usable as slice arguments — an opaque proxy would fail the equality assert or require `__eq__` trickery. No additional assertion is needed.
- Rationale (Won't-Do): The reviewer's own conclusion was "not a gap." No action warranted.

---

## test-3

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Nil. The source-bearing roundtrip test correctly asserts type, attribute values, source presence, and slice text. No gap identified.
- Rationale (Won't-Do): Reviewer found no issue; this is a confirmatory finding.

---

## test-4

- Disposition: Won't-Do
- Action: no change
- Severity assessment: Nil. The `Rule.child_name()` → `Identifier` path is not a span-returning accessor and is not in scope for `TestChildSpanAccessorContract`. The `Identifier` param covers the `visit_identifier` span-accessor path. No coverage gap.
- Rationale (Won't-Do): Reviewer found no issue; this is a confirmatory finding.

---

## test-5

- Disposition: Won't-Do
- Action: no change (correctness-1 already fixes the substantive issue here)
- Severity assessment: test-5 characterizes the absence of `match=` as "acceptable." This conflicts with correctness-1's correct analysis. The fix applied under correctness-1 (adding `match="unsupported child type"`) resolves the real concern.
- Rationale (Won't-Do): test-5 reached the wrong conclusion — "no finding" is incorrect given the vacuous-pass risk identified by correctness-1. No separate action needed; correctness-1's fix subsumes it.

---

## reuse-1

- Disposition: TODO(child-span-params-dedup)
- Action: Add `TODO(child-span-params-dedup)` comment adjacent to `_CHILD_SPAN_PARAMS` at `tests/test_phase4_fegen_rust_backend.py:115`. Add entry to `TODO.md`.
- Severity assessment: `_CHILD_SPAN_PARAMS` and the three `_span`-factory rows in `CLASS_LABEL_INFO` (`tests/test_fegen_rust_cst.py:55-57`) enumerate the same node/accessor triples in two separate files. A label rename in the generated CST would require updating both; silent divergence would cause the new tests to test a stale method name. The assertion bodies are genuinely distinct (not a duplicate test), so this is a parametrize-data duplication only.
- Deferred because: deduplifying requires either cross-file imports between test files (fragile) or a shared conftest fixture, which is a refactor beyond this test-addition scope. The duplication is low-risk in practice — these accessor names are generated from the grammar and change rarely. Tracking it in TODO.md is the right level of commitment.
