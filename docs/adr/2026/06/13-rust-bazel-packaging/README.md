# ADR: Out-of-tree Bazel consumption of FLTK's Rust backend

- **Status:** Accepted
- **Date:** 2026-06-13
- **Slug:** `rust-bazel-packaging`

## Context

FLTK gained a Rust backend: `gen-rust-cst` / `gen-rust-parser` emit a `cst.rs`
and `parser.rs` that, together with a `#[pymodule]` crate root, compile into a
PyO3 cdylib exposing a generated parser + CST to Python. In-tree this is built
by maturin (`fltk._native`) and by hand-written fixture crates. Nothing proved
that an **out-of-tree** application could consume the Rust backend through its
own build system.

We needed an end-to-end proof using a representative real consumer — Clockwork
(`~/tps/clockwork`), which already consumes FLTK's pure-Python codegen path via
the `@fltk//:rules.bzl` `generate_parser` rule under Bazel. The target: from a
clean Clockwork checkout, a single Bazel invocation runs FLTK's Rust codegen
against `clockwork.fltkg`, compiles the generated sources into a PyO3 cdylib,
and a `bazel test` parses a Clockwork source string through the Rust parser and
reads node/label/span data back — with FLTK's own `fltk._native` importable in
the same interpreter.

The open questions were genuinely *how*, not *whether*:

- **How FLTK's Rust reaches the consumer** — build from source via the existing
  `@fltk` Bazel module (git-pinned), vs. a maturin/pip wheel, vs. publishing
  `fltk-cst-core` / `fltk-parser-core` to crates.io.
- **Where `rules_rust` lives** — FLTK owning the toolchain wiring and a turnkey
  macro, vs. each consumer declaring it.

Two hard runtime invariants constrain any answer:

1. **`fltk._native` must be importable** by the consumer cdylib. Generated
   `cst.rs` resolves the canonical `Span` type via
   `py.import("fltk._native").getattr("Span")` on first span use; absent it,
   generated code raises a typed `RuntimeError`.
2. **A single `fltk-cst-core` rlib (version + layout) across all cdylibs.** An
   ABI gate (`FLTK_CST_CORE_ABI`) requires `fltk._native` and the consumer
   cdylib to link the *same* `fltk-cst-core`, or cross-cdylib `Span` passing
   raises a typed error — never a silent wrong answer.

Per CLAUDE.md, the new Bazel rules/macros and the visibility of `fltk._native`
become **public FLTK API** the moment a consumer loads them, and get the same
compatibility care as generated symbols.

## Decision

### Build FLTK's Rust from source, inside the consumer's Bazel, via the `@fltk` module

Clockwork already pins FLTK as a Bazel module (`bazel_dep` + `git_override`) at
a single git commit. That one pin *is* the entire FLTK source tree, including
the core crates and `src/lib.rs`. Both `fltk._native` and the consumer cdylib
are compiled from that **same** checkout, so invariant #2 holds *by
construction*: both reference the identical `@fltk//crates/fltk-cst-core`
rlib, and a version/layout mismatch is not constructible without editing FLTK's
own tree.

**Rejected:**

- **Maturin/pip wheel for `fltk._native`.** A wheel ships the canonical
  extension but not the `fltk-cst-core` rlib the consumer must link its *own*
  cdylib against. The consumer would still need the core crates from source and
  would have to independently re-pin them to the wheel's exact version to
  satisfy the ABI gate — reintroducing the mismatch risk the source path
  eliminates for free, and adding a wheel build/publish step for no benefit.
- **Publishing `fltk-cst-core` / `fltk-parser-core` to crates.io.** Permitted
  and viable, but adds an external publish cadence and a second
  version-coordination surface (crates.io version vs. FLTK commit pin) without
  removing the need for the consumer to take FLTK's Starlark rules from the
  source dep. The source path needs zero external publishing and keeps a single
  version authority — the git commit. The crates stay unpublished; publishing
  remains a future option if a non-source consumer ever needs it.

