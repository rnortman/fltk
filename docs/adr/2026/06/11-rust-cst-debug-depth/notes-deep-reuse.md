Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 2f9b05e
Base: 8c10cea

---

## reuse-1 — Duplicate `Shared::strong_count` unit test

**File:line:**
- `crates/fltk-cst-core/src/shared.rs:123` — `test_strong_count_new_clone_drop`
- `tests/rust_parser_fixture/src/native_tests.rs:100` — `test_shared_strong_count`

**What's duplicated.** Both tests assert `strong_count == 1` after `new`, `== 2` after `clone`, back to `1` after `drop`. The fixture test substitutes `Shared<cst::Expr>` for `Shared<u32>`; the tested behavior is `Arc::strong_count` on `Shared<T>` generically — the type parameter is not load-bearing. The method being tested (`Shared::strong_count`) lives in `fltk-cst-core`; its unit tests belong there.

**Existing function/utility:** `crates/fltk-cst-core/src/shared.rs:123` — `test_strong_count_new_clone_drop`.

**Consequence.** If the `strong_count` method contract changes (e.g. adjusts for Weak handles), both tests must be updated independently; they will diverge in coverage as the fixture test inherits whatever `cst::Expr::new` requires. Any `strong_count` correctness fix in the core test may also need propagation to the fixture if the fixture drifts. Low maintenance cost today, but a precedent that `Shared` method tests belong in the fixture crate, which would scatter ownership of `fltk-cst-core` API verification.

---

## reuse-2 — `DEEP_TREE_DEPTH` constant not reused in test 5

**File:line:** `tests/rust_parser_fixture/src/native_tests.rs:115` — `let n = 100_000usize;` inside `test_parser_produced_deep_tree_debug_and_drop`.

**What's duplicated.** `DEEP_TREE_DEPTH` is declared at line 9 (`const DEEP_TREE_DEPTH: usize = 100_000`) and is the authoritative depth for the deep-tree tests in this module. Test 5 introduces its own `100_000usize` literal at line 115 rather than referencing `DEEP_TREE_DEPTH`, so the two are not joined.

**Existing function/utility:** `tests/rust_parser_fixture/src/native_tests.rs:9` — `DEEP_TREE_DEPTH`.

**Consequence.** If the depth is lowered for CI speed or raised to increase confidence, test 5 must be updated separately and a reviewer must notice the second literal; the mismatch comment at line 114 ("~100_000-level chain") already mentions the expected depth, making silent divergence easy to miss.
