# User arbitration of deep2 ESCALATE

OK, the primary reasons for escalation are related to a TODO the implementer left because the work is for future iterations. That's fine, so long as a future implementer does it, which TODO(fltkfmt-integration-tests) suggests that we will. The real complaint is this one:

### Secondary — test-4 (cleanup branches untested)

- **Reviewer's claim/consequence:** `write_atomic`'s `remove_file` cleanup on write-failure and
  rename-failure is untested; a broken cleanup would go undetected (atomicity is the `--in-place`
  invariant). Should-fix.
- **Responder's disposition/rationale:** Fixed — added a missing-dir failure test + a success test.
- **Why flagged:** the missing-dir test fails at `create_temp` (pre-refactor it would have hit the
  write branch; post-refactor it returns before either cleanup branch), so the cleanup branches
  remain uncovered and the "failure/cleanup path now has coverage" claim is inaccurate. On its own
  this is a round-1 REWORK item (add a test that actually reaches a cleanup branch — e.g. rename
  failure by targeting a directory). Folded here so the implementer addresses it alongside the
  primary scope decision.


That's not an incomplete scope problem, that's a "the test is supposed to work but doesn't" problem, so that should be fixed.
