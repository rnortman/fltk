Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 2f9b05e

---

test-1. `tests/test_gsm2tree_rs.py:452-453` — stale/misleading comment + no new generator-level test.

The comment at line 448 says "data struct now also derives Debug (Phase 2)" and the assertion at line 453 asserts `"#[derive(Clone, Debug)]" in poc_source`. That assertion still passes — but only because child enums use `#[derive(Clone, Debug)]`. Node structs now use `#[derive(Clone)]` only. The comment is false as stated, and no test in `test_gsm2tree_rs.py` verifies the new behavior: (a) node structs use `#[derive(Clone)]` not `#[derive(Clone, Debug)]`; (b) a manual `impl fmt::Debug` is present on each node struct; (c) it uses `debug_struct`, prints `"span"`, and prints `"<N child(ren)>"`; (d) `DropWorklistItem` is emitted when the child-class union is non-empty; (e) `impl Drop` is emitted for nodes with node-typed children and omitted for span-only nodes; (f) `into_drop_item` is emitted only when needed (gating condition). Without these generator-level assertions, a regression in the generator (e.g. accidentally re-introducing `derive(Debug)` on the struct, or silently dropping the `fmt` impl) would pass all Python tests and only be caught by the Rust compile/test round, which is slower and less precise. Consequence: a generator regression that removes the manual Debug impl or re-derives it would not be caught before the Rust test phase; the stale comment actively misleads future readers into thinking derive(Clone, Debug) is the intended form for node structs. Fix: update the comment at 448-453 to note that only child enums derive Debug; add a `TestNodeDebugDrop` class to `test_gsm2tree_rs.py` with: (a) `assert "#[derive(Clone)]" in poc_source` for the Identifier struct line and `assert "#[derive(Clone, Debug)]" not in poc_source.split("pub struct Identifier")[1].split("pub struct")[0]` (scoped to avoid false negatives from child enum); (b) `assert "impl fmt::Debug for Identifier {" in poc_source`; (c) `assert 'f.debug_struct("Identifier")' in poc_source`; (d) `assert '"<{} child(ren)>"' in poc_source`; (e) `assert "enum DropWorklistItem {" in poc_source` (for a grammar with node-typed children, e.g. `poc_source` has `ItemsChild::Identifier`); (f) `assert "impl Drop for Items {" in poc_source` and `assert "impl Drop for Identifier {" not in poc_source` (span-only gets no Drop).

---

test-2. `tests/test_gsm2tree_rs.py` (absent) — no flat-grammar test for empty `DropWorklistItem` case.

The design explicitly states: "Degenerate case: if the union is empty (flat grammar, no node-typed children anywhere), emit no `_drop_block` at all." The `_make_minimal_grammar()` fixture (single rule, regex children only) is the flat case, but `TestMinimalGrammar` has no assertion checking that `DropWorklistItem` is absent from the minimal output. Consequence: a regression that emits an empty-union `DropWorklistItem` block (which would cause `dead_code` warnings under `-D warnings`) would not be caught by Python tests. Fix: add to `TestMinimalGrammar`: `assert "DropWorklistItem" not in minimal_source, "flat grammar must not emit DropWorklistItem"` and `assert "impl Drop" not in minimal_source`.

---

test-3. `tests/test_gsm2tree_rs.py:448-459` — `TestCfgFeatureGate.test_node_struct_pyclass_gated` comment+assertion contradict the new output.

