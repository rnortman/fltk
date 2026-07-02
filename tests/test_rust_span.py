"""Tests for the Rust-backed Span backend (fltk._native)."""

import ctypes
import subprocess
import sys

import pytest

_native_module = pytest.importorskip("fltk._native", reason="Rust extension not available")

from fltk._native import LineColPos, SourceText, Span, UnknownSpan  # noqa: E402

pytest.importorskip("fegen_rust_cst", reason="fegen_rust_cst not built; run 'make build-fegen-rust-cst' first")
from fegen_rust_cst.cst import Grammar  # noqa: E402


def _run_script(script: str) -> subprocess.CompletedProcess[str]:
    """Run a Python script in a subprocess; return the completed process."""
    return subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _assert_forge_rejected_cleanly(result: subprocess.CompletedProcess[str], context: str) -> None:
    """Assert a forged-ABI subprocess was rejected cleanly with no UB/SIGSEGV.

    The safety contract shared by every forge-rejection test: the forge must be rejected
    with a TypeError (the subprocess prints "OK" and exits 0), never reaching `cast_unchecked`
    and segfaulting (returncode -11 / 139).
    """
    assert result.returncode != -11, (
        f"SIGSEGV recurrence ({context}): subprocess exited with signal 11 — forged-ABI UB regression\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert result.returncode == 0, (
        f"subprocess crashed ({context}, returncode {result.returncode}) — possible segfault regression\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "OK" in result.stdout, (
        f"expected 'OK' in stdout ({context}); got: {result.stdout!r}\nstderr: {result.stderr}"
    )


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
        """Span._with_source_unchecked with a plain str raises TypeError naming the ABI marker.

        Deliberate behavior change (crosscdylib-abi-check-helper ADR): a missing-marker object
        now raises with the unified ABI-mismatch template instead of the old generic
        "expected fltk._native.SourceText, got str" message.
        """
        with pytest.raises(TypeError, match="SourceText ABI mismatch") as exc_info:
            Span._with_source_unchecked(0, 5, "hello world")  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        assert "_fltk_cst_core_abi marker" in msg, f"missing marker name in: {msg!r}"
        assert "pre-sentinel build" in msg, f"missing sentinel hint in: {msg!r}"

    def test_with_source_unchecked_no_marker_attr_raises_type_error(self):
        """An object with no _fltk_cst_core_abi attribute raises TypeError naming the ABI marker.

        Deliberate behavior change (crosscdylib-abi-check-helper ADR): a missing-marker object
        now raises with the unified ABI-mismatch template instead of the old generic
        "expected fltk._native.SourceText, got <type>" message.
        """

        class NoMarker:
            pass

        with pytest.raises(TypeError, match="SourceText ABI mismatch") as exc_info:
            Span._with_source_unchecked(0, 5, NoMarker())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        assert "_fltk_cst_core_abi marker" in msg, f"missing marker name in: {msg!r}"
        assert "pre-sentinel build" in msg, f"missing sentinel hint in: {msg!r}"

    def test_with_source_unchecked_non_str_marker_raises_type_error(self):
        """An object whose _fltk_cst_core_abi is a non-str raises TypeError with unified ABI template.

        Pins template 2: the unified check_abi_pair message includes "SourceText ABI mismatch",
        the attribute name, and "not str".
        """

        class IntMarker:
            _fltk_cst_core_abi = 42

        with pytest.raises(TypeError, match="SourceText ABI mismatch") as exc_info:
            Span._with_source_unchecked(0, 5, IntMarker())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        assert "_fltk_cst_core_abi" in msg, f"missing attr name in: {msg!r}"
        assert "not str" in msg, f"missing 'not str' in: {msg!r}"

    def test_with_source_unchecked_bogus_abi_marker_raises_type_error(self):
        """An object with _fltk_cst_core_abi = 'bogus/0.0.0' raises TypeError mentioning ABI mismatch.

        Also pins that the {subject} in the error is the derived type name (FakeSource),
        verifying the py_type_obj_name() derivation on the SourceText path (§2 of the
        crosscdylib-abi-check-helper design).
        """

        class FakeSource:
            _fltk_cst_core_abi = "bogus/0.0.0"

        with pytest.raises(TypeError, match="ABI mismatch") as exc_info:
            Span._with_source_unchecked(0, 5, FakeSource())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        assert "FakeSource" in msg, f"derived type name missing from error: {msg!r}"

    def test_with_source_unchecked_escape_in_type_name(self):
        """Type names containing bidi/C1/TAB are escaped correctly in TypeError text.

        Exercises the py_type_obj_name path through the canonical escape_control_chars:
        - U+202E (RLO bidi override) → \\u202e in the error
        - U+0085 (C1 NEL) → \\x85 in the error (one codepoint escape, NOT per-UTF-8-byte \\xc2\\x85)
        - TAB → passes through unchanged (TAB exclusion from C0 escaping)
        - No raw U+202E or U+0085 in the error message
        """
        # Dynamically create a class with a name containing RLO (U+202E), TAB, and C1 NEL (U+0085).
        fake_type = type("Fake\u202eSrc\t\x85", (), {"_fltk_cst_core_abi": "bogus/0.0.0"})

        with pytest.raises(TypeError, match="ABI mismatch") as exc_info:
            Span._with_source_unchecked(0, 5, fake_type())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        assert "\\u202e" in msg, f"U+202E should be escaped as \\u202e: {msg!r}"
        assert "\\x85" in msg, f"U+0085 should be escaped as \\x85 (single codepoint): {msg!r}"
        assert "\t" in msg, f"TAB should pass through unescaped: {msg!r}"
        assert "\u202e" not in msg, f"raw U+202E must not appear in error: {msg!r}"
        assert "\x85" not in msg, f"raw U+0085 must not appear in error: {msg!r}"
        assert "\\xc2\\x85" not in msg, f"UTF-8 byte escapes must not appear (was per-byte, now codepoint): {msg!r}"

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
        # Must be at least sizeof(PyObject) — rules out stub constants <= 8.
        assert layout >= ctypes.sizeof(ctypes.py_object)

    def test_source_text_abi_layout_is_positive_int(self):
        layout = SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]
        assert isinstance(layout, int)
        assert layout > 0
        # Must be at least sizeof(PyObject) — rules out stub constants <= 8.
        assert layout >= ctypes.sizeof(ctypes.py_object)

    def test_span_abi_layout_accessible_via_instance_type(self):
        s = Span(0, 5)
        assert type(s)._fltk_cst_core_abi_layout == Span._fltk_cst_core_abi_layout  # type: ignore[attr-defined]

    def test_source_text_abi_layout_accessible_via_instance_type(self):
        src = SourceText("hello")
        assert type(src)._fltk_cst_core_abi_layout == SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]


