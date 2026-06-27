//! `fltk-unparser-core`: the pyo3-free runtime for FLTK's Rust unparser backend.
//!
//! This crate is a faithful port of the Python unparser's formatting pipeline
//! (`fltk/unparse/combinators.py`, `accumulator.py`, `resolve_specs.py`,
//! `renderer.py`). It provides the grammar-independent building blocks that every
//! generated Rust unparser links against — the [`Doc`] combinator tree, the
//! [`DocAccumulator`] builder, spacing resolution ([`resolve_spacing_specs`]), and
//! the Wadler-Lindig [`Renderer`].
//!
//! It has no pyo3 dependency (pyo3-freedom is a structural absence, matching
//! `fltk-parser-core`) and no `fltk-cst-core` dependency: it operates on [`Doc`],
//! not on CST spans. Terminal text is extracted in the generated code and handed
//! in as [`Doc::Text`].

mod accumulator;
mod doc;
mod render;
mod resolve;
mod result;

pub use accumulator::DocAccumulator;
pub use doc::{
    after_spec, before_spec, comment, concat, group, hardline, indent, join, line, nbsp, nest, nil,
    separator_spec, softline, text, Doc,
};
pub use render::{Renderer, RendererConfig};
pub use resolve::resolve_spacing_specs;
pub use result::UnparseResult;
