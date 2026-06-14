# Codegen the Rust `lib.rs` boilerplate -- explained from scratch

## What this is about

FLTK is a toolkit for building parsers. You describe a language's grammar in a special file, and FLTK generates code that can parse that language and produce a structured tree (a "Concrete Syntax Tree," or CST) of the parsed result. FLTK can generate this parsing code in either Python or Rust; this design concerns the Rust path.

When FLTK generates Rust code for a grammar, it produces two files: `cst.rs` (the tree node definitions and their Python bindings) and `parser.rs` (the actual parser logic and its Python bindings). These are compiled into a Python extension module -- a shared library that Python can import and call, even though the internals are Rust. The framework that makes Rust code callable from Python is called pyo3.

But those two generated files are not enough to produce a working extension module. Rust requires a third file, `lib.rs`, that serves as the "front door" of the library. In this context, `lib.rs` does three things: it declares that `cst.rs` and `parser.rs` exist (via `mod cst;` and `mod parser;` statements), it defines the entry point that Python calls when importing the module (a function annotated with `#[pymodule]`), and inside that entry point it wires up the CST and parser as sub-modules so Python can reach them.

Today, every project that uses FLTK's Rust backend has to write this `lib.rs` by hand. The problem is that the file is pure boilerplate -- its contents are completely determined by information the toolchain already knows. The only thing that varies from one project to the next is the module name (e.g. `clockwork_native`). The submodule names (`cst` and `parser`), the registration calls, the imports -- all identical. Consumers are copy-pasting a file that the tool could just generate for them.

This design adds `lib.rs` generation to the FLTK toolchain, so that new consumers can stand up a Rust-backend extension module without writing any module-wiring boilerplate by hand, and existing consumers can delete their hand-written copies.

## The two consumers that matter

Two existing `lib.rs` files are targeted for migration to generated output.

**Clockwork** is an external project (living in a separate repository) that uses FLTK to parse its own domain-specific language. Its `lib.rs` is the prototypical "standard consumer" file: two submodules (`cst` and `parser`), one `#[pymodule]` function named `clockwork_native`, no special registrations. It is 25 lines of pure boilerplate.

**`fltk._native`** is FLTK's own internal Rust extension module. It is structurally different from a standard consumer in several ways. First, it is the canonical provider of three special types (`Span`, `SourceText`, and `UnknownSpan`) that all other FLTK consumers depend on at runtime -- so it registers those types directly in its module entry point, which normal consumers never do. Second, it hosts two grammar submodules under custom names (`poc_cst` and `fegen_cst`) instead of the standard `cst` and `parser`. Third, the Rust file names for those submodules (`cst_generated.rs` and `cst_fegen.rs`) differ from the Python-visible submodule names (`poc_cst` and `fegen_cst`), so there is a file-name-to-submodule-name mismatch that a generator must model. Fourth, it declares a global static (`UNKNOWN_SPAN`) with one-time initialization logic. In short, `fltk._native` is a singleton with unique responsibilities that no other consumer shares.

There are also three in-tree test fixture crates that have hand-written `lib.rs` files. The design examines each and finds that none qualifies for migration: one registers extra types and test functions, another has an extra test module and feature gating, and the third is a multi-grammar crate. All three carry test-only additions that fall outside what the standard generator intentionally models. This is a deliberate, called-out outcome -- those fixtures stay hand-written.

## How the build pipeline works (just enough to follow the rest)

FLTK has two build paths for Rust code.

The **Makefile/maturin path** is used for `fltk._native` and the test fixtures. The Makefile has a `gencode` target that invokes the CLI to generate `.rs` files, a developer commits those generated files, and `maturin develop` compiles them into a Python extension. Whether the committed generated files have drifted from what the generator would produce today is checked manually (`make gencode` then `git diff`), not by CI.

The **Bazel path** is used by external consumers like Clockwork. A Bazel macro called `fltk_pyo3_cdylib` orchestrates the build. It runs the FLTK generators to produce `cst.rs` and `parser.rs`, then assembles a complete Rust crate by copying those files alongside a consumer-supplied `lib.rs` into a single directory. During assembly, the macro prepends a `#![recursion_limit = "N"]` attribute to `lib.rs` -- this attribute must appear exactly once, and the macro owns it, so the consumer's `lib.rs` must never contain it. The consumer currently passes their hand-written `lib.rs` via a `lib_rs` attribute on the macro.

## The generator: a small templating unit, not a grammar processor

The existing CST and parser generators are complex: they consume a grammar definition and produce thousands of lines of Rust code with one class/struct per grammar rule. The new `lib.rs` generator is fundamentally different. There is nothing in `lib.rs` that comes from grammar rules -- no rule-derived symbols, no per-rule code. The file is entirely determined by a description of the module layout: what is the module name, what submodules exist, and whether any special registrations (like Span types) are needed.

