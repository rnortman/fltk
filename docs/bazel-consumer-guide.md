# Consuming FLTK from Bazel

FLTK ships a Bazel module (`bazel_dep(name = "fltk")`) that covers every supported
configuration: pure Python, Python with Rust parsers, and pure Rust with any combination of
parser, AST, unparser/formatter, and serde. This guide is the recipe book: pick your row in
the decision matrix, copy the recipe, and verify with the checks at the end.

Every example below is a working shape taken from `tests/bazel_consumer/`, FLTK's in-repo
downstream module. That module is a real `bazel_dep` consumer of `@fltk` and is built and
tested by `make bazel-consumer-check`, so the recipes here do not drift silently.

---

## 1. Module setup

Add FLTK to your `MODULE.bazel`. There is no Bazel registry entry; pin a git commit:

```starlark
bazel_dep(name = "fltk", version = "")
git_override(
    module_name = "fltk",
    remote = "https://github.com/rnortman/fltk",
    commit = "<40-char sha>",
)

# FLTK's rules load these; declare the ones your own BUILD files load directly.
bazel_dep(name = "rules_python", version = "1.5.0")
bazel_dep(name = "rules_rust", version = "0.70.0")

# Rust consumers: pin the same toolchain FLTK compiles with (see rust-toolchain.toml in
# the pinned revision). A root module selects its own toolchain; riding the rules_rust
# default means your crates and FLTK's runtime crates are built by different compilers.
rust = use_extension("@rules_rust//rust:extensions.bzl", "rust")
rust.toolchain(
    edition = "2021",
    versions = ["1.97.1"],
)
```

Two rules on pins, both load-bearing:

- **Pin only published commits.** A rev that exists solely in a local or rebased-away branch
  breaks every fetch of your module for everyone else. Pin commits reachable from `main`.
- **Pin in lockstep.** If you also take cargo dependencies on FLTK's runtime crates (§6),
  the cargo `rev` and the `git_override` `commit` must be the *same* commit. Generated code
  and the runtime crates it calls into are one unit; a skew shows up as a compile error at
  best and as behavioral mismatch at worst. Enforce it in your own repo — a script that
  greps both files and diffs the revs is enough.

FLTK's own third-party Rust hub (`@fltk_crates`) is module-private. You never need a
`use_repo` for it, and you cannot name its labels from your BUILD files.

---

## 2. Decision matrix

| Your configuration | Load | FLTK targets you link | §    |
|---|---|---|---|
| Pure Python parser | `@fltk//:rules.bzl` `generate_parser` | `@fltk` (+ `@fltk//:native_py`) | §3 |
| Python app, Rust parser extension | `@fltk//:rust.bzl` `generate_rust_parser(python_extension = True)` | none directly — the macro links them | §4 |
| Pure Rust, parser only | `@fltk//:rust.bzl` `generate_rust_parser` | `fltk-cst-core:no_python`, `fltk-parser-core:no_python` | §5 |
| Pure Rust + AST | same, `ast = True` | the above + `fltk-ast-core:no_python` | §5 |
| Pure Rust + unparser | same, `unparser = True` | the above + `fltk-unparser-core` | §5.2 |
| Pure Rust + formatter binary | same | the above + `fltk-fmt-cli` | §5.3 |
| Pure Rust + serde (your own model structs) | codegen from `@fltk`, runtime crates from **your** crate hub | none — see §6 | §6 |
| Grammar LSP tooling | `@fltk//:grammar_lsp` (py_binary) | n/a, no codegen | §7 |

The two `generate_*` macros are the only public entry points. `generate_rust_parser` has two
modes selected by `python_extension`; everything else is an attribute on one of them.

---

## 3. Pure Python

```starlark
load("@fltk//:rules.bzl", "generate_parser")
load("@rules_python//python:defs.bzl", "py_library")

generate_parser(
    name = "mylang_py_srcs",
    src = "mylang.fltkg",
    base_name = "mylang",
    cst_mod_path = "mylang_cst",
)

py_library(
    name = "mylang_parser",
    srcs = [":mylang_py_srcs"],
    imports = ["."],          # so the generated modules resolve as top-level imports
    deps = ["@fltk"],
)
```

`cst_mod_path`'s last dotted component must be `<base_name>_cst`, and any dotted prefix must
match the import root your `py_library` establishes: with `imports = ["."]` in package
`mylang/`, `mylang_cst` is correct; with `imports = ["../.."]` the modules are named
`mylang.mylang_cst` and `cst_mod_path` must say so. A mismatch fails at analysis time.

