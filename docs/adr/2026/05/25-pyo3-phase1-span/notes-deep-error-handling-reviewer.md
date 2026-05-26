Commit reviewed: 90074aa

---

errhandling-1
File: src/span.rs:98-105
Path: `Span::text_or_raise`
The error message is "Span({}, {}) has no source text" regardless of the actual failure mode. `text()` returns `None` for five distinct reasons: no source, negative indices, start > end, end out of bounds, and mid-codepoint boundary. `text_or_raise` collapses all of them into a message that implies only the "no source" case. An on-call engineer seeing "Span(0, 2) has no source text" when the span has a source but straddles a UTF-8 boundary will waste time looking for a missing `SourceText` attachment.
What must change: diagnose inside `text_or_raise` (or return a richer error enum from `text`) and emit a message that names the actual failure — separate messages for sourceless, negative indices, inverted range, out-of-bounds, and mid-codepoint.

---

errhandling-2
File: fltk/fegen/pyrt/terminalsrc.py:25-29
Path: `Span.text_or_raise` (pure-Python)
Same issue as errhandling-1: the message "Span(start, end) has no source text" is emitted for every failure mode of `text()` — including when source is present but end > len(source) or indices are negative. This obscures the actual cause from diagnostic messages.
What must change: align with the fix for errhandling-1; diagnose failure reason before raising.

---

errhandling-3
File: fltk/fegen/pyrt/span.py:7-10
Path: backend selector `try/except ImportError`
`ImportError` is caught but a different exception class — e.g. `AttributeError` if the extension builds but is missing `SourceText` or `Span`, or any `PyO3` initialisation panic that surfaces as a non-`ImportError` exception — will propagate uncaught and crash the import of `fltk.fegen.pyrt.span` entirely, with no diagnostic message. The *intent* is "fall back silently to Python backend," but the guard is too narrow to achieve that intent reliably.
Consequence: a partially-broken Rust build (e.g. ABI mismatch causing `OSError`, or a name missing from the module causing `ImportError` from a sub-import) crashes the import rather than falling back; on-call sees a raw traceback with no hint that a Python fallback exists.
What must change: either widen the catch to `Exception` with a logged warning (e.g. `warnings.warn`), or narrow the contract so the extension is guaranteed to export both names or nothing (and document that guarantee). The same applies to the parallel `try` in `span_protocol.py:21-26`.

---

errhandling-4
File: src/lib.rs:27-32
Path: `Py::new(m.py(), unknown)?`
`Py::new` can fail (OOM or GIL not held); the `?` propagates to the module-init function which returns `PyResult<()>`. PyO3 will convert that to a Python `ImportError`. This is correct propagation — the module fails to load cleanly rather than silently. No fix needed, noted for completeness.

---

errhandling-5
File: src/span.rs:78-96
Path: `Span::text` — silent `None` on mid-codepoint indices
When `start` or `end` lands inside a multi-byte codepoint, `text()` silently returns `None`. This is a reasonable design choice for the *caller-facing API*, but there is no log or debug trace, so if a bug in the parser generator produces a mis-aligned span, the failure is invisible until `text_or_raise` raises a confusing "no source text" message (see errhandling-1). No silent state corruption occurs, so this is purely a diagnosability concern tied to errhandling-1; it does not require a separate fix beyond that one.

---

errhandling-6
File: fltk/fegen/pyrt/terminalsrc.py:43-44 (merge) and 50-56 (intersect)
Path: `Span.merge` source-identity check uses `is` (identity), not `==` (equality)
This is intentional design (same object required), and the ValueError on mismatch is correctly raised and propagated. No error-handling defect. Noted for completeness.

---

Summary of actionable findings: errhandling-1, errhandling-2, errhandling-3.