The test asserts `assert "#[derive(Clone, Debug)]" in poc_source` at line 453 as evidence "Data struct derives Clone and Debug (Phase 2)" — this is now incorrect. The node struct assertion survives only because child enums still have `#[derive(Clone, Debug)]`. The test mislabels a child-enum fact as a node-struct fact, creating a false sense of coverage. Consequence: someone reading the test believes node structs still derive Debug (they don't), and the test provides no protection against accidentally reverting to derived Debug on the struct. Fix: replace the node-struct half of this assertion with `assert "#[derive(Clone)]\npub struct Identifier {" in poc_source` (exact form), add a negative: `assert "#[derive(Clone, Debug)]\npub struct Identifier {" not in poc_source`, and keep the child-enum positive separately.

---

test-4. `tests/rust_parser_fixture/src/native_tests.rs` — `build_deep_expr_chain` test structure exercises only the lhs:Expr path; rhs and multi-child teardown paths are not isolated.

Tests 1 and 2 build a 100 000-level chain where every level has exactly 1 node-typed child (lhs:Expr). The worklist therefore oscillates between 0 and 1 items — it never holds more than 1 entry. The design's worklist can hold many items when a node has multiple node-typed children (breadth > 1). The `rec_via_sub` rule (which has `inner:rec_via_sub + inner:atom` patterns) or `Expr` with both `lhs` and `rhs` children present would exercise multi-child worklist growth. Consequence: the deep-teardown tests do not exercise the multi-child-per-level drain path; a bug that drops extra worklist pushes or misidentifies the 2nd child variant would not be caught. This is a quality gap, not a catastrophic hole (the shared-subtree test and parser test do create multi-child nodes at small scale). Fix: add one test that builds a tree where each parent has two node-typed children (e.g., build `Expr(lhs=prev, rhs=some_shared_atom)` at each level of a 100-level chain) and drops it — verifying the multi-child arm correctly enqueues both children.

---

test-5. `crates/fltk-cst-core/src/shared.rs:118-131` — `test_strong_count_new_clone_drop` duplicates `test_shared_strong_count` in `native_tests.rs:100-107`.

Both tests check identical behavior (new→count 1, clone→count 2, drop clone→count 1) on the same `Shared` type. The design's plan item 4 says "in `crates/fltk-cst-core`" — that test was added. The one in `native_tests.rs` is redundant. Consequence: not a correctness gap, but redundant tests add noise and maintenance surface without additional protection. Fix: remove `test_shared_strong_count` from `native_tests.rs` (keep the `crates/fltk-cst-core` version which is the canonical home per the design) or, if the fixture-crate test is meant to confirm the method is accessible from downstream crates, add a comment to that effect.

---

test-6. `crates/fltk-cst-spike/src/spike_tests.rs:367-368` — `IdentifierChild::Span` Debug format! discarded without assertion.

After the upgrade, `span_child` (line 367-368) is still formatted with `let _ = format!(...)` — no assertion added. The design's plan item 6 says to "upgrade from discard-only to content assertions" and lists `IdentifierChild::Span` (a `Span`, no delegation through `Shared`) as needing a content assertion distinct from the `ItemsChild::Identifier` path. The Span variant's Debug is trivially non-recursive and would output something like `"Span(Span { ... })"` — the test does not verify that. Consequence: if `IdentifierChild::Span` were accidentally changed to delegate to a broken path, the discarded `format!` would still pass. Low risk, but the design explicitly called this out. Fix: replace the `let _ = ...` with an assertion that the output contains `"Span"` (at minimum).

---

test-7. `tests/rust_parser_fixture/src/native_tests.rs:113-141` — test 5 comment says "natural drop of r.result (and the parser memo table)" but the drop ordering means the parser drops last, silently holding live Shared<Expr> handles from the memo table.

In the test, `r.result` (the root) is dropped implicitly when `r` goes out of scope at end of test; `parser` was declared before `r` so it drops after `r` in Rust's LIFO destructor order. The parser's `Cache<Shared<Expr>>` holds one `Shared<Expr>` entry per (rule, pos) pair — for a 100 000-node parse, the cache holds ~100 000 handles to intermediate `Expr` nodes. Each of those drops iteratively when the Cache releases the handle (count → 1 → iterative Drop). But the assertion at line 138 (`dbg.len() < 256`) fires on the root node's Debug output before any cache drops. The test comment implies both drops are verified, which is true but implicit — no explicit `drop(r); drop(parser);` sequence to make the ordering visible, and no assertion that isolates the parser-cache teardown. This is a documentation/clarity gap only; the test does exercise both drops (parser's cache teardown happens at end-of-scope). Consequence: reader misunderstanding, not a functional gap. Fix: add `drop(r); drop(parser);` explicitly before the end of the test body, matching the comment's intent.
