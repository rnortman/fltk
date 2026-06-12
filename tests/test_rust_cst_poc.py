"""Tests for Phase 2 Rust CST PoC nodes: Identifier and Items."""

import pytest

_native_module = pytest.importorskip("fltk._native", reason="Rust extension not available")

from fltk._native import SourceText, Span, UnknownSpan  # noqa: E402
from fltk._native.poc_cst import Identifier, Items  # noqa: E402


def _span(start: int = 0, end: int = 1) -> Span:
    """Create a simple sourceless Span for use as test child values."""
    return Span(start, end)


class TestLabelSemantics:
    def test_label_identity_equality(self):
        """AC-1: Same-variant equality."""
        assert Identifier.Label.NAME == Identifier.Label.NAME

    def test_label_containment(self):
        """AC-2: Containment via __eq__."""
        assert Identifier.Label.NAME in (Identifier.Label.NAME,)

    def test_intra_class_discrimination(self):
        """AC-3: Different variants of the same enum are not equal."""
        assert Items.Label.ITEM != Items.Label.NO_WS

    def test_inter_class_discrimination(self):
        """AC-4: Labels from different enum types are not equal."""
        assert Identifier.Label.NAME != Items.Label.ITEM

    def test_label_hashability(self):
        """AC-5: Label instances are hashable and usable as dict keys."""
        h = hash(Identifier.Label.NAME)
        assert isinstance(h, int)
        d = {Identifier.Label.NAME: 1}
        assert d[Identifier.Label.NAME] == 1

    def test_label_not_equal_none(self):
        """PyO3 cross-type __richcmp__ must return NotImplemented for None, yielding False.
        This is load-bearing for None-label filtering in children_name etc."""
        assert Identifier.Label.NAME != None  # noqa: E711
        assert (Identifier.Label.NAME == None) is False  # noqa: E711


class TestChildrenListSemantics:
    def test_children_rebuilt_each_call(self):
        """Native children: node.children is rebuilt from the Vec on each call.
        The returned list need not be the same object on every access (§2.3 design)."""
        node = Identifier()
        a = node.children
        b = node.children
        # Both are empty lists with the same content; identity not guaranteed
        assert a == b
        assert isinstance(a, list)

    def test_children_getter_reflects_appended(self):
        """node.children reflects children appended via append/append_name."""
        node = Identifier()
        s = _span(0, 1)
        node.append_name(s)
        children = node.children
        assert len(children) == 1
        assert children[0][1] == s

    def test_cross_node_children_extend_via_method(self):
        """Use node.extend_name(b.children_name()) to extend a node with label-filtered children."""
        a = Identifier()
        b = Identifier()
        s1 = _span(0, 1)
        s2 = _span(1, 2)
        a.append_name(s1)
        b.append_name(s2)
        a.extend_name(b.children_name())
        assert len(a.children) == 2


class TestAppendAndAccessors:
    def test_children_tuple_structure(self):
        """AC-9: append_name produces a (Identifier.Label.NAME, child) tuple."""
        node = Identifier()
        s = _span()
        node.append_name(s)
        tup = node.children[0]
        assert len(tup) == 2
        assert tup[0] == Identifier.Label.NAME
        assert tup[1] == s

    def test_append_name_and_child_name(self):
        """AC-10: append_name + child_name round-trip; returns value, not (label, child) tuple."""
        node = Identifier()
        s = _span()
        node.append_name(s)
        result = node.child_name()
        assert result == s
        assert not isinstance(result, tuple)

    def test_extend_name_and_children_name(self):
        """AC-11: extend_name + children_name round-trip."""
        node = Identifier()
        s1 = _span(0, 1)
        s2 = _span(1, 2)
        node.extend_name([s1, s2])
        assert list(node.children_name()) == [s1, s2]

    def test_child_name_raises_on_empty(self):
        """AC-12: child_name() on empty node raises ValueError."""
        node = Identifier()
        with pytest.raises(ValueError, match="Expected one name child but have 0"):
            node.child_name()

    def test_maybe_name_returns_none_on_empty(self):
        """AC-13: maybe_name() on empty node returns None."""
        node = Identifier()
        assert node.maybe_name() is None

    def test_maybe_name_returns_child_on_one(self):
        """AC-14: maybe_name() with exactly one matching child returns it."""
        node = Identifier()
        s = _span()
        node.append_name(s)
        assert node.maybe_name() == s

    def test_maybe_name_raises_on_multiple(self):
        """AC-15: maybe_name() with more than one matching child raises ValueError."""
        node = Identifier()
        node.append_name(_span(0, 1))
        node.append_name(_span(1, 2))
        with pytest.raises(ValueError, match="Expected at most one name child but have at least 2"):
            node.maybe_name()