`@fltk` is the pure-Python library. Generated Python CST/parser modules never name
`fltk._native`, so this path needs nothing else. Add `@fltk//:native_py` (the `py_library`
that puts `fltk/_native.abi3.so` on the path) if something in your graph does import
`fltk._native` — a Rust CST extension resolving `UnknownSpan` at runtime is the usual
reason.

---

## 4. Python app with a Rust parser extension

```starlark
load("@fltk//:rust.bzl", "generate_rust_parser")

generate_rust_parser(
    name = "mylang_native",       # this is the importable module name
    src = "mylang.fltkg",
    python_extension = True,
    ast = True,                   # optional: adds ast.rs
    ast_config = "mylang.fltkast",
    unparser = True,              # optional: adds unparser.rs
    format_config = "mylang.fltkfmt",   # optional: bakes a spec into the unparser
    serde = True,                 # optional: adds de.rs (requires ast_config)
    protocol_module = "mylang_native.cst_protocol",  # optional: emits .pyi stubs
    protocol = True,
)

py_test(
    name = "mylang_test",
    srcs = ["mylang_test.py"],
    deps = [":mylang_native"],
)
```

The macro generates the crate root, assembles the crate, builds the cdylib, renames it to the
abi3 convention, and wraps it in a `py_library` named `mylang_native`; `import mylang_native`
then works, with `mylang_native.cst`, `.parser`, `.unparser`, `.ast`, `.de` as submodules
according to the attributes you set. It links FLTK's runtime crates for you — do not add them
to `deps` yourself.

**If you pass your own `lib_rs`**, you own the module declarations: an `.rs` file that no
`mod` declaration names is silently not compiled, so a hand-authored crate root that omits
`mod unparser;` (or `ast` / `de`) builds green with the submodule simply missing at import
time. Let the macro generate the crate root unless you have a reason not to.

`protocol_module` turns on `.pyi` emission into a stub package named after the target; the
stub package lists exactly the submodules you enabled.

---

## 5. Pure Rust

In pure-Rust mode `generate_rust_parser` emits `.rs` files and nothing else — no cdylib, no
`.pyi`, no Python. You compile them into your own crate.

Use `out_dir` to declare the generated files inside your crate's source directory. The
generated modules address each other as `super::` siblings, so they must land next to your
crate root:

```starlark
load("@fltk//:rust.bzl", "generate_rust_parser")
load("@rules_rust//rust:defs.bzl", "rust_library", "rust_test")

generate_rust_parser(
    name = "mylang_srcs",
    src = "mylang.fltkg",
    ast = True,
    ast_config = "mylang.fltkast",
    out_dir = "src",              # cst.rs, parser.rs, ast.rs land in src/
)

rust_library(
    name = "mylang",
    srcs = glob(["src/**/*.rs"]) + [":mylang_srcs"],
    crate_root = "src/lib.rs",    # your hand-written crate root, in the tree
    edition = "2021",
    deps = [
        "@fltk//crates/fltk-ast-core:no_python",
        "@fltk//crates/fltk-cst-core:no_python",
        "@fltk//crates/fltk-parser-core:no_python",
    ],
)
```

`src/lib.rs` declares the generated modules:

```rust
pub mod ast;
pub mod cst;
pub mod parser;
```

`out_dir` must be package-relative with no `..` segment, and is rejected in
`python_extension = True` mode (there the crate assembly owns the layout). Mixing tree
sources and generated sources in one `srcs` is supported by rules_rust; the copy-genrule
pattern — a genrule re-rooting every generated file next to `lib.rs` — is only needed for
layouts `out_dir` cannot express.

### 5.1 Which runtime targets

| Generated module | Runtime crate target |
|---|---|
| `cst.rs` | `@fltk//crates/fltk-cst-core:no_python` |
| `parser.rs` | `@fltk//crates/fltk-parser-core:no_python` |
| `ast.rs` | `@fltk//crates/fltk-ast-core:no_python` |
| `unparser.rs` | `@fltk//crates/fltk-unparser-core` |
| `de.rs` | not linkable from `@fltk` — see §6 |

