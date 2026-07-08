"""The ``fltk-lsp`` pygls server: protocol wiring over the pure engine and feature logic.

This module owns everything that is *policy* rather than translation: capability advertisement
and position-encoding negotiation, per-document lifecycle and state, debounced/awaited analysis
scheduling on a single worker thread, diagnostics publication, the stale-token serving policy,
and the lazy formatting pipeline. All coordinate math lives in :mod:`fltk.lsp.positions` and all
analysis-to-LSP translation in :mod:`fltk.lsp.features`; this layer never re-derives positions.

Importing this module requires the ``lsp`` extra (``pip install 'fltk[lsp]'``): it imports pygls
at load time. ``server_cli`` imports it lazily and turns a missing-pygls ``ImportError`` into an
actionable message.
"""

from __future__ import annotations

import asyncio
import bisect
import dataclasses
import importlib.metadata
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

import pygls.capabilities as _pygls_capabilities
from lsprotocol import types as lsp
from pygls.capabilities import get_capability
from pygls.exceptions import JsonRpcException
from pygls.lsp.server import LanguageServer

from fltk import plumbing
from fltk.lsp import features
from fltk.lsp.positions import LineIndex, PositionEncoding

if TYPE_CHECKING:
    from fltk.lsp import symbols
    from fltk.lsp.engine import AnalysisEngine, DocumentAnalysis
    from fltk.plumbing_types import ParserResult, UnparserResult
    from fltk.unparse.fmt_config import FormatterConfig
    from fltk.unparse.renderer import RendererConfig

    # Worker output: the analysis, its line index, and the served tokens (absolute segments plus
    # their delta encoding), or ``None`` when the analysis produced no tokens.
    _AnalysisResult = tuple[DocumentAnalysis, LineIndex, "_ServedTokens | None"]


_LOGGER = logging.getLogger(__name__)

_SERVER_NAME = "fltk-lsp"


def _server_version() -> str:
    """The installed ``fltk`` package version, or ``"unknown"`` outside an installed environment."""
    try:
        return importlib.metadata.version("fltk")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


# Debounce window between a `didChange` and the analysis it triggers, coalescing an edit burst
# into one parse. Module constant, not configurable.
_DEBOUNCE_SECONDS = 0.2


def _constrain_pygls_encodings() -> None:
    """Restrict pygls's negotiated position encodings to the two ``LineIndex`` implements.

    pygls otherwise advertises ``utf-8`` as well, which ``LineIndex`` does not support; leaving
    that in place would let the encoding pygls advertises diverge from the one this server can
    compute in. Narrowing the set to ``{utf-16, utf-32}`` makes pygls's own negotiation the single
    encoding owner: whatever it advertises, this server can honor, and ``_encoding`` reads that one
    advertised value back.

    This rides on a pygls private module global. Verify it still exists so a pygls upgrade that
    renames or removes it fails loudly here at import, rather than silently letting pygls resume
    advertising ``utf-8`` (which ``LineIndex`` does not implement) to any client that prefers it.
    Re-check this attribute name on each pygls bump.
    """
    if not hasattr(_pygls_capabilities, "_SUPPORTED_ENCODINGS"):
        msg = (
            "pygls.capabilities._SUPPORTED_ENCODINGS is missing; this pygls release is incompatible "
            "with fltk-lsp's position-encoding constraint"
        )
        raise RuntimeError(msg)
    _pygls_capabilities._SUPPORTED_ENCODINGS = frozenset(
        {lsp.PositionEncodingKind.Utf16, lsp.PositionEncodingKind.Utf32}
    )


_constrain_pygls_encodings()


@dataclasses.dataclass(frozen=True)
class _GoodAnalysis:
    """A snapshot of the last complete analysis, self-consistent across one document version.

    The line index, tree, segments, and symbols are all computed against the *same* document text,
    so serving any of them for a stale version can never mix coordinates from two versions. Its
    ``segments`` are the fresh absolute segments of that complete analysis -- the stale input a later
    partial analysis merges its fresh prefix with.
    """

    version: int | None
    line_index: LineIndex
    tree: Any
    segments: list[features.TokenSegment]
    symbols: symbols.SymbolTable


