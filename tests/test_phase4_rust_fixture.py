"""Tier-2 Phase 4 tests: standalone non-FLTK user-extension fixture.

These tests require the phase4_roundtrip_cst extension to be built.
They are skipped automatically when the fixture is not importable (run
`make build-test-user-ext` first, or use CI which builds it before pytest).
A CI lane where every test here is skipped is a failure signal — the artifacts
are not being built.

Test coverage:
  AC2 — cst_module exposes all rule classes (the standalone Rust CST extension)
  AC5 — all 12 API-Contract items exercised against the Rust-backed nodes
  AC7 — API-Contract operations via both Python and Rust CST classes

The standalone Rust CST extension (phase4_roundtrip_cst.cst) ships no parser, so
the Rust CST contracts are exercised by constructing nodes directly. Full
parse → CST → unparse roundtrip is covered on the pure-Python backend.
"""
# ruff: noqa: N806  # Class objects stored in uppercase variables (conventional for type aliases)

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Module-level skip when fixture not available
# ---------------------------------------------------------------------------

# The genuine config-2 Rust CST classes (the standalone extension ships no parser).
_rust_cst = pytest.importorskip(
    "phase4_roundtrip_cst.cst",
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

# Pure-Python parser for the AC7 backend comparison and the parse roundtrip.
_grammar = parse_grammar_file(_GRAMMAR_PATH)
_python_pr = generate_parser(_grammar)


def _span(start: int = 0, end: int = 1) -> Span:
    return Span(start, end)


# ── AC2: Rust CST extension exposes all rule classes ───────────────────────


class TestAC2ModuleExposesClasses:
    """AC2: the standalone Rust CST extension exposes every rule class."""

    def test_cst_module_exposes_config(self):
        assert hasattr(_rust_cst, "Config")
        assert isinstance(_rust_cst.Config, type)

    def test_cst_module_exposes_entry(self):
        assert hasattr(_rust_cst, "Entry")
        assert isinstance(_rust_cst.Entry, type)

    def test_cst_module_exposes_operator(self):
        assert hasattr(_rust_cst, "Operator")
        assert isinstance(_rust_cst.Operator, type)

    def test_cst_module_exposes_identifier(self):
        assert hasattr(_rust_cst, "Identifier")
        assert isinstance(_rust_cst.Identifier, type)

    def test_cst_module_exposes_literal(self):
        assert hasattr(_rust_cst, "Literal")
        assert isinstance(_rust_cst.Literal, type)


# ── AC5: API-Contract verification ────────────────────────────────────────


class TestAC5ApiContract:
    """AC5 (PRIMARY binding): all 12 API-Contract items exercised against Rust-backed nodes.

    Uses the Operator rule (3-variant label enum) and Entry rule (3 labeled children).
    Nodes are constructed directly from the standalone Rust CST extension.
    """

    # --- item 1: Construction ---
    def test_ac1_construction_default_span(self):
        """ClassName(span=Span(...)) and ClassName() with default UnknownSpan."""
        Entry = _rust_cst.Entry
        s = _span(3, 7)
        node = Entry(span=s)
        assert node.span == s
        default_node = Entry()
        assert default_node.span == UnknownSpan

    # --- item 2: span write ---
    def test_ac2_span_write(self):
        """node.span = new_span is settable."""
        Entry = _rust_cst.Entry
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
        Entry = _rust_cst.Entry
        s = _span(5, 15)
        node = Entry(span=s)
        # Span is readable and is the same object
        assert node.span == s
        # Span equality works (used by __eq__ on nodes)
        assert node.span == _span(5, 15)

    # --- item 4: children.extend ---
    def test_ac4_children_extend(self):
        """node.extend_children(other) copies other's children into node's native Vec."""
        # The Rust backend rebuilds `children` as a fresh list on each call, so
        # `a.children.extend(b.children)` would mutate a throwaway list and be
        # silently dropped.  Use the node's own extend_children() method instead,
        # which mutates the native Vec directly.
        Entry = _rust_cst.Entry
        a = Entry()
        b = Entry()
        Identifier = _rust_cst.Identifier
        ident = Identifier()
        b.append(ident)
        a.extend_children(b)
        assert len(a.children) == 1

    # --- item 5: typed append ---
    def test_ac5_typed_append(self):
        """node.append_{label}(child=value) with keyword child arg."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        # append_key accepts positional child (the generated method uses `child: PyObject`)
        node.append_key(ident)
        assert len(node.children) == 1

    # --- item 6: full list protocol ---
    def test_ac6_list_protocol_len(self):
        """len(node.children)."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        assert len(node.children) == 0
        node.append(Identifier())
        assert len(node.children) == 1

    def test_ac6_list_protocol_index(self):
        """node.children[i]."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        child = Identifier()
        node.append(child)
        tup = node.children[0]
        # Phase 1: registry ensures the same Python handle is returned each time.
        assert tup[1] is child

    def test_ac6_list_protocol_stride(self):
        """node.children[::2] and node.children[1::2] — stride slicing."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        Operator = _rust_cst.Operator
        Literal = _rust_cst.Literal
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
        assert len(odds) == 1  # children[1]

    def test_ac6_list_protocol_negative_index(self):
        """node.children[-1]."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        a = Identifier()
        b = Identifier()
        node.append(a)
        node.append(b)
        last = node.children[-1]
        # Phase 1: registry ensures the same Python handle is returned each time.
        assert last[1] is b

    # --- item 7: tuple items ---
    def test_ac7_tuple_items(self):
        """node.children[i] is (label_or_None, value), indexable as 2-tuple."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        tup = node.children[0]
        label, value = tup
        assert label == Entry.Label.KEY
        # Phase 1: registry ensures the same Python handle is returned each time.
        assert value is ident

    # --- item 8: label equality and containment ---
    def test_ac8_label_equality(self):
        """label == ClassName.Label.FOO."""
        Operator = _rust_cst.Operator
        assert Operator.Label.ASSIGN == Operator.Label.ASSIGN
        assert Operator.Label.ASSIGN != Operator.Label.APPEND
        assert Operator.Label.ASSIGN != Operator.Label.REMOVE

    def test_ac8_label_containment(self):
        """label in (ClassName.Label.FOO, ...) — requires __eq__ + __hash__."""
        Operator = _rust_cst.Operator
        assert Operator.Label.ASSIGN in (Operator.Label.ASSIGN, Operator.Label.APPEND)
        assert Operator.Label.REMOVE not in (Operator.Label.ASSIGN, Operator.Label.APPEND)

    def test_ac8_label_hashable(self):
        """Label variants are hashable (usable in sets and as dict keys)."""
        Operator = _rust_cst.Operator
        s = {Operator.Label.ASSIGN, Operator.Label.APPEND, Operator.Label.REMOVE}
        assert len(s) == 3
        d = {Operator.Label.ASSIGN: "assign"}
        assert d[Operator.Label.ASSIGN] == "assign"

    # --- item 9: class-attribute label access ---
    def test_ac9_class_attr_label_access(self):
        """ClassName.Label.VARIANT is accessible."""
        Operator = _rust_cst.Operator
        assert hasattr(Operator, "Label")
        assert hasattr(Operator.Label, "ASSIGN")
        assert hasattr(Operator.Label, "APPEND")
        assert hasattr(Operator.Label, "REMOVE")

    # --- item 10: isinstance dispatch ---
    def test_ac10_isinstance_dispatch(self):
        """isinstance(node, ClassName) resolves correctly."""
        Config = _rust_cst.Config
        Entry = _rust_cst.Entry
        c = Config()
        e = Entry()
        assert isinstance(c, Config)
        assert not isinstance(c, Entry)
        assert isinstance(e, Entry)
        assert not isinstance(e, Config)

    # --- item 11: iterator methods ---
    def test_ac11_iterator_methods(self):
        """node.children_{label}() iterable; node.child_{label}() single; node.maybe_{label}() Optional."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        # children_key()
        keys = list(node.children_key())
        assert keys == [ident]
        # child_key() / maybe_key() — Phase 1: registry ensures same handle each time.
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
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        tup = node.child()
        assert tup[0] == Entry.Label.KEY
        # Phase 1: registry ensures the same Python handle is returned each time.
        assert tup[1] is ident


# ── Phase 1 identity and mutation tests ───────────────────────────────────────


class TestPhase1IdentityAndMutation:
    """Phase 1 (rust-idiomatic-cst-api): Shared<T> ownership + canonical wrapper registry.

    Verifies that:
    - The same Python handle object is returned on every read (is-stable identity).
    - Mutations made via one reference are visible through all others.
    - Post-append aliasing: mutate after append, parent sees it.
    - extend_children duplicates children entries (matches Python backend).
    - `x == x` returns True without deadlock (ptr_eq short-circuit).
    """

    def test_repeated_child_reads_return_same_handle(self):
        """children[0] read twice yields the same Python object (registry hit)."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        first = node.children[0][1]
        second = node.children[0][1]
        assert first is second, "repeated child reads must return the same handle"

    def test_child_label_accessor_returns_same_handle(self):
        """child_key() returns the same handle as the appended node."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        assert node.child_key() is ident

    def test_mutation_propagates_python_to_python(self):
        """Mutating a child's span via one handle is visible through the parent."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier

        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        new_span = Span(99, 199)
        ident.span = new_span
        # Read through the parent's accessor — should reflect the mutation.
        key_via_parent = node.child_key()
        assert key_via_parent.span == new_span, "mutation must be visible through parent accessor"

    def test_post_append_alias_mutation_visible(self):
        """Mutating a node after appending it is visible through the parent."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier

        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        # Mutate AFTER append.
        ident.span = Span(42, 84)
        assert node.child_key().span == Span(42, 84), "post-append mutation must be visible"

    def test_extend_children_duplicates_entries(self):
        """node.extend_children(node) duplicates children (matches Python backend)."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        assert len(node.children) == 1
        node.extend_children(node)
        assert len(node.children) == 2, "self-extend should duplicate children"
        # Both entries reference the same child object.
        first = node.children[0][1]
        second = node.children[1][1]
        assert first is second, "extended entries should alias the same node"

    def test_extend_children_from_other(self):
        """node.extend_children(other) appends other's children, sharing identity."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        src = Entry()
        dst = Entry()
        ident = Identifier()
        src.append_key(ident)
        dst.extend_children(src)
        assert len(dst.children) == 1
        assert dst.children[0][1] is ident, "extended child must be the same handle"

    def test_node_eq_self_no_deadlock(self):
        """node == node returns True without deadlock (ptr_eq short-circuit)."""
        Entry = _rust_cst.Entry
        node = Entry()
        same = node  # alias to satisfy ruff PLR0124 (name compared with itself)
        assert node == same, "x == x must be True (ptr_eq short-circuit, no deadlock)"

    def test_node_eq_distinct_allocation_deep_tree(self):
        """Python == on two distinct-allocation trees exercises the full pymethod delegation.

        Builds two structurally-equal trees from independent allocations and asserts they
        compare equal via Python __eq__.  This pins the pymethod → Shared<T>::eq →
        iterative T::eq delegation chain, which test_node_eq_self_no_deadlock does not cover
        (that test short-circuits at ptr_eq).
        """
        Config = _rust_cst.Config
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier

        def build() -> object:
            cfg = Config()
            for _ in range(3):
                entry = Entry()
                entry.append_key(Identifier())
                cfg.append(entry)
            return cfg

        tree1 = build()
        tree2 = build()
        assert tree1 == tree2, "two distinct-allocation structurally-equal trees must compare equal via Python =="

    def test_identity_stable_across_different_accessors(self):
        """children[0][1] and child_key() return the same handle (registry hit)."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        via_children = node.children[0][1]
        via_child_key = node.child_key()
        assert via_children is via_child_key, "all accessors must return the same registered handle"

    def test_new_node_append_readback_identity(self):
        """py_new → append → read-back → is the original object."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append(ident)
        readback = node.children[0][1]
        assert readback is ident, "appended then read-back node must be is the original"

    def test_children_label_accessor_identity(self):
        """children_<label>() returns the same handle (registry hit via to_pyobject, test-9)."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        keys = node.children_key()
        assert len(keys) == 1, "expected one key child"
        assert keys[0] is ident, "children_<label>() must return the same registered handle"

    def test_extend_children_self_original_handle_survives(self):
        """After self-extend, children alias original ident (handle not evicted, test-11)."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        node = Entry()
        ident = Identifier()
        node.append_key(ident)
        node.extend_children(node)
        first = node.children[0][1]
        second = node.children[1][1]
        assert first is second, "extended entries should alias the same node"
        assert first is ident, "original handle must still be the canonical one after self-extend"

    def test_shared_child_mutation_visible_through_two_parents(self):
        """One child appended to two parents; mutation visible through both (Arc-clone, test-12)."""
        Entry = _rust_cst.Entry
        Identifier = _rust_cst.Identifier
        ident = Identifier()
        entry_a = Entry()
        entry_b = Entry()
        entry_a.append_key(ident)
        entry_b.append_key(ident)
        new_span = Span(99, 199)
        ident.span = new_span
        assert entry_a.child_key().span == new_span, "mutation must be visible through parent A"
        assert entry_b.child_key().span == new_span, "mutation must be visible through parent B"


# ── Error-path tests for extract_span (cross_cdylib.rs) ────────────────────


class TestExtractSpanErrorPaths:
    """Verify extract_span raises TypeError with a useful message for wrong-typed arguments.

    Exercises the error branch of extract_span (cross_cdylib.rs) — both the fast-path
    rejection (obj.extract::<Span>() fails) and the isinstance check both fail, so
    PyTypeError is returned with the type name of the rejected object.
    """

    def test_set_span_integer_raises_typeerror(self):
        """Passing an integer as a span raises TypeError."""
        Entry = _rust_cst.Entry
        node = Entry()
        with pytest.raises(TypeError):
            node.span = 42

    def test_set_span_string_raises_typeerror(self):
        """Passing a string as a span raises TypeError."""
        Entry = _rust_cst.Entry
        node = Entry()
        with pytest.raises(TypeError):
            node.span = "not a span"

    def test_set_span_none_raises_typeerror(self):
        """Passing None as a span raises TypeError."""
        Entry = _rust_cst.Entry
        node = Entry()
        with pytest.raises(TypeError):
            node.span = None

    def test_set_span_wrong_type_message_mentions_span(self):
        """The TypeError message from a wrong-typed span mentions fltk._native.Span."""
        Entry = _rust_cst.Entry
        node = Entry()
        with pytest.raises(TypeError, match=r"fltk\._native\.Span"):
            node.span = 99


# ── AC7: Both-backend contract sweep ──────────────────────────────────────


class TestAC7BothBackends:
    """AC7: API-Contract operations run against both Python and Rust CST classes.

    The Rust CST classes come from the standalone phase4_roundtrip_cst extension
    (constructed directly); the Python CST classes come from the pure-Python
    generated parser. The standalone fixture ships no Rust parser, so the full
    parse → unparse roundtrip is exercised on the pure-Python backend only.
    """

    @pytest.mark.parametrize(
        "cst_module,backend,expected_unknown",
        [
            (_python_pr.cst_module, "python", PyUnknownSpan),
            (_rust_cst, "rust", UnknownSpan),
        ],
        ids=["python", "rust"],
    )
    def test_construction_and_span(self, cst_module, backend, expected_unknown):  # noqa: ARG002
        Config = cst_module.Config
        node = Config()
        # Each backend has its own UnknownSpan type; compare by equality.
        assert node.span == expected_unknown
        s = _span(1, 2)
        node.span = s
        assert node.span == s

    @pytest.mark.parametrize(
        "cst_module,backend",
        [
            (_python_pr.cst_module, "python"),
            (_rust_cst, "rust"),
        ],
        ids=["python", "rust"],
    )
    def test_label_equality_and_hash(self, cst_module, backend):  # noqa: ARG002
        Operator = cst_module.Operator
        assert Operator.Label.ASSIGN == Operator.Label.ASSIGN
        assert Operator.Label.ASSIGN != Operator.Label.APPEND
        assert len({Operator.Label.ASSIGN, Operator.Label.APPEND, Operator.Label.REMOVE}) == 3

    @pytest.mark.parametrize(
        "cst_module,backend",
        [
            (_python_pr.cst_module, "python"),
            (_rust_cst, "rust"),
        ],
        ids=["python", "rust"],
    )
    def test_isinstance_dispatch(self, cst_module, backend):  # noqa: ARG002
        Config = cst_module.Config
        Entry = cst_module.Entry
        assert isinstance(Config(), Config)
        assert not isinstance(Config(), Entry)

    @pytest.mark.parametrize(
        "cst_module,backend",
        [
            (_python_pr.cst_module, "python"),
            (_rust_cst, "rust"),
        ],
        ids=["python", "rust"],
    )
    def test_children_list_protocol(self, cst_module, backend):  # noqa: ARG002
        Entry = cst_module.Entry
        Identifier = cst_module.Identifier
        node = Entry()
        node.append_key(Identifier())
        node.append_op(cst_module.Operator())
        node.append_value(cst_module.Literal())
        # Stride
        assert len(node.children[::2]) == 2
        assert len(node.children[1::2]) == 1
        # Negative index
        assert node.children[-1][0] == Entry.Label.VALUE

    def test_full_parse_roundtrip(self):
        """Full parse → CST → unparse roundtrip on the pure-Python backend."""
        ur = generate_unparser(_grammar, _python_pr.cst_module_name)
        result = parse_text(_python_pr, "key = 99;", "config")
        assert result.success, result.error_message
        doc = unparse_cst(ur, result.cst, result.terminals, "config")
        output = render_doc(doc)
        assert "key" in output and "99" in output

    def test_cross_cdylib_sourceless_span_accessor(self):
        """span_to_pyobject sourceless slow-path arm: a node with a sourceless span returns
        has_source() == False through the cross-cdylib accessor.

        This pins the None arm of span_to_pyobject's match on the slow (cross-cdylib) path.
        """
        Entry = _rust_cst.Entry
        node = Entry(span=Span(3, 7))
        s = node.span
        assert isinstance(s, Span)
        assert not s.has_source()
        assert s == Span(3, 7)
