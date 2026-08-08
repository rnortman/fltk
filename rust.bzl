"""FLTK Rust Bazel rules.

This file provides:
  - generate_rust_parser: the public macro consumers call. In its default
    (pure-Rust) mode it runs FLTK's Rust codegen on a grammar file and emits
    cst.rs + parser.rs as Bazel action outputs — plus ast.rs (ast = True) and
    de.rs (serde = True, which also needs the .fltkast sidecar as ast_config).
    With python_extension = True it additionally assembles the crate, compiles
    the PyO3 cdylib, generates the .pyi stub package, and wraps the result in a
    py_library.
  - fltk_pyo3_cdylib: the public helper (loaded by consumers as
    `load("@fltk//:rust.bzl", "fltk_pyo3_cdylib")`) that
    compiles those generated sources + a consumer-authored lib.rs into a PyO3
    cdylib (rust_shared_library with extension-module), wrapped in a py_library
    that places the resulting .so on the correct import path and carries
    @fltk//:native_py so that `import fltk._native` resolves in the test sandbox.

Load this file to use the Rust-backend Bazel integration:
    load("@fltk//:rust.bzl", "generate_rust_parser")

This file is intentionally separate from rules.bzl so that a pure-Python Bazel
consumer that never loads rust.bzl does not transitively require rules_rust to be
registered.
"""

load("@rules_rust//rust:defs.bzl", "rust_shared_library")
load("@rules_python//python:defs.bzl", "py_library")

# Default recursion_limit injected into the assembled PyO3 crate root. Single
# owner shared by the fltk_pyo3_cdylib / generate_rust_parser signatures and the
# pure-Rust "left at default?" misconfiguration guard, so the guard tracks the
# default automatically instead of comparing against a hardcoded literal.
_DEFAULT_RECURSION_LIMIT = 512

def _protocol_module_violation(protocol, protocol_module):
    """Return the protocol → protocol_module coupling failure message, or None.

    `protocol = True` requires a non-empty `protocol_module`. Shared by the public
    macro and the internal rule's analysis-time guard so the two cannot drift.
    """
    if protocol and not protocol_module:
        return "generate_rust_parser: protocol = True requires a non-empty protocol_module."
    return None

def _require_protocol_module(protocol, protocol_module):
    """Fire the protocol → protocol_module coupling guard (fail on violation)."""
    msg = _protocol_module_violation(protocol, protocol_module)
    if msg != None:
        fail(msg)

def _codegen_mode_violation(ast, serde, has_ast_config, goal = ""):
    """Return the ast/serde/ast_config/goal misconfiguration message, or None.

    Three conditions:
      - `serde = True` requires ast_config.
      - An `ast_config` with neither `ast` nor `serde` has no consumer and would be
        silently ignored.
      - A `goal` with neither `ast` nor `serde` is the same: only the gen-rust-ast and
        gen-rust-serde actions take --goal; the cst and parser actions never see it.

    `ast = True` without a sidecar is NOT a violation — a grammar-derived (Tier 0) AST is a
    supported mode.
    """
    if serde and not has_ast_config:
        return "generate_rust_parser: serde = True requires ast_config (the .fltkast sidecar shaping the tree)."
    if has_ast_config and not (ast or serde):
        return "generate_rust_parser: ast_config requires ast = True or serde = True; nothing else reads it."
    if goal and not (ast or serde):
        return "generate_rust_parser: goal requires ast = True or serde = True; nothing else reads it."
    return None

def _require_codegen_mode(ast, serde, has_ast_config, goal = ""):
    """Fire the ast/serde/ast_config/goal guard (fail on violation)."""
    msg = _codegen_mode_violation(ast, serde, has_ast_config, goal)
    if msg != None:
        fail(msg)

def _plain_modules_for(ast, serde):
    """The Rust-only modules a generated crate root declares, in `mod` order.

    The generated ast.rs / de.rs hold no pyclasses and no register_classes, so they reach the
    crate root as `pub mod` declarations and nothing else. An .rs file that lands in a crate's
    srcs but is named by no `mod` declaration is simply not compiled and rustc reports nothing,
    so this mapping has no compile-time witness — hence its own function and its own tests.
    """
    return (["ast"] if ast else []) + (["de"] if serde else [])

def _sibling_mod_path(cst_mod_path, module):
    """Return the Rust module path of `module` as a sibling of cst_mod_path.

    The generated files are assembled flat into one crate root (fixed basenames cst.rs /
    parser.rs / ast.rs / de.rs), so parser, ast and de are always siblings of cst. Deriving
    their module paths from cst_mod_path keeps that layout stated once: "super::cst" yields
    "super::parser", "crate::grammar::cst" yields "crate::grammar::parser". A single-segment
    path (no "::") yields the bare module name.
    """
    parts = cst_mod_path.split("::")
    return "::".join(parts[:-1] + [module])

