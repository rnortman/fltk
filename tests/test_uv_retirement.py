"""No doc and no checked-in launcher may teach a `uv` invocation.

uv is retired: the dependency manifest is `requirements.in`, its single writer is
`bazel run //:requirements.update`, and every workflow a developer or a consumer follows is a
`bazel` command. A surviving `uv run ...` recipe is worse than a dead link — it names a tool the
repo no longer configures, so a reader who has uv installed gets an environment assembled from
nothing this repo pins, and one who does not gets a command-not-found for a workflow the project
claims to support.

This module covers prose and editor launchers; CI and Makefile recipes are gated elsewhere,
against the same matcher (`tests/uv_scan.py`), whose self-test lives here.

The scan set is *derived* from the root BUILD file rather than restated: `//:repo_docs` is a
glob so a guide added later is scanned the day it lands, and a mirrored copy of its patterns
here would make the scan the intersection of two lists, only one of which is that glob. The
BUILD file is read as Starlark-as-Python (`ast`), the same trick
`tests/test_cli_binary_targets.py` uses for the `py_binary` declarations.
"""

from __future__ import annotations

import ast
import pathlib
import re

from tests.uv_scan import names_uv, offenders

_REPO_ROOT = pathlib.Path(__file__).parent.parent

_BUILD_FILE = _REPO_ROOT / "BUILD.bazel"

#: Docs that must be in the scan whatever `//:repo_docs` globs — the four a reader is most
#: likely to follow. Everything else in the set is whatever the glob matched.
_ANCHOR_DOCS = ("README.md", "CLAUDE.md", "docs/usage.md", "docs/bazel-consumer-guide.md")


def _filegroups() -> dict[str, ast.Call]:
    """Every `filegroup` call in the root BUILD file, by target name."""
    groups: dict[str, ast.Call] = {}
    for node in ast.walk(ast.parse(_BUILD_FILE.read_text())):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "filegroup":
            continue
        for keyword in node.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                groups[keyword.value.value] = node
    return groups


def _kwarg(call: ast.Call, name: str) -> ast.expr | None:
    return next((keyword.value for keyword in call.keywords if keyword.arg == name), None)


def _strings(node: ast.expr | None) -> list[str]:
    if node is None:
        return []
    assert isinstance(node, (ast.List, ast.Tuple)), ast.dump(node)
    return [element.value for element in node.elts if isinstance(element, ast.Constant)]


def _glob_patterns(call: ast.Call) -> tuple[list[str], list[str]]:
    """The `srcs = glob(include, exclude = ...)` patterns of a filegroup."""
    srcs = _kwarg(call, "srcs")
    assert isinstance(srcs, ast.Call) and isinstance(srcs.func, ast.Name) and srcs.func.id == "glob", ast.dump(srcs)
    include = _strings(srcs.args[0]) if srcs.args else _strings(_kwarg(srcs, "include"))
    return include, _strings(_kwarg(srcs, "exclude"))


def _as_regex(pattern: str) -> re.Pattern[str]:
    """Bazel glob semantics: `**` spans path segments, `*` and `?` stop at `/`."""
    out = ""
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out += "(?:[^/]+/)*"
            index += 3
        elif pattern.startswith("**", index):
            out += ".*"
            index += 2
        elif pattern[index] == "*":
            out += "[^/]*"
            index += 1
        elif pattern[index] == "?":
            out += "[^/]"
            index += 1
        else:
            out += re.escape(pattern[index])
            index += 1
    return re.compile(out + r"\Z")


def _matched(patterns: list[str], root: pathlib.Path = _REPO_ROOT) -> set[str]:
    """Every file under `root` matching one of the patterns, as root-relative paths.

    A pattern without `**` is handed to `pathlib.glob`, whose per-segment semantics already
    agree with Bazel's. One with `**` is walked from its fixed prefix instead, because
    `pathlib`'s `**` does not match files on every supported interpreter.
    """
    names: set[str] = set()
    for pattern in patterns:
        if "**" not in pattern:
            names.update(str(path.relative_to(root)) for path in root.glob(pattern) if path.is_file())
            continue
        prefix = pattern.split("**", 1)[0]
        base = root / prefix if prefix else root
        if not base.is_dir():
            continue
        matcher = _as_regex(pattern)
        for path in base.rglob("*"):
            relative = str(path.relative_to(root))
            if path.is_file() and matcher.match(relative):
                names.add(relative)
    return names


def _docs() -> list[pathlib.Path]:
    """Every doc `//:repo_docs` puts in the runfiles tree, derived from its glob."""
    include, exclude = _glob_patterns(_filegroups()["repo_docs"])
    return sorted(_REPO_ROOT / name for name in _matched(include) - _matched(exclude))


def _tooling() -> list[pathlib.Path]:
    """Every file `//:repo_tooling_files` puts in the runfiles tree, derived from its srcs."""
    return [_REPO_ROOT / name for name in _strings(_kwarg(_filegroups()["repo_tooling_files"], "srcs"))]


def _launchers() -> list[pathlib.Path]:
    """Every file `//:editor_launchers` puts in the runfiles tree, derived from its srcs."""
    return [_REPO_ROOT / name for name in _strings(_kwarg(_filegroups()["editor_launchers"], "srcs"))]


def _write(root: pathlib.Path, *names: str) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")


