//! Tests for the committed `ast.rs` artifact: the one-call entry points over a generated
//! parser and a `.fltkfmt`-baked unparser, and the failure paths on either side of them.

#[cfg(test)]
mod tests {
    use crate::ast::{
        self, Colour, ColourValue, DecimalVal, Nest, NestInner, NestSum, NestSumAlt1, Num, SumChain, SumChainBinary,
        UuidVal, Val,
    };
    use crate::cst;
    use crate::unparser::Unparser;
    use fltk_ast_core::{Decimal, ParseToAstError, Uuid};
    use fltk_cst_core::Span;
    use fltk_unparser_core::{Renderer, RendererConfig, UnparseResult, resolve_spacing_specs};

    const TEXT: &str = "((1))+2";

    fn num(text: &str) -> Num {
        Num {
            text: text.to_string(),
            span: Span::unknown(),
        }
    }

    fn nested(depth: usize, leaf: &str) -> Nest {
        let mut value = Nest::Leaf(num(leaf));
        for _ in 0..depth {
            value = Nest::Inner(Box::new(NestInner {
                inner: Box::new(value),
                span: Span::unknown(),
            }));
        }
        value
    }

    /// The hand-built shape for `TEXT` that the converter must agree with.
    fn synthesized() -> NestSum {
        NestSum::Alt1(Box::new(NestSumAlt1 {
            lhs: Box::new(NestSum::First(nested(2, "1"))),
            rhs: nested(0, "2"),
            span: Span::unknown(),
        }))
    }

    #[test]
    fn a_parse_converts_to_the_value_built_by_hand() {
        let parsed = ast::parse_str(TEXT, Some("fixture.txt")).expect("the document must parse and convert");
        assert_eq!(parsed, synthesized());
    }

    #[test]
    fn the_equality_the_previous_case_rests_on_ignores_spans() {
        // Without this the case above would pass on a value that carried no positions at all.
        let parsed = ast::parse_str(TEXT, None).expect("the document must parse and convert");
        assert_ne!(*parsed.span(), Span::unknown());
        assert_eq!(*synthesized().span(), Span::unknown());
        assert_ne!(
            parsed,
            ast::parse_str("((1))+3", None).expect("the document must parse and convert")
        );
    }

    #[test]
    fn text_the_goal_rule_leaves_unconsumed_is_not_a_parse() {
        // `nest_sum` matches "1+2" and stops; the trailing paren is what `parse_str` refuses.
        // Without the paren the same text converts, so the refusal is the consumption check
        // rather than a failure to match.
        assert!(ast::parse_str("1+2", None).is_ok());
        let error = ast::parse_str("1+2)", None).expect_err("a partial parse is not a parse");
        let ParseToAstError::Parse(message) = &error else {
            panic!("unconsumed input is a parse failure, not a conversion failure");
        };
        assert!(message.starts_with("Syntax error"), "got {message:?}");
    }

    #[test]
    fn text_that_is_not_in_the_language_is_not_a_parse() {
        let error = ast::parse_str("", None).expect_err("the goal rule needs at least a number");
        assert!(matches!(error, ParseToAstError::Parse(_)), "got {error:?}");
    }

    #[test]
    fn a_document_nested_past_the_parsers_depth_limit_is_refused() {
        // A depth-rejected parse can come back as `Some` holding a truncated tree, so the
        // flag is what `parse_str` has to read.
        let depth = 2 * fltk_parser_core::DEFAULT_MAX_DEPTH as usize;
        let text = format!("{}1{}", "(".repeat(depth), ")".repeat(depth));
        // The limit is a rule-application count, and the parser is recursive descent: reaching
        // the count takes ~`DEFAULT_MAX_DEPTH` nested frames, which is more than a default
        // 2 MiB test thread has in a debug build.
        let error = std::thread::Builder::new()
            .stack_size(64 * 1024 * 1024)
            .spawn(move || ast::parse_str(&text, None).expect_err("nesting past the limit is not a parse"))
            .expect("the deep-parse thread must start")
            .join()
            .expect("the parse must return rather than abort");
        let ParseToAstError::Parse(message) = error else {
            panic!("a depth rejection happens before any conversion");
        };
        assert!(message.contains("depth limit exceeded"), "got {message:?}");
    }

