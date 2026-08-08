"""Pytest session setup that must run before any test module imports Typer.

Typer reads its terminal-forcing decision once, at import time
(`typer.rich_utils.FORCE_TERMINAL`), and turns styling *on* whenever
`GITHUB_ACTIONS`, `FORCE_COLOR`, or `PY_COLORS` is set. Under CI that makes rich
decorate CLI error text token by token, so an option name like `--ast-config`
reaches `CliRunner.result.output` as several ANSI-separated fragments and a
plain substring assertion that passes on a developer machine fails on CI.
`_TYPER_FORCE_DISABLE_TERMINAL` overrides all three, so CLI output is plain
everywhere and the two environments agree.
"""

import os

os.environ["_TYPER_FORCE_DISABLE_TERMINAL"] = "1"
