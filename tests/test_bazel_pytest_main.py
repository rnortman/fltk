"""Tests for the shared Bazel py_test entry point.

Each guard in bazel_pytest_main turns an invisible non-run into a red target; these tests
assert that directly rather than inferring it from a green suite.  The entry point is driven
as a subprocess so the inner pytest session stays out of this one and the exit code is the
contract.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

from tests import bazel_pytest_main

MAIN = pathlib.Path(bazel_pytest_main.__file__).resolve()

# Runfiles root under Bazel, repo root under a plain pytest run; both hold pytest.ini.
INI = pathlib.Path("pytest.ini").resolve()


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run the entry point exactly as a py_test target does."""
    child_env = dict(os.environ)
    child_env.update(env or {})
    return subprocess.run(  # noqa: S603
        [sys.executable, str(MAIN), *args],
        capture_output=True,
        text=True,
        env=child_env,
        check=False,
    )


def _write(path: pathlib.Path, body: str) -> str:
    path.write_text(body)
    return str(path)


def test_a_passing_file_exits_zero(tmp_path: pathlib.Path) -> None:
    test_file = _write(tmp_path / "test_ok.py", "def test_ok():\n    assert True\n")
    result = _run(test_file, str(INI))
    assert result.returncode == 0, result.stderr


def test_a_file_with_no_tests_is_a_failure(tmp_path: pathlib.Path) -> None:
    """Exit code 5 must not reach Bazel as a pass.

    A target whose file stopped containing tests, or whose data went missing so collection
    produced nothing, is a green run of nothing otherwise.
    """
    test_file = _write(tmp_path / "test_empty.py", "x = 1\n")
    result = _run(test_file, str(INI))
    assert result.returncode == 1
    assert "no tests were collected" in result.stderr


def test_a_failing_test_keeps_pytests_exit_code(tmp_path: pathlib.Path) -> None:
    test_file = _write(tmp_path / "test_fail.py", "def test_fail():\n    assert False\n")
    result = _run(test_file, str(INI))
    assert result.returncode == 1


def test_fail_on_skip_reddens_a_skipped_test(tmp_path: pathlib.Path) -> None:
    """A skipped test in a gated file is a failure, and names itself; without the gate it is not.

    Both halves matter: the gate proves nothing if the file would have been red anyway.
    """
    test_file = _write(
        tmp_path / "test_skipping.py",
        'import pytest\n\ndef test_ran():\n    pass\n\n@pytest.mark.skip(reason="nope")\ndef test_gone():\n    pass\n',
    )

    gated = _run(test_file, str(INI), env={"FLTK_FAIL_ON_SKIP": "1"})
    assert gated.returncode == 1
    assert "FLTK_FAIL_ON_SKIP" in gated.stderr
    assert "test_gone" in gated.stderr

    ungated = _run(test_file, str(INI), env={"FLTK_FAIL_ON_SKIP": ""})
    assert ungated.returncode == 0, ungated.stderr


def test_a_module_level_importorskip_is_red_with_or_without_the_gate(tmp_path: pathlib.Path) -> None:
    """The missing-extension case the gate was built for is caught one step earlier.

    A module-level `importorskip` skips the whole module, so nothing is collected and the exit-5
    remap fires before the skip recorder is consulted.  Red either way, but by the collection
    path — so the message names the file rather than the skips.
    """
    test_file = _write(
        tmp_path / "test_importorskip.py",
        'import pytest\n\npytest.importorskip("fltk_no_such_module")\n\ndef test_x():\n    pass\n',
    )

    for env in ({"FLTK_FAIL_ON_SKIP": "1"}, {"FLTK_FAIL_ON_SKIP": ""}):
        result = _run(test_file, str(INI), env=env)
        assert result.returncode == 1
        assert "no tests were collected" in result.stderr


def test_fail_on_skip_ignores_xfail(tmp_path: pathlib.Path) -> None:
    """pytest reports an xfailed test as skipped-with-wasxfail; it is not missing coverage.

    Without the wasxfail check, the first `xfail` added to a fail-on-skip file turns an
    expected failure into a red target diagnosed as a skip.
    """
    test_file = _write(
        tmp_path / "test_xfail.py",
        "import pytest\n\n@pytest.mark.xfail(reason='known')\ndef test_x():\n    assert False\n",
    )
    result = _run(test_file, str(INI), env={"FLTK_FAIL_ON_SKIP": "1"})
    assert result.returncode == 0, result.stderr


def test_missing_arguments_are_a_usage_error() -> None:
    result = _run("only-one-arg")
    assert result.returncode == 2
    assert "usage:" in result.stderr


def test_a_test_file_missing_from_runfiles_is_a_usage_error(tmp_path: pathlib.Path) -> None:
    """A data dep that never made it into runfiles must not read as an empty test file."""
    result = _run(str(tmp_path / "test_absent.py"), str(INI))
    assert result.returncode == 2
    assert "not found in runfiles" in result.stderr


def test_export_import_path_publishes_every_sys_path_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Child interpreters must see the same import graph as the test that spawns them."""
    monkeypatch.setattr(sys, "path", ["/a", "", "/b", "/a"])
    monkeypatch.delenv("PYTHONPATH", raising=False)

    bazel_pytest_main._export_import_path()

    assert os.environ["PYTHONPATH"].split(os.pathsep) == ["/a", "/b"]


def test_export_import_path_preserves_an_existing_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """An inherited PYTHONPATH is appended to, not replaced, and never duplicated."""
    monkeypatch.setattr(sys, "path", ["/a", "/b"])
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join(["/b", "/c"]))

    bazel_pytest_main._export_import_path()

    assert os.environ["PYTHONPATH"].split(os.pathsep) == ["/a", "/b", "/c"]
