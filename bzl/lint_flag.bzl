"""The `--//bzl:lint` boolean build setting that gates fltk's Python lint targets.

Hand-rolled rather than `bazel_skylib`'s `bool_flag` on purpose: skylib is a
`dev_dependency` in MODULE.bazel, so it is not fetched into a downstream consumer's module
graph.  The root BUILD.bazel — which consumers *do* load, for `//:fltk` and `//:genparser` —
declares targets that read this flag, and a skylib load reached from there would break every
consumer's build.  Ten lines of our own cost nothing and keep that door shut.
"""

LintFlagInfo = provider(
    doc = "Whether the Python lint targets should run their tool, or stamp and do nothing.",
    fields = {"enabled": "bool"},
)

def _lint_flag_impl(ctx):
    return [LintFlagInfo(enabled = ctx.build_setting_value)]

lint_flag = rule(
    implementation = _lint_flag_impl,
    build_setting = config.bool(flag = True),
    doc = "Boolean flag; set with --//bzl:lint=true (the `lint` config in .bazelrc does).",
)
