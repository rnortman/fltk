# Design review r2: non-recursive Debug + iterative Drop for generated CST nodes

Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

Reviewed: `design.md` (r2, Drop scope folded in) against `request.md`, `exploration.md`, `evaluation-drop-depth-reachability.md`, and source at the working tree (HEAD 7ddec4a + staged docs; ef315be is an ancestor — HEAD additionally contains the parse-depth-limit implementation in `crates/fltk-parser-core/src/memo.rs`).

## Verification summary (claims checked against source)

- `gsm2tree_rs.py`: TODO comment + `#[derive(Clone, Debug)]` at 638-640 ✓; `_preamble()` at 261 (no existing `use std::fmt;` in generated files) ✓; `_child_enum_block` at 488, child-enum `derive(Clone, Debug)` at 504, manual `PartialEq` ends before the python-gated block at 533 ✓; `_repr_method` at 1500-1511 prints span start/end + child count, non-recursive ✓; node `PartialEq` impl directly follows the struct (insertion point exists) ✓.
- `shared.rs`: `Debug` at 98-102 (read lock + delegate) ✓; cycle contract at 36-40 ✓; `write()` ignores poison (58-60) ✓; no `Weak` anywhere in `fltk-cst-core`; registry uses a Python `WeakValueDictionary` keyed by `arc_ptr` (registry.rs:32-40), not `Arc::downgrade` → the `strong_count == 1` sole-ownership argument is sound ✓.
- `Span::Debug` is manual and shallow (`span.rs:155-166`, prints start/end/has_source, source elided) ✓; spike assertion at `spike_tests.rs:381-389` ✓; the four `format!` smoke calls at `spike_tests.rs:364-378` ✓.
- E0509 claim: grep over `src/`, fixture crates, spike found no by-value destructuring of node structs; only `ApplyResult { .. }` patterns (memo.rs / memo_toy.rs), not CST nodes ✓. `extend-children-owned` (TODO.md:80-82) appends via `&mut other.children` on an owned binding — compatible with `impl Drop` ✓.
- TODO bookkeeping: `TODO.md` entry at 84-86 ✓; only `TODO(rust-cst-debug-depth)` site is `gsm2tree_rs.py:638` ✓.
- Regeneration: `make gencode` produces exactly the six listed outputs, spike `cst.rs` via `cp src/cst_generated.rs` (Makefile 148-186) ✓.
- Test plan substrate: `expr := lhs:expr . "+" . rhs:atom | atom:atom` at `rust_parser_fixture.fltkg:32` ✓; `ExprChild::Expr(Shared<Expr>)` exists (fixture `cst.rs:5088-5091`) ✓; `native_tests.rs` exists ✓; `Shared<Alternatives>` in `tests/rust_cst_fegen/src/cst.rs:779` ✓.
- **Reachability conclusion re-verified (prompt directive): holds.** The depth guard counts only concurrent `apply` entries and decrements on exit (memo.rs:159-168); `grow_seed` is a `loop` (memo.rs:393-421) whose per-iteration `lhs` re-entry is a cache hit returning an Arc clone of the previously grown root (memo.rs:253-257), embedded as a child via `append_lhs` (fixture `parser.rs:481-485`). CST depth for `"1+1+…"` scales with input length at ~constant `apply` depth. Both Drop and Debug overflows remain reachable from untrusted input post-limit; both fixes warranted.
- Requirements coverage: every request constraint (`__repr__` unchanged, `Clone` unchanged, `Shared::Debug` unchanged, TODO removal) and verification expectation (deep-tree Debug test, spike updates, regen + pytest + cargo test) maps to a design section. Drop scope expansion is user-directed per the round-1 resolution; deep `PartialEq` correctly held out of scope.

## Findings

### design-1: `DropWorklistItem` variants for never-child node classes fail the `-D warnings` gate

