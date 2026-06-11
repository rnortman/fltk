//! Ports of all `fltk/fegen/pyrt/test_memo.py` test cases.
// The `apply__` double-underscore naming mirrors the naming convention used by generated
// parsers (apply__parse_<rule>) for cross-backend auditability.
#![allow(non_snake_case)]
//!
//! Uses a hand-written toy parser (`ToyParser`) that exercises `apply` through the public
//! API exactly as generated code will (non-capturing `fn` projectors, typed caches).
//!
//! Grammar:
//! ```text
//! expr    := expr "+" num | num                   (rule 0, direct left recursion)
//! a       := b "+" num                            (rule 1, indirect via b)
//! b       := a | num                              (rule 2, indirect via a)
//! multi_a := multi_b | multi_c | multi_d          (rule 0, multi-path)
//! multi_b := multi_a "b"                          (rule 1)
//! multi_c := multi_a "c"                          (rule 2)
//! multi_d := "d"                                  (rule 3)
//! ```
//!
//! Token representation: each element of the `tokens: Vec<String>` slice is a single token.
//! `pos` is a token-list index (not a codepoint index).

use fltk_parser_core::memo::{apply, ApplyResult, Cache, PackratState};

// ── Toy expression type ──────────────────────────────────────────────────────

/// Simple expression tree mirroring Python's `ExprType`.
#[derive(Clone, Debug, PartialEq)]
enum Expr {
    Num(i64),
    Str(String),
    BinOp(Box<Expr>, String, i64),
    Suffix(Box<Expr>, String),
}

// ── Toy parser struct ────────────────────────────────────────────────────────

struct ToyParser {
    tokens: Vec<String>,
    packrat: PackratState,
    cache0: Cache<Expr>,
    cache1: Cache<Expr>,
    cache2: Cache<Expr>,
    cache3: Cache<Expr>,
    /// Invocation counter per cache (for memoization assertions).
    invocations: [usize; 4],
}

impl ToyParser {
    fn new(tokens: Vec<String>) -> Self {
        ToyParser {
            tokens,
            packrat: PackratState::default(),
            cache0: Cache::default(),
            cache1: Cache::default(),
            cache2: Cache::default(),
            cache3: Cache::default(),
            invocations: [0; 4],
        }
    }

    // ── Field projectors (fn pointers, non-capturing) ───────────────────────

    fn state(p: &mut ToyParser) -> &mut PackratState { &mut p.packrat }
    fn cache0(p: &mut ToyParser) -> &mut Cache<Expr> { &mut p.cache0 }
    fn cache1(p: &mut ToyParser) -> &mut Cache<Expr> { &mut p.cache1 }
    fn cache2(p: &mut ToyParser) -> &mut Cache<Expr> { &mut p.cache2 }
    fn cache3(p: &mut ToyParser) -> &mut Cache<Expr> { &mut p.cache3 }

    // ── Helper ───────────────────────────────────────────────────────────────

    fn token(&self, pos: i64) -> Option<&str> {
        self.tokens.get(pos as usize).map(|s| s.as_str())
    }

    fn num_at(&self, pos: i64) -> Option<i64> {
        self.token(pos)?.parse().ok()
    }

    // ── Direct left-recursion grammar (rule_expr, cache0) ───────────────────

    /// `apply__rule_expr`: memoized entry point.
    fn apply__rule_expr(&mut self, pos: i64) -> Option<ApplyResult<Expr>> {
        apply(self, 0, pos, Self::state, Self::cache0, Self::rule_expr)
    }

    /// Rule body: `expr := expr "+" num | num`.
    ///
    /// Alternative 1 commits once `expr` succeeds: if the `"+" num` continuation fails,
    /// return `None` rather than falling through to Alternative 2. This matches the Python
    /// reference (`test_memo.py:51-83`) which returns `None` in that case.
    fn rule_expr(p: &mut ToyParser, pos: i64) -> Option<ApplyResult<Expr>> {
        p.invocations[0] += 1;
        let start_pos = pos;
        // Alternative 1: expr "+" num (commit after successful expr)
        if let Some(ApplyResult { pos: p1, result: r0 }) = p.apply__rule_expr(pos) {
            // Recursive call succeeded — commit to this alternative.
            // If the continuation fails, do NOT fall through to Alternative 2.
            return if p.token(p1) == Some("+") {
                p.num_at(p1 + 1).map(|n| ApplyResult {
                    pos: p1 + 2,
                    result: Expr::BinOp(Box::new(r0), "+".to_owned(), n),
                })
            } else {
                None
            };
        }
        // Alternative 2: num (only reached when Alternative 1's expr sub-call returned None)
        if let Some(n) = p.num_at(start_pos) {
            return Some(ApplyResult { pos: start_pos + 1, result: Expr::Num(n) });
        }
        None
    }

    // ── Indirect left-recursion grammar (indirect_a, indirect_b) ─────────────

    fn apply__indirect_a(&mut self, pos: i64) -> Option<ApplyResult<Expr>> {
        apply(self, 1, pos, Self::state, Self::cache1, Self::indirect_a)
    }

