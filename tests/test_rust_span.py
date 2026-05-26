"""Tests for the Rust-backed Span backend (fltk._native)."""

import pytest

_native_module = pytest.importorskip("fltk._native", reason="Rust extension not available")

from fltk._native import SourceText, Span, UnknownSpan  # noqa: E402


class TestConstruction:
    def test_positional(self):
        s = Span(1, 5)
        assert s.__repr__() == "Span(start=1, end=5)"

    def test_keyword(self):
        s = Span(start=1, end=5)
        assert s.__repr__() == "Span(start=1, end=5)"

    def test_negative_values(self):
        s = Span(-1, -1)
        assert s == UnknownSpan

    def test_type_error_on_string_args(self):
        with pytest.raises(TypeError):
            Span("a", "b")


class TestEquality:
    def test_equal_same_coords(self):
        assert Span(1, 2) == Span(1, 2)

    def test_unequal_diff_end(self):
        assert Span(1, 2) != Span(1, 3)

    def test_unequal_diff_start(self):
        assert Span(1, 2) != Span(2, 2)


class TestHash:
    def test_same_hash_same_coords(self):
        assert hash(Span(1, 2)) == hash(Span(1, 2))

    def test_usable_as_dict_key(self):
        d = {Span(1, 2): "x"}
        assert d[Span(1, 2)] == "x"

    def test_hash_ignores_source(self):
        src = SourceText("hello world")
        assert hash(Span.with_source(1, 5, src)) == hash(Span(1, 5))


class TestRepr:
    def test_repr(self):
        assert repr(Span(1, 5)) == "Span(start=1, end=5)"

    def test_repr_negative(self):
        assert repr(Span(-1, -1)) == "Span(start=-1, end=-1)"


class TestFrozen:
    def test_no_start_attribute(self):
        s = Span(1, 5)
        with pytest.raises(AttributeError):
            _ = s.start  # type: ignore[attr-defined]

    def test_no_end_attribute(self):
        s = Span(1, 5)
        with pytest.raises(AttributeError):
            _ = s.end  # type: ignore[attr-defined]

    def test_assignment_raises(self):
        s = Span(1, 5)
        with pytest.raises(AttributeError):
            s.start = 5  # type: ignore[misc]


class TestUnknownSpan:
    def test_unknown_equals_neg1_neg1(self):
        assert UnknownSpan == Span(-1, -1)

    def test_unknown_repr(self):
        assert repr(UnknownSpan) == "Span(start=-1, end=-1)"


class TestSourceBearingSpan:
    def test_with_source_text(self):
        src = SourceText("hello world")
        s = Span.with_source(6, 11, src)
        assert s.text() == "world"

    def test_sourceless_text_is_none(self):
        assert Span(1, 5).text() is None

    def test_text_or_raise_sourceless(self):
        with pytest.raises(ValueError):
            Span(1, 5).text_or_raise()

    def test_text_or_raise_source_bearing(self):
        src = SourceText("hello")
        assert Span.with_source(0, 5, src).text_or_raise() == "hello"

    def test_has_source_true(self):
        src = SourceText("hello")
        assert Span.with_source(0, 5, src).has_source() is True

    def test_has_source_false(self):
        assert Span(1, 5).has_source() is False

    def test_equality_ignores_source(self):
        src = SourceText("x" * 10)
        assert Span.with_source(1, 5, src) == Span(1, 5)

    def test_negative_index_text_is_none(self):
        src = SourceText("hello")
        assert Span.with_source(-1, -1, src).text() is None

    def test_out_of_bounds_text_is_none(self):
        src = SourceText("hello")
        assert Span.with_source(0, 999, src).text() is None

    def test_empty_span_text(self):
        src = SourceText("hello")
        assert Span.with_source(2, 2, src).text() == ""

    def test_unicode_byte_indices(self):
        # "é" is 2 bytes in UTF-8: 0xC3 0xA9
        # "héllo": h=0, é=1..3, l=3, l=4, o=5
        src = SourceText("héllo")
        assert Span.with_source(0, 3, src).text() == "hé"
        assert Span.with_source(1, 3, src).text() == "é"
        # byte 2 is mid-codepoint for é: not a char boundary
        assert Span.with_source(1, 2, src).text() is None


class TestLen:
    def test_len_positive(self):
        assert Span(1, 5).len() == 4

    def test_len_unknown(self):
        assert Span(-1, -1).len() == 0

    def test_len_zero_width(self):
        assert Span(3, 3).len() == 0


class TestIsEmpty:
    def test_zero_width_is_empty(self):
        assert Span(5, 5).is_empty() is True

    def test_nonempty(self):
        assert Span(1, 5).is_empty() is False

    def test_unknown_span_is_empty(self):
        assert Span(-1, -1).is_empty() is True


class TestMerge:
    def test_merge_sourceless(self):
        assert Span(1, 5).merge(Span(3, 8)) == Span(1, 8)

    def test_merge_same_source(self):
        src = SourceText("hello world")
        a = Span.with_source(0, 5, src)
        b = Span.with_source(6, 11, src)
        merged = a.merge(b)
        assert merged == Span(0, 11)
        assert merged.has_source()
        assert merged.text() == "hello world"

    def test_merge_different_sources_raises(self):
        src1 = SourceText("hello")
        src2 = SourceText("hello")
        a = Span.with_source(0, 5, src1)
        b = Span.with_source(0, 5, src2)
        with pytest.raises(ValueError, match="cannot merge spans from different sources"):
            a.merge(b)

    def test_merge_one_has_source(self):
        src = SourceText("hello world")
        a = Span.with_source(0, 5, src)
        b = Span(3, 8)
        merged = a.merge(b)
        assert merged == Span(0, 8)
        assert merged.has_source()


class TestIntersect:
    def test_intersect_overlapping(self):
        assert Span(1, 5).intersect(Span(3, 8)) == Span(3, 5)

    def test_intersect_disjoint_returns_unknown(self):
        assert Span(1, 3).intersect(Span(5, 8)) == UnknownSpan

    def test_intersect_adjacent_returns_unknown(self):
        assert Span(1, 5).intersect(Span(5, 8)) == UnknownSpan

    def test_intersect_with_source(self):
        src = SourceText("hello world")
        a = Span.with_source(0, 7, src)
        b = Span.with_source(4, 11, src)
        result = a.intersect(b)
        assert result is not None
        assert result == Span(4, 7)
        assert result.text() == "o w"

    def test_intersect_different_sources_raises(self):
        src1 = SourceText("hello")
        src2 = SourceText("world")
        a = Span.with_source(0, 5, src1)
        b = Span.with_source(3, 5, src2)
        with pytest.raises(ValueError, match="cannot merge spans from different sources"):
            a.intersect(b)


class TestImportPaths:
    def test_all_names_importable(self):
        assert _native_module.Span is Span
        assert _native_module.UnknownSpan == Span(-1, -1)
        assert _native_module.SourceText is SourceText


class TestSourceTextOpaque:
    def test_construction(self):
        src = SourceText("hello")
        assert isinstance(src, SourceText)

    def test_no_text_attribute(self):
        src = SourceText("hello")
        # SourceText should not expose text content directly
        with pytest.raises(AttributeError):
            _ = src.text  # type: ignore[attr-defined]