Section: "Drop: iterative worklist teardown", piece 2 — "one variant per node class in the grammar" and "Arms are uniform across all node classes (including span-only-children classes …)".

What's wrong: variants are constructed only by `into_drop_item`, which constructs only variants for classes that appear as a node-typed child-enum variant. Classes that never appear as anyone's child get a `DropWorklistItem` variant that is matched in `drain_into` but never constructed. rustc's `dead_code` lint fires "variant is never constructed" for such variants of a private enum (pattern matching does not count as construction).

Why (source-backed): per generated file, the never-child class sets are non-empty —
- `src/cst_generated.rs`: `Items`;
- `src/cst_fegen.rs`: `Grammar`;
- `tests/rust_parser_fixture/src/cst.rs`: `Arrow`, `Grouped`, `Items`, `LatinWord`, `LeadingWs`, `OptItem`, `ParenExpr`, `Stmt`, `Tagged`, `Val`, `ZeroItems` (11 of 21 classes).
`make check` runs `cargo clippy -q -- -D warnings` on the workspace and both fixture crates plus python-off variants (Makefile:51-71), so the warning is a hard gate failure. Generated code carries no `#[allow(dead_code)]` precedent to absorb it.

Consequence: the implementation as designed does not compile through `make check`; the implementer will be forced into an ad-hoc unreviewed fix mid-implementation.

Suggested fix (design should pick one deliberately): (a) restrict `DropWorklistItem` variants (and `drain_into` arms) to the union of node-typed child classes across all child enums — already computable from `_child_variants_for_rule`; root-only classes need no variant because their own `impl Drop` drains their children directly. Note the secondary effect: under (a), `into_drop_item` on the child enum of a never-child, span-only class (e.g. `Tagged`, `LatinWord` — no `Drop` impl, no `drain_into` arm) becomes uncalled and itself trips `dead_code`; emit `into_drop_item` only for enums whose class has a `Drop` impl or appears as a child. Or (b) keep uniform variants and emit a commented `#[allow(dead_code)]` on the enum. (a) is cleaner; (b) is simpler. Either way the design must state it.

### design-2: root-cause section cites the superseded (flawed) reachability argument instead of the evaluation

Section: "Root cause / context" — "The parse-depth-limit work does not eliminate either exposure (`exploration.md` §5)."

What's wrong: `exploration.md` §5 supports the (correct) conclusion with a claim the reachability evaluation showed to be false: "a successfully parsed tree could have node-nesting depth up to ~N [the limit]". The evaluation (`evaluation-drop-depth-reachability.md` §2, §4) establishes the stronger, correct mechanism — left-recursive seed-grow deepens the CST per loop iteration, so parser-produced depth is bounded by input length, not `max_depth` — and explicitly recommends: "if revised, cite the left-recursion mechanism above instead." This r2 revision did not update the citation and does not reference the evaluation doc at all.

Why: verified in code — depth counter decrements per `apply` exit (memo.rs:159-168); `grow_seed` loop (memo.rs:393-421); cache-hit Arc-clone embedding (memo.rs:253-257, fixture parser.rs:481-485).

Consequence: a future reader re-deriving the threat model from the design's only cited source would conclude post-limit CST depth ≤ ~1000 (`DEFAULT_MAX_DEPTH`, memo.rs:70) and could justify weakening the tests (e.g. lowering the 100 000 depth) or re-litigating whether the Drop fix is needed. The ADR record would preserve a wrong supporting argument for a load-bearing security claim.

Suggested fix: change the citation to `evaluation-drop-depth-reachability.md` (or restate the left-recursion mechanism in one sentence); optionally note the evaluation's optional parser-produced deep-tree test as a deliberate non-adoption.

No other findings. The Drop algorithm (steal-on-sole-ownership, worklist LIFO, early-return terminator), its termination/complexity claims, the concurrency race note, the cycle behavior, the E0509 analysis, the `strong_count` soundness argument, and the Debug rendering decisions all check out against source.
