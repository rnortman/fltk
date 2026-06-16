"""Tests for the pure-Python Span backend in fltk.fegen.pyrt.terminalsrc."""

import pytest

from fltk.fegen.pyrt.terminalsrc import LineColPos, SourceText, Span, TerminalSource, UnknownSpan


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


def test_with_source_text_object():
    st = SourceText("hello world")
    s = Span.with_source(6, 11, st)
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


# ── filename tests ──────────────────────────────────────────────────────────


def test_filename_from_source_text():
    """SourceText with filename propagates to span via with_source."""
    st = SourceText("hello", filename="test.fltkg")
    span = Span.with_source(0, 5, st)
    assert span.filename() == "test.fltkg"


def test_filename_none_when_no_filename():
    """SourceText without filename → span.filename() == None."""
    st = SourceText("hello")
    span = Span.with_source(0, 5, st)
    assert span.filename() is None


def test_filename_none_sourceless():
    """Sourceless span → span.filename() == None."""
    span = Span(0, 5)
    assert span.filename() is None


def test_filename_none_str_source():
    """Span built with bare str (no SourceText) → span.filename() == None."""
    span = Span.with_source(0, 5, "hello")
    assert span.filename() is None


def test_equality_unchanged_by_different_filenames():
    """Spans with same start/end but different filenames still compare equal (compare=False)."""
    st1 = SourceText("hello", filename="a.fltkg")
    st2 = SourceText("hello", filename="b.fltkg")
    s1 = Span.with_source(0, 5, st1)
    s2 = Span.with_source(0, 5, st2)
    assert s1 == s2


def test_hash_unchanged_by_filename():
    """Hash is unaffected by filename (hash=False on _source_filename)."""
    st1 = SourceText("hello", filename="a.fltkg")
    st2 = SourceText("hello", filename="b.fltkg")
    s1 = Span.with_source(0, 5, st1)
    s2 = Span.with_source(0, 5, st2)
    assert hash(s1) == hash(s2)


# ── line_col tests ──────────────────────────────────────────────────────────


def test_line_col_sourceless_returns_none():
    """Sourceless span → line_col() returns None."""
    assert Span(0, 5).line_col() is None


def test_line_col_negative_start_returns_none():
    """Span with start < 0 → line_col() returns None even with source."""
    st = SourceText("hello")
    span = Span.with_source(-1, 0, st)
    assert span.line_col() is None


def test_line_col_out_of_domain_returns_none():
    """start > len(source) → line_col() returns None."""
    st = SourceText("hello")
    span = Span.with_source(10, 11, st)
    assert span.line_col() is None


def test_line_col_first_line():
    """line_col at start of first line: line=0, col=0."""
    st = SourceText("hello\nworld")
    span = Span.with_source(0, 1, st)
    lc = span.line_col()
    assert lc is not None
    assert lc.line == 0
    assert lc.col == 0


def test_line_col_mid_first_line():
    """line_col mid-first-line: line=0, col=3."""
    st = SourceText("hello\nworld")
    span = Span.with_source(3, 4, st)
    lc = span.line_col()
    assert lc is not None
    assert lc.line == 0
    assert lc.col == 3


def test_line_col_second_line():
    """line_col at start of second line: line=1, col=0."""
    st = SourceText("hello\nworld")
    span = Span.with_source(6, 7, st)
    lc = span.line_col()
    assert lc is not None
    assert lc.line == 1
    assert lc.col == 0


def test_line_col_empty_source():
    """Empty source: start=0==len, EOF clamp fires, col=-1 (inherited algorithm, design §3).

    With source='', len=0, start=0: EOF clamp gives pos=start-1=-1.
    The sentinel pushed for empty text is -1, so col=-1 is the documented result.
    Returns LineColPos (not None) because start==len is in-domain (clamped, not rejected).
    """
    st = SourceText("")
    span = Span.with_source(0, 0, st)
    lc = span.line_col()
    assert lc is not None, "Empty source with start=0 should return LineColPos, not None"
    assert lc.line == 0
    assert lc.col == -1


def test_line_col_eof_clamp():
    """start == len(source) is clamped to len-1."""
    text = "abc"
    st = SourceText(text)
    span = Span.with_source(len(text), len(text), st)
    lc = span.line_col()
    assert lc is not None
    # Should match pos len-1 = 2
    lc2 = Span.with_source(2, 3, st).line_col()
    assert lc2 is not None
    assert lc.line == lc2.line
    assert lc.col == lc2.col


