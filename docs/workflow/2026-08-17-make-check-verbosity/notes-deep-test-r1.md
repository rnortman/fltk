# Deep review — test coverage & test quality (round 1, wave 2)

Base `e677c38552c250330ff1ad7ad145abc065dc24c8` → HEAD `b5167b93dc142e66b2b906ff838d8a409257963a`.
Scope reviewed: `Makefile` (VERBOSE/check-common reshape, batched pyo3 guards, `--config lint` on
the root lane), `tests/test_check_step_order.py` (all new/updated assertions), `CLAUDE.md`,
`TODO.md` (both new slugs — `pyo3-guard-shared-helper`, `consumer-serde-single-traversal` — have
entries at `TODO.md:417` and `TODO.md:440`, so the slug join holds).

Coverage is present for every part of the change at the text level, and several of the new tests
are genuinely well-aimed (the `rdeps(set(...))` control test at
`tests/test_check_step_order.py:172` and the unconditional-`exit 1` attribution test at `:200`
both assert the property they are named for, in both lanes, and would fail on the obvious
regressions). The findings below are where an assertion no longer bites, where the property the
change exists for has no witness at all, and one behavioral gap that is cheap to close.

---

## test-vacuous-union-control-grep

`tests/test_check_step_order.py:168` and `:239` —
`assert "fltk-cst-core:no_python" in recipe, "the positive control is what proves the cquery ran"`.

At the base commit that substring occurred exactly once per recipe: in the per-target cquery's
control grep. After this change each recipe mentions it three times
(`Makefile:223`/`227`/`231` in `bazel-test`, `Makefile:303`/`307`/`311` in the consumer lane), and
the `rdeps` control line alone satisfies the assertion. The docstring's claim ("proves the
*cquery* ran") is therefore no longer what the assertion checks.

**Consequence.** The configured-graph half of the control — `echo "$$graph" | grep -q
'fltk-cst-core:no_python'` at `Makefile:231` / `Makefile:311`, which the design keeps explicitly
(Part 3, item 3) — can be deleted in either lane with the whole suite green. Once it is gone, a
union cquery that prints nothing (or prints a graph that is not the one intended) passes
`! grep -qi pyo3` vacuously, which is the exact failure mode both the recipe comment
(`Makefile:120-124`) and this test exist to prevent.

**Fix.** Scope the assertion to the union cquery's own region in both lanes, e.g.
`union = _from(recipe, "deps(set(")` then
`assert "grep -q 'fltk-cst-core:no_python'" in union` (and that it is applied to `"$$graph"`),
rather than a bare `in recipe`.

## test-missing-invocation-count-witness

`tests/test_check_step_order.py:158-213` (both lanes) — the tests assert that `deps(set(` *exists*
and that the per-target loop survives as the attribution path, but nothing pins how many
configured cqueries the **passing** path runs. Re-adding the old per-target `bazel cquery
deps($$target)` loop to the happy path, alongside the union query, passes every test in the file
(`deps(set(` still present, control still present, attribution block still present).

Related and equally unwitnessed: the decision that the per-target control runs as a
loading-phase `bazel query "rdeps(...)"` rather than a `cquery` — documented at
`Makefile:129-134` as a ~2s vs ~25s choice — has no assertion. `test_root_gate_runs_one_configuration`
would still pass if it became `bazel cquery --config lint "rdeps(...)"`, and
`test_the_positive_control_stays_per_target_in_both_lanes` matches on the expression text only.

**Consequence.** Part 3 is entirely a performance change (measured 76s → ~12s) with
behaviour-preserving semantics; the semantics have tests, the performance property has none. The
~60s regression this change exists to remove can be reintroduced by a later edit with a green
gate, while `CLAUDE.md:14` and the Makefile comments keep claiming the batched shape.

**Fix.** In each lane, split the recipe at the attribution marker (`"grep -qi pyo3; then"`) and
assert `passing_path.count("bazel cquery") == 1`, plus that the `rdeps(` control line is preceded
by `bazel query ` and not `bazel cquery `. Both are one-line derivations over text already sliced
by the existing helpers.

## test-no-executable-coverage-check-common

`tests/test_check_step_order.py:248-340` (`test_verbose_defaults_quiet_locally_and_verbose_in_ci`,
`test_quiet_mode_buffers_and_dumps_on_failure`, `test_verbose_mode_streams`,
`test_every_step_reports_its_wall_time`, `test_a_failing_step_reports_its_wall_time_too`,
`test_the_heartbeat_says_which_step_carries_the_lint_surface`) — Part 1 is a new, non-trivial
shell recipe (a `case`, a `VERBOSE` branch, a nested `if`, two `$$(( ))` arithmetic expansions,
two failure arms) and every test over it is a substring/regex grep on the Makefile text. Nothing
executes it.

