# Judge verdict — requirements review

Phase: requirements. Artifact: `requirements.md`. Round 1.
Notes: 1 reviewer file; 12 findings.

## Other findings walk

### requirements-1 — Fixed
Claim: "Generic methods" section describes `node.child()` as returning `node.children[0]` without stating the return type is a `(label, child)` 2-tuple; consequence is implementer might return only the child value.
Disposition: Fixed — clarified `child()` return description.
Evidence: `requirements.md:75` now reads: `node.child()` returns the single element of `node.children` — a `(label, child)` 2-tuple — if `len(node.children) == 1`, otherwise raises `ValueError`. This matches the reviewer's suggested fix verbatim.
Assessment: Fix addresses the consequence. Accept.

### requirements-2 — Fixed
Claim: AC 25 lists four of five per-label methods, omitting `extend_<label>`; consequence is implementer or reviewer skipping four `extend_*` methods for Items.
Disposition: Fixed — added `extend_<label>` to AC 25.
Evidence: `requirements.md:158` AC 25 now lists: `append_<label>`, `extend_<label>`, `children_<label>`, `child_<label>`, `maybe_<label>`. All five present.
Assessment: Fix addresses the consequence. Accept.

### requirements-3 — Fixed
Claim: "Rust source files" subsection in "User-Visible Surface" is implementation direction, not requirements; consequence is unnecessary review friction.
Disposition: Fixed — removed the subsection.
Evidence: The "User-Visible Surface" section (lines 110-127) now contains only "Module registration," "Test file," and "No CLI changes..." — no "Rust source files" subsection.
Assessment: Fix addresses the consequence. Accept.

### requirements-4 — Won't-Do
Claim: Constraining `children_<label>()` to return a list (not generator/iterator) is over-specification; consequence is low — implementer would likely choose list anyway.
Rationale: The constraint is intentional, documented as "deliberate simplification," PoC context makes a clear simple target more valuable than flexibility, and relaxing it adds ambiguity without gain.
Inspection: `requirements.md:170` explicitly states "Returns a Python list (not a generator/iterator). This is a deliberate simplification..." with justification that no production code checks `isinstance(result, types.GeneratorType)`.
Assessment: The reviewer's own severity is "Low" and acknowledges "the implementer probably would choose a list anyway." The responder's rationale that constraining the return type in a PoC simplifies implementation and acceptance criteria is sound — a PoC benefits from fewer degrees of freedom. The finding has no meaningful consequence. Accept Won't-Do.

### requirements-5 — Won't-Do
Claim: Error message format issue.
Rationale: Self-retracted by reviewer ("no actual error... This finding is retracted — no issue").
Assessment: Reviewer explicitly retracted. Accept Won't-Do.

### requirements-6 — Fixed
Claim: Requirements don't specify cross-type `__eq__` return value (`False` vs `NotImplemented`); consequence is implementer uncertainty when writing `__richcmp__`.
Disposition: Fixed — added note clarifying both are acceptable.
Evidence: `requirements.md:67` now reads: "Cross-type `__eq__` (e.g., `Identifier.Label.NAME == Items.Label.ITEM`) may return `False` or `NotImplemented`; both are acceptable as long as `!=` returns `True`."
Assessment: Fix addresses the consequence. Accept.

### requirements-7 — Fixed
Claim: AC 6 uses `id(node.children) == id(node.children)` which is unreliable due to CPython GC; consequence is non-deterministic test results.
Disposition: Fixed — changed to two-reference form.
Evidence: `requirements.md:139` AC 6 now reads: "Holding two references: `a = node.children; b = node.children; assert a is b` — same object on repeated access."
Assessment: Fix addresses the consequence. Accept.

### requirements-8 — Won't-Do
Claim: Missing specification for `child()` with zero children.
Rationale: Self-retracted by reviewer ("No issue. Retracted.").
Assessment: Reviewer explicitly retracted. Accept Won't-Do.

### requirements-9 — Won't-Do
Claim: Affirmative finding — requirements are sound.
Rationale: Positive assessment, not actionable.
Assessment: Correct disposition for a non-actionable affirmative. Accept Won't-Do.

### requirements-10 — Fixed
Claim: Requirements don't specify whether `label` parameter in `append`/`extend` is positional-or-keyword vs keyword-only; consequence is Phase 3+ integration breakage if implementer chooses wrong calling convention.
Disposition: Fixed — added explicit positional-or-keyword specification.
Evidence: `requirements.md:76` now reads: "`append(child, label=None)` and `extend(children, label=None)` — both parameters are positional-or-keyword (not keyword-only)."
Assessment: Fix addresses the consequence. Accept.

### requirements-11 — Fixed
Claim: No AC tests `None`-label filtering (mixing unlabeled and labeled children then verifying `children_name()` excludes unlabeled); consequence is PoC could pass all ACs while core label-discrimination behavior is broken.
Disposition: Fixed — added AC 27.
Evidence: `requirements.md:160` AC 27: "After `node.append(child_a)` (unlabeled) followed by `node.append_name(child_b)`, `list(node.children_name())` returns `[child_b]` only — the unlabeled child is excluded."
Assessment: Fix addresses the consequence directly. This was the highest-severity finding and the AC pins the exact behavior. Accept.

### requirements-12 — Fixed
Claim: `OQ-extend-iterable` is an open question about something already decided in the behavioral spec; consequence is confusion.
Disposition: Fixed — resolved the OQ, added explicit "any Python iterable" statement.
Evidence: `requirements.md:185-187` shows `OQ-extend-iterable` struck through and marked resolved. `requirements.md:88` states: "The `extend` and `extend_<label>` methods accept any Python iterable, not only lists."
Assessment: Fix addresses the consequence. Accept.

## Approved

12 findings: 8 Fixed verified, 1 Won't-Do with sound rationale (requirements-4), 3 Won't-Do on retracted/affirmative findings (requirements-5, -8, -9).

---

## Verdict: APPROVED
