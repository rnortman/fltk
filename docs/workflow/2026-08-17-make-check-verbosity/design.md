# Design: `make check` verbosity, per-step timing, and hot-cache latency

Base commit: `e677c38552c250330ff1ad7ad145abc065dc24c8`.

## Context and root cause

Two problems, one gate:

1. **Opacity.** `check-common` (`Makefile:42-54`) runs every step with output buffered to a
   `mktemp` file and discarded on success. A passing run prints nothing until the final
   success line; a slow run is indistinguishable from a hung one, and there is no flag to
   change that. CI (`ci.yml:43`, `run: make check-ci`) gets the same silence.

2. **Hot-cache latency.** With a fully warm cache and a clean tree, `make check` takes
   ~140s. Measured per step at the base commit (hot 82GB output base, zero source changes,
   all 258 tests cached):

   | Step / sub-step                                             | Time    |
   |-------------------------------------------------------------|---------|
   | `bazel-toolchain-guard`                                      | 0.01s   |
   | `bazel test //...` (0 of 258 tests executed)                 | ~17-21s |
   | `bazel query` (pyo3-free target set)                         | 2.0s    |
   | **cquery loop, root: 9 serial `bazel cquery` invocations**   | **53.4s** |
   | `bazel query` (cargo_file_probe sweep, 2 invocations)        | 9.1s    |
   | `bazel build --config lint //...`                            | 12-28s  |
   | consumer `bazel test //...` (own workspace, own server)      | 21.5s   |
   | **cquery loop, consumer: 4 serial invocations**              | **22.4s** |
   | `check-bazel-locks`                                          | 0.01s   |

   The dominant cost — **~76s, over half the gate** — is the 13 serial `bazel cquery`
   invocations in the pyo3/serde guards (`Makefile:165-172` root loop, `Makefile:216-235`
   consumer). Each cquery pays command dispatch, Skyframe invalidation checking, and
   printing a full transitive closure (~5-6s apiece even hot), and they run one at a time.

   The second cost is inherent per-invocation overhead: a `bazel test //...` that executes
   zero tests still costs ~17-21s after another configuration has run, and ~6s
   back-to-back. Two contributors, confirmed by a thrash probe (test → lint → test, all
   hot: 17.5s / 27.9s / 17.4s):

   - **Analysis-cache discard on config alternation.** `--config lint` sets
     `--//bzl:lint=true` (a build setting, `bzl/lint_flag.bzl`) and adds the clippy aspect
     (`.bazelrc:11-20`). Changed build options discard Bazel's in-memory analysis cache, so
     every gate run pays re-analysis at least twice (test config → lint config, and the
     next run pays it again going back).
   - **Skyframe invalidation/diffing** over a large graph (profile of a warm no-op run:
     ~6.5s wall, ~2s each in `handleDiffs` / `fsvc.getDirtyKeys`).

   The consumer lane is a separate Bazel workspace with its own server and output base, so
   its `bazel test` pays the same ~21s floor independently.

   `//:requirements.test` (the PyPI resolve) is cached on a hot run and is *not* a
   contributor here; it matters only cold or after a manifest edit.

## Proposed approach

Four parts, all landing in this change. Part 1 is the requested feature; Part 2 makes
slowness permanently visible; Parts 3 and 4 are the semantics-preserving fixes for the
two measured costs. Part 3 is in scope deliberately: it is a Makefile-recipe reshape with
its guard tests updated in the same commit, and shipping the diagnosis without the
one-file fix for its dominant finding would be perverse. Part 4 runs the whole root gate
under one configuration (`--config lint`) so the intra-gate analysis-cache discard
disappears; it is a user directive (notes-design-user-r2.md).

### Part 1: `VERBOSE` mode — default off locally, default on in CI

All in `Makefile`. `ci.yml` is untouched (its tests in `tests/test_ci_workflow.py` pin
`run: make check-ci`; the CI default rides the `CI=true` environment variable GitHub
Actions always sets).