@dataclasses.dataclass(frozen=True)
class _ServedTokens:
    """What the semantic-token handlers serve: absolute segments plus their wire encoding.

    Either a complete analysis's fresh segments, or a partial analysis's fresh-prefix segments
    merged with the clipped stale tail of the previous complete analysis. Both the segments and
    their delta encoding are computed on the worker thread; the handlers only read them. Staleness
    ordering is enforced by ``_store``'s ``analyzed_version`` guard before this record is written,
    so it carries no version of its own.
    """

    segments: list[features.TokenSegment]
    encoded: list[int]


@dataclasses.dataclass
class _DocState:
    """Per-URI analysis state: the latest analysis, the served tokens, and the last complete one."""

    analyzed_version: int | None = None
    analysis: DocumentAnalysis | None = None
    line_index: LineIndex | None = None
    last_good: _GoodAnalysis | None = None
    served_tokens: _ServedTokens | None = None


class FltkLanguageServer(LanguageServer):
    """A pygls server that classifies, diagnoses, folds, selects, and formats one FLTK language.

    Construction is cheap; the engine (which paid for analysis-parser generation) is passed in,
    and the formatting pipeline is built lazily on first request. All parsing/classification runs
    on a single worker thread so the protocol loop is never blocked.
    """

    def __init__(
        self,
        engine: AnalysisEngine,
        formatter_config: FormatterConfig | None,
        renderer_config: RendererConfig,
    ) -> None:
        super().__init__(
            name=_SERVER_NAME,
            version=_server_version(),
            text_document_sync_kind=lsp.TextDocumentSyncKind.Full,
        )
        self._engine = engine
        self._formatter_config = formatter_config
        self._renderer_config = renderer_config
        # The engine owns the start rule; reading it here keeps the formatting parses and the
        # analysis parses from ever disagreeing on which rule the document starts with.
        self._start_rule = engine.start_rule
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fltk-lsp-analysis")
        self._docs: dict[str, _DocState] = {}
        self._debounce: dict[str, asyncio.Task[None]] = {}
        self._inflight: dict[str, tuple[int | None, asyncio.Future[_AnalysisResult]]] = {}
        # Per-URI epoch, bumped on drop: an analysis captures it at submit and its result is
        # discarded if a close advanced the epoch meanwhile, so closed-document state is never
        # resurrected by a late-completing analysis.
        self._epochs: dict[str, int] = {}
        # Formatting pipeline, built once on first request; a build failure is memoized so a
        # per-keystroke format request never retries multi-second codegen that cannot succeed
        # (its inputs -- grammar and .fltkfmt -- are fixed at startup).
        self._fmt_pipeline: tuple[ParserResult, UnparserResult] | None = None
        self._fmt_failed = False

    # -- encoding ---------------------------------------------------------------------------

    def _encoding(self) -> PositionEncoding:
        """The negotiated position encoding, read back from the advertised workspace value."""
        advertised = self.workspace.position_encoding
        if advertised == lsp.PositionEncodingKind.Utf32:
            return PositionEncoding.UTF32
        if advertised != lsp.PositionEncodingKind.Utf16:
            # pygls is constrained to advertise only utf-16/utf-32, so this is unreachable unless
            # that constraint has drifted; surface it rather than silently computing utf-16 math
            # against a client counting in some other unit.
            _LOGGER.warning(
                "fltk-lsp: advertised position encoding %r is not one LineIndex implements; using utf-16",
                advertised,
            )
        return PositionEncoding.UTF16

    # -- analysis scheduling ----------------------------------------------------------------

    def _analyze_blocking(self, text: str, stale: _GoodAnalysis | None) -> _AnalysisResult:
        """Run the engine, build the line index, and compute served tokens; on the worker thread.

        The whole semantic-token pipeline -- absolute segments, the stale-tail merge for a partial
        analysis, and delta encoding -- runs here, not on the loop thread, so its O(tokens) cost
        never blocks the protocol loop even for clients that never request tokens. A complete
        analysis serves its own fresh segments; a partial one serves its fresh prefix merged with
        ``stale``'s segments clipped at the prefix boundary; a failed one serves nothing.

        A single non-terminating parse (catastrophic regex backtracking, unbounded recursion the
        engine does not catch) starves every later analysis: Python worker threads cannot be
        preempted. The protocol loop stays responsive, but that document stops updating.
        TODO(lsp-analysis-watchdog): bound analysis wall-clock via process isolation or a
        parser-level budget so one runaway document cannot wedge the worker.
        """
        analysis = self._engine.analyze(text)
        line_index = LineIndex(text)
        served: _ServedTokens | None = None
        if analysis.tokens is not None:
            enc = self._encoding()
            fresh = features.absolute_segments(analysis.tokens, line_index, enc)
            if analysis.error is None:
                segments = fresh
            else:
                # A partial outcome guarantees prefix_end is set (DocumentAnalysis invariant); trust
                # it rather than defaulting, so a contract break crashes here instead of silently
                # computing a zero boundary that keeps the whole stale stream.
                assert analysis.prefix_end is not None
                boundary = line_index.offset_to_position(analysis.prefix_end, enc)
                stale_segments = stale.segments if stale is not None else []
                segments = features.merge_stale_segments(fresh, stale_segments, boundary)
            served = _ServedTokens(segments=segments, encoded=features.delta_encode_segments(segments))
        return analysis, line_index, served

    def _store(
        self,
        uri: str,
        version: int | None,
        analysis: DocumentAnalysis,
        line_index: LineIndex,
        served: _ServedTokens | None,
        epoch: int,
    ) -> _DocState:
        """Record an analysis result, advancing state only for the current-or-newer version.

        A result whose ``epoch`` no longer matches the URI's (a close happened after the analysis
        was submitted) is discarded, so a late-completing analysis never resurrects state for a
        document that is no longer open. When ``served`` is ``None`` (a failed analysis) the
        previously served token stream is left in place, mirroring the keep-serving-stale policy.
        """
        if self._epochs.get(uri, 0) != epoch:
            return _DocState()
        state = self._docs.setdefault(uri, _DocState())
        if state.analyzed_version is not None and version is not None and version < state.analyzed_version:
            return state
        state.analyzed_version = version
        state.analysis = analysis
        state.line_index = line_index
        if served is not None:
            state.served_tokens = served
            if analysis.error is None and analysis.tree is not None and analysis.symbols is not None:
                # Complete analysis: its served segments are the fresh segment list, the stale input
                # a later partial analysis merges against. A partial analysis (error set) never
                # promotes to last_good, so navigation/folding keep serving the last complete tree.
                state.last_good = _GoodAnalysis(
                    version=version,
                    line_index=line_index,
                    tree=analysis.tree,
                    segments=served.segments,
                    symbols=analysis.symbols,
                )
        return state

    async def _analysis_for(self, uri: str, version: int | None, text: str) -> _DocState:
        """Analyze ``text`` on the worker thread, reusing an in-flight run for the same version.

        Single-flight per URI: a request and the debounce timer racing on the same version share
        one worker submission rather than doing the parse twice.
        """
        epoch = self._epochs.get(uri, 0)
        inflight = self._inflight.get(uri)
        if inflight is not None and inflight[0] == version:
            analysis, line_index, served = await inflight[1]
        else:
            loop = asyncio.get_running_loop()
            # Snapshot last_good on the loop thread at submit time; only _store (also on the loop
            # thread) ever writes it, so the worker reads a race-free stale-tail source.
            existing = self._docs.get(uri)
            stale = existing.last_good if existing is not None else None
            future = loop.run_in_executor(self._executor, self._analyze_blocking, text, stale)
            self._inflight[uri] = (version, future)
            try:
                analysis, line_index, served = await future
            finally:
                if self._inflight.get(uri) is not None and self._inflight[uri][1] is future:
                    del self._inflight[uri]
        return self._store(uri, version, analysis, line_index, served, epoch)

    async def _ensure_analyzed(self, uri: str, version: int | None, text: str) -> _DocState:
        """Return state whose analysis matches ``version``, analyzing if necessary."""
        state = self._docs.get(uri)
        if state is not None and state.analyzed_version == version and state.analysis is not None:
            return state
        return await self._analysis_for(uri, version, text)

    # -- diagnostics ------------------------------------------------------------------------

    def _publish(self, uri: str, version: int | None, state: _DocState) -> None:
        """Publish the diagnostics implied by ``state``'s current analysis."""
        analysis = state.analysis
        line_index = state.line_index
        diagnostics: list[lsp.Diagnostic] = []
        if analysis is not None and analysis.error is not None and line_index is not None:
            enc = self._encoding()
            offset = analysis.error.offset
            if offset is None:
                zero = lsp.Position(line=0, character=0)
                rng = lsp.Range(start=zero, end=zero)
            else:
                start_line, start_char = line_index.offset_to_position(offset, enc)
                end_line, end_char = line_index.offset_to_position(offset + 1, enc)
                rng = lsp.Range(
                    start=lsp.Position(line=start_line, character=start_char),
                    end=lsp.Position(line=end_line, character=end_char),
                )
            diagnostics.append(
                lsp.Diagnostic(
                    range=rng,
                    message=analysis.error.message,
                    severity=lsp.DiagnosticSeverity.Error,
                    source=_SERVER_NAME,
                )
            )
        self.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics, version=version)
        )

    async def analyze_and_publish(self, uri: str, version: int | None, text: str) -> None:
        """Analyze the current document and publish diagnostics if it is still current.

        Routes through ``_ensure_analyzed`` so a version a pull handler already analyzed during the
        debounce window is not re-parsed when the debounce timer fires.
        """
        state = await self._ensure_analyzed(uri, version, text)
        document = self.workspace.get_text_document(uri)
        if document.version == version:
            self._publish(uri, version, state)

    async def _debounced_analyze(self, uri: str) -> None:
        """Wait out the debounce window, then analyze-and-publish the latest document text."""
        try:
            await asyncio.sleep(_DEBOUNCE_SECONDS)
        except asyncio.CancelledError:
            return
        finally:
            # Only evict our own slot: a reschedule during the sleep installs a replacement task,
            # and popping unconditionally here would orphan it (breaking later cancellation).
            if self._debounce.get(uri) is asyncio.current_task():
                self._debounce.pop(uri, None)
        document = self.workspace.get_text_document(uri)
        try:
            await self.analyze_and_publish(uri, document.version, document.source)
        except Exception:
            # This task is not awaited by anyone, so an unreported exception would surface only as
            # asyncio GC noise on stderr -- invisible in the client's server log. Log it there with
            # a full traceback: parse, extraction, and classification failures all land here, and the
            # stack is the only way to tell which stage broke from the client's server log alone.
            self.window_log_message(
                lsp.LogMessageParams(
                    type=lsp.MessageType.Error,
                    message=f"fltk-lsp: analysis failed for {uri}:\n{traceback.format_exc()}",
                )
            )

    def schedule_debounced(self, uri: str) -> None:
        """(Re)schedule a debounced analysis for ``uri``, cancelling any pending one."""
        existing = self._debounce.pop(uri, None)
        if existing is not None:
            existing.cancel()
        self._debounce[uri] = asyncio.ensure_future(self._debounced_analyze(uri))

    def drop(self, uri: str) -> None:
        """Forget all per-URI state and clear its diagnostics."""
        # Advance the epoch so any analysis already in flight for this URI is discarded on
        # completion rather than resurrecting state for the now-closed document.
        self._epochs[uri] = self._epochs.get(uri, 0) + 1
        existing = self._debounce.pop(uri, None)
        if existing is not None:
            existing.cancel()
        self._docs.pop(uri, None)
        self._inflight.pop(uri, None)
        self.text_document_publish_diagnostics(lsp.PublishDiagnosticsParams(uri=uri, diagnostics=[], version=None))

    # -- stale-serving accessors ------------------------------------------------------------

    def _serveable(self, state: _DocState) -> _GoodAnalysis | None:
        """The analysis to serve pull features from: current version's, else last-good, else none."""
        return state.last_good

    async def _serveable_for(self, uri: str) -> tuple[_GoodAnalysis, PositionEncoding] | None:
        """Fetch, ensure-analyzed, and return the serveable analysis plus encoding, or ``None``.

        The shared preamble of the read-only pull handlers: document fetch, current-version
        analysis, last-good fallback, and encoding lookup, in one place so the serving policy has a
        single owner.
        """
        document = self.workspace.get_text_document(uri)
        state = await self._ensure_analyzed(uri, document.version, document.source)
        good = self._serveable(state)
        if good is None:
            return None
        return good, self._encoding()

    # -- client-capability accessors --------------------------------------------------------

    def _hierarchical_symbols(self) -> bool:
        """Whether the client advertised hierarchical ``documentSymbol`` support.

        Read back from the capabilities captured at ``initialize``; these do not change within a
        session, so reading them per request is equivalent to caching them.
        """
        return get_capability(
            self.client_capabilities,
            "text_document.document_symbol.hierarchical_document_symbol_support",
            False,
        )

    def _document_changes(self) -> bool:
        """Whether the client advertised ``workspace.workspaceEdit.documentChanges`` support."""
        return get_capability(self.client_capabilities, "workspace.workspace_edit.document_changes", False)

    # -- rename -----------------------------------------------------------------------------

    async def rename_document(self, uri: str, position: lsp.Position, new_name: str) -> lsp.WorkspaceEdit | None:
        """Rename the symbol under ``position`` to ``new_name``, or ``None`` when nothing resolves.

        Unlike the read-only features, rename edits the document and so refuses to run against a
        stale tree: it requires a successful analysis of the *current* version, then verifies the
        renamed text reparses before returning any edits. A ``JsonRpcException`` is raised (surfaced
        to the user as an error) when the document has parse errors or the new name would break it.
        """
        document = self.workspace.get_text_document(uri)
        version = document.version
        # Snapshot the text once, up front: `document` is pygls's live buffer, so re-reading
        # `.source` after an await could splice this version's offsets into newer text.
        text = document.source
        if version is None:
            # A URI the client never opened is disk-backed: it has no version to guard a concurrent
            # on-disk rewrite, and every `.source` read re-reads the file. Rename must only touch a
            # document the client has opened and is syncing.
            msg = "cannot rename a document that is not open in the editor"
            raise JsonRpcException(msg, code=lsp.LSPErrorCodes.RequestFailed)
        state = await self._ensure_analyzed(uri, version, text)
        if self.workspace.get_text_document(uri).version != version:
            # A didChange landed on the loop during the analysis await; this version's offsets no
            # longer describe the live text, so applying them would corrupt it.
            msg = "document changed during rename; retry"
            raise JsonRpcException(msg, code=lsp.LSPErrorCodes.RequestFailed)
        analysis = state.analysis
        if analysis is None or state.line_index is None:
            msg = "cannot rename: no analysis is available for the current document"
            raise JsonRpcException(msg, code=lsp.LSPErrorCodes.RequestFailed)
        if analysis.error is not None:
            msg = "cannot rename while the document has parse errors"
            raise JsonRpcException(msg, code=lsp.LSPErrorCodes.RequestFailed)
        if analysis.symbols is None:
            msg = "cannot rename: internal error, the analysis produced no symbol table"
            raise JsonRpcException(msg, code=lsp.LSPErrorCodes.RequestFailed)
        enc = self._encoding()
        offset = state.line_index.position_to_offset(position.line, position.character, enc)
        found = features.rename_occurrences(analysis.symbols, offset)
        if found is None:
            return None
        symbol, occurrences = found
        document_changes = self._document_changes()
        if new_name == symbol.name:
            return features.rename_edits(
                uri, version, [], new_name, state.line_index, enc, document_changes=document_changes
            )
        renamed = _apply_edits(text, occurrences, new_name)
        loop = asyncio.get_running_loop()
        verify = await loop.run_in_executor(self._executor, self._engine.analyze, renamed)
        if verify.error is not None:
            msg = "cannot rename: the new name would leave the document unparseable"
            raise JsonRpcException(msg, code=lsp.LSPErrorCodes.RequestFailed)
        if self.workspace.get_text_document(uri).version != version:
            msg = "document changed during rename; retry"
            raise JsonRpcException(msg, code=lsp.LSPErrorCodes.RequestFailed)
        return features.rename_edits(
            uri, version, occurrences, new_name, state.line_index, enc, document_changes=document_changes
        )

    # -- formatting pipeline ----------------------------------------------------------------

    def _ensure_format_pipeline(
        self, logs: list[tuple[lsp.MessageType, str]]
    ) -> tuple[ParserResult, UnparserResult] | None:
        """Build the standard-disposition parser + unparser once; memoize a build failure.

        Returns the pipeline when available, else None. On the first failure the exception is logged
        in full and the failure recorded; every later call logs one line and returns None without
        retrying codegen that cannot start succeeding.
        """
        if self._fmt_failed:
            logs.append((lsp.MessageType.Info, "fltk-lsp: formatting is unavailable (pipeline build failed)"))
            return None
        if self._fmt_pipeline is not None:
            return self._fmt_pipeline
        try:
            parser = plumbing.generate_parser(self._engine.source_grammar)
            unparser = plumbing.generate_unparser(
                self._engine.source_grammar, parser.cst_module_name, self._formatter_config
            )
        except Exception as exc:
            self._fmt_failed = True
            logs.append((lsp.MessageType.Error, f"fltk-lsp: formatting unavailable, pipeline build failed: {exc!r}"))
            return None
        self._fmt_pipeline = (parser, unparser)
        return self._fmt_pipeline

    def _format_blocking(self, text: str) -> tuple[list[lsp.TextEdit] | None, list[tuple[lsp.MessageType, str]]]:
        """Format ``text`` on the worker thread; return edits (or None) plus messages to log.

        Every failure mode -- unbuildable pipeline, unparseable input, an unparser/render
        exception, or output that fails to reparse -- degrades to ``None`` (no edits) so a broken
        or mis-formatted document is never written. Protocol I/O (logging) is deferred to the
        caller on the loop thread.
        """
        logs: list[tuple[lsp.MessageType, str]] = []
        pipeline = self._ensure_format_pipeline(logs)
        if pipeline is None:
            return None, logs
        parser, unparser = pipeline
        try:
            # A valid but deeply nested document can raise RecursionError from the generated parser;
            # like the unparse/render step, that must degrade to no-edits, not a raw LSP error.
            parsed = plumbing.parse_text(parser, text, self._start_rule)
        except Exception as exc:
            logs.append((lsp.MessageType.Error, f"fltk-lsp: formatting failed while parsing input: {exc!r}"))
            return None, logs
        if not parsed.success:
            logs.append((lsp.MessageType.Info, "fltk-lsp: not formatting an unparseable document"))
            return None, logs
        try:
            doc = plumbing.unparse_cst(unparser, parsed.cst, text, self._start_rule)
            rendered = plumbing.render_doc(doc, self._renderer_config)
        except Exception as exc:
            logs.append((lsp.MessageType.Error, f"fltk-lsp: formatting failed during unparse/render: {exc!r}"))
            return None, logs
        try:
            verify = plumbing.parse_text(parser, rendered, self._start_rule)
        except Exception as exc:
            logs.append((lsp.MessageType.Error, f"fltk-lsp: formatted output failed to reparse: {exc!r}"))
            return None, logs
        if not verify.success:
            logs.append((lsp.MessageType.Error, "fltk-lsp: formatted output does not parse; discarding edits"))
            return None, logs
        if rendered == text:
            return [], logs
        end_line, end_char = LineIndex(text).end_position(self._encoding())
        whole = lsp.Range(
            start=lsp.Position(line=0, character=0),
            end=lsp.Position(line=end_line, character=end_char),
        )
        return [lsp.TextEdit(range=whole, new_text=rendered)], logs

    async def format_document(self, uri: str) -> list[lsp.TextEdit] | None:
        """Run the formatting pipeline for ``uri`` on the worker thread and emit any log messages."""
        document = self.workspace.get_text_document(uri)
        loop = asyncio.get_running_loop()
        edits, logs = await loop.run_in_executor(self._executor, self._format_blocking, document.source)
        for level, message in logs:
            self.window_log_message(lsp.LogMessageParams(type=level, message=message))
        return edits


