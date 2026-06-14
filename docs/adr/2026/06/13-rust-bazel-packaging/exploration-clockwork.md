# Clockwork Downstream Consumer — Exploration Report

## 1. How fltk is pulled in

**Mechanism: Bazel module via `git_override`** — FLTK is consumed as a Bazel
submodule, available to Clockwork's build files as `@fltk//...`. (This is a
*Bazel* submodule, resolved by `bazel_dep` + `git_override`; it is not a git
submodule and not `archive_override`.)

File: `/home/rnortman/tps/clockwork/MODULE.bazel`

- Line 34: entry in the `dependencies` list:
  ```
  ("fltk", "https://github.com/rnortman/fltk.git", "0afecaf5fe40a374c4f7ab5ac3cb9fc8953e81f3", NO_PATCH),  # main
  ```
- Lines 89–98: loop that emits `bazel_dep` + `git_override` for every `.git` remote:
  ```python
  [bazel_dep(name = name) for name, _, _, _ in dependencies]
  [git_override(
      module_name = name,
      commit = commit,
      ...
      remote = remote,
  ) for name, remote, commit, should_patch in dependencies if remote.endswith(".git")]
  ```

Pinned commit: `0afecaf5fe40a374c4f7ab5ac3cb9fc8953e81f3` (comment says `# main`).

No patch applied (`NO_PATCH`). No git submodule (`.gitmodules` does not exist). No entry in `third_party/patches/` for fltk.

fltk's own `MODULE.bazel` (`/home/rnortman/src/fltk/MODULE.bazel`) declares `module(name = "fltk")` with no Rust deps — `rules_rust` is absent from fltk's module file today.

## 2. The clockwork.fltkg grammar

File: `/home/rnortman/tps/clockwork/clockwork/dsl/clockwork.fltkg` — 413 lines.

Top-level rule (line 1):
```
module := (doc . '\n')? , ((clk_generate , clk_inner_attrs? , clk_use* , clk_entity+) | (use* , entity+));
```
The grammar covers the full Clockwork DSL: cog, schema, enum, representation, tag, channel, signal, udp_socket, multicast_udp_socket, box, strong_type, policy_def, policy, extern_type, cpu_domain, ethernet, dfl_trait_def, dfl_impl_decl, dfl_fn_def, and their sub-rules.

## 3. BUILD rule that invokes the generator

File: `/home/rnortman/tps/clockwork/clockwork/dsl/BUILD.bazel`

- Line 4: `load("@fltk//:rules.bzl", "generate_parser")` — imports the custom Starlark rule from fltk.
- Lines 57–62: invocation:
  ```python
  generate_parser(
      name = "generate_parser",
      src = "clockwork.fltkg",
      base_name = "clockwork",
      cst_mod_path = "clockwork.dsl.clockwork_cst",
  )
  ```
  No `trivia_only` or `no_trivia_only` attributes — the default path, which generates **both** parsers: `clockwork_cst.py`, `clockwork_parser.py`, `clockwork_trivia_parser.py`.

The `generate_parser` rule is defined in `/home/rnortman/src/fltk/rules.bzl` (lines 1–71). It invokes the `@fltk//:genparser` `py_binary` (defined in `/home/rnortman/src/fltk/BUILD.bazel` lines 9–16), which runs `fltk/fegen/genparser.py`.

The genparser binary is declared in fltk's BUILD.bazel:
```python
py_binary(
    name = "genparser",
    srcs = ["fltk/fegen/genparser.py"],
    visibility = ["//visibility:public"],
    deps = [":fltk", "@pypi//astor", "@pypi//typer"],
)
```

## 4. How the generated parser is consumed

The `generate_parser` rule outputs files (declared via `depset`) but is not itself a `py_library`. The generated `.py` files are consumed by two `py_library` targets in `clockwork/dsl/BUILD.bazel`:

- Lines 35–39: `clockwork_cst` — `srcs = [":generate_parser"]`, `deps = ["@fltk"]`
- Lines 41–48: `clockwork_parser` — `srcs = [":generate_parser"]`, `deps = [":clockwork_cst", "@fltk"]`

Downstream Python libraries depend on `//clockwork/dsl:clockwork_cst` directly. Representative consuming targets (all `py_library`, all in `clockwork/dsl/ir/BUILD.bazel`):

- `parse` (line 661–667): `deps = ["//clockwork/dsl:clockwork_cst", "@fltk"]`
- `node` (line 647–658): `deps = ["//clockwork/dsl:clockwork_cst", "//clockwork/dsl:compiler_context", "@fltk"]`
- `cst_util` (line 341–350): `deps = [":module_id", "//clockwork/dsl:clockwork_cst", "@fltk"]`
- `compiler` (line 145–200): `deps` include `//clockwork/dsl:clockwork_cst` and `@fltk`
- `dfl` (line 352–370): `deps` include `//clockwork/dsl:clockwork_cst` and `@fltk`
- `report_group` (line 829–850): `deps` include `//clockwork/dsl:clockwork_cst` and `@fltk`

