# Design: Clockwork consumes FLTK + Rust under Bazel

Status: Draft. Decision date 2026-06-13.

Scope and acceptance criteria: see
[`requirements.md`](./requirements.md). Grounding facts: see
[`exploration-fltk.md`](./exploration-fltk.md) and
[`exploration-clockwork.md`](./exploration-clockwork.md). This document does not
restate them; it cites them.

---

## 1. Root cause / context

Today Clockwork consumes FLTK purely through the Python codegen path. The
`@fltk//:rules.bzl` `generate_parser` rule runs the `genparser generate` CLI and
emits `clockwork_cst.py` / `clockwork_parser.py` / `clockwork_trivia_parser.py`,
which are wrapped by `py_library` targets and consumed across Clockwork's
compiler (exploration-clockwork §3–§4). No Rust is involved on either side of
the Bazel boundary:

- FLTK's `MODULE.bazel` depends only on `rules_python`; `rules_rust` is absent,
  and `MODULE.bazel:5` carries `# TODO(bazel-rules-rust)` (exploration-fltk
  "Existing Bazel Surface"; exploration-clockwork §1, §5).
- FLTK's `py_library(name = "fltk")` globs `**/*.py` only. The compiled
  `fltk/_native.abi3.so` is **not** a declared output or `data` dep, so any
  Bazel consumer silently falls through to the pure-Python `Span` backend via
  the `try/except` in `fltk/fegen/pyrt/span.py` (exploration-fltk "Existing
  Bazel Surface" / "Python import path"; requirements Constraints).
- There is no Bazel rule for `gen-rust-cst` / `gen-rust-parser`, and no macro to
  compile the emitted `cst.rs` + `parser.rs` into a PyO3 cdylib.

The runtime contract the integration must honor (exploration-fltk "Invariants"):

1. **`fltk._native` must be importable** by the consumer cdylib. Generated
   `cst.rs` resolves the canonical `Span` type at first span use via
   `py.import("fltk._native").getattr("Span")` (`cross_cdylib.rs:349–366`).
   Absent it, generated code raises `RuntimeError: cross-cdylib Span type lookup
   failed (fltk._native.Span)`.
2. **One `fltk-cst-core` rlib (version + layout) across all cdylibs.** The ABI
   marker `FLTK_CST_CORE_ABI = "fltk-cst-core/" + CARGO_PKG_VERSION` plus the
   `_fltk_cst_core_abi_layout` size are checked by `check_abi_pair`
   (`cross_cdylib.rs:19`, `:158–233`). `fltk._native` and the Clockwork cdylib
   must link the **same** `fltk-cst-core`, or cross-cdylib `Span` passing raises
   a typed `TypeError` — never a silent wrong answer.
3. **`extension-module` feature** on every Python-imported cdylib;
   `fltk-cst-core` consumed `default-features = false` + a forwarding `python`
   feature (the pattern in `tests/rust_parser_fixture/Cargo.toml:14–16`).
4. **`fltk-parser-core` re-exports `regex_automata`**; the consumer needs no
   direct `regex-automata` dependency.
5. Generated module name must equal `[lib] name` == `#[pymodule]` fn name.

The crates `fltk-cst-core` (v0.2.0) and `fltk-parser-core` (v0.2.0) are
`license = "MIT"`, not published to crates.io; `fltk-native` is `publish =
false` (exploration-fltk Cargo section; Open Factual Questions §1).

---

## 2. Decision: packaging path

This section resolves the three deferred design questions. Each is a deliberate,
called-out decision per the requirements' "this becomes public FLTK Bazel
surface" note.

### 2.1 (a) How Clockwork's Bazel build obtains and builds FLTK's Rust

**Decision: build FLTK's Rust from source in Bazel, through the existing
`@fltk` Bazel-module source dependency.** No wheel, no crates.io publish.

Clockwork already pins FLTK as a Bazel module via `bazel_dep` + `git_override`
at a single commit (`MODULE.bazel:34`, `:89–98`, exploration-clockwork §1). That
one commit pin is the entire FLTK source tree — including `Cargo.toml`,
`crates/fltk-cst-core`, `crates/fltk-parser-core`, and `src/lib.rs`. Building
both `fltk._native` and the Clockwork cdylib from that **same** checkout makes
invariant #2 (single `fltk-cst-core` version) hold *by construction*: both
cdylibs reference the identical rlib target `@fltk//crates/fltk-cst-core`, so a
version/layout mismatch is not constructible without editing FLTK's own tree.
This is the property requirements call "(A) makes a mismatch effectively
unproducible."

Rejected alternatives:

- **Wheel/pip for `fltk._native`.** A maturin wheel gives Clockwork the
  canonical extension, but it does **not** give Clockwork the `fltk-cst-core`
  rlib it must link its *own* cdylib against. Clockwork would still need the
  core crates from source, and would then have to independently pin them to the
  exact version baked into the wheel to satisfy the ABI gate — reintroducing the
  mismatch risk that the source path eliminates for free. It also adds a wheel
  build/publish step to FLTK's release process for no benefit here.
- **Publish `fltk-cst-core`/`fltk-parser-core` to crates.io + `crates_repository`.**
  Viable and explicitly permitted, but it adds an external publish cadence and a
  second version-coordination surface (the crates.io version vs. the FLTK commit
  pin) without removing the need for Clockwork to also have FLTK's Starlark
  rules from the source dep. The source path needs zero external publishing and
  keeps a single version authority (the git commit). We therefore **do not**
  publish as part of this work; we leave the crates unpublished (their current
  state) and note publishing remains a future option if a non-Bazel/non-source
  consumer ever needs it.

Consequence: Clockwork's Bazel build gains a Rust toolchain and compiles
`fltk-cst-core`, `fltk-parser-core`, `fltk._native`, and the Clockwork cdylib on
first build. This is the baseline cost the requirements already accept ("every
path requires Clockwork's Bazel build to be able to build Rust"). Build time and
caching are addressed in §5.

### 2.2 (b) Where `rules_rust` lives; new FLTK Bazel surface

**Decision: FLTK owns the `rules_rust` wiring and exposes a turnkey codegen +
cdylib macro. Clockwork adds `rules_rust` to its own `MODULE.bazel` and
registers the Rust toolchain, but writes no raw `rust_*` rules — it calls FLTK's
macro.**

Rationale:

- `rules_rust` toolchain registration is a *module-level* concern. Under Bzlmod,
  a non-root module (FLTK) can `bazel_dep(name = "rules_rust")` and that
  dependency is visible to the build, but `register_toolchains` ordering favors
  the root module's registrations (the root's appear first in resolution order),
  so a toolchain registered only by a non-root module is easy for the root to
  shadow or omit. **This precedence behavior is an assumption to validate in the
  first implementation spike** (it is a Bzlmod nuance, not grounded in in-repo
  source) — but the conclusion is robust either way: the *root* module
  (Clockwork) drives `rust.toolchain(...)` through the `rules_rust` `rust`
  extension, so the toolchain Clockwork builds against is unambiguously the one
  Clockwork declares. Clockwork owns toolchain registration. (See §3.2 for the
  exact extension calls.)
- The **rules/macros** — the analog of `generate_parser` — belong in FLTK,
  matching the existing pattern where Clockwork does
  `load("@fltk//:rules.bzl", "generate_parser")` and supplies only grammar +
  names (exploration-clockwork §3). FLTK owns the knowledge of which features
  (`extension-module`, forwarding `python`), which core crates, and which
  `#[pymodule]` wiring a correct cdylib needs. Pushing that into Clockwork would
  duplicate FLTK-internal invariants into every consumer.

New public FLTK Bazel surface (names are this design's choice; load-bearing):

1. **`@fltk//crates/fltk-cst-core`** and **`@fltk//crates/fltk-parser-core`** —
   `rust_library` targets, `visibility = ["//visibility:public"]`. These are the
   shared rlibs every consumer cdylib links. `fltk-cst-core` is built with a
   `python`-feature-enabled configuration suitable for cdylib linking
   (`default-features = false` at the *consumer* edge; see crate-feature note in
   §3.1).
2. **`@fltk//:native`** — a `rust_shared_library` (or `py_cc`/pyo3 extension
   target) producing `fltk/_native.abi3.so` with `extension-module` enabled,
   plus a `py_library` (`@fltk//:native_py`) that carries the `.so` as `data` on
   the correct import path so `import fltk._native` resolves. This closes the
   "`.so` not a Bazel output" gap (invariant #1). The existing pure-Python
   `@fltk` `py_library` is **unchanged**; the native `.so` is layered in as an
   additive, opt-in `data` dep so the pure-Python path (requirements AC #5)
   stays intact.
3. **`@fltk//:rust.bzl`** — a new Starlark file exposing two public symbols:
   - **`generate_rust_parser`** — a rule (loose analog of `generate_parser`) that
     runs **two** codegen actions and declares `cst.rs` + `parser.rs` as action
     outputs (AC #1). Unlike `generate_parser` (which calls the single `generate`
     subcommand with `--output-dir`), the Rust subcommands take a **positional
     `output_file`** each and have **no `--output-dir`** (`genparser.py:265–297`,
     `:368–379`). So the rule runs `gen-rust-cst <grammar> <cst_out>` and
     `gen-rust-parser <grammar> <parser_out> --cst-mod-path <…>` as two separate
     actions with explicit per-file output paths. `--cst-mod-path` exists **only**
     on `gen-rust-parser`; `gen-rust-cst` has no such flag. The rule does **not**
     pass `--protocol-module`/`--pyi-output` (no `.pyi` emitted) — pyright
     type-checking of the cdylib surface is out of scope (requirements). See §3.4.
   - **`fltk_pyo3_cdylib`** — a macro that takes the generated `cst.rs` /
     `parser.rs` plus a consumer-supplied `lib.rs`, and emits the `rust_shared_library`
     (cdylib, `extension-module`) linking `@fltk//crates/fltk-cst-core` and
     `@fltk//crates/fltk-parser-core`, wrapped in a `py_library` that puts the
     resulting `.so` on the right import path and carries `@fltk//:native_py` as
     a runtime `data` dep (so `fltk._native` is importable wherever the consumer
     cdylib is). The macro is responsible for **assembling the crate source tree**
     so module resolution works on Bazel action outputs — see §3.4 (Crate-source
     assembly).

   We keep `rust.bzl` separate from the existing `rules.bzl` so that a
   pure-Python Bazel consumer that never loads `rust.bzl` does not transitively
   require `rules_rust` to be registered. (`load` of a `.bzl` that references
   `@rules_rust//...` providers forces the dep to resolve.)

### 2.3 (c) How the generated parser + pyo3 bindings build and load so a Clockwork test gets a parse result

End-to-end target graph in Clockwork (`clockwork/dsl/BUILD.bazel`, additive to
the existing targets):

```
generate_rust_parser(            # @fltk//:rust.bzl
    name = "clockwork_rs_srcs",
    src  = "clockwork.fltkg",
    # emits clockwork_rs_srcs/cst.rs, clockwork_rs_srcs/parser.rs
    cst_mod_path = "super::cst",
)

fltk_pyo3_cdylib(                # @fltk//:rust.bzl  (macro)
    name        = "clockwork_native",   # -> module clockwork_native
    cst_rs      = ":clockwork_rs_srcs",  # cst.rs
    parser_rs   = ":clockwork_rs_srcs",  # parser.rs
    lib_rs      = "clockwork_native_lib.rs",   # consumer-authored #[pymodule]
    # macro injects deps on @fltk//crates/fltk-cst-core, fltk-parser-core,
    # pyo3 (abi3-py310, extension-module), and data-deps @fltk//:native_py
)

py_test(
    name = "clockwork_rust_roundtrip_test",
    srcs = ["clockwork_rust_roundtrip_test.py"],
    deps = [":clockwork_native"],   # py_library wrapping the cdylib + fltk._native
)
```

`clockwork_native_lib.rs` is the small consumer-authored wiring file (the
pattern from `genparser gen-rust-cst` docstring and
`tests/rust_parser_fixture/src/lib.rs`):

```rust
use fltk_cst_core::register_submodule;
use pyo3::prelude::*;
mod cst;      // = generated cst.rs    (resolved via macro-assembled crate dir)
mod parser;   // = generated parser.rs (resolved via macro-assembled crate dir)

#[pymodule]
fn clockwork_native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    register_submodule(m, "cst", cst::register_classes)?;
    register_submodule(m, "parser", parser::register_classes)?;
    Ok(())
}
```

The bare `mod cst;` / `mod parser;` declarations resolve only because the macro
co-locates `lib.rs`, `cst.rs`, and `parser.rs` into a **single synthesized crate
directory** before compiling (see §3.4, Crate-source assembly). In the in-tree
fixture these three files are physically co-located in
`tests/rust_parser_fixture/src/`; under Bazel the generated `cst.rs`/`parser.rs`
are action outputs in a `bazel-out/.../bin/...` tree while `lib.rs` is a consumer
source file, so without the assembly step rustc would fail with "file not found
for module `cst`". The macro must close this gap; it is part of the public
`fltk_pyo3_cdylib` surface, not an implementation afterthought.

The `#[pymodule]` fn name (`clockwork_native`) equals the `[lib] name` the macro
sets and the importable module name (invariant #5). Because Clockwork *also*
wants its own native Rust (requirements Goals): the macro accepts an optional
`deps` passthrough and Clockwork may add further `mod` declarations / `rust_library`
deps to its `lib.rs` crate — the cdylib is an ordinary `rust_shared_library`, so
hand-written Rust coexists with the generated modules in the same crate or in
sibling `rust_library` targets the macro links.

The test (AC #4) parses one representative Clockwork source string through
`clockwork_native.parser` (entry method `apply__parse_module` — `clockwork.fltkg`'s
top rule is `module`, exploration-clockwork §2; the source string must be a valid
`module`, which takes some care for the 413-line grammar), obtains a CST, and
reads node/label/span data through the generated accessors — asserting only that
it produces *a* result without error (not correctness, not Python-equivalence). Because the test's `py_library`
dep transitively carries `@fltk//:native_py`, `import fltk._native` succeeds and
the canonical `Span` resolves through the Rust path (AC #3), not the
`warnings.warn` fallback.

---

## 3. Proposed approach — concrete changes

### 3.1 FLTK: Cargo / crate-feature shape (no source-behavior change)

No Rust *source* changes. The Bazel `rust_library` for `fltk-cst-core` is built
with the `python` feature on (it is `default = ["python"]` already), and the
consumer cdylib links it with the established `default-features = false` +
forwarding-`python` discipline expressed in Bazel `crate_features`. The macro
sets:

- consumer cdylib crate features: `["extension-module"]` →
  forwarding to `pyo3/extension-module` + `fltk-cst-core/python`. In Bazel,
  `rules_rust` `rust_shared_library(crate_features = [...])` plus the
  `@fltk//crates/fltk-cst-core` target built with `python` selected.
- `fltk-parser-core`: linked as-is (no pyo3, re-exports `regex_automata`).

Because Bazel builds per-crate (not via Cargo workspaces), the **first-party**
rlibs (`fltk-cst-core`, `fltk-parser-core`) do not rely on a Cargo workspace:
each `rust_library`/`rust_shared_library` target declares its own first-party deps
as explicit Bazel labels, so the separate `[workspace]` topologies of FLTK's test
crates (exploration-fltk Cargo section / constraint "Separate Cargo workspace
topologies") do not affect them.

The **third-party** deps (`pyo3`, `regex-automata`, and their transitive graph)
still need a lockfile, generated from *some* manifest. Decision (single
mechanism, no either/or): a `rules_rust` `crate` extension (`crates_repository`)
**owned by FLTK**, seeded from the **root `Cargo.toml` + `Cargo.lock`**, covering
exactly the crates the Bazel build links — `fltk-cst-core`, `fltk-parser-core`,
`fltk-native`, and their transitive pyo3/regex-automata graph. The
`fltk-cst-spike` crate and the `tests/*` fixture crates (which declare their own
`[workspace]`) are **excluded** from this lockfile; they are not Bazel build
inputs. See §3.2 for the extension wiring. (This supersedes any reading of an
inline-pins alternative.)

### 3.2 FLTK + Clockwork: `MODULE.bazel`

FLTK `MODULE.bazel` adds (replacing the `# TODO(bazel-rules-rust)` line):

```python
bazel_dep(name = "rules_rust", version = "<pinned>")  # version resolved at impl
```

Third-party Rust deps (`pyo3`, `regex-automata`, and their transitive graph) are
declared through the `rules_rust` `crate` extension with a checked-in
`Cargo.lock` that FLTK owns, seeded from the root `Cargo.toml`/`Cargo.lock` and
covering `fltk-cst-core`, `fltk-parser-core`, `fltk-native` (spike and `tests/*`
excluded — see §3.1). FLTK exposes those `@crates//:pyo3` etc. repos via
`use_repo`.

Note on cross-module visibility: extension-created repos (e.g. FLTK's `@crates`
hub) are module-private by default and are **not** automatically visible to
Clockwork. The `fltk_pyo3_cdylib` macro references those pyo3 deps as
**FLTK-internal labels** (the macro lives in `@fltk//:rust.bzl` and resolves them
relative to FLTK's own module), so Clockwork does **not** need a `use_repo` for
FLTK's `@crates` hub to build the generated cdylib. Clockwork only needs its own
`crate` hub when it writes its *own* native Rust with third-party deps — that is
O1.

Both FLTK and Clockwork declare `bazel_dep(name = "rules_rust", version = "…")`.
Under Bzlmod single-version resolution these **must be a compatible/identical
version**; the `<pinned>` placeholder is resolved once at implementation and used
in both module files (a version conflict between the two is a build error, not a
silent divergence).

Clockwork `MODULE.bazel` adds the same `bazel_dep(name = "rules_rust", ...)` (via
its `dependencies` list mechanism, `MODULE.bazel:16–70`) **and** the toolchain
registration that only the root module can drive:

```python
rust = use_extension("@rules_rust//rust:extensions.bzl", "rust")
rust.toolchain(edition = "2021", versions = ["<pinned rustc>"])
use_repo(rust, "rust_toolchains")
register_toolchains("@rust_toolchains//:all")
```

Toolchain mode: **download-prebuilt** (`rules_rust` default host-triple
download), not host `rustup`, so CI is hermetic and reproducible (AC #1 "from a
clean checkout"). Target platforms: Linux x86_64 (and aarch64 if Clockwork CI
runs it — the `clang` toolchains at `MODULE.bazel:128–132` register both, so the
Rust toolchain should match the platforms Clockwork already builds). Windows is
out of scope (requirements).

Open question O1 (below) covers whether Clockwork reuses FLTK's `crate`
lockfile or declares its own for the third-party Rust deps its *own* native code
will need.

### 3.3 FLTK: `BUILD.bazel`

- Add `rust_library` targets for `@fltk//crates/fltk-cst-core` and
  `@fltk//crates/fltk-parser-core` (in per-crate `BUILD.bazel` files under
  `crates/`), public visibility.
- Add the `fltk._native` cdylib target (`rust_shared_library`, `extension-module`)
  and a `py_library` (`:native_py`) that re-homes the produced `.so` to
  `fltk/_native.abi3.so` on the import path (via the rename mechanism specified
  in §3.4, "`.so` basename binding" — `rust_shared_library` emits `lib*.so`, so a
  `copy_file` to the abi3 basename is required) and exposes it `public`. The
  existing `py_library(name = "fltk")` is untouched; downstream may depend on
  `@fltk//:native_py` additionally to get the Rust span path.

### 3.4 FLTK: `rust.bzl` (new)

**`generate_rust_parser` rule** — declares `cst.rs` and `parser.rs` as action
outputs via two separate `ctx.actions.run` calls on `@fltk//:genparser`, because
the Rust subcommands do **not** share a `--output-dir` the way the Python
`generate` subcommand does (`rules.bzl:10` uses `--output-dir`; the Rust commands
do not accept it). Each Rust subcommand takes a **positional `output_file`**:

- `gen-rust-cst <grammar_file> <cst_out>` — positional grammar + output; options
  are `--protocol-module` / `--pyi-output` only (`genparser.py:265–297`). This
  command has **no** `--cst-mod-path`. The rule passes neither protocol option
  (no `.pyi`; out of scope).
- `gen-rust-parser <grammar_file> <parser_out> --cst-mod-path <path>` — positional
  grammar + output, with `--cst-mod-path` the only relevant option
  (`genparser.py:368–379`, default `super::cst`). The rule's `cst_mod_path` attr
  forwards **here only**.

This is "reuse the CLI as-is" (requirements) but with two positional-output
actions rather than one `--output-dir` action — the `generate_parser` analogy is
loose, not literal.

**`fltk_pyo3_cdylib` macro** — wires the generated sources + consumer `lib.rs`
into a `rust_shared_library` and a wrapping `py_library` (§2.3), with two
load-bearing glue steps the macro must perform:

- **Crate-source assembly.** The bare `mod cst;` / `mod parser;`
  in the consumer `lib.rs` make rustc look for `cst.rs`/`parser.rs` *in the same
  directory as `lib.rs`*. The generated files are Bazel action outputs in a
  different tree from the consumer-authored `lib.rs`, so the macro must place all
  three in one directory used as the crate root dir before invoking
  `rust_shared_library`. Mechanism: a `copy_file`/genrule (or `crate_root` +
  co-located `srcs` with matching basenames) that materializes
  `<gendir>/lib.rs`, `<gendir>/cst.rs`, `<gendir>/parser.rs`, and sets
  `crate_root = "<gendir>/lib.rs"`. The generated files are emitted by
  `generate_rust_parser` with the fixed basenames `cst.rs` / `parser.rs` so the
  bare `mod` declarations resolve. (Alternative considered and rejected as more
  fragile: emit `#[path = "…"]` attributes pointing at the action-output paths —
  rejected because those paths are not stable across Bazel configurations.)
- **`.so` basename binding.** `rust_shared_library` produces a
  platform-default `lib<name>.so`, **not** the `_native.abi3.so` /
  `<module>.abi3.so` basename that `import fltk._native` (or
  `import clockwork_native`) requires; maturin produces that name today from
  `module-name = "fltk._native"` (`pyproject.toml:29`), and `rules_rust` has no
  maturin. The macro therefore renames/relocates the `rust_shared_library` output
  to the abi3 basename on the correct import path via a `copy_file` step inside
  the wrapping `py_library` (e.g. `lib<name>.so` → `<import_dir>/<name>.abi3.so`).
  For `@fltk//:native` the target basename is `fltk/_native.abi3.so`; for a
  consumer cdylib it is `<pkg>/<name>.abi3.so`. The abi3 infix is the maturin
  convention for an `abi3-py310` build and is importable on CPython 3.10+. This
  same rename is what `@fltk//:native_py` (§3.3) performs for the FLTK extension.

### 3.5 Clockwork: `BUILD.bazel` + test (additive)

The three targets in §2.3 plus `clockwork_native_lib.rs` and
`clockwork_rust_roundtrip_test.py`. Existing `generate_parser` Python targets and
their consumers are unchanged (AC #5).

---

## 4. Edge cases / failure modes

- **`fltk._native` not on the test's path** → silent pure-Python fallback (the
  exact bug we are closing). Mitigation: `fltk_pyo3_cdylib`'s wrapping
  `py_library` carries `@fltk//:native_py` as a transitive `data` dep, so any
  test depending on the cdylib gets `fltk._native`. AC #3 is the guard: the test
  asserts the native span path is live (e.g. the fallback's `warnings.warn` is
  not emitted, or `fltk._native.Span` is resolvable), turning a silent
  regression into a test failure.
- **ABI version/layout mismatch** between `fltk._native` and the Clockwork
  cdylib. Under the source path this is effectively unproducible (§2.1) — both
  link `@fltk//crates/fltk-cst-core` from one commit. If it ever occurs (e.g. a
  future mixed wheel/source setup), `check_abi_pair` raises the typed
  `TypeError`; the guard stays effective and never yields a wrong answer. Not a
  separate test (requirements: "constructing a deliberate mismatch is out of
  scope").
- **Missing `extension-module` feature** → linker pulls libpython, link/ABI
  errors. Mitigation: the macro sets the feature unconditionally; consumers
  cannot forget it.
- **Module-name mismatch** (`[lib] name` ≠ `#[pymodule]` fn ≠ import name) →
  `ImportError` at test time. Mitigation: the macro derives all three from a
  single `name` attr; the consumer `lib.rs` `#[pymodule]` fn name must match —
  documented, and a mismatch fails loudly at import (AC #4 would not pass).
- **Grammar uses regex outside the `regex-automata` subset** → generated
  `parser.rs` fails to compile (its built-in `all_regex_patterns_compile`
  `#[test]` also catches it). Requirements declare this out of scope and
  non-gating; surfaced here only so the failure is understood, not silently
  mis-attributed to packaging. If it bites, the fix is grammar-side or
  FLTK-regex-side, separate effort.
- **`rules_rust` toolchain not registered by Clockwork (root)** → build error,
  not silent. FLTK's `bazel_dep` alone is insufficient by design; documented in
  the ADR so consumers know they must register the toolchain.
- **Clockwork adding its own native Rust** that links a *different*
  `fltk-cst-core` (e.g. via crates.io) → ABI mismatch. Guidance: Clockwork's own
  Rust must link the same `@fltk//crates/fltk-cst-core` target if it touches
  Span types; otherwise it is free. The macro/ADR document this.
- **Build-time cost** of compiling pyo3 + regex-automata from source on a clean
  checkout. Mitigated by Bazel's action cache / remote cache; not a correctness
  issue. Noted in §5.

---

## 5. Test plan

After this work, the following exist and pass under `bazel test` from a clean
Clockwork checkout:

1. **`//clockwork/dsl:clockwork_rs_srcs` builds** — `bazel build` produces
   `cst.rs` + `parser.rs` as action outputs, not checked in (AC #1). Verified by
   building the target.
2. **`//clockwork/dsl:clockwork_native` builds** — the cdylib compiles with
   `extension-module`, linking `@fltk//crates/fltk-cst-core` (AC #2). Verified by
   building the target.
3. **`//clockwork/dsl:clockwork_rust_roundtrip_test` (py_test) passes** (AC #3 +
   #4): imports `clockwork_native` and `fltk._native` in one interpreter;
   asserts `fltk._native.Span` resolves through the native path (not the
   `warnings.warn` fallback); parses one representative `clockwork.fltkg` source
   string; reads node/label/span via generated accessors without error. Bar:
   *some* result, not correctness, not Rust-vs-Python equivalence.
4. **FLTK-side rule smoke test** — an in-FLTK `BUILD.bazel` target exercising
   `generate_rust_parser` + `fltk_pyo3_cdylib` against an existing fixture
   grammar (e.g. `bootstrap.fltkg`) so FLTK's own CI covers the new public Bazel
   surface, independent of Clockwork. (Analogous to the existing
   `generate_parser` smoke targets in `@fltk//:BUILD.bazel`.)
5. **Pure-Python path intact** (AC #5): Clockwork's existing
   `generate_parser`-based targets and tests
   (`//clockwork/dsl:clockwork_cst`, the `ir/tests` suite) still build and pass.
   Verified by running the existing suite unchanged.

No new unit tests of parser correctness (out of scope). No deliberate-ABI-mismatch
test (out of scope).

---

## 6. Open questions (user judgment)

- **O1 — Third-party Rust crate sourcing for Clockwork's *own* native code.**
  This design has FLTK own a `crate`/`crates_repository` lockfile for the FLTK
  crates' third-party deps (`pyo3`, `regex-automata`). When Clockwork starts
  writing its own native Rust (an assumed motivation, not an AC), it will want
  its own third-party crates. Should Clockwork (a) reuse/extend FLTK's `crate`
  hub, or (b) declare an independent `crates_repository`? Recommendation: (b) —
  Clockwork owns its own lockfile for its own deps, and only shares the
  *FLTK-owned* crate targets (`fltk-cst-core`, `fltk-parser-core`, `pyo3` as
  needed for the cdylib). This keeps version authority clean. Flagged because it
  shapes Clockwork's `MODULE.bazel` `crate` extension usage and is a judgment
  call the user may have a preference on.

- **O2 — `rust_toolchain` version pin and platform set.** Which exact `rustc`
  version to pin, and whether aarch64 Linux must be covered (Clockwork's `clang`
  toolchains register both x86_64 and aarch64; the Rust toolchain should match
  whatever Clockwork CI actually executes). Defaulting to download-prebuilt,
  x86_64-linux, latest stable unless the user specifies otherwise.

TODO(bazel-rules-rust): this design supersedes the one-line
`# TODO(bazel-rules-rust)` at `MODULE.bazel:5`; the TODO entry in `TODO.md`
should be updated to point at this ADR when the work lands.
