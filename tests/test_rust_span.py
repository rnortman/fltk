"""Tests for the Rust-backed Span backend (fltk._native)."""

import subprocess
import sys

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


class TestSpanAbiMarkerClassattr:
    """Phase 0 §4.1 item 1: Span._fltk_cst_core_abi classattr (parallel to SourceText)."""

    def test_span_abi_classattr_exists(self):
        assert hasattr(Span, "_fltk_cst_core_abi")
        s = Span(0, 5)
        assert hasattr(type(s), "_fltk_cst_core_abi")
        assert type(s)._fltk_cst_core_abi == Span._fltk_cst_core_abi  # type: ignore[attr-defined]

    def test_span_abi_classattr_is_string(self):
        marker = Span._fltk_cst_core_abi  # type: ignore[attr-defined]
        assert isinstance(marker, str)
        assert len(marker) > 0

    def test_span_abi_classattr_starts_with_prefix(self):
        marker = Span._fltk_cst_core_abi  # type: ignore[attr-defined]
        assert marker.startswith("fltk-cst-core/")

    def test_span_and_source_text_abi_match(self):
        assert Span._fltk_cst_core_abi == SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]


class TestAbiLayoutClassattr:
    """Phase 0 §4.1 item 2: _fltk_cst_core_abi_layout classattr on Span and SourceText."""

    def test_span_abi_layout_exists(self):
        assert hasattr(Span, "_fltk_cst_core_abi_layout")

    def test_source_text_abi_layout_exists(self):
        assert hasattr(SourceText, "_fltk_cst_core_abi_layout")

    def test_span_abi_layout_is_positive_int(self):
        layout = Span._fltk_cst_core_abi_layout  # type: ignore[attr-defined]
        assert isinstance(layout, int)
        assert layout > 0

    def test_source_text_abi_layout_is_positive_int(self):
        layout = SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]
        assert isinstance(layout, int)
        assert layout > 0

    def test_span_abi_layout_accessible_via_instance_type(self):
        s = Span(0, 5)
        assert type(s)._fltk_cst_core_abi_layout == Span._fltk_cst_core_abi_layout  # type: ignore[attr-defined]

    def test_source_text_abi_layout_accessible_via_instance_type(self):
        src = SourceText("hello")
        assert type(src)._fltk_cst_core_abi_layout == SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]


