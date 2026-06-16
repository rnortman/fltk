# ELI5: Adding line/column, filename, and error formatting to spans

## What this is about

FLTK is a Python library for building parsers and compilers. When you feed it a grammar (a description of a language's syntax), it generates a parser that can read source code in that language and produce a Concrete Syntax Tree (CST) -- a structured representation of the source. FLTK has two backends: a pure-Python one and a Rust one (exposed to Python via pyo3 bindings). The Rust backend is meant to be a near-drop-in replacement for the Python one -- downstream applications should not need to rewrite their code when switching between them.

When a parser reads source code, it produces "spans" -- objects that record where in the source text a particular syntax element starts and ends. Every span carries a reference to the full source text it came from (shared, not copied per span), so you can always ask a span "give me the text you cover." This is the `text()` method.

The problem is that spans cannot tell you anything else about their location. If you are writing an error message and want to say "error on line 5, column 12 of file foo.clk," you cannot get that from a span. There is no `line_col()` method, no `filename()` method, and no shared utility to render a caret-annotated error line (the kind that shows the offending source line with a `^` pointing at the problem). Every application that uses FLTK to build a compiler has to reimplement all of this from scratch.

A concrete example: clockwork, an out-of-tree consumer of FLTK, has a hand-rolled error formatter that takes a span, digs into its raw integer start position (which is not part of the public cross-backend protocol), calls a line/column lookup function that lives on an internal parser object, threads a separate `terminals` argument purely to work around the fact that the line-span it gets back has no source text attached, and formats a clockwork-specific `ModuleID` object to get the filename. Every piece of this is a workaround for something FLTK does not provide. And every other consumer that wants caret-annotated errors must do the same.

This design adds three things to close the gap: (1) line/column lookup directly on spans, (2) optional filename tracking so a span can tell you which file it came from, and (3) a shared error-formatting function that renders a caret-annotated error line, so consumers stop reimplementing it.

## The parts of the system you need to know about

**SpanProtocol** is a Python protocol (think: interface) that defines what methods any span must have, regardless of which backend produced it. It currently has methods like `text()`, `has_source()`, `merge()`, and `intersect()`. It deliberately omits `.start` and `.end` (raw integer positions) because their exact semantics could differ between backends. Both the Python `Span` and the Rust `Span` satisfy this protocol. Any code that types its span arguments as `SpanProtocol` works with both backends.

**SourceText / SourceInner** is the object that holds the actual source string. On the Rust side, `SourceInner` holds the text in an `Arc` (a reference-counted smart pointer), so all spans from the same parse share one allocation. On the Python side, `SourceText` is a thin frozen dataclass wrapping a string. When a span is created by the parser, it gets a reference to this shared source. That is how `span.text()` works -- it slices into the carried source.

**TerminalSource** is the parser's internal representation of the input. It holds a `SourceText` plus cached metadata (like a table mapping codepoint positions to byte offsets, and a lazily-built table of line-ending positions). It has a method `pos_to_line_col(pos)` that takes a raw integer position and returns a `LineColPos` (a small object with `line`, `col`, and `line_span` fields). This method exists on both backends but is not exposed on `SpanProtocol` and is not even callable from Python on the Rust backend.

**The Rust crate layout** matters because it constrains where code can live. There are three relevant crates:

- `fltk-cst-core`: the lowest-level crate. Defines `Span`, `SourceInner`, `SourceText`. This is where the pyo3 (Python-visible) `Span` type lives.
- `fltk-parser-core`: depends on `fltk-cst-core`. Defines `TerminalSource`, `LineColPos`, and the `pos_to_line_col` bisect algorithm.
- `fltk-native`: the pyo3 extension module (cdylib). Depends on `fltk-cst-core` only -- it does not depend on `fltk-parser-core`.

The dependency arrows all point downward toward `fltk-cst-core`. This means code in `fltk-cst-core` cannot call code in `fltk-parser-core` (that would create a cycle), and `fltk-native` cannot call code in `fltk-parser-core` (no dependency edge exists). So if we want the pyo3 `Span` to have a `line_col()` method, the line/column logic must live in `fltk-cst-core`.

**Generated parsers.** FLTK generates parser source code from grammars. There are two generators: `gsm2parser.py` emits the Python parser, and `gsm2parser_rs.py` emits the Rust parser. The generated code is checked in but is not hand-edited -- changes go through the generators, then a reformat step (`make fix`), then a commit. This "regen, fix, commit" flow is important because some of the changes in this design touch the generators and require regeneration.

## What we are going to do and why

### Move the line/column algorithm down into the lowest crate

Today, `LineColPos` (the return type) and the bisect algorithm that computes line/column from a position live in `fltk-parser-core`. The pyo3 `Span` lives in `fltk-cst-core`. An earlier draft of this design concluded the algorithm would have to be duplicated -- reimplemented in `fltk-cst-core` alongside the original in `fltk-parser-core`. The project owner rejected this duplication. The algorithm depends only on things that already exist in `fltk-cst-core` (a string, an integer position, and the `Span` type), so there is no reason it cannot move down.

The design moves `LineColPos` and a new free function `resolve_line_col` into `fltk-cst-core/src/span.rs`. The existing `TerminalSource::pos_to_line_col` in `fltk-parser-core` becomes a thin wrapper that delegates to the shared function. The `fltk-parser-core` crate re-exports `LineColPos` from `fltk-cst-core`, so any downstream Rust code using `fltk_parser_core::LineColPos` continues to compile without changes. No new dependency edges are needed (the `fltk-parser-core -> fltk-cst-core` edge already exists), and no cycle is created.

The shared function's signature takes the source text, an already-clamped position, and a caller-owned `OnceLock<Vec<i64>>` for the line-ends cache. Passing the cache in (rather than owning it inside the function) lets each caller control cache lifetime: the parser caches on `TerminalSource`, the span caches on `SourceInner`.

Three alternatives were considered and rejected:
- Making `fltk-cst-core` depend on `fltk-parser-core` would create a dependency cycle.
- Adding an `fltk-native -> fltk-parser-core` edge would pull a non-pyo3 crate into the cdylib link, violating the deliberate separation and bloating the binary.
- Extracting a third crate would be mechanically correct but cause maximum disruption by moving the established pyo3-linked types.

### Add `line_col()`, `line_col_or_raise()`, and `filename()` to the span protocol

Three new methods are added to `SpanProtocol`:

**`line_col() -> LineColPos | None`** returns the line and column of the span's start position, or `None` if the span has no source or its start position is invalid.

**`line_col_or_raise() -> LineColPos`** does the same thing, but raises `ValueError` instead of returning `None`. This is the form used by error-reporting code that expects a valid span and wants a loud failure on a sentinel. This pair mirrors the existing `text()` / `text_or_raise()` pattern. The error formatter (described below) uses the raising form, since parser-produced spans always carry source.

**`filename() -> str | None`** returns the optional filename carried by the span's source, or `None` when the source has no filename or the span is sourceless. This lets a formatter or any consumer learn a span's file without threading a separate filename argument.

**Why start-only, not start and end?** Every current consumer (clockwork's error formatter, the new shared formatter) wants only the start position -- the caret points at where the error begins. Reporting the end would require either a second method or changing the return shape. The design reports start only; adding end-position support later would be additive, not breaking. This remains an open question (see below).

**Why 0-based?** The existing `pos_to_line_col` on both backends returns 0-based line and column. Clockwork has two consumption sites with different conventions: the human-readable error header adds `+ 1` for display, while the caret-indent line uses the raw 0-based column for spacing. Switching to 1-based would silently break both. The new error formatter owns the `+ 1` display convention so consumers do not need to think about this.

**Tabs count as one column** (one codepoint), matching the existing algorithm. No tab expansion.

**The return type is `LineColPos`**, which carries `line`, `col`, and `line_span` (a span covering the full offending line). Returning a bare `(line, col)` tuple was rejected because it would drop the `line_span`, which the error formatter needs to render the source line. The `line_span` returned by the new span method is source-bearing on both backends (you can call `.text()` on it), which is an improvement over the existing Python `pos_to_line_col` whose `line_span` is sourceless. This removes clockwork's workaround of threading a `terminals` argument just to read the line text. The legacy Python `TerminalSource.pos_to_line_col` is not touched -- it keeps returning a sourceless `line_span` to avoid perturbing its existing consumers.

### Guard against invalid spans before delegating to the shared algorithm

The span-level `line_col()` applies a guard before calling the shared `resolve_line_col`. It returns `None` when:

- The span has no source attached (`UnknownSpan`, or a consumer-built sourceless span).
- The span's start is negative (the `-1` sentinel used for uninitialized CST node fields).
- The span's start exceeds the source length.

This guard matters because the shared algorithm (inherited from `pos_to_line_col`) treats `pos = -1` as in-domain and returns `LineColPos(line=0, col=-1)` rather than signaling "no valid position." The span method intercepts this and returns `None` instead, which is the right answer for a sentinel span meaning "no position."

This is a deliberate divergence from the legacy `pos_to_line_col` behavior on both backends. The legacy methods themselves also disagree on negative positions: the Rust one rejects `pos < -1` but accepts `pos == -1`, while the Python one has no negative guard at all and lets any negative position flow into the bisect. The new span method uniformly returns `None` for any negative start. The test plan includes explicit tests pinning this divergence.

### Cache line-ending positions on the shared source allocation

On the Rust side, a new lazily-initialized `line_ends` cache is added to `SourceInner`. Because `SourceInner` is shared (via `Arc`) across all spans from the same parse, the O(N) scan to find newlines happens at most once. After that, each `line_col()` call does an O(log N) binary search.

On the Python side, the `Span` is a frozen dataclass with `__slots__` -- it cannot hold a mutable cache. So Python's `Span.line_col()` recomputes the line-ends scan on every call. This is a performance asymmetry between backends, accepted because line/column lookup is a cold path (error reporting, not every parse). A future follow-up could add a cache to the Python `SourceText` and thread it through, but it is not worth the plumbing for a cold path.

On the Rust side, there will temporarily be two line-ends caches over the same source text: one on `TerminalSource` (used by the parser) and one on `SourceInner` (used by spans). Both derive deterministically from the same immutable text, so they cannot disagree. A future follow-up could consolidate them. Both follow-ups are captured as TODOs.

Adding a field to `SourceInner` does not trip the cross-cdylib ABI probe, because the probe measures the size of `SourceText` (which holds only an `Arc` pointer), not `SourceInner` itself.

### Make `LineColPos` a pyo3 class

For the Rust `Span.line_col()` to return a `LineColPos` that Python can use, `LineColPos` must become a pyo3 class. It gets a conditional `#[pyclass(frozen, eq)]` attribute (compiled only when the `python` feature is active). When `fltk-parser-core` builds `fltk-cst-core` with `default-features = false`, it never sees the pyo3 annotations, so `LineColPos` remains an ordinary Rust struct for pure-Rust use.

The pyclass must be registered through the full pyo3 module chain (exported, re-exported, imported, and registered with `add_class`) or it will not be importable from Python.

This means there are two `LineColPos` classes at the Python level: the existing Python dataclass in `terminalsrc` and the new Rust-backed pyclass in `fltk._native`. This parallels the existing Python/Rust `Span` situation -- two distinct classes, both exposing the same fields. The protocol annotates the return type using the Python class as canonical; consumers access `.line`, `.col`, `.line_span` on either.

The `line_span` getter on the pyo3 class returns an owned (cloned) `Span`, not a borrow. This is an O(1) operation (just an `Arc` pointer bump, no string copy) because `Span` is `Clone` via its `Arc<SourceInner>`.

`LineColPos` equality is value-equal and source-ignoring: two `LineColPos` values whose `line_span` fields differ only in attached source compare equal. This matches the Python dataclass behavior (where the `_source` field has `compare=False`) and means cross-backend equality assertions in the tests are not surprised by source attachment differences.

### Add optional filename tracking on the source allocation

A new optional `filename` field is added to the source allocation (`SourceInner` on Rust, `SourceText` on Python), stored once and shared by all spans from that source. The `filename()` method on `SpanProtocol` reads through to this field (or returns `None`). The filename is caller-provided at construction time, purely stored and retrieved, never interpreted by the runtime. `TerminalSource("source code")` keeps working exactly as before; `TerminalSource("source code", filename="foo.clk")` adds the optional metadata.

The filename must reach parser-produced spans, not just hand-built `SourceText` objects. On the Python side, `TerminalSource` gets a `filename` parameter, and the generated parser's `_source_text` construction expression is updated to pass `terminalsrc.filename` through to `SourceText`. On the Rust side, the generated Rust parser constructor (`Parser::new`) is updated to accept an optional `filename` and thread it into `SourceText::from_str`. Both parser generators must be updated and their outputs regenerated.

On the Python `Span`, a new `_source_filename` field (with `compare=False, hash=False`) carries the filename without affecting span equality or hashing -- the same pattern already used by the `_source` field.

**Why both parser generators need updating.** On the Rust backend, the generated pyo3 parser constructor takes a raw string and builds `SourceText` itself -- it never accepts a caller-built `SourceText`. Adding `filename` to the `SourceText` constructor alone would not help Rust parser-produced spans. The Rust parser generator must also emit a `filename` parameter so that `Parser(source, filename="foo.clk")` works. Without this, the cross-backend filename equivalence test would be untestable on the Rust backend.

**The Python regen and the Rust `SourceText` constructor change must land atomically.** The generated Python parser constructs `SourceText(text=..., filename=...)`, but at runtime this call resolves to the Rust pyo3 `SourceText` when the Rust backend is available. If the Python regen ships before the Rust constructor gains its `filename` parameter, every parse raises `TypeError`. These changes cannot be merged independently.

### Add a shared error-formatting function

A new public function `format_source_line` is added in a new module `fltk/fegen/pyrt/error_formatter.py`. It takes a `SpanProtocol`-typed span and a message string, and produces a multi-line string showing the offending source line with a caret:

```
In foo.clk:5:12:
    let x = 42 +
               ^
Expected an expression
```

The function calls `span.line_col_or_raise()` (so a sentinel span raises rather than producing garbage), reads the line text from `lc.line_span.text()` (which works because the line span is now source-bearing), and renders 1-based line/column in the header while using 0-based column for the caret indent.

An optional keyword-only `filename` parameter lets callers override `span.filename()`. When supplied, it wins over `span.filename()`. When both are `None`, the header degrades to `At line 5, column 12:` with no file prefix. This lets clockwork pass its rendered `ModuleID` path while using the shared formatter for everything else.

The formatter is placed in a dedicated module rather than the existing `errors.py` because `errors.py` is the parser's `ErrorTracker`/`ParseContext` machinery -- an unrelated concern.

The empty-source `col = -1` corner case is harmless here: Python's `' ' * -1` evaluates to the empty string, so the caret lands at column 0 with no special-casing.

**What clockwork keeps and what it drops on migration.** Clockwork drops its hand-rolled caret assembly and the `get_span(..., terminals)` sourceless fallback. It keeps its `ModuleID`-to-path rendering, passing the result as the `filename` argument. It migrates the span annotation from the concrete `terminalsrc.Span` to `SpanProtocol`.

The formatter deliberately does not subsume clockwork's caret-less parse-error path, which works from a raw integer position rather than a span (see open questions below).

## What could go wrong and how it is handled

**Backend divergence on multibyte input.** This is the single most important failure mode. If the Python and Rust backends counted columns differently for multibyte characters, error carets would point to the wrong place on one backend. Both backends count codepoints, not bytes. The line-ends table stores codepoint indices of newlines. The shared algorithm guarantees identical results. The test plan includes explicit multibyte cross-backend equivalence tests.

**Backend divergence on filename.** Mitigated by the filename being a stored-and-retrieved opaque string with no interpretation on either backend. Cross-backend equivalence tests parse on both backends with a filename set and assert the parser-produced spans report the same filename.

**Line-ends cache staleness.** Not possible. The source text is immutable after construction, and `OnceLock` initializes exactly once.

**Protocol `isinstance` breakage.** Adding methods to a `@runtime_checkable Protocol` causes `isinstance(x, SpanProtocol)` to return `False` for any class implementing only the old method set. Both in-tree backends are updated together. Out-of-tree consumers with hand-written `SpanProtocol` stubs must add the three new methods -- this is inherent to extending a runtime-checkable protocol and happened before when `merge`/`intersect` were added.

**Formatter on a sentinel span.** `format_source_line` calls `line_col_or_raise()`, so an uninitialized `UnknownSpan` raises `ValueError` rather than producing a misleading caret.

**Empty source corner case.** With `source = ""` and `start = 0`, the EOF clamp fires and the algorithm yields `col = -1`. This is a property of the existing algorithm, not new behavior. Both backends agree.

**Atomic landing risk.** If the Python parser regen merges before the Rust `SourceText` constructor gains its `filename` parameter, every Python parse under the Rust backend breaks at runtime. The design calls out that these must land together.

## What is still open

### 1. Should spans also report the end position's line/column?

The design reports only the start position. Every current consumer wants exactly that -- the error caret points at where the problem begins. If a future consumer wants multi-line span underlining (highlighting from start to end), that would require either a separate `end_line_col()` method or a different return shape. The formatter design cements start-only by pointing one caret at the start. Adding `end_line_col()` later would be purely additive and non-breaking, so deferring does not foreclose anything. The question is whether to do it now (more surface area, no known consumer) or later (less scope, add when needed).

### 2. Should `col = -1` for empty source be cleaned up?

When the source is empty and start is 0, the algorithm yields `line=0, col=-1`. Both backends agree. The formatter renders it harmlessly (caret at column 0). The question is purely cosmetic: should `LineColPos.col` read `-1` or `0` for this edge case? Preserving `-1` keeps the span method consistent with the existing `TerminalSource.pos_to_line_col`. Changing to `0` would diverge the two and add a special case. The stakes are low either way.

### 3. Do we need a formal `LineColPos` protocol or union type?

The Python and Rust backends each have their own `LineColPos` class. The protocol annotates the return as the Python `LineColPos`, and both classes expose the same `.line`, `.col`, `.line_span` fields, so field access works fine. But if a consumer needs to `isinstance`-check a `LineColPos` across backends, they would need either an `AnyLineColPos` union type or a `LineColPosProtocol`. No known consumer does this today -- clockwork accesses `LineColPos` only via field access on a return value, never importing the class directly.

Relatedly, the legacy Python `TerminalSource.pos_to_line_col` returns a sourceless `line_span`, while the new `Span.line_col()` returns a source-bearing one. The design deliberately does not "fix" the legacy method to avoid perturbing its consumers. The question is whether this scope boundary is right, or whether the legacy path should also be made source-bearing for full parity.

### 4. Should the shared formatter also cover the caret-less parse-error path?

`format_source_line` covers the span-based, caret-annotated error. Clockwork also has a separate caret-less parse-failure formatter that works from a raw `error_position()` integer (not a span) and formats a line/column header without a caret. The design does not subsume this because it has no span to operate on. If FLTK should also own that path, it would need a second helper taking a raw position and a source. This is a small additional surface if wanted.

### 5. Is `line_col_or_raise` necessary?

The design ships both `line_col()` (returns `None`) and `line_col_or_raise()` (raises), mirroring `text()` / `text_or_raise()`. The formatter uses the raising form. If only `line_col()` shipped, the formatter and clockwork would need to handle `None` explicitly even though parser-produced spans always have source and never return `None` in practice. Shipping both halves the boilerplate for the common case. The question is whether the added protocol surface is worth the ergonomic benefit.
