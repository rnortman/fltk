"""Shared pyright invocation utilities for test files.

Used by fltk/fegen/test_cst_protocol.py, tests/test_clean_protocol_consumer_api.py,
and tests/test_gsm2tree_rs.py to batch pyright runs and partition diagnostics.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
from typing import Any

import pytest

# Repo root: tests/ is one level below the repo root.
_REPO_ROOT = pathlib.Path(__file__).parent.parent


def _run_pyright_over_dir(
    tmpdir: pathlib.Path,
    *,
    pyright_available: bool,
) -> dict[str, list[dict[str, Any]]]:
    """Run pyright --outputjson over a directory; return error diagnostics partitioned by file path.

    Returns a dict mapping each file's absolute path string to its list of error diagnostics
    (severity == "error" only; callers that need warnings must use a separate invocation).
    Raises pytest.skip if pyright unavailable.

    Uses ``uv run --project <repo_root>`` so the venv is resolved from the project directory
    regardless of where the tmpdir lives on disk.  cwd is set to tmpdir so pyright picks up
    the pyrightconfig.json written there.
    """
    if not pyright_available:
        pytest.skip("pyright not available in this environment")
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "--project", str(_REPO_ROOT), "pyright", "--outputjson", str(tmpdir)],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        cwd=str(tmpdir),
    )
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"pyright produced non-JSON output: {result.stdout[:500]}")
    partitioned: dict[str, list[dict[str, Any]]] = {}
    for diag in data.get("generalDiagnostics", []):
        if diag.get("severity") != "error":
            continue
        file_key = diag.get("file", "")
        partitioned.setdefault(file_key, []).append(diag)
    return partitioned


def _diags_for_file(partitioned: dict[str, list[dict[str, Any]]], filename: str) -> list[dict[str, Any]]:
    """Return all diagnostics whose file path contains filename as a substring.

    Callers should pass the full filename including extension (e.g. ``"my_fixture.py"``)
    to avoid false matches against similarly-named files.
    """
    return [d for path, diags in partitioned.items() if filename in path for d in diags]


def write_pyright_config(tmpdir: pathlib.Path) -> None:
    """Write a pyrightconfig.json into tmpdir pointing at the repo venv.

    Ensures pyright uses the project venv and targets Python 3.10 regardless of
    where tmpdir is located on disk.
    """
    (tmpdir / "pyrightconfig.json").write_text(
        json.dumps({"pythonVersion": "3.10", "venvPath": str(_REPO_ROOT), "venv": ".venv"})
    )
