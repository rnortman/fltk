"""Data types for the FLTK library module."""

from __future__ import annotations

import types
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fltk.fegen import gsm
    from fltk.unparse.fmt_config import FormatterConfig, TriviaConfig


@dataclass
class ParserResult:
    """Result of generating a parser from a grammar."""

    parser_class: type
    cst_module: types.ModuleType
    cst_module_name: str
    grammar: gsm.Grammar
    capture_trivia: bool


@dataclass
class ParseResult:
    """Result of parsing text with a generated parser."""

    cst: Any | None
    terminals: str
    success: bool
    error_message: str | None = None


@dataclass
class UnparserResult:
    """Result of generating an unparser from a grammar."""

    unparser_class: type
    grammar: gsm.Grammar
    formatter_config: FormatterConfig
    trivia_config: TriviaConfig
