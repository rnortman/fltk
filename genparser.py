"""Professional CLI for FLTK parser generation.

Generates parsers from FLTK grammar files with options for trivia handling.
"""

import ast
from pathlib import Path
from typing import Annotated

import typer

import fltk2gsm
import fltk_parser
from fltk import pygen
from fltk.fegen import gsm, gsm2parser, gsm2tree
from fltk.fegen.pyrt import errors, terminalsrc
from fltk.iir.context import CompilerContext, create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg

app = typer.Typer(
    name="genparser",
    help="Generate parsers from FLTK grammar files",
    add_completion=False,
)


def parse_grammar_file(grammar_file: Path) -> gsm.Grammar:
    """Parse a grammar file and return the GSM representation."""
    if not grammar_file.exists():
        typer.echo(f"Error: Grammar file '{grammar_file}' not found", err=True)
        raise typer.Exit(1)

    try:
        with grammar_file.open() as f:
            terminals = terminalsrc.TerminalSource(f.read())
    except Exception as e:
        typer.echo(f"Error: Failed to read grammar file '{grammar_file}': {e}", err=True)
        raise typer.Exit(1) from e

    parser = fltk_parser.Parser(terminalsrc=terminals)
    result = parser.apply__parse_grammar(0)

    if not result or result.pos != len(terminals.terminals):
        error_msg = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        typer.echo(f"Error: Failed to parse grammar file '{grammar_file}':", err=True)
        typer.echo(error_msg, err=True)
        raise typer.Exit(1)

    cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals)
    grammar = cst2gsm.visit_grammar(result.result)
    return grammar


def generate_parser_files(
    grammar: gsm.Grammar,
    parser_file: Path,
    cst_file: Path,
    cst_module_name: str,
    *,
    preserve_trivia: bool,
    context: CompilerContext | None = None,
) -> None:
    """Generate parser and CST files from grammar."""
    if context is None:
        context = create_default_context()

    # Set trivia capture flag based on user preference
    context.capture_trivia = preserve_trivia

    # Conditionally enhance grammar with trivia rule
    if preserve_trivia:
        enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)
    else:
        enhanced_grammar = grammar

    # Generate CST and parser
    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=cst_module, context=context)
    pgen = gsm2parser.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

    # Compile parser class
    parser_ast = compiler.compile_class(pgen.parser_class, context)
    imports = [
        pyreg.Module(("collections", "abc")),
        pyreg.Module(("typing",)),
        pyreg.Module(("fltk", "fegen", "pyrt", "errors")),
        pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
        cst_module,
    ]

    # Generate parser module
    parser_mod = pygen.module(module.import_path for module in imports)
    parser_mod.body.append(parser_ast)

    # Write parser file
    try:
        with parser_file.open("w") as f:
            f.write(ast.unparse(parser_mod))
    except Exception as e:
        typer.echo(f"Error: Failed to write parser file '{parser_file}': {e}", err=True)
        raise typer.Exit(1) from e

    # Generate and write CST file
    try:
        cst_mod = cstgen.gen_py_module()
        with cst_file.open("w") as f:
            f.write(ast.unparse(cst_mod))
    except Exception as e:
        typer.echo(f"Error: Failed to write CST file '{cst_file}': {e}", err=True)
        raise typer.Exit(1) from e


def generate_parser_only(
    grammar: gsm.Grammar,
    parser_file: Path,
    cst_module_name: str,
    *,
    preserve_trivia: bool,
    context: CompilerContext | None = None,
) -> None:
    """Generate only a parser file using an existing CST module."""
    if context is None:
        context = create_default_context()

    # Set trivia capture flag based on user preference
    context.capture_trivia = preserve_trivia

    # Conditionally enhance grammar with trivia rule
    if preserve_trivia:
        enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, context)
    else:
        enhanced_grammar = grammar

    # Generate parser (reusing existing CST module)
    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=cst_module, context=context)
    pgen = gsm2parser.ParserGenerator(grammar=enhanced_grammar, cstgen=cstgen, context=context)

    # Compile parser class
    parser_ast = compiler.compile_class(pgen.parser_class, context)
    imports = [
        pyreg.Module(("collections", "abc")),
        pyreg.Module(("typing",)),
        pyreg.Module(("fltk", "fegen", "pyrt", "errors")),
        pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
        cst_module,
    ]

    # Generate parser module
    parser_mod = pygen.module(module.import_path for module in imports)
    parser_mod.body.append(parser_ast)

    # Write parser file
    try:
        with parser_file.open("w") as f:
            f.write(ast.unparse(parser_mod))
    except Exception as e:
        typer.echo(f"Error: Failed to write parser file '{parser_file}': {e}", err=True)
        raise typer.Exit(1) from e


