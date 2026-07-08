"""End-to-end cross-file navigation tests for ``fltk-lsp --resolver`` over the ``gear`` demo.

Each test spawns ``python -m fltk.lsp.server_cli`` against the committed gear language and the gear
resolver, with ``root_uri`` pointing at ``examples/gear/sample``, and drives it through a real LSP
client (pytest-lsp). These are the suite's first multi-URI scenarios: definition/references that
cross file boundaries, an unsaved-buffer target, the rename refusal guard, and a resolver that
always raises (degradation policy). A parallel resolver-free run pins that behavior is unchanged
without ``--resolver``.

The gear artifacts live outside the ``fltk`` package, so this suite skips at module level when
``examples/gear`` is absent (an installed-distribution run whose wheel omits ``examples/``).
"""

from __future__ import annotations

import contextlib
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

_GEAR = Path(__file__).resolve().parents[2] / "examples" / "gear"

if not _GEAR.is_dir():  # pragma: no cover - exercised only in an installed-distribution run
    pytest.skip("examples/gear is not present (installed distribution)", allow_module_level=True)

import pytest_lsp  # noqa: E402 -- after the module-level skip guard
from lsprotocol import types as t  # noqa: E402
from pygls import uris  # noqa: E402
from pytest_lsp import ClientServerConfig, LanguageClient  # noqa: E402

from fltk.lsp.conftest import nth_offset  # noqa: E402
from fltk.lsp.positions import LineIndex, PositionEncoding  # noqa: E402

_DATA = Path(__file__).parent / "test_data"
_GRAMMAR = str(_GEAR / "gear.fltkg")
_LSP = str(_GEAR / "gear.fltklsp")
_FMT = str(_GEAR / "gear.fltkfmt")
_RESOLVER = f"{_GEAR / 'gear_resolver.py'}:create_resolver"
_RAISING_RESOLVER = f"{_DATA / 'raising_resolver.py'}:create_resolver"


def _uri(path: Path) -> str:
    result = uris.from_fs_path(str(path))
    assert result is not None
    return result


_SAMPLE = (_GEAR / "sample").resolve()
_MAIN_PATH = _SAMPLE / "main.gear"
_SHAPES_PATH = _SAMPLE / "lib" / "shapes.gear"
_MAIN_URI = _uri(_MAIN_PATH)
_SHAPES_URI = _uri(_SHAPES_PATH)
_ROOT_URI = _uri(_SAMPLE)

_MAIN_TEXT = _MAIN_PATH.read_text()
_SHAPES_TEXT = _SHAPES_PATH.read_text()
_PUBLISH = t.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS


def _base_command(*extra: str) -> list[str]:
    return [
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
        "4",
        *extra,
    ]


_COMMAND = _base_command("--resolver", _RESOLVER)
_COMMAND_RAISING = _base_command("--resolver", _RAISING_RESOLVER)
_COMMAND_NO_RESOLVER = _base_command()


def _init_params() -> t.InitializeParams:
    return t.InitializeParams(
        capabilities=t.ClientCapabilities(
            general=t.GeneralClientCapabilities(position_encodings=[t.PositionEncodingKind.Utf32])
        ),
        root_uri=_ROOT_URI,
    )


def _pos(text: str, offset: int) -> t.Position:
    line, character = LineIndex(text).offset_to_position(offset, PositionEncoding.UTF32)
    return t.Position(line=line, character=character)


async def _open(client: LanguageClient, uri: str, text: str, *, version: int = 1) -> None:
    client.text_document_did_open(
        t.DidOpenTextDocumentParams(
            text_document=t.TextDocumentItem(uri=uri, language_id="gear", version=version, text=text)
        )
    )
    await client.wait_for_notification(_PUBLISH)


async def _change(client: LanguageClient, uri: str, text: str, *, version: int) -> None:
    client.text_document_did_change(
        t.DidChangeTextDocumentParams(
            text_document=t.VersionedTextDocumentIdentifier(uri=uri, version=version),
            content_changes=[t.TextDocumentContentChangeWholeDocument(text=text)],
        )
    )
    await client.wait_for_notification(_PUBLISH)


