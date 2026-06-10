# Gaps report: cst-python-feature-gate spike

Findings only — no fixes. Each item is a concrete friction point encountered while implementing `crates/fltk-cst-spike/src/spike_tests.rs`. A parser backend (phase 2) would hit all of these.

## 1. No `Debug` on generated types

`Span`, `SourceText`, node structs (`Identifier`, `Items`, `Trivia`), label enums (`Identifier_Label`, …), and child enums (`IdentifierChild`, …) derive no `Debug` impl. This forces spike tests to use `assert!(a == b)` instead of `assert_eq!(a, b)`, losing diff output on failures. A real parser's test suite will be much larger; without `Debug` every failing assertion is opaque. `PartialEq` is already derived unconditionally; adding `#[derive(Debug)]` (plain structs) or a hand-written `impl Debug` (generated match arms) on all generated types would cost nothing at runtime and would make the native API a first-class Rust citizen.

Scope note: adding `Debug` to `Span` and `SourceText` is a `fltk-cst-core` change; adding it to generated types is a `gsm2tree_rs.py` change.

## 2. Span text returns `Option<String>` — allocation per read

`Span::text()` always allocates a fresh `String`. A parser slicing the same source many times pays an allocation and copy per span read. The natural alternative for most parser use-cases is a `&str` reference into the source (`&self.source.inner.text[byte_start..byte_end]`), but returning a borrowed slice requires a lifetime tied to the `Arc<SourceInner>` and does not compose easily with the current API shape (`Span` does not carry a reference to `SourceText`). Options for phase 2: a `text_ref<'a>(&self, source: &'a SourceText) -> Option<&'a str>` variant that requires the caller to pass the source explicitly, or a byte-offset accessor pair so callers can do their own slice indexing without copying.

## 3. No codepoint-to-byte-offset helper

`Span::start()` and `end()` are codepoint indices. A parser building spans from byte-level scanning (the natural mode for a Rust parser) must convert byte offsets to codepoint counts before constructing a `Span`, or do the reverse when reading `text()`. There is no provided helper. Phase 2 will need either: (a) byte-offset `Span` variants, or (b) a `SourceText` method returning a precomputed byte-to-codepoint table, or (c) a constructor accepting byte offsets directly.

## 4. No builder / incremental node construction helper

Building a node requires repeated `push_child_native` calls with explicit label `Option`s. For a parser accumulating children in a match, this is mechanical but verbose and error-prone (it is easy to pass `None` where a label was intended). A typed builder pattern (e.g. `IdentifierBuilder::new(span).name(child_span).build()`) would reduce errors and provide a clearer API contract, though it adds generated code surface. Low priority until phase 2 defines the actual construction patterns.

## 5. No span arithmetic helpers (union-by-adjacency, slice-by-offset)

`merge` computes the bounding union; `intersect` computes the overlap. A parser commonly needs: checking adjacency (`a.end == b.start`), creating a zero-length span at a position, splitting a span at a codepoint offset. None of these are currently provided. The missing operations are small and could be added incrementally.

## 6. `SpanError` is non-exhaustive but carries no context

`SpanError::SourceMismatch` is the only variant. For a parser producing diagnostics, knowing *which* two sources mismatched would be valuable. The `#[non_exhaustive]` annotation reserves the right to add more variants; the phase-2 parser error-reporting design should decide whether `SourceMismatch` should carry identifying context (e.g. a source name or ID) or whether that context lives at a higher layer.
