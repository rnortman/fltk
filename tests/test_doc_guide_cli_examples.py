"""What the AST and serde guides print is checked against the CLI, and run.

The guides tell out-of-tree consumers how to generate public API for their own code, so a
renamed flag or a dropped command is a downstream break that no other test in the repo notices
— nothing mechanically connects the prose to `genparser`.

Two things are pinned here:

- The mechanical surface: command names and option spellings, in the invocations *and* in each
  command's option table.
- The runnable examples, which are the path a consumer copies whole. The serde guide's worked
  example and the AST guide's quick start are cases in `tests/test_generated_rust_gate.py`, and
  the join tests here hold what those cases compile to what the guides print, so the compiled
  example and the printed one cannot drift apart. For the AST quick start that is the printed Rust
  body as well as the generation input — the gate wraps the printed block itself rather than a
  mirror of it — plus the names its shape comments claim, which are the half of the block rustc
  ignores. The Python quick start has no compile gate to join to, so it runs here: the printed
  invocations generate a package and the printed snippet imports and parses through it, which is
  what fails when a printed module path is wrong.

Block lookups are keyed by the guide's own structure — a `###` subsection and a fence language —
never by position, and never by a string the test also judges: a wrong printed module path has to
fail in the execution that exercises it, not in the guard that found the block.

Deliberately not pinned: the guides' non-runnable prose — option-table default values, shape
tables, inline grammar fragments illustrating one statement. Pinning prose semantics
mechanically means either executing every fragment (a test suite the size of the guides, mostly
asserting nothing a consumer copies whole) or string-matching sentences, which is drift-prone in
the opposite direction: a correct edit breaks the test. Residual prose defects stay a
human-review matter.
"""

from __future__ import annotations

import importlib
import pathlib
import re
import shlex
import sys

import pytest
import typer.main
from typer.testing import CliRunner

from fltk.fegen.genparser import app
from tests.test_generated_rust_gate import (
    AST_GUIDE_GRAMMAR,
    AST_GUIDE_RUNTIME,
    AST_GUIDE_SIDECAR,
    AST_GUIDE_SNIPPET,
    SERDE_GUIDE_GRAMMAR,
    SERDE_GUIDE_SIDECAR,
)

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


_SHELL_FENCES = frozenset({"bash", "sh", "shell", "console"})


def _join_continuations(lines: list[str]) -> list[str]:
    """Shell lines with backslash continuations joined into one logical line each."""
    joined: list[str] = []
    pending = ""
    for line in lines:
        stripped = line.strip()
        if stripped.endswith("\\"):
            pending += stripped[:-1] + " "
        else:
            joined.append(pending + stripped)
            pending = ""
    if pending:
        joined.append(pending)
    return joined


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
    return _join_continuations(fenced)


def _flags(tokens: list[str]) -> list[str]:
    """The option spellings in a token list, with any `=value` suffix dropped."""
    return [token.split("=", 1)[0] for token in tokens if _FLAG.match(token.split("=", 1)[0])]


# The label the guides launch the generator by. Everything before it is Bazel's own argv
# (`bazel run --run_under=... `), and the `--` after it separates Bazel's flags from the CLI's.
_GENPARSER_LABEL = "@fltk//:genparser"


def _genparser_argv(line: str) -> list[str] | None:
    """The genparser argv a printed shell line carries, or None if it invokes something else."""
    if _GENPARSER_LABEL not in line:
        return None
    tokens = shlex.split(line)
    index = tokens.index(_GENPARSER_LABEL)
    argv = tokens[index + 1 :]
    assert argv and argv[0] == "--", (
        f"`{line}`: a `bazel run` invocation must separate the CLI's arguments with `--`, or Bazel eats them"
    )
    return argv[1:]


def _guide_text(guide: str) -> str:
    return (REPO_ROOT / guide).read_text()


@pytest.mark.parametrize("guide", GUIDES)
def test_guide_genparser_invocations_use_real_commands_and_flags(guide: str) -> None:
    """Every `genparser <command> --flag` a guide prints exists on the CLI."""
    seen = 0
    for line in _logical_lines(_guide_text(guide)):
        argv = _genparser_argv(line)
        if argv is None:
            continue
        command = argv[0]
        assert command in COMMANDS, f"{guide}: `{command}` is not a genparser command"
        for flag in _flags(argv[1:]):
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


_H2 = re.compile(r"^## ")
_H3 = re.compile(r"^### (.+)")


def _fenced_blocks_after(text: str, marker: str) -> list[tuple[str, str, str]]:
    """Each fenced block after the first line containing `marker`, in order.

    One entry per block: the `###` subsection it sits under (empty above the first), its fence
    language, and its body. Extraction stops at the next `##`, so a block from a later section of
    the guide cannot drift into a lookup here.
    """
    blocks: list[tuple[str, str, str]] = []
    current: list[str] | None = None
    section = ""
    language = ""
    reached = False
    for raw in text.splitlines():
        if not reached:
            reached = marker in raw
            continue
        if current is None:
            if _H2.match(raw):
                break
            subsection = _H3.match(raw)
            if subsection:
                section = subsection.group(1).strip()
        if raw.startswith("```"):
            if current is None:
                current, language = [], raw[3:].strip()
            else:
                blocks.append((section, language, "".join(f"{line}\n" for line in current)))
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
    blocks = [body for _, language, body in _fenced_blocks_after(_guide_text("docs/rust-serde-guide.md"), "**After**")]
    assert len(blocks) >= 2, "the worked example's After grammar and sidecar blocks must be there"
    assert blocks[0] == SERDE_GUIDE_GRAMMAR, "the printed grammar is not the one the gate compiles"
    assert blocks[1] == SERDE_GUIDE_SIDECAR, "the printed sidecar is not the one the gate compiles"


