# Deep citizen review — round 1, wave 1

Base `e677c38552c250330ff1ad7ad145abc065dc24c8` → HEAD `054d9f54153aab8d8f80f63f0b215764ea615e92`.
Reviewed: `Makefile`, `tests/test_check_step_order.py`, `CLAUDE.md`.

---

## quality-duplicated-union-cquery-guard

**Where:** `Makefile:187-205` (root lane) and `Makefile:255-271` (consumer lane).

**What's wrong:** the two pyo3 guards were near-duplicates before this change (one `for` loop each,
~7 lines). The change doubles each one to ~16 lines — union cquery + positive control +
`if grep -qi pyo3` + per-target attribution loop + unconditional `exit 1` — and copies the whole new
shape verbatim into both places. The copies are already diverging on exactly the axis this change
introduced: the root lane's cqueries carry `--config lint` (`Makefile:192`, `Makefile:199`), the
consumer lane's do not (`Makefile:258`, `Makefile:265`) — correct today (separate workspace, no lint
config there) but invisible as a *reason* at either site, since the two blocks no longer sit next to
each other in a form a reader can diff by eye. The union-vs-attribution invariant that
`test_the_pyo3_guard_attributes_a_union_failure_and_still_fails` pins is now asserted by regexing
the same structure out of two independent recipes.

**Consequence:** the next edit to this guard (a fourth consumer target, a third workspace, a change
to what "pyo3 present" greps for, the `--config lint` decision being revisited) has to be made
twice, in shell that is hard to test and only exercised on a red gate. The attribution arm in
particular is dead code on every green run: a divergence introduced there — say the consumer copy
losing its trailing `exit 1` — surfaces only the day the guard should have failed, which is the one
day it must not be wrong. Duplicated never-executed failure paths are the classic place this rots.

**Direction:** extract one parameterized shell helper, e.g. `bzl/no_pyo3_guard.sh <label>… ` taking
the target list on argv and the extra Bazel flags via an env var (`BAZEL_CONFIG_FLAGS`), run from the
workspace directory each lane already `cd`s into. Both recipes become one line plus their own
target derivation, the guard's logic gets one home, and the `--config lint` asymmetry becomes a
visible argument at the call site instead of a silent textual difference. The existing text-level
tests then assert over one implementation.

---

## quality-per-target-positive-control-dropped

**Where:** `Makefile:194-195` (root), `Makefile:260-261` (consumer). Was: one control per target
inside the loop.

**What's wrong:** the positive control (`grep -q 'fltk-cst-core:no_python'`) now runs once, over the
union. The design calls this out as knowingly given up, but the reasoning ("a control, not a stated
property") understates what it protected. The assertion it guards is *negative* — "pyo3 is absent"
— and a negative assertion over a per-target graph passes vacuously whenever that graph is not what
you think it is. Previously, a target that stopped reaching the runtime crates at all (retargeted
`//tests:rust_gate_lib`, a `rust_binary` reduced to a stub, a `no_python` alias pointed somewhere
harmless) failed its own control. Now any single member of the union satisfying the control masks
all eight others, and the comment at `Makefile:176-180` asserts the union identity for the *negative*
half only — which is sound — while the control silently weakened from nine facts to one.

**Consequence:** the guard's stated job is being "the only witness" (`Makefile:157-158`,
`Makefile:235-236`) to a failure mode that builds and tests green. A vacuous per-target pass is
precisely that failure mode wearing the guard's own uniform, and it will not be noticed by anything
else in the gate. The cost of the regression shows up years later as "the guard was green the whole
time".

**Direction:** the per-target control is recoverable in *one* invocation, so this is not a
speed/strength trade at all: `bazel cquery --config lint "rdeps(set($labels), //crates/fltk-cst-core:no_python)"`
emits every node on a path from a root to that target, so asserting each label in `$labels` appears
in the output restores all nine per-target facts for one cquery. Keep the union `deps(...)` cquery
for the pyo3 assertion and add this second one (2 invocations, not 9). If that proves awkward, at
minimum assert the union output size / member count so a collapsed graph cannot pass.

---

## efficiency-consumer-serde-graph-traversed-twice

**Where:** `Makefile:257-258` (union includes `//:consumer_serde`) and `Makefile:274` (`deps(//:consumer_serde)` again).

**What's wrong:** the design accepts the double traversal on the grounds that invocation count is
what costs, and that the serde assertions must not ride the union. Both premises are right, but the
conclusion isn't forced: dropping `//:consumer_serde` from the union and moving the pyo3
assertion + positive control onto the *second* cquery's graph (which is already
`deps(//:consumer_serde)`) gives the same two invocations, the same three targets covered for pyo3,
strictly stronger per-target attribution for the serde target, no redundant traversal, and a
smaller union to grep and hold in a shell variable.

**Consequence:** as written, the largest consumer graph is analyzed and printed twice per gate run,
on the lane the design measured at ~22s of cquery time. It is not the dominant cost after this
change, but it is pure waste that will grow with the consumer fixture, and it makes the union's
member list disagree with the set the second cquery is about — a reader has to reconstruct why
`consumer_serde` appears in both.

**Direction:** union over `//:consumer_ast //:consumer_fmt_bin` for the pyo3 assertion; put
`//:consumer_serde`'s pyo3 assertion and control alongside its serde assertions in the existing
second cquery block.

---

## quality-lint-step-timing-now-misattributes

**Where:** `Makefile:41-46`, `Makefile:186` (`bazel test --config lint //...`), `Makefile:223-227`,
`CHECK_STEPS` at `Makefile:47`.

