"""Cross-backend formatter parity: the `fltkfmt` binary vs the Python formatter.

`fltkfmt` is the pure-Rust `.fltkg` formatter (parse with the generated Rust parser,
unparse with the Rust unparser baked from `fegen.fltkfmt`, render) built from
`crates/fltkfmt/`. The Python reference is the exact pipeline `fltk/unparse_cli.py`
runs on `fegen.fltkg` + `fegen.fltkfmt` (parse_text -> unparse_cst -> render_doc); the
two must produce byte-identical output at matching `--width`/`--indent`.

This is the strongest guarantee that the standalone pure-Rust formatter matches the
established Python formatter (including trailing-whitespace handling) and guards against
future drift between `fegen.fltkfmt` and the committed Rust `unparser.rs`.

Mirrors `tests/test_rust_unparser_parity_fixture.py`. Unlike the importable Rust
extension fixtures, `fltkfmt` is a standalone binary with no `make` build wiring, so a
session-scoped fixture builds it with `cargo`. The Rust toolchain is mandatory for this
repo (CLAUDE.md), so a missing `cargo` is a hard failure rather than a skip — the parity
guarantee can never be silently bypassed, and these tests are never all-skipped.
"""

from __future__ import annotations

import functools
import shutil
import subprocess
from pathlib import Path

import pytest

from fltk import plumbing
from fltk.unparse.renderer import RendererConfig
from tests.unparser_parity import render_config_ids

_REPO_ROOT = Path(__file__).parent.parent
_FEGEN_FLTKG = _REPO_ROOT / "fltk" / "fegen" / "fegen.fltkg"
_FEGEN_FLTKFMT = _REPO_ROOT / "fltk" / "fegen" / "fegen.fltkfmt"
_FLTKFMT_MANIFEST = _REPO_ROOT / "crates" / "fltkfmt" / "Cargo.toml"
_FLTKFMT_BINARY = _REPO_ROOT / "crates" / "fltkfmt" / "target" / "debug" / "fltkfmt"

# Corpus: every real `.fltkg` in the tree (the canonical grammars plus the test-data
# grammars). Each is parsed and re-rendered by both backends; pinned explicitly so the
# coverage set is visible and a non-parsing addition can't silently widen it.
_CORPUS = [
    _REPO_ROOT / "fltk" / "fegen" / "bootstrap.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "fegen.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "fltk.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "regex.fltkg",
    _REPO_ROOT / "fltk" / "fegen" / "test_data" / "collision_fixture.fltkg",
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


@pytest.fixture(scope="session")
def fltkfmt_binary() -> Path:
    """Build (with cargo) and locate the standalone `fltkfmt` binary.

    Cargo is mandatory for this repo (CLAUDE.md), so its absence is a hard failure, not a
    skip: the parity guarantee must never be silently bypassed. A build failure is
    likewise a hard error.
    """
    assert shutil.which("cargo") is not None, (
        "cargo not available; the Rust toolchain is required for this repo (CLAUDE.md) "
        "and the fltkfmt parity tests must not be skipped"
    )
    build = subprocess.run(  # noqa: S603
        ["cargo", "build", "--manifest-path", str(_FLTKFMT_MANIFEST)],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, f"failed to build fltkfmt:\n{build.stderr}"
    assert _FLTKFMT_BINARY.exists(), f"fltkfmt binary not found at {_FLTKFMT_BINARY}"
    return _FLTKFMT_BINARY


@pytest.mark.parametrize("max_width,indent_width", _CONFIGS, ids=_CONFIG_IDS)
@pytest.mark.parametrize("fltkg", _CORPUS, ids=_CORPUS_IDS)
def test_fltkfmt_matches_python(fltkfmt_binary: Path, fltkg: Path, max_width: int, indent_width: int):
    text = fltkg.read_text()
    py_out = _py_format(text, max_width, indent_width)
    proc = subprocess.run(  # noqa: S603
        [str(fltkfmt_binary), str(fltkg), "-w", str(max_width), "-i", str(indent_width)],
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"[{fltkg.name} w={max_width} i={indent_width}] fltkfmt exited {proc.returncode}: "
        f"{proc.stderr.decode('utf-8', 'replace')}"
    )
    rust_out = proc.stdout.decode("utf-8", "replace")
    assert py_out == rust_out, (
        f"[{fltkg.name} w={max_width} i={indent_width}] formatter output mismatch:\n"
        f"Python: {py_out!r}\nRust:   {rust_out!r}"
    )
