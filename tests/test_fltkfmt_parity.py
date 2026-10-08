"""Cross-backend formatter parity: the `fltkfmt` binary vs the Python formatter.

`fltkfmt` is the pure-Rust `.fltkg` formatter (parse with the generated Rust parser,
unparse with the Rust unparser baked from `fegen.fltkfmt`, render) built from
`crates/fltkfmt/`. The Python reference is the exact pipeline `fltk/unparse_cli.py`
runs on `fegen.fltkg` + `fegen.fltkfmt` (parse_text -> unparse_cst -> render_doc); the
two must produce byte-identical output at matching `--width`/`--indent`.

This is the strongest guarantee that the standalone pure-Rust formatter matches the
established Python formatter (including trailing-whitespace handling) and guards against
future drift between `fegen.fltkfmt` and the generated Rust `unparser.rs`.

Mirrors `tests/test_rust_unparser_parity_fixture.py`. The binary is a built dependency of
this test, named by `FLTKFMT_BIN`; an absent variable is a hard failure rather than a skip,
so the parity guarantee can never be silently bypassed.
"""

from __future__ import annotations

import functools
import os
import subprocess
from pathlib import Path

import pytest

from fltk import plumbing
from fltk.unparse.renderer import RendererConfig
from tests.unparser_parity import render_config_ids

_REPO_ROOT = Path(__file__).parent.parent
_FEGEN_FLTKG = _REPO_ROOT / "fltk" / "fegen" / "fegen.fltkg"
_FEGEN_FLTKFMT = _REPO_ROOT / "fltk" / "fegen" / "fegen.fltkfmt"

# Corpus: every real `.fltkg` in the tree (the canonical grammars plus the test-data
# grammars). Each is parsed and re-rendered by both backends; pinned explicitly so the
# coverage set is visible and a non-parsing addition can't silently widen it.
# Mirrored by hand in `crates/fltkfmt/tests/cli.rs` (`CORPUS`); additions here must be
# added there too or the Rust idempotency sweep silently stops covering the new grammar.
_CORPUS = [
    _REPO_ROOT / "fltk" / "fegen" / "bootstrap.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "fegen.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "fltk.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "regex.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "test_data" / "collision_fixture.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "test_data" / "nest_boundary_comments.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "test_data" / "phase4_roundtrip.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "test_data" / "poc_grammar.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "test_data" / "rust_parser_fixture.fltkg",
]
_CORPUS_IDS = [p.name for p in _CORPUS]

# Wide (80/2, which is also the CLI default) and narrow (40/4), so the flat-vs-break
# decisions are exercised cross-backend.
_CONFIGS = [(80, 2), (40, 4)]
_CONFIG_IDS = render_config_ids(_CONFIGS)


@functools.cache
def _grammar():
    return plumbing.parse_grammar_file(_FEGEN_FLTKG)


@functools.cache
def _format_config():
    return plumbing.parse_format_config_file(_FEGEN_FLTKFMT)


@functools.cache
def _py_parser_result():
    return plumbing.generate_parser(_grammar(), capture_trivia=True)


@functools.cache
def _py_unparser_result():
    """Python unparser generated from `fegen.fltkfmt` — matches the baked Rust config."""
    parser_result = _py_parser_result()
    return plumbing.generate_unparser(
        parser_result.grammar,
        parser_result.cst_module_name,
        formatter_config=_format_config(),
    )


@functools.cache
def _py_doc(text: str):
    """Parse + unparse depend only on `text`, never on the render config; cache so the
    heavy pure-Python parse/unparse runs once per input instead of once per config."""
    parse_result = plumbing.parse_text(_py_parser_result(), text, rule_name=None)
    assert parse_result.success, f"Python parse failed: {parse_result.error_message}"
    return plumbing.unparse_cst(_py_unparser_result(), parse_result.cst, text, rule_name=None)


def _py_format(text: str, max_width: int, indent_width: int) -> str:
    """Reference output: exactly what `fltk/unparse_cli.py` produces for this input.

    `render_doc` treats the Doc as read-only input, so rendering the cached `_py_doc`
    under multiple configs is safe.
    """
    return plumbing.render_doc(_py_doc(text), RendererConfig(max_width=max_width, indent_width=indent_width))


def _rust_format(binary: Path, source: Path, max_width: int, indent_width: int) -> str:
    """`fltkfmt`'s output for the file `source` at the given width and indent."""
    proc = subprocess.run(  # noqa: S603
        [str(binary), str(source), "-w", str(max_width), "-i", str(indent_width)],
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"[{source.name} w={max_width} i={indent_width}] fltkfmt exited {proc.returncode}: "
        f"{proc.stderr.decode('utf-8', 'replace')}"
    )
    return proc.stdout.decode("utf-8", "replace")


