"""End-to-end tests for the ``fltk-lsp`` server, driven over the real protocol via pytest-lsp.

Each test spawns ``python -m fltk.lsp.server_cli`` as a subprocess against the fixture language
(``test_data/greet.*``) and exercises it through a real LSP client: initialization and
position-encoding negotiation, diagnostics, semantic tokens (including stale serving), folding,
selection, and formatting. The formatter-build-failure memoization is unit-tested in-process
(no live server) since a genuine codegen failure cannot be provoked from a valid grammar.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
from pathlib import Path

import pytest
import pytest_lsp
from lsprotocol import types as t
from pytest_lsp import ClientServerConfig, LanguageClient

from fltk import plumbing
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.positions import PositionEncoding
from fltk.lsp.server import create_server
from fltk.unparse.renderer import RendererConfig

_DATA = Path(__file__).parent / "test_data"
_GRAMMAR = str(_DATA / "greet.fltkg")
_LSP = str(_DATA / "greet.fltklsp")
_FMT = str(_DATA / "greet.fltkfmt")

_SERVER_COMMAND = [
    sys.executable,
    "-m",
    "fltk.lsp.server_cli",
    "--grammar",
    _GRAMMAR,
    "--lsp",
    _LSP,
    "--fmt",
    _FMT,
    "--width",
    "80",
    "--indent",
    "2",
]

_URI = "file:///doc.greet"
_CLEAN = "greet alice.\ngreet bob."
_BROKEN = "greet 123."  # `name` is /[a-z]+/, so a digit fails to parse
_ASTRAL = 'note "h\U0001f600i".'
_PUBLISH = t.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS


def _init_params(encodings: list[t.PositionEncodingKind]) -> t.InitializeParams:
    return t.InitializeParams(
        capabilities=t.ClientCapabilities(
            general=t.GeneralClientCapabilities(position_encodings=encodings),
        ),
        root_uri=None,
    )


async def _open(client: LanguageClient, text: str, *, version: int = 1) -> None:
    client.text_document_did_open(
        t.DidOpenTextDocumentParams(
            text_document=t.TextDocumentItem(uri=_URI, language_id="greet", version=version, text=text)
        )
    )
    await client.wait_for_notification(_PUBLISH)


async def _change(client: LanguageClient, text: str, *, version: int) -> None:
    client.text_document_did_change(
        t.DidChangeTextDocumentParams(
            text_document=t.VersionedTextDocumentIdentifier(uri=_URI, version=version),
            content_changes=[t.TextDocumentContentChangeWholeDocument(text=text)],
        )
    )
    await client.wait_for_notification(_PUBLISH)


async def _tokens(client: LanguageClient) -> list[int]:
    result = await client.text_document_semantic_tokens_full_async(
        t.SemanticTokensParams(text_document=t.TextDocumentIdentifier(uri=_URI))
    )
    assert result is not None
    return list(result.data)


@pytest_lsp.fixture(config=ClientServerConfig(server_command=_SERVER_COMMAND))
async def client(lsp_client: LanguageClient):
    yield
    # Teardown of a session a test may have left uninitialized.
    with contextlib.suppress(Exception):
        await lsp_client.shutdown_session()


@pytest.mark.asyncio
async def test_initialize_advertises_utf32_when_offered(client: LanguageClient) -> None:
    result = await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    assert result.capabilities.position_encoding == t.PositionEncodingKind.Utf32
    provider = result.capabilities.semantic_tokens_provider
    assert provider is not None
    assert next(iter(provider.legend.token_types)) == "keyword"


@pytest.mark.asyncio
async def test_initialize_falls_back_to_utf16(client: LanguageClient) -> None:
    result = await client.initialize_session(_init_params([t.PositionEncodingKind.Utf16]))
    assert result.capabilities.position_encoding == t.PositionEncodingKind.Utf16


@pytest.mark.asyncio
async def test_initialize_utf8_first_is_answered_and_tokens_agree(client: LanguageClient) -> None:
    # A client offering utf-8 first must be answered with utf-32 or utf-16 (never utf-8), and the
    # emitted token positions must be computed in the *advertised* encoding.
    result = await client.initialize_session(_init_params([t.PositionEncodingKind.Utf8, t.PositionEncodingKind.Utf16]))
    assert result.capabilities.position_encoding == t.PositionEncodingKind.Utf16
    await _open(client, _ASTRAL)
    data = await _tokens(client)
    # Groups of 5: [note kw, string, punct]. The astral emoji makes the string token one utf-16
    # unit longer than its codepoint length (5) -> 6.
    assert data[5 * 1 + 2] == 6


@pytest.mark.asyncio
async def test_utf32_token_lengths_are_codepoints(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _ASTRAL)
    data = await _tokens(client)
    assert data[5 * 1 + 2] == 5  # utf-32: the string token length is its codepoint count


@pytest.mark.asyncio
async def test_didopen_clean_document(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _CLEAN)
    assert not client.diagnostics[_URI]
    assert len(await _tokens(client)) > 0


@pytest.mark.asyncio
async def test_breaking_edit_reports_error_and_serves_stale_tokens(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _CLEAN)
    good = await _tokens(client)
    assert len(good) > 0

    await _change(client, _BROKEN, version=2)
    diagnostics = client.diagnostics[_URI]
    assert len(diagnostics) == 1
    assert diagnostics[0].severity == t.DiagnosticSeverity.Error
    # `123` starts at column 6 on line 0.
    assert diagnostics[0].range.start == t.Position(line=0, character=6)

    # Stale tokens from the last good parse are still served rather than a blank document.
    assert await _tokens(client) == good


@pytest.mark.asyncio
async def test_fixing_edit_clears_diagnostics_and_refreshes_tokens(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _BROKEN)
    assert len(client.diagnostics[_URI]) == 1

    await _change(client, _CLEAN, version=2)
    assert not client.diagnostics[_URI]
    assert len(await _tokens(client)) > 0


@pytest.mark.asyncio
async def test_folding_marks_block_comment(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, "/* a\n b */\ngreet alice.")
    result = await client.text_document_folding_range_async(
        t.FoldingRangeParams(text_document=t.TextDocumentIdentifier(uri=_URI))
    )
    assert result is not None
    comment_folds = [r for r in result if r.kind == t.FoldingRangeKind.Comment]
    assert any(r.start_line == 0 and r.end_line == 1 for r in comment_folds)


@pytest.mark.asyncio
async def test_selection_widens_outward(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _CLEAN)
    result = await client.text_document_selection_range_async(
        t.SelectionRangeParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            positions=[t.Position(line=0, character=8)],  # inside `alice`
        )
    )
    assert result is not None
    head = result[0]
    assert head.range.start.character >= 6  # within `alice`
    assert head.parent is not None  # widens to an enclosing node


@pytest.mark.asyncio
async def test_formatting_reformats_and_is_idempotent(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, "greet   alice.\ngreet bob.")
    edits = await client.text_document_formatting_async(
        t.DocumentFormattingParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            options=t.FormattingOptions(tab_size=8, insert_spaces=True),
        )
    )
    assert edits is not None
    assert len(edits) == 1
    canonical = "\ngreet alice.\ngreet bob.\n"
    assert edits[0].new_text == canonical

    # The already-canonical form yields no edits.
    await _change(client, canonical, version=2)
    edits2 = await client.text_document_formatting_async(
        t.DocumentFormattingParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            options=t.FormattingOptions(tab_size=8, insert_spaces=True),
        )
    )
    assert edits2 is not None
    assert len(edits2) == 0


@pytest.mark.asyncio
async def test_formatting_unparseable_document_returns_none(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _BROKEN)
    edits = await client.text_document_formatting_async(
        t.DocumentFormattingParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            options=t.FormattingOptions(tab_size=2, insert_spaces=True),
        )
    )
    assert edits is None


@pytest.mark.asyncio
async def test_close_then_reopen(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _CLEAN)
    client.text_document_did_close(t.DidCloseTextDocumentParams(text_document=t.TextDocumentIdentifier(uri=_URI)))
    await _open(client, _CLEAN, version=2)
    assert not client.diagnostics[_URI]
    assert len(await _tokens(client)) > 0


def _fixture_server():
    engine = AnalysisEngine.from_paths(Path(_GRAMMAR), Path(_LSP))
    formatter_config = plumbing.parse_format_config_file(Path(_FMT))
    return create_server(engine, formatter_config, RendererConfig(max_width=80, indent_width=2), start_rule=None)


def test_format_build_failure_is_memoized(monkeypatch: pytest.MonkeyPatch) -> None:
    server = _fixture_server()
    calls = {"n": 0}
    original = plumbing.generate_unparser

    def _boom(*args, **kwargs):  # noqa: ARG001
        calls["n"] += 1
        msg = "synthetic codegen failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(plumbing, "generate_unparser", _boom)

    edits1, logs1 = server._format_blocking(_CLEAN)
    edits2, logs2 = server._format_blocking(_CLEAN)

    assert edits1 is None
    assert edits2 is None
    assert calls["n"] == 1  # the failed build is memoized, not retried
    assert any(level == t.MessageType.Error for level, _ in logs1)
    assert logs2  # the second request still logs a one-line "unavailable" message
    monkeypatch.setattr(plumbing, "generate_unparser", original)


def test_format_render_exception_degrades_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    # The unparse/render guard catches broad Exception (not just ValueError): a KeyError/etc. from
    # generated code must degrade to no-edits + a log, never propagate as a raw LSP request error.
    server = _fixture_server()

    def _boom(*args, **kwargs):  # noqa: ARG001
        msg = "synthetic unparser bug"
        raise KeyError(msg)

    monkeypatch.setattr(plumbing, "unparse_cst", _boom)
    edits, logs = server._format_blocking(_CLEAN)
    assert edits is None
    assert any(level == t.MessageType.Error for level, _ in logs)


def test_formatting_without_fmt_uses_default_config(monkeypatch: pytest.MonkeyPatch) -> None:
    # Formatting is registered even without --fmt, using FormatterConfig() defaults; the path must
    # produce edits (possibly empty), never None or a crash, and log no error.
    engine = AnalysisEngine.from_paths(Path(_GRAMMAR), Path(_LSP))
    server = create_server(engine, None, RendererConfig(max_width=80, indent_width=2), start_rule=None)
    monkeypatch.setattr(server, "_encoding", lambda: PositionEncoding.UTF32)
    edits, logs = server._format_blocking("greet   alice.\ngreet bob.")
    assert edits is not None
    assert not any(level == t.MessageType.Error for level, _ in logs)


def test_store_ignores_older_version_result(monkeypatch: pytest.MonkeyPatch) -> None:
    # The out-of-order-version guard: an analysis for an older version must not clobber a newer one.
    server = _fixture_server()
    monkeypatch.setattr(server, "_encoding", lambda: PositionEncoding.UTF32)
    fresh = server._analyze_blocking(_CLEAN)
    stale = server._analyze_blocking(_BROKEN)
    server._store(_URI, 2, *fresh, epoch=0)
    server._store(_URI, 1, *stale, epoch=0)
    state = server._docs[_URI]
    assert state.analyzed_version == 2
    assert state.analysis is fresh[0]


def test_store_after_drop_does_not_resurrect_state(monkeypatch: pytest.MonkeyPatch) -> None:
    # A late-completing analysis whose URI was closed (epoch advanced) is discarded, not stored.
    server = _fixture_server()
    monkeypatch.setattr(server, "text_document_publish_diagnostics", lambda *_a, **_k: None)
    monkeypatch.setattr(server, "_encoding", lambda: PositionEncoding.UTF32)
    result = server._analyze_blocking(_CLEAN)
    epoch = server._epochs.get(_URI, 0)
    server.drop(_URI)
    server._store(_URI, 1, *result, epoch)
    assert _URI not in server._docs


@pytest.mark.asyncio
async def test_debounce_reschedule_cancels_prior_and_keeps_replacement() -> None:
    # correctness of the debounce bookkeeping: rescheduling cancels the pending task, and the
    # cancelled task's cleanup must not evict its replacement from the debounce map.
    server = _fixture_server()
    server.schedule_debounced(_URI)
    first = server._debounce[_URI]
    server.schedule_debounced(_URI)
    second = server._debounce[_URI]
    assert first is not second
    await asyncio.sleep(0.01)  # let `first`'s cancellation propagate and run its finally
    assert first.cancelled()
    assert server._debounce.get(_URI) is second
    second.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await second


@pytest.mark.asyncio
async def test_analysis_for_single_flight_shares_one_submission(monkeypatch: pytest.MonkeyPatch) -> None:
    # Two concurrent analyses for the same version share one worker submission rather than parsing
    # twice (the single-worker executor premise).
    server = _fixture_server()
    monkeypatch.setattr(server, "_encoding", lambda: PositionEncoding.UTF32)
    calls = {"n": 0}
    real = server._analyze_blocking

    def _counting(text: str):
        calls["n"] += 1
        return real(text)

    monkeypatch.setattr(server, "_analyze_blocking", _counting)
    states = await asyncio.gather(
        server._analysis_for(_URI, 1, _CLEAN),
        server._analysis_for(_URI, 1, _CLEAN),
    )
    assert calls["n"] == 1
    assert all(s.last_good is not None for s in states)


@pytest.mark.asyncio
async def test_semantic_tokens_range_returns_line_subset(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _CLEAN)  # "greet alice.\ngreet bob."
    full = await _tokens(client)
    result = await client.text_document_semantic_tokens_range_async(
        t.SemanticTokensRangeParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            range=t.Range(start=t.Position(line=1, character=0), end=t.Position(line=1, character=9)),
        )
    )
    assert result is not None
    data = list(result.data)
    assert 0 < len(data) < len(full)  # a strict subset of the full-document token stream
    assert data[0] == 1  # the first emitted token's deltaLine points at line 1
    assert all(data[i] == 0 for i in range(5, len(data), 5))  # every emitted token sits on line 1
