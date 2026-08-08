//! `fltk-serde-core`: the pyo3-free runtime for FLTK's generated serde frontend.
//!
//! A generated `de.rs` is a [`serde::Deserializer`] over a CST, so that a consumer's own
//! `#[derive(Deserialize)]` types are what a `from_str` call produces — the serde_json/toml
//! architecture with the consumer's own syntax at the front. This crate is the half of that
//! which is not generated: the error type the frontend reports, the two wrapper types a
//! target can ask for, and the protocol they reach the Deserializer through.
//!
//! What lives here:
//!
//! - [`DeserializeError`], which positions serde's own unknown-field / missing-field /
//!   invalid-type messages by CST span, and [`ParseToTargetError`], the `from_str` failure.
//! - [`Spanned`] and [`Raw`], the two things a grammar cannot produce as content: a source
//!   position, and a subtree held as syntax rather than deserialized.
//! - The [`tree`] description a generated module supplies — one [`NodeShape`] impl and one
//!   [`Shape`] per rule — and the Deserializer over it that [`from_node`] runs. A CST's node
//!   types, labels and children are per-rule generated types, so what a grammar contributes is
//!   the description; serving it as serde's data model is one implementation, here, rather
//!   than one emitted per grammar.
//! - The [`channel`] side channel those two ride on, which generated code drives with
//!   [`provide`] and [`Payload`], and [`deserialize_ast`], the whole body of the `Deserialize`
//!   impl a generated AST type gets: it hands `from_cst` in over that channel, so a field
//!   declared as `ast::Expr` is spelled like any other serde field.
//! - [`scalar`], re-exported from `fltk-ast-core`, so that a numeric or float target accepts
//!   exactly the lexemes a `type:` coercion accepts, and so a consumer's `Cargo.toml` names
//!   one version of everything.
//!
//! A consumer generating only `de.rs` adds exactly two dependencies: `serde` and this crate.
//!
//! It has no pyo3 dependency (pyo3-freedom is a structural absence, matching its sibling
//! runtimes). It depends on `fltk-cst-core` for [`fltk_cst_core::Span`] and
//! [`fltk_cst_core::Shared`], which every generated CST node is reached through.

pub mod channel;
mod de;
mod error;
pub mod tree;
mod wrappers;

pub use channel::{provide, take_ast, take_conversion, take_node, take_span, Carried, Conversion, Payload};
pub use de::from_node;
pub use error::{DeserializeError, ParseToTargetError};
pub use tree::{
    Alternative, Child, Container, Content, Direction, Field, Fold, Form, Key, KeyKind, Node, NodeShape, Shape, Variant,
    Wrapper,
};
pub use wrappers::{deserialize_ast, Raw, Spanned, AST_NAME_PREFIX, RAW_NAME, SPANNED_NAME};

/// The scalar coercions a target-driven `deserialize_u16` (and its siblings) runs over a
/// node's source text.
///
/// Re-exported rather than reached through `fltk-ast-core` directly so that the accepted
/// lexemes, range behavior and message templates of the serde path and the AST path are the
/// same code, and so a `de.rs`-only consumer needs no dependency of its own for them.
pub use fltk_ast_core::scalar;

/// How a sum rule's alternatives are told apart by the labeled children a node carries.
///
/// The same vocabulary the AST converters use, so serde and AST dispatch agree by
/// construction. Re-exported so a `de.rs`-only consumer needs no dependency on
/// `fltk-ast-core`.
pub use fltk_ast_core::dispatch;

/// The upper bound a grammar sets no limit on, as a [`dispatch::Bound`] spells it.
pub use fltk_ast_core::UNBOUNDED;
