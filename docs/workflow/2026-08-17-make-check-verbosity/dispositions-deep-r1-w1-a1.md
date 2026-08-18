# Dispositions — deep review round 1, wave 1

Notes: `notes-deep-citizen-r1.md`. All seven findings fact-checked against `Makefile`,
`tests/test_check_step_order.py`, `CLAUDE.md`, the base commit's Makefile
(`git show e677c38:Makefile`), and live `bazel query` / `bazel cquery` / `make check` runs.

quality-duplicated-union-cquery-guard:
- Disposition: TODO(pyo3-guard-shared-helper)
- Action: `TODO(pyo3-guard-shared-helper)` comments at `Makefile:209-211` (above `bazel-test`'s
  guard) and `Makefile:281` (above `bazel-consumer-check`'s), plus an entry in `TODO.md`
  naming the divergence risk, the `--config lint` asymmetry, and what "done" is.
- Severity assessment: the guard's attribution arm runs only on a red gate, so a divergence
  introduced in one copy (a dropped `exit 1`, a grep that stopped matching) would surface on the
  one day the guard must not be wrong. Green runs never exercise it.
- Rubric: Q1 yes — the duplication is real, it grew this round, and the never-executed failure
  paths are the classic place shell rots. Q2 yes — the helper has to be a tracked file both
  workspaces can reach, and `tests/bazel_consumer/` is deliberately a standalone downstream
  module that `bazel_dep`s on `@fltk`; whether its gate recipe may reach up into the parent
  repo for a script (or whether the helper should ship as something a consumer could use) is a
  call about that module's independence, not a mechanical extraction. Deciding it inside a
  respond pass would settle a question about the repo's consumer-facing boundary by accident.

quality-per-target-positive-control-dropped:
- Disposition: Fixed
- Action: the per-target control is back in both lanes, as one extra invocation rather than one
  per target. `Makefile:223-228`: `bazel query "rdeps(set($labels), //crates/fltk-cst-core:no_python)"`,
  then a loop requiring every derived label to appear as a whole line of that output.
  `Makefile:303-308`: the same over `//:consumer_ast //:consumer_fmt_bin //:consumer_serde`
  against `@fltk//crates/fltk-cst-core:no_python`. The union-level control on the `deps` cquery
  output stays — the two now carry different facts, and the comments at `Makefile:194-207` and
  `Makefile:274-279` say which is which. Test:
  `test_the_positive_control_stays_per_target_in_both_lanes` in
  `tests/test_check_step_order.py:172-197`. `CLAUDE.md:145` records the shape.
- Severity assessment: confirmed against the base commit — the old loop failed the gate when any
  single target's graph lacked `fltk-cst-core:no_python`, so the change really did collapse nine
  facts (three in the consumer lane) into one. The assertion those facts guard is negative, so a
  target that stopped reaching the runtime crates would have gone on passing "no pyo3" while
  proving nothing, with no other gate noticing. This round's own code created that weakening,
  which is why it is not deferrable.
- Note on cost: the reviewer's `cquery` spelling was measured at ~25s in the root lane (reverse-dep
  inversion over the whole configured graph) and would have doubled the gate. The shipped form is
  a loading-phase `bazel query`, measured at 1.9s (root) and 2.3s (consumer), which is where the
  fact actually lives: "this target still reaches the runtime crates" is structural, and the
  configured half of the control is the union check that stayed. Hot `make check` after the fix:
  54s, inside the design's 55-65s expectation.

efficiency-consumer-serde-graph-traversed-twice:
- Disposition: TODO(consumer-serde-single-traversal)
- Action: `TODO(consumer-serde-single-traversal)` comment at `Makefile:291-292`, above the
  `deps(//:consumer_serde)` block, plus a `TODO.md` entry stating the proposed shape and why it
  is deferred.
