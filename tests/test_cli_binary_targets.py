"""Every runtime CLI is launchable, and the things that launch it name a real target.

`bazel run` is the only launch path for fltk's CLIs: there is no console entry point, no
virtualenv, and the modules are not executable scripts. That makes three joins that nothing
else in the tree checks — a CLI module with no `py_binary` is unreachable, a launcher script
naming a stale label fails only when an editor tries to start a server, and a shebang left on a
module claims a launch path that no longer exists.

The BUILD file is read as Starlark-as-Python (`ast`): `py_binary(...)` is a call with keyword
arguments, so the declared set is a parse away and does not have to be restated here.
"""

from __future__ import annotations

import ast
import os
import pathlib
import re
import shlex
import subprocess

import pytest

RUNFILES_ROOT = pathlib.Path(__file__).parent.parent

BUILD_FILE = RUNFILES_ROOT / "BUILD.bazel"

# The CLI modules, and the py_binary that launches each. This mapping is the assertion: a new
# CLI module has to be added here *and* get a target, and a target that stops naming its module
# fails below.
CLI_TARGETS = {
    "fltk/lsp/grammar_cli.py": "grammar_lsp",
    "fltk/lsp/highlight_cli.py": "fltk_highlight",
    "fltk/lsp/server_cli.py": "fltk_lsp",
    "fltk/unparse_cli.py": "unparse_cli",
}

# Launcher scripts checked in for editor use, and the target each builds. They exist because a
# server started directly by `bazel run` holds the workspace lock for its whole lifetime.
LAUNCHERS = {
    "editors/vscode/run-grammar-lsp": "grammar_lsp",
    "examples/gear/vscode/run-gear-lsp": "fltk_lsp",
}

SHARED_LAUNCHER = "editors/run-lsp-target"

# Each VS Code client and the launcher its in-repo default command must name.
EXTENSIONS = {
    "editors/vscode/extension.js": "run-grammar-lsp",
    "examples/gear/vscode/extension.js": "run-gear-lsp",
}


def _py_binaries() -> dict[str, dict[str, str]]:
    """Every `py_binary` in the root BUILD file: target name -> its string-valued kwargs."""
    binaries: dict[str, dict[str, str]] = {}
    for node in ast.walk(ast.parse(BUILD_FILE.read_text())):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "py_binary":
            continue
        kwargs = {
            keyword.arg: keyword.value.value
            for keyword in node.keywords
            if keyword.arg is not None and isinstance(keyword.value, ast.Constant)
        }
        binaries[kwargs["name"]] = kwargs
    return binaries


BINARIES = _py_binaries()


@pytest.mark.parametrize(("module", "target"), sorted(CLI_TARGETS.items()))
def test_each_cli_module_is_launchable(module: str, target: str) -> None:
    """The CLI's py_binary exists and runs that module as its main."""
    assert target in BINARIES, f"//:{target} is not declared in BUILD.bazel"
    assert BINARIES[target].get("main") == module, (
        f"//:{target} must run {module} as its main, not {BINARIES[target].get('main')}"
    )
    assert (RUNFILES_ROOT / module).is_file(), f"{module} is not in the target's runfiles"


def test_no_cli_module_is_missing_a_target() -> None:
    """Every `*_cli.py` module in the package is one of the CLIs pinned above.

    A new CLI that nobody wires up is reachable only by `python -m`, which is not a supported
    launch path — nothing puts the package on an interpreter's path outside Bazel.
    """
    found = {
        str(path.relative_to(RUNFILES_ROOT))
        for path in (RUNFILES_ROOT / "fltk").rglob("*_cli.py")
        if not path.name.startswith("test_")
    }
    assert found == set(CLI_TARGETS), "a *_cli.py module has no py_binary (or the map is stale)"


@pytest.mark.parametrize("module", sorted(CLI_TARGETS))
def test_cli_modules_are_not_scripts(module: str) -> None:
    """No CLI module carries a shebang: `bazel run` is the launch path, not `./the_module`."""
    first_line = (RUNFILES_ROOT / module).read_text().splitlines()[0]
    assert not first_line.startswith("#!"), f"{module} still claims to be a directly executable script"


def _code(path: pathlib.Path) -> str:
    """A shell script's executable lines, with comments dropped.

    Every one of these scripts documents in prose what it then does in code, so a text
    assertion over the whole file is satisfied by the comment that describes the guard as
    much as by the guard.
    """
    return "\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("#"))