class TestGenericMethods:
    def test_generic_append_no_label(self):
        """AC-16: append(child) stores (None, child) in children."""
        node = Identifier()
        s = _span()
        node.append(s)
        tup = node.children[0]
        assert tup[0] is None
        assert tup[1] == s

    def test_generic_append_with_label(self):
        """AC-17: append(child, label=Identifier.Label.NAME) stores labeled tuple."""
        node = Identifier()
        s = _span()
        node.append(s, label=Identifier.Label.NAME)
        tup = node.children[0]
        assert tup[0] == Identifier.Label.NAME
        assert tup[1] == s

    def test_generic_extend(self):
        """AC-18: extend([c1, c2], label=...) appends two labeled tuples."""
        node = Identifier()
        s1 = _span(0, 1)
        s2 = _span(1, 2)
        node.extend([s1, s2], label=Identifier.Label.NAME)
        assert len(node.children) == 2
        assert node.children[0] == (Identifier.Label.NAME, s1)
        assert node.children[1] == (Identifier.Label.NAME, s2)

    def test_generic_child_one(self):
        """AC-19a: child() with exactly one child returns the (label, child) tuple."""
        node = Identifier()
        s = _span()
        node.append_name(s)
        tup = node.child()
        assert tup == (Identifier.Label.NAME, s)

    def test_generic_child_zero_raises(self):
        """AC-19b: child() with zero children raises ValueError."""
        node = Identifier()
        with pytest.raises(ValueError, match="Expected one child but have 0"):
            node.child()

    def test_generic_child_multiple_raises(self):
        """AC-19c: child() with more than one child raises ValueError."""
        node = Identifier()
        node.append_name(_span(0, 1))
        node.append_name(_span(1, 2))
        with pytest.raises(ValueError, match="Expected one child but have 2"):
            node.child()


class TestTypeIdentity:
    def test_isinstance_identifier(self):
        """AC-20a: Identifier instance passes isinstance(node, Identifier)."""
        node = Identifier()
        assert isinstance(node, Identifier)

    def test_not_isinstance_items(self):
        """AC-20b: Identifier instance fails isinstance(node, Items)."""
        node = Identifier()
        assert not isinstance(node, Items)

    def test_isinstance_items(self):
        """AC-20c: Items instance passes isinstance(node, Items)."""
        node = Items()
        assert isinstance(node, Items)

    def test_not_isinstance_identifier(self):
        """AC-20d: Items instance fails isinstance(node, Identifier)."""
        node = Items()
        assert not isinstance(node, Identifier)


class TestSpanField:
    def test_span_setter(self):
        """AC-21: Assigning node.span replaces the span."""
        node = Identifier()
        s = _span(5, 10)
        node.span = s
        assert node.span == s

    def test_span_default_is_unknown_span(self):
        """AC-22: Identifier() with no args has span == UnknownSpan."""
        node = Identifier()
        assert node.span == UnknownSpan

    def test_items_span_default_is_unknown_span(self):
        """AC-22 (Items): Items() with no args has span == UnknownSpan."""
        node = Items()
        assert node.span == UnknownSpan

    def test_span_keyword_construction_stores_provided_span(self):
        """Identifier(span=s) must store s, not UnknownSpan. Validates the
        keyword-only constructor path used by the parser."""
        s = _span(5, 10)
        node = Identifier(span=s)
        assert node.span == s
        assert node.span is not UnknownSpan

    def test_span_setter_rejects_non_span(self):
        """§4 item 3: Setting node.span to a non-Span Python object raises TypeError."""
        node = Identifier()
        with pytest.raises(TypeError):
            node.span = object()  # type: ignore[assignment]
        with pytest.raises(TypeError):
            node.span = "not a span"  # type: ignore[assignment]
        with pytest.raises(TypeError):
            node.span = 42  # type: ignore[assignment]

    def test_span_getter_returns_native_span(self):
        """§4 item 3: node.span returns a fltk._native.Span (not terminalsrc.Span)."""
        node = Identifier()
        s = _span(3, 7)
        node.span = s
        result = node.span
        assert isinstance(result, Span)
        assert result == s


