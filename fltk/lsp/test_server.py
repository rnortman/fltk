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
import types
from pathlib import Path

import pytest
import pytest_lsp
from lsprotocol import types as t
from pygls.exceptions import JsonRpcException
from pytest_lsp import ClientServerConfig, LanguageClient

from fltk import plumbing
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.positions import LineIndex, PositionEncoding
from fltk.lsp.server import _DocState, _GoodAnalysis, create_server
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

# A second invocation pinned to the `greeting` rule: unlike `document` (whose `item*` always matches
# zero items, so it never hard-fails), `greeting` can reject input outright, producing a *failed*
# analysis with no prefix -- the only way to exercise the served-nothing path over the real protocol.
_SERVER_COMMAND_RULE = [*_SERVER_COMMAND, "--rule", "greeting"]

_URI = "file:///doc.greet"
_CLEAN = "greet alice.\ngreet bob."
_BROKEN = "greet 123."  # `name` is /[a-z]+/, so a digit fails to parse
_ASTRAL = 'note "h\U0001f600i".'
_PUBLISH = t.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS

# Mid-file error shapes: `document := , item*`, so a broken later item leaves an assembled prefix.
_PARTIAL = "greet alice.\ngreet 123."  # first item parses; `123` on line 1 breaks the second
_PARTIAL_AFTER = "greet alicia.\ngreet 1."  # prefix repaints line 0 (`alicia`, len 6); line 1 breaks

# A document exercising def/ref/namespace: `module outer` opens a namespace whose name hoists to
# the root scope; `def alpha` inside defines a member; `use alpha` inside references it; `use outer`
# at the root references the hoisted module name.
_SYM = "module outer {\n  def alpha.\n  use alpha.\n}\nuse outer."
# A broken first item leaves a zero-length prefix, so the partial's own tree carries no symbols --
# any symbol the outline still reports must come from the last complete analysis, not the prefix.
_SYM_BROKEN = "greet 1.\n" + _SYM


def _init_params(
    encodings: list[t.PositionEncodingKind], *, hierarchical: bool = False, document_changes: bool = False
) -> t.InitializeParams:
    text_document = (
        t.TextDocumentClientCapabilities(
            document_symbol=t.DocumentSymbolClientCapabilities(hierarchical_document_symbol_support=True)
        )
        if hierarchical
        else None
    )
    workspace = (
        t.WorkspaceClientCapabilities(workspace_edit=t.WorkspaceEditClientCapabilities(document_changes=True))
        if document_changes
        else None
    )
    return t.InitializeParams(
        capabilities=t.ClientCapabilities(
            general=t.GeneralClientCapabilities(position_encodings=encodings),
            text_document=text_document,
            workspace=workspace,
        ),
        root_uri=None,
    )


def _line_col(text: str, offset: int, enc: t.PositionEncodingKind) -> t.Position:
    """The LSP ``Position`` of a codepoint ``offset`` in ``text``, via the same ``LineIndex`` math the server uses."""
    encoding = PositionEncoding.UTF32 if enc == t.PositionEncodingKind.Utf32 else PositionEncoding.UTF16
    line, character = LineIndex(text).offset_to_position(offset, encoding)
    return t.Position(line=line, character=character)


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


async def _range_tokens(client: LanguageClient, rng: t.Range) -> list[int]:
    result = await client.text_document_semantic_tokens_range_async(
        t.SemanticTokensRangeParams(text_document=t.TextDocumentIdentifier(uri=_URI), range=rng)
    )
    assert result is not None
    return list(result.data)


def _decode(data: list[int]) -> list[tuple[int, int, int, int, int]]:
    """Decode the LSP relative token stream into absolute ``(line, char, length, type, modifiers)``."""
    out: list[tuple[int, int, int, int, int]] = []
    line = char = 0
    for i in range(0, len(data), 5):
        delta_line, delta_char, length, ttype, mods = data[i : i + 5]
        line += delta_line
        char = delta_char if delta_line else char + delta_char
        out.append((line, char, length, ttype, mods))
    return out


@pytest_lsp.fixture(config=ClientServerConfig(server_command=_SERVER_COMMAND))
async def client(lsp_client: LanguageClient):
    yield
    # Teardown of a session a test may have left uninitialized.
    with contextlib.suppress(Exception):
        await lsp_client.shutdown_session()


