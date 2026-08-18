# Judge verdict — deep review

Phase: deep. Base `e677c38552c250330ff1ad7ad145abc065dc24c8`..HEAD `c51f6f96d3a92a39ece3f4744e83be939eb394d1`.
Reviewed HEAD `b5167b93dc142e66b2b906ff838d8a409257963a`. Round 1.
Notes: 3 reviewer files (citizen w1; tracer, test w2) — 16 findings.
Dispositions: `dispositions-deep-r1-w1-a1.md` (7), `dispositions-deep-r1-w2-a1.md` (9).
Design (frozen): `design.md`.

## Added TODOs walk

### quality-duplicated-union-cquery-guard — TODO(pyo3-guard-shared-helper) at `Makefile:215-217`, `Makefile:296`, `Makefile:228`; `TODO.md:417-445`
Q1 (worth doing): yes — the two guard blocks grew from ~7 to ~16 lines each this round
(`Makefile:231-255` vs `Makefile:315-337`), and each one's attribution arm executes only on a red
gate, so a divergence there surfaces the one day it must not.
Q2 (design/owner input required): yes, on balance. The mechanical part (parameterize on target
list, control label, flags, message prefix) is doable now, but the helper has to be a tracked file
the `tests/bazel_consumer` lane reaches, and that module exists precisely to be an arms-length
downstream consumer of `@fltk` — whether its gate recipe may reach up into the parent repo for a
script, or whether the helper ships as consumer-facing surface, is a repo-boundary call. The
TODO.md entry also folds in the default-configuration union cquery (item below), which is design
work in its own right, and pins "done".
Assessment: TODO acceptable; slug join holds (comment + `TODO.md` heading). Borderline on Q2, but
the boundary question is real and the entry states the shape and the done condition concretely.

