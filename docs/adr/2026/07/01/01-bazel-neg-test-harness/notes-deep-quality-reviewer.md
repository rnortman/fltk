# Deep quality review — bazel-neg-test-harness

Reviewed: 5eec3cd7..9afab45b (`bazel: add skylib negative-test harness` + prepass
respond commit). Read `rust.bzl` in full plus the new `tests/bazel_rules/`
package, `MODULE.bazel`, `BUILD.bazel`, `TODO.md` deltas.

Overall: clean change. The guard extraction is genuinely behavior-preserving
(conditions, messages, ordering, and firing phase unchanged; the knob-tuple loop
moved verbatim), the `rust_bzl_internals` struct is a well-fenced single export
with clear not-public-API signaling, skylib is correctly `dev_dependency`, and
the test suite pins exactly what the TODO asked for without over-constraining
loop order. Three small findings, all comment/duplication hygiene.

## quality-1: test-file docstring references the TODO slug this change deletes

- File: `tests/bazel_rules/rust_bzl_tests.bzl:3`
- Issue: `"Backs the TODO(bazel-neg-test-harness) work: ..."`. This change
  deletes both halves of that TODO (the `TODO.md` entry and the `BUILD.bazel`
  comment), so the docstring now cites a slug that no longer exists anywhere.
- Consequence: The project's TODO system uses `TODO(slug)` as a grep-able join
  key against `TODO.md`. This line is a dangling pseudo-TODO: any `TODO(`
  grep/audit (including the todo-burndown flow) matches it, and a reader who
  goes hunting for the slug in `TODO.md` finds nothing. It is also changelog
  prose — describing the work item that produced the code rather than what the
  code does. The rest of the docstring already stands on its own.
- Fix: Delete the "Backs the TODO(...) work:" clause; start the paragraph at
  "The public Bazel macro protects downstream consumers with seven
  misconfiguration conditions...".

## quality-2: third, truncated copy of the coupling message in the same file

- File: `tests/bazel_rules/rust_bzl_tests.bzl:127`
- Issue: The analysistest asserts
  `asserts.expect_failure(env, "protocol = True requires a non-empty protocol_module")`
  — a hand-written, prefix-and-period-stripped variant of `_COUPLING_MSG`
  defined at line 23 of the same file.
- Consequence: Copy-paste with slight variation. The file now holds two
  subtly different spellings of the same consumer-facing message; an
  intentional rewording must be updated in two places in this file, and the
  truncated variant invites drift (someone updates `_COUPLING_MSG` to match a
  production change, the analysistest substring silently keeps asserting the
  old fragment — or worse, a *partial* rewording keeps the substring matching
  while the exact-string unit test is the only thing catching the delta,
  weakening the end-to-end pin).
- Fix: `asserts.expect_failure(env, _COUPLING_MSG)`. skylib's
  `expect_failure` is a substring match, and the analysis-time `fail()`
  message contains the full string (same `_require_protocol_module` path), so
  the full constant matches; one owner for the message in the test file.

## quality-3: `_protocol_module_violation` docstring misstates the wrapping structure

- File: `rust.bzl:39-40`
- Issue: "...the two callers wrap it in `if msg != None: fail(msg)`." Neither
  of the two production call sites (macro at `rust.bzl:644`, rule impl at
  `rust.bzl:181`) wraps anything — both call `_require_protocol_module`, which
  performs the wrap exactly once (`rust.bzl:46-50`).
- Consequence: A maintainer told there are two wrap sites will look for the
  second one, or — worse — replicate the wrap pattern at a new call site
  instead of calling the existing `_require_protocol_module` helper, eroding
  the "single check, cannot drift" property the same docstring advertises.
- Fix: Reword to match the code, e.g. "...lets the logic be unit-tested
  without triggering fail(); `_require_protocol_module` wraps it in
  `if msg != None: fail(msg)` for both production call sites."

## Checked and found fine (not findings)

- Asymmetry between the coupling guard (has a fail-firing `_require_*` wrapper)
  and the pure-Rust guard (inline `if msg != None: fail(msg)` in the macro):
  justified — the wrapper exists because the coupling check has two call
  sites; the pure-Rust check has one.
- `_PURE_RUST_MSG_TMPL` / `_COUPLING_MSG` duplicating the production strings in
  the test file: intentional golden-string pinning — that duplication is the
  test's entire point (a production edit must trip a test).
- `_defaults()` in the test duplicating the macro's default values: intentional
  pinning of the default surface, not derivable state worth sharing.
- Per-knob test rules spelled out rather than generated in a loop: forced by
  Bazel's export requirement and the inline comment says so.
- `dev_dependency = True` + the "rust.bzl must never load skylib" invariant is
  stated at the one place a violator would edit (`MODULE.bazel`); no stronger
  in-Bazel enforcement is available.
- Pre-existing `§2.5`-style design-doc references in `_generate_rust_srcs_impl`
  comments are outside this diff.