The design introduces a new module, `gsm2lib_rs.py`, containing a `RustLibGenerator` class. Instead of taking a grammar as input, this generator takes a `LibSpec` -- a small frozen data structure that describes the module layout. A `LibSpec` contains:

- The module name (becomes the `#[pymodule]` function name).
- A list of submodules, where each submodule has a Rust module name (the `mod` declaration, corresponding to a `.rs` file), a Python-visible submodule name (passed to `register_submodule`), and a registration function name (defaulting to `register_classes`).
- Boolean flags for the `fltk._native` special case: whether to register Span types and whether to emit the `UNKNOWN_SPAN` static.

This is a deliberate divergence from the other generators. The CST and parser generators take a grammar and produce rule-derived code; the lib generator takes a layout descriptor and produces structural wiring code. It would be misleading to require a grammar file as input when nothing in the output depends on grammar rules.

Two convenience constructors keep common cases simple. `LibSpec.standard(module_name)` produces the Clockwork-style layout (submodules named `cst` and `parser`, no special registrations). A `native_spec()` factory function produces the one-off layout for `fltk._native` with its custom submodule names, Span registration, and `UNKNOWN_SPAN` static.

Input validation catches invalid module names (empty strings, names starting with digits, names containing spaces or hyphens -- anything that is not a valid Rust identifier). Invalid input raises a `ValueError` naming the offending value.

## The CLI surface

A new `gen-rust-lib` sub-command is added to `genparser.py`:

```
gen-rust-lib <output_file> --module-name <name> [--no-parser]
```

This command takes no grammar file, which is a deliberate departure from the `gen-rust-cst` and `gen-rust-parser` sub-commands. The reasoning: requiring a grammar argument would force a parse that produces nothing, since `lib.rs` has no rule-derived content. Accepting and ignoring a grammar file would be consistent in shape but misleading in substance. (Whether to accept a grammar positional anyway, purely for CLI symmetry, is left as an open question -- see the end of this document.)

The `--no-parser` flag produces a CST-only `lib.rs` that omits the `mod parser;` declaration and its registration line. This exists because some use cases only need CST nodes without a parser.

A separate `gen-rust-native-lib` command, taking only an output path and no other arguments, produces the `fltk._native` layout by calling `RustLibGenerator(native_spec()).generate()`. The `fltk._native` layout is fully determined and unique, so encoding it as a fixed factory and a parameterless command avoids polluting the standard CLI with flags that would exist solely to describe a single in-tree file.

## The Bazel surface

The `lib_rs` parameter on `fltk_pyo3_cdylib` becomes optional, defaulting to `None`. When omitted, the macro generates `lib.rs` automatically from the target's `name` attribute.

The mechanism: when `lib_rs` is `None`, the macro creates a new build rule (a `genrule`) that invokes `gen-rust-lib` with `--module-name` set to the target name, producing a generated `lib.rs`. The existing assembly step then consumes this generated file in exactly the same way it previously consumed a hand-written one -- including prepending the `#![recursion_limit]` attribute. Nothing downstream of the assembly step changes, so recursion-limit ownership is unaffected.

When a consumer explicitly supplies `lib_rs`, it is still used verbatim. Migration is opt-in: existing consumers with custom `lib.rs` files continue to work without modification. This preserves backward compatibility and provides an escape hatch for consumers that genuinely need custom wiring.

**CST-only is deliberately not wired into Bazel.** The `generate_rust_parser` rule always emits both `cst.rs` and `parser.rs`, and the assembly step requires both to be present. Adding a CST-only flag to the Bazel macro would control only the `lib.rs` shape while leaving a sibling `parser.rs` still generated and validated -- an unreconciled coupling. Since no in-scope migration target needs CST-only via Bazel, this is omitted. The `--no-parser` flag remains CLI-only.

The design also calls for wiring an existing smoke-test TODO (`fltk-pyo3-cdylib-smoke`) in the fltk repo to exercise the no-`lib_rs` generation path. Without this, the most mechanically novel part of the Bazel change -- the lib.rs-generating genrule -- would ship with zero automated in-repo coverage, relying entirely on Clockwork's out-of-repo build for validation.

## The Clockwork migration

In Clockwork's build configuration, the `lib_rs` attribute is dropped from the `fltk_pyo3_cdylib` call. The macro then generates `lib.rs` from `name = "clockwork_native"`. The hand-written `clockwork_native_lib.rs` file is deleted. The resulting extension module exposes the same `clockwork_native.cst` and `clockwork_native.parser` submodules with the same registered classes -- behavioral equivalence is the acceptance criterion, not byte-for-byte source equivalence.

