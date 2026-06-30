# Codegen protocol and .pyi outputs -- ELI5

This document explains the design in `design.md` for a reader who has never seen this codebase. It covers what is being built, why each decision was made, and what was resolved during the design process. Every decision described here comes from the design document; nothing is added or changed.

## What this is about

FLTK is a Python library for building parsers and compilers. You give it a grammar file (a `.fltkg` file that describes the syntax of some language), and it generates code for you: parser code that can read that language, and "CST node classes" that represent the parsed structure of a program in that language. FLTK can generate this code in two flavors -- pure Python, or Rust (compiled as a Python extension for speed). Both flavors are meant to look the same to downstream application code that uses them.

Two additional generated artifacts sit alongside the parsers and CST classes:

**The protocol module.** This is a Python file containing abstract type contracts -- `typing.Protocol` classes, one per grammar rule -- that describe the shape of a CST node without tying it to any concrete implementation (Python or Rust). A downstream application can write its type annotations against the protocol, and then swap between the Python and Rust backends without changing any annotations. The protocol module also includes a `NodeKind` enum (so code can distinguish node types), nested `Label` sentinel classes, a `Span` protocol (representing source-text positions), and a `CstModule` protocol (representing the module that holds all the node classes). Crucially, the protocol module is backend-agnostic: the exact same protocol file is valid whether you are using the Python CST or the Rust CST.

**The `.pyi` type stub.** When the CST is implemented in Rust (compiled into a `.so`/`.pyd`), Python type checkers like pyright cannot see inside it. A `.pyi` file provides type annotations that tell pyright the shape of the Rust module. The `.pyi` stub structurally depends on the protocol module -- it contains a line like `import fltk.fegen.fltk_cst_protocol as _proto` and references protocol types everywhere (e.g., `_proto.NodeKind`, `_proto.ClassName`). This means you cannot generate a `.pyi` without knowing the dotted Python import path of the protocol module.

FLTK has two build systems: a Makefile (for local development) and Bazel (for integration into larger projects). Both invoke the same CLI subcommands under the hood.

The problem this design solves has two parts. First, the protocol module is generated unconditionally by the Python path but cannot be generated at all by the Rust path, and neither build system exposes it cleanly. Second, the `.pyi` stub is not exposed through the Bazel Rust rule at all, even though it is essential for type checking.

## The relevant parts of the system

### CLI subcommands

FLTK's CLI (`genparser.py`) has several subcommands. The ones that matter here are:

- **`generate`** (the Python path): takes a grammar file, a base name, and a CST module name. It writes several Python files: the CST classes, parser(s), and currently always the protocol module. There is a `--protocol-only` flag that skips CST/parsers and writes only the protocol, but there is no way to suppress the protocol when generating everything else. The protocol file just always appears.

- **`gen-rust-cst`** (the Rust CST path): takes a grammar file and an output path. It writes a `.rs` file containing the Rust CST implementation. It has an optional `--protocol-module` flag that takes the dotted import path of an already-existing protocol module (e.g., `fltk.fegen.fltk_cst_protocol`). When that flag is provided, it also generates a `.pyi` stub that references that protocol. But it never writes a protocol `.py` file itself -- it expects someone else (typically the Python `generate` command) to have already produced the protocol.

- **`gen-rust-unparser`** (the Rust unparser path): analogous to `gen-rust-cst` for the unparser, with the same optional `--protocol-module` / `--pyi-output` pattern.

### Bazel rules

- **`generate_parser`** (Python, in `rules.bzl`): wraps the `generate` CLI subcommand. It declares output files for the CST and parsers, but does *not* declare the protocol file. The CLI still writes the protocol into Bazel's action directory, but because Bazel does not track it, it is invisible to downstream targets. This means no existing Bazel consumer has ever received the protocol as a tracked output -- making any protocol-related change purely additive at the Bazel layer.

- **`generate_rust_parser`** (Rust, in `rust.bzl`): wraps `gen-rust-cst` and `gen-rust-parser`. It declares only `cst.rs` and `parser.rs` as outputs. It does not pass `--protocol-module` or `--pyi-output`, so no `.pyi` is produced. No protocol-related attributes exist on the rule.