    #[test]
    fn a_value_built_by_hand_renders_through_the_generated_formatter() {
        let rendered = ast::unparse_str(&synthesized(), 80, 2).expect("a well-formed value must render");
        assert_eq!(rendered, TEXT);
    }

    #[test]
    fn a_render_of_a_parsed_value_parses_back_to_it() {
        let parsed = ast::parse_str(TEXT, None).expect("the document must parse and convert");
        let rendered = ast::unparse_str(&parsed, 80, 2).expect("a value read off a parse must render");
        assert_eq!(ast::parse_str(&rendered, None).expect("a rendered value must parse"), parsed);
    }

    #[test]
    fn a_parsed_value_synthesises_the_cst_it_was_read_from() {
        let parsed = ast::parse_str(TEXT, None).expect("the document must parse and convert");
        let node = parsed.to_cst().expect("a parsed value must synthesise");
        assert_eq!(NestSum::from_cst(&node).expect("a synthesised CST must convert"), parsed);
    }

    /// Parse `$text` with the native parser method `$parse` and return the CST node,
    /// checking what `parse_str` checks: the depth flag, a result at all, and full
    /// consumption. `$what` names the target in the panic messages.
    ///
    /// The depth check is not redundant with the consumption assert — a depth-rejected
    /// parse can come back as `Some` holding a wrong tree that an outer alternative
    /// consumed to the end.
    macro_rules! parse_cst {
        ($text:expr, $parse:ident, $what:expr) => {{
            let text: &str = $text;
            let mut parser = crate::parser::Parser::new(text, None, false);
            let parsed = parser
                .$parse(0)
                .unwrap_or_else(|| panic!("the text must parse as `{}`: {text:?}", $what));
            assert!(
                !parser.depth_exceeded(),
                "a depth-limited parse of `{}` is not a parse: {text:?}",
                $what
            );
            assert_eq!(parsed.pos, text.chars().count() as i64, "the whole input must be consumed");
            parsed.result
        }};
    }

    /// Parse `$text` as above and convert the resulting CST node to `$ty`. This is the only
    /// way to reach a rule the goal does not.
    macro_rules! parse_ast {
        ($text:expr, $parse:ident, $ty:ty) => {{
            let node = parse_cst!($text, $parse, stringify!($ty));
            <$ty>::from_cst(&node)
                .unwrap_or_else(|error| panic!("a parse of `{}` must convert: {error:?}", stringify!($ty)))
        }};
    }

    fn parse_val(text: &str) -> Val {
        parse_ast!(text, apply__parse_val, Val)
    }

    #[test]
    fn a_union_label_round_trips_whichever_kind_it_carries() {
        // `val`'s three alternatives all label their one position `item`, so the populated
        // label names are the same for every value it can hold; what picks the alternative is
        // the kind the value carries.
        for text in ["123", "abc", "!@#"] {
            let value = parse_val(text);
            let node = value.to_cst().unwrap_or_else(|error| panic!("{text:?} must synthesise: {error:?}"));
            assert_eq!(Val::from_cst(&node).expect("a synthesised CST must convert"), value);
        }
    }

    #[test]
    fn a_union_label_renders_the_child_kind_its_value_carries() {
        // What selecting by label names alone could not do: each alternative appends a child of
        // its own kind, so picking the wrong one puts the wrong kind of child under `item`.
        let kinds = ["123", "abc", "!@#"].map(|text| {
            let node = parse_val(text).to_cst().expect("every kind must synthesise");
            let guard = node.read();
            match &guard.children()[0].1 {
                cst::ValChild::Num(_) => "num",
                cst::ValChild::Name(_) => "name",
                cst::ValChild::Span(_) => "span",
            }
        });
        assert_eq!(kinds, ["num", "name", "span"]);
    }

