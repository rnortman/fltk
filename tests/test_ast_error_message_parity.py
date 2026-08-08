"""Cross-backend parity of the diagnostics an AST converter raises about a CST.

`crates/fltk-ast-core/src/children.rs` states the contract: a CST the one backend refuses
must be refused by the other for the same stated reason. The two implementations cannot
share a string, so this test reads the Rust `format!` templates out of that file, its
fold-chain sibling and the synthesis module, and checks each one renders — under the one
translation the contract allows, Rust's `{x:?}` becoming Python's `{x!r}` — to exactly the
message `fltk.fegen.pyrt.astrt` raises for the same input.

The loop is closed in both directions: every case's Python message must match some Rust
template, and every Rust template must be matched by some case. So a message edited on
either side, or a diagnostic added to only one backend, fails here.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any

import pytest

from fltk.fegen.pyrt import astrt, terminalsrc

_RUNTIME_SRC = Path(__file__).parent.parent / "crates" / "fltk-ast-core" / "src"

_SOURCES = (
    _RUNTIME_SRC / "children.rs",
    _RUNTIME_SRC / "fold.rs",
    _RUNTIME_SRC / "synth.rs",
    _RUNTIME_SRC / "terminal.rs",
)
"""The runtime modules whose diagnostics are about a CST — read from one, or synthesised into one.

`scalar.rs` is deliberately absent: its messages are about a *value*, and the two backends spell
their own numeric formatting there, which is the difference `error.rs` documents.

`terminal.rs` is here for its terminal-mismatch message. Its Python twin carries one further arm
with no Rust counterpart by construction — a field typed `String` cannot hold a non-string, where
the Python field can — so that arm has no case below, the same carve-out `scalar.rs` gets wholesale.
"""

# Every `format!` template in the module body. The `#[cfg(test)]` module is cut off first: its
# expected strings are the same texts with the placeholders already filled in.
_TEMPLATE_RE = re.compile(r'format!\(\s*"((?:[^"\\]|\\.)*)"')

_SPAN = terminalsrc.UnknownSpan


@dataclasses.dataclass
class _Element:
    """A keyed collection's element: a key field and a span, which is all `keyed` reads."""

    key: str
    span: Any = _SPAN


@dataclasses.dataclass
class _Link:
    """A fold chain's link: an operator and two sides, which is all `unfold_*` reads."""

    op: str
    lhs: Any
    rhs: Any


_BRANCHES = (frozenset({"a"}), frozenset({"b"}))
"""One sub-expression alternation's two branches, as `check_group` reads them."""


def _rust_templates() -> list[str]:
    templates: list[str] = []
    for path in _SOURCES:
        source = path.read_text()
        body = source[: source.index("#[cfg(test)]")]
        templates.extend(match.group(1) for match in _TEMPLATE_RE.finditer(body))
    return templates


def _render(template: str, values: dict[str, Any]) -> str:
    """One Rust template as the Python message it corresponds to.

    `{x:?}` becomes `{x!r}` — the one difference the contract permits, each language spelling
    its own debug form of an interpolated value. A bare `{}` takes `values["positional"]`, the
    single positional argument any of these templates uses.
    """
    python = re.sub(r"\{(\w+):\?\}", r"{\1!r}", template)
    python = python.replace("{}", "{positional}")
    return python.format(**values)


def _message(call: Any) -> str:
    """The message one astrt call produces, whether it raises the error or returns it."""
    try:
        returned = call()
    except astrt.AstError as error:
        return error.message
    assert isinstance(returned, astrt.AstError)
    return returned.message


