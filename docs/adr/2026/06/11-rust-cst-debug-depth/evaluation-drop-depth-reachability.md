# Evaluation: does parse-depth-limit bound CST depth, making the Drop/Debug fixes unreachable from parsing?

Concise. Precise. Complete. Unambiguous. Audience: smart LLM/human.

Question (user): once parse-depth-limit bounds parser recursion, is CST nesting depth bounded for parser-produced trees, leaving the recursive-Drop and recursive-Debug overflows reachable only via manual construction (not an untrusted-input attack surface)?

**Answer: No. Left recursion (seed-grow) produces CST depth proportional to input length at constant `apply` depth. Both overflows remain reachable from untrusted input after the depth limit lands. Keep both fixes.**

## 1. The premise holds only for right-recursive nesting

For right-recursive/nesting rules (e.g. the planned `nest := %"(" . inner:nest . %")" | leaf:num`), `apply` depth tracks CST depth one-to-one, so `max_depth = 1000` caps parser-produced CST depth at ~1000 — trivially safe for both Drop and Debug. If this were the only tree-deepening construct, the user's argument would be correct.

Loop quantifiers (`+`/`*`) are also not a vector: generated repetition loops `push_child` into a single node's `children` Vec (e.g. the trivia loops, `tests/rust_parser_fixture/src/parser.rs:254`, `parser.rs:815`) — width, not depth.

## 2. Counterexample: left recursion builds unbounded depth iteratively

The seed-grow algorithm deepens the CST one level **per loop iteration**, not per recursion level. Mechanism, fully verified in code:

1. `grow_seed` is a `loop` re-invoking the rule body at the same start position (`crates/fltk-parser-core/src/memo.rs:395-421`). The parse-depth-limit design states this itself: "`grow_seed`'s loop iterations are iteration, not recursion — one uncounted rule-body frame per iteration, constant" (`docs/adr/2026/06/11-parse-depth-limit/design.md` §1), and "`expr`/`lval`/`rval`/`rec_via_sub` are left-recursive (seed-grow handles them iteratively at constant depth)" (§5).
2. The depth guard counts only concurrent `apply` entries (`memo.rs:159-169`); the counter is decremented on each `apply` exit, so it returns to baseline after every growth iteration. Iteration count is unlimited.
3. Each growth iteration of `expr := lhs:expr . "+" . rhs:atom | atom:atom` (`fltk/fegen/test_data/rust_parser_fixture.fltkg:32`) re-enters `apply__parse_expr` for the `lhs` item (`parser.rs:453-455`), which is a **cache hit**: Step 2 returns an Arc clone of the previously grown `Shared<Expr>` (`memo.rs:253-257`). That handle is embedded as a child of the new node via `result.append_lhs(item0.result)` (`parser.rs:468-470`).

So parsing `"1+1+1+…+1"` with M terms yields a left-leaning `Expr` chain of CST depth ~M while `apply` depth peaks at ~3 (`expr` → `atom`, plus the growth-head entry) — far below any limit. Depth is bounded by **input length**, not `max_depth`. At ~2 bytes per level, a ~200 KiB input yields ~100 000 levels — the exact depth the Debug/Drop design's tests use to overflow an 8 MiB stack (`design.md` §Test plan, depth rationale). Left-recursive expression rules are the canonical grammar idiom (the fixture grammar has three: `expr`, `lval`/`rval`, `rec_via_sub`), so this is the common case, not a corner.

## 3. Per-concern conclusions

**Drop — real untrusted-input attack surface, post-limit.** Parse a long `"1+1+…"` input (depth limit never trips, parse succeeds and is *correct*); the resulting tree's teardown recurses through drop glue one frame set per level → SIGSEGV. Teardown is unavoidable (end of scope, Python handle GC, parser drop releasing its memo caches, which hold `Shared` clones of every grown intermediate). No downstream code choice avoids it.

**Debug — real untrusted-input attack surface, post-limit, conditional on caller behavior.** Same parsed tree; any `{:?}` on the root (`assert_eq!` failure path, `dbg!`, logging) recurses per level → SIGSEGV. Conditional on the downstream app formatting a node, but that is ordinary, encouraged usage — not manual CST construction.

**Subsumption: parse-depth-limit does not subsume any part of rust-cst-debug-depth.** It bounds *parser stack* consumption; it does not bound parser-produced *CST depth*.

## 4. Collateral findings

- `exploration.md` §5 reaches the right conclusion ("does not eliminate either exposure") via a wrong supporting claim: "a successfully parsed tree could have node-nesting depth up to ~N [the limit]". False for left-recursive rules — and the truth is *stronger* for the fix (depth is unbounded, not merely N). The design's root-cause sentence ("The parse-depth-limit work does not eliminate either exposure (`exploration.md` §5)") is correct but cites the flawed argument; if revised, cite the left-recursion mechanism above instead.
- Optional test-plan strengthening (not required for the design to stand): add a parser-produced deep-tree case — parse `"1" + "+1"*100_000` with the default `max_depth`, assert the parse succeeds and the tree drops cleanly. This pins reachability-via-parsing in CI rather than relying on manually built chains. The existing manual-construction tests remain valid (they isolate each fix from parser behavior).

## 5. Recommendation

**Keep both.** Order of implementation (parse-depth-limit first) is unaffected; the two designs address disjoint stack consumers: parse-time recursion vs. post-parse teardown/formatting recursion over trees whose depth the parse limit cannot bound.
