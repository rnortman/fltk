"""Analysis tests: the python-featured `rust_test` targets really compile with the feature.

`rust_test` does not inherit `crate_features` from the crate it wraps, so the two targets that
cover the python-gated Rust code restate `srcs`/`crate_features`/`deps` instead of taking
`crate = ...`.  Both failure modes are silent: a `crate = ...` "simplification" produces a
second copy of the no-python test binary, and dropping `"python"` from `crate_features`
compiles the same crate with the gated modules cfg'd out.  Either one is a green target running
tests that no longer exist, and these two targets are the only place the python-gated tests are
compiled at all.

The feature reaches rustc only through the compile action's command line, so that is what is
asserted.
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

def crate_flavor_test_suite(name):
    """Feature-argv coverage for the two hand-restated python-flavor `rust_test` targets."""
    crate_features_test(
        name = name + "_cst_core_python_test",
        target_under_test = "//crates/fltk-cst-core:python_test",
        expected_features = ["python"],
    )

    crate_features_test(
        name = name + "_rust_cst_fixture_native_test",
        target_under_test = "//tests/rust_cst_fixture:native_test",
        expected_features = [
            "extension-module",
            "python",
        ],
    )

    native.test_suite(
        name = name,
        tests = [
            ":" + name + "_cst_core_python_test",
            ":" + name + "_rust_cst_fixture_native_test",
        ],
    )
