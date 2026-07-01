# Exploration: `generate_parser` / `generate_rust_parser` Bazel rules and protocol-module wiring

## 1. Full rule definitions

### `generate_parser` (Python) — `/home/rnortman/src/fltk/rules.bzl:1-82`

```
_genparser_impl               rules.bzl:1-45
generate_parser = rule(...)   rules.bzl:47-82
```

Full text (rules.bzl:1-82):

```python
def _genparser_impl(ctx):
    args = ctx.actions.args()
    args.add("generate")
    args.add_all([ctx.file.src, ctx.attr.base_name, ctx.attr.cst_mod_path])

    # Auto-compute output file names based on base_name
    cst_file = ctx.actions.declare_file(ctx.attr.base_name + "_cst.py")
    outputs = [cst_file]

    # Set output directory to where Bazel will place the declared files
    args.add_all(["--output-dir", cst_file.dirname])

    # Control which parsers to generate
    if ctx.attr.trivia_only:
        args.add("--trivia-only")
    elif ctx.attr.no_trivia_only:
        args.add("--no-trivia-only")
    # Default generates both parsers

    # Conditionally declare parser outputs based on configuration
    if not ctx.attr.trivia_only:
        parser_file = ctx.actions.declare_file(ctx.attr.base_name + "_parser.py")
        outputs.append(parser_file)

    if not ctx.attr.no_trivia_only:
        trivia_parser_file = ctx.actions.declare_file(ctx.attr.base_name + "_trivia_parser.py")
        outputs.append(trivia_parser_file)

    # Opt-in protocol module (off by default).
    if ctx.attr.protocol:
        args.add("--protocol")
        protocol_file = ctx.actions.declare_file(ctx.attr.base_name + "_cst_protocol.py")
        outputs.append(protocol_file)

    # Action to call the script.
    ctx.actions.run(
        inputs = ctx.files.src,
        outputs = outputs,
        arguments = [args],
        progress_message = "Generating parser(s) for grammar %s" % ctx.file.src.short_path,
        executable = ctx.executable._gen_tool,
    )

    # Return providers with the generated files
    return [DefaultInfo(files = depset(outputs))]

generate_parser = rule(
    implementation = _genparser_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, mandatory = True, doc = "The FLTK grammar file (.fltkg)"),
        "base_name": attr.string(mandatory = True, doc = "Base name for output files (without extension)"),
        "cst_mod_path": attr.string(mandatory = True, doc = "Base module name for CST classes"),
        "trivia_only": attr.bool(default = False, doc = "Generate only the trivia-preserving parser"),
        "no_trivia_only": attr.bool(default = False, doc = "Generate only the non-trivia parser"),
        "protocol": attr.bool(default = False, doc = "Also generate the protocol module ({base_name}_cst_protocol.py)"),
        "_gen_tool": attr.label(default = Label(":genparser"), executable = True, allow_files = True, cfg = "exec"),
    },
)
```

### `generate_rust_parser` (Rust) — `/home/rnortman/src/fltk/rust.bzl:100-267`

```
_generate_rust_parser_impl        rust.bzl:102-190
generate_rust_parser = rule(...)  rust.bzl:192-267
```

Key structure (full text in rust.bzl:100-267): two independent `ctx.actions.run` calls —
Action 1 (`gen-rust-cst`, rust.bzl:132-172) and Action 2 (`gen-rust-parser`, rust.bzl:174-188) —
combined into one `DefaultInfo(files = depset(cst_outputs + [parser_out]))` (rust.bzl:190).

Companion rule `generate_rust_lib` (rust.bzl:25-98, `generate_rust_lib = rule(...)` at rust.bzl:58-98)
runs `gen-rust-lib` to synthesize `lib.rs` when a consumer doesn't hand-author one; it is invoked
by the `fltk_pyo3_cdylib` macro (see §5) when `lib_rs == None` (rust.bzl:359-364).

## 2. Protocol opt-in attributes

### Python side — `protocol: attr.bool`

- Declaration: rust... no, Python rule — `rules.bzl:71-74`:
  ```python
  "protocol": attr.bool(
      default = False,
      doc = "Also generate the protocol module ({base_name}_cst_protocol.py)",
  ),
  ```
- Threading: `rules.bzl:30-33` — `if ctx.attr.protocol: args.add("--protocol"); protocol_file = ctx.actions.declare_file(ctx.attr.base_name + "_cst_protocol.py"); outputs.append(protocol_file)`.
- This directly maps to the CLI's `generate --protocol` flag (see §4).

