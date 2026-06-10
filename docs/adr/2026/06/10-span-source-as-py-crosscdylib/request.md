# Request: span-source-as-py-crosscdylib

Style: concise, precise, no padding, no preamble. Self-contained — downstream agents do not see the triage conversation.

**Type**: performance fix spanning `fltk-cst-core` API surface + generated-code emission. **Requires a design stage** — the fix involves an `unsafe` cross-cdylib cast and a new native-side entry point.

## Background

Every span-returning accessor on a Rust-backend CST node copies the **entire source text twice per call** — O(source length) per node read. Verified (see `exploration.md` in this dir):

- Copy 1: `source_full_text_str()` (`crates/fltk-cst-core/src/span.rs:168-170`) = `arc.text.clone()` — full source `String` allocation.
- Copy 2: `get_source_text_type(py)?.call1((full_text.as_str(),))` → `SourceText::from_str` (`span.rs:39-45`) = `text.to_owned()` — full source again into a brand-new `Arc<SourceInner>` (also destroying Arc-sharing across spans of the same parse).
- Emission sites: span getter from `_span_getter_setter` (`fltk/fegen/gsm2tree_rs.py:703-731`) and the `to_pyobject` Span arm from `_child_enum_block` (`gsm2tree_rs.py:529-545`). 23 sites in `src/cst_fegen.rs`, 6 in `src/cst_generated.rs`, 10 in the fixture crate.
- The parse path is clean (one shared `SourceText`); the regression is exclusively at the read boundary.

The O(1) API exists: `Span::source_as_py` (`span.rs:151-161`) clones only the Arc. It can't be used today because the resulting `Py<SourceText>` is registered with the *calling* cdylib's type object, and `fltk._native.Span.with_source` (`span.rs:204-206`) does pyo3 type-checked extraction of `source: &SourceText`, which rejects a `SourceText` registered by another cdylib.

**The original TODO's fix shape (generated-preamble-only `extract_source_text`) is insufficient** — validation traced the data flow: the rejection happens on the *receiving* side inside `fltk._native`, which is not generated code. The fix needs a new entry point on the `fltk._native` side.

Sequencing note: `preamble-helpers-into-cst-core` (already implemented by the time this runs) moved the cross-cdylib helpers (`extract_span`, `get_span_type`, `get_source_text_type`) into `fltk-cst-core`. Any new helper belongs there, not in the generated preamble.

## Direction (decided at triage — designer refines the mechanism, not the goal)

Goal: span-returning accessors in generated code (including out-of-tree consumer crates) return a `fltk._native.Span` carrying the source **without any O(source) copy**, preserving Arc-sharing.

Validated mechanism sketch (designer to confirm/refine):

- Add a cross-cdylib-safe constructor entry point to `fltk._native`'s `Span` (e.g. a private classmethod like `_with_source_unchecked` / an alternative to `with_source`) that accepts the source argument as `&Bound<PyAny>`, verifies `isinstance` against the cached `fltk._native.SourceText` type object, and uses `downcast_unchecked::<SourceText>()` under the **same shared-rlib invariant** `extract_span` already documents (both cdylibs link the same `fltk-cst-core` rlib → identical type layout). Location: `crates/fltk-cst-core/src/span.rs` `#[pymethods]`.
- Generated code path becomes: `self.span.source_as_py(py)?` (O(1) Arc clone, locally-registered `Py<SourceText>`) → call the new entry point on the cached `fltk._native.Span` type. Update both emission sites (`_span_getter_setter`, `_child_enum_block` Span arm) in `gsm2tree_rs.py`.
- Wait — note the subtlety the designer must resolve: the new entry point receives a `SourceText` registered with the *consumer* cdylib but executes inside `fltk._native`. The `downcast_unchecked` there is exactly the `extract_span` pattern in reverse direction; the design must state the soundness argument explicitly, mirroring the existing safety comments.
- Returned object must remain `fltk._native.Span` — the canonical-type guarantee in the existing generated comment (`src/cst_fegen.rs:317-319`) is a hard constraint for downstream type checks.

## Constraints / non-goals

- **No public API breakage**: existing `Span.with_source` keeps its exact behavior and signature (out-of-tree code calls it). The new entry point is additive; name it as private-by-convention (leading underscore) unless the design argues otherwise.
- Python-visible semantics of accessors unchanged: same types, same `.text()` / `.has_source()` results. Only allocation behavior changes (and Arc identity of the underlying source becomes shared — design must confirm no observable contract depends on the *copying*).
- Sourceless-span path unchanged.
- Regenerate all generated files via `make gencode` + `make fix`; cross-backend equivalence and fixture-crate tests must stay green.
- Remove the `TODO(span-source-as-py-crosscdylib)` comments (`crates/fltk-cst-core/src/span.rs:148` area, and any in `gsm2tree_rs.py`) and the `TODO.md` entry.

## Verification expectations

- TDD: a test that proves source-preservation without copying — e.g. assert the `SourceText` returned via a span accessor shares the underlying source with the node's (the design should pick an observable: object identity of `.source` where exposed, or a Rust-level test on Arc pointer equality via the fixture crate; if no Python-observable exists, a crate-level `cargo test` is acceptable).
- A cross-cdylib test through the standalone fixture extension (the consumer-crate simulation) exercising the new path — this is the case the whole fix exists for.
- Existing span contract tests (`tests/test_phase4_fegen_rust_backend.py` `TestChildSpanAccessorContract`, `tests/test_fegen_rust_cst.py`) green.
- `uv run pytest`, `uv run ruff check . && uv run pyright`, `make gencode` idempotent.
- `grep -rn 'span-source-as-py-crosscdylib'` returns nothing.
