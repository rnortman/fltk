#[cfg(test)]
mod tests {
    use crate::cst;
    use crate::parser::Parser;
    use fltk_cst_core::Shared;

    // ── deep-tree tests (iterative Debug + iterative Drop) ────────────────

    const DEEP_TREE_DEPTH: usize = 100_000;

    /// Build a `DEEP_TREE_DEPTH`-level Expr chain iteratively (leaf-up), with a
    /// caller-specified span for the leaf Num node.
    fn build_deep_expr_chain_with_leaf_span(leaf_span: fltk_cst_core::Span) -> Shared<cst::Expr> {
        // Build an atom leaf (Atom wrapping a Num wrapping a Span) at the bottom.
        // Num: span-only.
        let leaf_num = Shared::new(cst::Num::new(leaf_span));
        let mut leaf_atom = cst::Atom::new(fltk_cst_core::Span::unknown());
        leaf_atom.append_num(leaf_num);
        let leaf_atom_shared = Shared::new(leaf_atom);

        // First Expr is atom:leaf_atom.
        let mut bottom = cst::Expr::new(fltk_cst_core::Span::unknown());
        bottom.append_atom(leaf_atom_shared);
        let mut prev = Shared::new(bottom);

        // Each subsequent level wraps the previous as lhs:Expr.
        for _ in 1..DEEP_TREE_DEPTH {
            let mut node = cst::Expr::new(fltk_cst_core::Span::unknown());
            node.append_lhs(prev.clone());
            prev = Shared::new(node);
        }
        prev
    }

    /// Build a `DEEP_TREE_DEPTH`-level Expr chain with `Span::unknown()` at the leaf.
    fn build_deep_expr_chain() -> Shared<cst::Expr> {
        build_deep_expr_chain_with_leaf_span(fltk_cst_core::Span::unknown())
    }

    /// Test 1: deep-tree Debug completes without stack overflow; output is bounded.
    #[test]
    fn test_deep_tree_debug_non_recursive() {
        let root = build_deep_expr_chain();
        // format! must complete (not abort or overflow).
        let s = format!("{:?}", root.read());
        // Output must contain the structural markers: "span" and "<N child(ren)>".
        assert!(s.contains("span"), "Debug output must contain 'span'; got: {s}");
        assert!(s.contains("child(ren)"), "Debug output must contain 'child(ren)'; got: {s}");
        // Output must be bounded regardless of tree depth: << 1 KiB.
        assert!(
            s.len() < 256,
            "Debug output must be small (< 256 bytes); got {} bytes: {s}",
            s.len()
        );
        // Natural drop here also exercises iterative Drop (test 1 covers both).
    }

    /// Test 2: deep-tree drop completes without stack overflow.
    /// Isolates the iterative Drop implementation from the iterative Debug implementation.
    #[test]
    fn test_deep_tree_drop_iterative() {
        let root = build_deep_expr_chain();
        // drop must complete (not abort or overflow).
        drop(root);
    }

    /// Test 3: shared-subtree survival.  Parent drops iteratively; the shared child is
    /// NOT stolen (strong_count > 1) and remains accessible through the retained handle.
    #[test]
    fn test_shared_subtree_survives_parent_drop() {
        // grandchild
        let grandchild = Shared::new(cst::Expr::new(fltk_cst_core::Span::unknown()));
        // child wraps grandchild via lhs
        let mut child_node = cst::Expr::new(fltk_cst_core::Span::unknown());
        child_node.append_lhs(grandchild);
        let child = Shared::new(child_node);
        // parent wraps child via lhs
        let mut parent_node = cst::Expr::new(fltk_cst_core::Span::unknown());
        parent_node.append_lhs(child.clone()); // clone: parent + retained handle both point to child
        let parent = Shared::new(parent_node);

        // Verify child strong_count is 2: parent's child list + our retained handle.
        assert_eq!(child.strong_count(), 2, "child strong_count must be 2 before parent drop");

        // Drop parent: iterative Drop should NOT steal child (strong_count == 2 → skip steal).
        drop(parent);

        // child must still be live: our retained handle holds it.
        // Its grandchild (the lhs) must still be present: child was not stolen.
        assert_eq!(
            child.read().children().len(),
            1,
            "child must still have its grandchild after parent drop (not stolen)"
        );

        // Drop retained handle: frees child + grandchild iteratively.
        drop(child);
    }

    /// Test 4: Shared::strong_count reachability from a downstream crate.
    /// The method contract (new→1, clone→2, drop→1) is the canonical unit test in
    /// fltk-cst-core/src/shared.rs; this test only confirms the method is publicly
    /// accessible when called on a generated CST type from a dependent crate.
    #[test]
    fn test_shared_strong_count() {
        let s: Shared<cst::Expr> = Shared::new(cst::Expr::new(fltk_cst_core::Span::unknown()));
        assert_eq!(s.strong_count(), 1, "count must be 1 after new");
        let s2 = s.clone();
        assert_eq!(s.strong_count(), 2, "count must be 2 after clone");
        drop(s2);
        assert_eq!(s.strong_count(), 1, "count must be back to 1 after drop of clone");
    }

