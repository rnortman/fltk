"""The CI workflow's two obligations that `make check-ci` cannot express itself.

CI runs `make check-ci` and nothing else, so the gate's *contents* stay in sync with the local
lane by construction. Two things about the runner do not:

- **No uv.** The workflow must not use uv: a setup step would introduce a second Python
  dependency writer alongside `bazel run //:requirements.update`, in the one lane a developer
  never runs locally.
- **A warm cargo registry.** The three compile-gate tests resolve `--offline`, and no check step
  populates the registry cache, so the workflow must fetch explicitly before the gate runs.
  Without it those tests fail in CI alone, with a resolution error that names nothing about the
  change under test.
"""

from __future__ import annotations

import pathlib
import re

from tests.uv_scan import names_uv

_WORKFLOW = pathlib.Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"

_KEY = re.compile(r"^(\s*)(?:- )?[\w-]+:")


def _lines() -> list[str]:
    return _WORKFLOW.read_text().splitlines()


def _code_lines() -> list[str]:
    """`ci.yml` with comments stripped.

    The workflow narrates itself heavily — the cache step's comment names `cargo fetch
    --locked` in prose — so a raw substring search over the file is satisfied by a comment
    that outlives the step it describes. Nothing in this file puts `#` inside a value.
    """
    return [re.sub(r"(?:^|\s)#.*$", "", line) for line in _lines()]


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


def test_the_registry_is_warmed_before_the_gate_runs() -> None:
    """Asserted over the steps' commands, not the file's lines.

    A line search is satisfied by a comment naming the command, or by a step gated off with
    `if:` — both of which leave the gates resolving `--offline` against a cold registry, and
    the failure shows up in CI alone as a resolution error naming nothing about the change.
    """
    assert _index_of_run("cargo fetch --locked") < _index_of_run("make check-ci"), (
        "`cargo fetch --locked` must run before `make check-ci`"
    )


def test_the_step_parser_sees_the_real_steps() -> None:
    """The parser above decides what the gate examines; an empty parse would pass vacuously."""
    steps = _steps()
    assert len(steps) >= 6, steps
    assert [step for step in steps if "checkout@" in "\n".join(step)], "the checkout step went missing"
    assert not _run(_steps()[0]), "the checkout step is a `uses:` step and has no command"
    conditional = [index for index, step in enumerate(steps) if _is_conditional(step)]
    assert conditional, "no `if:` step found, so `_is_conditional` is never exercised here"


def test_the_registry_cache_is_keyed_on_the_lock() -> None:
    """A cache keyed on anything else serves a stale index for a dependency bump."""
    assert "cargo-registry-${{ runner.os }}-${{ hashFiles('Cargo.lock') }}" in _WORKFLOW.read_text()
