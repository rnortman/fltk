# Dispositions — deep review round 1, wave 2

Notes: `notes-deep-tracer-r1.md`, `notes-deep-test-r1.md`. Nine findings: eight Fixed, one TODO.

correctness-pyo3-guard-asserts-lint-config-only:
- Disposition: Fixed
- Action: the narrowing is now stated as a deliberate accepted consequence rather than left
  implicit — `Makefile:222-228` (the `--config lint` comment block above `bazel-test` now says the
  pyo3 assertion holds at `--//bzl:lint=true`, not at the default configuration a consumer builds,
  and that a pyo3 edge behind a `select()` on the lint setting would be invisible to it),
  `CLAUDE.md:145` (same statement in the `make bazel-test` bullet), and `TODO.md:440-446`
  (the restoration under `TODO(pyo3-guard-shared-helper)`: a helper taking the extra Bazel flags as
  an argument can run the union once per configuration for one more cquery, paid at the end of the
  lane instead of mid-lane). No second cquery added: a default-configuration cquery inside the lane
  is exactly the mid-gate config switch the lane's uniform configuration exists to remove, and
  buying the fact back is what the TODO is for.
- Severity assessment: the guard's assertion surface really did move from the default
  configuration to `lint=true`, and nothing said so. Exploiting it needs a `select()` on the lint
  setting over a Rust dep, which does not exist today; the cost of the gap being undocumented is
  that the next person to add such a select has no way to know the guard stopped covering them.

correctness-positive-control-select-blind:
- Disposition: Fixed
- Action: the overclaim is gone and the residual is stated. `Makefile:204-214`: the comment no
  longer says "the configured half of the control is the union check above"; it says `query` unions
  every `select()` branch, and that no per-target *configured* fact is asserted anywhere — a target
  whose edge to the runtime crates sits in an untaken branch passes the unconfigured control while
  contributing nothing to the union, whose control the other members satisfy. `Makefile:292-294`
  carries the same note for the consumer lane, and `CLAUDE.md:145` for the reader who never opens
  the Makefile. The reviewer's other option (a per-target configured fact) is the ~25s/~53s cquery
  cost the batching removed, so the honest documentation is the fix.
- Severity assessment: silent vacuity for one derived target, and only under a
  select-shaped retargeting; the harm of the previous text was that it claimed the configured fact
  was covered, which would have stopped a future reader from noticing the corner at all.

test-one-config-sweep-scoped-to-two-recipes:
- Disposition: Fixed
- Action: `tests/test_check_step_order.py:411-431` — `test_root_gate_runs_one_configuration` now
  sweeps every recipe named in `CHECK_STEPS` (skipping `bazel-consumer-check`, the separate
  workspace with no `build:lint` block) instead of `bazel-test` plus one literal. The recipes are
  derived from the same list the Makefile advertises as the extension point, so a new step running
  a bare `bazel build` in the root workspace fails this test.
- Severity assessment: a performance-regression channel through the one documented extension point,
  with the test named for the invariant staying green; the gate would quietly re-grow the
  tens-of-seconds re-analysis tax.

test-vacuous-union-control-grep:
- Disposition: Fixed
- Action: `tests/test_check_step_order.py:168,172-185,280` — the bare
  `"fltk-cst-core:no_python" in recipe` is replaced in both lanes by
  `_assert_the_union_carries_its_own_control`, which slices from `deps(set(` and requires
  `"$$graph" | grep -q 'fltk-cst-core:no_python'` — the union cquery's own output, not a mention
  anywhere in the recipe. Deleting the configured control now reds the suite in either lane.
- Severity assessment: the assertion had gone vacuous exactly where it mattered — with the
  configured control deleted, a union cquery that printed nothing would pass `! grep -qi pyo3` and
  the guard would witness nothing at all.

