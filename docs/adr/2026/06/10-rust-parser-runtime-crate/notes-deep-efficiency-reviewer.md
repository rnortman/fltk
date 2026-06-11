# Efficiency review — fltk-parser-core runtime crate

Reviewed: d23d1df..1521372 (HEAD 1521372a8313ad9c61503e43db9d98cd23c8c1a0).
Scope: `crates/fltk-parser-core/{src,tests}`, `crates/fltk-cst-core/src/span.rs`, Makefile/Cargo wiring.
Style note: concise, precise, complete, unambiguous; no padding.

`apply()` is the per-(rule, pos) hot path of every generated parser; `consume_*` is the per-terminal-attempt hot path. Findings weighted accordingly.

## efficiency-1: dead `RecursionInfo` clone fed to an unused parameter

`crates/fltk-parser-core/src/memo.rs:165-170` and `:261`.

In the poison-dispatch branch, the code re-fetches the cache entry it already holds and clones the `Option<RecursionInfo>` (two `HashSet<u32>` allocations + copies) solely to pass it as `setup_recursion`'s last argument — whose name is `_existing_ri` and which is never read. `setup_recursion` re-reads the entry itself via `get_mut` (`:278`).

**Consequence**: one redundant HashMap lookup plus two HashSet clones on every poison hit — i.e., every left-recursion detection event and every re-entrant hit during seed growth. Pure waste; scales with how left-recursive the grammar is.

Fix: delete the `recursion_info` extraction block at `:165-169` and the `_existing_ri` parameter.

## efficiency-2: cache-miss path does 4-5 HashMap lookups + clones where design says "take"

`crates/fltk-parser-core/src/memo.rs:185-244` (steps 3-5).

On every cache miss (the dominant operation — first evaluation of each (rule, pos)):

1. `insert` poison (`:187`) — lookup 1.
2. Re-fetch `get` and **`ri.clone()`** (`:198-204`) — lookup 2. Design §2.5 step 3 says "**take** the `Option<RecursionInfo>` out of it"; the implementation clones instead. On the recursion-detected path that clones two HashSets which the seed-store at `:227-232` immediately overwrites anyway.
3. Step 4: `get_mut` (`:210`) — lookup 3; then `get` **again** (`:216`) to clone the value back out — lookup 4.
4. Step 5 (recursion head): `get_mut` (`:227`), then `get` (`:235`) just to test `Failure` — information already available from `call_result.is_none()`.

All of steps 2-4 can be one `get_mut` after the rule call: take `ri` out of the poison via `Option::take` (through `match &mut entry.result`), set `final_pos`/`result` in place, and clone the return value from the same borrow. 4-5 lookups → 2 (insert + get_mut), and the HashSet clones disappear.

**Consequence**: 2-3 extra hash lookups per memoized rule invocation across the entire parse — per-parse CPU cost on the hottest loop in the system, paid by every downstream generated parser forever. Cheap to fix now; load-bearing API is unchanged.

Same pattern in step 1's growth branch (`:105-139`): `recursions` is probed four times (`contains_key` `:105`, index `:111`, index `:124`, `get_mut` `:131`) and `cache` twice. A single `get`/`get_mut` per map suffices. This branch runs once per involved rule per growth iteration — rarer, but the fix falls out of the same restructure.

## efficiency-3: `grow_seed` clones an owned `RecursionInfo` it could move

`crates/fltk-parser-core/src/memo.rs:318`.

`state(parser).recursions.insert(start_pos, recursion.clone());` — `recursion` is passed by value and never used again. The clone copies both HashSets.

**Consequence**: two HashSet allocations per growth-cycle start. Small, but strictly zero-benefit.

Fix: `insert(start_pos, recursion)`.

## efficiency-4: `line_ends` init binary-searches per newline when the index is free

`crates/fltk-parser-core/src/terminalsrc.rs:181-197`.

The lazy `line_ends` builder runs `char_indices()` and, for each `\n`, does a `partition_point` binary search over `cp_to_byte` to recover the codepoint index. But `char_indices().enumerate()` yields the codepoint index directly (`(cp_idx, (byte_idx, ch))`); no search is needed:

```rust
text.chars().enumerate().filter(|(_, c)| *c == '\n').map(|(i, _)| i as i64)
```

**Consequence**: O(L·log N) instead of O(N) on first `pos_to_line_col` call (every error-message format). For large inputs this is the difference between a single scan and a scan plus a binary search per line. The fix is also less code.

## efficiency-5: `cp_to_byte` over-reserves up to ~4x for multibyte input

`crates/fltk-parser-core/src/terminalsrc.rs:59`.

`Vec::with_capacity(text.len() + 1)` reserves one slot per **byte**; the vec holds one entry per **codepoint**. For heavily multibyte text (codepoints ≈ bytes/3 for CJK) up to ~3/4 of the reservation is dead capacity that persists for the `TerminalSource`'s lifetime — e.g. a 10 MB CJK source reserves ~80 MB for a table needing ~27 MB. The design doc's memory note (§3, 8 B/codepoint) accounts for entries, not slack.

**Consequence**: retained-memory overhead proportional to input size for non-ASCII sources, alive for the whole parse.

Fix: `cp_to_byte.shrink_to_fit()` after the build (one realloc, only when slack exists), or keep the comment honest about the slack. ASCII input is unaffected either way.

## Not flagged (checked, fine)

- `consume_literal`/`consume_regex`: allocation-free, single table index, no per-call passes over the literal beyond the pairwise compare. Good.
- `ErrorTracker::fail_*`: `ParseContext` is `Copy`, failure path allocation-free except the replace-case `vec![ctx]` (inherent). Good.
- `build_expected_block` / `py_repr_str`: O(n²) `contains` dedup, per-line `format!`, `to_owned` rule names — all on the format-one-error-message cold path with tiny n. Not worth churn.
- `fn`-pointer projectors in `apply` (indirect calls, shared monomorphization): deliberate, documented design tradeoff (design §2.5).
- `grow_seed`'s per-iteration `eval_set = involved.clone()`: algorithm-required, matches Python.
- `OnceLock` for `line_ends`: correct lazy/`Sync` choice, mirrors Python laziness.
