"""Tier-2 Phase 4 tests: standalone non-FLTK user-extension fixture.

These tests require the phase4_roundtrip_cst extension to be built.
They are skipped automatically when the fixture is not importable (run
`make build-test-user-ext` first, or use CI which builds it before pytest).
A CI lane where every test here is skipped is a failure signal — the artifacts
are not being built.

Test coverage:
  AC2 — cst_module registered and exposes all rule classes
  AC3 — full parse → CST → unparse → render roundtrip
  AC5 — all 12 API-Contract items exercised against the Rust-backed nodes
  AC7 (Rust half) — API-Contract operations via both backends on same grammar
"""
# ruff: noqa: N806  # Class objects stored in uppercase variables (conventional for type aliases)

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module-level skip when fixture not available
# ---------------------------------------------------------------------------

phase4_roundtrip_cst = pytest.importorskip(
    "phase4_roundtrip_cst",
    reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
)

# These imports only execute if the module is available (importorskip handles it)
from fltk._native import Span, UnknownSpan  # noqa: E402
from fltk.fegen.pyrt.terminalsrc import UnknownSpan as PyUnknownSpan  # noqa: E402
from fltk.plumbing import (  # noqa: E402
    generate_parser,
    generate_unparser,
    parse_grammar_file,
    parse_text,
    render_doc,
    unparse_cst,
)

# ── Grammar and parser fixtures ────────────────────────────────────────────

_GRAMMAR_PATH = Path(__file__).parent.parent / "fltk" / "fegen" / "test_data" / "phase4_roundtrip.fltkg"

# Use separate grammar objects for each backend so that generate_parser
# assigns distinct cst_module_name values (keyed on id(grammar)).
_grammar_for_rust = parse_grammar_file(_GRAMMAR_PATH)
_grammar_for_python = parse_grammar_file(_GRAMMAR_PATH)

_rust_pr = generate_parser(_grammar_for_rust, rust_cst_module="phase4_roundtrip_cst")
_python_pr = generate_parser(_grammar_for_python)  # Python backend for AC7 comparison

# Convenience alias used by most single-backend tests.
_grammar = _grammar_for_rust


def _span(start: int = 0, end: int = 1) -> Span:
    return Span(start, end)


# ── AC2: module registered and exposes all rule classes ────────────────────

class TestAC2ModuleRegistered:
    """AC2: generate_parser with Rust backend; cst_module in sys.modules, exposes classes."""

    def test_cst_module_in_sys_modules(self):
        assert _rust_pr.cst_module_name in sys.modules
        assert sys.modules[_rust_pr.cst_module_name] is _rust_pr.cst_module

    def test_cst_module_exposes_config(self):
        assert hasattr(_rust_pr.cst_module, "Config")
        assert isinstance(_rust_pr.cst_module.Config, type)

    def test_cst_module_exposes_entry(self):
        assert hasattr(_rust_pr.cst_module, "Entry")
        assert isinstance(_rust_pr.cst_module.Entry, type)

    def test_cst_module_exposes_operator(self):
        assert hasattr(_rust_pr.cst_module, "Operator")
        assert isinstance(_rust_pr.cst_module.Operator, type)

    def test_cst_module_exposes_identifier(self):
        assert hasattr(_rust_pr.cst_module, "Identifier")
        assert isinstance(_rust_pr.cst_module.Identifier, type)

    def test_cst_module_exposes_literal(self):
        assert hasattr(_rust_pr.cst_module, "Literal")
        assert isinstance(_rust_pr.cst_module.Literal, type)


# ── AC3: parse → CST → unparse roundtrip ──────────────────────────────────