@pytest.mark.parametrize(("launcher", "target"), sorted(LAUNCHERS.items()))
def test_launchers_build_a_real_target(launcher: str, target: str) -> None:
    """A launcher names a py_binary that exists, and delegates to the shared implementation."""
    path = RUNFILES_ROOT / launcher
    assert path.is_file(), f"{launcher} is not in the target's runfiles"
    assert target in BINARIES, f"{launcher} builds //:{target}, which is not declared"
    body = [line for line in _code(path).splitlines() if line.strip()]
    argv = shlex.split(body[-1])
    assert argv[0] == "exec", f"{launcher} must exec its delegate, not fork it: {body[-1]}"
    assert argv[1].endswith("run-lsp-target"), (
        f"{launcher} must exec {SHARED_LAUNCHER} rather than run bazel itself: {body[-1]}"
    )
    assert argv[2] == f"//:{target}", f"{launcher} must name //:{target}, not {argv[2]}"


def test_the_shared_launcher_takes_the_lock_only_to_build() -> None:
    """The one place `bazel run` is spelled keeps the workspace lock scoped to the build.

    Without --script_path the server runs under `bazel run` and blocks every other Bazel command
    in the checkout for its lifetime.
    """
    code = _code(RUNFILES_ROOT / SHARED_LAUNCHER)
    assert "--script_path=" in code, f"{SHARED_LAUNCHER} must run the built binary, not `bazel run` it"


def _run_launcher(directory: pathlib.Path, **environment: str) -> subprocess.CompletedProcess[str]:
    """Invoke the shared launcher with `directory` as its private-directory root.

    `bazel` is stubbed out on PATH: everything under test happens before the build, and a real
    build in a test would be minutes of work to reach an assertion that does not need it.
    """
    stub_bin = directory / "bin"
    stub_bin.mkdir(exist_ok=True)
    stub = stub_bin / "bazel"
    stub.write_text("#!/bin/sh\nexit 0\n")
    stub.chmod(0o755)
    return subprocess.run(  # noqa: S603
        [str(RUNFILES_ROOT / SHARED_LAUNCHER), "//:grammar_lsp"],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
        env={**os.environ, "PATH": f"{stub_bin}:{os.environ['PATH']}", **environment},
    )


def test_the_shared_launcher_refuses_a_pre_seeded_launcher_directory(tmp_path: pathlib.Path) -> None:
    """A symlink someone else planted at the directory name is a script this launcher execs."""
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    elsewhere = tmp_path / "attacker"
    elsewhere.mkdir()
    (runtime_dir / f"fltk-lsp-{os.getuid()}").symlink_to(elsewhere)

    result = _run_launcher(tmp_path, XDG_RUNTIME_DIR=str(runtime_dir))

    assert result.returncode == 1, result.stderr
    assert "refusing to use" in result.stderr, result.stderr


def test_the_shared_launcher_narrows_a_world_readable_directory(tmp_path: pathlib.Path) -> None:
    """An existing directory of ours that anyone can write is re-narrowed before anything runs."""
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    launcher_dir = runtime_dir / f"fltk-lsp-{os.getuid()}"
    launcher_dir.mkdir()
    launcher_dir.chmod(0o777)

    _run_launcher(tmp_path, XDG_RUNTIME_DIR=str(runtime_dir))

    assert launcher_dir.stat().st_mode & 0o777 == 0o700, oct(launcher_dir.stat().st_mode)


def test_the_shared_launcher_publishes_the_script_atomically() -> None:
    """Two clients starting at once must not have one exec the file the other is rewriting.

    VS Code restoring a session with several fltk language ids open starts three clients on the
    same target in the same tick, so they compute the same launcher path. Bazel writes its
    `--script_path` in place, so the build has to land on a private name and be renamed over the
    shared one, which is atomic.
    """
    code = _code(RUNFILES_ROOT / SHARED_LAUNCHER)
    build = next(line for line in code.splitlines() if "--script_path=" in line)
    assert '--script_path="$launcher"' not in build, f"the build must not write the shared path directly: {build}"
    assert re.search(r'^\s*mv -f -- "\$staging" "\$launcher"\s*$', code, re.MULTILINE), (
        f"the built script must be renamed over the shared name: {code}"
    )


@pytest.mark.parametrize(("extension", "launcher"), sorted(EXTENSIONS.items()))
def test_vscode_clients_launch_through_the_launcher(extension: str, launcher: str) -> None:
    """The in-repo default server command is the checked-in launcher, resolved from the repo."""
    text = (RUNFILES_ROOT / extension).read_text()
    assert f'"{launcher}"' in text, f"{extension} must build its default command from {launcher}"


def test_launcher_paths_are_the_ones_the_clients_join() -> None:
    """Each launcher the clients name is a real file, and executable — as is the shared one."""
    for launcher in [*LAUNCHERS, SHARED_LAUNCHER]:
        path = pathlib.Path(RUNFILES_ROOT / launcher).resolve()
        assert path.is_file(), f"{launcher} is missing"
        assert path.stat().st_mode & 0o111, f"{launcher} is not executable"
