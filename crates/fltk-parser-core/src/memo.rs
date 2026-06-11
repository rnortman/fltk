//! Port of `fltk/fegen/pyrt/memo.py` — packrat memoizer with left-recursion (seed-grow).
//!
//! The algorithm is the Warth/Douglass/Millstein seed-grow variant.
//! Key structural change from Python: Python mutates a `Poison` object aliased between
//! stack frames (memo.py:112-122, 206-226). Rust instead keeps poison/recursion info
//! *inside* the cache entry and re-fetches the entry after the rule call returns.
//! The algorithm is observably equivalent; ownership is safe.
//!
//! All Python `assert` statements are ported as `assert!` (not `debug_assert!`) —
//! they are cheap algorithm invariants that should fire loudly on any violation.
//! The one documented reachable panic is the untested corner case (memo.py:181-187).

use std::collections::{HashMap, HashSet};

/// Result of a successful parser rule application.
///
/// Mirrors `ApplyResult` in `memo.py:68-74`.
#[derive(Clone, Debug, PartialEq)]
pub struct ApplyResult<T> {
    pub pos: i64,
    pub result: T,
}

/// Recursion bookkeeping for the seed-grow algorithm (Python: "head").
///
/// Mirrors `RecursionInfo` in `memo.py:27-41`.
#[derive(Debug, Clone)]
pub struct RecursionInfo {
    /// ID of the rule that first created the recursion (head and tail of the cycle).
    pub rule_id: u32,
    /// Rules involved in the recursive cycle other than the head/tail.
    pub involved: HashSet<u32>,
    /// Rules still due for a cache bypass during this growth cycle.
    pub eval_set: HashSet<u32>,
}

/// Contents of a memo-cache entry.
///
/// Collapses Python's untyped `Poison | ResultType | None` union (memo.py:61):
/// - `Poison(None)` → `Poison(None)`: a plain poison (no recursion detected yet).
/// - `Poison(Some(ri))` → `Poison(Some(RecursionInfo))`: poison after recursion detected.
/// - A successful result → `Value(T)`.
/// - A failure → `Failure`.
#[derive(Clone, Debug)]
pub enum MemoResult<T> {
    Poison(Option<RecursionInfo>),
    Value(T),
    Failure,
}

/// A single memo cache entry.
///
/// Mirrors `MemoEntry` in `memo.py:59-63`.
#[derive(Clone, Debug)]
pub struct MemoEntry<T> {
    pub result: MemoResult<T>,
    /// The final position after this rule completed (or the start position on failure).
    pub final_pos: i64,
}

/// Per-rule memo cache type alias.
pub type Cache<T> = HashMap<i64, MemoEntry<T>>;

/// Default rule-application depth limit. Configurable via `PackratState::set_max_depth`.
///
/// Depth counts concurrent `apply` entries (cache hits included; they add ~2 transient
/// frames and return immediately). 1000 levels × ~5-7 native frames/level ≈ 5 000-7 000
/// frames — well within an 8 MiB main-thread stack. **This default is sized for an ~8 MiB
/// stack and ~5-7 native frames per rule application.** Callers on smaller thread stacks
/// (Rust's default spawned threads use 2 MiB; async-runtime worker threads vary) or with
/// grammars that have deep per-rule call structure must lower `max_depth` proportionally
/// or size the stack accordingly. Cargo-test threads have 2 MiB; do not test the default
/// limit from `cargo test` — use pytest (see design §6).
pub const DEFAULT_MAX_DEPTH: u32 = 1000;

/// Mutable state for the packrat memoizer, held by the generated `Parser`.
///
/// `invocation_stack` is `pub` for direct access; all other fields are private.
/// `Default` (manual, so `max_depth` defaults to `DEFAULT_MAX_DEPTH` rather than `0`)
/// is the primary construction path; `with_max_depth` is a convenience constructor.
/// Struct-literal construction is impossible, so adding private fields never breaks
/// existing callers.
///
/// # Panic and `PanicException` safety
///
/// Memo-invariant panics inside `apply_inner` skip the `depth` decrement (they abort the
/// parse state). In the Python binding layer, pyo3 converts Rust panics to
/// `PanicException` *before* returning control to Python — a distinct exception type from
/// `RecursionError`. If a Python caller catches `PanicException` and continues to use the
/// same `PyParser`, the depth counter will be stale. Treat any `PanicException` from a
/// parser call as "instance is spent" — construct a fresh parser.
#[derive(Debug)]
pub struct PackratState {
    /// Active rule invocation stack (rule IDs, innermost last).
    pub invocation_stack: Vec<u32>,
    /// Active growth cycles keyed by start position.
    recursions: HashMap<i64, RecursionInfo>,
    /// Maximum concurrent memoized rule applications allowed.
    /// Set this before parsing via `set_max_depth`. Default: `DEFAULT_MAX_DEPTH`.
    max_depth: u32,
    /// Current concurrent `apply` entry count (private; managed by `apply` guard).
    depth: u32,
    /// Sticky flag: once set, every subsequent `apply` returns `None` immediately.
    /// Read via `depth_exceeded()`. Never cleared — a parser instance with this flag
    /// set is spent; construct a fresh one.
    depth_exceeded: bool,
}

