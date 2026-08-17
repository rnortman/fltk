"""`fltk_py_test` — one Bazel `py_test` per pytest file.

Per-file targets are the unit of caching and parallelism: editing one test file re-runs one
target, and a green run of the rest is a cache hit.  That is why the suite is declared as an
explicit list of files rather than discovered by glob — a glob would silently absorb a new file
with whatever deps the pattern happened to carry, and silently keep passing when a file is
deleted or renamed out from under a target.

Every target runs //:tests/bazel_pytest_main.py, which invokes `pytest.main` on the one file.
The base deps and data below are what a plain pytest file needs; anything more (a fixture
extension, pygls, a test_data corpus, an examples/ tree) is named per target.

`fltk_py_tests` is also the inventory gate: it takes the package's pytest glob and the deferred
list alongside the declared dict, and fails at load time when the three do not account for
exactly the same files.  The check lives here rather than in a test because both the declared
set and the file set are already in hand at that point — the alternative is re-deriving them by
parsing the BUILD file's Starlark, which pins the gate to the file's syntax rather than its
meaning.  The cost is that a missing target breaks `bazel build //...` rather than reddening one
test; that is the louder end of the trade and the intended one for "a test file runs nowhere".
"""

load("@rules_python//python:defs.bzl", "py_test")

# The root conftest.py sets _TYPER_FORCE_DISABLE_TERMINAL at import time, before any test module
# imports Typer.  Under Bazel, pytest still loads it from the runfiles root (it is an ancestor of
# every test file we run), but the env var is set here as well so a target's behaviour does not
# depend on conftest collection order.
_PYTEST_ENV = {"_TYPER_FORCE_DISABLE_TERMINAL": "1"}

_PYTEST_MAIN = "//tests:bazel_pytest_main.py"

_BASE_DEPS = [
    "//:fltk",
    # The Rust extension is always present under Bazel, so the `importorskip` guards in the
    # extension-dependent tests are always satisfied.  They stay in the test files: outside
    # Bazel they turn an accidental invocation into a skip rather than a collection error.
    "//:native_py",
    "@pypi//astor",
    "@pypi//pytest",
    "@pypi//typer",
]

# The fixture corpora under fltk/**/test_data are deliberately NOT here: they are named per
# target (//:fegen_test_data, //:lsp_test_data) so editing one grammar invalidates the handful
# of targets that read it rather than all ~125 of them, which is the caching per-file targets
# exist to buy.
_BASE_DATA = [
    "//:conftest.py",
    "//:pytest.ini",
]

def _target_name(src):
    """Path-derived, collision-free target name: fltk/lsp/test_server.py -> fltk_lsp_test_server."""
    if not src.endswith(".py"):
        fail("fltk_py_test src must be a .py file, got: " + src)
    return src[:-len(".py")].replace("/", "_")

def fltk_py_test(
        src,
        name = None,
        deps = [],
        data = [],
        size = "small",
        fail_on_skip = False,
        env = {},
        **kwargs):
    """Declares a py_test running pytest over a single test file.

    Args:
        src: the test file, package-relative.
        name: target name; defaults to the src path with `/` replaced by `_`.
        deps: extra deps beyond the base set (fixture extensions, pygls, ...).
        data: extra runtime files beyond the base set.
        size: Bazel test size; most pytest files are `small`.
        fail_on_skip: turn a skipped test in this file into a failure.  For files whose
            coverage is entirely behind an `importorskip` guard, where a missing extension
            module would otherwise be a green run of nothing.
        env: extra environment variables, merged over the shared ones.  `$(rootpath ...)` is
            expanded against this target's srcs, deps and data, so a test that spawns a
            Bazel-built binary names it here.
        **kwargs: forwarded to py_test (tags, env_inherit, shard_count, timeout, ...).
    """
    merged_env = dict(_PYTEST_ENV)
    if fail_on_skip:
        merged_env["FLTK_FAIL_ON_SKIP"] = "1"
    merged_env.update(env)
    py_test(
        name = name or _target_name(src),
        srcs = [src, _PYTEST_MAIN],
        main = _PYTEST_MAIN,
        args = [
            "$(rootpath %s)" % src,
            "$(rootpath //:pytest.ini)",
        ],
        data = _BASE_DATA + data,
        env = merged_env,
        # Without this, rules_python drops an empty __init__.py into every runfiles directory,
        # which turns a fixture crate's source directory (tests/rust_parser_fixture/, holding
        # only Rust and BUILD files) into a regular package that shadows the compiled extension
        # module of the same name.  With it, that directory is at most a namespace portion,
        # which loses to the real .so wherever it sits on sys.path.
        legacy_create_init = 0,
        size = size,
        deps = _BASE_DEPS + deps,
        **kwargs
    )

def _inventory_violation(declared, deferred, on_disk):
    """Return the declared/deferred/on-disk mismatch message, or None.

    Three ways the three sets can disagree, each a real loss:
      - a file declared *and* deferred: the deferral is stale and reads as uncovered;
      - a file on disk in neither set: it runs nowhere and nothing says so;
      - a declared or deferred file that is not on disk: a target naming a deleted file, or an
        exemption outliving the file it was written for.

    Returned rather than raised so a Starlark unit test can assert the messages; `fail` cannot
    be caught.
    """
    both = sorted([p for p in declared if p in deferred])
    if both:
        return "fltk_py_tests: declared and deferred name the same files: {}.".format(", ".join(both))

    accounted = {p: True for p in declared}
    for p in deferred:
        accounted[p] = True

    present = {p: True for p in on_disk}
    unaccounted = sorted([p for p in on_disk if p not in accounted])
    if unaccounted:
        return ("fltk_py_tests: pytest files with no target and no deferral: {}. Add each to the " +
                "tests dict, or to `deferred` with the reason it cannot run in the sandbox.").format(
            ", ".join(unaccounted),
        )

    missing = sorted([p for p in accounted if p not in present])
    if missing:
        return "fltk_py_tests: declared or deferred files that do not exist: {}.".format(", ".join(missing))
    return None

def fltk_py_tests(tests, glob_pattern, deferred = {}):
    """Declares one fltk_py_test per entry, and gates the package's pytest inventory.

    Args:
        tests: dict mapping the test file path to a dict of fltk_py_test keyword overrides
            (`{}` for a file that needs nothing beyond the base deps and data).
        glob_pattern: the package-relative glob matching every pytest file the package owns.
            Mandatory: it is what makes the inventory check unskippable, so a package cannot
            gain test files that silently run nowhere.
        deferred: dict mapping a pytest file with no target yet to the reason it has none.
    """
    msg = _inventory_violation(tests.keys(), deferred.keys(), native.glob([glob_pattern]))
    if msg != None:
        fail(msg)

    for src, attrs in tests.items():
        fltk_py_test(src = src, **attrs)

py_test_internals = struct(
    target_name = _target_name,
    inventory_violation = _inventory_violation,
    base_deps = _BASE_DEPS,
    base_data = _BASE_DATA,
)
