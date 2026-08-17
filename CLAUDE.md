# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

FLTK (Formal Language ToolKit) is a Python library for building parsers and compilers. It uses a custom grammar format (.fltkg files) to generate parsers that produce Concrete Syntax Trees (CST).

## CRITICAL: Generated Output is Public API for Out-of-Tree Consumers

FLTK's PRIMARY purpose is to be used by OTHER, OUT-OF-TREE applications. External downstream apps use FLTK to generate their own parsers and CST node classes, then write application code against those generated artifacts. The generated CST node classes, parsers, label enums, accessor methods, and their type-annotation and equality/comparison surfaces are **public API consumed by real downstream consumers who live outside this repo**.

**When evaluating whether a change is "needed" or "breaking": the absence of an in-tree consumer is NOT evidence the change is safe.** The real consumers live outside this repository and are not visible here.

Concrete consequences:

- Renaming generated public symbols (e.g. adding a `Node` suffix to class names) is a **breaking change** for downstream code.
- Changing the type-annotation surface in ways that force downstream callers to update every function or parameter annotation is also a breaking change.
- The explicit goal of the Rust-backend work is a near-drop-in replacement for the Python backend: downstream consumers may need to update import statements, but must **not** be forced to edit their type annotations or call sites wholesale.
- Backward compatibility and cross-backend (Python/Rust) behavioral equivalence must be evaluated from the perspective of out-of-tree consumers, not just FLTK's self-hosting tests.
- Do not rename generated public symbols or otherwise cause annotation churn unless the need is explicit, justified, and unavoidable — and even then it must be a deliberate, called-out decision, not an incidental side effect of an implementation choice.

## Development Commands

### Testing

Tests run under Bazel — one `py_test` per pytest file, plus the Rust and Starlark test targets.
There is no pytest lane outside Bazel: the generated modules and the extension cdylibs the suite
imports are build outputs, not files in the source tree.

```bash
# Run all tests
bazel test //...

# Run tests with coverage
bazel coverage //...

# Run one test file (see "The pytest suite under Bazel" for the naming rule)
bazel test //tests:test_span
```

### Linting and Formatting

Ruff and pyright run under Bazel. `bazel build --config lint //...` is the whole lint
surface — the rules_rust clippy aspect plus `//:ruff_check`, `//:ruff_format_check` and
`//:pyright` — and it is what `make bazel-lint` runs. The Python lint targets are gated on
`--//bzl:lint` (which `--config lint` sets), so a plain `bazel build //...` skips them
entirely.

```bash
# Everything: clippy + ruff check + ruff format --check + pyright
bazel build --config lint //...

# Just the Python half
bazel build --config lint //:ruff_check //:ruff_format_check //:pyright

# Fix auto-fixable issues and reformat, in your working tree
make fix          # == bazel run //:ruff_fix
```

The ruff pin lives in `requirements.in`/`requirements_lock.txt`, and the settings that shape
generated code live in `gencode-ruff.toml`, which `pyproject.toml`'s `[tool.ruff]` `extend`s.
Put anything that affects emitted code in `gencode-ruff.toml`; repo-local-only settings
(per-file-ignores and the like) stay in `pyproject.toml`.

`//:pyright` stages its sources into one declared directory next to a generated
`pyrightconfig.json` and runs the pyright bundled inside the `pyright` wheel under the node
binary from the `nodejs-wheel-binaries` wheel — no network, no virtualenv. The config is
derived from `[tool.pyright]` in `pyproject.toml`, minus `venvPath`: third-party imports
resolve through `extraPaths` entries pointing at the hub wheels named in the target's `deps`,
so a new third-party import in checked code needs that package added there.

### Generated Code and Formatting

Generated Python is normalized by the generator itself: every command that writes a `.py` or a `.pyi` (`generate`, `gen-ast`, `gen-rust-cst --protocol-output`, and the `.pyi` stubs the `gen-rust-cst` / `gen-rust-unparser` / `gen-rust-all` paths emit) runs `ruff check --fix` → `ruff format` → `ruff check --fix` over what it wrote before exiting. So generated code is format-clean straight out of the generator, and the old regen → `make fix` → commit dance is gone. Generated Rust is emitted pre-formatted and is untouched by this.