**Always the `:no_python` flavor** for cst/parser/ast/serde-core. The default labels
(`@fltk//crates/fltk-cst-core` etc.) carry pyo3 — they are what the cdylib path needs. The
`:no_python` targets are the same crates with the `python` feature off and the pyo3 edge
gone. `fltk-unparser-core` and `fltk-fmt-cli` have one flavor each; they never touch pyo3.

**Never link both flavors of the same crate into one binary.** They share a crate name, and
rustc refuses two crates with the same name in one graph. The failure is loud and immediate,
which is the intended behavior: a binary that pulls in both a pyo3-ful and a pyo3-free
`fltk_cst_core` is incoherent regardless of what Bazel would have done with it.

### 5.2 Adding an unparser

```starlark
generate_rust_parser(
    name = "mylang_srcs",
    src = "mylang.fltkg",
    unparser = True,
    format_config = "mylang.fltkfmt",   # optional
    out_dir = "src",
)
```

The `.fltkfmt` spec is baked into `unparser.rs` at generation time, so editing the spec is an
ordinary input change Bazel tracks — no regeneration ceremony. Omitting `format_config`
selects the default formatting config. Passing `format_config` without `unparser = True` is
an error.

With `ast = True` as well, `ast.rs` also gains its `unparse_str` entry point.

Add `"@fltk//crates/fltk-unparser-core"` to the library's `deps`.

### 5.3 A formatter binary

`fltk-fmt-cli` provides `fltk_formatter_main!`, which builds a complete CLI (file or stdin
input, `--check`, in-place rewriting, exit codes) around your generated parser and unparser:

```starlark
rust_binary(
    name = "mylang_fmt",
    srcs = ["main.rs"],
    edition = "2021",
    deps = [
        ":mylang",
        "@fltk//crates/fltk-fmt-cli",
    ],
)
```

See `docs/rust-formatter-guide.md` for the macro invocation itself; the Bazel-specific part
is only the two deps above. `tests/bazel_consumer` builds exactly this shape and diff-tests
the binary's output.

---

## 6. Pure Rust + serde: the one-serde rule

**Rule: `fltk-serde-core` must be compiled against the same `serde` instance your model
structs derive from.** This is the whole story, and it is why serde-mode pure-Rust
consumption does not go through FLTK's Bazel crate targets.

Generated `de.rs` describes your grammar's tree to the `fltk-serde-core` deserializer and
hands values to *your* `#[derive(Deserialize)]` structs. Those derives are generated by your
`serde_derive` and implement traits from your `serde`. `@fltk//crates/fltk-serde-core` links
`@fltk_crates//:serde` — FLTK's module-private hub instance, a different crate instance by
construction. Trait coherence then fails: your structs implement *your* `serde::Deserialize`,
and FLTK's deserializer wants *its* one. No target FLTK can ship from its own module fixes
this, and exporting a `serde` alias from FLTK's hub would only move the problem — your model
types would then be split from the rest of your serde ecosystem.

**The recipe: codegen from FLTK's module, runtime crates from your own crate hub.**

`MODULE.bazel`:

```starlark
bazel_dep(name = "fltk", version = "")
git_override(
    module_name = "fltk",
    remote = "https://github.com/rnortman/fltk",
    commit = "<sha>",              # same sha as the cargo revs below
)

crate = use_extension("@rules_rust//crate_universe:extensions.bzl", "crate")
crate.from_cargo(
    name = "crates",
    cargo_lockfile = "//:Cargo.lock",
    manifests = ["//:Cargo.toml"],
)
use_repo(crate, "crates")
```

Your `Cargo.toml` (the manifest that hub resolves — it need not build anything with cargo,
but it does have to be a complete manifest: `crate.from_cargo` runs cargo over it, so it needs
a `[package]` stanza and a target — an empty `src/lib.rs` next to it is enough):

```toml
[package]
name = "mylang-deps"
version = "0.0.0"
edition = "2021"
publish = false

[dependencies]
serde = { version = "1", features = ["derive"] }
fltk-cst-core   = { git = "https://github.com/rnortman/fltk", rev = "<sha>" }
fltk-parser-core = { git = "https://github.com/rnortman/fltk", rev = "<sha>" }
fltk-ast-core   = { git = "https://github.com/rnortman/fltk", rev = "<sha>" }
fltk-serde-core = { git = "https://github.com/rnortman/fltk", rev = "<sha>" }
```

`fltk-cst-core` has no default features, so this graph is pyo3-free without further ceremony;
add `features = ["python"]` only if you actually want the pyo3 bindings.

