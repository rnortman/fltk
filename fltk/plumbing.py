"""High-level plumbing functions for FLTK grammar processing.

This module provides the essential plumbing that connects all the pieces:
grammar parsing, parser generation, parsing, unparsing, formatting, and rendering.
Think of it as the pipes that connect your grammar to formatted output.
"""

from __future__ import annotations

import ast
import importlib
import itertools
import sys
import types
from pathlib import Path
from typing import TYPE_CHECKING, Optional, cast

import fltk
from fltk.fegen import (
    ast_model,
    fltk2gsm,
    fltk_parser,
    gsm,
    gsm2ast,
    gsm2ast_rs,
    gsm2parser,
    gsm2serde_rs,
    gsm2tree,
    naming,
)
from fltk.fegen.ast_config import ALL_BACKENDS, Backend, ResolvedAstConfig, load_ast_config
from fltk.fegen.pyrt import errors, memo, terminalsrc
from fltk.iir.context import create_default_context
from fltk.iir.py import compiler
from fltk.iir.py import reg as pyreg
from fltk.lsp.lsp_config import ResolvedLspConfig, load_lsp_config
from fltk.plumbing_types import AstResult, ParseResult, ParserResult, UnparserResult
from fltk.unparse import gsm2unparser
from fltk.unparse.combinators import Doc
from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig, fmt_cst_to_config
from fltk.unparse.renderer import Renderer, RendererConfig
from fltk.unparse.resolve_specs import resolve_spacing_specs
from fltk.unparse.unparsefmt_parser import Parser as FmtParser

if TYPE_CHECKING:
    from collections.abc import Collection
    from typing import Any

    from fltk.fegen import fltk_cst_protocol as cst


_module_counter = itertools.count()
"""Names the in-memory modules ``generate_parser``, ``generate_protocol_module`` and ``generate_ast``
register in ``sys.modules``.

A process-wide counter rather than object ids: an id is only unique while its object lives, so a
recycled one could name a second module over an earlier one's ``sys.modules`` entry while that
module's classes still resolve their string annotations through it.
"""