The pipeline lives in `fltk/fegen/gencode_format.py`. Both halves are pinned, never discovered: the ruff binary comes from the wheel the generator depends on, and the config is `gencode-ruff.toml`, passed explicitly with `--config` at every invocation. That is what makes generated output a function of (grammar, generator, pinned ruff, pinned config) alone — a Bazel action sees only its declared inputs, and config discovery from the action's working directory would mean a downstream consumer's own `pyproject.toml` reshaped what FLTK generates for them. A ruff bump or a `gencode-ruff.toml` edit can therefore change generated bytes; that is intended, and `tests/test_seed_fixed_point.py` is what makes it visible.

The self-hosting seed (`fltk/fegen/{fltk_cst,fltk_cst_protocol,fltk_parser,fltk_trivia_parser}.py`) is the one generated artifact that stays committed — the generator needs it to read any grammar file, including the one it is generated from. `tests/test_seed_fixed_point.py` regenerates it and byte-compares, so a generator change without a regeneration is a red test rather than a seed quietly describing a language the code no longer implements. Regenerate it with `make regen-seed` (`bazel run //:regen_seed`), the one entry point that writes generated code back into the source tree, and commit the result.

### Python-backend codegen layering

`fltk/fegen/pybackend.py` is the whole Python generation path, and its transitive imports are hand-written modules plus the seed. Keep it that way: the generators reachable from `genparser.py` import the *generated* aux modules at module level (`gsm2parser_rs` → `regex_parser`, `ast_config` → `fltkast_parser`, `plumbing` → `unparsefmt_parser` / `fltklsp_parser`), so `genparser.py` cannot be what brings those into existence. `fltk/fegen/genparser_stage0.py` is a minimal CLI over `pybackend` for exactly that job; `generate_parser(gen_tool = "//:genparser_stage0")` selects it. `genparser.py`'s own `generate` command is a thin wrapper over the same function — there is exactly one writer of Python-backend output, and the seed's fixed-point property depends on that staying true.

The Python unparser has the same shape: `genparser gen-py-unparser` writes `<base_name>_unparser.py` through `fltk.plumbing.generate_unparser_source`, which is also what the in-process `generate_unparser` and the `fltk/unparse/genunparser.py` dump script go through. `generate_parser(unparser = True, format_config = ...)` is the Bazel surface over it. It needs the full `:genparser` — stage-0 has the `generate` command only.

### Rust-backend codegen: one process per grammar

`genparser gen-rust-all` emits every requested Rust artifact for a grammar in one process:
`--cst-output` is required and each of `--parser-output` / `--unparser-output` / `--ast-output`
/ `--serde-output` (plus the `.pyi` / protocol / stub-marker outputs) is written exactly when
its option is given. `generate_rust_parser` runs only this form — one `ctx.actions.run`
declaring every output — so a grammar with five generated modules costs one interpreter startup
and one grammar parse instead of five.

The five single-purpose subcommands (`gen-rust-cst`, `gen-rust-parser`, `gen-rust-unparser`,
`gen-rust-ast`, `gen-rust-serde`) stay: they are the documented ad-hoc and guide recipes.
Nothing in this repo drives them anymore — every generated `.rs` here is a Bazel action output —
so an ad-hoc run is `bazel run --run_under="cd $PWD &&" //:genparser -- ...`: the Rust-backend
generators import the aux Python modules, those are Bazel outputs, and `--run_under` is what
makes a relative output path mean a path in the source tree rather than one in the runfiles.
All of them share the per-artifact emitters in `genparser.py`
with `gen-rust-all`, and `tests/test_gen_rust_all.py` pins byte-identity across the two paths —
add a new artifact to both or to neither, or the same grammar generates two different trees.
In `gen-rust-all` every emitted file is named by its own option, with no defaulted paths: the
Bazel action has to declare all of them.

### Where the generated Rust and its stubs come from

