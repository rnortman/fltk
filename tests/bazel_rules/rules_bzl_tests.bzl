"""Regression coverage for generate_parser's guards, output layout and argv.

The Python-backend codegen rule has three kinds of behavior nothing else can witness:

- the misconfiguration guards (cst_mod_path/base_name coupling, out_dir path shape, the
  two selector exclusions), whose messages are the only thing a caller sees;
- which files it declares under which directory, since a missed `out_dir` on one output
  still builds the codegen target and only breaks whatever consumes the modules; and
- what the generator is actually invoked with — a dropped flag makes the generator fall
  back to its own default, still generate, and still compile.

Loads test-only internals via rules_bzl_internals; downstream consumers must never load
that symbol.
"""

load("@bazel_skylib//lib:unittest.bzl", "analysistest", "asserts", "unittest")
load("//:rules.bzl", "rules_bzl_internals")

_OUT_DIR_ABSOLUTE_MSG_TMPL = "generate_parser: out_dir must be a package-relative directory; '{}' is absolute."
_OUT_DIR_ESCAPE_MSG_TMPL = "generate_parser: out_dir must stay inside the package; '{}' escapes it via '..'."
_PROTOCOL_ONLY_MSG = ("generate_parser: protocol_only emits no parsers, so it cannot be combined with " +
                      "trivia_only or no_trivia_only.")
_TRIVIA_SELECTOR_MSG = "generate_parser: trivia_only and no_trivia_only are mutually exclusive."
_FORMAT_CONFIG_MSG = "generate_parser: format_config requires unparser = True; nothing else reads it."
_UNPARSER_PROTOCOL_ONLY_MSG = ("generate_parser: protocol_only emits only the protocol module, so it cannot be " +
                               "combined with unparser.")
_UNPARSER_GEN_TOOL_MSG = (
    "generate_parser: unparser = True needs the full generator; '{}' has the ".format(
        rules_bzl_internals.stage0_label,
    ) + "`generate` command only. Drop gen_tool to use the default //:genparser."
)

# ---- Unit tests ------------------------------------------------------------------

def _out_dir_absolute_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _OUT_DIR_ABSOLUTE_MSG_TMPL.format("/etc"),
        rules_bzl_internals.out_dir_violation("/etc"),
        "declare_file can only name files inside the package",
    )
    return unittest.end(env)

out_dir_absolute_test = unittest.make(_out_dir_absolute_impl)

def _out_dir_escape_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _OUT_DIR_ESCAPE_MSG_TMPL.format("../elsewhere"),
        rules_bzl_internals.out_dir_violation("../elsewhere"),
        "a '..' segment escapes the package just as an absolute path does",
    )
    asserts.equals(
        env,
        _OUT_DIR_ESCAPE_MSG_TMPL.format("fltk/../../out"),
        rules_bzl_internals.out_dir_violation("fltk/../../out"),
        "a '..' anywhere in the path counts, not only in the first segment",
    )
    return unittest.end(env)

out_dir_escape_test = unittest.make(_out_dir_escape_impl)

def _out_dir_legal_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, None, rules_bzl_internals.out_dir_violation(""), "empty is the default")
    asserts.equals(env, None, rules_bzl_internals.out_dir_violation("fltk/fegen"))
    asserts.equals(
        env,
        None,
        rules_bzl_internals.out_dir_violation("gen..erated"),
        "'..' inside a segment name is not a parent-directory hop",
    )
    return unittest.end(env)

out_dir_legal_test = unittest.make(_out_dir_legal_impl)

def _protocol_only_violation_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _PROTOCOL_ONLY_MSG,
        rules_bzl_internals.protocol_only_violation(True, True, False),
        "protocol_only with trivia_only selects among parsers it emits none of",
    )
    asserts.equals(
        env,
        _PROTOCOL_ONLY_MSG,
        rules_bzl_internals.protocol_only_violation(True, False, True),
        "same for no_trivia_only",
    )
    return unittest.end(env)