### Rust side — TWO attributes: `protocol_module: attr.string` and `generate_protocol: attr.bool`

- Declarations: `rust.bzl:210-229`:
  ```python
  "protocol_module": attr.string(
      default = "",
      doc = ("Dotted Python import path of the protocol module (e.g. "
             "'my.pkg.grammar_cst_protocol'). When non-empty, the gen-rust-cst "
             "action also emits the .pyi type stub (<name>/cst.pyi) and the "
             "stub-package marker (<name>/__init__.pyi, with --extension-name "
             "<name> --submodules cst,parser), declaring both as outputs so "
             "<name>/ is a complete stub package. When empty, no .pyi is produced."),
  ),
  "generate_protocol": attr.bool(
      default = False,
      doc = ("When True, the gen-rust-cst action also writes the protocol .py "
             "module (<name>/cst_protocol.py), declared as an output. Requires "
             "protocol_module to be non-empty (the rule fails at analysis time "
             "otherwise). Off by default."),
  ),
  ```
- Threading (rust.bzl:115-172):
  - `protocol_module = ctx.attr.protocol_module` and `generate_protocol = ctx.attr.generate_protocol` read at rust.bzl:115-116.
  - Analysis-time guard, rust.bzl:118-121: `if generate_protocol and not protocol_module: fail("generate_rust_parser: generate_protocol = True requires a non-empty protocol_module.")` — this mirrors the CLI's own `--protocol-output requires --protocol-module` check (see §4, genparser.py:458-459).
  - `if protocol_module:` block (rust.bzl:138-157) unconditionally (whenever `protocol_module` is set) adds `--protocol-module <value>`, `--pyi-output <name>/cst.pyi`, `--init-pyi-output <name>/__init__.pyi`, `--extension-name <name>`, `--submodules cst,parser` to the `gen-rust-cst` invocation, and declares `cst.pyi` / `__init__.pyi` as outputs.
  - Nested `if generate_protocol:` block (rust.bzl:159-164), only reachable when `protocol_module` is also set, adds `--protocol-output <name>/cst_protocol.py` and declares that file as an output.