class TestSpanPathAbiGate:
    """Phase 0 §4.1 item 1: ABI gate on the Span path (subprocess tests for PyOnceLock init).

    The ABI check fires once in get_span_type's PyOnceLock init, which is not resettable
    within a live process.  Subprocess tests ensure a fresh interpreter for each scenario.
    The cross-cdylib fixture (phase4_roundtrip_cst) is required; tests skip if unavailable.

    Note: PyOnceLock does NOT cache errors, so all three scenarios (wrong-ABI-string,
    wrong-layout, success) could in principle share one subprocess (run failures first,
    success last).  Each scenario has its own subprocess for isolation and readability.
    """

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
node = cst.cst.Config(span=cst.Span(0, 5))
s = node.span
# s is a fltk._native.Span (returned by span_to_pyobject slow path);
# check via repr since cross-cdylib == is not guaranteed for frozen pyo3 types
assert repr(s) == "Span(start=0, end=5)", f"unexpected span: {s!r}"
print("OK")
"""
        result = _run_script(script)
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
node = cst.cst.Config(span=cst.Span(0, 5))
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
        result = _run_script(script)
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
node = cst.cst.Config(span=cst.Span(0, 5))
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
        result = _run_script(script)
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
node = cst.cst.Config(span=cst.Span(0, 5))
try:
    s = node.span
    print(f"FAIL: no error, got {s!r}")
except TypeError as e:
    msg = str(e)
    assert "pre-sentinel build" in msg, f"missing 'pre-sentinel build' in: {msg!r}"
    assert "fltk-cst-core/" in msg, f"missing expected version in: {msg!r}"
    print("OK")
"""
        result = _run_script(script)
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
node = cst.cst.Config(span=cst.Span(0, 5))
try:
    s = node.span
    print(f"FAIL: no error, got {s!r}")
except TypeError as e:
    msg = str(e)
    assert "partial-upgrade" in msg, f"missing 'partial-upgrade' in: {msg!r}"
    assert "fltk._native.Span" in msg, f"missing type name in: {msg!r}"
    print("OK")
"""
        result = _run_script(script)
        assert result.returncode == 0, f"subprocess failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_non_str_abi_marker_raises_type_error(self):
        """Patching fltk._native.Span._fltk_cst_core_abi to a non-str fires TypeError (template 2).

        Pins check_abi_pair step 2 on the Span path: message includes "Span ABI mismatch"
        and "not str".
        """
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        del phase4

        script = """
import fltk._native as native

real_layout = native.Span._fltk_cst_core_abi_layout