def _pure_rust_mode_violation(
        protocol_module,
        protocol,
        lib_rs,
        deps,
        crate_features,
        recursion_limit):
    """Return the pure-Rust-mode misconfiguration message, or None.

    In pure-Rust mode (python_extension = False) the Python-extension-only knobs
    must be left at their defaults; setting any of them has no effect and is a
    misconfiguration. Each entry pairs the attribute name with "was it set away
    from its default?"; normalizing on that boolean lets one loop + one message
    template cover all six knobs (truthy defaults and sentinel defaults alike),
    so a new python-extension-only knob just adds one tuple. recursion_limit is
    compared against _DEFAULT_RECURSION_LIMIT here, preserving that constant as
    the single owner of the default. Returns the message for the first offending
    knob, or None; the macro wraps it in `if msg != None: fail(msg)`.
    """
    python_only_knobs = [
        ("protocol_module", bool(protocol_module)),
        ("protocol", bool(protocol)),
        ("lib_rs", lib_rs != None),
        ("deps", bool(deps)),
        ("crate_features", bool(crate_features)),
        ("recursion_limit", recursion_limit != _DEFAULT_RECURSION_LIMIT),
    ]
    for attr_name, is_set in python_only_knobs:
        if is_set:
            return "generate_rust_parser: {} is only valid with python_extension = True.".format(attr_name)
    return None

# ---- generate_rust_lib ----------------------------------------------------------

def _generate_rust_lib_impl(ctx):
    """Implementation for generate_rust_lib rule.

    Runs: genparser gen-rust-lib <out> --module-name <name> [flags...]

    The output file is always named "lib.rs" in a subdirectory named after the
    rule, so that fltk_pyo3_cdylib's assembly genrule can reference it via a
    single-file depset.
    """
    lib_out = ctx.actions.declare_file(ctx.attr.name + "/lib.rs")

    args = ctx.actions.args()
    args.add("gen-rust-lib")
    args.add(lib_out)
    args.add("--module-name")
    args.add(ctx.attr.module_name)
    if ctx.attr.no_cst:
        args.add("--no-cst")
    if ctx.attr.register_span_types:
        args.add("--register-span-types")
    if ctx.attr.unknown_span_static:
        args.add("--unknown-span-static")
    for mod_name in ctx.attr.plain_modules:
        args.add("--plain-module")
        args.add(mod_name)

    ctx.actions.run(
        inputs = [],
        outputs = [lib_out],
        arguments = [args],
        executable = ctx.executable._gen_tool,
        progress_message = "Generating Rust lib.rs for module %s" % ctx.attr.module_name,
    )

    return [DefaultInfo(files = depset([lib_out]))]

generate_rust_lib = rule(
    implementation = _generate_rust_lib_impl,
    attrs = {
        "module_name": attr.string(
            mandatory = True,
            doc = "The Rust module name passed to gen-rust-lib as --module-name. Must be a valid Rust identifier and match the #[pymodule] fn name in the generated lib.rs.",
        ),
        "no_cst": attr.bool(
            default = False,
            doc = "Pass --no-cst to gen-rust-lib; generates a span-only lib.rs with no grammar submodules.",
        ),
        "register_span_types": attr.bool(
            default = False,
            doc = "Pass --register-span-types to gen-rust-lib.",
        ),
        "unknown_span_static": attr.bool(
            default = False,
            doc = "Pass --unknown-span-static to gen-rust-lib.",
        ),
        "plain_modules": attr.string_list(
            default = [],
            doc = (
                "Module names passed as --plain-module: declared as `pub mod <name>;` in the " +
                "generated lib.rs and never registered with the #[pymodule]. This is how the " +
                "Rust-only generated modules (ast, de) reach the crate root — they hold no " +
                "pyclasses and have no register_classes entry point."
            ),
        ),
        "_gen_tool": attr.label(
            default = Label("//:genparser"),
            executable = True,
            allow_files = True,
            cfg = "exec",
        ),
    },
    doc = """Generate a Rust lib.rs entry point for a PyO3 cdylib module.

Emits one action output:
  <name>/lib.rs — generated crate root declaring mod cst; mod parser; and #[pymodule].

Designed to be consumed by fltk_pyo3_cdylib (via the auto-generated lib_rs path)
or used standalone when a hand-authored lib.rs is not required.

Example:
    generate_rust_lib(
        name = "mymodule_lib_rs",
        module_name = "mymodule",
    )
""",
)

# ---- _generate_rust_srcs --------------------------------------------------------

