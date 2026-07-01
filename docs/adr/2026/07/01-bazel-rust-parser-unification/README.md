# Unify FLTK's Bazel Rust parser-codegen surface into one `generate_rust_parser` macro

- Status: Accepted
- Date: 2026-07-01

## Context

FLTK's generated output (CST classes, parsers, protocol modules, type stubs) is
public API for out-of-tree consumers, and those consumers wire FLTK into their
own builds through Bazel building blocks that FLTK ships. This ADR concerns the
Bazel *authoring surface* for the Rust backend — the rules and macros a consumer
calls — not what the generator emits.

Two codegen entry points had drifted apart:

- **Python backend** — the `generate_parser` rule (`rules.bzl`) opts into the
  protocol module with a single bool attribute `protocol` (default `False`),
  made opt-in in commit 3b95f0a.
- **Rust backend** — the `generate_rust_parser` *rule* (`rust.bzl`) emits `.rs`
  (and optionally `.pyi`/protocol), and the separate `fltk_pyo3_cdylib` *macro*
  (`rust.bzl`) turns those `.rs` files into an importable Python extension. The
  Rust rule opts into the protocol `.py` module with a bool named
  `generate_protocol`, and keeps a separate string `protocol_module` (the dotted
  `.pyi` import path) whose non-emptiness triggers `.pyi` emission.

This shape produced three concrete problems:

1. **Gratuitous name divergence.** The same concept — "also emit the protocol
   `.py` module" — was spelled `protocol` on the Python rule but
   `generate_protocol` on the Rust rule.

2. **Two-call surface.** A Rust consumer had to instantiate `generate_rust_parser`
   (`.rs` output) and then `fltk_pyo3_cdylib` (crate assembly →
   `rust_shared_library` → abi3 rename → `py_library`), threading the first
   target's label into the second. The only out-of-tree consumer found
   (Clockwork, `clockwork/dsl/BUILD.bazel`) shows this required pairing:
   `generate_rust_parser(name = "clockwork_rs_srcs")` followed by
   `fltk_pyo3_cdylib(name = "clockwork_native", rs_srcs = ":clockwork_rs_srcs")`.

3. **Latent stub-directory bug.** A PEP 561 stub package must be a directory
   named after the *actual compiled Python module*. That module name is the
   `fltk_pyo3_cdylib` target's `name` (it becomes the crate name and the
   `#[pymodule]` function name). But the codegen rule derived both the
   stub-package subdirectory and the `--extension-name` CLI flag from **its own**
   target `name`. These are two independent, caller-chosen strings on two
   separate targets, and nothing threaded one into the other. In Clockwork they
   differ (`clockwork_rs_srcs` vs `clockwork_native`), so an emitted stub package
   would be named after the wrong thing and would not type the module it belongs
   to. The bug is latent only because no live call site sets `protocol_module`
   today.

Two constraints frame the solution:

- **A `rule` cannot instantiate other targets.** Assembling the crate, building
  the cdylib, and wrapping in `py_library` require a macro, which is why
  `fltk_pyo3_cdylib` is a `def` and why the unified entry point must also be one.
- **`cst` and `parser` must share one cdylib.** PyO3 exposes both as submodules
  of a single compiled extension. They share `#[pyclass]` types, and Python's
  type identity would break if those types were compiled into two
  separately-linked cdylibs. This is not up for redesign — and it is precisely
  *why* the type stubs must form a PEP 561 stub-package directory (containing
  `cst.pyi` and an `__init__.pyi` marker) rather than a single flat stub file.

The CLI (`genparser.py`) already accepts explicit output paths, `--extension-name`,
`--protocol-module`, `--protocol-output`, `--init-pyi-output`, and `--submodules`.
No CLI flag needs to change; all the work stays in the Bazel layer.

## Decision

Unify the Rust Bazel surface into a single public macro over an internal codegen
rule, rename the divergent option, and let the single owning `name` structurally
fix the stub-directory bug.

### 1. Rename the Rust protocol toggle

