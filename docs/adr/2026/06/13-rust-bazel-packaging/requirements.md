# Requirements: Prove Clockwork can consume FLTK+Rust under Bazel

## Goals

Prove, end-to-end and inside Bazel, that a representative out-of-tree consumer
(Clockwork) can pull in FLTK, generate a **Rust** parser + CST classes with
PyO3/Python bindings for `clockwork.fltkg`, and successfully use those bindings
from Clockwork's Python code under `bazel test`. The deliverable is a working
integration plus the FLTK-side surface required to support it. *How* the Rust
artifacts reach the consumer (build-from-source-in-Bazel vs. wheel/pip
packaging, where `rules_rust` is registered) is a **design** decision to be
resolved downstream — these requirements state what must work, not which
packaging path is chosen.

Assumed motivation (not a downside to weigh): a consumer like Clockwork adopts
the FLTK Rust backend in part because it wants to start writing **its own
native Rust code** alongside the generated PyO3 bindings. The integration
should not preclude that.

## In scope

- A reproducible Bazel build in the Clockwork repo (`~/tps/clockwork`) that:
  - obtains FLTK (the packaging/dependency mechanism is a design choice),
  - runs FLTK's Rust codegen on `clockwork/dsl/clockwork.fltkg`,
  - compiles the generated `cst.rs` + `parser.rs` (plus a consumer `lib.rs`
    wiring `#[pymodule]`) into a PyO3 cdylib,
  - makes both that cdylib and FLTK's own `fltk._native` extension importable,
  - and exercises the bindings from Python under `bazel test`.
- Any FLTK-side changes required to support the above: a Bazel-visible way to
  run FLTK's Rust codegen (the existing `gen-rust-cst` / `gen-rust-parser` CLI
  subcommands) and to build the resulting sources into an importable PyO3
  cdylib; `rules_rust` wiring reachable from the Bazel build;
  packaging/visibility of `fltk._native`; and exposure of the `fltk-cst-core` /
  `fltk-parser-core` crates as Bazel-buildable artifacts. The concrete shape
  (number of rules, macro names, intermediate file names) is the designer's
  choice — see "Implementation notes (non-normative)".
- A written decision record (ADR) capturing whatever packaging/dependency
  mechanism and `rules_rust` placement the design ultimately lands on. (The
  *choice* is the designer's; this only requires that the chosen path be
  recorded.)

Note on scope of the FLTK-side work: the FLTK changes here are not throwaway
POC scaffolding — they are genuine FLTK product/feature work (new Bazel rules
and macros, `rules_rust` wiring, and packaging `fltk._native` as a
Bazel-visible artifact). Per CLAUDE.md, FLTK's generated artifacts are public
API for out-of-tree consumers; the new Bazel surface (rule/macro names,
visibility) likewise becomes public API the moment a consumer loads it.
Approving this work approves shipping that new public FLTK Bazel surface, which
must get the same compatibility care CLAUDE.md demands of generated symbols.

## Out of scope

- Migrating Clockwork's application code to *use* the Rust parser in production
  (e.g. swapping `clockwork_parser` consumers from Python backend to Rust). The
  POC proves the bindings work in context; it does not rewire Clockwork's
  compiler. The existing Python-backend path (`clockwork_cst.py`,
  `clockwork_parser.py`) may remain Clockwork's production path.
- Performance tuning / release-build benchmarking of the Rust parser.
- Publishing FLTK crates to crates.io or wheels to PyPI as a *requirement*
  (may be selected as the mechanism — see open questions — but is not mandated).
- Windows / non-Linux platform support.
- Changing the generated public API surface (class names, accessors, type
  annotations). Per CLAUDE.md these are downstream-consumed public API; this
  work must not force annotation/call-site churn.
- The pure-Python Bazel path FLTK already ships (`generate_parser` rule →
  `clockwork_cst.py` etc.) is not removed or broken by this work.

## System behavior (acceptance criteria)

Concrete, observable outcomes that define "done":

1. **Codegen under Bazel.** From a clean checkout of Clockwork, a single Bazel
   invocation (e.g. `bazel build //...` over the new targets) runs FLTK's Rust
   codegen against `clockwork.fltkg` and produces the generated Rust CST and
   parser sources as Bazel action outputs (not checked in).

2. **cdylib builds under Bazel.** Bazel compiles the generated sources into a
   PyO3 cdylib, with the `extension-module` / `python` features enabled, linking
   the **same** `fltk-cst-core` rlib version that `fltk._native` was built
   against (cross-cdylib ABI gate — see Constraints).