def test_line_col_line_span_is_source_bearing():
    """line_col().line_span is source-bearing and covers the full line including last char.

    For "hello\nworld" the last line has no trailing newline so the sentinel is `len` (11),
    giving line_span = Span(6, 11) and text = "world" (all 5 characters).
    """
    st = SourceText("hello\nworld")
    span = Span.with_source(6, 7, st)
    lc = span.line_col()
    assert lc is not None
    assert lc.line_span.has_source()  # source-bearing is the key property
    # line_span covers the full last line: sentinel = len = 11.
    assert lc.line_span.start == 6
    assert lc.line_span.end == 11
    assert lc.line_span.text() == "world"


def test_line_col_line_span_source_bearing_first_line():
    """line_col() on first line: line_span is source-bearing."""
    st = SourceText("hello\nworld")
    span = Span.with_source(2, 3, st)
    lc = span.line_col()
    assert lc is not None
    assert lc.line_span.has_source()
    # "hello\nworld": '\n' is at index 5, so line_span = Span(0, 5)
    assert lc.line_span.start == 0
    assert lc.line_span.end == 5
    assert lc.line_span.text() == "hello"


def test_line_col_multibyte():
    """Multibyte source: column counts codepoints, not bytes."""
    # "café\nrésumé": 'é' in café is codepoint 3
    st = SourceText("café\nrésumé")
    span = Span.with_source(3, 4, st)
    lc = span.line_col()
    assert lc is not None
    assert lc.line == 0
    assert lc.col == 3


def test_line_col_tab_counts_as_one():
    """Tab counts as one codepoint column."""
    st = SourceText("a\tb")
    span = Span.with_source(2, 3, st)  # 'b' at codepoint 2
    lc = span.line_col()
    assert lc is not None
    assert lc.col == 2


def test_line_col_or_raise_sourceless_raises():
    """line_col_or_raise() raises ValueError for sourceless span."""
    with pytest.raises(ValueError, match="has no source"):
        Span(0, 5).line_col_or_raise()


def test_line_col_or_raise_negative_raises():
    """line_col_or_raise() raises ValueError for span with negative start."""
    with pytest.raises(ValueError, match="negative"):
        Span.with_source(-1, 0, SourceText("hello")).line_col_or_raise()


def test_line_col_or_raise_out_of_bounds_raises():
    """line_col_or_raise() raises ValueError when start > len(source)."""
    with pytest.raises(ValueError, match="out of bounds"):
        Span.with_source(100, 101, SourceText("hello")).line_col_or_raise()


def test_line_col_or_raise_valid_returns_line_col_pos():
    """line_col_or_raise() returns LineColPos for a valid span."""
    st = SourceText("hello\nworld")
    span = Span.with_source(6, 7, st)
    lc = span.line_col_or_raise()
    assert isinstance(lc, LineColPos)
    assert lc.line == 1
    assert lc.col == 0


def test_line_col_parity_with_terminalsrc_pos_to_line_col():
    """Span.line_col() agrees with TerminalSource.pos_to_line_col() on line, col, and line_span.start.

    Both implementations now use sentinel = len (exclusive past-end) for the final line when
    there is no trailing newline, so line_span.end agrees on both paths. We use text ending
    with '\n' here to additionally confirm that the newline-terminated case (no sentinel push)
    also produces identical results.
    """
    # Text ending with '\n' so sentinel behavior is identical between the two implementations.
    text = "hello\nworld\ncafé\n"
    ts = TerminalSource(text)
    src = SourceText(text)
    for pos in [0, 3, 6, 10, 12, 14]:
        span = Span.with_source(pos, pos + 1, src)
        lc_span = span.line_col()
        lc_ts = ts.pos_to_line_col(pos)
        assert lc_span is not None, f"span.line_col() returned None at pos={pos}"
        assert lc_span.line == lc_ts.line, f"line mismatch at pos={pos}"
        assert lc_span.col == lc_ts.col, f"col mismatch at pos={pos}"
        assert lc_span.line_span.start == lc_ts.line_span.start, f"line_span.start mismatch at pos={pos}"
        assert lc_span.line_span.end == lc_ts.line_span.end, f"line_span.end mismatch at pos={pos}"


def test_line_col_negative_diverges_from_pos_to_line_col():
    """Span with start=-1 returns line_col()=None while TerminalSource.pos_to_line_col(-1) still returns a value.

    Pins the deliberate divergence: the new span-level guard returns None for any negative start,
    while the unguarded legacy pos_to_line_col accepts -1 as a sentinel and returns col=-1.
    """
    ts = TerminalSource("abc")
    # Legacy: -1 is accepted
    lc_legacy = ts.pos_to_line_col(-1)
    assert lc_legacy.line == 0
    assert lc_legacy.col == -1

    # New span method: -1 → None (guard fires before any bisect)
    src = SourceText("abc")
    span = Span.with_source(-1, 0, src)
    assert span.line_col() is None, "span.line_col() should return None for negative start"