- **`fltk_pyo3_cdylib`** (also in `rust.bzl`): a macro that takes the `.rs` files from `generate_rust_parser` and assembles them into a compiled Python extension (a `.so`/`.pyd`). It copies all files from its input into a build directory and compiles them. This is relevant because once the Rust rule starts outputting `.pyi` files alongside `.rs` files, those `.pyi` files will flow into this macro's copy step. The design confirms this is harmless: the macro only declares `.rs` files as its outputs, so the `.pyi` files are stray files that Bazel discards. Rustc also ignores them.

### Stub packages

For pyright to find `.pyi` stubs, the stubs need to live in a "stub package" -- a directory with an `__init__.pyi` file. The existing in-tree stubs live under `fltk/_stubs/`, where each subdirectory has a hand-authored `__init__.pyi` (just a comment-only marker file with no real content) alongside the generated `.pyi` stubs. In a Bazel sandbox, those hand-authored markers do not exist, so whatever produces the `.pyi` also needs to produce the `__init__.pyi` marker.

### The Makefile

The `make gencode` target is the canonical way to regenerate all committed generated code in-tree. It invokes the CLI directly with specific flag combinations for each grammar. After regeneration, `make fix` normalizes formatting, and then the results are committed. This is the primary integration-test surface for the generators.

## What we are going to do and why

### Python protocol generation becomes opt-in

A new `--protocol` flag (default off) is added to the `generate` subcommand. When set, the protocol module is written alongside the CST and parsers. When unset, the protocol is not written.

The existing `--protocol-only` flag is unchanged -- it continues to skip the CST and parsers while emitting the protocol. If both `--protocol` and `--protocol-only` are passed together, `--protocol-only` wins (it already short-circuits the rest of the command before the redundancy matters, so no new validation logic is needed).

The reason for this change is the explicit requirement that protocol generation be opt-in for both backends. The alternative -- leaving the Python path unconditional -- would create an asymmetry where the Python backend always emits the protocol and the Rust backend only does so on request.

This is a deliberate breaking change to the CLI default. Any caller that previously relied on `generate` producing the protocol as a side effect must now pass `--protocol`. The Makefile's five Python `generate` invocations are updated to include `--protocol` so the committed protocol files continue to regenerate. Bazel consumers, however, are not affected: the protocol was never a declared Bazel output, so no Bazel target could have depended on it.

### The Rust generator gains the ability to produce the protocol module

A new `--protocol-output PATH` option is added to `gen-rust-cst`. When provided (along with the existing `--protocol-module` flag that supplies the dotted import path), the command writes the protocol `.py` to the specified path. It also emits the `.pyi` stub (driven, as today, by `--protocol-module` being present). So opting into protocol output yields both the protocol file and the stub -- no separate stub opt-in is needed.

The reason `--protocol-output` requires `--protocol-module` rather than working alone is structural: the `.pyi` stub contains a literal `import {protocol_module} as _proto` line and needs the dotted Python import path. That import path is not derivable from the output file path -- they are independent strings (a file at `output/cst_protocol.py` tells you nothing about whether it will be importable as `fltk.fegen.fltk_cst_protocol` or `myapp.grammar_protocol`). Producing the protocol `.py` without the import path needed for the `.pyi` would leave the system in a half-configured state. Supplying `--protocol-output` without `--protocol-module` is rejected as a CLI error.

The requirement as originally stated envisioned a "single opt-in" where enabling protocol output on the Rust generator would be sufficient to also get the `.pyi`, without separately passing `--protocol-module`. The design does not honor this literally because the single-opt-in model is under-specified -- it does not account for the file-path-versus-import-path distinction. The user confirmed this two-flag coupling as the accepted design.

Existing behavior when only `--protocol-module` is passed (no `--protocol-output`) is unchanged: only the `.pyi` is produced, no protocol `.py` is written. This preserves the current workflow where the Makefile generates protocols via the Python path and only passes `--protocol-module` to the Rust path for `.pyi` emission.

