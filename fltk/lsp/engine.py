"""``AnalysisEngine``: the reusable seam an LSP server wraps.

The engine owns the expensive one-time setup -- parse the grammar, load the ``.fltklsp``
config, and generate the analysis-grammar parser -- once, then turns text into semantic
tokens on every ``highlight`` call.  Stale-token serving, debouncing, and
``Diagnostic``-shaped errors are server policy layered on top; the engine stays in
codepoint offsets and returns either tokens or a formatted parse-error message.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from fltk import plumbing
from fltk.lsp import classify
from fltk.lsp.analysis import prepare_analysis_grammar
from fltk.lsp.lsp_config import ResolvedLspConfig, load_lsp_config

if TYPE_CHECKING:
    from pathlib import Path

    from fltk.fegen import gsm


@dataclasses.dataclass(frozen=True)
class HighlightResult:
    """The outcome of highlighting one document.

    ``tokens`` is the classified token stream on a successful parse and ``None`` on a parse
    failure, in which case ``error`` carries the parser's formatted error message.
    """

    tokens: list[classify.Token] | None
    error: str | None


class AnalysisEngine:
    """Holds the analysis parser and resolved config; classifies text into tokens.

    Construction generates one runtime parser from the analysis-grammar transform of
    ``grammar`` (which raises ``ValueError`` for ``!``-bearing grammars, per
    ``prepare_analysis_grammar``).  ``highlight`` parses text with that parser and paints it
    under ``resolved_config``.
    """

    def __init__(
        self,
        grammar: gsm.Grammar,
        resolved_config: ResolvedLspConfig,
        *,
        start_rule: str | None = None,
    ) -> None:
        self._parser_result = plumbing.generate_parser(prepare_analysis_grammar(grammar))
        self._tables = classify.build_grammar_tables(self._parser_result.grammar)
        self._resolved_config = resolved_config
        self._start_rule = start_rule

    @classmethod
    def from_paths(
        cls,
        grammar_path: Path,
        lsp_path: Path | None = None,
        *,
        start_rule: str | None = None,
    ) -> AnalysisEngine:
        """Build an engine from a ``.fltkg`` grammar file and an optional ``.fltklsp`` spec.

        With no ``lsp_path`` the engine runs the built-in defaults alone (an empty config).
        """
        grammar = plumbing.parse_grammar_file(grammar_path)
        resolved_config = (
            plumbing.parse_lsp_config_file(lsp_path, grammar) if lsp_path is not None else load_lsp_config("", grammar)
        )
        return cls(grammar, resolved_config, start_rule=start_rule)

    def highlight(self, text: str) -> HighlightResult:
        """Classify ``text`` into semantic tokens, or report a parse failure.

        On a successful parse returns the token stream with ``error`` ``None``; on failure
        returns ``tokens`` ``None`` and the parser's formatted error message verbatim.

        The grammar, spec, and input are all workspace-supplied and untrusted. A deeply nested
        input that exhausts the parser's recursion is caught and reported as a parse failure. A
        grammar regex that backtracks catastrophically or a non-terminating recursive parse is
        *not* bounded here -- a wall-clock/cancellation budget is the concern of the long-lived
        server layer that wraps this engine, not the one-shot classification seam.
        """
        try:
            parsed = plumbing.parse_text(self._parser_result, text, self._start_rule)
            if not parsed.success:
                return HighlightResult(tokens=None, error=parsed.error_message)
            tokens = classify.classify(
                parsed.cst, self._parser_result.grammar, self._resolved_config, text, tables=self._tables
            )
        except RecursionError:
            return HighlightResult(tokens=None, error="Input exceeds the maximum nesting depth the parser can handle")
        return HighlightResult(tokens=tokens, error=None)