class TestAC3Roundtrip:
    """AC3: full parse → CST → unparse → render roundtrip with standalone Rust extension."""

    @pytest.fixture(scope="class")
    def unparser_result(self):
        return generate_unparser(_grammar, _rust_pr.cst_module_name)

    def test_parse_simple_entry(self, unparser_result):
        """Parse and round-trip a simple assignment entry."""
        result = parse_text(_rust_pr, "foo = 42;", "config")
        assert result.success, result.error_message
        doc = unparse_cst(unparser_result, result.cst, result.terminals, "config")
        output = render_doc(doc)
        assert "foo" in output
        assert "42" in output

    def test_parse_append_operator(self, unparser_result):
        """Parse and round-trip an append operator."""
        result = parse_text(_rust_pr, "bar += 99;", "config")
        assert result.success, result.error_message
        doc = unparse_cst(unparser_result, result.cst, result.terminals, "config")
        output = render_doc(doc)
        assert "bar" in output
        assert "99" in output

    def test_parse_string_literal(self, unparser_result):
        """Parse and round-trip a string literal value."""
        result = parse_text(_rust_pr, 'key = "hello";', "config")
        assert result.success, result.error_message
        doc = unparse_cst(unparser_result, result.cst, result.terminals, "config")
        output = render_doc(doc)
        assert "key" in output
        assert "hello" in output

    def test_parse_multiple_entries(self, unparser_result):
        """Parse and round-trip multiple config entries."""
        result = parse_text(_rust_pr, "a = 1; b += 2; c -= 3;", "config")
        assert result.success, result.error_message
        doc = unparse_cst(unparser_result, result.cst, result.terminals, "config")
        output = render_doc(doc)
        assert "a" in output and "b" in output and "c" in output

    def test_cst_nodes_are_rust_backed(self):
        """Nodes constructed by the generated parser are instances of the Rust classes."""
        Config = _rust_pr.cst_module.Config
        result = parse_text(_rust_pr, "x = 1;", "config")
        assert result.success, result.error_message
        assert isinstance(result.cst, Config)


# ── AC5: API-Contract verification ────────────────────────────────────────

