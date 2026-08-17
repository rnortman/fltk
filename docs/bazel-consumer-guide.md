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

# Rust consumers: pin the same toolchain FLTK compiles with (the rust.toolchain versions tag
# in FLTK's own MODULE.bazel at the pinned revision). A root module selects its own toolchain;
# riding the rules_rust default means your crates and FLTK's runtime crates are built by
# different compilers.
rust = use_extension("@rules_rust//rust:extensions.bzl", "rust")
rust.toolchain(
    edition = "2021",
    versions = ["1.97.1"],
)
```

Two rules on pins, both load-bearing:

- **Pin only published commits.** A rev that exists solely in a local or rebased-away branch
  breaks every fetch of your module for everyone else. Pin commits reachable from `main`.
- **One pin, because there is only one.** FLTK's crates carry no Cargo manifests — they are
  Bazel targets only — so the runtime crates cannot be taken as cargo git dependencies and the
  `git_override` commit is the whole pin. Generated code and the runtime crates it calls into
  stay one unit by construction.

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
| Pure Rust + serde (your own model structs) | same, `serde = True` | the above + `fltk-serde-core:no_python`, with the serde flag pointed at your hub | §6 |
| Editor tooling and CLIs | `@fltk//:grammar_lsp`, `@fltk//:fltk_lsp`, `@fltk//:unparse_cli`, … (py_binary) | n/a, no codegen | §7 |

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

The emitted modules are formatter-normalized by the generator itself, against a ruff version
and config that FLTK pins. Your own ruff settings do not apply to them and cannot: generated
output is a function of the grammar, the generator and that pin, so it is identical in your
build and in FLTK's. Nothing needs (or gets) a formatting pass after codegen.

### 3.1 Optional attributes

| Attribute | Effect |
|---|---|
| `trivia_only` / `no_trivia_only` | Emit only one of the two parser variants. Mutually exclusive. |
| `protocol_only` | Emit only `<base_name>_cst_protocol.py` — no CST module, no parsers. This is the typing-protocol surface on its own, which is what you want when the CST and parser come from a Rust extension and you only need something to type a `.pyi` against. Cannot be combined with the two selectors above. |
| `out_dir` | Package-relative directory the modules are declared in, instead of the package root. Use it when the modules have to land at a Python package path that cannot have its own `BUILD` file. Must be package-relative with no `..` segment. |
| `gen_tool` | The generator binary. Defaults to `@fltk//:genparser`. `@fltk//:genparser_stage0` is the same `generate` command over the Python backend alone; FLTK uses it internally to break a bootstrap cycle, and a consumer has no reason to override the default. |
| `unparser` | Also emit `<base_name>_unparser.py`: the `Unparser` class that walks the CST and renders it back to source text. It reads the trivia the trivia-preserving parser captures, so leave that parser in place (do not pair it with `no_trivia_only`). Cannot be combined with `protocol_only`, which emits no CST module for the unparser to walk, and needs the default `gen_tool` — only the full generator carries the unparser subcommand. |
| `format_config` | A `.fltkfmt` spec baked into the generated unparser at generation time (spacing, anchors, dispositions). Editing it is an ordinary input change. Requires `unparser = True`; omitting it selects the default `FormatterConfig`. |

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

**Compiling the cdylib yourself is not supported.** A cdylib you assemble must compile the
generated `#[pyclass]` code against the *same* pyo3 instance `@fltk//crates/fltk-cst-core` links,
and crate_universe hub repos are module-local, so a downstream module has no way to name it. Build
Python extensions with `fltk_pyo3_cdylib` — see `TODO(bazel-consumer-pyo3-seam)` in `TODO.md`.

A pure-Rust crate gets its `.pyi` stub package from the same codegen target that emits its `.rs`:
set `protocol_module` and `extension_name` on the pure-Rust `generate_rust_parser` call your crate
already uses.

```starlark
generate_rust_parser(
    name = "mylang_srcs",
    src = "mylang.fltkg",
    out_dir = "src",                                  # the crate's own source directory
    extension_name = "mylang",                        # the importable module name
    protocol_module = "mypkg.mylang_cst_protocol",
    submodules = ["cst", "parser", "unparser", "other_cst"],
    unparser = True,
    format_config = "mylang.fltkfmt",
)
```