_CASES: list[tuple[str, Any, dict[str, Any]]] = [
    (
        "one, no child",
        lambda: astrt.one({}, "KEY", "entry", "key", _SPAN),
        {"rule": "entry", "label": "key", "positional": 0},
    ),
    (
        "one, two children",
        lambda: astrt.one({"KEY": ["a", "b"]}, "KEY", "entry", "key", _SPAN),
        {"rule": "entry", "label": "key", "positional": 2},
    ),
    (
        "optional, two children",
        lambda: astrt.optional({"TAG": ["a", "b"]}, "TAG", "entry", "tag", _SPAN),
        {"rule": "entry", "label": "tag", "found": 2},
    ),
    (
        "presence, two children",
        lambda: astrt.presence({"PUB": ["a", "b"]}, "PUB", "decl", "pub", _SPAN),
        {"rule": "decl", "label": "pub", "found": 2},
    ),
    (
        "text of a sourceless span",
        lambda: astrt.text(terminalsrc.Span(0, 3), "word", "w", _SPAN),
        {"rule": "word", "label": "w"},
    ),
    (
        "node_text of a sourceless span",
        lambda: astrt.node_text(terminalsrc.Span(0, 3), "word"),
        {"rule": "word"},
    ),
    (
        "a child of the wrong kind",
        lambda: astrt.unexpected_child("wrap", "a", _SPAN),
        {"rule": "wrap", "label": "a"},
    ),
    (
        "two elements under one key",
        lambda: astrt.keyed([_Element("host"), _Element("host")], "key", "setting"),
        {"rule": "setting", "key": "host"},
    ),
    (
        "a key of a multi map with no element to carry it",
        lambda: astrt.multi_values({"host": []}, "setting"),
        {"rule": "setting", "key": "host"},
    ),
    (
        "a fold with no operand",
        lambda: astrt.check_fold_arity(0, 0, "expr", _SPAN),
        {"rule": "expr"},
    ),
    (
        "a fold whose operators do not sit between its operands",
        lambda: astrt.check_fold_arity(3, 1, "expr", _SPAN),
        {"rule": "expr", "operands": 3, "operators": 1, "positional": 2},
    ),
    (
        "a terminal-only rule no split can rebuild",
        # The failure is decided before the class is touched, so nothing here has to be a node class.
        lambda: astrt.terminal_to_cst(object(), "anything", [astrt.TerminalAlt(None, ())], "parts"),
        {"rule": "parts"},
    ),
    (
        "text a terminal-only rule could not have matched",
        lambda: astrt.terminal_to_cst(object(), "zz", [astrt.TerminalAlt("[0-9]+", ())], "num"),
        {"rule": "num", "text": "zz"},
    ),
    (
        "an item position the grammar requires a value for",
        lambda: astrt.filled([], 2, "pair", "a"),
        {"rule": "pair", "label": "a", "minimum": 2, "available": 0},
    ),
    (
        "a value no item position has room for",
        lambda: astrt.check_consumed("pair", (("a", astrt.cursor([1, 2])),)),
        {"rule": "pair", "label": "a", "remaining": 2},
    ),
    (
        "a value no branch of an alternation accepts",
        lambda: astrt.unplaceable("text", "val", "x"),
        {"rule": "val", "label": "x", "kind": "str"},
    ),
    (
        "a flattened wrapper missing a field it requires",
        lambda: astrt.hoisted(None, "schedule", "interval"),
        {"rule": "schedule", "field": "interval"},
    ),
    (
        "an alternation the grammar demands a value for",
        lambda: astrt.check_group("decl", frozenset(), _BRANCHES, frozenset({"a", "b"}), demanded=True),
        {"rule": "decl", "offered": "['a', 'b']"},
    ),
    (
        "values that cannot come from one branch of an alternation",
        lambda: astrt.check_group("decl", frozenset({"a", "b"}), _BRANCHES, frozenset({"a", "b"}), demanded=True),
        {"rule": "decl", "narrowed": "['a', 'b']", "offered": "['a'] | ['b']"},
    ),
    (
        "text the grammar's terminal could not have matched",
        lambda: astrt.validate_terminal("12x", "[0-9]+", "number", "val"),
        {"rule": "number", "label": "val", "text": "12x", "positional": "[0-9]+"},
    ),
    (
        "a synthesised node the formatter declined to render",
        lambda: astrt.unrenderable("config"),
        {"rule": "config"},
    ),
    (
        "a chain nested against the fold's own direction",
        lambda: astrt.unfold_left(_Link("+", 1, _Link("-", 2, 3)), _Link, "op", "expr"),
        {"rule": "expr", "side": "right"},
    ),
    (
        "a fold over operands from two sources",
        lambda: astrt.fold_left(
            # The merge fails before a link is built, so nothing here has to be a real link class.
            lambda *_arguments: None,
            [1, 2],
            [terminalsrc.Span.with_source(0, 1, "a"), terminalsrc.Span.with_source(0, 1, "b")],
            ["+"],
            "expr",
        ),
        {"rule": "expr"},
    ),
]

_CASE_IDS = [name for name, _call, _values in _CASES]


@pytest.mark.parametrize(("call", "values"), [(call, values) for _name, call, values in _CASES], ids=_CASE_IDS)
def test_the_python_message_is_a_rust_template(call: Any, values: dict[str, Any]) -> None:
    message = _message(call)
    rendered = [_render(template, values) for template in _rust_templates() if _renderable(template, values)]
    assert message in rendered, f"no children.rs template renders to {message!r}"


def _renderable(template: str, values: dict[str, Any]) -> bool:
    """Whether ``values`` supplies every name ``template`` interpolates."""
    names = set(re.findall(r"\{(\w+)(?::\?)?\}", template))
    if "{}" in template:
        names.add("positional")
    return names <= set(values)


def test_every_rust_template_has_a_python_counterpart() -> None:
    covered = {
        _render(template, values)
        for _name, call, values in _CASES
        for template in _rust_templates()
        if _renderable(template, values) and _render(template, values) == _message(call)
    }
    unmatched = [
        template
        for template in _rust_templates()
        if not any(
            _renderable(template, values) and _render(template, values) in covered for _name, _call, values in _CASES
        )
    ]
    assert not unmatched, f"children.rs templates with no astrt counterpart: {unmatched}"