protocol_only_violation_test = unittest.make(_protocol_only_violation_impl)

def _protocol_only_legal_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        None,
        rules_bzl_internals.protocol_only_violation(True, False, False),
        "protocol_only on its own is the supported protocol-surface-only mode",
    )
    asserts.equals(
        env,
        None,
        rules_bzl_internals.protocol_only_violation(False, True, False),
        "a selector without protocol_only is the ordinary single-parser mode",
    )
    return unittest.end(env)

protocol_only_legal_test = unittest.make(_protocol_only_legal_impl)

def _trivia_selector_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _TRIVIA_SELECTOR_MSG,
        rules_bzl_internals.trivia_selector_violation(True, True),
        "both selectors together would ask for exactly no parser",
    )
    asserts.equals(env, None, rules_bzl_internals.trivia_selector_violation(True, False))
    asserts.equals(env, None, rules_bzl_internals.trivia_selector_violation(False, False))
    return unittest.end(env)

trivia_selector_test = unittest.make(_trivia_selector_impl)

def _format_config_violation_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _FORMAT_CONFIG_MSG,
        rules_bzl_internals.format_config_violation(True, False),
        "only the unparser action reads a format_config",
    )
    asserts.equals(
        env,
        None,
        rules_bzl_internals.format_config_violation(True, True),
        "a format_config with an unparser is the baked-spec mode",
    )
    asserts.equals(
        env,
        None,
        rules_bzl_internals.format_config_violation(False, True),
        "an unparser without a format_config takes the default FormatterConfig",
    )
    return unittest.end(env)

format_config_violation_test = unittest.make(_format_config_violation_impl)

def _unparser_protocol_only_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _UNPARSER_PROTOCOL_ONLY_MSG,
        rules_bzl_internals.unparser_protocol_only_violation(True, True),
        "the generated unparser imports the CST module protocol_only does not emit",
    )
    asserts.equals(env, None, rules_bzl_internals.unparser_protocol_only_violation(True, False))
    asserts.equals(env, None, rules_bzl_internals.unparser_protocol_only_violation(False, True))
    return unittest.end(env)

unparser_protocol_only_test = unittest.make(_unparser_protocol_only_impl)

def _unparser_gen_tool_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        _UNPARSER_GEN_TOOL_MSG,
        rules_bzl_internals.unparser_gen_tool_violation(True, rules_bzl_internals.stage0_label),
        "the stage-0 generator has no gen-py-unparser subcommand",
    )
    asserts.equals(
        env,
        None,
        rules_bzl_internals.unparser_gen_tool_violation(False, rules_bzl_internals.stage0_label),
        "stage-0 is the right tool for everything except an unparser",
    )
    asserts.equals(
        env,
        None,
        rules_bzl_internals.unparser_gen_tool_violation(True, Label("//:genparser")),
        "the full generator is what unparser = True needs",
    )
    return unittest.end(env)

unparser_gen_tool_test = unittest.make(_unparser_gen_tool_impl)

def _cst_mod_path_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        None,
        rules_bzl_internals.cst_mod_path_violation("mylang_cst", "mylang"),
        "the flat in-package name",
    )
    asserts.equals(
        env,
        None,
        rules_bzl_internals.cst_mod_path_violation("fltk.fegen.regex_cst", "regex"),
        "a dotted prefix is the consumer's import root and is not this rule's business",
    )
    asserts.true(
        env,
        rules_bzl_internals.cst_mod_path_violation("mylang.cst", "mylang") != None,
        "a last component that is not <base_name>_cst breaks the baked NodeKind import",
    )
    return unittest.end(env)

cst_mod_path_test = unittest.make(_cst_mod_path_impl)

def _generated_path_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(env, "a_cst.py", rules_bzl_internals.generated_path("", "a_cst.py"))
    asserts.equals(env, "a_cst.py", rules_bzl_internals.generated_path(".", "a_cst.py"))
    asserts.equals(env, "fltk/fegen/a_cst.py", rules_bzl_internals.generated_path("fltk/fegen", "a_cst.py"))
    asserts.equals(
        env,
        "fltk/fegen/a_cst.py",
        rules_bzl_internals.generated_path("fltk/fegen/", "a_cst.py"),
        "a trailing slash is absorbed rather than doubled",
    )
    return unittest.end(env)