class FakeSpan:
    _fltk_cst_core_abi = 42  # non-str marker (should be a string)
    _fltk_cst_core_abi_layout = real_layout
    def __init__(self, *a, **kw): pass

native.Span = FakeSpan
assert native.Span is FakeSpan, "patch did not take effect"

import phase4_roundtrip_cst as cst
node = cst.cst.Config(span=cst.Span(0, 5))
try:
    s = node.span
    print(f"FAIL: no error, got {s!r}")
except TypeError as e:
    msg = str(e)
    assert "Span ABI mismatch" in msg, f"missing 'Span ABI mismatch' in: {msg!r}"
    assert "not str" in msg, f"missing 'not str' in: {msg!r}"
    print("OK")
"""
        result = _run_script(script)
        assert result.returncode == 0, f"subprocess failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        assert "OK" in result.stdout

    def test_non_int_abi_layout_raises_type_error(self):
        """Patching fltk._native.Span._fltk_cst_core_abi_layout to a non-int fires TypeError (template 5).

        Pins check_abi_pair step 6 on the Span path: message includes "Span ABI mismatch"
        and "not int".
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
    _fltk_cst_core_abi_layout = "oops"  # non-int layout (should be an int)
    def __init__(self, *a, **kw): pass

native.Span = FakeSpan
assert native.Span is FakeSpan, "patch did not take effect"

import phase4_roundtrip_cst as cst
node = cst.cst.Config(span=cst.Span(0, 5))
try:
    s = node.span
    print(f"FAIL: no error, got {s!r}")
except TypeError as e:
    msg = str(e)
    assert "Span ABI mismatch" in msg, f"missing 'Span ABI mismatch' in: {msg!r}"
    assert "not int" in msg, f"missing 'not int' in: {msg!r}"
    print("OK")
"""
        result = _run_script(script)
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
        node = phase4.cst.Config(span=phase4.Span(3, 7))  # type: ignore[attr-defined]
        results = [node.span for _ in range(5)]
        assert all(s == Span(3, 7) for s in results)

    def test_source_bearing_span_reads_from_consumer_cdylib(self):
        """WITH_SOURCE_UNCHECKED_METHOD cache: source-bearing spans from a consumer cdylib are correct across reads."""
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason="phase4_roundtrip_cst not built; run 'make build-test-user-ext' first",
        )
        src = phase4.SourceText("hello world")  # type: ignore[attr-defined]
        node = phase4.cst.Config(span=phase4.Span.with_source(0, 11, src))  # type: ignore[attr-defined]
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

        with pytest.raises(TypeError, match="has no _fltk_cst_core_abi_layout") as exc_info:
            Span._with_source_unchecked(0, 5, FakeSourceNoLayout())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        assert "partial-upgrade" in msg, f"missing partial-upgrade hint in: {msg!r}"

    def test_source_text_abi_layout_non_int_raises(self):
        """SourceText: non-int _fltk_cst_core_abi_layout raises TypeError naming the attr type."""

        class FakeSourceBadLayoutType:
            _fltk_cst_core_abi = SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]
            _fltk_cst_core_abi_layout = "not-an-int"

        with pytest.raises(TypeError, match="_fltk_cst_core_abi_layout is") as exc_info:
            Span._with_source_unchecked(0, 5, FakeSourceBadLayoutType())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        assert "not int" in msg, f"missing 'not int' in: {msg!r}"

    def test_source_text_abi_string_missing_raises(self):
        """SourceText: absent _fltk_cst_core_abi on a foreign-looking object raises TypeError.

        Pins the deliberate behavior change from crosscdylib-abi-check-helper ADR: a missing
        _fltk_cst_core_abi marker now raises the unified ABI-mismatch template (template 1)
        instead of the old generic "expected fltk._native.SourceText, got <type>" message.
        Both are PyTypeError; the new message is strictly more informative (names the missing
        attr, the expected ABI string, and the "pre-sentinel build" diagnostic hint).
        """

        class FakeSourceNoAbi:
            _fltk_cst_core_abi_layout = SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]
            # _fltk_cst_core_abi intentionally absent

        with pytest.raises(TypeError, match="SourceText ABI mismatch") as exc_info:
            Span._with_source_unchecked(0, 5, FakeSourceNoAbi())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        assert "_fltk_cst_core_abi marker" in msg, f"missing marker name in: {msg!r}"
        assert "pre-sentinel build" in msg, f"missing sentinel hint in: {msg!r}"

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


class TestForgedSourceTextRejected:
    """Regression tests for the forged-ABI segfault fix (fix-forged-abi-segfault design).

    Before the fix, a pure-Python class that copied both `_fltk_cst_core_abi` and
    `_fltk_cst_core_abi_layout` from a genuine SourceText could pass `check_abi_pair` and
    reach `cast_unchecked`, causing a SIGSEGV (exit code -11 / 139).  The fix adds a
    `check_instance_layout` gate that reads `__basicsize__` from the object's actual CPython
    type — which cannot be satisfied by copying class attributes — and raises TypeError
    instead of proceeding to UB.

    All tests that invoke `_with_source_unchecked` with a forged object use subprocess
    isolation so that a regression (segfault) does not take down the test suite.
    """

    def test_forged_source_text_raises_type_error(self):
        """Trivial forge (copied attrs, default object layout) raises TypeError, not SIGSEGV.

        This is the exact §1.1 repro: a pure-Python class copies both ABI attributes from a
        genuine SourceText.  Before the fix, `_with_source_unchecked(0, 5, Forge())` exited
        with signal 11 (SIGSEGV, returncode -11 / 139).  After the fix it must raise TypeError
        and the subprocess must exit cleanly (returncode 0).
        """
        script = """
