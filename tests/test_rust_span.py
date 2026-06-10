"""Tests for the Rust-backed Span backend (fltk._native)."""

import pytest

_native_module = pytest.importorskip("fltk._native", reason="Rust extension not available")

from fltk._native import SourceText, Span, UnknownSpan  # noqa: E402
from fltk._native.fegen_cst import Grammar  # noqa: E402


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
    def test_start_attribute_readable(self):
        # .start and .end are readable getters for drop-in parity with terminalsrc.Span.
        s = Span(1, 5)
        assert s.start == 1

    def test_end_attribute_readable(self):
        s = Span(1, 5)
        assert s.end == 5

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

    def test_unicode_codepoint_indices(self):
        # Span start/end are codepoint (Unicode character) indices, matching Python semantics.
        # "héllo": h=0, é=1, l=2, l=3, o=4  (5 codepoints; 'é' is 2 UTF-8 bytes)
        src = SourceText("héllo")
        # Codepoint slice [0:2] = "hé" (2 codepoints)
        assert Span.with_source(0, 2, src).text() == "hé"
        # Codepoint slice [1:2] = "é" (1 codepoint, 2 UTF-8 bytes)
        assert Span.with_source(1, 2, src).text() == "é"
        # Codepoint slice [0:5] = full string
        assert Span.with_source(0, 5, src).text() == "héllo"
        # Out-of-bounds codepoint index returns None
        assert Span.with_source(0, 6, src).text() is None


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


class TestAbiMarkerClassattr:
    """§4 item 3: SourceText._fltk_cst_core_abi classattr and Span._with_source_unchecked."""

    def test_source_text_abi_classattr_exists(self):
        """SourceText exposes _fltk_cst_core_abi as a class attribute, accessible via type(instance).

        extract_source_text reads obj.get_type().getattr("_fltk_cst_core_abi") — the type-of-instance
        path — so both the class-direct and type(instance) access paths must agree.
        """
        assert hasattr(SourceText, "_fltk_cst_core_abi")
        src = SourceText("hello")
        assert hasattr(type(src), "_fltk_cst_core_abi")
        assert type(src)._fltk_cst_core_abi == SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]

    def test_source_text_abi_classattr_is_string(self):
        """SourceText._fltk_cst_core_abi is a non-empty string."""
        marker = SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]
        assert isinstance(marker, str)
        assert len(marker) > 0

    def test_source_text_abi_classattr_contains_fltk_cst_core(self):
        """SourceText._fltk_cst_core_abi starts with 'fltk-cst-core/'."""
        marker = SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]
        assert marker.startswith("fltk-cst-core/")

    def test_span_to_pyobject_fast_path_arc_sharing(self):
        """span_to_pyobject fast path (same cdylib): fegen_cst nodes share Arc with their source.

        Exercises the Span::type_object(py).is(&span_type) branch of span_to_pyobject in
        cross_cdylib.rs: when the executing cdylib IS fltk._native, Py::new is used directly
        and the returned Span shares the original Arc. Two .span reads from the same node
        must merge without ValueError.
        """
        src = SourceText("hello world")
        node = Grammar(span=Span.with_source(0, 11, src))
        s1 = node.span
        s2 = node.span
        assert s1.has_source()
        merged = s1.merge(s2)
        assert merged.text() == "hello world"

    def test_with_source_unchecked_canonical_source_text(self):
        """Span._with_source_unchecked with a canonical (same-cdylib) SourceText works correctly."""
        src = SourceText("hello world")
        s = Span._with_source_unchecked(0, 5, src)  # type: ignore[attr-defined]
        assert s.text() == "hello"
        assert s.start == 0
        assert s.end == 5

    def test_with_source_unchecked_canonical_spans_merge(self):
        """Two spans built from the same SourceText via _with_source_unchecked merge successfully."""
        src = SourceText("hello world")
        s1 = Span._with_source_unchecked(0, 5, src)  # type: ignore[attr-defined]
        s2 = Span._with_source_unchecked(6, 11, src)  # type: ignore[attr-defined]
        merged = s1.merge(s2)
        assert merged.text() == "hello world"

    def test_with_source_unchecked_str_raises_type_error(self):
        """Span._with_source_unchecked with a plain str raises TypeError naming the type."""
        with pytest.raises(TypeError, match="fltk._native.SourceText"):
            Span._with_source_unchecked(0, 5, "hello world")  # type: ignore[attr-defined]

    def test_with_source_unchecked_no_marker_attr_raises_type_error(self):
        """An object with no _fltk_cst_core_abi attribute raises TypeError naming the type."""

        class NoMarker:
            pass

        with pytest.raises(TypeError, match="fltk._native.SourceText"):
            Span._with_source_unchecked(0, 5, NoMarker())  # type: ignore[attr-defined]

    def test_with_source_unchecked_non_str_marker_raises_type_error(self):
        """An object whose _fltk_cst_core_abi is a non-str raises TypeError naming the attribute type."""

        class IntMarker:
            _fltk_cst_core_abi = 42

        with pytest.raises(TypeError, match="_fltk_cst_core_abi"):
            Span._with_source_unchecked(0, 5, IntMarker())  # type: ignore[attr-defined]

    def test_with_source_unchecked_bogus_abi_marker_raises_type_error(self):
        """An object with _fltk_cst_core_abi = 'bogus/0.0.0' raises TypeError mentioning ABI mismatch."""

        class FakeSource:
            _fltk_cst_core_abi = "bogus/0.0.0"

        with pytest.raises(TypeError, match="ABI mismatch"):
            Span._with_source_unchecked(0, 5, FakeSource())  # type: ignore[attr-defined]

    def test_with_source_keeps_exact_behavior(self):
        """Public with_source still rejects foreign-cdylib SourceText (pinned behavior).

        Requires make build-test-user-ext; skipped if the fixture is not available.
        A CI lane where this test is always skipped is a gap, not a pass.
        """
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        foreign_st = phase4.SourceText("hello world")  # type: ignore[attr-defined]
        with pytest.raises(TypeError, match="SourceText"):
            Span.with_source(0, 5, foreign_st)

    def test_with_source_unchecked_foreign_cdylib_works(self):
        """Span._with_source_unchecked accepts a foreign-cdylib SourceText (the cross-cdylib case)."""
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        foreign_st = phase4.SourceText("hello world")  # type: ignore[attr-defined]
        s = Span._with_source_unchecked(0, 5, foreign_st)  # type: ignore[attr-defined]
        assert s.text() == "hello"

    def test_with_source_unchecked_foreign_spans_merge(self):
        """Two spans built from the same foreign SourceText via _with_source_unchecked merge successfully."""
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        foreign_st = phase4.SourceText("hello world")  # type: ignore[attr-defined]
        s1 = Span._with_source_unchecked(0, 5, foreign_st)  # type: ignore[attr-defined]
        s2 = Span._with_source_unchecked(6, 11, foreign_st)  # type: ignore[attr-defined]
        merged = s1.merge(s2)
        assert merged.text() == "hello world"
