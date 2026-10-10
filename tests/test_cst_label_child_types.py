"""Labelled writes check the label's own child type set, on both backends.

A child stored under a label always has one of the types that label's accessors are annotated
with.  The node-wide child union is the wrong set to check against wherever a label is narrower
than the node, so every rejected row below is a value the node-wide check accepts: a union label
strictly inside the node-wide set (``RecViaSub.inner``, ``Grouped.left``), a node beside a Span
label (``MixedOpt``), and labels that differ on a node with two variants (``Expr``).  ``Val.item``
equals its node-wide set and is here only as the acceptance half.

Messages are asserted per backend against the shared template; the two backends' node classes
live in different modules, so their messages differ by construction.
"""

from __future__ import annotations

import pytest

rust_parser_fixture = pytest.importorskip(
    "rust_parser_fixture",
    reason="rust_parser_fixture not importable; it is built by //tests/rust_parser_fixture:rust_parser_fixture",
)

from fltk._native import Span as NativeSpan  # noqa: E402
from fltk.fegen.pyrt import terminalsrc  # noqa: E402
from fltk.plumbing import generate_parser, parse_grammar, parse_grammar_file  # noqa: E402
from tests.cst_mutator_helpers import assert_rejected  # noqa: E402
from tests.fixture_ast_layer import FIXTURE_FLTKG  # noqa: E402
from tests.gsm2tree_helpers import MIXED_SPAN_LABEL_GRAMMAR  # noqa: E402

_BACKEND_KEYS = ["py", "rust"]


@pytest.fixture(scope="module")
def py_cst():
    return generate_parser(parse_grammar_file(FIXTURE_FLTKG)).cst_module


@pytest.fixture(params=_BACKEND_KEYS)
def backend(request, py_cst):
    """(cst module, span factory) for one backend."""
    if request.param == "py":
        return py_cst, terminalsrc.Span
    return rust_parser_fixture.cst, NativeSpan


class TestUnionLabelStrictlyInsideTheNode:
    """``rec_via_sub``: ``inner`` = {RecViaSub, Atom}, ``suffix`` = {Name}; node-wide adds nothing."""

    def test_inner_accepts_both_of_its_types(self, backend) -> None:
        mod, _span = backend
        node = mod.RecViaSub()
        atom, rec, atom2, rec2 = mod.Atom(), mod.RecViaSub(), mod.Atom(), mod.RecViaSub()
        node.append_inner(atom)
        node.append_inner(rec)
        node.extend_inner([atom2, rec2])
        assert list(node.children_inner()) == [atom, rec, atom2, rec2]

    def test_inner_rejects_the_other_labels_type(self, backend) -> None:
        mod, _span = backend
        node = mod.RecViaSub()
        name = mod.Name()
        label = mod.RecViaSub.Label.INNER
        assert_rejected(node, lambda: node.append_inner(name), name)
        assert_rejected(node, lambda: node.append(name, label), name)
        assert_rejected(node, lambda: node.insert(0, name, label), name)
        node.append_inner(mod.Atom())
        assert_rejected(node, lambda: node.replace_at(0, name, label), name)

    def test_suffix_rejects_an_inner_type(self, backend) -> None:
        mod, _span = backend
        node = mod.RecViaSub()
        atom = mod.Atom()
        assert_rejected(node, lambda: node.append_suffix(atom), atom)
        assert_rejected(node, lambda: node.extend_suffix([mod.Name(), atom]), atom)
        assert node.children == []

    def test_an_unlabelled_write_checks_the_node_wide_set(self, backend) -> None:
        mod, _span = backend
        node = mod.RecViaSub()
        node.append(mod.Name())
        node.append(mod.Atom())
        assert [label for label, _child in node.children] == [None, None]