def _generate_rust_srcs_impl(ctx):
    """Implementation for the _generate_rust_srcs rule.

    Runs two separate genparser actions:
      1. gen-rust-cst  <grammar> <cst_out>
      2. gen-rust-parser <grammar> <parser_out> --cst-mod-path <path>

    Both actions are independent (no shared --output-dir).  The generated files
    use fixed basenames "cst.rs" and "parser.rs" so that bare `mod cst;` /
    `mod parser;` declarations in a co-located lib.rs resolve correctly.
    """
    grammar = ctx.file.src

    protocol_module = ctx.attr.protocol_module
    protocol = ctx.attr.protocol
    ast_config = ctx.file.ast_config

    # Mirror the CLI's `--protocol-output requires --protocol-module` check,
    # surfacing the misconfiguration at analysis time.
    _require_protocol_module(protocol, protocol_module)

    # Defense-in-depth: the public macro checks at loading time; this guard catches
    # direct instantiation of the internal rule.
    _require_codegen_mode(ctx.attr.ast, ctx.attr.serde, ast_config != None, ctx.attr.goal)

    # The output subdirectory and the --extension-name CLI flag are both driven
    # by extension_name when it is set, and fall back to the rule's own target
    # name when it is empty (preserving today's pure-Rust behavior).  This
    # decouples the stub-package directory / extension name from the rule's
    # target name: the wrapping macro sets extension_name to the single owner
    # module name so the stub package is named after the compiled module.
    out_subdir = ctx.attr.extension_name or ctx.attr.name

    # Declare the two output files in the output subdirectory.
    cst_out = ctx.actions.declare_file(out_subdir + "/cst.rs")
    parser_out = ctx.actions.declare_file(out_subdir + "/parser.rs")

    # cst_out is always produced by the gen-rust-cst action; the .pyi / marker /
    # protocol outputs are appended below when protocol_module (and optionally
    # protocol) are set.
    cst_outputs = [cst_out]

    # stub_outputs collects the files that ride along on the compiled Python
    # module (the .pyi stub package and, when protocol = True, the protocol .py).
    # It stays empty when protocol_module is empty; it feeds the stub_srcs output
    # group returned below.
    stub_outputs = []

    # --- Action 1: gen-rust-cst ---
    cst_args = ctx.actions.args()
    cst_args.add("gen-rust-cst")
    cst_args.add(grammar)
    cst_args.add(cst_out)

    if protocol_module:
        # Expose the .pyi stub plus the stub-package __init__.pyi marker through
        # the same gen-rust-cst action, so <name>/ is a complete stub package in
        # the Bazel output tree.  The marker is generator-produced via
        # --init-pyi-output (not a ctx.actions.write fixed body), keeping it on the
        # same dogfooded path as the in-tree markers.
        cst_pyi = ctx.actions.declare_file(out_subdir + "/cst.pyi")
        init_pyi = ctx.actions.declare_file(out_subdir + "/__init__.pyi")
        cst_args.add("--protocol-module")
        cst_args.add(protocol_module)
        cst_args.add("--pyi-output")
        cst_args.add(cst_pyi)
        cst_args.add("--init-pyi-output")
        cst_args.add(init_pyi)
        cst_args.add("--extension-name")
        cst_args.add(out_subdir)
        cst_args.add("--submodules")
        cst_args.add("cst,parser")
        cst_outputs.append(cst_pyi)
        cst_outputs.append(init_pyi)
        stub_outputs.append(cst_pyi)
        stub_outputs.append(init_pyi)

        if protocol:
            # Opt-in protocol .py output (Change 1, Rust side).
            protocol_out = ctx.actions.declare_file(out_subdir + "/cst_protocol.py")
            cst_args.add("--protocol-output")
            cst_args.add(protocol_out)
            cst_outputs.append(protocol_out)
            stub_outputs.append(protocol_out)

    ctx.actions.run(
        inputs = [grammar],
        outputs = cst_outputs,
        arguments = [cst_args],
        executable = ctx.executable._gen_tool,
        progress_message = "Generating Rust CST for grammar %s" % grammar.short_path,
    )

    # --- Action 2: gen-rust-parser ---
    parser_args = ctx.actions.args()
    parser_args.add("gen-rust-parser")
    parser_args.add(grammar)
    parser_args.add(parser_out)
    parser_args.add("--cst-mod-path")
    parser_args.add(ctx.attr.cst_mod_path)

    ctx.actions.run(
        inputs = [grammar],
        outputs = [parser_out],
        arguments = [parser_args],
        executable = ctx.executable._gen_tool,
        progress_message = "Generating Rust parser for grammar %s" % grammar.short_path,
    )

    # --- Actions 3 and 4: gen-rust-ast / gen-rust-serde (opt-in) ---
    rule_srcs = [cst_out, parser_out]
    config_inputs = [ast_config] if ast_config != None else []
    parser_mod_path = _sibling_mod_path(ctx.attr.cst_mod_path, "parser")

    if ctx.attr.ast:
        ast_out = ctx.actions.declare_file(out_subdir + "/ast.rs")
        ast_args = ctx.actions.args()
        ast_args.add("gen-rust-ast")
        ast_args.add(grammar)
        ast_args.add(ast_out)
        ast_args.add("--cst-mod-path")
        ast_args.add(ctx.attr.cst_mod_path)
        ast_args.add("--parser-mod-path")
        ast_args.add(parser_mod_path)
        if ast_config != None:
            ast_args.add("--ast-config")
            ast_args.add(ast_config)
        if ctx.attr.goal:
            ast_args.add("--goal")
            ast_args.add(ctx.attr.goal)

        ctx.actions.run(
            inputs = [grammar] + config_inputs,
            outputs = [ast_out],
            arguments = [ast_args],
            executable = ctx.executable._gen_tool,
            progress_message = "Generating Rust AST for grammar %s" % grammar.short_path,
        )
        rule_srcs.append(ast_out)

    if ctx.attr.serde:
        de_out = ctx.actions.declare_file(out_subdir + "/de.rs")
        serde_args = ctx.actions.args()
        serde_args.add("gen-rust-serde")
        serde_args.add(grammar)
        serde_args.add(de_out)
        serde_args.add("--ast-config")
        serde_args.add(ast_config)
        serde_args.add("--cst-mod-path")
        serde_args.add(ctx.attr.cst_mod_path)
        serde_args.add("--parser-mod-path")
        serde_args.add(parser_mod_path)
        if ctx.attr.ast:
            # ast = True means an ast module exists for serde to target with
            # Deserialize impls; without it, --ast-mod-path has no referent.
            serde_args.add("--ast-mod-path")
            serde_args.add(_sibling_mod_path(ctx.attr.cst_mod_path, "ast"))
        if ctx.attr.goal:
            serde_args.add("--goal")
            serde_args.add(ctx.attr.goal)

        ctx.actions.run(
            inputs = [grammar] + config_inputs,
            outputs = [de_out],
            arguments = [serde_args],
            executable = ctx.executable._gen_tool,
            progress_message = "Generating Rust serde frontend for grammar %s" % grammar.short_path,
        )
        rule_srcs.append(de_out)

    # Expose outputs both as DefaultInfo (all declared files) and as two named
    # output groups so the wrapping macro can route heterogeneous outputs without
    # addressing individual declared files by label:
    #   rust_srcs — the .rs files (fed to crate assembly): cst.rs and parser.rs
    #               always, plus ast.rs / de.rs when those are enabled.
    #   stub_srcs — the .pyi stub package + optional protocol .py (fed to
    #               py_library.data); an empty depset when protocol_module is empty.
    return [
        DefaultInfo(files = depset(cst_outputs + rule_srcs)),
        OutputGroupInfo(
            rust_srcs = depset(rule_srcs),
            stub_srcs = depset(stub_outputs),
        ),
    ]