Rename the Rust bool `generate_protocol` → `protocol`, matching the Python rule.
The string `protocol_module` is unchanged — it has no Python-side analog and it
remains the trigger for `.pyi` emission. The existing coupling is preserved:
`protocol = True` requires `protocol_module` non-empty. This is a pure rename of
the boolean; the protocol/pyi trigger relationship is not redesigned. The
analysis-time guard and the CLI's `--protocol-output requires --protocol-module`
check are both retained; only the guard's referenced attribute name changes.

### 2. One public `generate_rust_parser` macro over an internal codegen rule

The current `generate_rust_parser` *rule* is demoted to a private codegen rule
(proposed `_generate_rust_srcs`) that keeps its two actions (`gen-rust-cst`,
`gen-rust-parser`), its `src` / `cst_mod_path` attributes, the renamed `protocol`
bool, and `protocol_module`. It gains one new attribute:

- **`extension_name`** (string, default `""`) — when non-empty, used as BOTH the
  `--extension-name` CLI argument AND the output subdirectory holding the
  generated files. When empty, the subdirectory falls back to the rule's own
  `name` (preserving today's behavior for the pure-Rust case, where no stub is
  emitted and the subdir name is irrelevant to type resolution). This attribute
  is the structural fix: the stub-package directory and `--extension-name` are
  decoupled from the rule's own target name and instead driven by a value the
  macro sets to the single owner `name`.

The internal rule exposes outputs as `DefaultInfo` (all declared files) *and* as
an `OutputGroupInfo` with two named groups, because a Bazel macro cannot address
an individual `declare_file` output by label:

- `rust_srcs` — always `[<name>/cst.rs, <name>/parser.rs]`.
- `stub_srcs` — the files that ride along on the compiled Python module:
  `<name>/cst.pyi` + `<name>/__init__.pyi` when `protocol_module` is non-empty,
  plus `<name>/cst_protocol.py` when `protocol = True`; an **empty depset** when
  `protocol_module` is empty.

A new public `generate_rust_parser(...)` **macro** (a `def`, replacing the old
rule of that name) is what consumers call. It carries a `python_extension` bool
toggle (default `False`) plus the codegen knobs and the Python-extension-only
knobs folded in from `fltk_pyo3_cdylib` (`lib_rs`, `deps`, `crate_features`,
`recursion_limit`, `visibility`, `**kwargs`).

- **`python_extension = False` (default — pure Rust).** Instantiate the internal
  codegen rule with `name = name` (it *is* the public target); `extension_name`
  left empty. Emit only `cst.rs` / `parser.rs` under `<name>/` — no `.pyi`, no
  protocol module, no cdylib, no `py_library`. The public `:name` target provides
  the `.rs` files for the consumer to drop into their own crate. The
  Python-extension-only knobs and `protocol_module`/`protocol` must be at their
  defaults, else the macro `fail()`s (see below).

- **`python_extension = True` (full Python extension).** Instantiate the internal
  rule as `name + "_srcs"` with `extension_name = name` (the single owner name),
  then fold in the four `fltk_pyo3_cdylib` steps (crate-assembly genrule →
  `rust_shared_library` cdylib → abi3 rename → `py_library`), with the public
  `py_library` named `name`. Crate assembly consumes **only the `rust_srcs`
  output group**, so the `.pyi`/`.py` outputs never enter the flat crate root.
  Stub emission stays optional and gated on `protocol_module` (the rename does
  not force stubs on): `protocol_module = ""` yields cdylib + `py_library` only;
  a non-empty `protocol_module` additionally yields the stub package
  `<name>/cst.pyi` + `<name>/__init__.pyi` (named after `name`, i.e. the compiled
  module — the bug fix); `protocol = True` additionally yields
  `<name>/cst_protocol.py`. The macro adds the internal rule's `stub_srcs` output
  group to the public `py_library` as `data`, so a downstream target depending on
  `:name` gets both the runtime `.so` and the stub package. Because `stub_srcs`
  is empty exactly when `protocol_module` is empty, this routing is self-gating.

**Toggle attribute name.** `python_extension` was chosen because it
self-documents intent (`python_extension = True` = "build the Python extension").
Alternatives considered and rejected: `python` (too generic), `pyo3` (leaks the
implementation), `build_python` (verb-y). The requirements delegated this choice
to design.

