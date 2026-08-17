"""FLTK Python-backend Bazel rules.

`generate_parser` runs FLTK's Python code generator over a grammar file and declares the
emitted modules as action outputs: the shared CST module, its typing-protocol companion,
and the two parser variants.

Load it as:
    load("@fltk//:rules.bzl", "generate_parser")

This file is deliberately free of rules_rust loads, so a pure-Python consumer that never
touches the Rust backend does not have to register a Rust toolchain.
"""

def _out_dir_violation(out_dir):
    """Return the out_dir misconfiguration message, or None.

    Two conditions, both about `declare_file` only being able to name files inside the
    package: an absolute path, and a path with a `..` segment. An empty out_dir is the
    default (outputs land directly in the package) and never violates.
    """
    if not out_dir:
        return None
    if out_dir.startswith("/"):
        return "generate_parser: out_dir must be a package-relative directory; '{}' is absolute.".format(out_dir)
    if ".." in out_dir.split("/"):
        return "generate_parser: out_dir must stay inside the package; '{}' escapes it via '..'.".format(out_dir)
    return None

def _protocol_only_violation(protocol_only, trivia_only, no_trivia_only):
    """Return the protocol_only/parser-selector exclusion message, or None.

    --protocol-only emits no parsers at all, so pairing it with a selector that picks
    *which* parser to emit describes nothing.
    """
    if protocol_only and (trivia_only or no_trivia_only):
        return ("generate_parser: protocol_only emits no parsers, so it cannot be combined with " +
                "trivia_only or no_trivia_only.")
    return None

def _format_config_violation(has_format_config, unparser):
    """Return the format_config/unparser coupling message, or None.

    Only the gen-py-unparser action takes a --format-config; with no unparser to bake it
    into, a format_config describes nothing and would silently do nothing.
    """
    if has_format_config and not unparser:
        return "generate_parser: format_config requires unparser = True; nothing else reads it."
    return None

def _unparser_protocol_only_violation(unparser, protocol_only):
    """Return the unparser/protocol_only exclusion message, or None.

    protocol_only means "the protocol module and nothing else", and the generated unparser
    imports the CST module that mode does not emit.
    """
    if unparser and protocol_only:
        return ("generate_parser: protocol_only emits only the protocol module, so it cannot be " +
                "combined with unparser.")
    return None

_STAGE0_LABEL = Label("//:genparser_stage0")

def _unparser_gen_tool_violation(unparser, gen_tool_label):
    """Return the unparser/stage-0 tool message, or None.

    The stage-0 generator carries the `generate` command alone, so `unparser = True` with it
    fails inside the codegen action with typer's "No such command 'gen-py-unparser'" — no
    rule, no attribute, nothing pointing at the constraint. Caught at analysis instead.
    """
    if unparser and gen_tool_label == _STAGE0_LABEL:
        return ("generate_parser: unparser = True needs the full generator; '{}' has the ".format(gen_tool_label) +
                "`generate` command only. Drop gen_tool to use the default //:genparser.")
    return None

def _trivia_selector_violation(trivia_only, no_trivia_only):
    """Return the trivia_only/no_trivia_only exclusion message, or None."""
    if trivia_only and no_trivia_only:
        return "generate_parser: trivia_only and no_trivia_only are mutually exclusive."
    return None

def _cst_mod_path_violation(cst_mod_path, base_name):
    """Return the cst_mod_path/base_name coupling message, or None.

    The generated CST module bakes in `from <cst_mod_path>_protocol import NodeKind`, and the
    protocol file is written as `<base_name>_cst_protocol.py` beside it. Those agree in place
    only when cst_mod_path's last dotted component is `<base_name>_cst`.
    """
    expected_last = base_name + "_cst"
    if cst_mod_path.split(".")[-1] != expected_last:
        return (("cst_mod_path %r must have %r as its last dotted component: the generated CST " +
                 "module imports NodeKind from cst_mod_path + \"_protocol\", and the protocol file " +
                 "is written as %s_cst_protocol.py beside it in this package.") %
                (cst_mod_path, expected_last, base_name))
    return None

def _generated_path(out_dir, basename):
    """The package-relative path a generated file is declared at.

    Empty and "." both mean the package root, where a bare basename is the declared path; a
    trailing slash on a real directory is absorbed rather than doubled.
    """
    subdir = out_dir.rstrip("/")
    if subdir == "" or subdir == ".":
        return basename
    return subdir + "/" + basename