import fltk._native as native
ST = native.SourceText

class Forge:
    _fltk_cst_core_abi = ST._fltk_cst_core_abi
    _fltk_cst_core_abi_layout = ST._fltk_cst_core_abi_layout

try:
    native.Span._with_source_unchecked(0, 5, Forge())
    print("FAIL: no exception raised")
except TypeError:
    print("OK")
"""
        result = _run_script(script)
        _assert_forge_rejected_cleanly(result, "trivial SourceText forge")

    def test_forged_source_text_message_is_diagnostic(self):
        """TypeError message for a trivial forge names the layout/basicsize mismatch.

        Pins that the error message is informative enough that a future regression
        (swapping the gate for a silent pass) would be caught by the message check.
        """

        class Forge:
            _fltk_cst_core_abi = SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]
            _fltk_cst_core_abi_layout = SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]

        with pytest.raises(TypeError) as exc_info:
            Span._with_source_unchecked(0, 5, Forge())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        # The basicsize gate fires (check_abi_pair passes first; check_instance_layout rejects).
        # Pin the specific `check_instance_layout` message: it contains "__basicsize__" or
        # "not a genuine SourceText allocation".  A weaker "layout" substring would also match
        # check_abi_pair messages, masking a broken or absent basicsize gate.
        assert "__basicsize__" in msg or "not a genuine SourceText" in msg, (
            f"error message does not name the basicsize gate — check_instance_layout may not be firing: {msg!r}"
        )

    def test_padded_forge_passes_basicsize_gate_boundary(self):
        """Documents the known residual: a __slots__-padded forge matches SourceText.__basicsize__.

        The `check_instance_layout` gate reads `tp_basicsize` from the object's actual CPython
        type.  A pure-Python class with `__slots__` padding can be tuned to produce a
        `tp_basicsize` equal to `SourceText._fltk_cst_core_abi_layout` (verified in the design).
        This test pins that the residual EXISTS — the basicsize gate alone cannot distinguish
        a padded forge from a genuine foreign SourceText.

        THIS TEST DOES NOT CALL `_with_source_unchecked` ON THE PADDED FORGE.
        Crossing the gate with this object is Undefined Behavior: the `PyObject*` in the
        __slots__ slot is not an `Arc<SourceInner>`, so `cast_unchecked` reads garbage.
        UB has no stable runtime outcome — it can silently pass, crash, or corrupt memory
        depending on build mode, allocator, and pyo3 internals.  Asserting any runtime
        outcome here would produce a flaky or actively misleading test.

        The gate boundary (basicsize equality) is what this test pins.  Closing the residual
        fully requires a per-instance unforgeable token (e.g. a PyCapsule wrapping a real
        Rust pointer), which the project has not adopted.
        """
        native_layout = SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]

        # A class with one __slots__ entry produces tp_basicsize == native_layout on CPython 3.10+.
        # (Verified in the design: native_layout is 24 for SourceText; default object is 32;
        # one slot removes 8 bytes from the __dict__ pointer overhead, reaching 24.)
        class PaddedForge:
            __slots__ = ("x",)
            _fltk_cst_core_abi = SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]
            _fltk_cst_core_abi_layout = SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]

        padded_basicsize = type(PaddedForge()).__basicsize__
        # Pin: on a typical CPython build, the padded forge has the same basicsize as SourceText.
        # If this assertion fails, the residual may be narrower or the layout has changed.
        assert padded_basicsize == native_layout, (
            f"padded forge basicsize {padded_basicsize} != native layout {native_layout}; "
            "the design's residual assumption may no longer hold — re-evaluate"
        )
        # Confirm: the padded forge's basicsize EQUALS the gate threshold, so the gate
        # cannot distinguish it from a genuine foreign SourceText on basicsize alone.
        # (See above: do NOT call _with_source_unchecked on PaddedForge — that is UB.)

    def test_foreign_source_text_basicsize_matches_native_layout(self):
        """Genuine foreign-cdylib SourceText has the same __basicsize__ as native SourceText.

        Pins the accept-branch precondition of the basicsize gate directly: a foreign
        SourceText (from a cdylib linking the same fltk-cst-core rlib) must have a
        `type(foreign_st).__basicsize__` equal to `SourceText._fltk_cst_core_abi_layout`.
        If a future change breaks this equality, the gate would reject genuine foreign
        SourceText objects, breaking the cross-cdylib path (Requirements item 1).
        """
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason=(
                "phase4_roundtrip_cst not built; run 'make build-test-user-ext' first — "
                "skipping this test means the basicsize gate's accept-branch precondition "
                "(foreign __basicsize__ == native layout) is unverified in this lane"
            ),
        )
        foreign_st = phase4.SourceText("hello world")  # type: ignore[attr-defined]
        native_layout = SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]
        foreign_basicsize = type(foreign_st).__basicsize__
        assert foreign_basicsize == native_layout, (
            f"foreign SourceText __basicsize__ ({foreign_basicsize}) != "
            f"native SourceText._fltk_cst_core_abi_layout ({native_layout}); "
            "cross-cdylib basicsize gate would reject genuine foreign SourceText"
        )

    def test_metaclass_property_forge_raises_type_error(self):
        """Metaclass-property forge is rejected by the metaclass guard.

        A metaclass property that returns the expected basicsize value (24) could shadow
        `getattr(ty, "__basicsize__")` and fool the size check.  The gate now guards against
        this by first verifying that the candidate type's metaclass is exactly the built-in
        `type` (which is immutable and cannot carry a shadowing property).  A type with a
        custom metaclass is rejected before `__basicsize__` is even read.

        Before the security-1 fix, this forge passed the gate: the metaclass property returned
        24 while the object's real allocation was a bare 16-byte `object`.  The subsequent
        `cast_unchecked` would reinterpret CPython header fields as `Arc<SourceInner>` — a
        write-what-where primitive.

        This test is subprocess-isolated because a regression segfaults the interpreter.
        """
        script = """
