# Deep error-handling review: forged-abi-extract-span-uniformity

Commit reviewed: aa9a5f27d4d307a43bfc9115857a9e52e4a384cb (base a330940ed619771bcb4724be3e53d4f68fd8fcfe)

## Scope
Diff touches `cross_cdylib.rs` (one new gate call + comment rewrites), `span.rs` (doc comments only),
`tests/test_rust_span.py`, `TODO.md`, and an ADR note. Error-observability/response lane only.

## Result
No findings.

## Basis (verified, not paraphrased)
- The only behavioral change is `check_instance_layout::<Span>(&span_type, "Span")?;` at
  `cross_cdylib.rs:503`, inside `get_span_type`'s `get_or_try_init` closure. Error is propagated
  via `?` to a `PyResult`-returning public fn; caller (`extract_span`, `span_to_pyobject`,
  generated `cst.rs`) already handles `PyResult`. No swallow.
- Reused helper `check_instance_layout` (lines 292-339) has full error discipline: every
  `getattr`/`extract` uses `map_err` into a diagnostic `PyTypeError` (metaclass name, basicsize,
  expected size) — no `unwrap`/`expect` on Python-controlled input. The one `unwrap_or_else` (line
  303) is on `metaclass.name()` while already building an error message and falls back to
  "<unknown>"; failure is still reported, not lost.
- Gate ordering (`check_abi_pair` then `check_instance_layout`) preserves pre-existing pinned
  diagnostics; both failures surface distinct `TypeError` messages. This is a wrong-input rejection
  path (validate + reject + diagnostic), correctly classified vs. invariant-violation; no crash used
  where a diagnostic is appropriate.
- `PyOnceLock` does not cache the `Err` branch (documented at design §3 and test_rust_span.py
  comments), so a rejected forge re-runs and re-fails on every call rather than poisoning the cell —
  no silent degradation.
- No `let _ = Result`, empty catch, broad catch, or default-on-error fallback introduced. `span.rs`
  changes are doc-comment only.
