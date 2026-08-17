"""Generate unparser combinators from grammar and format specification."""

import sys
from pathlib import Path

from fltk import plumbing
from fltk.fegen import gsm, pybackend
from fltk.fegen.pyrt import errors, terminalsrc
from fltk.plumbing import generate_unparser_source
from fltk.unparse import toy_trivia_parser, unparsefmt_parser

# Constants
EXPECTED_ARGC_MINIMAL = 2
EXPECTED_ARGC_FULL = 4


def parse_grammar_file(grammar_path: Path) -> tuple[gsm.Grammar, str]:
    """Parse a .fltkg file and return the GSM plus the grammar text it was parsed from.

    The file is read exactly once, so the returned text is the same bytes the returned GSM
    describes — a caller resolving spans against the text cannot see a file that changed
    mid-call.

    A missing file raises ``FileNotFoundError``.  A grammar that does not parse goes through
    the shared generator path's error contract: the diagnostic is written to stderr and
    ``typer.Exit`` is raised.
    """
    if not grammar_path.exists():
        msg = f"Grammar file '{grammar_path}' not found"
        raise FileNotFoundError(msg)

    source = grammar_path.read_text()
    return pybackend.parse_grammar_source(source, grammar_path), source


def parse_format_file(format_path: Path) -> tuple:
    """Parse a .fltkfmt file and return the format CST and FormatterConfig."""
    if not format_path.exists():
        msg = f"Format file '{format_path}' not found"
        raise FileNotFoundError(msg)

    content = format_path.read_text()

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

    return result.result, plumbing.parse_format_config(content)


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
    """Dump the toy grammar's unparser module, or the three parse trees, to stdout.

    A development aid over the same generator the `genparser gen-py-unparser` subcommand
    calls; the subcommand is what a build action uses, since it writes a named file.
    """
    if len(sys.argv) not in [EXPECTED_ARGC_MINIMAL, EXPECTED_ARGC_FULL]:
        msg = "Usage: python genunparser.py <grammar.fltkg> [<format.fltkfmt> <source.toy>]"
        sys.stderr.write(f"{msg}\n")
        sys.exit(1)

    grammar_path = Path(sys.argv[1])

    if not grammar_path.exists():
        msg = f"Grammar file not found: {grammar_path}"
        sys.stderr.write(f"{msg}\n")
        sys.exit(1)

    grammar, _ = parse_grammar_file(grammar_path)

    if len(sys.argv) == EXPECTED_ARGC_FULL:
        format_path = Path(sys.argv[2])
        source_path = Path(sys.argv[3])

        if not format_path.exists():
            msg = f"Format file not found: {format_path}"
            sys.stderr.write(f"{msg}\n")
            sys.exit(1)

        format_spec, _formatter_config = parse_format_file(format_path)
        source_cst = parse_source(source_path)

        sys.stdout.write(f"{grammar}\n")
        sys.stdout.write("---\n")
        sys.stdout.write(f"{format_spec}\n")
        sys.stdout.write("---\n")
        sys.stdout.write(f"{source_cst}\n")
        return

    # One writer for unparser module source: the same function the CLI subcommand and
    # the in-process generator both go through.
    sys.stdout.write(f"{generate_unparser_source(grammar, 'fltk.unparse.toy_cst')}\n")


if __name__ == "__main__":
    main()