The `.rs` land under `out_dir` and the stub package under `<package>/<extension_name>/`, from one
action — a second, stubs-only codegen target would re-parse the grammar and regenerate the CST to
throw it away. Because the target's outputs are now of two kinds, the macro also declares
`:mylang_srcs_rust_srcs` (feed that to your `rust_library`'s `srcs`) and `:mylang_srcs_stub_srcs`
(the stub package, for whatever target ships it to your type checker).

`submodules` is the list written into the `__init__.pyi` marker. Leave it empty and the marker
names only what this action generated, which understates a crate root registering modules from
another grammar; state it explicitly when that is the case. It belongs to this hand-assembly
recipe only: with `python_extension = True` the macro builds the cdylib out of that one target's
sources, so a wider list would name submodules no stub file backs, and setting it there is an
error. A type checker reaches the package
by putting the directory *holding* it on its search path (`extraPaths`), since the directory
name is the import name.

---

## 5. Pure Rust

In pure-Rust mode `generate_rust_parser` emits `.rs` files and no cdylib. You compile them into
your own crate. (It emits the `.pyi` stub package too if you ask for one — see §4 for that
shape; without `protocol_module` there is no Python in the output at all.)

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

If your crate compiles only the CST — or only the unparser, which is generated against the
CST — add `parser = False`. The parser is the largest generated artifact for a grammar of any
size, and one nothing compiles is invisible: it is generated on every clean build, declared,
and simply never named by a `mod` declaration. `parser = False` is pure-Rust mode only, and
cannot be combined with `ast` or `serde` (both are generated against the parser module).

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
| `de.rs` | `@fltk//crates/fltk-serde-core:no_python`, plus the serde flag — see §6 |

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
structs derive from.** This is the whole story, and one flag is all it takes.

Generated `de.rs` describes your grammar's tree to the `fltk-serde-core` deserializer and
hands values to *your* `#[derive(Deserialize)]` structs. Those derives are generated by your
`serde_derive` and implement traits from your `serde`. By default
`@fltk//crates/fltk-serde-core` links `@fltk_crates//:serde` — FLTK's module-private hub
instance, a different crate instance by construction — and trait coherence then fails: your
structs implement *your* `serde::Deserialize`, and FLTK's deserializer wants *its* one.

**The recipe: point the serde flag at your hub.** `@fltk//crates/fltk-serde-core:serde` is a
`label_flag` naming the serde every FLTK Bazel target compiles against. Set it once, in your
`.bazelrc`, and every FLTK target in your build — the `:no_python` runtime library and the
cdylib assembly in `rust.bzl` alike — is on your instance:

```
build --@fltk//crates/fltk-serde-core:serde=@crates//:serde
```

`MODULE.bazel` then needs only the module pin and whatever hub your model structs already
resolve serde from:

```starlark
bazel_dep(name = "fltk", version = "")
git_override(
    module_name = "fltk",
    remote = "https://github.com/rnortman/fltk",
    commit = "<sha>",
)

crate = use_extension("@rules_rust//crate_universe:extensions.bzl", "crate")
crate.spec(package = "serde", version = "1", features = ["derive"])
crate.from_specs(
    name = "crates",
    cargo_lockfile = "//:cargo-bazel-resolved.lock",
    lockfile = "//:cargo-bazel-lock.json",
)
use_repo(crate, "crates")
```

Your hub declares `serde` and nothing of FLTK's: the runtime crates come from the module, so
there is no second pin to keep in lockstep with the `git_override`. This is the form FLTK's own
hubs use — no Cargo manifest anywhere — but `crate.from_cargo` with a manifest of your own works
identically for this purpose; the flag below is what matters, not where your serde comes from.

Track both lockfiles and commit them: `crate.from_specs` re-resolves your semver ranges at fetch
time without them, so a new serde release could change what your build compiles on an unchanged
commit. `CARGO_BAZEL_REPIN=1 bazel build …` is what rewrites the pair after a spec edit.

Then generate with FLTK's macro and link the `:no_python` targets exactly as §5 does:

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
        "@crates//:serde",
        "@fltk//crates/fltk-ast-core:no_python",
        "@fltk//crates/fltk-cst-core:no_python",
        "@fltk//crates/fltk-parser-core:no_python",
        "@fltk//crates/fltk-serde-core:no_python",
    ],
)
```

Generated code names runtime crates by plain paths (`::fltk_serde_core`, `::serde`), so it
resolves against whatever your graph provides — that is what makes this work. FLTK's crate
requirement is plain `serde = "1"` with hand-written impls, so any serde 1.x build satisfies
it; a `derive`-featured one is a superset.

What goes wrong if you forget the flag: `fltk-serde-core` silently keeps FLTK's serde and
your crate fails to compile with "two different versions of crate `serde`" walls that name
neither the flag nor this page. If you want that failure to arrive by name instead, assert
over your own graph that `@fltk_crates//:serde` is absent:

```bash
bazel cquery 'deps(//mylang:mylang)' | grep fltk_crates.*serde && echo "FAIL: fltk's serde is in the graph"
```

`tests/bazel_consumer` runs this configuration in CI: `//:consumer_serde` is a pure-Rust
serde crate whose model structs derive from a hub of the consumer module's own, and it
compiles only because the flag reaches `fltk-serde-core`.

---

## 7. Runtime CLIs

FLTK's command-line tools are public `py_binary` targets — there is no wheel and no console
entry point, so `bazel run` is the launch path:

| Target | What it is |
|---|---|
| `@fltk//:grammar_lsp` | Language server for FLTK's own DSLs; takes the language id (`fltkg`, `fltkfmt`, `fltklsp`) |
| `@fltk//:fltk_lsp` | The generic language server for *your* grammar (`--grammar`/`--lsp`/`--fmt`/`--resolver`) |
| `@fltk//:fltk_highlight` | Standalone ANSI semantic highlighter for a file in your language |
| `@fltk//:unparse_cli` | Format a file against a grammar + `.fltkfmt` spec |
| `@fltk//:genparser` | The generator CLI, for ad-hoc runs outside the codegen rules |

```bash
bazel run @fltk//:grammar_lsp -- fltkg
bazel run --run_under="cd $PWD &&" @fltk//:unparse_cli -- lang.fltkg lang.fltkfmt input.src
```

`--run_under="cd $PWD &&"` is needed wherever an argument is a relative path: `bazel run`
executes in the runfiles tree, so a relative path otherwise names a different file or none.

These are runtime tools, not codegen — nothing about them integrates with your grammar targets,
and they serve your own `.fltkg`/`.fltkfmt`/`.fltklsp` files as-is. `docs/lsp.md` has the editor
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

FLTK runs this shape over its own graphs, in `make bazel-test` (every `:no_python` target,
every `rust_binary`, and the compile-gate crate) and `make bazel-consumer-check` (the
cross-module consumer targets).

The one edge to watch is `fltk-cst-core`: it is the only runtime crate with a `python`
feature, and everything else reaches pyo3 through it. Take `:no_python` and the feature is
never on.

---

## 9. Guard rails, collected

| Situation | What happens |
|---|---|
| `format_config` without `unparser = True` | error at loading time (`generate_rust_parser`) / at analysis time (`generate_parser`) |
| `parser = False` with `ast`, `serde`, or `python_extension = True` | error at loading time |
| `unparser` with `protocol_only = True` | error at analysis time |
| `out_dir` with `python_extension = True` | error at loading time |
| `submodules` or `extension_name` without `protocol_module` | error at loading time |
| `protocol_module` in pure-Rust mode without `extension_name` | error at loading time |
| `extension_name` or `submodules` with `python_extension = True` | error at loading time |
| `out_dir` absolute or containing `..` | error at loading time |
| `serde = True` without `ast_config` | error at loading time |
| cdylib-only attrs (`lib_rs`, `deps`, `crate_features`, `recursion_limit`) in pure-Rust mode | error at loading time |
| Both crate flavors in one binary | rustc duplicate-crate-name error |
| Hand-authored `lib_rs` missing a `mod` declaration | green build, submodule silently absent |
| Rev pinned that is not published | consumer fetch fails |
| Serde mode with the serde flag left at its default | "two different versions of crate `serde`" at compile time (§6) |
