# Design: parse depth limit (resolves `apply-depth-limit` + `parser-depth-limit`)

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Requirements: `request.md` (this dir). Exploration: `exploration-apply-depth-limit.md`, `exploration-parser-depth-limit.md` (this dir).

## Context / root cause

Generated Rust parsers recurse through one chokepoint: every cross-rule call is `apply__parse_X` → `apply` (`crates/fltk-parser-core/src/memo.rs:102`) → `parse_X` → alt/item helpers → `apply__parse_Y`. Depth is proportional to input nesting, unbounded; intra-rule helpers add only constant frames per level (~5 native frames/level). Stack overflow in the cdylib is SIGSEGV — an uncatchable process abort, strictly worse than the Python backend's catchable `RecursionError`. Exploration verified: all recursion flows through `apply`; one runtime counter suffices; no generated-wrapper counter needed (`exploration-parser-depth-limit.md` §"Call graph").

No configuration or error channel exists today: `PackratState::default()` is the only construction path (`memo.rs:68`), generated `Parser` has no config fields (`gsm2parser_rs.py:329-390`), and `apply` returns `Option<ApplyResult<T>>` with `None` meaning only "didn't match".

## Approach

### 1. Runtime: counter + limit + flag in `PackratState` (`memo.rs`)

```rust
pub const DEFAULT_MAX_DEPTH: u32 = 1000;

#[derive(Debug)]
pub struct PackratState {
    pub invocation_stack: Vec<u32>,
    recursions: HashMap<i64, RecursionInfo>,
    /// Maximum concurrent memoized rule applications. Public: set before parsing.
    pub max_depth: u32,
    depth: u32,           // private: current concurrent apply entries
    depth_exceeded: bool, // private: sticky; read via depth_exceeded()
}

impl PackratState {
    pub fn depth_exceeded(&self) -> bool { self.depth_exceeded }
}
```

`Default` becomes a manual impl (currently derived) so `max_depth` defaults to `DEFAULT_MAX_DEPTH`, not `0`. Struct-literal construction stays impossible (private fields), so adding fields breaks no one. `lib.rs` re-exports `DEFAULT_MAX_DEPTH`.

**Guard placement**: rename the current `apply` body to a private `apply_inner` (body unchanged); `apply` becomes a thin guard with the existing public signature:

```rust
pub fn apply<P, T: Clone>(parser, rule_id, pos, state, cache, rule) -> Option<ApplyResult<T>> {
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
```

Why this shape:

- **Signature unchanged** — previously generated parser files keep compiling against the new core (additive struct fields only). Putting the flag in `ErrorTracker` (request's suggested option) would force a seventh projector parameter onto `apply`, breaking every already-generated `.rs` file; `PackratState` is the channel `apply` already has. Decision: flag lives in `PackratState`. Compile compatibility is *not* behavior compatibility for the mixed-version case — see "Versioning" below.
- **Counts every `apply` entry** (cache hits included). Hits add ~2 transient frames and return immediately; counting them is marginally conservative and keeps the guard branch-free.
- **Covers all recursion sites without enumeration.** The Step-3 `rule()` call (`memo.rs:201`), the eval-set bypass `rule()` call (`memo.rs:152`), and `grow_seed`'s `rule()` call (`memo.rs:332`) each occur inside an already-counted `apply` frame, and every descent below them re-enters `apply`. `grow_seed`'s loop iterations are iteration, not recursion — one uncounted rule-body frame per iteration, constant.
- **Check precedes any cache write.** A depth-rejected `apply` writes no poison/Failure entry, so no false memoization at the rejection point itself.
- **Single decrement point**; internal control flow of `apply_inner` never touches the counter. The invariant-violation `panic!`s inside `apply_inner` skip the decrement — irrelevant, since those panics abandon the parser state entirely.

### 2. Semantics: sticky flag; flag outranks the parse result

`depth_exceeded` is **sticky**: once set, every subsequent `apply` on that parser instance returns `None` immediately. Rationale:

- **Cache pollution.** Rules *below* the limit whose sub-rules were depth-rejected get memoized as `Failure` — wrong if the same (rule, pos) were later reached via a shallower path. Stickiness makes the whole parse fail fast, so polluted entries are never trusted for a "real" answer. This mirrors Python, where `RecursionError` propagates and aborts the entire parse (the Python parser's caches are equally polluted if a caller catches and reuses — we do no worse, and we document not to reuse).
- **Truncated success.** Depth rejection can still surface as a `Some` overall result. Once the flag is set, no *new* `apply` returns `Some` (the sticky check precedes even cache lookup), but frames already in flight can complete: (a) `grow_seed` treats a depth-rejected growth iteration as "growth stalled" and returns the previously stored seed; (b) an in-flight alternative can skip a depth-rejected optional (`?`/`*`) item and finish on terminal consumption alone (`consume_literal`/`consume_regex` do not pass through `apply`). In both cases the result is *not* the parse the grammar defines. Therefore: **callers must consult `depth_exceeded()` after parsing and discard the result if set, regardless of `Some`/`None`.** The generated bindings enforce this (§4); the generated `Parser` docs state it for Rust-native callers.

A parser instance with `depth_exceeded` set is spent; construct a fresh one. No reset method (non-goal: keep surface minimal; parsers are already effectively single-parse objects).

`max_depth == 0` rejects the very first `apply` (guard uses `>=`). Degenerate but well-defined; no special-casing.

### Versioning: old-generated parser + new core is a deliberate behavior break

A previously generated parser linked against the new core (out-of-tree consumer upgrading `fltk-parser-core` without regenerating) gets `DEFAULT_MAX_DEPTH` enforcement with **none** of the new surfacing: no `depth_exceeded()` accessor, no setter, header docs still describing abort behavior. For inputs nested past 1000 but under the native-overflow threshold (far above 1000 at ~5-7 frames/level on an 8 MiB stack — such inputs previously parsed *correctly*): (a) parses that used to succeed return `None`, indistinguishable from no-match and unconfigurable; (b) the §2 truncated-`Some` shapes return a *wrong* parse with no flag the old generated surface can read — silent corruption. Per CLAUDE.md, this must be a called-out decision, not an incidental side effect. Disposition:

- **Declared semver-breaking.** `fltk-parser-core` is pre-1.0 (`0.1.0`, path-dep only in-tree today); bump to `0.2.0` — the 0.x breaking signal — so a plain `cargo update` cannot silently mix a pre-limit generated parser with the new core.
- **Lockstep rule documented** in the `memo.rs` `apply`/module docs (§7 rewrite): generated parsers must be regenerated when crossing this core version boundary; a pre-limit generated parser on the new core enforces the default limit without any way to observe or configure it.
- In-tree fixtures use path deps and are regenerated in this change (§8), so the hazard is exclusively the out-of-tree mixed-version case.

### 3. Generated `Parser` surface (`gsm2parser_rs.py:_gen_parser_struct`)

Additive methods only; `new`/`from_source_text` signatures unchanged (out-of-tree constraint):

```rust
pub fn set_max_depth(&mut self, max_depth: u32) { self.packrat.max_depth = max_depth; }
pub fn max_depth(&self) -> u32 { self.packrat.max_depth }
pub fn depth_exceeded(&self) -> bool { self.packrat.depth_exceeded() }
```

A setter (vs. a new constructor) composes with both existing constructors and avoids constructor proliferation. Doc comments on `set_max_depth`/`depth_exceeded` carry the §2 contract (set before parsing; check after; discard result if set).

### 4. Python bindings (`gsm2parser_rs.py:_gen_python_bindings`)

- Import `PyRecursionError` alongside `PyValueError`.
- Constructor gains an optional keyword arg: `#[pyo3(signature = (text, capture_trivia = false, max_depth = None))]`, `max_depth: Option<u32>`; `Some(d)` → `inner.set_max_depth(d)`. Additive — existing call sites (including parity tests) unaffected. Add `#[getter] fn max_depth` and `fn depth_exceeded`.
- Each per-rule `apply__parse_X` checks the flag **after** the call and **before** inspecting the result (per §2 truncated-success hazard):

```rust
let result = self.inner.apply__parse_x(pos);
if self.inner.depth_exceeded() {
    return Err(PyRecursionError::new_err(format!(
        "parse depth limit exceeded (max_depth = {})", self.inner.max_depth())));
}
match result { Some(r) => ..., None => Ok(None) }  // existing body
```

`RecursionError` is the deliberate exception type: it is exactly what the Python backend raises on the same input shape, so downstream `except RecursionError:` handlers work identically on both backends. Distinguishable from "doesn't match" (`None` return) and from bad-position (`ValueError`).

Stickiness means subsequent calls on the same `PyParser` also raise `RecursionError` — consistent with "instance is spent".

### 5. Fixture grammar additions (test enablement)

The fixture grammar (`fltk/fegen/test_data/rust_parser_fixture.fltkg`) has **no rule whose `apply` depth grows with input**: `expr`/`lval`/`rval`/`rec_via_sub` are left-recursive (seed-grow handles them iteratively at constant depth) and `paren_expr` nests exactly one level (`inner:atom`, and `atom` is `num | name`). Depth-limit tests need real nesting. Append two rules (appending keeps it additive for every existing fixture test; both fixture parsers regenerate anyway):

```
// Right-recursive nesting: apply depth proportional to input nesting (depth-limit tests).
nest := %"(" . inner:nest . %")" | leaf:num ;

// Left recursion whose growth step descends into nesting: a depth-rejected growth
// iteration stalls grow_seed, which returns the seed — the Some-with-flag shape (§2).
nest_sum := lhs:nest_sum . "+" . rhs:nest | first:nest ;
```

Example of the `Some`-with-flag shape: `nest_sum` on `"1+(((9)))"` with `max_depth = 4` — seed `"1"` parses (depth 3); the growth iteration descends `rhs:nest` past the limit and fails; `grow_seed` stalls and returns the seed; `apply` returns `Some(pos = 1)` with the flag set.

Add shallow `nest`/`nest_sum` `SUCCESS` entries to the parity corpus (`tests/test_rust_parser_parity_fixture.py`) so the new rules are parity-covered like every other fixture rule; the Python side regenerates from the `.fltkg` at test time, so parity is automatic.

### 6. Default limit value

`DEFAULT_MAX_DEPTH = 1000` (rule-application depth), per the request's baseline. Margin math: 1000 levels × ~5-7 native frames/level (`apply__parse_X` → `apply` → `apply_inner` → `parse_X` → alt → item) ≈ 5000-7000 frames against an 8 MiB main-thread stack ⇒ ~1.2-1.6 KiB/frame budget. Debug-build frames of generated alt functions are fat (CST node + locals), so the budget is plausible but not proven on paper. The default-limit safety test (§Test plan, T6) pins it empirically. **Decision rule**: if T6 overflows in a debug build, halve `DEFAULT_MAX_DEPTH` until T6 passes with margin (input nested to 2× the limit still errors cleanly); the value is a single const. Note: Python's effective limit is ~200 rule levels (1000 CPython frames ÷ ~5 frames/level), so even 500 remains more permissive than the Python backend.

### 7. Stale-warning and TODO cleanup

- `memo.rs:83-90` (`apply` doc): replace the "no limit / hard DoS" paragraph and `TODO(apply-depth-limit)` with a description of the limit: default `DEFAULT_MAX_DEPTH`, configurable via `PackratState::max_depth`, depth-exceeded surfaces as `None` + sticky `depth_exceeded()`; callers must check the flag (§2 contract).
- `gsm2parser_rs.py:258-263` (generated header template): replace the warning block and `TODO(parser-depth-limit)` line with:

```
//! **Stack depth note**: this parser is recursive-descent. Rule-application depth is
//! bounded by `max_depth` (default `fltk_parser_core::DEFAULT_MAX_DEPTH`, configurable
//! via `Parser::set_max_depth`). Exceeding it fails the parse with
//! `Parser::depth_exceeded()` set (Python bindings raise `RecursionError`) instead of
//! overflowing the native stack. Check `depth_exceeded()` after parsing; a result
//! produced with the flag set must be discarded.
```

- PyParser doc comment (template in `_gen_python_bindings`, currently "cannot be caught from Python"): replace with the bounded-depth + `RecursionError` description.
- `TODO.md`: delete both entries (`apply-depth-limit` at TODO.md:45-52, `parser-depth-limit` at TODO.md:76-78). No `TODO(slug)` comments for either remain in code after the doc edits above.

### 8. Files touched

| File | Change |
|---|---|
| `crates/fltk-parser-core/src/memo.rs` | `PackratState` fields, manual `Default`, `DEFAULT_MAX_DEPTH`, `apply` guard + `apply_inner`, doc rewrite |
| `crates/fltk-parser-core/src/lib.rs` | re-export `DEFAULT_MAX_DEPTH` |
| `crates/fltk-parser-core/tests/memo_toy.rs` | toy-parser depth tests (T1-T4) |
| `fltk/fegen/gsm2parser_rs.py` | header template, `_gen_parser_struct` accessors, `_gen_python_bindings` (import, signature, flag check, getters, docs) |
| `fltk/fegen/test_data/rust_parser_fixture.fltkg` | append `nest`, `nest_sum` rules (§5) |
| `tests/rust_parser_fixture/src/parser.rs` + `cst.rs`, `tests/rust_cst_fegen/src/parser.rs` | regenerated (`make fix` after) |
| `tests/test_rust_parser_fixture_bindings.py` (new) | binding-level depth tests (T5, T6) against `rust_parser_fixture`, own `importorskip` |
| `crates/fltk-parser-core/Cargo.toml` | version `0.1.0` → `0.2.0` (§2 Versioning) |
| `tests/test_rust_parser_parity_fixture.py` | shallow `nest`/`nest_sum` corpus entries |
| `TODO.md` | remove both entries |

Python backend (`fltk/fegen/pyrt/`, `gsm2parser.py`): untouched (constraint).

## Edge cases / failure modes

- **Truncated `Some` with flag set** (grow_seed stall; optional-item skip in an in-flight frame): handled by flag-outranks-result contract; bindings enforce, Rust-native docs require it (§2, §4). Tested (T4, T5).
- **Cache pollution below the limit**: neutralized by sticky flag — instance never returns a trusted result afterward (§2).
- **Parser reuse after depth-exceeded**: every subsequent apply fails fast / raises `RecursionError`. Documented as "instance is spent".
- **`max_depth = 0`**: first apply fails with flag set. Well-defined.
- **Panic inside `apply_inner` skips decrement**: parser state is abandoned after any memo-invariant panic; counter staleness is unobservable.
- **Parity comparator** (`tests/parser_parity.py`): the existing corpus cannot trigger the default limit — the current fixture grammar has no depth-proportional rule at all (§5), and the new `nest`/`nest_sum` corpus entries are shallow. On hypothetical deep inputs the backends diverge in threshold (Python `RecursionError` at ~200 effective levels, Rust at 1000) but agree in kind: both fail catchably with `RecursionError`. Accepted, not comparator-visible.
- **Cargo-test thread stacks are 2 MiB** (vs 8 MiB main thread): any cargo test exercising the *default* limit would overflow where production wouldn't. Default-limit testing therefore lives in pytest (CPython main thread, 8 MiB) — T6; cargo tests use small explicit limits only.
- **Old-generated parser + new core (out-of-tree mixed versions)**: default limit enforced with no surfacing — silent `None`s and truncated-`Some` corruption on deep inputs that previously parsed. Handled as a deliberate semver break: core version bump + lockstep-regeneration docs (§2 Versioning).

## Test plan

Core (cargo, `crates/fltk-parser-core/tests/memo_toy.rs`), small explicit limits:

- **T1**: recursive toy rule, input deeper than `max_depth` → `apply` returns `None`, `depth_exceeded()` true; same input with larger `max_depth` → `Some`, flag false.
- **T2 (unwind)**: two sibling subtrees each near-but-under the limit parse successfully — proves the counter decrements on return (a leaky counter would fail the second sibling).
- **T3 (sticky)**: after depth-exceeded, a subsequent `apply` at pos 0 on a trivial input returns `None` immediately, flag still set.
- **T4 (flag outranks Some)**: left-recursive toy rule whose growth iteration descends past the limit (the §5 `nest_sum` shape) → `apply` returns `Some` (the seed) *and* `depth_exceeded()` is true. Pins the §2 contract's premise.

Bindings (pytest, **new file** `tests/test_rust_parser_fixture_bindings.py` with its own `importorskip("rust_parser_fixture")` guard), using the new `nest`/`nest_sum` rules (§5). Not `tests/test_rust_parser_bindings.py`: that file guards and tests only `fegen_rust_cst` (the fegen-grammar parser), which has no `nest` rules; mixing modules there would error instead of skip when only one extension is built.

- **T5**: `Parser(text, max_depth=10)` on `nest` input nested ~50 → raises `RecursionError` (catchable); same input with `max_depth=200` → parses. `nest_sum` on `"1+" + nested-past-limit` → also raises despite the in-flight `Some` (binding-level flag-outranks-result).
- **T6 (default-limit safety)**: default `Parser` on `nest` input nested `DEFAULT_MAX_DEPTH + 100` → raises `RecursionError`, process survives. Empirically pins that the default fires before native overflow in debug builds (§6 decision rule on failure).
- **T7 (default untriggered)**: existing binding/parity suites pass unchanged with the default limit — no new construction args anywhere.

Process: regenerate both fixture parsers; `make fix`; `uv run pytest` and `cargo test` fully clean.

## Open questions

None. The only empirical unknown (debug-build frame size vs. the 1000 default) is resolved by T6 plus the §6 decision rule, not by user judgment.
