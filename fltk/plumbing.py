"""High-level plumbing functions for FLTK grammar processing.

This module provides the essential plumbing that connects all the pieces:
grammar parsing, parser generation, parsing, unparsing, formatting, and rendering.
Think of it as the pipes that connect your grammar to formatted output.
"""

from __future__ import annotations

import ast
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import fltk
from fltk.fegen import fltk2gsm, fltk_parser, gsm, gsm2parser, gsm2tree
from fltk.fegen.pyrt import errors, memo, terminalsrc
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg
from fltk.plumbing_types import ParseResult, ParserResult, UnparserResult
from fltk.unparse import gsm2unparser
from fltk.unparse.combinators import Doc
from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig, fmt_cst_to_config
from fltk.unparse.renderer import Renderer, RendererConfig
from fltk.unparse.resolve_specs import resolve_spacing_specs
from fltk.unparse.unparsefmt_parser import Parser as FmtParser

if TYPE_CHECKING:
    from typing import Any


def parse_grammar(grammar_text: str) -> gsm.Grammar:
    """Parse .fltkg text to Grammar Semantic Model.

    Args:
        grammar_text: The .fltkg grammar source text

    Returns:
        The parsed grammar

    Raises:
        ValueError: If grammar parsing fails
    """
    terminals = terminalsrc.TerminalSource(grammar_text)
    parser = fltk_parser.Parser(terminalsrc=terminals)
    result = parser.apply__parse_grammar(0)

    if not result or result.pos != len(terminals.terminals):
        error_msg = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f"Grammar parse failed:\n{error_msg}"
        raise ValueError(msg)

    cst2gsm = fltk2gsm.Cst2Gsm(terminals.terminals)
    return cst2gsm.visit_grammar(result.result)


def parse_grammar_file(grammar_path: Path) -> gsm.Grammar:
    """Parse .fltkg file to Grammar Semantic Model.

    Args:
        grammar_path: Path to .fltkg grammar file

    Returns:
        The parsed grammar

    Raises:
        ValueError: If grammar parsing fails
        FileNotFoundError: If grammar file doesn't exist
    """
    if not grammar_path.exists():
        msg = f"Grammar file not found: {grammar_path}"
        raise FileNotFoundError(msg)

    with grammar_path.open() as f:
        grammar_text = f.read()

    return parse_grammar(grammar_text)


def generate_parser(grammar: gsm.Grammar, *, capture_trivia: bool = True) -> ParserResult:
    """Generate parser and CST classes from grammar.

    Args:
        grammar: The parsed grammar
        capture_trivia: If True, generates parser that captures whitespace/comments as Trivia nodes.
                       If False, generates simpler parser that skips whitespace.

    Returns:
        ParserResult containing the generated parser class and CST module
    """
    context = create_default_context(capture_trivia=capture_trivia)

    grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))

    cstgen = gsm2tree.CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)
    cst_module_ast = cstgen.gen_py_module()

    cst_globals = {}
    exec(compile(cst_module_ast, "<cst_module>", "exec"), cst_globals)  # noqa: S102

    module_name = f"fltk_grammar_{id(grammar)}"
    cst_module = types.ModuleType(module_name)
    for name, obj in cst_globals.items():
        if not name.startswith("_"):
            setattr(cst_module, name, obj)
    sys.modules[module_name] = cst_module

    pgen = gsm2parser.ParserGenerator(grammar=grammar_with_trivia, cstgen=cstgen, context=context)
    parser_class_ast = compiler.compile_class(pgen.parser_class, context)
    parser_module = ast.fix_missing_locations(ast.Module(body=[parser_class_ast], type_ignores=[]))

    parser_globals = {
        "ApplyResult": memo.ApplyResult,
        "Span": terminalsrc.Span,
        "Optional": Optional,
        "typing": __import__("typing"),
        "terminalsrc": terminalsrc,
        "fltk": fltk,
        "errors": errors,
    }
    parser_globals.update(cst_globals)

    exec(compile(parser_module, "<parser>", "exec"), parser_globals)  # noqa: S102

    parser_class = None
    for name, obj in parser_globals.items():
        if isinstance(obj, type) and name.endswith("Parser"):
            parser_class = obj
            break

    if parser_class is None:
        msg = "Generated parser class not found"
        raise RuntimeError(msg)

    return ParserResult(
        parser_class=parser_class,
        cst_module=cst_module,
        cst_module_name=module_name,
        grammar=grammar_with_trivia,
        capture_trivia=capture_trivia,
    )