class TestEquality:
    def test_equal_same_span_and_children(self):
        """AC-23a: Two nodes with identical span and children are equal."""
        s = _span()
        a = Identifier(span=s)
        b = Identifier(span=s)
        child = _span(2, 3)
        a.append_name(child)
        b.append_name(child)
        assert a == b

    def test_not_equal_different_children(self):
        """AC-23b: Nodes with different children are not equal."""
        s = _span()
        a = Identifier(span=s)
        b = Identifier(span=s)
        a.append_name(_span(0, 1))
        b.append_name(_span(1, 2))
        assert a != b

    def test_not_equal_different_spans(self):
        """AC-23c: Nodes with different spans are not equal."""
        a = Identifier(span=_span(0, 1))
        b = Identifier(span=_span(1, 2))
        assert a != b

    def test_not_equal_cross_type(self):
        """AC-23d: __eq__ returns NotImplemented for non-Identifier arguments,
        so Identifier != Items and Identifier != non-node types."""
        ident = Identifier()
        items = Items()
        assert ident != items
        assert ident != "string"
        assert ident != None  # noqa: E711
        assert ident != 42


class TestHashability:
    def test_node_unhashable(self):
        """AC-24: hash(node) raises TypeError."""
        node = Identifier()
        with pytest.raises(TypeError):
            hash(node)

    def test_items_node_unhashable(self):
        """AC-24 (Items): hash(Items()) raises TypeError."""
        node = Items()
        with pytest.raises(TypeError):
            hash(node)


class TestItemsMethods:
    """AC-25: All four Items label methods work correctly."""

    def _make_node(self) -> Items:
        return Items()

    def test_item_label(self):
        node = self._make_node()
        s = _span(0, 1)
        node.append_item(s)
        assert node.child_item() == s
        assert list(node.children_item()) == [s]
        assert node.maybe_item() == s

        node2 = self._make_node()
        assert node2.maybe_item() is None
        with pytest.raises(ValueError, match="Expected one item child but have 0"):
            node2.child_item()

        node.append_item(_span(1, 2))
        with pytest.raises(ValueError, match="Expected at most one item child but have at least 2"):
            node.maybe_item()

        node3 = self._make_node()
        node3.extend_item([_span(0, 1), _span(1, 2)])
        assert list(node3.children_item()) == [_span(0, 1), _span(1, 2)]

    def test_no_ws_label(self):
        node = self._make_node()
        s = _span(0, 1)
        node.append_no_ws(s)
        assert node.child_no_ws() == s
        assert list(node.children_no_ws()) == [s]
        assert node.maybe_no_ws() == s

        node2 = self._make_node()
        assert node2.maybe_no_ws() is None
        with pytest.raises(ValueError, match="Expected one no_ws child but have 0"):
            node2.child_no_ws()

        node.append_no_ws(_span(1, 2))
        with pytest.raises(ValueError, match="Expected at most one no_ws child but have at least 2"):
            node.maybe_no_ws()

        node3 = self._make_node()
        node3.extend_no_ws([_span(0, 1), _span(1, 2)])
        assert list(node3.children_no_ws()) == [_span(0, 1), _span(1, 2)]

    def test_ws_allowed_label(self):
        node = self._make_node()
        s = _span(0, 1)
        node.append_ws_allowed(s)
        assert node.child_ws_allowed() == s
        assert list(node.children_ws_allowed()) == [s]
        assert node.maybe_ws_allowed() == s

        node2 = self._make_node()
        assert node2.maybe_ws_allowed() is None
        with pytest.raises(ValueError, match="Expected one ws_allowed child but have 0"):
            node2.child_ws_allowed()

        node.append_ws_allowed(_span(1, 2))
        with pytest.raises(ValueError, match="Expected at most one ws_allowed child but have at least 2"):
            node.maybe_ws_allowed()

        node3 = self._make_node()
        node3.extend_ws_allowed([_span(0, 1), _span(1, 2)])
        assert list(node3.children_ws_allowed()) == [_span(0, 1), _span(1, 2)]

    def test_ws_required_label(self):
        node = self._make_node()
        s = _span(0, 1)
        node.append_ws_required(s)
        assert node.child_ws_required() == s
        assert list(node.children_ws_required()) == [s]
        assert node.maybe_ws_required() == s

        node2 = self._make_node()
        assert node2.maybe_ws_required() is None
        with pytest.raises(ValueError, match="Expected one ws_required child but have 0"):
            node2.child_ws_required()

        node.append_ws_required(_span(1, 2))
        with pytest.raises(ValueError, match="Expected at most one ws_required child but have at least 2"):
            node.maybe_ws_required()

        node3 = self._make_node()
        node3.extend_ws_required([_span(0, 1), _span(1, 2)])
        assert list(node3.children_ws_required()) == [_span(0, 1), _span(1, 2)]

    def test_label_constants_correct(self):
        """Verify label constants are accessible and distinct."""
        assert Items.Label.ITEM != Items.Label.NO_WS
        assert Items.Label.NO_WS != Items.Label.WS_ALLOWED
        assert Items.Label.WS_ALLOWED != Items.Label.WS_REQUIRED
        assert Items.Label.ITEM != Items.Label.WS_REQUIRED

    def test_cross_label_filtering(self):
        """children_item() must return only ITEM-labeled children, not NO_WS etc."""
        node = Items()
        s_item1 = _span(0, 1)
        s_no_ws = _span(1, 2)
        s_item2 = _span(2, 3)
        s_ws_allowed = _span(3, 4)
        node.append_item(s_item1)
        node.append_no_ws(s_no_ws)
        node.append_item(s_item2)
        node.append_ws_allowed(s_ws_allowed)
        assert list(node.children_item()) == [s_item1, s_item2]
        assert list(node.children_no_ws()) == [s_no_ws]
        assert list(node.children_ws_allowed()) == [s_ws_allowed]
        assert list(node.children_ws_required()) == []


