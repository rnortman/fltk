# Design: Phase 1 — `fltk-parser-core` Runtime Crate

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Controlling design: `docs/adr/2026/06/10-rust-parser-codegen/design.md` (§3.1 specifies this crate; §6 defines Phase 1). Requirements: `docs/adr/2026/06/10-rust-parser-codegen/request.md`. Facts: `exploration.md` in this directory. This doc is the detailed implementation plan for Phase 1 only — the runtime crate, no codegen, no Python bindings.

---

## 1. Context

Phase 1 delivers `crates/fltk-parser-core`: a pure-Rust, unconditionally pyo3-free port of `fltk/fegen/pyrt/` (`memo.py`, `terminalsrc.py`, `errors.py`) that Phase 2's generated parsers will call. The Python runtime is the parity reference; the port must reproduce its observable behavior (positions, memoization semantics including left recursion, error tracking and message format) while restructuring for the borrow checker where Python relies on aliasing (controlling design §2.2, §3.1).

Deliverable: the crate, its unit tests (including ports of all `fltk/fegen/pyrt/test_memo.py` cases against a hand-written toy parser), and build-gate wiring (`make check` lanes, no-pyo3 assertion).

---

## 2. Proposed approach

### 2.1 Crate layout and build wiring

New crate `crates/fltk-parser-core/`:

```
Cargo.toml          package fltk-parser-core, lib name fltk_parser_core, crate-type rlib
src/lib.rs          module decls, re-exports, `pub use regex;`
src/memo.rs         port of pyrt/memo.py
src/terminalsrc.rs  port of pyrt/terminalsrc.py (TerminalSource, LineColPos only — Span/SourceText come from fltk-cst-core)
src/errors.rs       port of pyrt/errors.py
tests/memo_toy.rs   toy parser exercising apply() through the public API (ports test_memo.py)
```

Dependencies:

```toml
[dependencies]
fltk-cst-core = { path = "../fltk-cst-core", default-features = false }
regex = "1"
```

No `python` feature exists at all — pyo3-freedom is structural absence, not a disabled feature (exploration.md §2). `lib.rs` re-exports `pub use regex;` so Phase 2 generated code can reference `fltk_parser_core::regex::Regex` without consumer crates declaring a `regex` dependency (controlling design §3.1). New pattern in this codebase; the rationale (version coherence between runtime and generated code) is documented on the re-export.

Crate-root re-exports: `apply`, `ApplyResult`, `Cache`, `MemoEntry`, `MemoResult`, `PackratState`, `RecursionInfo` from `memo`; `TerminalSource`, `LineColPos` from `terminalsrc`; `ErrorTracker`, `ParseContext`, `TokenType`, `format_error_message` from `errors`.

Each module's doc comment names its Python source file so the two are side-by-side auditable (controlling design §2.7 mitigation, applied to the runtime as well as the future generator).

Build wiring (exploration.md §6):

- Root `Cargo.toml`: add `"crates/fltk-parser-core"` to `members`. `cargo-check`/`cargo-test`/`cargo-clippy` pick it up automatically.
- `Makefile cargo-test-no-python`: add `cargo test -q -p fltk-parser-core` (no `--no-default-features` — there is no feature to disable).
- `Makefile cargo-clippy-no-python`: add `cargo clippy -q -p fltk-parser-core -- -D warnings`.
- `Makefile check-no-pyo3`: add a stanza `cargo tree -p fltk-parser-core --edges normal,build`; positive control `grep -q fltk-cst-core`, negative assertion `! grep -q pyo3` — same shape as the existing stanzas (Makefile:63-71).

### 2.2 One additive change to `fltk-cst-core`: `SourceText::text()`

`SourceInner.text` is `pub(crate)` (span.rs:48-50), so an external crate cannot read the text out of a `SourceText`. Without an accessor, `TerminalSource` would have to keep a second copy of the input. Add to `fltk-cst-core`:

```rust
impl SourceText {
    /// Borrow the underlying source text.
    pub fn text(&self) -> &str { &self.inner.text }
}
```