async def _definition(
    client: LanguageClient, uri: str, position: t.Position
) -> t.Location | Sequence[t.Location] | Sequence[t.LocationLink] | None:
    return await client.text_document_definition_async(
        t.DefinitionParams(text_document=t.TextDocumentIdentifier(uri=uri), position=position)
    )


async def _references(
    client: LanguageClient, uri: str, position: t.Position, *, include_declaration: bool
) -> Sequence[t.Location] | None:
    return await client.text_document_references_async(
        t.ReferenceParams(
            text_document=t.TextDocumentIdentifier(uri=uri),
            position=position,
            context=t.ReferenceContext(include_declaration=include_declaration),
        )
    )


async def _rename(client: LanguageClient, uri: str, position: t.Position, new_name: str) -> t.WorkspaceEdit | None:
    return await client.text_document_rename_async(
        t.RenameParams(text_document=t.TextDocumentIdentifier(uri=uri), position=position, new_name=new_name)
    )


@pytest_lsp.fixture(config=ClientServerConfig(server_command=_COMMAND))
async def client(lsp_client: LanguageClient):
    yield
    with contextlib.suppress(Exception):
        await lsp_client.shutdown_session()


@pytest_lsp.fixture(config=ClientServerConfig(server_command=_COMMAND_RAISING))
async def raising_client(lsp_client: LanguageClient):
    yield
    with contextlib.suppress(Exception):
        await lsp_client.shutdown_session()


@pytest_lsp.fixture(config=ClientServerConfig(server_command=_COMMAND_NO_RESOLVER))
async def plain_client(lsp_client: LanguageClient):
    yield
    with contextlib.suppress(Exception):
        await lsp_client.shutdown_session()


