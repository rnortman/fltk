Commit reviewed: 90074aa

reuse-1
File: tests/test_rust_span.py:5,7
What: `import fltk._native as _native_module` (line 5) followed immediately by `pytest.importorskip("fltk._native", ...)` (line 7). The module-level import on line 5 will itself raise ImportError if the extension is absent, defeating the importorskip guard. The established pattern in tests/test_native.py:3 is to assign the result of `importorskip` to the module variable and use that; no separate bare import is needed.
Existing: `tests/test_native.py:3` — `native = pytest.importorskip("fltk._native", ...)`.
Consequence: The redundant bare import means the guard is cosmetically present but functionally broken when the Rust extension is absent; the file diverges from the clean pattern set by test_native.py and will confuse future authors about which idiom to follow.

reuse-2
File: tests/test_span_protocol.py:10,30,35
What: Uses a bespoke availability check (`_rust_available = hasattr(_fltk_native, "Span")`) combined with per-method `@pytest.mark.skipif`. This is a third guard idiom for the same condition already handled two ways in the test suite (`importorskip` in test_native.py and test_rust_span.py).
Existing: `pytest.importorskip` at module scope (tests/test_native.py:3, tests/test_rust_span.py:7).
Consequence: Three different idioms for "skip if Rust extension absent" in three adjacent files. Future contributors will copy whichever they read first; the `hasattr` variant silently imports `fltk._native` regardless of availability (succeeding only because fltk/_native stub exists), masking potential import errors and making the skip condition subtly differ from the other two.

reuse-3
File: fltk/fegen/pyrt/terminalsrc.py:47 and :55
What: The source-fallback expression `self._source if self._source is not None else other._source` is written identically in both `merge` (line 47) and `intersect` (line 55) within the same class.
Existing: No extracted helper; the expression could be a private `_coerce_source` method or inlined with `or` idiom (`self._source or other._source`) since `_source` is `str | None` and empty string is not a valid source.
Consequence: If source-selection logic ever needs to change (e.g., to validate same-identity or handle a future `SourceText` wrapper), two sites must be updated in sync. Low risk now, but establishes a precedent of copy-paste within the same class.

reuse-4
File: src/span.rs:130 and :143
What: `self.source.clone().or_else(|| other.source.clone())` appears verbatim in both `merge` (line 130) and `intersect` (line 143) in the Rust `Span` impl.
Existing: No extracted helper; mirrors the Python duplication in reuse-3.
Consequence: Same drift risk as reuse-3 for the Rust backend; the two backends' source-selection logic are already slightly different (Python uses `is not None` branch; Rust uses `Option::or_else`), and having the expression repeated within each backend increases the surface for future divergence.
