"""Smoke tests for the fegen.fltkg Rust CST classes in fegen_rust_cst.cst.

Validates AC-7 (14 classes compile) and AC-8 (construction, label access, append/child
round-trip, children is a list). Tests are parameterized over all 14 classes.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fegen_rust_cst", reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first")

from fegen_rust_cst.cst import (
    Alternatives,
    BlockComment,
    Disposition,
    Grammar,
    Identifier,
    Item,
    Items,
    LineComment,
    Literal,
    Quantifier,
    RawString,
    Rule,
    Term,
    Trivia,
)

from fltk._native import SourceText, Span, UnknownSpan


def _span() -> Span:
    """Create a simple sourceless Span for use as a terminal child value."""
    return Span(0, 1)


# ---------------------------------------------------------------------------
# Catalogue: (class, label_for_Label_access, label_for_roundtrip, child_factory)
# label_for_Label_access: any label name (UPPERCASE) to test ClassName.Label.VARIANT
# label_for_roundtrip: method suffix (lowercase) for append_{l} / child_{l} round-trip
# child_factory: callable returning a valid child for append_{label_for_roundtrip}
# ---------------------------------------------------------------------------

# fmt: off
CLASS_LABEL_INFO = [
    # (class, label_for_Label_access, label_for_roundtrip, child_factory)
    # child_factory produces a valid child value for append_{label_for_roundtrip}.
    # Terminal children (regex/literal) → Span; rule-ref children → the referenced class.
    (Grammar,      "RULE",          "rule",         Rule),
    (Rule,         "NAME",          "name",         Identifier),   # name:identifier rule ref
    (Alternatives, "ITEMS",         "items",        Items),
    (Items,        "ITEM",          "item",         Item),
    (Item,         "LABEL",         "label",        Identifier),   # label:identifier rule ref
    (Term,         "IDENTIFIER",    "identifier",   Identifier),
    (Disposition,  "INCLUDE",       "include",      _span),        # literal terminal
    (Quantifier,   "OPTIONAL",      "optional",     _span),        # literal terminal
    (Identifier,   "NAME",          "name",         _span),        # regex terminal
    (RawString,    "VALUE",         "value",        _span),        # regex terminal
    (Literal,      "VALUE",         "value",        _span),        # literal terminal
    (Trivia,       "LINE_COMMENT",  "line_comment", LineComment),
    (LineComment,  "PREFIX",        "prefix",       _span),        # literal terminal
    (BlockComment, "START",         "start",        _span),        # literal terminal
]
# fmt: on

ALL_CLASSES = [cls for cls, _, _, _ in CLASS_LABEL_INFO]
ALL_CLASS_IDS = [cls.__name__ for cls, _, _, _ in CLASS_LABEL_INFO]


# ---------------------------------------------------------------------------
# AC-8a: Construction with default UnknownSpan
# ---------------------------------------------------------------------------


class TestConstructionDefaultSpan:
    @pytest.mark.parametrize("cls", ALL_CLASSES, ids=ALL_CLASS_IDS)
    def test_default_span_is_unknown(self, cls: type) -> None:
        """AC-8: Each class constructs with default span == UnknownSpan."""
        node = cls()
        assert node.span == UnknownSpan

    @pytest.mark.parametrize("cls", ALL_CLASSES, ids=ALL_CLASS_IDS)
    def test_explicit_span(self, cls: type) -> None:
        """Explicit span is stored correctly."""
        sp = Span(0, 5)
        node = cls(span=sp)
        assert node.span == sp
        assert node.span is not UnknownSpan


# ---------------------------------------------------------------------------
# AC-8b: children is a Python list
# ---------------------------------------------------------------------------


class TestChildrenIsList:
    @pytest.mark.parametrize("cls", ALL_CLASSES, ids=ALL_CLASS_IDS)
    def test_children_is_list(self, cls: type) -> None:
        """AC-8: node.children is a Python list for each class."""
        node = cls()
        assert isinstance(node.children, list)
        assert node.children == []


# ---------------------------------------------------------------------------
# AC-8c: Label access (ClassName.Label.VARIANT)
# ---------------------------------------------------------------------------


class TestLabelAccess:
    @pytest.mark.parametrize(
        "cls, variant_name",
        [(cls, label) for cls, label, _, _ in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_label_variant_accessible(self, cls: type, variant_name: str) -> None:
        """AC-8: ClassName.Label.VARIANT is accessible for at least one label per class."""
        label_enum = cls.Label
        variant = getattr(label_enum, variant_name)
        assert repr(variant) == f"{cls.__name__}.Label.{variant_name}"


# ---------------------------------------------------------------------------
# AC-8d: append_{label} / child_{label} round-trip
# ---------------------------------------------------------------------------


class TestAppendChildRoundtrip:
    @pytest.mark.parametrize(
        "cls, method_suffix, child_factory",
        [(cls, suffix, factory) for cls, _, suffix, factory in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_append_and_child_roundtrip(self, cls: type, method_suffix: str, child_factory) -> None:
        """AC-8: append_{label} then child_{label} returns a value-equal child."""
        parent = cls()
        child = child_factory()
        getattr(parent, f"append_{method_suffix}")(child)
        retrieved = getattr(parent, f"child_{method_suffix}")()
        # Use value equality (==), not identity (is): native storage clones on extraction.
        assert retrieved == child

    @pytest.mark.parametrize(
        "cls, method_suffix, child_factory",
        [(cls, suffix, factory) for cls, _, suffix, factory in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_children_label_returns_list(self, cls: type, method_suffix: str, child_factory) -> None:
        """AC-8: children_{label} returns a list containing value-equal appended children."""
        parent = cls()
        child1 = child_factory()
        child2 = child_factory()
        getattr(parent, f"append_{method_suffix}")(child1)
        getattr(parent, f"append_{method_suffix}")(child2)
        result = getattr(parent, f"children_{method_suffix}")()
        assert isinstance(result, list)
        assert len(result) == 2
        # Value equality (==) rather than identity (is): native storage clones on extraction.
        assert result[0] == child1
        assert result[1] == child2


# ---------------------------------------------------------------------------
# AC-8e: extend_{label} and maybe_{label} for fegen classes
# ---------------------------------------------------------------------------


class TestArcSharingNodeSpan:
    """§4 item 1: span accessor preserves Arc-sharing; multiple reads merge without ValueError.

    These tests verify the fix for the O(N) copy bug: span accessors must return a
    fltk._native.Span that shares the same source Arc as the node, so that two spans
    from the same node can be merged without "cannot merge spans from different sources".
    """

    def test_node_span_read_twice_merges(self):
        """Reading node.span twice yields spans that merge successfully (same source Arc)."""
        src = SourceText("hello world")
        node = Grammar(span=Span.with_source(0, 11, src))
        s1 = node.span
        s2 = node.span
        merged = s1.merge(s2)
        assert merged.text() == "hello world"

    def test_node_span_has_source(self):
        """node.span is source-bearing when node was constructed with a source-bearing span."""
        src = SourceText("hello world")
        node = Grammar(span=Span.with_source(0, 5, src))
        assert node.span.has_source()
        assert node.span.text() == "hello"

    def test_span_child_read_twice_merges(self):
        """A Span child read back through children/child_<label> twice merges without ValueError."""
        src = SourceText("hello world!")
        span1 = Span.with_source(0, 5, src)
        node = Identifier()
        node.append_name(span1)
        s1 = node.child_name()
        s2 = node.child_name()
        merged = s1.merge(s2)
        assert merged.text() == "hello"

    def test_span_child_merges_with_node_span(self):
        """A Span child from children_<label> merges with the node's .span."""
        src = SourceText("hello world!")
        node = Identifier(span=Span.with_source(0, 5, src))
        span_child = Span.with_source(0, 5, src)
        node.append_name(span_child)
        child_span = node.child_name()
        node_span = node.span
        merged = child_span.merge(node_span)
        assert merged.text() == "hello"

    def test_span_from_children_getter_merges(self):
        """Span retrieved via generic children list merges with another span from same source."""
        src = SourceText("hello world!")
        node = Identifier(span=Span.with_source(0, 12, src))
        node.append_name(Span.with_source(0, 5, src))
        # children returns list of (label, value) tuples
        _, child_span = node.children[0]
        node_span = node.span
        merged = child_span.merge(node_span)
        assert merged.text() == "hello world!"


