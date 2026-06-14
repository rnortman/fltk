# Cleaning up `fltk._native`: making the Rust runtime module grammar-free

## What this is about

FLTK is a toolkit for building parsers and compilers. You describe a language's grammar in a special file, and FLTK generates code that can parse that language -- both a parser (the thing that reads text and understands its structure) and a CST (Concrete Syntax Tree -- a set of classes representing every piece of the parsed text). FLTK can generate these artifacts in Python or in Rust, and external applications use those generated artifacts to build their own tools.

FLTK also uses itself: it has its own grammar (called "fegen," short for "frontend generator") that describes the grammar-definition language. FLTK generates a parser and CST for fegen, then uses them to read other grammars. This is called self-hosting.

The Rust side of FLTK is exposed to Python through a compiled extension module called `fltk._native`. Think of it as a bridge: Rust code compiled into a shared library that Python can import. The key question this design addresses is: what should live inside that bridge module?

## The principle: runtime versus grammar-specific code

There is a clean conceptual split between two kinds of code:

1. **Runtime code** -- shared infrastructure that every generated parser needs regardless of what grammar it was built from. This includes things like span types (which track where in the source text a parsed element came from), source-text wrappers, the packrat memoization engine, and error formatting. This code is hand-written, grammar-agnostic, and never changes when you add a new grammar.

2. **Grammar-specific code** -- the generated parser and CST classes for a particular grammar. Each grammar gets its own set of these. They depend on the runtime, but the runtime never depends on them.

The governing principle is that `fltk._native` should contain only runtime code. It should have no knowledge of any specific grammar -- no parsers, no CST node classes. Grammar-specific artifacts belong in their own separate modules.

## The Python side already gets this right

On the Python side, FLTK already follows this principle perfectly, and understanding how it does so makes the Rust problem clear.

The Python runtime lives in a package called `fltk/fegen/pyrt/` ("Python runtime"). It contains hand-written, grammar-agnostic modules: span types and terminal matching, a packrat parsing engine, error tracking and formatting, and a backend-selector module that chooses between the pure-Python and Rust implementations of span types. None of these modules import anything grammar-specific. The dependency arrow points strictly one way: generated code imports the runtime, never the reverse.

FLTK's own self-hosting grammar artifacts are generated as separate files that sit next to the grammar definition: `fltk_cst.py` (the CST node classes), `fltk_parser.py` (the parser), and so on. They are committed to the repository but clearly separated from the runtime package. They import from `pyrt` but `pyrt` knows nothing about them.

## The Rust side has a problem

The Rust runtime is split across two internal crates (think of these as Rust library packages): `fltk-cst-core` provides span and source-text types, and `fltk-parser-core` provides the packrat parsing engine. These are the Rust analogs of the Python runtime and are correctly placed -- they are grammar-agnostic shared infrastructure.

The problem is in `fltk._native`, the compiled extension module that bridges Rust into Python. Today, its generated `lib.rs` (the file that defines what Python can see) registers three things:

- **Span types** (`Span`, `SourceText`, `UnknownSpan`) at the top level -- these are runtime types and belong here. Correct.
- **`fegen_cst`** as a submodule -- this is the CST for FLTK's real self-hosting grammar, containing 28 node classes. This is grammar-specific generated code. It should not be here.
- **`poc_cst`** as a submodule -- this is a CST for a tiny three-rule toy grammar used only for testing. It is grammar-specific test material. It definitely should not be here.

This is the Rust equivalent of compiling `fltk_cst.py` into the `pyrt/` runtime package -- exactly the coupling the principle forbids. Furthermore, there is a bespoke code path (`native_spec()` and a dedicated `gen-rust-native-lib` CLI command) whose sole purpose is to describe and generate this mixed layout.

An important simplifying fact: the correctly-shaped replacement for the fegen CST already exists. There is a standalone Rust extension crate at `tests/rust_cst_fegen/` that builds a module called `fegen_rust_cst` with proper `cst` and `parser` submodules. It depends on the runtime crates, pulls span types from `fltk._native` at runtime, and is built through the standard code-generation path. The fegen CST file in this standalone crate is required to be byte-for-byte identical to the `cst_fegen.rs` file inside `_native`. So the "right shape" artifact already exists -- `_native` has a redundant copy of it. The refactor is therefore mostly deletion and rewiring, not new construction.

## What the design does and why

### Making `_native` runtime-only

After the refactor, `fltk._native` exports exactly three things at its top level: `Span`, `SourceText`, and `UnknownSpan`. There are no submodules. The two generated CST source files (`cst_generated.rs` and `cst_fegen.rs`) are deleted from the `src/` directory. The hand-maintained type-stub file (which already documents only the span types) stays, minus a now-factually-false comment block about the PoC classes that would actively mislead if left in place. The separate `fegen_cst.pyi` stub file is deleted from `fltk/_native/` because its replacement moves with the relocated CST.

This is the exact runtime surface that the only external consumer (an unpushed research spike called clockwork) depends on -- clockwork imports only `fltk._native.Span`, so it is completely unaffected.

### Promoting the fegen crate to a first-class location

