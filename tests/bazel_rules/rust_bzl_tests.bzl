"""Regression coverage for generate_rust_parser's misconfiguration guards.

The public Bazel macro protects downstream consumers with seven
misconfiguration conditions (six pure-Rust-mode
python-extension-only knob checks + the protocol/protocol_module coupling). This
suite pins each condition and its exact user-facing message so a future edit that
disables a guard or reworks a message fails a test.

Six of the seven conditions fire at loading time (BUILD-file evaluation), so no
target exists for analysistest to wrap; their condition + message logic is
extracted into pure functions in rust.bzl and exercised here via skylib unittest.
The one analysis-time guard (the coupling check inside the internal
_generate_rust_srcs rule impl) is covered end-to-end with analysistest.

Loads test-only internals via rust_bzl_internals; downstream consumers must never
load that symbol.
"""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//:rust.bzl", "rust_bzl_internals")

_PURE_RUST_MSG_TMPL = "generate_rust_parser: {} is only valid with python_extension = True."
_COUPLING_MSG = "generate_rust_parser: protocol = True requires a non-empty protocol_module."

# ---- Unit tests: _pure_rust_mode_violation ---------------------------------------
#
# Each test sets exactly one knob away from its default (all others at defaults)
# and asserts the exact per-knob message, so the tests pin condition + message
# without over-constraining the loop's iteration order.

def _defaults():
    """Return the pure-Rust knob kwargs, all at their defaults (no violation)."""
    return {
        "protocol_module": "",
        "protocol": False,
        "lib_rs": None,
        "deps": [],
        "crate_features": [],
        "recursion_limit": rust_bzl_internals.default_recursion_limit,
    }

def _pure_rust_knob_impl_factory(knob_name, override):
    def _impl(ctx):
        env = unittest.begin(ctx)
        kwargs = _defaults()
        kwargs[knob_name] = override
        msg = rust_bzl_internals.pure_rust_mode_violation(**kwargs)
        asserts.equals(
            env,
            _PURE_RUST_MSG_TMPL.format(knob_name),
            msg,
            "knob %s set away from default must report its own violation message" % knob_name,
        )
        return unittest.end(env)

    return _impl

# One unittest per knob. Each rule MUST be bound to a top-level global in this
# .bzl (Bazel rejects rules created only as dict/list values — "Invalid rule
# class hasn't been exported by a bzl file"), so they are spelled out rather than
# built in a comprehension. lib_rs uses a string label (its sentinel is None, not
# falsiness); recursion_limit uses default + 1.
pure_rust_protocol_module_test = unittest.make(
    _pure_rust_knob_impl_factory("protocol_module", "some.module"),
)
pure_rust_protocol_test = unittest.make(
    _pure_rust_knob_impl_factory("protocol", True),
)
pure_rust_lib_rs_test = unittest.make(
    _pure_rust_knob_impl_factory("lib_rs", ":lib.rs"),
)
pure_rust_deps_test = unittest.make(
    _pure_rust_knob_impl_factory("deps", ["//some:dep"]),
)
pure_rust_crate_features_test = unittest.make(
    _pure_rust_knob_impl_factory("crate_features", ["some_feature"]),
)
pure_rust_recursion_limit_test = unittest.make(
    _pure_rust_knob_impl_factory("recursion_limit", rust_bzl_internals.default_recursion_limit + 1),
)

def _pure_rust_all_defaults_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.pure_rust_mode_violation(**_defaults())
    asserts.equals(env, None, msg, "all knobs at defaults must be a non-violation (None)")
    return unittest.end(env)

pure_rust_all_defaults_test = unittest.make(_pure_rust_all_defaults_impl)

# ---- Unit tests: _protocol_module_violation --------------------------------------

def _coupling_violation_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.protocol_module_violation(True, "")
    asserts.equals(env, _COUPLING_MSG, msg, "protocol=True with empty protocol_module must violate")
    return unittest.end(env)

coupling_violation_test = unittest.make(_coupling_violation_impl)

def _coupling_satisfied_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.protocol_module_violation(True, "some.module")
    asserts.equals(env, None, msg, "protocol=True with a non-empty protocol_module is fine")
    return unittest.end(env)

coupling_satisfied_test = unittest.make(_coupling_satisfied_impl)

def _coupling_protocol_off_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.protocol_module_violation(False, "")
    asserts.equals(env, None, msg, "protocol=False never requires protocol_module")
    return unittest.end(env)

coupling_protocol_off_test = unittest.make(_coupling_protocol_off_impl)

# ---- Analysis test: analysis-time coupling guard in _generate_rust_srcs ----------
#
# Wraps the :neg_protocol_without_module target-under-test (instantiated in
# BUILD.bazel via rust_bzl_internals.generate_rust_srcs with protocol = True and
# protocol_module = ""). Via the public macro this analysis-time guard is shadowed
# by the loading-time coupling check; instantiating the internal rule directly is
# the only way the analysis-time path fires, which is exactly the defense-in-depth
# path this test pins.

def _coupling_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _COUPLING_MSG)
    return analysistest.end(env)

coupling_analysis_test = analysistest.make(
    _coupling_analysis_impl,
    expect_failure = True,
)

# ---- Suite -----------------------------------------------------------------------

def rust_bzl_test_suite(name):
    """Instantiate every unit test, the analysistest, and a wrapping test_suite.

    The unit tests are grouped under a `<name>_unit_tests` sub-suite via
    `unittest.suite` (which builds a `native.test_suite` with an explicit `tests`
    list). The analysistest is a separate target, so it is added alongside that
    sub-suite in the top-level `<name>` test_suite. Otherwise `bazel test
    //tests/bazel_rules:<name>` would silently skip the one analysis-time guard.
    """
    unittest.suite(
        name + "_unit_tests",
        pure_rust_protocol_module_test,
        pure_rust_protocol_test,
        pure_rust_lib_rs_test,
        pure_rust_deps_test,
        pure_rust_crate_features_test,
        pure_rust_recursion_limit_test,
        pure_rust_all_defaults_test,
        coupling_violation_test,
        coupling_satisfied_test,
        coupling_protocol_off_test,
    )

    coupling_analysis_test(
        name = name + "_coupling_analysis_test",
        target_under_test = ":neg_protocol_without_module",
    )

    native.test_suite(
        name = name,
        tests = [
            ":" + name + "_unit_tests",
            ":" + name + "_coupling_analysis_test",
        ],
    )
