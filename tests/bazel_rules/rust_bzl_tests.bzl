"""Regression coverage for generate_rust_parser's misconfiguration guards.

The public Bazel macro protects downstream consumers with ten misconfiguration
conditions (six pure-Rust-mode python-extension-only knob checks, the
protocol/protocol_module coupling, and the three ast/serde/ast_config/goal
conditions). This suite pins each condition and its exact user-facing message so a
future edit that disables a guard or reworks a message fails a test. It also pins
the cst_mod_path → sibling module-path derivation the generated ast.rs / de.rs name
each other through, the ast/serde → plain-module mapping, and — by reading action
command lines — that the rule attrs actually reach the generators.

Every condition fires at loading time (BUILD-file evaluation), so no target exists
for analysistest to wrap; their condition + message logic is extracted into pure
functions in rust.bzl and exercised here via skylib unittest. The two guards that
are also enforced at analysis time (inside the internal _generate_rust_srcs rule
impl) are covered end-to-end with analysistest.

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

# ---- Unit tests: _codegen_mode_violation -----------------------------------------
#
# Three misconfigurations: serde without a sidecar, a sidecar nothing reads, and a
# goal nothing reads. `ast` without a sidecar is legal (grammar-derived AST); pinning
# that keeps a future "require it everywhere" edit from silently breaking Tier 0
# consumers, as does pinning the legal serde-without-ast combination.

_SERDE_NEEDS_CONFIG_MSG = "generate_rust_parser: serde = True requires ast_config (the .fltkast sidecar shaping the tree)."
_UNUSED_CONFIG_MSG = "generate_rust_parser: ast_config requires ast = True or serde = True; nothing else reads it."
_UNUSED_GOAL_MSG = "generate_rust_parser: goal requires ast = True or serde = True; nothing else reads it."

def _serde_without_config_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(False, True, False)
    asserts.equals(env, _SERDE_NEEDS_CONFIG_MSG, msg, "serde = True without a sidecar must violate")
    return unittest.end(env)

codegen_serde_without_config_test = unittest.make(_serde_without_config_impl)

def _config_without_consumer_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(False, False, True)
    asserts.equals(env, _UNUSED_CONFIG_MSG, msg, "a sidecar with neither ast nor serde must violate")
    return unittest.end(env)

codegen_config_without_consumer_test = unittest.make(_config_without_consumer_impl)

def _ast_without_config_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(True, False, False)
    asserts.equals(env, None, msg, "ast = True without a sidecar is the grammar-derived mode, not a violation")
    return unittest.end(env)

codegen_ast_without_config_test = unittest.make(_ast_without_config_impl)

def _codegen_off_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(False, False, False)
    asserts.equals(env, None, msg, "neither knob set and no sidecar is the default configuration")
    return unittest.end(env)

codegen_off_test = unittest.make(_codegen_off_impl)

def _codegen_both_with_config_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(True, True, True)
    asserts.equals(env, None, msg, "ast + serde + sidecar is the full configuration")
    return unittest.end(env)

codegen_both_with_config_test = unittest.make(_codegen_both_with_config_impl)

def _codegen_serde_only_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(False, True, True)
    asserts.equals(env, None, msg, "serde + sidecar without ast is the bring-your-own-structs mode")
    return unittest.end(env)

codegen_serde_only_test = unittest.make(_codegen_serde_only_impl)

def _codegen_goal_without_consumer_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(False, False, False, "config")
    asserts.equals(env, _UNUSED_GOAL_MSG, msg, "a goal with neither ast nor serde is read by nothing")
    return unittest.end(env)

codegen_goal_without_consumer_test = unittest.make(_codegen_goal_without_consumer_impl)

def _codegen_goal_with_ast_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(True, False, False, "config")
    asserts.equals(env, None, msg, "gen-rust-ast reads goal, so ast = True makes it legal")
    return unittest.end(env)

codegen_goal_with_ast_test = unittest.make(_codegen_goal_with_ast_impl)

# ---- Unit tests: _plain_modules_for ----------------------------------------------
#
# The macro hop from fltk_pyo3_cdylib's ast / serde flags to the generated crate root's
# `pub mod` declarations. No compile target can witness it: an .rs file in a crate's srcs
# that no `mod` declaration names is not compiled, and rustc reports nothing — so a target
# whose generated modules silently stopped being declared still passes. These tests and the
# gen-rust-lib argv analysistest below are the two halves of that path.
#
# This is a pure function rather than an analysistest over the macro-generated _gen_lib
# target because those targets are package-private to the root package, and making the root
# BUILD file load this (skylib-dependent) .bzl breaks every downstream consumer: skylib is a
# dev_dependency of @fltk, so @fltk//'s root package would stop loading from another module.

def _plain_modules_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, ["ast", "de"], rust_bzl_internals.plain_modules_for(True, True))
    asserts.equals(env, ["ast"], rust_bzl_internals.plain_modules_for(True, False))
    asserts.equals(
        env,
        ["de"],
        rust_bzl_internals.plain_modules_for(False, True),
        "serde without ast is the bring-your-own-structs crate: de.rs alone, no fltk-ast-core",
    )
    asserts.equals(env, [], rust_bzl_internals.plain_modules_for(False, False))
    return unittest.end(env)

plain_modules_for_test = unittest.make(_plain_modules_impl)

# ---- Unit tests: _sibling_mod_path -----------------------------------------------
#
# The generated modules name each other by module path, and the crate assembly puts
# them in one flat root; this derivation is what states that layout once.

def _sibling_default_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, "super::parser", rust_bzl_internals.sibling_mod_path("super::cst", "parser"))
    asserts.equals(env, "super::ast", rust_bzl_internals.sibling_mod_path("super::cst", "ast"))
    return unittest.end(env)

sibling_default_test = unittest.make(_sibling_default_impl)

def _sibling_nested_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        "crate::grammar::parser",
        rust_bzl_internals.sibling_mod_path("crate::grammar::cst", "parser"),
        "a deeper cst path keeps every segment but the last",
    )
    return unittest.end(env)

sibling_nested_test = unittest.make(_sibling_nested_impl)

def _sibling_single_segment_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        "de",
        rust_bzl_internals.sibling_mod_path("cst", "de"),
        "a single-segment cst path yields the bare module name",
    )
    return unittest.end(env)

sibling_single_segment_test = unittest.make(_sibling_single_segment_impl)

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

# Defense-in-depth for the serde → ast_config coupling: the public macro's
# loading-time check fires first, so only direct instantiation of the internal
# rule reaches this analysis-time guard.

def _serde_config_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _SERDE_NEEDS_CONFIG_MSG)
    return analysistest.end(env)

serde_config_analysis_test = analysistest.make(
    _serde_config_analysis_impl,
    expect_failure = True,
)

# ---- Analysis tests: what the codegen actions are actually invoked with ----------
#
# The rule attrs reach the generators only through action argv. A dropped forwarding
# is invisible to every build target: each generator falls back to its own default,
# still generates, still compiles. These tests read the argv instead.

def _argv_of_output(env, basename):
    """The argv of the target's action producing a file named `basename`, or None."""
    for action in analysistest.target_actions(env):
        for out in action.outputs.to_list():
            if out.basename == basename:
                return action.argv
    return None

