# Deep quality review — unify FLTK's Bazel parser-codegen surface

Commit reviewed: 224344d (base 3c244d1)

## quality-1: `recursion_limit` default `512` is a magic constant duplicated across three sites

- `rust.bzl:530` — `generate_rust_parser(..., recursion_limit = 512, ...)` (macro signature default)
- `rust.bzl:599` — `if recursion_limit != 512:` (pure-Rust misconfiguration guard)
- `rust.bzl:323` — `_build_pyo3_cdylib(..., recursion_limit = 512, ...)` (helper signature default)

The guard at line 599 encodes the intent "was `recursion_limit` left at its
default?" but does so by comparing against a hardcoded literal rather than
against the actual default. The literal `512` is now the source of truth in
three independent places that must stay in lockstep.

**Consequence.** If a future owner raises the default (e.g. the E0275 overflow
mentioned in the `_build_pyo3_cdylib` docstring forces a higher limit) and edits
one or two signatures but not the `!= 512` guard, the guard silently misfires:
either it rejects the *new* default as a "misconfiguration" in pure-Rust mode,
or (if only the guard is left stale) it lets a knob-that-does-nothing slip
through. Nothing links the three occurrences, so the breakage is invisible until
a confusing `fail()` at a call site. This is exactly the kind of derived-value
duplication that rots over time.

**Fix.** Hoist a module-level `_DEFAULT_RECURSION_LIMIT = 512` and use it for
both signature defaults and the guard (`if recursion_limit != _DEFAULT_RECURSION_LIMIT`).
One owner; the guard tracks the default automatically.

## quality-2: Six near-identical `fail()` guards — copy-paste with slight variation

`rust.bzl:586-600` — the pure-Rust misconfiguration block is six copies of the
same shape, differing only in the predicate and the attribute name spliced into
an otherwise identical message template
(`"generate_rust_parser: X is only valid with python_extension = True."`):

```
if protocol_module: fail("... protocol_module ...")
if protocol:        fail("... protocol ...")
if lib_rs != None:  fail("... lib_rs ...")
if deps:            fail("... deps ...")
if crate_features:  fail("... crate_features ...")
if recursion_limit != 512: fail("... recursion_limit ...")
```

**Consequence.** Every python-extension-only knob added to the macro in future
requires remembering to hand-write another guard line, and any wording change to
the shared message must be applied six times. The template string is duplicated,
so the message can drift between attributes. Adds linear maintenance cost to a
list that will grow as the macro grows.

**Fix.** Drive the truthiness-predicate cases from a single
`[(protocol_module, "protocol_module"), (protocol, "protocol"), (deps, "deps"),
(crate_features, "crate_features")]` list looped once with a shared message
template. The two default-sentinel cases (`lib_rs != None`,
`recursion_limit != _DEFAULT_RECURSION_LIMIT`) can be normalized into the same
list by comparing each value against its default, unifying all six. (Predicates
are mildly heterogeneous today, which is the only thing that makes the current
copy-paste tempting — normalizing on "not equal to default" removes that.)

## Note (not a finding, out of lane): expected-to-fail smoke target

`BUILD.bazel` points both `bootstrap_rust_srcs` and `bootstrap_native` at
`bootstrap.fltkg`, whose block-comment regex is outside the Rust portable
subset, so a full `bazel build //:bootstrap_native` fails at `gen-rust-parser`
(per implementation-log.md and `TODO(bazel-rust-smoke-bootstrap-regex)`). The
design's stated value — an *actively built* regression guard for the stub-dir
bug — is only reachable by building the internal `//:bootstrap_native_stub_srcs`
filegroup subtarget by hand, not by any standard CI target. This is documented
via TODO + TODO.md entry, so it clears the workaround bar; flagging only so
scope/test reviewers can judge whether the guard's automation gap matters.
