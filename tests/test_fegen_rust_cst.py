"""Smoke tests for the fegen.fltkg Rust CST classes compiled into fltk._native.fegen_cst.

Validates AC-7 (14 classes compile) and AC-8 (construction, label access, append/child
round-trip, children is a list). Tests are parameterized over all 14 classes.
"""

from __future__ import annotations

import pytest

from fltk._native import Span, UnknownSpan
from fltk._native.fegen_cst import (
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

# ---------------------------------------------------------------------------
# Catalogue: (class, label_for_Label_access, label_for_roundtrip)
# label_for_Label_access: any label name (UPPERCASE) to test ClassName.Label.VARIANT
# label_for_roundtrip: method suffix (lowercase) for append_{l} / child_{l} round-trip
# ---------------------------------------------------------------------------

# fmt: off
CLASS_LABEL_INFO = [
    (Grammar,      "RULE",          "rule"),
    (Rule,         "NAME",          "name"),
    (Alternatives, "ITEMS",         "items"),
    (Items,        "ITEM",          "item"),
    (Item,         "LABEL",         "label"),
    (Term,         "IDENTIFIER",    "identifier"),
    (Disposition,  "INCLUDE",       "include"),
    (Quantifier,   "OPTIONAL",      "optional"),
    (Identifier,   "NAME",          "name"),
    (RawString,    "VALUE",         "value"),
    (Literal,      "VALUE",         "value"),
    (Trivia,       "LINE_COMMENT",  "line_comment"),
    (LineComment,  "PREFIX",        "prefix"),
    (BlockComment, "START",         "start"),
]
# fmt: on

ALL_CLASSES = [cls for cls, _, _ in CLASS_LABEL_INFO]
ALL_CLASS_IDS = [cls.__name__ for cls, _, _ in CLASS_LABEL_INFO]


# ---------------------------------------------------------------------------
# AC-7: All 14 classes importable
# ---------------------------------------------------------------------------


class TestAllClassesImportable:
    @pytest.mark.parametrize("cls", ALL_CLASSES, ids=ALL_CLASS_IDS)
    def test_class_is_type(self, cls: type) -> None:
        """AC-7: Each class is a real Python type (importable and callable)."""
        # TODO(test-class-is-type-body): `isinstance(cls, type)` passes for any
        # imported class including a misimported alias. Import success is the real
        # AC-7 check; a construction test (cls()) would be stronger. The AC-8a
        # tests already cover construction for all 14 classes.
        assert isinstance(cls, type)


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
        [(cls, label) for cls, label, _ in CLASS_LABEL_INFO],
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
        "cls, method_suffix",
        [(cls, suffix) for cls, _, suffix in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_append_and_child_roundtrip(self, cls: type, method_suffix: str) -> None:
        """AC-8: append_{label} then child_{label} returns the same object."""
        parent = cls()
        child = cls()  # use same type as child; any PyObject is fine
        getattr(parent, f"append_{method_suffix}")(child)
        retrieved = getattr(parent, f"child_{method_suffix}")()
        assert retrieved is child

    @pytest.mark.parametrize(
        "cls, method_suffix",
        [(cls, suffix) for cls, _, suffix in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_children_label_returns_list(self, cls: type, method_suffix: str) -> None:
        """AC-8: children_{label} returns a list containing appended children."""
        parent = cls()
        child1 = cls()
        child2 = cls()
        getattr(parent, f"append_{method_suffix}")(child1)
        getattr(parent, f"append_{method_suffix}")(child2)
        result = getattr(parent, f"children_{method_suffix}")()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] is child1
        assert result[1] is child2


# ---------------------------------------------------------------------------
# AC-8e: extend_{label} and maybe_{label} for fegen classes
# ---------------------------------------------------------------------------


class TestExtendAndMaybe:
    @pytest.mark.parametrize(
        "cls, method_suffix",
        [(cls, suffix) for cls, _, suffix in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_extend_label_appends_children(self, cls: type, method_suffix: str) -> None:
        """extend_{label} appends multiple children with the correct label."""
        parent = cls()
        child1 = cls()
        child2 = cls()
        getattr(parent, f"extend_{method_suffix}")([child1, child2])
        result = getattr(parent, f"children_{method_suffix}")()
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0] is child1
        assert result[1] is child2

    @pytest.mark.parametrize(
        "cls, method_suffix",
        [(cls, suffix) for cls, _, suffix in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_maybe_label_returns_none_when_empty(self, cls: type, method_suffix: str) -> None:
        """maybe_{label} returns None when no matching child exists."""
        parent = cls()
        result = getattr(parent, f"maybe_{method_suffix}")()
        assert result is None

    @pytest.mark.parametrize(
        "cls, method_suffix",
        [(cls, suffix) for cls, _, suffix in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_maybe_label_returns_child_when_one_match(self, cls: type, method_suffix: str) -> None:
        """maybe_{label} returns the child when exactly one matching child exists."""
        parent = cls()
        child = cls()
        getattr(parent, f"append_{method_suffix}")(child)
        result = getattr(parent, f"maybe_{method_suffix}")()
        assert result is child

    @pytest.mark.parametrize(
        "cls, method_suffix",
        [(cls, suffix) for cls, _, suffix in CLASS_LABEL_INFO],
        ids=ALL_CLASS_IDS,
    )
    def test_maybe_label_raises_when_two_matches(self, cls: type, method_suffix: str) -> None:
        """maybe_{label} raises ValueError when two or more matching children exist."""
        parent = cls()
        child1 = cls()
        child2 = cls()
        getattr(parent, f"append_{method_suffix}")(child1)
        getattr(parent, f"append_{method_suffix}")(child2)
        with pytest.raises(ValueError, match="Expected at most one"):
            getattr(parent, f"maybe_{method_suffix}")()
