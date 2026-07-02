#[cfg(test)]
mod tests {
    use crate::parser::Parser;

    #[test]
    fn test_parse_simple_grammar() {
        let src = "grammar := rule+ ;";
        let mut parser = Parser::new(src, None, false);
        let result = parser.apply__parse_grammar(0);
        assert!(result.is_some(), "Failed to parse: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, parser.terminals().len());
    }

    #[test]
    fn test_parse_fegen_fltkg() {
        let src = include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../fltk/fegen/fegen.fltkg"));
        let mut parser = Parser::new(src, None, false);
        let result = parser.apply__parse_grammar(0);
        assert!(
            result.is_some(),
            "Failed to parse fegen.fltkg: {}",
            parser.error_message()
        );
        let r = result.unwrap();
        assert_eq!(
            r.pos,
            parser.terminals().len(),
            "Did not parse to end. Error: {}",
            parser.error_message()
        );
    }

    #[test]
    fn test_error_position_on_failure() {
        let src = "grammar := !!!invalid;";
        let mut parser = Parser::new(src, None, false);
        let result = parser.apply__parse_grammar(0);
        assert!(result.is_none(), "Expected parse failure for invalid input");
        assert!(
            parser.error_position().is_some(),
            "error_position() should be Some after a failed parse attempt"
        );
    }

    #[test]
    fn test_rule_names_not_empty() {
        let src = "";
        let parser = Parser::new(src, None, false);
        assert!(!parser.rule_names().is_empty());
        assert_eq!(parser.rule_names()[0], "grammar");
    }

    // test-3: parse fegen.fltkg with capture_trivia=true (exercises all trivia-capture sites)
    #[test]
    fn test_parse_fegen_fltkg_with_capture_trivia() {
        let src = include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../fltk/fegen/fegen.fltkg"));
        let mut parser = Parser::new(src, None, true);
        let result = parser.apply__parse_grammar(0);
        assert!(
            result.is_some(),
            "Failed to parse fegen.fltkg with capture_trivia=true: {}",
            parser.error_message()
        );
        let r = result.unwrap();
        assert_eq!(
            r.pos,
            parser.terminals().len(),
            "Did not parse to end with capture_trivia=true. Error: {}",
            parser.error_message()
        );
        // With capture_trivia=true the grammar node must have more children than without,
        // because trivia/whitespace children are included.
        let mut parser_false = Parser::new(src, None, false);
        let r_false = parser_false.apply__parse_grammar(0).expect("should also parse capture_trivia=false");
        let children_true = r.result.read().children().len();
        let children_false = r_false.result.read().children().len();
        assert!(
            children_true > children_false,
            "capture_trivia=true ({children_true} children) should yield more children than false ({children_false})"
        );
    }

    // test-4: parse a snippet with a comment and assert trivia children are present
    #[test]
    fn test_parse_snippet_with_comment_trivia() {
        // A minimal fegen snippet containing a line comment.
        // With capture_trivia=true, the trivia rule captures the comment.
        let src = "// a comment\nrule := /x/ ;";
        let mut parser = Parser::new(src, None, true);
        let result = parser.apply__parse_grammar(0);
        assert!(
            result.is_some(),
            "Failed to parse snippet with comment: {}",
            parser.error_message()
        );
        let r = result.unwrap();
        assert_eq!(r.pos, parser.terminals().len(), "Should parse to end");
        // The grammar node must have trivia children (the comment + newline captured).
        let node = r.result.read();
        let has_trivia_child = node.children().iter().any(|(label, _)| label.is_none());
        assert!(
            has_trivia_child,
            "Grammar node must have unlabeled trivia children when capture_trivia=true and input has comments"
        );
    }

    // Site 1 of unparser-none-path-diagnostics: a confirmed-preservable comment whose
    // unparse__trivia returns None must panic (refusing to silently drop the comment) rather
    // than discard it. The fegen unparser preserves LineComment/BlockComment, so a Trivia
    // carrying a childless LineComment is preservable but fails to unparse.
    #[test]
    #[should_panic(expected = "refusing to silently drop comments")]
    fn test_preservable_trivia_unparse_none_panics() {
        use crate::cst::{Identifier, LineComment, Rule, RuleChild, Trivia};
        use crate::unparser::Unparser;
        use fltk_cst_core::{SourceText, Span};

        // A valid `name` identifier: its regex `name` child is source-bearing so span.text()
        // succeeds (otherwise site 2 would panic first, before the trivia is reached).
        let source = SourceText::from_str("x", None);
        let mut identifier = Identifier::new(Span::new_sourceless(0, 1));
        identifier.append_name(Span::new_with_source(0, 1, &source));

        // A Trivia carrying a childless LineComment: preservable per _has_preservable_trivia,
        // but unparse_line_comment returns None (its required prefix child is missing), so
        // unparse__trivia returns None.
        let line_comment = LineComment::new(Span::new_sourceless(0, 0));
        let mut trivia = Trivia::new(Span::new_sourceless(0, 0));
        trivia.append_line_comment(line_comment);

        // rule := name:identifier , ... — the `,` gap after `name` captures the Trivia child,
        // so unparse_rule reaches the trivia-preservation site right after unparsing `name`.
        let mut rule = Rule::new(Span::new_sourceless(0, 0));
        rule.append_name(identifier);
        rule.push_child(None, RuleChild::Trivia(trivia.into()));

        let unparser = Unparser::new();
        let _ = unparser.unparse_rule(&rule);
    }
}
