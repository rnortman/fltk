"""The CI workflow's obligations that `make check-ci` cannot express itself.

CI runs `make check-ci` and nothing else, so the gate's *contents* stay in sync with the local
lane by construction. Three things about the runner do not:

- **No uv.** The workflow must not use uv: a setup step would introduce a second Python
  dependency writer alongside `bazel run //:requirements.update`, in the one lane a developer
  never runs locally.
- **No cargo and no rustup.** The gate builds and tests everything through Bazel's own
  hermetic Rust toolchain. A toolchain install, a registry cache or a fetch step here would be
  the runner quietly re-acquiring the host cargo this repo retired, and the first test to
  reach for it would pass in CI and nowhere else.
- **The failing run's evidence.** `--test_output=errors` puts a failing target's log in the
  step output, but multi-megabyte logs, `test.xml` files and undeclared outputs live only in
  the `bazel-testlogs` tree, which dies with the runner. An `if: failure()` upload step after
  the gate is what makes a CI-only failure diagnosable at all.
"""

from __future__ import annotations

import pathlib
import re

from tests.cargo_scan import names_cargo
from tests.retirement_scan import uncommented
from tests.uv_scan import names_uv

_WORKFLOW = pathlib.Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"

_KEY = re.compile(r"^(\s*)(?:- )?[\w-]+:")


def _lines() -> list[str]:
    return _WORKFLOW.read_text().splitlines()


def _code_lines() -> list[str]:
    """`ci.yml` with comments stripped, which is what the step parser below reads.

    The workflow explains retired steps in prose, and that prose has the shape of an
    invocation. A raw substring search would match the explanation rather than a live
    command. Nothing in this file puts `#` inside a value.
    """
    return uncommented(_WORKFLOW)


def _steps() -> list[list[str]]:
    """The `steps:` list of the single job, one entry per step, comments already stripped."""
    lines = _code_lines()
    start = next(index for index, line in enumerate(lines) if line.strip() == "steps:")
    item_indent: int | None = None
    steps: list[list[str]] = []
    for line in lines[start + 1 :]:
        indent = len(line) - len(line.lstrip())
        if line.strip().startswith("- ") and item_indent in (None, indent):
            item_indent = indent
            steps.append([line])
        elif not steps:
            continue
        elif not line.strip() or indent > (item_indent or 0):
            steps[-1].append(line)
        else:
            break
    return steps


def _run(step: list[str]) -> str:
    """The step's `run:` command, inline or block scalar; empty for a `uses:` step."""
    body: list[str] = []
    run_indent: int | None = None
    for line in step:
        if run_indent is None:
            match = re.match(r"^(\s*)(- )?run:(.*)$", line)
            if match:
                # A `- run:` opens the step, so its key sits two columns right of the dash.
                run_indent = len(match.group(1)) + (2 if match.group(2) else 0)
                body.append(match.group(3))
            continue
        indent = len(line) - len(line.lstrip())
        if line.strip() and indent <= run_indent and _KEY.match(line):
            break
        body.append(line)
    return "\n".join(body)


def _is_conditional(step: list[str]) -> bool:
    return any(re.match(r"^\s*(?:- )?if:", line) for line in step)


def _index_of_run(needle: str) -> int:
    """The position of the unconditional step whose command contains `needle`."""
    matches = [index for index, step in enumerate(_steps()) if needle in _run(step) and not _is_conditional(step)]
    assert matches, f"no unconditional step runs `{needle}`"
    return matches[0]


def test_the_workflow_does_not_use_uv() -> None:
    """Matching the bare word would redden this gate on a comment saying uv was retired —
    the wrong reason, in the one lane a developer never runs locally.
    """
    offenders = [line for line in _lines() if names_uv(line)]
    assert not offenders, f"uv is retired but the CI workflow still invokes it: {offenders}"


def test_the_workflow_neither_installs_nor_runs_cargo() -> None:
    """Comments are stripped first: the steps this replaces are described in prose above it.

    Both halves matter. A `run:` naming cargo is the direct violation; a `uses:` pulling in a
    toolchain installer is the indirect one, and it is what makes the direct one possible.
    """
    offenders = [line for line in _code_lines() if names_cargo(line) or "rust-toolchain@" in line]
    assert not offenders, f"cargo is retired but the CI workflow still reaches for it: {offenders}"


def test_nothing_installs_a_language_toolchain_before_the_gate() -> None:
    """Setup before the gate is where a second, CI-only environment gets assembled.

    The Bazel disk cache step is legitimate — it is a cache, and correctness does not depend
    on a hit. An installer is not: whatever it puts on `PATH` is a tool the local lane does
    not have, so a step that reaches for it passes in exactly one place.
    """
    installers = [step for step in _steps()[: _index_of_run("make check-ci")] if _installs_a_toolchain(step)]
    assert not installers, f"a toolchain installer runs before the gate: {installers}"