Near the top of the Makefile:

```make
# Stream each check step's output as it runs (VERBOSE=1) or buffer it and print only on
# failure (VERBOSE=0, the local default).  CI defaults to verbose: GitHub Actions sets
# CI=true, and a CI log that shows nothing until the end is a CI log nobody can read a
# hang or a slow step out of.  Explicit VERBOSE=0/1 on the command line or in the
# environment overrides the default in both directions.
VERBOSE ?= $(if $(filter true,$(CI)),1,0)
```

`check-common` grows a branch on `$(VERBOSE)`. The quiet path keeps its current
buffering behavior (buffer, dump on failure, delete on success) and both paths gain the
heartbeat/timing lines:

```make
check-common:
	@steps="$(CHECK_STEPS)"; gate_start=$$(date +%s); \
	for step in $$steps; do \
	    echo "check-common: running $$step"; \
	    step_start=$$(date +%s); \
	    if [ "$(VERBOSE)" = "1" ]; then \
	        $(MAKE) $$step || { echo "FAILED: $$step"; exit 1; }; \
	    else \
	        tmpfile=$$(mktemp); \
	        if ! $(MAKE) $$step >"$$tmpfile" 2>&1; then \
	            echo "FAILED: $$step"; \
	            cat "$$tmpfile"; \
	            rm -f "$$tmpfile"; \
	            exit 1; \
	        fi; \
	        rm -f "$$tmpfile"; \
	    fi; \
	    echo "check-common: $$step passed in $$(( $$(date +%s) - step_start ))s"; \
	done; \
	echo "check-common: all steps passed in $$(( $$(date +%s) - gate_start ))s ($(CHECK_STEPS))"
```

Design points:

- **Quiet mode stays the local default and stays quiet about step *content*.** What it
  gains is a heartbeat: one line when a step starts and one when it finishes, with its
  wall time. Ten short lines total. This is deliberately in both modes — it is what turns
  "make check is slow" from a mystery into "the cquery guard took 53s" without re-running
  anything.
- **Verbose mode streams.** No tmpfile, no redirect; sub-make output (including Bazel's
  progress UI) goes straight to the terminal/CI log. The `FAILED: $$step` trailer is kept
  so the two modes end a failing run with the same marker.
- **CI default via `$(CI)`, not a ci.yml edit.** GitHub Actions sets `CI=true`
  unconditionally; `$(filter true,$(CI))` matches exactly that value, so `CI=false`,
  `CI=`, or unset all mean quiet. `VERBOSE ?=` means an environment or command-line
  `VERBOSE` wins over the derived default in both directions (`make check VERBOSE=0` in
  CI, `VERBOSE=1 make check` locally). Keeping ci.yml untouched also keeps
  `test_ci_workflow.py` untouched and preserves the "CI runs `make check-ci` and nothing
  else" invariant its docstring states.

### Part 2: the timing lines are the diagnosis surface

The heartbeat/timing lines above are Part 1's mechanism doing double duty: every future
run, local or CI, quiet or verbose, reports where its time went at step granularity. The
sub-step numbers in the Context table answer today's "why is it slow"; the per-step lines
keep the next regression from needing another manual instrumentation session.

### Part 3: batch the cquery guards (the measured 76s → ~12s)

The guards' *properties* are untouched; only the invocation count changes. Soundness rests
on an identity: `deps(set(a b c))` is exactly `deps(a) ∪ deps(b) ∪ deps(c)`, so "pyo3
absent from the union" is equivalent to "pyo3 absent from every member's graph".

**Root lane (`bazel-test` recipe).** Replace the 9-iteration loop with:

1. One `bazel query` deriving `$labels` (unchanged), still failing on an empty set.
2. One `bazel cquery "deps(set($labels))"` (labels space-joined into the `set()`).
3. Positive control on the union: it must contain `fltk-cst-core:no_python` — same
   purpose as today (a silently-empty cquery must not pass the negative assertion
   vacuously), asserted once instead of nine times.
