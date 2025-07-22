#!/usr/bin/env -S uv run python
"""CLI for unparsing and rendering source files using FLTK.

This tool takes a grammar file, format specification, and input file to produce
formatted output using the FLTK unparsing and rendering pipeline.
"""

import ast
import sys
from pathlib import Path
from typing import Annotated

import typer

from fltk import plumbing
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.unparse import gsm2unparser
from fltk.unparse.renderer import RendererConfig

app = typer.Typer(
    name="unparse",
    help="Unparse and render source files using FLTK grammar and format specifications",
    add_completion=False,
    pretty_exceptions_enable=False,  # Disable rich exception formatting
)


@app.command()
def main(
    grammar: Annotated[Path, typer.Argument(help="Path to the grammar file (.fltkg)")],
    format_spec: Annotated[Path, typer.Argument(help="Path to the format specification file (.fltkfmt)")],
    input_file: Annotated[
        Path | None, typer.Argument(help="Path to the input file (omit or use '-' for stdin)")
    ] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path (default: stdout)")] = None,
    width: Annotated[int, typer.Option("--width", "-w", help="Maximum line width")] = 80,
    indent: Annotated[int, typer.Option("--indent", "-i", help="Indent spacing")] = 2,
    rule: Annotated[str | None, typer.Option("--rule", "-r", help="Start rule name")] = None,
    generate_unparser: Annotated[
        Path | None, typer.Option("--generate-unparser", help="Write generated unparser code to file")
    ] = None,
    cst_module: Annotated[
        str | None,
        typer.Option(
            "--cst-module",
            help="CST module import path for generated unparser (required with --generate-unparser)",
        ),
    ] = None,
    parser_module: Annotated[
        str | None,
        typer.Option("--parser-module", help="Parser module import path for generated unparser (optional)"),
    ] = None,
):
    """Unparse and render a source file using FLTK grammar and format specifications."""
    # Parse the grammar
    grammar_obj = plumbing.parse_grammar_file(grammar)

    # Parse the format specification
    formatter_config = plumbing.parse_format_config_file(format_spec)

    # Generate parser with trivia capture enabled (required for unparsing)
    parser_result = plumbing.generate_parser(grammar_obj, capture_trivia=True)

    if generate_unparser:
        if not cst_module:
            typer.echo("Error: --cst-module is required when using --generate-unparser", err=True)
            raise typer.Exit(1)

        # Generate and write unparser code to file
        context = create_default_context(capture_trivia=True)
        grammar_with_trivia = parser_result.grammar

        # Generate unparser class and imports
        unparser_class, imports = gsm2unparser.generate_unparser(
            grammar_with_trivia,
            context,
            cst_module,
            formatter_config=formatter_config,
        )

        # Add parser module import if specified
        if parser_module:
            parser_import = ast.Import(names=[ast.alias(name=parser_module, asname=None)])
            imports.append(parser_import)

        # Compile to AST
        unparser_ast = compiler.compile_class(unparser_class, context)
        module = ast.fix_missing_locations(ast.Module(body=[*imports, unparser_ast], type_ignores=[]))

        # Convert to source code
        unparser_source = ast.unparse(module)

        # Write to file
        with generate_unparser.open("w") as f:
            f.write(unparser_source)

        typer.echo(f"Generated unparser code written to: {generate_unparser}")
        return

    # Read input
    if input_file is None or (isinstance(input_file, str) and input_file == "-"):
        input_text = sys.stdin.read()
    else:
        with input_file.open() as f:
            input_text = f.read()

    # Parse the input
    parse_result = plumbing.parse_text(parser_result, input_text, rule_name=rule)
    if not parse_result.success:
        typer.echo(f"Error: Failed to parse input: {parse_result.error_message}", err=True)
        raise typer.Exit(1)

    # Generate unparser
    unparser_result = plumbing.generate_unparser(
        parser_result.grammar,
        parser_result.cst_module_name,
        formatter_config=formatter_config,
    )

    # Unparse to Doc combinators
    doc = plumbing.unparse_cst(unparser_result, parse_result.cst, input_text, rule_name=rule)

    # Configure renderer
    renderer_config = RendererConfig(max_width=width, indent_width=indent)

    # Render to formatted text
    output_text = plumbing.render_doc(doc, renderer_config)

    # Write output
    if output:
        with output.open("w") as f:
            f.write(output_text)
    else:
        sys.stdout.write(output_text)


if __name__ == "__main__":
    app()