The existing `tests/rust_cst_fegen/` crate is promoted from its test-fixture location to `crates/fegen-rust/`. This makes it the canonical, permanently committed home of FLTK's own Rust-side fegen grammar artifacts -- the Rust peer of the committed Python files `fltk_cst.py` and `fltk_parser.py`.

Why move it out of `tests/`? Because it is no longer just a test fixture. Once `_native` stops carrying the fegen CST, this crate becomes the sole location of FLTK's own generated Rust grammar. Putting it under `crates/` (where FLTK's other first-class Rust crates live) signals its status accurately. Leaving it under `tests/` would invite future contributors to treat a canonical artifact as disposable scaffolding.

The crate's internal shape is unchanged: it builds a Python module called `fegen_rust_cst` with `cst` and `parser` submodules. The importable module name `fegen_rust_cst` is deliberately kept as-is. The governing principle constrains where grammar code lives, not what its module is named, and renaming would be gratuitous churn with no structural benefit.

With the fegen CST living in exactly one place, the old byte-for-byte identity coupling between `src/cst_fegen.rs` and the standalone crate's `cst.rs` simply disappears -- there is no second copy to keep in sync.

### Routing the type stub where pyright will find it

FLTK uses pyright (a type checker) and `.pyi` stub files to verify that the Rust CST classes conform to a protocol that the Python CST also follows. pyright is configured to only look for stubs inside the `fltk` package tree. If the fegen stub ended up somewhere outside that tree (like under `crates/fegen-rust/`), pyright would silently ignore it and the protocol-conformance check would die without anyone noticing.

The design routes the stub to `fltk/_stubs/fegen_rust_cst/cst.pyi` -- a stub package inside the `fltk` tree, named to match the importable module `fegen_rust_cst.cst`. A corresponding `stubPath`/`extraPaths` entry is added to `[tool.pyright]` in `pyproject.toml`. The design is explicit that this `pyproject.toml` edit is a mandatory part of acceptance: without it the stub is dead and the conformance check silently stops running. The existing `gen-rust-cst --pyi-output` flag controls where the file is written, but resolution is governed by the pyright configuration, not the emit path -- the two must agree.

### Relocating the PoC CST into its own test-fixture crate

The proof-of-concept toy grammar CST (`poc_cst`) has no Python-side analog at all. It is purely test material exercising basic CST behaviors like label semantics and span handling.

The design creates a new standalone test-fixture crate at `tests/rust_poc_cst/`. This becomes a top-level Python module called `poc_cst` (no longer a submodule of `_native`) with a `cst` submodule following the standard shape. Test imports become `from poc_cst.cst import Identifier, Items`. The design deliberately does not register PoC classes at the top level of the module, because that would be a one-off wiring inconsistent with every other grammar extension -- the refactor is establishing a "one grammar per extension, uniform shape" invariant.

Why a separate fixture rather than folding the PoC into the fegen crate? The PoC's whole purpose is to be a minimal, independent CST exercise, deliberately distinct from the real grammar. Combining the two would reintroduce two grammars in one module -- the same smell, just smaller. A standalone fixture preserves the one-grammar-per-extension invariant.

There is a related crate called `fltk-cst-spike` that compiles the same toy CST in a python-off configuration (pure Rust, no Python bindings). It currently gets its source by copying `src/cst_generated.rs`. After the refactor, it copies from the PoC fixture's generated `cst.rs` instead. The copy is intentionally preserved rather than replaced with independent code generation: a `cp` provides a byte-identity guarantee by construction, whereas two separate `gen-rust-cst` invocations could diverge if run with subtly different flags -- the exact fragility this refactor eliminates for the fegen grammar. This is the one grammar where "exactly one generated CST" cannot be fully achieved, because the python-on and python-off builds genuinely need two compiled copies. The `cp` keeps them a single source of truth.

### Collapsing the bespoke code-generation path

The function `native_spec()` and the CLI command `gen-rust-native-lib` existed solely to encode the mixed `_native` layout. Now that `_native` is runtime-only, the layout simplifies to "span types plus an UNKNOWN_SPAN static, zero submodules" -- and the existing generic `LibSpec` data model already has the knobs to express this (the `register_span_types` and `unknown_span_static` fields, and a validation rule that already permits zero submodules when span registration is present).

The design deletes `native_spec()` and `gen-rust-native-lib` entirely. The standard `gen-rust-lib` command gains three new flags: `--register-span-types`, `--unknown-span-static`, and `--no-cst`. With these, `_native`'s `lib.rs` is generated by the same generic path downstream consumers use, just with different options. The rendering engine (`RustLibGenerator.generate()`) is already fully data-driven and needs no changes -- only the spec fed to it changes.

The standard consumer factory (`LibSpec.standard()`) is completely unaffected. It never referenced `native_spec()`. Downstream consumers (like clockwork) keep getting their `cst`+`parser` submodules through the same path as before.

Tests that pinned the old `native_spec()` shape (approximately eleven functions in `test_gsm2lib_rs.py`) are deleted. The `native_spec` name is removed from the module's import line -- this is a hard dependency, not cleanup, because leaving it would make the entire test module fail to collect under pytest. New assertions are added for the span-only `gen-rust-lib` flag combination.

