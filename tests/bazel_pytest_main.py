"""Entry point for every Bazel `py_test` that runs a pytest file.

One `py_test` target per test file (see //bzl:py_test.bzl), each invoking this main with the
runfiles-relative path of its file.  `bazel run`/`bazel test` puts the runfiles root on the
working directory, so the path arrives already resolvable; anything after it is passed through
to pytest, which is what `--test_arg` reaches.

Exit code 5 ("no tests were collected") is remapped to a failure: a target whose file stopped
containing tests, or whose data went missing so collection produced nothing, must be red rather
than a silently passing no-op.

FLTK_FAIL_ON_SKIP=1 extends that to skips, for files whose whole coverage sits behind an
`importorskip` guard: an extension module that failed to build or link would otherwise be a
green run of nothing.
"""

from __future__ import annotations

import os
import pathlib
import sys

import pytest

_NO_TESTS_COLLECTED = 5

# Program name, test file, pytest.ini path.
_MIN_ARGV = 3


def _pytest_argv(test_file: str, ini: str, passthrough: list[str]) -> list[str]:
    argv = [
        # The runfiles tree is read-only; the cache plugin would try to write .pytest_cache
        # into it on every run.
        "-p",
        "no:cacheprovider",
        "-c",
        ini,
        test_file,
    ]
    argv.extend(passthrough)
    return argv


def _export_import_path() -> None:
    """Put this interpreter's import path on PYTHONPATH for child processes.

    rules_python builds the test's `sys.path` in its launcher stub, not from the environment,
    so a test that spawns `sys.executable -m some.module` gets an interpreter that can see the
    runfiles root (its working directory) but none of the wheels the target depends on.  The
    child must run against the same graph as the parent, and PYTHONPATH is how it is told.
    """
    entries = [p for p in sys.path if p]
    existing = os.environ.get("PYTHONPATH")
    if existing:
        entries.extend(existing.split(os.pathsep))
    seen: set[str] = set()
    deduped = [p for p in entries if not (p in seen or seen.add(p))]
    os.environ["PYTHONPATH"] = os.pathsep.join(deduped)


class _RecordSkips:
    """Collects every skip reason pytest reports, including collection-time skips."""

    def __init__(self) -> None:
        self.skipped: list[str] = []

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        # An xfailed test is reported as skipped, with `wasxfail` set. It is an expected
        # failure that ran, not coverage that went missing, so it is not what this gate is
        # looking for.
        if report.skipped and getattr(report, "wasxfail", None) is None:
            self.skipped.append(f"{report.nodeid}: {report.longrepr}")

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.skipped:
            self.skipped.append(f"{report.nodeid or '<collection>'}: {report.longrepr}")


def main(argv: list[str]) -> int:
    if len(argv) < _MIN_ARGV:
        sys.stderr.write("usage: bazel_pytest_main.py <test-file> <pytest-ini> [pytest args...]\n")
        return 2
    test_file, ini = argv[1], argv[2]
    if not pathlib.Path(test_file).is_file():
        sys.stderr.write(f"test file not found in runfiles: {test_file}\n")
        return 2

    # Bazel hands tests a private scratch directory; without this, tmp_path and every
    # tempfile.mkdtemp land in the system temp dir and outlive the run.
    tmpdir = os.environ.get("TEST_TMPDIR")
    if tmpdir:
        os.environ.setdefault("TMPDIR", tmpdir)

    _export_import_path()

    passthrough = list(argv[3:])
    xml_out = os.environ.get("XML_OUTPUT_FILE")
    if xml_out:
        passthrough.append(f"--junitxml={xml_out}")

    recorder = _RecordSkips()
    code = pytest.main(_pytest_argv(test_file, ini, passthrough), plugins=[recorder])
    exit_code = int(code)
    if exit_code == _NO_TESTS_COLLECTED:
        sys.stderr.write(f"no tests were collected from {test_file}\n")
        return 1
    if os.environ.get("FLTK_FAIL_ON_SKIP") == "1" and recorder.skipped:
        sys.stderr.write(f"{len(recorder.skipped)} skipped test(s) with FLTK_FAIL_ON_SKIP set:\n")
        for entry in recorder.skipped:
            sys.stderr.write(f"  {entry}\n")
        return 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
