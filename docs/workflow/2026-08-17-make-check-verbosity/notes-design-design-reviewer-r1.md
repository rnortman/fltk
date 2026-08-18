# Design review — make check verbosity / hot-cache latency (r1)

Design: `docs/workflow/2026-08-17-make-check-verbosity/design.md` @ e677c38.
No requirements/exploration docs; requirements are the user's verbatim request.

## Verification summary

Checked against source; all of the following are accurate:

- `check-common` at `Makefile:42-54` buffers to `mktemp`, discards on success, no verbosity flag — matches.
- CI runs `run: make check-ci` (`ci.yml:43`); `tests/test_ci_workflow.py` pins that exact line (its `_index_of_run("make check-ci")` and the literal `run: make check-ci` assertion), so keeping ci.yml untouched is correct and necessary for the "CI runs `make check-ci` and nothing else" invariant.
- Root pyo3 loop is `Makefile:165-173` (design says 165-172, off by one line — immaterial); consumer loop + serde step at `Makefile:216-235`; cargo-probe sweep at `Makefile:174-184`; stderr-to-file discipline comment at `Makefile:210-213`; consumer positive-control comment at `Makefile:200-202`; serde comment at `Makefile:204-208`. All quotes match.
- `--config lint` = `--config=clippy` + `--//bzl:lint=true` (`.bazelrc:11-20`); `bzl/lint_flag.bzl` exists. The analysis-cache-discard-on-config-alternation explanation is mechanically correct Bazel behavior.
- `.bazelrc:28-32` comment ("make check buffers each step and prints it on failure") — the quiet path preserves the property it depends on; verbose mode streams, which satisfies it a fortiori.
- Test names quoted from `tests/test_check_step_order.py` all exist, and the quoted docstring/assert fragments ("the positive control is what proves the cquery ran", the exact query string, `test -n "$$labels"`, the serde grep pair) match lines 147-181. No test in that file executes `make`; all are text-level over the Makefile, so the test plan's pattern claim holds.
- `VERBOSE ?= $(if $(filter true,$(CI)),1,0)` semantics: GNU make `filter` is exact-word match, `?=` yields to environment and command line — the edge-case section is correct.
- `deps(set(a b c)) == deps(a) ∪ deps(b) ∪ deps(c)` under one top-level configuration — sound; the grep-based assertions are insensitive to cquery's config-hash suffixes. The union positive control is present in every member graph today (the current per-target loop passing proves it), so the batch cannot newly trip the control.
- git pre-commit hook path (`make check`, no `CI` var) stays quiet — matches the "default locally should be quiet" requirement.

Requirements coverage: (1) "understand why it's slow" — the Context table plus root-cause analysis is the answer, and Part 2 keeps it answerable; (2) optional streaming, default off locally — Part 1; (3) default on in CI — the `CI=true` derivation. All three covered.

## Findings

### design-open-question-1-contradicts-files-touched

- **Where:** "Open questions" item 1 vs. "Files touched", "Test plan", and "Expected outcome: ~140s → ~80s hot".
- **What's wrong:** Open question 1 presents Part 3 as undecided ("Does Part 3 land in this change...?", with a defer branch producing `TODO(batch-pyo3-cqueries)`), but the rest of the document is written as if it is decided: Files touched unconditionally includes "batched cquery guards in `bazel-test` and `bazel-consumer-check`", the Test plan unconditionally lists the two updated guard tests, and the Expected outcome asserts the ~80s number.
- **Why:** Internal consistency — an implementer handed this design has no authoritative answer to whether the guard recipes change; the "if deferred" branch (TODO.md entry, TODO comments in a Makefile with no TODO(slug) convention shown for it) is a second, incompatible file-touch list.
- **Consequence:** Implementation ambiguity on the single largest change in the design; a wrong guess either ships a gate rewrite the user didn't approve or ships a diagnosis with its fix silently dropped and the guard-test updates orphaned.
- **Suggested fix:** Resolve the question in the design (the recommendation to land it is well-argued and I found nothing unsound in the batching itself); if deferred instead, rewrite Files touched and the Test plan to the verbosity-only shape.

### design-consumer-graph-computed-once-claim-inaccurate

- **Where:** Part 3, consumer lane: "Today's recipe computes `deps(//:consumer_serde)` twice ... the new shape computes each graph once."
- **What's wrong:** The new shape still computes `//:consumer_serde`'s graph twice — once inside `deps(set(//:consumer_ast //:consumer_fmt_bin //:consumer_serde))` and once in the standalone `deps(//:consumer_serde)` cquery for the serde assertions. "Each graph once" is false as stated; what's true is "4 invocations become 2".
- **Why:** The invocation count (the actual cost driver per the design's own analysis: ~5-6s of dispatch/invalidation per cquery regardless of overlap) is correctly stated one sentence earlier; the "once" claim is the only inaccurate sentence.
- **Consequence:** Minor — nobody builds anything wrong from it, but the sentence overstates the improvement's mechanism and could mislead a future edit into "deduplicating" further by moving the serde greps onto the union, which the design itself correctly rejects as a weaker assertion.
- **Suggested fix:** Drop or reword the sentence to the invocation count.

### design-timing-measurements-unverified

- **Where:** Context table (~140s total, 53.4s / 22.4s cquery loops, 17-21s no-op test, thrash probe numbers, "9 serial invocations" root / "4" consumer, "258 tests", "82GB output base) and the "~140s → ~80s" / "~76s → ~12s" projections.
- **What's wrong:** Nothing found wrong — but none of it is verifiable from source in this review (the numbers require running the gate; the loop counts require a live `bazel query`). Recording as unverified, not as an error. The 9/4 invocation counts and the shape of the analysis are consistent with the recipes at `Makefile:165-173` and `Makefile:216-235`, and the mechanism claims (per-cquery dispatch cost, analysis-cache discard on `--//bzl:lint` alternation) are correct Bazel behavior independent of the exact figures.
- **Consequence:** Low. Part 3's justification is structural (13 serial invocations → 3), not dependent on the exact seconds; the design's own manual-verification step ("re-run of the timing measurement to confirm the ~80s expectation") is the right hedge and should be kept.

No other findings. The batching soundness argument, the attribution-fallback fail-closed rule, the `set()` space-joining edge case, the CI-default mechanism, and the test-plan/requirements mapping all check out against source.
