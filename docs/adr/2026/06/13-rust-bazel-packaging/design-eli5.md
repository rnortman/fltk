# How Clockwork Will Build FLTK's Rust Parser Under Bazel (ELI5)

## What this is about

FLTK is a library for building parsers. You give it a grammar file (a `.fltkg` file that describes the syntax of a language), and it generates code that can parse text written in that language into a structured tree (a Concrete Syntax Tree, or CST). FLTK is used by other projects that live outside the FLTK repository -- the generated parsers and tree classes are public API for those downstream consumers.

Clockwork is one such consumer. Clockwork has its own domain-specific language (DSL), described by a 413-line grammar file called `clockwork.fltkg`. Today, Clockwork uses FLTK to generate Python parser code (`clockwork_cst.py`, `clockwork_parser.py`, etc.), and this all works under Bazel, the build system both projects use.

FLTK also has a newer Rust backend: instead of generating Python files, it can generate Rust source files (`cst.rs` and `parser.rs`) that get compiled into a native Python extension (a "cdylib" -- a compiled shared library that Python can import). This Rust backend exists and works, but it has never been wired up to work through Bazel. This design is about closing that gap so that Clockwork (and any future consumer) can use FLTK's Rust codegen inside a Bazel build.

## The pieces you need to know about

### Bazel modules and how Clockwork gets FLTK today

Bazel organizes dependencies as "modules." Clockwork already declares FLTK as a Bazel module dependency, pinned to a specific git commit. This means Clockwork's Bazel build has access to the entire FLTK source tree under the label `@fltk//...`. Today, Clockwork loads a Starlark rule called `generate_parser` from `@fltk//:rules.bzl`, calls it with the grammar file, and gets Python source files as build outputs. Those Python files are then wrapped in `py_library` targets that the rest of Clockwork's compiler imports.

### The Rust extension and the cross-cdylib problem

FLTK's Rust backend produces two things that must work together at runtime:

1. **`fltk._native`** -- FLTK's own compiled Rust extension. It provides, among other things, the canonical `Span` type (which tracks where in the source text a parsed element came from).

2. **The consumer's cdylib** -- for Clockwork, this would be `clockwork_native`, a compiled Rust extension containing the generated Clockwork-specific parser and CST classes.

These two shared libraries load into the same Python interpreter, and the consumer's cdylib needs to reach into `fltk._native` at runtime to get the `Span` type. This creates a hard constraint: both libraries must be built against the exact same version of a shared Rust library called `fltk-cst-core`. If the versions differ, an ABI (Application Binary Interface) check fires and raises a clear error -- it never silently gives wrong results, but it does prevent the system from working. A second shared Rust library, `fltk-parser-core`, provides regex and parsing infrastructure that the generated parser code needs.

### What is missing today

Three things are absent from FLTK's current Bazel setup:

- **No Rust build support.** FLTK's `MODULE.bazel` has no `rules_rust` dependency. There is literally a TODO comment in the file about adding it.
- **No `fltk._native` in Bazel.** The existing `py_library` target for FLTK only globs `*.py` files. The compiled `.so` extension is not a declared Bazel output, so any Bazel consumer silently falls back to a slower pure-Python implementation of `Span` -- without any warning at build time.
- **No Rust codegen rules.** There is no Bazel rule to run the `gen-rust-cst` or `gen-rust-parser` CLI commands, and no macro to compile the resulting Rust sources into a cdylib.

## What we are going to do and why

### Decision 1: Build FLTK's Rust from source, not from a published package

The design builds all of FLTK's Rust code from source inside Bazel, using the same `@fltk` source tree that Clockwork already pins by git commit. No wheels are published to PyPI. No crates are published to crates.io.

The reason is the cross-cdylib ABI constraint described above. Both `fltk._native` and Clockwork's cdylib must link the same `fltk-cst-core`. If both are built from source out of the same git checkout, this is true by construction -- there is literally one copy of the `fltk-cst-core` code, referenced by one Bazel label. A version mismatch cannot happen because there is only one version.

The alternative of distributing a pre-built wheel was rejected because it only solves half the problem: a wheel gives Clockwork the `fltk._native` extension, but Clockwork still needs the `fltk-cst-core` Rust library to compile its own cdylib against. Clockwork would then have to independently pin that library to the exact version baked into the wheel, re-introducing the mismatch risk that building from source eliminates for free.

Publishing the core crates to crates.io was also considered but deferred. It adds a second version-coordination surface (the crates.io version versus the git commit pin) without removing the need for the source dependency. It remains a future option if a non-Bazel consumer ever needs it.

### Decision 2: FLTK owns the build rules; Clockwork owns the Rust toolchain

Under Bazel's module system (Bzlmod), there is a question of who declares what.

**FLTK provides the rules and macros.** FLTK will ship a new file, `rust.bzl`, containing two public symbols:

- `generate_rust_parser` -- a rule that runs FLTK's Rust codegen commands and produces `cst.rs` and `parser.rs` as build outputs.
- `fltk_pyo3_cdylib` -- a macro that takes the generated Rust files plus a consumer-authored `lib.rs`, compiles everything into a cdylib, and wraps it in a `py_library` so Python can import it.

The rationale for FLTK owning these rules: FLTK knows the internal invariants -- which Cargo features to enable, which core crates to link, how the `#[pymodule]` wiring works. If every consumer had to re-derive this knowledge and encode it in their own `BUILD.bazel` files, they would be duplicating FLTK internals and creating opportunities for subtle misconfiguration.

This file is kept separate from the existing `rules.bzl` so that a pure-Python consumer who never loads `rust.bzl` does not need `rules_rust` installed at all.

**Clockwork registers the Rust toolchain.** Under Bzlmod, toolchain registration is a root-module concern -- the root module's registrations take precedence. Since Clockwork is the root module in its own build, it must be the one to call `rust.toolchain(...)` and `register_toolchains(...)`. This ensures that Clockwork controls which Rust compiler version it builds with. The toolchain will use pre-built downloads (not a locally installed `rustup`), so CI builds are hermetic and reproducible.

Both FLTK and Clockwork declare `bazel_dep(name = "rules_rust", ...)`. Under Bzlmod's single-version resolution, these must be a compatible version -- a conflict is a build error, not a silent divergence.

### Decision 3: How the end-to-end build works

Here is the target graph that will exist in Clockwork's `BUILD.bazel`:

1. **`generate_rust_parser`** takes the grammar file and produces `cst.rs` and `parser.rs`. Under the hood, this runs two separate build actions (one for each file) because the Rust codegen CLI commands each produce a single output file with a positional argument -- unlike the Python `generate` command, which takes an `--output-dir` and produces multiple files at once. This is a "reuse the CLI as-is" approach.

2. **`fltk_pyo3_cdylib`** takes those generated files plus a small hand-written `lib.rs` (the "wiring file" that declares the Python module and registers the CST and parser submodules). It compiles them into a shared library and wraps it in a `py_library`. The macro automatically injects dependencies on `fltk-cst-core`, `fltk-parser-core`, and `pyo3`, and it carries `fltk._native` as a transitive runtime dependency so that `import fltk._native` works wherever the consumer cdylib is used.

3. **A `py_test`** imports the compiled module, parses a representative Clockwork source string, and reads node/label/span data through the generated accessors. The bar is deliberately low: it must produce some result without error. It is not a parser-correctness test or a Rust-vs-Python equivalence test -- this work is about packaging and integration, not parser semantics.

The hand-written `lib.rs` is small (about 10 lines) and follows an established pattern. The consumer declares `mod cst;` and `mod parser;` to pull in the generated files, then registers them as Python submodules via a helper function from `fltk-cst-core`. The `#[pymodule]` function name must match the library name must match the importable Python module name -- a constraint enforced by PyO3.

### How the macro assembles the crate

There is a practical wrinkle with Bazel that the macro must handle. In a normal Rust project, `lib.rs`, `cst.rs`, and `parser.rs` sit in the same `src/` directory, so `mod cst;` resolves naturally. Under Bazel, the generated files are action outputs in a `bazel-out/` tree while `lib.rs` is a consumer source file in a completely different directory. The Rust compiler would fail with "file not found for module `cst`."

The macro solves this by copying all three files into a single synthesized directory and pointing the Rust compiler at that directory as the crate root. This crate-source assembly step is a load-bearing part of the macro's contract, not an implementation detail.

An alternative was considered: emitting `#[path = "..."]` attributes in the generated code to point at the action-output paths directly. This was rejected because those paths are not stable across Bazel configurations, making the approach fragile.

### How the `.so` file gets the right name

There is another naming wrinkle. Bazel's `rust_shared_library` produces a file named something like `libclockwork_native.so`. But Python expects to import a file named `clockwork_native.abi3.so` (the `.abi3` infix is a convention meaning the extension works across Python versions 3.10+). Maturin, the tool FLTK uses outside Bazel, handles this renaming automatically, but there is no maturin under Bazel. So the macro includes a `copy_file` step that renames the output to the correct `<name>.abi3.so` basename and places it on the correct import path.

### New FLTK Bazel targets

FLTK's own `BUILD.bazel` gains several new targets:

- `rust_library` targets for `fltk-cst-core` and `fltk-parser-core`, with public visibility so consumers can link them.
- A `rust_shared_library` target that builds `fltk._native` (the FLTK extension itself), with the `extension-module` feature enabled.
- A `py_library` target (`:native_py`) that wraps the `.so` and puts it on the correct import path so `import fltk._native` works.

The existing `py_library(name = "fltk")` is unchanged. The native extension is additive and opt-in -- consumers who want the Rust `Span` path depend on `:native_py` in addition to `:fltk`.

### Third-party Rust dependencies

