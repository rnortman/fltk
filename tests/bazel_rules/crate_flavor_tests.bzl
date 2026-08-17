"""Analysis tests: the python-featured `rust_test` targets really compile with the feature.

`rust_test` does not inherit `crate_features` from the crate it wraps, so the two targets that
cover the python-gated Rust code restate `srcs`/`crate_features`/`deps` instead of taking
`crate = ...`.  Both failure modes are silent: a `crate = ...` "simplification" produces a
second copy of the no-python test binary, and dropping `"python"` from `crate_features`
compiles the same crate with the gated modules cfg'd out.  Either one is a green target running
tests that no longer exist, and these two targets are the only place the python-gated tests are
compiled at all.

"""

load("//bzl:crate_features_test.bzl", "crate_features_test")

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