@pytest.mark.asyncio
async def test_definition_crosses_into_unopened_file(client: LanguageClient) -> None:
    # Go-to-def on a field type in main.gear lands on the shape's definition in lib/shapes.gear --
    # which the client never opened, so the server read it from disk via the workspace root.
    await client.initialize_session(_init_params())
    await _open(client, _MAIN_URI, _MAIN_TEXT)
    # `hub: Circle` -- the field-type reference (occurrence 1; occurrence 0 is the import binding).
    result = await _definition(client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Circle", 1) + 1))
    assert isinstance(result, t.Location)
    assert result.uri == _SHAPES_URI
    def_at = _SHAPES_TEXT.index("Circle")
    assert result.range.start == _pos(_SHAPES_TEXT, def_at)
    assert result.range.end == _pos(_SHAPES_TEXT, def_at + len("Circle"))


@pytest.mark.asyncio
async def test_definition_through_alias(client: LanguageClient) -> None:
    # `frame: Box` -- `Box` is the alias of `Square`; navigation must land on `Square`'s definition.
    await client.initialize_session(_init_params())
    await _open(client, _MAIN_URI, _MAIN_TEXT)
    result = await _definition(client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Box", 1) + 1))
    assert isinstance(result, t.Location)
    assert result.uri == _SHAPES_URI
    def_at = _SHAPES_TEXT.index("Square")
    assert result.range.start == _pos(_SHAPES_TEXT, def_at)


@pytest.mark.asyncio
async def test_references_span_into_unopened_file(client: LanguageClient) -> None:
    # Find-refs on the shape def in lib/shapes.gear lists occurrences in main.gear (import binding +
    # field type) though main.gear was never opened this session.
    await client.initialize_session(_init_params())
    await _open(client, _SHAPES_URI, _SHAPES_TEXT)
    pos = _pos(_SHAPES_TEXT, _SHAPES_TEXT.index("Circle") + 1)

    with_decl = await _references(client, _SHAPES_URI, pos, include_declaration=True)
    assert with_decl is not None
    by_uri = {loc.uri for loc in with_decl}
    assert _SHAPES_URI in by_uri  # the declaration
    assert _MAIN_URI in by_uri  # cross-file uses
    assert sum(loc.uri == _MAIN_URI for loc in with_decl) == 2  # import binding + field type

    without_decl = await _references(client, _SHAPES_URI, pos, include_declaration=False)
    assert without_decl is not None
    # The declaration span in shapes.gear is dropped; only the main.gear uses remain.
    assert all(loc.uri == _MAIN_URI for loc in without_decl)
    assert len(without_decl) == 2


@pytest.mark.asyncio
async def test_definition_follows_unsaved_buffer_edit(client: LanguageClient) -> None:
    # An unsaved edit to the target file participates: after inserting a blank line before the
    # `Circle` shape in the open shapes buffer, definition from main.gear points at the new line.
    await client.initialize_session(_init_params())
    await _open(client, _MAIN_URI, _MAIN_TEXT)
    await _open(client, _SHAPES_URI, _SHAPES_TEXT)
    edited = "\n" + _SHAPES_TEXT  # shift everything down one line
    await _change(client, _SHAPES_URI, edited, version=2)

    result = await _definition(client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Circle", 1) + 1))
    assert isinstance(result, t.Location)
    assert result.uri == _SHAPES_URI
    def_at = edited.index("Circle")
    assert result.range.start == _pos(edited, def_at)  # moved to line 1


@pytest.mark.asyncio
async def test_rename_exported_shape_is_refused(client: LanguageClient) -> None:
    # Renaming a shape other files reference must refuse (same-file rename would corrupt the project).
    await client.initialize_session(_init_params())
    await _open(client, _SHAPES_URI, _SHAPES_TEXT)
    with pytest.raises(Exception, match="other files"):
        await _rename(client, _SHAPES_URI, _pos(_SHAPES_TEXT, _SHAPES_TEXT.index("Circle") + 1), "Ring")


@pytest.mark.asyncio
async def test_rename_import_binding_is_refused(client: LanguageClient) -> None:
    # Renaming an import binding locally would detach it from what it imports: refuse.
    await client.initialize_session(_init_params())
    await _open(client, _MAIN_URI, _MAIN_TEXT)
    with pytest.raises(Exception, match="import binding"):
        await _rename(client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Circle", 0) + 1), "Ring")


@pytest.mark.asyncio
async def test_rename_local_binding_succeeds(client: LanguageClient) -> None:
    # A purely local binding (a `let`) has no cross-file references: rename proceeds as before.
    await client.initialize_session(_init_params())
    await _open(client, _MAIN_URI, _MAIN_TEXT)
    result = await _rename(client, _MAIN_URI, _pos(_MAIN_TEXT, _MAIN_TEXT.index("let r") + 4), "radius")
    assert result is not None
    changes = result.changes or {}
    edits = changes.get(_MAIN_URI, [])
    assert len(edits) >= 2  # `let r` plus its uses in the expression
    assert {e.new_text for e in edits} == {"radius"}


@pytest.mark.asyncio
async def test_raising_resolver_degrades_references_but_fails_rename_closed(raising_client: LanguageClient) -> None:
    # A resolver that always raises: read-only find-refs degrades to the same-file answer, while the
    # rename guard fails closed (refuses) rather than silently reopening the cross-file hazard.
    await raising_client.initialize_session(_init_params())
    await _open(raising_client, _MAIN_URI, _MAIN_TEXT)

    refs = await _references(
        raising_client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Circle", 1) + 1), include_declaration=True
    )
    assert refs is not None  # degraded to same-file, not an error
    assert all(loc.uri == _MAIN_URI for loc in refs)  # same-file only

    # Definition degrades the same way: `hub: Circle` falls back to the local import binding.
    defn = await _definition(raising_client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Circle", 1) + 1))
    assert isinstance(defn, t.Location)
    assert defn.uri == _MAIN_URI  # same-file fallback, never crossing into shapes.gear
    assert defn.range.start == _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Circle", 0))

    with pytest.raises(Exception, match="could not verify"):
        await _rename(raising_client, _MAIN_URI, _pos(_MAIN_TEXT, _MAIN_TEXT.index("Wheel") + 1), "Gear")


@pytest.mark.asyncio
async def test_definition_through_prealias_name(client: LanguageClient) -> None:
    # Cursor on `Square` in the `use` statement itself (the pre-alias import name, not its `Box`
    # alias or a usage site) also navigates to `Square`'s definition.
    await client.initialize_session(_init_params())
    await _open(client, _MAIN_URI, _MAIN_TEXT)
    result = await _definition(client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Square", 0) + 1))
    assert isinstance(result, t.Location)
    assert result.uri == _SHAPES_URI
    def_at = _SHAPES_TEXT.index("Square")
    assert result.range.start == _pos(_SHAPES_TEXT, def_at)


@pytest.mark.asyncio
async def test_definition_from_last_good_after_break(client: LanguageClient) -> None:
    # The requesting document is broken by a syntax error; cross-file definition must still resolve,
    # served from the last complete analysis (the `_GoodAnalysis.text`-sourced ResolvedDocument),
    # never pairing the live broken buffer with a stale tree.
    await client.initialize_session(_init_params())
    await _open(client, _MAIN_URI, _MAIN_TEXT)
    await _change(client, _MAIN_URI, _MAIN_TEXT + "\nshape {", version=2)  # unterminated -> parse error
    result = await _definition(client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Circle", 1) + 1))
    assert isinstance(result, t.Location)
    assert result.uri == _SHAPES_URI
    def_at = _SHAPES_TEXT.index("Circle")
    assert result.range.start == _pos(_SHAPES_TEXT, def_at)


@pytest.mark.asyncio
async def test_definition_via_workspace_folders(client: LanguageClient) -> None:
    # A real editor opening a folder sends `workspace_folders`, not `root_uri`; the workspace root
    # must resolve from that branch too.
    params = t.InitializeParams(
        capabilities=t.ClientCapabilities(
            general=t.GeneralClientCapabilities(position_encodings=[t.PositionEncodingKind.Utf32])
        ),
        workspace_folders=[t.WorkspaceFolder(uri=_ROOT_URI, name="sample")],
    )
    await client.initialize_session(params)
    await _open(client, _MAIN_URI, _MAIN_TEXT)
    result = await _definition(client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Circle", 1) + 1))
    assert isinstance(result, t.Location)
    assert result.uri == _SHAPES_URI


@pytest.mark.asyncio
async def test_no_resolver_definition_stays_same_file(plain_client: LanguageClient) -> None:
    # Without --resolver, definition stays same-file-only: `hub: Circle` resolves to the local
    # import binding in main.gear, never crossing into shapes.gear.
    await plain_client.initialize_session(_init_params())
    await _open(plain_client, _MAIN_URI, _MAIN_TEXT)
    result = await _definition(plain_client, _MAIN_URI, _pos(_MAIN_TEXT, nth_offset(_MAIN_TEXT, "Circle", 1) + 1))
    assert isinstance(result, t.Location)
    assert result.uri == _MAIN_URI  # stays in the requesting file
    binding_at = nth_offset(_MAIN_TEXT, "Circle", 0)  # the import binding
    assert result.range.start == _pos(_MAIN_TEXT, binding_at)


@pytest.mark.asyncio
async def test_no_resolver_rename_exported_shape_succeeds(plain_client: LanguageClient) -> None:
    # Without a resolver the cross-file guard is inert: a same-file rename of a shape proceeds (the
    # same-file-only behavior), proving the guard is resolver-gated.
    await plain_client.initialize_session(_init_params())
    await _open(plain_client, _MAIN_URI, _MAIN_TEXT)
    result = await _rename(plain_client, _MAIN_URI, _pos(_MAIN_TEXT, _MAIN_TEXT.index("Wheel") + 1), "Gear")
    assert result is not None
    edits = (result.changes or {}).get(_MAIN_URI, [])
    assert len(edits) >= 1
    assert {e.new_text for e in edits} == {"Gear"}