### FLTK owns the rules and macros; the consumer owns toolchain registration

FLTK adds a `rules_rust` `bazel_dep`, owns its third-party Rust lockfile (a
`crates_repository` seeded from the root `Cargo.toml`/`Cargo.lock`, covering
the core crates + `fltk-native` and their pyo3/regex-automata graph; the spike
and `tests/*` workspace crates are excluded), and exposes new public Bazel
surface:

- **`@fltk//crates/fltk-cst-core`**, **`@fltk//crates/fltk-parser-core`** —
  public `rust_library` targets; the shared rlibs every consumer cdylib links.
- **`@fltk//:native`** + **`@fltk//:native_py`** — the `fltk._native` cdylib
  (built with both `extension-module` *and* `python` crate features) and a
  `py_library` that re-homes the produced `.so` to `fltk/_native.abi3.so` on
  the import path. This closes the long-standing gap where FLTK's `py_library`
  globbed `**/*.py` only, leaving Bazel consumers silently on the pure-Python
  `Span` fallback. The existing pure-Python `py_library(name = "fltk")` is
  untouched; the native path is additive and opt-in.
- **`@fltk//:rust.bzl`** with two public symbols, kept separate from
  `rules.bzl` so a pure-Python consumer never forces `rules_rust` to resolve:
  - **`generate_rust_parser`** — a rule running two codegen actions
    (`gen-rust-cst`, `gen-rust-parser`), declaring `cst.rs` + `parser.rs` as
    action outputs. (The Rust subcommands take positional output files and have
    no shared `--output-dir`, so this is a loose analog of `generate_parser`,
    not a literal one.)
  - **`fltk_pyo3_cdylib`** — a macro that assembles the generated `cst.rs` /
    `parser.rs` plus a consumer-authored `lib.rs` into a single synthesized
    crate directory (so the bare `mod cst;` / `mod parser;` resolve on Bazel
    action outputs), compiles a `rust_shared_library` with `extension-module`
    + `python` linking the core crates, renames the output to the
    `<name>.abi3.so` basename maturin would produce, and wraps it in a
    `py_library` carrying `@fltk//:native_py` as a `data` dep.

The **consumer** adds the matching `rules_rust` `bazel_dep` and — because
toolchain registration is driven by the root module — calls
`rust.toolchain(...)` itself (download-prebuilt, Linux x86_64; Windows out of
scope). FLTK's `bazel_dep` alone is deliberately insufficient: a missing
consumer toolchain registration is a loud build error, not a silent fallback.

The end-to-end consumer graph is: `generate_rust_parser` →
`fltk_pyo3_cdylib(lib_rs = <consumer #[pymodule]>)` → a `py_test` that imports
the cdylib and exercises one round-trip parse.

### Build-fix decisions surfaced by the first real Bazel run

The design above was first implemented and reviewed on code-reading alone, then
a real `bazel test` surfaced defects review had missed. The load-bearing ones:

- **Generalized fully-qualified pyo3 references in generated Rust.** A grammar
  rule named `list`, `tuple`, `type`, or `module` derives a handle struct
  (`PyList`, `PyTuple`, …) that collides with the pyo3 prelude/types names the
  generated `cst.rs` imported unqualified — `clockwork.fltkg` has both `list`
  and `module` rules, so this blocked the build. Resolution: emit
  fully-qualified `pyo3::types::PyList::…` references (and qualified
  `register_classes` signatures) so common rule names stay legal, backstopped
  by the existing reserved-name diagnostic. This is generated-public-API
  robustness, not a two-name patch: the namespace a consumer's grammar may use
  must be maximal and must never silently miscompile. (Burndown of the
  remaining unqualified prelude surface is tracked — see Deferred work.)
- **`recursion_limit` is the macro's / crate-root's concern, not the
  consumer's.** Deeply recursive grammars exceed rustc's default trait-solver
  recursion limit (128) when PyO3's `#[pyclass]` evaluates `Send + Sync`
  bounds across the recursive child chain, producing an `E0275` with no hint
  that `#![recursion_limit]` is the fix. A `#![recursion_limit = "512"]` is
  required; ownership belongs at crate-root assembly, not buried in every
  consumer's hand-authored `lib.rs`.