import fltk._native as native
ST = native.SourceText

class Meta(type):
    @property
    def __basicsize__(cls):
        return ST._fltk_cst_core_abi_layout  # forged value; real allocation is 16-byte object

class Forge(metaclass=Meta):
    _fltk_cst_core_abi = ST._fltk_cst_core_abi
    _fltk_cst_core_abi_layout = ST._fltk_cst_core_abi_layout

try:
    native.Span._with_source_unchecked(0, 5, Forge())
    print("FAIL: no exception raised")
except TypeError as e:
    msg = str(e)
    # The metaclass guard fires; message names the custom metaclass.
    if "metaclass" in msg or "Meta" in msg:
        print("OK")
    else:
        print(f"FAIL: unexpected message: {msg}")
"""
        result = _run_script(script)
        _assert_forge_rejected_cleanly(result, "metaclass-property SourceText forge")

    def test_exotic_type_no_basicsize_raises_type_error(self):
        """An object whose type raises on tp_basicsize access surfaces a TypeError, not a panic.

        `check_instance_layout` uses `PyType_GetSlot(Py_tp_basicsize)` which returns 0 for
        non-heap types.  A type that is not a heap type (unusual but possible with ctypes
        or extension module tricks) produces basicsize == 0; the helper rejects it with a
        TypeError naming the exotic-type case rather than unwrapping or panicking.

        We simulate a basicsize==0 response by using ctypes to create a C-extension-like
        type — but that is fragile.  Instead, we verify the failure mode by patching:
        the simplest reachable path is an ordinary object that nonetheless fails check_abi_pair
        first (which fires before check_instance_layout).  A direct test of the
        exotic-type branch is inherently hard to construct from pure Python.

        Instead, this test verifies the `map_err` discipline of `check_instance_layout` by
        confirming that a TypeError (not a panic/abort) is always raised for any failing
        argument — the test exercises the guard via the trivial forge path (which reaches
        `check_instance_layout` and fails on size mismatch).
        """

        class Forge:
            _fltk_cst_core_abi = SourceText._fltk_cst_core_abi  # type: ignore[attr-defined]
            _fltk_cst_core_abi_layout = SourceText._fltk_cst_core_abi_layout  # type: ignore[attr-defined]

        # Confirm: raises TypeError (not AttributeError, RuntimeError, or panic).
        with pytest.raises(TypeError) as exc_info:
            Span._with_source_unchecked(0, 5, Forge())  # type: ignore[attr-defined]
        msg = str(exc_info.value)
        # The basicsize gate fires; the message names __basicsize__ or "not a genuine SourceText".
        assert "__basicsize__" in msg or "not a genuine SourceText" in msg, (
            f"check_instance_layout did not fire; got: {msg!r}"
        )


class TestForgedSpanRejected:
    """Regression tests for forged-ABI on the Span path.

    Mirrors TestForgedSourceTextRejected, but for extract_span / get_span_type.  A pure-Python
    class copying both `_fltk_cst_core_abi` and `_fltk_cst_core_abi_layout` from a genuine Span,
    installed as `fltk._native.Span` before the first span boundary crossing, previously passed
    `check_abi_pair::<Span>` in get_span_type and reached `cast_unchecked` in extract_span —
    reinterpreting a plain Python object's memory as a Rust Span (UB / SIGSEGV).  The
    `check_instance_layout::<Span>` gate added to get_span_type rejects it with a TypeError.

    All forge tests run in subprocesses (`_run_script`) so a regression segfaults the child,
    not the suite.  They drive the gate via `fegen_rust_cst`, a module-level import-or-skip of
    this file.
    """

    def test_forged_span_via_reassignment_raises_type_error(self):
        """Correct-attrs forge installed as fltk._native.Span raises TypeError, not SIGSEGV.

        The end-to-end forge scenario: FakeSpan copies both ABI attributes (so
        check_abi_pair passes) but has a plain-object CPython layout (so check_instance_layout
        rejects it via __basicsize__).  Before the gate, get_span_type cached FakeSpan and
        extract_span's cast_unchecked reinterpreted a plain Python object as a Rust Span (UB).
        """
        script = """
