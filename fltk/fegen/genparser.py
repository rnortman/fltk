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
from fltk.fegen.ast_config import Backend
from fltk.fegen.pyrt import errors, terminalsrc
from fltk.iir.context import CompilerContext, create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg
from fltk.plumbing import (
    generate_ast_source,
    generate_rust_ast_source,
    generate_rust_serde_source,
    parse_ast_config_file,
    parse_format_config_file,
)
from fltk.unparse import gsm2unparser_rs

if TYPE_CHECKING:
    from fltk.fegen import fltk_cst_protocol as cst

app = typer.Typer(
    name="genparser",
    help="Generate parsers from FLTK grammar files",
    add_completion=False,
)


def _read_and_parse_grammar(grammar_file: Path) -> gsm.Grammar:
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
    grammar = cst2gsm.visit_grammar(cast("cst.Grammar", result.result))

    try:
        return gsm.expand_inline_dispositions(grammar)
    except ValueError as e:
        typer.echo(f"Error: Invalid grammar file '{grammar_file}': {e}", err=True)
        raise typer.Exit(1) from e


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
        typer.Option(
            "--protocol-only",
            help=(
                "Generate only the {base_name}_cst_protocol.py module, skipping the shared CST "
                "module and both parsers. Use when only the typing-protocol surface is needed "
                "(e.g. to type a Rust-backed unparser .pyi against)."
            ),
        ),
    ] = False,
    protocol: Annotated[
        bool,
        typer.Option(
            "--protocol",
            help=(
                "Also write the {base_name}_cst_protocol.py typing-protocol module alongside the "
                "CST and parsers. Off by default. (--protocol-only already implies protocol "
                "emission and remains authoritative.)"
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
    Use --protocol to also write the CST protocol module (off by default).
    Use --protocol-only to generate just the CST protocol module (no CST, no parsers).

    Files generated by default:
    - {base_name}_cst.py (shared CST classes)
    - {base_name}_parser.py (no trivia)
    - {base_name}_trivia_parser.py (with trivia)

    Files generated only when requested:
    - {base_name}_cst_protocol.py (typing protocol; --protocol or --protocol-only)

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

    # Protocol module is opt-in: written only with --protocol (alongside CST/parsers) or
    # --protocol-only (which short-circuits below). A bare `generate` writes no protocol module.
    if protocol or protocol_only:
        shared_cst_protocol = output_dir / f"{base_name}_cst_protocol.py"
        if verbose:
            typer.echo("Generating CST Protocol module...")
        # Generate before opening the file so any AST construction error doesn't leave a partial
        # artifact.  gen_protocol_module_text is the single home for the rendering formula and the
        # file-level ruff-suppression rationale, shared with the Rust path's generate_protocol.
        protocol_text = cstgen.gen_protocol_module_text()
        try:
            with shared_cst_protocol.open("w", newline="\n") as f:
                f.write(protocol_text)
        except OSError as e:
            typer.echo(f"Error: Failed to write CST Protocol file '{shared_cst_protocol}': {e}", err=True)
            raise typer.Exit(1) from e

    if protocol_only:
        if verbose:
            typer.echo("✓ Protocol generation completed successfully")
            typer.echo(f"CST Protocol: {output_dir / f'{base_name}_cst_protocol.py'}")
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


@app.command(name="gen-ast")
def gen_ast(
    grammar_file: Annotated[Path, typer.Argument(help="Path to the FLTK grammar file (.fltkg)")],
    base_name: Annotated[str, typer.Argument(help="Base name for the output file (writes {base_name}_ast.py)")],
    cst_module_name: Annotated[
        str, typer.Argument(help='Module import name for CST classes (usually "<base_name>_cst")')
    ],
    *,
    ast_config: Annotated[
        Path | None,
        typer.Option(
            "--ast-config",
            help=(
                "Path to a .fltkast sidecar shaping the generated AST (type coercions, "
                "transparency, naming and shape overrides, custom rules). Validated against "
                "the grammar at generation time. When omitted, the AST is pure Tier 0 — "
                "derived from the grammar alone."
            ),
        ),
    ] = None,
    parser_module: Annotated[
        str | None,
        typer.Option(
            "--parser-module",
            help=(
                "Import path of the generated parser module for this grammar "
                "(e.g. 'mylang.mylang_parser'). When given, the AST module gains a "
                "parse(source, filename=None) convenience returning the goal rule's AST. "
                "When omitted, no parse() is emitted."
            ),
        ),
    ] = None,
    unparser_module: Annotated[
        str | None,
        typer.Option(
            "--unparser-module",
            help=(
                "Import path of the generated unparser module for this grammar "
                "(e.g. 'mylang.mylang_unparser'). When given, the AST module gains an "
                "unparse(value, renderer_config=None) convenience rendering an AST to source "
                "text. When omitted, no unparse() is emitted."
            ),
        ),
    ] = None,
    goal: Annotated[
        str | None,
        typer.Option(
            "--goal",
            help=(
                "Rule the parse()/unparse() conveniences target. Defaults to the grammar's "
                "first rule, matching the Python parse_text default."
            ),
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Output directory for the generated module"),
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Enable verbose output")] = False,
) -> None:
    """Emit Python AST node classes and CST converters ({base_name}_ast.py) from a grammar.

    The generated module holds one dataclass per rule (plus payload classes, union aliases
    and value enums as the rule shapes require) and the converters in both directions:
    from_cst/to_cst members on every class and module-level {rule}_from_cst / {rule}_to_cst
    functions. It imports the CST module named by CST_MODULE, so generate that module first
    with the `generate` command.

    Naming a parser module adds parse(); naming an unparser module adds unparse(), closing
    the text -> AST -> text loop. A .fltkast sidecar passed with --ast-config shapes the
    result beyond the grammar-derived default.

    Examples:
        genparser gen-ast grammar.fltkg mylang mylang.mylang_cst -o mylang/
        genparser gen-ast grammar.fltkg mylang mylang.mylang_cst \\
            --ast-config grammar.fltkast \\
            --parser-module mylang.mylang_parser \\
            --unparser-module mylang.mylang_unparser --goal config -o mylang/
    """
    _validate_python_module(cst_module_name, "CST_MODULE")
    if parser_module is not None:
        _validate_python_module(parser_module, "--parser-module")
    if unparser_module is not None:
        _validate_python_module(unparser_module, "--unparser-module")

    if output_dir is None:
        output_dir = Path(".")

    if verbose:
        typer.echo(f"Parsing grammar file: {grammar_file}")

    grammar = parse_grammar_file(grammar_file)

    resolved_config = None
    if ast_config is not None:
        if verbose:
            typer.echo(f"Parsing AST config file: {ast_config}")
        try:
            # Only the Python backend is generated here, so a `custom(...)` list may omit its
            # Rust entries.  AstConfigError is a ValueError; OSError covers an unreadable path.
            resolved_config = parse_ast_config_file(ast_config, grammar, {Backend.PYTHON})
        except (ValueError, OSError) as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from e

    if verbose:
        typer.echo("Generating AST module...")

    # Generate before creating the output directory or opening the file so a model error leaves
    # no artifacts behind.  AstModelError is a ValueError, as is the unknown-goal error.
    try:
        src = generate_ast_source(
            grammar, cst_module_name, parser_module, unparser_module, goal, ast_config=resolved_config
        )
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{base_name}_ast.py"
    _write_output_file(output_file, src, "AST module")

    if verbose:
        typer.echo("✓ AST generation completed successfully")
        typer.echo(f"AST module: {output_file}")


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
    *,
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
    protocol_output: Annotated[
        Path | None,
        typer.Option(
            "--protocol-output",
            help=(
                "Path to write the generated protocol .py module. Requires --protocol-module "
                "(which supplies the protocol's dotted import path that the .pyi imports). When "
                "set, the protocol module is written here AND the .pyi is emitted too — the protocol "
                ".py and its .pyi are a matched pair. The output is byte-identical to the Python "
                "`generate --protocol` protocol module for the same grammar. Off by default."
            ),
        ),
    ] = None,
    init_pyi_output: Annotated[
        Path | None,
        typer.Option(
            "--init-pyi-output",
            help=(
                "Path to write the stub-package __init__.pyi marker. Requires --extension-name "
                "and --submodules. The marker is comment-only and makes the <name>/ directory a "
                "recognized stub package for pyright (its top-level module exports nothing directly, "
                "only the listed submodules). Independent of --protocol-module."
            ),
        ),
    ] = None,
    extension_name: Annotated[
        str | None,
        typer.Option(
            "--extension-name",
            help=(
                "The compiled extension's importable name (e.g. 'fegen_rust_cst'), interpolated "
                "into the --init-pyi-output marker. Required when --init-pyi-output is given."
            ),
        ),
    ] = None,
    submodules: Annotated[
        str | None,
        typer.Option(
            "--submodules",
            help=(
                "Comma-separated names of the submodules the extension registers (e.g. "
                "'cst,parser'), interpolated into the --init-pyi-output marker. Required when "
                "--init-pyi-output is given; each entry must be a valid identifier."
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

    When --protocol-output is given (which requires --protocol-module), the Rust
    generator also writes the protocol .py module itself, byte-identical to the
    Python `generate --protocol` output, alongside the .pyi.

    When --init-pyi-output is given (which requires --extension-name and
    --submodules), also writes a comment-only stub-package __init__.pyi marker so
    the <name>/ directory is a recognized stub package for pyright. The marker is
    independent of --protocol-module.

    Examples:
        genparser gen-rust-cst grammar.fltkg output/cst.rs
        genparser gen-rust-cst grammar.fltkg src/cst_fegen.rs \\
            --protocol-module fltk.fegen.fltk_cst_protocol \\
            --pyi-output fltk/_native/fegen_cst.pyi
        genparser gen-rust-cst grammar.fltkg out/cst.rs \\
            --protocol-module mylang.cst_protocol \\
            --protocol-output mylang/cst_protocol.py
        genparser gen-rust-cst grammar.fltkg out/cst/cst.rs \\
            --init-pyi-output out/cst/__init__.pyi \\
            --extension-name mylang_cst --submodules cst,parser
    """
    if pyi_output is not None and protocol_module is None:
        typer.echo("Error: --pyi-output requires --protocol-module", err=True)
        raise typer.Exit(1)
    if protocol_output is not None and protocol_module is None:
        typer.echo("Error: --protocol-output requires --protocol-module", err=True)
        raise typer.Exit(1)
    if protocol_module is not None:
        _validate_protocol_module(protocol_module)
    # Render the grammar-independent stub-package marker up front so a malformed marker never
    # reaches disk (validation precedes any output write, and even the grammar parse).
    init_pyi_text = _render_init_pyi(init_pyi_output, extension_name, submodules)

    grammar = _parse_grammar_raw(grammar_file)
    try:
        gen = gsm2tree_rs.RustCstGenerator(grammar, source_name=str(grammar_file))
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    # Generate all artifact text before opening any file so a generation error doesn't leave
    # partial files. Write order: .rs, then the protocol .py, then the .pyi.
    pyi_text: str | None = None
    protocol_text: str | None = None
    try:
        if protocol_module is not None:
            pyi_text = gen.generate_pyi(protocol_module)
        if protocol_output is not None:
            protocol_text = gen.generate_protocol()
        src = gen.generate()
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e
    _write_output_file(output_file, src)

    if protocol_output is not None:
        # generate_protocol() is the only assignment to protocol_text and any error in it exits
        # above, so protocol_text is non-None whenever protocol_output is set.  Assert the invariant
        # (mirroring the init_pyi_text writer below) rather than a double-condition guard that would
        # silently skip the write on a control-flow defect.
        assert protocol_text is not None
        _write_output_file(protocol_output, protocol_text, "protocol module")

    if pyi_text is not None:
        stub_path = pyi_output if pyi_output is not None else output_file.with_suffix(".pyi")
        _write_output_file(stub_path, pyi_text, ".pyi stub")

    if init_pyi_output is not None:
        # _render_init_pyi returns a non-None string whenever init_pyi_output is set (it exits
        # otherwise), so the marker is always written here; the assert documents that invariant
        # and narrows the type for the writer below.
        assert init_pyi_text is not None
        _write_output_file(init_pyi_output, init_pyi_text, "stub-package __init__.pyi")


# ``\Z`` rather than ``$``: ``$`` also matches before a trailing newline, which would let a
# value carrying one through into a ``use`` line.
_RUST_MOD_PATH_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*(::[A-Za-z_][A-Za-z0-9_]*)*\Z")


def _validate_rust_mod_path(mod_path: str, option: str) -> None:
    """Exit with a CLI error when ``mod_path`` is not a valid Rust module path.

    ``option`` names the CLI option in the message.  Every caller interpolates the value verbatim
    into a generated ``use``/``mod`` line, so a malformed value would otherwise reach disk and fail
    only when rustc reads it.
    """
    if not _RUST_MOD_PATH_RE.match(mod_path):
        typer.echo(f"Error: {option} {mod_path!r} is not a valid Rust module path", err=True)
        raise typer.Exit(1)


def _validate_cst_mod_path(cst_mod_path: str) -> None:
    """Exit with a CLI error when ``--cst-mod-path`` is not a valid Rust module path.

    Shared by gen-rust-parser / gen-rust-unparser / gen-rust-ast, which all accept
    ``--cst-mod-path``.
    """
    _validate_rust_mod_path(cst_mod_path, "--cst-mod-path")


# ``\Z`` rather than ``$``: ``$`` also matches before a trailing newline, which would let a
# value carrying one through into an ``import`` line.
_PROTOCOL_MODULE_RE = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*\Z")


def _validate_python_module(module: str, option: str) -> None:
    """Exit with a CLI error when ``module`` is not a valid Python dotted module path.

    ``option`` names the CLI option or argument in the message.  Every caller interpolates the
    value verbatim into generated source — a ``.pyi`` stub's ``import <module> as _proto`` line,
    or an AST module's ``import <module> as cst``.  Without this guard a malformed value (empty,
    embedded spaces, leading/trailing dot) raises no exception: the generator exits 0 and writes
    a file that only fails later when something parses it.  Validating up front turns that into
    an immediate, diagnosable CLI error before any file is written.
    """
    if not _PROTOCOL_MODULE_RE.match(module):
        typer.echo(f"Error: {option} {module!r} is not a valid Python module path", err=True)
        raise typer.Exit(1)


def _validate_protocol_module(protocol_module: str) -> None:
    """Exit with a CLI error when ``--protocol-module`` is not a valid Python dotted module path.

    Shared by gen-rust-cst / gen-rust-unparser, which both interpolate the value into the
    generated ``.pyi`` stub.
    """
    _validate_python_module(protocol_module, "--protocol-module")


def _render_init_pyi(
    init_pyi_output: Path | None,
    extension_name: str | None,
    submodules: str | None,
) -> str | None:
    """Validate the stub-package marker options and render the ``__init__.pyi`` text.

    Shared by gen-rust-cst / gen-rust-unparser, which can both emit the grammar-independent
    stub-package marker alongside the ``.pyi`` they already write.  Returns
    ``None`` when ``--init-pyi-output`` is not given (no marker requested).  Otherwise exits via
    typer.Exit on a misconfiguration: ``--init-pyi-output`` requires both ``--extension-name``
    and ``--submodules``, and the extension name plus each comma-separated submodule entry must
    be a valid identifier (enforced by ``render_stub_package_init``).  The text is rendered
    before any output file is opened so a malformed marker never reaches disk.
    """
    if init_pyi_output is None:
        return None
    if extension_name is None or submodules is None:
        typer.echo("Error: --init-pyi-output requires --extension-name and --submodules", err=True)
        raise typer.Exit(1)
    submodule_names = [name.strip() for name in submodules.split(",")]
    try:
        return gsm2lib_rs.render_stub_package_init(extension_name, submodule_names)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e


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
    *,
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
    init_pyi_output: Annotated[
        Path | None,
        typer.Option(
            "--init-pyi-output",
            help=(
                "Path to write the stub-package __init__.pyi marker. Requires --extension-name "
                "and --submodules. The marker is comment-only and makes the <name>/ directory a "
                "recognized stub package for pyright (its top-level module exports nothing directly, "
                "only the listed submodules). Independent of --protocol-module."
            ),
        ),
    ] = None,
    extension_name: Annotated[
        str | None,
        typer.Option(
            "--extension-name",
            help=(
                "The compiled extension's importable name (e.g. 'rust_parser_fixture'), interpolated "
                "into the --init-pyi-output marker. Required when --init-pyi-output is given."
            ),
        ),
    ] = None,
    submodules: Annotated[
        str | None,
        typer.Option(
            "--submodules",
            help=(
                "Comma-separated names of the submodules the extension registers (e.g. "
                "'cst,parser,unparser'), interpolated into the --init-pyi-output marker. Required "
                "when --init-pyi-output is given; each entry must be a valid identifier."
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

    When --init-pyi-output is given (which requires --extension-name and
    --submodules), also writes a comment-only stub-package __init__.pyi marker so
    the <name>/ directory is a recognized stub package for pyright. The marker is
    independent of --protocol-module, so it can be attached to this unparser
    invocation even when the package's .pyi comes from the unparser path.

    Examples:
        genparser gen-rust-unparser grammar.fltkg output/unparser.rs
        genparser gen-rust-unparser grammar.fltkg src/unparser.rs \\
            --cst-mod-path super::cst --format-config grammar.fltkfmt
        genparser gen-rust-unparser grammar.fltkg src/unparser.rs \\
            --protocol-module mylang.cst_protocol --pyi-output mylang/unparser.pyi
        genparser gen-rust-unparser grammar.fltkg out/pkg/unparser.rs \\
            --init-pyi-output out/pkg/__init__.pyi \\
            --extension-name mylang_pkg --submodules cst,parser,unparser
    """
    _validate_cst_mod_path(cst_mod_path)

    if pyi_output is not None and protocol_module is None:
        typer.echo("Error: --pyi-output requires --protocol-module", err=True)
        raise typer.Exit(1)
    if protocol_module is not None:
        _validate_protocol_module(protocol_module)
    # Render the grammar-independent stub-package marker up front so a malformed marker never
    # reaches disk (validation precedes any output write, and even the grammar parse).
    init_pyi_text = _render_init_pyi(init_pyi_output, extension_name, submodules)

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

    if init_pyi_output is not None:
        # _render_init_pyi returns a non-None string whenever init_pyi_output is set (it exits
        # otherwise), so the marker is always written here; the assert documents that invariant
        # and narrows the type for the writer below.
        assert init_pyi_text is not None
        _write_output_file(init_pyi_output, init_pyi_text, "stub-package __init__.pyi")


@app.command(name="gen-rust-ast")
def gen_rust_ast(
    grammar_file: Annotated[Path, typer.Argument(help="Path to the FLTK grammar file (.fltkg)")],
    output_file: Annotated[Path, typer.Argument(help="Path to write the .rs source")],
    *,
    ast_config: Annotated[
        Path | None,
        typer.Option(
            "--ast-config",
            help=(
                "Path to a .fltkast sidecar shaping the generated AST (type coercions, "
                "transparency, naming and shape overrides, custom rules). Validated against "
                "the grammar at generation time. When omitted, the AST is pure Tier 0 — "
                "derived from the grammar alone."
            ),
        ),
    ] = None,
    cst_mod_path: Annotated[
        str,
        typer.Option(
            "--cst-mod-path",
            help="Rust module path to the generated CST module (e.g. 'super::cst')",
        ),
    ] = "super::cst",
    parser_mod_path: Annotated[
        str | None,
        typer.Option(
            "--parser-mod-path",
            help=(
                "Rust module path to the generated parser module (e.g. 'super::parser'). When "
                "given, the AST module gains a parse_str(src, filename) entry point returning the "
                "goal rule's AST. When omitted, no parse_str is emitted."
            ),
        ),
    ] = None,
    unparser_mod_path: Annotated[
        str | None,
        typer.Option(
            "--unparser-mod-path",
            help=(
                "Rust module path to the generated unparser module (e.g. 'super::unparser'). When "
                "given, the AST module gains an unparse_str(value, max_width, indent_width) entry "
                "point rendering an AST back to source text. When omitted, no unparse_str is emitted."
            ),
        ),
    ] = None,
    goal: Annotated[
        str | None,
        typer.Option(
            "--goal",
            help=(
                "Rule the parse_str/unparse_str entry points target. Defaults to the grammar's "
                "first rule carrying an AST type."
            ),
        ),
    ] = None,
) -> None:
    """Emit Rust AST source (.rs) from a grammar file.

    The generated module holds one Rust type per rule (plus payload structs, sums and value
    enums as the rule shapes require) and the converters in both directions: from_cst/to_cst
    associated functions on every type. It references the generated Rust CST module named by
    --cst-mod-path, so generate that module first with gen-rust-cst.

    Naming a parser module adds parse_str; naming an unparser module adds unparse_str, closing
    the text -> AST -> text loop. A .fltkast sidecar passed with --ast-config shapes the result
    beyond the grammar-derived default.

    The emitted module's header names the `fltk-ast-core` features it needs (indexmap for keyed
    collections, uuid / decimal for those scalar builtins); enable them on the runtime crate.

    Examples:
        genparser gen-rust-ast grammar.fltkg src/ast.rs
        genparser gen-rust-ast grammar.fltkg src/ast.rs \\
            --ast-config grammar.fltkast \\
            --parser-mod-path super::parser \\
            --unparser-mod-path super::unparser --goal config
    """
    _validate_cst_mod_path(cst_mod_path)
    if parser_mod_path is not None:
        _validate_rust_mod_path(parser_mod_path, "--parser-mod-path")
    if unparser_mod_path is not None:
        _validate_rust_mod_path(unparser_mod_path, "--unparser-mod-path")

    grammar = parse_grammar_file(grammar_file)

    resolved_config = None
    if ast_config is not None:
        try:
            # Only the Rust backend is generated here, so a `custom(...)` list may omit its
            # Python entries.  AstConfigError is a ValueError; OSError covers an unreadable path.
            resolved_config = parse_ast_config_file(ast_config, grammar, {Backend.RUST})
        except (ValueError, OSError) as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from e

    # Generate before opening the file so a model error leaves no artifact behind.  AstModelError
    # is a ValueError, as are the unknown-goal and missing-Rust-type errors.
    try:
        src = generate_rust_ast_source(
            grammar,
            cst_mod_path,
            parser_mod_path=parser_mod_path,
            unparser_mod_path=unparser_mod_path,
            goal_rule=goal,
            ast_config=resolved_config,
            source_name=str(grammar_file),
        )
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    _write_output_file(output_file, src)


@app.command(name="gen-rust-serde")
def gen_rust_serde(
    grammar_file: Annotated[Path, typer.Argument(help="Path to the FLTK grammar file (.fltkg)")],
    output_file: Annotated[Path, typer.Argument(help="Path to write the .rs source")],
    *,
    ast_config: Annotated[
        Path,
        typer.Option(
            "--ast-config",
            help=(
                "Path to the .fltkast sidecar shaping the tree (keyed regions, transparency, "
                "flattening, renames). Required: the shaping statements are what tell the serde "
                "frontend a repetition is a keyed map and what keys it, and there is no "
                "serde-specific directive — one sidecar serves the AST emitters and this one."
            ),
        ),
    ],
    cst_mod_path: Annotated[
        str,
        typer.Option(
            "--cst-mod-path",
            help="Rust module path to the generated CST module (e.g. 'super::cst')",
        ),
    ] = "super::cst",
    parser_mod_path: Annotated[
        str | None,
        typer.Option(
            "--parser-mod-path",
            help=(
                "Rust module path to the generated parser module (e.g. 'super::parser'). When "
                "given, the serde module gains a from_str(src, filename) entry point parsing and "
                "deserializing in one call. When omitted, no from_str is emitted."
            ),
        ),
    ] = None,
    goal: Annotated[
        str | None,
        typer.Option(
            "--goal",
            help=(
                "Rule the from_str entry point targets. Defaults to the grammar's first rule; "
                "every rule gets a from_<rule>_cst entry point either way."
            ),
        ),
    ] = None,
    ast_mod_path: Annotated[
        str | None,
        typer.Option(
            "--ast-mod-path",
            help=(
                "Rust module path to the generated AST module (e.g. 'super::ast'), generated "
                "from the same grammar and sidecar. When given, the serde module also emits a "
                "Deserialize impl for every generated AST type, so a target can declare one as "
                "a field type (configs: IndexMap<String, ast::Expr>). When omitted, the "
                "frontend generates no types at all."
            ),
        ),
    ] = None,
) -> None:
    """Emit the Rust serde frontend (.rs) for a grammar file.

    The generated module describes this grammar's tree to the fltk-serde-core Deserializer —
    one shape per rule, one NodeShape impl per CST node type — and emits the entry points that
    run it: from_<rule>_cst for every rule, plus from_str when a parser module is named. It
    generates no types at all: the consumer's own #[derive(Deserialize)] structs are the schema,
    and serde's unknown-field / missing-field / invalid-type errors come back positioned by CST
    span. Naming an AST module adds a Deserialize impl per generated AST type, which is how an
    expression sub-language becomes a field of a hand-written target.

    It references the generated Rust CST module named by --cst-mod-path, so generate that module
    first with gen-rust-cst. A consumer crate depending on it needs exactly two crates: `serde`
    and `fltk-serde-core`.

    Name the output `de.rs` rather than `serde.rs`: a crate-root `mod serde` makes every
    `use serde::...` in the crate ambiguous.

    Examples:
        genparser gen-rust-serde grammar.fltkg src/de.rs --ast-config grammar.fltkast
        genparser gen-rust-serde grammar.fltkg src/de.rs \\
            --ast-config grammar.fltkast \\
            --parser-mod-path super::parser --goal config \\
            --ast-mod-path super::ast
    """
    _validate_cst_mod_path(cst_mod_path)
    if parser_mod_path is not None:
        _validate_rust_mod_path(parser_mod_path, "--parser-mod-path")
    if ast_mod_path is not None:
        _validate_rust_mod_path(ast_mod_path, "--ast-mod-path")

    grammar = parse_grammar_file(grammar_file)

    try:
        # Only the Rust backend is generated here, so a `custom(...)` list may omit its Python
        # entries.  AstConfigError is a ValueError; OSError covers an unreadable path.
        resolved_config = parse_ast_config_file(ast_config, grammar, {Backend.RUST})
    except (ValueError, OSError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    # Generate before opening the file so a model, name-collision or unknown-goal error leaves no
    # artifact behind.  All of them are ValueErrors.
    try:
        src = generate_rust_serde_source(
            grammar,
            cst_mod_path,
            parser_mod_path=parser_mod_path,
            goal_rule=goal,
            ast_mod_path=ast_mod_path,
            ast_config=resolved_config,
            source_name=str(grammar_file),
        )
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    _write_output_file(output_file, src)


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
    *,
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
    plain_module: Annotated[
        list[str] | None,
        typer.Option(
            "--plain-module",
            help=(
                "Declare a module that is NOT registered as a Python submodule (repeatable). "
                "The generated 'ast' and 'de' modules are Rust-only — they hold no pyclasses "
                "and have no register_classes — so they need `pub mod <name>;` in the crate "
                "root and nothing else. Each name must be a valid Rust identifier that is not a "
                "keyword (the generated lib.rs spells it bare, never as r#name) and must not "
                "name a module the generator already declares (a registered submodule, or 'span' "
                "under --register-span-types)."
            ),
        ),
    ] = None,
    register_span_types: Annotated[
        bool,
        typer.Option(
            "--register-span-types",
            help="Emit Span/SourceText/LineColPos class registration and span module import "
            "(the consumer's `mod span;` must export LineColPos, e.g. by re-exporting from fltk-cst-core).",
        ),
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
        genparser gen-rust-lib lib.rs --module-name my_module --plain-module ast --plain-module de
        genparser gen-rust-lib src/lib.rs --module-name _native --no-cst --register-span-types --unknown-span-static
    """
    plain_modules = tuple(plain_module or ())
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
            plain_modules=plain_modules,
            register_span_types=register_span_types,
            unknown_span_static=unknown_span_static,
        )
    else:
        spec = gsm2lib_rs.LibSpec.standard(
            module_name,
            with_parser=not no_parser,
            with_unparser=unparser,
            plain_modules=plain_modules,
        )
    try:
        gen = gsm2lib_rs.RustLibGenerator(spec)
        src = gen.generate()
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from e

    _write_output_file(output_file, src)


if __name__ == "__main__":
    app()