Native-only (not a `#[pymethods]` addition — the Python-visible `SourceText` surface stays construction-only per terminalsrc.py:8-16's portability contract). Purely additive; no existing behavior changes.

### 2.3 `terminalsrc.rs` — `TerminalSource`

```rust
pub struct TerminalSource {
    source: SourceText,            // single owner of the input text (Arc<SourceInner>)
    cp_to_byte: Vec<usize>,        // cp_to_byte[i] = byte offset of codepoint i; cp_to_byte[len] = text.len() sentinel
    line_ends: OnceLock<Vec<i64>>, // lazy, mirrors Python (terminalsrc.py:189-192); OnceLock keeps &self API and Sync
}

pub struct LineColPos { pub line: i64, pub col: i64, pub line_span: Span }
```

Constructors: `TerminalSource::new(text: &str)` (builds `SourceText::from_str`) and `TerminalSource::from_source_text(source: SourceText)` (no copy; reads text via §2.2 accessor). `cp_to_byte` is built once at construction via `char_indices()` plus the final sentinel.

Accessors: `source_text(&self) -> &SourceText` (for `Span::new_with_source` at generated-code span sites), `text(&self) -> &str`, `len(&self) -> i64` (codepoint count, the Python `terminals_len`), `is_empty`.

All positions are **codepoint indices, `i64`** (exploration.md §7). Position validity contract (controlling design §4 no-panic rule): any `pos < 0` or `pos > len` in `consume_*` returns `None` — never panics, never wraps through `as usize`.

**`consume_literal(&self, pos: i64, literal: &str) -> Option<Span>`** — port of terminalsrc.py:168-175. Bounds-check `pos`, convert to byte offset via `cp_to_byte`, then compare `text[byte_pos..].chars()` against `literal.chars()` pairwise, counting literal codepoints during the same loop (no separate `chars().count()` pass). Any mismatch or input exhaustion → `None`. Success → `Span::new_with_source(pos, pos + literal_cp_len, &self.source)`. For `pos >= 0` this matches Python's per-codepoint comparison exactly, including the empty-literal case: `0 <= pos <= len` with empty literal yields `Some(empty span)`; `pos > len` yields `None`. For `pos < 0` the validity contract above governs (`None`) — a **deliberate divergence** from Python, whose `self.terminals[pos + i]` indexing wraps negative positions (terminalsrc.py:173: `consume_literal(-1, <last char>)` succeeds with `Span(-1, 0)`; empty literal at `pos = -5` yields `Span(-5, -5)`). Negative `pos` is unreachable from generated code; any cross-backend differential testing of `consume_*` must restrict to `pos >= 0`.

**`consume_regex(&self, pos: i64, regex: &Regex) -> Option<Span>`** — per controlling design §3.1: bounds-check `pos` (note `pos == len` is valid — a pattern like `a*` matches empty at end-of-input, as Python's `re.match(pos=len)` does), then `regex.find_at(self.text(), byte_pos)`; reject unless `m.start() == byte_pos` (emulates `re.match`'s anchoring; `find_at` scans forward, so a later match must be treated as failure). Searching the full haystack from a byte offset — not slicing — preserves look-behind context (`\b`/`\B`) identically to Python's `re.match(pos=...)`. Convert `m.end()` (byte) back to a codepoint index by binary search on `cp_to_byte` (`partition_point`; regex match boundaries are always UTF-8 char boundaries, so the search hits an exact entry — `debug_assert` that). Success → source-bearing span `[pos, end_cp)`.

Span-source note: Python's `TerminalSource.consume_*` return *sourceless* spans which the generated parser re-wraps via `Span.with_source` (gsm2parser.py:135-181). The Rust runtime attaches the source directly — it owns the `SourceText` anyway, this removes a step from every generated call site, and `Span` equality ignores source (span.rs:161-165) so parity comparisons are unaffected. Deliberate layering simplification, recorded here.

**`pos_to_line_col(&self, pos: i64) -> Option<LineColPos>`** — verbatim port of the bisect logic (terminalsrc.py:183-205), including: the `pos == len → pos -= 1` decrement; lazy `line_ends` = codepoint indices of `\n` plus a final `len - 1` sentinel when not newline-terminated (which is `-1` for empty input); `bisect_left` ≡ `partition_point(|&e| e < pos)`. Domain: `pos ∈ [-1, len]` (Python raises `ValueError` for `pos > len`; `-1` arises from `ErrorTracker.longest_parse_len`'s initial value and must produce Python's exact line-1/col-0-equivalent result — see §2.4). Out-of-domain → `None` (≈ Python's `ValueError`; `pos < -1` is unreachable from this runtime's own call sites and also returns `None`). `line_span` is returned source-bearing (improvement over Python's sourceless span; equality-compatible) so `format_error_message` can slice via `Span::text()`.

### 2.4 `errors.rs` — `ErrorTracker` + `format_error_message`

```rust
pub enum TokenType { Literal, Regex }
pub struct ParseContext { pub rule_id: u32, pub token_type: TokenType, pub token: &'static str }
pub struct ErrorTracker {
    pub longest_parse_len: i64,              // -1 initial, like Python (errors.py:26)
    pub expected_context: Vec<ParseContext>,
}
```

`token: &'static str`: all callers are generated parsers (and tests) whose literals and regex patterns are `'static`; this makes `ParseContext` `Copy` and keeps the hot failure path (every failed terminal attempt) allocation-free. `longest_parse_len` stays public — it is Phase 3's `error_position()` source.

Construction: `impl Default for ErrorTracker` — `longest_parse_len: -1` (errors.py:26), empty `expected_context`. The `-1` initial value is a correctness invariant; `Default` encodes it once so the toy tests and Phase 2's generated `Parser` constructor cannot get it wrong via field-literal construction.

`fail_literal(&mut self, pos: i64, rule_id: u32, literal: &'static str)` / `fail_regex(...)`: exact port of errors.py:29-49 — `pos < longest` ignore; `pos == longest` append; `pos > longest` replace-and-update.

**`format_error_message(tracker: &ErrorTracker, terminals: &TerminalSource, rule_names: &[&str]) -> String`** — port of errors.py:52-71, format string identical:

```
Syntax error at line {line+1} col {col+1}:\n{line_text}\n{' ' * col}^\nExpected:\n  From rule "{name}":\n    {LITERAL|REGEX}: {py_repr(token)}\n
```

Porting decisions, each grounded in the Python source:

- `rule_names: &[&str]` replaces Python's `rule_name_lookup` callable — the only real lookup is the generated `rule_names` table (exploration.md §5). Out-of-range id → `"<unknown rule {id}>"` (no panic; Python would `IndexError`, unreachable from generated code).
- `' ' * col` with `col == -1` (the `longest_parse_len == -1` case) is `""` in Python; Rust uses `" ".repeat(col.max(0) as usize)`.
- `line_span.text()` returning `None` (only the empty-input `Span(0, -1)` case, where Python's `[0:-1]` slice on `""` is also `""`) → `""`.
- If `pos_to_line_col` returns `None` (unreachable: `longest_parse_len ∈ [-1, len]` by construction since failures are recorded at positions the parser actually reached), fall back to `"Syntax error at unknown position\n"` plus the Expected block rather than panicking.
- **Within-rule token ordering**: Python groups into a `defaultdict(set)` and iterates the *set* (errors.py:64-70) — with `PYTHONHASHSEED` randomization, Python's within-rule line order is nondeterministic across processes. Rust cannot and should not reproduce nondeterminism: group by `rule_id` in first-occurrence order (matching `defaultdict` insertion order, which Python does guarantee), and within a rule emit deduplicated contexts in first-occurrence order. Consequence for Phase 3 recorded here: the parity comparator must treat within-rule "Expected" lines as an unordered set; byte-identical comparison is only valid for single-token rule groups. This refines the controlling design §5 item 3 ("`error_message()` matches") — equality is up to within-rule line order.
- **`{token!r}` is Python `repr`, not Rust `{:?}`**: Python reprs `\s+` as `'\\s+'` (single quotes, backslash doubled); Rust `{:?}` would give `"\\s+"`. Implement a private `py_repr_str(&str) -> String` reproducing Python 3 `str.__repr__` for the relevant domain: prefer `'` quotes, switch to `"` iff the string contains `'` and not `"`; escape `\\`, the active quote, `\n`, `\r`, `\t`; other chars `< 0x20` and `\x7f` as `\xHH`; non-ASCII emitted raw (Python escapes non-printable Unicode, but grammar tokens are printable; golden tests pin the behavior, divergence outside the tested domain is acceptable and documented on the function).

### 2.5 `memo.rs` — packrat with left-recursion support

Types (port of memo.py:27-74):

```rust
pub struct ApplyResult<T> { pub pos: i64, pub result: T }      // Clone, Debug, PartialEq where T allows
pub struct RecursionInfo { pub rule_id: u32, pub involved: HashSet<u32>, pub eval_set: HashSet<u32> }
pub enum MemoResult<T> { Poison(Option<RecursionInfo>), Value(T), Failure }
pub struct MemoEntry<T> { pub result: MemoResult<T>, pub final_pos: i64 }
pub type Cache<T> = HashMap<i64, MemoEntry<T>>;
pub struct PackratState { pub invocation_stack: Vec<u32>, recursions: HashMap<i64, RecursionInfo> }
```

Construction: `impl Default for PackratState` — empty stack, empty `recursions`. This is the only external construction path: `recursions` is private, so the toy test crate (`tests/memo_toy.rs` is an integration test outside the crate) and Phase 2's generated `Parser::new` (controlling design §3.2) cannot use a struct literal. `Default` ships in the §2.1 public surface alongside the type.

`MemoResult<T>` collapses Python's untyped `Poison | ResultType | None` union (memo.py:61) into one enum; `Poison(Option<RecursionInfo>)` *is* the Python `Poison` dataclass, but it lives only inside the cache entry — there is no separately-owned poison object to alias (controlling design §2.2, §3.1). Rule ids are concrete `u32`, positions concrete `i64` (Python's generics over `RuleId`/`PosType` exist for typing flexibility the generated code never uses).

The memoizer is a generic free function (not a method — avoids the triple-`&mut self` borrow of the Python call shape, memo.py-via-gsm2parser.py:456-462):

```rust
pub fn apply<P, T: Clone>(
    parser: &mut P,
    rule_id: u32,
    pos: i64,
    state: fn(&mut P) -> &mut PackratState,
    cache: fn(&mut P) -> &mut Cache<T>,
    rule: fn(&mut P, i64) -> Option<ApplyResult<T>>,
) -> Option<ApplyResult<T>>
```

`fn` pointers, not `impl Fn`: every projector the generated code (and the toy tests) needs is non-capturing (`|p| &mut p.packrat`, `Parser::parse_x`), they coerce to `fn`, and monomorphization stays minimal. Every access to state/cache re-borrows through `parser`, so `rule` can recurse into `apply` freely. `T: Clone` because cache hits clone the stored result — for generated code `T = Shared<NodeT>`, so a hit is an Arc clone, reproducing Python's cached-object sharing (controlling design §3.2).

Algorithm mapping (each step cites memo.py):

1. **Recall** (memo.py:158-204). Read `state(parser).recursions.get(&pos)`:
   - No active growth at `pos` (nominal): fall through to step 2 with the existing cache entry, if any.
   - Active growth: if no cache entry and `rule_id` is neither the head nor in `involved` → `panic!` with the memo.py:181-187 message verbatim ("Untested corner case; see source code for more information.") — the same deliberate fail-loudly choice. Otherwise the entry must exist (`assert`, memo.py:191). If `rule_id ∈ eval_set`: remove it (via `recursions.get_mut`), drop the borrow, call `rule(parser, pos)`, then overwrite the entry through `cache(parser).get_mut(&pos)` with `Value/Failure` + `final_pos` (memo.py:193-203). Sequential borrows replace Python's simultaneous aliasing.
2. **Cache-entry dispatch** (memo.py:96-109): entry present and `Poison` → `assert entry.final_pos == pos` (memo.py:100), run `setup_recursion` (step 6), return `None`; `Value(v)` → `Some(ApplyResult { pos: entry.final_pos, result: v.clone() })`; `Failure` → `None`.
3. **Miss** (memo.py:111-122): insert `MemoEntry { result: Poison(None), final_pos: pos }`; push `rule_id` onto `invocation_stack`; `let call_result = rule(parser, pos)`; pop and `assert` it matches. Re-fetch the entry from the map (`assert` it exists and is still `Poison` — the Rust expression of Python's `assert memo.result is poison`, memo.py:122) and **take** the `Option<RecursionInfo>` out of it. Re-fetching after the call is the load-bearing restructure: Python mutates the poison through an alias held across the recursive call; Rust re-reads the map instead.
4. **No recursion detected** (`recursion_info == None`; memo.py:131-136): set `final_pos` to the result pos (or `pos` on failure), store `Value/Failure`, return.
5. **Recursion detected** (memo.py:144-156): `assert recursion_info.rule_id == rule_id` (we are the head). Store the seed (`Value/Failure` + `final_pos`); on `Failure` return `None` (no seed to grow). Otherwise push `rule_id`, run `grow_seed`, pop+assert, return its result.
6. **`setup_recursion`** (memo.py:206-226), private helper: first walk `state(parser).invocation_stack` top-down collecting rule ids into a local set until hitting `rule_id` (`assert` it is found — Python's `assert idx >= 0`); then mutate the cache entry's `Poison` payload: `None` → `Some(RecursionInfo { rule_id, involved, eval_set: ∅ })`; `Some(ri)` → `assert ri.rule_id == rule_id`, extend `ri.involved` with the walked set (Python re-walks and re-adds on every poison hit; sets dedupe — identical semantics). Reading the stack fully before touching the cache replaces Python's interleaved access; the two are observably equivalent because the walk doesn't depend on the cache.
7. **`grow_seed`** (memo.py:228-257), private helper with the same `parser`/projector parameters: move the `RecursionInfo` into `state(parser).recursions[pos]`; loop: `eval_set = involved.clone()` (through `get_mut`), call `rule(parser, pos)`, re-fetch the cache entry; if the call failed or `new_pos <= entry.final_pos` → break (memo.py:248); else store `Value(result)` + `final_pos = new_pos`. After the loop remove `recursions[pos]`, `assert` the entry holds `Value`, and return `ApplyResult { pos: final_pos, result: value.clone() }`.

Assertion policy: the Python asserts above are cheap algorithm invariants, active in normal Python runs; port them as plain `assert!` (not `debug_assert!`) for identical fail-loudly behavior. They are not input-reachable — only the memo.py:181 `panic!` is a documented reachable panic, matching controlling design §4. The byte-conversion `debug_assert` in §2.3 is the one debug-only check (its invariant is guaranteed by the `regex` crate).

---

## 3. Edge cases / failure modes

- **Codepoint/byte confusion** — highest-risk bug class (controlling design §4). Every `TerminalSource` test runs an ASCII and a multibyte variant: literals starting at multibyte offsets, literals containing multibyte chars, regex matches ending mid-string after multibyte chars (exercising the byte→codepoint binary search), line/col over multibyte lines.
- **Regex anchoring**: `find_at` finding a match *later* than `byte_pos` must yield `None` — explicit test (pattern matches at pos+2, not pos). Look-behind context: `\b` at a position preceded by a word char must behave as in Python `re.match(pos=...)` — test both accept and reject directions.
- **`pos == len`**: valid for `consume_*` (empty-match regexes, empty literals) and for `pos_to_line_col` (decrement branch, terminalsrc.py:187-188). Tested.
- **Out-of-range / negative `pos`**: `consume_*` return `None`; no `as usize` wraparound anywhere (`i64` validated before conversion). For `pos < 0` this intentionally diverges from Python's negative-index wrapping (§2.3). `pos_to_line_col` domain `[-1, len]`, `None` outside.
- **Empty input**: `pos_to_line_col(0)` on `""` goes through `pos = -1`, `line_ends = [-1]`, `line_span = Span(0, -1)`; `format_error_message` renders line 1 / col 0 / empty line text. Golden-tested against captured Python output.
- **`longest_parse_len == -1`** (no failure recorded): `format_error_message` must still produce Python's exact output (line 1, col 0, no leading spaces before `^`). Golden-tested.
- **Error-message ordering nondeterminism in Python** (§2.4): Rust output is deterministic; the divergence is one-directional (Python is the unstable side) and recorded for Phase 3's comparator.
- **Memo poison/growth fidelity**: the cache-entry restructure (no aliased poison) is gated by the full `test_memo.py` port — direct, indirect, and multi-path left recursion, plus failure caching. The untestable memo.py:181 corner stays a `panic!`, deliberately (Python: `NotImplementedError`, `pragma: nocover`).
- **Cache-hit cloning**: `T: Clone` hits clone; a test asserts the rule body executes exactly once per `(rule, pos)` (invocation counter in the toy parser), proving memoization, and a left-recursion test asserts growth termination on `new_pos <= final_pos` (memo.py:248) including the equal-position case.
- **`cp_to_byte` memory**: 8 bytes/codepoint (`Vec<usize>`). Acceptable for grammar-sized inputs; if it ever matters, `u32` offsets halve it — not done now, noted in a code comment only (no TODO: no concrete trigger).

---

## 4. Test plan

All Rust, in `fltk-parser-core`; runs under workspace `cargo test` and the new `-p fltk-parser-core` no-python lane.

1. **`tests/memo_toy.rs`** — toy parser struct (`PackratState` + per-rule `Cache<Expr>` fields, `Expr` a small `Clone + PartialEq` enum) exercising `apply` through the public API exactly as generated code will:
   - Ports of all five `test_memo.py` cases: `test_direct`, `test_indirect`, `test_multi_b`, `test_multi_c`, `test_fail` — same grammars, same inputs, same expected structures and positions.
   - Memoization: invocation-count assertions (rule body runs once per position; second `apply` at same pos is a pure cache hit).
   - Failure caching: failed rule re-queried at same pos does not re-execute.
   - Growth termination at equal position (non-growing recursive alternative).
2. **`terminalsrc` unit tests**: `consume_literal` (match/mismatch/exhaustion/empty literal/`pos == len`/out-of-range/negative, ASCII + multibyte); `consume_regex` (anchor rejection, `\b` look-behind both directions, empty match at `pos == len`, multibyte end-offset conversion, out-of-range); `pos_to_line_col` (first/middle/last line, `pos == len`, trailing-newline vs not, `-1`, empty input, multibyte cols, out-of-domain → `None`).
3. **`errors` unit tests**: `fail_*` replace/append/ignore transitions; `format_error_message` golden tests — expected strings captured by running the Python `format_error_message` on the same tracker states (capture method documented in the test file), covering multi-rule grouping, dedup, regex tokens with backslashes (`py_repr_str` quoting/escaping), `-1` position, empty input. Ordering constraint (consequence of §2.4's nondeterminism analysis): byte-equality golden cases use **at most one distinct token per rule group** — Python's within-rule line order is hash-seed-dependent, so a multi-token capture is not stable. Cases with ≥2 distinct tokens in one rule assert the header and rule-group order byte-exactly and the within-rule lines as an unordered set (the same comparator rule §2.4 prescribes for Phase 3).
4. **Build gates**: `make check` green with the three Makefile additions (§2.1); `check-no-pyo3` stanza proves the crate's dependency graph is pyo3-free.

TDD order: tests 1 (ported memo cases) and 2 are written against the module skeletons first, per the controlling design's Phase 1 TDD note.

---

## 5. Open questions

None. The three judgment calls that arose — source-bearing spans from `consume_*` (§2.3), rejecting negative `pos` instead of Python's index wrapping (§2.3), and deterministic error-message ordering (§2.4) — are decided above with rationale; none needs user input. The `SourceText::text()` accessor (§2.2) is additive and Python-invisible, within Phase 1's remit.