    /// Test 4b: multi-child worklist drain.
    /// Tests 1 and 2 each build a chain where every Expr has exactly 1 node-typed child
    /// (lhs:Expr), so the worklist holds at most 1 item at a time.  This test builds a tree
    /// where each parent has two node-typed children (lhs:Expr + rhs:Atom) to exercise the
    /// multi-child drain path that enqueues both children.
    #[test]
    fn test_multi_child_drop_worklist() {
        // Build a 100-level chain; each level has lhs:Expr (node-typed) and rhs:Atom (node-typed).
        // At each level the worklist must hold at least 2 items simultaneously.
        let leaf_num = Shared::new(cst::Num::new(fltk_cst_core::Span::unknown()));
        let mut leaf_atom = cst::Atom::new(fltk_cst_core::Span::unknown());
        leaf_atom.append_num(leaf_num);
        let leaf_atom_shared = Shared::new(leaf_atom);

        // Bottom Expr: atom:leaf_atom (atom-only variant).
        let mut bottom = cst::Expr::new(fltk_cst_core::Span::unknown());
        bottom.append_atom(leaf_atom_shared.clone());
        let mut prev = Shared::new(bottom);

        // Build 100 levels; each level adds lhs:Expr + rhs:Atom children.
        for _ in 0..100 {
            let mut node = cst::Expr::new(fltk_cst_core::Span::unknown());
            node.append_lhs(prev);
            // rhs: a fresh atom (owned, sole ref → will be stolen and enqueued)
            let mut rhs_atom = cst::Atom::new(fltk_cst_core::Span::unknown());
            rhs_atom.append_num(Shared::new(cst::Num::new(fltk_cst_core::Span::unknown())));
            node.append_rhs(Shared::new(rhs_atom));
            prev = Shared::new(node);
        }
        // drop must complete without stack overflow; both child paths are exercised.
        drop(prev);
        drop(leaf_atom_shared);
    }

    /// Test 5: parser-produced deep-tree.  Left-recursive seed-grow creates trees whose
    /// depth scales with input length (evaluation-drop-depth-reachability.md §2), independently
    /// of the parse-depth-limit.  This test pins reachability via actual parsing in CI.
    #[test]
    fn test_parser_produced_deep_tree_debug_and_drop() {
        // Input: "1" + "+1" * DEEP_TREE_DEPTH ≈ 200 KiB; left-recursive expr builds a DEEP_TREE_DEPTH-level chain.
        let n = DEEP_TREE_DEPTH;
        let mut src = String::with_capacity(1 + 2 * n);
        src.push('1');
        for _ in 0..n {
            src.push_str("+1");
        }

        let mut parser = Parser::new(&src, false);
        let result = parser.apply__parse_expr(0);
        assert!(
            result.is_some(),
            "parser must succeed on deep input: {}",
            parser.error_message()
        );
        let r = result.unwrap();
        assert_eq!(r.pos, (1 + 2 * n) as i64, "parser must consume all input");

        // format! must complete (not abort).
        let dbg = format!("{:?}", r.result.read());
        assert!(
            dbg.contains("child(ren)"),
            "Debug output must contain 'child(ren)'; got: {dbg}"
        );
        assert!(dbg.len() < 256, "Debug output must be bounded; got {} bytes", dbg.len());

        // Explicit drop ordering: result (r) first, then parser (memo table).
        // `r` was declared after `parser`, so Rust's LIFO destructor order would drop it
        // first anyway; the explicit calls make the intended sequence visible and testable.
        // After drop(r): root's iterative Drop runs.
        // After drop(parser): the memo cache releases its ~100_000 memoized Shared<Expr>
        // handles; each whose count hits 1 runs an iterative Drop.
        drop(r);
        drop(parser);
    }

    // ── deep-equality tests (iterative PartialEq) ────────────────────────

    /// EQ-1: two structurally equal 100k chains compare equal without stack overflow.
    #[test]
    fn test_deep_tree_eq_iterative_equal() {
        let a = build_deep_expr_chain();
        let b = build_deep_expr_chain();
        assert!(a.read().eq(&*b.read()), "two equal deep chains must compare equal");
    }

    /// EQ-2: two 100k chains differing only at the deepest leaf span compare unequal
    /// without stack overflow.  Forces full-depth traversal on the false path.
    #[test]
    fn test_deep_tree_eq_iterative_unequal() {
        let a = build_deep_expr_chain_with_leaf_span(fltk_cst_core::Span::unknown());
        // Use a non-unknown span so the leaf differs.
        let b = build_deep_expr_chain_with_leaf_span(fltk_cst_core::Span::new_sourceless(0, 1));
        assert!(!a.read().eq(&*b.read()), "chains differing at leaf must compare unequal");
    }

