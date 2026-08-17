"""FLTK Rust Bazel rules.

This file provides:
  - generate_rust_parser: the public macro consumers call. In its default
    (pure-Rust) mode it runs FLTK's Rust codegen on a grammar file and emits
    cst.rs + parser.rs as Bazel action outputs — plus ast.rs (ast = True),
    de.rs (serde = True, which also needs the .fltkast sidecar as ast_config),
    and unparser.rs (unparser = True, optionally baked with a .fltkfmt spec
    passed as format_config).
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
load("//bzl:pyo3_ext.bzl", "pyo3_extension_py_library")

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

def _codegen_mode_violation(ast, serde, has_ast_config, goal = "", unparser = False, has_format_config = False):
    """Return the ast/serde/ast_config/goal/format_config misconfiguration message, or None.

    Four conditions:
      - `serde = True` requires ast_config.
      - An `ast_config` with neither `ast` nor `serde` has no consumer and would be
        silently ignored.
      - A `goal` with neither `ast` nor `serde` is the same: only the gen-rust-ast and
        gen-rust-serde outputs read --goal; the cst and parser outputs never do.
      - A `format_config` without `unparser`: only the generated unparser reads
        --format-config.

    `ast = True` without a sidecar is NOT a violation — a grammar-derived (Tier 0) AST is a
    supported mode. Neither is `unparser = True` without a format_config: that is the
    default-FormatterConfig mode.

    Call this with keyword arguments only. The parameter list is five booleans around one
    string, so a transposed pair reads as a plausible guard and the message-pinning tests
    would carry the same transposition rather than catch it.
    """
    if serde and not has_ast_config:
        return "generate_rust_parser: serde = True requires ast_config (the .fltkast sidecar shaping the tree)."
    if has_ast_config and not (ast or serde):
        return "generate_rust_parser: ast_config requires ast = True or serde = True; nothing else reads it."
    if goal and not (ast or serde):
        return "generate_rust_parser: goal requires ast = True or serde = True; nothing else reads it."
    if has_format_config and not unparser:
        return "generate_rust_parser: format_config requires unparser = True; nothing else reads it."
    return None

def _require_codegen_mode(ast, serde, has_ast_config, goal = "", unparser = False, has_format_config = False):
    """Fire the ast/serde/ast_config/goal/format_config guard (fail on violation)."""
    msg = _codegen_mode_violation(
        ast = ast,
        serde = serde,
        has_ast_config = has_ast_config,
        goal = goal,
        unparser = unparser,
        has_format_config = has_format_config,
    )
    if msg != None:
        fail(msg)

def _parser_violation(parser, ast, serde, extension = False):
    """Return the `parser = False` misconfiguration message, or None.

    The parser is the one generated module other artifacts name: ast.rs and de.rs are generated
    against `--parser-mod-path`, and an assembled PyO3 crate root declares `mod parser;` and
    registers it as a submodule. Turning it off under either is a crate that does not compile,
    reported by rustc against generated code, so it is refused here instead.

    `extension` is the python_extension flag in the macro and, in the rule, the attrs that
    stand in for it.
    """
    if parser:
        return None
    if ast or serde:
        return "generate_rust_parser: parser = False cannot be combined with ast or serde; both generate against the parser module."
    if extension:
        return "generate_rust_parser: parser = False is pure-Rust mode only; an assembled PyO3 crate root always declares mod parser."
    return None

def _require_parser(parser, ast, serde, extension = False):
    """Fire the `parser = False` guard (fail on violation)."""
    msg = _parser_violation(parser, ast, serde, extension = extension)
    if msg != None:
        fail(msg)

def _submodules_violation(submodules, protocol_module, python_extension = False):
    """Return the `submodules` misconfiguration message, or None.

    The list is written into the stub-package __init__.pyi marker and nothing else, and that
    marker only exists when protocol_module does. Accepting it without one would silently
    discard a caller's description of their extension.

    It is also pure-Rust-mode only, for the same reason extension_name is. The list widens the
    marker beyond this target's own outputs, which is what a hand-assembled crate root fed by
    several codegen targets needs; in python_extension mode the cdylib is assembled from this
    target's rust_srcs alone, so every name beyond the derived list would promise a submodule
    with no .pyi behind it.
    """
    if submodules and python_extension:
        return "generate_rust_parser: submodules is pure-Rust mode only; with python_extension = True the marker is derived from this target's own outputs."
    if submodules and not protocol_module:
        return "generate_rust_parser: submodules requires protocol_module; it describes the stub package, which is emitted only with one."
    return None

def _require_submodules(submodules, protocol_module, python_extension = False):
    """Fire the `submodules` guard (fail on violation)."""
    msg = _submodules_violation(submodules, protocol_module, python_extension = python_extension)
    if msg != None:
        fail(msg)

def _out_dir_violation(out_dir, python_extension = False):
    """Return the out_dir misconfiguration message, or None.

    Three conditions:
      - out_dir in python_extension mode: the crate-assembly genrule already owns the
        layout there, so the value would be silently ignored.
      - An absolute out_dir: declare_file only names files inside the package.
      - An out_dir with a `..` segment: same reason, stated as the escape it is.

    An empty out_dir is the default (generated files land under the rule's own
    <name>/ subdirectory) and never violates.
    """
    if not out_dir:
        return None
    if python_extension:
        return "generate_rust_parser: out_dir is only valid with python_extension = False; in extension mode the assembled crate owns the layout."
    if out_dir.startswith("/"):
        return "generate_rust_parser: out_dir must be a package-relative directory; '{}' is absolute.".format(out_dir)
    if ".." in out_dir.split("/"):
        return "generate_rust_parser: out_dir must stay inside the package; '{}' escapes it via '..'.".format(out_dir)
    return None

def _require_out_dir(out_dir, python_extension = False):
    """Fire the out_dir guard (fail on violation)."""
    msg = _out_dir_violation(out_dir, python_extension = python_extension)
    if msg != None:
        fail(msg)

def _stub_package_violation(protocol_module, extension_name, python_extension):
    """Return the stub-package naming misconfiguration message, or None.

    The stub package's directory name is the compiled module's import name, so in pure-Rust
    mode — where the crate is assembled by hand and the rule has no module name to derive it
    from — asking for stubs means naming them. In python_extension mode the macro derives both
    from `name`, so a caller-supplied extension_name there is a value that would be ignored.
    """
    if python_extension:
        if extension_name:
            return "generate_rust_parser: extension_name is derived from name with python_extension = True; drop it."
        return None
    if extension_name and not protocol_module:
        return "generate_rust_parser: extension_name names the stub package, which is emitted only with protocol_module."
    if protocol_module and not extension_name:
        return "generate_rust_parser: protocol_module in pure-Rust mode requires extension_name; it is the stub package's directory, i.e. the hand-assembled module's import name."
    return None

def _require_stub_package(protocol_module, extension_name, python_extension):
    """Fire the stub-package naming guard (fail on violation)."""
    msg = _stub_package_violation(protocol_module, extension_name, python_extension)
    if msg != None:
        fail(msg)

def _generated_path(out_subdir, basename):
    """The package-relative path a generated file is declared at.

    Empty and "." both mean the package root, where a bare basename is the declared path;
    a trailing slash on a real directory is absorbed rather than doubled.
    """
    subdir = out_subdir.rstrip("/")
    if subdir == "" or subdir == ".":
        return basename
    return subdir + "/" + basename

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
        lib_rs,
        deps,
        crate_features,
        recursion_limit):
    """Return the pure-Rust-mode misconfiguration message, or None.

    In pure-Rust mode (python_extension = False) the knobs that only the cdylib
    build reads must be left at their defaults; setting any of them has no effect
    and is a misconfiguration. The stub knobs (protocol_module, protocol,
    extension_name, submodules) are NOT among them: a hand-assembled extension
    generates its .rs in this mode and needs its stub package from the same
    action. Each entry pairs the attribute name with "was it set away
    from its default?"; normalizing on that boolean lets one loop + one message
    template cover every knob (truthy defaults and sentinel defaults alike),
    so a new python-extension-only knob just adds one tuple. recursion_limit is
    compared against _DEFAULT_RECURSION_LIMIT here, preserving that constant as
    the single owner of the default. Returns the message for the first offending
    knob, or None; the macro wraps it in `if msg != None: fail(msg)`.
    """
    python_only_knobs = [
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
    if ctx.attr.unparser:
        args.add("--unparser")
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
        "unparser": attr.bool(
            default = False,
            doc = (
                "Pass --unparser to gen-rust-lib: the generated crate root gains `mod unparser;` " +
                "and registers it as a Python submodule. The unparser is registered rather than " +
                "plain because unparser.rs exports a feature-gated register_classes."
            ),
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

    Runs one genparser action:
      gen-rust-all <grammar> --cst-output <path> --parser-output <path> [...]

    Every enabled artifact is named by its own option on that one command line, so the
    grammar is read and parsed once per target rather than once per artifact.  The generated
    files use fixed basenames ("cst.rs", "parser.rs", "unparser.rs", "ast.rs", "de.rs") so
    that bare `mod cst;` / `mod parser;` declarations in a co-located lib.rs resolve
    correctly.
    """
    grammar = ctx.file.src

    protocol_module = ctx.attr.protocol_module
    protocol = ctx.attr.protocol
    ast_config = ctx.file.ast_config
    format_config = ctx.file.format_config
    unparser = ctx.attr.unparser

    # Mirror the CLI's `--protocol-output requires --protocol-module` check,
    # surfacing the misconfiguration at analysis time.
    _require_protocol_module(protocol, protocol_module)

    # Defense-in-depth: the public macro checks at loading time; this guard catches
    # direct instantiation of the internal rule.
    _require_codegen_mode(
        ast = ctx.attr.ast,
        serde = ctx.attr.serde,
        has_ast_config = ast_config != None,
        goal = ctx.attr.goal,
        unparser = unparser,
        has_format_config = format_config != None,
    )

    # The out_dir path shape decides where declare_file lands, so it is enforced here as
    # well as in the macro. out_dir and the stub attrs coexist: the .rs files go under
    # out_dir and the stub package under the extension-name directory, which is what a
    # hand-assembled extension whose crate sources live in src/ needs.
    _require_out_dir(ctx.attr.out_dir)
    _require_submodules(ctx.attr.submodules, protocol_module)

    # Only the ast/serde arm of the parser guard is checkable here. The `assembled PyO3 crate
    # root` arm needs python_extension, which is a macro concept the rule never sees.
    # The macro fires that arm with the real value.
    parser = ctx.attr.parser
    _require_parser(parser, ctx.attr.ast, ctx.attr.serde)

    # The output subdirectory and the --extension-name CLI flag are both driven
    # by extension_name when it is set, and fall back to the rule's own target
    # name when it is empty.  This decouples the stub-package directory /
    # extension name from the rule's target name: the wrapping macro sets
    # extension_name to the single owner module name so the stub package is
    # named after the compiled module.
    #
    # stub_subdir owns the .pyi path, out_subdir owns the .rs path; when both
    # extension_name and out_dir are set they diverge intentionally.
    stub_subdir = ctx.attr.extension_name or ctx.attr.name
    out_subdir = ctx.attr.out_dir or stub_subdir

    cst_out = ctx.actions.declare_file(_generated_path(out_subdir, "cst.rs"))

    # cst_out is always produced; the .pyi / marker / protocol outputs are appended below
    # when protocol_module (and optionally protocol) are set.
    cst_outputs = [cst_out]

    # stub_outputs collects the files that ride along on the compiled Python
    # module (the .pyi stub package and, when protocol = True, the protocol .py).
    # It stays empty when protocol_module is empty; it feeds the stub_srcs output
    # group returned below.
    stub_outputs = []

    # One gen-rust-all process emits every artifact this rule declares.
    args = ctx.actions.args()
    args.add("gen-rust-all")
    args.add(grammar)
    args.add("--cst-output")
    args.add(cst_out)
    args.add("--cst-mod-path")
    args.add(ctx.attr.cst_mod_path)

    rule_srcs = [cst_out]
    submodules = ["cst"]
    if parser:
        parser_out = ctx.actions.declare_file(_generated_path(out_subdir, "parser.rs"))
        args.add("--parser-output")
        args.add(parser_out)
        rule_srcs.append(parser_out)
        submodules.append("parser")

    if protocol_module:
        # The .pyi stub plus the stub-package __init__.pyi marker make <name>/ a complete stub
        # package in the Bazel output tree.  The marker is generator-produced via
        # --init-pyi-output (not a ctx.actions.write fixed body), keeping it on the
        # same dogfooded path as the in-tree markers.
        cst_pyi = ctx.actions.declare_file(stub_subdir + "/cst.pyi")
        init_pyi = ctx.actions.declare_file(stub_subdir + "/__init__.pyi")
        args.add("--protocol-module")
        args.add(protocol_module)
        args.add("--cst-pyi-output")
        args.add(cst_pyi)
        args.add("--init-pyi-output")
        args.add(init_pyi)
        args.add("--extension-name")
        args.add(stub_subdir)
        args.add("--submodules")

        # The marker's submodule list must match what the crate root actually registers,
        # or a downstream `from <ext> import unparser` type-checks against nothing.  A
        # hand-assembled crate root can register modules this grammar does not generate
        # (a second grammar's CST, a second unparser flavor), so the list is overridable.
        args.add(",".join(ctx.attr.submodules or (submodules + (["unparser"] if unparser else []))))
        cst_outputs.append(cst_pyi)
        cst_outputs.append(init_pyi)
        stub_outputs.append(cst_pyi)
        stub_outputs.append(init_pyi)

        if protocol:
            # Opt-in protocol .py output.
            protocol_out = ctx.actions.declare_file(stub_subdir + "/cst_protocol.py")
            args.add("--protocol-output")
            args.add(protocol_out)
            cst_outputs.append(protocol_out)
            stub_outputs.append(protocol_out)

    action_inputs = [grammar]
    if ast_config != None:
        action_inputs.append(ast_config)

    # The .fltkfmt spec is baked into the generated methods at generation time, so it is an
    # ordinary action input: editing it re-runs codegen like any other source change.
    if unparser:
        unparser_out = ctx.actions.declare_file(_generated_path(out_subdir, "unparser.rs"))
        args.add("--unparser-output")
        args.add(unparser_out)
        rule_srcs.append(unparser_out)

        if format_config != None:
            args.add("--format-config")
            args.add(format_config)
            action_inputs.append(format_config)

        if protocol_module:
            # The unparser half of the stub package the marker above declares.
            unparser_pyi = ctx.actions.declare_file(stub_subdir + "/unparser.pyi")
            args.add("--unparser-pyi-output")
            args.add(unparser_pyi)
            stub_outputs.append(unparser_pyi)

    if ctx.attr.ast:
        ast_out = ctx.actions.declare_file(_generated_path(out_subdir, "ast.rs"))
        args.add("--ast-output")
        args.add(ast_out)
        rule_srcs.append(ast_out)
        if unparser:
            # The ast module's unparse_str entry point requires a sibling unparser module;
            # without this flag the generated code has no referent for the import.
            args.add("--unparser-mod-path")
            args.add(_sibling_mod_path(ctx.attr.cst_mod_path, "unparser"))

    if ctx.attr.serde:
        de_out = ctx.actions.declare_file(_generated_path(out_subdir, "de.rs"))
        args.add("--serde-output")
        args.add(de_out)
        rule_srcs.append(de_out)
        if ctx.attr.ast:
            # ast = True means an ast module exists for serde to target with
            # Deserialize impls; without it, --ast-mod-path has no referent.
            args.add("--ast-mod-path")
            args.add(_sibling_mod_path(ctx.attr.cst_mod_path, "ast"))

    # --parser-mod-path, --ast-config and --goal shape ast.rs and de.rs only; they must not
    # be passed when neither output was requested.
    if ctx.attr.ast or ctx.attr.serde:
        args.add("--parser-mod-path")
        args.add(_sibling_mod_path(ctx.attr.cst_mod_path, "parser"))
        if ast_config != None:
            args.add("--ast-config")
            args.add(ast_config)
        if ctx.attr.goal:
            args.add("--goal")
            args.add(ctx.attr.goal)

    # The three lists overlap; depset dedupes so the action declares each file once.
    all_outputs = depset(cst_outputs + rule_srcs + stub_outputs)

    ctx.actions.run(
        inputs = action_inputs,
        outputs = all_outputs.to_list(),
        arguments = [args],
        executable = ctx.executable._gen_tool,
        progress_message = "Generating Rust sources for grammar %s" % grammar.short_path,
    )

    # Expose outputs both as DefaultInfo (all declared files) and as two named
    # output groups so the wrapping macro can route heterogeneous outputs without
    # addressing individual declared files by label:
    #   rust_srcs — the .rs files (fed to crate assembly): cst.rs and parser.rs
    #               always, plus unparser.rs / ast.rs / de.rs when those are enabled.
    #   stub_srcs — the .pyi stub package + optional protocol .py (fed to
    #               py_library.data); an empty depset when protocol_module is empty.
    return [
        DefaultInfo(files = all_outputs),
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
                "When True, the codegen action also writes the protocol .py " +
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
        "parser": attr.bool(
            default = True,
            doc = (
                "When True (the default), the codegen action emits <name>/parser.rs. Set it " +
                "False for a CST-only or unparser-only crate: the parser is by far the " +
                "largest generated artifact, and generating one nothing compiles costs a " +
                "grammar's worth of work on every clean build. Pure-Rust mode only, and " +
                "incompatible with ast / serde, which generate against the parser module."
            ),
        ),
        "ast": attr.bool(
            default = False,
            doc = (
                "When True, the codegen action also emits <name>/ast.rs — the generated " +
                "typed tree with from_cst/to_cst converters, reading the CST module as " +
                "cst_mod_path and the parser as its sibling."
            ),
        ),
        "serde": attr.bool(
            default = False,
            doc = (
                "When True, the codegen action also emits <name>/de.rs — the serde " +
                "frontend (shape descriptions plus from_str / from_<rule>_cst entry points), " +
                "which a consumer's own #[derive(Deserialize)] types deserialize through. " +
                "Requires ast_config. With ast = True it also emits a Deserialize impl per " +
                "generated AST type."
            ),
        ),
        "unparser": attr.bool(
            default = False,
            doc = (
                "When True, the codegen action also emits <name>/unparser.rs — the " +
                "generated unparser over the CST module named by cst_mod_path, linking the " +
                "fltk-unparser-core runtime. With ast = True the AST module additionally gains " +
                "its unparse_str entry point. Valid in both modes."
            ),
        ),
        "format_config": attr.label(
            allow_single_file = True,
            doc = (
                "A .fltkfmt formatter-config file, passed to gen-rust-unparser as " +
                "--format-config. Its spacing/anchor/disposition decisions are baked into the " +
                "generated unparser at generation time, so editing it is an ordinary input " +
                "change. Omitting it selects the default FormatterConfig. Requires unparser = " +
                "True: no other action reads it."
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
        "out_dir": attr.string(
            default = "",
            doc = (
                "Package-relative directory the generated .rs files are declared in. Empty " +
                "(the default) puts them under <name>/, matching the historical layout. Set " +
                "it to the directory holding the consumer's own crate sources (e.g. \"src\") " +
                "so a rust_library can take srcs = glob([\"src/**/*.rs\"]) + [\":gen\"] with " +
                "crate_root = \"src/lib.rs\" and no copying step. Must be package-relative " +
                "and must not contain a '..' segment. Pure-Rust mode only: the crate " +
                "assembly genrule owns the layout in python_extension mode."
            ),
        ),
        "submodules": attr.string_list(
            doc = (
                "The compiled extension's submodule names, written into the stub-package " +
                "__init__.pyi marker. Empty (the default) derives the list from what this " +
                "target generates (cst, parser, unparser). Set it when the crate root " +
                "registers modules that come from elsewhere, so the marker describes the " +
                "extension rather than this one codegen action. Requires protocol_module."
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

Always emits:
  <name>/cst.rs    — generated CST node classes (PyO3 Rust)

and, unless `parser = False`:
  <name>/parser.rs — generated parser (PyO3 Rust)

With `out_dir` set, the .rs files are declared under that package-relative
directory instead (<out_dir>/cst.rs, ...). The .pyi stub package always stays
under the extension-name subdirectory, so the two can be combined: a
hand-assembled extension generates into its own src/ and gets its stub package
beside it.

When `protocol_module` is non-empty, the codegen action additionally emits
and declares:
  <name>/cst.pyi       — type stub for the compiled extension
  <name>/__init__.pyi  — stub-package marker (extension <name>; submodules cst,parser)

When `protocol = True` (requires `protocol_module`), it also emits:
  <name>/cst_protocol.py — the backend-agnostic protocol module

When `ast = True` it emits <name>/ast.rs, when `serde = True` (which requires
`ast_config`) it emits <name>/de.rs, and when `unparser = True` it emits
<name>/unparser.rs (optionally baked with a `format_config` .fltkfmt spec). All
three ride the rust_srcs output group with cst.rs / parser.rs, so crate assembly
picks them up unchanged. With `protocol_module`, the unparser action also emits
<name>/unparser.pyi into the stub package.

These files are designed to be consumed by fltk_pyo3_cdylib, which assembles
them alongside a consumer-authored lib.rs into a single crate directory and
compiles the result into a PyO3 cdylib.

The fixed basenames (cst.rs / parser.rs / unparser.rs / ast.rs / de.rs) are
load-bearing: a consumer lib.rs that contains `mod cst;`, `mod parser;` and
`mod unparser;` (and `pub mod ast;` / `pub mod de;`) relies on these exact names,
and the generated modules name each other as siblings of cst_mod_path.

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
        unparser = False,
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
        unparser: True when rs_srcs also carries unparser.rs. Links
                  fltk-unparser-core, requires unparser.rs in the assembled crate,
                  and (when lib_rs is generated) declares and registers
                  `mod unparser;` as a Python submodule. A hand-authored lib_rs
                  must declare and register it itself.
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
            unparser = unparser,
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
    if unparser:
        crate_srcs.append(name + "_crate_root/unparser.rs")
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
    # ast.rs requires fltk-ast-core; de.rs requires fltk-serde-core and serde;
    # unparser.rs requires fltk-unparser-core.
    #
    # The serde edge is the //crates/fltk-serde-core:serde flag, not the hub label directly:
    # a generated de.rs names `::serde` and hands values to fltk-serde-core's traits, so the
    # two must be one instance. Reading the flag here keeps that true when a consumer points
    # it at their own hub.
    generated_deps = []
    if unparser:
        generated_deps.append(Label("//crates/fltk-unparser-core"))
    if ast:
        generated_deps.append(Label("//crates/fltk-ast-core"))
    if serde:
        generated_deps.append(Label("//crates/fltk-serde-core"))
        generated_deps.append(Label("//crates/fltk-serde-core:serde"))

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

    # Steps 3 and 4: abi3 rename + py_library wrapper.
    pyo3_extension_py_library(
        name = name,
        cdylib = ":" + name + "_cdylib",
        data = data,
        visibility = visibility,
    )

# ---- generate_rust_parser (public macro) ----------------------------------------

def generate_rust_parser(
        name,
        src,
        cst_mod_path = "super::cst",
        python_extension = False,
        ast_config = None,
        parser = True,
        ast = False,
        serde = False,
        unparser = False,
        format_config = None,
        goal = "",
        out_dir = "",
        protocol_module = "",
        protocol = False,
        extension_name = "",
        submodules = [],
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
    emitting `<name>/cst.rs` and (unless `parser = False`) `<name>/parser.rs` — or, with `out_dir`, the same
    files under a package-relative directory of the consumer's choosing, which is
    what lets their own `rust_library` glob its crate sources alongside them. No
    cdylib.
    With `protocol_module` (which then requires `extension_name`) the same action
    also emits the `.pyi` stub package, for a crate that is assembled and compiled
    by hand — several grammars in one cdylib, or a runtime flavor this macro does
    not link — so its stubs cost no second codegen run. `:name_stub_srcs` and
    `:name_rust_srcs` are then declared alongside `:name`, since the target's own
    files are both.
    The cdylib-only knobs (`lib_rs`, `deps`, `crate_features`, a non-default
    `recursion_limit`) must be left at their defaults; setting any of them is a
    misconfiguration and fails fast.
    `ast` / `serde` / `ast_config` / `unparser` / `format_config` / `goal` are
    valid in BOTH modes: the extra generated modules are ordinary Rust sources
    either way.

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
        parser: When True (the default), emit <name>/parser.rs. Set it False for a
                CST-only or unparser-only crate, which pays for the largest
                generated artifact in the set and then compiles none of it.
                python_extension = False only, and incompatible with ast / serde.
        ast: When True, also emit <name>/ast.rs (the generated typed tree). In
             python_extension mode the cdylib links fltk-ast-core and the
             generated lib.rs declares `pub mod ast;`.
        serde: When True, also emit <name>/de.rs (the serde frontend); requires
               ast_config. In python_extension mode the cdylib links
               fltk-serde-core and serde, and the generated lib.rs declares
               `pub mod de;`. With ast = True, de.rs also carries a Deserialize
               impl per generated AST type.
        unparser: When True, also emit <name>/unparser.rs (the generated unparser).
                  In python_extension mode the cdylib links fltk-unparser-core, the
                  generated lib.rs declares and registers `mod unparser;`, and (with
                  protocol_module) the stub package gains unparser.pyi. With
                  ast = True, ast.rs also gains its unparse_str entry point.
        format_config: A .fltkfmt spec baked into the generated unparser at
                       generation time. Requires unparser = True; omitting it
                       selects the default FormatterConfig.
        goal: Rule the ast.rs / de.rs entry points target (--goal). Empty (the
              default) leaves each generator's own default. Requires ast = True
              or serde = True; nothing else reads it.
        out_dir: Package-relative directory the generated .rs files land in, so a
                 consumer's rust_library can glob its own sources alongside them
                 (srcs = glob(["src/**/*.rs"]) + [":gen"], crate_root =
                 "src/lib.rs") instead of copying everything into one gendir.
                 Empty (the default) keeps the historical <name>/ layout. Must be
                 package-relative with no '..' segment. python_extension = False
                 only.
        protocol_module: Dotted Python import path of the protocol module; when
                         non-empty it triggers .pyi stub-package emission. In
                         pure-Rust mode it requires extension_name.
        protocol: When True (requires protocol_module), also emit the protocol
                  .py module.
        extension_name: The compiled module's import name, which is also the stub
                        package's directory name. Pure-Rust mode only, and only
                        with protocol_module: in python_extension mode both derive
                        from name.
        submodules: The submodule names written into the stub package's
                    __init__.pyi marker. Empty derives them from this target's own
                    outputs, which understates a hand-assembled crate root that
                    registers modules generated elsewhere. Requires
                    protocol_module, and pure-Rust mode only: in
                    python_extension mode the cdylib carries this target's
                    sources alone, so the derived list is the whole extension.
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
    _require_codegen_mode(
        ast = ast,
        serde = serde,
        has_ast_config = ast_config != None,
        goal = goal,
        unparser = unparser,
        has_format_config = format_config != None,
    )
    _require_out_dir(out_dir, python_extension = python_extension)
    _require_parser(parser, ast, serde, extension = python_extension)
    _require_stub_package(protocol_module, extension_name, python_extension)
    _require_submodules(submodules, protocol_module, python_extension = python_extension)

    if not python_extension:
        # Pure-Rust mode: the cdylib-only knobs must be at defaults.
        # Fail fast rather than silently ignore a value that has no effect here.
        msg = _pure_rust_mode_violation(
            lib_rs = lib_rs,
            deps = deps,
            crate_features = crate_features,
            recursion_limit = recursion_limit,
        )
        if msg != None:
            fail(msg)

        # The internal codegen rule IS the public target. With protocol_module it also
        # emits the stub package, named by extension_name — the shape a hand-assembled
        # extension needs, where the .rs go to the crate's own src/ and the .pyi to the
        # stub directory beside it.
        _generate_rust_srcs(
            name = name,
            src = src,
            cst_mod_path = cst_mod_path,
            ast_config = ast_config,
            parser = parser,
            ast = ast,
            serde = serde,
            unparser = unparser,
            format_config = format_config,
            goal = goal,
            out_dir = out_dir,
            extension_name = extension_name,
            protocol_module = protocol_module,
            protocol = protocol,
            submodules = submodules,
            visibility = visibility,
            **kwargs
        )
        if protocol_module:
            # The rule's DefaultInfo carries every output, .rs and .pyi alike, so the two
            # consumers each take an output group: a rust_library globs :name for sources,
            # and the py_library packaging the compiled module takes this filegroup as data.
            # The tags ride along so a `manual` codegen target does not get pulled into a
            # wildcard build through a filegroup that is not tagged.
            group_tags = kwargs.get("tags", [])
            native.filegroup(
                name = name + "_rust_srcs",
                srcs = [":" + name],
                output_group = "rust_srcs",
                tags = group_tags,
                visibility = visibility,
            )
            native.filegroup(
                name = name + "_stub_srcs",
                srcs = [":" + name],
                output_group = "stub_srcs",
                tags = group_tags,
                visibility = visibility,
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
        unparser = unparser,
        format_config = format_config,
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
    # Public alongside the extension itself: a consumer type-checking against the stubs needs
    # to name them directly, which reading them out of the py_library's runfiles does not allow.
    native.filegroup(
        name = name + "_stub_srcs",
        srcs = [":" + name + "_srcs"],
        output_group = "stub_srcs",
        visibility = visibility,
    )

    fltk_pyo3_cdylib(
        name = name,
        rs_srcs = ":" + name + "_rust_srcs",
        lib_rs = lib_rs,
        ast = ast,
        serde = serde,
        unparser = unparser,
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
    parser_violation = _parser_violation,
    submodules_violation = _submodules_violation,
    out_dir_violation = _out_dir_violation,
    stub_package_violation = _stub_package_violation,
    generated_path = _generated_path,
    plain_modules_for = _plain_modules_for,
    sibling_mod_path = _sibling_mod_path,
    generate_rust_srcs = _generate_rust_srcs,
    default_recursion_limit = _DEFAULT_RECURSION_LIMIT,
)