4. Negative assertion on the union: `! grep -qi pyo3`.
5. **Attribution fallback:** when pyo3 *is* found, re-run today's per-target loop purely
   to name the offending target(s) in the failure message, then exit 1 unconditionally —
   even if the per-target pass inexplicably finds nothing (the union said otherwise;
   inconsistency is itself a failure). The slow path runs only on a red gate, where 50
   extra seconds is irrelevant.

What is knowingly given up: the current loop incidentally proves *each* target's graph
contains `fltk-cst-core:no_python`. That per-target fact is a control, not a stated
property — the consumer recipe's comment (`Makefile:200-202`, "Positive control first: a
silently failing cquery would otherwise pass the negative assertion vacuously") and
`test_the_pyo3_guard_survives_in_the_bazel_test_recipe` ("the positive control is what
proves the cquery ran") both frame it that way — and the union-level control serves that
purpose identically.

**Consumer lane (`bazel-consumer-check` recipe).** 4 cquery invocations become 2:

1. One union cquery `deps(set(//:consumer_ast //:consumer_fmt_bin //:consumer_serde))`
   carrying the positive control and the pyo3 assertion, with the same attribution
   fallback on failure.
2. One `deps(//:consumer_serde)` cquery for the two serde assertions
   (`consumer_crates.*:serde` present, `fltk_crates.*:serde` absent). These stay on
   consumer_serde's own graph rather than the union: "the serde target links the consumer
   hub's serde" asserted on a union would be satisfiable by any member, which is a weaker
   statement than the one the comment at `Makefile:204-208` promises.

The saving is in invocation count, not graph deduplication: `//:consumer_serde`'s graph
is still traversed twice (inside the union and standalone), but the per-invocation
dispatch/invalidation cost — the actual driver per the Context analysis — drops from 4
payments to 2.

The stderr-to-file discipline (`Makefile:210-213`) is kept for every cquery: progress
noise stays out of a passing quiet run, failure diagnostics survive into the log.

**Considered and rejected:** merging the cargo-probe sweep's two `bazel query`
invocations (`Makefile:174-184`, 9.1s combined) into one `--output label_kind` query with
shell-side derivation of both package sets. ~5s saved for a meaningfully more delicate
recipe; not worth it.

**Expected outcome of Part 3 alone:** ~140s → ~80s hot. What remains after it is
Bazel-invocation invalidation and re-analysis cost, which Part 4 attacks.

### Part 4: one configuration for the whole root gate (`--config lint` everywhere)

Per the user's decision (notes-design-user-r2.md): run `bazel test --config lint //...`
*and* `bazel build --config lint //...`. Everything in the root workspace's gate runs under
the lint configuration, so the test → lint → test alternation that discards Bazel's in-memory
analysis cache on every gate run (the second cost in the Context analysis) is gone —
every root-lane invocation sees the same configuration checksum.

Concretely, in `Makefile`:

- **`bazel-test`**: `bazel test //...` becomes `bazel test --config lint //...`, and every
  `bazel cquery` in its guard (the Part 3 batched form) gains `--config lint` too — a
  cquery configures targets, so a config-less cquery between two lint-config builds would
  reintroduce exactly the discard this part removes. Verified at the base commit: `bazel
  cquery --config lint "deps(//tests:rust_gate_lib)"` succeeds (cquery inherits the
  `build:lint` block from `.bazelrc`) and the graph is pyo3-free. The plain `bazel query`
  invocations are untouched — query is loading-phase only, no configuration.
- **`bazel-lint`**: unchanged — `bazel build --config lint //...` stays as its own step.
  After `bazel test --config lint //...` it is a same-configuration near-no-op (cache-hit
  confirmation, seconds not tens of seconds), but it stays because the user asked for
  both, it preserves a named lint lane in the step list and its heartbeat line, and it is
  the backstop if the `test` command ever skips an output group the `build` form covers.
- **Consumer lane**: untouched by Part 4. It is a separate workspace with a single
  configuration already (no `--config lint` there, so no alternation to remove); its cost
  is the separate-server floor, not config thrash.

**Failure attribution** is handled, per the user's framing ("if something fails, we must
know what failed"): Bazel names every
failing target and action, `--test_output=errors` (`.bazelrc:32`) prints failing tests'
logs, clippy and the Python lint stamps print their diagnostics with the failing action,
and both `check-common` modes put that output in front of the developer (verbose streams
it; quiet dumps the buffer on failure). A clippy or ruff failure may now surface during
the `bazel-test` step rather than waiting for `bazel-lint`; the output names the lint
target either way, and earlier is better.

**Accepted consequences**, stated so they're deliberate:

- The gate's configuration now differs from the plain `bazel test //...` developers type,
  so dev-run ↔ gate alternation thrashes the analysis cache instead of the gate thrashing
  itself. The gate runs far more often than not (precommit hook), and a developer who
  cares can type `bazel test --config lint //...` themselves. This trade is the user's
  explicit call.
- The first gate run after landing re-executes all tests once under the new
  configuration (different config checksum = no cached results); subsequent runs cache as
  before.
- `bazel test --config lint //...` builds non-test targets in the pattern (no
  `--build_tests_only` in `.bazelrc`), so the flag-gated Python lint targets and the
  clippy output groups ride the test invocation. That is the point.

Comment/document updates ride along: the Makefile's "Three Bazel lanes" comment block
(`Makefile:36-38`) and the `bazel-test`/cargo-lane comments (`Makefile:78-87`), plus
CLAUDE.md's Build System description of `make bazel-test`, must describe the
single-configuration shape.

**Expected outcome of Parts 3+4 together:** ~140s → roughly 55-65s hot. The remaining
floor is per-invocation Skyframe invalidation on two servers plus the consumer workspace's
independent ~21s; no further structural lever short of merging workspaces, which nobody
has asked for.

## Files touched

- `Makefile` — `VERBOSE` default, `check-common` branch + timing, batched cquery guards
  in `bazel-test` and `bazel-consumer-check`, `--config lint` on the root lane's test and
  cquery invocations, comment updates for the single-configuration shape.
- `tests/test_check_step_order.py` — new assertions for Parts 1 and 4, updated guard
  assertions for Part 3.
- `CLAUDE.md` — the Build System section's one-line description of `make bazel-test`
  gains the `--config lint` shape.
- `TODO.md` — untouched.

No Starlark, no `.bazelrc`, no `ci.yml`, no generated code, no consumer-facing surface.

## Edge cases and failure modes

- **`CI` set to something other than `true`** (`CI=false`, `CI=1`, empty): quiet.
  `$(filter true,$(CI))` is an exact-word match, not a truthiness test.
- **Developer with `CI` exported locally** (some shells/tools do this): they get verbose;
  `VERBOSE=0` overrides. Documented in the Makefile comment.
- **Failure in verbose mode:** output already streamed; the `FAILED: $$step` trailer still
  prints, so scripts grepping for it work in both modes.
- **Interrupt (ctrl-C) in quiet mode leaks the tmpfile:** pre-existing behavior,
  unchanged; not worth a trap in a recipe this size.
- **`$labels` interpolation into `set(...)`:** the query output is newline-separated;
  the recipe must space-join it (unquoted `echo $$labels` or `tr '\n' ' '`) before
  splicing into the cquery expression. An empty set is already a failure before the
  cquery runs (`test -n "$$labels"`).
- **Union cquery output size:** the 9 graphs overlap heavily (shared crate universe and
  toolchains), so the union is roughly the size of the largest single graph today; the
  shell-variable capture pattern is unchanged.
- **Attribution fallback disagreement:** union shows pyo3, per-target loop doesn't (e.g.
  something rebuilt between the two invocations). Exit 1 regardless, with a message saying
  the union check failed; never let the fallback convert a red result to green.
