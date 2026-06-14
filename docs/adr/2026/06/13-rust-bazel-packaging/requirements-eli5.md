# ELI5: What We Need to Prove (and Why)

## The problem, from the top

FLTK is a toolkit for building parsers. You hand it a grammar file (a `.fltkg` file that describes the syntax of some language), and it generates code that can parse text written in that language. The generated code produces a Concrete Syntax Tree (CST) -- a structured representation of the parsed text that downstream application code can walk through and act on.

FLTK has two code-generation backends. The original one generates Python code. A newer one generates Rust code with Python bindings (via a library called PyO3 that lets Rust code expose itself as a Python module). The Rust backend is faster, but newer and less battle-tested.

Clockwork is a separate project that uses FLTK to parse its own domain-specific language. Today Clockwork uses only FLTK's Python backend. The goal of this work is to prove that Clockwork can also use FLTK's Rust backend, and specifically that it can do so using Bazel, the build system both projects use.

A secondary motivation: a consumer like Clockwork adopts the Rust backend not just for parser speed but also because it wants the option to write its own native Rust code alongside the generated bindings. The integration should not preclude that.

## How FLTK and Clockwork are connected today

Clockwork pulls in FLTK as a Bazel module. In Clockwork's `MODULE.bazel` file, FLTK is declared as a `bazel_dep` resolved via `git_override`, pinned to a specific git commit hash. This makes FLTK available in Clockwork's build files under the label `@fltk//...`. When Bazel runs, it fetches the FLTK source at that commit and builds it as part of Clockwork's build.

FLTK exposes a Starlark build rule called `generate_parser` in its `rules.bzl` file. Clockwork loads this rule and uses it to run FLTK's code generator against `clockwork.fltkg`, producing Python files (`clockwork_cst.py`, `clockwork_parser.py`, etc.) as Bazel build outputs. Clockwork's Python code then imports and uses these generated files.

Today this entire pipeline is Python-only. FLTK has a Rust extension module (`fltk._native`) that provides performance-optimized native types, but the Bazel build does not package or expose it. FLTK's Bazel `py_library` target only globs `**/*.py` files, so the compiled `.so` file for the native extension is not included. Bazel consumers silently get a pure-Python fallback instead.

## What we want to prove

The goal is an end-to-end proof that Clockwork can, under Bazel:

1. Run FLTK's Rust code generator against `clockwork.fltkg` to produce Rust source files.
2. Compile those generated Rust files into a Python-importable native library (a "cdylib" -- a shared library that Python can load as a module).
3. Actually use that library from Python test code, including verifying that the Rust-native code path is exercised (not the pure-Python fallback).
4. Get some parse result back -- proving the packaging and plumbing work.

This is a proof-of-concept for packaging and integration, not a production migration. It is also not a parser correctness test. Clockwork's existing Python-based parser pipeline must remain intact and working. The Rust integration is purely additive.

## The hard technical constraints

Several invariants make this integration non-trivial. Understanding them is essential to understanding the requirements.

### The Span type and the cross-cdylib ABI protocol

When a parser produces a CST, each node in the tree carries a "span" -- a record of where in the source text that node came from. FLTK's Rust code represents spans using a native Rust type defined in a library crate called `fltk-cst-core`. When these spans cross from Rust back into Python, they go through a protocol called the "cross-cdylib ABI."