def parse_grammar(grammar_text: str) -> gsm.Grammar:
    """Parse .fltkg text to Grammar Semantic Model.

    Args:
        grammar_text: The .fltkg grammar source text

    Inline (``!``) dispositions are expanded away here, so no consumer of the returned
    grammar ever sees an INLINE item.

    Returns:
        The parsed grammar

    Raises:
        ValueError: If grammar parsing or inline expansion fails
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
    # result.result is typed Any (ParseResult.cst: Any); cast to satisfy visit_grammar's annotation.
    return gsm.expand_inline_dispositions(cst2gsm.visit_grammar(cast("cst.Grammar", result.result)))


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


def generate_parser(
    grammar: gsm.Grammar,
    *,
    capture_trivia: bool = True,
) -> ParserResult:
    """Generate parser and CST classes from grammar.

    Args:
        grammar: The parsed grammar
        capture_trivia: If True, generates parser that captures whitespace/comments as Trivia nodes.
                       If False, generates simpler parser that skips whitespace.

    The grammar's CST protocol module is generated and registered here too: the CST module imports
    its ``NodeKind`` from it, and its name is returned on the result.

    Returns:
        ParserResult containing the generated parser class and CST module
    """
    context = create_default_context(capture_trivia=capture_trivia)

    grammar_with_trivia = gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, context))

    cstgen = gsm2tree.CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)

    module_name = f"fltk_grammar_{next(_module_counter)}"
    cst_module = types.ModuleType(module_name)

    # The CST module imports NodeKind from its protocol module, so that module has to be
    # registered before the CST source is exec'd.  A failure anywhere after that takes the entry
    # back out, for the same reason the CST module is registered only on success below.
    protocol_module_name = _register_protocol_module(grammar_with_trivia, None, cstgen)
    try:
        # Python backend: generate and exec CST dataclass module
        cst_module_ast = cstgen.gen_py_module(protocol_module_name)
        cst_globals = {}
        exec(compile(cst_module_ast, "<cst_module>", "exec"), cst_globals)  # noqa: S102
        public = {k: v for k, v in cst_globals.items() if not k.startswith("_")}

        for name, obj in public.items():
            setattr(cst_module, name, obj)

        pgen = gsm2parser.ParserGenerator(grammar=grammar_with_trivia, cstgen=cstgen, context=context)
        parser_class_ast = compiler.compile_class(pgen.parser_class, context)
        # Prepend `from __future__ import annotations` so the exec'd parser's span annotations
        # are lazy strings.  The parser annotates its terminal spans with `terminalsrc.Span`;
        # `terminalsrc` is bound in `parser_globals` below, so even eager evaluation would resolve,
        # but keeping the annotations lazy removes the dependency entirely and matches the committed
        # parsers (which also carry `from __future__ import annotations`).
        future_import = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
        parser_module = ast.fix_missing_locations(ast.Module(body=[future_import, parser_class_ast], type_ignores=[]))

        parser_globals = {
            "ApplyResult": memo.ApplyResult,
            "Span": terminalsrc.Span,
            "Optional": Optional,
            "typing": __import__("typing"),
            "terminalsrc": terminalsrc,
            "fltk": fltk,
            "errors": errors,
        }
        parser_globals.update(public)  # bind the generated Python CST node classes

        exec(compile(parser_module, "<parser>", "exec"), parser_globals)  # noqa: S102

        parser_class = None
        for name, obj in parser_globals.items():
            if isinstance(obj, type) and name.endswith("Parser"):
                parser_class = obj
                break

        if parser_class is None:
            msg = "Generated parser class not found"
            raise RuntimeError(msg)
    except Exception:
        del sys.modules[protocol_module_name]
        raise

    # Register in sys.modules only after successful parser generation, so a codegen
    # failure does not leave a stale module entry under module_name.
    sys.modules[module_name] = cst_module

    return ParserResult(
        parser_class=parser_class,
        cst_module=cst_module,
        cst_module_name=module_name,
        grammar=grammar_with_trivia,
        capture_trivia=capture_trivia,
        protocol_module_name=protocol_module_name,
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
        error_msg, error_pos = errors.failure_details(
            parser.error_tracker,
            terminals,
            lambda rule_id: parser.rule_names[rule_id],
            result.pos if result else None,
        )
        # Early success without full consumption: the start rule assembled a real CST for
        # [0, result.pos) but input remained. Keep that prefix tree; leave both fields None on
        # hard failure (result is None), where nothing was assembled.
        prefix_cst = result.result if result else None
        prefix_pos = result.pos if result else None
        return ParseResult(
            None, text, False, error_msg, error_pos=error_pos, prefix_cst=prefix_cst, prefix_pos=prefix_pos
        )

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


def parse_lsp_config(config_text: str, grammar: gsm.Grammar) -> ResolvedLspConfig:
    """Parse .fltklsp text into a resolved config against ``grammar``.

    Args:
        config_text: Editor-tooling spec text
        grammar: The target grammar the anchors resolve against

    Returns:
        The resolved LSP config (empty for empty/whitespace-only text)

    Raises:
        LspConfigError: If parsing or validation fails
    """
    return load_lsp_config(config_text, grammar)


def parse_lsp_config_file(config_path: Path, grammar: gsm.Grammar) -> ResolvedLspConfig:
    """Parse .fltklsp file into a resolved config against ``grammar``.

    Args:
        config_path: Path to the editor-tooling spec file
        grammar: The target grammar the anchors resolve against

    Returns:
        The resolved LSP config

    Raises:
        LspConfigError: If parsing or validation fails
        FileNotFoundError: If the config file doesn't exist
        OSError: If the file cannot be read (e.g. permissions)
        UnicodeDecodeError: If the file is not valid text in the default encoding
    """
    if not config_path.exists():
        msg = f"LSP config file not found: {config_path}"
        raise FileNotFoundError(msg)

    with config_path.open() as f:
        config_text = f.read()

    return parse_lsp_config(config_text, grammar)


def _assemble_unparser_module(
    grammar: gsm.Grammar,
    cst_module_name: str,
    formatter_config: FormatterConfig | None,
) -> tuple[str, gsm.Grammar, FormatterConfig]:
    """Run the unparser assembly pipeline; return (source, grammar_with_trivia, formatter_config).

    Single source of truth for the unparser assembly steps shared by generate_unparser
    (which exec's the returned source) and generate_unparser_source (which returns it).
    """
    context = create_default_context(capture_trivia=True)
    formatter_config = formatter_config or FormatterConfig()

    grammar_with_trivia = gsm.add_trivia_rule_to_grammar(grammar, context)
    grammar_with_trivia = gsm.classify_trivia_rules(grammar_with_trivia)

    unparser_class, imports = gsm2unparser.generate_unparser(
        grammar_with_trivia,
        context,
        cst_module_name,
        formatter_config=formatter_config,
    )

    unparser_ast = compiler.compile_class(unparser_class, context)
    module = ast.fix_missing_locations(ast.Module(body=[*imports, unparser_ast], type_ignores=[]))

    return ast.unparse(module), grammar_with_trivia, formatter_config


def generate_unparser_source(
    grammar: gsm.Grammar,
    cst_module_name: str,
    formatter_config: FormatterConfig | None = None,
) -> str:
    """Generate the unparser module source from grammar without executing it.

    Note: The parser must have been generated with capture_trivia=True
    for the unparser to work correctly.

    generate_unparser exec's exactly this source.

    Args:
        grammar: The grammar to generate unparser for
        cst_module_name: Name of the CST module (from ParserResult)
        formatter_config: Optional formatter configuration

    Returns:
        The generated unparser module source as a string
    """
    source, _grammar_with_trivia, _formatter_config = _assemble_unparser_module(
        grammar, cst_module_name, formatter_config
    )
    return source


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
    source, grammar_with_trivia, formatter_config = _assemble_unparser_module(
        grammar, cst_module_name, formatter_config
    )

    exec_globals = {}
    exec(source, exec_globals)  # noqa: S102

    return UnparserResult(
        unparser_class=exec_globals["Unparser"],
        grammar=grammar_with_trivia,
        formatter_config=formatter_config,
        trivia_config=formatter_config.trivia_config or TriviaConfig(),
    )


def _ast_grammar(grammar: gsm.Grammar) -> gsm.Grammar:
    """The trivia-processed grammar the AST model and the sidecar index are both built from.

    Both steps are idempotent, so a raw grammar and a ParserResult's already-processed one
    give the same result.  That is also why resolving a sidecar and then generating runs
    this twice on the same grammar: the second pass rebuilds the same result, at the cost
    of one generation-time walk, rather than making callers thread the processed grammar.
    """
    return gsm.classify_trivia_rules(gsm.add_trivia_rule_to_grammar(grammar, create_default_context()))


def parse_ast_config(
    config_text: str,
    grammar: gsm.Grammar,
    backends: Collection[Backend] = ALL_BACKENDS,
) -> ResolvedAstConfig:
    """Parse .fltkast text into a resolved config against ``grammar``.

    Args:
        config_text: AST-shaping sidecar text
        grammar: The target grammar the rule and label names resolve against
        backends: The code-generation targets whose ``custom(...)`` entries are required

    Returns:
        The resolved AST config (empty for empty/whitespace-only text)

    Raises:
        AstConfigError: If parsing or validation fails
    """
    return load_ast_config(config_text, _ast_grammar(grammar), backends)


def parse_ast_config_file(
    config_path: Path,
    grammar: gsm.Grammar,
    backends: Collection[Backend] = ALL_BACKENDS,
) -> ResolvedAstConfig:
    """Parse a .fltkast file into a resolved config against ``grammar``.

    Args:
        config_path: Path to the AST-shaping sidecar file
        grammar: The target grammar the rule and label names resolve against
        backends: The code-generation targets whose ``custom(...)`` entries are required

    Returns:
        The resolved AST config

    Raises:
        AstConfigError: If parsing or validation fails
        FileNotFoundError: If the config file doesn't exist
        OSError: If the file cannot be read (e.g. permissions)
        UnicodeDecodeError: If the file is not valid text in the default encoding
    """
    if not config_path.exists():
        msg = f"AST config file not found: {config_path}"
        raise FileNotFoundError(msg)

    with config_path.open() as f:
        config_text = f.read()

    return parse_ast_config(config_text, grammar, backends)


def generate_protocol_module(grammar: gsm.Grammar, module_name: str | None = None) -> str:
    """Generate the CST protocol module for ``grammar`` and register it; return its name.

    The generated AST module's forward direction is annotated and keyed against the grammar's
    protocol module, so a caller that generates an AST layer in memory needs that module
    importable.  The classes are built from the trivia-processed grammar, the same one the CST
    module is built from, so the two describe the same tree.

    ``module_name`` names the ``sys.modules`` entry; without one a counter-suffixed name is used,
    which is unique but exists only in this process.

    A named entry is always rendered afresh and *replaces* whatever ``sys.modules`` holds under
    that name, including an on-disk module — so naming a committed module shadows it for every
    later importer in the process, and repeat calls hand out fresh ``NodeKind``/sentinel objects
    (equal and hash-equal by canonical name, but not ``is`` the previous ones).
    """
    return _register_protocol_module(_ast_grammar(grammar), module_name)


def _register_protocol_module(
    grammar_with_trivia: gsm.Grammar, module_name: str | None, cstgen: gsm2tree.CstGenerator | None = None
) -> str:
    """Render, exec and register the protocol module of an already trivia-processed grammar.

    A caller that already holds a generator over this grammar passes it: the protocol module and
    the concrete module that shares its ``NodeKind`` are then rendered from one generator carrying
    one context, instead of two built over the same grammar.
    """
    if cstgen is None:
        context = create_default_context()
        cstgen = gsm2tree.CstGenerator(grammar=grammar_with_trivia, py_module=pyreg.Builtins, context=context)

    name = module_name if module_name is not None else f"fltk_cst_protocol_{next(_module_counter)}"
    module = types.ModuleType(name)
    module.__dict__["__name__"] = name
    exec(compile(cstgen.gen_protocol_module_text(), f"<{name}>", "exec"), module.__dict__)  # noqa: S102
    sys.modules[name] = module
    return name


def _protocol_module_for(grammar_with_trivia: gsm.Grammar, cst_module_name: str) -> str:
    """The name the AST source imports when the caller named no protocol module.

    Always the convention a regenerated pair uses, ``<cst_module>_protocol``, so source written
    to disk names a module that exists there.  An already-importable one of that name — the
    committed module beside a committed CST module, or one an earlier call registered — is used as
    it is; otherwise one is generated and registered under that name, which is what makes the
    source exec-able in this process.

    A reused module is checked against this grammar first: the AST source reads a
    ``NodeKind`` member per rule at import time, so one built from a different or older grammar
    would fail deep inside that exec with a bare ``AttributeError`` — or, if the rule names
    happen to overlap, bind the forward direction to the wrong shapes.  A module missing any of
    the grammar's kinds raises instead.

    Raises:
        ValueError: If the reused module was built from a grammar without all of this one's rules
    """
    name = naming.protocol_module_name(cst_module_name)
    try:
        module = importlib.import_module(name)
    except ModuleNotFoundError:
        return _register_protocol_module(grammar_with_trivia, name)
    _check_protocol_module_matches(module, grammar_with_trivia, name)
    return name


def _check_protocol_module_matches(module: types.ModuleType, grammar_with_trivia: gsm.Grammar, name: str) -> None:
    """Raise unless ``module`` exposes a NodeKind member for every rule of the grammar."""
    node_kind = getattr(module, "NodeKind", None)
    missing = sorted(
        member
        for member in (naming.snake_to_upper_camel(rule.name).upper() for rule in grammar_with_trivia.rules)
        if not hasattr(node_kind, member)
    )
    if missing:
        msg = (
            f"protocol module {name!r} does not match this grammar: its NodeKind is missing "
            f"{', '.join(missing)}. Regenerate it beside the CST module, or pass "
            f"protocol_module_name explicitly."
        )
        raise ValueError(msg)


def _assemble_ast_module(
    grammar: gsm.Grammar,
    cst_module_name: str,
    parser_module_name: str | None,
    unparser_module_name: str | None,
    goal_rule: str | None,
    *,
    ast_config: ResolvedAstConfig | None,
    protocol_module_name: str | None,
) -> tuple[str, ast_model.AstModel, gsm.Grammar, str]:
    """Run the AST assembly pipeline; return (source, model, grammar_with_trivia, goal_rule).

    Single source of truth for the steps shared by generate_ast (which exec's the returned
    source) and generate_ast_source (which returns it).

    An unnamed protocol module falls back to the ``<cst_module>_protocol`` convention, generated
    and registered here when nothing of that name is importable yet — so the source both entry
    points produce names a module that is importable both in this process and, after a regen,
    beside a CST module on disk.
    """
    grammar_with_trivia = _ast_grammar(grammar)
    protocol = (
        protocol_module_name
        if protocol_module_name is not None
        else _protocol_module_for(grammar_with_trivia, cst_module_name)
    )
    model = ast_model.build_ast_model(grammar_with_trivia, ast_config)
    goal = ast_model.resolve_goal_rule(model, goal_rule)
    source = gsm2ast.generate_ast_module(
        model, cst_module_name, parser_module_name, unparser_module_name, goal, protocol_module_name=protocol
    )
    return source, model, grammar_with_trivia, goal


def generate_ast_source(
    grammar: gsm.Grammar,
    cst_module_name: str,
    parser_module_name: str | None = None,
    unparser_module_name: str | None = None,
    goal_rule: str | None = None,
    *,
    ast_config: ResolvedAstConfig | None = None,
    protocol_module_name: str | None = None,
) -> str:
    """Generate the AST module source from grammar without executing it.

    generate_ast exec's exactly this source.

    Args:
        grammar: The grammar to generate the AST layer for
        cst_module_name: Importable name of the grammar's generated CST module
        parser_module_name: Importable name of a generated parser module; enables ``parse()``
        unparser_module_name: Importable name of a generated unparser module; enables ``unparse()``
        goal_rule: Rule the conveniences target; defaults to the grammar's first rule
        ast_config: Resolved .fltkast sidecar shaping the AST; None is pure Tier 0
        protocol_module_name: Importable name of the grammar's generated CST protocol module,
            which the forward converters are annotated and keyed against.  When omitted, one is
            generated and registered in ``sys.modules`` so the returned source is exec-able here.

    Returns:
        The generated AST module source as a string

    Raises:
        AstModelError: If the grammar cannot be modelled as an AST
        ValueError: If goal_rule is not a rule of the grammar
    """
    source, _model, _grammar_with_trivia, _goal = _assemble_ast_module(
        grammar,
        cst_module_name,
        parser_module_name,
        unparser_module_name,
        goal_rule,
        ast_config=ast_config,
        protocol_module_name=protocol_module_name,
    )
    return source


def generate_ast(
    grammar: gsm.Grammar,
    cst_module_name: str,
    parser_module_name: str | None = None,
    unparser_module_name: str | None = None,
    goal_rule: str | None = None,
    *,
    ast_config: ResolvedAstConfig | None = None,
    protocol_module_name: str | None = None,
) -> AstResult:
    """Generate AST node classes and CST converters from grammar.

    The CST module named by ``cst_module_name`` must be importable (in ``sys.modules``)
    when this function runs.  The grammar's CST protocol module, which the forward converters
    are annotated and keyed against, is generated and registered here unless
    ``protocol_module_name`` names an already-importable one.

    Args:
        grammar: The grammar to generate the AST layer for
        cst_module_name: Importable name of the grammar's generated CST module
        parser_module_name: Importable name of a generated parser module; enables ``parse()``
        unparser_module_name: Importable name of a generated unparser module; enables ``unparse()``
        goal_rule: Rule the conveniences target; defaults to the grammar's first rule
        ast_config: Resolved .fltkast sidecar shaping the AST; None is pure Tier 0
        protocol_module_name: Importable name of the grammar's generated CST protocol module;
            when omitted, one is generated and registered

    Returns:
        AstResult containing the executed AST module

    Raises:
        AstModelError: If the grammar cannot be modelled as an AST
        ValueError: If goal_rule is not a rule of the grammar
    """
    source, model, grammar_with_trivia, goal = _assemble_ast_module(
        grammar,
        cst_module_name,
        parser_module_name,
        unparser_module_name,
        goal_rule,
        ast_config=ast_config,
        protocol_module_name=protocol_module_name,
    )

    module_name = f"fltk_ast_{next(_module_counter)}"
    module = types.ModuleType(module_name)
    module.__dict__["__name__"] = module_name
    # Registered before exec, not after: dataclasses resolves a class's defining module out of
    # sys.modules while building its fields, so the entry has to exist by then.  A failed exec
    # takes the entry back out rather than leaving a half-built module behind.
    sys.modules[module_name] = module
    try:
        exec(compile(source, f"<{module_name}>", "exec"), module.__dict__)  # noqa: S102
    except Exception:
        del sys.modules[module_name]
        raise

    return AstResult(
        ast_module=module,
        ast_module_name=module_name,
        model=model,
        grammar=grammar_with_trivia,
        goal_rule=goal,
    )


def generate_rust_ast_source(
    grammar: gsm.Grammar,
    cst_mod_path: str = "super::cst",
    *,
    parser_mod_path: str | None = None,
    unparser_mod_path: str | None = None,
    goal_rule: str | None = None,
    ast_config: ResolvedAstConfig | None = None,
    source_name: str | None = None,
) -> str:
    """Generate the Rust AST module source (``ast.rs``) for ``grammar``.

    The Rust counterpart of ``generate_ast_source``: same model, same sidecar, a different
    emitter.  There is no ``generate_rust_ast`` beside it — Rust source is compiled by the
    consumer's build, not exec'd here.

    Args:
        grammar: The grammar to generate the AST layer for
        cst_mod_path: Rust module path of the grammar's generated CST module, imported as ``cst``
        parser_mod_path: Rust module path of a generated parser module; enables ``parse_str``
        unparser_mod_path: Rust module path of a generated unparser module; enables ``unparse_str``
        goal_rule: Rule the conveniences target; defaults to the grammar's first rule with a type
        ast_config: Resolved .fltkast sidecar shaping the AST; None is pure Tier 0
        source_name: Names the grammar in the module's header comment when it is known

    Returns:
        The generated Rust AST module source as a string

    Raises:
        AstModelError: If the grammar cannot be modelled as an AST
        ValueError: If goal_rule is not a rule of the grammar, or a rule the module must
            reference names no Rust type
    """
    model = ast_model.build_ast_model(_ast_grammar(grammar), ast_config)
    return gsm2ast_rs.generate_ast_rs(
        model,
        cst_mod_path,
        source_name,
        parser_mod_path=parser_mod_path,
        unparser_mod_path=unparser_mod_path,
        goal_rule=goal_rule,
    )


def generate_rust_serde_source(
    grammar: gsm.Grammar,
    cst_mod_path: str = "super::cst",
    *,
    parser_mod_path: str | None = None,
    goal_rule: str | None = None,
    ast_mod_path: str | None = None,
    ast_config: ResolvedAstConfig | None = None,
    source_name: str | None = None,
) -> str:
    """Generate the Rust serde description module source (``de.rs``) for ``grammar``.

    The third consumer of the same model and the same sidecar: instead of generated types it
    emits what the ``fltk-serde-core`` Deserializer needs to know about this grammar's tree, plus
    the entry points that run it.  The consumer's own ``#[derive(Deserialize)]`` targets supply
    the types.

    Args:
        grammar: The grammar to generate the serde frontend for
        cst_mod_path: Rust module path of the grammar's generated CST module, imported as ``cst``
        parser_mod_path: Rust module path of a generated parser module; enables ``from_str``
        goal_rule: Rule ``from_str`` targets; defaults to the grammar's first rule
        ast_mod_path: Rust module path of a generated AST module; enables the ``Deserialize``
            impls that let a target declare a generated AST type as a field
        ast_config: Resolved .fltkast sidecar shaping the tree; None is pure Tier 0
        source_name: Names the grammar in the module's header comment when it is known

    Returns:
        The generated Rust serde module source as a string

    Raises:
        AstModelError: If the grammar cannot be modelled, or two generated serde names collide
        ValueError: If goal_rule is not a rule of the grammar
    """
    model = ast_model.build_ast_model(_ast_grammar(grammar), ast_config)
    return gsm2serde_rs.generate_de_rs(
        model,
        cst_mod_path,
        source_name,
        parser_mod_path=parser_mod_path,
        goal_rule=goal_rule,
        ast_mod_path=ast_mod_path,
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