@pytest_lsp.fixture(config=ClientServerConfig(server_command=_SERVER_COMMAND_RULE))
async def client_rule(lsp_client: LanguageClient):
    yield
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


_ASTRAL_SYM = 'note "h\U0001f600i". def alpha. use alpha.'


@pytest.mark.asyncio
async def test_document_symbol_hierarchical_nests_members(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32], hierarchical=True))
    await _open(client, _SYM)
    result = await client.text_document_document_symbol_async(
        t.DocumentSymbolParams(text_document=t.TextDocumentIdentifier(uri=_URI))
    )
    assert result is not None
    assert all(isinstance(sym, t.DocumentSymbol) for sym in result)
    roots = {sym.name: sym for sym in result if isinstance(sym, t.DocumentSymbol)}
    assert set(roots) == {"outer"}
    outer = roots["outer"]
    assert outer.kind == t.SymbolKind.Namespace
    assert outer.detail == "namespace"
    children = list(outer.children or [])
    assert [child.name for child in children] == ["alpha"]
    alpha = children[0]
    assert alpha.kind == t.SymbolKind.Variable
    # selection range is the name span, contained in the (wider) declaration range.
    assert alpha.selection_range.start == _line_col(_SYM, _SYM.index("alpha"), t.PositionEncodingKind.Utf32)


@pytest.mark.asyncio
async def test_document_symbol_flat_for_client_without_hierarchy(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _SYM)
    result = await client.text_document_document_symbol_async(
        t.DocumentSymbolParams(text_document=t.TextDocumentIdentifier(uri=_URI))
    )
    assert result is not None
    assert all(isinstance(sym, t.SymbolInformation) for sym in result)
    assert {sym.name for sym in result} == {"outer", "alpha"}


@pytest.mark.asyncio
@pytest.mark.parametrize("encoding", [t.PositionEncodingKind.Utf16, t.PositionEncodingKind.Utf32])
async def test_definition_from_reference_over_astral_text(
    client: LanguageClient, encoding: t.PositionEncodingKind
) -> None:
    await client.initialize_session(_init_params([encoding]))
    await _open(client, _ASTRAL_SYM)
    use_at = _ASTRAL_SYM.rindex("alpha")
    result = await client.text_document_definition_async(
        t.DefinitionParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            position=_line_col(_ASTRAL_SYM, use_at + 1, encoding),
        )
    )
    assert isinstance(result, t.Location)
    def_at = _ASTRAL_SYM.index("alpha")
    assert result.range.start == _line_col(_ASTRAL_SYM, def_at, encoding)
    assert result.range.end == _line_col(_ASTRAL_SYM, def_at + len("alpha"), encoding)


@pytest.mark.asyncio
async def test_references_and_highlights(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _SYM)
    enc = t.PositionEncodingKind.Utf32
    def_pos = _line_col(_SYM, _SYM.index("alpha") + 1, enc)

    with_decl = await client.text_document_references_async(
        t.ReferenceParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            position=def_pos,
            context=t.ReferenceContext(include_declaration=True),
        )
    )
    assert with_decl is not None
    assert len(with_decl) == 2  # def alpha + use alpha

    without_decl = await client.text_document_references_async(
        t.ReferenceParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            position=def_pos,
            context=t.ReferenceContext(include_declaration=False),
        )
    )
    assert without_decl is not None
    assert len(without_decl) == 1  # only the use site

    highlights = await client.text_document_document_highlight_async(
        t.DocumentHighlightParams(text_document=t.TextDocumentIdentifier(uri=_URI), position=def_pos)
    )
    assert highlights is not None
    kinds = {h.kind for h in highlights}
    assert t.DocumentHighlightKind.Write in kinds  # the declaration
    assert t.DocumentHighlightKind.Read in kinds  # the reference


@pytest.mark.asyncio
async def test_rename_returns_versioned_document_changes(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32], document_changes=True))
    await _open(client, _SYM)
    result = await client.text_document_rename_async(
        t.RenameParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            position=_line_col(_SYM, _SYM.index("alpha") + 1, t.PositionEncodingKind.Utf32),
            new_name="beta",
        )
    )
    assert result is not None
    assert result.changes is None
    assert result.document_changes is not None
    edit = result.document_changes[0]
    assert isinstance(edit, t.TextDocumentEdit)
    assert edit.text_document.version == 1  # versioned against the analyzed document
    assert all(isinstance(e, t.TextEdit) for e in edit.edits)
    assert {e.new_text for e in edit.edits if isinstance(e, t.TextEdit)} == {"beta"}
    assert len(edit.edits) == 2  # both occurrences


