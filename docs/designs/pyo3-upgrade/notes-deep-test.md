Reviewed commit: 6df2369

test-1. `tests/test_rust_span.py:470–478` — Stale type name in test docstring.
`TestSpanPathAbiGate`'s class docstring says "GILOnceCell init" twice and "GILOnceCell does NOT cache errors". The implementation now uses `PyOnceLock`, not `GILOnceCell`. `PyOnceLock.get_or_try_init` leaves the cell uninitialized on error (same retry behavior), so the behavioral claim is still true — but the type name is wrong. Consequence: the docstring's "GILOnceCell" reference is misleading to a reader checking whether the test premise matches implementation, and may cause confusion in future maintenance.
Fix: replace "GILOnceCell" with "PyOnceLock" in the three occurrences at lines 470, 472, 476.

test-2. `crates/fltk-cst-core/src/span.rs:380,382,565` and `cross_cdylib.rs:33,247,383` — Stale type names in Rust doc comments.
Several doc comment lines still reference the removed API names: "GILOnceCell init" (span.rs:380), "downcast_unchecked UB" (span.rs:382), "GILOnceCell cache" (span.rs:565), "`None` cell = not yet populated … fast-path hits `downcast`" (cross_cdylib.rs:33), "Build the canonical fltk._native.Span PyObject" (cross_cdylib.rs:247), "before any unchecked downcast" (cross_cdylib.rs:383). These are not code bugs — all production code was correctly updated — but they are stale doc comments on public/semipublic items. Consequence: a reader of the doc comments gets the old API names rather than the current ones; cross-referencing doc vs code is harder than it should be.
Fix: update the six doc-comment occurrences to use `PyOnceLock`, `cast_unchecked`, and `Py<PyAny>` respectively.

test-3. `fltk/fegen/test_genparser.py:75` — Stale "GILOnceCell" in a test docstring.
`test_gen_rust_cst_sentinel_decoupled` docstring says "no GILOnceCell cache". The design (§2.F) explicitly calls out this file as needing an opportunistic update, but the update was not applied. Consequence: same cosmetic issue as test-1 — misleads readers cross-referencing the test's rationale with the implementation.
Fix: replace "GILOnceCell" with "PyOnceLock" at line 75.

test-4. `tests/test_rust_span.py` — No Python-side test for the ABI probe floor.
The design's §2.A guard test (new Rust unit test asserting `probe >= size_of::<ffi::PyObject>() + size_of::<T>()`) was added in `crates/fltk-cst-core/src/lib.rs` (the `abi_probe_tests` module). The Python-side `TestAbiLayoutClassattr` tests (test_rust_span.py:441–466) only assert `layout > 0` and `isinstance(layout, int)` — they don't assert that the value is at least `sizeof(PyObject) + sizeof(T)`. This matters because the Python tests exercise the exposed classattr value at runtime (the actual running binary) while the Rust unit tests only run under `cargo test`. Consequence: if someone builds and installs a probe-disabled variant that returns `1` (passes `> 0` check), the Python test suite would not catch it. The Rust test would, but only when `cargo test -p fltk-cst-core --features python` is run — not as part of `uv run pytest`.
Fix: add assertions in `test_span_abi_layout_is_positive_int` and `test_source_text_abi_layout_is_positive_int` (or add new tests) that `layout >= ctypes.sizeof(ctypes.py_object)`, which gives `sizeof(PyObject)` at the Python level and is a reasonable floor that rules out stub constants ≤ 8.
