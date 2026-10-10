"""The shell `make check` runs, executed rather than read.

The Makefile's recipes are thin call sites; the shell with control flow lives in `scripts/`, and
this module runs it under `bash` with stub `bazel` and `make` binaries first on `PATH`. The
failure arms are the point: they are what no green gate run ever enters, so a text test over them
is satisfied by a recipe whose `exit 1` has become `:` — and so is the gate.

`scripts/pyo3-guard` is the no-pyo3 guard both Bazel lanes call. The fake `bazel` logs its argv,
writes a stderr marker, and answers each verb from a file the scenario writes:

- `query` → `query.out` (the `rdeps` positive control);
- `cquery` over `deps(set(` → `union.out`;
- any other `cquery` → `single.out` (the per-target attribution loop).

`<name>.exit` sets the matching exit status. `scripts/check-steps` is the step loop; the fake
`make` prints one marker to each stream and fails on the step named `fail`.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess

import pytest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
_PYO3_GUARD = _REPO_ROOT / "scripts" / "pyo3-guard"
_CHECK_STEPS = _REPO_ROOT / "scripts" / "check-steps"

_CONTROL = "//crates/fltk-cst-core:no_python"
_TARGETS = ("//a:x", "//b:y")

_FAKE_BAZEL = """#!/bin/sh
echo "$*" >> "$FAKE_BAZEL_LOG"
echo "fake-bazel-stderr:$1" >&2
case "$1" in
    query) name=query ;;
    cquery)
        case "$*" in
            *"deps(set("*) name=union ;;
            *) name=single ;;
        esac ;;
    *) name=other ;;
esac
cat "$FAKE_BAZEL_DIR/$name.out" 2>/dev/null
if [ -f "$FAKE_BAZEL_DIR/$name.exit" ]; then
    exit "$(cat "$FAKE_BAZEL_DIR/$name.exit")"
fi
exit 0
"""

_FAKE_MAKE = """#!/bin/sh
echo "$*" >> "$FAKE_MAKE_LOG"
echo "child-out:$1"
echo "child-err:$1" >&2
[ "$1" != fail ]
"""


def _stub_bin(tmp_path: pathlib.Path, name: str, body: str) -> pathlib.Path:
    """Write ``tmp/bin/<name>`` as an executable script and return the directory holding it."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / name
    stub.write_text(body)
    stub.chmod(0o755)
    return bin_dir


