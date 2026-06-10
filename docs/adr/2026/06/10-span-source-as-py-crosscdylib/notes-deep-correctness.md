# Deep correctness review — span-source-as-py-crosscdylib

Commit reviewed: 588d55f (base 9db20de). Single pass. Concise. Precise. Complete. Unambiguous. No padding.

## Verification performed

- Traced `extract_source_text` (`crates/fltk-cst-core/src/cross_cdylib.rs:50-87`): fast path (local `downcast`), marker path (classattr read on `ob_type` — instance attrs cannot spoof; marker comparison is Rust byte equality, not Python `__eq__`, so a `str` subclass with custom `__eq__` cannot spoof; non-str marker falls through to the plain `TypeError` before any `unsafe`; non-UTF8/surrogate strs fail `extract::<&str>` → same safe path). Error-path ordering matches design §3 "exotic objects" claim.
- Traced `span_to_pyobject` (`cross_cdylib.rs:99-119`): fast-path gate `Span::type_object(py).is(&span_type)` is correct — inside `fltk._native`, `m.add_class::<Span>()` and `type_object` share the same lazy type object, so identity holds; in a consumer cdylib the lazily-created local type differs → slow path. `Py::new(py, span.clone())` preserves `source: None` for sourceless spans and the Arc for source-bearing spans; field-for-field equivalent to the old `call1`/`with_source` construction for all observables except the intended Arc-identity change.
- Slow path: `source_as_py` clones only the Arc; `_with_source_unchecked` executes in `fltk._native`'s copy of the rlib, so pyo3 converts the returned `Span` with the canonical type cache — the "always return `fltk._native.Span`" invariant in every emitted getter holds. Two accessor reads share one `Arc<SourceInner>` → `Arc::ptr_eq` in `coerce_source` (`span.rs:194-201`) succeeds → merge fix is real on both fast and slow paths.
- `Span::with_source` (`span.rs:221`) untouched: pyo3-extracted `&SourceText` still rejects foreign objects (pinned by `test_with_source_keeps_exact_behavior`).
- Generator (`fltk/fegen/gsm2tree_rs.py`): `to_pyobject` `span_type` parameter drop is consistent at all call sites (`children` getter, `child`, `children_/child_/maybe_<label>`); `py_param` logic correct for all variant combinations (`_rule_info` raises on empty models, so the zero-variant `_py` branch is dead); `extract_from_pyobject` and append/extend paths keep `get_span_type` and are untouched. Note: the pre-existing dead branch at `gsm2tree_rs.py:478-480` (`let _ = (py, span_type);` referencing `_py`/`_span_type`-named params) would not compile if ever reached, but it is unreachable and outside this diff.
- `extract_span` child-append path clones the source Arc on both its fast and slow paths, so the append→read-back→merge test scenario is sound, not coincidental.
- Soundness contract delta (forgeable marker → UB; pyo3-resolution skew → matching marker over divergent layouts) is a deliberate, documented design decision with `TODO(crosscdylib-abi-sentinel)` at the site — not a finding.
- Empirical gates run at HEAD: `make gencode` → zero tracked-file drift (committed generated files exactly match the generator; no hand-patches); `make build-native build-test-user-ext build-fegen-rust-cst` clean; full `uv run pytest` 1038 passed (cross-cdylib fixture tests ran, did not skip); `cargo clippy -- -D warnings` clean on fltk-cst-core; slug grep over `*.py`/`*.rs`/`*.pyi` empty.

## Findings

### correctness-1
- File: `TODO.md:17` (the `crosscdylib-abi-sentinel` entry).
- What: the slug `span-source-as-py-crosscdylib` still appears once in `TODO.md`, in the sentinel entry's prose ("added in the `span-source-as-py-crosscdylib` fix").
- Why: design §4 item 5 states the completion gate as "the slug is absent from `TODO.md`"; that gate fails as written at HEAD. (Design §2.7 simultaneously asks the sentinel entry to credit the SourceText marker's provenance, so the design is internally in tension; the implementation followed §2.7.)
- Consequence: anyone running the design's stated slug-grep gate against `TODO.md` gets a false failure, and slug-based tooling or a reader scanning `TODO.md` may conclude the `span-source-as-py-crosscdylib` work is still open. No runtime effect.
- Suggested fix: reword the sentinel entry to describe the marker without naming the retired slug (e.g. "added when `extract_source_text` was introduced"), or amend the gate wording to "no slug *entry/heading* in TODO.md".

No logic, control-flow, or data-flow defects found in the Rust core changes, the generator changes, or the regenerated code.
