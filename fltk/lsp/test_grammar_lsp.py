"""Tests for the ``fltk-grammar-lsp`` entry point and the packaged built-in-language specs.

Covers the registry (every entry's grammar/spec/format files load), per-language highlighting,
``.fltkg`` def/ref navigation, formatting round-trips on real in-tree files, the CLI's argument
handling and path resolution, and one end-to-end LSP session over the real protocol.
"""

from __future__ import annotations

import contextlib
import sys

import pytest
import pytest_lsp
from lsprotocol import types as t
from pytest_lsp import ClientServerConfig, LanguageClient
from typer.testing import CliRunner

from fltk import plumbing
from fltk.lsp import grammar_cli
from fltk.lsp.conftest import token_type_at as tt
from fltk.lsp.engine import AnalysisEngine
from fltk.lsp.grammar_cli import BUILTIN_LANGUAGES, resolve_paths
from fltk.unparse.renderer import RendererConfig

runner = CliRunner()

# For the formatting round-trip: each language's samples are every in-tree file of that language,
# so the registry attribute to collect for language X is X's own file kind across all registry
# entries. None is required to already be format-clean.
_SAMPLE_ATTR: dict[str, str] = {"fltkg": "grammar", "fltkfmt": "fmt", "fltklsp": "lsp"}


def _engine(language_id: str) -> AnalysisEngine:
    builtin = BUILTIN_LANGUAGES[language_id]
    with contextlib.ExitStack() as stack:
        grammar, lsp, _fmt = resolve_paths(builtin, stack)
        return AnalysisEngine.from_paths(grammar, lsp)


# --- 1. Registry integrity ------------------------------------------------------------------------


@pytest.mark.parametrize("language_id", list(BUILTIN_LANGUAGES))
def test_registry_entry_resources_load(language_id: str) -> None:
    builtin = BUILTIN_LANGUAGES[language_id]
    with contextlib.ExitStack() as stack:
        grammar, lsp, fmt = resolve_paths(builtin, stack)
        assert grammar.exists()
        # The grammar + .fltklsp spec load and resolve against each other.
        AnalysisEngine.from_paths(grammar, lsp)
        # The .fltkfmt config parses.
        assert fmt is not None
        plumbing.parse_format_config_file(fmt)


def test_language_enum_matches_registry() -> None:
    assert {member.value for member in grammar_cli.Language} == set(BUILTIN_LANGUAGES)


# --- 2. Highlight smoke per language --------------------------------------------------------------


def test_highlight_fltkg() -> None:
    engine = _engine("fltkg")
    text = 'foo := name:bar , "lit" | baz ;\nbar := /[a-z]+/ ;\nbaz := "x" ;\n'
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens is not None
    # A rule name is a definition -> `type`.
    assert tt(result.tokens, text, "foo") == "type"
    # An item capture label -> `label`.
    assert tt(result.tokens, text, "name") == "label"
    # A quoted literal -> `string`.
    assert tt(result.tokens, text, '"lit"') == "string"
    # A regex body gets the distinct non-legend paint (`macro`, since the legend has no `regexp`).
    assert tt(result.tokens, text, "[a-z]+") == "macro"
    # Operators from the global operator group: `:=` and the alternation `|`.
    assert tt(result.tokens, text, ":=") == "operator"
    assert tt(result.tokens, text, "|") == "operator"
    # Punctuation from the global punctuation group: the `,` separator and the `;` terminator.
    assert tt(result.tokens, text, ",") == "punctuation"
    assert tt(result.tokens, text, ";") == "punctuation"


def test_highlight_fltkfmt() -> None:
    engine = _engine("fltkfmt")
    text = 'rule foo {\n  after "x" { hard; }\n}\npreserve_blanks: 3;\n'
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens is not None
    # The configured rule name -> `type`; statement keywords -> `keyword`.
    assert tt(result.tokens, text, "foo") == "type"
    assert tt(result.tokens, text, "after") == "keyword"
    # A quoted anchor literal -> `string`; an integer count -> `number`.
    assert tt(result.tokens, text, '"x"') == "string"
    assert tt(result.tokens, text, "3") == "number"


def test_highlight_fltklsp() -> None:
    engine = _engine("fltklsp")
    text = 'rule foo {\n  scope "x": keyword;\n}\n'
    result = engine.highlight(text)
    assert result.error is None
    assert result.tokens is not None
    # The addressed rule name -> `type` (rule_config def); the `scope` keyword -> `keyword`.
    assert tt(result.tokens, text, "foo") == "type"
    assert tt(result.tokens, text, "scope") == "keyword"
    assert tt(result.tokens, text, '"x"') == "string"


# --- 3. fegen def/ref semantics -------------------------------------------------------------------


def test_fltkg_reference_resolves_to_rule_definition() -> None:
    engine = _engine("fltkg")
    text = "alpha := beta ;\nbeta := /x/ ;\n"
    analysis = engine.analyze(text)
    assert analysis.error is None
    assert analysis.symbols is not None
    # Both rule names are definitions of kind `type`.
    definitions = {(s.name, s.kind) for s in analysis.symbols.symbols}
    assert ("alpha", ("type",)) in definitions
    assert ("beta", ("type",)) in definitions
    # The `beta` invocation in `alpha`'s body is a reference resolving to `beta`'s definition.
    resolved = [r for r in analysis.symbols.references if r.symbol is not None]
    assert any(r.name == "beta" and r.symbol is not None and r.symbol.kind == ("type",) for r in resolved)


