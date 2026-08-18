# Implementation log — `make check` verbosity, per-step timing, hot-cache latency

## Increment 1 — all four design parts (Parts 1-4)

The design's whole surface is three files and is naturally indivisible: Part 3 reshapes the
same recipes Part 4 configures, and Parts 1/2 share one `check-common` recipe. Well under the
500-line target; splitting would leave incoherent halves.

- `Makefile:24-32`: `VERBOSE ?= $(if $(filter true,$(CI)),1,0)` with the comment covering the
  exact-word `CI=true` match and the both-directions override.
- `Makefile:52-72`: `check-common` branches on `$(VERBOSE)` — verbose arm runs
  `$(MAKE) $$step` unredirected, quiet arm keeps mktemp/buffer/dump-on-failure. Heartbeat
  (`running <step>`), per-step wall time and whole-gate wall time echo in both modes.
- `Makefile:174-192`: batched pyo3 guard in `bazel-test` — one `bazel cquery --config lint
  "deps(set($(echo $labels)))"`, union positive control, union `grep -qi pyo3`, and the
  per-target attribution loop behind `if`, with `exit 1` after the loop unconditionally.
- `Makefile:196`: `bazel test --config lint //...`; every cquery in the recipe carries
  `--config lint`; the two plain `bazel query` calls left alone (loading phase, no config).
- `Makefile:243-258`: consumer lane's 4 cqueries become 2 — one union over
  `//:consumer_ast //:consumer_fmt_bin //:consumer_serde` (positive control + pyo3 +
  attribution fallback), one `deps(//:consumer_serde)` keeping the serde pair on its own graph.
  No `--config lint` there, per design (separate workspace, single configuration already).
- `Makefile`: comment updates for the single-configuration shape — the CHECK_STEPS block, the
  cargo-retirement note, the `bazel-test` guard rationale, `bazel-lint`'s now-near-no-op role,
  the consumer guard's union/serde split.
- `tests/test_check_step_order.py`: new `test_verbose_defaults_quiet_locally_and_verbose_in_ci`,
  `test_quiet_mode_buffers_and_dumps_on_failure`, `test_verbose_mode_streams`,
  `test_every_step_reports_its_wall_time`, `test_root_gate_runs_one_configuration`; updated
  `test_the_pyo3_guard_survives_in_the_bazel_test_recipe` (gains `deps(set(`) and
  `test_the_pyo3_guard_survives_in_the_consumer_recipe` (gains `deps(set(`, and the serde pair
  is now asserted against the `deps(//:consumer_serde)` slice of the recipe rather than the
  whole recipe).
- Deviation (addition): also added
  `test_the_pyo3_guard_attributes_a_union_failure_and_still_fails`, covering both lanes'
  attribution fallback — the design's "never let the fallback convert a red result to green"
  edge case had no test named for it in the test plan and it is the one new property that can
  silently invert the guard.
- Deviation (addition): `CLAUDE.md` also gained a sentence documenting `VERBOSE` and the
  timing lines in the `make check` paragraph; the design's Files-touched list named only the
  `make bazel-test` one-liner, but the user-facing flag would otherwise be undocumented.
- `CLAUDE.md:142,145`: `make check` paragraph gains the VERBOSE/timing sentence; the
  `make bazel-test` bullet now says `bazel test --config lint //...`, describes the union
  cquery guard, and states the dev-run/gate configuration trade.

Verification (not committed as tests): `bazel test //tests:test_check_step_order
//tests:test_ci_workflow //tests:test_cargo_retirement` green; full `make check VERBOSE=1`
green (105s, the one-time re-execution under the new configuration); hot `make check` green at
**30s** (was ~140s — better than the design's 55-65s expectation: `bazel-test` 14s,
`bazel-lint` 2s, `bazel-consumer-check` 14s). Failure paths exercised: the root guard's
attribution branch, driven by forcing its union grep to match, exits 1 with the union message
and no per-target line (the designed disagreement-is-still-failure behavior); both consumer
guard blocks pass `bash -n`. A real ruff diagnostic during development surfaced through the
`bazel-test` step and named its target, which is the Part 4 attribution case.

## Respond round 1 (deep review, wave 1)

Dispositions: `dispositions-deep-r1-w1-a1.md`. Five findings Fixed, two TODO'd.

