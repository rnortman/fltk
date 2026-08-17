"""Tests for the shared pyright harness (`tests/pyright_test_utils.py`).

The suites that use it assert things about *other* code's type-checking, so a harness that
quietly resolved the wrong tool — or no tool — would turn every one of them into a skip or a
vacuous pass.  These tests pin the resolution rules and the config shape directly.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from tests import pyright_test_utils as utils

_CLEAN_SOURCE = """\
from __future__ import annotations


def f(x: int) -> int:
    return x + 1
"""

_BROKEN_SOURCE = """\
from __future__ import annotations


def f(x: int) -> str:
    return x
"""


def test_the_tool_is_the_bundled_pair() -> None:
    """Both halves come from wheels in the target's own deps, never from the host.

    Guards the hermeticity property those wheels buy: the whole point of running the bundled
    npm build under the bundled node is that no part of the invocation is ambient.
    """
    command = utils.pyright_command()
    assert command is not None, "pyright must be resolvable from the target's own deps"
    assert command[0].endswith("/bin/node"), command
    assert command[1].endswith("/pyright/dist/index.js"), command
    assert len(command) == 2, command


def test_a_missing_package_yields_no_bundled_file() -> None:
    assert utils._bundled_file("a_package_that_does_not_exist_anywhere", "x") is None


def test_a_missing_file_in_a_real_package_yields_none() -> None:
    assert utils._bundled_file("tests.pyright_test_utils", "no_such_file.js") is None


def test_the_config_names_this_interpreters_import_paths() -> None:
    config = utils.pyright_config()
    assert config["pythonVersion"] == "3.10"
    assert "venvPath" not in config, "a runfiles tree has no venv to point at"
    assert str(utils._REPO_ROOT) in config["extraPaths"] or any(
        pathlib.Path(p) == utils._REPO_ROOT for p in config["extraPaths"]
    )


def test_caller_extra_paths_come_first_and_are_not_duplicated() -> None:
    first = utils.import_search_paths()[0]
    config = utils.pyright_config(["/somewhere/else", first])
    assert config["extraPaths"][0] == "/somewhere/else"
    assert config["extraPaths"][1] == first
    assert config["extraPaths"].count(first) == 1


def test_write_pyright_config_writes_the_config_pyright_reads(tmp_path: pathlib.Path) -> None:
    utils.write_pyright_config(tmp_path, extra_paths=["/some/stub/dir"])
    written = json.loads((tmp_path / "pyrightconfig.json").read_text())
    assert written == utils.pyright_config(["/some/stub/dir"])


def test_an_unavailable_pyright_skips_rather_than_fails(tmp_path: pathlib.Path) -> None:
    with pytest.raises(BaseException, match="pyright not available") as excinfo:
        utils._run_pyright_over_dir(tmp_path, pyright_available=False)
    assert excinfo.typename == "Skipped"


def test_a_clean_file_produces_no_error_diagnostics(
    pyright_available: bool,  # noqa: FBT001
    tmp_path: pathlib.Path,
) -> None:
    utils.write_pyright_config(tmp_path)
    (tmp_path / "clean.py").write_text(_CLEAN_SOURCE)
    assert utils.run_pyright_over_file(tmp_path / "clean.py", pyright_available=pyright_available) == []


def test_a_broken_file_produces_error_diagnostics(
    pyright_available: bool,  # noqa: FBT001
    tmp_path: pathlib.Path,
) -> None:
    utils.write_pyright_config(tmp_path)
    (tmp_path / "broken.py").write_text(_BROKEN_SOURCE)
    errors = utils.run_pyright_over_file(tmp_path / "broken.py", pyright_available=pyright_available)
    assert errors, "returning an int where str is declared must be an error"
    assert all(d["severity"] == "error" for d in errors)


def test_a_directory_run_partitions_by_file(
    pyright_available: bool,  # noqa: FBT001
    tmp_path: pathlib.Path,
) -> None:
    utils.write_pyright_config(tmp_path)
    (tmp_path / "clean.py").write_text(_CLEAN_SOURCE)
    (tmp_path / "broken.py").write_text(_BROKEN_SOURCE)
    partitioned = utils._run_pyright_over_dir(tmp_path, pyright_available=pyright_available)
    assert utils._diags_for_file(partitioned, "broken.py")
    assert utils._diags_for_file(partitioned, "clean.py") == []


def test_a_file_outside_the_config_directory_is_checked_under_project(
    pyright_available: bool,  # noqa: FBT001
    tmp_path: pathlib.Path,
) -> None:
    """`project` is what lets a source-tree file be checked under a generated config."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    utils.write_pyright_config(config_dir)
    target_dir = tmp_path / "elsewhere"
    target_dir.mkdir()
    (target_dir / "broken.py").write_text(_BROKEN_SOURCE)
    errors = utils.run_pyright_over_file(
        target_dir / "broken.py",
        pyright_available=pyright_available,
        cwd=config_dir,
        project=config_dir,
    )
    assert errors
