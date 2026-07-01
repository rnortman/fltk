# Refined request: unify and fix FLTK's Bazel parser-codegen surface

## Original request

The request was worked out interactively with the user; its wording is settled intent, not a rough prompt. Reproduced verbatim:

> Problem: FLTK's Bazel codegen surface diverged badly between `generate_parser` (Python, rules.bzl) and `generate_rust_parser` (Rust, rust.bzl) + the `fltk_pyo3_cdylib` macro. Divergences are partly gratuitous (option naming) and partly a latent bug (stub-package directory named after the wrong thing). Current-state facts are in exploration.md.
>
> Settled decisions:
>
> 1. Unify the protocol opt-in option name: Rust's `generate_protocol` bool → `protocol`, matching the Python rule's `protocol`. Keep `protocol_module` (dotted import path) — it feeds `.pyi` generation and has no Python-side analog.
>
> 2. Restructure `generate_rust_parser` into a SINGLE unified entry point the consumer invokes. It must be a Bazel MACRO (a `rule` cannot instantiate other targets like rust_shared_library/genrule/py_library). The current `generate_rust_parser` rule becomes an internal codegen rule (emits `.rs`, and optionally `.pyi`/protocol). The new `generate_rust_parser` macro wraps that internal rule and, when Python support is enabled, ALSO assembles the crate, builds the `rust_shared_library` cdylib, generates stubs, and wraps in `py_library` — folding in what `fltk_pyo3_cdylib` does today.
>
> 3. A Python-support toggle (exact attribute name is a design detail):
>    - OFF (default) = pure-Rust: emit only `.rs` files; no cdylib, no `.pyi`, no protocol. Consumer drops the `.rs` into their own crate.
>    - ON = build cdylib + stubs + py_library.
>
> 4. Because the unified macro owns a single `name`, that name is the extension/module name: passed as `--extension-name` and used for the stub-package directory. This STRUCTURALLY fixes the current bug where the stub dir and `--extension-name` derive from the codegen rule's own target name instead of the real compiled-module name (the `fltk_pyo3_cdylib` name), which mismatch when they differ.
>
> 5. Accept the `.pyi` stub-package subdirectory — it is mandatory: PyO3 exposes cst/parser as submodules of one extension, so the PEP 561 stub package must be a directory named after the module. Python shims to avoid the subdir were considered and REJECTED (complexity for no real gain). The `.rs` files stay privately assembled for the crate; the `.py` protocol module may be flat.
>
> 6. cst and parser stay in ONE cdylib — shared `#[pyclass]` types cannot be split across separately-compiled cdylibs without breaking Python type identity. Not up for redesign.
>
> 7. Breaking changes to these Bazel rules ARE permitted. Do NOT scope any Clockwork / out-of-tree consumer migration — it is handled out of tree. `fltk_pyo3_cdylib` may be removed or demoted to an internal helper.
>
> 8. The CLI (`genparser.py`) already takes explicit output paths and `--extension-name`. Prefer keeping changes in the Bazel layer (rust.bzl/rules.bzl); touch the CLI only if genuinely required.
>
> Scope boundary: this is about the Bazel rule/macro surface — option naming, the unified macro + pure-Rust toggle, and fixing the stub-dir naming. Not changing generated CST/parser semantics, and not changing the Python `generate_parser` rule beyond what naming consistency requires.

Everything below refines this. The decisions above are settled; the refinement exists so a downstream agent who has never seen the exploration can act on them without guessing.

## Background a reader needs

FLTK (Formal Language ToolKit) generates parsers from grammar files (`.fltkg`). Its generated output — CST node classes, parsers, protocol modules, type stubs — is public API consumed by out-of-tree applications that build against it. Those consumers wire FLTK into their own builds through a set of Bazel building blocks that FLTK ships. This request is about three of those building blocks and how they fit together; it is *not* about what the generator emits.

There are two code-generation backends and, correspondingly, two Bazel entry points:

- **`generate_parser`** — the Python-backend rule, defined in `rules.bzl`. It runs FLTK's codegen CLI (`//:genparser`, the `py_binary` wrapping `fltk/fegen/genparser.py`) and produces Python source files: `{base_name}_cst.py`, the parser modules, and — opt-in — a "protocol module" (`{base_name}_cst_protocol.py`). The protocol module is a set of typing-only `Protocol` definitions describing the CST node surface; it was recently (commit 3b95f0a) made opt-in via a single boolean attribute named **`protocol`** (default `False`).

- **`generate_rust_parser`** — the Rust-backend rule, defined in `rust.bzl`. It runs the same CLI through different subcommands (`gen-rust-cst`, `gen-rust-parser`) and produces Rust source: `cst.rs` and `parser.rs`. When configured for Python interop, it can additionally emit a **`.pyi` type stub** (`cst.pyi` plus a stub-package marker `__init__.pyi`) and the same protocol `.py` module. These extra outputs exist because a Rust-backed parser can be compiled into a Python extension module.

The Rust path needs a third building block to actually become an importable Python module:

- **`fltk_pyo3_cdylib`** — a Bazel *macro* (a `def`, not a `rule`) in `rust.bzl`. A `rule` in Bazel cannot instantiate other targets, so anything that has to spin up several targets must be a macro. This macro takes the `.rs` files produced by a `generate_rust_parser` target (`rs_srcs`) and: optionally synthesizes a `lib.rs` (via the `generate_rust_lib` rule) declaring the PyO3 `#[pymodule]`; assembles all the `.rs` files plus `lib.rs` into one flat crate directory (a `genrule`); compiles that into a shared library via `rust_shared_library`; renames it for the Python ABI; and finally wraps the result in a `py_library` so downstream Python code can import it.

**Why cst and parser live in one extension.** PyO3 exposes both `cst` and `parser` as submodules of a *single* compiled extension module. This is not an incidental packaging choice: the two share `#[pyclass]` types, and Python's type identity would break if those types were compiled into two separately-linked cdylibs. So there is exactly one cdylib, and it carries submodules — which is why the type stubs must form a PEP 561 *stub package* (a directory named after the module, containing `cst.pyi`, `parser.pyi`-style stubs, and an `__init__.pyi` marker) rather than a single flat stub file.

## What the user wants done

Three intertwined changes to this Bazel surface, plus the removal of one gratuitous divergence. None of them touch what the generator emits or how the CST/parser behave.

### 1. Rename the Rust protocol toggle to match Python

Today the two backends spell the same concept differently. The Python rule opts into the protocol module with a boolean `protocol`. The Rust rule opts into the protocol `.py` module with a boolean named **`generate_protocol`**. The user wants the Rust boolean renamed to **`protocol`** so both backends read the same.

Keep the Rust rule's separate string attribute **`protocol_module`** (the dotted Python import path, e.g. `my.pkg.grammar_cst_protocol`). It drives `.pyi` stub generation and has no counterpart on the Python side, so it stays as-is. Note the existing relationship the exploration documents: `protocol_module` being non-empty is what triggers `.pyi` emission, and today `generate_protocol = True` additionally requires `protocol_module` to be non-empty (enforced both at Bazel analysis time and in the CLI). That coupling is part of the current behavior; this rename is about the *name* of the boolean, not about redesigning the protocol/pyi trigger relationship.

### 2. Make `generate_rust_parser` a single unified entry point

Right now a Rust consumer must invoke *two* things in sequence: `generate_rust_parser` (to get `.rs` files) and then `fltk_pyo3_cdylib` (to turn them into an importable Python module), passing the first's label into the second. The user wants to collapse this into **one** call the consumer makes: `generate_rust_parser`.

Concretely:

- The thing consumers call, `generate_rust_parser`, becomes a **macro** (it must be, because when Python interop is on it has to instantiate the crate-assembly genrule, `rust_shared_library`, and `py_library` — none of which a `rule` can create).
- The *current* `generate_rust_parser` rule — the pure codegen step that emits `.rs` and optionally `.pyi`/protocol — becomes an **internal** rule that the new macro wraps.
- When Python interop is enabled, the macro also does everything `fltk_pyo3_cdylib` does today: assemble the crate, build the cdylib, generate the stubs, and wrap in `py_library`.