class TestRepr:
    def test_identifier_repr_contains_class_name(self):
        """AC-26: repr(node) is non-empty and contains 'Identifier'."""
        node = Identifier()
        r = repr(node)
        assert r
        assert "Identifier" in r

    def test_items_repr_contains_class_name(self):
        """AC-26 (Items): repr(node) contains 'Items'."""
        node = Items()
        r = repr(node)
        assert r
        assert "Items" in r

    def test_label_repr_contains_class_and_variant(self):
        """Label repr must include class name and variant name."""
        r = repr(Identifier.Label.NAME)
        assert "Identifier" in r
        assert "NAME" in r

    def test_items_label_repr(self):
        r = repr(Items.Label.ITEM)
        assert "Items" in r
        assert "ITEM" in r


class TestSpanSourcePreservation:
    """Regression tests for rust-cst-span-getter-source-loss fix.

    Span getter and child span to_pyobject must preserve source from the native stored Span.
    """

    def _source_span(self, start: int, end: int, text: str) -> Span:
        """Create a source-bearing Span."""
        return Span.with_source(start, end, SourceText(text))

    def test_node_span_getter_preserves_source(self):
        """node.span getter returns a source-bearing Span when source was stored."""
        src = SourceText("hello world")
        s = Span.with_source(0, 5, src)
        node = Identifier(span=s)
        result = node.span
        assert result.has_source() is True
        assert result.text() == "hello"

    def test_node_span_getter_sourceless_stays_sourceless(self):
        """node.span getter returns sourceless Span when no source was stored."""
        s = Span(0, 5)
        node = Identifier(span=s)
        result = node.span
        assert result.has_source() is False

    def test_child_span_accessor_preserves_source(self):
        """Child span returned via label accessor retains source text from native storage."""
        src = SourceText("hello world")
        s = Span.with_source(6, 11, src)
        node = Identifier()
        node.append_name(s)
        result = node.child_name()
        assert result is not None
        assert isinstance(result, Span)
        assert result.has_source() is True
        assert result.text() == "world"

    def test_child_span_in_children_getter_preserves_source(self):
        """Child span accessed through node.children list retains source text."""
        src = SourceText("abcde")
        s = Span.with_source(1, 4, src)
        node = Identifier()
        node.append_name(s)
        children = node.children
        assert len(children) == 1
        _, child_span = children[0]
        assert isinstance(child_span, Span)
        assert child_span.has_source() is True
        assert child_span.text() == "bcd"


class TestNoneLabelFiltering:
    def test_unlabeled_child_excluded_from_children_name(self):
        """AC-27: children_name() excludes children appended with no label (None)."""
        node = Identifier()
        child_a = _span(0, 1)
        child_b = _span(1, 2)
        node.append(child_a)  # label=None
        node.append_name(child_b)
        assert list(node.children_name()) == [child_b]

    def test_extend_iterable_not_just_list(self):
        """extend and extend_name accept any iterable, not only lists."""
        node = Identifier()
        s1 = _span(0, 1)
        s2 = _span(1, 2)
        # Use a generator as the iterable
        node.extend_name(s for s in [s1, s2])
        assert list(node.children_name()) == [s1, s2]

        node2 = Identifier()
        node2.extend((s for s in [s1, s2]), label=Identifier.Label.NAME)
        assert list(node2.children_name()) == [s1, s2]