So: the Python rule uses a single bool `protocol=True` to opt in to protocol-module generation; the Rust rule uses `protocol_module` (a required string — the dotted import path) as the trigger for `.pyi`/marker generation, and a *separate* bool `generate_protocol=True` (which requires `protocol_module` to be non-empty) as the trigger for the protocol `.py` module itself. Confirmed against the current `BUILD.bazel` example comment (rust.bzl:263-264 / doc string at rust.bzl:248-249, and the commented-out example at `BUILD.bazel` is not present — the example lives in the rule's `doc` string, rust.bzl:258-266):
```python
generate_rust_parser(
    name = "clockwork_rs_srcs",
    src  = "clockwork.fltkg",
    cst_mod_path = "super::cst",  # default; can omit
    # protocol_module = "clockwork.clockwork_cst_protocol",  # opt-in .pyi
    # generate_protocol = True,                              # opt-in protocol .py
)
```

## 3. Output path derivation

### Python rule

Output directory is the Bazel-declared file's own directory, computed once from `cst_file.dirname` (rules.bzl:11): `args.add_all(["--output-dir", cst_file.dirname])`. Filenames are `{base_name}_cst.py`, `{base_name}_parser.py`, `{base_name}_trivia_parser.py`, `{base_name}_cst_protocol.py` (rules.bzl:7,22,26,32), where `base_name` is the rule's own `base_name` attribute (mandatory string, rules.bzl:55-58) — **not** derived from any other rule.

### Rust rule

All Rust-side outputs are declared under a subdirectory named after **`generate_rust_parser`'s own rule `name`** (`ctx.attr.name`), NOT the `fltk_pyo3_cdylib` rule name:
- `cst_out = ctx.actions.declare_file(ctx.attr.name + "/cst.rs")` (rust.bzl:124)
- `parser_out = ctx.actions.declare_file(ctx.attr.name + "/parser.rs")` (rust.bzl:125)
- `cst_pyi = ctx.actions.declare_file(ctx.attr.name + "/cst.pyi")` (rust.bzl:144)
- `init_pyi = ctx.actions.declare_file(ctx.attr.name + "/__init__.pyi")` (rust.bzl:145)
- `protocol_out = ctx.actions.declare_file(ctx.attr.name + "/cst_protocol.py")` (rust.bzl:161)

Additionally, the `--extension-name` CLI flag passed to `gen-rust-cst` (rust.bzl:152-153: `cst_args.add("--extension-name"); cst_args.add(ctx.attr.name)`) is also `ctx.attr.name` of the `generate_rust_parser` rule itself — again not the `fltk_pyo3_cdylib` rule's `name`.

In the one real out-of-tree caller found (`/home/rnortman/tps/clockwork/clockwork/dsl/BUILD.bazel:70-82`):
```python
generate_rust_parser(
    name = "clockwork_rs_srcs",
    src = "clockwork.fltkg",
    # cst_mod_path defaults to "super::cst" ...
)

fltk_pyo3_cdylib(
    name = "clockwork_native",
    rs_srcs = ":clockwork_rs_srcs",
    # lib_rs omitted: generated from name="clockwork_native" via gen-rust-lib.
    visibility = ["//clockwork:__subpackages__"],
)
```
Here `generate_rust_parser`'s `name` is `clockwork_rs_srcs` (so, were `protocol_module` set, outputs would land under `clockwork_rs_srcs/` and `--extension-name clockwork_rs_srcs` would be passed), while `fltk_pyo3_cdylib`'s `name` (`clockwork_native`) is the value used elsewhere as the compiled PyO3 module/crate name (`module_name = name` at rust.bzl:362 inside `generate_rust_lib`, and `crate_name = name` at rust.bzl:414 for `rust_shared_library`). Neither `generate_protocol` nor `protocol_module` is currently set on this Clockwork call site — they are left at their defaults (commented out in the fltk in-tree examples too; no live example passes them). No code path in `rust.bzl` or `rules.bzl` reads `fltk_pyo3_cdylib`'s `name` attribute when computing `generate_rust_parser`'s output paths or `--extension-name`; that value is a caller-supplied attribute of a separate macro invocation (§5) and is only threaded into `generate_rust_lib`/`rust_shared_library`, not into `generate_rust_parser`.

## 4. Underlying codegen entry point(s)

CLI: `/home/rnortman/src/fltk/fltk/fegen/genparser.py`, invoked as `ctx.executable._gen_tool` = `Label(":genparser")` / `Label("//:genparser")` (rules.bzl:76, rust.bzl:78,231), which is the `py_binary` target `//:genparser` (`BUILD.bazel:13-22`, `srcs = ["fltk/fegen/genparser.py"]`).

- `generate` command (genparser.py:128) — Python backend. Relevant params: `protocol_only` (genparser.py:146-149, `--protocol-only`), `protocol` (genparser.py:160, `--protocol`, added in commit 3b95f0a). Logic: `if protocol or protocol_only:` (genparser.py:241) writes `{base_name}_cst_protocol.py` via `cstgen.gen_protocol_module_text()` (genparser.py:247; method defined at `/home/rnortman/src/fltk/fltk/fegen/gsm2tree.py:800`). Previously (pre-3b95f0a) the protocol module was written unconditionally; commit 3b95f0a made it opt-in.
- `gen-rust-cst` command (genparser.py:330) — Rust backend. New flags from 3b95f0a: `protocol_output` (genparser.py:361-372, `--protocol-output`), `init_pyi_output`/`extension_name`/`submodules` (genparser.py:373-...`--init-pyi-output`/`--extension-name`/`--submodules`). Validation: `if protocol_output is not None and protocol_module is None: ... "Error: --protocol-output requires --protocol-module"` (genparser.py:458-459) — the same check the Bazel rule replicates at analysis time (rust.bzl:118-121). Generation: `protocol_text = gen.generate_protocol()` (genparser.py:482), calling `RustCstGenerator.generate_protocol()` (`/home/rnortman/src/fltk/fltk/fegen/gsm2tree_rs.py:426`), documented (gsm2tree_rs.py:429-430) to produce output "byte-identical to the Python `generate --protocol` output for the same grammar". `.pyi` generation is `gen.generate_pyi(protocol_module)` (genparser.py, `RustCstGenerator.generate_pyi` at gsm2tree_rs.py:321).
- `gen-rust-parser` command (genparser.py:571) — invoked by Action 2 of `generate_rust_parser` (rust.bzl:174-188); does not itself take protocol flags (protocol wiring is entirely inside `gen-rust-cst`).
- `gen-rust-unparser` command (genparser.py, ~line 640+) also gained `--init-pyi-output`/`--extension-name`/`--submodules` in the same commit (used for dogfooded fixtures, not wired into `generate_rust_parser`/`generate_rust_lib` Bazel rules).

### Commit 3b95f0a wiring (from `git show 3b95f0a -- rules.bzl rust.bzl fltk/fegen/genparser.py Makefile`)

- `rules.bzl` diff: added the `protocol` bool attr (rules.bzl:71-74) and the `if ctx.attr.protocol:` block (rules.bzl:30-33) — the entire Python-side Bazel change.
- `rust.bzl` diff: added `protocol_module`/`generate_protocol` attrs, the `fail()` guard, the `if protocol_module:` / nested `if generate_protocol:` blocks, and changed the Action-1 outputs from the previous fixed `outputs = [cst_out]` to the accumulated `cst_outputs` list — i.e., before this commit `generate_rust_parser` had no protocol/`.pyi` support at all.
- No changes to `BUILD.bazel` in this commit (verified via `git show 3b95f0a -- ... BUILD.bazel` producing no diff hunks for that path) — the in-tree smoke targets (`bootstrap_rust_srcs`, `bootstrap_native`) still don't set `protocol_module`/`generate_protocol`.
- `genparser.py`: added `--protocol` to `generate` (guarded write), added `--protocol-output`/`--init-pyi-output`/`--extension-name`/`--submodules` to `gen-rust-cst`, added `_render_init_pyi` helper (genparser.py:~525) calling `gsm2lib_rs.render_stub_package_init`.
- `Makefile`: `gencode` target updated to pass `--protocol` to every Python `generate` invocation (previously protocol was unconditional/default) and to pass `--init-pyi-output --extension-name --submodules` to the in-tree `gen-rust-cst`/`gen-rust-unparser` invocations for `fegen_rust_cst` and `rust_parser_fixture`.

## 5. Macro tying `generate_rust_parser` and `fltk_pyo3_cdylib` together

`fltk_pyo3_cdylib` (`/home/rnortman/src/fltk/rust.bzl:271-462`) is a `def` macro (not a `rule`) that takes `rs_srcs` — expected to be a `generate_rust_parser` target label (doc explicitly requires this at rust.bzl:325-333: "Always pass a generate_rust_parser target here"). It does NOT call `generate_rust_parser` itself; the caller instantiates `generate_rust_parser` separately and passes its label in. Four steps (rust.bzl:283-301, implemented at rust.bzl:359-462):

1. Optionally auto-generates `lib.rs` via `generate_rust_lib(name = name + "_gen_lib", module_name = name)` when `lib_rs == None` (rust.bzl:359-364) — this is the one place `fltk_pyo3_cdylib`'s own `name` is threaded into a sibling rule (`module_name = name`, rust.bzl:362), and it must match the `#[pymodule] fn <name>` in the generated/consumer `lib.rs` (rust.bzl:320-324).
2. `native.genrule(name = name + "_assemble_crate", srcs = [lib_rs, rs_srcs], outs = [crate_lib_rs, crate_cst_rs, crate_parser_rs], ...)` (rust.bzl:387-406) copies `lib.rs` + every file from `rs_srcs`'s outputs (by basename) into one flat directory `<name>_crate_root/`, prepending `#![recursion_limit = "<N>"]`. This step only asserts presence of `cst.rs`/`parser.rs` (rust.bzl:398-399); it says nothing about `.pyi`/protocol files, which are declared as `generate_rust_parser` outputs but are not consumed by the assembly genrule (they're exposed via `generate_rust_parser`'s own `DefaultInfo`, e.g. for downstream `py_library`/pyright targets that depend on `:clockwork_rs_srcs` directly, not through `fltk_pyo3_cdylib`).
3. `rust_shared_library(name = name + "_cdylib", srcs = [":" + name + "_assemble_crate"], crate_name = name, ...)` (rust.bzl:409-435).
4. ABI3 rename genrule (rust.bzl:441-447) and `py_library(name = name, data = [":" + name + "_so"], deps = [Label("@fltk//:native_py")], imports = ["."], visibility = visibility)` (rust.bzl:456-462).

Confirmed real-world pairing in Clockwork (`/home/rnortman/tps/clockwork/clockwork/dsl/BUILD.bazel:70-82`, quoted in §3 above): `generate_rust_parser(name = "clockwork_rs_srcs", ...)` followed by `fltk_pyo3_cdylib(name = "clockwork_native", rs_srcs = ":clockwork_rs_srcs", ...)`. This is the only external (out-of-tree) consumer found under `/home/rnortman/tps/clockwork`; a `grep` for `protocol_module`/`generate_protocol` there returned no matches — Clockwork does not currently exercise the protocol-module opt-in on either rule.
