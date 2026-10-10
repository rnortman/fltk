"""The `ruff_tree_check` launcher, executed rather than read.

`//:ruff_check_ignored_dirs` is a `bazel run` target over the `.bazelignore`d directories, so the
only proof that it gates is driving real inputs through its launcher. Each case runs the
launcher from its runfiles directory (where it resolves the pinned ruff) with
`BUILD_WORKSPACE_DIRECTORY` pointed at a scratch tree: copies of the repo's two ruff config
files plus every directory the launcher sweeps, the first of which the case populates. The real
directories are never read and the working tree is never touched.
"""

from __future__ import annotations

import os
import pathlib
import re
import shlex
import shutil
import subprocess

_RUNFILES_ROOT = pathlib.Path(__file__).parent.parent
_LAUNCHER = _RUNFILES_ROOT / "ruff_check_ignored_dirs.sh"

_CLEAN = "def answer() -> int:\n    return 42\n"
_UNUSED_IMPORT = "import os\n\n\ndef answer() -> int:\n    return 42\n"
_BADLY_FORMATTED = "def answer() -> int:\n    return max( 1, 2 )\n"
_MAGIC_NUMBER = "def is_answer(x: int) -> bool:\n    return x == 42\n"


def _launcher_paths(command: str) -> list[str]:
    for line in _LAUNCHER.read_text().splitlines():
        if line.startswith(f'"$ruff" {command} '):
            words = shlex.split(line)
            return words[words.index("--") + 1 : words.index("||")]
    raise AssertionError(_LAUNCHER.read_text())


def _populated_dir() -> str:
    return _launcher_paths("check")[0]


def _workspace(tmp_path: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    # A swept path missing from the scratch tree is a ruff error, so every one is created.
    root = tmp_path / "ws"
    for swept in _launcher_paths("check"):
        (root / swept).mkdir(parents=True)
    for config in ("pyproject.toml", "gencode-ruff.toml"):
        shutil.copy(_RUNFILES_ROOT / config, root / config)
    for name, text in files.items():
        (root / _populated_dir() / name).write_text(text)
    return root


def _run(workspace: pathlib.Path | None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "BUILD_WORKSPACE_DIRECTORY"}
    if workspace is not None:
        env["BUILD_WORKSPACE_DIRECTORY"] = str(workspace)
    return subprocess.run(  # noqa: S603
        ["bash", str(_LAUNCHER)],  # noqa: S607
        cwd=_RUNFILES_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def test_a_clean_tree_passes_both_commands(tmp_path: pathlib.Path) -> None:
    result = _run(_workspace(tmp_path, {"clean.py": _CLEAN}))
    assert result.returncode == 0, _output(result)
    assert "All checks passed!" in result.stdout
    assert "already formatted" in result.stdout


def test_a_lint_finding_fails(tmp_path: pathlib.Path) -> None:
    result = _run(_workspace(tmp_path, {"unused.py": _UNUSED_IMPORT}))
    assert result.returncode != 0, _output(result)
    assert "F401" in _output(result)


def test_a_format_only_finding_fails_on_its_own(tmp_path: pathlib.Path) -> None:
    result = _run(_workspace(tmp_path, {"spaced.py": _BADLY_FORMATTED}))
    assert result.returncode != 0, _output(result)
    out = _output(result)
    # The check half passed, so the failure is the format half gating by itself.
    assert "All checks passed!" in out
    assert "would be reformatted" in out


def test_both_commands_run_when_both_fail(tmp_path: pathlib.Path) -> None:
    result = _run(_workspace(tmp_path, {"unused.py": _UNUSED_IMPORT, "spaced.py": _BADLY_FORMATTED}))
    assert result.returncode != 0, _output(result)
    out = _output(result)
    assert "F401" in out
    assert "would be reformatted" in out


def _ruff_binary() -> pathlib.Path:
    # The launcher names the pinned ruff by its runfiles-relative path; reuse it for the control.
    match = re.search(r'^ruff="\$PWD/(.+)"$', _LAUNCHER.read_text(), re.MULTILINE)
    assert match, _LAUNCHER.read_text()
    return _RUNFILES_ROOT / match.group(1)


def test_the_tests_per_file_ignores_still_apply(tmp_path: pathlib.Path) -> None:
    # PLR2004 is selected and only pyproject.toml's `tests/**/*` per-file-ignore silences it
    # here (the file is not named test_*.py), so this passes only when the launcher resolves the
    # paths from the workspace root.
    assert _populated_dir().startswith("tests/"), "the waiver case needs a swept path under tests/"
    workspace = _workspace(tmp_path, {"magic.py": _MAGIC_NUMBER})
    result = _run(workspace)
    assert result.returncode == 0, _output(result)

    # Control: the same file outside tests/ is reported, so the pass above is the waiver.
    shutil.copytree(workspace / _populated_dir(), workspace / "other")
    reported = subprocess.run(  # noqa: S603
        [str(_ruff_binary()), "check", "--no-cache", "--config", "pyproject.toml", "other"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    assert reported.returncode != 0, reported.stdout + reported.stderr
    assert "PLR2004" in reported.stdout


def test_outside_bazel_run_it_refuses() -> None:
    result = _run(None)
    assert result.returncode == 2, _output(result)
    assert "ruff_check_ignored_dirs must be invoked via 'bazel run'" in result.stderr


def test_every_bazelignore_entry_is_swept() -> None:
    lines = (_RUNFILES_ROOT / ".bazelignore").read_text().splitlines()
    ignored = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    assert ignored, "an empty .bazelignore leaves this join vacuous"
    for command in ("check", "format"):
        assert _launcher_paths(command) == ignored, (command, _launcher_paths(command), ignored)
