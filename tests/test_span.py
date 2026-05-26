"""Tests for the pure-Python Span backend in fltk.fegen.pyrt.terminalsrc."""

import pytest

from fltk.fegen.pyrt.terminalsrc import Span, UnknownSpan


def test_construction_positional():
    s = Span(1, 5)
    assert s.start == 1
    assert s.end == 5


def test_construction_keyword():
    s = Span(start=1, end=5)
    assert s.start == 1
    assert s.end == 5


def test_construction_negative():
    s = Span(-1, -1)
    assert s.start == -1
    assert s.end == -1


def test_equality_equal():
    assert Span(1, 2) == Span(1, 2)


def test_equality_not_equal():
    assert Span(1, 2) != Span(1, 3)


def test_hash_consistent():
    assert hash(Span(1, 2)) == hash(Span(1, 2))


def test_hash_dict_lookup():
    d = {Span(1, 2): "x"}
    assert d[Span(1, 2)] == "x"


def test_repr():
    assert repr(Span(1, 5)) == "Span(start=1, end=5)"


def test_frozen():
    s = Span(1, 5)
    with pytest.raises((AttributeError, TypeError)):
        s.start = 5  # type: ignore[misc]


def test_unknown_span_equality():
    assert UnknownSpan == Span(-1, -1)


def test_unknown_span_start():
    assert UnknownSpan.start == -1


def test_with_source_text():
    s = Span.with_source(6, 11, "hello world")
    assert s.text() == "world"


def test_sourceless_text_none():
    assert Span(1, 5).text() is None


def test_text_or_raise_sourceless():
    with pytest.raises(ValueError):
        Span(1, 5).text_or_raise()


def test_text_or_raise_source_bearing():
    assert Span.with_source(0, 5, "hello").text_or_raise() == "hello"


def test_has_source_true():
    assert Span.with_source(0, 5, "hello").has_source() is True


def test_has_source_false():
    assert Span(1, 5).has_source() is False


def test_equality_ignores_source():
    assert Span.with_source(1, 5, "x" * 10) == Span(1, 5)


def test_hash_ignores_source():
    assert hash(Span.with_source(1, 5, "x" * 10)) == hash(Span(1, 5))


def test_negative_index_text_none():
    assert Span.with_source(-1, -1, "hello").text() is None


def test_out_of_bounds_text_none():
    assert Span.with_source(0, 999, "hello").text() is None


def test_unicode_codepoint_indices():
    # Python backend uses codepoint indices
    s = Span.with_source(1, 4, "héllo")
    assert s.text() == "éll"


def test_len_normal():
    assert Span(1, 5).len() == 4


def test_len_unknown():
    assert Span(-1, -1).len() == 0


def test_is_empty_zero_width():
    assert Span(5, 5).is_empty() is True


def test_is_empty_nonempty():
    assert Span(1, 5).is_empty() is False


def test_is_empty_negative():
    assert Span(-1, -1).is_empty() is True


def test_merge_sourceless():
    assert Span(1, 5).merge(Span(3, 8)) == Span(1, 8)


def test_merge_shared_source():
    src = "hello world"
    a = Span.with_source(0, 5, src)
    b = Span.with_source(6, 11, src)
    merged = a.merge(b)
    assert merged == Span(0, 11)
    assert merged.text() == "hello world"


def test_merge_different_sources_raises():
    a = Span.with_source(0, 5, "hello")
    b = Span.with_source(0, 5, "world")
    with pytest.raises(ValueError, match="cannot merge spans from different sources"):
        a.merge(b)


def test_merge_one_has_source():
    a = Span.with_source(0, 5, "hello world")
    b = Span(3, 8)
    merged = a.merge(b)
    assert merged.has_source()
    assert merged.text() == "hello wo"


def test_intersect_overlapping():
    assert Span(1, 5).intersect(Span(3, 8)) == Span(3, 5)


def test_intersect_disjoint():
    assert Span(1, 3).intersect(Span(5, 8)) == Span(-1, -1)


def test_intersect_adjacent_returns_unknown():
    assert Span(1, 5).intersect(Span(5, 8)) == Span(-1, -1)


def test_intersect_with_source():
    src = "hello world"
    a = Span.with_source(0, 7, src)
    b = Span.with_source(4, 11, src)
    result = a.intersect(b)
    assert result is not None
    assert result == Span(4, 7)
    assert result.text() == "o w"


def test_intersect_different_sources_raises():
    a = Span.with_source(0, 5, "hello")
    b = Span.with_source(3, 8, "world")
    with pytest.raises(ValueError, match="cannot merge spans from different sources"):
        a.intersect(b)


def test_empty_span_text():
    # Zero-width span returns empty string, not None
    s = Span.with_source(5, 5, "hello world")
    assert s.text() == ""