Here is the key problem: in this architecture, there are two separate compiled Rust libraries loaded into the same Python process. One is `fltk._native` (FLTK's own native extension). The other is the consumer's generated parser (e.g., Clockwork's). Each is compiled independently into its own `.so` file. Even though both use `fltk-cst-core` internally, they each get their own copy of the code. To Python, these are separate modules with separate type systems.

To make span objects interoperable between the two modules, `fltk-cst-core` includes a protocol: the consumer's cdylib does not define its own `Span` Python type. Instead, at runtime, it calls `py.import("fltk._native")` to look up the canonical `Span` type from FLTK's native extension and uses that. This means `fltk._native` must be importable whenever a consumer cdylib is used.

### The same-version constraint

The cross-cdylib protocol includes an ABI version guard. Both `fltk._native` and the consumer's cdylib embed a version string derived from `fltk-cst-core`'s Cargo package version at compile time. At runtime, these version strings are compared. If they do not match (because the two were compiled against different versions of `fltk-cst-core`), a `TypeError` is raised rather than silently producing incorrect results.

The Bazel build must ensure both cdylibs link the same `fltk-cst-core` version. The chosen build mechanism should make this the natural default. Deliberately constructing a mismatch to test the error is out of scope for the POC -- this is an invariant to preserve, not a separately-tested acceptance gate.

### Extension-module feature and Python feature gating

PyO3 cdylibs that are imported from Python must be compiled with the `extension-module` Cargo feature enabled. Additionally, `fltk-cst-core` has a `python` feature that enables all of its PyO3 integration code; consumers use it with `default-features = false` plus an explicit `python` feature. This is a load-bearing pattern that the Bazel build must replicate.

### Re-exported regex dependency

`fltk-parser-core` re-exports the `regex_automata` crate. Generated parser code uses `fltk_parser_core::regex_automata::meta::Regex`, so consumers need no direct `regex-automata` dependency. The Bazel build must preserve this transitive dependency path.

### Regex compatibility is assumed, not tested

FLTK's Rust code generator targets the subset of regular expressions that `regex-automata` supports (no lookahead, lookbehind, or backreferences). The requirements assume `clockwork.fltkg` is already within this subset. If it turns out not to be, that is a separate, out-of-scope effort (either adjust the grammar or extend FLTK's regex support). It does not change these requirements and is not a pass/fail gate for the integration.

### ABI3 and Python version

The compiled `.so` files use Python's stable ABI (ABI3) targeting CPython 3.10 and above. A single compiled library works across Python 3.10 through 3.x without recompilation. Clockwork's Bazel setup already uses a CPython 3.10-compatible toolchain, so this is compatible.

### A Rust toolchain is universally required

Neither FLTK nor Clockwork registers `rules_rust` (the Bazel ruleset for building Rust) today. This work adds it. This is required regardless of which packaging approach is chosen -- every path needs Rust compilation. Because it is universally required, it does not distinguish one approach from another and should not be weighed against any option.

### Separate Cargo workspaces

FLTK's test crates each declare their own Cargo workspace and are excluded from the root workspace. A Bazel integration must not assume a single unified Cargo workspace or `Cargo.lock`. Bazel typically builds Rust crates individually, but dependency resolution must account for this topology.

## Acceptance criteria in plain terms

There are five concrete outcomes that define "done."

### 1. Code generation runs under Bazel

Starting from a clean Clockwork checkout, a Bazel build command runs FLTK's Rust code generator against `clockwork.fltkg` and produces Rust source files (a CST module and a parser module) as Bazel action outputs. These files are generated fresh, not checked in.

### 2. The cdylib compiles under Bazel

Bazel compiles the generated Rust sources into a PyO3 cdylib with the correct feature flags (`extension-module`, `python`), linking the same `fltk-cst-core` rlib version that `fltk._native` was built against.

### 3. Both native modules load and the Rust path is exercised

Under Bazel, Python can import both the generated Clockwork cdylib and FLTK's `fltk._native` module in the same interpreter. The canonical `fltk._native.Span` is resolved through the native (Rust) path, not the pure-Python fallback. Today, the fallback emits a `warnings.warn`, and a missing or mismatched `fltk._native` raises a `RuntimeError` -- these serve as diagnostic hints for verifying the path is correct, but they are hints, not formal pass/fail gates.

### 4. A round-trip parse produces some result

A Bazel Python test parses at least one representative Clockwork source string through the generated Rust parser, obtains a CST, and reads node, label, and span data through the generated accessors without error. The test passes under `bazel test`.

The bar is deliberately modest: the Bazel-built Rust parser plus PyO3 bindings, invoked in context, produce *some* parse result at all. This is not a test that FLTK parses correctly, and it is not a Rust-versus-Python equivalence test. Parser correctness is FLTK's own concern, tested elsewhere. This work tests packaging and integration.

### 5. The existing Python path still works

Clockwork's existing Python-based `generate_parser` targets and their tests still build and pass. Nothing is broken by the addition.

## What is out of scope

- Migrating Clockwork's production code to use the Rust parser. The existing Python-backend path may remain Clockwork's production path.
- Performance tuning or release-build benchmarks.
- Publishing FLTK crates to crates.io or wheels to PyPI as a requirement (may be selected as the mechanism, but is not mandated).
- Windows or non-Linux support.
- Changing any generated public API symbols (class names, accessors, type annotations). Per FLTK's compatibility policy, these are downstream-consumed public API and must not be forced to change.
- Removing or breaking the pure-Python Bazel path FLTK already ships.

## The FLTK-side work is real product work

An important note the requirements call out: the changes made to FLTK as part of this effort are not throwaway proof-of-concept scaffolding. They are genuine product features -- new Bazel rules, macros, `rules_rust` wiring, packaging of `fltk._native`. FLTK's generated artifacts are public API for out-of-tree consumers; the new Bazel surface (rule names, macro interfaces, visibility) likewise becomes public API the moment a consumer loads it. This surface must get the same backward-compatibility care that FLTK demands of its generated symbols. The exact number of rules, their names, and their shape are left to the designer.

## What the user sees

This work's user-visible surface is build configuration, not new runtime API:

- **In Clockwork:** new entries in `MODULE.bazel` (possibly `rules_rust` registration, depending on design), new `BUILD.bazel` targets for Rust code generation, cdylib compilation, and a test. The existing `load("@fltk//:rules.bzl", "generate_parser")` usage is preserved.
- **In FLTK:** a new `rules_rust` dependency in its module configuration, new Starlark rules or macros for Rust code generation and cdylib building, and packaging of `fltk._native` plus the core crates as Bazel-visible artifacts. The concrete shape (number of rules, macro names, intermediate file names) is the designer's choice.
- **Unchanged:** generated CST/parser class names, accessor method names, type annotations, and the `fltk._native` import path.

The existing `genparser` CLI subcommands (`generate`, `gen-rust-cst`, `gen-rust-parser`) are reused as-is unless a gap is found; any new CLI flag is an open question, not assumed.

## What is left to design

The requirements deliberately leave the packaging and dependency-mechanism decisions to the design phase. They are recorded below to scope the design space the designer inherits, not to force a choice. The requirements must hold regardless of which path is chosen.

### How FLTK's Rust artifacts reach the consumer

This is the central design question. Two broad options:

**Build Rust from source in Bazel.** Clockwork already pulls in FLTK as a Bazel source dependency via `git_override`, pinned to a specific git commit. If the Rust crates are also built from that same source checkout, a single version pin (the git commit) governs both `fltk._native` and the consumer's cdylib. This directly satisfies the ABI-version-match constraint by construction -- a mismatch becomes effectively unproducible.

**Wheel/pip packaging.** FLTK publishes (or Clockwork vendors) a maturin wheel containing `fltk._native`. But the consumer still needs to build its own cdylib from the generated Rust sources, linking against the matching `fltk-cst-core`. So this path must also answer how the core crates are obtained and how the ABI version pin stays matched.

Every path requires Clockwork's Bazel build to be able to compile Rust -- that is a baseline given, not a differentiator. What differs between paths is only where the core rlibs come from and how the version pin is kept matched. That is the design question.

### Where `rules_rust` lives

FLTK owning the `rules_rust` wiring plus a cdylib macro (so consumers get a turnkey "generate + build cdylib" path, matching the existing `rules.bzl::generate_parser` pattern) versus Clockwork declaring it itself versus both. Whichever is chosen becomes public FLTK Bazel surface.

### How the core crates are distributed

`fltk-cst-core` and `fltk-parser-core` are MIT-licensed and are not currently published to crates.io. Publishing them is a fully available option -- if the designer judges it the cleanest path, FLTK will publish them, and Bazel consumers can then fetch them via `crates_repository`. Equally, if source-only distribution is preferred, consumers obtain them through the FLTK source dependency. Neither is mandated, and "not yet published" is not a constraint or blocker -- it is simply one of the design alternatives.

### Rust toolchain registration details

Where the `rules_rust` toolchain is registered (download a pre-built toolchain versus use the host system's `rustup`) and which CI platforms it must cover. Clockwork's CI does not build Rust today; adding a Rust toolchain is part of the baseline work.

### An ADR will record the outcome

Whatever packaging and dependency mechanism the design lands on, a written Architecture Decision Record must capture it. The choice is the designer's; the requirement is only that the chosen path is recorded.
