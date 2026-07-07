# Judge verdict — round 2 pre-pass

Phase: pre-pass (slop + scope). Base 9719bab7..HEAD d9ab841. Round 1.
Notes: `notes-prepass-slop.md` (no findings), `notes-prepass-scope.md` (no findings).
Dispositions: `dispositions-prepass.md`.

## Added TODOs walk

One TODO added in the diff range (verified by grepping the full diff for added `TODO` lines).

### TODO(lsp-analysis-watchdog) at fltk/lsp/server.py:142
Q1 (worth doing): yes — a non-terminating parse (catastrophic regex backtracking, unbounded
recursion below the interpreter limit) permanently starves the single-worker analysis executor;
for a long-lived server process this is a real robustness gap, and the engine's docstring
explicitly assigns wall-clock enforcement to the server layer.
Q2 (design/owner input required): yes — the two candidate mechanisms (per-analysis killable
subprocess isolation, or a step/time budget threaded into the generated parser) are both
substantial cross-cutting designs; neither is doable as a contained fix this round.
Provenance: this TODO is not an implementer dodge — it is mandated by the approved design
(design.md §2.3, §5 "Runaway analysis", and the §3 deliverables row for `TODO.md`). Both halves
of the TODO system are present and in sync: `TODO.md` entry `lsp-analysis-watchdog` with concrete
deferral context, and the `TODO(lsp-analysis-watchdog)` comment at the exact starvation point
(`_analyze_blocking`). The "created this iteration, cannot silently defer" rule is satisfied by
visibility: the limitation is design-documented, TODO-tracked, and was reviewed as part of the
approved design rather than smuggled in.
Assessment: passes both rubric questions. TODO acceptable.

## Other findings walk

No findings from either reviewer; there are no dispositions to adjudicate item-by-item.

Cross-checks performed on the "no findings" claims and the dispositions doc:

- Dispositions doc accurately reflects the notes: both files verified to read "No findings."
  The claim "no code change was made, no commit" matches reality — HEAD is d9ab841 (the M2
  implementation commit itself), working tree contains only the three untracked review
  artifacts, and `git log 9719bab7..d9ab841` shows exactly the three implementation commits
  the log declares.
- The scope reviewer's note is substantive, not rubber-stamp: it traces the effective design
  (§3 deliverables, §4.1–4.8, §2.1–2.7) to the three commits, names the three log-declared
  deviations (pygls >=2,<3 vs design's >=1.3,<2 — the version-bump contingency §2.5 explicitly
  anticipated; self-contained grammar in `test_plumbing_error_pos.py`; LOC over target), and
  reports independently re-running pytest (2796 passed, 1 skipped), ruff check, ruff format
  --check, and pyright (0 errors).
- The slop reviewer is a thin diff-only pass by charter; a bare "No findings." is within its
  role.
- Judge spot-check of the diff: exactly one TODO added (walked above); no other deferral
  markers, changelog comments, or obvious not-ready tells surfaced in the added lines scanned.

## Disputed items

None.

## Approved

0 findings to disposition; dispositions doc consistent with both notes files. 1 added TODO
scored acceptable under the rubric.

---

## Verdict: APPROVED
