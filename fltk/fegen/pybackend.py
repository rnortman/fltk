"""The Python-backend parser generator: grammar file in, normalized ``.py`` modules out.

This module is the whole Python code-generation path, and its transitive imports are
restricted to hand-written modules plus the committed self-hosting seed
(``fltk_parser`` / ``fltk_cst`` / ``fltk_cst_protocol``).  That restriction is
load-bearing rather than stylistic: the generator that produces ``regex_cst.py`` cannot
itself import ``regex_cst``, and the Rust-backend generators reachable from
``genparser.py`` do exactly that (``gsm2parser_rs`` imports ``regex_parser``,
``ast_config`` imports ``fltkast_parser``, ``plumbing`` imports ``unparsefmt_parser``
and ``fltklsp_parser``).  So this module, not ``genparser.py``, is what a build system
runs to bring those aux modules into existence.

``genparser.py``'s ``generate`` command is a thin wrapper over :func:`generate` here, and
``genparser_stage0.py`` is a second, minimal CLI over the same function.  There must be
exactly one writer of Python-backend output: the seed's fixed-point property and the aux
modules both depend on every path producing byte-identical text.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

import typer

from fltk import pygen
from fltk.fegen import fltk2gsm, fltk_parser, gencode_format, gsm, gsm2parser, gsm2tree, naming
from fltk.fegen.pyrt import errors, terminalsrc
from fltk.iir.context import CompilerContext, create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg

if TYPE_CHECKING:
    from fltk.fegen import fltk_cst_protocol as cst


def parse_grammar_source(source: str, grammar_file: Path) -> gsm.Grammar:
    """Return the GSM for already-read grammar ``source``, with CLI-friendly error handling.

    ``grammar_file`` names the source in error messages only; nothing is read from disk here.
    Does NOT apply trivia processing; callers are
    responsible for calling add_trivia_rule_to_grammar / classify_trivia_rules if needed.
    """
    terminals = terminalsrc.TerminalSource(source)
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
    # result.result is typed Any (ParseResult.cst: Any); cast to satisfy visit_grammar's annotation.
    grammar = cst2gsm.visit_grammar(cast("cst.Grammar", result.result))

    try:
        return gsm.expand_inline_dispositions(grammar)
    except ValueError as e:
        typer.echo(f"Error: Invalid grammar file '{grammar_file}': {e}", err=True)
        raise typer.Exit(1) from e


def read_and_parse_grammar(grammar_file: Path) -> gsm.Grammar:
    """Read a grammar file and return the GSM, with CLI-friendly error handling.

    Runs the full file-read + TerminalSource + fltk_parser + Cst2Gsm pipeline plus inline
    (``!``) expansion, and exits via typer on any failure.  Does NOT apply trivia processing;
    callers are responsible for calling add_trivia_rule_to_grammar / classify_trivia_rules
    if needed.
    """
    if not grammar_file.exists():
        typer.echo(f"Error: Grammar file '{grammar_file}' not found", err=True)
        raise typer.Exit(1)

    try:
        with grammar_file.open() as f:
            source = f.read()
    except Exception as e:
        typer.echo(f"Error: Failed to read grammar file '{grammar_file}': {e}", err=True)
        raise typer.Exit(1) from e

    return parse_grammar_source(source, grammar_file)


def apply_trivia_processing(grammar: gsm.Grammar) -> gsm.Grammar:
    """Return ``grammar`` with the built-in trivia rule added and trivia rules classified.

    Both steps are pure — they return new Grammar values — so the result can be derived from
    a previously parsed grammar without re-reading the file.
    """
    return gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context=create_default_context()))


def parse_grammar_file(grammar_file: Path) -> gsm.Grammar:
    """Parse a grammar file and return the GSM representation."""
    return apply_trivia_processing(read_and_parse_grammar(grammar_file))


# ``\Z`` rather than ``$``: ``$`` also matches before a trailing newline, which would let a
# value carrying one through into an ``import`` line.
_PYTHON_MODULE_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*\Z")


def validate_python_module(module: str, option: str) -> None:
    """Exit with a CLI error when ``module`` is not a valid Python dotted module path.

    ``option`` names the CLI option or argument in the message.  Every caller interpolates the
    value verbatim into generated source — a ``.pyi`` stub's ``import <module> as _proto`` line,
    or an AST module's ``import <module> as cst``.  Without this guard a malformed value (empty,
    embedded spaces, leading/trailing dot) raises no exception: the generator exits 0 and writes
    a file that only fails later when something parses it.  Validating up front turns that into
    an immediate, diagnosable CLI error before any file is written.
    """
    if not _PYTHON_MODULE_RE.match(module):
        typer.echo(f"Error: {option} {module!r} is not a valid Python module path", err=True)
        raise typer.Exit(1)


def warn_on_relocated_module_layout(base_name: str, cst_module_name: str) -> None:
    """Warn when the written filenames only work after the caller relocates them.

    ``generate`` writes ``{base_name}_cst.py`` and ``{base_name}_cst_protocol.py`` but bakes
    ``from {cst_module_name}_protocol import NodeKind`` into the first.  Those agree in place only
    when ``cst_module_name``'s last component is ``{base_name}_cst``.  Any other value describes a
    layout the caller intends to move the files into, which is supported (and is what the dotted
    ``mylang.cst`` form means) — so this warns rather than failing, naming both halves so a caller
    who did not intend to relocate sees the cause before the ``ModuleNotFoundError`` at import.
    """
    if cst_module_name.rsplit(".", 1)[-1] == f"{base_name}_cst":
        return
    typer.echo(
        f"Warning: CST_MODULE {cst_module_name!r} does not match the written file "
        f"'{base_name}_cst.py'. The emitted CST module imports NodeKind from "
        f"'{naming.protocol_module_name(cst_module_name)}', so '{base_name}_cst_protocol.py' must "
        f"be importable under that name — relocate both files, or pass '{base_name}_cst'.",
        err=True,
    )


def generate_parser(
    grammar: gsm.Grammar,
    parser_file: Path,
    cst_module_name: str,
    *,
    preserve_trivia: bool,
    context: CompilerContext | None = None,
) -> None:
    """Generate only a parser file using an existing CST module.

    The caller is responsible for normalization: :func:`generate` normalizes the whole set of
    files it wrote in one pass, and a direct caller that wants normalized output passes the
    written path to :func:`fltk.fegen.gencode_format.normalize`.
    """
    if context is None:
        context = create_default_context()

    context.capture_trivia = preserve_trivia

    grammar = gsm.add_trivia_rule_to_grammar(grammar, context)

    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module, context=context)
    pgen = gsm2parser.ParserGenerator(grammar=grammar, cstgen=cstgen, context=context)

    parser_ast = compiler.compile_class(pgen.parser_class, context)
    imports = [
        pyreg.Module(("collections", "abc")),
        pyreg.Module(("typing",)),
        pyreg.Module(("fltk", "fegen", "pyrt", "errors")),
        pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
        pyreg.Module(("fltk", "fegen", "pyrt", "terminalsrc")),
        cst_module,
    ]

    parser_mod = pygen.module(module.import_path for module in imports)
    # `from __future__ import annotations` keeps the parser's span-typed annotations as lazy
    # strings.  The parser annotates its terminal spans with the concrete pure-Python
    # `fltk.fegen.pyrt.terminalsrc.Span` (runtime-imported above for construction) — it names
    # neither the `fltk.fegen.pyrt.span` selector nor `fltk._native`, so it never touches
    # span.py's process-wide native-span probe in any environment.
    parser_mod.body.insert(0, pygen.stmt("from __future__ import annotations"))
    parser_mod.body.append(parser_ast)

    try:
        with parser_file.open("w") as f:
            f.write(ast.unparse(parser_mod))
    except Exception as e:
        typer.echo(f"Error: Failed to write parser file '{parser_file}': {e}", err=True)
        raise typer.Exit(1) from e


def generate(
    grammar_file: Path,
    base_name: str,
    cst_module_name: str,
    *,
    output_dir: Path | None = None,
    trivia_only: bool = False,
    no_trivia_only: bool = False,
    protocol_only: bool = False,
    protocol: bool = False,
    verbose: bool = False,
) -> list[Path]:
    """Emit the Python-backend modules for ``grammar_file`` and return what was written.

    Writes ``{base_name}_cst.py``, ``{base_name}_cst_protocol.py`` and the two parser
    variants into ``output_dir``, subject to the ``trivia_only`` / ``no_trivia_only`` /
    ``protocol_only`` selectors, then normalizes every file it wrote.  ``protocol`` is a
    deprecated no-op accepted so existing invocations keep working.
    """
    if trivia_only and no_trivia_only:
        typer.echo("Error: --trivia-only and --no-trivia-only are mutually exclusive", err=True)
        raise typer.Exit(1)
    if protocol_only and (trivia_only or no_trivia_only):
        typer.echo(
            "Error: --protocol-only cannot be combined with --trivia-only/--no-trivia-only "
            "(--protocol-only generates no parsers)",
            err=True,
        )
        raise typer.Exit(1)
    if protocol:
        typer.echo(
            "Warning: --protocol is a deprecated no-op; the protocol module is always generated.",
            err=True,
        )
    validate_python_module(cst_module_name, "CST_MODULE")
    warn_on_relocated_module_layout(base_name, cst_module_name)

    if output_dir is None:
        output_dir = Path(".")

    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        typer.echo(f"Parsing grammar file: {grammar_file}")

    grammar = parse_grammar_file(grammar_file)

    # The CstGenerator is the shared source for both the CST module and the protocol module.
    grammar = gsm.add_trivia_rule_to_grammar(grammar, create_default_context())
    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module, context=create_default_context())

    written: list[Path] = []

    if not protocol_only:
        shared_cst = output_dir / f"{base_name}_cst.py"

        if verbose:
            typer.echo("Generating shared CST module...")

        cst_mod = cstgen.gen_py_module(naming.protocol_module_name(cst_module_name))
        cst_text = ast.unparse(cst_mod)  # generate before opening file so an error doesn't leave a partial file
        try:
            with shared_cst.open("w", newline="\n") as f:
                f.write(cst_text)
        except OSError as e:
            typer.echo(f"Error: Failed to write shared CST file '{shared_cst}': {e}", err=True)
            raise typer.Exit(1) from e
        written.append(shared_cst)

    # Always written: the CST module imports NodeKind from it, so the pair is mandatory.
    shared_cst_protocol = output_dir / f"{base_name}_cst_protocol.py"
    if verbose:
        typer.echo("Generating CST Protocol module...")
    # Generate before opening the file so any AST construction error doesn't leave a partial
    # artifact.
    protocol_text = cstgen.gen_protocol_module_text()
    try:
        with shared_cst_protocol.open("w", newline="\n") as f:
            f.write(protocol_text)
    except OSError as e:
        typer.echo(f"Error: Failed to write CST Protocol file '{shared_cst_protocol}': {e}", err=True)
        raise typer.Exit(1) from e
    written.append(shared_cst_protocol)

    if protocol_only:
        gencode_format.normalize(written)
        if verbose:
            typer.echo("✓ Protocol generation completed successfully")
            typer.echo(f"CST Protocol: {shared_cst_protocol}")
        return written

    generate_no_trivia = not trivia_only
    generate_trivia = not no_trivia_only

    if generate_no_trivia:
        no_trivia_parser = output_dir / f"{base_name}_parser.py"

        if verbose:
            typer.echo("Generating parser without trivia preservation...")

        generate_parser(
            grammar=grammar,
            parser_file=no_trivia_parser,
            cst_module_name=cst_module_name,
            preserve_trivia=False,
        )
        written.append(no_trivia_parser)

    if generate_trivia:
        trivia_parser = output_dir / f"{base_name}_trivia_parser.py"

        if verbose:
            typer.echo("Generating parser with trivia preservation...")

        generate_parser(
            grammar=grammar,
            parser_file=trivia_parser,
            cst_module_name=cst_module_name,
            preserve_trivia=True,
        )
        written.append(trivia_parser)

    gencode_format.normalize(written)

    if verbose:
        typer.echo("✓ Parser generation completed successfully")
        typer.echo(f"Shared CST: {output_dir / f'{base_name}_cst.py'}")
        typer.echo(f"CST Protocol: {output_dir / f'{base_name}_cst_protocol.py'}")
        if generate_no_trivia:
            typer.echo(f"Non-trivia parser: {output_dir / f'{base_name}_parser.py'}")
        if generate_trivia:
            typer.echo(f"Trivia parser: {output_dir / f'{base_name}_trivia_parser.py'}")

    return written