def _genparser_impl(ctx):
    for msg in [
        _cst_mod_path_violation(ctx.attr.cst_mod_path, ctx.attr.base_name),
        _out_dir_violation(ctx.attr.out_dir),
        _trivia_selector_violation(ctx.attr.trivia_only, ctx.attr.no_trivia_only),
        _protocol_only_violation(ctx.attr.protocol_only, ctx.attr.trivia_only, ctx.attr.no_trivia_only),
        _format_config_violation(ctx.file.format_config != None, ctx.attr.unparser),
        _unparser_protocol_only_violation(ctx.attr.unparser, ctx.attr.protocol_only),
        _unparser_gen_tool_violation(ctx.attr.unparser, ctx.attr.gen_tool.label),
    ]:
        if msg != None:
            fail(msg)

    # The generated CST module imports NodeKind from the protocol module, so the protocol
    # file is the one output every configuration produces — including protocol_only, where it
    # is the only one. Declaring it first also makes its dirname the --output-dir every other
    # file lands beside.
    protocol_file = ctx.actions.declare_file(
        _generated_path(ctx.attr.out_dir, ctx.attr.base_name + "_cst_protocol.py"),
    )
    outputs = [protocol_file]

    args = ctx.actions.args()
    args.add("generate")
    args.add_all([ctx.file.src, ctx.attr.base_name, ctx.attr.cst_mod_path])
    args.add_all(["--output-dir", protocol_file.dirname])

    if ctx.attr.protocol_only:
        args.add("--protocol-only")
    else:
        if ctx.attr.trivia_only:
            args.add("--trivia-only")
        elif ctx.attr.no_trivia_only:
            args.add("--no-trivia-only")

        outputs.append(ctx.actions.declare_file(
            _generated_path(ctx.attr.out_dir, ctx.attr.base_name + "_cst.py"),
        ))
        if not ctx.attr.trivia_only:
            outputs.append(ctx.actions.declare_file(
                _generated_path(ctx.attr.out_dir, ctx.attr.base_name + "_parser.py"),
            ))
        if not ctx.attr.no_trivia_only:
            outputs.append(ctx.actions.declare_file(
                _generated_path(ctx.attr.out_dir, ctx.attr.base_name + "_trivia_parser.py"),
            ))

    ctx.actions.run(
        inputs = ctx.files.src,
        outputs = outputs,
        arguments = [args],
        progress_message = "Generating parser(s) for grammar %s" % ctx.file.src.short_path,
        executable = ctx.executable.gen_tool,
    )

    if ctx.attr.unparser:
        # Its own action, and its own process: the unparser is generated from the same grammar
        # by a different subcommand, and it is the only output a format_config feeds.
        #
        # The Rust backend merges its five codegen subcommands into one action instead, and
        # the same argument (shared .fltkg input, so the granularity buys nothing) applies
        # here — but the Python side has exactly two subcommands, and folding the unparser
        # into `generate` would change the argv every existing consumer already sends.  Two
        # actions is the cheaper of the two costs; revisit if a third subcommand appears.
        unparser_file = ctx.actions.declare_file(
            _generated_path(ctx.attr.out_dir, ctx.attr.base_name + "_unparser.py"),
        )
        unparser_args = ctx.actions.args()
        unparser_args.add("gen-py-unparser")
        unparser_args.add_all([ctx.file.src, ctx.attr.base_name, ctx.attr.cst_mod_path])
        unparser_args.add_all(["--output-dir", unparser_file.dirname])
        unparser_inputs = list(ctx.files.src)
        if ctx.file.format_config != None:
            unparser_args.add_all(["--format-config", ctx.file.format_config])
            unparser_inputs.append(ctx.file.format_config)

        ctx.actions.run(
            inputs = unparser_inputs,
            outputs = [unparser_file],
            arguments = [unparser_args],
            progress_message = "Generating unparser for grammar %s" % ctx.file.src.short_path,
            executable = ctx.executable.gen_tool,
        )
        outputs.append(unparser_file)

    return [DefaultInfo(files = depset(outputs))]

