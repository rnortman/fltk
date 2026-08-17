"""Unit coverage for `fltk_py_tests`' inventory check.

The declared dict is what makes a per-file py_test the unit of caching, and also what makes a
dropped file silently uncovered — a test that runs nowhere is green everywhere.  The check that
closes that hole is one pure function over three sets, and no build result can witness it: a
package missing a target builds perfectly well.  Hence its own unit tests.
"""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//bzl:py_test.bzl", "py_test_internals")

def _accounted_impl(ctx):
    env = unittest.begin(ctx)
    violation = py_test_internals.inventory_violation(
        ["test_a.py", "test_b.py"],
        ["test_c.py"],
        ["test_c.py", "test_a.py", "test_b.py"],
    )
    asserts.equals(env, None, violation, "declared plus deferred covering the glob exactly is the green case")
    return unittest.end(env)

accounted_test = unittest.make(_accounted_impl)

def _unaccounted_impl(ctx):
    env = unittest.begin(ctx)
    violation = py_test_internals.inventory_violation(
        ["test_a.py"],
        [],
        ["test_a.py", "test_new.py", "test_newer.py"],
    )
    asserts.equals(
        env,
        "fltk_py_tests: pytest files with no target and no deferral: test_new.py, test_newer.py. " +
        "Add each to the tests dict, or to `deferred` with the reason it cannot run in the sandbox.",
        violation,
        "a new test file that nothing declares runs nowhere",
    )
    return unittest.end(env)

unaccounted_test = unittest.make(_unaccounted_impl)

def _missing_file_impl(ctx):
    env = unittest.begin(ctx)
    violation = py_test_internals.inventory_violation(
        ["test_a.py", "test_gone.py"],
        ["test_also_gone.py"],
        ["test_a.py"],
    )
    asserts.equals(
        env,
        "fltk_py_tests: declared or deferred files that do not exist: test_also_gone.py, test_gone.py.",
        violation,
        "a target naming a deleted file, or a deferral outliving its file, is caught on both sides",
    )
    return unittest.end(env)

missing_file_test = unittest.make(_missing_file_impl)

def _double_counted_impl(ctx):
    env = unittest.begin(ctx)
    violation = py_test_internals.inventory_violation(
        ["test_a.py"],
        ["test_a.py"],
        ["test_a.py"],
    )
    asserts.equals(
        env,
        "fltk_py_tests: declared and deferred name the same files: test_a.py.",
        violation,
        "a file with a target reads as uncovered while its deferral stands",
    )
    return unittest.end(env)

double_counted_test = unittest.make(_double_counted_impl)

def _target_name_impl(ctx):
    env = unittest.begin(ctx)
    asserts.equals(
        env,
        "fltk_lsp_test_server",
        py_test_internals.target_name("fltk/lsp/test_server.py"),
        "the target name is the path with separators flattened, so two packages cannot collide",
    )
    return unittest.end(env)

target_name_test = unittest.make(_target_name_impl)

def py_test_test_suite(name):
    """Inventory-check unit tests for `fltk_py_tests`."""
    unittest.suite(
        name + "_unit_tests",
        accounted_test,
        unaccounted_test,
        missing_file_test,
        double_counted_test,
        target_name_test,
    )

    native.test_suite(
        name = name,
        tests = [":" + name + "_unit_tests"],
    )