test-missing-invocation-count-witness:
- Disposition: Fixed
- Action: `tests/test_check_step_order.py:230-256` — new `_passing_path` (the recipe minus the
  attribution block, which runs only on a red gate) and
  `test_a_green_gate_run_pays_one_configured_cquery_per_graph`, asserting one configured cquery on
  the root lane's passing path and two on the consumer's (union + the serde graph), plus that the
  positive control is spelled `bazel query "rdeps(set(` rather than a cquery. Slicing the
  attribution block out rather than truncating at the marker keeps the count order-independent.
- Severity assessment: Part 3 is a pure performance change whose performance property had no
  witness; the measured ~60s could be reinstated by a later edit with the whole suite green while
  the Makefile comments and CLAUDE.md kept describing the batched shape.

test-no-executable-coverage-check-common:
- Disposition: TODO(check-common-executable-coverage)
- Action: `TODO.md:447-469` entry plus the `TODO(check-common-executable-coverage)` comment at
  `tests/test_check_step_order.py:298-300`, above the `check-common` tests. Both record the
  reviewer's verified mechanism (`make -n check-common CHECK_STEPS=<target>` runs the loop in under
  a second without invoking Bazel, and a nonexistent step exercises both failure arms), the
  behavioral assertions a real test must make, and the two candidate harnesses.
- Severity assessment: the `check-common` shell's behavior is unverified — a VERBOSE comparison
  against the wrong token, a failure that fails to propagate, or an empty duration would all leave
  the suite green. It degrades the gate's diagnostics rather than its verdicts (the failure
  propagation path was exercised live during the previous round in both modes), so the exposure is
  a future regression going unnoticed rather than a live defect.
- Rubric: Q1 yes — a non-trivial shell recipe with no executable coverage is worth closing, and the
  mechanism is known to work. Q2 yes — the design of this change decided the other way in as many
  words ("no test in this repo executes `make`, and this change does not introduce a host-`make`
  dependency"), and both routes past that need a call I cannot make here: shelling out to `make`
  adds a dependency on a host tool the build graph does not pin, which this repo documents
  `genhtml` as its sole exception to, and the text-substitution alternative trades that for a
  harness that can drift from what `make` actually expands. Which one the repo wants is a
  hermeticity decision for the owner, not a mechanical edit.

test-brittle-positional-timing-assert:
- Disposition: Fixed
- Action: `tests/test_check_step_order.py:352-357` — the `recipe.index(passed) > recipe.rindex("exit
  1")` offset comparison is replaced by two structural assertions: the timing echo follows the `fi`
  that closes the VERBOSE branch (`re.search(r'fi; \\\n\s*echo "check-common: \$\$step passed in')`),
  and the echo does not appear inside the buffering arm before that branch closes. Moving the echo
  into the quiet arm now fails; adding an `exit 1` below it no longer does.
- Severity assessment: both directions were live — the named regression (timing in one mode only)
  passed the old assertion, and a benign later reshape would have failed it with a message pointing
  at slicing rather than at the property.

test-brittle-config-flag-position:
- Disposition: Fixed
- Action: `tests/test_check_step_order.py:397-410` — new `_bazel_invocations` slices each
  `bazel <verb>` to the end of its own command (`; \` or newline) and the sweep looks for
  `--config lint` anywhere in that slice, so flag order no longer matters. The same helper needed a
  lookbehind (`(?<![\w.-])`) once the sweep covered every step's recipe: `bazel-toolchain-guard`'s
  own echo strings contain prose like "the root MODULE.bazel pin", which the old `\b` pattern read
  as an invocation of `bazel pin` — the first run of the widened sweep failed on exactly that.
- Severity assessment: brittleness, not a hole — a legitimate flag reordering would have reported a
  spurious "runs a second configuration"; the lookbehind was load-bearing for the widened sweep and
  would otherwise have made finding 3's fix unshippable.

quality-stray-content-tag-in-dispositions:
- Disposition: Fixed
- Action: the trailing `</content>` line is deleted from
  `docs/workflow/2026-08-17-make-check-verbosity/dispositions-deep-r1-w1-a1.md`.
- Severity assessment: cosmetic; committed copy-paste noise in a workflow record.