(Smaller real-toolchain corrections were also made: `@fltk//:native` needs the
`python` crate feature explicitly because Bazel does not forward Cargo features;
Starlark forbids implicit string concatenation in `rust.bzl`; the round-trip
test keys on the *fallback* module name because PyO3 0.29 reports a bare
`#[pyclass]`'s `__module__` as `"builtins"`.)

## Consequences

**Downstream consumers must:**

- Declare the `rules_rust` `bazel_dep` and register the Rust toolchain in their
  **root** `MODULE.bazel` (FLTK cannot do this for them).
- Use `generate_rust_parser` + `fltk_pyo3_cdylib` from `@fltk//:rust.bzl`
  rather than raw `rust_*` rules — FLTK owns the feature flags, core-crate
  links, and crate-source assembly a correct cdylib needs.
- Author a small `lib.rs` with the `#[pymodule]` entry point whose function
  name equals the cdylib `name` and the importable module name.
- Depend (transitively, via the macro's wrapper) on `@fltk//:native_py` so
  `fltk._native` is on the test's Python path and the Rust `Span` path is live.
- Accept that their Bazel build now compiles Rust (pyo3, regex-automata, the
  FLTK core crates) from source — a baseline cost, mitigated by Bazel caching.
  A consumer that links its own native Rust touching `Span` types must link the
  same `@fltk//crates/fltk-cst-core` target.

**New public FLTK Bazel surface** (subject to the same compatibility care as
generated symbols): the `@fltk//crates/fltk-cst-core` /
`@fltk//crates/fltk-parser-core` rust_library targets, `@fltk//:native` /
`@fltk//:native_py`, and `@fltk//:rust.bzl`'s `generate_rust_parser` rule and
`fltk_pyo3_cdylib` macro. The pre-existing pure-Python `generate_parser` path
is unchanged and is not forced to resolve `rules_rust`.

## Status / deferred work

**Proven GREEN.** A clean Clockwork checkout runs FLTK's Rust codegen,
builds the cdylib, and `bazel test //clockwork/dsl:clockwork_rust_roundtrip_test`
passes (1/1); the FLTK-side smoke target builds; FLTK's own `make check` gate
and gencode-drift check are clean.

**Deferred:**

- **Pin finalization — `TODO(fltk-pin-finalize)`.** The GREEN run used a
  temporary `local_path_override` in Clockwork's `MODULE.bazel` pointing at the
  local FLTK checkout. Finalization requires pushing the FLTK Rust-Bazel commits
  to the remote `git_override` fetches from, reverting the override back to the
  `git_override` pin at the pushed HEAD, re-verifying against the real fetch
  path, and dropping the TODO.
- **FLTK should generate the cdylib crate root / `#[pymodule]` entry point.**
  Today the crate root is hand-written everywhere — FLTK's own `_native`, the
  in-tree fixtures, and every consumer (Clockwork's `clockwork_native_lib.rs`).
  Its structural content (the `use`s, `mod cst;` / `mod parser;`, the
  `#[pymodule]` wiring, and the `recursion_limit`) is fully determined by the
  module name and the two generated submodules. Generating it — or having
  `fltk_pyo3_cdylib` synthesize it from `name` with an optional hook for
  consumer-owned native Rust — would eliminate the hand-authoring and move the
  `recursion_limit` ownership into FLTK, but is out of scope for this POC and
  remains an open design question.
- Robustness burndown of the pyo3 name-collision fix
  (`TODO(rust-pyany-qualify)`: de-glob the `pyo3::prelude::*` import so the full
  collision surface — including non-`Py`-prefixed prelude re-exports vs. the
  bare data struct — is mechanically checkable, and recover `any` as a legal
  rule name) and the optional `recursion_limit` macro attribute
  (`TODO(rust-recursion-limit-macro)`).