_QUICK_START_MARKER = "## Quick start"
_GRAMMAR_FILE = "calc.fltkg"
_SIDECAR_FILE = "calc.fltkast"

_RUST_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# The keywords a printed `pub struct … { … }` / `pub enum … { … }` shape comment spells; everything
# else in one is a name the emitted module has to carry.
_SHAPE_COMMENT_KEYWORDS = frozenset({"pub", "enum", "struct"})

# What the quick start is made of, as (subsection, fence language) -> block count. The lookups
# below are keyed by this rather than by position, so nothing a test asserts about a block's
# *content* also decides which block it read: a wrong printed module path has to fail in the
# execution that judges it, not in an extractor guard that happened to name the same string.
_QUICK_START_SHAPE = {
    ("Rust", ""): 2,  # the grammar and the sidecar, in that order
    ("Rust", "bash"): 1,
    ("Rust", "rust"): 1,
    ("Python", "bash"): 1,
    ("Python", "python"): 1,
}


def _quick_start_blocks() -> dict[tuple[str, str], list[str]]:
    """The AST guide's quick-start code blocks, keyed by subsection and fence language."""
    grouped: dict[tuple[str, str], list[str]] = {}
    for section, language, body in _fenced_blocks_after(_guide_text("docs/ast-guide.md"), _QUICK_START_MARKER):
        grouped.setdefault((section, language), []).append(body)
    shape = {key: len(bodies) for key, bodies in grouped.items()}
    assert shape == _QUICK_START_SHAPE, f"the quick start's blocks moved: {shape}"
    return grouped


def test_the_ast_guides_quick_start_is_the_one_the_gate_compiles() -> None:
    """Every Rust block the AST guide's quick start prints is the compile gate's `ast_guide` case.

    The quick start is the first thing a consumer copies: the grammar and sidecar are the case's
    generation input, and the snippet is the body the case compiles and runs — so the printed Rust
    is the Rust rustc saw, not a mirror of it that can go stale on a renamed variant or a moved
    field. This is the join.
    """
    blocks = _quick_start_blocks()
    grammar, sidecar = blocks[("Rust", "")]
    assert grammar == AST_GUIDE_GRAMMAR, "the printed grammar is not the one the gate compiles"
    assert sidecar == AST_GUIDE_SIDECAR, "the printed sidecar is not the one the gate compiles"
    (snippet,) = blocks[("Rust", "rust")]
    assert snippet == AST_GUIDE_SNIPPET, "the printed snippet is not the one the gate compiles"

    # The snippet opens with two comments printing the emitted shapes, and a comment is the half of
    # the block rustc ignores. The gate's own assertions annotate each of those names against the
    # emitted type, so requiring every printed name to appear in that hand-written half is what
    # makes a printed shape nobody checks fail here.
    checked = AST_GUIDE_RUNTIME.replace(AST_GUIDE_SNIPPET, "")
    printed = {
        name for line in snippet.splitlines() if line.startswith("//") for name in _RUST_IDENTIFIER.findall(line)
    } - _SHAPE_COMMENT_KEYWORDS
    unchecked = sorted(name for name in printed if not re.search(rf"\b{name}\b", checked))
    assert not unchecked, f"the printed shape comments name types the gate never checks: {unchecked}"


def test_the_ast_guides_python_quick_start_runs_as_printed(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Python quick start's printed commands generate a package its printed snippet imports.

    The Rust half has the compile gate; the Python half has only this. It shipped once with a
    module path that raised `ModuleNotFoundError` on the printed import — a defect no lint and no
    in-tree consumer sees, because every other test drives generated modules from a path it
    chooses itself rather than the one the guide prints.
    """
    blocks = _quick_start_blocks()
    (commands,) = blocks[("Python", "bash")]
    (snippet,) = blocks[("Python", "python")]
    grammar, sidecar = blocks[("Rust", "")]

    (tmp_path / _GRAMMAR_FILE).write_text(grammar)
    (tmp_path / _SIDECAR_FILE).write_text(sidecar)
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    invocations = 0
    for line in _join_continuations(commands.splitlines()):
        argv = _genparser_argv(line)
        if argv is None:
            continue
        result = runner.invoke(app, argv)
        assert result.exit_code == 0, f"`{line}` failed:\n{result.output}\n{result.exception}"
        invocations += 1
    assert invocations == 2, "the Python quick start prints a `generate` and a `gen-ast` invocation"

    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    namespace: dict[str, object] = {}
    try:
        # The snippet as printed: its import lines are the thing under test, so it is executed
        # rather than paraphrased.
        exec(compile(snippet, "docs/ast-guide.md quick start", "exec"), namespace)  # noqa: S102
    finally:
        # The generated package lives in a tmp_path about to disappear; leaving it in sys.modules
        # would hand a later importer modules whose source files are gone.
        for name in [name for name in sys.modules if name == "calc" or name.startswith("calc.")]:
            sys.modules.pop(name, None)

    expr_binary = namespace["ExprBinary"]
    assert isinstance(expr_binary, type), "the snippet imports the link dataclass it tests against"
    value = namespace["value"]
    assert isinstance(value, expr_binary), "the printed isinstance arm is the one taken"
    assert value.op.name == "MINUS", "the outer link of a left fold carries the last operator"
    assert (value.lhs.lhs, value.lhs.rhs, value.rhs) == (1, 2, 3), "the operands coerce in source order"