- `Makefile:223-228`, `Makefile:303-308`: the positive control is per target again in both
  lanes — one `bazel query "rdeps(set(<targets>), //crates/fltk-cst-core:no_python)"` (the
  consumer lane's names `@fltk//crates/...`) plus a loop requiring each derived target to be a
  whole line of that output. The union-level control on the `deps` cquery stays; the two carry
  different facts and the comments at `Makefile:194-207` / `Makefile:274-279` say which.
- Deviation from the reviewer's proposed fix: it asked for a `cquery`. Measured at ~25s in the
  root lane (reverse-dep inversion over the configured graph), which would have doubled the
  gate; the loading-phase `bazel query` is 1.9s/2.3s and is where a "does this target still
  reach the runtime crates" fact actually lives. `test_root_gate_runs_one_configuration` already
  exempts `query`.
- `Makefile:60-66,79,81`: `check-common` derives a per-step note and prints it on both the start
  and the timing line — `bazel-test` says it builds the lint surface, `bazel-lint` says it is a
  same-configuration cache-hit confirmation. Without them the timing surface reads "lint is 3s".
- `Makefile:69,73`: both failure arms now print `FAILED: $step after Ns (gate ran Ns)`; the
  `FAILED: $$step` token is unchanged so existing greps hold.
- `tests/test_check_step_order.py:147-156,270-278`: `_from` / `_quiet_arm` / `_verbose_arm` —
  region slicing asserts before indexing and keys on what the recipe does, not on `else`,
  `if echo`, or a four-space `fi;`.
- `tests/test_check_step_order.py:172-197,314-325,328-341`: new
  `test_the_positive_control_stays_per_target_in_both_lanes`,
  `test_a_failing_step_reports_its_wall_time_too`,
  `test_the_heartbeat_says_which_step_carries_the_lint_surface`.
- `tests/test_check_step_order.py:343-362`: the one-configuration sweep matches every
  `bazel <verb>` against a `_LOADING_PHASE_VERBS` allowlist instead of listing `test|cquery`.
- `CLAUDE.md:142,145`: the heartbeat notes, the failure-line durations, and the per-target
  control's shape and why it is a `query`.
- TODO(pyo3-guard-shared-helper) at `Makefile:209-211` and `Makefile:281`, with a `TODO.md`
  entry: the two guards are near-duplicate shell whose attribution arms only run on a red gate.
- TODO(consumer-serde-single-traversal) at `Makefile:291-292`, with a `TODO.md` entry:
  `//:consumer_serde`'s graph is walked twice per consumer-lane run.
- Verification: `bazel test //tests:test_check_step_order //tests:test_ci_workflow
  //tests:test_cargo_retirement` green; `make check VERBOSE=1` green; hot `make check` green at
  **54s** (bazel-test 35s, bazel-lint 3s, bazel-consumer-check 16s) — above the 30s the first
  increment measured, and inside the design's 55-65s expectation. Both failure arms exercised
  live via `make check-common CHECK_STEPS=no-such-step` in each mode.

## Respond round 1 (deep review, wave 2)

Dispositions: `dispositions-deep-r1-w2-a1.md`. Eight findings Fixed, one TODO'd.

- `Makefile:204-214`, `Makefile:292-294`: the positive-control comment no longer claims "the
  configured half of the control is the union check above". It states that `query` unions every
  `select()` branch, so no per-target *configured* fact is asserted, and names the residual: a
  target reaching the runtime crates only through an untaken branch passes its own control while
  contributing nothing to the union.
- `Makefile:222-228`: the `--config lint` block states the assertion-surface narrowing as an
  accepted consequence — the root lane's pyo3 check holds at `--//bzl:lint=true`, not at the
  default configuration a consumer builds. No default-config cquery added: that is the mid-gate
  config switch the lane's uniform configuration exists to remove.
- `TODO.md:440-446`: `TODO(pyo3-guard-shared-helper)` gains the restoration — a helper taking the
  Bazel flags as an argument can run the union once per configuration, paid at the end of the lane.
- `tests/test_check_step_order.py:172-185`: `_assert_the_union_carries_its_own_control`, used by
  both lanes' guard tests at `:168` and `:280`, requires the control to be applied to `"$$graph"`
  inside the union region instead of the substring appearing anywhere in the recipe.
- `tests/test_check_step_order.py:230-256`: `_passing_path` plus
  `test_a_green_gate_run_pays_one_configured_cquery_per_graph` — one configured cquery on the root
  lane's passing path, two on the consumer's, and the control held to a loading-phase `bazel query`.
- `tests/test_check_step_order.py:352-357`: the timing echo's position is asserted structurally
  (it follows the `fi` closing the VERBOSE branch and is absent from the buffering arm) rather than
  by comparing character offsets against the last `exit 1`.
- `tests/test_check_step_order.py:397-431`: `_bazel_invocations` slices each `bazel <verb>` to the
  end of its own command and the one-configuration sweep now runs over every `CHECK_STEPS` recipe
  except `bazel-consumer-check`, looking for `--config lint` anywhere in the invocation.
- Surprise: widening that sweep needed a `(?<![\w.-])` lookbehind — `bazel-toolchain-guard`'s echo
  strings contain "the root MODULE.bazel pin", which the old `\b` pattern read as an invocation of
  `bazel pin`. The first run of the widened sweep failed on exactly that.
- TODO(check-common-executable-coverage) at `tests/test_check_step_order.py:298-300`, with a
  `TODO.md:447-469` entry: every assertion over the `check-common` recipe is a grep on Makefile
  text, so the shell it describes is never executed.
- `dispositions-deep-r1-w1-a1.md`: trailing `</content>` copy-paste artifact deleted.
- `CLAUDE.md:145`: the unconfigured-control residual and the lint-configuration assertion surface.
- Verification: `bazel test //tests:test_check_step_order //tests:test_ci_workflow
  //tests:test_cargo_retirement` green; full `make check` green at 112s (bazel-test 71s after the
  edits invalidated its cache, bazel-lint 2s, bazel-consumer-check 39s).