generated_path_test = unittest.make(_generated_path_impl)

# ---- Analysis tests --------------------------------------------------------------

def _out_dir_escape_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _OUT_DIR_ESCAPE_MSG_TMPL.format("../escapes"))
    return analysistest.end(env)

out_dir_escape_analysis_test = analysistest.make(
    _out_dir_escape_analysis_impl,
    expect_failure = True,
)

def _protocol_only_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _PROTOCOL_ONLY_MSG)
    return analysistest.end(env)

protocol_only_analysis_test = analysistest.make(
    _protocol_only_analysis_impl,
    expect_failure = True,
)

def _declared_layout_impl(ctx):
    env = analysistest.begin(ctx)
    target = analysistest.target_under_test(env)
    paths = [f.short_path for f in target[DefaultInfo].files.to_list()]
    prefix = "tests/bazel_rules/"
    if ctx.attr.expected_dir:
        prefix += ctx.attr.expected_dir + "/"
    asserts.equals(
        env,
        sorted([prefix + basename for basename in ctx.attr.expected_files]),
        sorted(paths),
        "declared outputs must be exactly the expected set, at the expected paths",
    )
    return analysistest.end(env)

declared_layout_test = analysistest.make(
    _declared_layout_impl,
    attrs = {
        "expected_dir": attr.string(
            doc = "Package-relative directory the outputs must sit in; empty means the package root.",
        ),
        "expected_files": attr.string_list(
            doc = "The exact basenames the rule must declare.",
        ),
    },
)

def _generate_argv(env):
    """The argv of the target's single `generate` action."""
    for action in analysistest.target_actions(env):
        if "generate" in action.argv:
            return action.argv
    return None

def _flag_value(argv, flag):
    for i in range(len(argv) - 1):
        if argv[i] == flag:
            return argv[i + 1]
    return None

def _action_with(env, subcommand):
    """The action whose argv carries `subcommand`, or None."""
    for action in analysistest.target_actions(env):
        if subcommand in action.argv:
            return action
    return None

def _input_basenames(action):
    return [f.basename for f in action.inputs.to_list()]

def _argv_impl(ctx):
    env = analysistest.begin(ctx)
    action = _action_with(env, "generate")
    asserts.true(env, action != None, "no action with a `generate` subcommand was registered")
    argv = action.argv

    # The grammar must be a declared input, not merely a path on the command line: with the two
    # independently editable, a lost input means editing the .fltkg stops invalidating the action
    # and the modules silently stay stale.
    asserts.true(
        env,
        "dummy.fltkg" in _input_basenames(action),
        "the grammar must be among the action's inputs; got %s" % _input_basenames(action),
    )

    asserts.true(env, "dummy.fltkg" in argv[argv.index("generate") + 1], "the grammar is the first positional")
    asserts.equals(env, ctx.attr.expected_base_name, argv[argv.index("generate") + 2])
    asserts.equals(env, ctx.attr.expected_cst_mod_path, argv[argv.index("generate") + 3])

    output_dir = _flag_value(argv, "--output-dir")
    asserts.true(env, output_dir != None, "--output-dir must always be passed")
    asserts.true(
        env,
        output_dir.endswith(ctx.attr.expected_output_dir_suffix),
        "--output-dir %s must end with %s" % (output_dir, ctx.attr.expected_output_dir_suffix),
    )

    for flag in ctx.attr.expected_flags:
        asserts.true(env, flag in argv, "expected %s in argv; got %s" % (flag, argv))
    for flag in ctx.attr.forbidden_flags:
        asserts.false(env, flag in argv, "%s must not be in argv; got %s" % (flag, argv))
    return analysistest.end(env)

