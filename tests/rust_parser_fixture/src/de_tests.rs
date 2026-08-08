//! Tests for the committed `de.rs` artifact: the shape descriptions the `fltk-serde-core`
//! Deserializer reads this grammar's tree through, the entry points that run it, and the
//! `Deserialize` impls it puts on the generated AST types.
//!
//! The targets here are hand-written `#[derive(Deserialize)]` types, which is the point of the
//! frontend: nothing about them is generated, and the grammar's labels and alternative names are
//! the whole contract between the two halves.

#[cfg(test)]
mod tests {
    use crate::parser::Parser;
    use crate::{ast, cst, de};
    use fltk_cst_core::{Shared, Span};
    use fltk_serde_core::{ParseToTargetError, Raw, Spanned};
    use serde::Deserialize;

    /// `nest_sum` over `nest`: a left-recursive sum whose operand is a nesting sum.
    const TEXT: &str = "((1))+2";

    /// `nest_sum` as a consumer would write it: externally tagged, one variant per grammar
    /// alternative, the alternative's labels as its fields.
    #[derive(Debug, Deserialize, PartialEq)]
    enum Sum {
        Alt1 { lhs: Box<Sum>, rhs: Nested },
        First(Nested),
    }

    /// `nest`, whose `leaf` alternative carries its `num` child directly — so a newtype variant
    /// over an integer target reads the terminal's own source text through the shared gate.
    #[derive(Debug, Deserialize, PartialEq)]
    enum Nested {
        Inner { inner: Box<Nested> },
        Leaf(u32),
    }

    /// `pair := key:name . "=" . val:num` — the flat product the error-position cases use.
    #[derive(Debug, Deserialize, PartialEq)]
    #[serde(deny_unknown_fields)]
    struct Pair {
        key: String,
        val: u8,
    }

    fn nested(depth: usize, leaf: u32) -> Nested {
        let mut value = Nested::Leaf(leaf);
        for _ in 0..depth {
            value = Nested::Inner {
                inner: Box::new(value),
            };
        }
        value
    }

    /// What `TEXT` means, written out.
    fn expected() -> Sum {
        Sum::Alt1 {
            lhs: Box::new(Sum::First(nested(2, 1))),
            rhs: nested(0, 2),
        }
    }

    fn ast_nested(depth: usize, leaf: &str) -> ast::Nest {
        let mut value = ast::Nest::Leaf(ast::Num {
            text: leaf.to_string(),
            span: Span::unknown(),
        });
        for _ in 0..depth {
            value = ast::Nest::Inner(Box::new(ast::NestInner {
                inner: Box::new(value),
                span: Span::unknown(),
            }));
        }
        value
    }

    fn parse_pair(src: &str) -> Shared<cst::Pair> {
        let mut parser = Parser::new(src, Some("fixture.txt"), false);
        let parsed = parser.apply__parse_pair(0).expect("the fixture text must parse");
        assert_eq!(parsed.pos, src.chars().count() as i64, "the whole input must be consumed");
        parsed.result
    }

    #[test]
    fn from_str_deserializes_the_document_into_hand_written_targets() {
        let value: Sum = de::from_str(TEXT, Some("fixture.txt")).expect("the document must deserialize");
        assert_eq!(value, expected());
    }

    #[test]
    fn a_parse_failure_arrives_as_the_parse_arm() {
        let error = de::from_str::<Sum>("((1))+", None).expect_err("a truncated document must not parse");
        assert!(
            matches!(error, ParseToTargetError::Parse(_)),
            "expected a parse failure; got {error}"
        );
    }

    #[test]
    fn spanned_carries_the_position_of_the_value_it_wraps() {
        let value: Spanned<Sum> = de::from_str(TEXT, Some("fixture.txt")).expect("the document must deserialize");
        assert_eq!(*value.value(), expected());
        assert_eq!(value.span().start(), 0);
        assert_eq!(value.span().end(), TEXT.chars().count() as i64);
    }

    #[test]
    fn raw_holds_a_subtree_that_a_later_entry_point_deserializes() {
        /// The right operand is held as syntax; everything else is read now.
        #[derive(Debug, Deserialize)]
        enum Held {
            Alt1 { lhs: Box<Held>, rhs: Raw<cst::Nest> },
            First(Nested),
        }

        let value: Held = de::from_str(TEXT, Some("fixture.txt")).expect("the document must deserialize");
        let Held::Alt1 { lhs, rhs } = value else {
            panic!("`{TEXT}` is the binary alternative");
        };
        let Held::First(left) = *lhs else {
            panic!("the left operand is a single nest");
        };
        assert_eq!(left, nested(2, 1), "the left operand is read as usual");

        let expanded: Nested = de::from_nest_cst(rhs.node()).expect("the held node must deserialize later");
        assert_eq!(expanded, nested(0, 2));
    }

    #[test]
    fn a_generated_ast_type_is_a_target_like_any_other() {
        let root: ast::NestSum = de::from_str(TEXT, Some("fixture.txt")).expect("the document must deserialize");
        assert_eq!(root, ast::parse_str(TEXT, None).expect("the document must convert"));

        /// The expression sub-language as a field of a hand-written target.
        #[derive(Debug, Deserialize)]
        enum Mixed {
            Alt1 { lhs: Box<Mixed>, rhs: ast::Nest },
            First(ast::Nest),
        }

        let value: Mixed = de::from_str(TEXT, Some("fixture.txt")).expect("the document must deserialize");
        let Mixed::Alt1 { lhs, rhs } = value else {
            panic!("`{TEXT}` is the binary alternative");
        };
        let Mixed::First(left) = *lhs else {
            panic!("the left operand is a single nest");
        };
        assert_eq!(left, ast_nested(2, "1"));
        assert_eq!(rhs, ast_nested(0, "2"));
    }

    #[test]
    fn a_product_rule_serves_one_entry_per_field() {
        let value: Pair = de::from_pair_cst(&parse_pair("a=1")).expect("the node must deserialize");
        assert_eq!(
            value,
            Pair {
                key: "a".to_string(),
                val: 1,
            }
        );
    }

    #[test]
    fn an_unknown_field_is_serdes_message_at_the_offending_child() {
        #[derive(Debug, Deserialize)]
        #[serde(deny_unknown_fields)]
        struct OnlyKey {
            #[allow(dead_code)]
            key: String,
        }

        let error = de::from_pair_cst::<OnlyKey>(&parse_pair("a=1")).expect_err("`val` is not a field of the target");
        assert_eq!(
            error.to_string(),
            "unknown field `val`, expected `key` at line 1, column 3"
        );
    }

    #[test]
    fn a_missing_field_is_positioned_at_the_node() {
        #[derive(Debug, Deserialize)]
        struct Extra {
            #[allow(dead_code)]
            key: String,
            #[allow(dead_code)]
            val: u8,
            #[allow(dead_code)]
            missing: u8,
        }

        let error = de::from_pair_cst::<Extra>(&parse_pair("a=1")).expect_err("the grammar has no `missing` label");
        assert_eq!(error.to_string(), "missing field `missing` at line 1, column 1");
    }

    #[test]
    fn a_scalar_target_runs_the_shared_gate_over_the_source_text() {
        let error = de::from_pair_cst::<Pair>(&parse_pair("a=300")).expect_err("300 does not fit a u8");
        assert_eq!(
            error.to_string(),
            "rule \"num\": \"300\" is not in range for u8 (0 to 255) at line 1, column 3"
        );
    }
}