_generate_rust_srcs = rule(
    implementation = _generate_rust_srcs_impl,
    attrs = {
        "src": attr.label(
            allow_single_file = True,
            mandatory = True,
            doc = "The FLTK grammar file (.fltkg).",
        ),
        "cst_mod_path": attr.string(
            default = "super::cst",
            doc = (
                "Rust module path passed to gen-rust-parser as --cst-mod-path. " +
                "Defaults to 'super::cst', which works when cst.rs and parser.rs " +
                "are siblings under the same crate root (the fltk_pyo3_cdylib helper " +
                "assembles exactly this layout). Override when you use a different " +
                "module hierarchy."
            ),
        ),
        "protocol_module": attr.string(
            default = "",
            doc = (
                "Dotted Python import path of the protocol module (e.g. " +
                "'my.pkg.grammar_cst_protocol'). When non-empty, the gen-rust-cst " +
                "action also emits the .pyi type stub (<name>/cst.pyi) and the " +
                "stub-package marker (<name>/__init__.pyi, with --extension-name " +
                "<name> --submodules cst,parser), declaring both as outputs so " +
                "<name>/ is a complete stub package. When empty, no .pyi is produced."
            ),
        ),
        "protocol": attr.bool(
            default = False,
            doc = (
                "When True, the gen-rust-cst action also writes the protocol .py " +
                "module (<name>/cst_protocol.py), declared as an output. Requires " +
                "protocol_module to be non-empty (the rule fails at analysis time " +
                "otherwise). Off by default."
            ),
        ),
        "ast_config": attr.label(
            allow_single_file = True,
            doc = (
                "The .fltkast shaping sidecar, passed to gen-rust-ast / gen-rust-serde as " +
                "--ast-config. Required by serde = True (the frontend is shaped by it and has " +
                "no directives of its own); optional for ast = True, which without it emits a " +
                "grammar-derived AST. Setting it with neither ast nor serde is an error."
            ),
        ),
        "ast": attr.bool(
            default = False,
            doc = (
                "When True, a gen-rust-ast action also emits <name>/ast.rs — the generated " +
                "typed tree with from_cst/to_cst converters, reading the CST module as " +
                "cst_mod_path and the parser as its sibling."
            ),
        ),
        "serde": attr.bool(
            default = False,
            doc = (
                "When True, a gen-rust-serde action also emits <name>/de.rs — the serde " +
                "frontend (shape descriptions plus from_str / from_<rule>_cst entry points), " +
                "which a consumer's own #[derive(Deserialize)] types deserialize through. " +
                "Requires ast_config. With ast = True it also emits a Deserialize impl per " +
                "generated AST type."
            ),
        ),
        "goal": attr.string(
            default = "",
            doc = (
                "Rule the generated entry points target (--goal for both gen-rust-ast and " +
                "gen-rust-serde). Empty (the default) leaves each generator's own default: " +
                "the first rule carrying an AST type for ast.rs, the first rule for de.rs. " +
                "Requires ast or serde: no other action reads it."
            ),
        ),
        "extension_name": attr.string(
            default = "",
            doc = (
                "When non-empty, used as BOTH the --extension-name CLI argument and " +
                "the output subdirectory that holds the generated files. When empty, " +
                "the subdirectory falls back to the rule's own target name. The " +
                "wrapping macro sets this to the single owner module name so the " +
                "stub package directory and the extension name match the compiled " +
                "Python module (the structural stub-dir/extension-name fix)."
            ),
        ),
        "_gen_tool": attr.label(
            default = Label("//:genparser"),
            executable = True,
            allow_files = True,
            cfg = "exec",
        ),
    },
    doc = """Generate Rust CST and parser sources from an FLTK grammar file.

Always emits two action outputs:
  <name>/cst.rs    — generated CST node classes (PyO3 Rust)
  <name>/parser.rs — generated parser (PyO3 Rust)

When `protocol_module` is non-empty, the gen-rust-cst action additionally emits
and declares:
  <name>/cst.pyi       — type stub for the compiled extension
  <name>/__init__.pyi  — stub-package marker (extension <name>; submodules cst,parser)

When `protocol = True` (requires `protocol_module`), it also emits:
  <name>/cst_protocol.py — the backend-agnostic protocol module

When `ast = True` it emits <name>/ast.rs, and when `serde = True` (which requires
`ast_config`) it emits <name>/de.rs. Both ride the rust_srcs output group with
cst.rs / parser.rs, so crate assembly picks them up unchanged.

These files are designed to be consumed by fltk_pyo3_cdylib, which assembles
them alongside a consumer-authored lib.rs into a single crate directory and
compiles the result into a PyO3 cdylib.

The fixed basenames (cst.rs / parser.rs / ast.rs / de.rs) are load-bearing: a
consumer lib.rs that contains `mod cst;` and `mod parser;` (and `pub mod ast;` /
`pub mod de;`) relies on these exact names, and the generated modules name each
other as siblings of cst_mod_path.

This is an internal rule wrapped by the public generate_rust_parser macro; it is
not loaded or instantiated directly by consumers.

Example (internal instantiation by the macro):
    _generate_rust_srcs(
        name = "clockwork_rs_srcs",
        src  = "clockwork.fltkg",
        cst_mod_path = "super::cst",  # default; can omit
        # protocol_module = "clockwork.clockwork_cst_protocol",  # opt-in .pyi
        # protocol = True,                                       # opt-in protocol .py
    )
""",
)