**Consequence.** Behaviour is unverified. All of these pass the suite: `[ "$(VERBOSE)" = "1" ]`
comparing against the wrong token so verbose never engages; a step failure not propagating a
non-zero exit out of the loop; the quiet arm printing the buffer before the `FAILED:` line; the
timing echo landing in only one arm (see the next finding); a broken `$$(( ))` printing an empty
duration. The only witness is a human running the gate — which the design's "manual verification
during implementation" acknowledges, so the first regression after this commit is caught by
nobody.

This is cheap to close, and I verified the mechanism works at HEAD: `make -n check-common` runs
the whole loop in well under a second **without invoking Bazel** (sub-makes inherit `-n`), and
prints the real heartbeat/timing/note lines:

```
check-common: running bazel-test [builds the lint surface too: same --config lint configuration]
check-common: bazel-test passed in 0s [builds the lint surface too: ...]
check-common: all steps passed in 0s (bazel-toolchain-guard bazel-test ...)
```

and `make -n check-common CHECK_STEPS=nope [VERBOSE=1]` exercises **both** failure arms, printing
`FAILED: nope after 0s (gate ran 0s)` and failing the make invocation.

**Fix.** Add a py_test (new `fltk_py_tests` dict entry in `tests/BUILD.bazel`, `Makefile` already
crosses the package boundary via `exports_files`) that runs `make -n check-common` with
`CHECK_STEPS` overridden — once to a trivially-passing target and once to a nonexistent one —
under `VERBOSE=0` and `VERBOSE=1`, asserting: a start line and a `passed in <n>s` line per step in
*both* modes; the sub-make's own output present under `VERBOSE=1` and absent from a passing quiet
run; non-zero exit plus a `FAILED: <step> after …s (gate ran …s)` line in both modes; and the
buffer dumped after the `FAILED:` line in quiet mode. If a host `make` dependency in the sandbox
is unacceptable, the host-tool-free equivalent is to extract the recipe text, substitute
`$$`→`$` / `$(MAKE)`→a stub script / `$(VERBOSE)`→the mode, and run it under `bash` — which also
catches the shell-syntax class that no current test covers.

## test-brittle-positional-timing-assert

`tests/test_check_step_order.py:308` —
`assert recipe.index(passed) > recipe.rindex("exit 1")`, justified as "the per-step timing must be
reported in both modes, i.e. after both failure arms".

It does not enforce that. The last `exit 1` in the recipe sits inside the quiet arm
(`Makefile:82`); moving the `passed in` echo *into* the quiet arm — after `rm -f "$$tmpfile"`,
before the closing `fi` — keeps it after that `rindex` and keeps the test green, while verbose
runs would print no per-step timing at all. Conversely, any later reshape that adds an `exit 1`
below the echo (a trailing guard, a trap) fails the test for no behavioural reason.

**Consequence.** The named regression (timing available in one mode only) is not caught, and
benign edits produce a false failure whose message points at slicing rather than at a property.

**Fix.** Anchor on the branch structure instead of on character offsets — e.g.
`re.search(r'fi; \\\n\s*echo "check-common: \$\$step passed in', recipe)`, which states "the echo
follows the `fi` that closes the VERBOSE branch" — or replace it with the behavioural assertion
from the previous finding (both modes print a `passed in` line for every step).

## test-brittle-config-flag-position

`tests/test_check_step_order.py:357-361` — the sweep matches `\bbazel ([a-z]+)\b` and requires the
remainder to `startswith(" --config lint")`, i.e. the flag must sit immediately after the verb and
the verb must be separated by exactly one space.

**Consequence.** Brittleness rather than a hole: a legitimate reordering
(`bazel cquery --output=label --config lint "…"`) or `bazel  test` reports a spurious
"runs a second configuration" failure. The derived-sweep design is the right call; only the
adjacency requirement is over-tight.

**Fix.** Match the flag anywhere in the invocation's own line/segment (slice to the next `; \` or
newline and search for `--config lint` in it) instead of requiring it in the first position.

## Non-findings, checked

- `test_root_gate_runs_one_configuration` correctly exempts loading-phase `query` and does catch
  a `--config`-less `bazel test`/`bazel cquery` added to `bazel-test`; the echo strings in that
  recipe spell the lane `bazel-test` (hyphen), so they do not match the sweep and no false
  positive arises.
- The consumer lane deliberately keeps its cqueries config-less (there is no `build:lint` block in
  `tests/bazel_consumer`, so `--config lint` there would hard-fail on the first run). Untested,
  but a violation is loud rather than silent — not worth an assertion.
- `_recipe`'s `"\n\n"` terminator still bounds each reshaped recipe correctly (no blank line was
  introduced inside `check-common`, `bazel-test` or `bazel-consumer-check`).
- The serde assertions are correctly scoped to `_from(recipe, "deps(//:consumer_serde)")`; the
  attribution loop uses `deps($$target)`, so that marker still resolves to the standalone serde
  cquery and the "not the union" claim in the test holds.
- `test_ci_workflow.py` is untouched, consistent with `ci.yml` being untouched.