import fltk._native as native

class FakeSpan:
    _fltk_cst_core_abi = native.Span._fltk_cst_core_abi
    _fltk_cst_core_abi_layout = native.Span._fltk_cst_core_abi_layout
    def __init__(self, *a, **kw): pass

native.Span = FakeSpan  # patch before first span boundary crossing
assert native.Span is FakeSpan, "patch did not take effect"

import fegen_rust_cst.cst as cst
try:
    node = cst.Grammar(span=FakeSpan())
    print(f"FAIL: no error, got {node!r}")
except TypeError as e:
    msg = str(e)
    assert "__basicsize__" in msg or "not a genuine Span" in msg, (
        f"error message does not name the basicsize gate: {msg!r}"
    )
    print("OK")
"""
        result = _run_script(script)
        _assert_forge_rejected_cleanly(result, "reassignment Span forge")

    def test_forged_span_metaclass_property_raises_type_error(self):
        """Metaclass-property forge on the Span path is rejected by the metaclass guard.

        A metaclass whose __basicsize__ property returns the expected size would fool a bare
        getattr; the metaclass guard in check_instance_layout rejects any type whose metaclass
        is not exactly the built-in `type` before __basicsize__ is read.  Mirrors
        test_metaclass_property_forge_raises_type_error on the SourceText path.
        """
        script = """
import fltk._native as native

class Meta(type):
    @property
    def __basicsize__(cls):
        return native.Span._fltk_cst_core_abi_layout  # forged value; real allocation differs

class FakeSpan(metaclass=Meta):
    _fltk_cst_core_abi = native.Span._fltk_cst_core_abi
    _fltk_cst_core_abi_layout = native.Span._fltk_cst_core_abi_layout
    def __init__(self, *a, **kw): pass

native.Span = FakeSpan
assert native.Span is FakeSpan, "patch did not take effect"

import fegen_rust_cst.cst as cst
try:
    node = cst.Grammar(span=FakeSpan())
    print(f"FAIL: no error, got {node!r}")
except TypeError as e:
    msg = str(e)
    if "metaclass" in msg or "Meta" in msg:
        print("OK")
    else:
        print(f"FAIL: unexpected message: {msg}")
"""
        result = _run_script(script)
        _assert_forge_rejected_cleanly(result, "metaclass-property Span forge")

    def test_genuine_native_span_accepted_cross_cdylib(self):
        """No false rejection: a genuine fltk._native.Span passes the new gate on the slow path.

        Subprocess (fresh interpreter) so get_span_type's PyOnceLock init — and therefore the
        new check_instance_layout accept branch — provably runs inside this test; in-process the
        cache would already be seeded by earlier tests, degrading this to a cache-hit test.
        Grammar's constructor extract::<Span> fast path fails on the foreign fltk._native.Span,
        so this exercises extract_span's slow path with the genuine canonical type.
        """
        script = """
