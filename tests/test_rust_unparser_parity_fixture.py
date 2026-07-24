"""Cross-backend unparser parity: Python unparser vs rust_parser_fixture.

For each (rule, text) in the shared corpus the input is parsed with both the Python and
the Rust parser backends (capture_trivia=True), unparsed with both unparser backends, and
rendered to a string at matching RendererConfig; the rendered bytes must be equal.

The Rust unparser bakes its FormatterConfig at generation time, so each config is a
separate baked module. Design §4 requires parity over *both* configs, so this module
runs the shared corpus twice:

- `.fltkfmt`: the committed Rust `unparser.rs` (baked with the fixture `.fltkfmt`,
  exposed as `rust_parser_fixture.unparser`) vs the Python unparser generated from the
  same `.fltkfmt`.
- default `FormatterConfig`: the committed Rust `unparser_default.rs` (baked with no
  format config, exposed as `rust_parser_fixture.unparser_default`) vs the Python
  unparser generated with the default config.

Requires rust_parser_fixture to be built: run 'make build-rust-parser-fixture' first.
A CI lane where every test here is skipped is a failure signal.
"""

from __future__ import annotations

import functools
from pathlib import Path

import pytest

rust_parser_fixture = pytest.importorskip(
    "rust_parser_fixture",
    reason="rust_parser_fixture not built; run 'make build-rust-parser-fixture' first",
)

from fltk.plumbing import (  # noqa: E402
    generate_parser,
    generate_unparser,
    parse_format_config_file,
    parse_grammar_file,
    parse_text,
)
from tests.unparser_parity import assert_unparse_parity, render_config_ids  # noqa: E402

_FIXTURE_DIR = Path(__file__).parent.parent / "fltk" / "fegen" / "test_data"
_FIXTURE_FLTKG = _FIXTURE_DIR / "rust_parser_fixture.fltkg"
_FIXTURE_FLTKFMT = _FIXTURE_DIR / "rust_parser_fixture.fltkfmt"


@functools.cache
def _grammar():
    return parse_grammar_file(_FIXTURE_FLTKG)


@functools.cache
def _py_parser_result():
    return generate_parser(_grammar(), capture_trivia=True)


@functools.cache
def _py_unparser_result():
    """Python unparser generated from the fixture `.fltkfmt` (matching the baked Rust config)."""
    cfg = parse_format_config_file(_FIXTURE_FLTKFMT)
    return generate_unparser(_grammar(), _py_parser_result().cst_module_name, cfg)


@functools.cache
def _py_unparser_result_default():
    """Python unparser generated with the default FormatterConfig (matching unparser_default.rs)."""
    # No formatter_config -> default FormatterConfig(), matching the Rust
    # unparser_default.rs (generated with no --format-config).
    return generate_unparser(_grammar(), _py_parser_result().cst_module_name)


@functools.cache
def _py_cst(text: str, rule: str):
    # Parse depends only on (rule, text); the render-config axis never affects it,
    # so cache to avoid re-parsing the same input once per config/backend cell.
    result = parse_text(_py_parser_result(), text, rule)
    assert result.success, f"Python parse failed for rule={rule!r} text={text!r}: {result.error_message}"
    return result.cst


@functools.cache
def _rust_node(text: str, rule: str):
    # Cached for the same reason as _py_cst; the CST is read-only to the unparser.
    parser = rust_parser_fixture.parser.Parser(text, capture_trivia=True)
    result = getattr(parser, f"apply__parse_{rule}")(0)
    assert result is not None and result.pos == len(text), (
        f"Rust parse failed for rule={rule!r} text={text!r}: result={result!r}"
    )
    return result.result


