def _genparser_impl(ctx):
    args = ctx.actions.args()
    args.add("generate")
    args.add_all([ctx.file.src, ctx.attr.base_name, ctx.attr.cst_mod_path])
    
    # Set output directory to current package directory
    args.add_all(["--output-dir", ctx.bin_dir.path + "/" + ctx.label.package])
    
    # Control which parsers to generate
    if ctx.attr.trivia_only:
        args.add("--trivia-only")
    elif ctx.attr.no_trivia_only:
        args.add("--no-trivia-only")
    # Default generates both parsers

    # Auto-compute output file names based on base_name
    cst_file = ctx.actions.declare_file(ctx.attr.base_name + "_cst.py")
    outputs = [cst_file]
    
    # Conditionally declare parser outputs based on configuration
    if not ctx.attr.trivia_only:
        parser_file = ctx.actions.declare_file(ctx.attr.base_name + "_parser.py")
        outputs.append(parser_file)
    
    if not ctx.attr.no_trivia_only:
        trivia_parser_file = ctx.actions.declare_file(ctx.attr.base_name + "_trivia_parser.py")
        outputs.append(trivia_parser_file)

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
            doc = "Base module name for CST classes",
        ),
        "trivia_only": attr.bool(
            default = False,
            doc = "Generate only the trivia-preserving parser",
        ),
        "no_trivia_only": attr.bool(
            default = False,
            doc = "Generate only the non-trivia parser",
        ),
        "_gen_tool": attr.label(
            default = Label(":genparser"),
            executable = True,
            allow_files = True,
            cfg = "exec",
        ),
    },
)