    /// EQ-3: two distinct root Expr nodes that both hold the *same* Shared 100k chain as
    /// their lhs:Expr child compare equal; exercises the per-pair ptr_eq short-circuit
    /// (the shared chain must not be traversed at all).
    #[test]
    fn test_deep_shared_subtree_eq_ptr_eq_short_circuit() {
        let shared_chain = build_deep_expr_chain();

        let mut root_a = cst::Expr::new(fltk_cst_core::Span::unknown());
        root_a.append_lhs(shared_chain.clone());

        let mut root_b = cst::Expr::new(fltk_cst_core::Span::unknown());
        root_b.append_lhs(shared_chain.clone());

        assert!(root_a.eq(&root_b), "two roots sharing the same Shared child must compare equal");
    }

    /// EQ-4: mirror of test_multi_child_drop_worklist — two equal ~100-level trees where
    /// each level has two node-typed children (lhs:Expr + rhs:Atom).  Then an unequal
    /// variant (one rhs differs at a mid-level rhs branch, not on the lhs spine) → unequal.
    /// Exercises worklists holding multiple pending pairs and verifies that a `false` result
    /// from a non-final worklist item (a dequeued rhs subtree) is detected correctly.
    #[test]
    fn test_multi_child_eq_worklist() {
        /// Build a 100-level multi-child tree.
        /// `rhs_diff_level`: if Some(k), the rhs Atom at level k (0-indexed from the bottom)
        /// gets a non-default Span on its Num child; all other nodes use Span::unknown().
        fn build_multi_child_tree(rhs_diff_level: Option<usize>) -> Shared<cst::Expr> {
            let leaf_num = Shared::new(cst::Num::new(fltk_cst_core::Span::unknown()));
            let mut leaf_atom = cst::Atom::new(fltk_cst_core::Span::unknown());
            leaf_atom.append_num(leaf_num);
            let leaf_atom_shared = Shared::new(leaf_atom);

            let mut bottom = cst::Expr::new(fltk_cst_core::Span::unknown());
            bottom.append_atom(leaf_atom_shared.clone());
            let mut prev = Shared::new(bottom);

            for level in 0..100 {
                let mut node = cst::Expr::new(fltk_cst_core::Span::unknown());
                node.append_lhs(prev);
                let rhs_num_span = if rhs_diff_level == Some(level) {
                    fltk_cst_core::Span::new_sourceless(0, 1)
                } else {
                    fltk_cst_core::Span::unknown()
                };
                let mut rhs_atom = cst::Atom::new(fltk_cst_core::Span::unknown());
                rhs_atom.append_num(Shared::new(cst::Num::new(rhs_num_span)));
                node.append_rhs(Shared::new(rhs_atom));
                prev = Shared::new(node);
            }
            prev
        }

        let a = build_multi_child_tree(None);
        let b = build_multi_child_tree(None);
        assert!(a.read().eq(&*b.read()), "two equal multi-child trees must compare equal");

        // Mismatch is in the rhs branch at level 50 (mid-level), not on the lhs spine.
        // This exercises a `false` result from a non-final worklist item (the dequeued rhs
        // subtree), not just from the deepest pending path.
        let c = build_multi_child_tree(Some(50));
        assert!(!a.read().eq(&*c.read()), "trees differing at a mid-level rhs branch must compare unequal");
    }

    /// EQ-5: parse "1" + "+1"*100_000 twice with two independent Parser instances;
    /// the two resulting trees compare equal without stack overflow.
    #[test]
    fn test_parser_produced_deep_tree_eq() {
        let n = DEEP_TREE_DEPTH;
        let mut src = String::with_capacity(1 + 2 * n);
        src.push('1');
        for _ in 0..n {
            src.push_str("+1");
        }

        let mut p1 = Parser::new(&src, false);
        let r1 = p1.apply__parse_expr(0).expect("first parse must succeed");

        let mut p2 = Parser::new(&src, false);
        let r2 = p2.apply__parse_expr(0).expect("second parse must succeed");

        assert!(
            r1.result.read().eq(&*r2.result.read()),
            "two independently-parsed equal trees must compare equal"
        );
    }

    /// EQ-6: same-label / different-variant pair reaches the wildcard arm of the child
    /// equality logic and returns false.  Uses the union-label "item" in Val:
    /// one Val with item:num vs. one Val with item:name under the same label.
    #[test]
    fn test_eq_variant_mismatch_unequal() {
        let mut val_num = cst::Val::new(fltk_cst_core::Span::unknown());
        let num = Shared::new(cst::Num::new(fltk_cst_core::Span::unknown()));
        val_num.append_item(cst::ValChild::Num(num));

        let mut val_name = cst::Val::new(fltk_cst_core::Span::unknown());
        let name = Shared::new(cst::Name::new(fltk_cst_core::Span::unknown()));
        val_name.append_item(cst::ValChild::Name(name));

        assert!(!val_num.eq(&val_name), "same label, different variant must compare unequal");
    }