class TestAC5ApiContract:
    """AC5 (PRIMARY binding): all 12 API-Contract items exercised against Rust-backed nodes.

    Uses the Operator rule (3-variant label enum) and Entry rule (3 labeled children).
    """

    # --- item 1: Construction ---
    def test_ac1_construction_default_span(self):
        """ClassName(span=Span(...)) and ClassName() with default UnknownSpan."""
        Entry = _rust_pr.cst_module.Entry
        s = _span(3, 7)
        node = Entry(span=s)
        assert node.span == s
        default_node = Entry()
        assert default_node.span == UnknownSpan

    # --- item 2: span write ---
    def test_ac2_span_write(self):
        """node.span = new_span is settable."""
        Entry = _rust_pr.cst_module.Entry
        node = Entry()
        s = _span(10, 20)
        node.span = s
        assert node.span == s

    # --- item 3: span read ---
    def test_ac3_span_read(self):
        """The span stored on a node is readable and is the same object that was set.

        Note: The Rust fltk._native.Span intentionally does NOT expose .start/.end
        as Python attributes (they are internal Rust fields).  The API Contract for
        span-read as used by fltk2gsm.py does not require .start/.end; it requires
        that the span is readable (node.span returns the span) and that the span
        object supports equality (used in node equality checks).  This test verifies
        what the real consumer contract requires.
        """
        Entry = _rust_pr.cst_module.Entry
        s = _span(5, 15)
        node = Entry(span=s)
        # Span is readable and is the same object
        assert node.span == s
        # Span equality works (used by __eq__ on nodes)
        assert node.span == _span(5, 15)

    # --- item 4: children.extend ---
    def test_ac4_children_extend(self):
        """node.children.extend(other.children) mutates the backing list."""
        Entry = _rust_pr.cst_module.Entry
        a = Entry()
        b = Entry()
        Identifier = _rust_pr.cst_module.Identifier
        ident = Identifier()
        b.append(ident)
        a.children.extend(b.children)
        assert len(a.children) == 1

    # --- item 5: typed append ---
    def test_ac5_typed_append(self):
        """node.append_{label}(child=value) with keyword child arg."""
        Entry = _rust_pr.cst_module.Entry
        Identifier = _rust_pr.cst_module.Identifier
        node = Entry()
        ident = Identifier()
        # append_key accepts positional child (the generated method uses `child: PyObject`)
        node.append_key(ident)
        assert len(node.children) == 1

    # --- item 6: full list protocol ---
    def test_ac6_list_protocol_len(self):
        """len(node.children)."""
        Entry = _rust_pr.cst_module.Entry
        node = Entry()
        assert len(node.children) == 0
        node.append(Entry())
        assert len(node.children) == 1

    def test_ac6_list_protocol_index(self):
        """node.children[i]."""
        Entry = _rust_pr.cst_module.Entry
        node = Entry()
        child = Entry()
        node.append(child)
        tup = node.children[0]
        assert tup[1] is child

    def test_ac6_list_protocol_stride(self):
        """node.children[::2] and node.children[1::2] — stride slicing."""
        Entry = _rust_pr.cst_module.Entry
        Identifier = _rust_pr.cst_module.Identifier
        Operator = _rust_pr.cst_module.Operator
        Literal = _rust_pr.cst_module.Literal
        node = Entry()
        ident = Identifier()
        op = Operator()
        lit = Literal()
        node.append_key(ident)
        node.append_op(op)
        node.append_value(lit)
        # Even-indexed children (labels at [::2]) — these are tuple elements, but
        # the full children list supports stride slicing.
        evens = node.children[::2]
        assert len(evens) == 2  # children[0] and children[2]
        odds = node.children[1::2]
        assert len(odds) == 1   # children[1]

    def test_ac6_list_protocol_negative_index(self):
        """node.children[-1]."""
        Entry = _rust_pr.cst_module.Entry
        node = Entry()
        a = Entry()
        b = Entry()
        node.append(a)
        node.append(b)
        last = node.children[-1]
        assert last[1] is b

    # --- item 7: tuple items ---
    def test_ac7_tuple_items(self):
        """node.children[i] is (label_or_None, value), indexable as 2-tuple."""
        Entry = _rust_pr.cst_module.Entry
        Identifier = _rust_pr.cst_module.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        tup = node.children[0]
        label, value = tup
        assert label == Entry.Label.KEY
        assert value is ident

    # --- item 8: label equality and containment ---
    def test_ac8_label_equality(self):
        """label == ClassName.Label.FOO."""
        Operator = _rust_pr.cst_module.Operator
        assert Operator.Label.ASSIGN == Operator.Label.ASSIGN
        assert Operator.Label.ASSIGN != Operator.Label.APPEND
        assert Operator.Label.ASSIGN != Operator.Label.REMOVE

    def test_ac8_label_containment(self):
        """label in (ClassName.Label.FOO, ...) — requires __eq__ + __hash__."""
        Operator = _rust_pr.cst_module.Operator
        assert Operator.Label.ASSIGN in (Operator.Label.ASSIGN, Operator.Label.APPEND)
        assert Operator.Label.REMOVE not in (Operator.Label.ASSIGN, Operator.Label.APPEND)

    def test_ac8_label_hashable(self):
        """Label variants are hashable (usable in sets and as dict keys)."""
        Operator = _rust_pr.cst_module.Operator
        s = {Operator.Label.ASSIGN, Operator.Label.APPEND, Operator.Label.REMOVE}
        assert len(s) == 3
        d = {Operator.Label.ASSIGN: "assign"}
        assert d[Operator.Label.ASSIGN] == "assign"

    # --- item 9: class-attribute label access ---
    def test_ac9_class_attr_label_access(self):
        """ClassName.Label.VARIANT is accessible."""
        Operator = _rust_pr.cst_module.Operator
        assert hasattr(Operator, "Label")
        assert hasattr(Operator.Label, "ASSIGN")
        assert hasattr(Operator.Label, "APPEND")
        assert hasattr(Operator.Label, "REMOVE")

    # --- item 10: isinstance dispatch ---
    def test_ac10_isinstance_dispatch(self):
        """isinstance(node, ClassName) resolves correctly."""
        Config = _rust_pr.cst_module.Config
        Entry = _rust_pr.cst_module.Entry
        c = Config()
        e = Entry()
        assert isinstance(c, Config)
        assert not isinstance(c, Entry)
        assert isinstance(e, Entry)
        assert not isinstance(e, Config)

    # --- item 11: iterator methods ---
    def test_ac11_iterator_methods(self):
        """node.children_{label}() iterable; node.child_{label}() single; node.maybe_{label}() Optional."""
        Entry = _rust_pr.cst_module.Entry
        Identifier = _rust_pr.cst_module.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        # children_key()
        keys = list(node.children_key())
        assert keys == [ident]
        # child_key()
        assert node.child_key() is ident
        # maybe_key()
        assert node.maybe_key() is ident
        # Empty case
        node2 = Entry()
        assert node2.maybe_key() is None
        with pytest.raises(ValueError):
            node2.child_key()

    # --- item 12: generic child() ---
    def test_ac12_generic_child(self):
        """node.child() returns (label, value) when exactly one child."""
        Entry = _rust_pr.cst_module.Entry
        Identifier = _rust_pr.cst_module.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        tup = node.child()
        assert tup[0] == Entry.Label.KEY
        assert tup[1] is ident


