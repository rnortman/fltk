# Workflow scan — round 1 (final), `make check` verbosity

**Decision: CONTINUE.** This was the final implementation round and the log accounts for all four
parts of the design, so there is no future work left for anything below to contaminate. Two items
are decisions that are now waiting on you rather than problems that block the pipeline; the rest
is smaller.

Covered: `docs/workflow/2026-08-17-make-check-verbosity/` (design + design reviews r1/r2, prepass,
deep review waves 1 and 2, all dispositions and verdicts) and commits
`e677c38..c51f6f9`.

---

## The no-pyo3 guard now only holds under the lint configuration, and nobody asked you about it

Background you need: `make check`'s `bazel-test` step contains a guard whose job is to prove that
none of the "pure Rust" build targets — every target named `no_python`, every Rust binary, and the
compile-gate crate — has picked up a dependency on `pyo3`. That guard matters because, as
`CLAUDE.md` and the recipe's own comment say, a `:no_python` target that starts linking libpython
still compiles and still passes its tests: the guard is the only thing that notices. It works by
asking Bazel to print the dependency graph of those targets and grepping for `pyo3`.

Before this change, that graph was asked for in Bazel's **default** configuration — the same
configuration a downstream consumer of fltk builds in. Part 4 of the design (your directive, in
`notes-design-user-r2.md`: "Just run everything with `--config lint`") made every configured Bazel
invocation in that step, including the guard's, run with the lint build setting turned on
(`--//bzl:lint=true`). That was proposed and approved purely as an analysis-cache-thrash fix; the
design's Part 3 says in as many words that "the guards' *properties* are untouched." That turned
out not to be true. The guard now proves "no pyo3 when lint is on"; nothing in the gate any longer
checks the configuration your consumers actually build.

A second, related weakening landed in the same round. The guard's "positive control" — the check
that keeps the negative assertion from passing vacuously over an empty or wrong graph — was
per-target and configuration-aware before this change. It was collapsed to a single union-level
fact in the first increment, then restored per-target in wave 1, but restored using an
*unconfigured* query (`bazel query "rdeps(...)"`, chosen because the configured form costs ~25s).
The net position, stated honestly in the shipped comment at `Makefile:209-213`, is that **no
per-target configured fact is asserted anywhere**: a target whose edge to the runtime crates sits
in a `select()` branch the gate's configuration doesn't take passes its own control while
contributing nothing to the union that the pyo3 grep actually runs over.

Both of these were found by reviewers (the wave-2 tracer, `notes-deep-tracer-r1.md`, findings
`correctness-pyo3-guard-asserts-lint-config-only` and `correctness-positive-control-select-blind`)
and both were dispositioned **Fixed by documenting them** — comments in the `Makefile`, a sentence
in `CLAUDE.md`, and a paragraph folded into `TODO(pyo3-guard-shared-helper)` in `TODO.md`. The
judge accepted that, correctly noting the reviewer had offered documentation as one of its two
options and that the other option costs back the seconds this change exists to save.

Why I'm raising it anyway: this is a deliberate reduction in the coverage of a safety net that the
repo documents as unique and irreplaceable, it was a side effect of a directive you gave about
*performance*, and it reached you nowhere except as a comment in a file you have not been asked to
read. Exploiting it requires a `select()` on the lint setting over a Rust dependency, which does
not exist today, so the exposure is latent rather than live. Also worth knowing: the restoration is
now parked behind `TODO(pyo3-guard-shared-helper)`, which is itself blocked on an unrelated
question (whether the `tests/bazel_consumer` module may reach up into the parent repo for a shared
shell script), so "buy the default-configuration fact back" is not a small independent errand any
more — it is bundled with a repo-boundary decision.

Where to look: `Makefile:209-213` and `Makefile:219-228` (the two stated residuals),
`Makefile:236-245` (the control and the union cquery), `CLAUDE.md:145`, `TODO.md` entry
`pyo3-guard-shared-helper`, `notes-deep-tracer-r1.md`, `dispositions-deep-r1-w2-a1.md`.

## A hermeticity decision was deferred to you, and this is the only place you'd learn of it