def _apply_edits(text: str, occurrences: list[tuple[int, int]], new_name: str) -> str:
    """Replace every ``(start, end)`` codepoint span in ``text`` with ``new_name``.

    Occurrences are non-overlapping; applying them back-to-front keeps earlier offsets valid.
    """
    result = text
    for start, end in sorted(occurrences, reverse=True):
        result = result[:start] + new_name + result[end:]
    return result


def create_server(
    engine: AnalysisEngine,
    formatter_config: FormatterConfig | None,
    renderer_config: RendererConfig,
) -> FltkLanguageServer:
    """Build and wire an :class:`FltkLanguageServer`; the caller runs ``start_io``.

    Kept separate from the CLI so the server can be constructed and driven in-process by tests. The
    start rule comes from ``engine``; there is no separate parameter to keep in sync with it.
    """
    server = FltkLanguageServer(engine, formatter_config, renderer_config)
    legend = lsp.SemanticTokensLegend(
        token_types=list(features.SEMANTIC_TOKEN_TYPES),
        token_modifiers=list(features.SEMANTIC_TOKEN_MODIFIERS),
    )

    @server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
    async def did_open(params: lsp.DidOpenTextDocumentParams) -> None:
        document = params.text_document
        await server.analyze_and_publish(document.uri, document.version, document.text)

    @server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
    async def did_change(params: lsp.DidChangeTextDocumentParams) -> None:
        server.schedule_debounced(params.text_document.uri)

    @server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
    async def did_close(params: lsp.DidCloseTextDocumentParams) -> None:
        server.drop(params.text_document.uri)

    @server.feature(lsp.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL, legend)
    async def semantic_tokens_full(params: lsp.SemanticTokensParams) -> lsp.SemanticTokens:
        uri = params.text_document.uri
        document = server.workspace.get_text_document(uri)
        state = await server._ensure_analyzed(uri, document.version, document.source)
        served = state.served_tokens
        return lsp.SemanticTokens(data=list(served.encoded) if served is not None else [])

    @server.feature(lsp.TEXT_DOCUMENT_SEMANTIC_TOKENS_RANGE)
    async def semantic_tokens_range(params: lsp.SemanticTokensRangeParams) -> lsp.SemanticTokens:
        uri = params.text_document.uri
        document = server.workspace.get_text_document(uri)
        state = await server._ensure_analyzed(uri, document.version, document.source)
        served = state.served_tokens
        if served is None:
            return lsp.SemanticTokens(data=[])
        # Segments are sorted and non-overlapping by (line, char), so their end positions are
        # monotonic too: the overlap window {s : s.end_pos > range.start and s.start_pos < range.end}
        # is the slice [lo:hi] found by two bisects on position tuples -- no line index needed, which
        # is correct for the stale tail too (its positions are already client-coordinate approximations).
        segments = served.segments
        start_pos = (params.range.start.line, params.range.start.character)
        end_pos = (params.range.end.line, params.range.end.character)
        lo = bisect.bisect_right(segments, start_pos, key=lambda s: (s.line, s.char + s.length))
        hi = bisect.bisect_left(segments, end_pos, key=lambda s: (s.line, s.char))
        return lsp.SemanticTokens(data=features.delta_encode_segments(segments[lo:hi]))

    @server.feature(lsp.TEXT_DOCUMENT_FOLDING_RANGE)
    async def folding_range(params: lsp.FoldingRangeParams) -> list[lsp.FoldingRange] | None:
        ready = await server._serveable_for(params.text_document.uri)
        if ready is None:
            return None
        good, _enc = ready
        return features.folding_ranges(good.tree, engine.trivia_kind_names, good.line_index)

    @server.feature(lsp.TEXT_DOCUMENT_SELECTION_RANGE)
    async def selection_range(params: lsp.SelectionRangeParams) -> list[lsp.SelectionRange] | None:
        ready = await server._serveable_for(params.text_document.uri)
        if ready is None:
            return None
        good, enc = ready
        offsets = [good.line_index.position_to_offset(pos.line, pos.character, enc) for pos in params.positions]
        return features.selection_ranges(good.tree, offsets, good.line_index, enc)

    @server.feature(lsp.TEXT_DOCUMENT_FORMATTING)
    async def formatting(params: lsp.DocumentFormattingParams) -> list[lsp.TextEdit] | None:
        return await server.format_document(params.text_document.uri)

    @server.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    async def document_symbol(
        params: lsp.DocumentSymbolParams,
    ) -> list[lsp.DocumentSymbol] | list[lsp.SymbolInformation] | None:
        uri = params.text_document.uri
        ready = await server._serveable_for(uri)
        if ready is None:
            return None
        good, enc = ready
        if server._hierarchical_symbols():
            return features.document_symbols(good.symbols, good.line_index, enc)
        return features.document_symbols_flat(good.symbols, uri, good.line_index, enc)

    @server.feature(lsp.TEXT_DOCUMENT_DEFINITION)
    async def definition(params: lsp.DefinitionParams) -> lsp.Location | None:
        uri = params.text_document.uri
        ready = await server._serveable_for(uri)
        if ready is None:
            return None
        good, enc = ready
        offset = good.line_index.position_to_offset(params.position.line, params.position.character, enc)
        return features.definition_location(good.symbols, offset, uri, good.line_index, enc)

    @server.feature(lsp.TEXT_DOCUMENT_REFERENCES)
    async def references(params: lsp.ReferenceParams) -> list[lsp.Location] | None:
        uri = params.text_document.uri
        ready = await server._serveable_for(uri)
        if ready is None:
            return None
        good, enc = ready
        offset = good.line_index.position_to_offset(params.position.line, params.position.character, enc)
        return features.reference_locations(
            good.symbols, offset, uri, good.line_index, enc, include_declaration=params.context.include_declaration
        )

    @server.feature(lsp.TEXT_DOCUMENT_DOCUMENT_HIGHLIGHT)
    async def document_highlight(params: lsp.DocumentHighlightParams) -> list[lsp.DocumentHighlight] | None:
        ready = await server._serveable_for(params.text_document.uri)
        if ready is None:
            return None
        good, enc = ready
        offset = good.line_index.position_to_offset(params.position.line, params.position.character, enc)
        return features.document_highlights(good.symbols, offset, good.line_index, enc)

    @server.feature(lsp.TEXT_DOCUMENT_PREPARE_RENAME)
    async def prepare_rename(params: lsp.PrepareRenameParams) -> lsp.Range | None:
        ready = await server._serveable_for(params.text_document.uri)
        if ready is None:
            return None
        good, enc = ready
        offset = good.line_index.position_to_offset(params.position.line, params.position.character, enc)
        return features.prepare_rename(good.symbols, offset, good.line_index, enc)

    @server.feature(lsp.TEXT_DOCUMENT_RENAME, lsp.RenameOptions(prepare_provider=True))
    async def rename(params: lsp.RenameParams) -> lsp.WorkspaceEdit | None:
        return await server.rename_document(params.text_document.uri, params.position, params.new_name)

    return server
