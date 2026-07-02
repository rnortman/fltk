# Design: `bazel-neg-test-harness` — automated negative tests for `generate_rust_parser` misconfiguration guards

Requirements: `docs/adr/2026/07/01/01-bazel-neg-test-harness/request.md`
Exploration: `docs/adr/2026/07/01/01-bazel-neg-test-harness/exploration.md`
Base commit: c03a801. (All line citations in this design are verified at
c03a801. exploration.md was written at 8fd5ecf, whose line numbers differ —
e.g. the TODO.md entry sat at 109-111 there vs. 59-61 here.)

## Context / root cause

`generate_rust_parser` (rust.bzl) protects downstream Bazel consumers with 7
misconfiguration conditions, implemented at exactly two `fail()` call sites:

1. **Six pure-Rust-mode knob checks** — `rust.bzl:612-622`: a templated loop over
   `(attr_name, is_set)` tuples for `protocol_module`, `protocol`, `lib_rs`, `deps`,
   `crate_features`, `recursion_limit`; message
   `"generate_rust_parser: {attr} is only valid with python_extension = True."`.
   Fires inside the macro body, i.e. **at loading time** (BUILD-file evaluation).
2. **`protocol` → `protocol_module` coupling** — `_require_protocol_module`
   (`rust.bzl:32-41`), message
   `"generate_rust_parser: protocol = True requires a non-empty protocol_module."`.
   Called from two sites: the macro at `rust.bzl:603` (**loading time**) and the
   internal rule impl `_generate_rust_srcs_impl` at `rust.bzl:140` (**analysis time**).

None of this is automatically tested (verified once by hand — TODO.md:59-61,
`BUILD.bazel:138-142`, `docs/workflow-bazel-protocol/implementation-log.md`
"Misconfiguration coverage"). `bazel_skylib` is not a dependency
(`MODULE.bazel:5-6`). Per request.md, the misconfiguration UX is public API now
that the Bazel Rust surface is public; a future edit that disables a guard or
mangles a message must be caught.

## Correction to the requirements' sketch

request.md sketches "one `analysistest` negative target per guard condition."
That is not literally implementable: `analysistest` asserts **analysis-time**
failures of an instantiated target, but six of the seven conditions (and the
macro-side firing of the seventh) call `fail()` during **loading** — the BUILD
file containing the misconfigured macro call never finishes evaluating, so
there is no target for `analysistest` to wrap, in any package, under any tag.
Only the rule-impl guard at `rust.bzl:140` is an analysis-time failure.

The intent — automated per-condition regression coverage asserting failure with
the expected message, via a `bazel_skylib` harness — is fully achievable with
the standard skylib toolkit:

- **skylib `unittest`** for the loading-time guard *logic*, after extracting it
  into pure functions that return the failure message instead of failing
  (behavior-preserving refactor; the macro then does `if msg != None: fail(msg)`).
- **skylib `analysistest`** (`expect_failure = True`) end-to-end for the one
  analysis-time guard.

### Rejected alternatives

- **Deferred-fail rule** (macro instantiates a rule whose impl `fail()`s,
  converting loading-time errors to analysis-time so `analysistest` covers them
  end-to-end): changes when consumers see the error (target analysis instead of
  package load). Misconfiguration UX is API (request.md); altering production
  error timing to suit the test harness is backwards.
- **Bazel-in-Bazel `sh_test`** driving `bazel build` against fixture workspaces:
  the only true end-to-end test of loading-time `fail()`, but nested-Bazel
  hermeticity/toolchain cost is disproportionate to request.md's "cheap
  insurance" framing.

## Proposed approach

### 1. `MODULE.bazel`: add skylib as a dev dependency

```starlark
bazel_dep(name = "bazel_skylib", version = "<latest BCR release>", dev_dependency = True)
```

(Substitute the current latest BCR release at implementation time — not
verifiable from this repo, so no literal is pinned here.) `dev_dependency =
True` keeps skylib out of downstream consumers' module graphs. Invariant:
`rust.bzl` and `rules.bzl` — the files consumers load — must never load skylib;
only the new test-only `.bzl` does.

### 2. `rust.bzl`: behavior-preserving guard extraction + test accessor

