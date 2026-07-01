# Deep error-handling review — workflow-bazel-protocol

Commit reviewed: 224344d844feeefa7acdb8f4eaa285322a70634d (base 3c244d1)
Scope: error observability and response in the changed Starlark (`rust.bzl`,
`BUILD.bazel`). Diff is Bazel/Starlark; there is no Rust/Python error-path code
in this diff.

General assessment: the misconfiguration handling in the changed code is strong.
The public `generate_rust_parser` macro fail-fasts on every *named* invalid knob
with a clear, attribute-naming message (rust.bzl:583-600), the `protocol` /
`protocol_module` cross-check is duplicated defensively at both the macro
(rust.bzl:583) and the internal rule's analysis time (rust.bzl:123-124), and the
empty-`stub_srcs` depset self-gates so no undeclared-file label is ever
referenced (rust.bzl:632-641). Expected-bad-input vs. invariant distinction is
clean: misconfig is rejected, not crashed-on. Two findings below, both minor.

---

## errhandling-1

File: rust.bzl:586-610 (pure-Rust `not python_extension` branch, `**kwargs`
forward to `_generate_rust_srcs`).

Broken error path: the branch fail-fasts on the six *named* python-only knobs
(`protocol_module`, `protocol`, `lib_rs`, `deps`, `crate_features`,
`recursion_limit`) with messages that name the offending attribute and point at
`python_extension`. But arbitrary extra keyword args land in `**kwargs` and are
forwarded straight to `_generate_rust_srcs(...)`. A consumer who passes a
Python-extension-only knob that is *not* one of the six named params — e.g. a
`rust_shared_library` passthrough like `rustc_flags = [...]` — in pure-Rust mode
does not hit the curated fail(). It reaches `_generate_rust_srcs`, which has no
such attribute, and Bazel raises its generic "no such attribute `rustc_flags` in
`_generate_rust_srcs` rule" error.

Why / where the error goes: the situation is still *reported* (Bazel errors, the
build stops — nothing is swallowed), but the report leaks the private
`_generate_rust_srcs` rule name and omits the `python_extension` guidance that
the sibling checks deliberately provide. The macro's own docstring markets
`_generate_rust_srcs` as "not loaded or instantiated directly by consumers"
(rust.bzl:301-302), yet a misconfiguration surfaces that internal symbol to the
consumer.

Consequence: a downstream author who fat-fingers an extension-only passthrough in
pure-Rust mode gets an error naming an undocumented internal rule instead of the
"only valid with python_extension = True" message the named-knob path gives. They
cannot tell from the message that `python_extension` is the lever; diagnosis
requires reading rust.bzl. Not a silent failure — a degraded error message on an
otherwise fail-fast path.

What must change: acceptable to leave as-is given `**kwargs` is intentionally
open-ended and cannot be enumerated; if tightened, note in the docstring that
unrecognized kwargs in pure-Rust mode fall through to the internal rule, or
document that only common Bazel attrs (`tags`, `visibility`, …) are expected
there. A code change is optional; the gap is message quality, not swallowing.

---

## errhandling-2

File: BUILD.bazel (`bootstrap_rust_srcs`, `bootstrap_native` smoke targets) plus
TODO.md:110 (`bazel-rust-smoke-bootstrap-regex`).

Broken reporting path: the design and the BUILD.bazel comment
(BUILD.bazel:new block) present `bootstrap_native` as the *active regression
guard* that would catch a re-introduction of the stub-dir naming bug by
materializing `bootstrap_native/cst.pyi` + `__init__.pyi` at build time. But the
grammar (`bootstrap.fltkg`) contains a block-comment regex outside the Rust
backend's portable subset, so `gen-rust-parser` fails at build time for BOTH
smoke targets. Because `bazel build //:bootstrap_native` requests the
`py_library` (→ cdylib → crate assembly → `parser.rs`), the failing parser action
aborts the whole target before the stub half is ever produced end-to-end. There
is also no `bazel build`/`bazel test` step in CI (`.github/workflows/ci.yml`
loads no bazel; the targets were only ever validated via `--nobuild` analysis).

Why / where the error goes: the guard that was supposed to *report* a stub-dir
regression cannot execute. A regression of the exact bug this change fixes would
therefore go unreported by any running check — only the analysis-time
`declare_file` name is exercised, not the actual materialization the design's
Test Plan claims (design.md §Test plan, "the stub package must materialize at
bootstrap_native/cst.pyi").

Consequence: a reviewer or on-call reading design/BUILD.bazel reasonably believes
stub-package emission is guarded by a green build. It is not; the guard is inert.
A future change that re-breaks the stub-dir naming (e.g. reverting the
`extension_name` → `out_subdir` coupling at rust.bzl:132) would pass all executing
checks silently.

Status: acknowledged and tracked in TODO.md:110 with a concrete remediation
(fix the Rust parser regex handling, or repoint the smoke targets at a
fully-compilable grammar). Primarily a test-coverage gap (test-reviewer lane);
flagged here only because it concerns whether an unexpected regression gets
*reported* — and currently it would not. No additional code change required
beyond the tracked TODO.