Because `fltk_pyo3_cdylib`'s responsibilities are being folded into the macro, `fltk_pyo3_cdylib` itself may be **removed or demoted to an internal helper** — the user's call. Breaking the existing two-call surface is explicitly permitted (see "What this changes for consumers" below).

### 3. Add a Python-support toggle with a pure-Rust default

The unified macro needs a switch — its exact attribute name is left to the design phase — governing whether Python interop is built:

- **OFF (the default) = pure Rust.** Emit only the `.rs` files. No cdylib, no `.pyi`, no protocol module. This supports the consumer who just wants Rust source to drop into their own crate and compile themselves.
- **ON = full Python extension.** Build the cdylib, generate the stub package, and wrap in a `py_library`, exactly as the combined `generate_rust_parser` + `fltk_pyo3_cdylib` flow does today.

### 4. Fix the stub-directory / `--extension-name` naming bug (a structural consequence of unification)

This is the latent bug the restructure is designed to eliminate, so it matters that the reader understands it precisely.

The `.pyi` stub package must be a directory named after the *actual compiled Python module*. That module's name is the one the extension is compiled and imported under. In today's two-call world, that name is the **`fltk_pyo3_cdylib`** target's `name` (it becomes the crate name and the `#[pymodule]` function name). But `generate_rust_parser` derives both the stub-package directory and the `--extension-name` CLI flag from **its own** target `name` instead. Those two names are independent caller-chosen strings on two separate targets, and nothing threads one into the other. When they differ — which they do in the real Clockwork call site, where `generate_rust_parser(name = "clockwork_rs_srcs")` pairs with `fltk_pyo3_cdylib(name = "clockwork_native")` — the generated stub package is named after the wrong thing and does not match the module it is supposed to type.

Unifying into one macro fixes this **structurally, not by patching**: the macro owns a single `name`, and that one name is both the compiled module name *and* the source of the stub directory and `--extension-name`. There is no longer a second, divergent name to get out of sync. The reader should treat "the bug is fixed" as an automatic property of the single-name design, not as a separate task requiring its own workaround.

Note the exploration's observation that today no live call site actually sets `protocol_module`/`generate_protocol` (Clockwork leaves them at defaults, and FLTK's in-tree smoke targets don't set them either), so the mismatch is currently latent rather than actively breaking anyone. It should still be fixed as part of the restructure.

## What this changes for consumers

The generated *artifacts* consumers build against (CST classes, parser API, protocol types, stubs) are unchanged — this is important given FLTK's rule that generated symbols are public API. What changes is the **Bazel authoring surface**: the set of rules/macros and their attribute names. That surface break is explicitly sanctioned here. In particular:

- Out-of-tree consumers (Clockwork is the only one found) will migrate their `BUILD.bazel` call sites to the new single-macro form. **Do not scope or perform that migration** — it is handled out of tree.
- FLTK's own in-tree callers of these rules/macros (e.g. the smoke targets in `BUILD.bazel`, and the `Makefile` regen invocations) are in-tree and *will* need to keep building; keeping the in-tree build green is part of this work even though the external migration is not.

## Scope boundaries (from the user)

- **In scope:** the Bazel rule/macro surface in `rust.bzl` and `rules.bzl` — the `protocol` rename, the unified macro, the pure-Rust toggle, and the structural stub-dir/`--extension-name` fix. Keeping FLTK's in-tree build and regen path working.
- **Out of scope:** changing generated CST/parser semantics; changing the Python `generate_parser` rule beyond what the naming-consistency rename requires; migrating Clockwork or any other out-of-tree consumer.
- **Prefer not to touch the CLI.** `genparser.py` already accepts explicit output paths and `--extension-name`, so the work should live in the Bazel layer. Touch the CLI only if genuinely unavoidable.

## Open questions

None. The decisions above were settled interactively with the user, and the remaining choices the user flagged — the toggle's attribute name, and whether `fltk_pyo3_cdylib` is deleted outright versus kept as an internal helper — are explicitly delegated to the design phase, not matters of user intent left unresolved here.