def test_a_double_star_spans_path_segments_and_a_single_star_does_not(tmp_path: pathlib.Path) -> None:
    """The one property that decides whether a nested guide is scanned or silently skipped.

    An under-matching emulator is invisible: the scan below simply opens fewer files and
    still passes, so the glob semantics are pinned here rather than inferred from a green run.
    """
    _write(tmp_path, "docs/top.md", "docs/guide/nested.md", "docs/guide/deep/deeper.md", "docs/notes.txt")

    assert _matched(["docs/*.md"], tmp_path) == {"docs/top.md"}
    assert _matched(["docs/**/*.md"], tmp_path) == {
        "docs/top.md",
        "docs/guide/nested.md",
        "docs/guide/deep/deeper.md",
    }
    assert _matched(["docs/**"], tmp_path) == {
        "docs/top.md",
        "docs/notes.txt",
        "docs/guide/nested.md",
        "docs/guide/deep/deeper.md",
    }


def test_a_nested_exclusion_removes_only_its_subtree(tmp_path: pathlib.Path) -> None:
    """`//:repo_docs` carves out `docs/adr/**` and its `node_modules` trees this way."""
    _write(tmp_path, "docs/usage.md", "docs/adr/2026/notes.md", "examples/a/README.md", "examples/a/node_modules/x.md")

    include = ["docs/**/*.md", "examples/**/*.md"]
    exclude = ["docs/adr/**", "examples/**/node_modules/**"]
    assert _matched(include, tmp_path) - _matched(exclude, tmp_path) == {"docs/usage.md", "examples/a/README.md"}


def test_a_pattern_matches_files_only_and_a_question_mark_stops_at_a_slash(tmp_path: pathlib.Path) -> None:
    """A directory named `x.md`, or a `?` swallowing a separator, would inflate the set."""
    _write(tmp_path, "docs/a/b.md")
    (tmp_path / "docs/dir.md").mkdir(parents=True)

    assert _matched(["docs/**/*.md"], tmp_path) == {"docs/a/b.md"}
    assert _matched(["docs?a/b.md"], tmp_path) == set()
    assert _as_regex("a?c").match("abc")
    assert not _as_regex("a?c").match("a/c")


def test_the_scan_set_is_non_empty_and_includes_the_anchors() -> None:
    """A file `//:repo_docs` declares but this scan never opens is the failure mode here.

    Both sides come from the same glob, so the assertion is that the derivation produced files
    at all and that the docs a reader actually follows are among them — a glob narrowed to
    nothing, or one that stopped matching the guides, is red rather than vacuously green. The
    glob emulation itself is pinned by the three tests above.
    """
    names = {str(path.relative_to(_REPO_ROOT)) for path in _docs()}
    assert names, "//:repo_docs matched nothing, so the scan below passes over an empty set"
    for expected in _ANCHOR_DOCS:
        assert expected in names, f"{expected} is missing from //:repo_docs, so nothing scans it"
    assert "CHANGELOG.md" not in names, "CHANGELOG.md records the migration onto uv and is excluded by the glob"


def test_every_declared_doc_is_readable_here() -> None:
    """The declaration is only a gate if the files reach this target's runfiles."""
    missing = [str(path) for path in _docs() if not path.is_file()]
    assert not missing, f"//:repo_docs declares files that did not reach the runfiles tree: {missing}"


def test_docs_teach_no_uv_invocation() -> None:
    hits = offenders(_docs(), _REPO_ROOT)
    assert not hits, "uv is retired; these docs still teach a uv invocation:\n" + "\n".join(hits)


def test_launchers_invoke_no_uv() -> None:
    paths = _launchers()
    assert paths, "//:editor_launchers declares no srcs, so the launcher scan is vacuous"
    missing = [str(path) for path in paths if not path.is_file()]
    assert not missing, f"//:editor_launchers no longer supplies: {missing}"
    hits = offenders(paths, _REPO_ROOT)
    assert not hits, "the editor launch path still names uv:\n" + "\n".join(hits)


def test_tooling_config_invokes_no_uv() -> None:
    """Prose is not the only place a uv recipe survives; `[tool.uv]` lived in pyproject.toml.

    TODO(uv-retired-agent-hook): `.claude/settings.json` is not in this set yet — its
    PostToolUse hook still runs `uv run ruff format` and would turn this red.
    """
    paths = _tooling()
    assert paths, "//:repo_tooling_files declares no srcs, so the tooling scan is vacuous"
    missing = [str(path) for path in paths if not path.is_file()]
    assert not missing, f"//:repo_tooling_files no longer supplies: {missing}"
    hits = offenders(paths, _REPO_ROOT)
    assert not hits, "uv is retired; this tooling config still names it:\n" + "\n".join(hits)


def test_the_matchers_recognize_the_recipes_they_replaced() -> None:
    """A pattern that matches nothing passes every scan — including the Makefile and CI scans."""
    retired = (
        "uv run pytest",
        "    uv run --group dev python -m fltk.fegen.genparser generate g.fltkg g g_cst",
        "`uv sync --extra lsp`",
        '"uv", "--project", repoRoot(), "run", "--extra", "lsp", "fltk-grammar-lsp"',
        "make regen-locks writes uv.lock",
        "\tuv\tlock",
        "      - uses: astral-sh/setup-uv@v6",
        "uvx ruff format .",
        "cd /home/rnortman/src/fltk && uvx --from ruff ruff check .",
        "uv build --wheel",
        "uv tool install pyright",
    )
    for line in retired:
        assert names_uv(line), f"matcher missed: {line}"

    allowed = (
        "There is no uv and no maturin, and cargo survives in three narrow roles only.",
        "uv's product-side roles get explicit successors.",
        "the ruv-fann crate and the /uv/run endpoint",
        "# uv is retired: this workflow installs no Python tooling.",
    )
    for line in allowed:
        assert not names_uv(line), f"matcher over-matched prose: {line}"
