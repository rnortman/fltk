# TODO burndown triage: `backend-with-source-signature`

Concise. Precise. Token-dense — no fluff, full information. No preamble. No padding.

## Claim verification

**Claimed:** "Python backend takes a raw `str` while the Rust backend takes a `SourceText` handle."
**Status: ACCURATE.**

- Python `Span.with_source(cls, start: int, end: int, source: str)` — `fltk/fegen/pyrt/terminalsrc.py:115`.
- Rust `fn with_source(_cls, start: i64, end: i64, source: &SourceText)` — `src/span.rs:117`.
- `SourceText` is a separate `#[pyclass(frozen)]` struct wrapping `Arc<SourceInner>` — `src/span.rs:29-46`.

**Claimed:** "`fltk/fegen/pyrt/span.py` is the location."
**Status: ACCURATE.** `fltk/fegen/pyrt/span.py` is the backend-selector module (25 lines), imports from `terminalsrc` or `fltk._native`, re-exports `SourceText`, `Span`, `UnknownSpan`. The TODO comment is at `span.py:7`.

**Claimed:** "Code using `from fltk.fegen.pyrt.span import Span` that calls `Span.with_source(start, end, src_str)` breaks silently when the Rust backend is active."
**Status: PARTIALLY ACCURATE, with a correction.**
It does not break *silently*. Passing a plain `str` to Rust `Span.with_source` raises a `TypeError` at the call site (PyO3 type coercion rejects `str` for `&SourceText`). The failure is noisy, not silent. However the TODO text predates the current `span.py:3-6` doc-comment which already documents this and warns callers. The `span.py` module-docstring now explicitly says:
```
Code calling `with_source` must either know which backend is active or branch on
`SourceText is not None`.
```

**Claimed:** "`with_source` intentionally excluded from `SpanProtocol`."
**Status: ACCURATE.** `SpanProtocol` (`fltk/fegen/pyrt/span_protocol.py:9-57`) has no `with_source` method. The test at `tests/test_span_protocol.py:62-73` verifies `SpanProtocol` does not require `start`/`end` attributes.

## Current state of the divergence

### Additional divergence not mentioned in TODO

The TODO mentions only the `with_source` signature. There is a second divergence:

**`span.start` and `span.end` attributes are absent on the Rust backend.**

- Python `Span` is a `@dataclass(frozen=True, slots=True)` with public `start: int` and `end: int` fields — `terminalsrc.py:33-39`.
- Rust `Span` has `pub(crate) start: i64` and `pub(crate) end: i64` — `src/span.rs:66-67`. There are NO `#[getter]` decorators for `start` or `end`; the test at `tests/test_rust_span.py:60-74` asserts accessing `.start` raises `AttributeError`.
- Production code in `fltk/fegen/fltk2gsm.py:26,147,151` calls `span.start` and `span.end` directly on spans derived from the Python-backend `TerminalSource.consume_literal/consume_regex`. Generated parsers (`fltk_parser.py`, `bootstrap_parser.py`) construct `Span(start=..., end=-1)` using `fltk.fegen.pyrt.terminalsrc.Span` directly (hardcoded import), not the backend-selector `span.py` module. So these parsers are permanently Python-backend-only.

## Active callers of `with_source`

**In production code:** zero callers of `with_source` found outside of test files and the definition sites. `grep -rn '\.with_source'` in `fltk/` (excluding tests and definitions) returns only `span.py:3` (the doc comment).

**In tests:**
- `tests/test_span_protocol.py:19`: `PySpan.with_source(0, 5, "hello")` — calls directly on the Python class (not the backend-selector), so it is always correct.
- `tests/test_rust_span.py:48,88,100,etc.`: All use `SourceText(...)` before calling `Span.with_source(...)` — correct Rust usage.

No in-tree code calls `Span.with_source` via the backend-selector import path (i.e., `from fltk.fegen.pyrt.span import Span; Span.with_source(...)`). The risk described is theoretical for in-tree code.

## Parse path / source-bearing spans

**Claimed deferral condition:** "until the parse path is wired to produce source-bearing spans (Phase 2+)."

**Status: The parse path does NOT produce source-bearing spans today.** Generated parsers (`fltk_parser.py`, `bootstrap_parser.py`) construct `Span(start=pos, end=-1)` and `Span(start=result.span.start, end=pos)` using the unsourced two-argument constructor. `fltk2gsm.py` consumes spans via `span.start`/`span.end` and indexes `self.terminals` directly. No parser code calls `with_source` at all. The deferral condition has not been reached.

## Feasibility of the proposed fixes

**Option A: expose a `SourceText`-like wrapper in the Python backend.**
Feasible. `terminalsrc.py` could add a `SourceText` class that wraps `str`, and `with_source` could accept `str | SourceText`. This unifies the call signature. The risk is that `SourceText` is semantically different between backends: in Rust it is an `Arc`-shared heap allocation (one copy per source); in Python any wrapper would be a thin `str` container. Cross-backend identity semantics would differ.

`fltk/fegen/pyrt/span.py:14` already sets `SourceText: type | None = None` for the Python path, then overwrites it from `fltk._native` in the Rust path. A Python `SourceText` could be injected here.

**Option B: accept both types in the Rust backend.**
Feasible as a PyO3 change: `source: &PyAny` with a downcast attempt on `SourceText` first, then a `str` extraction. Increases Rust complexity, breaks the clean `SourceText`-only API design.

## Blockers not mentioned in TODO

1. **The `span.start`/`span.end` divergence is a prerequisite blocker.** Before source-bearing spans can be wired into the parse path end-to-end, consumers (`fltk2gsm.py:26,147,151`) that access `.start`/`.end` must either switch to `.text()`/`.text_or_raise()`, or the Rust `Span` must expose `start`/`end` as getters. This is explicitly blocked by `SpanProtocol` design (protocol omits `start`/`end` because index semantics differ).

2. **Generated parsers import `fltk.fegen.pyrt.terminalsrc.Span` directly**, bypassing the backend selector. Wiring source-bearing spans through the parse path would require generator changes in `gsm2parser.py` so emitted code uses the backend-selector `Span` and `SourceText`.

3. **`fltk2gsm.Cst2Gsm` calls `self.terminals[span.start : span.end]`** — this pattern is incompatible with the Rust backend where `.start`/`.end` are not exposed. The `rust-cst-child-span-test` TODO (`TODO.md:61`) already notes this gap with the same files.

## Is this papering over a symptom?

The deeper problem: the Python parse path produces sourceless spans (bare index-pairs) and then separately carries the source string through `self.terminals` in the visitor. Attaching source to spans (`with_source`) is only needed if spans become the sole carrier of text, which the parse path does not yet do. The `with_source` divergence is a symptom of a half-completed architectural step (source-bearing spans), not a standalone wart. The TODO accurately defers it to when that step completes.