impl Default for PackratState {
    fn default() -> Self {
        Self {
            invocation_stack: Vec::new(),
            recursions: HashMap::new(),
            max_depth: DEFAULT_MAX_DEPTH,
            depth: 0,
            depth_exceeded: false,
        }
    }
}

impl PackratState {
    /// Create a `PackratState` with a specific maximum depth.
    ///
    /// Equivalent to `Default::default()` followed by `set_max_depth(max_depth)`.
    pub fn with_max_depth(max_depth: u32) -> Self {
        Self { max_depth, ..Self::default() }
    }

    /// Set the maximum concurrent rule-application depth. Call before parsing.
    pub fn set_max_depth(&mut self, max_depth: u32) {
        self.max_depth = max_depth;
    }

    /// Return the current maximum rule-application depth limit.
    pub fn max_depth(&self) -> u32 {
        self.max_depth
    }

    /// Returns `true` if a depth limit was exceeded during parsing.
    ///
    /// Sticky: once set, every `apply` on this instance returns `None` immediately.
    /// Check this after every parse; discard the result if set (§2 contract — a result
    /// produced with the flag set is not the parse the grammar defines; see design).
    pub fn depth_exceeded(&self) -> bool {
        self.depth_exceeded
    }
}

/// Apply a memoized parser rule with left-recursion support and depth-limit guard.
///
/// Generic free function (not a method on the parser) to avoid the triple-`&mut self`
/// borrow that makes the Python call shape (`self.packrat.apply(self.parse_X, ...)`)
/// uncompilable in Rust. Every access to `state`/`cache` re-borrows through `parser`,
/// so `rule` can recurse into `apply` freely.
///
/// # Stack-depth limit
///
/// `apply` → `rule` → `apply` recursion depth is bounded by `PackratState::max_depth`
/// (default `DEFAULT_MAX_DEPTH`). Exceeding the limit sets the sticky
/// `PackratState::depth_exceeded` flag and returns `None`. **Callers must check
/// `depth_exceeded()` after parsing and discard the result if set** — a result produced
/// with the flag set is not the parse the grammar defines (e.g. a left-recursive rule's
/// seed can surface as `Some` even when growth iterations were depth-rejected). See the
/// design doc for the full contract.
///
/// Parameters:
/// - `parser`: the generated `Parser` struct (or toy parser in tests).
/// - `rule_id`: numeric rule ID (unique across the grammar).
/// - `pos`: codepoint position at which to apply the rule.
/// - `state`: projector `|p| &mut p.packrat` (non-capturing → `fn` pointer).
/// - `cache`: projector `|p| &mut p.cache_rule_x` (non-capturing → `fn` pointer).
/// - `rule`: the rule body `|p, pos| p.parse_rule_x(pos)` (non-capturing → `fn` pointer).
///
/// `T: Clone` because cache hits clone the stored result — for generated code
/// `T = Shared<NodeT>`, so a hit is an Arc clone, reproducing Python's object-sharing.
///
/// # Lockstep-regeneration note
///
/// Generated parsers must be regenerated when crossing a `fltk-parser-core` version
/// boundary. A pre-limit generated parser compiled against this core version enforces
/// `DEFAULT_MAX_DEPTH` with no way for the caller to observe or configure it.
pub fn apply<P, T: Clone>(
    parser: &mut P,
    rule_id: u32,
    pos: i64,
    state: fn(&mut P) -> &mut PackratState,
    cache: fn(&mut P) -> &mut Cache<T>,
    rule: fn(&mut P, i64) -> Option<ApplyResult<T>>,
) -> Option<ApplyResult<T>> {
    {
        let st = state(parser);
        if st.depth_exceeded || st.depth >= st.max_depth {
            st.depth_exceeded = true;
            return None;
        }
        st.depth += 1;
    }
    let result = apply_inner(parser, rule_id, pos, state, cache, rule);
    state(parser).depth -= 1;
    result
}