class TestUnionLabelBesideTheWhitespaceType:
    """``grouped``: ``left`` = {Num, Name}; the ``,`` separators add a node-wide ``Trivia``."""

    def test_left_accepts_both_of_its_types(self, backend) -> None:
        mod, _span = backend
        node = mod.Grouped()
        num, name = mod.Num(), mod.Name()
        node.append_left(num)
        node.append_left(name)
        assert list(node.children_left()) == [num, name]

    def test_left_rejects_the_whitespace_type(self, backend) -> None:
        mod, _span = backend
        node = mod.Grouped()
        trivia = mod.Trivia()
        assert_rejected(node, lambda: node.append_left(trivia), trivia)
        assert_rejected(node, lambda: node.append(trivia, mod.Grouped.Label.LEFT), trivia)
        node.append(trivia)
        assert node.children == [(None, trivia)]


def test_a_node_and_span_union_label_accepts_every_member(backend) -> None:
    """``val``: ``item`` = {Num, Name, Span}, equal to the node-wide set."""
    mod, span = backend
    node = mod.Val()
    num, name, s = mod.Num(), mod.Name(), span(0, 1)
    node.append_item(num)
    node.append_item(name)
    node.append_item(s)
    node.extend_item([num, s, name])
    assert len(list(node.children_item())) == 6


def test_a_node_and_span_label_inside_a_wider_node_admits_both_kinds_of_span() -> None:
    """``mix``: ``item`` = {Num, Span}, ``other`` = {Name}; one dispatch arm admits a node and a Span.

    Python backend only: no fixture crate carries this shape, and the Rust predicate's arm is
    pinned by the generator-shape suite.  Both span classes are fed, so the native-Span probe is
    exercised inside a mixed arm of a multi-arm dispatch.
    """
    mod = generate_parser(parse_grammar(MIXED_SPAN_LABEL_GRAMMAR)).cst_module
    node = mod.Mix()
    num, py_span, native_span, name = mod.Num(), terminalsrc.Span(0, 1), NativeSpan(1, 2), mod.Name()
    node.append_item(num)
    node.extend_item([py_span, native_span])
    assert [child for _label, child in node.children] == [num, py_span, native_span]
    assert all(a is b for a, b in zip(node.children_item(), [num, py_span, native_span], strict=True))
    assert_rejected(node, lambda: node.append_item(name), name)
    assert_rejected(node, lambda: node.append(name, mod.Mix.Label.ITEM), name)


class TestLabelsThatDifferOnATwoVariantNode:
    """``expr``: ``lhs`` = {Expr}, ``rhs`` = ``atom`` = {Atom}; node-wide = {Atom, Expr}."""

    def test_each_label_accepts_its_own_type(self, backend) -> None:
        mod, _span = backend
        node = mod.Expr()
        node.append_lhs(mod.Expr())
        node.append_rhs(mod.Atom())
        node.append_atom(mod.Atom())
        assert len(node.children) == 3

    def test_each_label_rejects_the_other_type(self, backend) -> None:
        mod, _span = backend
        node = mod.Expr()
        atom, expr = mod.Atom(), mod.Expr()
        assert_rejected(node, lambda: node.append_lhs(atom), atom)
        assert_rejected(node, lambda: node.append_rhs(expr), expr)
        assert_rejected(node, lambda: node.append_atom(expr), expr)


class TestSpanLabelBesideANodeLabel:
    """``mixed_opt``: ``key`` = {Span}, ``node`` = {Num}; node-wide = {Span, Num}."""

    def test_key_accepts_a_span(self, backend) -> None:
        mod, span = backend
        node = mod.MixedOpt()
        s = span(0, 1)
        node.append_key(s)
        assert len(node.children) == 1

    def test_each_label_rejects_the_other_type(self, backend) -> None:
        mod, span = backend
        node = mod.MixedOpt()
        num, s = mod.Num(), span(0, 1)
        assert_rejected(node, lambda: node.append_key(num), num)
        assert_rejected(node, lambda: node.append_node(s), s)