Nothing generated is in git except the seed and `src/lib.rs` (`TODO(bazel-generated-native-lib)`
explains why that one is). The `.rs` for each in-tree crate comes from the `generate_rust_parser`
target in its own package — `//crates/fegen-rust`, `//tests/rust_poc_cst`,
`//tests/rust_cst_fixture`, `//tests/rust_parser_fixture` — with `out_dir = "src"`, so the
generated modules land beside the hand-written crate root and each package's glob excludes their
basenames so a stray in-tree copy cannot shadow them.

The two PEP 561 stub packages are Bazel outputs too, staged at their own package paths:
`crates/fegen-rust/fegen_rust_cst/` (from `//crates/fegen-rust:fegen_rust_cst_stub_srcs`, the
`stub_srcs` output group of the extension-flavor codegen) and
`tests/rust_parser_fixture/rust_parser_fixture/` (from
`//tests/rust_parser_fixture:fixture_srcs_stub_srcs`). That fixture's crate is hand-assembled, so
its stubs ride its pure-Rust codegen target: `generate_rust_parser` emits the stub package
whenever `protocol_module` is set, `extension_name` names the stub directory, and `submodules`
is what makes the `__init__.pyi` marker name all six modules the crate root registers. A separate
stubs-only target would re-parse the grammar and regenerate the tree's largest artifact to throw
it away. A type checker reaches a stub package by putting the directory *holding* it on its
search path; `tests/tree_paths.py` states those paths once for the suites, and `//:pyright`'s
`extra_paths` is the same thing for the repo-wide gate.

### Where the aux generated modules come from

The 24 aux modules (`bootstrap_*`, `regex_*`, `fltkast_*`, `toy_*`, `unparsefmt_*`, `fltklsp_*`) are produced by the `generate_parser` targets `//bzl:aux_grammars.bzl` declares in the root `BUILD.bazel`, each with `gen_tool = ":genparser_stage0"` and an `out_dir` naming its Python package directory; `//tests:rust_parser_fixture_protocol_py` is the same thing for the fixture protocol module. `//:fltk` is `:fltk_src` (the hand-written half and the seed) plus those outputs, so what the library ships is always what the current grammars generate. `//:pyright` type-checks the generated copies for the same reason; `//:ruff_check` and `//:ruff_format_check` skip them, since the generator already normalizes its output against the same pinned config.

None of them is in git — they exist only as build outputs, so there is nothing to regenerate, review or merge, and no way for a checked-in copy to disagree with the grammar it came from. The globs that build `:fltk_src` and the lint targets still exclude their source paths, defensively: an ad-hoc `bazel run //:genparser` aimed at the source tree can leave a copy behind, and an in-tree file would otherwise shadow the generated one. Nothing else in the tree may import from those paths except through `//:fltk`.

### Build System

Bazel is the build system. There is no uv and no maturin, and cargo survives in three narrow roles only: `cargo-deny` (the supply-chain gate, local lane), the `cargo metadata --locked` probe in `check-cargo-lock`, and the three compile-gate pytest targets that hand a throwaway crate to a real compiler driver. No cargo lane builds, tests or lints this repo's code anymore — every crate has Bazel targets in both feature flavors, so `bazel test //...` compiles and runs them and the clippy aspect lints them, over strictly more configurations than the retired lanes covered (fegen-rust, fltkfmt and the three fixture extensions have no Cargo manifest at all).

`make check` is six steps, and four of them are Bazel:

