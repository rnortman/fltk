# Efficiency review — forged-abi-extract-span-uniformity

Commit reviewed: aa9a5f27d4d307a43bfc9115857a9e52e4a384cb (base a330940ed619771bcb4724be3e53d4f68fd8fcfe)

No findings.

## Notes

The functional change is a single added line in `crates/fltk-cst-core/src/cross_cdylib.rs`:
`check_instance_layout::<Span>(&span_type, "Span")?;` placed inside the
`FLTK_NATIVE_SPAN_TYPE.get_or_try_init(...)` init closure of `get_span_type`
(cross_cdylib.rs:503). That closure runs at most once per process, so the two
`getattr`/`__basicsize__` reads it performs are one-time init cost, not per-call.

The design (§2.1) explicitly chose this placement over a per-call check in
`extract_span` precisely to avoid adding two getattrs to every cross-cdylib span
setter call — `extract_span`'s slow path is the normal path for cross-cdylib
consumers, so a per-call gate would have been genuine hot-path bloat. The chosen
placement reuses the existing `PyOnceLock` cache and adds zero per-call cost. This
is the efficiency-optimal choice.

- No new work on any per-request/per-render hot path (`extract_span` fast path and
  the `is_instance`/`cast_unchecked` slow path are unchanged).
- No redundant computation, no new allocations, no unbounded structures.
- Everything else in the diff is comment rewrites (cross_cdylib.rs, span.rs) and
  new subprocess-isolated tests (tests/test_rust_span.py). Subprocess isolation is
  required here (fresh interpreter to force `PyOnceLock` init, plus segfault
  containment), so it is not an avoidable test-runtime cost.