Generated CST is not checked in — `clockwork/dsl/` contains no `clockwork_cst.py` or `clockwork_parser.py`; those are Bazel action outputs only.

Python import pattern in consuming code (e.g. `parse.py` lines 10–11):
```python
from clockwork.dsl import clockwork_cst as cst
from clockwork.dsl import clockwork_parser as parser
```

The `@fltk` label (the `py_library` target at `/home/rnortman/src/fltk/BUILD.bazel` lines 18–25) is a direct runtime dependency because fltk's runtime Python modules (`fltk.fegen.pyrt.*`) are used directly in consuming code. Example: `parse.py` line 12 imports `from fltk.fegen.pyrt import errors, terminalsrc`.

The root `BUILD.bazel` gazelle directive at line 34 maps the bare Python import `fltk` to `@fltk`:
```
# gazelle:resolve py fltk @fltk
```

## 5. Bazel setup generally

- Bazel version: **8.4.2** (from `/home/rnortman/tps/clockwork/.bazelversion`)
- `MODULE.bazel` line 57: `("rules_python", SINGLE_VERSION_OVERRIDE, "1.5.4", PATCH)`
- `MODULE.bazel` line 51: `("rules_go", SINGLE_VERSION_OVERRIDE, "0.59.0", PATCH)` — Go is present
- `MODULE.bazel` line 36: `("gazelle", ...)` — gazelle present for Go and Python
- **`rules_rust` is NOT present** in `MODULE.bazel`. No Rust toolchain is registered for clockwork itself. (fltk's Rust extension is built via maturin in the Python/uv path, which is not used here — Bazel uses only the pure-Python `py_library` `@fltk` target today.)
- clockwork is mixed-language: C++, Python, Go, TypeScript are all present. No Rust source in clockwork itself.

## 6. Test targets that exercise the generated parser

All tests are `py_test` targets using pytest (via `aspect_rules_py`'s `py_pytest_main`). The test suite is in `clockwork/dsl/ir/tests/BUILD.bazel`. Representative tests that transitively depend on the generated parser through `//clockwork/dsl:clockwork_cst`:

- `cog_test` (line 126–160): deps include `//clockwork/dsl:clockwork_cst`, `//clockwork/dsl:compiler_context`, and `//clockwork/dsl/ir:parse`
- `schema_test` (line 882–908): deps include `//clockwork/dsl:clockwork_cst` and `//clockwork/dsl/ir:parse`
- `dfl_test` (line 379–406): deps include `//clockwork/dsl:clockwork_cst`, `@fltk`
- `dfl_integration_test` (line 350–377): deps include `//clockwork/dsl:clockwork_cst`, `@fltk`
- `expr_test` (line 459–478): deps include `//clockwork/dsl:clockwork_cst`, `@fltk`
- `node_test` (line 601–625): deps include `//clockwork/dsl/ir:parse`
- `box_test`, `cog_test`, `compiler_test`, `importer_test`, etc. all transitively depend on the parser through `//clockwork/dsl/ir:compiler` which depends on `//clockwork/dsl:clockwork_cst`.

One CC test exists (`report_group_schema_test`, line 821–829) but it depends on `//clockwork/dsl/ir/tests/support:report_group_defs_dial` — C++ code generated from the DSL, not from fltk directly.

## 7. Summary of the fltk integration surface

| Artifact | Role | Consumed as |
|---|---|---|
| `@fltk//:genparser` py_binary | Runs at build time to generate CST + parser `.py` files | Bazel `exec` tool inside `generate_parser` rule |
| `@fltk` py_library | Runtime dep: provides `fltk.fegen.pyrt.*` modules | `deps = ["@fltk"]` in py_library targets |
| `@fltk//:rules.bzl` `generate_parser` rule | Starlark build rule | `load("@fltk//:rules.bzl", "generate_parser")` |
| Generated `clockwork_cst.py` | CST node classes (public API consumed broadly) | `from clockwork.dsl import clockwork_cst as cst` |
| Generated `clockwork_parser.py` | Parser class | `from clockwork.dsl import clockwork_parser as parser` |
| Generated `clockwork_trivia_parser.py` | Trivia-preserving parser (generated but not yet observed in an import) | (generated by default) |

The Rust extension module (PyO3/maturin) is **not involved at all** in the Bazel build path clockwork uses. Clockwork uses the pure-Python `fltk` `py_library` target exclusively.