- `bazel-toolchain-guard` — the rust-toolchain.toml/MODULE.bazel mirror check below.
- `make bazel-test` (`bazel test //...` plus the no-pyo3 cquery loop) covers fltk's own internal Bazel surface: the `tests/bazel_rules` analysis tests, the codegen smoke targets, the `:native` cdylib, every pytest file as its own `py_test`, and the `rust_test` targets that run each runtime crate's unit tests on its `:no_python` flavor — plus the feature carve-outs the cargo lanes used to own: `//crates/fltk-ast-core:no_features_test` (every feature off), `//crates/fltk-cst-core:python_test` (the `python` feature set, including the pyclass ABI-layout probes), and `//crates/fegen-rust:native_parser_test` / `//crates/fltkfmt:cli_test`, which build their crates from Bazel-generated sources. The three fixture extensions under `tests/rust_poc_cst`, `tests/rust_cst_fixture` and `tests/rust_parser_fixture` are Bazel targets too, each hand-assembled from its own codegen targets rather than through `fltk_pyo3_cdylib`. The cquery loop is what replaced `check-no-pyo3`: it asserts pyo3 is absent from every `:no_python` target's graph and every `rust_binary`'s.
- `make bazel-lint` (`bazel build --config lint //...`) runs the rules_rust clippy aspect with `-D warnings` over every Rust target in both of its feature flavors, plus the flag-gated Python lint targets `//:ruff_check`, `//:ruff_format_check` and `//:pyright`.
- `make bazel-consumer-check` (`cd tests/bazel_consumer && bazel test //...`) covers the consumer surface — an in-repo downstream module (`tests/bazel_consumer/`) that `bazel_dep`s on `@fltk` via `local_path_override` and loads `@fltk//:rules.bzl` + `@fltk//:rust.bzl` cross-module (the Clockwork path: `generate_parser`, `generate_rust_parser`, `fltk_pyo3_cdylib`), which the same-repo `//` loads of `bazel-test` cannot exercise. Real git-pin consumption is verified downstream by Clockwork's own CI.

The remaining two steps are the lock diffs, `check-cargo-lock` and `check-bazel-locks`. `docs/bazel-consumer-guide.md` is the consumer-facing recipe book (one recipe per supported configuration, the `:no_python` runtime targets, the one-serde rule for serde-mode pure-Rust consumers, and the no-pyo3 verification queries); keep it in step with `rust.bzl` and the crate BUILD files.

**Rust toolchain required**: `rustup` and `cargo` must be installed on your machine. Install via https://rustup.rs/. The compile-gate tests, `cargo-deny` and the lock probe drive it directly; the Bazel lanes use their own hermetic toolchain. Those gates resolve `--offline` and nothing in `make check` fetches, so a fresh clone needs one `cargo fetch --locked` (CI has a step for it).

The exact toolchain version is pinned in `rust-toolchain.toml` (rustup installs it automatically) and CI reads its `channel` from that same file. `make check` denies all clippy warnings, so an unpinned toolchain would let a new stable release break CI on an unchanged commit. Bazel cannot read TOML, so every `MODULE.bazel` that uses rules_rust mirrors the version in a `rust.toolchain(versions = [...])` tag, keeping the Bazel lanes on the same compiler the rustup toolchain gives the compile gates; `make bazel-toolchain-guard` — the first `CHECK_STEPS` entry and a prerequisite of all three Bazel lanes — derives the mirror list from the tracked `MODULE.bazel` files and fails if any of them is stale or missing the tag, so a newly added Bazel workspace cannot silently opt out of the pin. Bumping the pin is a deliberate change: edit `channel` in `rust-toolchain.toml` **and** the `versions` line in every `MODULE.bazel`, run `make check`, and fix any newly-surfaced lints in the same commit.

**Lockfile workflow (single writer per file).** `requirements.in` is the single Python dependency manifest — runtime, test and tool packages alike — and `requirements_lock.txt` has exactly one writer: `bazel run //:requirements.update`. Its gate is `//:requirements.test`, which runs inside `bazel test //...` (i.e. `make bazel-test`), so it has no make-level step. That gate resolves the manifest against PyPI, so **`make check` requires network access**: offline, or during a PyPI outage, it fails at that target rather than at anything to do with the change under test. Its result is cached, so a green run does not re-fetch. `pyproject.toml` declares no dependencies at all now — it is tool config (`[tool.ruff]`, `[tool.pyright]`, `[tool.coverage]`) and nothing else.

