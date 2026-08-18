# Deep review (tracer) — round 1, wave 2

Reviewed: e677c38..b5167b93 (`git diff` base..HEAD). Files: `Makefile`,
`tests/test_check_step_order.py`, `CLAUDE.md`, `TODO.md`, workflow docs.

Traced adversarially: the `check-common` shell (both VERBOSE arms, failure arms, timing
arithmetic, mktemp/exit paths), the batched pyo3 guards in both lanes (quoting of
`$$(echo $$labels)` inside nested `$( )`, `set -e` interaction with `if`/`!`/`||`, the
attribution loop's `continue` + unconditional `exit 1`, `grep -qxF` exact-line semantics
against `bazel query` output, `rdeps` self-inclusion of `//crates/fltk-cst-core:no_python`
when it is itself a member of `$labels`), and every new test's regex against the literal
Makefile text (`_from`, `_quiet_arm`/`_verbose_arm` slicing, the `rdeps\(set\(` non-greedy
match over the nested-paren `$$(echo $$labels)` universe, the `done; \`+`exit 1` pattern,
the `\bbazel ([a-z]+)\b` sweep against echo strings containing "bazel-test"). All of those
hold; the fail-closed properties (empty `$labels` fails, empty `reaching` fails every
per-target grep, attribution disagreement still exits 1, quiet-mode buffer is dumped before
exit) are intact. Findings below.

## Findings

### correctness-pyo3-guard-asserts-lint-config-only

- **File:line:** `Makefile:229,236` (union cquery and attribution cquery, `--config lint`);
  contrast base `Makefile` (`git show e677c38:Makefile`, lines 165-173), where the per-target
  cqueries ran with no `--config`.
- **What's wrong:** Part 4 moved the root-lane pyo3 negative assertion from the default
  target configuration to the lint configuration. `--config lint` sets a real build setting,
  `--//bzl:lint=true` (`.bazelrc` `build:lint` block, `bzl/lint_flag.bzl`), which any
  `select()` in the tree can key on. The guard now proves "pyo3 absent when lint=true"; the
  configuration downstream consumers of the `:no_python` flavors actually build — and the one
  the base commit's guard covered — is lint=false, which no root-lane assertion inspects
  anymore.
- **Why:** Trace the input that breaks it: a dep expressed as
  `select({"//bzl:lint_enabled": [], "//conditions:default": [pyo3-flavored dep]})` (or any
  select on the lint setting, which is exactly the setting this config flips) puts pyo3 in
  every consumer-facing build while the union cquery, run only at lint=true, sees a clean
  graph. The design and the Makefile comment (`Makefile:213-215`) justify `--config lint` on
  the cqueries purely as an analysis-cache measure ("a different configuration mid-gate
  discards the analysis cache") — nowhere is the change of *assertion surface* stated or
  accepted. The consumer lane still asserts in its own default config, but it only covers
  the three consumer targets, not the nine root-derived ones (the Makefile's own comment at
  `Makefile:167-170` says the consumer lane's coverage gap is why the root guard exists).
- **Consequence:** A pyo3 edge gated behind `select()` on the lint flag (or any other
  setting the lint config flips) ships in every non-lint build of a `:no_python` target /
  `rust_binary` with the gate green. Low likelihood today (no such select exists on Rust
  deps), but the guard's whole reason to exist is graphs that build fine and pass tests
  while silently linking libpython — this is one more shape of exactly that.
- **Suggested fix:** State the narrowing as a deliberate accepted consequence in the
  Makefile comment and CLAUDE.md (it currently reads as if only the cache behavior changed),
  or — if the default-config fact is worth keeping — note it under the existing
  TODO(pyo3-guard-shared-helper) as something the helper could restore cheaply (one extra
  default-config union cquery costs ~6s and, running last in the step, pays the
  config-switch penalty once rather than reintroducing mid-gate thrash for the test step).

### correctness-positive-control-select-blind

- **File:line:** `Makefile:223-228` (root), `Makefile:303-308` (consumer): the per-target
  positive control is `bazel query "rdeps(set(...), ...no_python)"`, a loading-phase query.
- **What's wrong:** The base commit's per-target control was configured: each target's
  `cquery deps(...)` output had to contain `fltk-cst-core:no_python`, proving the *configured*
  graph the negative assertion runs over actually reaches the runtime crates. The restored
  control checks the *unconfigured* graph, where `bazel query` unions all `select()` branches
  and ignores configuration entirely. The Makefile comment (`Makefile:203-207`) asserts
  "'this target still reaches the runtime crates' is a structural fact about the unconfigured
  graph, and the configured half of the control is the union check above" — but the union
  check is one fact over nine targets: a single member reaching `no_python` satisfies it for
  all the others.
- **Why:** The vacuity scenario the control exists for — "a target that stopped reaching
  them at all (retargeted, stubbed, aliased somewhere harmless)", `Makefile:200-202` — is
  reopened for any divergence between unconfigured and configured graphs: a target whose dep
  on the runtime crates sits in a select branch not taken under the gate's configuration
  passes the per-target control (query sees the branch) while contributing nothing to the
  configured union, and the union-level control is satisfied by the other eight members. Net:
  that target's pyo3 assertion is vacuous again, exactly the weakening the r1-w1 reviewer
  flagged, surviving in the select-divergence corner.
- **Consequence:** Silent vacuity, not a wrong failure: the gate stays green while one
  derived target's configured graph is no longer being inspected for pyo3 in any meaningful
  sense. Requires a select-shaped retargeting, so narrow — but the control's entire purpose
  is the narrow silent case.
- **Suggested fix:** Cheapest configured per-target fact without the ~25s rdeps cquery: the
  union cquery's output is already in `$graph`; a per-target `cquery deps($target)` is what
  cost 53s, but `cquery "somepath($target, //crates/fltk-cst-core:no_python)"` per target is
  equally expensive. Realistic options: accept and document the select-divergence residual
  honestly in the comment (it currently overclaims "the configured half of the control is
  the union check"), or run the rdeps as one `cquery` in the consumer lane only (its graph
  is small; the ~25s figure was the root lane).

### test-one-config-sweep-scoped-to-two-recipes

- **File:line:** `tests/test_check_step_order.py`, `test_root_gate_runs_one_configuration`
  (sweeps `_recipe("bazel-test")` plus one literal assert on `_recipe("bazel-lint")`).
- **What's wrong:** The invariant the design states is "no root-lane invocation alternates
  configuration mid-gate" (design.md Part 4, and the test plan's own wording). The test pins
  it only for the `bazel-test` recipe's invocations and `bazel-lint`'s one line. A new step
  appended to `CHECK_STEPS` (the documented extension point — "ADD new steps here",
  `Makefile:29`) that runs a plain `bazel build`/`bazel run`/`bazel cquery` in the root
  workspace reintroduces the mid-gate analysis-cache discard Part 4 exists to remove, with
  this test green. The docstring's claim ("a `bazel build` or `bazel run` added to this
  recipe later has to carry the configuration") is true only of one recipe.
- **Consequence:** Silent performance regression channel: the gate re-grows the tens-of-
  seconds re-analysis tax through the one extension point the Makefile advertises, and the
  test named for the invariant keeps passing.
- **Suggested fix:** Derive the swept recipes from `CHECK_STEPS` (excluding
  `bazel-consumer-check`, the deliberately separate workspace, and steps whose recipes
  contain no `bazel ` at all), running the same verb/allowlist sweep over each.

### quality-stray-content-tag-in-dispositions

- **File:line:** `docs/workflow/2026-08-17-make-check-verbosity/dispositions-deep-r1-w1-a1.md`,
  last line.
- **What's wrong:** The file ends with a literal `</content>` line — a copy-paste artifact
  from whatever tool buffer the document came out of.
- **Consequence:** Cosmetic only; committed noise in a workflow record.
- **Suggested fix:** Delete the line.

## Checked and clean (for the responder's benefit)

- `check-common`: timing arithmetic (`$$(( $$(date +%s) - step_start ))`) expands to valid
  POSIX shell; both failure arms print duration + gate total with the `FAILED: $$step` token
  preserved; quiet arm removes the tmpfile on both paths; `exit 1` inside the loop kills the
  recipe shell and fails make. `VERBOSE` values other than `1` (e.g. `VERBOSE=yes`) fall to
  quiet — matches the documented 0/1 contract, not a trap worth flagging.
- Guard shell: nested quoting of `"deps(set($$(echo $$labels)))"` is correct (quoting
  restarts inside `$( )`); label word-splitting is safe for this repo's label alphabet;
  `grep -qxF` against `bazel query` output is exact-line-correct in both workspaces (the
  consumer greps only its own `//:` labels, sidestepping canonical-repo-name printing);
  the attribution fallback's `continue` cannot convert red to green (`exit 1` after the loop
  is unconditional); `$err` is only ever `cat`ed on a failure path (occasionally containing
  a prior successful command's progress noise — cosmetic).
- The new tests' region slicing and regexes all match the shipped Makefile text, including
  the non-obvious `rdeps\(set\((.*?)\), ` non-greedy match over the nested parens of
  `$$(echo $$labels)`, and the `\bbazel ([a-z]+)\b` sweep does not false-positive on the
  hyphenated "bazel-test" echo strings.
- No security-relevant surface: no untrusted input reaches the shell; `mktemp` is used for
  both buffers; no secrets, no injection sinks.