- **Sub-make `Entering directory` noise in verbose mode:** harmless and mildly useful;
  no `--no-print-directory` added.
- **`date +%s` timing:** 1-second resolution, POSIX-portable; sufficient at step
  granularity.
- **cquery under `--config lint`:** verified working at the base commit (cquery inherits
  `build:lint` from `.bazelrc`; the clippy-aspect flags in the expansion are accepted).
  Should a future rules_rust or Bazel change make cquery reject part of the config
  expansion, the fallback is passing the block's flags to cquery directly — but that is a
  then-problem; the recipe uses `--config lint` so the three spellings can't drift.
- **`bazel-lint` after `bazel test --config lint //...`:** same configuration, so it
  cannot discard the analysis cache; expected to be a cache-hit pass in seconds. If a
  lint diagnostic fails the test step first, the gate still stops with the diagnostic in
  the failure output — attribution comes from Bazel's named failing target, not from
  which make step tripped.

## Test plan

All in `tests/test_check_step_order.py`, following its existing pattern (text-level
assertions over the Makefile via `_recipe()`; no test in this repo executes `make`, and
this change does not introduce a host-`make` dependency):

New tests (Part 1):

- `test_verbose_defaults_quiet_locally_and_verbose_in_ci` — the `VERBOSE` assignment uses
  `?=` (so environment/command line override) and derives from `$(filter true,$(CI))`
  (so only exactly `CI=true` flips the default).
