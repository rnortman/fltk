"""Error and atomicity contracts of `fltk.unparse.genunparser`'s file-parsing helpers.

Both helpers are library functions with in- and out-of-tree callers, and both fail in ways a
caller has to distinguish: a path that is not there, a file that does not parse, and (for the
grammar) a text/GSM pair that must describe the same bytes.  None of that is observable from
the success path the rest of the suite exercises.
"""

from __future__ import annotations

import pathlib

import pytest
import typer

from fltk.unparse import fmt_config, genunparser

_GRAMMAR = "word := value:/[a-z]+/ ;\n_trivia := /\\s+/ ;\n"
_FORMAT_CONFIG = "ws_allowed: bsp;\nws_required: nbsp;\n"


# ---------------------------------------------------------------------------
# parse_grammar_file
# ---------------------------------------------------------------------------


def test_parse_grammar_file_returns_the_text_it_parsed(tmp_path: pathlib.Path) -> None:
    """One read: the returned text is the bytes the returned GSM describes.

    A caller resolving spans against the text would otherwise be reading a second, possibly
    newer, revision of the file with no error anywhere.
    """
    grammar_path = tmp_path / "word.fltkg"
    grammar_path.write_text(_GRAMMAR)

    grammar, text = genunparser.parse_grammar_file(grammar_path)

    assert text == _GRAMMAR
    assert [rule.name for rule in grammar.rules] == ["word", "_trivia"]


def test_parse_grammar_file_missing_path_raises_file_not_found(tmp_path: pathlib.Path) -> None:
    missing = tmp_path / "absent.fltkg"

    with pytest.raises(FileNotFoundError) as excinfo:
        genunparser.parse_grammar_file(missing)

    assert str(missing) in str(excinfo.value)


def test_parse_grammar_file_unparseable_grammar_exits(tmp_path: pathlib.Path) -> None:
    """A malformed grammar takes the shared generator path's CLI error contract."""
    grammar_path = tmp_path / "broken.fltkg"
    grammar_path.write_text("word := ;;; not a grammar\n")

    with pytest.raises(typer.Exit):
        genunparser.parse_grammar_file(grammar_path)


# ---------------------------------------------------------------------------
# parse_format_file
# ---------------------------------------------------------------------------


def test_parse_format_file_returns_cst_and_config(tmp_path: pathlib.Path) -> None:
    format_path = tmp_path / "word.fltkfmt"
    format_path.write_text(_FORMAT_CONFIG)

    format_cst, config = genunparser.parse_format_file(format_path)

    assert format_cst is not None
    assert isinstance(config, fmt_config.FormatterConfig)


def test_parse_format_file_missing_path_raises_file_not_found(tmp_path: pathlib.Path) -> None:
    """The diagnostic names the file: a bare read_text() traceback does not say what it was."""
    missing = tmp_path / "absent.fltkfmt"

    with pytest.raises(FileNotFoundError) as excinfo:
        genunparser.parse_format_file(missing)

    assert "Format file" in str(excinfo.value)
    assert str(missing) in str(excinfo.value)


def test_parse_format_file_unparseable_raises_runtime_error(tmp_path: pathlib.Path) -> None:
    format_path = tmp_path / "broken.fltkfmt"
    format_path.write_text("this is not a format spec {{{\n")

    with pytest.raises(RuntimeError) as excinfo:
        genunparser.parse_format_file(format_path)

    assert "Failed to parse format file" in str(excinfo.value)
