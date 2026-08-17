"""The one `uv` matcher, shared by every retirement gate.

uv is retired, and three surfaces have to stay clear of it: the prose docs and checked-in editor
launchers (`test_uv_retirement.py`), the Makefile recipes (`test_check_step_order.py`) and the CI
workflow (`test_ci_workflow.py`). Self-tested in `test_uv_retirement.py`.

Only *invocations and artifacts* match. Prose is free to say uv was retired, and `CHANGELOG.md`
is free to record that it was once adopted; what may not survive is a command a reader could run
or a workflow step a machine does run.
"""

from __future__ import annotations

import pathlib
import re

from tests import retirement_scan as scan

# Requiring a subcommand makes this an invocation matcher, not a word matcher: prose about uv
# reads "uv" or "uv's", never "uv run".  The separator is any whitespace, so a tab-indented
# `uv	lock` in a Makefile recipe is not a hole.  The alternation is uv's whole top-level
# command set, not just the subcommands this repo used to call: a recipe reaching for a
# different one is the same violation.
UV_INVOCATION = re.compile(
    r"(?<![\w./-])uv\s+"
    r"(?:run|sync|lock|pip|export|add|remove|venv|python|tool|build|init|publish|tree|self|cache|format)\b"
)

# Invocation-like spellings that lack the `uv <subcommand>` shape: `uvx` (one token, and the
# form uv's own docs teach for running a tool without a project), the lockfile, the bare
# `--project` form, the argv-array form the VS Code clients used, and the CI setup action
# (whose hyphen puts it out of reach of the lookbehind above).
UV_ARTIFACT = re.compile(
    r"(?<![\w./-])uvx\b|(?<![\w./-])uv\.lock\b|(?<![\w./-])uv\s+--project\b"
    r"|\"uv\" *,|\bsetup-uv\b|\bastral-sh/uv\b"
)


def names_uv(line: str) -> bool:
    """True when the line invokes uv or names one of its artifacts."""
    return bool(UV_INVOCATION.search(line) or UV_ARTIFACT.search(line))


def offenders(paths: list[pathlib.Path], root: pathlib.Path) -> list[str]:
    """Every `<path>:<lineno>: <line>` in `paths` that names uv, reported relative to `root`.

    Raw lines, comments included: the surfaces this gate scans are prose docs and launcher
    scripts, and the matcher already requires an invocation shape, so a documented recipe is a
    hit worth reporting rather than noise to strip.
    """
    return scan.offenders(paths, root, names_uv)
