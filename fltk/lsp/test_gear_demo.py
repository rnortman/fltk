"""Tests for the committed ``gear`` demo language and its resolver (``examples/gear``).

The gear artifacts live outside the ``fltk`` package (they are consumer-style example files),
so this suite skips at module level when ``examples/gear`` is absent -- e.g. a test run against
an installed distribution, whose wheel ships the colocated tests but not ``examples/``.

Coverage: the grammar + ``.fltklsp`` + ``.fltkfmt`` load cleanly; the sample project parses; the
requested highlight categories all appear over ``main.gear``; formatting is idempotent; and the
gear resolver resolves an imported name and an aliased import to ``lib/shapes.gear`` via a real
``ProjectHost`` over the sample project.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

_GEAR = Path(__file__).resolve().parents[2] / "examples" / "gear"

if not _GEAR.is_dir():  # pragma: no cover - exercised only in an installed-distribution run
    pytest.skip("examples/gear is not present (installed distribution)", allow_module_level=True)

from pygls import uris  # noqa: E402 -- after the module-level skip guard

from fltk import plumbing  # noqa: E402
from fltk.lsp.conftest import nth_offset  # noqa: E402
from fltk.lsp.engine import AnalysisEngine  # noqa: E402
from fltk.lsp.project import ProjectHost, ProjectNavigator  # noqa: E402
from fltk.lsp.resolver import Resolver, load_resolver  # noqa: E402
from fltk.unparse.renderer import RendererConfig  # noqa: E402

_GRAMMAR = _GEAR / "gear.fltkg"
_LSP = _GEAR / "gear.fltklsp"
_FMT = _GEAR / "gear.fltkfmt"
_RESOLVER_SPEC = f"{_GEAR / 'gear_resolver.py'}:create_resolver"
_SAMPLE = _GEAR / "sample"
_MAIN = _SAMPLE / "main.gear"
_SHAPES = _SAMPLE / "lib" / "shapes.gear"


def _engine() -> AnalysisEngine:
    return AnalysisEngine.from_paths(_GRAMMAR, _LSP)


def _gear_formatter() -> Callable[[str], str]:
    """Build the gear format pipeline once and return a ``text -> formatted text`` callable.

    The callable parses its input (asserting success), unparses, and renders at the gear demo's
    width/indent -- the parse->unparse->render sequence every formatting test needs.
    """
    engine = _engine()
    config = plumbing.parse_format_config_file(_FMT)
    grammar = engine.source_grammar
    parser = plumbing.generate_parser(grammar)
    unparser = plumbing.generate_unparser(grammar, parser.cst_module_name, config)
    renderer = RendererConfig(max_width=80, indent_width=4)

    def render(text: str) -> str:
        parsed = plumbing.parse_text(parser, text, engine.start_rule)
        assert parsed.success
        doc = plumbing.unparse_cst(unparser, parsed.cst, text, engine.start_rule)
        return plumbing.render_doc(doc, renderer)

    return render


def test_engine_and_format_config_load_cleanly() -> None:
    engine = _engine()
    # Loading the .fltklsp validates every anchor against the grammar; a typo would raise here.
    assert engine.start_rule is None
    config = plumbing.parse_format_config_file(_FMT)
    assert config is not None


def test_sample_project_parses() -> None:
    engine = _engine()
    for path in (_MAIN, _SHAPES):
        analysis = engine.analyze(path.read_text())
        assert analysis.error is None, f"{path.name} failed to parse: {analysis.error}"
        assert analysis.symbols is not None


def test_highlight_classes_cover_requested_categories() -> None:
    engine = _engine()
    analysis = engine.analyze(_MAIN.read_text())
    assert analysis.tokens is not None
    present = {token.token_type for token in analysis.tokens}
    # Comments/trivia, strings, numbers, keywords, operators, types, and (via const) constants
    # must all be distinctly classifiable over the sample.
    required = {"comment", "string", "number", "keyword", "operator", "type", "constant"}
    assert required <= present, f"missing highlight classes: {required - present}"


def test_formatting_is_idempotent() -> None:
    render = _gear_formatter()
    once = render(_MAIN.read_text())
    # render() reparses its input and asserts success, so this second call also confirms the
    # formatted output itself reparses (the server's verify-reparse guard).
    twice = render(once)
    assert once == twice


def test_formatting_preserves_blank_lines_between_items() -> None:
    """Formatting main.gear keeps the blank lines between top-level items.

    gear's ``.fltkfmt`` sets ``preserve_blanks: 1`` before ``trivia_preserve`` (so config parsing
    must not let the later directive discard it), and its grammar wraps whitespace in a named
    ``ws`` trivia rule (so blank-line detection must count newlines inside node-wrapped
    whitespace). The formatted output must keep one blank line before each item that had one in
    source, and keep the leading ``// gear`` comment.
    """
    output = _gear_formatter()(_MAIN.read_text())

    # Each of these top-level items is preceded by a blank line in the source; that blank must survive.
    for marker in ("shape Wheel {", "const SPOKES", "fn rim_area", "fn total_area"):
        assert f"\n\n{marker}" in output, f"blank line before {marker!r} was collapsed:\n{output}"
    # The leading comment is preserved (trivia_preserve: LineComment).
    assert output.lstrip().startswith("// gear"), f"leading comment lost:\n{output}"


def test_gear_resolver_loads_as_valid_resolver() -> None:
    resolver = load_resolver(_RESOLVER_SPEC)
    assert isinstance(resolver, Resolver)
    assert resolver.file_suffixes == (".gear",)


def _navigator() -> tuple[ProjectNavigator, ProjectHost, str, str]:
    engine = _engine()
    resolver = load_resolver(_RESOLVER_SPEC)
    root = _SAMPLE.resolve()
    host = ProjectHost(engine, resolver, root_path=root, open_docs={})
    navigator = ProjectNavigator(host, resolver)
    main_uri = uris.from_fs_path(str(root / "main.gear"))
    shapes_uri = uris.from_fs_path(str(root / "lib" / "shapes.gear"))
    assert main_uri is not None and shapes_uri is not None
    return navigator, host, main_uri, shapes_uri


def test_resolver_resolves_imported_name_across_files() -> None:
    navigator, host, main_uri, shapes_uri = _navigator()
    main_doc = host.document(main_uri)
    shapes_doc = host.document(shapes_uri)
    assert main_doc is not None and shapes_doc is not None

    # The field type `hub: Circle` (second `Circle`; the first is the import binding).
    offset = nth_offset(main_doc.text, "Circle", 1)
    target = navigator.definition(main_doc, offset + 1)
    assert target is not None
    assert target.uri == shapes_uri
    assert shapes_doc.text[target.name_start : target.name_end] == "Circle"


def test_resolver_resolves_alias_to_original_definition() -> None:
    navigator, host, main_uri, shapes_uri = _navigator()
    main_doc = host.document(main_uri)
    shapes_doc = host.document(shapes_uri)
    assert main_doc is not None and shapes_doc is not None

    # `Box` is the alias of `Square`; using it as a field type must land on `Square`'s definition.
    offset = nth_offset(main_doc.text, "Box", 1)  # 0 = `Square as Box`, 1 = `frame: Box`
    target = navigator.definition(main_doc, offset + 1)
    assert target is not None
    assert target.uri == shapes_uri
    assert shapes_doc.text[target.name_start : target.name_end] == "Square"


def test_resolver_find_references_spans_files() -> None:
    navigator, host, main_uri, shapes_uri = _navigator()
    shapes_doc = host.document(shapes_uri)
    assert shapes_doc is not None

    offset = shapes_doc.text.index("Circle")
    occurrences = navigator.references(shapes_doc, offset + 1, include_declaration=True)
    assert occurrences is not None
    uris_hit = {uri for uri, _start, _end in occurrences}
    assert shapes_uri in uris_hit  # the declaration
    assert main_uri in uris_hit  # the import binding and the field type in main.gear
    # Every reported occurrence is the identifier `Circle`.
    for uri, start, end in occurrences:
        if uri == shapes_uri:
            text = shapes_doc.text
        else:
            other = host.document(uri)
            assert other is not None
            text = other.text
        assert text[start:end] == "Circle"
