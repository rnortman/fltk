# Rust Backend Exploration

## Sonnet explorations (code ground-truth)
- **explore-iir.md** — IIR model nodes, type system, Python-specific assumptions, Python compiler.
- **explore-parser-gen.md** — Parser generation pipeline: GSM to parser code via IIR.
- **explore-unparser-gen.md** — Unparser generation pipeline: GSM to unparser code via IIR.
- **explore-pygen-plumbing.md** — Code generation utilities, plumbing layer, full pipeline map.
- **explore-cst-interface.md** — CST node class API surface and consumer usage patterns.

## Opus analyses (judgment/design)
- **analysis-iir-adaptation.md** — Can the existing IIR be adapted for Rust codegen, and does it still earn its keep?
- **analysis-alternative-irs.md** — Off-the-shelf and custom IR designs for multi-language parser/unparser generation.
- **analysis-separate-reimplementation.md** — Cost in LoC of reimplementing generators per-language or rewriting in Rust.
- **analysis-rust-cst-first.md** — Feasibility of drop-in Rust+PyO3 CST nodes as an intermediate step.

## Synthesis
- **synthesis.md** — Cross-analysis summary: where the three main analyses agree/disagree, paths forward, key numbers.