- New `_pure_rust_mode_violation(protocol_module, protocol, lib_rs, deps,
  crate_features, recursion_limit)`: contains the existing knob-tuple loop
  (`rust.bzl:612-622`) verbatim, but returns the message string for the first
  offending knob, or `None`. It compares `recursion_limit` against
  `_DEFAULT_RECURSION_LIMIT` internally, preserving the single-owner property
  (`rust.bzl:26-30`). The macro's pure-Rust branch becomes:
  `msg = _pure_rust_mode_violation(...); if msg != None: fail(msg)`.
- New `_protocol_module_violation(protocol, protocol_module)`: returns the
  coupling message or `None`. `_require_protocol_module` keeps its name and
  both call sites (`rust.bzl:140`, `rust.bzl:603`) and becomes
  `msg = _protocol_module_violation(...); if msg != None: fail(msg)` — the
  shared-single-check property (`rust.bzl:33-38` docstring) is preserved.
- Export one test-only accessor at the bottom of `rust.bzl`:

  ```starlark
  # Not public API. Exported solely for //tests/bazel_rules. Downstream
  # consumers must not load this symbol; it may change without notice.
  rust_bzl_internals = struct(
      pure_rust_mode_violation = _pure_rust_mode_violation,
      protocol_module_violation = _protocol_module_violation,
      generate_rust_srcs = _generate_rust_srcs,
      default_recursion_limit = _DEFAULT_RECURSION_LIMIT,
  )
  ```

  A struct is one exported name instead of four, and its name signals intent.
  Instantiating a rule via a struct attribute should be legal (the rule is
  bound to a top-level global in its defining `.bzl`, which is what Bazel
  requires) — but this is an external-Bazel-semantics claim with no in-repo
  precedent, so **verify it first**: build the `neg_protocol_without_module`
  target's analysis before writing the rest of the suite. If it fails, fall
  back to a direct `generate_rust_srcs_for_testing = _generate_rust_srcs`
  alias (second exported symbol, same comment discipline) and adjust the §3
  BUILD snippet accordingly.

No other production changes. Messages, conditions, ordering, and firing phase
are all unchanged.

### 3. New test package `tests/bazel_rules/`

Three files:

- **`dummy.fltkg`** — minimal one-rule grammar for the analysistest
  target-under-test's mandatory `src`. Analysis fails before any action runs,
  so content is never parsed; a real tiny grammar is used purely so the fixture
  is self-explanatory.
- **`rust_bzl_tests.bzl`** — loads `//:rust.bzl` (`rust_bzl_internals`) and
  skylib's `unittest`/`analysistest`/`asserts`:
  - Unit tests (skylib `unittest`) of `pure_rust_mode_violation`:
    - one assertion per knob — exactly one knob set away from default, all
      others at defaults — asserting the **exact** message string
      (`"generate_rust_parser: <knob> is only valid with python_extension = True."`).
      `recursion_limit` uses `default_recursion_limit + 1`; `lib_rs` uses a
      string label (its sentinel is `None`, not falsiness).
    - all-defaults case → `None`.
  - Unit tests of `protocol_module_violation`:
    - `(True, "")` → exact coupling message; `(True, "some.module")` → `None`;
      `(False, "")` → `None`.
  - Analysis test: `analysistest.make(expect_failure = True)` wrapping a
    target-under-test instantiated in the BUILD file via
    `rust_bzl_internals.generate_rust_srcs`, asserting via
    `asserts.expect_failure(env, "protocol = True requires a non-empty protocol_module")`
    (substring match, per skylib semantics). Note: via the public macro this
    analysis-time guard is shadowed by the loading-time call at `rust.bzl:603`;
    instantiating the internal rule directly is the only way the analysis-time
    path fires, which is exactly the defense-in-depth path this test pins.
  - A `rust_bzl_test_suite(name)` macro (skylib convention) that instantiates
    everything.