@pytest.mark.asyncio
async def test_rename_returns_plain_changes_without_capability(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _SYM)
    result = await client.text_document_rename_async(
        t.RenameParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            position=_line_col(_SYM, _SYM.index("alpha") + 1, t.PositionEncodingKind.Utf32),
            new_name="beta",
        )
    )
    assert result is not None
    assert result.document_changes is None
    assert result.changes is not None
    assert len(result.changes[_URI]) == 2


@pytest.mark.asyncio
async def test_rename_to_same_name_returns_empty_edit(client: LanguageClient) -> None:
    # A no-op rename (new name == old name) returns an empty edit and skips the verify-reparse.
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32], document_changes=True))
    await _open(client, _SYM)
    result = await client.text_document_rename_async(
        t.RenameParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            position=_line_col(_SYM, _SYM.index("alpha") + 1, t.PositionEncodingKind.Utf32),
            new_name="alpha",
        )
    )
    assert result is not None
    assert result.document_changes is not None
    edit = result.document_changes[0]
    assert isinstance(edit, t.TextDocumentEdit)
    assert list(edit.edits) == []


@pytest.mark.asyncio
async def test_rename_refuses_when_version_advances_during_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    # The version-race guard: a didChange bumping the live document during the analysis await must
    # abort the rename rather than splice this version's offsets into newer text.
    server = _fixture_server()
    docs = [types.SimpleNamespace(version=1, source=_SYM), types.SimpleNamespace(version=2, source=_SYM)]
    seen = {"n": 0}

    def _get(_uri: str) -> types.SimpleNamespace:
        doc = docs[min(seen["n"], len(docs) - 1)]
        seen["n"] += 1
        return doc

    fake_ws = types.SimpleNamespace(get_text_document=_get)
    monkeypatch.setattr(type(server), "workspace", property(lambda _self: fake_ws))

    async def _ensure(_uri: str, version: int | None, _text: str) -> _DocState:
        return _DocState(analyzed_version=version)

    monkeypatch.setattr(server, "_ensure_analyzed", _ensure)
    with pytest.raises(JsonRpcException, match="changed during rename"):
        await server.rename_document(_URI, t.Position(line=0, character=0), "beta")


@pytest.mark.asyncio
async def test_rename_on_broken_document_errors(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _BROKEN)
    with pytest.raises(Exception):  # noqa: B017 -- server returns a response error
        await client.text_document_rename_async(
            t.RenameParams(
                text_document=t.TextDocumentIdentifier(uri=_URI),
                position=t.Position(line=0, character=0),
                new_name="whatever",
            )
        )


@pytest.mark.asyncio
async def test_rename_to_parse_breaking_name_errors(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _SYM)
    with pytest.raises(Exception):  # noqa: B017 -- verify-reparse rejects the edit
        await client.text_document_rename_async(
            t.RenameParams(
                text_document=t.TextDocumentIdentifier(uri=_URI),
                position=_line_col(_SYM, _SYM.index("alpha") + 1, t.PositionEncodingKind.Utf32),
                new_name="beta1",  # `name` is /[a-z]+/, so the trailing digit derails the parse
            )
        )


@pytest.mark.asyncio
async def test_prepare_rename_on_keyword_is_null(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _SYM)
    on_keyword = await client.text_document_prepare_rename_async(
        t.PrepareRenameParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            position=_line_col(_SYM, _SYM.index("def") + 1, t.PositionEncodingKind.Utf32),
        )
    )
    assert on_keyword is None
    on_name = await client.text_document_prepare_rename_async(
        t.PrepareRenameParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            position=_line_col(_SYM, _SYM.index("alpha") + 1, t.PositionEncodingKind.Utf32),
        )
    )
    assert on_name is not None


@pytest.mark.asyncio
async def test_navigation_served_from_last_good_after_break(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _SYM)
    await _change(client, _BROKEN, version=2)
    # The current version has parse errors; navigation still serves the last good analysis.
    result = await client.text_document_definition_async(
        t.DefinitionParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            position=_line_col(_SYM, _SYM.rindex("alpha") + 1, t.PositionEncodingKind.Utf32),
        )
    )
    assert isinstance(result, t.Location)
    assert result.range.start == _line_col(_SYM, _SYM.index("alpha"), t.PositionEncodingKind.Utf32)