Two tracked `Cargo.lock`s remain (the root workspace's and the consumer module's serde hub); every other crate in the tree is Bazel-only and has no manifest. `make check-cargo-lock` is their gate: nothing rewrites a `Cargo.lock` anymore, so the step asks each tracked manifest whether its lock still resolves (`cargo metadata --locked`) and then diffs the tracked set. After editing a `Cargo.toml`, re-resolve the lock (`cargo metadata --manifest-path <it>`) and commit it. Never hand-edit these files or add a second generator (a pip updater, another exporter writing `requirements_lock.txt`) — its edits would be silently clobbered on the next regeneration.

The two `MODULE.bazel.lock` files (repo root and `tests/bazel_consumer/`) are tracked, Bazel-written locks, and bzlmod's default `lockfile_mode` is `update`: a Bazel run repairs a stale one in place and still reports green, so a manifest edit can leave the committed lock wrong indefinitely. `make check-bazel-locks` is the diff that forces the repair to be committed, and it runs last in `CHECK_STEPS` — after `bazel-test` and `bazel-consumer-check`, which are the lanes that do the repairing. Same caveat as above: the diff step alone passes vacuously with no prior Bazel run, so `make check` is the gate that clears them.

**`CARGO_BAZEL_REPIN=1` after editing a `Cargo.toml`.** With an already-populated Bazel output base, a Bazel lane can fail with `no such target '@fltk_crates//:<crate>'` — the crate_universe repos were resolved from the previous manifests. One run with `CARGO_BAZEL_REPIN=1` (e.g. `CARGO_BAZEL_REPIN=1 bazel test //...`) re-resolves them and clears it. A fresh cache, including CI, never sees this.

**Version pin for Bazel.** Bazel is pinned via `.bazelversion` (bazelisk honors it in CI). It is not Dependabot-managed; bump it manually — edit the pin, run `make check`, commit.

**Build and test workflow**:
```bash
# Build everything, run every test
bazel test //...

# The whole lint surface
bazel build --config lint //...
```

No build step precedes the tests. The five extension modules the suite imports (`fltk._native`, `fegen_rust_cst`, `rust_parser_fixture`, `phase4_roundtrip_cst`, `poc_cst`) are Bazel targets named in the deps of the `py_test`s that import them, so a generator change rebuilds exactly the cdylibs it affects before the tests that use them run. The stale-extension false green that the ad-hoc `maturin develop` builds used to allow is gone with them.

### The pytest suite under Bazel

The pytest suite is one `py_test` target per test file, so editing one test file re-runs one target and everything else is a cache hit. Targets are named after the package-relative path with `/` replaced by `_`:

```bash
bazel test //:fltk_unparse_test_unparser        # one file under fltk/
bazel test //tests:test_gsm2tree_py             # one file under tests/
bazel test //:fltk_lsp_test_engine --test_arg=-k --test_arg=positions   # one test
bazel test //tests:test_span --test_output=streamed                     # live output
```

`log_cli = True` output goes to the test log (`bazel-testlogs/<target>/test.log`), not the terminal, unless `--test_output=streamed`.

The inventory is the explicit `fltk_py_tests(tests = {...})` dict — never a glob, so a new test file needs a dict entry. Files under `fltk/` are declared in the **root** `BUILD.bazel`; files under `tests/` in `tests/BUILD.bazel`, with package-relative keys. The macro is its own gate: it takes the package's `glob_pattern` and an optional `deferred` map (file -> why it cannot run in the sandbox yet; both packages are empty of these now) and `fail`s at load time when the three sets do not account for exactly the same files. A test file with no target therefore breaks `bazel build //...` rather than reddening one test. Fixture corpora are named per target (`//:fegen_test_data`, `//:lsp_test_data`), not carried in the base data, so editing one grammar re-runs only the targets that read it. Test files under `fltk/` are declared in the root package on purpose: a BUILD file anywhere under `fltk/` would cut the root package's `fltk/**` globs off at that directory, taking `:fltk_src`, `:fltk` and the lint targets with it.

The suites that type-check their own fixtures run pyright as a subprocess through `tests/pyright_test_utils.py`. That harness runs the npm bundle inside the `pyright` wheel (`pyright/dist/index.js`) under the `node` binary inside `nodejs-wheel-binaries` — the same tool and pin `//:pyright` resolves in Starlark — so one dep, `//bzl:pyright_tool.bzl`'s `PYRIGHT_TOOL_DEPS`, covers both. It writes a `pyrightconfig.json` whose `extraPaths` is the running interpreter's `sys.path`, so **whatever a generated fixture imports must be a dep of the py_test target**, exactly as if the test module imported it itself; there is no venv for pyright to discover.

