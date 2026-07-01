# ELI5: Unifying FLTK's Bazel parser-codegen surface

## What this is about

FLTK (Formal Language ToolKit) is a library that takes grammar files and generates parsers from them -- programs that can read structured text and break it into a tree of meaningful pieces called a Concrete Syntax Tree (CST). The generated parsers, CST node classes, and related artifacts are public API: real applications outside this repository depend on them and build against them.

FLTK can generate parsers in two languages: Python and Rust. The Python backend produces `.py` files you can import directly. The Rust backend produces `.rs` source files that must be compiled further. When the Rust backend is used to build a Python extension (so that Python code can call into fast Rust-compiled parsers), there is additional machinery: the Rust source gets compiled into a shared library, renamed to follow Python's binary-extension naming conventions, and wrapped as a Python package.

All of this build orchestration is expressed in Bazel, a build system where you define targets and their relationships in configuration files. Bazel offers two kinds of abstractions: "rules" (which define a single build action) and "macros" (which are ordinary functions that can instantiate multiple rules and wire them together). This distinction matters because some of the work -- like compiling Rust, renaming the output, and packaging it for Python -- requires spinning up several targets, which only a macro can do.

The problem is that the Bazel-facing surface for these two backends drifted apart as features were added. The same concepts are spelled differently, the Rust path requires two separate, manually-coordinated calls where one would suffice, and a latent bug means a certain output directory would be named after the wrong thing if anyone turned on the feature that triggers it. This design cleans all three problems up.

## The relevant parts of the system

To follow the rest of this document, you need to know about four building blocks that FLTK ships for Bazel consumers.

**`generate_parser`** is the Python-backend rule. You give it a grammar file, and it produces Python source files: the CST node classes, the parser(s), and optionally a "protocol module" -- a set of typing-only Protocol definitions describing the CST surface, useful for type checking. The protocol module is opt-in via a boolean attribute called `protocol`.

**`generate_rust_parser`** is the Rust-backend rule. It runs two codegen actions (one for CST, one for the parser) and produces Rust source files: `cst.rs` and `parser.rs`. It can also optionally emit `.pyi` type-stub files (for Python type checkers to understand the compiled extension) and the same protocol `.py` module the Python backend can produce. Two attributes control these extras: a string called `protocol_module` (which, when non-empty, triggers `.pyi` stub emission) and a boolean called `generate_protocol` (which triggers the protocol `.py` file and requires `protocol_module` to also be set).

**`fltk_pyo3_cdylib`** is a macro that takes the `.rs` files from a `generate_rust_parser` target and turns them into an importable Python extension module. It does this in four steps: optionally synthesize a `lib.rs` entry point; copy all the Rust source into a single flat crate directory; compile it into a shared library (cdylib); rename the shared library to match the Python ABI; and wrap it in a `py_library` so downstream Python targets can depend on it.

**Why one cdylib, not two.** The CST and parser are compiled together into a single extension module with submodules. This is not incidental -- they share Rust types exposed to Python, and splitting them into separate compiled libraries would break Python's type identity (a `CstNode` from one library would not be the same type as a `CstNode` from another). Because they live in one module with submodules, the type stubs must be a PEP 561 "stub package" -- a directory named after the module, containing per-submodule `.pyi` files and an `__init__.pyi` marker -- rather than a single flat stub file.

## Three problems with the current shape

### Problem 1: Gratuitous name divergence

The Python rule opts into the protocol module with a boolean called `protocol`. The Rust rule opts into the same thing with a boolean called `generate_protocol`. There is no reason for the names to differ; the concept is identical.

### Problem 2: Two-call surface for Rust consumers

A consumer who wants a Rust-backed Python extension must make two separate calls in their Bazel configuration: first `generate_rust_parser` to produce the `.rs` files, then `fltk_pyo3_cdylib` to compile them into an importable module. The consumer must manually thread the first target's label into the second's `rs_srcs` attribute. This is ceremony that could be eliminated by a single unified entry point.

### Problem 3: A latent stub-directory naming bug

This is the subtlest problem and worth understanding precisely.

The `.pyi` stub package must be a directory named after the compiled Python module -- the thing you actually `import` in Python. That module name comes from the `fltk_pyo3_cdylib` macro's `name` attribute (it becomes the crate name, the `#[pymodule]` function name, and the importable module name). But the codegen rule `generate_rust_parser` derives both the stub-package directory name and the `--extension-name` CLI flag from its own, separate `name` attribute. These two names are independently chosen strings on two separate targets, and nothing connects them.

