"""The two bootstrap writers emit a CST module and its protocol module as a pair.

`fltk/fegen/bootstrap.py` (hand-written GSM) and `runbs.py` (bootstrap grammar file) are the
regeneration path used after a bootstrap-grammar change. The CST module they write imports its
NodeKind from `<cst_module>_protocol`, so writing only the CST module leaves it paired with
whatever protocol module happens to be on disk: a fresh rule fails at import with a bare
`AttributeError` inside a dataclass body, and merely renamed rules silently reuse the wrong enum.
These run the writers as scripts, the way a maintainer does.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).parent.parent


def _assert_pair(cst_file: pathlib.Path, protocol_file: pathlib.Path, module_name: str) -> None:
    assert cst_file.exists(), f"{cst_file.name} was not written"
    assert protocol_file.exists(), f"{protocol_file.name} was not written beside {cst_file.name}"
    assert f"from {module_name}_protocol import NodeKind" in cst_file.read_text()
    assert "class NodeKind" in protocol_file.read_text()


def test_bootstrap_py_renders_both_modules() -> None:
    """`fltk/fegen/bootstrap.py`'s writer renders the protocol module as well as the CST module.

    Checked by inspection rather than by running it: its hand-written GSM constant carries no
    `_trivia` rule and its `__main__` never adds one, so `ParserGenerator` refuses it with
    "Expected _trivia rule to exist for parsing" before any file is written. That is a separate,
    pre-existing breakage; this pins the pairing so the writer is correct whenever it is revived.
    """
    source = (_REPO_ROOT / "fltk" / "fegen" / "bootstrap.py").read_text()
    assert "cstgen.gen_protocol_module_text()" in source
    assert "naming.protocol_module_path(cst_filename)" in source


def test_runbs_writes_the_protocol_module_beside_the_cst_module(tmp_path: pathlib.Path) -> None:
    grammar = _REPO_ROOT / "fltk" / "fegen" / "bootstrap.fltkg"
    if not grammar.exists():  # pragma: no cover - the grammar is committed
        pytest.skip("bootstrap grammar missing")
    parser_file = tmp_path / "bs_parser.py"
    cst_file = tmp_path / "bs_cst.py"
    result = subprocess.run(  # noqa: S603 - fixed argv, interpreter and repo paths only
        [sys.executable, "runbs.py", str(grammar), str(parser_file), str(cst_file), "bs_cst"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    _assert_pair(cst_file, tmp_path / "bs_cst_protocol.py", "bs_cst")