`tests/` being a package means the root package can no longer glob into it: `//tests:lint_py_srcs` is what keeps those files in `//:ruff_check` / `//:ruff_format_check` / `//:pyright`, and repo-root files a test reads (`Makefile`, `pyproject.toml`, the lock files, `runbs.py`) cross the boundary through `exports_files` in the root `BUILD.bazel`. `fltk_py_test` sets `legacy_create_init = 0`: the empty `__init__.py` rules_python otherwise drops into every runfiles directory turns a fixture crate's source directory into a regular package that shadows the compiled extension module of the same name. A file whose whole coverage sits behind `importorskip` takes `fail_on_skip = True`, which turns a skip into a red test rather than a green run of nothing.

Three files are compile gates: they write a throwaway Cargo crate with path dependencies on this repo's runtime crates and hand it to `cargo`, because "does the generated Rust compile" needs a compiler driver. Their targets carry `tags = ["local", "requires-cargo"]` (a real toolchain, a writable target dir, and the registry cache in `$CARGO_HOME`, which the environment they inherit names), and `//:cargo_workspace_files` puts the workspace root manifest, the toolchain pin and every member crate's manifest and sources in their runfiles. Resolution is `--offline`, so a fresh clone needs `cargo fetch --locked` once. They are the one deliberate exception to the all-Bazel rule — `TODO(bazel-rustc-gate-tests)` is the hermetic replacement. `tests/test_fltkfmt_parity.py` is no longer one of them: it consumes the Bazel-built `//crates/fltkfmt:fltkfmt` through `FLTKFMT_BIN` and spawns no cargo.

Coverage is `bazel coverage //tests:test_span` (or `//...`), the successor to `coverage run -m pytest`; `.bazelrc` sets `--instrumentation_filter=^//:` because the default filter is the package under test, which holds no library code. For one report over the whole suite add `--combined_report=lcov`, which writes `bazel-out/_coverage/_coverage_report.dat`; rendering it as HTML is `genhtml` (from `lcov`) over that file. `genhtml` is the one tool this repo asks for that the build graph does not pin — install `lcov` from the system package manager; the `.dat` itself, which is what CI and any tooling consume, needs nothing beyond Bazel.

### Running the CLIs

Every fltk CLI is a `py_binary`, and `bazel run` is the launch path — there are no console entry points and no virtualenv to install into:

```bash
bazel run --run_under="cd $PWD &&" //:genparser -- generate calc.fltkg calc calc_cst
bazel run --run_under="cd $PWD &&" //:unparse_cli -- grammar.fltkg spec.fltkfmt input.txt
bazel run --run_under="cd $PWD &&" //:fltk_highlight -- --grammar g.fltkg file.src
bazel run //:grammar_lsp -- fltkg          # fltk's own DSLs; //:fltk_lsp for any other grammar
bazel run --run_under="cd $PWD &&" //:regex_corpus -- path/to/grammar.fltkg
```

`--run_under="cd $PWD &&"` is load-bearing wherever a path argument is relative: `bazel run` executes in the runfiles tree, so without it a relative path names a different file or none at all. The language servers take no path arguments in their `grammar_lsp` form and need no wrapper.

`tests/test_cli_binary_targets.py` is the join: every `fltk/**/*_cli.py` must be some `py_binary`'s `main`, none of them may carry a shebang, and the two checked-in editor launchers (`editors/vscode/run-grammar-lsp`, `examples/gear/vscode/run-gear-lsp`) must name real targets. Both are one-line wrappers over `editors/run-lsp-target <target> [args…]`, which is where the launch rules live: a server started directly by `bazel run` holds the Bazel workspace lock for its whole lifetime and blocks every other Bazel command in the checkout, so the lock is taken only to build (`bazel run --script_path=…`) and the built binary is exec'd afterwards. The generated launcher is written into a mode-700 per-user directory keyed on checkout and target — it is a file this script execs, so a predictable name in a shared temp directory would let another local user pre-seed it. A third language server is a new wrapper, not a new copy of the script.