### 3. Accept the stub-package subdirectory; reject Python shims

The PEP 561 stub package is a directory named after the module, because the one
cdylib carries `cst`/`parser` as submodules (see the single-cdylib constraint
above). Python shim modules to flatten away the subdirectory were considered and
**rejected** as complexity for no real gain. The `.rs` files stay privately
assembled for the crate; the `.py` protocol module may be flat.

### 4. Demote `fltk_pyo3_cdylib` to an internal helper

Rather than delete the working four-step logic and its load-bearing comments,
rename the `def` to a private helper (proposed `_build_pyo3_cdylib`) with the same
body, called from the macro's `python_extension = True` branch. Drop
`fltk_pyo3_cdylib` from the public surface: remove it from the BUILD.bazel `load`,
and update the module docstring's load example and the two in-source
`fltk_pyo3_cdylib` doc references so the source no longer advertises a removed
symbol. The `generate_rust_lib` rule and the auto-`lib_rs` path are kept unchanged,
reached through the helper. The old consumer-facing warning against passing an
`rs_srcs` whose outputs include `lib.rs` becomes an internal invariant, since the
codegen rule is now always the macro's own.

### 5. Keep the in-tree build green

Rewrite the in-tree smoke targets to the new macro so both paths stay covered:

- `bootstrap_rust_srcs` with `python_extension = False` — exercises the pure-Rust
  path (`.rs` only).
- `bootstrap_native` with `python_extension = True`, `protocol_module` set, and
  `protocol = True` — exercises the full Python path *including* stub-package
  emission, which no in-tree target does today. This turns the latent stub-dir
  bug into an actively built regression case: the stub package must materialize at
  `bootstrap_native/cst.pyi` and `bootstrap_native/__init__.pyi`.

No `Makefile` change is required: the regen path invokes the CLI directly with
flags that are not renamed. The Python `generate_parser` rule and its `protocol`
attribute are untouched.

### These are deliberate breaking changes to the Bazel public API

The generated *artifacts* consumers build against are byte-for-byte unchanged.
What changes is the Bazel authoring surface: the set of rules/macros and their
attribute names (`generate_protocol` → `protocol`, two calls → one,
`fltk_pyo3_cdylib` removed from the public surface). Breaking this surface is
explicitly sanctioned by the requirements. Out-of-tree consumers (Clockwork is
the only one found) will migrate their `BUILD.bazel` call sites to the new
single-macro form; that migration is handled **out of tree** and is not part of
this work.

## Consequences

- **The stub-directory bug is fixed structurally, not patched.** One owner `name`
  is simultaneously the compiled module name, the `--extension-name`, and the
  stub-package directory, so there is no second name to fall out of sync. The bug
  cannot recur without reintroducing a second divergent name.

- **The two backends now read the same** for the protocol opt-in (`protocol` on
  both), and Rust consumers make a single call instead of two.

- **Downstream Bazel call sites must migrate** (breaking change). This is accepted
  and out of scope here.

- **A new analysis-time property must be confirmed by build.** In
  `python_extension = True` mode the internal rule (target `name + "_srcs"`)
  declares outputs under directory `<name>/` while the `py_library` target is
  `name`; these are distinct labels (`//pkg:name/cst.rs` vs `//pkg:name`) and do
  not collide, but this is the one non-obvious property of the single-name design
  and is verified by actually building `bootstrap_native`.

- **Misconfiguration is fail-fast.** Setting Python-only attributes with
  `python_extension = False`, or `protocol = True` with empty `protocol_module`,
  fails at macro-evaluation / analysis time with a message naming the offending
  attribute, rather than silently ignoring the value.

- **Automated negative-test coverage is deferred.** FLTK has no harness for
  asserting expected Bazel analysis failures. The misconfiguration cases above
  are documented as manual `bazel build`-expected-to-fail expectations; building
  the harness is deferred under `TODO(bazel-neg-test-harness)`. Until then, these
  guards are not automatically regression-tested.

- **The pre-existing `TODO(bazel-lib-rs-no-cst)`** (span-only / `no_trivia`
  `lib.rs`) is unaffected and carried into the internal helper verbatim.
