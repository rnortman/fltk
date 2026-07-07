#!/usr/bin/env -S uv run python
"""``fltk-lsp``: a generic pygls language server for any FLTK grammar.

Invoked as ``fltk-lsp --grammar lang.fltkg [--lsp lang.fltklsp] [--fmt lang.fltkfmt]
[--rule START_RULE] [--width N] [--indent N]``. One process serves one language (one grammar);
editors spawn a separate server per language, the LSP-standard shape.

Startup is fail-fast: the grammar, optional ``.fltklsp`` spec, optional ``.fltkfmt`` config, and
``--rule`` are all validated before any protocol I/O, so a misconfiguration surfaces as a clear
stderr message and a non-zero exit (which editors show in their logs) rather than as a broken
running server. ``pygls`` is an optional extra; its absence is reported with an actionable install
hint before anything else runs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from fltk import plumbing
from fltk.lsp.engine import AnalysisEngine
from fltk.unparse.renderer import RendererConfig

app = typer.Typer(
    name="fltk-lsp",
    help="Run a generic LSP server for an FLTK grammar (one process serves one language).",
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.command()
def main(
    grammar: Annotated[Path, typer.Option("--grammar", help="Path to the grammar file (.fltkg)")],
    lsp: Annotated[Path | None, typer.Option("--lsp", help="Path to the editor-tooling spec file (.fltklsp)")] = None,
    fmt: Annotated[Path | None, typer.Option("--fmt", help="Path to the formatting spec file (.fltkfmt)")] = None,
    rule: Annotated[str | None, typer.Option("--rule", help="Start rule name (defaults to the first rule)")] = None,
    width: Annotated[int, typer.Option("--width", help="Line width for document formatting")] = 80,
    indent: Annotated[int, typer.Option("--indent", help="Indent width for document formatting")] = 2,
) -> None:
    """Serve GRAMMAR over LSP on stdio, applying optional .fltklsp and .fltkfmt specs."""
    try:
        from fltk.lsp.server import create_server  # noqa: PLC0415 -- lazy so a missing pygls is a message, not a crash
    except ImportError:
        typer.echo("fltk-lsp requires the 'lsp' extra: pip install 'fltk[lsp]'", err=True)
        raise typer.Exit(1) from None

    try:
        engine = AnalysisEngine.from_paths(grammar, lsp, start_rule=rule)
        if rule is not None:
            rule_names = [r.name for r in engine.source_grammar.rules]
            if rule not in rule_names:
                valid = ", ".join(rule_names)
                typer.echo(f"Unknown start rule '{rule}'. Valid rules: {valid}", err=True)
                raise typer.Exit(1)
        formatter_config = plumbing.parse_format_config_file(fmt) if fmt is not None else None
    except (ValueError, OSError) as exc:
        # ValueError covers grammar/.fltklsp/.fltkfmt content errors (LspConfigError is a
        # ValueError); OSError covers missing/unreadable --grammar, --lsp, and --fmt.
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc

    renderer_config = RendererConfig(max_width=width, indent_width=indent)
    server = create_server(engine, formatter_config, renderer_config, start_rule=rule)
    server.start_io()


if __name__ == "__main__":
    app()