### Byte-identity between the Python and Rust protocol paths

The protocol module is structurally backend-agnostic -- it describes the contract, not the implementation. Both paths must produce byte-identical output for the same grammar.

There is a subtle trap that makes this non-trivial. The protocol generation code lives in a class called `CstGenerator`. One of its behaviors depends on whether the `py_module` it was constructed with has a non-empty `import_path`. If the path is non-empty (truthy), each protocol class gets a `kind` attribute typed as `typing.Literal[NodeKind.SomeRule]` -- a precise type discriminant that lets type checkers narrow node types. If the path is empty (falsy), it falls back to a degraded `kind: object` form that provides no type narrowing.

The Rust generator internally holds a `CstGenerator` instance, but it constructs it with a built-in placeholder module whose `import_path` is empty. If the Rust path naively called that instance's protocol generator, it would get the degraded form, producing a structurally weaker protocol that differs from the Python path's output.

The design addresses this by having the Rust generator's new `generate_protocol()` method construct its own protocol generator with a non-empty `import_path`. The actual value does not matter (it never appears in the protocol output -- only its truthiness is checked), so any non-empty placeholder works. The existing internal `CstGenerator` instance is left untouched since it backs `.rs` and `.pyi` generation and must not change.

Additionally, the existing test infrastructure includes a helper (`make_generator`) that also constructs with the empty-path placeholder. The design flags this as an implementer hazard: the new `generate_protocol()` method and any supporting test infrastructure must not be built on that helper.

To prevent the two paths from drifting apart over time, the design calls for factoring the protocol text production into a shared helper so both CLI commands render protocol bytes through a single code path. The exact factoring is left to the implementer, because a byte-identity test serves as the hard guardrail regardless of how the code is organized.

### Stub-package markers become generator-produced

Both `.pyi`-producing subcommands (`gen-rust-cst` and `gen-rust-unparser`) gain three new options: `--init-pyi-output PATH`, `--extension-name NAME`, and `--submodules CSV`. When `--init-pyi-output` is set, the subcommand writes a stub-package `__init__.pyi` marker at the given path. The marker is comment-only text that names the extension and its submodules, carrying the same informative explanation the hand-authored markers had.

A new helper function, `render_stub_package_init`, is added to `gsm2lib_rs.py` (the existing home for module-layout templating) to produce this marker text. This helper is grammar-independent -- it takes only the extension name and the list of submodules. Because the output is pure comments plus a trailing newline, it is stable under formatting tools -- ruff leaves it byte-identical, which keeps the regeneration drift check clean.

The marker is also independent of `--protocol-module` -- it references no protocol and only describes package structure. This independence matters for a practical routing issue: one of the in-tree test fixtures gets its `.pyi` from the unparser path (`gen-rust-unparser`), not from the CST path, because that fixture's `gen-rust-cst` invocation does not use `--protocol-module` and produces no `cst.pyi`. The marker can be attached to whichever invocation already writes a `.pyi` for a given package.

Validation follows the same pattern as other flag interactions: `--init-pyi-output` requires both `--extension-name` and `--submodules`, and each value is checked as a valid identifier before any file is written.

This supersedes an earlier plan to keep the in-tree markers hand-authored and scope generation to Bazel only. The motivation is dogfooding: the markers are now produced through the same generator/CLI path as every other stub, giving a single maintenance point for their content. Both the Bazel rule and the Makefile use this same CLI path. One concrete benefit: the regenerated marker for the `fegen_rust_cst` package now correctly lists `unparser` as a submodule, fixing a pre-existing staleness in the hand-authored marker that omitted it.

### The `.rs` output is unaffected

The generated Rust source code does not change based on any protocol or `.pyi` flag. This invariant already has a test for the `--protocol-module` flag and is extended to cover the new `--protocol-output` flag.

### Bazel: Python rule gains protocol opt-in

A new boolean attribute `protocol` (default false) is added to the `generate_parser` Bazel rule. When true, the rule passes `--protocol` to the CLI and declares `{base_name}_cst_protocol.py` as a tracked output. When false, nothing changes from today's behavior.

