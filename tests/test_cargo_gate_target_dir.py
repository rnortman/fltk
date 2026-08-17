"""Where the compile gates build, and that no two of them build in the same place.

`cargo_target_dir` is a four-branch precedence chain that creates a directory, and every branch
is invisible in a passing run: pick the wrong root and the gates still compile, they just land
somewhere the operator did not choose and stop reusing yesterday's artifacts — which surfaces
only as `size = "large"` tests getting slower. The name argument has the same property in
reverse: two gates handed the same name serialize on cargo's exclusive lock on a target
directory instead of running in parallel.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from tests.generated_rust_gate import cargo_target_dir

_HERE = pathlib.Path(__file__).parent

_VARIABLES = ("FLTK_CARGO_GATE_TARGET_DIR", "XDG_CACHE_HOME", "HOME", "TEST_TMPDIR")

#: The pytest files that own a compile gate, i.e. that call `cargo_target_dir`.
GATE_MODULES = (
    "test_generated_rust_gate.py",
    "test_nullable_loop_guard.py",
    "test_rust_prelude_qualification.py",
)


@pytest.fixture
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in _VARIABLES:
        monkeypatch.delenv(variable, raising=False)


@pytest.mark.usefixtures("_clean_env")
def test_the_explicit_override_wins_over_every_other_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """The knob a CI image or container sets must not be shadowed by an ambient HOME."""
    monkeypatch.setenv("FLTK_CARGO_GATE_TARGET_DIR", str(tmp_path / "override"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("TEST_TMPDIR", str(tmp_path / "scratch"))

    assert cargo_target_dir("gate") == tmp_path / "override" / "gate"


@pytest.mark.usefixtures("_clean_env")
def test_the_xdg_cache_wins_over_home(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """XDG_CACHE_HOME *is* the cache location when it is set; $HOME/.cache is the guess."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("TEST_TMPDIR", str(tmp_path / "scratch"))

    assert cargo_target_dir("gate") == tmp_path / "xdg" / "fltk-cargo-gate" / "gate"


@pytest.mark.usefixtures("_clean_env")
def test_home_wins_over_the_runner_scratch(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """The scratch directory is wiped per run, so it is the last resort, not the default."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("TEST_TMPDIR", str(tmp_path / "scratch"))

    assert cargo_target_dir("gate") == tmp_path / "home" / ".cache" / "fltk-cargo-gate" / "gate"


@pytest.mark.usefixtures("_clean_env")
def test_the_runner_scratch_is_the_last_resort(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    monkeypatch.setenv("TEST_TMPDIR", str(tmp_path / "scratch"))

    assert cargo_target_dir("gate") == tmp_path / "scratch" / "fltk-cargo-gate" / "gate"


@pytest.mark.usefixtures("_clean_env")
def test_no_private_root_is_an_error_rather_than_a_shared_temp_directory() -> None:
    """The directory holds rlibs and a binary a gate executes; a world-writable one is a hijack."""
    with pytest.raises(RuntimeError, match="FLTK_CARGO_GATE_TARGET_DIR"):
        cargo_target_dir("gate")


@pytest.mark.usefixtures("_clean_env")
def test_the_resolved_directory_exists(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    """Callers hand the result straight to `--target-dir`, which does not create it."""
    monkeypatch.setenv("FLTK_CARGO_GATE_TARGET_DIR", str(tmp_path / "override"))

    assert cargo_target_dir("gate").is_dir()


def _gate_names(module: str) -> set[str]:
    source = (_HERE / module).read_text()
    return set(re.findall(r"""cargo_target_dir\(["']([^"']+)["']\)""", source))


def test_every_gate_builds_in_a_directory_of_its_own() -> None:
    """cargo takes an exclusive lock per target directory, so a shared name serializes the gates."""
    seen: dict[str, str] = {}
    for module in GATE_MODULES:
        names = _gate_names(module)
        assert names, f"{module} is listed as a compile gate but names no cargo_target_dir"
        for name in names:
            assert name not in seen, f"{module} reuses the {name!r} target directory of {seen[name]}"
            seen[name] = module
