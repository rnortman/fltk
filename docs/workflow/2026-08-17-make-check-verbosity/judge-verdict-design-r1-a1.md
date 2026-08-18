# Judge verdict — design review

Phase: design. Doc: `docs/workflow/2026-08-17-make-check-verbosity/design.md`. Round 1.
Notes: 1 reviewer file (`notes-design-design-reviewer-r1.md`); 3 findings. Dispositions: `dispositions-design-r1-a1.md`.

## Other findings walk

### design-open-question-1-contradicts-files-touched — Fixed
Claim: former Open question 1 presented Part 3 as undecided while Files touched, Test plan and the "~140s → ~80s" outcome were written as if decided; consequence is implementation ambiguity on the largest change — an implementer guessing "defer" ships the diagnosis without its fix and orphans the guard-test updates.
Severity: real should-fix. A design doc that contains two incompatible file-touch lists cannot be implemented without a guess.
Evidence in the current doc: "Proposed approach" (design.md:56-62) now reads "Three parts, all landing in this change" and carries the rationale for including Part 3 ("shipping the diagnosis without the one-file fix for its dominant finding would be perverse"). `grep` for `Open question` finds exactly two hits — the section heading at :264 and the forward reference at :186 — and the section holds a single numbered item, the ~60-80s floor question; the `TODO(batch-pyo3-cqueries)` defer branch is gone from the doc entirely. The dangling "(see Open question 2)" is resolved to "(see Open questions)" at :186, which is now correct since the floor question is the only one. Files touched (:190-196) and Test plan (:244-253) are unchanged and were already in the "land it" shape, so the doc is internally consistent.
Residual checked: Files touched still says `TODO.md` is "untouched, unless the user's answer to the open question introduces a deferral" (:194). With Part 3 resolved, "the open question" unambiguously names the surviving floor question, whose defer branch would plausibly want a TODO entry. Not ambiguity — a correct conditional over the one question that remains open.
Assessment: fix addresses the consequence; the resolution direction is the one the doc's own argument supported. Accept.

### design-consumer-graph-computed-once-claim-inaccurate — Fixed
Claim: "the new shape computes each graph once" is false — `//:consumer_serde` is still traversed inside the union cquery and again standalone; consequence is minor (could invite a future "deduplicate onto the union" edit that weakens the serde assertion the design elsewhere rejects weakening).
Severity: nit-to-should-fix; the reviewer priced it correctly as minor.
Evidence in the current doc: design.md:172-175 now reads "The saving is in invocation count, not graph deduplication: `//:consumer_serde`'s graph is still traversed twice (inside the union and standalone), but the per-invocation dispatch/invalidation cost … drops from 4 payments to 2." The inaccurate sentence is gone, and the replacement states the double traversal as accepted, which forecloses the future edit the reviewer worried about. Verified 4 → 2 against source: `Makefile:216-235` is a 3-iteration cquery loop plus one standalone `deps(//:consumer_serde)` cquery.
Assessment: accurate as rewritten. Accept.

### design-timing-measurements-unverified — Fixed
Claim: the Context table's figures and the ~80s projection are not verifiable from source; recorded explicitly as unverified-not-wrong, asking only that the manual re-measurement hedge be kept.
Severity: informational. The finding states no defect, so there is nothing for a disposition to fix; the only actionable content is "keep the hedge".
Evidence: the hedge is present — Test plan :259-262 still includes "a re-run of the timing measurement to confirm the ~80s expectation"; Context :15-16 states its measurement conditions; Part 3's justification is stated structurally (13 serial invocations → 3, :30-33 and :133), so the exact seconds are not load-bearing. Independently spot-checked the structural claims the figures rest on: root loop is a per-target cquery loop over the derived `$labels` set (`Makefile:165-173`), consumer is 3 + 1 (`Makefile:216-235`), so "13 serial cquery invocations" is the right shape given 9 root labels.
Assessment: "Fixed" is a loose label for a no-edit-required informational finding, but the substance is right and the one thing the reviewer asked to preserve is preserved. Accept.

## Approved

3 findings: 3 Fixed verified (2 with doc edits, 1 no-edit-required by the finding's own terms).

Additional owner-level read of the design beyond the findings: the batching identity `deps(set(a b c)) = deps(a) ∪ deps(b) ∪ deps(c)` is sound; the union positive control preserves the "a silently-empty cquery must not pass vacuously" purpose the existing `Makefile:200-202` comment and `test_the_pyo3_guard_survives_in_the_bazel_test_recipe` both state, and the knowingly-given-up per-target control is called out rather than glossed; the attribution fallback is fail-closed ("exit 1 unconditionally"); the serde assertions correctly stay off the union; the `VERBOSE ?= $(if $(filter true,$(CI)),1,0)` semantics and the quiet path's retained buffer/dump-on-failure keep the property `.bazelrc:28-32` documents. No unaddressed defect found.

---

## Verdict: APPROVED

All three dispositions acceptable; design is self-consistent against source at `e677c38`.
