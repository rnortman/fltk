"""The `//:pyright` type-check target, gated on `--//bzl:lint`.

Same shape as the ruff targets in `py_lint.bzl` — a build target with a stamp output that
only materializes when the tool exits clean — but pyright is whole-program, so there is one
coarse target rather than one per file.

Two things make it hermetic:

  * The tool is the `pyright` wheel's bundled `dist/index.js` (the npm package and its
    typeshed fallback ship inside the wheel), run under the `node` binary from the
    `nodejs-wheel-binaries` wheel.  The `pyright` package's own Python wrapper is bypassed
    on purpose: it fetches the npm package over the network on first run, which an action
    cannot do.
  * Sources are staged into a declared directory holding a generated `pyrightconfig.json`,
    so the checked tree is exactly the declared inputs at their package paths and pyright
    resolves every path relative to that directory.  Third-party imports resolve through
    `extraPaths` pointing at the deps' site-packages in the execroot.
"""

load("@rules_python//python:defs.bzl", "PyInfo")
load("//bzl:lint_flag.bzl", "LintFlagInfo")
load("//bzl:python_version.bzl", "FLTK_PYTHON_VERSION")

# The execroot is only knowable at action time, so absolute extraPaths entries are written
# as this placeholder and substituted by the action.
_EXECROOT = "@@EXECROOT@@"

def _tool_file(files, suffix, what):
    for f in files:
        if f.path.endswith(suffix):
            return f
    fail("no %s (*%s) among the wheel's extracted files; did the wheel layout change?" % (what, suffix))

def _import_to_exec_path(imp):
    """Maps a PyInfo `imports` entry (runfiles-root-relative) to an execroot-relative path."""
    if imp == "_main":
        return "."
    if imp.startswith("_main/"):
        return imp[len("_main/"):]
    return "external/" + imp

def _stage_pair(f):
    # `<input path>|<path inside the staged tree>`.  short_path is the package path for
    # source and generated files alike, which is what makes Bazel-generated modules land
    # beside the hand-written ones.
    return f.path + "|" + f.short_path

# Staging is pure overhead, so directory creation is batched: one `mkdir -p` over the
# deduplicated destination list rather than one per file.
_COMMAND = """
set -euo pipefail
node="$1"; js="$2"; tree="$3"; cfg="$4"; stamp="$5"; params="${6#@}"
rm -rf "$tree"
mkdir -p "$tree"
awk -F'|' -v tree="$tree" '{ d = $2; if (sub(/\\/[^\\/]*$/, "", d)) print tree "/" d }' "$params" |
    sort -u | tr '\\n' '\\0' | xargs -0 -r mkdir -p
while IFS='|' read -r src dest; do
    cp -f "$src" "$tree/$dest"
done < "$params"
sed "s|@@EXECROOT@@|$PWD|g" "$cfg" > "$tree/pyrightconfig.json"
"$node" "$js" --project "$tree"
: > "$stamp"
"""

def _pyright_lint_impl(ctx):
    stamp = ctx.actions.declare_file(ctx.label.name + ".stamp")

    if not ctx.attr._lint_flag[LintFlagInfo].enabled:
        ctx.actions.write(stamp, "lint disabled (--//bzl:lint=false)\n")
        return [DefaultInfo(files = depset([stamp]))]

    node = _tool_file(ctx.files._node, "/bin/node", "node binary")
    pyright_js = _tool_file(ctx.files._pyright, "/pyright/dist/index.js", "bundled pyright")
    # The typeshed fallback and the rest of dist/ are read at runtime, so the whole
    # extracted wheel rides along as a tool input.
    pyright_files = [f for f in ctx.files._pyright if "/pyright/dist/" in f.path]

    dep_imports = depset(transitive = [d[PyInfo].imports for d in ctx.attr.deps]).to_list()
    # Runfiles rather than PyInfo.transitive_sources: the latter carries only `.py` files,
    # and a wheel's `.pyi` stubs and `py.typed` markers are exactly what pyright reads.
    dep_files = depset(transitive = [
        d[DefaultInfo].default_runfiles.files
        for d in ctx.attr.deps
    ])

    config = ctx.actions.declare_file(ctx.label.name + ".pyrightconfig.json")
    ctx.actions.write(config, json.encode_indent({
        "pythonVersion": ctx.attr.python_version,
        "include": ctx.attr.include,
        "exclude": ctx.attr.exclude,
        "stubPath": ctx.attr.stub_path,
        "extraPaths": list(ctx.attr.extra_paths) +
                      [_EXECROOT + "/" + _import_to_exec_path(i) for i in dep_imports],
    }))

    tree = ctx.actions.declare_directory(ctx.label.name + ".tree")

    fixed = ctx.actions.args()
    fixed.add_all([node, pyright_js, tree, config, stamp], expand_directories = False)

    stage = ctx.actions.args()
    stage.add_all(ctx.files.srcs, map_each = _stage_pair)
    stage.use_param_file("@%s", use_always = True)
    stage.set_param_file_format("multiline")

    ctx.actions.run_shell(
        outputs = [stamp, tree],
        inputs = depset(ctx.files.srcs + [config], transitive = [dep_files]),
        tools = [node] + pyright_files,
        arguments = [fixed, stage],
        command = _COMMAND,
        mnemonic = "Pyright",
        progress_message = "pyright on %{label}",
        # pyright writes nothing outside the project, but node consults HOME for its
        # (unused here) config; point it at a path that exists in every sandbox.
        env = {"HOME": "/tmp"},
    )
    return [DefaultInfo(files = depset([stamp]))]

pyright_lint = rule(
    implementation = _pyright_lint_impl,
    doc = "Runs pyright over a staged copy of srcs when --//bzl:lint is set.",
    attrs = {
        "deps": attr.label_list(
            providers = [PyInfo],
            doc = "Third-party libraries whose site-packages become extraPaths entries.",
        ),
        "exclude": attr.string_list(doc = "pyrightconfig `exclude`, relative to the staged tree."),
        "extra_paths": attr.string_list(
            doc = "pyrightconfig `extraPaths` entries relative to the staged tree.",
        ),
        "include": attr.string_list(
            mandatory = True,
            doc = "pyrightconfig `include`, relative to the staged tree.",
        ),
        "python_version": attr.string(default = FLTK_PYTHON_VERSION),
        "srcs": attr.label_list(
            allow_files = True,
            doc = "Files staged into the checked tree at their package paths.",
        ),
        "stub_path": attr.string(default = ""),
        "_lint_flag": attr.label(default = Label("//bzl:lint")),
        "_node": attr.label(
            default = Label("@pypi//nodejs_wheel_binaries:extracted_whl_files"),
            allow_files = True,
        ),
        "_pyright": attr.label(
            default = Label("@pypi//pyright:extracted_whl_files"),
            allow_files = True,
        ),
    },
)