Then generate with FLTK's macro and link the hub-resolved crates:

```starlark
generate_rust_parser(
    name = "mylang_srcs",
    src = "mylang.fltkg",
    ast = True,
    ast_config = "mylang.fltkast",
    serde = True,
    out_dir = "src",
)

rust_library(
    name = "mylang",
    srcs = glob(["src/**/*.rs"]) + [":mylang_srcs"],
    crate_root = "src/lib.rs",
    edition = "2021",
    deps = [
        "@crates//:fltk-ast-core",
        "@crates//:fltk-cst-core",
        "@crates//:fltk-parser-core",
        "@crates//:fltk-serde-core",
        "@crates//:serde",
    ],
)
```

Generated code names runtime crates by plain paths (`::fltk_serde_core`, `::serde`), so it
resolves against whatever your graph provides — that is what makes this work. The runtime
crates are consumable this way by design: no build scripts, no `[patch]` requirements, no
MSRV floor.

Two consequences worth stating plainly:

- Only serde-mode consumers need a hub. Parser / AST / unparser consumers link FLTK's
  `:no_python` targets and never resolve a Cargo graph (§5).
- A serde-mode consumer already has a hub, because their model structs already need serde.
  This recipe adds four crates to a manifest that exists anyway.

**Why FLTK has no in-tree fixture for this path.** A hub over *path* deps into `../../crates`
is refused by crate_universe: its splicer rewrites dependency paths relative to the module
directory and fails with ``failed to read `/crates/fltk-ast-core/Cargo.toml` ``. A git dep
would pin a published commit rather than the working tree under test, so it would verify the
previous release instead of the change in front of you. The channel is therefore verified by
real downstream consumers; FLTK's own fixture covers serde in extension mode, where the hub
question does not arise.

---

## 7. Grammar LSP tooling

`@fltk//:grammar_lsp` is a `py_binary` running the FLTK grammar language server. It takes the
language id as its argument (`fltkg`, `fltkfmt`, or `fltklsp`):

```bash
bazel run @fltk//:grammar_lsp -- fltkg
```

It is a runtime tool, not codegen — nothing about it integrates with your grammar targets, and
it serves your own `.fltkg`/`.fltkfmt`/`.fltklsp` files as-is. `docs/lsp.md` has the editor
wiring, including the Bazel workspace-lock caveat when several servers start at once.

---

## 8. Verifying you got no pyo3

A "pure-Rust" build that quietly links pyo3 still compiles; the only symptom is a libpython
dependency you did not want. Assert it, in CI, with a positive control — a silently failing
query otherwise passes the negative assertion vacuously.

Bazel:

```bash
graph="$(bazel cquery 'deps(//:mylang)')"
echo "$graph" | grep -q 'fltk-cst-core:no_python' || { echo "query broken"; exit 1; }
! echo "$graph" | grep -qi pyo3 || { echo "FAIL: pyo3 in the graph"; exit 1; }
```

Cargo (for the §6 hub graph):

```bash
tree="$(cargo tree --locked -p my-grammar --edges normal,build)"
echo "$tree" | grep -q fltk-cst-core || { echo "query broken"; exit 1; }
! echo "$tree" | grep -q pyo3 || { echo "FAIL: pyo3 in the graph"; exit 1; }
```

FLTK runs both shapes over its own graphs (`make check-no-pyo3`,
`make bazel-consumer-check`).

The one edge to watch is `fltk-cst-core`: it is the only runtime crate with a `python`
feature, and everything else reaches pyo3 through it. In Bazel that means taking
`:no_python`; in cargo it means not writing `features = ["python"]` (the crate's default
feature set is empty, so plain `default-features = false` is redundant but harmless).

---

## 9. Guard rails, collected

| Situation | What happens |
|---|---|
| `format_config` without `unparser = True` | error at loading time |
| `out_dir` with `python_extension = True` | error at loading time |
| `out_dir` absolute or containing `..` | error at loading time |
| `serde = True` without `ast_config` | error at loading time |
| Python-extension-only attrs in pure-Rust mode | error at loading time |
| Both crate flavors in one binary | rustc duplicate-crate-name error |
| Hand-authored `lib_rs` missing a `mod` declaration | green build, submodule silently absent |
| Rev pinned that is not published | consumer fetch fails |
| `git_override` commit ≠ cargo rev | codegen/runtime skew, compile error at best |
