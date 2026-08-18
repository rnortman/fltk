# Making `make check` faster and less opaque

## What this is about

FLTK is a parser-generation toolkit. Its build system is Bazel, and its pre-commit gate is `make check` -- a Makefile recipe that runs a sequence of Bazel commands (tests, lints, lock-file checks) and reports pass/fail. Two things are wrong with it:

1. **You cannot see what it is doing.** Every step's output is captured to a temp file and thrown away on success. A run that takes over two minutes looks identical to a run that is hung. There is no `VERBOSE` flag.

2. **It takes about 140 seconds even when nothing has changed.** Bazel caches aggressively, so a fully-cached run with zero source changes should be fast. It is not.

The goal is to fix both: add optional visibility into what is happening, and cut the hot-cache time roughly in half.

## The pieces of the system you need to know about

**`make check`** runs a list of named steps in order. Each step is itself a Make recipe that typically invokes one or more Bazel commands. The steps, roughly, are:

- A toolchain-version guard (instant).
- `bazel-test`: runs all tests, then runs a "pyo3 guard" -- a set of queries that verify certain build targets do not link against pyo3 (a Python-to-Rust bridge library). The property being checked is that pure-Rust library targets stay pure-Rust.
- `bazel-lint`: runs clippy (Rust linter), ruff (Python linter/formatter), and pyright (Python type checker) via `bazel build --config lint //...`.
- `bazel-consumer-check`: a separate Bazel workspace that pretends to be a downstream consumer of the library, with its own pyo3 and serde guards.
- A lock-file diff check (instant).

**`--config lint`** is a Bazel configuration that turns on lint targets and the clippy aspect. It changes Bazel's build settings, which matters because Bazel discards its in-memory analysis cache whenever the configuration changes.

**`bazel cquery`** resolves a target's full transitive dependency graph under a specific configuration. The pyo3 guards use it to check that pyo3 does not appear in certain targets' dependency closures. Each invocation costs about 5-6 seconds of overhead even when everything is cached, because Bazel must start up, check for file-system changes, and print the full closure.

## Where the time actually goes

Detailed measurement identified two culprits:

**The dominant cost (~76 seconds): serial `bazel cquery` invocations.** The pyo3 guards run 9 separate `bazel cquery` commands in the main workspace and 4 in the consumer workspace, one target at a time, each paying ~5-6 seconds of fixed startup cost. That is about 76 seconds to confirm cached results 13 times.

**The secondary cost (~40 seconds): analysis-cache thrashing from configuration switching.** `make check` runs `bazel test //...` (default config) and then `bazel build --config lint //...` (lint config). When Bazel switches between configurations, it discards its in-memory analysis cache and re-analyzes the build graph. So every gate run pays for re-analysis at least twice. Even a single no-op `bazel test //...` costs 17-21 seconds after a config switch, or about 6 seconds back-to-back with itself. The consumer workspace has its own Bazel server and pays a similar ~21 second floor independently.

## What we are going to do

Four parts, all landing together. Parts 1 and 2 are the visibility feature. Parts 3 and 4 are the performance fixes.

### Part 1: A `VERBOSE` flag with sensible defaults

A new `VERBOSE` variable at the top of the Makefile controls whether step output is streamed live or buffered.

- **Locally, the default is quiet** (the current behavior). Output is captured; on success it is discarded; on failure it is dumped so you can see what went wrong.
- **In CI, the default is verbose.** GitHub Actions always sets the environment variable `CI=true`. The Makefile detects this with `$(filter true,$(CI))` -- an exact string match on the word `true` -- and defaults to `VERBOSE=1`. A CI log that shows nothing until the final line is useless for diagnosing hangs or slowness.
- **You can always override.** `make check VERBOSE=1` locally gives you streaming output. `make check VERBOSE=0` in CI gives you quiet mode. The `?=` assignment means an explicit value on the command line or in the environment always wins.

The reason `ci.yml` is not edited: the CI workflow already runs `make check-ci`, and a test pins that exact invocation. Rather than changing the CI workflow and its test, the Makefile reads the `CI` environment variable that GitHub Actions already provides.

Both modes gain a heartbeat: one line when each step starts, one when it finishes with its wall-clock time. This is deliberately outside the verbose/quiet branch -- even quiet runs show which step is running and how long each took. That is Part 2.

### Part 2: Permanent per-step timing (the diagnosis surface)

This is the heartbeat lines from Part 1 doing double duty. Every future run, in any mode, reports where its time went at step granularity. The next time something regresses, the information is already in the output without needing any special instrumentation. Timing uses `date +%s` (1-second resolution, POSIX-portable), sufficient for steps that take 5-50 seconds each.

### Part 3: Batch the cquery guards (~76 seconds down to ~12 seconds)

The key insight is a set-theory identity: `deps(set(A B C))` equals `deps(A) union deps(B) union deps(C)`. So "pyo3 is absent from the union" is the same statement as "pyo3 is absent from every member." Instead of 9 separate `bazel cquery` calls, we run one over the union.

**Root workspace -- the batched guard:**