def _run(
    script: pathlib.Path, args: list[str], bin_dir: pathlib.Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run ``script`` under bash with ``bin_dir`` first on PATH, stdout and stderr merged.

    One merged stream is what makes cross-stream ordering assertable: whether a child's stderr
    lands before or after the script's own `FAILED:` line is the buffering behaviour itself.
    """
    return subprocess.run(  # noqa: S603
        ["bash", str(script), *args],  # noqa: S607
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        timeout=60,
        env={**os.environ, **(env or {}), "PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )


# ── Scripts as files ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("script", [_PYO3_GUARD, _CHECK_STEPS], ids=lambda path: path.name)
def test_each_script_is_an_executable_bash_script(script: pathlib.Path) -> None:
    """The recipes run them by path, so the exec bit and the shebang are the launch contract."""
    assert script.is_file(), f"{script} is missing"
    assert script.stat().st_mode & 0o111, f"{script} is not executable"
    assert script.read_text().startswith("#!/usr/bin/env bash\n"), f"{script} does not start with a bash shebang"


@pytest.mark.parametrize(
    ("script", "args"),
    [
        (_PYO3_GUARD, ["--lane", "l", "--control", _CONTROL]),
        (_PYO3_GUARD, ["--lane", "l", "--control", _CONTROL, "--bogus", "//a:x"]),
        (_PYO3_GUARD, ["--control", _CONTROL, "//a:x"]),
        (_CHECK_STEPS, ["--make", "make", "--verbose", "0"]),
        (_CHECK_STEPS, ["--make", "make", "--verbose", "0", "--bogus", "x"]),
    ],
    ids=["guard-no-targets", "guard-unknown-option", "guard-no-lane", "steps-no-steps", "steps-unknown-option"],
)
def test_a_wrong_call_is_a_usage_error(tmp_path: pathlib.Path, script: pathlib.Path, args: list[str]) -> None:
    """Exit 2, distinct from a check failure — and never 0, which would be a gate checking nothing."""
    bin_dir = _stub_bin(tmp_path, "bazel", "#!/bin/sh\nexit 0\n")
    _stub_bin(tmp_path, "make", "#!/bin/sh\nexit 0\n")
    result = _run(script, args, bin_dir)
    assert result.returncode == 2, result.stdout
    assert "usage:" in result.stdout, result.stdout


# ── scripts/pyo3-guard ───────────────────────────────────────────────────────


class _Guard:
    """One pyo3-guard scenario: the fake `bazel`'s canned answers, and the run's log."""

    def __init__(self, tmp_path: pathlib.Path) -> None:
        self.dir = tmp_path / "fake-bazel"
        self.dir.mkdir()
        self.log = tmp_path / "bazel.log"
        self.bin_dir = _stub_bin(tmp_path, "bazel", _FAKE_BAZEL)
        self.answer("query", "\n".join(_TARGETS) + "\n")
        self.answer("union", f"{_CONTROL} (abc)\n//a:x (abc)\n//b:y (abc)\n")
        self.answer("single", f"{_CONTROL} (abc)\n")

    def answer(self, name: str, out: str, status: int | None = None) -> None:
        (self.dir / f"{name}.out").write_text(out)
        if status is not None:
            (self.dir / f"{name}.exit").write_text(f"{status}\n")

    def run(self, control: str = _CONTROL) -> subprocess.CompletedProcess[str]:
        args = ["--lane", "test-lane", "--control", control, "--cquery-flags", "--config lint", *_TARGETS]
        return _run(
            _PYO3_GUARD,
            args,
            self.bin_dir,
            {"FAKE_BAZEL_LOG": str(self.log), "FAKE_BAZEL_DIR": str(self.dir)},
        )

    def calls(self, verb: str) -> list[str]:
        lines = self.log.read_text().splitlines() if self.log.exists() else []
        return [line for line in lines if line.split(" ", 1)[0] == verb]


@pytest.fixture
def guard(tmp_path: pathlib.Path) -> _Guard:
    return _Guard(tmp_path)


def test_the_guard_passes_a_pyo3_free_union_with_one_query_and_one_cquery(guard: _Guard) -> None:
    """The green path: one loading-phase control, one configured cquery, and stderr kept quiet."""
    result = guard.run()
    assert result.returncode == 0, result.stdout
    assert len(guard.calls("query")) == 1, guard.log.read_text()
    assert len(guard.calls("cquery")) == 1, f"a green run pays one configured cquery: {guard.log.read_text()}"
    assert "test-lane: pyo3 absent from the union of 2 targets: //a:x //b:y" in result.stdout, result.stdout
    assert "fake-bazel-stderr" not in result.stdout, f"a passing run must not print Bazel's stderr: {result.stdout}"


def test_a_target_outside_the_control_fails_before_any_cquery(guard: _Guard) -> None:
    """Over a union one member satisfies the control for all; the rdeps check is per target."""
    guard.answer("query", "//a:x\n")
    result = guard.run()
    assert result.returncode == 1, result.stdout
    assert "//b:y does not reach" in result.stdout, result.stdout
    assert guard.calls("cquery") == [], guard.log.read_text()


def test_a_union_that_lacks_the_control_fails(guard: _Guard) -> None:
    """A cquery that printed nothing would otherwise pass `no pyo3` vacuously."""
    guard.answer("union", "//a:x (abc)\n//b:y (abc)\n")
    result = guard.run()
    assert result.returncode == 1, result.stdout
    assert "union cquery output lacks" in result.stdout, result.stdout
    assert "fake-bazel-stderr:cquery" in result.stdout, f"the failure must carry Bazel's stderr: {result.stdout}"


def test_a_pyo3_hit_is_attributed_per_target_and_fails(guard: _Guard) -> None:
    guard.answer("union", f"{_CONTROL} (abc)\n@fltk_crates//:pyo3 (abc)\n")
    guard.answer("single", f"{_CONTROL} (abc)\n@fltk_crates//:pyo3 (abc)\n")
    result = guard.run()
    assert result.returncode == 1, result.stdout
    assert "attributing per target" in result.stdout, result.stdout
    for target in _TARGETS:
        assert f"pyo3 present in the {target} Bazel graph" in result.stdout, result.stdout
    assert len(guard.calls("query")) == 1, guard.log.read_text()
    assert len(guard.calls("cquery")) == 3, guard.log.read_text()


def test_a_union_hit_the_attribution_cannot_reproduce_still_fails(guard: _Guard) -> None:
    """The union already proved pyo3 is reachable; the loop disagreeing is itself a bug."""
    guard.answer("union", f"{_CONTROL} (abc)\n@fltk_crates//:pyo3 (abc)\n")
    result = guard.run()
    assert result.returncode == 1, result.stdout
    assert "attributing per target" in result.stdout, result.stdout
    assert "pyo3 present in the //" not in result.stdout, result.stdout


@pytest.mark.parametrize("pyo3", [False, True], ids=["green", "attribution"])
def test_cquery_flags_reach_every_cquery_and_no_query(guard: _Guard, pyo3: bool) -> None:  # noqa: FBT001
    """The root lane's one-configuration rule, held behaviourally.

    Every configured invocation carries the gate's configuration, or it discards the analysis
    cache mid-gate; the control stays a loading-phase `query`, which takes none.
    """
    if pyo3:
        guard.answer("union", f"{_CONTROL} (abc)\n@fltk_crates//:pyo3 (abc)\n")
    guard.run()
    (query,) = guard.calls("query")
    assert "--config" not in query, f"the loading-phase control must not be configured: {query}"
    assert query == f"query rdeps(set(//a:x //b:y), {_CONTROL})", query
    cqueries = guard.calls("cquery")
    assert cqueries, guard.log.read_text()
    for cquery in cqueries:
        assert cquery.startswith("cquery --config lint "), f"a cquery ran without the configuration: {cquery}"
    assert cqueries[0] == "cquery --config lint deps(set(//a:x //b:y))", cqueries[0]


def test_a_failed_control_query_fails_with_its_stderr(guard: _Guard) -> None:
    guard.answer("query", "", status=1)
    result = guard.run()
    assert result.returncode == 1, result.stdout
    assert "rdeps query for the positive control failed" in result.stdout, result.stdout
    assert "fake-bazel-stderr:query" in result.stdout, result.stdout


def test_a_failed_union_cquery_fails_with_its_stderr(guard: _Guard) -> None:
    guard.answer("union", f"{_CONTROL} (abc)\n", status=1)
    result = guard.run()
    assert result.returncode == 1, result.stdout
    assert "union cquery over //a:x //b:y failed" in result.stdout, result.stdout
    assert "fake-bazel-stderr:cquery" in result.stdout, result.stdout


def test_a_failed_attribution_cquery_is_reported_and_the_loop_goes_on(guard: _Guard) -> None:
    """A per-target cquery error is reported, the loop continues to the next target, and the
    union's hit still fails the guard."""
    guard.answer("union", f"{_CONTROL} (abc)\n@fltk_crates//:pyo3 (abc)\n")
    guard.answer("single", "", status=1)
    result = guard.run()
    assert result.returncode == 1, result.stdout
    for target in _TARGETS:
        assert f"cquery for {target} failed" in result.stdout, result.stdout
    assert "fake-bazel-stderr:cquery" in result.stdout, result.stdout


def test_a_repository_prefixed_control_matches_its_canonical_spelling(guard: _Guard) -> None:
    """The consumer lane names `@fltk//…`; cquery prints it from the consumer as `@@fltk+//…`."""
    guard.answer("union", "@@fltk+//crates/fltk-cst-core:no_python (abc)\n//a:x (abc)\n")
    result = guard.run(control="@fltk//crates/fltk-cst-core:no_python")
    assert result.returncode == 0, result.stdout
    assert guard.calls("query") == ["query rdeps(set(//a:x //b:y), @fltk//crates/fltk-cst-core:no_python)"]


# ── scripts/check-steps ──────────────────────────────────────────────────────

_GREEN = ["bazel-toolchain-guard", "bazel-test", "bazel-lint", "x"]
_RED = ["pass", "fail", "sentinel"]
_SECONDS = r"\d+s"


def _steps(
    tmp_path: pathlib.Path, verbose: str, steps: list[str]
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run check-steps over ``steps`` with the fake make; return the result and make's argv log."""
    log = tmp_path / "make.log"
    bin_dir = _stub_bin(tmp_path, "make", _FAKE_MAKE)
    result = _run(
        _CHECK_STEPS,
        ["--make", "make", "--verbose", verbose, *steps],
        bin_dir,
        {"FAKE_MAKE_LOG": str(log)},
    )
    return result, log.read_text().splitlines() if log.exists() else []


def _index(lines: list[str], pattern: str) -> int:
    """The index of the one line matching ``pattern`` in full."""
    hits = [index for index, line in enumerate(lines) if re.fullmatch(pattern, line)]
    assert len(hits) == 1, f"{pattern!r} matched {len(hits)} lines: {lines}"
    return hits[0]


@pytest.mark.parametrize("verbose", ["0", "1"])
def test_a_green_gate_reports_every_step_in_order_and_the_trailer_last(tmp_path: pathlib.Path, verbose: str) -> None:
    result, calls = _steps(tmp_path, verbose, _GREEN)
    assert result.returncode == 0, result.stdout
    lines = result.stdout.splitlines()
    notes = {
        "bazel-test": re.escape(" [builds the lint surface too: same --config lint configuration]"),
        "bazel-lint": re.escape(
            " [same-configuration cache-hit confirmation plus the uncached ruff sweep of tests/bazel_consumer;"
            " lint's cost is in bazel-test]"
        ),
    }
    previous = -1
    for step in _GREEN:
        note = notes.get(step, "")
        running = _index(lines, rf"check-common: running {re.escape(step)}{note}")
        passed = _index(lines, rf"check-common: {re.escape(step)} passed in {_SECONDS}{note}")
        assert previous < running < passed, f"{step} is out of order: {lines}"
        previous = passed
    trailer = rf"check-common: all steps passed in {_SECONDS} \({' '.join(_GREEN)}\)"
    assert re.fullmatch(trailer, lines[-1]), f"the trailer must be the last line: {lines}"
    assert calls == _GREEN, f"make must be run once per step with the step as its sole argument: {calls}"


@pytest.mark.parametrize("verbose", ["0", "1"])
def test_the_first_failing_step_stops_the_gate(tmp_path: pathlib.Path, verbose: str) -> None:
    """The failure arm is what no green run enters; turning its `exit 1` into `:` reddens this."""
    result, calls = _steps(tmp_path, verbose, _RED)
    assert result.returncode != 0, result.stdout
    lines = result.stdout.splitlines()
    order = [
        _index(lines, "check-common: running pass"),
        _index(lines, rf"check-common: pass passed in {_SECONDS}"),
        _index(lines, "check-common: running fail"),
        _index(lines, rf"FAILED: fail after {_SECONDS} \(gate ran {_SECONDS}\)"),
    ]
    assert order == sorted(order), lines
    for absent in ("fail passed", "running sentinel", "child-out:sentinel", "all steps passed"):
        assert absent not in result.stdout, f"{absent!r} printed after a failed step: {result.stdout}"
    assert calls == ["pass", "fail"], calls


def test_quiet_mode_hides_passing_output_and_dumps_a_failure_after_its_line(tmp_path: pathlib.Path) -> None:
    (tmp_path / "green").mkdir()
    green, _ = _steps(tmp_path / "green", "0", _GREEN)
    assert "child-out:" not in green.stdout and "child-err:" not in green.stdout, green.stdout

    (tmp_path / "red").mkdir()
    red, _ = _steps(tmp_path / "red", "0", _RED)
    lines = red.stdout.splitlines()
    failed = _index(lines, rf"FAILED: fail after {_SECONDS} \(gate ran {_SECONDS}\)")
    assert _index(lines, "child-out:fail") > failed, f"the buffer must be dumped after the FAILED line: {lines}"
    assert _index(lines, "child-err:fail") > failed, f"the buffer must hold the step's stderr too: {lines}"
    assert "child-out:pass" not in red.stdout and "child-err:pass" not in red.stdout, red.stdout


def test_verbose_mode_streams_each_steps_output_while_it_runs(tmp_path: pathlib.Path) -> None:
    (tmp_path / "green").mkdir()
    green, _ = _steps(tmp_path / "green", "1", _GREEN)
    lines = green.stdout.splitlines()
    for step in _GREEN:
        running = _index(lines, rf"check-common: running {re.escape(step)}.*")
        passed = _index(lines, rf"check-common: {re.escape(step)} passed in .*")
        for marker in (f"child-out:{step}", f"child-err:{step}"):
            assert running < _index(lines, re.escape(marker)) < passed, f"{marker} is outside its step: {lines}"

    (tmp_path / "red").mkdir()
    red, _ = _steps(tmp_path / "red", "1", _RED)
    lines = red.stdout.splitlines()
    failed = _index(lines, rf"FAILED: fail after {_SECONDS} \(gate ran {_SECONDS}\)")
    assert _index(lines, "child-out:fail") < failed, f"verbose output must stream before the FAILED line: {lines}"
    assert _index(lines, "child-err:fail") < failed, lines