def _fixture_server():
    engine = AnalysisEngine.from_paths(Path(_GRAMMAR), Path(_LSP))
    formatter_config = plumbing.parse_format_config_file(Path(_FMT))
    return create_server(engine, formatter_config, RendererConfig(max_width=80, indent_width=2))


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
    server = create_server(engine, None, RendererConfig(max_width=80, indent_width=2))
    monkeypatch.setattr(server, "_encoding", lambda: PositionEncoding.UTF32)
    edits, logs = server._format_blocking("greet   alice.\ngreet bob.")
    assert edits is not None
    assert not any(level == t.MessageType.Error for level, _ in logs)


def test_store_ignores_older_version_result(monkeypatch: pytest.MonkeyPatch) -> None:
    # The out-of-order-version guard: an analysis for an older version must not clobber a newer one.
    server = _fixture_server()
    monkeypatch.setattr(server, "_encoding", lambda: PositionEncoding.UTF32)
    fresh = server._analyze_blocking(_CLEAN, None)
    stale = server._analyze_blocking(_BROKEN, None)
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
    result = server._analyze_blocking(_CLEAN, None)
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

    def _counting(text: str, stale: _GoodAnalysis | None):
        calls["n"] += 1
        return real(text, stale)

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


# --- Partial (prefix-CST) serving --------------------------------------------------------------


@pytest.mark.asyncio
async def test_partial_on_open_serves_fresh_prefix_and_diagnostic(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _PARTIAL)
    # A mid-file error still reports a diagnostic at the failure position, exactly as a full failure.
    diagnostics = client.diagnostics[_URI]
    assert len(diagnostics) == 1
    assert diagnostics[0].severity == t.DiagnosticSeverity.Error
    assert diagnostics[0].range.start == t.Position(line=1, character=6)  # `123`
    # With no prior good version the served tokens are the fresh prefix only: every token sits on
    # line 0, and nothing is served for the broken tail on line 1.
    decoded = _decode(await _tokens(client))
    assert len(decoded) > 0
    assert all(line == 0 for line, *_rest in decoded)


@pytest.mark.asyncio
async def test_hard_failure_serves_empty_tokens_from_both_handlers(client_rule: LanguageClient) -> None:
    await client_rule.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client_rule, "xyz")  # the `greeting` start rule rejects `xyz`: no prefix tree at all
    assert len(client_rule.diagnostics[_URI]) == 1
    assert await _tokens(client_rule) == []
    rng = t.Range(start=t.Position(line=0, character=0), end=t.Position(line=0, character=3))
    assert await _range_tokens(client_rule, rng) == []


@pytest.mark.asyncio
async def test_partial_after_good_merges_fresh_prefix_with_stale_tail(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _CLEAN)  # "greet alice.\ngreet bob."
    assert len(await _tokens(client)) > 0
    await _change(client, _PARTIAL_AFTER, version=2)  # "greet alicia.\ngreet 1."
    decoded = _decode(await _tokens(client))
    # The fresh prefix repaints line 0: the `alicia` name token is length 6 (current text), not the
    # stale `alice` length 5 -- proof the prefix region is served fresh, not whole-document stale.
    line0 = [seg for seg in decoded if seg[0] == 0]
    assert any(length == 6 for _line, _char, length, *_rest in line0)
    # The stale tail past the prefix boundary is still merged in: line 1 keeps its last-good tokens.
    assert any(line == 1 for line, *_rest in decoded)


@pytest.mark.asyncio
async def test_semantic_tokens_range_on_partial_state(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _CLEAN)
    await _change(client, _PARTIAL_AFTER, version=2)
    full = _decode(await _tokens(client))
    # A range confined to the fresh prefix (line 0) returns a non-empty, line-0-only subset.
    prefix_rng = t.Range(start=t.Position(line=0, character=0), end=t.Position(line=0, character=13))
    prefix = _decode(await _range_tokens(client, prefix_rng))
    assert len(prefix) > 0
    assert all(line == 0 for line, *_rest in prefix)
    # A range on the stale tail (line 1) returns the merged stale tokens.
    tail_rng = t.Range(start=t.Position(line=1, character=0), end=t.Position(line=1, character=10))
    tail = _decode(await _range_tokens(client, tail_rng))
    assert len(tail) > 0
    assert all(line == 1 for line, *_rest in tail)
    assert len(prefix) + len(tail) == len(full)  # the two disjoint ranges partition the served stream
    # A single range straddling the merge boundary (start in the fresh prefix on line 0, end in the
    # stale tail on line 1) returns the union of both -- the boundary is not special-cased.
    span_rng = t.Range(start=t.Position(line=0, character=0), end=t.Position(line=1, character=10))
    span = _decode(await _range_tokens(client, span_rng))
    assert span == prefix + tail