- Severity assessment: pure waste, no correctness effect — the lane's largest graph is analyzed
  and printed twice per run, and it grows with the consumer fixture. Not the dominant cost after
  this change (the consumer lane runs 16s hot, most of it the separate server's floor).
- Rubric: Q1 yes — the reviewer's shape is strictly better on every axis and costs nothing.
  Q2 yes — the design spells out this union's membership as all three targets and explicitly
  weighed and accepted the double traversal ("The saving is in invocation count, not graph
  deduplication"). Changing which targets ride the union is a revision of a frozen decision, not
  a patch to an implementation slip, and the design and its deltas are the wrong thing for a
  respond pass to edit around.

quality-lint-step-timing-now-misattributes:
- Disposition: Fixed
- Action: `Makefile:55-83` — `check-common` now annotates the two steps whose names stopped
  partitioning the work, on both the start line and the timing line: `bazel-test` gets
  `[builds the lint surface too: same --config lint configuration]` and `bazel-lint` gets
  `[same-configuration cache-hit confirmation; lint's cost is in bazel-test]`. The notes print in
  quiet mode too, which is where the timing surface is actually read. `CLAUDE.md:142` says the
  same thing in prose. Test: `test_the_heartbeat_says_which_step_carries_the_lint_surface` in
  `tests/test_check_step_order.py:328-341`. Verified live: `check-common: bazel-lint passed in 3s
  [same-configuration cache-hit confirmation; lint's cost is in bazel-test]`.
- Severity assessment: real and self-inflicted — the change exists to make gate time legible, and
  unannotated it would have shipped a timing surface reading "linting takes two seconds", sending
  the next person optimizing the gate at the wrong lane. Renaming the steps (the reviewer's other
  option) was not taken: `bazel-test` is what developers type, what `CLAUDE.md` documents and what
  `_REQUIRED_STEPS` pins, and the design keeps both steps deliberately; annotation buys the same
  legibility without the churn.

observability-failing-step-reports-no-duration:
- Disposition: Fixed
- Action: `Makefile:69` (verbose arm) and `Makefile:73` (quiet arm) now print
  `FAILED: $step after Ns (gate ran Ns)`. The `FAILED: $$step` token is intact in both, so
  anything grepping for it — including the two existing tests — still works. Test:
  `test_a_failing_step_reports_its_wall_time_too` in `tests/test_check_step_order.py:314-325`.
  Verified live in both modes with `make check-common CHECK_STEPS=no-such-step`.
- Severity assessment: the case timing matters most — a CI timeout, a step that hung — was the one
  case with no timing at all, and the gate total never printed on a failure either.

test-brittle-slicing-raises-instead-of-asserting:
- Disposition: Fixed
- Action: `tests/test_check_step_order.py:147-156` adds `_from(recipe, marker)`, which asserts
  with the recipe in the message before slicing; `:270-278` add `_quiet_arm` / `_verbose_arm`,
  which locate the two branches by what they do (`tmpfile=$$(mktemp)`, the `$(VERBOSE)` test)
  rather than by the literal word `else`. The `fi;`-with-four-spaces slice is gone —
  `test_every_step_reports_its_wall_time` now asserts the timing echo appears after the last
  `exit 1`, which is the property (reported in both modes) rather than a spelling. The
  `">" not in verbose.replace("2>", "")` heuristic is now `'>"$$tmpfile"' not in verbose`. The
  attribution and serde slices go through `_from` too.
- Severity assessment: guard tests whose failure mode is `ValueError` in the test body point the
  reader at the slicing instead of the property, which is how a guard gets relaxed rather than
  repaired. Recipe indentation was never a property anyone meant to pin.

test-config-guard-regex-misses-build-and-run:
- Disposition: Fixed
- Action: `tests/test_check_step_order.py:343-362` — the sweep now matches every `bazel <verb>`
  and exempts an explicit `_LOADING_PHASE_VERBS = {"query"}` allowlist, requiring `--config lint`
  on everything else. A `bazel build` or `bazel run` added to the recipe later is caught.
- Severity assessment: as written the guard covered the two spellings that existed rather than the
  invariant, so a plausible future edit would have silently reintroduced the analysis-cache
  discard that Part 4 exists to remove, with the test green.
