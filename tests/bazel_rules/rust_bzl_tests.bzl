"""Regression coverage for generate_rust_parser's misconfiguration guards.

The public Bazel macro protects downstream consumers with fourteen misconfiguration
conditions (six pure-Rust-mode python-extension-only knob checks, the
protocol/protocol_module coupling, the three ast/serde/ast_config/goal conditions,
the format_config/unparser coupling, and the three out_dir conditions). This suite pins
each condition and its exact user-facing message so a
future edit that disables a guard or reworks a message fails a test. It also pins
the cst_mod_path → sibling module-path derivation the generated ast.rs / de.rs name
each other through, the ast/serde → plain-module mapping, the out_dir → declared-output
layout, and — by reading action command lines — that the rule attrs actually reach the
generators.

Every condition fires at loading time (BUILD-file evaluation), so no target exists
for analysistest to wrap; their condition + message logic is extracted into pure
functions in rust.bzl and exercised here via skylib unittest. The guards that
are also enforced at analysis time (inside the internal _generate_rust_srcs rule
impl) are covered end-to-end with analysistest.

Loads test-only internals via rust_bzl_internals; downstream consumers must never
load that symbol.
"""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//:rust.bzl", "rust_bzl_internals")
load("//bzl:runtime_crate.bzl", "runtime_crate_internals")

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
_UNUSED_FORMAT_CONFIG_MSG = "generate_rust_parser: format_config requires unparser = True; nothing else reads it."

def _serde_without_config_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(ast = False, serde = True, has_ast_config = False)
    asserts.equals(env, _SERDE_NEEDS_CONFIG_MSG, msg, "serde = True without a sidecar must violate")
    return unittest.end(env)

codegen_serde_without_config_test = unittest.make(_serde_without_config_impl)

def _config_without_consumer_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(ast = False, serde = False, has_ast_config = True)
    asserts.equals(env, _UNUSED_CONFIG_MSG, msg, "a sidecar with neither ast nor serde must violate")
    return unittest.end(env)

codegen_config_without_consumer_test = unittest.make(_config_without_consumer_impl)

def _ast_without_config_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(ast = True, serde = False, has_ast_config = False)
    asserts.equals(env, None, msg, "ast = True without a sidecar is the grammar-derived mode, not a violation")
    return unittest.end(env)

codegen_ast_without_config_test = unittest.make(_ast_without_config_impl)

def _codegen_off_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(ast = False, serde = False, has_ast_config = False)
    asserts.equals(env, None, msg, "neither knob set and no sidecar is the default configuration")
    return unittest.end(env)

codegen_off_test = unittest.make(_codegen_off_impl)

def _codegen_both_with_config_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(ast = True, serde = True, has_ast_config = True)
    asserts.equals(env, None, msg, "ast + serde + sidecar is the full configuration")
    return unittest.end(env)

codegen_both_with_config_test = unittest.make(_codegen_both_with_config_impl)

def _codegen_serde_only_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(ast = False, serde = True, has_ast_config = True)
    asserts.equals(env, None, msg, "serde + sidecar without ast is the bring-your-own-structs mode")
    return unittest.end(env)

codegen_serde_only_test = unittest.make(_codegen_serde_only_impl)

def _codegen_goal_without_consumer_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(ast = False, serde = False, has_ast_config = False, goal = "config")
    asserts.equals(env, _UNUSED_GOAL_MSG, msg, "a goal with neither ast nor serde is read by nothing")
    return unittest.end(env)

codegen_goal_without_consumer_test = unittest.make(_codegen_goal_without_consumer_impl)

def _codegen_goal_with_ast_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(ast = True, serde = False, has_ast_config = False, goal = "config")
    asserts.equals(env, None, msg, "gen-rust-ast reads goal, so ast = True makes it legal")
    return unittest.end(env)

codegen_goal_with_ast_test = unittest.make(_codegen_goal_with_ast_impl)

# The unparser half of the same guard family: only the gen-rust-unparser action takes
# --format-config, so a format_config with unparser = False is read by nothing. The
# reverse (unparser without a spec) is the default-FormatterConfig mode and is legal.

def _codegen_format_config_without_unparser_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(
        ast = False,
        serde = False,
        has_ast_config = False,
        goal = "",
        unparser = False,
        has_format_config = True,
    )
    asserts.equals(
        env,
        _UNUSED_FORMAT_CONFIG_MSG,
        msg,
        "a format_config with unparser = False is read by nothing",
    )
    return unittest.end(env)