def parse_text(parser_result: ParserResult, text: str, rule_name: str | None = None) -> ParseResult:
    """Parse text using generated parser.

    Args:
        parser_result: Result from generate_parser()
        text: Text to parse
        rule_name: Grammar rule to use as start rule. If None, uses first rule in grammar.

    Returns:
        ParseResult with the CST and success status
    """
    terminals = terminalsrc.TerminalSource(text)
    parser = parser_result.parser_class(terminals)

    if rule_name is None:
        rule_name = parser_result.grammar.rules[0].name

    method_name = f"apply__parse_{rule_name}"
    if not hasattr(parser, method_name):
        return ParseResult(None, text, False, f"No parse method for rule '{rule_name}'")

    result = getattr(parser, method_name)(0)

    if not result or result.pos != len(terminals.terminals):
        error_msg = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        return ParseResult(None, text, False, error_msg)

    return ParseResult(result.result, text, True)


def parse_format_config(config_text: str) -> FormatterConfig:
    """Parse .fltkfmt text into FormatterConfig.

    Args:
        config_text: Format configuration text

    Returns:
        Parsed FormatterConfig

    Raises:
        ValueError: If format parsing fails
    """
    if not config_text.strip():
        return FormatterConfig()

    terminals = terminalsrc.TerminalSource(config_text)
    parser = FmtParser(terminals)
    result = parser.apply__parse_formatter(0)

    if not result or result.pos != len(terminals.terminals):
        error_msg = errors.format_error_message(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
        )
        msg = f"Format config parse failed:\n{error_msg}"
        raise ValueError(msg)

    return fmt_cst_to_config(result.result, terminals)


def parse_format_config_file(config_path: Path) -> FormatterConfig:
    """Parse .fltkfmt file into FormatterConfig.

    Args:
        config_path: Path to format configuration file

    Returns:
        Parsed FormatterConfig

    Raises:
        ValueError: If format parsing fails
        FileNotFoundError: If config file doesn't exist
    """
    if not config_path.exists():
        msg = f"Format config file not found: {config_path}"
        raise FileNotFoundError(msg)

    with config_path.open() as f:
        config_text = f.read()

    return parse_format_config(config_text)


def generate_unparser(
    grammar: gsm.Grammar,
    cst_module_name: str,
    formatter_config: FormatterConfig | None = None,
) -> UnparserResult:
    """Generate unparser from grammar.

    Note: The parser must have been generated with capture_trivia=True
    for the unparser to work correctly.

    Args:
        grammar: The grammar to generate unparser for
        cst_module_name: Name of the CST module (from ParserResult)
        formatter_config: Optional formatter configuration

    Returns:
        UnparserResult containing the generated unparser class
    """
    context = create_default_context(capture_trivia=True)
    formatter_config = formatter_config or FormatterConfig()

    grammar_with_trivia = gsm.add_trivia_rule_to_grammar(grammar, context)

    unparser_class, imports = gsm2unparser.generate_unparser(
        grammar_with_trivia,
        context,
        cst_module_name,
        formatter_config=formatter_config,
    )

    unparser_ast = compiler.compile_class(unparser_class, context)
    module = ast.fix_missing_locations(ast.Module(body=[*imports, unparser_ast], type_ignores=[]))

    exec_globals = {}
    exec(ast.unparse(module), exec_globals)  # noqa: S102

    return UnparserResult(
        unparser_class=exec_globals["Unparser"],
        grammar=grammar_with_trivia,
        formatter_config=formatter_config,
        trivia_config=formatter_config.trivia_config or TriviaConfig(),
    )


def unparse_cst(unparser_result: UnparserResult, cst: Any, terminals: str, rule_name: str | None = None) -> Doc:
    """Unparse CST to Doc combinators.

    Args:
        unparser_result: Result from generate_unparser()
        cst: The CST to unparse
        terminals: The original terminal string
        rule_name: Rule to use for unparsing. If None, uses first rule in grammar.

    Returns:
        Doc combinator tree

    Raises:
        ValueError: If unparsing fails
    """
    unparser = unparser_result.unparser_class(terminals)

    if rule_name is None:
        rule_name = unparser_result.grammar.rules[0].name

    method_name = f"unparse_{rule_name}"
    if not hasattr(unparser, method_name):
        msg = f"No unparse method for rule '{rule_name}'"
        raise ValueError(msg)

    result = getattr(unparser, method_name)(cst)

    if result is None:
        msg = "Unparsing failed"
        raise ValueError(msg)

    return resolve_spacing_specs(result.accumulator.doc)


def render_doc(doc: Doc, config: RendererConfig | None = None) -> str:
    """Render Doc combinators to formatted text.

    Args:
        doc: Doc combinator tree
        config: Optional renderer configuration

    Returns:
        Formatted text
    """
    renderer = Renderer(config or RendererConfig())
    return renderer.render(doc)