3. **Bindings import and the Rust span path is exercised.** Under Bazel, Python
   can `import` the generated cdylib's module and FLTK's `fltk._native` module in
   the same interpreter, and the canonical `fltk._native.Span` is resolved
   through the native (Rust) path rather than the pure-Python span fallback —
   i.e. the Rust path is actually wired up, not silently replaced by the
   fallback. (Diagnostic hints, not pass/fail gates: today the fallback emits a
   `warnings.warn` from `fltk/fegen/pyrt/span.py`, and a missing/mismatched
   `fltk._native` raises `RuntimeError: cross-cdylib Span type lookup failed
   (fltk._native.Span)`.)

4. **Bindings produce a result — round-trip parse.** A `py_test` (or equivalent
   Bazel test) parses at least one representative Clockwork source string through
   the generated Rust parser, obtains a CST, and reads node/label/span data
   through the generated accessors **without error**. This test **passes** under
   `bazel test`. The bar is only that the packaged, Bazel-built Rust parser +
   PyO3 bindings, invoked in context, produce *some* parse result/output at all —
   it is **not** a test that FLTK parses correctly and is **not** a Rust-vs-Python
   equivalence test. Correctness of FLTK's parsing is out of scope here; this work
   tests packaging and integration, not parser correctness.

5. **Pure-Python path intact.** Clockwork's existing `generate_parser`-based
   Python targets still build and their existing tests still pass — the Rust
   integration is additive.

## User-visible surface

This work's user-visible surface is **build configuration**, not new runtime
API. Specifically:

- **Clockwork `MODULE.bazel`**: how FLTK is declared as a Bazel module (the
  existing `bazel_dep` + `git_override` tuple at line 34, resolving `@fltk`, or a
  replacement mechanism) and whether `rules_rust` is added here.
- **Clockwork `BUILD.bazel` files**: new target(s) for Rust codegen, the cdylib,
  and the test. Existing `load("@fltk//:rules.bzl", ...)` usage is preserved.
- **FLTK `MODULE.bazel` / `BUILD.bazel` / `rules.bzl`**: a new `rules_rust`
  dependency, new Starlark rule(s)/macro(s) for Rust codegen and cdylib
  building, and packaging of `fltk._native` + the core crates as Bazel-visible
  artifacts. The number, names, and shape of these rules/macros are the
  designer's choice (see "Implementation notes (non-normative)").
- **No change** to generated CST/parser public symbols, accessor method names,
  type annotations, or the `fltk._native` Python import path. Generated Rust
  module name still must equal the `[lib] name` / `#[pymodule]` name / maturin
  `module-name` (the existing constraint).
- The existing `genparser` subcommand surface (`generate`, `gen-rust-cst`,
  `gen-rust-parser`) is reused as-is unless a gap is found; any new CLI flag is
  an open question, not assumed.

## Protocols / constraints (pinned)

These are invariants the integration must satisfy (from FLTK exploration):

- **`fltk._native` must be importable at runtime** by the consumer cdylib.
  Generated `cst.rs` resolves the canonical `Span` type via
  `py.import("fltk._native").getattr("Span")` on first span use. The Bazel
  packaging must make `fltk._native.abi3.so` present on the Python path of the
  test — today FLTK's `py_library` globs `**/*.py` only and the `.so` is **not**
  a declared output/data dep, so Bazel consumers silently get the pure-Python
  fallback. Fixing this is in scope.

- **Single `fltk-cst-core` rlib version across all cdylibs.** The ABI gate
  `FLTK_CST_CORE_ABI = "fltk-cst-core/<CARGO_PKG_VERSION>"` requires
  `fltk._native` and the consumer cdylib to link the *same* `fltk-cst-core`.
  Under Bazel this means both must reference the same rlib artifact / version
  pin — a hard constraint on how the two cdylibs are built. The ABI guard must
  remain effective across the Bazel-built artifacts: a mismatch must surface as
  the existing typed error, never a silent wrong answer. The chosen build
  mechanism should make the matched-version case the default (mechanism (A)
  makes a mismatch effectively unproducible). This is an invariant to preserve,
  not a separately-tested acceptance gate — constructing a deliberate mismatch
  is out of scope for the POC.

- **`extension-module` feature required** for Python-imported cdylibs;
  `fltk-cst-core` consumed with `default-features = false` + a forwarding
  `python` feature (the established consumer pattern).

- **`fltk-parser-core` re-exports `regex_automata`**; consumer needs no direct
  `regex-automata` dep. Generated `parser.rs` uses
  `fltk_parser_core::regex_automata::meta::Regex`.

