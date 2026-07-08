#!/usr/bin/env -S uv run python
"""``fltk-highlight``: a standalone semantic highlighter for FLTK grammars.

Loads a ``.fltkg`` grammar and an optional ``.fltklsp`` spec, parses an input file, and
writes the source to stdout with a small fixed ANSI-color theme -- one 16-color mapping per
legend member, with the ``declaration`` modifier rendered bold and unpainted text passed
through unchanged. A ``.fltklsp`` load error prints to stderr and exits 1 with no stdout. An input
parse failure exits 1 with the error on stderr; if the parse assembled a prefix, the prefix is
painted and the (uncolored) tail is still written to stdout, otherwise stdout is empty.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from fltk.fegen.pyrt.errors import escape_control_chars
from fltk.lsp.classify import Token
from fltk.lsp.engine import AnalysisEngine

app = typer.Typer(
    name="fltk-highlight",
    help="Semantically highlight a source file using an FLTK grammar and optional .fltklsp spec",
    add_completion=False,
    pretty_exceptions_enable=False,
)

# One 16-color ANSI foreground code per legend member. Private, non-configurable in round 1.
_THEME: dict[str, str] = {
    "keyword": "35",
    "comment": "90",
    "string": "32",
    "number": "33",
    "operator": "36",
    "punctuation": "37",
    "variable": "34",
    "parameter": "94",
    "property": "96",
    "type": "93",
    "function": "92",
    "enumMember": "95",
    "constant": "91",
    "macro": "95",
    "label": "36",
    "text": "37",
}

_RESET = "\x1b[0m"


def _sanitize(text: str) -> str:
    """Escape terminal-control and bidi characters in workspace text, keeping newlines and tabs.

    The input file is untrusted; emitting it verbatim would let embedded escape sequences drive
    the terminal (clipboard, title, cursor) or restyle malicious code as a comment. Newlines are
    preserved so multi-line source still renders; ``escape_control_chars`` keeps tabs and escapes
    ``\\x1b`` and the rest of the control/bidi set.
    """
    return "\n".join(escape_control_chars(line) for line in text.split("\n"))


def _render(text: str, tokens: list[Token]) -> str:
    """Wrap each token's source slice in its ANSI color; pass unpainted gaps through sanitized.

    ``tokens`` is the sorted, non-overlapping stream the classifier returns. Bold is added for
    the ``declaration`` modifier. A token whose type has no theme entry is passed through
    uncolored. Every emitted source slice is sanitized so untrusted control bytes cannot reach
    the terminal, while the tool's own SGR framing stays intact.
    """
    out: list[str] = []
    cursor = 0
    for token in tokens:
        assert token.start >= cursor, f"tokens not sorted/non-overlapping: {token.start} < {cursor}"
        if token.start > cursor:
            out.append(_sanitize(text[cursor : token.start]))
        segment = _sanitize(text[token.start : token.end])
        code = _THEME.get(token.token_type)
        if code is None:
            out.append(segment)
        else:
            sgr = f"1;{code}" if "declaration" in token.modifiers else code
            out.append(f"\x1b[{sgr}m{segment}{_RESET}")
        cursor = token.end
    if cursor < len(text):
        out.append(_sanitize(text[cursor:]))
    return "".join(out)


@app.command()
def main(
    file: Annotated[Path, typer.Argument(help="Path to the source file to highlight")],
    grammar: Annotated[Path, typer.Option("--grammar", help="Path to the grammar file (.fltkg)")],
    lsp: Annotated[Path | None, typer.Option("--lsp", help="Path to the editor-tooling spec file (.fltklsp)")] = None,
    rule: Annotated[str | None, typer.Option("--rule", help="Start rule name")] = None,
) -> None:
    """Highlight FILE using GRAMMAR and an optional .fltklsp spec, writing ANSI to stdout."""
    try:
        engine = AnalysisEngine.from_paths(grammar, lsp, start_rule=rule)
        text = file.read_text()
    except (ValueError, OSError) as exc:
        # ValueError covers grammar/.fltklsp content errors (LspConfigError is a ValueError,
        # UnicodeDecodeError too); OSError covers missing/unreadable --grammar, --lsp, and FILE.
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    analysis = engine.analyze(text)
    if analysis.error is None:
        assert analysis.tokens is not None
        sys.stdout.write(_render(text, analysis.tokens))
        return

    # Parse failed. A partial analysis still carries prefix tokens: paint them (the tail past the
    # prefix passes through uncolored) so the manual-highlighting harness shows what did parse.
    if analysis.tokens is not None:
        sys.stdout.write(_render(text, analysis.tokens))
    typer.echo(analysis.error.message, err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
