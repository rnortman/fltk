# Deep efficiency review — span-source-as-py-crosscdylib

Reviewed: 9db20de..588d55f (HEAD 588d55f).

The diff is itself an efficiency fix and lands it correctly: every generated span accessor drops from two O(source-length) string copies per call to O(1) Arc sharing, on both the in-tree fast path (`Py::new`, zero Python calls) and the consumer-cdylib slow path. Generator correctly strips `get_span_type` fetches from all call sites that only fed `to_pyobject`, keeps them where `extract_from_pyobject` still needs them, and drops the dead `span_type` parameter from `to_pyobject`. Caches (`GILOnceCell` statics, interned strings) are bounded; no leaks introduced. Legacy `source_full_text_str`/`get_source_text_type` retention is compat-only and documented.

One finding, small magnitude, optional.

## efficiency-1: `span_to_pyobject` re-derives process-constant facts on every call

`crates/fltk-cst-core/src/cross_cdylib.rs:104-122` (`span_to_pyobject`), called once per span accessor read by all generated code.

Per call, work whose result never changes for the life of the process:

- Both paths: `get_span_type(py)` (cell lookup + type-object incref/decref) followed by `Span::type_object(py).is(&span_type)` — the "am I the canonical cdylib" answer is a per-cdylib constant; cacheable as a `GILOnceCell<bool>` initialized alongside `FLTK_NATIVE_SPAN_TYPE`.
- Slow path additionally: `call_method1(intern!("_with_source_unchecked"), ...)` does a getattr of the classmethod on the canonical type per call (cacheable as a `GILOnceCell<PyObject>` of the bound classmethod); inside `extract_source_text` (`cross_cdylib.rs:52-90`), the local `downcast::<SourceText>()` always fails on this path (the incoming object is by construction foreign to `fltk._native`), so every call pays the failed downcast + marker getattr + string compare. A one-slot cache of the last-validated foreign `SourceText` type pointer would skip the getattr in the common single-consumer-cdylib process. The transient `source_as_py` `SourceText` PyObject (alloc + immediate drop per call) is harder to avoid without a C-level bridge and is fine to keep.

**Consequence**: per-span-read constant overhead in the accessor hot path — the slow path is the one out-of-tree consumers (the project's primary audience) hit on every `.span` / span-child read; walking a large CST pays ~2 extra Python attribute lookups + 1 transient object per node read on top of the irreducible Python method call. Magnitude is small (likely ≤2x a plain Python call, vs the O(N)-per-read it replaces), so this bites only for consumers iterating very large trees; it does not block the change.

**Fix direction**: fold the canonical-cdylib bool and the bound `_with_source_unchecked` classmethod into the existing `GILOnceCell` init in `get_span_type`; optionally a one-slot validated-foreign-type cache in `extract_source_text`. Natural home: the `crosscdylib-abi-sentinel` follow-up, which already owns the gate mechanism — extend that TODO rather than churn this change.

No other findings. Test additions are proportionate (no redundant parsing beyond per-test isolation); regenerated files match the generator; no new startup work; no unbounded growth.
