No findings.

Reviewed commit: 1144c7f615093b087550946f4dbe79653821b852

---

## Review scope

The diff adds `start`/`end` properties to `SpanProtocol` and updates the test class
that previously asserted those properties were absent.  Neither file contains
application logic or new error paths; the change is purely a protocol declaration.

The following were checked as context:

- `fltk/fegen/pyrt/span_protocol.py` — the modified protocol definition and the
  `except Exception` fallback that builds `AnySpan` when the Rust extension is absent.
- `fltk/fegen/pyrt/terminalsrc.py` — the Python `Span` dataclass that satisfies the
  protocol.  `start` and `end` are frozen dataclass fields; access cannot raise.
- `fltk/fegen/pyrt/span.py` — the backend selector; the `except Exception` swallows all
  import errors and falls back gracefully with a warning, which is pre-existing and
  correct (no code change here).
- `fltk/fegen/pyrt/error_formatter.py` — consumer of `SpanProtocol`; calls
  `line_col_or_raise()` whose `ValueError` is documented and intentional.
- `crates/fltk-cst-core/src/span.rs` — Rust `Span`.  `get_start` and `get_end` are
  simple `#[getter]` methods returning `i64`; they cannot panic or raise.

No new error paths were introduced.  The `except Exception` fallback in
`span_protocol.py` and `span.py` pre-dates this diff and is unchanged.  The
`@property` stubs in the `Protocol` body are never called (Protocol members are not
executed); they declare structure only.  Both concrete backends expose `start`/`end`
as infallible accessors (frozen dataclass field; plain `#[getter]`), so adding them
to the protocol cannot introduce unhandled failure modes.
