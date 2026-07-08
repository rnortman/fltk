# Judge verdict — deep review, round 5 (r1, attempt 2)

Phase: deep. Base `1e920dc`..HEAD `1d1f1b6` (rework commit `1d1f1b6` on top of the a1-reviewed
`481ba2e`). Round 2 — APPROVED or ESCALATE only.
Scope: the two dispositions REWORKed in `judge-verdict-deep-r1-a1.md` (correctness-2 pinning test;
errhandling-3 residual TODO). The other 25 dispositions were accepted in round 1 and are unchanged
in the rework diff (verified: `481ba2e..1d1f1b6` touches only `TODO.md`, `fltk/lsp/project.py`
comment lines, `fltk/lsp/test_project.py`, and the dispositions doc) — not re-walked.

## Added TODOs walk

### errhandling-3 residual — TODO(rename-guard-incomplete-scan) at `fltk/lsp/project.py` (`ProjectNavigator.rename_hazard`)
Q1 (worth doing): yes — an incomplete workspace scan (walk error, unreadable/unparseable neighbor)
lets the guard return `Hazard.NONE` and permit a rename that may break an unscanned file; real
fail-open residual on the one safety-critical path, created this round.
Q2 (design/owner input required): yes — the §4.6 fail-closed mandate vs. the §5
silent-degradation policy is a tension the frozen design did not resolve; refusing on every
transiently-unparseable neighbor would gut rename during live editing, so the policy choice needs a
design delta. This is the exact TODO the round-1 verdict prescribed as the acceptable resolution.
Mechanics: comment present in the diff immediately before the global reference scan it describes,
standing alone with the full hazard and the unresolved-policy reason (no ephemeral-doc references
in the code comment — hygiene clean); matching `TODO.md` entry present with slug, the §4.6-vs-§5
tension, the design-delta requirement, and location. Both halves of the convention satisfied.
"Created this round → cannot silently defer" is satisfied by escalation-in-place: the residual is
now durably surfaced, matching the security-2 shape round 1 endorsed.
Assessment: TODO acceptable. Disposition accepted.

## Other findings walk

### correctness-2 — Fixed (pinning tests added)
Round-1 gap: the URI-canonicalization fix was correct but invisible — the entire suite passed with
`canonical_uri` reverted to identity.
Evidence (diff at `fltk/lsp/test_project.py:192-222`):
- `test_canonical_uri_collapses_percent_encoding` — constructs a percent-encoded (`%61`) spelling
  string-unequal to the canonical form; asserts collapse to canonical and idempotence on the
  canonical form.
- `test_open_buffer_served_through_noncanonical_uri` — `ProjectHost` with `open_docs` keyed by the
  non-canonical spelling, lookup by the canonical form, asserts the open-buffer symbol
  (`InBuffer`) is served, not stale disk text. This is disputed-item fix (a) from the round-1
  verdict, exactly as prescribed.
Bite verified independently: both tests pass on HEAD (2 passed); with `canonical_uri` monkeypatched
to the identity function at runtime (no repo edit), the same scenario serves the stale disk symbol
`OnDisk` — confirming the test fails if the fix regresses. The responder's revert-check claim is
reproduced, not just asserted. Touched module fully green (22 passed).
Assessment: fix now pinned; disposition accepted.

## Disputed items

None. Both round-1 disputes resolved as prescribed.

## Approved

27 findings: 23 Fixed verified (correctness-2 now with pinning coverage), 2 Won't-Do sound
(round 1), 2 TODOs acceptable (security-2 from round 1; rename-guard-incomplete-scan this round).

---

## Verdict: APPROVED

Both REWORKed dispositions completed exactly as the round-1 verdict specified, with the pinning
test's bite independently reproduced. Round 2.
