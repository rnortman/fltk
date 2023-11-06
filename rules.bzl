def _genparser_impl(ctx):
    args = ctx.actions.args()
    args.add_all([ctx.file.src, ctx.outputs.out_parser_py, ctx.outputs.out_cst_py, ctx.attr.cst_mod_path])

    outputs = [ctx.outputs.out_parser_py, ctx.outputs.out_cst_py]

    # Action to call the script.
    ctx.actions.run(
        inputs = ctx.files.src,
        outputs = outputs,
        arguments = [args],
        progress_message = "Generating parser for grammar %s" % ctx.file.src.short_path,
        executable = ctx.executable._gen_tool,
    )

generate_parser = rule(
    implementation = _genparser_impl,
    attrs = {
        "src": attr.label(
            allow_single_file = True,
            mandatory = True,
        ),
        "out_parser_py": attr.output(mandatory=True),
        "out_cst_py": attr.output(mandatory=True),
	"cst_mod_path": attr.string(mandatory=True),
        "_gen_tool": attr.label(
            default = Label(":genparser"),
            executable = True,
            allow_files = True,
            cfg = "exec",
        ),
    },
)