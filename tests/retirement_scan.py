"""The scanning half the retirement gates share, so only the matcher differs between them.

A retirement gate is one shape: take a set of files that can carry a command, run a matcher over
their lines, and report every hit with enough context to fix it. `tests/uv_scan.py` and
`tests/cargo_scan.py` own the matchers; the walk, the comment stripping and the
`<path>:<lineno>: <line>` report live here, so a third gate inherits them rather than growing a
third copy that drifts on its first false positive.
"""

from __future__ import annotations

import pathlib
from collections.abc import Callable


def strip_comment(line: str) -> str:
    """`line` up to the `#` that starts a comment on it, or `line` when it has none.

    A comment opener is a `#` at the start of the line or after whitespace, outside a quoted
    string. The quote tracking is what keeps a command hidden inside a string literal visible:
    a Starlark `cmd = "foo # bar"` or a shell recipe echoing a `#` would otherwise take the rest
    of its line out of the scan, and a retirement gate that cannot see a genrule's command is
    the hole it exists to close. It is still not a lexer — escapes and here-documents are not
    modelled — but every construct these gates scan (Makefile recipes, YAML values, Starlark
    strings) balances its quotes on one line.
    """
    quote: str | None = None
    for index, char in enumerate(line):
        if quote is not None:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or line[index - 1].isspace()):
            return line[:index]
    return line


def uncommented(path: pathlib.Path) -> list[str]:
    """`path`'s lines with `#` comments stripped.

    Every surface a retirement gate scans explains the retirement in prose, and that prose has
    the shape of an invocation, so a raw scan would match the explanation rather than a live
    command.
    """
    return [strip_comment(line) for line in path.read_text().splitlines()]


def offenders(
    paths: list[pathlib.Path],
    root: pathlib.Path,
    matcher: Callable[[str], bool],
    *,
    strip_comments: bool = False,
) -> list[str]:
    """Every `<path>:<lineno>: <line>` in `paths` that `matcher` accepts, relative to `root`.

    The line number is the point: these gates are read at the moment of failure, and a report
    naming only the text leaves the reader grepping for where it lives.
    """
    hits = []
    for path in paths:
        lines = uncommented(path) if strip_comments else path.read_text().splitlines()
        for lineno, line in enumerate(lines, start=1):
            if matcher(line):
                hits.append(f"{path.relative_to(root)}:{lineno}: {line.strip()}")
    return hits
