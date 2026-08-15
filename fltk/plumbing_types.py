"""Data types for the FLTK library module."""

from __future__ import annotations

import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fltk.fegen import gsm
    from fltk.fegen.ast_model import AstModel
    from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig


@dataclass
class ParserResult:
    """Result of generating a parser from a grammar."""

    parser_class: type
    cst_module: types.ModuleType
    cst_module_name: str
    grammar: gsm.Grammar
    capture_trivia: bool
    protocol_module_name: str
    """Importable name of the CST protocol module the CST module imports ``NodeKind`` from.

    Registered in ``sys.modules`` alongside the CST module; pass it wherever a generated layer
    has to name this grammar's protocol module (e.g. ``generate_ast``)."""


@dataclass
class ParseResult:
    """Result of parsing text with a generated parser."""

    cst: Any | None
    terminals: str
    success: bool
    error_message: str | None = None
    error_pos: int | None = None
    """Codepoint offset of the furthest parse failure; None when there is no source position
    (e.g. an unknown start rule)."""
    prefix_cst: Any | None = None
    """The start rule's CST for the successfully-parsed prefix ``[0, prefix_pos)`` on an
    early-success-without-full-consumption failure (the start rule matched but did not consume the
    whole input). ``None`` on success (``cst`` already holds the whole parse), on hard failure (the
    start rule returned no result), and on an unknown start rule. ``prefix_cst is not None`` iff
    ``prefix_pos is not None``; a prefix is exposed whenever the start rule returned a result, even a
    zero-length one."""
    prefix_pos: int | None = None
    """Codepoint length consumed by ``prefix_cst`` (may be ``0``); ``None`` whenever ``prefix_cst``
    is ``None``."""


@dataclass
class AstResult:
    """Result of generating an AST module from a grammar."""

    ast_module: types.ModuleType
    ast_module_name: str
    model: AstModel
    grammar: gsm.Grammar
    """The trivia-classified grammar the model was built from."""
    goal_rule: str
    """The rule the module's ``parse``/``unparse`` conveniences target."""


@dataclass
class UnparserResult:
    """Result of generating an unparser from a grammar."""

    unparser_class: type
    grammar: gsm.Grammar
    formatter_config: FormatterConfig
    trivia_config: TriviaConfig