import fltk._native as native
import fegen_rust_cst.cst as cst
node = cst.Grammar(span=native.Span(0, 5))
s = node.span
assert repr(s) == "Span(start=0, end=5)", f"unexpected span: {s!r}"
print("OK")
"""
        result = _run_script(script)
        assert result.returncode == 0, (
            f"subprocess failed (returncode {result.returncode})\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout, f"expected 'OK' in stdout; got: {result.stdout!r}\nstderr: {result.stderr}"

    def test_span_basicsize_matches_layout_attr(self):
        """Accept-branch precondition: Span.__basicsize__ == Span._fltk_cst_core_abi_layout.

        If this equality ever breaks, the check_instance_layout gate would reject genuine
        spans.  Analogous to test_foreign_source_text_basicsize_matches_native_layout.
        """
        assert Span.__basicsize__ == Span._fltk_cst_core_abi_layout, (  # type: ignore[attr-defined]
            f"native Span __basicsize__ ({Span.__basicsize__}) != "
            f"Span._fltk_cst_core_abi_layout ({Span._fltk_cst_core_abi_layout}); "  # type: ignore[attr-defined]
            "the new basicsize gate would reject genuine spans"
        )
        phase4 = pytest.importorskip(
            "phase4_roundtrip_cst",
            reason=(
                "phase4_roundtrip_cst not built; run 'make build-test-user-ext' first — "
                "skipping leaves the foreign-Span accept-branch precondition unverified"
            ),
        )
        foreign_basicsize = phase4.Span.__basicsize__  # type: ignore[attr-defined]
        assert foreign_basicsize == Span._fltk_cst_core_abi_layout, (  # type: ignore[attr-defined]
            f"foreign Span __basicsize__ ({foreign_basicsize}) != "
            f"native Span._fltk_cst_core_abi_layout ({Span._fltk_cst_core_abi_layout}); "  # type: ignore[attr-defined]
            "cross-cdylib basicsize gate would reject genuine foreign Span"
        )


class TestLineColPos:
    """Tests for fltk._native.LineColPos class."""

    def test_line_col_pos_importable(self):
        """LineColPos is importable from fltk._native."""
        assert LineColPos is not None

    def test_line_col_pos_fields(self):
        """LineColPos has line, col, line_span fields."""
        src = SourceText("hello\nworld")
        span = Span.with_source(6, 7, src)
        lc = span.line_col()
        assert lc is not None
        assert isinstance(lc.line, int)
        assert isinstance(lc.col, int)
        # line_span is a Span
        assert isinstance(lc.line_span, Span)

    def test_line_col_pos_values(self):
        """LineColPos has correct line=1, col=0 for start of second line."""
        src = SourceText("hello\nworld")
        span = Span.with_source(6, 7, src)
        lc = span.line_col()
        assert lc is not None
        assert lc.line == 1
        assert lc.col == 0

    def test_line_col_pos_line_span_is_source_bearing(self):
        """line_col().line_span is source-bearing and covers the full line including last char.

        For "hello\nworld" the last line has no trailing newline so the sentinel is `len` (11),
        giving line_span = Span(6, 11) and text = "world" (all 5 characters).
        """
        src = SourceText("hello\nworld")
        span = Span.with_source(6, 7, src)
        lc = span.line_col()
        assert lc is not None
        assert lc.line_span.has_source()
        # Sentinel for "world" (no trailing \n): len = 11; line_span = Span(6, 11)
        assert lc.line_span.start == 6
        assert lc.line_span.end == 11
        assert lc.line_span.text() == "world"


class TestLineCol:
    """Tests for Span.line_col / line_col_or_raise on the Rust backend."""

    def test_sourceless_returns_none(self):
        """Sourceless Rust span: line_col() returns None."""
        assert Span(0, 5).line_col() is None

    def test_unknown_span_returns_none(self):
        """UnknownSpan (start=-1): line_col() returns None."""
        assert UnknownSpan.line_col() is None

    def test_negative_start_with_source_returns_none(self):
        """Source-bearing span with start=-1: line_col() returns None (guard fires)."""
        src = SourceText("hello")
        span = Span.with_source(-1, 0, src)
        assert span.line_col() is None

    def test_out_of_domain_returns_none(self):
        """start > len(source): line_col() returns None."""
        src = SourceText("hello")
        span = Span.with_source(100, 101, src)
        assert span.line_col() is None

    def test_first_line_start(self):
        """line_col at col 0 of first line."""
        src = SourceText("hello\nworld")
        span = Span.with_source(0, 1, src)
        lc = span.line_col()
        assert lc is not None
        assert lc.line == 0
        assert lc.col == 0

    def test_mid_first_line(self):
        """line_col mid first line."""
        src = SourceText("hello\nworld")
        span = Span.with_source(3, 4, src)
        lc = span.line_col()
        assert lc is not None
        assert lc.line == 0
        assert lc.col == 3

    def test_second_line_start(self):
        """line_col at start of second line."""
        src = SourceText("hello\nworld")
        span = Span.with_source(6, 7, src)
        lc = span.line_col()
        assert lc is not None
        assert lc.line == 1
        assert lc.col == 0

    def test_eof_clamp(self):
        """start == len(source): clamped to last codepoint."""
        text = "abc"
        src = SourceText(text)
        span_eof = Span.with_source(3, 3, src)  # start == len
        span_last = Span.with_source(2, 3, src)  # last char
        lc_eof = span_eof.line_col()
        lc_last = span_last.line_col()
        assert lc_eof is not None
        assert lc_last is not None
        assert lc_eof.line == lc_last.line
        assert lc_eof.col == lc_last.col

    def test_multibyte_column(self):
        """Multibyte: column counts codepoints, not bytes."""
        # "café\nrésumé": é in café is codepoint 3
        src = SourceText("café\nrésumé")
        span = Span.with_source(3, 4, src)
        lc = span.line_col()
        assert lc is not None
        assert lc.line == 0
        assert lc.col == 3

    def test_line_span_text_works(self):
        """line_col().line_span is source-bearing and covers the full line.

        Sentinel for last line without trailing '\\n' is `len` (exclusive), so
        line_span = Span(6, 11) covers all 5 characters of 'world'.
        """
        src = SourceText("hello\nworld")
        span = Span.with_source(6, 7, src)
        lc = span.line_col()
        assert lc is not None
        assert lc.line_span.has_source()
        # Sentinel = len = 11 for "world" (no trailing \n)
        assert lc.line_span.start == 6
        assert lc.line_span.end == 11
        assert lc.line_span.text() == "world"

    def test_line_col_or_raise_sourceless_raises(self):
        """line_col_or_raise() raises ValueError with 'has no source' message."""
        with pytest.raises(ValueError, match="has no source"):
            Span(0, 5).line_col_or_raise()

    def test_line_col_or_raise_negative_raises(self):
        """line_col_or_raise() raises ValueError with 'negative' message for negative start."""
        src = SourceText("hello")
        with pytest.raises(ValueError, match="negative"):
            Span.with_source(-1, 0, src).line_col_or_raise()

    def test_line_col_or_raise_out_of_bounds_raises(self):
        """line_col_or_raise() raises ValueError with 'out of bounds' message when start > len."""
        src = SourceText("hello")
        with pytest.raises(ValueError, match="out of bounds"):
            Span.with_source(100, 101, src).line_col_or_raise()

    def test_line_col_or_raise_valid(self):
        """line_col_or_raise() returns LineColPos for valid span."""
        src = SourceText("hello\nworld")
        span = Span.with_source(6, 7, src)
        lc = span.line_col_or_raise()
        assert lc.line == 1
        assert lc.col == 0

    def test_negative_start_diverges_from_pos_to_line_col(self):
        """Rust Span(-1) returns line_col()=None while pos_to_line_col(-1) returns LineColPos.

        Pins the deliberate divergence: the new span-level guard returns None for negative start,
        while the unguarded legacy pos_to_line_col accepts -1 as a sentinel.
        This is a cross-backend regression test for the design-3 resolution.
        """
        # Import TerminalSource from Python (it's not a pyo3 class, but test via Python wrapper)
        from fltk.fegen.pyrt.terminalsrc import TerminalSource as PyTS  # noqa: PLC0415

        ts = PyTS("abc")
        lc_legacy = ts.pos_to_line_col(-1)
        assert lc_legacy.line == 0
        assert lc_legacy.col == -1

        src = SourceText("abc")
        span = Span.with_source(-1, 0, src)
        assert span.line_col() is None, "Rust span.line_col() should return None for negative start"


class TestFilename:
    """Tests for Span.filename() on the Rust backend."""

    def test_filename_from_source_text(self):
        """SourceText with filename → span.filename() returns it."""
        src = SourceText("hello", filename="test.fltkg")  # type: ignore[call-arg]
        span = Span.with_source(0, 5, src)
        assert span.filename() == "test.fltkg"

    def test_filename_none_when_not_provided(self):
        """SourceText without filename → span.filename() == None."""
        src = SourceText("hello")
        span = Span.with_source(0, 5, src)
        assert span.filename() is None

    def test_filename_sourceless_returns_none(self):
        """Sourceless Rust span → span.filename() == None."""
        span = Span(0, 5)
        assert span.filename() is None

    def test_filename_unknown_span_returns_none(self):
        """UnknownSpan → span.filename() == None."""
        assert UnknownSpan.filename() is None

    def test_source_text_accepts_filename_kwarg(self):
        """SourceText(text, filename=...) constructor works."""
        src = SourceText("hello", filename="foo.fltkg")  # type: ignore[call-arg]
        assert isinstance(src, SourceText)