    /// EQ-7: child label mismatch returns false.
    /// Two Expr nodes with one child each: same child value but under different labels
    /// (atom vs. rhs — both accept ExprChild::Atom).
    /// Exercises the `la != lb` early-exit in the iterative PartialEq driver.
    #[test]
    fn test_eq_label_mismatch_unequal() {
        let atom = Shared::new(cst::Atom::new(fltk_cst_core::Span::unknown()));

        let mut expr_atom_label = cst::Expr::new(fltk_cst_core::Span::unknown());
        expr_atom_label.push_child(Some(cst::ExprLabel::Atom), cst::ExprChild::Atom(atom.clone()));

        let mut expr_rhs_label = cst::Expr::new(fltk_cst_core::Span::unknown());
        expr_rhs_label.push_child(Some(cst::ExprLabel::Rhs), cst::ExprChild::Atom(atom.clone()));

        assert!(!expr_atom_label.eq(&expr_rhs_label), "same child variant under different labels must compare unequal");
    }

    /// EQ-8: child count mismatch returns false.
    /// Two Expr nodes with the same span but different numbers of children.
    /// Exercises the `children.len() != other.children.len()` early-exit in the driver.
    #[test]
    fn test_eq_child_count_mismatch_unequal() {
        let atom = Shared::new(cst::Atom::new(fltk_cst_core::Span::unknown()));

        let expr_zero = cst::Expr::new(fltk_cst_core::Span::unknown());

        let mut expr_one = cst::Expr::new(fltk_cst_core::Span::unknown());
        expr_one.append_atom(atom);

        assert!(!expr_zero.eq(&expr_one), "nodes with different child counts must compare unequal");
    }

    // ── num rule ──────────────────────────────────────────────────────────

