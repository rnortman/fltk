# Dispositions: User Notes on Design

Source: `notes-design-user.md` (3 findings). Round: user revision (authoritative — not reviewable).

---

note-1 (two swappable backends):
- Disposition: Fixed
- Action: Rewrote entire design architecture. Previous design replaced Python Span with Rust. New design retains pure-Python Span, adds Rust as a second backend, introduces `span.py` backend selector, and keeps `terminalsrc.py` as the pure-Python implementation (updated with better API). Affects: Root Cause/Context, Proposed Approach (all subsections), File Changes table, Test Plan (split into per-backend test files), Edge Cases.
- Severity assessment: Fundamental misread of the assignment. The previous design would have eliminated the pure-Python Span, making the Rust toolchain a hard dependency for all FLTK users.

note-2 (Span Protocol + union type alias):
- Disposition: Fixed
- Action: Added `SpanProtocol` (typing.Protocol, @runtime_checkable) and `AnySpan` (Union type alias) in new `fltk/fegen/pyrt/span_protocol.py`. SpanProtocol defines the shared interface (start, end, text, text_or_raise, has_source). AnySpan is the union of concrete implementations for isinstance. Added test_span_protocol.py to test plan. Affects: Proposed Approach (new "SpanProtocol" and "Backend Selection" sections), File Changes table, Test Plan.
- Severity assessment: Without this, code wanting to work with both backends would have no type-safe way to annotate Span parameters or perform isinstance checks.

note-3 (throwing variant of text()):
- Disposition: Fixed
- Action: Added `text_or_raise()` method to both backends. Returns `str` (not `str | None`). Raises `ValueError` when span has no source text or indices are invalid. Name chosen: `text_or_raise` — user rejected "ensure_text"; `text_or_raise` follows the `x_or_raise` convention and clearly communicates the contract. Added to SpanProtocol. Added dedicated tests (test 9-10 in Python backend, mirrored in Rust backend). Affects: Proposed Approach (new "text_or_raise" section), Python API, Rust API, SpanProtocol, Test Plan.
- Severity assessment: Without this, every call site using `text()` would need a manual None-check-and-raise pattern, creating boilerplate throughout the codebase.