There is a bookkeeping wrinkle: the deleted file contains a `TODO(native-submodule-error-context)` comment about improving error context in `register_submodule`. This TODO currently violates the project's convention (which requires both an inline `TODO(slug)` comment and a matching entry in `TODO.md` -- it only has the inline comment). On deletion, the comment is relocated to the actual `register_submodule` implementation in `fltk_cst_core`, and a proper `TODO.md` entry is added to bring it into compliance. Alternatively, the TODO can be adjudicated for removal if the work is not worth tracking.

## The `fltk._native` migration

A `gen-rust-native-lib` invocation is added to the Makefile's `gencode` target, writing `src/lib.rs` alongside the existing `gen-rust-cst` calls. The committed `src/lib.rs` becomes generated output with the same "drift posture" as the other generated `.rs` files: `make check` verifies that it compiles (via `maturin`/cargo), but does not regenerate it or diff it against generator output. Drift detection is the developer's responsibility via the manual `make gencode` + `git diff` workflow.

There is no `rustfmt` step in the build. Unlike the Python generators whose output is normalized by `ruff` via `make fix`, the Rust generators emit code that is never run through a formatter. The "done" gate for generated `.rs` files is compilation, not formatting. The generator must emit code that compiles; matching a formatter's style is neither required nor verifiable.

## What could go wrong

**Double recursion-limit injection.** The generated `lib.rs` must not contain `#![recursion_limit]` because the Bazel macro injects it during assembly. If both the generated file and the macro contained it, the crate root would have the attribute twice, causing a compile error. A test explicitly asserts the generated output does not contain `recursion_limit`.

**CST-only with stale parser references.** If `--no-parser` omitted the `mod parser;` declaration but left the `register_submodule` call for the parser (or vice versa), the result would fail to compile. A single flag controls both, ensuring they stay in sync.

**File-name/submodule-name mismatch.** In `fltk._native`, the Rust file `cst_generated.rs` is registered under the Python name `poc_cst`. The `Submodule` data structure models this with separate `mod_name` and `submodule_name` fields. A naive single-name design would emit the wrong `mod` declaration or the wrong registration name.

**`UNKNOWN_SPAN` double initialization.** The `UNKNOWN_SPAN` static uses `.expect("UNKNOWN_SPAN already set; module initialized twice")` to enforce single initialization. The generated output reproduces this exactly, preserving the "initialized once" semantic.

**Invalid module names.** Empty strings, names starting with digits, names with spaces or hyphens -- anything that is not a valid Rust identifier -- are rejected at generation time with a `ValueError` naming the offending value. The CLI converts this to a non-zero exit with a clear error message.

## What is still open

### 1. Is codegenning `fltk._native` worth the bespoke machinery?

This is the one genuine judgment call the design surfaces for the requester.

`fltk._native` is a singleton. It has unique responsibilities (providing Span, SourceText, UnknownSpan, and the UNKNOWN_SPAN static) that no other consumer shares or ever will share. The standard generator's payoff -- eliminating copy-paste boilerplate across multiple consumers -- does not apply here. There is exactly one `fltk._native`, and there will only ever be one.

Generating its `lib.rs` requires dedicated machinery: a `native_spec()` factory, special-case branches in the generator for Span registration and the UNKNOWN_SPAN static, and a dedicated CLI command. This machinery exists solely to produce one 38-line file.

The options are: **(a)** generate it via the dedicated path described in this design (the current default, which satisfies the explicit request that `fltk._native` be codegenned); or **(b)** scope this work to the standard consumer generator only and leave `fltk._native`'s `src/lib.rs` hand-written. Option (b) would significantly reduce the scope of the generator and CLI work while sacrificing nothing for downstream consumers.

What hangs on this: if the answer is (b), the `native_spec()` factory, the `register_span_types` and `unknown_span_static` flags on `LibSpec`, the special-case generator branches, and the `gen-rust-native-lib` CLI command are all removed from scope. The generator becomes simpler and the `fltk._native` `lib.rs` continues to be maintained by hand, as it has been.

### 2. Should `gen-rust-lib` accept a grammar file for CLI symmetry?

The existing `gen-rust-cst` and `gen-rust-parser` sub-commands both take a grammar file as their first positional argument. The new `gen-rust-lib` command does not, because `lib.rs` has no rule-derived content -- the grammar would be parsed and then ignored. The design omits it to avoid misleading users into thinking the grammar influences the output.

However, the requirements say the CLI should be "consistent with existing sub-commands." If that is read strictly to mean every sub-command should accept a grammar positional, the command would accept one and either ignore it or use it to auto-detect whether the grammar produces a parser (enabling automatic CST-only detection without the `--no-parser` flag).

What hangs on this: if the answer is "accept a grammar for symmetry," the command signature changes, and there is an opportunity to derive the `--no-parser` behavior automatically from the grammar rather than requiring an explicit flag. If the answer is "omit it" (the current default), the command stays simple and honest about its inputs, at the cost of being the one sub-command that does not take a grammar file.
