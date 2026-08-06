//! Crate root for the consumer-lane AST smoke target.
//!
//! `ast` reads its CST types as `super::cst`, so both modules must be siblings under
//! this root.
//!
//! The two accessors below name the coerced types themselves, so the lane fails to build on
//! either half of what it exists to prove: the runtime target dropping its `uuid`/`decimal`
//! features, and the sidecar's `type:` coercions ceasing to reach the generated module — which
//! would degrade both fields to `String` and otherwise still compile.

pub mod ast;
pub mod cst;

/// The payment's identifier, as `rule ident { type: uuid; }` coerces it.
pub fn payment_id(payment: &ast::Payment) -> &::fltk_ast_core::Uuid {
    &payment.id.value
}

/// The payment's amount, as `rule money { type: decimal; }` coerces it.
pub fn payment_amount(payment: &ast::Payment) -> &::fltk_ast_core::Decimal {
    &payment.amount.value
}