1. One `bazel query` derives the target labels (unchanged from today).
2. One `bazel cquery "deps(set(...))"` computes the dependency graph of all targets at once.
3. A positive control verifies the output contains a known target (`fltk-cst-core:no_python`), catching the case where a silently-empty cquery would vacuously pass the negative check.
4. A negative assertion: grep for pyo3.
5. An attribution fallback: if pyo3 is found, re-run the old per-target loop to identify which target(s) are the offenders, then fail unconditionally. If the union said pyo3 is present but the per-target loop disagrees (possible if something rebuilt between the two runs), the gate still fails -- the union result is authoritative, and an inconsistency is itself a failure.

**What is knowingly given up:** The current per-target loop incidentally proves that every individual target's graph contains the `fltk-cst-core:no_python` marker. The batched version only checks the union. This is a weaker statement -- the positive control could pass even if one target's graph is unexpectedly empty, as long as another target's graph contains the marker. The design judges this acceptable because the positive control's stated purpose (per existing code comments and tests) is to prevent a silently-empty cquery from vacuously passing the negative assertion, and the union-level control serves that purpose.

**Consumer workspace:** 4 cquery invocations become 2. The pyo3 check batches into a union query. The serde assertions stay on a per-target query against `//:consumer_serde` specifically, because "the serde target links the consumer hub's serde" asserted on a union would be satisfiable by any member, which is a weaker statement than what is intended.

**Considered and rejected:** batching the cargo-probe sweep's two `bazel query` invocations (~9 seconds combined) into one. About 5 seconds saved for a meaningfully more fragile recipe; not worth it.

**Expected result of Part 3 alone:** ~140 seconds drops to ~80 seconds.

### Part 4: One configuration for the entire root gate

This eliminates the analysis-cache thrashing. Instead of running `bazel test //...` (default config) and then `bazel build --config lint //...` (lint config), the test step becomes `bazel test --config lint //...`. Now every root-lane Bazel invocation sees the same configuration, so there is no analysis-cache discard within a gate run.

The cquery invocations in the guard also get `--config lint` -- a config-less cquery between lint-config builds would reintroduce the discard. Verified working at the base commit: cquery inherits the `build:lint` block from `.bazelrc`, and the clippy-aspect flags are accepted. The plain `bazel query` invocations are untouched because `query` is loading-phase only and does not configure targets.

The `bazel-lint` step stays as a separate step. After `bazel test --config lint //...`, it is a same-configuration near-instant cache-hit confirmation. It is kept because: the user asked for both, it preserves a named step in the timing output, and it is a backstop if the `test` command ever skips an output group that `build` covers.

**The trade-off, and why it was chosen:** The gate's configuration now differs from what developers type when they run `bazel test //...` without `--config lint`. So alternating between a manual test run and a gate run still thrashes the analysis cache -- but now the thrash is dev-vs-gate rather than the gate thrashing itself. Since the gate runs far more often than manual test commands (it is a precommit hook), optimizing the gate is the better trade. A developer who cares can type `--config lint` themselves. This trade-off is the user's explicit decision.

**One-time cost at landing:** The first gate run after this change re-executes all tests once under the new configuration (different config checksum means no cached results). Subsequent runs cache normally.

**A lint failure may now surface during `bazel-test` instead of `bazel-lint`:** This is expected and fine. Because `bazel test --config lint //...` also builds lint targets, a clippy or ruff failure can stop the gate at the test step. Bazel names the failing target in its output, so attribution is clear regardless of which step trips. Earlier failure is better.

The consumer lane is untouched by Part 4. It already uses a single configuration, so there is no alternation to remove.

**Expected result of Parts 3 and 4 together:** ~140 seconds drops to roughly 55-65 seconds. The remaining floor is per-invocation Skyframe overhead on two servers plus the consumer workspace's independent ~21 seconds. No further structural lever exists short of merging the workspaces, which nobody has asked for.

## What could go wrong

- **`CI` set to something other than `true`** (`CI=false`, `CI=1`, empty): quiet mode. The `$(filter true,$(CI))` is an exact-word match, not a truthiness test.
- **A developer has `CI` exported in their shell:** they get verbose mode. `VERBOSE=0` overrides. Documented in the Makefile comment.
- **Ctrl-C during quiet mode leaks a temp file:** pre-existing behavior, unchanged. Not worth adding a shell trap.
- **Attribution fallback disagrees with the union result:** gate fails anyway. The union is authoritative; the fallback is purely for identifying the offender. Inconsistency is itself a failure.
- **Union cquery output is large:** the 9 individual graphs overlap heavily (shared toolchains, crate universe), so the union is roughly the size of the largest single graph, not 9 times larger. The shell capture pattern is unchanged.
- **Verbose mode shows `make[1]: Entering directory` noise:** harmless and mildly useful for debugging; no suppression added.
- **`date +%s` timing resolution:** 1-second resolution, sufficient at step granularity.
- **A future Bazel change makes cquery reject part of the lint config expansion:** the fallback would be passing the config's flags to cquery directly. The recipe uses `--config lint` so the three spellings (test, build, cquery) cannot drift apart.
- **`bazel-lint` after `bazel test --config lint //...`:** same configuration, so it cannot discard the analysis cache. Expected to be a cache-hit pass in seconds.

## What is still open

Nothing. The one open question from an earlier draft -- whether to merge the test and lint lanes onto one configuration or accept the ~80-second floor -- was answered by the user: merge them. That is Part 4.