argv_test = analysistest.make(
    _argv_impl,
    attrs = {
        "expected_base_name": attr.string(),
        "expected_cst_mod_path": attr.string(),
        "expected_flags": attr.string_list(),
        "expected_output_dir_suffix": attr.string(),
        "forbidden_flags": attr.string_list(),
    },
)

def _unparser_argv_impl(ctx):
    env = analysistest.begin(ctx)
    action = _action_with(env, "gen-py-unparser")
    asserts.true(env, action != None, "no action with a `gen-py-unparser` subcommand was registered")
    argv = action.argv
    inputs = _input_basenames(action)

    asserts.true(
        env,
        "dummy.fltkg" in inputs,
        "the grammar must be among the unparser action's inputs; got %s" % inputs,
    )

    head = argv.index("gen-py-unparser")
    asserts.true(env, "dummy.fltkg" in argv[head + 1], "the grammar is the first positional")
    asserts.equals(env, ctx.attr.expected_base_name, argv[head + 2])
    asserts.equals(env, ctx.attr.expected_cst_mod_path, argv[head + 3])

    output_dir = _flag_value(argv, "--output-dir")
    asserts.true(env, output_dir != None, "--output-dir must always be passed")
    asserts.true(
        env,
        output_dir.endswith(ctx.attr.expected_output_dir_suffix),
        "--output-dir %s must end with %s" % (output_dir, ctx.attr.expected_output_dir_suffix),
    )

    format_config = _flag_value(argv, "--format-config")
    fltkfmt_inputs = [name for name in inputs if name.endswith(".fltkfmt")]
    if ctx.attr.expected_format_config_suffix:
        asserts.true(env, format_config != None, "--format-config must be passed when the attr is set")
        asserts.true(
            env,
            format_config.endswith(ctx.attr.expected_format_config_suffix),
            "--format-config %s must end with %s" % (format_config, ctx.attr.expected_format_config_suffix),
        )

        # Argv and input set are independently editable: with the spec named on the command line
        # but missing from the inputs, the build still succeeds in-repo and editing the .fltkfmt
        # no longer invalidates the action — consumers ship unparsers built from a stale spec.
        asserts.true(
            env,
            [name for name in fltkfmt_inputs if name.endswith(ctx.attr.expected_format_config_suffix)] != [],
            "the format_config must be among the action's inputs; got %s" % inputs,
        )
    else:
        asserts.equals(env, None, format_config, "--format-config must be absent when the attr is unset")
        asserts.equals(env, [], fltkfmt_inputs, "no .fltkfmt may be an input when the attr is unset")
    return analysistest.end(env)

unparser_argv_test = analysistest.make(
    _unparser_argv_impl,
    attrs = {
        "expected_base_name": attr.string(),
        "expected_cst_mod_path": attr.string(),
        "expected_format_config_suffix": attr.string(),
        "expected_output_dir_suffix": attr.string(),
    },
)

def _format_config_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _FORMAT_CONFIG_MSG)
    return analysistest.end(env)

format_config_analysis_test = analysistest.make(
    _format_config_analysis_impl,
    expect_failure = True,
)

def _unparser_protocol_only_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _UNPARSER_PROTOCOL_ONLY_MSG)
    return analysistest.end(env)

unparser_protocol_only_analysis_test = analysistest.make(
    _unparser_protocol_only_analysis_impl,
    expect_failure = True,
)

def _unparser_gen_tool_analysis_impl(ctx):
    env = analysistest.begin(ctx)
    asserts.expect_failure(env, _UNPARSER_GEN_TOOL_MSG)
    return analysistest.end(env)

unparser_gen_tool_analysis_test = analysistest.make(
    _unparser_gen_tool_analysis_impl,
    expect_failure = True,
)

def _gen_tool_impl(ctx):
    env = analysistest.begin(ctx)
    argv = _generate_argv(env)
    asserts.true(env, argv != None, "no action with a `generate` subcommand was registered")
    asserts.true(
        env,
        argv[0].endswith(ctx.attr.expected_tool_suffix),
        "action executable %s must be the %s binary" % (argv[0], ctx.attr.expected_tool_suffix),
    )
    return analysistest.end(env)