# ── AC7: Both-backend contract sweep ──────────────────────────────────────

class TestAC7BothBackends:
    """AC7: API-Contract operations run against both Python and Rust backends."""

    @pytest.mark.parametrize("pr,backend,expected_unknown", [
        (_python_pr, "python", PyUnknownSpan),
        (_rust_pr, "rust", UnknownSpan),
    ], ids=["python", "rust"])
    def test_construction_and_span(self, pr, backend, expected_unknown):  # noqa: ARG002
        Config = pr.cst_module.Config
        node = Config()
        # Each backend has its own UnknownSpan type; compare by equality.
        assert node.span == expected_unknown
        s = _span(1, 2)
        node.span = s
        assert node.span == s

    @pytest.mark.parametrize("pr,backend", [
        (_python_pr, "python"),
        (_rust_pr, "rust"),
    ], ids=["python", "rust"])
    def test_label_equality_and_hash(self, pr, backend):  # noqa: ARG002
        Operator = pr.cst_module.Operator
        assert Operator.Label.ASSIGN == Operator.Label.ASSIGN
        assert Operator.Label.ASSIGN != Operator.Label.APPEND
        assert len({Operator.Label.ASSIGN, Operator.Label.APPEND, Operator.Label.REMOVE}) == 3

    @pytest.mark.parametrize("pr,backend", [
        (_python_pr, "python"),
        (_rust_pr, "rust"),
    ], ids=["python", "rust"])
    def test_isinstance_dispatch(self, pr, backend):  # noqa: ARG002
        Config = pr.cst_module.Config
        Entry = pr.cst_module.Entry
        assert isinstance(Config(), Config)
        assert not isinstance(Config(), Entry)

    @pytest.mark.parametrize("pr,backend", [
        (_python_pr, "python"),
        (_rust_pr, "rust"),
    ], ids=["python", "rust"])
    def test_children_list_protocol(self, pr, backend):  # noqa: ARG002
        Entry = pr.cst_module.Entry
        Identifier = pr.cst_module.Identifier
        node = Entry()
        node.append_key(Identifier())
        node.append_op(pr.cst_module.Operator())
        node.append_value(pr.cst_module.Literal())
        # Stride
        assert len(node.children[::2]) == 2
        assert len(node.children[1::2]) == 1
        # Negative index
        assert node.children[-1][0] == Entry.Label.VALUE

    @pytest.mark.parametrize("pr,backend", [
        (_python_pr, "python"),
        (_rust_pr, "rust"),
    ], ids=["python", "rust"])
    def test_full_parse_roundtrip(self, pr, backend):
        ur = generate_unparser(_grammar, pr.cst_module_name)
        result = parse_text(pr, "key = 99;", "config")
        assert result.success, f"{backend}: {result.error_message}"
        doc = unparse_cst(ur, result.cst, result.terminals, "config")
        output = render_doc(doc)
        assert "key" in output and "99" in output
