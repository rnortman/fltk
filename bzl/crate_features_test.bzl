"""Analysis test: a Rust target really compiles with the features its purpose depends on.

Several targets in this repo exist only to compile code that lives behind a `#[cfg(feature =
...)]`, and the feature reaches rustc only through the compile action's command line. Dropping or
misspelling `crate_features` compiles the gated code away and leaves a green target covering
nothing, so the argv is what is asserted.
"""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts")

def _rustc_argv(env):
    """The argv of the target's single Rustc action, or None."""
    actions = [a for a in analysistest.target_actions(env) if a.mnemonic == "Rustc"]
    if len(actions) != 1:
        return None
    return actions[0].argv

def _crate_features_impl(ctx):
    env = analysistest.begin(ctx)
    argv = _rustc_argv(env)
    asserts.true(env, argv != None, "expected exactly one Rustc action to inspect")
    if argv != None:
        for feature in ctx.attr.expected_features:
            asserts.true(
                env,
                'feature="%s"' % feature in argv,
                "rustc must be told feature %s; without it the target compiles the gated code away" % feature,
            )
    return analysistest.end(env)

crate_features_test = analysistest.make(
    _crate_features_impl,
    attrs = {
        "expected_features": attr.string_list(
            mandatory = True,
            doc = "Features the target under test must pass to rustc.",
        ),
    },
)