@pytest.fixture(scope="session")
def fltkfmt_binary() -> Path:
    """The standalone `fltkfmt` binary the test target named in `FLTKFMT_BIN`.

    The same variable `crates/fltkfmt/tests/cli.rs` reads. A missing one is a broken target,
    not an environment to fall back from: the parity guarantee must never be silently bypassed.
    """
    prebuilt = os.environ.get("FLTKFMT_BIN")
    assert prebuilt, "FLTKFMT_BIN is not set; the test target must supply the built binary"
    # Resolve so assertion failures name the actual path, not a bare runfiles-relative one.
    binary = Path(prebuilt).resolve()
    assert binary.exists(), f"FLTKFMT_BIN names no file: {prebuilt}"
    return binary


@pytest.mark.parametrize("max_width,indent_width", _CONFIGS, ids=_CONFIG_IDS)
@pytest.mark.parametrize("fltkg", _CORPUS, ids=_CORPUS_IDS)
def test_fltkfmt_matches_python(fltkfmt_binary: Path, fltkg: Path, max_width: int, indent_width: int):
    py_out = _py_format(fltkg.read_text(), max_width, indent_width)
    rust_out = _rust_format(fltkfmt_binary, fltkg, max_width, indent_width)
    assert py_out == rust_out, (
        f"[{fltkg.name} w={max_width} i={indent_width}] formatter output mismatch:\n"
        f"Python: {py_out!r}\nRust:   {rust_out!r}"
    )


# Preserved comments inside a rule's nest, and a multi-line block comment there: every line after
# the comment keeps the nest indent, the comment's own bytes are never re-indented, and the output
# is a fixed point on both backends.
_INLINE_CASES = [
    pytest.param("a := x\n// c\n| y ;\n", "a :=\n  x\n  // c\n  | y ;\n", id="column0_comment"),
    pytest.param("a := x\n// c1\n// c2\n| y ;\n", "a :=\n  x\n  // c1\n  // c2\n  | y ;\n", id="two_column0_comments"),
    pytest.param("a := x\n  // c\n  | y ;\n", "a :=\n  x\n  // c\n  | y ;\n", id="indented_comment"),
    pytest.param("a := x // t\n| y ;\n", "a :=\n  x // t\n  | y ;\n", id="trailing_comment"),
    pytest.param("a := x\n/* l1\n   l2 */\n| y ;\n", "a :=\n  x\n  /* l1\n   l2 */\n  | y ;\n", id="block_comment"),
]


def _assert_layout(binary: Path, tmp_path: Path, source: Path, expected: str) -> None:
    """Both backends format `source` to `expected` at 80/2, and `expected` is a fixed point on both."""
    text = source.read_text()
    formatted = tmp_path / "formatted.fltkg"
    formatted.write_text(expected)
    for out in (_py_format(text, 80, 2), _rust_format(binary, source, 80, 2)):
        assert out == expected
    assert _py_format(expected, 80, 2) == expected
    assert _rust_format(binary, formatted, 80, 2) == expected


@pytest.mark.parametrize(("text", "expected"), _INLINE_CASES)
def test_preserved_comment_layout(fltkfmt_binary: Path, tmp_path: Path, text: str, expected: str):
    source = tmp_path / "input.fltkg"
    source.write_text(text)
    _assert_layout(fltkfmt_binary, tmp_path, source, expected)
    assert _py_format(text, 40, 4) == _rust_format(fltkfmt_binary, source, 40, 4)


_NEST_BOUNDARY_COMMENTS = _REPO_ROOT / "fltk" / "fegen" / "test_data" / "nest_boundary_comments.fltkg"

# A preserved comment in the first or last gap of a nest takes the nest's indent and the gap
# renders the source's whitespace around it and nothing else: a delimiter after an own-line
# comment starts its own line at the enclosing indent, a delimiter the source left on a same-line
# comment's line stays there even when the group breaks (`g`), and a blank line survives.
_NEST_BOUNDARY_EXPECTED = """\
// Comments in the boundary gaps of fegen's two nest regions.
a :=
  (
    // lead
    "x" | "y"
    // trail
  ) ;
b :=
  (
    // one
    // two
    "x"

    // after blank
  ) ;
c :=
  ( // same line
    "x"
  ) ;
d :=
  (
    /* block
     continued */
    "x"
  ) ;
e :=
  // lead after :=
  "x" ;
f := ( "x" /* trail */ ) ;
g :=
  (
    // lead
    "x" | "y" /* trail */ ) ;
"""


def test_nest_boundary_comment_layout(fltkfmt_binary: Path, tmp_path: Path):
    # Parity at 40/4 is `test_fltkfmt_matches_python`'s: the file is in `_CORPUS`.
    _assert_layout(fltkfmt_binary, tmp_path, _NEST_BOUNDARY_COMMENTS, _NEST_BOUNDARY_EXPECTED)