@app.command()
def generate(
    grammar_file: Annotated[Path, typer.Argument(help="Path to the FLTK grammar file (.fltkg)")],
    base_name: Annotated[str, typer.Argument(help="Base name for output files (without extension)")],
    cst_module_base: Annotated[str, typer.Argument(help="Base module name for CST classes")],
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
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Generate parsers from an FLTK grammar file.

    By default, this command generates a shared CST module and both parser variants:
    - Shared CST classes that work with both parsers
    - Parser without trivia preservation (faster, for compilers/interpreters)
    - Parser with trivia preservation (for formatters/syntax highlighters)

    Use --trivia-only or --no-trivia-only to generate just one parser variant.

    Files generated by default:
    - {base_name}_cst.py (shared CST classes)
    - {base_name}_parser.py (no trivia)
    - {base_name}_trivia_parser.py (with trivia)

    Examples:
        genparser generate grammar.fltkg mylang mylang.cst
        genparser generate grammar.fltkg mylang mylang.cst --trivia-only
        genparser generate grammar.fltkg mylang mylang.cst -o output/ --verbose
    """
    # Validate mutually exclusive options
    if trivia_only and no_trivia_only:
        typer.echo("Error: --trivia-only and --no-trivia-only are mutually exclusive", err=True)
        raise typer.Exit(1)

    if output_dir is None:
        output_dir = Path(".")

    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        typer.echo(f"Parsing grammar file: {grammar_file}")

    grammar = parse_grammar_file(grammar_file)

    # Generate shared CST module first
    shared_cst = output_dir / f"{base_name}_cst.py"
    shared_cst_module = f"{cst_module_base}_cst"

    if verbose:
        typer.echo("Generating shared CST module...")

    # Generate CST module using trivia-enhanced grammar (contains all possible nodes)
    enhanced_grammar = gsm.add_trivia_rule_to_grammar(grammar, create_default_context())
    cst_module = pyreg.Module(shared_cst_module.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=enhanced_grammar, py_module=cst_module, context=create_default_context())

    try:
        cst_mod = cstgen.gen_py_module()
        with shared_cst.open("w") as f:
            f.write(ast.unparse(cst_mod))
    except Exception as e:
        typer.echo(f"Error: Failed to write shared CST file '{shared_cst}': {e}", err=True)
        raise typer.Exit(1) from e

    # Determine which parsers to generate
    generate_no_trivia = not trivia_only
    generate_trivia = not no_trivia_only

    # Generate non-trivia parser
    if generate_no_trivia:
        no_trivia_parser = output_dir / f"{base_name}_parser.py"

        if verbose:
            typer.echo("Generating parser without trivia preservation...")

        generate_parser_only(
            grammar=grammar,
            parser_file=no_trivia_parser,
            cst_module_name=shared_cst_module,
            preserve_trivia=False,
        )

    # Generate trivia-preserving parser
    if generate_trivia:
        trivia_parser = output_dir / f"{base_name}_trivia_parser.py"

        if verbose:
            typer.echo("Generating parser with trivia preservation...")

        generate_parser_only(
            grammar=grammar,
            parser_file=trivia_parser,
            cst_module_name=shared_cst_module,
            preserve_trivia=True,
        )

    # Success message
    if verbose:
        typer.echo("✓ Parser generation completed successfully")
        typer.echo(f"Shared CST: {shared_cst}")
        if generate_no_trivia:
            typer.echo(f"Non-trivia parser: {output_dir / f'{base_name}_parser.py'}")
        if generate_trivia:
            typer.echo(f"Trivia parser: {output_dir / f'{base_name}_trivia_parser.py'}")
    else:
        parser_count = sum([generate_no_trivia, generate_trivia])
        typer.echo(f"Generated {parser_count} parser{'s' if parser_count != 1 else ''} successfully")


@app.command()
def generate_single(
    grammar_file: Annotated[Path, typer.Argument(help="Path to the FLTK grammar file (.fltkg)")],
    parser_file: Annotated[Path, typer.Argument(help="Output path for the generated parser file")],
    cst_file: Annotated[Path, typer.Argument(help="Output path for the generated CST file")],
    cst_module: Annotated[str, typer.Argument(help="Python module name for the CST classes")],
    preserve_trivia: Annotated[
        bool,
        typer.Option(
            "--preserve-trivia/--no-trivia",
            help="Whether to preserve trivia (whitespace/comments) in the CST",
        ),
    ] = True,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Generate a single parser and CST pair (legacy/Bazel compatibility).

    This command generates one parser and corresponding CST module from a grammar.
    Use this for legacy scripts or Bazel integration that need explicit file paths.

    For new usage, prefer the main 'generate' command which creates both parser
    variants with a shared CST module.

    Example:
        genparser generate-single grammar.fltkg parser.py cst.py my_lang.cst --preserve-trivia
    """
    if verbose:
        typer.echo(f"Parsing grammar file: {grammar_file}")

    grammar = parse_grammar_file(grammar_file)

    if verbose:
        trivia_status = "with trivia preservation" if preserve_trivia else "without trivia"
        typer.echo(f"Generating parser {trivia_status}")
        typer.echo(f"Parser output: {parser_file}")
        typer.echo(f"CST output: {cst_file}")
        typer.echo(f"CST module: {cst_module}")

    generate_parser_files(
        grammar=grammar,
        parser_file=parser_file,
        cst_file=cst_file,
        cst_module_name=cst_module,
        preserve_trivia=preserve_trivia,
    )

    if verbose:
        typer.echo("✓ Parser generation completed successfully")
    else:
        typer.echo("Parser generated successfully")


if __name__ == "__main__":
    app()