# ---- fltk_pyo3_cdylib ---------------------------------------------------------

def fltk_pyo3_cdylib(
        name,
        rs_srcs,
        lib_rs = None,
        ast = False,
        serde = False,
        deps = [],
        crate_features = [],
        recursion_limit = _DEFAULT_RECURSION_LIMIT,
        visibility = None,
        data = [],
        **kwargs):
    """Compile generated Rust CST/parser sources + a consumer lib.rs into a PyO3 cdylib.

    The macro performs four steps:

    1. **Crate-source assembly**: copies lib.rs, cst.rs, and parser.rs into a
       single gendir so that bare `mod cst;` / `mod parser;` in lib.rs resolve.
       The generated files are Bazel action outputs (in a different directory
       from the consumer-authored lib.rs); without this assembly step, rustc
       would fail with "file not found for module `cst`".

    2. **Cdylib compilation**: compiles the assembled sources into a
       rust_shared_library (cdylib) with extension-module feature, linking
       @fltk//crates/fltk-cst-core and @fltk//crates/fltk-parser-core.

    3. **ABI3 rename**: renames the produced lib<name>.so to <name>.abi3.so.
       rules_rust emits lib<crate_name>.so; CPython's stable-ABI loader requires
       the abi3 suffix (the convention maturin produces for abi3-py310 builds).

    4. **py_library wrapper**: places <name>.abi3.so on the Python import path
       and carries @fltk//:native_py as a data dep so `import fltk._native`
       resolves inside any test sandbox that depends on this target (closing
       invariant #1: fltk._native must be importable by the consumer cdylib).

    Consumer lib.rs template:
        use fltk_cst_core::register_submodule;
        use pyo3::prelude::*;
        mod cst;    // generated cst.rs (resolved by macro crate-source assembly)
        mod parser; // generated parser.rs (same)

        #[pymodule]
        fn <name>(m: &Bound<'_, PyModule>) -> PyResult<()> {
            register_submodule(m, "cst", cst::register_classes)?;
            register_submodule(m, "parser", parser::register_classes)?;
            Ok(())
        }

    Note on recursion_limit: the macro injects `#![recursion_limit = "<N>"]` as
    the very first line of the assembled lib.rs, so consumer lib.rs files must
    NOT include their own `#![recursion_limit]` — the macro owns that line.

    Args:
        name: Module name. Must match the `#[pymodule]` fn name in lib_rs and
              the importable module name (e.g. "clockwork_native"). This becomes
              the crate name and the .so stem. Invariant: the `#[pymodule]` fn
              in lib_rs must have exactly this name.
        rs_srcs: Label providing cst.rs and parser.rs as outputs. Typically the
                 label of a generate_rust_parser(...) target in its default
                 (pure-Rust) mode, whose rust_srcs are exactly cst.rs / parser.rs
                 (this is the Clockwork consumption pattern). generate_rust_parser
                 with python_extension = True feeds its own codegen target here
                 internally.
                 CALLER INVARIANT: the assembly step copies every file from
                 rs_srcs into the crate gendir by basename AFTER writing lib.rs.
                 If rs_srcs emitted a file whose basename is "lib.rs" it would
                 silently overwrite the assembled crate root (losing the injected
                 recursion_limit and the lib_rs content).  generate_rust_parser
                 only ever emits cst.rs / parser.rs (plus ast.rs / de.rs when
                 asked), upholding this invariant; direct callers feeding a
                 hand-rolled rs_srcs must do the same.
        lib_rs: Label or file of the consumer-authored lib.rs that declares
                `mod cst;`, `mod parser;`, and the `#[pymodule]` entry point.
                When omitted (default None), the macro generates lib.rs from
                the target `name` using gen-rust-lib.  Pass an explicit label
                to retain a hand-authored lib.rs (backward-compatible override).
        ast: True when rs_srcs also carries ast.rs. Links fltk-ast-core, requires
             ast.rs in the assembled crate, and (when lib_rs is generated) adds
             `pub mod ast;` to it. A hand-authored lib_rs must declare it itself.
        serde: True when rs_srcs also carries de.rs. Links fltk-serde-core and
               serde, requires de.rs in the assembled crate, and (when lib_rs is
               generated) adds `pub mod de;` to it.
        deps: Extra rust_library deps to link into the cdylib (for consumer
              native Rust code that coexists with the generated modules).
        crate_features: Extra crate features beyond the mandatory
                        ["extension-module"] the macro always adds.
        recursion_limit: Integer recursion limit injected as
                         `#![recursion_limit = "<N>"]` at the top of the
                         assembled crate root.  Default 512, which is sufficient
                         for grammars with deep recursive type references
                         (e.g. Clockwork's DFL expression chain).  Increase for
                         grammars with deeper recursion.  The symptom of too low
                         a limit is E0275 "overflow evaluating `Shared<X>: Send".
        visibility: Visibility for the resulting py_library target (name). The
                    intermediate targets are package-private.
        data: Extra data targets appended to the py_library's data (alongside the
              cdylib .abi3.so). The wrapping macro feeds the codegen rule's
              stub_srcs output group here so the PEP 561 stub package rides along
              on the public py_library. Empty by default.
        **kwargs: Forwarded to rust_shared_library (e.g. rustc_flags).
    """

    # When lib_rs is omitted, generate lib.rs from the target name using the
    # generate_rust_lib rule (a proper ctx.actions.run invocation, not a genrule
    # shell command).  This avoids both the cross-repo $(location) fragility and
    # any shell-quoting surface for module_name.
    plain_modules = _plain_modules_for(ast, serde)
    if lib_rs == None:
        generate_rust_lib(
            name = name + "_gen_lib",
            module_name = name,
            plain_modules = plain_modules,
        )
        lib_rs = ":" + name + "_gen_lib"

    # Step 1: Crate-source assembly.
    #
    # We need lib.rs, cst.rs, and parser.rs in the same directory so that
    # bare `mod cst;` / `mod parser;` in lib.rs find their siblings.
    #
    # lib.rs is a consumer source file (or a generated label); cst.rs and
    # parser.rs are outputs of _generate_rust_srcs (in <rs_srcs_name>/cst.rs,
    # <rs_srcs_name>/parser.rs relative to the package gendir).
    #
    # Strategy: a single genrule that receives all three inputs and copies them
    # into a flat gendir.  We use `basename` in the shell command to strip the
    # <rs_srcs_name>/ prefix from the generated files.
    crate_lib_rs = name + "_crate_root/lib.rs"

    # The generated modules each need a declared genrule output: an undeclared file copied
    # into the gendir is not staged into the compile action's sandbox, so `pub mod ast;`
    # would fail to resolve there while succeeding in a non-sandboxed build.
    crate_srcs = [name + "_crate_root/cst.rs", name + "_crate_root/parser.rs"]
    if ast:
        crate_srcs.append(name + "_crate_root/ast.rs")
    if serde:
        crate_srcs.append(name + "_crate_root/de.rs")

    # Note: the assembly genrule requires every file it declares to be in rs_srcs — cst.rs and
    # parser.rs always, ast.rs / de.rs when the corresponding flag is set.  Every current
    # caller is a grammar crate and always provides both files.  If a runtime-only (span-only)
    # crate is ever built via this macro, the test -f guards will fail misleadingly; at that
    # point, split into grammar and span-only assembly variants.
    guards = "\n".join([
        '            test -f $$OUTDIR/{basename} || {{ echo "ERROR: {basename} not produced by rs_srcs (expected basename {basename} in outputs)"; exit 1; }}'.format(
            basename = crate_src.split("/")[-1],
        )
        for crate_src in crate_srcs
    ])

    native.genrule(
        name = name + "_assemble_crate",
        srcs = [lib_rs, rs_srcs],
        outs = [crate_lib_rs] + crate_srcs,
        cmd = """
            OUTDIR=$$(dirname $(location {crate_lib_rs}))
            printf '#![recursion_limit = "{recursion_limit}"]\\n' > $$OUTDIR/lib.rs
            cat $(location {lib_rs}) >> $$OUTDIR/lib.rs
            for f in $(locations {rs_srcs}); do
                cp $$f $$OUTDIR/$$(basename $$f)
            done
{guards}
        """.format(
            crate_lib_rs = crate_lib_rs,
            lib_rs = lib_rs,
            rs_srcs = rs_srcs,
            recursion_limit = recursion_limit,
            guards = guards,
        ),
    )

    # Step 2: Compile the cdylib.
    #
    # ast.rs requires fltk-ast-core; de.rs requires fltk-serde-core and serde.
    generated_deps = []
    if ast:
        generated_deps.append(Label("//crates/fltk-ast-core"))
    if serde:
        generated_deps.append(Label("//crates/fltk-serde-core"))
        generated_deps.append(Label("@fltk_crates//:serde"))

    rust_shared_library(
        name = name + "_cdylib",
        srcs = [
            ":" + name + "_assemble_crate",
        ],
        crate_name = name,
        crate_root = ":" + crate_lib_rs,
        edition = "2021",
        # "extension-module" enables the pyo3 extension-module feature (no libpython link).
        # "python" must be set explicitly: Cargo would forward it via the feature definition
        # `extension-module = ["python", "pyo3/extension-module"]`, but Bazel crate_features
        # do not forward — each feature is set independently.  Without "python", the generated
        # register_classes symbols (gated on #[cfg(feature = "python")]) are compiled out and
        # the crate root's unconditional register_submodule calls fail to link.
        crate_features = ["extension-module", "python"] + crate_features,
        deps = [
            # Use Label() so these cross-repo labels are resolved relative to the FLTK module
            # (where this macro is defined), not the calling package.  In Bzlmod, string labels
            # passed to rule attrs in a macro are resolved at rule-instantiation time in the
            # caller's repository context, so bare "//crates/..." would resolve to
            # @clockwork//crates/... when called from Clockwork — which does not exist.
            Label("//crates/fltk-cst-core"),
            Label("//crates/fltk-parser-core"),
            Label("@fltk_crates//:pyo3"),
        ] + generated_deps + deps,
        **kwargs
    )

    # Step 3: ABI3 rename: lib<name>.so -> <name>.abi3.so.
    # rules_rust produces lib<crate_name>.so; CPython expects the abi3 suffix.
    # Use $(location ...) rather than $< to avoid positional ambiguity if rules_rust
    # ever emits additional files alongside the .so (e.g. debug info).
    abi3_so = name + ".abi3.so"
    native.genrule(
        name = name + "_so",
        srcs = [":" + name + "_cdylib"],
        outs = [abi3_so],
        cmd = "cp $(location :{cdylib}) $@".format(cdylib = name + "_cdylib"),
    )

    # Step 4: py_library wrapper.
    # - data: the consumer cdylib .abi3.so, placed on the Python path so
    #   `import <name>` resolves.
    # - deps: @fltk//:native_py, which transitively brings fltk/_native.abi3.so
    #   onto the path so `import fltk._native` resolves (invariant #1: the
    #   generated cst.rs resolves the canonical Span type via fltk._native at
    #   runtime; without native_py in the sandbox the pure-Python fallback fires).
    py_library(
        name = name,
        data = [":" + name + "_so"] + data,
        deps = [Label("@fltk//:native_py")],
        imports = ["."],
        visibility = visibility,
    )

