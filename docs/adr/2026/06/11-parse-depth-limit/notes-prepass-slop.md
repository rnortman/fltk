## slop-1

**File:** `crates/fltk-parser-core/src/memo.rs` (PackratState struct, ~line 94–103)

**Quote:**
```
    /// Maximum concurrent memoized rule applications allowed.
    /// Set this before parsing. Default: `DEFAULT_MAX_DEPTH`.
    pub max_depth: u32,
```

**What's wrong:** `max_depth` is `pub` on the struct while all other mutable fields are private. The doc comment on `PackratState` was updated to say "per-field public accessors are the only external construction/mutation path — struct-literal construction is impossible, so adding fields never breaks existing callers." But `max_depth` being `pub` means callers can set it directly via `state.packrat.max_depth = N` in addition to the `Parser::set_max_depth` accessor, and adding any field to `PackratState` would still be non-breaking only if nothing relied on struct-literal initialization (which `Default` already prevents). The pub field is not itself broken, but the comment overstates the encapsulation. It also means the generated parser exposes `parser.packrat.max_depth` as a direct mutation path bypassing `set_max_depth` — inconsistent with stated encapsulation intent.

**Consequence:** Comment promises encapsulation that the `pub` field does not deliver. A reviewer reading the doc comment against the field declaration will notice the mismatch and flag it. Minor but looks sloppy.

**Fix:** Either make `max_depth` private and add a setter (already done at the `Parser` level), or remove the encapsulation claim from the comment. The latter is simpler since generated parsers already wrap it through `set_max_depth`.

---

## slop-2

**File:** `crates/fltk-parser-core/tests/memo_toy.rs` (T4 test body, lines ~406–418)

**Quote:**
```rust
    // max_depth=4: enough to parse `1` at depth ~2, but the growth step into `(((9)))`
    // (which needs depth ~4 more entries) will hit the limit.
    let mut p = DepthParser::new(input, 4);
    let result = p.apply__nest_sum(0);
    assert!(p.packrat.depth_exceeded(), ...);
    assert!(result.is_some(), ...);
    let ApplyResult { pos, .. } = result.unwrap();
    assert_eq!(pos, 1, "seed was `1` at pos=1");
```

**What's wrong:** The test comment says "needs depth ~4 more entries" with no rigorous accounting. The test relies on a specific `max_depth=4` value being simultaneously above the seed-parse depth and below the growth-iteration depth, but the exact depth accounting for `apply__nest_sum`+`apply__nest_sum`+`apply__nest` inside a left-recursive growth step is not spelled out. If `apply` is entered once for `nest_sum` at pos=0 (depth 1), re-entered for the recursive call inside `grow_seed` (depth 2), and then `nest` on `(((9)))` needs ~3 additional frames, a `max_depth` of 4 seems tight. If the counts shift — e.g. due to a future refactor of how `grow_seed` calls `rule` — the test could silently stop pinning the T4 shape and start passing for the wrong reason (growth succeeds, no flag set). The test doc comment acknowledges this is intentionally approximate ("~4"), but that approximation is not verified or bounded.

**Consequence:** T4 is the only test pinning the §2 truncated-Some premise; if it starts passing vacuously, the contract goes untested. This will make reviewers uneasy about the test's reliability.

**Fix:** Add a comment or assertion that explicitly verifies `depth_exceeded` is set AND `result.is_some()` AND `pos < input.len()` (i.e., the parse did not consume the full input). The last assertion distinguishes "growth was depth-rejected and seed was returned" from "nest_sum fully parsed" more concretely than relying on `pos==1` alone. Or tighten the depth accounting with an explicit note explaining why 4 is the right threshold.

---

## slop-3

**File:** `crates/fltk-parser-core/tests/memo_toy.rs` (T3 test, ~line 383)

**Quote:**
```rust
    // Clear the caches so there's no stale Failure entry for pos 0.
    p.cache_nest.clear();
    p.cache_nest_sum.clear();
```

**What's wrong:** The test clears caches between uses of the same `DepthParser` instance after triggering `depth_exceeded`, then checks that a trivial subsequent `apply` still returns `None`. The cache-clearing is correct for the intent (avoiding a cached `None` hit that returns early for an unrelated reason), but the test comment explains this incompletely — a cache `None` entry would still return `None`, so the assertion `result.is_none()` would appear to pass even if the sticky flag were not working. The only thing the sticky-flag test is actually distinguishing from "cached failure" is the `depth_exceeded()` assertion on line 388. If a reader misses that nuance, the test's value is overstated. The cache-clear comment says "stale Failure entry" but does not explain that the test distinguishes flag-based rejection from cache-based rejection via the `depth_exceeded()` assertion — not via `result`.

**Consequence:** The test looks weaker than it is to a careful reader; they may wonder if it actually tests stickiness or just cache behavior. Not a functional bug, but a readability issue that will prompt review questions.

**Fix:** Add a brief comment: "The cache-clear ensures the subsequent `apply` is not short-circuited by a cached `None`; stickiness is proven by `depth_exceeded()` remaining set, not by `result` alone."

---

No other LLM-tell comments, silent fallbacks, or obvious workarounds found in the diff.