def test_the_installer_matcher_recognizes_the_steps_it_retired() -> None:
    """A negative assertion over a clean file passes just as well with a typo in its pattern."""
    retired = (
        ["      - uses: dtolnay/rust-toolchain@e97e2d8cc328f1b50210efc529dca0028893a2d9  # v1"],
        ["      - name: Install Rust", "        run: rustup toolchain install stable"],
        ["      - uses: actions/setup-python@v5"],
        ["      - uses: astral-sh/setup-uv@v5"],
        ["      - name: Install", "        run: curl -LsSf https://example/install.sh | sh"],
        ["      - name: Deps", "        run: sudo apt-get install -y lcov"],
        ["      - name: Tools", "        run: pip install ruff"],
    )
    for step in retired:
        assert _installs_a_toolchain(step), f"installer matcher missed: {step}"

    allowed = (
        ["      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1"],
        ["      - uses: actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9  # v6.1.0"],
        ["      - name: Run checks", "        run: make check-ci"],
    )
    for step in allowed:
        assert not _installs_a_toolchain(step), f"installer matcher over-matched: {step}"


def _installs_a_toolchain(step: list[str]) -> bool:
    """True when the step installs a language toolchain or a tool onto the runner."""
    return bool(
        re.search(r"(?:^|\s)(?:apt-get|pip install|npm install|rustup|curl .*\|\s*sh)", _run(step))
        or re.search(r"uses:.*(?:setup-|rust-toolchain@)", "\n".join(step))
    )


def _artifact_path(step: list[str]) -> str:
    """The `path:` value of an `upload-artifact` step."""
    match = re.search(r"^\s*path:\s*(\S+)\s*$", "\n".join(step), re.MULTILINE)
    assert match, f"the upload step declares no path: {step}"
    return match.group(1)


def test_the_failing_run_collects_and_uploads_its_test_logs() -> None:
    """The two steps that make a CI-only failure diagnosable, joined to each other.

    The collect step resolves each workspace's `bazel-testlogs` symlink into a directory and
    the upload step ships that directory. Asserted as a pair, and on the directory name rather
    than on a literal this test also owns: with the upload alone pinned, renaming or breaking
    the collect step uploads nothing, and `continue-on-error` plus `if-no-files-found: ignore`
    make that silent — the exact blindness these steps were added to remove.
    """
    steps = _steps()
    gate = _index_of_run("make check-ci")
    collects = [
        index
        for index, step in enumerate(steps)
        if "bazel info bazel-testlogs" in _run(step) and any("if: failure()" in line for line in step)
    ]
    assert collects, "no `if: failure()` step resolves bazel-testlogs, so there is nothing to upload"
    assert collects[0] > gate, "the collect step must follow the gate that produces the logs"

    collected = _run(steps[collects[0]])
    assert "tests/bazel_consumer" in collected, "the consumer lane is its own workspace and has its own testlogs"

    uploads = [
        index
        for index, step in enumerate(steps)
        if "upload-artifact@" in "\n".join(step) and any("if: failure()" in line for line in step)
    ]
    assert uploads, "no `if: failure()` upload step, so a failing run's test logs die with the runner"
    assert uploads[0] > collects[0], "the upload step must follow the collect step"

    path = _artifact_path(steps[uploads[0]])
    assert path in collected, f"the collect step writes nothing to {path}, which is what the upload ships"


def test_the_step_parser_sees_the_real_steps() -> None:
    """The parser above decides what the gate examines; an empty parse would pass vacuously."""
    steps = _steps()
    assert len(steps) >= 6, steps
    assert [step for step in steps if "checkout@" in "\n".join(step)], "the checkout step went missing"
    assert not _run(_steps()[0]), "the checkout step is a `uses:` step and has no command"
    conditional = [index for index, step in enumerate(steps) if _is_conditional(step)]
    assert conditional, "no `if:` step found, so `_is_conditional` is never exercised here"


def test_the_bazel_disk_cache_is_keyed_on_what_changes_its_contents() -> None:
    """A key missing a lock serves artifacts built from a different dependency graph.

    Performance-only, so a miss is not a correctness problem — but a key that never changes
    is a cache that grows a generation per commit and evicts itself. Read out of the `key:`
    line's own `hashFiles(...)` argument list: a search of the whole file is satisfied by a
    comment naming the file, which is not a key at all.
    """
    key = next((line for line in _code_lines() if re.match(r"^\s*key:", line)), None)
    assert key, "the Bazel disk cache step declares no key"
    hashed = re.search(r"hashFiles\(([^)]*)\)", key)
    assert hashed, f"the cache key hashes no files, so it never changes: {key}"
    files = {name.strip().strip("'\"") for name in hashed.group(1).split(",")}
    for keyed in (
        ".bazelversion",
        "MODULE.bazel",
        "MODULE.bazel.lock",
        "tests/bazel_consumer/MODULE.bazel",
        "tests/bazel_consumer/MODULE.bazel.lock",
        "cargo-bazel-lock.json",
        "tests/bazel_consumer/cargo-bazel-lock.json",
    ):
        assert keyed in files, f"the Bazel disk cache key ignores {keyed}: {sorted(files)}"
