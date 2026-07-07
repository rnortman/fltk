"""``AnalysisEngine``: the reusable seam an LSP server wraps.

The engine owns the expensive one-time setup -- parse the grammar, load the ``.fltklsp``
config, and generate the analysis-grammar parser -- once, then turns text into semantic
tokens on every ``highlight``/``analyze`` call.  Stale-token serving, debouncing, and
``Diagnostic``-shaped errors are server policy layered on top; the engine stays in
codepoint offsets and returns either tokens or a formatted parse-error message.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any

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


@dataclasses.dataclass(frozen=True)
class ParseErrorInfo:
    """A structured parse failure: the formatted message plus its source position.

    ``message`` is the ``ErrorTracker``-formatted message verbatim. ``offset`` is the
    codepoint offset of the furthest failure, or ``None`` when no source position is
    available (e.g. a recursion-limit failure, which has no tracked offset).
    """

    message: str
    offset: int | None


@dataclasses.dataclass(frozen=True)
class DocumentAnalysis:
    """The full outcome of analyzing one document.

    On success ``tree`` and ``tokens`` are populated and ``error`` is ``None``; on failure
    ``tree`` and ``tokens`` are ``None`` and ``error`` carries the structured failure. The
    ``tree`` is the analysis-grammar CST root, typed ``Any`` because analysis CSTs are
    per-grammar exec'd classes with no shared base -- consumers walk them structurally via
    ``kind``/``span``/``children``.
    """

    tree: Any | None
    tokens: list[classify.Token] | None
    error: ParseErrorInfo | None


class AnalysisEngine:
    """Holds the analysis parser and resolved config; classifies text into tokens.

    Construction generates one runtime parser from the analysis-grammar transform of
    ``grammar`` (which raises ``ValueError`` for ``!``-bearing grammars, per
    ``prepare_analysis_grammar``).  ``analyze`` parses text with that parser and paints it
    under ``resolved_config``; ``highlight`` is a thin wrapper over ``analyze`` preserving its
    original result type and behavior.
    """

    def __init__(
        self,
        grammar: gsm.Grammar,
        resolved_config: ResolvedLspConfig,
        *,
        start_rule: str | None = None,
    ) -> None:
        self._source_grammar = grammar
        self._parser_result = plumbing.generate_parser(prepare_analysis_grammar(grammar))
        self._tables = classify.build_grammar_tables(self._parser_result.grammar)
        self._trivia_kind_names = frozenset(
            kind for kind, rule in self._tables.kind_to_rule.items() if rule.is_trivia_rule
        )
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

    @property
    def source_grammar(self) -> gsm.Grammar:
        """The original grammar passed to ``__init__``, before the analysis transform.

        The formatting pipeline must be built from this, never from the analysis variant:
        analysis CSTs contain suppressed terminals the generated unparser does not expect.
        """
        return self._source_grammar

    @property
    def trivia_kind_names(self) -> frozenset[str]:
        """The analysis-tree ``kind`` names whose grammar rules are trivia rules.

        Folding marks these nodes as comment folds. Keys match a CST node's ``kind.name``.
        """
        return self._trivia_kind_names

    def analyze(self, text: str) -> DocumentAnalysis:
        """Analyze ``text`` into a CST, semantic tokens, and any structured parse error.

        On a successful parse returns ``tree`` and ``tokens`` with ``error`` ``None``; on
        failure returns both ``None`` and a ``ParseErrorInfo`` carrying the formatted message
        and the failure offset. A recursion-limit failure is caught and reported with
        ``offset`` ``None``.

        The grammar, spec, and input are all workspace-supplied and untrusted. A deeply nested
        input that exhausts the parser's recursion is caught and reported as a parse failure. A
        grammar regex that backtracks catastrophically or a non-terminating recursive parse is
        *not* bounded here -- a wall-clock/cancellation budget is the concern of the long-lived
        server layer that wraps this engine, not the one-shot classification seam.
        """
        try:
            parsed = plumbing.parse_text(self._parser_result, text, self._start_rule)
            if not parsed.success:
                return DocumentAnalysis(
                    tree=None,
                    tokens=None,
                    error=ParseErrorInfo(message=parsed.error_message or "", offset=parsed.error_pos),
                )
            tokens = classify.classify(
                parsed.cst, self._parser_result.grammar, self._resolved_config, text, tables=self._tables
            )
        except RecursionError:
            return DocumentAnalysis(
                tree=None,
                tokens=None,
                error=ParseErrorInfo(
                    message="Input exceeds the maximum nesting depth the parser can handle",
                    offset=None,
                ),
            )
        return DocumentAnalysis(tree=parsed.cst, tokens=tokens, error=None)

    def highlight(self, text: str) -> HighlightResult:
        """Classify ``text`` into semantic tokens, or report a parse failure.

        On a successful parse returns the token stream with ``error`` ``None``; on failure
        returns ``tokens`` ``None`` and the parser's formatted error message verbatim. This is
        a thin wrapper over ``analyze`` preserving its original result type and behavior exactly.
        """
        analysis = self.analyze(text)
        return HighlightResult(
            tokens=analysis.tokens,
            error=analysis.error.message if analysis.error is not None else None,
        )