**What's wrong:** Part 4 moves the entire lint surface (clippy aspect, `//:ruff_check`,
`//:ruff_format_check`, `//:pyright`) into the invocation the gate reports as the step named
`bazel-test`, and leaves `bazel-lint` in `CHECK_STEPS` as an acknowledged cache-hit no-op. The new
per-step heartbeat (Part 2, whose entire stated purpose is trustworthy time attribution — design
§Part 2) will therefore print something like `bazel-test passed in 45s` / `bazel-lint passed in 2s`
forever. Both numbers are true and the pair is actively misleading: linting is not 2s, and the step
whose name says "test" is now the test *and* lint lane. Same for failure attribution: a ruff or
clippy diagnostic now surfaces under `FAILED: bazel-test`.

**Consequence:** the diagnosis surface this change exists to build starts out lying about where the
gate's time goes, which is exactly the ambiguity that motivated the change. The next person
optimizing the gate reads the heartbeat, concludes lint is free, and looks in the wrong place. The
step name is also the thing developers type (`make bazel-test`) and the thing CLAUDE.md documents,
so the naming drift propagates into docs and habits.

**Direction:** make the names match reality. Either rename the merged lane (`bazel-verify` /
`bazel-test-and-lint`, keeping `bazel-lint` as a standalone non-gate target for `make bazel-lint`
ergonomics), or drop `bazel-lint` from `CHECK_STEPS` and say in the heartbeat/comment that the lint
surface is inside the merged lane. If both steps stay, have the `bazel-lint` heartbeat line say it
is a same-configuration cache-hit confirmation so the 2s is not read as lint's cost.

---

## observability-failing-step-reports-no-duration

**Where:** `Makefile:57-69`.

**What's wrong:** `step_start` is captured before the branch, but the elapsed-time echo
(`Makefile:69`) is only reached on success. Both failure paths (`Makefile:58`, `Makefile:62-65`)
`exit 1` without printing the step's wall time, and the gate total at `Makefile:71` is skipped too.

**Consequence:** the case where timing matters most is the one that has it: "the gate failed and it
took forever" — a timeout in CI, a flaky test that hung for 20 minutes, a step that died three
seconds in versus one that died after the whole suite. The CI log shows `FAILED: bazel-test` with no
duration and no gate total, so reconstructing the timeline means reading Bazel timestamps. One echo
in the failure arms closes it.

**Direction:** print `check-common: $$step FAILED after $$(( $$(date +%s) - step_start ))s` in both
failure paths (it can replace the current `FAILED: $$step` line as long as the `FAILED:` token stays
on it — `test_verbose_mode_streams` and `test_quiet_mode_buffers_and_dumps_on_failure` both grep for
that token, and the design promises scripts can too).

---

## test-brittle-slicing-raises-instead-of-asserting

**Where:** `tests/test_check_step_order.py:170` (`recipe.index("if echo")`), `:239`
(`recipe.index("else")`), `:256` (`recipe.index("\n\t    fi;")`), `:243`
(`">" not in verbose.replace("2>", "")`).

**What's wrong:** four of the new assertions locate their region with bare `str.index` on incidental
text — the literal word `else`, the literal string `if echo`, and a `fi;` preceded by exactly four
spaces of recipe indentation. A benign reshape (`elif`, `if [ -n "$$hit" ]`, a re-indent, moving the
buffering into a shell function) makes these raise `ValueError: substring not found` rather than
fail an assertion with the message the test author wrote. `:243`'s `">" not in verbose.replace("2>", "")`
is likewise structure-by-coincidence: it happens to hold only because the verbose arm contains no
`>` at all today, and it would pass just as happily on an arm that had been deleted.

**Consequence:** these are guard tests over a gate — their whole value is that a *future* edit gets
a clear "you broke property X". A `ValueError` in a test named
`test_every_step_reports_its_wall_time` sends the reader to the test's slicing code instead of to
the property, which is how guard tests get weakened ("the test is brittle, relax it") rather than
repaired. The indentation coupling at `:256` is the worst of them: recipe whitespace is not a
property anybody intends to preserve.

**Direction:** slice with a helper that asserts before indexing (`_after(recipe, marker)` raising an
assertion with the recipe on a miss), and key the regions on things the recipe means rather than how
it is spelled — e.g. find the branch by the `$(VERBOSE)` test and the quiet arm by `mktemp`, and
assert the timing echo appears *after both* `exit 1` sites rather than after a literal `fi;`. For
`:243`, assert positively that the verbose arm's `$(MAKE) $$step` is followed by `||` and nothing
between it and the `||` (already covered by the regex on `:240`) and drop the fragile
negative-on-`>` heuristic, or scope it to "no `>"$$tmpfile"` in the verbose arm".

---

## test-config-guard-regex-misses-build-and-run

**Where:** `tests/test_check_step_order.py:270`.

**What's wrong:** the sweep is `re.finditer(r"bazel (test|cquery) (?!--config lint)", recipe)` — limited to those two verbs. The property the
docstring states is "every *configured* invocation carries `--config lint`", but `bazel build`,
`bazel run` and `bazel aquery` in the `bazel-test` recipe would all configure targets and all slip
past. Adding a `bazel build` line to that recipe — a plausible future edit, e.g. pre-building a
fixture — silently reintroduces the analysis-cache discard this whole part exists to remove, with
the guard green.

**Consequence:** the guard covers the two spellings that exist today rather than the property, so it
protects the change that just landed and not the invariant. That is the failure mode the repo's own
comments call out repeatedly (derive the set, don't list it).

**Direction:** invert it — match `bazel <verb>` for every verb, treat loading-phase-only verbs
(`query`) as the explicit allowlist, and require `--config lint` on everything else.