codegen_format_config_without_unparser_test = unittest.make(_codegen_format_config_without_unparser_impl)

def _codegen_unparser_without_format_config_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(
        ast = False,
        serde = False,
        has_ast_config = False,
        goal = "",
        unparser = True,
        has_format_config = False,
    )
    asserts.equals(env, None, msg, "unparser without a spec is the default-FormatterConfig mode")
    return unittest.end(env)

codegen_unparser_without_format_config_test = unittest.make(_codegen_unparser_without_format_config_impl)

def _codegen_unparser_with_format_config_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.codegen_mode_violation(
        ast = True,
        serde = False,
        has_ast_config = False,
        goal = "nest_sum",
        unparser = True,
        has_format_config = True,
    )
    asserts.equals(env, None, msg, "ast + unparser + a baked spec is the full unparser configuration")
    return unittest.end(env)

codegen_unparser_with_format_config_test = unittest.make(_codegen_unparser_with_format_config_impl)

# ---- Unit tests: _out_dir_violation and _generated_path --------------------------
#
# out_dir re-roots the generated files at a consumer-chosen package-relative directory so
# a pure-Rust consumer's rust_library can glob its own sources alongside them. Three ways
# to get it wrong, each with its own message: setting it in extension mode (where the crate
# assembly genrule owns the layout), an absolute path, and a path escaping the package.

_OUT_DIR_EXTENSION_MSG = "generate_rust_parser: out_dir is only valid with python_extension = False; in extension mode the assembled crate owns the layout."
_OUT_DIR_ABSOLUTE_MSG_TMPL = "generate_rust_parser: out_dir must be a package-relative directory; '{}' is absolute."
_OUT_DIR_ESCAPE_MSG_TMPL = "generate_rust_parser: out_dir must stay inside the package; '{}' escapes it via '..'."

def _out_dir_in_extension_mode_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.out_dir_violation("src", python_extension = True)
    asserts.equals(env, _OUT_DIR_EXTENSION_MSG, msg, "out_dir has no effect in extension mode")
    return unittest.end(env)

out_dir_in_extension_mode_test = unittest.make(_out_dir_in_extension_mode_impl)

def _out_dir_absolute_impl(ctx):
    env = unittest.begin(ctx)
    msg = rust_bzl_internals.out_dir_violation("/etc/src")
    asserts.equals(env, _OUT_DIR_ABSOLUTE_MSG_TMPL.format("/etc/src"), msg, "an absolute out_dir must violate")
    return unittest.end(env)

out_dir_absolute_test = unittest.make(_out_dir_absolute_impl)

def _out_dir_escape_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _OUT_DIR_ESCAPE_MSG_TMPL.format("../sibling"),
        rust_bzl_internals.out_dir_violation("../sibling"),
        "a leading .. must violate",
    )
    asserts.equals(
        env,
        _OUT_DIR_ESCAPE_MSG_TMPL.format("src/../../out"),
        rust_bzl_internals.out_dir_violation("src/../../out"),
        "an interior .. segment must violate too",
    )
    asserts.equals(
        env,
        None,
        rust_bzl_internals.out_dir_violation("src/..sneaky"),
        "a segment merely starting with dots is an ordinary directory name",
    )
    return unittest.end(env)

out_dir_escape_test = unittest.make(_out_dir_escape_impl)

def _out_dir_legal_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, None, rust_bzl_internals.out_dir_violation(""), "unset out_dir keeps the default layout")
    asserts.equals(env, None, rust_bzl_internals.out_dir_violation("src"), "a plain package-relative directory is legal")
    asserts.equals(env, None, rust_bzl_internals.out_dir_violation("src/grammar"), "a nested directory is legal")
    asserts.equals(
        env,
        None,
        rust_bzl_internals.out_dir_violation("", python_extension = True),
        "leaving out_dir unset is legal in extension mode",
    )
    return unittest.end(env)

out_dir_legal_test = unittest.make(_out_dir_legal_impl)

# The mode exclusion. python_extension is a macro concept, so the rule enforces it through
# the two attrs the macro sets in extension mode; without this the rule would accept both
# and emit .rs files under out_dir with the stub package elsewhere.

_OUT_DIR_MODE_MSG = "generate_rust_parser: out_dir is only valid in pure-Rust mode; it cannot be combined with extension_name or protocol_module."

