"""Shared pyright invocation utilities for test files.

Pyright is the npm bundle shipped inside the ``pyright`` wheel (``pyright/dist/index.js``), run
under the ``node`` binary shipped inside ``nodejs-wheel-binaries`` (the ``[nodejs]`` extra, which
``pyright`` pulls in).  Both are ordinary importable packages, so they resolve from
``sys.path`` in a runfiles tree and in a virtualenv alike, and neither reaches the network —
the ``pyright`` package's own Python wrapper, which downloads the npm package on first run, is
deliberately bypassed.

Import resolution for the checked fixtures comes from ``extraPaths`` built out of this
interpreter's ``sys.path``, not from a ``venvPath``: a runfiles tree has no venv, and the
wheels and first-party packages a fixture imports are exactly what is already importable here.
"""

from __future__ import annotations

import functools
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

import pytest

# Under Bazel this is the runfiles root.
_REPO_ROOT = pathlib.Path(__file__).parent.parent


def _bundled_file(package: str, *parts: str) -> pathlib.Path | None:
    """Return a file shipped inside an importable package, or None if it is not there."""
    spec = importlib.util.find_spec(package)
    if spec is None or spec.origin is None:
        return None
    candidate = pathlib.Path(spec.origin).parent.joinpath(*parts)
    return candidate if candidate.is_file() else None


@functools.lru_cache(maxsize=1)
def pyright_command() -> list[str] | None:
    """Return the argv prefix that runs pyright, or None when no pyright is reachable.

    The tool is the npm bundle inside the `pyright` wheel run under the node inside the
    `nodejs-wheel-binaries` wheel — the same pair `//:pyright` resolves in Starlark, and the
    only one that works inside a test sandbox: nothing in the invocation comes from the host.
    """
    node = _bundled_file("nodejs_wheel", "bin", "node")
    pyright_js = _bundled_file("pyright", "dist", "index.js")
    if node is not None and pyright_js is not None and os.access(node, os.X_OK):
        return [str(node), str(pyright_js)]
    return None


def pyright_runnable() -> bool:
    """Return True when a pyright invocation is available in this environment."""
    return pyright_command() is not None


def _pyright_env() -> dict[str, str]:
    """Environment for the pyright subprocess.

    node reads HOME for its own config even when there is none to read, and a Bazel test
    sandbox does not always define it.
    """
    env = dict(os.environ)
    if not env.get("HOME"):
        env["HOME"] = env.get("TEST_TMPDIR") or tempfile.gettempdir()
    return env


def _run_pyright_json(
    target: pathlib.Path,
    cwd: pathlib.Path,
    project: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Run `pyright --outputjson <target>` from cwd and return the parsed report.

    ``project`` names the directory holding the pyrightconfig.json to use, for targets that
    live outside the directory the config was written into.
    """
    command = pyright_command()
    assert command is not None, "pyright_runnable() must be checked before invoking pyright"
    project_args = ["--project", str(project)] if project is not None else []
    result = subprocess.run(  # noqa: S603
        [*command, *project_args, "--outputjson", str(target)],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        cwd=str(cwd),
        env=_pyright_env(),
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"pyright produced non-JSON output: {result.stdout[:500]}\nstderr: {result.stderr[:500]}")


def _run_pyright_over_dir(
    tmpdir: pathlib.Path,
    *,
    pyright_available: bool,
) -> dict[str, list[dict[str, Any]]]:
    """Run pyright --outputjson over a directory; return error diagnostics partitioned by file path.

    Returns a dict mapping each file's absolute path string to its list of error diagnostics
    (severity == "error" only; callers that need warnings must use a separate invocation).
    Raises pytest.skip if pyright unavailable.

    cwd is the tmpdir so pyright picks up the pyrightconfig.json written there.
    """
    if not pyright_available:
        pytest.skip("pyright not available in this environment")
    data = _run_pyright_json(tmpdir, cwd=tmpdir)
    partitioned: dict[str, list[dict[str, Any]]] = {}
    for diag in data.get("generalDiagnostics", []):
        if diag.get("severity") != "error":
            continue
        file_key = diag.get("file", "")
        partitioned.setdefault(file_key, []).append(diag)
    return partitioned


def run_pyright_over_file(
    file_path: pathlib.Path,
    *,
    pyright_available: bool,
    cwd: pathlib.Path | None = None,
    project: pathlib.Path | None = None,
) -> list[dict[str, Any]]:
    """Run pyright --outputjson on one file; return its error diagnostics.

    cwd defaults to the file's directory, which is where its pyrightconfig.json lives;
    ``project`` names that directory explicitly when the file lives elsewhere.
    Raises pytest.skip if pyright unavailable.
    """
    if not pyright_available:
        pytest.skip("pyright not available in this environment")
    data = _run_pyright_json(file_path, cwd=cwd if cwd is not None else file_path.parent, project=project)
    return [d for d in data.get("generalDiagnostics", []) if d.get("severity") == "error"]


def _diags_for_file(partitioned: dict[str, list[dict[str, Any]]], filename: str) -> list[dict[str, Any]]:
    """Return all diagnostics whose file path contains filename as a substring.

    Callers should pass the full filename including extension (e.g. ``"my_fixture.py"``)
    to avoid false matches against similarly-named files.
    """
    return [d for path, diags in partitioned.items() if filename in path for d in diags]


def import_search_paths() -> list[str]:
    """This interpreter's importable directories, for pyright's ``extraPaths``.

    Covers the first-party tree and every third-party package directory at once, which is
    what makes one config work both in a runfiles tree (no venv exists) and in a checkout.
    """
    return [p for p in sys.path if p and pathlib.Path(p).is_dir()]


def pyright_config(extra_paths: list[str] | None = None) -> dict[str, Any]:
    """Return the pyrightconfig contents a fixture tmpdir needs."""
    paths = list(extra_paths) if extra_paths is not None else []
    for path in import_search_paths():
        if path not in paths:
            paths.append(path)
    return {"pythonVersion": "3.10", "extraPaths": paths}


def write_pyright_config(tmpdir: pathlib.Path, *, extra_paths: list[str] | None = None) -> None:
    """Write a pyrightconfig.json into tmpdir resolving imports the way this interpreter does.

    Targets Python 3.10 regardless of where tmpdir is located on disk.  ``extra_paths``, when
    given, is prepended to ``extraPaths`` (e.g. the runfiles root and the directory holding a
    generated stub package) so pyright resolves stub packages exactly as the project-wide run
    does.
    """
    (tmpdir / "pyrightconfig.json").write_text(json.dumps(pyright_config(extra_paths)))
