"""`//:pyright` and `[tool.pyright]` describe the same type-checked tree.

The pyright configuration lives in two places: the `pyright_lint` stanza in `BUILD.bazel`
drives `bazel build --config lint //:pyright`, and `[tool.pyright]` in `pyproject.toml` drives
an editor opening the checkout and the tests that shell out to pyright directly
(`fltk/fegen/test_cst_protocol.py`, `tests/test_clean_protocol_consumer_api.py`,
`tests/test_gsm2tree_rs.py`, `tests/test_rust_unparser_pyi.py`).  Nothing else compares them,
and a directory added to one and not the other means the two check different trees — or that
`//:pyright`, the gate, quietly covers less than what a developer sees locally.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

_REPO_ROOT = Path(__file__).parent.parent

#: The rule's attr defaults, used when the stanza does not set them.
_PYRIGHT_LINT_DEFAULTS = {"python_version": "3.10", "stub_path": ""}


def _pyright_lint_stanza() -> str:
    """The `pyright_lint(name = "pyright", ...)` call source out of BUILD.bazel."""
    build = (_REPO_ROOT / "BUILD.bazel").read_text()
    match = re.search(r'^pyright_lint\(\n\s*name = "pyright",\n(.*?)^\)$', build, re.DOTALL | re.MULTILINE)
    assert match, 'no `pyright_lint(name = "pyright", ...)` stanza in BUILD.bazel'
    return match.group(1)


def _string_list(stanza: str, attr: str) -> list[str]:
    match = re.search(rf"^    {attr} = \[(.*?)\]", stanza, re.DOTALL | re.MULTILINE)
    if not match:
        return []
    return re.findall(r'"([^"]*)"', match.group(1))


def _string(stanza: str, attr: str) -> str:
    match = re.search(rf'^    {attr} = "([^"]*)"', stanza, re.MULTILINE)
    return match.group(1) if match else _PYRIGHT_LINT_DEFAULTS[attr]


def _tool_pyright() -> dict[str, object]:
    return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text())["tool"]["pyright"]


def test_include_matches() -> None:
    stanza = _pyright_lint_stanza()
    assert sorted(_string_list(stanza, "include")) == sorted(_tool_pyright()["include"]), (
        "`include` differs between //:pyright and [tool.pyright]: the two lanes would check "
        "different trees. Update both."
    )


def test_exclude_matches() -> None:
    stanza = _pyright_lint_stanza()
    assert sorted(_string_list(stanza, "exclude")) == sorted(_tool_pyright()["exclude"])


def test_extra_paths_match() -> None:
    """The BUILD stanza's `deps` add further entries at analysis time; the literal ones pair."""
    stanza = _pyright_lint_stanza()
    assert sorted(_string_list(stanza, "extra_paths")) == sorted(_tool_pyright()["extraPaths"])


def test_python_version_matches() -> None:
    assert _string(_pyright_lint_stanza(), "python_version") == _tool_pyright()["pythonVersion"]


def test_stub_path_matches() -> None:
    assert _string(_pyright_lint_stanza(), "stub_path") == _tool_pyright()["stubPath"]