@pytest.mark.asyncio
async def test_document_symbol_served_from_last_good_during_partial(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _SYM)
    await _change(client, _SYM_BROKEN, version=2)  # zero-length prefix: the partial tree has no symbols
    result = await client.text_document_document_symbol_async(
        t.DocumentSymbolParams(text_document=t.TextDocumentIdentifier(uri=_URI))
    )
    assert result is not None
    # The outline keeps the complete last-good symbols rather than blanking to the empty prefix.
    assert {sym.name for sym in result} == {"outer", "alpha"}


@pytest.mark.asyncio
async def test_folding_served_from_last_good_during_partial(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, "/* a\n b */\ngreet alice.")  # comment fold on lines 0-1
    await _change(client, "/* a\n b */\ngreet 1.", version=2)  # line 2 breaks -> partial analysis
    result = await client.text_document_folding_range_async(
        t.FoldingRangeParams(text_document=t.TextDocumentIdentifier(uri=_URI))
    )
    assert result is not None
    # Folding still serves the last complete tree's comment fold rather than blanking on the partial.
    comment_folds = [r for r in result if r.kind == t.FoldingRangeKind.Comment]
    assert any(r.start_line == 0 and r.end_line == 1 for r in comment_folds)


@pytest.mark.asyncio
async def test_selection_served_from_last_good_during_partial(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _CLEAN)
    await _change(client, _PARTIAL, version=2)  # line 1 breaks -> partial analysis
    result = await client.text_document_selection_range_async(
        t.SelectionRangeParams(
            text_document=t.TextDocumentIdentifier(uri=_URI),
            positions=[t.Position(line=0, character=8)],  # inside `alice`
        )
    )
    assert result is not None
    # Selection still widens against the last complete tree rather than returning nothing.
    head = result[0]
    assert head.range.start.character >= 6
    assert head.parent is not None


@pytest.mark.asyncio
async def test_rename_refused_on_partial_after_good(client: LanguageClient) -> None:
    await client.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client, _SYM)
    await _change(client, _SYM_BROKEN, version=2)
    with pytest.raises(Exception):  # noqa: B017 -- the partial carries a parse error; rename refuses
        await client.text_document_rename_async(
            t.RenameParams(
                text_document=t.TextDocumentIdentifier(uri=_URI),
                position=_line_col(_SYM_BROKEN, _SYM_BROKEN.index("alpha") + 1, t.PositionEncodingKind.Utf32),
                new_name="beta",
            )
        )


@pytest.mark.asyncio
async def test_hard_failure_after_partial_keeps_serving_tokens(client_rule: LanguageClient) -> None:
    await client_rule.initialize_session(_init_params([t.PositionEncodingKind.Utf32]))
    await _open(client_rule, "greet alice. extra")  # `greeting` matches the prefix; ` extra` trails
    served = await _tokens(client_rule)
    assert len(served) > 0
    await _change(client_rule, "xyz", version=2)  # hard failure: no prefix, so served tokens stay put
    assert await _tokens(client_rule) == served


def test_create_server_reads_start_rule_from_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    # The server takes its start rule from the engine, so the formatting parses and the analysis
    # parses can never disagree on it.
    engine = AnalysisEngine.from_paths(Path(_GRAMMAR), Path(_LSP), start_rule="greeting")
    server = create_server(engine, None, RendererConfig(max_width=80, indent_width=2))
    assert server._start_rule == "greeting"
    monkeypatch.setattr(server, "_encoding", lambda: PositionEncoding.UTF32)
    edits, logs = server._format_blocking("greet alice.")
    # Formatting parses with the engine's start rule, so a bare greeting formats without error.
    assert edits is not None
    assert not any(level == t.MessageType.Error for level, _ in logs)
