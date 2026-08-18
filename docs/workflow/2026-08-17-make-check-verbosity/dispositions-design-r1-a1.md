# Dispositions — design review r1

Design: `docs/workflow/2026-08-17-make-check-verbosity/design.md`
Notes: `notes-design-design-reviewer-r1.md`

design-open-question-1-contradicts-files-touched:
- Disposition: Fixed
- Action: Resolved the question in the design rather than leaving two incompatible
  file-touch lists. The "Proposed approach" intro now states all three parts land in this
  change and carries the (previously recommendation-only) rationale for including Part 3;
  former Open question 1 is removed; the surviving floor question is renumbered to 1; the
  "Files touched" `TODO.md` line no longer references a defer branch of a resolved
  question; the dangling "(see Open question 2)" cross-reference in Part 3's Expected
  outcome is updated. Verified: the reviewer is right that the rest of the document (Files
  touched, Test plan, Expected outcome) was already written to the "land it" shape, so
  resolving in that direction makes the doc self-consistent with zero further edits; the
  question was not genuinely user-judgment — the doc itself argued the defer branch was
  the worse outcome ("perverse").
- Severity assessment: Real implementation ambiguity on the largest change in the design;
  an implementer guessing "defer" would orphan the Test plan's guard-test updates and the
  ~80s outcome claim.

design-consumer-graph-computed-once-claim-inaccurate:
- Disposition: Fixed
- Action: Rewrote the sentence in Part 3's consumer-lane section. It now states the saving
  explicitly as invocation count (4 → 2 payments of dispatch/invalidation cost) and that
  `//:consumer_serde`'s graph is still traversed twice — which also forecloses the future
  "deduplicate onto the union" edit the reviewer flagged, since the sentence now says the
  double traversal is accepted, not an oversight. Verified against the design's own
  consumer-lane structure: the union cquery includes `//:consumer_serde` and the standalone
  `deps(//:consumer_serde)` remains, so "each graph once" was indeed false as written.
- Severity assessment: Minor accuracy issue; no implementation would go wrong from it, but
  it invited exactly the weakening (serde greps on the union) the design elsewhere rejects.

design-timing-measurements-unverified:
- Disposition: Fixed
- Action: No design edit required; the finding records the numbers as unverified-not-wrong
  and asks only that the manual re-measurement hedge be kept. It is kept: the Test plan's
  "Manual verification during implementation" paragraph still includes "a re-run of the
  timing measurement to confirm the ~80s expectation", and the Context table already
  states its measurement conditions (base commit, hot 82GB output base, zero source
  changes, all 258 tests cached). Part 3's justification remains structural (13 serial
  invocations → 3), per the design's own framing, so the exact seconds are not
  load-bearing.
- Severity assessment: Low; worst case the projected ~80s is off by some margin, which the
  retained manual re-measurement catches before the change is declared done.