def _out_dir_mode_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _OUT_DIR_MODE_MSG,
        rust_bzl_internals.out_dir_mode_violation("src", "myext", ""),
        "out_dir with extension_name must violate",
    )
    asserts.equals(
        env,
        _OUT_DIR_MODE_MSG,
        rust_bzl_internals.out_dir_mode_violation("src", "", "my.pkg.cst_protocol"),
        "out_dir with protocol_module must violate",
    )
    asserts.equals(
        env,
        None,
        rust_bzl_internals.out_dir_mode_violation("src", "", ""),
        "out_dir alone is the pure-Rust configuration",
    )
    asserts.equals(
        env,
        None,
        rust_bzl_internals.out_dir_mode_violation("", "myext", "my.pkg.cst_protocol"),
        "the extension attrs without out_dir are the extension-mode configuration",
    )
    return unittest.end(env)

out_dir_mode_test = unittest.make(_out_dir_mode_impl)

def _generated_path_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, "src/cst.rs", rust_bzl_internals.generated_path("src", "cst.rs"))
    asserts.equals(env, "src/grammar/cst.rs", rust_bzl_internals.generated_path("src/grammar", "cst.rs"))
    asserts.equals(
        env,
        "cst.rs",
        rust_bzl_internals.generated_path(".", "cst.rs"),
        "'.' is the package root, not a directory literally named '.'",
    )
    asserts.equals(
        env,
        "src/cst.rs",
        rust_bzl_internals.generated_path("src/", "cst.rs"),
        "a trailing slash must not double up",
    )
    asserts.equals(env, "cst.rs", rust_bzl_internals.generated_path("", "cst.rs"))
    return unittest.end(env)

generated_path_test = unittest.make(_generated_path_impl)

# ---- Unit tests: the runtime-crate flavor derivation -----------------------------
#
# fltk_runtime_library derives each :no_python target's deps from the bare fltk_deps
# labels, which is what makes a flavor divergence between the two libraries of a runtime
# crate unrepresentable. Nothing compiles differently when that derivation breaks: the
# :no_python target still builds, it just links the python flavor of its sibling crate.

_FLAVOR_LABEL_MSG_TMPL = ("fltk_runtime_library: fltk_deps take bare package labels (the macro derives " +
                          "the :no_python flavor); got '{}'.")

def _flavor_derivation_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        "//crates/fltk-cst-core:no_python",
        runtime_crate_internals.no_python_flavor("//crates/fltk-cst-core"),
        "a bare package label gains the :no_python flavor",
    )
    asserts.equals(
        env,
        None,
        runtime_crate_internals.flavor_label_violation("//crates/fltk-ast-core"),
        "a bare package label is what the macro asks for",
    )
    return unittest.end(env)

runtime_crate_flavor_test = unittest.make(_flavor_derivation_impl)

def _flavor_label_violation_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _FLAVOR_LABEL_MSG_TMPL.format("//crates/fltk-cst-core:no_python"),
        runtime_crate_internals.flavor_label_violation("//crates/fltk-cst-core:no_python"),
        "an already-flavored label would derive a target that does not exist",
    )
    asserts.equals(
        env,
        _FLAVOR_LABEL_MSG_TMPL.format("@fltk_crates//:pyo3"),
        runtime_crate_internals.flavor_label_violation("@fltk_crates//:pyo3"),
        "a hub label has no flavor to derive; it belongs in hub_deps",
    )
    return unittest.end(env)

runtime_crate_flavor_violation_test = unittest.make(_flavor_label_violation_impl)

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
    asserts.equals(env, "super::unparser", rust_bzl_internals.sibling_mod_path("super::cst", "unparser"))
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

# Same defense-in-depth shape for the format_config → unparser coupling.

def _format_config_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _UNUSED_FORMAT_CONFIG_MSG)
    return analysistest.end(env)

format_config_analysis_test = analysistest.make(
    _format_config_analysis_impl,
    expect_failure = True,
)

# The out_dir path shape is intrinsic to the rule (it decides where declare_file lands),
# so unlike the mode exclusion it is enforced at analysis time as well as by the macro.

def _out_dir_escape_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _OUT_DIR_ESCAPE_MSG_TMPL.format("../escapes"))
    return analysistest.end(env)

out_dir_escape_analysis_test = analysistest.make(
    _out_dir_escape_analysis_impl,
    expect_failure = True,
)

# The out_dir / extension-attrs exclusion has no loading-time shadow at all: the macro
# refuses out_dir in extension mode, but the rule is what would otherwise accept both and
# split the layout, so this analysis-time guard is the only enforcement of it.

def _out_dir_mode_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _OUT_DIR_MODE_MSG)
    return analysistest.end(env)

