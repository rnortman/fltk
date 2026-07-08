# Deep-review dispositions — round 5, r1 (rework attempt 2)

Rework round addressing the judge's REWORK verdict (`judge-verdict-deep-r1-a1.md`). Only the two
disputed items are revised; all other dispositions in `dispositions-deep-r1-a1.md` stand unchanged
and are not re-examined. Full suite green (`uv run pytest`: 2973 passed, 1 skipped — up two from the
new tests); `ruff check`/`pyright` clean on the touched files.

---

## correctness-2 (revised: Fixed — pinning test added)

- Disposition: Fixed
- Action: added the pinning tests the fix lacked (the code fix from a1 is unchanged and accepted).
  Two new unit tests in `fltk/lsp/test_project.py`:
  - `test_canonical_uri_collapses_percent_encoding` — constructs a percent-encoded (`%61` for `a`)
    spelling of a file URI, string-unequal to the canonical form, and asserts `canonical_uri`
    collapses it to the canonical spelling and is idempotent on the canonical form.
  - `test_open_buffer_served_through_noncanonical_uri` — keys `ProjectHost.open_docs` by the
    non-canonical spelling and looks the document up by the canonical form, asserting the open-buffer
    text (not stale disk text) is served. This is the judge's suggested fix (a).
- Verification that the test bites: with `canonical_uri` stubbed to the identity function (i.e. the
  fix reverted), `test_open_buffer_served_through_noncanonical_uri` reads stale disk text
  (`["OnDisk"]` instead of `["InBuffer"]`) and fails — confirmed by direct execution. Previously the
  entire suite passed with or without the fix; it now pins the fail-open/reference-drop hazard on
  divergent-serialization clients.
- Severity assessment: high on Windows/percent-encoding clients (unchanged from a1); the round-1
  gap was a TDD-coverage hole, now closed.

## errhandling-3 residual (revised: durable TODO marker added)

- Disposition: Fixed (surfacing) + TODO(rename-guard-incomplete-scan) (residual policy)
- Action: the a1 surfacing fix (`os.walk` `onerror` callback recording scan errors into the drained
  warnings) is unchanged and accepted. Added the durable marker the residual needed:
  - `TODO(rename-guard-incomplete-scan)` comment at `ProjectNavigator.rename_hazard`
    (`fltk/lsp/project.py`, just before the global reference scan it consumes), stating that an
    incomplete scan (walk error, or an unreadable/unparseable neighbor dropped from the scan) lets
    the guard return `Hazard.NONE`/permit despite a possibly-undetected cross-file reference, and
    that whether to refuse on any imperfect scan is an unresolved policy question. The comment stands
    alone (no reference to any ephemeral workflow/design doc, per project comment hygiene).
  - Matching `TODO.md` entry (`rename-guard-incomplete-scan`) recording the full tension — the one
    fail-closed path (step5 §4.6) meeting the read path's deliberate silent-degradation policy (§5),
    a tension the design did not resolve — and that reconciling it requires a design delta, not a
    respond-mode patch. Both halves of the TODO convention satisfied, matching the security-2 shape
    the judge endorsed.
- Severity assessment: real residual on the one safety-critical path, created this round; no behavior
  change (refusing on every transiently-unparseable neighbor would gut rename during live editing —
  the reason it genuinely needs a design cycle). The marker is now durable rather than living only in
  a dispositions doc that will rot.
