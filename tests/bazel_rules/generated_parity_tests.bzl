"""Unit coverage for `generated_parity`'s pairing function.

The rule's whole value is that it compares *every* pair it was given: while a module is both
Bazel-generated and committed, an unmatched path on either side means the gate is covering less
than it claims and must fail rather than skip.  `_pair_lines` is where that decision lives, and
nothing else can witness it — a rule that silently dropped a pair would still build green.
"""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//bzl:generated_parity.bzl", "generated_parity_internals")

def _file(short_path, root):
    """A stand-in for the two `File` fields `_pair_lines` reads."""
    return struct(short_path = short_path, path = root + "/" + short_path)

_GEN_ROOT = "bazel-out/k8-fastbuild/bin"
_SRC_ROOT = "."

def _matched_pairs_impl(ctx):
    env = unittest.begin(ctx)
    generated = [_file("fltk/fegen/regex_cst.py", _GEN_ROOT), _file("fltk/lsp/fltklsp_parser.py", _GEN_ROOT)]
    committed = [_file("fltk/lsp/fltklsp_parser.py", _SRC_ROOT), _file("fltk/fegen/regex_cst.py", _SRC_ROOT)]
    lines, violation = generated_parity_internals.pair_lines(generated, committed)

    asserts.equals(env, None, violation, "every generated file has its committed counterpart")
    asserts.equals(
        env,
        [
            _GEN_ROOT + "/fltk/fegen/regex_cst.py|./fltk/fegen/regex_cst.py",
            _GEN_ROOT + "/fltk/lsp/fltklsp_parser.py|./fltk/lsp/fltklsp_parser.py",
        ],
        lines,
        "pairing is by short_path, in generated order, one line per pair",
    )
    return unittest.end(env)

matched_pairs_test = unittest.make(_matched_pairs_impl)

def _unmatched_generated_impl(ctx):
    env = unittest.begin(ctx)
    generated = [_file("fltk/fegen/regex_cst.py", _GEN_ROOT)]
    _, violation = generated_parity_internals.pair_lines(generated, [])

    asserts.equals(
        env,
        "generated_parity: generated file fltk/fegen/regex_cst.py has no committed counterpart in `committed`.",
        violation,
        "a generated file the `committed` list does not name is unchecked, not fine",
    )
    return unittest.end(env)

unmatched_generated_test = unittest.make(_unmatched_generated_impl)

def _unmatched_committed_impl(ctx):
    env = unittest.begin(ctx)
    committed = [_file("fltk/unparse/toy_cst.py", _SRC_ROOT), _file("fltk/fegen/regex_cst.py", _SRC_ROOT)]
    _, violation = generated_parity_internals.pair_lines([], committed)

    asserts.equals(
        env,
        "generated_parity: committed files with no generated counterpart: " +
        "fltk/fegen/regex_cst.py, fltk/unparse/toy_cst.py.",
        violation,
        "a committed file whose generator target vanished is the drift the gate exists to catch",
    )
    return unittest.end(env)

unmatched_committed_test = unittest.make(_unmatched_committed_impl)

def generated_parity_test_suite(name):
    """Pairing-function unit tests for `generated_parity`."""
    unittest.suite(
        name + "_unit_tests",
        matched_pairs_test,
        unmatched_generated_test,
        unmatched_committed_test,
    )

    native.test_suite(
        name = name,
        tests = [":" + name + "_unit_tests"],
    )
