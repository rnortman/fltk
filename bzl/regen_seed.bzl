"""`bazel run` wrapper that regenerates a committed generated file group in place.

The self-hosting seed (`fltk/fegen/fltk_{cst,cst_protocol,parser,trivia_parser}.py`) is the
one generated group that stays committed: the generator needs it to read any grammar file,
so nothing can generate it from scratch inside the build graph.  This target is how it is
refreshed, and the fixed-point test is what fails when someone forgets.

Like //:ruff_fix, the launcher edits the developer's sources rather than a sandbox, which is
what BUILD_WORKSPACE_DIRECTORY points at.
"""

_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail
if [[ -z "${{BUILD_WORKSPACE_DIRECTORY:-}}" ]]; then
  echo "{name} must be invoked via 'bazel run', not executed directly" >&2
  exit 2
fi
gen_tool="$PWD/{gen_tool}"
cd "$BUILD_WORKSPACE_DIRECTORY"
# Every substitution is quoted: these values become a path in the developer's own source
# tree, and an unquoted one containing a space or a glob character would write elsewhere.
exec "$gen_tool" generate "{grammar}" "{base_name}" "{cst_mod_path}" --output-dir "{out_dir}"
"""

def _regen_seed_impl(ctx):
    launcher = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        output = launcher,
        content = _TEMPLATE.format(
            name = ctx.label.name,
            gen_tool = ctx.executable.gen_tool.short_path,
            grammar = ctx.attr.grammar,
            base_name = ctx.attr.base_name,
            cst_mod_path = ctx.attr.cst_mod_path,
            out_dir = ctx.attr.out_dir,
        ),
        is_executable = True,
    )
    runfiles = ctx.runfiles(files = [ctx.executable.gen_tool])
    runfiles = runfiles.merge(ctx.attr.gen_tool[DefaultInfo].default_runfiles)
    return [DefaultInfo(executable = launcher, runfiles = runfiles)]

regen_seed = rule(
    implementation = _regen_seed_impl,
    doc = "`bazel run` target that regenerates a grammar's Python modules into the source tree.",
    executable = True,
    attrs = {
        "base_name": attr.string(
            mandatory = True,
            doc = "Base name for the emitted files, the generator's second positional.",
        ),
        "cst_mod_path": attr.string(
            mandatory = True,
            doc = "Import name of the generated CST module, the generator's third positional.",
        ),
        "grammar": attr.string(
            mandatory = True,
            doc = "Workspace-relative path to the .fltkg file, read from the source tree.",
        ),
        "out_dir": attr.string(
            mandatory = True,
            doc = "Workspace-relative directory the modules are written into.",
        ),
        "gen_tool": attr.label(
            mandatory = True,
            executable = True,
            cfg = "target",
            doc = "The generator binary to run.",
        ),
    },
)
