"""The two bootstrap writers emit a CST module and its protocol module as a pair.

`fltk/fegen/bootstrap.py` (hand-written GSM) and `runbs.py` (bootstrap grammar file) are the
regeneration path used after a bootstrap-grammar change. The CST module they write imports its
NodeKind from `<cst_module>_protocol`, so writing only the CST module leaves it paired with
whatever protocol module happens to be on disk: a fresh rule fails at import with a bare
`AttributeError` inside a dataclass body, and merely renamed rules silently reuse the wrong enum.
These run the writers as scripts, the way a maintainer does. Both entry points share one writer
(`fltk.fegen.emit.write_generated_modules`), so if either test below goes red for the pair
invariant, both do.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import typing

import pytest

from fltk import plumbing
from fltk.fegen import emit, gsm2tree

# The scripts below are run as subprocesses with this as their working directory, so it has to be
# the runfiles root — which is what this is under Bazel, pytest reporting the collected file's
# unresolved path.  The spawns must stay `-m runbs`: `python runbs.py` puts the *resolved* script
# directory first on sys.path, and from the source tree `fltk.fegen` has no generated modules.
_REPO_ROOT = pathlib.Path(__file__).parent.parent

_PARSE_BOOTSTRAP_GRAMMAR = """
import sys
sys.path.insert(0, {tmp!r})
import bs_parser
from fltk.fegen.pyrt import terminalsrc

terminals = terminalsrc.TerminalSource(open({grammar!r}).read())
result = bs_parser.Parser(terminalsrc=terminals).apply__parse_grammar(0)
assert result is not None, "the recovered parser rejected the bootstrap grammar"
assert result.pos == len(terminals.terminals), (
    f"the recovered parser consumed {{result.pos}} of {{len(terminals.terminals)}} terminals"
)
"""


def _assert_pair(cst_file: pathlib.Path, protocol_file: pathlib.Path, module_name: str) -> None:
    assert cst_file.exists(), f"{cst_file.name} was not written"
    assert protocol_file.exists(), f"{protocol_file.name} was not written beside {cst_file.name}"
    assert f"from {module_name}_protocol import NodeKind" in cst_file.read_text()
    assert "class NodeKind" in protocol_file.read_text()


def _run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, interpreter and repo paths only
        argv,
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _class_body(module_text: str, class_name: str) -> str:
    """The source of one generated class, from its `class` line to the next top-level statement."""
    start = module_text.index(f"class {class_name}:")
    end = module_text.find("\nclass ", start + 1)
    body = module_text[start:] if end == -1 else module_text[start:end]
    assert body.count("\n") > 5, f"the slice for {class_name} is implausibly short"
    return body


def test_bootstrap_py_renders_all_three_modules(tmp_path: pathlib.Path) -> None:
    """`fltk/fegen/bootstrap.py` run as a script writes a parser, a CST module and its protocol.

    This is the recovery path for a lost `bootstrap_parser`: every other regeneration route parses
    a grammar file, which needs the parser this one writes.
    """
    parser_file = tmp_path / "bs_parser.py"
    cst_file = tmp_path / "bs_cst.py"
    result = _run([sys.executable, "-m", "fltk.fegen.bootstrap", str(parser_file), str(cst_file), "bs_cst"])
    assert result.returncode == 0, result.stderr
    assert parser_file.exists(), "the parser module was not written"
    _assert_pair(cst_file, tmp_path / "bs_cst_protocol.py", "bs_cst")

    grammar = _REPO_ROOT / "fltk" / "fegen" / "bootstrap.fltkg"
    check = _run(
        [
            sys.executable,
            "-c",
            _PARSE_BOOTSTRAP_GRAMMAR.format(tmp=str(tmp_path), grammar=str(grammar)),
        ]
    )
    assert check.returncode == 0, check.stderr


def test_runbs_writes_the_protocol_module_beside_the_cst_module(tmp_path: pathlib.Path) -> None:
    grammar = _REPO_ROOT / "fltk" / "fegen" / "bootstrap.fltkg"
    if not grammar.exists():  # pragma: no cover - the grammar is committed
        pytest.skip("bootstrap grammar missing")
    parser_file = tmp_path / "bs_parser.py"
    cst_file = tmp_path / "bs_cst.py"
    # `-m runbs` rather than the `runbs.py` path a maintainer types: a script path makes
    # sys.path[0] the script's directory *with symlinks resolved*, and every runfiles entry for
    # a tracked file resolves back into the checkout — where the generated modules runbs.py
    # imports do not exist.  `-m` uses the working directory as given.
    result = _run([sys.executable, "-m", "runbs", str(grammar), str(parser_file), str(cst_file), "bs_cst"])
    assert result.returncode == 0, result.stderr
    _assert_pair(cst_file, tmp_path / "bs_cst_protocol.py", "bs_cst")

    # The writer classifies trivia rules, which `runbs.py` did not do on its own. A rule reachable
    # only from `_trivia` is classified as trivia, and trivia-classified rules drop `Trivia` from
    # every other node's child union — the observable marker that the classification ran.
    line_comment = _class_body(cst_file.read_text(), "LineComment")
    assert "Trivia" not in line_comment, "the emitted grammar was not run through classify_trivia_rules"


def test_a_grammar_with_no_trivia_rule_is_augmented_and_written(tmp_path: pathlib.Path) -> None:
    """The writer augments its input, so a grammar lacking `_trivia` generates instead of raising.

    `ParserGenerator` refuses such a grammar ("Expected _trivia rule to exist for parsing"); the
    hand-written bootstrap seed is one, which is why the augmentation lives in the writer.
    """
    grammar = plumbing.parse_grammar("foo := bar:/[a-z]+/ ;")
    assert "_trivia" not in grammar.identifiers

    parser_file = tmp_path / "tiny_parser.py"
    cst_file = tmp_path / "tiny_cst.py"
    emit.write_generated_modules(grammar, str(parser_file), str(cst_file), "tiny_cst")

    assert parser_file.exists()
    _assert_pair(cst_file, tmp_path / "tiny_cst_protocol.py", "tiny_cst")


def test_a_rendering_failure_leaves_every_target_untouched(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing is written until all three modules have rendered.

    A rendering exception must not leave a truncated `bootstrap_parser.py` on top of the file this
    path exists to restore, so the three targets keep whatever they held before the failed run.
    """
    grammar = plumbing.parse_grammar("foo := bar:/[a-z]+/ ;")
    parser_file = tmp_path / "tiny_parser.py"
    cst_file = tmp_path / "tiny_cst.py"
    protocol_file = tmp_path / "tiny_cst_protocol.py"
    for path in (parser_file, cst_file, protocol_file):
        path.write_text("sentinel\n")

    def _boom(self: gsm2tree.CstGenerator) -> typing.NoReturn:  # noqa: ARG001 - a bound method stand-in
        msg = "rendering failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(gsm2tree.CstGenerator, "gen_protocol_module_text", _boom)

    with pytest.raises(RuntimeError, match="rendering failed"):
        emit.write_generated_modules(grammar, str(parser_file), str(cst_file), "tiny_cst")

    for path in (parser_file, cst_file, protocol_file):
        assert path.read_text() == "sentinel\n", f"{path.name} was overwritten by a failed run"
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "tiny_cst.py",
        "tiny_cst_protocol.py",
        "tiny_parser.py",
    ], "a temp file survived the failed run"
