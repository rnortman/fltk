# Deep Correctness Review — span-start-end-api

Commit reviewed: 1144c7f615093b087550946f4dbe79653821b852 (base 1f75363).

Scope: `fltk/fegen/pyrt/span_protocol.py`, `tests/test_span_protocol.py`. Spec: expose
`.start`/`.end` on the SpanProtocol; remove stale byte-vs-codepoint rationale; both
Python and Rust backends conform.

## Findings

No findings.

## Verification trace

- **Protocol declaration (`span_protocol.py:18-26`).** `start`/`end` are added as
  `@property` methods returning `int`. For a `@runtime_checkable` Protocol, `isinstance`
  only checks attribute presence (not type), so a `@property` declaration is satisfied
  by both the Python dataclass field (`terminalsrc.py:55-56`) and the Rust `#[getter]`
  (`span.rs:740-751`). Confirmed by passing isinstance tests
  (`test_py_span_exposes_start_end_via_protocol`, `test_rust_span_exposes_start_end_via_protocol`).
- **Semantics claim is now accurate.** Python `Span.start/end` are direct string indices
  (`self._source[start:end]`, `terminalsrc.py:71`) = codepoints. Rust `get_start/get_end`
  return the raw `start`/`end` fields (`span.rs:741-742, 749-750`), which the crate doc
  (`span.rs:275`) defines as codepoint indices; byte translation happens only inside
  `text()`. So "`start` and `end` are codepoint indices on both backends" is correct, and
  the `len()` docstring change to "codepoints (`end - start`)" matches both
  `Span.len` impls (`terminalsrc.py:93-100` returns `end - start`; Rust `len` is codepoint).
- **No invariant violation in the cross-backend test.** `test_start_end_are_codepoint_indices_cross_backend`
  uses "café" (one multibyte codepoint) with span (0,4); both backends report start=0,
  end=4, text="café" — distinguishes codepoint (4) from byte (5) indexing. Sound.
- **Test inversion is correct.** Old `TestProtocolHasNoStartEnd` asserted absence;
  new `TestProtocolHasStartEnd` asserts presence and keeps the method-callable checks.
  No stray references to the removed assertions elsewhere.
- **No off-by-one / operator / control-flow / data-flow concerns**: the change is purely
  additive protocol surface plus docstring text; no loops, indexing arithmetic, mutation,
  or branching introduced.
- All 42 tests in `tests/test_span_protocol.py` pass (Rust extension present).