This is purely additive. Existing `generate_parser` targets are unaffected because the default is off.

### Bazel: Rust rule gains `.pyi` and protocol opt-in

Two new attributes are added to the `generate_rust_parser` Bazel rule:

- **`protocol_module`** (string, default empty): the dotted import path for the protocol. When non-empty, the rule passes `--protocol-module` and `--pyi-output` to the `gen-rust-cst` action for the `.pyi` stub. The same action also receives the `--init-pyi-output`, `--extension-name`, and `--submodules` flags, producing the stub-package marker through the same generator/CLI path used by the Makefile and the in-tree dogfooded markers -- not a Bazel-specific `ctx.actions.write` mechanism. The rule name doubles as the extension name (the convention already established for `{name}/cst.pyi`), and the submodule list is `cst,parser` because those are what `generate_rust_parser` produces. The rule declares two new outputs: `{name}/cst.pyi` and `{name}/__init__.pyi`, making the `{name}/` directory a complete stub package in the Bazel sandbox so pyright resolves it without a separately committed marker.

- **`generate_protocol`** (boolean, default false): when true (requires `protocol_module` to be non-empty), the rule additionally passes `--protocol-output` and declares `{name}/cst_protocol.py` as a tracked output.

Setting `generate_protocol` to true without providing `protocol_module` is a rule-time error (the rule calls `fail()`), mirroring the CLI's validation. This surfaces the misconfiguration at Bazel analysis time rather than at build time.

No new Bazel rule is introduced -- both new capabilities are attributes on existing rules. Placing the resulting stub-package directory onto a particular consumer's pyright stub path remains that consumer's build-integration step -- this design only ensures the artifacts exist as tracked outputs.

### The `.pyi` flows harmlessly into a downstream Bazel macro

The `fltk_pyo3_cdylib` macro assembles `.rs` sources from `generate_rust_parser` into a compiled crate. Once the Rust rule starts declaring `.pyi` files as outputs, they get pulled into the assembly step because the macro copies all files from its input. The design notes this is benign: the macro only declares `.rs` files as its own outputs, so Bazel discards undeclared files; rustc compiles only `.rs` modules and never reads `.pyi` files; and the existing file-existence guards still pass. The implementer should confirm this with a build. If it ever becomes a problem, the fix is to filter `.pyi` files out of the genrule's copy loop rather than changing the output declarations.

### Makefile: dogfood the in-tree stub-package markers

The Makefile's `gencode` target is updated in several ways:

- The five Python `generate` invocations all gain `--protocol` so the committed protocol files continue to regenerate under the new default-off behavior.

- The existing `fegen` `gen-rust-cst` invocation (which already writes `cst.pyi`) gains the `--init-pyi-output`, `--extension-name`, and `--submodules` flags so it also regenerates `fltk/_stubs/fegen_rust_cst/__init__.pyi`. The regenerated marker now correctly lists `unparser` as a submodule, fixing the pre-existing staleness in the hand-authored version.

- The existing fixture `gen-rust-unparser` invocation (which already writes `unparser.pyi`) gains the same marker flags so it also regenerates `fltk/_stubs/rust_parser_fixture/__init__.pyi`. This routing is deliberate: the fixture's `gen-rust-cst` invocation does not use `--protocol-module` and writes no `cst.pyi`, so the marker is attached to the unparser invocation instead. No new `cst.pyi` is introduced for the fixture.

- Both regenerated markers are comment-only and formatting-stable, so the regen-then-format-then-commit flow leaves them byte-identical. The `make gencode` drift check (comparing committed versus regenerated files) now covers these markers like every other generated artifact.

- The `--protocol-output` flag is not used in the Makefile's in-tree corpus (in-tree protocols are committed via the Python path), but it is exercised by tests.

- One file is explicitly out of scope: `fltk/_native/__init__.pyi` is a substantive hand-written type stub (it describes `Span`, `SourceText`, and `UnknownSpan`), not a stub-package marker. It is left untouched.

## What could go wrong and how it is handled