gen_tool_test = analysistest.make(
    _gen_tool_impl,
    attrs = {"expected_tool_suffix": attr.string()},
)

# ---- Suite -----------------------------------------------------------------------

def rules_bzl_test_suite(name):
    """Instantiate every unit test, the analysis tests, and a wrapping test_suite."""
    unittest.suite(
        name + "_unit_tests",
        out_dir_absolute_test,
        out_dir_escape_test,
        out_dir_legal_test,
        protocol_only_violation_test,
        protocol_only_legal_test,
        trivia_selector_test,
        format_config_violation_test,
        unparser_protocol_only_test,
        unparser_gen_tool_test,
        cst_mod_path_test,
        generated_path_test,
    )

    format_config_analysis_test(
        name = name + "_format_config_analysis_test",
        target_under_test = ":py_neg_format_config_without_unparser",
    )

    unparser_protocol_only_analysis_test(
        name = name + "_unparser_protocol_only_analysis_test",
        target_under_test = ":py_neg_unparser_with_protocol_only",
    )

    unparser_gen_tool_analysis_test(
        name = name + "_unparser_gen_tool_analysis_test",
        target_under_test = ":py_neg_unparser_with_stage0",
    )

    declared_layout_test(
        name = name + "_unparser_layout_test",
        target_under_test = ":py_unparser_srcs",
        expected_files = [
            "pyunparser_cst.py",
            "pyunparser_cst_protocol.py",
            "pyunparser_parser.py",
            "pyunparser_trivia_parser.py",
            "pyunparser_unparser.py",
        ],
    )

    declared_layout_test(
        name = name + "_unparser_out_dir_layout_test",
        target_under_test = ":py_unparser_out_dir_srcs",
        expected_dir = "gensrc/unp",
        expected_files = [
            "pyunpout_cst.py",
            "pyunpout_cst_protocol.py",
            "pyunpout_parser.py",
            "pyunpout_trivia_parser.py",
            "pyunpout_unparser.py",
        ],
    )

    unparser_argv_test(
        name = name + "_unparser_argv_test",
        target_under_test = ":py_unparser_srcs",
        expected_base_name = "pyunparser",
        expected_cst_mod_path = "pyunparser_cst",
        expected_format_config_suffix = "dummy.fltkfmt",
        expected_output_dir_suffix = "tests/bazel_rules",
    )

    unparser_argv_test(
        name = name + "_unparser_no_format_config_argv_test",
        target_under_test = ":py_unparser_out_dir_srcs",
        expected_base_name = "pyunpout",
        expected_cst_mod_path = "pyunpout_cst",
        expected_output_dir_suffix = "tests/bazel_rules/gensrc/unp",
    )

    out_dir_escape_analysis_test(
        name = name + "_out_dir_escape_analysis_test",
        target_under_test = ":py_neg_out_dir_escape",
    )

    protocol_only_analysis_test(
        name = name + "_protocol_only_analysis_test",
        target_under_test = ":py_neg_protocol_only_with_selector",
    )

    declared_layout_test(
        name = name + "_default_layout_test",
        target_under_test = ":py_default_srcs",
        expected_files = [
            "pydefault_cst.py",
            "pydefault_cst_protocol.py",
            "pydefault_parser.py",
            "pydefault_trivia_parser.py",
        ],
    )

    declared_layout_test(
        name = name + "_out_dir_layout_test",
        target_under_test = ":py_out_dir_srcs",
        expected_dir = "gensrc/pkg",
        expected_files = [
            "pyoutdir_cst.py",
            "pyoutdir_cst_protocol.py",
            "pyoutdir_parser.py",
            "pyoutdir_trivia_parser.py",
        ],
    )

    declared_layout_test(
        name = name + "_protocol_only_layout_test",
        target_under_test = ":py_protocol_only_srcs",
        expected_files = ["pyproto_cst_protocol.py"],
    )

    declared_layout_test(
        name = name + "_trivia_only_layout_test",
        target_under_test = ":py_trivia_only_srcs",
        expected_files = [
            "pytrivia_cst.py",
            "pytrivia_cst_protocol.py",
            "pytrivia_trivia_parser.py",
        ],
    )

    argv_test(
        name = name + "_default_argv_test",
        target_under_test = ":py_default_srcs",
        expected_base_name = "pydefault",
        expected_cst_mod_path = "pydefault_cst",
        expected_output_dir_suffix = "tests/bazel_rules",
        forbidden_flags = [
            "--protocol-only",
            "--trivia-only",
            "--no-trivia-only",
        ],
    )

    argv_test(
        name = name + "_out_dir_argv_test",
        target_under_test = ":py_out_dir_srcs",
        expected_base_name = "pyoutdir",
        expected_cst_mod_path = "pyoutdir_cst",
        expected_output_dir_suffix = "tests/bazel_rules/gensrc/pkg",
    )

    argv_test(
        name = name + "_protocol_only_argv_test",
        target_under_test = ":py_protocol_only_srcs",
        expected_base_name = "pyproto",
        expected_cst_mod_path = "pyproto_cst",
        expected_flags = ["--protocol-only"],
        expected_output_dir_suffix = "tests/bazel_rules",
    )

    declared_layout_test(
        name = name + "_no_trivia_only_layout_test",
        target_under_test = ":py_no_trivia_only_srcs",
        expected_files = [
            "pynotrivia_cst.py",
            "pynotrivia_cst_protocol.py",
            "pynotrivia_parser.py",
        ],
    )

    argv_test(
        name = name + "_no_trivia_only_argv_test",
        target_under_test = ":py_no_trivia_only_srcs",
        expected_base_name = "pynotrivia",
        expected_cst_mod_path = "pynotrivia_cst",
        expected_flags = ["--no-trivia-only"],
        expected_output_dir_suffix = "tests/bazel_rules",
        forbidden_flags = ["--trivia-only"],
    )

    argv_test(
        name = name + "_trivia_only_argv_test",
        target_under_test = ":py_trivia_only_srcs",
        expected_base_name = "pytrivia",
        expected_cst_mod_path = "pytrivia_cst",
        expected_flags = ["--trivia-only"],
        expected_output_dir_suffix = "tests/bazel_rules",
        forbidden_flags = ["--no-trivia-only"],
    )

    gen_tool_test(
        name = name + "_default_gen_tool_test",
        target_under_test = ":py_default_srcs",
        expected_tool_suffix = "genparser",
    )

    gen_tool_test(
        name = name + "_stage0_gen_tool_test",
        target_under_test = ":py_stage0_srcs",
        expected_tool_suffix = "genparser_stage0",
    )

    native.test_suite(
        name = name,
        tests = [
            ":" + name + "_unit_tests",
            ":" + name + "_out_dir_escape_analysis_test",
            ":" + name + "_protocol_only_analysis_test",
            ":" + name + "_default_layout_test",
            ":" + name + "_out_dir_layout_test",
            ":" + name + "_protocol_only_layout_test",
            ":" + name + "_trivia_only_layout_test",
            ":" + name + "_no_trivia_only_layout_test",
            ":" + name + "_default_argv_test",
            ":" + name + "_out_dir_argv_test",
            ":" + name + "_protocol_only_argv_test",
            ":" + name + "_trivia_only_argv_test",
            ":" + name + "_no_trivia_only_argv_test",
            ":" + name + "_default_gen_tool_test",
            ":" + name + "_stage0_gen_tool_test",
            ":" + name + "_format_config_analysis_test",
            ":" + name + "_unparser_protocol_only_analysis_test",
            ":" + name + "_unparser_gen_tool_analysis_test",
            ":" + name + "_unparser_layout_test",
            ":" + name + "_unparser_out_dir_layout_test",
            ":" + name + "_unparser_argv_test",
            ":" + name + "_unparser_no_format_config_argv_test",
        ],
    )