In the one real-world consumer (an application called Clockwork), the codegen rule is named `clockwork_rs_srcs` and the cdylib macro is named `clockwork_native`. If anyone turned on `protocol_module`, the stub package would be created under `clockwork_rs_srcs/` -- but the module it is supposed to describe is called `clockwork_native`. The stubs would not match the module they type. This bug is latent only because no one has turned on that feature yet; but it would bite the moment someone does.

## What the design does and why

### Decision 1: Rename the Rust protocol toggle

The Rust boolean `generate_protocol` is renamed to `protocol`, matching the Python rule. The string attribute `protocol_module` (the dotted import path for `.pyi` generation) keeps its name -- it has no Python-side counterpart and is not part of the divergence. The existing relationship between the two -- `protocol = True` requires `protocol_module` to be non-empty -- is preserved exactly as-is, including both the Bazel analysis-time guard and the CLI's own validation. This is a pure naming unification.

**Why this over the alternative:** The Python rule's `protocol` is the simpler, more natural name. The `generate_` prefix on the Rust side was needless verbosity that made the two backends look more different than they are.

### Decision 2: Split `generate_rust_parser` into an internal rule and a public macro

The current `generate_rust_parser` rule is renamed to a private internal rule (`_generate_rust_srcs`). A new macro -- also called `generate_rust_parser` -- becomes the single thing consumers call. The macro instantiates the internal codegen rule and, when Python support is enabled, also folds in everything `fltk_pyo3_cdylib` does today.