def _flag_value(argv, flag):
    """The token following `flag` in argv, or None when the flag is absent."""
    for i in range(len(argv) - 1):
        if argv[i] == flag:
            return argv[i + 1]
    return None

_ARGV_GOAL = "nest_sum"

def _codegen_argv_impl(ctx):
    env = analysistest.begin(ctx)
    ast_argv = _argv_of_output(env, "ast.rs")
    de_argv = _argv_of_output(env, "de.rs")
    asserts.true(env, ast_argv != None, "ast = True must run a gen-rust-ast action producing ast.rs")
    asserts.true(env, de_argv != None, "serde = True must run a gen-rust-serde action producing de.rs")

    if ast_argv != None:
        asserts.equals(env, _ARGV_GOAL, _flag_value(ast_argv, "--goal"), "goal must reach gen-rust-ast")
        asserts.equals(env, "super::cst", _flag_value(ast_argv, "--cst-mod-path"), "cst_mod_path must reach gen-rust-ast")
        asserts.equals(
            env,
            "super::parser",
            _flag_value(ast_argv, "--parser-mod-path"),
            "gen-rust-ast must name the parser derived by sibling_mod_path",
        )
        asserts.true(
            env,
            (_flag_value(ast_argv, "--ast-config") or "").endswith(".fltkast"),
            "the sidecar must reach gen-rust-ast: %s" % ast_argv,
        )

    if de_argv != None:
        asserts.equals(env, _ARGV_GOAL, _flag_value(de_argv, "--goal"), "goal must reach gen-rust-serde")
        asserts.equals(env, "super::cst", _flag_value(de_argv, "--cst-mod-path"), "cst_mod_path must reach gen-rust-serde")
        asserts.equals(
            env,
            "super::parser",
            _flag_value(de_argv, "--parser-mod-path"),
            "gen-rust-serde must name the parser derived by sibling_mod_path",
        )
        asserts.equals(
            env,
            "super::ast",
            _flag_value(de_argv, "--ast-mod-path"),
            "with ast = True, gen-rust-serde must name the ast module derived by sibling_mod_path",
        )
        asserts.true(
            env,
            (_flag_value(de_argv, "--ast-config") or "").endswith(".fltkast"),
            "the sidecar must reach gen-rust-serde: %s" % de_argv,
        )
    return analysistest.end(env)