## Development Protocols

Almost all changes should follow Test-Driven Design (TDD): First write a set of tests that fail but will pass when your task is done, and then complete the task.

When you identify a bug, first implement the test that demonstrates the bug (if there isn't one already) before fixing the bug.

TDD is all that's needed for straightforward changes.
For more complex changes, follow the Design-Test-Code (DTC) process, which is just TDD but with a design stage first, where you will plan out your implementation approach and API surfaces.
For even more complex changes, follow Explore-Design-Test-Code (EDTC), where you first read necessary context and clarify requirements and approach interactively with the user.

You may find when you are designing, testing, or coding, that you don't understand something.
That indicates that you should stop and start an Explore-Design-Test-Code (EDTC) process.

Remember that any of these phases can be interactive with the user, especially Explore and Design phases.
The user is a smart human and likely knows more than you do about this codebase and the requirements.

## Architecture

### Core Components

1. **Grammar System** (`fltk/fegen/`):
   - `.fltkg` files define grammars using custom syntax
   - `fegen.fltkg`: Full grammar definition for the system
   - `gsm.py`: Grammar Semantic Model - core data structures for representing grammars

2. **Parser Generation**:
   - `fltk_parser.py`: Generated parser for full grammar
   - `gsm2parser.py`: Converts GSM to parser code
   - `gsm2tree.py`: Converts GSM to CST node classes

3. **Intermediate Representation** (`fltk/iir/`):
   - `model.py`: Type system and data model definitions
   - `typemodel.py`: Type modeling infrastructure
   - `py/`: Python-specific compilation and code generation

### Grammar Format

The `.fltkg` grammar format supports:
- Rule definitions with `:=`
- Alternatives with `|`
- Item separators: `.` (no whitespace), `,` (whitespace allowed), `:` (whitespace required)
- Quantifiers: `?` (optional), `+` (one or more), `*` (zero or more)
- Dispositions: `%` (suppress), `$` (include), `!` (inline)
- Labels for capturing specific parts: `label:term`
- Literals, regexes, and sub-expressions

### CST Design

- Each grammar rule generates a corresponding node class
- Nodes maintain references only to children (no parent/sibling refs)
- Spans track source text positions
- Type-safe child access methods based on labels
- Suppressed elements may create gaps in spans

## Configuration

- `requirements.in`: the Python dependency manifest (compiled to `requirements_lock.txt`)
- `pyproject.toml`: tool settings only — ruff, pyright, coverage
- `pytest.ini`: Test configuration with debug logging enabled
- Black line length: 120 characters
- Target Python version: 3.10+

## Architecture Decision Records (ADRs)

Significant or hard-to-reverse decisions get an ADR. Store them at `docs/adr/YYYY/MM/DD-slug/`, where the date is the decision date and `slug` is a short kebab-case name (e.g. `docs/adr/2026/05/25-rust-build-system/`). Each ADR directory holds one or more `*.md` files (typically `README.md` for the decision itself; add others for supporting notes or diagrams). An ADR records context, the decision, and consequences. Treat accepted ADRs as immutable — supersede with a new ADR rather than rewriting history.

## TODO System

Two pieces that stay in sync:
- `TODO.md` at the repo root — master list. Each entry has a slug, a description, and the deferral context.
- `TODO(slug)` comments in code — mark the spot where the work needs to happen.

Slugs are the join key. Adding a TODO requires both an entry in `TODO.md` and a `TODO(slug)` comment at the relevant location. Don't use TODOs for vague aspirations — every TODO should describe a concrete thing that needs to happen, in a place where "done" is obvious.

## Working tips

Always read the entire file when reading a source file.
Trying to read only a few lines at a time usually leads to misunderstandings.
Don't search for specific lines and try to read only those; just read the whole file.
The precommit hook can take a long time to run. Use a 5-minute timeout when running commits.
