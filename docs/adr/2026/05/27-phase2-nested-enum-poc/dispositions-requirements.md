# Dispositions: Requirements Review — Phase 2 Nested Enum PoC

Concise. Precise. Complete. Unambiguous. No padding. Audience: smart LLM/human.

---

## requirements-1

- Disposition: Fixed
- Action: Clarified `child()` return description in "Generic methods" to explicitly state it returns a `(label, child)` 2-tuple (the single element of `node.children`), and raises `ValueError` otherwise.
- Severity assessment: Low. AC 19 already pins the exact behavior; only the prose was imprecise. An implementer reading only the system-behavior section could return the unwrapped child value.

---

## requirements-2

- Disposition: Fixed
- Action: Added `extend_<label>` to AC 25's method list.
- Severity assessment: Medium. The five-method pattern is stated elsewhere but AC 25 is the checklist for Items. Omitting `extend_<label>` could cause an implementer or reviewer to skip four methods.

---

## requirements-3

- Disposition: Fixed
- Action: Removed the "Rust source files" subsection from "User-Visible Surface." Internal file layout is design, not requirements.
- Severity assessment: Low. The "or similar" hedge made it non-binding, but it doesn't belong in a requirements doc.

---

## requirements-4

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: None. The constraint is intentional.
- Rationale: The requirements doc explicitly calls this "a deliberate simplification" and cites evidence that no production code checks `isinstance(result, types.GeneratorType)`. The exploration (section 6) confirms all callers iterate or call `list()`. Making the return type unconstrained (list-or-iterator) adds ambiguity to the acceptance criteria without benefit — AC 11 asserts `list(node.children_name()) == [s1, s2]`, which works for both, but the "deliberate simplification" note gives the implementer a clear, simple target. The Python CST returns a generator; the Rust PoC returning a list is a known, documented divergence. Relaxing the constraint would actively harm clarity for no gain in this PoC context.

---

## requirements-5

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: None. The reviewer retracted this finding ("no actual error... This finding is retracted — no issue").
- Rationale: Self-retracted by reviewer.

---

## requirements-6

- Disposition: Fixed
- Action: Added note to "Label enum semantics": "Cross-type `__eq__` (e.g., `Identifier.Label.NAME == Items.Label.ITEM`) may return `False` or `NotImplemented`; both are acceptable as long as `!=` returns `True`."
- Severity assessment: Low. Both `False` and `NotImplemented` produce the correct `!=` result. Documenting acceptability of either prevents unnecessary custom `__richcmp__` work.

---

## requirements-7

- Disposition: Fixed
- Action: Changed AC 6 to: "Holding two references: `a = node.children; b = node.children; assert a is b` — same object on repeated access."
- Severity assessment: Medium. The original `id(node.children) == id(node.children)` formulation is genuinely unreliable due to CPython GC reusing memory addresses when the first reference is dropped before the second `id()` call. A test written from the original AC could pass or fail non-deterministically.

---

## requirements-8

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: None. The reviewer retracted this finding ("No issue. Retracted.").
- Rationale: Self-retracted by reviewer.

---

## requirements-9

- Disposition: Won't-Do
- Action: No change.
- Severity assessment: None. Affirmative finding — reviewer confirmed the requirements are sound.
- Rationale: Positive assessment, not actionable.

---

## requirements-10

- Disposition: Fixed
- Action: Added to "Generic methods": "`append(child, label=None)` — both parameters are positional-or-keyword (not keyword-only)." Same for `extend`.
- Severity assessment: Medium. The Python CST allows positional `label`, and generated parser code may pass it positionally. If the Rust implementation made `label` keyword-only, Phase 3+ integration would break silently (the PoC tests would pass but real callers would fail).

---

## requirements-11

- Disposition: Fixed
- Action: Added AC 27: "After `node.append(child_a)` (unlabeled) followed by `node.append_name(child_b)`, `list(node.children_name())` returns `[child_b]` only — the unlabeled child is excluded." This directly tests the `None`-label filtering that `OQ-none-label-eq` flags as needing empirical verification.
- Severity assessment: High. This is one of the two core PoC goals (label discrimination), and without this AC the PoC could pass all tests while `None`-vs-label comparison is broken. The exploration (section 13, question 5) explicitly calls this out.

---

## requirements-12

- Disposition: Fixed
- Action: Resolved `OQ-extend-iterable`. Removed from Open Questions. Added statement to "Generic methods" and "Per-label methods" sections: "The `extend` and `extend_<label>` methods accept any Python iterable, not only lists." The system-behavior section already says "for each `child` in the iterable," so this makes the implicit explicit and removes the contradiction of having an OQ for something already decided.
- Severity assessment: Low. The OQ contained implementation advice (`&Bound<'_, PyAny>`) that doesn't belong in requirements. Resolving it removes confusion without changing behavior.