fn apply_inner<P, T: Clone>(
    parser: &mut P,
    rule_id: u32,
    pos: i64,
    state: fn(&mut P) -> &mut PackratState,
    cache: fn(&mut P) -> &mut Cache<T>,
    rule: fn(&mut P, i64) -> Option<ApplyResult<T>>,
) -> Option<ApplyResult<T>> {
    let start_pos = pos;

    // Step 1: Recall (memo.py:158-204).
    // Check whether a growth cycle is active at this position.
    let has_recursion = state(parser).recursions.contains_key(&start_pos);

    if has_recursion {
        // Growth cycle active at this position.
        let has_cache_entry = cache(parser).contains_key(&start_pos);
        let is_head_or_involved = {
            let rec = &state(parser).recursions[&start_pos];
            rec.rule_id == rule_id || rec.involved.contains(&rule_id)
        };

        if !has_cache_entry && !is_head_or_involved {
            // memo.py:181-187: untested corner case. Fail loudly.
            panic!("Untested corner case; see source code for more information.");
        }
        if !has_cache_entry {
            // has_cache_entry == false but is_head_or_involved == true: growth cycle
            // is active and this rule is the head/involved, but there is no cache entry.
            // This is an invariant violation distinct from the above untested corner case.
            panic!(
                "memo invariant: growth-cycle rule is head/involved but has no cache entry"
            );
        }

        let rule_in_eval_set = {
            let rec = &state(parser).recursions[&start_pos];
            rec.eval_set.contains(&rule_id)
        };

        if rule_in_eval_set {
            // Cache bypass: this rule hasn't run in the current growth cycle yet.
            // Remove from eval_set, call the rule, update the cache entry.
            state(parser)
                .recursions
                .get_mut(&start_pos)
                .unwrap()
                .eval_set
                .remove(&rule_id);

            let call_result = rule(parser, start_pos);
            let entry = cache(parser).get_mut(&start_pos).unwrap();
            match call_result {
                Some(ApplyResult { pos: new_pos, result }) => {
                    entry.result = MemoResult::Value(result);
                    entry.final_pos = new_pos;
                }
                None => {
                    entry.result = MemoResult::Failure;
                    entry.final_pos = start_pos;
                }
            }
        }

        // Fall through to cache-entry dispatch below.
    }

    // Step 2: Cache-entry dispatch (memo.py:96-109).
    if let Some(entry) = cache(parser).get(&start_pos) {
        match &entry.result {
            MemoResult::Poison(_) => {
                // We hit a cache poison. Assert final_pos invariant then set up recursion.
                let final_pos = entry.final_pos;
                assert!(
                    final_pos == start_pos,
                    "memo invariant: poison entry final_pos must equal start_pos"
                );
                setup_recursion(parser, rule_id, start_pos, state, cache);
                // Fail here to let another alternative generate the seed parse.
                return None;
            }
            MemoResult::Value(v) => {
                let pos = entry.final_pos;
                let result = v.clone();
                return Some(ApplyResult { pos, result });
            }
            MemoResult::Failure => {
                return None;
            }
        }
    }

    // Step 3: Miss (memo.py:111-122).
    // Insert poison entry, run the rule, pop the stack.
    cache(parser).insert(
        start_pos,
        MemoEntry { result: MemoResult::Poison(None), final_pos: start_pos },
    );
    state(parser).invocation_stack.push(rule_id);
    let call_result = rule(parser, start_pos);
    let popped = state(parser).invocation_stack.pop();
    assert!(popped == Some(rule_id), "memo invariant: invocation_stack.pop() must return rule_id");

    // Re-fetch the entry to read the (possibly updated) poison.
    // Python asserts `memo.result is poison` here; Rust asserts the entry is still Poison.
    let recursion_info = match cache(parser).get(&start_pos) {
        Some(entry) => match &entry.result {
            MemoResult::Poison(ri) => ri.clone(),
            _ => panic!("memo invariant: cache entry must still be Poison after rule call"),
        },
        None => panic!("memo invariant: cache entry must exist after rule call"),
    };

    let new_pos = call_result.as_ref().map(|r| r.pos).unwrap_or(start_pos);

    // Step 4: No recursion detected (memo.py:131-136).
    if recursion_info.is_none() {
        let return_value = call_result.as_ref().map(|r| r.result.clone());
        let entry = cache(parser).get_mut(&start_pos).unwrap();
        entry.final_pos = new_pos;
        entry.result = match call_result {
            Some(ApplyResult { result, .. }) => MemoResult::Value(result),
            None => MemoResult::Failure,
        };
        return return_value.map(|result| ApplyResult { pos: new_pos, result });
    }

    // Step 5: Recursion detected (memo.py:144-156).
    let ri = recursion_info.unwrap();
    assert!(ri.rule_id == rule_id, "memo invariant: recursion head must be current rule");

    // Store the seed result.
    let entry = cache(parser).get_mut(&start_pos).unwrap();
    entry.final_pos = new_pos;
    entry.result = match call_result {
        Some(ApplyResult { result, .. }) => MemoResult::Value(result),
        None => MemoResult::Failure,
    };

    // If the seed parse failed, nothing to grow.
    if matches!(cache(parser).get(&start_pos).unwrap().result, MemoResult::Failure) {
        return None;
    }

    // Grow the seed.
    state(parser).invocation_stack.push(rule_id);
    let grow_result = grow_seed(parser, rule_id, start_pos, ri, state, cache, rule);
    let popped2 = state(parser).invocation_stack.pop();
    assert!(popped2 == Some(rule_id), "memo invariant: invocation_stack.pop() must return rule_id");
    Some(grow_result)
}