    fn apply__indirect_b(&mut self, pos: i64) -> Option<ApplyResult<Expr>> {
        apply(self, 2, pos, Self::state, Self::cache2, Self::indirect_b)
    }

    /// `a := b "+" num`
    ///
    /// Ports Python's `indirect_a` (test_memo.py:92-114). Commits after `b` succeeds:
    /// if the `"+" num` continuation fails, returns `None` (no fallback alternative).
    /// When `b` returns `None`, returns `None` — there is no `<nothing>` empty production.
    fn indirect_a(p: &mut ToyParser, pos: i64) -> Option<ApplyResult<Expr>> {
        p.invocations[1] += 1;
        if let Some(ApplyResult { pos: p1, result: r0 }) = p.apply__indirect_b(pos) {
            // b succeeded — commit. Return None if "+" num continuation fails.
            return if p.token(p1) == Some("+") {
                p.num_at(p1 + 1).map(|n| ApplyResult {
                    pos: p1 + 2,
                    result: Expr::BinOp(Box::new(r0), "+".to_owned(), n),
                })
            } else {
                None
            };
        }
        // b returned None — no alternative; return None.
        None
    }

    /// `b := a | num`
    fn indirect_b(p: &mut ToyParser, pos: i64) -> Option<ApplyResult<Expr>> {
        p.invocations[2] += 1;
        if let Some(r) = p.apply__indirect_a(pos) {
            return Some(r);
        }
        if let Some(n) = p.num_at(pos) {
            return Some(ApplyResult { pos: pos + 1, result: Expr::Num(n) });
        }
        None
    }

    // ── Multi-path left-recursion grammar ────────────────────────────────────

    fn apply__multi_a(&mut self, pos: i64) -> Option<ApplyResult<Expr>> {
        apply(self, 0, pos, Self::state, Self::cache0, Self::multi_a)
    }

    fn apply__multi_b(&mut self, pos: i64) -> Option<ApplyResult<Expr>> {
        apply(self, 1, pos, Self::state, Self::cache1, Self::multi_b)
    }

    fn apply__multi_c(&mut self, pos: i64) -> Option<ApplyResult<Expr>> {
        apply(self, 2, pos, Self::state, Self::cache2, Self::multi_c)
    }

    fn apply__multi_d(&mut self, pos: i64) -> Option<ApplyResult<Expr>> {
        apply(self, 3, pos, Self::state, Self::cache3, Self::multi_d)
    }

    /// `multi_a := multi_b | multi_c | multi_d`
    fn multi_a(p: &mut ToyParser, pos: i64) -> Option<ApplyResult<Expr>> {
        p.apply__multi_b(pos).or_else(|| p.apply__multi_c(pos)).or_else(|| p.apply__multi_d(pos))
    }

    /// `multi_b := multi_a "b"`
    fn multi_b(p: &mut ToyParser, pos: i64) -> Option<ApplyResult<Expr>> {
        let ApplyResult { pos: p1, result: r0 } = p.apply__multi_a(pos)?;
        if p.token(p1) == Some("b") {
            Some(ApplyResult { pos: p1 + 1, result: Expr::Suffix(Box::new(r0), "b".to_owned()) })
        } else {
            None
        }
    }

    /// `multi_c := multi_a "c"`
    fn multi_c(p: &mut ToyParser, pos: i64) -> Option<ApplyResult<Expr>> {
        let ApplyResult { pos: p1, result: r0 } = p.apply__multi_a(pos)?;
        if p.token(p1) == Some("c") {
            Some(ApplyResult { pos: p1 + 1, result: Expr::Suffix(Box::new(r0), "c".to_owned()) })
        } else {
            None
        }
    }

    /// `multi_d := "d"`
    fn multi_d(p: &mut ToyParser, pos: i64) -> Option<ApplyResult<Expr>> {
        if p.token(pos) == Some("d") {
            Some(ApplyResult { pos: pos + 1, result: Expr::Str("d".to_owned()) })
        } else {
            None
        }
    }
}

// Helper to build a token sequence from a string (each char is one token).
fn tokens(s: &str) -> Vec<String> {
    s.chars().map(|c| c.to_string()).collect()
}

// ── Ported test cases ────────────────────────────────────────────────────────

/// Port of `test_memo.py::test_direct`.
///
/// Input "0+1+2+3+4+i" → `((((0+1)+2)+3)+4)` ending at pos 9.
/// Note: each character is a token; "i" is not a digit so the parse stops at pos 9.
#[test]
fn test_direct() {
    let mut p = ToyParser::new(tokens("0+1+2+3+4+i"));
    let result = p.apply__rule_expr(0);
    assert!(result.is_some());
    let ApplyResult { pos, result } = result.unwrap();
    assert_eq!(pos, 9);
    let expected = Expr::BinOp(
        Box::new(Expr::BinOp(
            Box::new(Expr::BinOp(
                Box::new(Expr::BinOp(Box::new(Expr::Num(0)), "+".to_owned(), 1)),
                "+".to_owned(),
                2,
            )),
            "+".to_owned(),
            3,
        )),
        "+".to_owned(),
        4,
    );
    assert_eq!(result, expected);
}