class TestExtendAndMaybe:
    @pytest.mark.parametrize(
        "cls, method_suffix, child_factory",
        [(cls, suffix, factory) for cls, _, suffix, factory in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_extend_label_appends_children(self, cls: type, method_suffix: str, child_factory) -> None:
        """extend_{label} appends multiple children with the correct label."""
        parent = cls()
        child1 = child_factory()
        child2 = child_factory()
        getattr(parent, f"extend_{method_suffix}")([child1, child2])
        result = getattr(parent, f"children_{method_suffix}")()
        assert isinstance(result, list)
        assert len(result) == 2
        # Value equality (==) rather than identity (is): native storage clones on extraction.
        assert result[0] == child1
        assert result[1] == child2

    @pytest.mark.parametrize(
        "cls, method_suffix",
        [(cls, suffix) for cls, _, suffix, _ in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_maybe_label_returns_none_when_empty(self, cls: type, method_suffix: str) -> None:
        """maybe_{label} returns None when no matching child exists."""
        parent = cls()
        result = getattr(parent, f"maybe_{method_suffix}")()
        assert result is None

    @pytest.mark.parametrize(
        "cls, method_suffix, child_factory",
        [(cls, suffix, factory) for cls, _, suffix, factory in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_maybe_label_returns_child_when_one_match(self, cls: type, method_suffix: str, child_factory) -> None:
        """maybe_{label} returns a value-equal child when exactly one matching child exists."""
        parent = cls()
        child = child_factory()
        getattr(parent, f"append_{method_suffix}")(child)
        result = getattr(parent, f"maybe_{method_suffix}")()
        # Value equality (==) rather than identity (is): native storage clones on extraction.
        assert result == child

    @pytest.mark.parametrize(
        "cls, method_suffix, child_factory",
        [(cls, suffix, factory) for cls, _, suffix, factory in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_maybe_label_raises_when_two_matches(self, cls: type, method_suffix: str, child_factory) -> None:
        """maybe_{label} raises ValueError when two or more matching children exist."""
        parent = cls()
        child1 = child_factory()
        child2 = child_factory()
        getattr(parent, f"append_{method_suffix}")(child1)
        getattr(parent, f"append_{method_suffix}")(child2)
        with pytest.raises(ValueError, match="Expected at most one"):
            getattr(parent, f"maybe_{method_suffix}")()
