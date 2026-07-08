# Judge verdict — pre-pass (round 5)

Phase: pre-pass (slop + scope). Base 1e920dc..HEAD f38cdb3. Round 1.
Notes: notes-prepass-slop-r1.md (2 findings), notes-prepass-scope-r1.md (no findings).
Dispositions: dispositions-prepass-r1-a1.md.

## Added TODOs walk

No TODO-dispositioned findings; no `TODO(` comments added anywhere in 1e920dc..f38cdb3
(verified by diff grep). Section vacuous.

## Other findings walk

### slop-1 — Fixed (disputed: incomplete)
Claim: "step3" workflow-milestone label in permanent code comments at `fltk/lsp/server.py:170`
and `:831`; consequence — future/out-of-tree readers have no "step3" to look up; changelog-style
leak. Comment-hygiene standard applies (standing project rule, not reviewer invention).
Diff at f38cdb3: both named lines reworded to "same-file-only shape/behavior" — accurate,
self-contained, behavior-describing. The named lines are correctly fixed.
However: the identical defect class survives elsewhere **in this same round's added code** —
`fltk/lsp/test_server_crossfile.py:288` ("byte-identical to step3: ...") and `:302` ("the step3
behavior"), both added lines in the 1e920dc..f38cdb3 diff (grep over `fltk/lsp/*.py` and
`examples/gear/` at HEAD confirms these are the only two remaining `stepN` references).
Assessment: the finding's substance — no workflow-milestone pointers in permanent code — is only
partially addressed. An owner asked to remove "step3" leakage sweeps the diff, not just the two
lines the reviewer happened to quote. Partial fix → dispute.

### slop-2 — Fixed
Claim: `fltk/lsp/test_gear_demo.py:74` comment references "the requester's brief" — authoring-
session note, not documentation of the assertion.
Diff at f38cdb3: comment reworded to state the invariant directly ("Comments/trivia, strings,
numbers, keywords, operators, types, and (via const) constants must all be distinctly
classifiable over the sample."). No requester/task reference remains.
Assessment: fix addresses the consequence at the named line. Accept.

### Scope notes — no findings
Reviewer confirmed every design deliverable (§3, §4.1–§4.10) present, out-of-scope items (§1)
absent, the one documented deviation (references-aggregation subsuming §4.4's (a)/(b) split) a
strict superset. Nothing to disposition; nothing to adjudicate.

## Disputed items

- **slop-1**: same defect class still standing at `fltk/lsp/test_server_crossfile.py:288` and
  `:302` — "step3" as a behavior label in comments added by this round. Need: reword both to
  describe the behavior on its own terms. Concrete fix, within design scope (comment-only):
  - line 288: `# Without --resolver, definition is byte-identical to a resolver-free server:
    \`hub: Circle\` resolves to the local ...`
  - line 302: `# ... a same-file rename of a shape proceeds (the same-file-only behavior),
    proving the guard is resolver-gated.`
  Any equivalent self-contained wording is fine; the requirement is no workflow-milestone
  pointer.

## Approved

2 findings: 1 Fixed verified (slop-2), 1 Fixed partially verified and disputed (slop-1).
Scope: clean, no dispositions required.

---

## Verdict: REWORK

slop-1's fix is incomplete — the flagged defect class ("step3" workflow labels in permanent
comments) persists at two locations in this round's own added code
(`fltk/lsp/test_server_crossfile.py:288`, `:302`). Round 1; trivial comment-only rework.