The internal rule gains one new attribute: `extension_name`. When non-empty, this value (rather than the rule's own target name) is used as both the `--extension-name` CLI argument and the output subdirectory name. This is the structural fix for the stub-directory bug: the macro sets `extension_name` to its own `name`, which is simultaneously the compiled module name. There is no second, divergent name to get out of sync.

The internal rule exposes its outputs through two named output groups (a Bazel mechanism for tagging subsets of a target's outputs):

- `rust_srcs` -- always contains `cst.rs` and `parser.rs`.
- `stub_srcs` -- contains the `.pyi` stubs and the protocol `.py` module when they are generated, and is empty otherwise.

**Why output groups matter:** A Bazel macro cannot address individual declared files by label from another target -- it can only see the target as a whole and its providers. Without output groups, the macro would have no clean way to route the `.rs` files to crate assembly while keeping the `.pyi` and `.py` files out of it. The groups make this routing explicit: crate assembly gets only `rust_srcs` (no stray `.pyi` files end up in the crate root), and the public `py_library` gets `stub_srcs` as data (so downstream dependents receive both the compiled extension and the type stubs). When stubs are not enabled, `stub_srcs` is an empty set, so nothing dangling is referenced.

### Decision 3: A Python-extension toggle on the macro

The macro takes a boolean called `python_extension` (default `False`):

- **`python_extension = False` (the default)** produces pure Rust output only. The internal codegen rule is instantiated directly as the public target, emitting just `cst.rs` and `parser.rs`. No cdylib, no stubs, no Python packaging. The consumer drops these `.rs` files into their own Rust crate.

- **`python_extension = True`** builds the full Python extension. The internal codegen rule is instantiated as a private target (`name + "_srcs"`), and its Rust outputs are fed through crate assembly, cdylib compilation, ABI renaming, and `py_library` wrapping -- all the steps `fltk_pyo3_cdylib` performs today. The public target (`:name`) is the resulting `py_library`.

**Why `python_extension` as the name:** It self-documents intent. Alternatives considered and rejected: `python` (too generic -- could mean many things), `pyo3` (leaks the implementation detail of which Rust-Python binding is used), `build_python` (unnecessarily verb-like).

**Stub emission within the `python_extension = True` path** remains optional and gated on `protocol_module`, exactly as today:

- `protocol_module` empty: cdylib and `py_library` only. No stubs.
- `protocol_module` set: additionally emits `cst.pyi` and `__init__.pyi` in a stub-package directory named after `name` (the module). This is where the bug fix is visible -- the directory is now guaranteed to match the compiled module.
- `protocol_module` set and `protocol = True`: additionally emits the `cst_protocol.py` module.

### Decision 4: Demote `fltk_pyo3_cdylib` to an internal helper

Rather than deleting the working four-step cdylib-building logic and its extensive comments, the design renames it to a private function (`_build_pyo3_cdylib`) and calls it from the macro's `python_extension = True` branch. The public name `fltk_pyo3_cdylib` is removed from the exported surface -- it no longer appears in load statements or documentation. Breaking the existing two-call surface is explicitly permitted by the requirements.

**Why demote rather than delete:** The logic is working, well-commented, and non-trivial. Inlining it into the macro or rewriting it would risk introducing bugs for no gain. Keeping it as a private helper preserves the code while removing the public surface that consumers had to coordinate manually.

### Decision 5: Update in-tree targets to stay green

FLTK's own `BUILD.bazel` has two smoke targets that exercise the Rust path: `bootstrap_rust_srcs` (the codegen rule) and `bootstrap_native` (the cdylib macro). These are rewritten to use the new unified macro:

- `bootstrap_rust_srcs` with `python_extension = False` -- exercises the pure-Rust path.
- `bootstrap_native` with `python_extension = True`, `protocol_module` set, and `protocol = True` -- exercises the full Python path including stub-package emission. This is significant because no in-tree target exercises stub emission today. Adding it turns the latent stub-directory bug into an actively built regression case: if the stub package directory is ever named after the wrong thing, this target will fail.

The Makefile's code-regeneration path is unaffected because it invokes the CLI directly with flags that are not being renamed. The Python `generate_parser` rule is also untouched.

### What is not changing

The CLI (`genparser.py`) already accepts all necessary flags (`--extension-name`, `--protocol-module`, `--protocol-output`, `--init-pyi-output`, `--submodules`). No CLI changes are needed; all the work lives in the Bazel layer.

The generated artifacts themselves -- the content of `cst.rs`, `parser.rs`, `cst.pyi`, `cst_protocol.py` -- are byte-identical to what they are today for the same grammar. Only the Bazel wiring and the stub-directory name change. Existing generator-level tests remain valid without modification.

## What could go wrong and how it is handled

**Setting Python-only attributes in pure-Rust mode.** If a consumer sets `protocol_module`, `protocol`, `lib_rs`, `deps`, `crate_features`, or a non-default `recursion_limit` while `python_extension = False`, that is a misconfiguration -- pure Rust produces no cdylib or stubs, so those attributes have no meaning. The macro fails at evaluation time with a message naming the offending attribute and pointing at `python_extension`. Failing fast is preferred over silently ignoring the values, which would hide the mistake.

**`protocol = True` with empty `protocol_module`.** This is still rejected, as it is today. The guard lives in both the internal rule (analysis time) and the CLI (runtime). The macro may additionally fail early for a clearer error message.

**Directory and target name collision.** In `python_extension = True` mode, the internal rule (target `name + "_srcs"`) declares output files under the directory `name/`, while the `py_library` target is also called `name`. These are distinct Bazel labels (`//pkg:name/cst.rs` vs `//pkg:name`) and should not collide, but this is the one non-obvious property of the single-name design. It must be confirmed by actually building the smoke target.

**Stub and protocol files leaking into crate assembly.** The internal rule's default output bundle includes both `.rs` and (when enabled) `.pyi`/`.py` files. If the crate-assembly step consumed the whole target, the non-Rust files would end up in the flat crate root. Bazel would likely discard them (they would be undeclared genrule outputs), but the design does not rely on that grace: crate assembly consumes only the `rust_srcs` output group, so no `.pyi` or `.py` file ever enters the crate root. The `bootstrap_native` smoke target with protocol enabled is the regression guard for this.

**The `lib.rs` basename hazard.** The old `fltk_pyo3_cdylib` warned callers never to pass an `rs_srcs` target whose outputs include a file named `lib.rs` (it would collide with the synthesized entry point). With the codegen rule now internal and always the macro's own, this hazard is no longer consumer-reachable. The guard comment moves into the private helper as an internal invariant.

## What is still open

The design declares no open questions. The two choices the requirements delegated to the design phase -- the toggle attribute name and whether to delete or demote `fltk_pyo3_cdylib` -- are both decided: the toggle is `python_extension`, and `fltk_pyo3_cdylib` is demoted to a private helper. No remaining question requires judgment from outside the design.