class TestFilterUnderGuardRegression:
    """Regression pin for rust-cst-accessor-clone-efficiency fix.

    Verifies that per-label accessors correctly filter by label when the children Vec
    contains many children spread across multiple labels (the old full-Vec-clone approach
    would have returned correct results but cloned all; the new approach must not
    accidentally include wrong-label children in the result).
    """

    def _make_items_with_mixed_labels(self) -> tuple["Items", list, list]:
        """Return an Items node with many item-labeled and no_ws-labeled children interleaved."""
        node = Items()
        item_spans = [_span(i * 2, i * 2 + 1) for i in range(5)]
        no_ws_spans = [_span(i * 2 + 1, i * 2 + 2) for i in range(5)]
        # Interleave: item, no_ws, item, no_ws, ...
        for i in range(5):
            node.append_item(item_spans[i])
            node.append_no_ws(no_ws_spans[i])
        return node, item_spans, no_ws_spans

    def test_children_label_filters_correctly(self):
        """children_item() returns only ITEM-labeled children; children_no_ws() the rest."""
        node, item_spans, no_ws_spans = self._make_items_with_mixed_labels()
        assert list(node.children_item()) == item_spans
        assert list(node.children_no_ws()) == no_ws_spans
        # Labels not used — must return empty list, not a subset of others
        assert list(node.children_ws_allowed()) == []
        assert list(node.children_ws_required()) == []

    def test_child_label_raises_with_exact_count(self):
        """child_<label> with multiple matching children reports the exact count."""
        node, item_spans, _ = self._make_items_with_mixed_labels()
        # 5 item children → count == 5
        with pytest.raises(ValueError, match="Expected one item child but have 5"):
            node.child_item()

    def test_maybe_label_raises_when_multiple(self):
        """maybe_<label> with >1 matching children raises the standard error."""
        node, _, _ = self._make_items_with_mixed_labels()
        with pytest.raises(ValueError, match="Expected at most one item child but have at least 2"):
            node.maybe_item()

    def test_generic_child_raises_with_exact_count(self):
        """child() with N children (N != 1) reports N in error message."""
        node, _, _ = self._make_items_with_mixed_labels()
        # 10 total children (5 item + 5 no_ws)
        with pytest.raises(ValueError, match="Expected one child but have 10"):
            node.child()

    def test_child_label_returns_unique_match(self):
        """child_<label> succeeds when exactly one child matches, ignoring non-matching entries."""
        node = Items()
        non_target = _span(0, 1)
        target = _span(1, 2)
        another_non_target = _span(2, 3)
        node.append_no_ws(non_target)
        node.append_item(target)
        node.append_no_ws(another_non_target)
        result = node.child_item()
        assert result == target

    def test_maybe_label_returns_unique_match(self):
        """maybe_<label> returns the sole match when exactly one child has that label."""
        node = Items()
        node.append_no_ws(_span(0, 1))
        target = _span(1, 2)
        node.append_item(target)
        node.append_no_ws(_span(2, 3))
        result = node.maybe_item()
        assert result == target

    def test_child_label_raises_when_zero_among_non_matching(self):
        """child_<label> raises with count==0 when node has only non-matching children."""
        node = Items()
        # Node has only no_ws children; zero item children
        node.append_no_ws(_span(0, 1))
        node.append_no_ws(_span(1, 2))
        with pytest.raises(ValueError, match="Expected one item child but have 0"):
            node.child_item()

    def test_maybe_label_returns_none_when_zero_among_non_matching(self):
        """maybe_<label> returns None when node has only non-matching children."""
        node = Items()
        # Node has only no_ws children; zero item children
        node.append_no_ws(_span(0, 1))
        node.append_no_ws(_span(1, 2))
        result = node.maybe_item()
        assert result is None

    def test_accessor_identity_registry_pin(self):
        """Reading the same node child twice via child_item() returns the same Python handle (registry pin).

        Node-typed children go through the WeakValueDictionary registry; the canonical handle
        should be returned on every read as long as at least one reference keeps it alive.
        The node-typed child is surrounded by non-matching Span children to exercise
        the filter-under-guard path in a mixed-Vec scenario.
        """
        node = Items()
        child_node = Identifier()
        # Surround the item child with non-matching no_ws children
        node.append_no_ws(_span(0, 1))
        node.append_item(child_node)
        node.append_no_ws(_span(2, 3))
        r1 = node.child_item()
        r2 = node.child_item()
        # Both must be equal and the same object (WeakValueDictionary canonical handle)
        assert r1 == r2
        assert r1 is r2