# (rule, text) pairs that fully parse on both backends. Chosen to exercise the
# `.fltkfmt` config paths (before/after anchors, rule- and item-level group/nest/join,
# WS_REQUIRED/WS_ALLOWED spacing, trivia collapse) plus default-spacing rules,
# union labels, multibyte text, suppressed/included terms, sub-expressions, and
# bounded-depth recursion (design §4: recursion without the deep-tree limit).
_CORPUS = [
    # Basic rules (default spacing)
    ("num", "123"),
    ("name", "hello"),
    ("atom", "42"),
    ("atom", "world"),
    # expr: left recursion + before/after "+" + rule-level group + item-level nest
    # from lhs to rhs + after-lhs spacing
    ("expr", "1+2"),
    ("expr", "1+2+3"),
    ("expr", "x"),
    # lval/rval: indirect mutual left recursion — distinct codegen shape from the
    # self-referencing `expr` path (two methods, two match arms). base + indirect.
    ("lval", "hello"),
    ("lval", "42!"),
    ("rval", "123"),
    ("rval", "hello?"),
    # stmt: WS_REQUIRED + item-level group from lhs to rhs + before/after "="
    ("stmt", "x = y"),
    ("stmt", "1 = 2"),
    # items: rule-level join (bsp) + after-item spacing over a quantified item
    ("items", "1"),
    ("items", "1a"),
    ("items", "1a2b"),
    # quantifiers: opt (?) present and absent, zero-or-more (*), incl. empty match.
    # opt_item "" exercises the absent-? path (if-let skipped, Some(empty doc)),
    # distinct from the *-loop-never-entered path covered by zero_items "".
    ("opt_item", "1"),
    ("opt_item", ""),
    ("zero_items", ""),
    ("zero_items", "1"),
    ("zero_items", "1a2"),
    # paren_expr: rule-level nest + item-level group from after "(" to before ")"
    # + soft anchors around the parens; with and without inner trivia
    ("paren_expr", "(42)"),
    ("paren_expr", "( hello )"),
    # leading_ws: leading WS_ALLOWED initial separator (trivia collapse)
    ("leading_ws", "42"),
    ("leading_ws", "   42"),
    # union label (num node / name node / bare span)
    ("val", "42"),
    ("val", "hello"),
    ("val", "!@#"),
    # multibyte literal + regex (codepoint-indexed spans)
    ("arrow", "→x"),
    ("latin_word", "àáâ"),
    # $-included unlabeled literal re-emitted as text
    ("tagged", "tagword"),
    # sub-expression with WS_ALLOWED separators inside
    ("grouped", "(42)"),
    ("grouped", "( hello )"),
    # recursion through a sub-expression (inline-to-parent)
    ("rec_via_sub", "1x"),
    ("rec_via_sub", "1x+y"),
    # bounded-depth right-recursive nesting
    ("nest", "42"),
    ("nest", "(42)"),
    ("nest", "((42))"),
    ("nest", "(((42)))"),
    # bounded-depth left-recursive sum of nests
    ("nest_sum", "42"),
    ("nest_sum", "42+99"),
    ("nest_sum", "1+(2)"),
]

_CORPUS_IDS = [f"{rule}-{n}" for n, (rule, _) in enumerate(_CORPUS)]

# Render at a wide width (everything flat) and a narrow width (groups break),
# so the Wadler-Lindig flat-vs-break decisions are exercised cross-backend.
_CONFIGS = [(80, 4), (8, 2)]
_CONFIG_IDS = render_config_ids(_CONFIGS)

# Each baked Rust unparser module is paired with the Python unparser generated from
# the matching FormatterConfig. Rust class refs are wrapped in lambdas because
# rust_parser_fixture is not importable at module level when the fixture isn't built.
_BACKEND_CONFIGS = [
    (
        "fltkfmt",
        _py_unparser_result,
        lambda: rust_parser_fixture.unparser.Unparser(),  # noqa: PLW0108 -- defers the attribute lookup; inlining would resolve rust_parser_fixture at import time, before the fixture is guaranteed built
    ),
    (
        "default",
        _py_unparser_result_default,
        lambda: rust_parser_fixture.unparser_default.Unparser(),  # noqa: PLW0108 -- same deferred-lookup reason as above
    ),
]


@pytest.mark.parametrize("_cfg,py_result_fn,rust_unparser_fn", _BACKEND_CONFIGS, ids=[c[0] for c in _BACKEND_CONFIGS])
@pytest.mark.parametrize("max_width,indent_width", _CONFIGS, ids=_CONFIG_IDS)
@pytest.mark.parametrize("rule,text", _CORPUS, ids=_CORPUS_IDS)
def test_unparse_parity(*, rule, text, max_width, indent_width, _cfg, py_result_fn, rust_unparser_fn):
    py_cst = _py_cst(text, rule)
    rust_node = _rust_node(text, rule)
    assert_unparse_parity(
        py_result_fn(),
        py_cst,
        rust_unparser=rust_unparser_fn(),
        rust_node=rust_node,
        rule=rule,
        text=text,
        indent_width=indent_width,
        max_width=max_width,
    )