- **`BUILD.bazel`** — the target-under-test:

  ```starlark
  rust_bzl_internals.generate_rust_srcs(
      name = "neg_protocol_without_module",
      src = "dummy.fltkg",
      protocol = True,
      protocol_module = "",
      tags = ["manual"],
  )
  ```

  plus `rust_bzl_test_suite(name = "rust_bzl_tests")`. The `manual` tag is the
  standard skylib `expect_failure` pattern: wildcard patterns (`//...`) skip
  the intentionally-failing target, while the analysistest still analyzes it
  and captures the failure. This resolves the old
  "intentionally-failing targets cannot be committed" constraint that motivated
  deferring this work.

Test granularity requirement: a regression in any single condition or message
must produce a test failure that names that condition. Whether that is one
skylib test function per knob or grouped functions with per-knob assertion
messages is an implementation choice.

### 4. Cleanup

- Delete the `TODO(bazel-neg-test-harness)` comment (`BUILD.bazel:138-142`).
- Delete the `bazel-neg-test-harness` entry (`TODO.md:59-61`).

## Coverage summary and accepted residual gap

| Condition | Coverage |
| --- | --- |
| 6 pure-Rust knob checks (condition + exact message) | skylib unittest on extracted function |
| protocol coupling, logic (condition + exact message) | skylib unittest on extracted function |
| protocol coupling, analysis-time firing in `_generate_rust_srcs` | analysistest, end-to-end |
| Loading-time `fail()` wiring in the macro (2 × `if msg != None: fail(msg)`) | **not covered** |

The uncovered residue is two trivial lines. The historically churned part — the
condition/message logic (six separate `if/fail`s were already refactored into
the loop once, per exploration.md) — is fully pinned, and the shared coupling
helper is additionally exercised end-to-end through the rule path. Accepted as
the cheap-insurance tradeoff; the only ways to close it are the two rejected
alternatives above.

## Edge cases / failure modes

- **Downstream `bazel build @fltk//tests/bazel_rules/...`**: fails to load
  there because skylib is a dev dependency. Downstream consumers load
  `@fltk//:rust.bzl` / build `@fltk//:fltk`-side targets, not FLTK's test
  packages; no supported flow builds them from a consuming module. Not
  mitigated further.
- **Root `glob(["**/*.py"])` in `//:fltk`** (`BUILD.bazel:26`): adding a BUILD
  file makes `tests/bazel_rules` its own package, removing its files from the
  root glob — it contains no `.py` files, so the glob's contents are unchanged.
  The directory also has no `Cargo.toml`, so the Cargo workspace
  (`MODULE.bazel:25-28` membership note) is unaffected.
- **Intentional message rewording**: exact-string unit tests fail. Desired —
  the messages are consumer-facing UX; changing one becomes a deliberate,
  test-visible act.
- **Knob-check ordering**: each unit test sets exactly one knob, so the tests
  do not over-constrain the loop's iteration order (only per-knob
  condition + message).
- **skylib version drift**: pinned in `MODULE.bazel` like the existing
  `rules_python`/`rules_rust` deps; no special handling.

## Test plan

After implementation the following exist and pass:

1. `bazel test //tests/bazel_rules:all` — the new suite:
   - 6 knob-violation assertions (exact message each) + 1 all-defaults → `None`.
   - 3 coupling-logic assertions (`(True,"")` → message, `(True,"m")` → `None`,
     `(False,"")` → `None`).
   - 1 analysistest asserting analysis failure of `:neg_protocol_without_module`
     with the coupling message.
2. Regression checks that the refactor changed nothing:
   - `bazel build //:bootstrap_rust_srcs //:bootstrap_native` still succeed
     (existing smoke targets, `BUILD.bazel:114-136`).
   - `bazel build //...` still succeeds (`manual` tag keeps the negative target
     out of the wildcard).
3. Guard-disable sanity check performed once during implementation (not
   committed): comment out one knob tuple in `rust.bzl` and confirm the
   corresponding unit test fails — proving the harness detects exactly the
   regression class the TODO describes.

Note: neither CI (`.github/workflows/ci.yml`) nor the Makefile invokes Bazel
today; these tests have the same run-manually status as the existing Bazel
smoke targets. Wiring Bazel into CI is out of scope here.

## Open questions

None. The one judgment call — deviating from request.md's literal
"analysistest per guard" sketch — is decided in the Correction section on
grounds request.md itself supplies.