**Silent protocol divergence between backends.** The central risk. If the Rust path's protocol generator were accidentally constructed with an empty module path, every rule would get the degraded `kind: object` form instead of the precise `Literal` discriminant, producing a structurally weaker protocol. A consumer regenerating their grammar's protocol via the Rust path would silently get a different file than the Python path produces. This is mitigated by using a non-empty module path in the Rust generator's `generate_protocol()` method and pinned by a cross-path byte-identity test: the protocol produced by `gen-rust-cst --protocol-module X --protocol-output P` must be byte-identical to the one produced by `generate --protocol` (and `--protocol-only`) for the same grammar.

**Incomplete flag combinations.** `--protocol-output` without `--protocol-module` is rejected at the CLI before any file is written. `--init-pyi-output` without `--extension-name` or `--submodules` is likewise rejected. At the Bazel layer, `generate_protocol=True` without `protocol_module` causes a `fail()` at analysis time. All validations prevent half-configured states and are checked before any file is opened.

**Partial files on generation error.** The existing convention -- generate all artifact text in memory before opening any file for writing -- is extended to cover the new protocol `.py` and `__init__.pyi` outputs. If text generation fails, no files are written.

**Invalid values for `--protocol-module`, `--extension-name`, or `--submodules`.** The protocol module value is validated against a regex for dotted Python identifiers. The extension name and each submodule entry are validated as identifiers. All checks run before any file write.

**Breaking out-of-tree CLI callers.** Making the Python protocol default-off is an accepted, explicitly requested breaking change. The migration path is straightforward: add `--protocol` to the command. Bazel consumers are insulated because the protocol was never a declared Bazel output and no target could have depended on it.

**Protocol module does not exist at the declared import path.** When `--protocol-module` is provided but `--protocol-output` is not (the "protocol was generated separately" case), the `.pyi` is emitted with an import of that module. Whether the module actually exists and is importable at runtime or at type-checking time is the consumer's responsibility -- the rule does not verify importability. This matches today's behavior.

**Both invocations for a package write the same marker path.** If both a package's `gen-rust-cst` and `gen-rust-unparser` invocations were given `--init-pyi-output` for the same path, the later write would win. The Makefile avoids this by attaching the flag to exactly one invocation per package.

**Generated marker drifts under formatting.** The marker is pure comments plus a trailing newline, so ruff format and ruff check leave it byte-identical. The `make gencode` drift check now covers both in-tree markers.

## What was resolved during the design process

All design questions were resolved before the design was finalized. No open questions remain.

**Should the Bazel rule generate the stub-package `__init__.pyi`?** Yes. `generate_rust_parser` generates and declares the `__init__.pyi` alongside `cst.pyi` whenever `protocol_module` is set. The marker is produced through the shared `--init-pyi-output` generator/CLI path -- the same path used by the Makefile and the in-tree dogfooded markers -- so the marker content stays a single maintenance point. Placing the resulting stub-package directory onto a particular consumer's pyright stub path remains that consumer's build-integration step.

**Should the Rust protocol opt-in require two flags, or should one flag suffice?** Two flags. The protocol's dotted import path is a required input, supplied explicitly via `--protocol-module` (Bazel `protocol_module`), and is not auto-derived from co-generating the protocol. The `.pyi` is emitted whenever that import path is supplied; `--protocol-output` / `generate_protocol` only additionally writes the protocol `.py`. The original requirement's "single opt-in" wording is treated as under-specified for the CLI because the `.pyi`'s `import {protocol_module} as _proto` line needs the dotted import path, which is independent of any output file path.

**Should the in-tree stub-package markers stay hand-authored or become generator-produced?** Generator-produced, superseding the earlier plan that the markers would stay hand-authored and that generation would be scoped to Bazel only. Both in-tree markers are now regenerated by `make gencode` through the same CLI path (`--init-pyi-output` / `--extension-name` / `--submodules`) that the Bazel rule uses. This means the marker content has a single maintenance point shared between the Makefile and Bazel paths. The `fltk/_native/__init__.pyi` file is out of scope -- it is a substantive hand-written type stub, not a package marker.