class TestSpanPathAbiGate:
    """Phase 0 §4.1 item 1: ABI gate on the Span path (subprocess tests for GILOnceCell init).

    The ABI check fires once in get_span_type's GILOnceCell init, which is not resettable
    within a live process.  Subprocess tests ensure a fresh interpreter for each scenario.
    The cross-cdylib fixture (phase4_roundtrip_cst) is required; tests skip if unavailable.

    Note: GILOnceCell does NOT cache errors, so all three scenarios (wrong-ABI-string,
    wrong-layout, success) could in principle share one subprocess (run failures first,
    success last).  Each scenario has its own subprocess for isolation and readability.
    TODO(abi-gate-test-consolidation): if subprocess startup cost becomes significant,
    collapse to one subprocess driving all three scenarios sequentially.
    """

    @staticmethod
    def _run_script(script: str) -> subprocess.CompletedProcess[str]:
        """Run a Python script in a subprocess, return the completed process."""
        return subprocess.run(  # noqa: S603
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def test_control_no_patch_passes(self):
        """Control: without patching, a node span read from the consumer cdylib succeeds."""
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        del phase4  # only needed for skip check; real work is in subprocess

        script = """
import fltk._native as native  # ensure real module is loaded
# Control: no patch applied; verify the real Span is intact.
assert hasattr(native.Span, "_fltk_cst_core_abi"), "real Span missing ABI marker (unexpected)"
import phase4_roundtrip_cst as cst
node = cst.Config(span=cst.Span(0, 5))
s = node.span
# s is a fltk._native.Span (returned by span_to_pyobject slow path);
# check via repr since cross-cdylib == is not guaranteed for frozen pyo3 types
assert repr(s) == "Span(start=0, end=5)", f"unexpected span: {s!r}"
print("OK")
"""
        result = self._run_script(script)
        assert result.returncode == 0, f"subprocess failed: {result.stderr}"
        assert "OK" in result.stdout

    def test_abi_string_mismatch_raises_type_error(self):
        """Patching fltk._native.Span to have a wrong _fltk_cst_core_abi fires TypeError on first span cross."""
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        del phase4

        script = """
import fltk._native as native

class FakeSpan:
    _fltk_cst_core_abi = "wrong/0.0.0"
    _fltk_cst_core_abi_layout = native.Span._fltk_cst_core_abi_layout  # correct layout
    def __init__(self, *a, **kw): pass

native.Span = FakeSpan  # patch before first span boundary crossing
assert native.Span is FakeSpan, "patch did not take effect"

import phase4_roundtrip_cst as cst
node = cst.Config(span=cst.Span(0, 5))
try:
    s = node.span
    print(f"FAIL: no error, got {s!r}")
except TypeError as e:
    msg = str(e)
    assert "ABI mismatch" in msg, f"missing 'ABI mismatch' in: {msg!r}"
    assert "wrong/0.0.0" in msg, f"missing reported version in: {msg!r}"
    assert "fltk-cst-core/" in msg, f"missing expected version in: {msg!r}"
    print("OK")
"""
        result = self._run_script(script)
        assert result.returncode == 0, f"subprocess failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_layout_mismatch_raises_type_error(self):
        """Patching _fltk_cst_core_abi_layout to wrong value fires TypeError even with correct ABI string."""
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        del phase4

        script = """
import fltk._native as native

real_abi = native.Span._fltk_cst_core_abi  # correct string
real_layout = native.Span._fltk_cst_core_abi_layout  # correct layout (expected value)

class FakeSpan:
    _fltk_cst_core_abi = real_abi  # correct ABI string
    _fltk_cst_core_abi_layout = 999999  # wrong layout
    def __init__(self, *a, **kw): pass

native.Span = FakeSpan
assert native.Span is FakeSpan, "patch did not take effect"

import phase4_roundtrip_cst as cst
node = cst.Config(span=cst.Span(0, 5))
try:
    s = node.span
    print(f"FAIL: no error, got {s!r}")
except TypeError as e:
    msg = str(e)
    assert "layout mismatch" in msg.lower(), f"missing 'layout mismatch' in: {msg!r}"
    assert "999999" in msg, f"missing reported layout in: {msg!r}"
    assert str(real_layout) in msg, f"missing expected layout in: {msg!r}"
    print("OK")
"""
        result = self._run_script(script)
        assert result.returncode == 0, f"subprocess failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_missing_abi_marker_raises_type_error(self):
        """Patching fltk._native.Span to have no _fltk_cst_core_abi fires TypeError on first span cross.

        This is the most realistic skew scenario: a pre-Phase-0 fltk._native.Span build has
        no _fltk_cst_core_abi attribute at all.  The gate must treat the missing attribute as
        a mismatch (not a pass) and emit a diagnostic TypeError naming the expected marker.
        """
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        del phase4

        script = """
import fltk._native as native

class FakeSpan:
    # _fltk_cst_core_abi intentionally absent (pre-Phase-0 build simulation)
    _fltk_cst_core_abi_layout = native.Span._fltk_cst_core_abi_layout
    def __init__(self, *a, **kw): pass

native.Span = FakeSpan
assert native.Span is FakeSpan, "patch did not take effect"

import phase4_roundtrip_cst as cst
node = cst.Config(span=cst.Span(0, 5))
try:
    s = node.span
    print(f"FAIL: no error, got {s!r}")
except TypeError as e:
    msg = str(e)
    assert "pre-sentinel build" in msg, f"missing 'pre-sentinel build' in: {msg!r}"
    assert "fltk-cst-core/" in msg, f"missing expected version in: {msg!r}"
    print("OK")
"""
        result = self._run_script(script)
        assert result.returncode == 0, f"subprocess failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_missing_layout_attr_raises_type_error(self):
        """Patching fltk._native.Span to have no _fltk_cst_core_abi_layout fires TypeError on first span cross.

        Simulates a partial-upgrade build: ABI string present but layout probe absent.
        The gate must treat the missing layout attr as a mismatch (not a pass).
        """
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        del phase4

        script = """
import fltk._native as native

real_abi = native.Span._fltk_cst_core_abi

class FakeSpan:
    _fltk_cst_core_abi = real_abi
    # _fltk_cst_core_abi_layout intentionally absent (partial-upgrade build simulation)
    def __init__(self, *a, **kw): pass

native.Span = FakeSpan
assert native.Span is FakeSpan, "patch did not take effect"

import phase4_roundtrip_cst as cst
node = cst.Config(span=cst.Span(0, 5))
try:
    s = node.span
    print(f"FAIL: no error, got {s!r}")
except TypeError as e:
    msg = str(e)
    assert "partial-upgrade" in msg, f"missing 'partial-upgrade' in: {msg!r}"
    assert "fltk._native.Span" in msg, f"missing type name in: {msg!r}"
    print("OK")
"""
        result = self._run_script(script)
        assert result.returncode == 0, f"subprocess failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "OK" in result.stdout


class TestSpanToPyobjectCaching:
    """Phase 0 §4.1 item 3: boundary caching smoke tests for span_to_pyobject."""

    def test_repeated_span_reads_are_correct(self):
        """span_to_pyobject returns the correct value across repeated calls (caching is correct)."""
        src = SourceText("hello world")
        node = Grammar(span=Span.with_source(0, 11, src))
        results = [node.span for _ in range(5)]
        assert all(s == Span(0, 11) for s in results)
        assert all(s.has_source() for s in results)

    def test_repeated_span_reads_from_consumer_cdylib(self):
        """Repeated span reads via consumer cdylib return correct results (caches initialized once)."""
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        node = phase4.Config(span=phase4.Span(3, 7))  # type: ignore[attr-defined]
        results = [node.span for _ in range(5)]
        assert all(s == Span(3, 7) for s in results)

    def test_source_bearing_span_reads_from_consumer_cdylib(self):
        """WITH_SOURCE_UNCHECKED_METHOD cache: source-bearing spans from a consumer cdylib are correct across reads."""
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        src = phase4.SourceText("hello world")  # type: ignore[attr-defined]
        node = phase4.Config(span=phase4.Span.with_source(0, 11, src))  # type: ignore[attr-defined]
        results = [node.span for _ in range(5)]
        assert all(s == Span(0, 11) for s in results), f"unexpected spans: {results}"
        assert all(s.has_source() for s in results), "source-bearing spans should carry source"

    def test_source_text_abi_layout_mismatch_raises(self):
        """SourceText: _fltk_cst_core_abi_layout wrong int value raises TypeError naming both layouts."""

        class FakeSource:
            _fltk_cst_core_abi = SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]
            _fltk_cst_core_abi_layout = 999999

        with pytest.raises(TypeError, match="layout mismatch") as exc_info:
            Span._with_source_unchecked(0, 5, FakeSource())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        assert "999999" in msg, f"reported layout missing from error: {msg!r}"
        expected_layout = str(SourceText._fltk_cst_core_abi_layout)  # type: ignore[attr-defined]
        assert expected_layout in msg, f"expected layout missing from error: {msg!r}"

    def test_source_text_abi_layout_missing_raises(self):
        """SourceText: absent _fltk_cst_core_abi_layout (partial-upgrade build) raises TypeError."""

        class FakeSourceNoLayout:
            _fltk_cst_core_abi = SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]
            # _fltk_cst_core_abi_layout intentionally absent

        with pytest.raises(TypeError, match="_fltk_cst_core_abi_layout missing"):
            Span._with_source_unchecked(0, 5, FakeSourceNoLayout())  # type: ignore[attr-defined]

    def test_source_text_abi_layout_non_int_raises(self):
        """SourceText: non-int _fltk_cst_core_abi_layout raises TypeError naming the attr type."""

        class FakeSourceBadLayoutType:
            _fltk_cst_core_abi = SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]
            _fltk_cst_core_abi_layout = "not-an-int"

        with pytest.raises(TypeError, match="_fltk_cst_core_abi_layout attribute is"):
            Span._with_source_unchecked(0, 5, FakeSourceBadLayoutType())  # type: ignore[attr-defined]

    def test_source_text_abi_string_missing_raises(self):
        """SourceText: absent _fltk_cst_core_abi on a foreign-looking object raises TypeError."""

        class FakeSourceNoAbi:
            _fltk_cst_core_abi_layout = SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]
            # _fltk_cst_core_abi intentionally absent

        with pytest.raises(TypeError, match="expected fltk._native.SourceText"):
            Span._with_source_unchecked(0, 5, FakeSourceNoAbi())  # type: ignore[attr-defined]

    def test_source_text_fast_path_succeeds(self):
        """SourceText in-process fast path (downcast): canonical SourceText is accepted immediately.

        The canonical SourceText hits the `downcast::<SourceText>()` fast path in
        extract_source_text, bypassing all ABI checks.  Cross-cdylib slow-path success
        (all markers correct, full ABI validation passing) is covered by
        test_source_bearing_span_reads_from_consumer_cdylib above (a forged-marker fake
        object cannot be used safely — downcast_unchecked on non-SourceText data is UB).
        """
        src = SourceText("hello")
        result = Span._with_source_unchecked(0, 5, src)  # type: ignore[attr-defined]
        assert result == Span(0, 5)
        assert result.has_source()