    #[test]
    fn text_the_rules_terminal_cannot_match_is_refused() {
        let value = NestSum::First(Nest::Leaf(num("not a number")));
        let error = ast::unparse_str(&value, 80, 2).expect_err("the num terminal accepts digits only");
        // The wording belongs to `fltk-ast-core`, which pins it; what this case owns is that the
        // refusal reaches `unparse_str` naming the rule and the text it could not have matched.
        assert!(error.message.contains("rule \"num\""), "got {:?}", error.message);
        assert!(error.message.contains("\"not a number\""), "got {:?}", error.message);
    }

    // ------------------------------------------------------------------
    // Rules the goal does not reach: the two wide scalar builtins, the
    // multi-spelling label, and the fold.
    // ------------------------------------------------------------------

    /// Render what a rule's own unparser method produced, as `unparse_str` renders the goal's.
    fn render(unparsed: Option<UnparseResult>) -> String {
        let unparsed = unparsed.expect("a synthesised node must render");
        let resolved = resolve_spacing_specs(unparsed.doc());
        let config = RendererConfig {
            indent_width: 2,
            max_width: 80,
        };
        Renderer::new(config).render(&resolved)
    }

    fn parse_uuid_val(text: &str) -> UuidVal {
        parse_ast!(text, apply__parse_uuid_val, UuidVal)
    }

    fn parse_decimal_val(text: &str) -> DecimalVal {
        parse_ast!(text, apply__parse_decimal_val, DecimalVal)
    }

    fn parse_colour(text: &str) -> Colour {
        parse_ast!(text, apply__parse_colour, Colour)
    }

    fn parse_sum_chain(text: &str) -> SumChain {
        parse_ast!(text, apply__parse_sum_chain, SumChain)
    }

    #[test]
    fn a_uuid_coerced_rule_carries_the_runtimes_uuid_and_renders_it_back() {
        const TEXT: &str = "550e8400-e29b-41d4-a716-446655440000";
        let value = parse_uuid_val(TEXT);
        assert_eq!(value.value, Uuid::parse_str(TEXT).expect("the text is a uuid"));
        assert_ne!(value.value, Uuid::nil(), "the field is not the sentinel");
        let node = value.to_cst().expect("a uuid value must synthesise");
        let guard = node.read();
        assert_eq!(render(Unparser::new().unparse_uuid_val(&guard)), TEXT);
    }

    #[test]
    fn an_uppercase_uuid_renders_back_in_the_runtimes_canonical_spelling() {
        // The field holds a parsed `Uuid`, not the text, so rendering is whatever the runtime
        // renders — lowercase — rather than what the document happened to spell.
        let value = parse_uuid_val("550E8400-E29B-41D4-A716-446655440000");
        let node = value.to_cst().expect("a uuid value must synthesise");
        let guard = node.read();
        assert_eq!(
            render(Unparser::new().unparse_uuid_val(&guard)),
            "550e8400-e29b-41d4-a716-446655440000"
        );
    }

    #[test]
    fn a_decimal_coerced_rule_carries_the_runtimes_decimal_and_renders_it_back() {
        const TEXT: &str = "-12.50";
        let value = parse_decimal_val(TEXT);
        assert_eq!(value.value, Decimal::new(-1250, 2));
        assert_ne!(value.value, Decimal::ZERO, "the field is not the sentinel");
        let node = value.to_cst().expect("a decimal value must synthesise");
        let guard = node.read();
        // The scale survives the round trip: -12.50 is not rendered as -12.5.
        assert_eq!(render(Unparser::new().unparse_decimal_val(&guard)), TEXT);
    }

    #[test]
    fn both_spellings_of_one_label_are_one_value_and_render_as_the_first() {
        let written = parse_colour("gray");
        let alternate = parse_colour("grey");
        assert_eq!(written.value, ColourValue::Shade);
        assert_eq!(alternate.value, ColourValue::Shade);
        assert_eq!(written, alternate, "a shared label makes the two spellings one value");
        // Both values map to the same variant and `to_cst` does not preserve spelling,
        // so one render covers both.
        let node = written.to_cst().expect("a colour value must synthesise");
        let guard = node.read();
        assert_eq!(render(Unparser::new().unparse_colour(&guard)), "gray");
    }

