"""The CLI surface the AST and serde guides print is checked against the CLI.

The guides tell out-of-tree consumers how to generate public API for their own code, so a
renamed flag, a dropped command or a Makefile target that stopped taking a variable is a
downstream break that no other test in the repo notices — nothing mechanically connects the
prose to `genparser` or to the Makefile.

Scope is the mechanical surface: command names, option spellings (in the invocations *and* in
each command's option table), Makefile target names and the variables those recipes read. The
semantic half is the compile gate's: the serde guide's worked example is a case in
`tests/test_generated_rust_gate.py`, and the last test here holds that case's generation input
to what the guide prints, so the compiled example and the printed one cannot drift apart.
"""

from __future__ import annotations

import pathlib
import re
import shlex

import pytest
import typer.main

from fltk.fegen.genparser import app
from tests.test_generated_rust_gate import SERDE_GUIDE_GRAMMAR, SERDE_GUIDE_SIDECAR

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
GUIDES = ("docs/ast-guide.md", "docs/rust-serde-guide.md")

# A flag token as written in an invocation or a table cell: --long-name or -o.
_FLAG = re.compile(r"^-{1,2}[A-Za-z][A-Za-z0-9-]*$")
_TABLE_FLAG = re.compile(r"--[a-z][a-z0-9-]*")
# "### `gen-rust-serde`" / "### `gen-ast` (Python backend)" — the section whose table
# documents that command's options.
_COMMAND_HEADING = re.compile(r"^(#{2,6})\s+.*`(gen-[a-z-]+)`")
_HEADING = re.compile(r"^(#{2,6})\s")


def _click_commands() -> dict[str, set[str]]:
    """Every genparser command mapped to the option spellings it accepts."""
    group = typer.main.get_command(app)
    commands = {}
    for name, command in group.commands.items():  # type: ignore[attr-defined]
        opts = {"--help"}
        for param in command.params:
            opts.update(param.opts)
            opts.update(param.secondary_opts)
        commands[name] = opts
    return commands


COMMANDS = _click_commands()
MAKEFILE = (REPO_ROOT / "Makefile").read_text()


_SHELL_FENCES = frozenset({"bash", "sh", "shell", "console"})


def _logical_lines(text: str) -> list[str]:
    """Shell-fenced code lines, with backslash continuations joined."""
    fenced: list[str] = []
    fence_info: str | None = None
    for raw in text.splitlines():
        if raw.startswith("```"):
            fence_info = None if fence_info is not None else raw[3:].strip()
            continue
        if fence_info in _SHELL_FENCES:
            fenced.append(raw)
    lines: list[str] = []
    pending = ""
    for line in fenced:
        stripped = line.strip()
        if stripped.endswith("\\"):
            pending += stripped[:-1] + " "
        else:
            lines.append(pending + stripped)
            pending = ""
    if pending:
        lines.append(pending)
    return lines


def _flags(tokens: list[str]) -> list[str]:
    """The option spellings in a token list, with any `=value` suffix dropped."""
    return [token.split("=", 1)[0] for token in tokens if _FLAG.match(token.split("=", 1)[0])]


def _guide_text(guide: str) -> str:
    return (REPO_ROOT / guide).read_text()


@pytest.mark.parametrize("guide", GUIDES)
def test_guide_genparser_invocations_use_real_commands_and_flags(guide: str) -> None:
    """Every `genparser <command> --flag` a guide prints exists on the CLI."""
    seen = 0
    for line in _logical_lines(_guide_text(guide)):
        if "fltk.fegen.genparser" not in line:
            continue
        tokens = shlex.split(line)
        index = next(i for i, token in enumerate(tokens) if token.endswith("genparser"))
        command = tokens[index + 1]
        assert command in COMMANDS, f"{guide}: `{command}` is not a genparser command"
        for flag in _flags(tokens[index + 2 :]):
            assert flag in COMMANDS[command], f"{guide}: `{command}` has no option `{flag}`"
        seen += 1
    assert seen, f"{guide}: no genparser invocation found — the extractor stopped matching"


@pytest.mark.parametrize("guide", GUIDES)
def test_guide_option_tables_document_real_flags(guide: str) -> None:
    """The option table under a `### \\`gen-*\\`` heading names that command's own options."""
    command: str | None = None
    command_depth = 0
    seen = 0
    for line in _guide_text(guide).splitlines():
        heading = _HEADING.match(line)
        if heading:
            named = _COMMAND_HEADING.match(line)
            if named:
                command = named.group(2)
                command_depth = len(named.group(1))
            elif command is not None and len(heading.group(1)) <= command_depth:
                # A heading at or above the command's own level ends its section.
                command = None
            continue
        if command is None or not line.startswith("|"):
            continue
        first_cell = line.split("|")[1]
        for flag in _TABLE_FLAG.findall(first_cell):
            assert command in COMMANDS, f"{guide}: `{command}` is not a genparser command"
            assert flag in COMMANDS[command], f"{guide}: `{command}` has no option `{flag}`"
            seen += 1
    assert seen, f"{guide}: no documented option rows found — the extractor stopped matching"


def _fenced_blocks_after(text: str, marker: str) -> list[str]:
    """The fenced code blocks following the first line containing `marker`, in order."""
    blocks: list[str] = []
    current: list[str] | None = None
    reached = False
    for raw in text.splitlines():
        if not reached:
            reached = marker in raw
            continue
        if raw.startswith("```"):
            if current is None:
                current = []
            else:
                blocks.append("".join(f"{line}\n" for line in current))
                current = None
            continue
        if current is not None:
            current.append(raw)
    return blocks


def test_the_serde_guides_worked_example_is_the_one_the_gate_compiles() -> None:
    """The grammar and sidecar the guide prints are the compile gate's `serde_guide` case.

    The example is what a Clockwork-shaped consumer copies; it shipped once with a sidecar that
    failed at generation time. The gate case is what makes it run — this is the join.
    """
    blocks = _fenced_blocks_after(_guide_text("docs/rust-serde-guide.md"), "**After**")
    assert len(blocks) >= 2, "the worked example's After grammar and sidecar blocks must be there"
    assert blocks[0] == SERDE_GUIDE_GRAMMAR, "the printed grammar is not the one the gate compiles"
    assert blocks[1] == SERDE_GUIDE_SIDECAR, "the printed sidecar is not the one the gate compiles"


@pytest.mark.parametrize("guide", GUIDES)
def test_guide_make_recipes_name_real_targets_and_variables(guide: str) -> None:
    """A `make gen-… VAR=…` recipe names a Makefile target that reads every variable it sets."""
    seen = 0
    for line in _logical_lines(_guide_text(guide)):
        tokens = shlex.split(line)
        if not tokens or tokens[0] != "make":
            continue
        target = tokens[1]
        assert re.search(rf"^{re.escape(target)}:", MAKEFILE, re.MULTILINE), (
            f"{guide}: the Makefile has no `{target}` target"
        )
        for assignment in tokens[2:]:
            variable, _, value = assignment.partition("=")
            assert f"$({variable})" in MAKEFILE, f"{guide}: the Makefile never reads $({variable})"
            if variable == "EXTRA_ARGS":
                # The Makefile targets are named after the command they run, so the flags a
                # recipe forwards are that command's.
                for flag in _flags(shlex.split(value)):
                    assert flag in COMMANDS[target], f"{guide}: `{target}` has no option `{flag}`"
        seen += 1
    assert seen, f"{guide}: no make recipe found — the extractor stopped matching"