codegen_argv_test = analysistest.make(_codegen_argv_impl)

def _plain_modules_argv_impl(ctx):
    env = analysistest.begin(ctx)
    argv = _argv_of_output(env, "lib.rs")
    asserts.true(env, argv != None, "the target under test must run a gen-rust-lib action")
    if argv != None:
        for mod_name in ctx.attr.expected_plain_modules:
            asserts.true(
                env,
                _plain_module_declared(argv, mod_name),
                "expected `--plain-module %s` in %s" % (mod_name, argv),
            )
        for mod_name in ctx.attr.forbidden_plain_modules:
            asserts.false(
                env,
                _plain_module_declared(argv, mod_name),
                "unexpected `--plain-module %s` in %s" % (mod_name, argv),
            )
    return analysistest.end(env)

def _plain_module_declared(argv, mod_name):
    """True when argv carries `--plain-module <mod_name>` (the flag is repeatable)."""
    for i in range(len(argv) - 1):
        if argv[i] == "--plain-module" and argv[i + 1] == mod_name:
            return True
    return False

plain_modules_argv_test = analysistest.make(
    _plain_modules_argv_impl,
    attrs = {
        "expected_plain_modules": attr.string_list(
            doc = "Module names that must be declared as --plain-module on the gen-rust-lib action.",
        ),
        "forbidden_plain_modules": attr.string_list(
            doc = "Module names that must NOT be declared (the serde-only / ast-only shapes).",
        ),
    },
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
        codegen_serde_without_config_test,
        codegen_config_without_consumer_test,
        codegen_ast_without_config_test,
        codegen_off_test,
        codegen_both_with_config_test,
        codegen_serde_only_test,
        codegen_goal_without_consumer_test,
        codegen_goal_with_ast_test,
        plain_modules_for_test,
        sibling_default_test,
        sibling_nested_test,
        sibling_single_segment_test,
    )

    coupling_analysis_test(
        name = name + "_coupling_analysis_test",
        target_under_test = ":neg_protocol_without_module",
    )

    serde_config_analysis_test(
        name = name + "_serde_config_analysis_test",
        target_under_test = ":neg_serde_without_config",
    )

    codegen_argv_test(
        name = name + "_codegen_argv_test",
        target_under_test = ":argv_ast_serde_srcs",
    )

    plain_modules_argv_test(
        name = name + "_plain_modules_argv_test",
        target_under_test = ":argv_plain_modules_lib",
        expected_plain_modules = ["ast", "de"],
        forbidden_plain_modules = ["cst"],
    )

    native.test_suite(
        name = name,
        tests = [
            ":" + name + "_unit_tests",
            ":" + name + "_coupling_analysis_test",
            ":" + name + "_serde_config_analysis_test",
            ":" + name + "_codegen_argv_test",
            ":" + name + "_plain_modules_argv_test",
        ],
    )
