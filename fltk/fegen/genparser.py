"""CLI for FLTK parser generation.

Generates parsers from FLTK grammar files with options for trivia handling.
"""

import ast
import re
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, cast

import typer

from fltk import pygen
from fltk.fegen import fltk2gsm, fltk_parser, gsm, gsm2lib_rs, gsm2parser, gsm2parser_rs, gsm2tree, gsm2tree_rs
from fltk.fegen.pyrt import errors, terminalsrc
from fltk.iir.context import CompilerContext, create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg
from fltk.plumbing import parse_format_config_file
from fltk.unparse import gsm2unparser_rs

if TYPE_CHECKING:
    from fltk.fegen import fltk_cst_protocol as cst

app = typer.Typer(
    name="genparser",
    help="Generate parsers from FLTK grammar files",
    add_completion=False,
)


def _read_and_parse_grammar(grammar_file: Path) -> gsm.Grammar:
    """Read a grammar file and return the raw GSM, with CLI-friendly error handling.

    Runs the full file-read + TerminalSource + fltk_parser + Cst2Gsm pipeline and
    exits via typer on any failure.  Does NOT apply trivia processing; callers are
    responsible for calling add_trivia_rule_to_grammar / classify_trivia_rules if needed.
    """
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
    # result.result is typed Any (ParseResult.cst: Any); cast to satisfy visit_grammar's annotation.
    return cst2gsm.visit_grammar(cast("cst.Grammar", result.result))


def parse_grammar_file(grammar_file: Path) -> gsm.Grammar:
    """Parse a grammar file and return the GSM representation."""
    grammar = _read_and_parse_grammar(grammar_file)
    grammar = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context=create_default_context()))
    return grammar


