# Design review notes — bazel-neg-test-harness

Verified against the working tree at c03a801 (rust.bzl, MODULE.bazel, BUILD.bazel, TODO.md,
.bazelrc, tests/ layout, .github/workflows + Makefile, and the 8fd5ecf→c03a801 diff).

Confirmed accurate (no findings): the two `fail()` sites and exact messages
(`rust.bzl:41`, `rust.bzl:622`); the 6-knob tuple list (`rust.bzl:612-619`); the shared
`_require_protocol_module` with call sites at `rust.bzl:140` (analysis time) and
`rust.bzl:603` (loading time); skylib absent from `MODULE.bazel` (lines 5-6 list only
rules_python/rules_rust); `TODO.md:59-61` and `BUILD.bazel:138-142` cleanup targets; no
`.bazelignore` and no BUILD files anywhere under `tests/`, so `tests/bazel_rules/` becomes a
new package cleanly; the root `glob(["**/*.py"])` edge-case reasoning (the new dir has no
`.py` files); no Bazel invocation in CI or Makefile; bzlmod enabled (`.bazelrc`). The central
"Correction" is factually right: six of seven conditions (plus the macro-side seventh) fire
during BUILD-file evaluation of the legacy macro, so `analysistest` cannot wrap them and the
request's literal "one analysistest per guard" sketch is unimplementable; the
extract-and-unit-test approach preserves message, condition, ordering, and firing phase.
Requirements coverage is complete (all 7 conditions + messages, dep added, TODO cleanup in
both places per the TODO-system convention), the residual gap (two `if msg != None:
fail(msg)` wiring lines) is honestly declared, and scope is disciplined.

## design-1 — Stated base commit is wrong; citations actually match c03a801

- Section: header, "Base commit: 8fd5ecf."
- What's wrong: the design's line citations are taken from c03a801 ("TODO burndown"), not
  8fd5ecf. At 8fd5ecf the TODO.md entry sits at lines 109-111 (per exploration.md:7) and the
  macro's coupling call sits at rust.bzl:604 (per exploration.md:22); the design cites
  TODO.md:59-61 and rust.bzl:603, which are correct only at c03a801 (the 8fd5ecf→c03a801
  diff removes a net line above rust.bzl:603 and 50 lines from TODO.md). The task-supplied
  base for this work is c03a801.
- Why: `git diff --stat 8fd5ecf c03a801` shows TODO.md -50 lines and rust.bzl/-MODULE.bazel
  edits; current-tree reads confirm every design citation at c03a801.
- Consequence: an implementer who checks the design's citations against its *stated* base
  finds them all off (TODO entry at 109, not 59) and either distrusts otherwise-correct
  citations or edits the wrong lines; MODULE.bazel content also differs between the commits.
- Fix: change the header line to `Base commit: c03a801`.

## design-2 — skylib version snippet contradicts its own instruction (unverified external claim)

- Section: "1. MODULE.bazel", snippet `version = "1.7.1"` + "(Pin the current latest BCR
  release at implementation time.)"
- What's wrong: "1.7.1" is presented in the copyable snippet while the parenthetical says to
  pin the latest BCR release. Whether 1.7.1 is the latest is not verifiable from this repo
  (external-registry claim), and bazel_skylib releases newer than 1.7.1 (1.8.x) existed well
  before this design's date, so the two statements likely conflict.
- Why: no vendored skylib or lockfile in-tree to check against (exploration.md:30 confirms
  skylib absent); the claim is registry knowledge, flagged unverified.
- Consequence: an implementer copying the snippet verbatim pins a stale version, silently
  ignoring the design's own instruction; harmless functionally but a built-in ambiguity about
  which of the two directives wins.
- Fix: make the snippet's version a placeholder (`version = "<latest BCR release>"`) or drop
  the literal.

## design-3 — Struct-attribute rule instantiation asserted as "legal" without in-repo evidence

- Section: "2. rust.bzl ... test accessor", "Instantiating a rule via a struct attribute is
  legal (the rule is bound to a top-level global in its defining .bzl ...)".
- What's wrong: this is an external Bazel-semantics claim with no in-repo precedent (nothing
  in the tree instantiates a rule through a struct field), so it is unverified. The design
  does hedge with a concrete fallback (`generate_rust_srcs_for_testing = _generate_rust_srcs`
  alias).
- Why: repo-wide search shows no existing struct-exported rule usage to point to; the claim
  rests on Bazel behavior not checkable here.
- Consequence: limited — if the struct path fails at implementation time, the BUILD.bazel
  snippet in §3 (`rust_bzl_internals.generate_rust_srcs(...)`) and the "one exported name
  instead of four" rationale both need reworking mid-implementation (the alias reintroduces a
  second exported symbol). Because the fallback is pre-declared, this costs churn, not
  correctness; flagged so the implementer verifies it first rather than last.