/// Set up left-recursion bookkeeping when a poison cache entry is encountered.
///
/// Port of `Packrat._setup_recursion` (memo.py:206-226).
///
/// Walks the invocation stack top-down collecting rule IDs until hitting `rule_id`,
/// then updates the poison's `RecursionInfo` in the cache entry.
/// Reading the stack fully before touching the cache replaces Python's interleaved
/// access; the two are observably equivalent.
fn setup_recursion<P, T: Clone>(
    parser: &mut P,
    rule_id: u32,
    start_pos: i64,
    state: fn(&mut P) -> &mut PackratState,
    cache: fn(&mut P) -> &mut Cache<T>,
) {
    // Walk the invocation stack backward to collect involved rules.
    let involved: HashSet<u32> = {
        let stack = &state(parser).invocation_stack;
        assert!(!stack.is_empty(), "memo invariant: invocation_stack must be non-empty");
        let mut idx = stack.len() as isize - 1;
        let mut involved = HashSet::new();
        while stack[idx as usize] != rule_id {
            involved.insert(stack[idx as usize]);
            idx -= 1;
            assert!(idx >= 0, "memo invariant: rule_id must appear in invocation_stack");
        }
        involved
    };

    // Update the poison's RecursionInfo in the cache entry.
    let entry = cache(parser).get_mut(&start_pos).unwrap();
    match &mut entry.result {
        MemoResult::Poison(ri_opt) => match ri_opt {
            None => {
                *ri_opt = Some(RecursionInfo {
                    rule_id,
                    involved,
                    eval_set: HashSet::new(),
                });
            }
            Some(ri) => {
                assert!(
                    ri.rule_id == rule_id,
                    "memo invariant: existing RecursionInfo must have same rule_id"
                );
                // Python re-walks and re-adds on every poison hit; sets dedupe.
                ri.involved.extend(involved);

            }
        },
        _ => panic!("memo invariant: cache entry must be Poison in setup_recursion"),
    }
}

/// Grow a recursive seed until it stops growing.
///
/// Port of `Packrat._grow_seed` (memo.py:228-257).
///
/// Moves the `RecursionInfo` into `state.recursions[start_pos]` to signal the growth
/// cycle, then repeatedly re-invokes the rule until the result no longer improves.
/// Cleans up `recursions[start_pos]` on exit.
fn grow_seed<P, T: Clone>(
    parser: &mut P,
    _rule_id: u32,
    start_pos: i64,
    recursion: RecursionInfo,
    state: fn(&mut P) -> &mut PackratState,
    cache: fn(&mut P) -> &mut Cache<T>,
    rule: fn(&mut P, i64) -> Option<ApplyResult<T>>,
) -> ApplyResult<T> {
    state(parser).recursions.insert(start_pos, recursion);
    loop {
        // Reset eval_set to involved for this growth iteration.
        {
            let ri = state(parser).recursions.get_mut(&start_pos).unwrap();
            ri.eval_set = ri.involved.clone();
        }

        let call_result = rule(parser, start_pos);
        let entry = cache(parser).get_mut(&start_pos).unwrap();

        let (new_pos, has_result) = match &call_result {
            Some(r) => (r.pos, true),
            None => (start_pos, false),
        };

        if !has_result || new_pos <= entry.final_pos {
            // Growth stalled: no result or no improvement (memo.py:248).
            break;
        }

        // Store the improved result.
        // Safety: we only reach here when has_result == true (call_result is Some).
        // The break condition above fires when !has_result || new_pos <= entry.final_pos,
        // so reaching this line guarantees has_result && new_pos > entry.final_pos.
        entry.final_pos = new_pos;
        entry.result = MemoResult::Value(call_result.unwrap().result);
    }

    // Clean up: remove the growth cycle marker.
    state(parser).recursions.remove(&start_pos);

    // Assert and return the final result.
    let entry = cache(parser).get(&start_pos).unwrap();
    assert!(
        matches!(entry.result, MemoResult::Value(_)),
        "memo invariant: cache entry must hold Value after grow_seed"
    );
    let (final_pos, result) = match &entry.result {
        MemoResult::Value(v) => (entry.final_pos, v.clone()),
        _ => unreachable!(),
    };
    ApplyResult { pos: final_pos, result }
}