The Rust code depends on third-party crates like `pyo3` (Python bindings) and `regex-automata` (regex engine). Under Bazel, these are managed through `rules_rust`'s `crate` extension, which works from a lockfile. FLTK owns this lockfile, generated from FLTK's root `Cargo.toml` and `Cargo.lock`. It covers the crates needed by `fltk-cst-core`, `fltk-parser-core`, and `fltk-native`, but excludes FLTK's test fixtures (which have their own separate Cargo workspaces).

An important detail: the third-party crate repositories created by FLTK's `crate` extension are module-private under Bzlmod. Clockwork does not see them directly. But it does not need to -- the `fltk_pyo3_cdylib` macro lives inside `@fltk//:rust.bzl` and resolves those dependencies using FLTK-internal labels. Clockwork only needs its own crate hub if it writes its own native Rust with its own third-party dependencies (which is an open question -- see below).

## What could go wrong and how it is handled

**`fltk._native` not on the import path.** This is the exact silent bug that exists today -- Bazel consumers get the pure-Python fallback without knowing it. The fix is structural: the `fltk_pyo3_cdylib` macro's wrapping `py_library` carries `@fltk//:native_py` as a transitive data dependency, so any test that depends on the cdylib automatically gets `fltk._native`. The roundtrip test explicitly asserts that the native Span path is active (not the fallback), turning a silent regression into a test failure.

**ABI version mismatch between the two cdylibs.** Under the source-build approach, this is effectively impossible -- both link the same `@fltk//crates/fltk-cst-core` target from one git commit. If it ever happens (say, in a future mixed wheel/source setup), the existing `check_abi_pair` function raises a typed `TypeError` -- it never silently gives wrong results.

**Missing `extension-module` feature.** Without this Cargo feature, the build tries to link against `libpython`, causing linker errors. The macro sets this feature unconditionally, so consumers cannot forget it.

**Module name mismatch.** If the `[lib] name`, the `#[pymodule]` function name, and the Python import name do not all match, Python raises `ImportError`. The macro derives the first two from a single `name` attribute; the consumer's `lib.rs` must use the same name for its `#[pymodule]` function. A mismatch fails loudly at import time.

**Regex compatibility.** FLTK's Rust backend targets the `regex-automata` engine, which does not support lookahead, lookbehind, or backreferences. If the Clockwork grammar uses any of these, the generated `parser.rs` will fail to compile. This is explicitly out of scope for this design -- if it bites, the fix is in the grammar or in FLTK's regex support, a separate effort.

**Rust toolchain not registered.** If Clockwork's `MODULE.bazel` does not register a Rust toolchain, the build fails with an error, not a silent fallback. The ADR documents that consumers must register the toolchain themselves.

**Build time.** Compiling PyO3, regex-automata, and the FLTK crates from source on a clean checkout takes real time. Bazel's action cache and remote cache mitigate this on subsequent builds. This is noted as a cost, not a correctness concern.

## What is still open

### O1: Where Clockwork gets third-party Rust crates for its own native code

This design covers FLTK's third-party Rust dependencies (pyo3, regex-automata). But one of the motivations for adopting the Rust backend is that Clockwork wants to write its own native Rust code alongside the generated parser bindings. That code will have its own third-party crate dependencies.

The question is: should Clockwork reuse FLTK's crate lockfile (extending it to cover Clockwork's deps too), or should Clockwork declare its own independent `crates_repository` with its own lockfile?

The design recommends option (b), an independent lockfile. The reasoning is that it keeps version authority clean -- FLTK controls its own dependency versions, Clockwork controls its own, and the only shared artifacts are the FLTK-owned crate targets (`fltk-cst-core`, `fltk-parser-core`, the pyo3 version needed for the cdylib). But this is flagged as a user judgment call because it shapes how Clockwork's `MODULE.bazel` is structured, and the user may have a preference.

What hangs on the answer: if Clockwork reuses FLTK's crate hub, upgrades to any shared dependency (e.g., a new version of `serde`) require coordination between the two repos. If Clockwork owns its own hub, upgrades are independent but there are two lockfiles to maintain, and care is needed to ensure pyo3 versions stay compatible across the two cdylibs.

### O2: Which Rust compiler version and which platforms

The design calls for a specific `rustc` version to be pinned in Clockwork's toolchain registration, but does not specify which one ("latest stable" is the default). It also notes that Clockwork's existing C/C++ toolchains register both x86_64 and aarch64 Linux platforms, and the Rust toolchain should match whatever Clockwork's CI actually runs.

What hangs on the answer: if only x86_64 is registered but CI runs aarch64 jobs, those jobs will fail. If both are registered unnecessarily, it just means downloading an extra toolchain. The version pin affects which language features and compiler optimizations are available, and whether the pin stays compatible with FLTK's own `pyo3` version requirements (pyo3 0.29 requires at least Rust 1.63, but any recent stable version satisfies this easily).