### Makefile and build system rewiring

The Makefile's `gencode` target gets several updates:

- The `gen-rust-native-lib` invocation is replaced with the generalized `gen-rust-lib` call using the new flags.
- Lines that generated `src/cst_generated.rs` and `src/cst_fegen.rs` are deleted.
- Fegen CST generation is repointed to the promoted crate at `crates/fegen-rust/src/cst.rs`, carrying the protocol and `.pyi` flags that were previously on the `cst_fegen.rs` step. The `.pyi` output target is the pyright-resolved stub-package location (`fltk/_stubs/fegen_rust_cst/cst.pyi`), not a path under the crate that pyright would not check.
- A new line generates the PoC fixture's CST, and the spike's `cp` is repointed to copy from there.
- The "must match" comment about byte identity with `cst_fegen.rs` is deleted because there is no second copy to match.

Build and check targets that reference `tests/rust_cst_fegen` by path are repointed to `crates/fegen-rust`. A new `build-poc-cst` target is added and wired into `build-test-fixtures` so `make test` builds it before pytest runs.

For `cargo-deny` (the supply-chain audit), the new `tests/rust_poc_cst` crate is a standalone workspace with its own `Cargo.lock`, so it needs an explicit fifth `cargo deny` line alongside the existing four. Omitting it would silently drop the new crate from the supply-chain gate. The design calls this out specifically because silent coverage loss is the most insidious failure mode in a quality gate.

### Bazel wiring

The Bazel `:native` target uses a source glob (`src/**/*.rs`). Deleting the two CST files means the glob naturally yields only runtime code -- no rule changes needed for the source set. The only required edit is a comment that explains why the `python` crate feature is enabled: it currently cites the deleted CST modules, but the real reason (it gates span-type registration via `fltk-cst-core/python`) remains valid. The comment must be rewritten to cite the correct justification.

The `:native` / `:native_so` / `:native_py` Bazel targets are otherwise unchanged. Consumers still depend on `:native_py` for `import fltk._native` to get the span types. The relocated crates are standalone maturin workspaces built by the Makefile, not by Bazel; no new Bazel targets are needed.

### Clockwork needs no changes

Clockwork's only `_native` dependency is `fltk._native.Span`, which remains exported. Its own grammar extension is built through the standard code-generation path, which is untouched. A manual verification step -- rebuild clockwork's module and run its roundtrip test -- confirms no breakage, but no source changes are required.

## What could go wrong and how it is handled

**The `pyrt/span.py` backend selector.** This module imports `Span`, `SourceText`, and `UnknownSpan` from `fltk._native`, falling back to pure-Python versions on failure. Since we are removing only the CST submodules and keeping those three names, the selector continues to work. Existing tests that assert these names are present on `_native` stay green and pin this invariant.

**Stale build artifacts.** If the CST source files are deleted but the old compiled `.so` is not rebuilt, `import fltk._native.fegen_cst` would still appear to work from the cached build. The Makefile's `test` target has `build-test-fixtures` as a prerequisite, so `make test` and `make check` always rebuild `_native` before running pytest. This existing safeguard prevents stale-artifact surprises.

**Tests importing old paths.** Several test files currently import from `fltk._native.poc_cst` and `fltk._native.fegen_cst`. These imports must be updated to the new paths (`from poc_cst.cst import ...` and `import fegen_rust_cst.cst`). The file `test_module_split.py` already imports `fegen_rust_cst.cst` and `fegen_rust_cst.parser` for other assertions, so those existing imports are unaffected by the crate's filesystem move since the importable name is preserved. The PoC-related assertions and the `fegen_cst`-reachability assertions are the ones that must flip to assert absence from `_native` and presence at the new paths.

**Type stub resolution.** pyright resolves stubs only within its configured search tree. A stub under `crates/fegen-rust/` would be invisible. The design routes the stub into the `fltk` tree and requires the `pyproject.toml` configuration edit. If the configuration were wrong, `make check` (which runs pyright) would not fail loudly on the specific conformance check -- it would silently stop checking it. This is why the `pyproject.toml` edit is part of acceptance, not a follow-up.

**Path drift in `make check`.** Several `make check` sub-targets (clippy, cargo test, cargo deny, no-pyo3 checks) hard-code `tests/rust_cst_fegen/Cargo.toml`. Missing any one when repointing to `crates/fegen-rust` would silently drop a coverage lane. The design enumerates every such reference. A full `make check` pass is the final gate.

**Two copies of the PoC CST.** The python-on fixture and the python-off spike need two compiled copies of the same generated source. The `cp`-from-fixture approach ensures byte identity by construction. If someone replaced the `cp` with two independent generation invocations, the guarantee would depend on both using identical flags -- the same kind of fragile coupling this refactor eliminates elsewhere.

## What is still open

The design has resolved all previously open questions. Every decision about module naming (keep `fegen_rust_cst`), crate location (promote to `crates/fegen-rust/`), and stub placement (route to `fltk/_stubs/fegen_rust_cst/cst.pyi` with matching pyright config) is settled and reflected in the design body. There are no remaining open questions.
