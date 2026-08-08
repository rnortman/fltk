//! `fltk-ast-core`: the pyo3-free runtime for FLTK's generated AST layer.
//!
//! A generated `ast.rs` names this crate by absolute path (`::fltk_ast_core::AstError`), so
//! a rule called `error` or `span` cannot collide with anything a preamble imported. The
//! crate is the Rust counterpart of `fltk/fegen/pyrt/astrt.py`: the two are written against
//! one model, and a value that converts, rejects, or renders one way on one backend does so
//! the same way on the other.
//!
//! What lives here:
//!
//! - [`AstError`] and [`ParseToAstError`], the failures conversion and the `parse_str`
//!   convenience report.
//! - [`FromCst`] / [`ToCst`], the traits a `custom(...)` rule's user type implements so
//!   generated converters can reach it.
//! - The child-reading helpers ([`one`], [`optional`], [`presence`], [`text`], [`node_text`],
//!   [`unexpected_child`], [`duplicate_key`]) a generated `from_cst` asks about the children
//!   it collected under one label.
//! - [`check_fold_arity`], [`fold_left`] and [`fold_right`], which turn a fold rule's flat run of
//!   operands and operators into the nested chain its AST type is, and [`against_direction`],
//!   which refuses a chain the grammar has no shape to render.
//! - [`TerminalPattern`], [`LazyTerminal`] and [`validate_terminal`], which keep serialization
//!   honest: text that would not re-parse is refused rather than written out.
//! - [`TerminalShape`], the other half of that honesty in the serialize direction: it splits a
//!   terminal-only rule's text back across the grammar items it was read from.
//! - [`merged_span`], the lenient covering span a diagnostic over a run of children is
//!   positioned at.
//! - The [`dispatch`] tables, which say which alternative of a sum rule a node's labeled
//!   children came from — one counting rule, described per rule and evaluated here.
//! - [`Cursor`] and its companions ([`check_group`], [`alternative_fits`], [`filled`],
//!   [`check_consumed`], [`hoisted`], [`wrapper_needed`], [`multi_values`]), which hand a field's
//!   values to the item
//!   positions that can carry them and name the shapes the grammar cannot accommodate, plus
//!   [`unrenderable`], which the `unparse_str` convenience reports when the formatter declines a
//!   synthesised CST.
//! - The [`scalar`] coercions: one strict parse and one canonical rendering per `type:`
//!   builtin, gated so that both backends accept the same lexemes and render the same
//!   bytes.
//! - [`IndexMap`], and the two third-party scalar types `Uuid` and `Decimal`, re-exported so
//!   generated code names one version of each.
//!
//! It has no pyo3 dependency (pyo3-freedom is a structural absence, matching
//! `fltk-parser-core` and `fltk-unparser-core`). It depends on `fltk-cst-core` for
//! [`fltk_cst_core::Span`], which every AST node carries.
//!
//! # Features
//!
//! - `indexmap` (default-on): the container a `key:` keyed collection generates. A consumer
//!   whose sidecar uses no `key:` statement can take this crate with
//!   `default-features = false` and drop the dependency; a generated module that needs the
//!   feature says so in its header comment.
//! - `uuid` / `decimal` (off by default): the `type: uuid` and `type: decimal` builtins,
//!   which are the two whose value is a third-party type (`uuid::Uuid`,
//!   `rust_decimal::Decimal`). A generated module using either names its feature in the
//!   same header comment.

mod children;
mod convert;
pub mod dispatch;
mod error;
mod fold;
pub mod scalar;
mod spans;
mod synth;
mod terminal;

pub use children::{duplicate_key, node_text, one, optional, presence, text, unexpected_child};
pub use convert::{FromCst, ToCst};
pub use fold::{against_direction, check_fold_arity, fold_left, fold_right};
pub use error::{AstError, ParseToAstError};
pub use spans::merged_span;
pub use synth::{
    alternative_fits, check_consumed, check_group, filled, hoisted, multi_values, populated, unplaceable, unrenderable,
    wrapper_needed, Cursor, TerminalAlt, TerminalShape, TerminalSplit, UNBOUNDED,
};
pub use terminal::{source_span, text_span, validate_terminal, LazyTerminal, TerminalPattern};

/// The insertion-ordered map a `key:` keyed collection generates.
///
/// Re-exported rather than named directly by generated code so the generated module and this
/// runtime cannot end up on two versions of `indexmap`.
#[cfg(feature = "indexmap")]
pub use indexmap::IndexMap;

/// The value of a `type: uuid;` coercion, as [`scalar::parse_uuid`] returns it.
///
/// Re-exported for the same reason as [`IndexMap`]: a generated field naming `uuid::Uuid`
/// directly would be a different type from this crate's whenever the two resolve to different
/// versions of `uuid`, and the consumer's crate would then need the dependency of its own.
#[cfg(feature = "uuid")]
pub use uuid::Uuid;

/// The value of a `type: decimal;` coercion, as [`scalar::parse_decimal`] returns it.
///
/// Re-exported for the same reason as [`Uuid`].
#[cfg(feature = "decimal")]
pub use rust_decimal::Decimal;

// A generated field is typed by the re-export and filled by the coercion, so the two have to be
// one type. The coercion is the whole check, and it happens at compile time: a `#[test]` body
// asserting a value equals itself through an identity function reads like a runtime check while
// carrying none, so these are `const` items instead — they fail to compile if a re-export drifts.
#[cfg(feature = "uuid")]
const _UUID_RE_EXPORT_IS_WHAT_THE_COERCION_PRODUCES: fn(uuid::Uuid) -> Uuid = |value| value;

#[cfg(feature = "decimal")]
const _DECIMAL_RE_EXPORT_IS_WHAT_THE_COERCION_PRODUCES: fn(rust_decimal::Decimal) -> Decimal = |value| value;
