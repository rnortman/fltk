def _genparser_impl(ctx):
    expected_last = ctx.attr.base_name + "_cst"
    if ctx.attr.cst_mod_path.split(".")[-1] != expected_last:
        fail(
            ("cst_mod_path %r must have %r as its last dotted component: the generated CST " +
             "module imports NodeKind from cst_mod_path + \"_protocol\", and the protocol file " +
             "is written as %s_cst_protocol.py beside it in this package.") %
            (ctx.attr.cst_mod_path, expected_last, ctx.attr.base_name),
        )

    args = ctx.actions.args()
    args.add("generate")
    args.add_all([ctx.file.src, ctx.attr.base_name, ctx.attr.cst_mod_path])

    cst_file = ctx.actions.declare_file(ctx.attr.base_name + "_cst.py")
    outputs = [cst_file]

    args.add_all(["--output-dir", cst_file.dirname])

    if ctx.attr.trivia_only:
        args.add("--trivia-only")
    elif ctx.attr.no_trivia_only:
        args.add("--no-trivia-only")

    if not ctx.attr.trivia_only:
        parser_file = ctx.actions.declare_file(ctx.attr.base_name + "_parser.py")
        outputs.append(parser_file)
    
    if not ctx.attr.no_trivia_only:
        trivia_parser_file = ctx.actions.declare_file(ctx.attr.base_name + "_trivia_parser.py")
        outputs.append(trivia_parser_file)

    # The generated CST module imports NodeKind from the protocol module, so it
    # must always be emitted. The `protocol` attr is a deprecated no-op kept so
    # existing BUILD files keep working.
    protocol_file = ctx.actions.declare_file(ctx.attr.base_name + "_cst_protocol.py")
    outputs.append(protocol_file)

    ctx.actions.run(
        inputs = ctx.files.src,
        outputs = outputs,
        arguments = [args],
        progress_message = "Generating parser(s) for grammar %s" % ctx.file.src.short_path,
        executable = ctx.executable._gen_tool,
    )
    
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
        "protocol": attr.bool(
            default = False,
            doc = "Deprecated no-op: {base_name}_cst_protocol.py is always generated",
        ),
        "_gen_tool": attr.label(
            default = Label(":genparser"),
            executable = True,
            allow_files = True,
            cfg = "exec",
        ),
    },
)