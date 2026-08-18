# Judge verdict — design review (round 2, user notes)

Phase: design. Doc: `docs/workflow/2026-08-17-make-check-verbosity/design.md` (revised in place).
Notes: `notes-design-user-r2.md` — 1 finding (user's answer to the design's open question).
Dispositions: `dispositions-design-r2-a1.md`. Round 1 of adjudication on this wave.

## Other findings walk

### user-r2-1 — Fixed
Claim (user, authoritative): reject the draft's conclusion; run `bazel test --config lint
//...` *and also* `bazel build --config lint //...`, one configuration for the whole root
gate, to eliminate the analysis-cache discard. The "you won't know what failed" objection is
a bug to fix, not a justification — failure attribution must be surfaced.
Consequence: without it the gate keeps a permanent re-analysis tax (measured ~20-40s per hot
run, per the design's own thrash probe at `design.md:36-44`).

Evidence in the revised design:
- Open question removed; `design.md:344-347` now reads "None ... answered by the user: merge
  — Part 4."
- New **Part 4** (`design.md:188-245`) specifies exactly the user's two invocations:
  `bazel-test`'s test command becomes `bazel test --config lint //...` (`:198`), and
  `bazel-lint` "stays exactly `bazel build --config lint //...` as its own step" (`:205-209`)
  — the "and also" half, kept rather than collapsed.
- The non-obvious ripple is caught: every `bazel cquery` in the `bazel-test` guard also gains
  `--config lint` (`:198-203`), because a config-less cquery between two lint-config builds
  would reintroduce the very discard being removed. Plain `bazel query` is correctly left
  alone (loading phase, unconfigured). This is the part a lazy "Fixed" would have missed.
- Failure attribution answered on the user's own terms (`:214-221`): Bazel names the failing
  target/action; `--test_output=errors` prints failing test logs. Verified against source —
  `.bazelrc` last line is `test --test_output=errors`, and `check-common`'s quiet path already
  `cat`s the buffer on failure (`Makefile:42-54`), with Part 1's verbose path streaming.
- The claim that lint coverage actually rides the test invocation checks out: `.bazelrc` has
  no `--build_tests_only`, and `build:lint` = `--config=clippy` (aspect + `+clippy_checks` +
  `-Dwarnings`) plus `--//bzl:lint=true`, so the flag-gated Python lint stamps and the clippy
  output groups are produced by `bazel test --config lint //...`. Design states this at
  `:233-235`.
- Ripples applied rather than promised: Files touched gains CLAUDE.md and the Makefile comment
  updates (`:249-254`) — and the CLAUDE.md line that needs it is real (`CLAUDE.md:145`,
  "`make bazel-test` (`bazel test //...` plus the no-pyo3 cquery loop)"), as is the Makefile's
  "Three Bazel lanes" block (`Makefile:36-38`), which currently asserts the split the change
  removes. Edge cases gain the cquery-under-lint-config and lint-failure-in-the-test-step
  entries (`:284-293`). Test plan gains `test_root_gate_runs_one_configuration` (`:328-331`),
  which pins the actual property — every `bazel test`/`bazel cquery` in the recipe carries
  `--config lint`, and `bazel-lint` still runs the build form.
- Costs are stated as deliberate rather than buried (`:223-235`): dev-typed plain
  `bazel test //...` now alternates config against the gate (explicitly the user's trade), and
  the first post-landing gate run re-executes all tests once. Not hidden, not overclaimed;
  the revised expected outcome (~55-65s for Parts 3+4) replaces the Part-3-only ~80s.

Cross-checks for hidden breakage from Part 4: `tests/test_check_step_order.py` mentions
`bazel test //...` only in a module comment (`:26`) and a docstring (`:148`); no assertion
matches the literal command, so "other tests unchanged" holds. `_recipe()` slices to the next
blank line, so the reshaped recipes must stay contiguous — a Part 3 implementation detail, not
a design gap. `tests/test_cargo_retirement.py`'s Makefile scan looks for `cargo`, unaffected.
The consumer lane is correctly excluded (single-configuration workspace; nothing to merge).

Assessment: the disposition does what the user directed, in both halves, and fixes the two
things a superficial edit would have left broken (the cquery configuration, and the docs that
assert the old split). No hand-waving, no scope smuggling. Accept.

## Approved

1 finding: 1 Fixed verified.

---

## Verdict: APPROVED

The sole finding — the user's directive to merge the root gate onto `--config lint` while
keeping the separate `bazel build --config lint //...` step — is implemented in the design as
Part 4, with the load-bearing ripple (cquery configuration), the attribution requirement, the
doc/comment updates, a pinning test, and the accepted costs all stated. Nothing disputed.
