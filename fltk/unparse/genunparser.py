"""Generate unparser combinators from grammar and format specification."""

import ast
import sys
from pathlib import Path

from fltk.fegen import fltk2gsm, fltk_parser, gsm
from fltk.fegen.pyrt import errors, terminalsrc
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.unparse import fmt_config, toy_trivia_parser, unparsefmt_parser
from fltk.unparse.gsm2unparser import generate_unparser

# Constants
EXPECTED_ARGC_MINIMAL = 2
EXPECTED_ARGC_FULL = 4


def parse_grammar_file(grammar_path: Path) -> tuple[gsm.Grammar, str]:
    """Parse a .fltkg file and return the GSM."""
    if not grammar_path.exists():
        msg = f"Grammar file '{grammar_path}' not found"
        raise FileNotFoundError(msg)

    try:
        with grammar_path.open() as f:
            terminals = terminalsrc.TerminalSource(f.read())
    except Exception as e:
        msg = f"Failed to read grammar file '{grammar_path}': {e}"
        raise RuntimeError(msg) from e

    parser = fltk_parser.Parser(terminalsrc=terminals)
    result = parser.apply__parse_grammar(0)

    if not result or result.pos != len(terminals.terminals):
        error_msg = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f"Failed to parse grammar file '{grammar_path}':\n{error_msg}"
        raise RuntimeError(msg)

    # Convert CST to GSM
    cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals)
    grammar = cst2gsm.visit_grammar(result.result)

    return grammar, terminals.terminals


def parse_format_file(format_path: Path) -> tuple:
    """Parse a .fltkfmt file and return the format CST and FormatterConfig."""
    if not format_path.exists():
        msg = f"Format file '{format_path}' not found"
        raise FileNotFoundError(msg)

    with format_path.open() as f:
        content = f.read()

    terminal_source = terminalsrc.TerminalSource(content)
    parser = unparsefmt_parser.Parser(terminal_source)
    result = parser.apply__parse_formatter(0)

    if not result or result.pos != len(terminal_source.terminals):
        error_msg = errors.format_error_message(
            parser.error_tracker,
            terminal_source,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f"Failed to parse format file '{format_path}':\n{error_msg}"
        raise RuntimeError(msg)

    # Convert CST to FormatterConfig
    formatter_config = fmt_config.fmt_cst_to_config(result.result, terminal_source)

    return result.result, formatter_config


def parse_source(source_path: Path):
    """Parse a .fltkfmt file and return the format CST."""
    if not source_path.exists():
        msg = f"Source file '{source_path}' not found"
        raise FileNotFoundError(msg)

    with source_path.open() as f:
        content = f.read()

    terminal_source = terminalsrc.TerminalSource(content)
    parser = toy_trivia_parser.Parser(terminal_source)
    result = parser.apply__parse_expr(0)

    if not result or result.pos != len(terminal_source.terminals):
        error_msg = errors.format_error_message(
            parser.error_tracker,
            terminal_source,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f"Failed to parse source file '{source_path}':\n{error_msg}"
        raise RuntimeError(msg)

    return result.result


def main():
    """Main entry point."""
    if len(sys.argv) not in [EXPECTED_ARGC_MINIMAL, EXPECTED_ARGC_FULL]:
        msg = "Usage: python genunparser.py <grammar.fltkg> [<format.fltkfmt> <source.toy>]"
        sys.stderr.write(f"{msg}\n")
        sys.exit(1)

    grammar_path = Path(sys.argv[1])

    if not grammar_path.exists():
        msg = f"Grammar file not found: {grammar_path}"
        sys.stderr.write(f"{msg}\n")
        sys.exit(1)

    try:
        # Parse the grammar
        grammar, _ = parse_grammar_file(grammar_path)

        # Parse format file if provided (preserve the original functionality)
        if len(sys.argv) == EXPECTED_ARGC_FULL:
            format_path = Path(sys.argv[2])
            source_path = Path(sys.argv[3])

            if not format_path.exists():
                msg = f"Format file not found: {format_path}"
                sys.stderr.write(f"{msg}\n")
                sys.exit(1)

            format_spec, formatter_config = parse_format_file(format_path)
            source_cst = parse_source(source_path)

            sys.stdout.write(f"{grammar}\n")
            sys.stdout.write("---\n")
            sys.stdout.write(f"{format_spec}\n")
            sys.stdout.write("---\n")
            sys.stdout.write(f"{source_cst}\n")
            return

        # Create compiler context
        context = create_default_context()

        # Use formatter_config if we parsed a format file, otherwise None (will use defaults)
        formatter_config = locals().get("formatter_config", None)

        # Generate unparser class
        unparser_class, imports = generate_unparser(
            grammar, context, "fltk.unparse.toy_cst", formatter_config=formatter_config
        )

        # Compile to Python AST
        unparser_ast = compiler.compile_class(unparser_class, context)

        # Create module
        module = ast.Module(body=[*imports, unparser_ast], type_ignores=[])

        # Output generated code
        sys.stdout.write(f"{ast.unparse(module)}\n")

    except Exception:
        # Let the exception propagate with full traceback
        raise


if __name__ == "__main__":
    main()
