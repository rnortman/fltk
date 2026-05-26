# Phase 1 Request: Span / TerminalSource Rust design

Audience: smart human/LLM. Concise. Precise. No padding.

## Goal

Execute Phase 1 of the PyO3 CST implementation plan. Phase 0 is done.

## Critical input documents (read these)

- Phase plan (Phase 1 is the relevant section): `docs/adr/2026/05/25-pyo3-cst-plan/phase-plan.md`
- Documents referenced by the phase plan, all critical inputs:
  - `docs/adr/2026/05/25-rust-backend-exploration/README.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/synthesis.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/analysis-rust-cst-first.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/analysis-iir-adaptation.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/analysis-alternative-irs.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/analysis-separate-reimplementation.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/explore-cst-interface.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/explore-iir.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/explore-parser-gen.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/explore-pygen-plumbing.md`
  - `docs/adr/2026/05/25-rust-backend-exploration/explore-unparser-gen.md`
- Phase 0 ADR (completed predecessor, for context): `docs/adr/2026/05/25-pyo3-phase0-rust-infra/`

## Extra information from the user (verbatim)

One thing the phase plan undersells -- doesn't mention at all really -- is that this involves the design of the Rust equivalent of TerminalSource. This is a critical design decision for memory efficiency, and it needs careful consideration. I'll add another note, which is that the Python design has a really inconvenient feature, which is that CST nodes carry a Span but, critically *no reference to the actual source text that it's a view into*. In practice, user applications bundle CST nodes together with a TerminalSource in some kind of compiler context, because you cannot even generate good compiler errors without access to the TerminalSource. We need to remain *compatible with* the Python API, but we must not repeat the mistakes of the Python API. We should do *better* in the Rust implementation, and we should expose both a compatible Python API and a *better* Python API, one which allows you to always access the source text of a CST node. But, and this is critical, we also need to be able to support use cases where synthetic CST nodes are created (e.g., automated refactoring tools) from which we then generate new source text by unparsing; these synthetic CST nodes may not have source text or may have a span into their own private TerminalSource representing their source text.