/// Port of `test_memo.py::test_indirect`.
///
/// Same result as `test_direct`, via indirect mutual recursion.
#[test]
fn test_indirect() {
    let mut p = ToyParser::new(tokens("0+1+2+3+4+i"));
    let result = p.apply__indirect_a(0);
    assert!(result.is_some());
    let ApplyResult { pos, result } = result.unwrap();
    assert_eq!(pos, 9);
    let expected = Expr::BinOp(
        Box::new(Expr::BinOp(
            Box::new(Expr::BinOp(
                Box::new(Expr::BinOp(Box::new(Expr::Num(0)), "+".to_owned(), 1)),
                "+".to_owned(),
                2,
            )),
            "+".to_owned(),
            3,
        )),
        "+".to_owned(),
        4,
    );
    assert_eq!(result, expected);
}

/// Port of `test_memo.py::test_multi_b`.
///
/// Input "db" → `("d", "b")` at pos 2.
#[test]
fn test_multi_b() {
    let mut p = ToyParser::new(tokens("db"));
    let result = p.apply__multi_a(0);
    assert!(result.is_some());
    let ApplyResult { pos, result } = result.unwrap();
    assert_eq!(pos, 2);
    assert_eq!(result, Expr::Suffix(Box::new(Expr::Str("d".to_owned())), "b".to_owned()));
}

/// Port of `test_memo.py::test_multi_c`.
///
/// Input "dc" → `("d", "c")` at pos 2.
#[test]
fn test_multi_c() {
    let mut p = ToyParser::new(tokens("dc"));
    let result = p.apply__multi_a(0);
    assert!(result.is_some());
    let ApplyResult { pos, result } = result.unwrap();
    assert_eq!(pos, 2);
    assert_eq!(result, Expr::Suffix(Box::new(Expr::Str("d".to_owned())), "c".to_owned()));
}

/// Port of `test_memo.py::test_fail`.
///
/// Input "a": `b` fails (not a digit, `a` poisoned), so `a` returns `None`.
/// Python asserts `apply_result is None` (test_memo.py:253).
#[test]
fn test_fail() {
    let mut p = ToyParser::new(tokens("a"));
    let result = p.apply__indirect_a(0);
    // a := b "+" num; b := a | num.
    // b(0): a(0) → poison (Failure seed); num("a") → None; b returns None.
    // a(0): b returned None; no fallback; a returns None.
    // Exercises the failed-recursion-seed path (design §2.5 step 5).
    assert!(result.is_none());
}

// ── Memoization assertions ───────────────────────────────────────────────────

/// Verify that the rule body executes at most once per (rule, pos) pair.
///
/// Second `apply` at the same position should be a pure cache hit.
#[test]
fn test_memoization_hit() {
    let mut p = ToyParser::new(tokens("0+1"));
    // First call — populates the cache.
    let r1 = p.apply__rule_expr(0);
    let count_after_first = p.invocations[0];
    assert!(r1.is_some());
    assert!(count_after_first > 0, "rule body must execute at least once on first call");

    // Second call at the same position — must not increment the invocation counter.
    let r2 = p.apply__rule_expr(0);
    assert_eq!(p.invocations[0], count_after_first, "rule body re-executed on cache hit");
    assert_eq!(r1, r2);
}

/// Verify that a `Failure` cache entry is not recomputed on the second call.
///
/// Covers design §4.1: "Failure caching: failed rule re-queried at same pos does not re-execute."
/// Maps to test_memo.py::test_fail (Python verifies `None`; we additionally verify no re-execution).
#[test]
fn test_failure_caching() {
    // `a := b "+" num`; `b := a | num`. Input "a": indirect_a returns None (failure).
    // The second call at the same position must be a Failure cache hit — no re-execution.
    let mut p = ToyParser::new(tokens("a"));
    let r1 = p.apply__indirect_a(0);
    let count_after_first = p.invocations[1];
    assert!(r1.is_none(), "first call should return None for input 'a'");
    assert!(count_after_first > 0, "rule body must execute at least once on first call");

    let r2 = p.apply__indirect_a(0);
    assert_eq!(r2, None, "second call should also return None (Failure cache hit)");
    assert_eq!(
        p.invocations[1], count_after_first,
        "indirect_a re-executed after Failure was cached"
    );
}

/// Verify that the `new_pos <= entry.final_pos` termination condition (memo.py:248)
/// fires on the equal-position case (non-growing recursive alternative).
#[test]
fn test_growth_termination_equal_position() {
    // Grammar: just `multi_d := "d"` — no alternative that grows.
    // Input "d": multi_a → multi_b (fails, multi_a returns "d" from cache) → "d" pos=1 → multi_b needs "b" at pos 1, none.
    // multi_a should return ("d") at pos 1 via the multi_d alternative.
    let mut p = ToyParser::new(tokens("d"));
    let result = p.apply__multi_a(0);
    assert!(result.is_some());
    let ApplyResult { pos, result } = result.unwrap();
    assert_eq!(pos, 1);
    assert_eq!(result, Expr::Str("d".to_owned()));
}