out_dir_mode_analysis_test = analysistest.make(
    _out_dir_mode_analysis_impl,
    expect_failure = True,
)

# ---- Analysis test: out_dir re-roots every declared output -----------------------
#
# The whole point of out_dir is that the generated files land at package-relative paths a
# consumer's rust_library can name; a partial re-rooting (one action's declare_file left on
# the old path) still builds the codegen target and only breaks the consumer's crate root.

def _out_dir_layout_impl(ctx):
    env = analysistest.begin(ctx)
    target = analysistest.target_under_test(env)
    paths = [f.short_path for f in target[DefaultInfo].files.to_list()]
    asserts.true(env, len(paths) > 0, "the target under test must declare outputs")
    expected_dir = "tests/bazel_rules/" + ctx.attr.expected_dir
    for p in paths:
        asserts.equals(
            env,
            expected_dir,
            p[:p.rindex("/")],
            "every generated file must be declared under out_dir: %s" % p,
        )
    for basename in ctx.attr.expected_basenames:
        asserts.true(
            env,
            expected_dir + "/" + basename in paths,
            "expected %s under out_dir; got %s" % (basename, paths),
        )
    return analysistest.end(env)

out_dir_layout_test = analysistest.make(
    _out_dir_layout_impl,
    attrs = {
        "expected_dir": attr.string(
            doc = "The package-relative directory every declared output must sit in.",
        ),
        "expected_basenames": attr.string_list(
            doc = "Basenames that must be present under that directory.",
        ),
    },
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

    asserts.true(
        env,
        _argv_of_output(env, "unparser.rs") == None,
        "unparser = False must run no gen-rust-unparser action",
    )
    if ast_argv != None:
        asserts.equals(
            env,
            None,
            _flag_value(ast_argv, "--unparser-mod-path"),
            "without unparser there is no unparser module for gen-rust-ast to name",
        )
    return analysistest.end(env)

codegen_argv_test = analysistest.make(_codegen_argv_impl)

# ---- Analysis test: the unparser action and what enabling it changes elsewhere ----
#
# Enabling unparser touches three action command lines: gen-rust-unparser (the new action),
# gen-rust-ast (--unparser-mod-path), and gen-rust-cst (--submodules). A drop in any of the
# three still builds — the generators fall back to their defaults — so argv is the witness.

def _unparser_argv_impl(ctx):
    env = analysistest.begin(ctx)
    unparser_argv = _argv_of_output(env, "unparser.rs")
    asserts.true(env, unparser_argv != None, "unparser = True must run a gen-rust-unparser action")

    if unparser_argv != None:
        asserts.equals(
            env,
            "super::cst",
            _flag_value(unparser_argv, "--cst-mod-path"),
            "cst_mod_path must reach gen-rust-unparser",
        )
        asserts.true(
            env,
            (_flag_value(unparser_argv, "--format-config") or "").endswith(".fltkfmt"),
            "the format spec must reach gen-rust-unparser: %s" % unparser_argv,
        )
        asserts.equals(
            env,
            "tests.dummy_cst_protocol",
            _flag_value(unparser_argv, "--protocol-module"),
            "protocol_module must reach gen-rust-unparser so the stub package gains unparser.pyi",
        )
        asserts.true(
            env,
            (_flag_value(unparser_argv, "--pyi-output") or "").endswith("/unparser.pyi"),
            "the unparser stub must be written into the stub package: %s" % unparser_argv,
        )

    ast_argv = _argv_of_output(env, "ast.rs")
    asserts.true(env, ast_argv != None, "the target under test sets ast = True")
    if ast_argv != None:
        asserts.equals(
            env,
            "super::unparser",
            _flag_value(ast_argv, "--unparser-mod-path"),
            "ast + unparser must name the unparser module derived by sibling_mod_path",
        )

    cst_argv = _argv_of_output(env, "cst.rs")
    asserts.true(env, cst_argv != None, "every codegen target runs a gen-rust-cst action")
    if cst_argv != None:
        asserts.equals(
            env,
            "cst,parser,unparser",
            _flag_value(cst_argv, "--submodules"),
            "the stub-package marker must list the unparser submodule",
        )

    # Declaring unparser.pyi is only half of it: the macro feeds the stub_srcs output group
    # to the py_library's data, so a stub left out of that group is absent from the consumer's
    # installed stub package while everything still builds and imports.
    target = analysistest.target_under_test(env)
    stub_paths = [f.short_path for f in target[OutputGroupInfo].stub_srcs.to_list()]
    default_paths = [f.short_path for f in target[DefaultInfo].files.to_list()]
    for expected in ["argv_unparser/unparser.pyi", "argv_unparser/cst.pyi", "argv_unparser/__init__.pyi"]:
        full = "tests/bazel_rules/" + expected
        asserts.true(env, full in stub_paths, "expected %s in stub_srcs; got %s" % (full, stub_paths))
        asserts.true(env, full in default_paths, "expected %s in DefaultInfo; got %s" % (full, default_paths))
    for path in stub_paths:
        asserts.true(
            env,
            not path.endswith(".rs"),
            "stub_srcs carries only the stub package, never generated Rust: %s" % path,
        )
    return analysistest.end(env)

unparser_argv_test = analysistest.make(_unparser_argv_impl)

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

# The unparser is a registered submodule (--unparser, not --plain-module). Same invisibility
# as the plain modules: an undeclared unparser.rs is simply not compiled and rustc says nothing.

def _lib_unparser_argv_impl(ctx):
    env = analysistest.begin(ctx)
    argv = _argv_of_output(env, "lib.rs")
    asserts.true(env, argv != None, "the target under test must run a gen-rust-lib action")
    if argv != None:
        asserts.equals(
            env,
            ctx.attr.expect_unparser,
            "--unparser" in argv,
            "gen-rust-lib --unparser presence must track the rule's unparser attr: %s" % argv,
        )
    return analysistest.end(env)

lib_unparser_argv_test = analysistest.make(
    _lib_unparser_argv_impl,
    attrs = {
        "expect_unparser": attr.bool(
            doc = "Whether the gen-rust-lib action is expected to carry --unparser.",
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
        codegen_format_config_without_unparser_test,
        codegen_unparser_without_format_config_test,
        codegen_unparser_with_format_config_test,
        out_dir_in_extension_mode_test,
        out_dir_absolute_test,
        out_dir_escape_test,
        out_dir_legal_test,
        out_dir_mode_test,
        generated_path_test,
        runtime_crate_flavor_test,
        runtime_crate_flavor_violation_test,
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

    format_config_analysis_test(
        name = name + "_format_config_analysis_test",
        target_under_test = ":neg_format_config_without_unparser",
    )

    out_dir_escape_analysis_test(
        name = name + "_out_dir_escape_analysis_test",
        target_under_test = ":neg_out_dir_escape",
    )

    out_dir_mode_analysis_test(
        name = name + "_out_dir_mode_analysis_test",
        target_under_test = ":neg_out_dir_with_extension_name",
    )

    out_dir_layout_test(
        name = name + "_out_dir_layout_test",
        target_under_test = ":out_dir_srcs",
        expected_basenames = [
            "ast.rs",
            "cst.rs",
            "de.rs",
            "parser.rs",
            "unparser.rs",
        ],
        expected_dir = "gensrc/grammar",
    )

    codegen_argv_test(
        name = name + "_codegen_argv_test",
        target_under_test = ":argv_ast_serde_srcs",
    )

    unparser_argv_test(
        name = name + "_unparser_argv_test",
        target_under_test = ":argv_unparser_srcs",
    )

    plain_modules_argv_test(
        name = name + "_plain_modules_argv_test",
        target_under_test = ":argv_plain_modules_lib",
        expected_plain_modules = ["ast", "de"],
        forbidden_plain_modules = ["cst"],
    )

    lib_unparser_argv_test(
        name = name + "_lib_unparser_argv_test",
        target_under_test = ":argv_unparser_lib",
        expect_unparser = True,
    )

    lib_unparser_argv_test(
        name = name + "_lib_no_unparser_argv_test",
        target_under_test = ":argv_plain_modules_lib",
        expect_unparser = False,
    )

    native.test_suite(
        name = name,
        tests = [
            ":" + name + "_unit_tests",
            ":" + name + "_coupling_analysis_test",
            ":" + name + "_serde_config_analysis_test",
            ":" + name + "_format_config_analysis_test",
            ":" + name + "_out_dir_escape_analysis_test",
            ":" + name + "_out_dir_mode_analysis_test",
            ":" + name + "_out_dir_layout_test",
            ":" + name + "_codegen_argv_test",
            ":" + name + "_unparser_argv_test",
            ":" + name + "_plain_modules_argv_test",
            ":" + name + "_lib_unparser_argv_test",
            ":" + name + "_lib_no_unparser_argv_test",
        ],
    )
