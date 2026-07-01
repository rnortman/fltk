# Judge verdict — deep review

Phase: deep. Base 3c244d1..HEAD 9aac952. Round 1.
Notes: 7 reviewer files (correctness / security / efficiency = no findings); 7 findings.
Ground truth: design.md (unify FLTK's Bazel parser-codegen surface).

## Added TODOs walk

### test-2 — TODO(bazel-neg-test-harness) at BUILD.bazel (near `bootstrap_native`)
Q1 (worth doing): yes — the six pure-Rust `fail()` misconfiguration guards plus the
`protocol` → `protocol_module` coupling are net-new this iteration and have no
reproducible automated test; a future edit could silently disable a guard. Worth an
eventual regression harness.
Q2 (design/owner input required): yes — remediation requires adding a `bazel_skylib`
`analysistest` dependency to `MODULE.bazel` (a new third-party build dependency, a
genuine dependency/infrastructure decision, not an incidental respond-mode patch) and
building a negative-target harness. The reviewer's own suggestion (commit
intentionally-failing targets) is correctly rejected by the responder: such targets
break `bazel build //...` wildcard builds, so the analysistest route — able to assert
analysis failure without a failing target in the graph — is the only sound vehicle, and
it does not exist yet.
Design-sanction: the design's Test plan explicitly pre-accepted this deferral — "If no
harness exists, these are documented as manual `bazel build` expectations rather than
automated tests" (design.md §Test plan). The guards were also re-verified live this
round (two exercised, four eyeballed as identical `if cond: fail(...)` shape;
implementation-log "Misconfiguration coverage").
Iteration-created check: the untested guards were created this iteration, so the "cannot
be silently deferred" clause applies — but it is satisfied: the gap is surfaced in both
TODO.md and a `TODO(bazel-neg-test-harness)` BUILD.bazel comment, and the underlying
guards work (verified). It is not silent, and it is design-sanctioned.
TODO hygiene: slug present in both TODO.md and the BUILD.bazel comment; the now-resolved
`bazel-rust-smoke-bootstrap-regex` TODO was removed from TODO.md (no orphan).
Assessment: YES to both → TODO acceptable. Single TODO this phase, not a pile.

## Other findings walk

### errhandling-1 — Fixed (docstring)
Claim: in pure-Rust mode, an unrecognized `**kwargs` (e.g. `rustc_flags`) is forwarded to
the private `_generate_rust_srcs` rule and surfaces a generic Bazel "no such attribute"
error naming the internal rule instead of the curated `python_extension` guidance.
Consequence: degraded error message on an otherwise fail-fast path (nothing swallowed).
Reviewer rated the code change optional and recommended a docstring note.
Diff at rust.bzl `**kwargs` doc: the docstring now states that in pure-Rust mode kwargs
forward to the internal rule and an unrecognized attr surfaces the generic Bazel error
naming that internal rule rather than the `python_extension` guidance.
Assessment: this is exactly the reviewer's recommended remediation; `**kwargs` is
intentionally open-ended and cannot be enumerated. Accept.

### errhandling-2 — Fixed
Claim: `bootstrap_native` was advertised as the live stub-dir regression guard but
`bootstrap.fltkg`'s block-comment regex is outside the Rust portable subset, so
`gen-rust-parser` aborts the whole target before the stub half is produced — guard inert.
Consequence: a re-break of the stub-dir naming bug would go unreported.
Verification (this round, live): repointed both smoke targets to
`fltk/fegen/test_data/rust_parser_fixture.fltkg` (proven Rust-compilable — used in
`test_gsm2lib_rs.py` for cst/parser/unparser). Ran `bazel build //:bootstrap_rust_srcs
//:bootstrap_native` → EXIT 0. `bazel-bin/bootstrap_native/cst.pyi` + `__init__.pyi` +
`cst_protocol.py` materialize; `bazel-bin/bootstrap_native.abi3.so` present.
Assessment: the guard is now live and executes on a standard build. Accept.

### test-1 — Fixed
Claim: the new macro's `python_extension = True` branch (crate assembly → cdylib → abi3
→ `py_library`, `rust_srcs`/`stub_srcs` output-group routing) had never been exercised by
a successful full build; comments overstated verification.
Consequence: a regression in the new branch would not be caught by the smoke target.
Verification (live): the successful `bazel build //:bootstrap_native` above exercises the
full path. `bazel-bin/bootstrap_native_crate_root/` contains exactly
`lib.rs`/`cst.rs`/`parser.rs` — no `.pyi`/`.py` leak into the crate root, confirming the
`rust_srcs`-only feed the design specifies (design.md §"Stub/protocol files must not
reach crate assembly"). Comments updated to state the grammar is fully Rust-compilable.
Assessment: the actual new logic is now built and its non-obvious property (name
coexistence, clean crate root) confirmed. Accept.

### reuse-1 — Fixed
Claim: the `protocol && !protocol_module` check was hand-copied verbatim into both the
macro body and `_generate_rust_srcs_impl`; the two copies can drift.
Diff: `_require_protocol_module(protocol, protocol_module)` extracted (single condition +
message); called from `_generate_rust_srcs_impl` (rust.bzl ~140) and the macro (rust.bzl
~594). Verbatim copies removed.
Assessment: one owner; message text is now single-sourced. Accept.

### quality-1 — Fixed
Claim: the `512` default was the source of truth in three sites (two signatures + the
`!= 512` guard); raising the default while missing the guard makes it misfire.
Diff: module-level `_DEFAULT_RECURSION_LIMIT = 512` hoisted; both `_build_pyo3_cdylib`
and `generate_rust_parser` signature defaults reference it, and the guard is now
`recursion_limit != _DEFAULT_RECURSION_LIMIT`. The guard tracks the default.
Assessment: single owner across all three sites. Accept.

### quality-2 — Fixed
Claim: six near-identical `fail()` guards; each new python-only knob needs another
hand-written line and message drift is possible.
Diff: replaced with a `python_only_knobs` list of `(attr_name, is_set)` pairs looped over
one shared template `"generate_rust_parser: {} is only valid with python_extension =
True.".format(attr_name)`. Default-sentinel cases (`lib_rs != None`,
`recursion_limit != _DEFAULT_RECURSION_LIMIT`) normalized to booleans alongside the
truthy ones. Per-attribute messages remain byte-identical to before.
Assessment: adding a knob is now one tuple; messages single-sourced. Accept.

## Approved

7 findings: 6 Fixed verified (errhandling-1 docstring, errhandling-2 + test-1 live build
confirmed, reuse-1, quality-1, quality-2), 1 TODO acceptable (test-2 —
`bazel-neg-test-harness`, design-sanctioned deferral, requires a new `bazel_skylib`
build dependency + harness).

---

## Verdict: APPROVED

All dispositions acceptable. The two load-bearing "Fixed" claims (errhandling-2 / test-1)
were confirmed by an actual `bazel build` of both smoke targets end-to-end, with the stub
package materializing and a clean crate root. The single TODO passes both rubric
questions and is surfaced (not silently deferred). Round 1.