    #[test]
    fn the_spelling_a_document_used_renders_back_as_the_first_one() {
        // Unlike the case above, these nodes come straight off the parser and carry the
        // original span text. Both spellings must still render as the label's first one.
        for text in ["gray", "grey"] {
            let node = parse_cst!(text, apply__parse_colour, "colour");
            let guard = node.read();
            assert_eq!(render(Unparser::new().unparse_colour(&guard)), "gray");
        }
    }

    #[test]
    fn a_label_of_its_own_is_a_variant_of_its_own() {
        // Without this the case above would hold on a rule with one variant.
        let value = parse_colour("black");
        assert_eq!(value.value, ColourValue::Dark);
        assert_ne!(value, parse_colour("gray"));
        let node = value.to_cst().expect("a colour value must synthesise");
        let guard = node.read();
        assert_eq!(render(Unparser::new().unparse_colour(&guard)), "black");
    }

    #[test]
    fn a_fold_rule_parses_into_a_left_nested_chain() {
        let parsed = parse_sum_chain("1+2-3");
        let expected = SumChain::Binary(SumChainBinary {
            op: "-".to_string(),
            lhs: Box::new(SumChain::Binary(SumChainBinary {
                op: "+".to_string(),
                lhs: Box::new(SumChain::Operand(num("1"))),
                rhs: Box::new(SumChain::Operand(num("2"))),
                span: Span::unknown(),
            })),
            rhs: Box::new(SumChain::Operand(num("3"))),
            span: Span::unknown(),
        });
        assert_eq!(parsed, expected);
        // Operator and operand separators are ws-allowed, so the rendering need not be the
        // document's; what has to hold is that it parses back to the same chain.
        let node = parsed.to_cst().expect("a chain must synthesise");
        let rendered = {
            let guard = node.read();
            render(Unparser::new().unparse_sum_chain(&guard))
        };
        assert_eq!(parse_sum_chain(&rendered), parsed);
    }

    const OPERANDS: usize = 100_000;

    /// A left-nested chain of `OPERANDS` operands whose innermost operator is `first_op` and
    /// whose every other operator is `"+"`. The innermost link is the one the comparison
    /// reaches last, so `first_op` is what an equality walk has to descend the whole chain
    /// to see.
    fn long_chain(first_op: &str) -> SumChain {
        let span = Span::unknown();
        let operands: Vec<(Num, Span)> = (0..OPERANDS).map(|_| (num("1"), span.clone())).collect();
        let operators: Vec<String> = (0..OPERANDS - 1)
            .map(|index| if index == 0 { first_op } else { "+" }.to_string())
            .collect();
        fltk_ast_core::fold_left(
            "sum_chain",
            &span,
            operands,
            operators,
            SumChain::Operand,
            |op, lhs, rhs, span| {
                SumChain::Binary(SumChainBinary {
                    op,
                    lhs: Box::new(lhs),
                    rhs: Box::new(rhs),
                    span,
                })
            },
        )
        .expect("a long run of operands folds")
    }

    #[test]
    fn a_chain_of_one_hundred_thousand_operands_compares_and_tears_down_without_recursing() {
        // Both halves of the pair fail the same way: a recursive `PartialEq` and a derived
        // teardown each overflow the stack at this length, which is a process abort rather
        // than a catchable failure. So the value of this case is that it returns at all.
        let chain = long_chain("+");
        assert!(matches!(chain, SumChain::Binary(_)));
        assert_eq!(chain, long_chain("+"));
        // The `-` is on the innermost link, so this inequality is only reachable by walking
        // every link — it cannot be answered at the root.
        assert_ne!(chain, long_chain("-"));
        drop(chain);
    }
}