# ---- generate_rust_parser (public macro) ----------------------------------------

def generate_rust_parser(
        name,
        src,
        cst_mod_path = "super::cst",
        python_extension = False,
        ast_config = None,
        ast = False,
        serde = False,
        goal = "",
        protocol_module = "",
        protocol = False,
        lib_rs = None,
        deps = [],
        crate_features = [],
        recursion_limit = _DEFAULT_RECURSION_LIMIT,
        visibility = None,
        **kwargs):
    """Generate a Rust-backed parser from an FLTK grammar file.

    This is the single public entry point consumers call. It has two modes,
    selected by `python_extension`:

    **python_extension = False (default — pure Rust).**
    Instantiates only the internal codegen rule as the public `:name` target,
    emitting `<name>/cst.rs` and `<name>/parser.rs`. No cdylib, no .pyi, no
    protocol module. The consumer drops the .rs files into their own crate.
    The Python-extension-only knobs (`protocol_module`, `protocol`, `lib_rs`,
    `deps`, `crate_features`, a non-default `recursion_limit`) must be left at
    their defaults; setting any of them is a misconfiguration and fails fast.
    `ast` / `serde` / `ast_config` / `goal` are valid in BOTH modes: the extra
    generated modules are ordinary Rust sources either way.

    **python_extension = True (full Python extension).**
    Instantiates the internal codegen rule as `<name>_srcs` with
    `extension_name = name` (the single owner module name — this is the
    structural fix for the stub-dir / --extension-name naming bug), then folds in
    the four cdylib-build steps (crate assembly → rust_shared_library → abi3
    rename → py_library) with the public `py_library` named `name`. Crate
    assembly consumes ONLY the codegen rule's `rust_srcs` output group (the .rs
    files), so the .pyi / .py outputs never enter the flat crate root. The
    `stub_srcs` output group (the .pyi stub package, plus `cst_protocol.py` when
    `protocol = True`) is added to the public py_library as `data`; it is an empty
    depset exactly when `protocol_module` is empty, so this routing self-gates.

    Args:
        name: The public target name. In python_extension = True mode this is the
              compiled Python module name (the crate name, the #[pymodule] fn
              name, --extension-name, and the stub-package directory all derive
              from it).
        src: The FLTK grammar file (.fltkg).
        cst_mod_path: Rust module path passed to gen-rust-parser as
                      --cst-mod-path. Defaults to "super::cst".
        python_extension: When True, build the Python extension (cdylib + stubs +
                          py_library). When False (default), emit only .rs files.
        ast_config: The .fltkast shaping sidecar. Required by serde = True,
                    optional for ast = True, an error with neither.
        ast: When True, also emit <name>/ast.rs (the generated typed tree). In
             python_extension mode the cdylib links fltk-ast-core and the
             generated lib.rs declares `pub mod ast;`.
        serde: When True, also emit <name>/de.rs (the serde frontend); requires
               ast_config. In python_extension mode the cdylib links
               fltk-serde-core and serde, and the generated lib.rs declares
               `pub mod de;`. With ast = True, de.rs also carries a Deserialize
               impl per generated AST type.
        goal: Rule the ast.rs / de.rs entry points target (--goal). Empty (the
              default) leaves each generator's own default. Requires ast = True
              or serde = True; nothing else reads it.
        protocol_module: Dotted Python import path of the protocol module; when
                         non-empty (python_extension = True only) triggers .pyi
                         stub-package emission.
        protocol: When True (requires protocol_module), also emit the protocol
                  .py module. python_extension = True only.
        lib_rs: Optional consumer-authored lib.rs label; when omitted the macro
                generates one. python_extension = True only.
        deps: Extra rust_library deps linked into the cdylib. python_extension =
              True only.
        crate_features: Extra crate features. python_extension = True only.
        recursion_limit: recursion_limit injected into the assembled crate root.
                         python_extension = True only.
        visibility: Visibility for the public target.
        **kwargs: In python_extension = True mode, forwarded to rust_shared_library
                  (e.g. rustc_flags). In pure-Rust mode, forwarded to the internal
                  _generate_rust_srcs rule; an unrecognized attribute there (e.g. a
                  rust_shared_library passthrough set by mistake) surfaces a generic
                  Bazel "no such attribute" error naming that internal rule rather
                  than the curated python_extension guidance the named knobs give.
    """
    _require_protocol_module(protocol, protocol_module)
    _require_codegen_mode(ast, serde, ast_config != None, goal)

    if not python_extension:
        # Pure-Rust mode: the Python-extension-only knobs must be at defaults.
        # Fail fast rather than silently ignore a value that has no effect here.
        msg = _pure_rust_mode_violation(
            protocol_module = protocol_module,
            protocol = protocol,
            lib_rs = lib_rs,
            deps = deps,
            crate_features = crate_features,
            recursion_limit = recursion_limit,
        )
        if msg != None:
            fail(msg)

        # The internal codegen rule IS the public target; extension_name stays
        # empty (no stub emission, subdir irrelevant to type resolution).
        _generate_rust_srcs(
            name = name,
            src = src,
            cst_mod_path = cst_mod_path,
            ast_config = ast_config,
            ast = ast,
            serde = serde,
            goal = goal,
            visibility = visibility,
            **kwargs
        )
        return

    # Python-extension mode.
    #
    # The codegen rule is <name>_srcs with extension_name = name, so its outputs
    # land under <name>/ and the stub package (when protocol_module is set) is
    # named after the compiled module. The public py_library is <name>.
    _generate_rust_srcs(
        name = name + "_srcs",
        src = src,
        cst_mod_path = cst_mod_path,
        ast_config = ast_config,
        ast = ast,
        serde = serde,
        goal = goal,
        extension_name = name,
        protocol_module = protocol_module,
        protocol = protocol,
    )

    # A macro cannot address an individual declare_file output by label, so route
    # the codegen rule's output groups through filegroups: crate assembly draws
    # only rust_srcs (the .rs files), and the py_library carries stub_srcs (the
    # .pyi stub package + optional cst_protocol.py). stub_srcs is an empty depset
    # when protocol_module is empty, so its filegroup contributes nothing.
    native.filegroup(
        name = name + "_rust_srcs",
        srcs = [":" + name + "_srcs"],
        output_group = "rust_srcs",
    )
    native.filegroup(
        name = name + "_stub_srcs",
        srcs = [":" + name + "_srcs"],
        output_group = "stub_srcs",
    )

    fltk_pyo3_cdylib(
        name = name,
        rs_srcs = ":" + name + "_rust_srcs",
        lib_rs = lib_rs,
        ast = ast,
        serde = serde,
        deps = deps,
        crate_features = crate_features,
        recursion_limit = recursion_limit,
        visibility = visibility,
        data = [":" + name + "_stub_srcs"],
        **kwargs
    )

# Not public API. Exported solely for //tests/bazel_rules. Downstream consumers
# must not load this symbol; it may change without notice.
rust_bzl_internals = struct(
    pure_rust_mode_violation = _pure_rust_mode_violation,
    protocol_module_violation = _protocol_module_violation,
    codegen_mode_violation = _codegen_mode_violation,
    plain_modules_for = _plain_modules_for,
    sibling_mod_path = _sibling_mod_path,
    generate_rust_srcs = _generate_rust_srcs,
    default_recursion_limit = _DEFAULT_RECURSION_LIMIT,
)