generate_parser = rule(
    implementation = _genparser_impl,
    attrs = {
        "src": attr.label(
            allow_single_file = True,
            mandatory = True,
            doc = "The FLTK grammar file (.fltkg)",
        ),
        "base_name": attr.string(
            mandatory = True,
            doc = "Base name for output files (without extension)",
        ),
        "cst_mod_path": attr.string(
            mandatory = True,
            doc = """Import name of the generated CST module.

The generated CST module imports its NodeKind from cst_mod_path + "_protocol", and the
protocol file is declared as base_name + "_cst_protocol.py" beside it in this package.
Both files land in this package, so the last dotted component must be base_name + "_cst"
(enforced: a mismatch fails at analysis time). Any dotted prefix must match the import
root of the py_library that consumes these srcs: with imports = ["."] on a py_library in
this package the flat name base_name + "_cst" is correct, while a consumer in package
mylang/ whose py_library sets imports = ["../.."] names the modules mylang.<base>_cst and
mylang.<base>_cst_protocol and must pass cst_mod_path = "mylang.<base>_cst".""",
        ),
        "trivia_only": attr.bool(
            default = False,
            doc = "Generate only the trivia-preserving parser",
        ),
        "no_trivia_only": attr.bool(
            default = False,
            doc = "Generate only the non-trivia parser",
        ),
        "protocol_only": attr.bool(
            default = False,
            doc = (
                "Emit only base_name + \"_cst_protocol.py\" — no CST module and no parsers. " +
                "This is the typing-protocol surface on its own, which is what a Rust-backed " +
                "grammar needs: the compiled extension supplies the CST and parser, and only " +
                "the protocol is needed to type a .pyi against. Cannot be combined with " +
                "trivia_only or no_trivia_only, which select among parsers this mode emits none of."
            ),
        ),
        "protocol": attr.bool(
            default = False,
            doc = "Deprecated no-op: {base_name}_cst_protocol.py is always generated",
        ),
        "unparser": attr.bool(
            default = False,
            doc = (
                "When True, a second action also emits <base_name>_unparser.py — the generated " +
                "Unparser class over the CST module named by cst_mod_path, rendering a parsed " +
                "tree back to source text. It reads the trivia the trivia-preserving parser " +
                "captures, so keep that parser (do not pair this with no_trivia_only). Cannot " +
                "be combined with protocol_only, which emits no CST module for it to walk."
            ),
        ),
        "format_config": attr.label(
            allow_single_file = True,
            doc = (
                "A .fltkfmt formatter-config file, passed to gen-py-unparser as " +
                "--format-config. Its spacing/anchor/disposition decisions are baked into the " +
                "generated unparser at generation time, so editing it is an ordinary input " +
                "change. Omitting it selects the default FormatterConfig. Requires unparser = " +
                "True: no other action reads it."
            ),
        ),
        "out_dir": attr.string(
            default = "",
            doc = (
                "Package-relative directory the generated modules are declared in. Empty (the " +
                "default) puts them directly in the package. Set it when the modules must land " +
                "at a Python package path a BUILD file cannot own — a root-package target " +
                "emitting into fltk/fegen/, say, where adding fltk/fegen/BUILD.bazel would cut " +
                "the root package's globs off at that directory. Must be package-relative and " +
                "must not contain a '..' segment."
            ),
        ),
        "gen_tool": attr.label(
            default = Label(":genparser"),
            executable = True,
            allow_files = True,
            cfg = "exec",
            doc = (
                "The generator binary. Defaults to //:genparser, the full CLI. Override it with " +
                "//:genparser_stage0 for the grammars whose output the full CLI transitively " +
                "imports — the Rust-backend generators it also carries import the generated " +
                "regex / fltkast / unparsefmt / fltklsp modules at module level, so the full " +
                "tool cannot be what brings those into existence. Both accept the same " +
                "`generate` argv; only the full tool has gen-py-unparser, so unparser = True " +
                "with the stage-0 tool is rejected at analysis."
            ),
        ),
    },
    doc = """Generate Python CST, protocol and parser modules from an FLTK grammar file.

Emits, in the package (or under out_dir):
  <base_name>_cst_protocol.py  — the typing protocol; always written
  <base_name>_cst.py           — the shared CST node classes
  <base_name>_parser.py        — parser without trivia preservation
  <base_name>_trivia_parser.py — parser with trivia preservation
  <base_name>_unparser.py      — the unparser; only with unparser = True

trivia_only / no_trivia_only drop one parser; protocol_only drops everything but the
protocol module. The emitted source is formatter-normalized by the generator itself, so
it never needs a separate formatting step.

Example:
    generate_parser(
        name = "mylang_parser",
        src = "mylang.fltkg",
        base_name = "mylang",
        cst_mod_path = "mylang_cst",
    )
""",
)

# Not public API. Exported solely for //tests/bazel_rules. Downstream consumers must not load
# this symbol; it may change without notice.
rules_bzl_internals = struct(
    out_dir_violation = _out_dir_violation,
    protocol_only_violation = _protocol_only_violation,
    format_config_violation = _format_config_violation,
    unparser_protocol_only_violation = _unparser_protocol_only_violation,
    unparser_gen_tool_violation = _unparser_gen_tool_violation,
    stage0_label = _STAGE0_LABEL,
    trivia_selector_violation = _trivia_selector_violation,
    cst_mod_path_violation = _cst_mod_path_violation,
    generated_path = _generated_path,
    generate_parser = generate_parser,
)