Part 1 of the change replaced `check-common` — the loop that runs every gate step — with a
substantially bigger shell recipe: a `case`, a `VERBOSE` branch, a nested `if`, four arithmetic
expansions and two failure arms (`Makefile:59-83`). Every test over it is a text grep on the
Makefile. Nothing executes it. The wave-2 test reviewer demonstrated a cheap, Bazel-free way to
close that (`make -n check-common CHECK_STEPS=<target>` runs the whole loop in under a second and
exercises both failure arms), and it was still deferred as
`TODO(check-common-executable-coverage)`.

The deferral is legitimate on its own terms and both the responder and the judge said why: adding a
test that shells out to `make` puts a host tool the build graph does not pin into the test graph,
which this repo documents `genhtml` as its *sole* exception to; the alternative (extract the recipe
text, substitute, run under `bash`) trades that for a harness that can drift from what `make`
actually expands. That is your call to make, not theirs.

What is at stake if it stays open: quiet mode is the default locally and in the pre-commit hook,
and quiet mode's job is to swallow a passing step's output and dump the buffer when a step fails.
If the `VERBOSE` comparison, the non-zero-exit propagation out of the loop, or the buffer dump ever
breaks, `make check` can go green on a failing step or fail with no explanation, and the whole test
suite stays green. The implementer did exercise both failure arms by hand in both modes during
implementation, so it works today; the gap is that nothing catches the next regression.

Where to look: `Makefile:59-83`, `tests/test_check_step_order.py:298-300`, `TODO.md` entry
`check-common-executable-coverage`, `notes-deep-test-r1.md` finding
`test-no-executable-coverage-check-common`.

## The earlier review pass looked straight at the first item and waved it through

Worth knowing about the process, since the outcome was fine. The prepass reviewer explicitly
considered the lint-configuration narrowing and declined to file it ("No consequence to state, so
no finding"), and the prepass judge independently asserted the stronger, wrong claim that the lint
setting "cannot add a pyo3 edge to a `:no_python` / `rust_binary` graph" and approved on that
basis. Two agents reasoned their way to "nothing to see here" on the one substantive semantic
change in the round; only the later adversarial wave caught it. No harm done here — the deep review
picked it up — but the pattern is that the residual survived a reviewer *and* a judge who both had
it in hand.

Where to look: `notes-prepass-r1.md` (last paragraph of the slop lane),
`judge-verdict-prepass-r1-a1.md` (last bullet of the slop-lane section).

## Two smaller things

**The headline number was never re-measured at the shipped code.** The whole point of Parts 3 and 4
is hot-gate latency, and the design's manual-verification list asks for a re-run of the timing
measurement. The last hot measurement in the log is 54s, taken after wave 1 (`bazel-test` 35s,
`bazel-lint` 3s, `bazel-consumer-check` 16s) — down from ~140s and inside the design's 55-65s
expectation, but ~24s above the 30s the first increment measured, because wave 1's fix added an
extra query per lane. The wave-2 entry reports 112s with a cache the edits had just invalidated and
no fresh hot number. Wave 2 touched only comments and test code, so 54s should still hold; nobody
confirmed it. `implementation-log.md`, lines 45-53 / 89-93 / 130-132.

**A load-bearing explanation was deleted by the final commit.** `c51f6f9` ("Clean up comments to
standard") stripped the docstring paragraph from `_bazel_invocations` that recorded why its regex
needs a lookbehind — the widened configuration sweep had failed because the prose "the root
MODULE.bazel pin" in a recipe's echo string parsed as an invocation of `bazel pin`. That is exactly
the kind of surprise a comment exists to preserve, it was discovered during this round, and the
comment-cleanup pass removed it. The judge saw the change and classified it as "no code change".
`tests/test_check_step_order.py:397-404`, `judge-verdict-deep-r1-a1.md` §Respond-commit scan.

Everything else in the round checks out: the frozen `design.md` is unchanged since it was committed
in `360e4d6`, all four design parts trace to the log and the diff, every "Fixed" disposition I
spot-checked is present at the named lines, the three added TODOs each carry both halves of the
slug join, and no design item is left unaccounted for.