    #[test]
    fn test_parse_num() {
        let src = "123";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_num(0);
        assert!(result.is_some(), "Failed to parse num: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 3);
    }

    #[test]
    fn test_parse_num_fail() {
        let src = "abc";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_num(0);
        assert!(result.is_none());
    }

    // ── name rule ─────────────────────────────────────────────────────────

    #[test]
    fn test_parse_name() {
        let src = "hello";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_name(0);
        assert!(result.is_some(), "Failed to parse name: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 5);
    }

    // ── atom rule ─────────────────────────────────────────────────────────

    #[test]
    fn test_parse_atom_num() {
        let src = "42";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_atom(0);
        assert!(result.is_some(), "Failed to parse atom as num: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 2);
    }

    #[test]
    fn test_parse_atom_name() {
        let src = "foo";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_atom(0);
        assert!(result.is_some(), "Failed to parse atom as name: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 3);
    }

    // ── paren_expr rule ───────────────────────────────────────────────────

    #[test]
    fn test_parse_paren_expr() {
        let src = "(42)";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_paren_expr(0);
        assert!(result.is_some(), "Failed to parse paren_expr: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 4);
    }

    #[test]
    fn test_parse_paren_expr_with_ws() {
        // WS_ALLOWED separator inside paren_expr
        let src = "( 42 )";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_paren_expr(0);
        assert!(result.is_some(), "Failed to parse paren_expr with spaces: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 6);
    }

    // ── stmt rule (WS_REQUIRED) ───────────────────────────────────────────

    #[test]
    fn test_parse_stmt_with_required_ws() {
        let src = "foo = bar";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_stmt(0);
        assert!(result.is_some(), "Failed to parse stmt: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 9);
    }

    #[test]
    fn test_parse_stmt_no_ws_fails() {
        // WS_REQUIRED: stmt fails without whitespace around "="
        let src = "foo=bar";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_stmt(0);
        assert!(result.is_none(), "stmt should fail without whitespace");
        // The error tracker must have recorded a position (test-9: WS_REQUIRED updates tracker).
        assert!(
            parser.error_position().is_some(),
            "error_position() must be Some after WS_REQUIRED failure"
        );
    }

    // ── items rule (+ quantifier) ─────────────────────────────────────────

    #[test]
    fn test_parse_items_one() {
        let src = "42";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_items(0);
        assert!(result.is_some(), "Failed to parse items with one atom: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 2);
    }

    #[test]
    fn test_parse_items_multiple() {
        // items := item:atom+ with NO_WS separator: atoms must be adjacent (no whitespace)
        // "42foo7" - three adjacent atoms
        let src = "42foo7";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_items(0);
        assert!(result.is_some(), "Failed to parse items: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 6);
    }

    #[test]
    fn test_parse_items_empty_fails() {
        let src = "";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_items(0);
        assert!(result.is_none(), "items should fail on empty input");
    }

    // ── opt_item rule (? quantifier) ──────────────────────────────────────

    #[test]
    fn test_parse_opt_item_present() {
        let src = "42";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_opt_item(0);
        assert!(result.is_some(), "Failed to parse opt_item: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 2);
    }

    #[test]
    fn test_parse_opt_item_absent() {
        // opt_item succeeds on empty input (? quantifier = optional)
        let src = "";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_opt_item(0);
        assert!(result.is_some(), "opt_item should succeed on empty input (? is optional)");
        let r = result.unwrap();
        assert_eq!(r.pos, 0);
    }

    // ── zero_items rule (* quantifier) ────────────────────────────────────

    #[test]
    fn test_parse_zero_items_empty() {
        let src = "";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_zero_items(0);
        assert!(result.is_some(), "zero_items should succeed on empty input (* quantifier)");
        let r = result.unwrap();
        assert_eq!(r.pos, 0);
    }

    #[test]
    fn test_parse_zero_items_some() {
        // zero_items := item:atom* with NO_WS separator: adjacent atoms
        let src = "123foo";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_zero_items(0);
        assert!(result.is_some(), "Failed to parse zero_items: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 6);
    }

    // ── capture_trivia behavior ───────────────────────────────────────────

    #[test]
    fn test_capture_trivia_false() {
        let src = "foo = bar";
        let mut parser = Parser::new(src, false);
        assert!(!parser.capture_trivia());
        let result = parser.apply__parse_stmt(0);
        assert!(result.is_some());
    }

    #[test]
    fn test_capture_trivia_true() {
        let src = "foo = bar";
        let mut parser = Parser::new(src, true);
        assert!(parser.capture_trivia());
        let result = parser.apply__parse_stmt(0);
        assert!(result.is_some());
    }

    // ── error_message / error_position ───────────────────────────────────

    #[test]
    fn test_error_message_on_failure() {
        let src = "!!!";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_num(0);
        assert!(result.is_none());
        let msg = parser.error_message();
        assert!(!msg.is_empty(), "error_message should not be empty on failure");
    }

    #[test]
    fn test_error_position_on_failure() {
        let src = "!!!";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_num(0);
        assert!(result.is_none());
        assert!(
            parser.error_position().is_some(),
            "error_position() should be Some after a failed parse attempt"
        );
    }

    #[test]
    fn test_rule_names() {
        let parser = Parser::new("", false);
        let names = parser.rule_names();
        assert!(names.contains(&"num"));
        assert!(names.contains(&"name"));
        assert!(names.contains(&"atom"));
        assert!(names.contains(&"_trivia"));
        assert!(names.contains(&"expr"));
        assert!(names.contains(&"arrow"));
        assert!(names.contains(&"latin_word"));
    }

    // ── boundary pos ─────────────────────────────────────────────────────

    #[test]
    fn test_negative_pos_non_nullable_rule_returns_none() {
        // Non-nullable rule at negative pos: should return None (not panic).
        let src = "42";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_num(-1);
        assert!(result.is_none(), "non-nullable rule at pos -1 should return None");
    }

    #[test]
    fn test_beyond_end_pos_non_nullable_rule_returns_none() {
        // Non-nullable rule past end: should return None.
        let src = "42";
        let len = Parser::new(src, false).terminals().len();
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_num(len + 1);
        assert!(result.is_none(), "non-nullable rule at pos > len should return None");
    }

    #[test]
    fn test_negative_pos_nullable_rule_returns_empty_match() {
        // zero_items (* quantifier) is nullable: at any pos it succeeds with an empty match.
        let src = "42";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_zero_items(-1);
        assert!(result.is_some(), "nullable rule at pos -1 should return Some (empty match)");
        let r = result.unwrap();
        assert_eq!(r.pos, -1, "nullable rule at pos -1 should leave pos unchanged");
    }

    // ── memo sharing (Shared::ptr_eq) ─────────────────────────────────────

    #[test]
    fn test_memo_sharing_ptr_eq() {
        // Two apply__ calls at the same (rule, pos) must return the same Arc (ptr_eq).
        let src = "42";
        let mut parser = Parser::new(src, false);
        let r1 = parser.apply__parse_num(0).expect("should parse");
        let r2 = parser.apply__parse_num(0).expect("should parse from cache");
        assert!(
            r1.result.ptr_eq(&r2.result),
            "cached result must be the same Arc (ptr_eq)"
        );
    }

    // ── direct left recursion (expr) ─────────────────────────────────────

    #[test]
    fn test_expr_single_atom() {
        // expr := lhs:expr "+" rhs:atom | atom:atom
        // "42" should parse as atom:42
        let src = "42";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_expr(0);
        assert!(result.is_some(), "Failed to parse expr: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 2);
        let node = r.result.read();
        // Single atom: atom label should be present, lhs should be absent.
        assert!(node.child_atom().is_ok(), "single expr should have atom label");
        assert!(node.child_lhs().is_err(), "single expr should not have lhs label");
    }

    #[test]
    fn test_expr_left_associativity() {
        // "1+2+3" should parse left-recursively: ((1+2)+3)
        // pos 5 = end of "1+2+3" (each char is 1 codepoint)
        let src = "1+2+3";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_expr(0);
        assert!(result.is_some(), "Failed to parse expr: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 5, "should consume all input");
        // outermost node: lhs=expr(1+2), rhs=atom(3); span covers all 5 codepoints.
        let outer = r.result.read();
        assert!(outer.child_lhs().is_ok(), "outer node should have lhs (left-recursive)");
        assert!(outer.child_rhs().is_ok(), "outer node should have rhs");
        // Span assertions (test-8): verify codepoint-indexed span values for each level.
        assert_eq!(outer.span().start(), 0, "outer span must start at 0");
        assert_eq!(outer.span().end(), 5, "outer span must end at 5");
        // inner node: lhs=expr(1), rhs=atom(2); span covers "1+2" = codepoints 0..3.
        let inner_shared = outer.child_lhs().unwrap().clone();
        drop(outer);
        let inner = inner_shared.read();
        assert!(inner.child_lhs().is_ok(), "inner node should also have lhs");
        assert!(inner.child_rhs().is_ok(), "inner node should have rhs");
        assert_eq!(inner.span().start(), 0, "inner span must start at 0");
        assert_eq!(inner.span().end(), 3, "inner span must end at 3 (covers '1+2')");
        // innermost: just atom(1) — no lhs; span covers "1" = codepoints 0..1.
        let innermost_shared = inner.child_lhs().unwrap().clone();
        drop(inner);
        let innermost = innermost_shared.read();
        assert!(innermost.child_atom().is_ok(), "innermost should be plain atom");
        assert!(innermost.child_lhs().is_err(), "innermost should not have lhs");
        assert_eq!(innermost.span().start(), 0, "innermost span must start at 0");
        assert_eq!(innermost.span().end(), 1, "innermost span must end at 1 (covers '1')");
    }

    #[test]
    fn test_expr_terminates_on_non_recursive_input() {
        // Verify left recursion doesn't loop: parse stops when no progress.
        let src = "foo";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_expr(0);
        assert!(result.is_some(), "expr should parse a plain name atom");
        let r = result.unwrap();
        assert_eq!(r.pos, 3);
    }

    // ── indirect left recursion (lval/rval) ───────────────────────────────

    #[test]
    fn test_lval_base_case() {
        // lval := inner:rval "!" | base:name
        // "foo" should parse as base:name
        let src = "foo";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_lval(0);
        assert!(result.is_some(), "Failed to parse lval: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 3);
        assert!(r.result.read().child_base().is_ok(), "lval base case should have base label");
    }

    #[test]
    fn test_rval_base_case() {
        // rval := inner:lval "?" | base:num
        // "42" should parse as base:num
        let src = "42";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_rval(0);
        assert!(result.is_some(), "Failed to parse rval: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 2);
        assert!(r.result.read().child_base().is_ok(), "rval base case should have base label");
    }

    #[test]
    fn test_rval_indirect_left_recursion_base_only() {
        // rval := inner:lval "?" | base:num
        // lval := inner:rval "!" | base:name
        // "42?": rval tries inner:lval "?" first.  lval("42") fails (only base:name matches,
        // and "42" is not a name).  Packrat grows: lval at 0 = None.  rval falls to
        // base:num "42" = pos 2.  The "?" is not consumed; that would require lval to match
        // "42" first, which it cannot.  So rval("42?") = base:num at pos 2.
        let src = "42?";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_rval(0);
        assert!(result.is_some(), "rval '42?' should parse via base:num: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 2, "rval should consume only '42' (base:num), not the '?'");
        assert!(r.result.read().child_base().is_ok(), "rval '42?' base case should have base label");
        assert!(r.result.read().child_inner().is_err(), "rval '42?' base case must not have inner label");
    }

    #[test]
    fn test_lval_indirect_left_recursion_wires_correctly() {
        // lval := inner:rval "!" | base:name
        // rval := inner:lval "?" | base:num
        // "foo!": lval tries inner:rval "!" first.  rval("foo") tries inner:lval "?".
        // lval("foo") packrat seed = None; falls to base:name "foo" = 3.
        // rval("foo") inner:lval "?" — lval = 3, "?" at pos 3 is "!" → fail.
        // rval base:num("foo") fails.  rval("foo") = None.
        // lval inner:rval = None; falls to base:name "foo" = 3.
        // Packrat grows lval to 3 but rval is still None.
        // Next grow: lval tries inner:rval "!" — rval = None → fall to base:name = 3.  No progress.
        // Result: lval("foo!") = base:name at pos 3 (not consuming "!").
        let src = "foo!";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_lval(0);
        assert!(result.is_some(), "lval 'foo!' should parse via base:name: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 3, "lval should consume only 'foo' (base:name), not '!'");
        assert!(r.result.read().child_base().is_ok(), "lval 'foo!' base case should have base label");
        assert!(r.result.read().child_inner().is_err(), "lval 'foo!' base case must not have inner label");
    }

    #[test]
    fn test_rval_mutual_recursion_positive() {
        // rval := inner:lval . "?" | base:num
        // lval := inner:rval . "!" | base:name
        // "foo?": lval("foo") = base:name at pos 3 (name matches).
        //         rval tries inner:lval "?": lval("foo") = 3, "?" at pos 3 = pos 4.
        //         So rval("foo?") = Some(pos=4), inner label set.
        let src = "foo?";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_rval(0);
        assert!(result.is_some(), "rval 'foo?' should parse: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 4, "rval should consume all 4 codepoints ('foo?')");
        assert!(
            r.result.read().child_inner().is_ok(),
            "rval 'foo?' must have inner label (mutual recursion consumed)"
        );
    }

    #[test]
    fn test_lval_mutual_recursion_positive() {
        // lval := inner:rval . "!" | base:name
        // rval := inner:lval . "?" | base:num
        // "42!": rval("42") = base:num at pos 2 (num matches).
        //        lval tries inner:rval "!": rval("42") = 2, "!" at pos 2 = pos 3.
        //        So lval("42!") = Some(pos=3), inner label set.
        let src = "42!";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_lval(0);
        assert!(result.is_some(), "lval '42!' should parse: {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 3, "lval should consume all 3 codepoints ('42!')");
        assert!(
            r.result.read().child_inner().is_ok(),
            "lval '42!' must have inner label (mutual recursion consumed)"
        );
    }

    // ── multibyte literal (arrow) ─────────────────────────────────────────

    #[test]
    fn test_arrow_multibyte_literal() {
        // "→foo": arrow literal is U+2192 (3 UTF-8 bytes, 1 codepoint)
        // Codepoint layout: pos 0 = →, pos 1 = f, pos 2 = o, pos 3 = o
        // NO_WS separator: arrow.target starts immediately after →
        let src = "→foo";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_arrow(0);
        assert!(result.is_some(), "Failed to parse arrow: {}", parser.error_message());
        let r = result.unwrap();
        // Total codepoints: →(1) + foo(3) = 4
        assert_eq!(r.pos, 4, "arrow should consume 4 codepoints (1 for → + 3 for foo)");
    }

    // ── multibyte regex (latin_word) ──────────────────────────────────────

    #[test]
    fn test_latin_word_multibyte_regex_partial_match() {
        // 'é' (U+00E9) is in À-ÿ range; 'c', 'l', etc. are ASCII and not.
        // "éclair": matches only 'é' (1 codepoint) at pos 0, stops at 'c'.
        let src = "éclair";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_latin_word(0);
        assert!(result.is_some(), "Failed to parse latin_word: {}", parser.error_message());
        let r = result.unwrap();
        // Matches only 'é' (1 codepoint in range), stops at 'c' (ASCII)
        assert_eq!(r.pos, 1, "latin_word should stop at first non-extended-Latin char");
        let node = r.result.read();
        let span = node.child_value().expect("latin_word should have value span").clone();
        assert_eq!(span.start(), 0);
        assert_eq!(span.end(), 1, "span end should be codepoint offset 1 (after é)");
    }

    #[test]
    fn test_latin_word_pure_extended() {
        // "ÀÁÂ" (U+00C0, U+00C1, U+00C2) — all in À-ÿ range, each 2 UTF-8 bytes.
        // Span offsets must be codepoint-based (3), not byte-based (6).
        let src = "ÀÁÂ";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_latin_word(0);
        assert!(result.is_some(), "Failed to parse latin_word: {}", parser.error_message());
        let r = result.unwrap();
        // 3 codepoints, each 2 UTF-8 bytes; pos should be codepoint-based = 3
        assert_eq!(r.pos, 3, "latin_word span should be 3 codepoints, not byte count");
        let node = r.result.read();
        let span = node.child_value().expect("latin_word should have value span").clone();
        assert_eq!(span.start(), 0);
        assert_eq!(span.end(), 3, "span end must be codepoint offset, not byte offset");
    }

    // ── capture_trivia on/off tree delta ──────────────────────────────────

    #[test]
    fn test_capture_trivia_tree_delta() {
        // stmt := lhs:atom : "=" : rhs:atom  (WS_REQUIRED separators)
        // With capture_trivia=false: only lhs and rhs children (2 labeled).
        // With capture_trivia=true: lhs, trivia, rhs, trivia children (2 labeled + 2 unlabeled).
        let src = "foo = bar";

        let mut p_false = Parser::new(src, false);
        let r_false = p_false.apply__parse_stmt(0).expect("parse failed (capture_trivia=false)");
        let node_false = r_false.result.read();

        let mut p_true = Parser::new(src, true);
        let r_true = p_true.apply__parse_stmt(0).expect("parse failed (capture_trivia=true)");
        let node_true = r_true.result.read();

        // Labeled children must be identical in both modes.
        let lhs_false = node_false.child_lhs().expect("lhs absent (capture_trivia=false)");
        let lhs_true = node_true.child_lhs().expect("lhs absent (capture_trivia=true)");
        assert_eq!(lhs_false.read().span(), lhs_true.read().span(), "lhs span must match across capture_trivia modes");

        let rhs_false = node_false.child_rhs().expect("rhs absent (capture_trivia=false)");
        let rhs_true = node_true.child_rhs().expect("rhs absent (capture_trivia=true)");
        assert_eq!(rhs_false.read().span(), rhs_true.read().span(), "rhs span must match across capture_trivia modes");

        // Total children differ: capture_trivia=true adds unlabeled trivia entries.
        let total_false = node_false.children().len();
        let total_true = node_true.children().len();
        assert!(
            total_true > total_false,
            "capture_trivia=true should produce more total children ({total_true}) than false ({total_false})"
        );
        // capture_trivia=false: only lhs and rhs (2 children).
        assert_eq!(total_false, 2, "capture_trivia=false should have exactly 2 children (lhs + rhs)");
    }

    // ── SUPPRESS absent from children ─────────────────────────────────────

    #[test]
    fn test_suppress_absent_from_children() {
        // paren_expr := %"(" , inner:atom , %")"
        // Suppressed "(" and ")" must not appear in children.
        // With capture_trivia=false: only inner (1 child).
        let src = "(42)";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_paren_expr(0).expect("parse failed");
        let node = result.result.read();

        // inner:atom must be present.
        assert!(node.child_inner().is_ok(), "inner child must be present");
        // Total children must be exactly 1 (the inner label only; parens are suppressed).
        assert_eq!(
            node.children().len(),
            1,
            "paren_expr with capture_trivia=false should have exactly 1 child (inner), got {}",
            node.children().len()
        );
    }

    // ── union-label val rule ─────────────────────────────────────────────

    #[test]
    fn test_val_union_label_num() {
        // val := item:num | item:name | item:/[!@#$]+/
        // The same label "item" covers a num node, a name node, and a bare span → union label.
        // "42" parses as item:num (ValChild::Num arm).
        let src = "42";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_val(0);
        assert!(result.is_some(), "Failed to parse val '42': {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 2);
        // child_item returns the union enum; verify parse succeeded and consumed correct span.
        assert!(r.result.read().child_item().is_ok(), "val '42' must have item label");
        // Must be the Num variant, not Span.
        let child = r.result.read().child_item().unwrap().clone();
        assert!(matches!(child, cst::ValChild::Num(_)), "val '42' item must be ValChild::Num");
    }

    #[test]
    fn test_val_union_label_name() {
        // val := item:num | item:name | item:/[!@#$]+/
        // "foo" parses as item:name (ValChild::Name arm).
        let src = "foo";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_val(0);
        assert!(result.is_some(), "Failed to parse val 'foo': {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 3);
        assert!(r.result.read().child_item().is_ok(), "val 'foo' must have item label");
        let child = r.result.read().child_item().unwrap().clone();
        assert!(matches!(child, cst::ValChild::Name(_)), "val 'foo' item must be ValChild::Name");
    }

    #[test]
    fn test_val_union_label_span() {
        // val := item:num | item:name | item:/[!@#$]+/
        // "!@#" parses as item:/[!@#$]+/ (ValChild::Span arm — the union-span case).
        // This exercises cst::ValChild::Span, the third append variant in the decision table.
        let src = "!@#";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_val(0);
        assert!(result.is_some(), "Failed to parse val '!@#': {}", parser.error_message());
        let r = result.unwrap();
        assert_eq!(r.pos, 3, "val '!@#' should consume all 3 codepoints");
        assert!(r.result.read().child_item().is_ok(), "val '!@#' must have item label");
        let child = r.result.read().child_item().unwrap().clone();
        assert!(matches!(child, cst::ValChild::Span(_)), "val '!@#' item must be ValChild::Span");
    }

    // ── $-included unlabeled literal present as child ─────────────────────

    #[test]
    fn test_include_span_present_unlabeled() {
        // tagged := $"tag" . value:/[a-z]+/
        // The $-included "tag" literal must appear as an unlabeled child (label == None).
        // With capture_trivia=false: 2 children — unlabeled Span("tag") + labeled value.
        let src = "tagfoo";
        let mut parser = Parser::new(src, false);
        let result = parser.apply__parse_tagged(0).expect("parse failed");
        let node = result.result.read();

        // labeled value child must be present.
        assert!(node.child_value().is_ok(), "value child must be present");
        // Total children: unlabeled tag span + labeled value = 2.
        assert_eq!(
            node.children().len(),
            2,
            "tagged should have 2 children (unlabeled tag span + labeled value), got {}",
            node.children().len()
        );
        // First child must have label == None (the $-included literal).
        let (first_label, _) = &node.children()[0];
        assert!(first_label.is_none(), "first child of tagged must be unlabeled ($-included literal)");
    }
}
