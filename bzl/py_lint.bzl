"""Python lint targets, gated on `--//bzl:lint`.

The linters are *build* targets, not tests: each declares a stamp output that only
materializes when the tool exits clean, so `bazel build --config lint //...` is the gate and
Bazel's action cache makes an unchanged re-run free.  A plain `bazel build //...` must stay
cheap, so with the flag off the rule writes the stamp directly and never reaches for the
tool at all — with no action consuming them, neither the ruff binary nor the source list is
staged.

`ruff_tree_check` is the one deliberate exception: a `bazel run` target that checks
working-tree paths the build graph cannot name (a `.bazelignore`d directory has no package, so
no label reaches its files).  It reads the developer's tree from the workspace root, is
uncached, and is not gated on the flag.
"""

load("//bzl:gencode_tool.bzl", "RUFF_WHL_FILES")
load("//bzl:lint_flag.bzl", "LintFlagInfo")

# The ruff wheel ships its executable under `<wheel>.data/scripts/`, not as a
# `entry_points.txt` console script, so rules_python's py_console_script_binary cannot see
# it and the package's own `find_ruff_bin()` cannot locate it from a runfiles layout (it
# probes venv/sysconfig script directories that do not exist there).  Picking the file out
# of the extracted wheel at analysis time sidesteps both and yields a plain executable File.
def _ruff_exe(ctx):
    for f in ctx.files._ruff:
        if f.basename == "ruff" and f.dirname.endswith("/bin"):
            return f
    fail("no bin/ruff in @pypi//ruff's extracted wheel files; did the wheel layout change?")

def _ruff_lint_impl(ctx):
    stamp = ctx.actions.declare_file(ctx.label.name + ".stamp")

    if not ctx.attr._lint_flag[LintFlagInfo].enabled:
        ctx.actions.write(stamp, "lint disabled (--//bzl:lint=false)\n")
        return [DefaultInfo(files = depset([stamp]))]

    ruff = _ruff_exe(ctx)
    args = ctx.actions.args()
    args.add(ruff)
    if ctx.attr.mode == "format":
        args.add_all(["format", "--check"])
    else:
        args.add("check")
    args.add("-q")
    args.add("--config", ctx.file.config)
    args.add_all(ctx.files.srcs)

    ctx.actions.run_shell(
        outputs = [stamp],
        inputs = depset(ctx.files.srcs + ctx.files.config_deps + [ctx.file.config]),
        tools = [ruff],
        arguments = [args],
        # "$@" runs the tool with everything the Args object carried; the stamp is written
        # only on success, which is what makes a finding fail `bazel build`.
        command = '"$@" && : > "' + stamp.path + '"',
        mnemonic = "RuffFormatCheck" if ctx.attr.mode == "format" else "RuffCheck",
        progress_message = "ruff %s on %%{label}" % ctx.attr.mode,
    )
    return [DefaultInfo(files = depset([stamp]))]

_RUFF_ATTR = attr.label(
    default = Label(RUFF_WHL_FILES),
    allow_files = True,
)

ruff_lint = rule(
    implementation = _ruff_lint_impl,
    doc = "Runs `ruff check` or `ruff format --check` over srcs when --//bzl:lint is set.",
    attrs = {
        "config": attr.label(
            allow_single_file = True,
            mandatory = True,
            doc = "The ruff config, passed explicitly; discovery is never relied on.",
        ),
        "config_deps": attr.label_list(
            allow_files = True,
            doc = "Files the config `extend`s, so editing one invalidates the check.",
        ),
        "mode": attr.string(
            mandatory = True,
            values = ["check", "format"],
        ),
        "srcs": attr.label_list(allow_files = True),
        "_lint_flag": attr.label(default = Label("//bzl:lint")),
        "_ruff": _RUFF_ATTR,
    },
)

_RUFF_FIX_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail
# `bazel run` lands in the runfiles tree; the point of this target is to edit the developer's
# actual sources, which is what BUILD_WORKSPACE_DIRECTORY points at.
if [[ -z "${{BUILD_WORKSPACE_DIRECTORY:-}}" ]]; then
  echo "ruff_fix must be invoked via 'bazel run', not executed directly" >&2
  exit 2
fi
ruff="$PWD/{ruff}"
cd "$BUILD_WORKSPACE_DIRECTORY"
"$ruff" check --fix .
"$ruff" format .
"""

def _write_ruff_launcher(ctx, template, **fields):
    ruff = _ruff_exe(ctx)
    launcher = ctx.actions.declare_file(ctx.label.name + ".sh")
    ctx.actions.write(
        output = launcher,
        content = template.format(ruff = ruff.short_path, **fields),
        is_executable = True,
    )
    return [DefaultInfo(
        executable = launcher,
        runfiles = ctx.runfiles(files = [ruff]),
    )]

def _ruff_fix_impl(ctx):
    return _write_ruff_launcher(ctx, _RUFF_FIX_TEMPLATE)

ruff_fix = rule(
    implementation = _ruff_fix_impl,
    doc = "`bazel run //:ruff_fix` — ruff check --fix + ruff format over the source tree.",
    executable = True,
    attrs = {"_ruff": _RUFF_ATTR},
)

_RUFF_TREE_CHECK_TEMPLATE = """#!/usr/bin/env bash
set -uo pipefail
# The paths this target checks have no Bazel label, so it reads them from the developer's tree,
# which is what BUILD_WORKSPACE_DIRECTORY points at.  Running from that root is also what makes
# the config's path-scoped per-file-ignores match them.
if [[ -z "${{BUILD_WORKSPACE_DIRECTORY:-}}" ]]; then
  echo "{name} must be invoked via 'bazel run', not executed directly" >&2
  exit 2
fi
ruff="$PWD/{ruff}"
cd "$BUILD_WORKSPACE_DIRECTORY"
# No `set -e`: both commands run, and either one failing fails the target.
status=0
# `--config=` and `--` keep a value that starts with `-` from being read as an option.
"$ruff" check --no-cache --config={config} -- {paths} || status=1
"$ruff" format --check --no-cache --config={config} -- {paths} || status=1
exit "$status"
"""

# Single-quotes a value for the launcher: inside '...' the shell expands nothing, and an
# embedded ' is closed, escaped and reopened.
def _sh_quote(value):
    return "'" + value.replace("'", "'\\''") + "'"

def _ruff_tree_check_impl(ctx):
    return _write_ruff_launcher(
        ctx,
        _RUFF_TREE_CHECK_TEMPLATE,
        name = ctx.label.name,
        config = _sh_quote(ctx.attr.config),
        paths = " ".join([_sh_quote(p) for p in ctx.attr.paths]),
    )

ruff_tree_check = rule(
    implementation = _ruff_tree_check_impl,
    doc = "`bazel run` target: ruff check + ruff format --check over working-tree paths the " +
          "build graph cannot name (a .bazelignore'd directory).  Uncached; reads the tree.",
    executable = True,
    attrs = {
        "config": attr.string(
            mandatory = True,
            doc = "Workspace-relative ruff config, read from the working tree after the cd.",
        ),
        "paths": attr.string_list(
            mandatory = True,
            allow_empty = False,
            doc = "Workspace-relative paths to check.",
        ),
        "_ruff": _RUFF_ATTR,
    },
)