def generate_parser(
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

    grammar = gsm.add_trivia_rule_to_grammar(grammar, context)

    # Generate parser (reusing existing CST module)
    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module, context=context)
    pgen = gsm2parser.ParserGenerator(grammar=grammar, cstgen=cstgen, context=context)

    # Compile parser class
    parser_ast = compiler.compile_class(pgen.parser_class, context)
    imports = [
        pyreg.Module(("collections", "abc")),
        pyreg.Module(("typing",)),
        pyreg.Module(("fltk", "fegen", "pyrt", "errors")),
        pyreg.Module(("fltk", "fegen", "pyrt", "memo")),
        pyreg.Module(("fltk", "fegen", "pyrt", "terminalsrc")),
        cst_module,
    ]

    # Generate parser module
    parser_mod = pygen.module(module.import_path for module in imports)
    # `from __future__ import annotations` keeps the parser's span-typed annotations as lazy
    # strings.  The parser annotates its terminal spans with the concrete pure-Python
    # `fltk.fegen.pyrt.terminalsrc.Span` (runtime-imported above for construction) — it names
    # neither the `fltk.fegen.pyrt.span` selector nor `fltk._native`, so it never touches
    # span.py's process-wide native-span probe in any environment.
    parser_mod.body.insert(0, pygen.stmt("from __future__ import annotations"))
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
    cst_module_name: Annotated[
        str, typer.Argument(help='Module import name for CST classes (usually "<base_name>_cst")')
    ],
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
        typer.Option(
            "--protocol-only",
            help=(
                "Generate only the {base_name}_cst_protocol.py module, skipping the shared CST "
                "module and both parsers. Use when only the typing-protocol surface is needed "
                "(e.g. to type a Rust-backed unparser .pyi against)."
            ),
        ),
    ] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Generate parsers from an FLTK grammar file.

    By default, this command generates a shared CST module and both parser variants:
    - Shared CST classes that work with both parsers
    - Parser without trivia preservation (faster, for compilers/interpreters)
    - Parser with trivia preservation (for formatters/syntax highlighters)

    Use --trivia-only or --no-trivia-only to generate just one parser variant.
    Use --protocol-only to generate just the CST protocol module (no CST, no parsers).

    Files generated by default:
    - {base_name}_cst.py (shared CST classes)
    - {base_name}_cst_protocol.py (typing protocol)
    - {base_name}_parser.py (no trivia)
    - {base_name}_trivia_parser.py (with trivia)

    Examples:
        genparser generate grammar.fltkg mylang mylang.cst
        genparser generate grammar.fltkg mylang mylang.cst --trivia-only
        genparser generate grammar.fltkg mylang mylang.cst --protocol-only
        genparser generate grammar.fltkg mylang mylang.cst -o output/ --verbose
    """
    # Validate mutually exclusive options
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

    if output_dir is None:
        output_dir = Path(".")

    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        typer.echo(f"Parsing grammar file: {grammar_file}")

    grammar = parse_grammar_file(grammar_file)

    # Build the trivia-enhanced grammar and CST generator (contains all possible nodes).
    # The CstGenerator is the shared source for both the CST module and the protocol module.
    grammar = gsm.add_trivia_rule_to_grammar(grammar, create_default_context())
    cst_module = pyreg.Module(cst_module_name.split("."))
    cstgen = gsm2tree.CstGenerator(grammar=grammar, py_module=cst_module, context=create_default_context())

    # Generate shared CST module first (skipped under --protocol-only)
    if not protocol_only:
        shared_cst = output_dir / f"{base_name}_cst.py"

        if verbose:
            typer.echo("Generating shared CST module...")

        cst_mod = cstgen.gen_py_module()
        cst_text = ast.unparse(cst_mod)  # generate before opening file so an error doesn't leave a partial file
        try:
            with shared_cst.open("w", newline="\n") as f:
                f.write(cst_text)
        except OSError as e:
            typer.echo(f"Error: Failed to write shared CST file '{shared_cst}': {e}", err=True)
            raise typer.Exit(1) from e

    shared_cst_protocol = output_dir / f"{base_name}_cst_protocol.py"
    if verbose:
        typer.echo("Generating CST Protocol module...")
    # Generate before opening the file so any AST construction error doesn't leave a partial artifact.
    protocol_mod = cstgen.gen_protocol_module()
    # Prepend file-level ruff suppressions:
    # N802: CstModule @property methods have PascalCase names matching module attributes (intentional).
    # E501 is NOT added here: `make fix` reformats the generated file so no lines exceed the limit,
    # and including E501 causes RUF100 (unused noqa) after `make fix`.
    # F821 is NOT added here: nested Label references resolve via `from __future__ import annotations`
    # and ruff does not raise F821 for them; including F821 causes RUF100 (unused noqa) after `make fix`.
    protocol_text = "# ruff: noqa: N802\n" + ast.unparse(protocol_mod)
    try:
        with shared_cst_protocol.open("w", newline="\n") as f:
            f.write(protocol_text)
    except OSError as e:
        typer.echo(f"Error: Failed to write CST Protocol file '{shared_cst_protocol}': {e}", err=True)
        raise typer.Exit(1) from e

    if protocol_only:
        if verbose:
            typer.echo("✓ Protocol generation completed successfully")
            typer.echo(f"CST Protocol: {shared_cst_protocol}")
        return

    # Determine which parsers to generate
    generate_no_trivia = not trivia_only
    generate_trivia = not no_trivia_only

    # Generate non-trivia parser
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

    # Generate trivia-preserving parser
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

    if verbose:
        typer.echo("✓ Parser generation completed successfully")
        typer.echo(f"Shared CST: {output_dir / f'{base_name}_cst.py'}")
        if generate_no_trivia:
            typer.echo(f"Non-trivia parser: {output_dir / f'{base_name}_parser.py'}")
        if generate_trivia:
            typer.echo(f"Trivia parser: {output_dir / f'{base_name}_trivia_parser.py'}")


def _parse_grammar_raw(grammar_file: Path) -> gsm.Grammar:
    """Parse a grammar file and return the raw GSM without trivia processing.

    Unlike parse_grammar_file, this does NOT apply add_trivia_rule_to_grammar or
    classify_trivia_rules.  This is the correct input for RustCstGenerator, which
    applies trivia processing internally.
    """
    return _read_and_parse_grammar(grammar_file)


def _write_output_file(output_file: Path, src: str, artifact_label: str = "output file") -> None:
    """Write generated source to ``output_file``, exiting with a CLI error on failure.

    Shared by the Rust-backend subcommands (gen-rust-cst / gen-rust-parser / gen-rust-unparser /
    gen-rust-lib), which all write generated artifacts with the same error contract (so the
    message/exit-code stay a single maintenance point).  ``artifact_label`` names the artifact in
    the error message; it is overridden to ``".pyi stub"`` for the optional stub writes so the
    ``.rs`` and ``.pyi`` writes share this one helper instead of duplicating the try/except.
    """
    try:
        output_file.write_text(src)
    except Exception as e:
        typer.echo(f"Error: Failed to write {artifact_label} '{output_file}': {e}", err=True)
        raise typer.Exit(1) from e


@app.command(name="gen-rust-cst")
def gen_rust_cst(
    grammar_file: Annotated[Path, typer.Argument(help="Path to the FLTK grammar file (.fltkg)")],
    output_file: Annotated[Path, typer.Argument(help="Path to write the .rs source")],
    protocol_module: Annotated[
        str | None,
        typer.Option(
            "--protocol-module",
            help=(
                "Import path of the committed protocol module for this grammar "
                "(e.g. 'fltk.fegen.fltk_cst_protocol'). When provided, also emits a .pyi stub "
                "so pyright can verify the PyO3 surface satisfies CstModule. "
                "When omitted, no .pyi is emitted (backward compatible)."
            ),
        ),
    ] = None,
    pyi_output: Annotated[
        Path | None,
        typer.Option(
            "--pyi-output",
            help=(
                "Path to write the .pyi stub. The canonical location is "
                "<name>/cst.pyi inside a stub-package directory (alongside "
                "<name>/__init__.pyi). Defaults to output_file with .pyi suffix "
                "when --protocol-module is given. Override when the .rs stem differs "
                "from the compiled module's import name — pyright resolves stubs by "
                "import name, not .rs file name. "
                "Example: 'src/cst_fegen.rs' backs 'fltk._native.fegen_cst', "
                "so --pyi-output fltk/_native/fegen_cst.pyi is required."
            ),
        ),
    ] = None,
) -> None:
    """Emit Rust CST source (.rs) from a grammar file, and optionally a .pyi stub.

    Generates a standalone PyO3 Rust extension source file from a grammar.
    The user compiles and installs it with their own build tool (e.g. maturin).
    The generated .rs file is independent of FLTK's crate at link time; it
    depends on fltk._native only at runtime for the UnknownSpan sentinel.

    The generated cst.rs wires into the cst submodule of the compiled extension,
    e.g. <module>.cst. Import Span and SourceText from fltk._native, not from
    the generated module.

    Wire the generated cst.rs and parser.rs into your lib.rs like this:

        use fltk_cst_core::register_submodule;
        #[pymodule]
        fn my_grammar(m: &Bound<'_, PyModule>) -> PyResult<()> {
            register_submodule(m, "cst", cst::register_classes)?;
            register_submodule(m, "parser", parser::register_classes)?;
            Ok(())
        }

    When --protocol-module is given, also emits a .pyi stub derived from the same
    GSM so pyright can verify the compiled extension satisfies CstModule without a
    cast. The stub goes in a stub-package directory <name>/ as <name>/cst.pyi;
    use --pyi-output to control the exact path.

    Examples:
        genparser gen-rust-cst grammar.fltkg output/cst.rs
        genparser gen-rust-cst grammar.fltkg src/cst_fegen.rs \\
            --protocol-module fltk.fegen.fltk_cst_protocol \\
            --pyi-output fltk/_native/fegen_cst.pyi
    """
    if pyi_output is not None and protocol_module is None:
        typer.echo("Error: --pyi-output requires --protocol-module", err=True)
        raise typer.Exit(1)
    if protocol_module is not None:
        _validate_protocol_module(protocol_module)

    grammar = _parse_grammar_raw(grammar_file)
    try:
        gen = gsm2tree_rs.RustCstGenerator(grammar, source_name=str(grammar_file))
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    # Generate .pyi text before opening any file so a generation error doesn't leave partial files.
    pyi_text: str | None = None
    try:
        if protocol_module is not None:
            pyi_text = gen.generate_pyi(protocol_module)
        src = gen.generate()
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e
    _write_output_file(output_file, src)

    if pyi_text is not None:
        stub_path = pyi_output if pyi_output is not None else output_file.with_suffix(".pyi")
        _write_output_file(stub_path, pyi_text, ".pyi stub")


_CST_MOD_PATH_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)*$")


def _validate_cst_mod_path(cst_mod_path: str) -> None:
    """Exit with a CLI error when ``cst_mod_path`` is not a valid Rust module path.

    Shared by gen-rust-parser / gen-rust-unparser, which both accept ``--cst-mod-path`` and
    interpolate it into the generated ``use``/``mod`` lines, so the validation error stays a
    single maintenance point.
    """
    if not _CST_MOD_PATH_RE.match(cst_mod_path):
        typer.echo(f"Error: --cst-mod-path {cst_mod_path!r} is not a valid Rust module path", err=True)
        raise typer.Exit(1)


_PROTOCOL_MODULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def _validate_protocol_module(protocol_module: str) -> None:
    """Exit with a CLI error when ``protocol_module`` is not a valid Python dotted module path.

    Shared by gen-rust-cst / gen-rust-unparser, which both interpolate ``--protocol-module``
    verbatim into the generated ``.pyi`` stub's ``import <module> as _proto`` line.  Without this
    guard a malformed value (empty, embedded spaces, leading/trailing dot) raises no exception:
    the generator exits 0 and writes a ``.pyi`` that only fails later when a downstream type
    checker parses it.  Validating up front turns that into an immediate, diagnosable CLI error
    before any file is written.
    """
    if not _PROTOCOL_MODULE_RE.match(protocol_module):
        typer.echo(f"Error: --protocol-module {protocol_module!r} is not a valid Python module path", err=True)
        raise typer.Exit(1)


@app.command(name="gen-rust-parser")
def gen_rust_parser(
    grammar_file: Annotated[Path, typer.Argument(help="Path to the FLTK grammar file (.fltkg)")],
    output_file: Annotated[Path, typer.Argument(help="Path to write the .rs source")],
    cst_mod_path: Annotated[
        str,
        typer.Option(
            "--cst-mod-path",
            help="Rust module path to the generated CST module (e.g. 'super::cst')",
        ),
    ] = "super::cst",
) -> None:
    """Emit Rust parser source (.rs) from a grammar file."""
    _validate_cst_mod_path(cst_mod_path)

    grammar = _parse_grammar_raw(grammar_file)
    try:
        gen = gsm2parser_rs.RustParserGenerator(grammar, cst_mod_path=cst_mod_path, source_name=str(grammar_file))
        src = gen.generate()
    except (ValueError, RuntimeError, NotImplementedError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    _write_output_file(output_file, src)


@app.command(name="gen-rust-unparser")
def gen_rust_unparser(
    grammar_file: Annotated[Path, typer.Argument(help="Path to the FLTK grammar file (.fltkg)")],
    output_file: Annotated[Path, typer.Argument(help="Path to write the .rs source")],
    cst_mod_path: Annotated[
        str,
        typer.Option(
            "--cst-mod-path",
            help="Rust module path to the generated CST module (e.g. 'super::cst')",
        ),
    ] = "super::cst",
    format_config: Annotated[
        Path | None,
        typer.Option(
            "--format-config",
            help=(
                "Path to a .fltkfmt formatter-config file.  Its spacing/anchor/disposition "
                "decisions are baked into the generated unparser at generation time.  When "
                "omitted, the default FormatterConfig (no extra spacing) is used."
            ),
        ),
    ] = None,
    protocol_module: Annotated[
        str | None,
        typer.Option(
            "--protocol-module",
            help=(
                "Import path of the committed CST protocol module for this grammar "
                "(e.g. 'mylang.cst_protocol'). When provided, also emits a .pyi stub "
                "describing the Unparser/Doc Python surface so pyright can type-check "
                "downstream calls; each unparse_{rule} method's node parameter is typed "
                "against this module. When omitted, no .pyi is emitted (backward compatible)."
            ),
        ),
    ] = None,
    pyi_output: Annotated[
        Path | None,
        typer.Option(
            "--pyi-output",
            help=(
                "Path to write the .pyi stub. Defaults to output_file with .pyi suffix "
                "when --protocol-module is given. Override when the .rs stem differs from "
                "the compiled module's import name (pyright resolves stubs by import name, "
                "not .rs file name)."
            ),
        ),
    ] = None,
) -> None:
    """Emit Rust unparser source (.rs) from a grammar file, and optionally a .pyi stub.

    Mirrors gen-rust-parser: parses the grammar, optionally parses a .fltkfmt
    format-config file into a FormatterConfig, and writes the generated unparser
    .rs.  The generated pure-Rust layer links against the fltk-unparser-core
    runtime crate; the optional PyO3 wrapper (gated behind the `python` feature)
    accepts only the Rust CST handles, so a Python caller must pair it with the
    Rust parser backend.

    When --protocol-module is given, also emits a .pyi stub describing the
    Unparser/Doc Python surface so downstream code is type-checked;
    use --pyi-output to control the exact path.

    Examples:
        genparser gen-rust-unparser grammar.fltkg output/unparser.rs
        genparser gen-rust-unparser grammar.fltkg src/unparser.rs \\
            --cst-mod-path super::cst --format-config grammar.fltkfmt
        genparser gen-rust-unparser grammar.fltkg src/unparser.rs \\
            --protocol-module mylang.cst_protocol --pyi-output mylang/unparser.pyi
    """
    _validate_cst_mod_path(cst_mod_path)

    if pyi_output is not None and protocol_module is None:
        typer.echo("Error: --pyi-output requires --protocol-module", err=True)
        raise typer.Exit(1)
    if protocol_module is not None:
        _validate_protocol_module(protocol_module)

    grammar = _parse_grammar_raw(grammar_file)

    formatter_config = None
    if format_config is not None:
        try:
            formatter_config = parse_format_config_file(format_config)
        except (ValueError, OSError) as e:
            # OSError (not just FileNotFoundError) so a --format-config path that exists but is
            # unreadable / is a directory surfaces the clean CLI error, not a raw traceback.
            # FileNotFoundError is an OSError subclass, so the not-found message still applies.
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from e

    # Generate the .pyi text (when requested) and the .rs together, before writing either file,
    # so a generation error leaves no partial artifacts -- matching gen-rust-cst.
    pyi_text: str | None = None
    try:
        gen = gsm2unparser_rs.RustUnparserGenerator(
            grammar,
            formatter_config=formatter_config,
            cst_mod_path=cst_mod_path,
            source_name=str(grammar_file),
        )
        if protocol_module is not None:
            pyi_text = gen.generate_pyi(protocol_module)
        src = gen.generate()
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    _write_output_file(output_file, src)

    if pyi_text is not None:
        stub_path = pyi_output if pyi_output is not None else output_file.with_suffix(".pyi")
        _write_output_file(stub_path, pyi_text, ".pyi stub")


@app.command(name="gen-rust-lib")
def gen_rust_lib(
    output_file: Annotated[Path, typer.Argument(help="Path to write the lib.rs source")],
    module_name: Annotated[
        str,
        typer.Option(
            "--module-name",
            help="The #[pymodule] function name / importable module name (e.g. 'clockwork_native').",
        ),
    ],
    no_parser: Annotated[
        bool,
        typer.Option("--no-parser", help="Emit a CST-only lib.rs (omit mod parser; and its registration)."),
    ] = False,
    unparser: Annotated[
        bool,
        typer.Option("--unparser", help="Also include the unparser submodule (mod unparser; and its registration)."),
    ] = False,
    no_cst: Annotated[
        bool,
        typer.Option(
            "--no-cst",
            help="Emit zero submodules (omit mod cst; and all registrations). "
            "Use with --register-span-types/--unknown-span-static for runtime-only libs.",
        ),
    ] = False,
    register_span_types: Annotated[
        bool,
        typer.Option("--register-span-types", help="Emit Span/SourceText class registration and span module import."),
    ] = False,
    unknown_span_static: Annotated[
        bool,
        typer.Option("--unknown-span-static", help="Emit the UNKNOWN_SPAN static declaration and once-init."),
    ] = False,
) -> None:
    """Emit a Rust lib.rs module-wiring boilerplate for a standard pyo3 cdylib.

    Unlike gen-rust-cst / gen-rust-parser, this command needs no grammar file —
    lib.rs has no rule-derived content.  It is parameterized only by the module
    name and whether a parser submodule is included.

    Standard path: declares mod cst; (and mod parser; unless --no-parser, and
    mod unparser; when --unparser), and a #[pymodule] fn that registers them as
    Python submodules.

    Runtime-only path (--no-cst --register-span-types --unknown-span-static):
    emits span/UNKNOWN_SPAN wiring with zero submodules. Used for fltk._native.
    (--unparser, like --no-parser, has no effect when --no-cst is given.)

    Note: do NOT include #![recursion_limit] in the module name or output — the
    fltk_pyo3_cdylib Bazel macro injects it at assembly time.

    Examples:
        genparser gen-rust-lib lib.rs --module-name clockwork_native
        genparser gen-rust-lib lib.rs --module-name my_module --no-parser
        genparser gen-rust-lib lib.rs --module-name my_module --unparser
        genparser gen-rust-lib src/lib.rs --module-name _native --no-cst --register-span-types --unknown-span-static
    """
    if not no_cst and (register_span_types or unknown_span_static):
        typer.echo(
            "Error: --register-span-types and --unknown-span-static require --no-cst. "
            "Combining span-type registration with grammar submodules is not a supported use case.",
            err=True,
        )
        raise typer.Exit(1)
    if no_cst:
        spec = gsm2lib_rs.LibSpec(
            module_name=module_name,
            submodules=(),
            register_span_types=register_span_types,
            unknown_span_static=unknown_span_static,
        )
    else:
        spec = gsm2lib_rs.LibSpec.standard(module_name, with_parser=not no_parser, with_unparser=unparser)
    try:
        gen = gsm2lib_rs.RustLibGenerator(spec)
        src = gen.generate()
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    _write_output_file(output_file, src)


if __name__ == "__main__":
    app()
