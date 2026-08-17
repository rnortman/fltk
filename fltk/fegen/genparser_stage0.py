"""Stage-0 parser generator: the ``generate`` command over the Python backend alone.

``genparser.py`` reaches the Rust-backend generators, and those import generated aux
modules (``regex_parser``, ``fltkast_parser``, ``unparsefmt_parser``, ``fltklsp_parser``)
at module level — so it cannot be the tool that generates them.  This entry point imports
only :mod:`fltk.fegen.pybackend`, whose transitive imports are hand-written modules plus
the committed seed, breaking that cycle.

The accepted argv is the same shape ``rules.bzl`` emits for the full generator, so a
codegen target picks one or the other with a single attribute and nothing else changes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from fltk.fegen import pybackend

app = typer.Typer(
    name="genparser_stage0",
    help="Generate Python-backend parsers from FLTK grammar files (no Rust backend)",
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Stage-0 generator.

    Present so typer keeps `generate` as a named subcommand: a Typer app with a single
    command and no callback collapses into a bare CLI, and the argv `rules.bzl` emits
    always leads with the subcommand name.
    """


@app.command()
def generate(
    grammar_file: Annotated[Path, typer.Argument(help="Path to the FLTK grammar file (.fltkg)")],
    base_name: Annotated[str, typer.Argument(help="Base name for output files (without extension)")],
    cst_module_name: Annotated[
        str, typer.Argument(help='Module import name for CST classes (usually "<base_name>_cst")')
    ],
    *,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Output directory for generated files"),
    ] = None,
    trivia_only: Annotated[
        bool,
        typer.Option("--trivia-only", help="Generate only the trivia-preserving parser"),
    ] = False,
    no_trivia_only: Annotated[
        bool,
        typer.Option("--no-trivia-only", help="Generate only the non-trivia parser"),
    ] = False,
    protocol_only: Annotated[
        bool,
        typer.Option("--protocol-only", help="Generate only the {base_name}_cst_protocol.py module"),
    ] = False,
    protocol: Annotated[
        bool,
        typer.Option("--protocol", help="Deprecated no-op; the protocol module is always generated"),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Generate the Python-backend CST, protocol and parser modules for a grammar.

    Output must stay byte-for-byte identical to ``genparser generate``.
    """
    pybackend.generate(
        grammar_file,
        base_name,
        cst_module_name,
        output_dir=output_dir,
        trivia_only=trivia_only,
        no_trivia_only=no_trivia_only,
        protocol_only=protocol_only,
        protocol=protocol,
        verbose=verbose,
    )


if __name__ == "__main__":
    app()
