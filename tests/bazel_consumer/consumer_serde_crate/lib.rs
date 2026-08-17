//! Crate root for the consumer-lane pure-Rust serde target.
//!
//! The configuration under test is bring-your-own-structs: `serde = True` without
//! `ast = True`, so nothing typed is generated and the hand-written types below are the only
//! model. They `#[derive(Deserialize)]` from @consumer_crates//:serde, and the generated
//! `de.rs` hands their fields through `fltk-serde-core`'s wrappers — which type-checks only
//! when fltk-serde-core was compiled against that same serde. With the flag unset this crate
//! fails to compile with mismatched-`serde`-instance errors, which is the assertion.

pub mod cst;
mod de;
pub mod parser;

use fltk_serde_core::{ParseToTargetError, Spanned};
use serde::Deserialize;

/// `payment := id:ident , amount:money` — the grammar's goal rule as a consumer types it.
///
/// Both fields are `Spanned`, so the newtype-name protocol between the derive and
/// fltk-serde-core's wrapper is exercised, not just plain scalars.
#[derive(Debug, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Payment {
    pub id: Spanned<String>,
    pub amount: Spanned<String>,
}

/// A target missing one of the grammar's labels: deserializing into it must fail rather
/// than drop the field silently.
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct OnlyId {
    #[allow(dead_code)]
    id: Spanned<String>,
}

/// Parse `src` as a `payment` and deserialize it into `Payment`.
pub fn parse_payment(src: &str) -> Result<Payment, ParseToTargetError> {
    de::from_str(src, Some("consumer.txt"))
}

#[cfg(test)]
mod tests {
    use super::{de, parse_payment, OnlyId};

    #[test]
    fn a_document_deserializes_into_the_consumers_own_struct() {
        let payment = parse_payment("0a1b-2c3d 12.50").expect("the fixture text must deserialize");
        assert_eq!(payment.id.value(), "0a1b-2c3d");
        assert_eq!(payment.amount.value(), "12.50");
    }

    /// Spans survive the crossing, which is what makes the wrapper protocol worth having.
    #[test]
    fn spans_reach_the_consumers_fields() {
        let payment = parse_payment("0a1b-2c3d 12.50").expect("the fixture text must deserialize");
        assert!(payment.amount.span().start() > payment.id.span().start());
    }

    #[test]
    fn a_target_missing_a_label_is_an_error() {
        de::from_str::<OnlyId>("0a1b-2c3d 12.50", None)
            .expect_err("`amount` is not a field of the target");
    }

    #[test]
    fn unparseable_input_is_an_error() {
        de::from_str::<super::Payment>("=", None).expect_err("`=` is not a payment");
    }
}