# --- 4. Formatting round-trip on real files -------------------------------------------------------


@pytest.mark.parametrize("language_id", list(BUILTIN_LANGUAGES))
def test_formatting_roundtrip_on_real_files(language_id: str) -> None:
    builtin = BUILTIN_LANGUAGES[language_id]
    sample_attr = _SAMPLE_ATTR[language_id]
    with contextlib.ExitStack() as stack:
        grammar_path, _lsp, fmt_path = resolve_paths(builtin, stack)
        grammar = plumbing.parse_grammar_file(grammar_path)
        assert fmt_path is not None
        cfg = plumbing.parse_format_config_file(fmt_path)
        # Parser/unparser depend only on grammar+cfg, so generate them once and reuse across every
        # sample and both round-trip passes rather than regenerating per format call.
        parser = plumbing.generate_parser(grammar)
        unparser = plumbing.generate_unparser(grammar, parser.cst_module_name, cfg)

        def _format(text: str) -> str:
            parsed = plumbing.parse_text(parser, text)
            assert parsed.success, parsed.error_message
            doc = plumbing.unparse_cst(unparser, parsed.cst, text)
            return plumbing.render_doc(doc, RendererConfig(max_width=80, indent_width=2))

        # The samples are every in-tree file of this language, drawn from the registry itself:
        # e.g. for `fltkg`, every entry's `.fltkg` grammar; for `fltkfmt`, every entry's `.fltkfmt`.
        for entry in BUILTIN_LANGUAGES.values():
            grammar_p, lsp_p, fmt_p = resolve_paths(entry, stack)
            path = {"grammar": grammar_p, "lsp": lsp_p, "fmt": fmt_p}[sample_attr]
            assert path is not None, (entry, sample_attr)
            text = path.read_text()
            once = _format(text)
            # The formatted output reparses under the same grammar ...
            assert plumbing.parse_text(parser, once).success, path
            # ... and formatting is idempotent (format of a formatted document is unchanged).
            twice = _format(once)
            assert once == twice, path


# --- 5. CLI behavior ------------------------------------------------------------------------------


def test_cli_unknown_language_exits_nonzero_and_lists_ids() -> None:
    result = runner.invoke(grammar_cli.app, ["not-a-language"])
    assert result.exit_code != 0
    # Typer's invalid-choice error names every valid id.
    for language_id in BUILTIN_LANGUAGES:
        assert language_id in result.output


def test_cli_help_works() -> None:
    result = runner.invoke(grammar_cli.app, ["--help"])
    assert result.exit_code == 0


def test_resolve_paths_returns_existing_files_for_every_language() -> None:
    for builtin in BUILTIN_LANGUAGES.values():
        with contextlib.ExitStack() as stack:
            grammar, lsp, fmt = resolve_paths(builtin, stack)
            assert grammar.exists()
            assert lsp is not None and lsp.exists()
            assert fmt is not None and fmt.exists()


# --- 6. One end-to-end LSP session ----------------------------------------------------------------

_URI = "file:///sample.fltkg"
_PUBLISH = t.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS
_SERVER_COMMAND = [sys.executable, "-m", "fltk.lsp.grammar_cli", "fltkg"]


@pytest_lsp.fixture(config=ClientServerConfig(server_command=_SERVER_COMMAND))
async def client(lsp_client: LanguageClient):
    yield
    # Teardown only: a shutdown failure here (server already gone, protocol torn down) must not
    # mask the test's own result, so any exception is swallowed.
    with contextlib.suppress(Exception):
        await lsp_client.shutdown_session()


async def _open(client: LanguageClient, text: str, *, version: int = 1) -> None:
    client.text_document_did_open(
        t.DidOpenTextDocumentParams(
            text_document=t.TextDocumentItem(uri=_URI, language_id="fltkg", version=version, text=text)
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


@pytest.mark.asyncio
async def test_end_to_end_tokens_and_diagnostic(client: LanguageClient) -> None:
    await client.initialize_session(
        t.InitializeParams(
            capabilities=t.ClientCapabilities(
                general=t.GeneralClientCapabilities(position_encodings=[t.PositionEncodingKind.Utf32])
            ),
            root_uri=None,
        )
    )
    # A clean grammar: no diagnostics, and semantic tokens are produced.
    await _open(client, 'rule := name:identifier , ":=" ;\nidentifier := /[a-z]+/ ;\n')
    assert not client.diagnostics[_URI]
    tokens = await client.text_document_semantic_tokens_full_async(
        t.SemanticTokensParams(text_document=t.TextDocumentIdentifier(uri=_URI))
    )
    assert tokens is not None
    assert len(tokens.data) > 0

    # A breaking edit (a number where a term is required) surfaces a diagnostic.
    await _change(client, "rule := 4 ;\n", version=2)
    diagnostics = client.diagnostics[_URI]
    assert len(diagnostics) >= 1
    assert diagnostics[0].severity == t.DiagnosticSeverity.Error