- `test_quiet_mode_buffers_and_dumps_on_failure` — the `check-common` recipe's quiet
  branch retains `mktemp`, the `>"$$tmpfile" 2>&1` redirect, `FAILED: $$step`, and
  `cat "$$tmpfile"` — the "failure evidence reaches the developer/CI log" property
  `.bazelrc:28-32` depends on.
- `test_verbose_mode_streams` — the recipe branches on `$(VERBOSE)` and the verbose arm
  invokes `$(MAKE) $$step` with no output redirection.
- `test_every_step_reports_its_wall_time` — the per-step timing echo is present and not
  inside only one branch (both modes report timings).

Updated tests (Part 3):

- `test_the_pyo3_guard_survives_in_the_bazel_test_recipe` — keeps asserting: the derived
  label query string, `test -n "$$labels"` (empty derivation fails), the
  `fltk-cst-core:no_python` positive control, and `grep -qi pyo3`. Gains: the recipe
  contains `deps(set(` (the batch), and the attribution fallback loop exists and ends in
  a hard failure.
- `test_the_pyo3_guard_survives_in_the_consumer_recipe` — same reshaping; additionally
  keeps asserting the serde pair (`consumer_crates.*:serde`, `fltk_crates.*:serde`) and
  that those assertions run against `deps(//:consumer_serde)` specifically, not the union.

New test (Part 4):

- `test_root_gate_runs_one_configuration` — every `bazel test` and `bazel cquery` in the
  `bazel-test` recipe carries `--config lint`, and the `bazel-lint` recipe still runs
  `bazel build --config lint //...` — the property that no root-lane invocation alternates
  configuration mid-gate.

Unchanged and expected to keep passing as-is: every other test in
`test_check_step_order.py` (aliases, step order, lock-diff shape, PHONY sweep) and all of
`test_ci_workflow.py` (ci.yml is untouched).

Manual verification during implementation (not committed as tests): a hot `make check`
(run twice — the first pays the one-time config-switch re-run, the second is the number
that matters), a hot `make check VERBOSE=1`, and a deliberately-broken target — including
a deliberate clippy warning, to see how a lint failure reports through the `bazel-test`
step — under both modes; plus a re-run of the timing measurement to confirm the ~55-65s
expectation.

## Open questions

None. The draft's one open question (accept the post-Part-3 floor, or merge the test and
lint lanes onto one configuration) was answered by the user: merge — Part 4.
