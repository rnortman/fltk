//! Crate root for the CST-only consumer target.
//!
//! Only `mod cst` is declared: `parser.rs` is absent when `parser = False`, so naming a parser
//! module here would fail to build — this crate root is the compile-time check on that attribute.

pub mod cst;

/// Whether `num` has no children.
pub fn empty_num_children(num: &cst::Num) -> bool {
    num.children().is_empty()
}