### efficiency-consumer-serde-graph-traversed-twice — TODO(consumer-serde-single-traversal) at `Makefile:306-307`; `TODO.md:473-484`
Q1 (worth doing): weak yes — the reviewer's shape (union over `consumer_ast`/`consumer_fmt_bin`,
`consumer_serde`'s pyo3 assertion moved onto the `deps(//:consumer_serde)` block it already needs)
is strictly better on traversal count at the same invocation count. Pure waste, no correctness
effect, in a lane whose cost is dominated by the separate server's ~21s floor.
Q2 (design/owner input required): yes — `design.md:161-177` names all three targets as the union's
membership and weighs and accepts the double traversal in as many words ("The saving is in
invocation count, not graph deduplication"). Changing which target rides which cquery revises a
frozen decision rather than repairing an implementation slip, and the change also redistributes
which assertion lives in which block — a legibility trade the design owner should make.
Assessment: TODO acceptable. Low-value either way; the entry surfaces it rather than burying it.

### test-no-executable-coverage-check-common — TODO(check-common-executable-coverage) at `tests/test_check_step_order.py:298-300`; `TODO.md:447-471`
Q1 (worth doing): yes — `check-common` (`Makefile:59-83`) is now a `case`, a `VERBOSE` branch, a
nested `if`, four `$$(( ))` expansions and two failure arms, and every assertion over it
(`tests/test_check_step_order.py:301-388`) is a grep on Makefile text. The reviewer demonstrated a
working, sub-second, Bazel-free mechanism (`make -n check-common CHECK_STEPS=<target>`).
Q2 (design/owner input required): yes. The frozen design decided this explicitly — "no test in
this repo executes `make`, and this change does not introduce a host-`make` dependency"
(`design.md:297-299`) — and it went through two design review rounds on that basis. Both routes
past it need an owner call: a `py_test` shelling out to host `make` adds an unpinned host tool to
the test graph, which this repo documents `genhtml` as its *sole* exception to (CLAUDE.md, coverage
section); the text-substitution alternative buys hermeticity at the cost of a harness that can
drift from what `make` actually expands. Extracting the recipe into a tracked script so an
`sh_test` could drive it hermetically is a third option and a Makefile redesign — out of respond
scope.
Assessment: TODO acceptable. This iteration did enlarge the untested recipe, but it is not
*silently* deferred: comment + `TODO.md` entry naming the four concrete regressions that would go
unnoticed, the verified mechanism, both candidate harnesses, and a behavioral "done".

Three TODOs, none of them a `scope-*` deferral of designed functionality: no phase-scope signal.

## Other findings walk

### quality-per-target-positive-control-dropped — Fixed
Claim: batching collapsed nine per-target "this target reaches `fltk-cst-core:no_python`" facts
into one union fact; consequence is that a target that stopped reaching the runtime crates keeps
passing a negative assertion vacuously, with no other gate noticing.
Evidence: `Makefile:236-241` — `bazel query "rdeps(set($labels), //crates/fltk-cst-core:no_python)"`
followed by a loop requiring `grep -qxF "$$target"` per derived label; `Makefile:318-323` the same
over the consumer's three targets against `@fltk//crates/fltk-cst-core:no_python`. Semantics
verified: `rdeps(u, x)` evaluates within the transitive closure of `u`, so a label appearing in the
output is exactly "this label reaches x". The union-level control on `"$$graph"` stays
(`Makefile:244`, `:326`). Tests: `test_the_positive_control_stays_per_target_in_both_lanes`
(`:186`), `test_a_green_gate_run_pays_one_configured_cquery_per_graph` (`:238`) pinning the control
as a loading-phase `query`.
Assessment: nine facts restored for one extra invocation, not nine. Accept.

### quality-lint-step-timing-now-misattributes — Fixed
Claim: with the lint surface inside the `bazel-test` invocation, the new heartbeat reports
"bazel-lint passed in 2s" forever — the diagnosis surface this change exists to build lies about
where gate time goes.
Evidence: `Makefile:62-66` `case` assigning per-step notes, echoed on both the start line
(`:67`) and the timing line (`:81`); `CLAUDE.md:142` states the same in prose; test
`test_the_heartbeat_says_which_step_carries_the_lint_surface` (`:376`) requires a note for both
steps and `$$note` on both lines. Renaming was declined with a reason (`bazel-test` is what
developers type, what CLAUDE.md documents and what `_REQUIRED_STEPS` pins) — and annotation is
the reviewer's own third option ("have the `bazel-lint` heartbeat line say it is a
same-configuration cache-hit confirmation").
Assessment: addresses the consequence at the named lines. Accept.

### observability-failing-step-reports-no-duration — Fixed
Claim: both failure arms `exit 1` without printing step duration or gate total; the case where
timing matters most is the one without it.
Evidence: `Makefile:70` (verbose) and `Makefile:74` (quiet) both print
`FAILED: $$step after Ns (gate ran Ns)`; the `FAILED: $$step` token grepped by the two existing
tests is intact. Test `test_a_failing_step_reports_its_wall_time_too` (`:362`) checks both arms for
`step_start` and `gate_start` on the failure line.
Assessment: closed in both arms. Accept.

### test-brittle-slicing-raises-instead-of-asserting — Fixed
Claim: four assertions locate their region with bare `str.index` on incidental text (`else`,
`if echo`, `\n\t    fi;`) so a benign reshape raises `ValueError` instead of failing the named
property.
Evidence: `_from` (`:147-155`) asserts with the recipe before slicing; `_quiet_arm` /
`_verbose_arm` (`:314-322`) locate the arms by `mktemp` and the `$(VERBOSE)` test; the
four-space `fi;` slice is gone, replaced by a structural regex (`:352`); the
`">" not in verbose.replace("2>", "")` heuristic is now `'>"$$tmpfile"' not in verbose` (`:337`).
Residual noted, not disputed: that negative and the `"mktemp" not in verbose` companion are
near-tautological given how `_verbose_arm` slices — but the property (no redirect between
`$(MAKE) $$step` and its `||`) is positively asserted by the regex at `:334`, which is what the
reviewer's own direction asked for.
Assessment: Accept.

### test-config-guard-regex-misses-build-and-run — Fixed
Claim: the sweep matched only `bazel (test|cquery)`, so a later `bazel build`/`run`/`aquery` in the
recipe would reintroduce the analysis-cache discard with the guard green.
Evidence: `_LOADING_PHASE_VERBS = {"query"}` (`:394`), `_bazel_invocations` (`:397-404`) matching
every `bazel <verb>`, sweep at `:422-427` requiring `--config lint` on everything outside the
allowlist. Verified the widened sweep does not false-positive on recipe prose: the lookbehind
`(?<![\w.-])` excludes "MODULE.bazel pin" in `bazel-toolchain-guard`'s echo strings, and
`//tests:test_check_step_order` passes at HEAD.
Assessment: property, not spellings. Accept.

### correctness-pyo3-guard-asserts-lint-config-only — Fixed (documented narrowing)
Claim: `--config lint` moved the root-lane pyo3 assertion off the default configuration a consumer
builds; a pyo3 edge behind a `select()` on the lint setting ships invisibly.
Evidence: `Makefile:223-228` now states the narrowing as an accepted consequence and points at
`TODO(pyo3-guard-shared-helper)`; `CLAUDE.md:145` says the same for the reader who never opens the
Makefile; `TODO.md:440-445` records the cheap restoration (one more union cquery at the default
configuration, expressible once the helper takes flags as an argument). I checked the alternative
the reviewer floated — a second default-config cquery "running last in the step" does *not* avoid
the discard, because `bazel-lint`'s `bazel build --config lint //...` still follows it in
`CHECK_STEPS`; restoring the fact without re-thrashing requires moving it outside the lane, which
is a design change. Uniform configuration is itself a user directive (`design.md:188-194`).
Assessment: the reviewer's own first suggested fix, taken in full, plus the TODO route. Accept.

### correctness-positive-control-select-blind — Fixed (overclaim removed)
Claim: the comment asserted "the configured half of the control is the union check above", which is
one fact over nine targets; `bazel query` unions every `select()` branch, so a target reaching the
runtime crates only through an untaken branch passes its own control vacuously.
Evidence: `Makefile:204-213` — the overclaim is gone and the residual is stated explicitly ("no
per-target CONFIGURED fact is asserted anywhere"), with the cost of buying it back (a cquery per
target = the 53s the batching removed); `Makefile:292-294` carries the same note in the consumer
lane; `CLAUDE.md:145` repeats it. Documenting was one of the two options the finding itself
offered, and the other (per-target configured facts) is the cost this whole part removed.
Assessment: Accept.

### test-one-config-sweep-scoped-to-two-recipes — Fixed
Claim: the sweep covered `bazel-test`'s recipe plus one literal on `bazel-lint`, so a new
`CHECK_STEPS` step — the Makefile's advertised extension point (`Makefile:29`) — running a bare
`bazel build` reintroduces the discard with the test green.
Evidence: `tests/test_check_step_order.py:418-428` iterates `check_steps()`, exempting only
`bazel-consumer-check` (separate workspace, no `build:lint` block to name — which the test's own
docstring states). Verified green at HEAD, including over the two recipes the widening newly
pulled in.
Assessment: derived from the same list the Makefile advertises. Accept.

### test-vacuous-union-control-grep — Fixed
Claim: `"fltk-cst-core:no_python" in recipe` is now satisfied by the `rdeps` control line alone, so
the configured control on `"$$graph"` could be deleted in either lane with the suite green.
Evidence: `_assert_the_union_carries_its_own_control` (`:172-183`) requires
`"$$graph" | grep -q 'fltk-cst-core:no_python'`, called from both lanes' tests (`:168`, `:280`).
Noted, not disputed: `_from(recipe, "deps(set(")` matches inside `rdeps(set(` first, so the slice
starts one line early — the assertion is still about the `$graph` grep specifically (it names the
variable), so deleting `Makefile:244` or `:326` now reds the suite, which is the property.
Assessment: Accept.

### test-missing-invocation-count-witness — Fixed
Claim: nothing pinned how many configured cqueries the *passing* path runs, so re-adding the
per-target `cquery deps($target)` loop to the happy path — the ~60s this change removed — passes
every test.
Evidence: `_passing_path` (`:230-235`) excises the attribution block by slicing at
`grep -qi pyo3; then` and rejoining at its closing `fi; \`;
`test_a_green_gate_run_pays_one_configured_cquery_per_graph` (`:238-254`) asserts one configured
cquery on the root passing path and two on the consumer's, plus that the control stays
`bazel query "rdeps(set(`. Counts verified against `Makefile:242` (root: one) and
`Makefile:324`/`:340` (consumer: two), with the attribution cqueries at `:249` and `:331` excised.
Assessment: the performance property now has a witness. Accept.

### test-brittle-positional-timing-assert — Fixed
Claim: `recipe.index(passed) > recipe.rindex("exit 1")` does not enforce "both modes report
timing" (moving the echo into the quiet arm keeps it green) and false-fails on a later `exit 1`.
Evidence: `:352-358` — a structural regex requiring the echo to follow the `fi` that closes the
`VERBOSE` branch, plus `passed not in quiet[: quiet.rindex("fi; \\")]` so the echo cannot hide in
the buffering arm. Checked against `Makefile:80-81`: the outer `fi; \` is the last one, so the
slice does bound the branch as claimed.
Assessment: both directions closed. Accept.

### test-brittle-config-flag-position — Fixed
Claim: requiring `--config lint` immediately after the verb false-fails a legitimate flag
reordering.
Evidence: `_bazel_invocations` (`:397-404`) slices each invocation to its own `; \` or newline and
the sweep searches anywhere in that slice (`:425`).
Assessment: Accept.

### quality-stray-content-tag-in-dispositions — Fixed
Evidence: `git diff b5167b9..c51f6f9` shows the trailing `</content>` line removed from
`dispositions-deep-r1-w1-a1.md`.
Assessment: Accept.

## Respond-commit scan

`b5167b93..c51f6f96` — two commits.

- `b941ac1` ("test(check): scope the gate's guard assertions and state the config residuals"): the
  w2 fixes — `tests/test_check_step_order.py` (union-control helper, `_passing_path` + count test,
  structural timing asserts, `_bazel_invocations`, CHECK_STEPS-derived sweep), `Makefile` comment
  blocks stating the two accepted residuals, `CLAUDE.md` and three `TODO.md` entries. **No
  behavioral change to any recipe** in this commit: the `Makefile` diff is comment-only (verified
  hunk by hunk), so the guards' shell is exactly what the tracer reviewed.
- `c51f6f9` ("Clean up comments to standard"): comment-rewriter sweep, one docstring trimmed in
  `_bazel_invocations`. No code change.

Adversarial checks on the new test code, since no reviewer saw it: the widened sweep could have
false-positived on recipe prose (`bazel-toolchain-guard`'s "the root MODULE.bazel pin") — the
`(?<![\w.-])` lookbehind handles it; `_recipe(step)` resolves for all four swept steps (`\n<step>:`
is unique per recipe, and the `.PHONY`/`CHECK_STEPS` mentions are not line-initial);
`_passing_path`'s rejoin point is the attribution block's own `fi; \` in both lanes, not the
`check-common` one (it slices from within the recipe). `bazel test //tests:test_check_step_order`
passes at HEAD. No regression or new unhandled path found.

## Approved

16 findings: 13 Fixed verified, 3 TODOs acceptable.

---

## Verdict: APPROVED

Every Fixed disposition is verifiable at the named lines and the tests that pin it are green at
HEAD. The three TODOs each clear both rubric questions, carry the slug join in both directions,
and name a concrete "done"; none of them defers designed functionality, so there is no scope
signal to escalate. The two configuration residuals the tracer found are now stated where a future
reader meets them (recipe comment, `CLAUDE.md`, `TODO.md`) rather than left implicit, which is what
the findings asked for and what the frozen design's user-directed uniform configuration permits.