- **Regex subset (assumption, not a gate):** FLTK's Rust codegen targets the
  `regex-automata`-compatible subset (no lookahead/lookbehind/backreferences).
  This work *assumes* `clockwork.fltkg` is already within that subset. Whether
  it is is incidental to the packaging/integration goal: if the grammar turns
  out to need adjustment, that is a separate, out-of-scope effort (either edit
  `clockwork.fltkg` or extend FLTK's regex support) — it does not change these
  requirements and is not a pass/fail gate for the integration.

- **PyO3 `abi3-py310`**: cdylib is ABI3, CPython 3.10+. Clockwork's Bazel
  CPython toolchain is 3.10-compatible (`rules_python` present).

- **Toolchain (baseline given):** a Rust toolchain must be available to the
  Bazel build. Today neither FLTK nor Clockwork registers `rules_rust`; this work
  adds it. This is required on every packaging path, so it is not a factor that
  distinguishes one path from another (*where* the toolchain is registered is a
  design detail — see Open questions).

- **Separate Cargo workspace topologies**: FLTK's test crates declare their own
  `[workspace]` and are excluded from the root workspace. A Bazel integration
  must not assume a single workspace/`Cargo.lock`. (Bazel typically builds
  per-crate rather than via Cargo workspaces, but crate dependency resolution
  must account for this.)

## Open questions

The packaging/dependency-mechanism and `rules_rust`-placement decisions are
**design** questions, not requirements — they are deliberately *not* forced
here. They are recorded below only to scope the design space the designer
inherits, not as decisions the user must ratify before design begins.

### Design space (not a requirement to decide up front): how FLTK+Rust reaches the consumer

The requirements above must hold regardless of which packaging path the
designer picks. The space the designer chooses within:

- **Build Rust from source in Bazel** via the existing Bazel-module source dep
  (`@fltk//...` resolved by `git_override`; exploration-clockwork §1,
  `MODULE.bazel:34`, `:89–98`). A single version-pin (the git commit) then
  governs both `fltk._native` and the consumer cdylib, which directly satisfies
  the same-`fltk-cst-core`-version ABI constraint.
- **Wheel/pip packaging.** FLTK publishes (or Clockwork vendors) a maturin wheel
  for `fltk._native`; the consumer still needs a way to build its **own** cdylib
  from generated `cst.rs`/`parser.rs` linking the matching `fltk-cst-core`, so
  this path also has to answer how the core rlibs are obtained and how the
  ABI-version pin stays matched.

Note: *every* path requires Clockwork's Bazel build to be able to build Rust —
that is a baseline given, not a differentiator. (Indeed, a primary reason a
consumer adopts the Rust backend is to write its own native Rust too.) So "needs
a Rust toolchain / `rules_rust`" is true universally and should not be weighed
against any option. What differs between paths is only *where* the core rlibs
come from and how the ABI-version pin is kept matched — that is the design
question.

Related sub-points the design will need to settle (all design, none gating
requirements):

- **`rules_rust` placement.** FLTK owning the `rules_rust` wiring + a cdylib
  macro (so consumers get a turnkey "generate + build cdylib" path, matching the
  existing `rules.bzl::generate_parser` pattern) vs. Clockwork declaring it
  itself vs. both. Whichever is chosen becomes public FLTK Bazel surface (see
  Goals / In scope note).
- **Core-crate distribution.** `fltk-cst-core` / `fltk-parser-core` are
  `license = "MIT"` and are **not currently published to crates.io**. Publishing
  them to crates.io is a fully available design option — if the designer judges
  it the cleanest/most expedient path, FLTK will publish them, and a Bazel
  consumer can then obtain them via `crates_repository`. Equally, if source-only
  is preferred, a Bazel consumer obtains them via the FLTK source dep. Neither is
  mandated and "not yet published" is **not** a constraint or blocker — it is one
  of the design alternatives.
- **Rust toolchain registration.** Where the `rules_rust` toolchain is
  registered (download-prebuilt vs host rustup) and which CI platforms it must
  cover. Clockwork's CI does not build Rust today; adding a Rust toolchain to
  its Bazel build is part of the baseline given above.

## Implementation notes (non-normative)

These are the designer's choice, not requirements — recorded here only to sketch
a likely shape and to ground the exploration's findings. The designer is free to
deviate (e.g. one combined rule vs. separate rules, different macro shapes,
different intermediate file names).

- FLTK already exposes the codegen via `genparser` CLI subcommands
  (`generate`, `gen-rust-cst`, `gen-rust-parser` — genparser.py:120/265/368),
  reused as-is unless a gap is found. The Rust codegen emits a CST source file
  (`cst.rs` in the existing fixtures) and a parser source file (`parser.rs`).
- A likely shape on the FLTK side: a Starlark rule wrapping the Rust codegen
  (analogous to the existing `rules.bzl::generate_parser`) plus a macro that
  compiles generated sources + a consumer `lib.rs` (wiring `#[pymodule]`,
  `register_submodule`) into a PyO3 cdylib. Names such as
  `generate_rust_parser` / `fltk_pyo3_cdylib` are illustrative only.
- Generated module name must equal `[lib] name` / `#[pymodule]` name / maturin
  `module-name` (a real, load-bearing constraint — see User-visible surface).
