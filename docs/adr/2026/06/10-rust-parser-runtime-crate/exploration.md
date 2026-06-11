# Exploration: Phase 1 — `fltk-parser-core` Runtime Crate

Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

---

## 1. Phase 1 scope (from design.md §6)

Phase 1 is limited to the runtime crate `crates/fltk-parser-core`. No codegen. Contents:
- `ApplyResult<T>`, `MemoEntry`, `MemoResult<T>` enum (`Poison(Option<RecursionInfo>)` / `Value(T)` / `Failure`)
- `TerminalSource` (owns `SourceText`, codepoint→byte map, `consume_literal`, `consume_regex`, `pos_to_line_col`)
- `Packrat` (restructured for borrow checker, generic `apply` free function)
- `ErrorTracker` + `format_error_message`

No pyo3, no `python` feature. Deliverable: passing unit tests including ported `test_memo.py` cases.

---

## 2. Workspace layout — where the new crate slots in

`Cargo.toml` (root, line 1-21):
```toml
[workspace]
members = [".", "crates/fltk-cst-core", "crates/fltk-cst-spike"]
```

`fltk-parser-core` goes in `crates/fltk-parser-core/` and is added to `members`. It is an `rlib`, no `python` feature (unconditionally pyo3-free — the design enforces this by structural absence, not by a disabled feature).

`fltk-cst-core/Cargo.toml` (lines 7-19): `rlib`, `python` feature gates `dep:pyo3`. `fltk-parser-core` depends on `fltk-cst-core` with `default-features = false` (for `Span`, `SourceText`). Adds `regex` as a direct dependency.

`fltk-cst-spike/Cargo.toml` (lines 13-15): pattern for a crate that is python-off by default (`default = []`, `python = ["dep:pyo3", "fltk-cst-core/python"]`). `fltk-parser-core` follows the same pattern except no `python` feature exists at all.

`tests/rust_cst_fegen/Cargo.toml` (line 1-3): standalone workspace (`[workspace]` on line 1), NOT a member of the root workspace; built via `cd tests/rust_cst_fegen && uv run maturin develop`. Future `tests/rust_parser_fegen/` follows the same isolation model.

---

## 3. Existing Rust types Phase 1 depends on

### 3.1 `SourceText` — `crates/fltk-cst-core/src/span.rs:48-74`

```rust
pub struct SourceInner { pub(crate) text: String }
pub struct SourceText { pub inner: Arc<SourceInner> }
impl SourceText {
    pub fn from_str(text: &str) -> Self { ... }  // line 67-73
}
```

`SourceText` is `Arc<SourceInner>` — cloning is a refcount bump. `TerminalSource` owns one `SourceText` (the single owner of the input text); all spans produced reference it via `Arc::clone` on `source.inner`.

### 3.2 `Span` — `crates/fltk-cst-core/src/span.rs:141-365`

```rust
pub struct Span {
    pub(crate) start: i64,   // codepoint index
    pub(crate) end: i64,     // codepoint index
    pub(crate) source: Option<Arc<SourceInner>>,
}
```

Constructor for runtime use: `Span::new_with_source(start: i64, end: i64, source: &SourceText)` (line 204). Positions are **Unicode codepoint indices** matching Python's string indexing; `Span::text()` (line 271) converts to byte offsets with a single char-index scan.

Sentinel: `Span::unknown()` → `{start: -1, end: -1, source: None}` (line 181-187).

### 3.3 `Shared<T>` — `crates/fltk-cst-core/src/shared.rs:44`

`Arc<RwLock<T>>` newtype. `Clone` is shallow (refcount). Memoized parser results are cached as `Shared<NodeT>`; cache hits are `Arc::clone`. `From<T>` impl (line 104-108) allows `.into()` at construction sites.

### 3.4 `CstError` — `crates/fltk-cst-core/src/error.rs:15`

Used by CST accessor methods. `fltk-parser-core` does not use it directly but depends on `fltk-cst-core`, which exports it.

### 3.5 `fltk-cst-core/src/lib.rs` public exports (lines 10-13)

```rust
pub use error::CstError;
pub use shared::Shared;
pub use span::{SourceText, Span, SpanError};
```

Python-gated exports (`cross_cdylib`, `registry`) are absent without `python` feature — `fltk-parser-core` gets a clean dependency.

---

## 4. Python runtime (`fltk/fegen/pyrt/`) — parity reference

### 4.1 `terminalsrc.py` — `fltk/fegen/pyrt/terminalsrc.py`

**`TerminalSource`** (line 162-205):
- `__init__(terminals: str)` — stores text, computes `terminals_len`, lazily builds `line_ends`
- `consume_literal(pos, literal) -> Span | None` (line 168-175): char-by-char comparison at codepoint positions; returns `Span(pos, pos + len(literal))` (sourceless). Note: Python `Span` here is sourceless; generated parser wraps it with `Span.with_source(start, end, self._source_text)` via `_make_span_expr`.
- `consume_regex(pos, regex) -> Span | None` (line 177-180): `re.compile(regex).match(terminals, pos=pos)` — anchored at `pos` but searching full string (no slice). Returns `Span(pos, match.end())`.
- `pos_to_line_col(pos) -> LineColPos` (line 183-205): bisect on lazily-computed `line_ends` list. `line_ends` is `[idx for idx, c in enumerate(terminals) if c == '\n']` plus final position if not already newline-terminated.

**`Span`** (line 48-149): `start: int, end: int, _source: str | None`. Equality and hash ignore `_source` — identical to Rust's `PartialEq` which ignores `source`. `UnknownSpan: Final = Span(-1, -1)` (line 152).

**`SourceText`** (line 8-21): wrapper over `_text: str`; `SourceText(text)` is the portable constructor.

### 4.2 `memo.py` — `fltk/fegen/pyrt/memo.py`

**`Packrat`** (line 77-257): `invocation_stack: list[RuleId]`, `_recursions: dict[PosType, RecursionInfo]`.

`apply(rule_callable, rule_id, rule_cache, pos)` (line 82-156):
1. `_recall` checks cache + active growth cycle (line 92)
2. If `Poison` in cache: call `_setup_recursion`, return `None` (lines 97-106)
3. If `Value`/`None` in cache: return cached result (lines 108-109)
4. Otherwise: plant poison, push `rule_id` onto `invocation_stack`, call `rule_callable`, pop stack (lines 112-120)
5. If no recursion detected: store result in cache, return (lines 131-136)
6. If recursion: call `_grow_seed` (lines 152-156)

Python aliasing that cannot translate directly to Rust:
- `memo.result = poison` then `call_result = rule_callable(start_pos)` then `assert memo.result is poison` (lines 113-122) — the cache entry is mutated through the aliased `Poison` object while the rule runs. Rust: re-fetch entry from map after the call.
- `self.packrat.apply(rule_callable=self.parse_X.bind(), ...)` in generated parsers (gsm2parser.py:456-462) — simultaneous borrows of `packrat`, `cache`, and `self` for the method bind. Rust: `apply` must be a free function taking field-projector function pointers.

**`_recall`** (line 158-204): the `NotImplementedError` path (lines 181-187) is the documented unimplemented corner case; Rust equivalent is `panic!`.

**`_grow_seed`** (line 228-257): terminates when `new_pos <= memo.final_pos` (line 248). Cleans up `_recursions` entry on exit.

**`ApplyResult`** (line 68-70): frozen dataclass `{pos: PosType, result: ResultType}`. Rust: `pub struct ApplyResult<T> { pub pos: i64, pub result: T }`.

**`MemoEntry`** (line 59-62): `{result: Poison | ResultType | None, final_pos: PosType}`. Rust: `result` field is an enum.

### 4.3 `errors.py` — `fltk/fegen/pyrt/errors.py`

**`ErrorTracker`** (line 25-49): `longest_parse_len: int = -1`, `expected_context: list[ParseContext]`.
- `fail_literal(pos, rule_id, literal)`: update if `pos >= longest_parse_len` (lines 29-37)
- `fail_regex(pos, rule_id, regex)`: same logic (lines 39-49)

**`format_error_message`** (line 52-71): takes `tracker`, `terminals: TerminalSource`, `rule_name_lookup: Callable[[int], str]`. Calls `terminals.pos_to_line_col(tracker.longest_parse_len)`, formats multi-rule "Expected:" block grouped by `rule_id`. Output format (line 58-64):
```
Syntax error at line {line+1} col {col+1}:\n
{line_text}\n
{' ' * col}^\n
Expected:\n
  From rule "{rule_name}":\n
    {LITERAL|REGEX}: {token!r}\n
```

**`ParseContext`** (lines 17-21): frozen `{rule_id: RuleId, token_type: TokenType, token: str}`.

---

## 5. How generated parsers use the runtime today

From `fltk/fegen/gsm2parser.py` (ParserGenerator.__init__):

**Parser struct fields** (lines 62-103):
- `packrat: Packrat[int, int]` — `Packrat()` constructed in init
- `terminalsrc: TerminalSource` — passed to constructor
- `_source_text: SourceText` — built as `SourceText(text=terminalsrc.terminals)` in init
- `error_tracker: ErrorTracker[int]` — constructed in init
- `rule_names: Sequence[str]` — literal list of rule names from grammar

**Constructor signature** (line 119-131): `Parser(terminalsrc: TerminalSource)`. `_source_text` init from `terminalsrc.terminals`.

**`consume_literal`** (lines 135-181): calls `self.terminalsrc.consume_literal(pos, literal)`. On success, wraps with `Span.with_source(start, end, self._source_text)`. On failure, calls `self.error_tracker.fail_literal(pos, rule_id=self.packrat.invocation_stack[-1], literal)`.

**`consume_regex`** (lines 183-230): same pattern for regex branch.

**Memoizer (apply method)** (lines 440-473): calls `self.packrat.apply(rule_callable=self.parse_X.bind(), rule_id=N, rule_cache=self._cache__parse_X, pos=pos)`. Each memoized rule gets its own cache field `_cache__parse_<rule>: dict[int, MemoEntry]` (lines 464-472).

**Two Python parser variants** (`genparser.py:85`, `genparser.py:214-242`): `preserve_trivia=False` → `_parser.py`, `preserve_trivia=True` → `_trivia_parser.py`. The only difference is whether trivia-append calls are emitted.

**Call pattern in plumbing.py** (lines 130-143, 302-316):
```python
terminals = terminalsrc.TerminalSource(text)
parser = SomeParser(terminalsrc=terminals)
result = parser.apply__parse_<rule>(0)
if not result or result.pos != len(terminals.terminals):
    error_msg = errors.format_error_message(
        parser.error_tracker, terminals, lambda rule_id: parser.rule_names[rule_id]
    )
```

---

## 6. Build and test touchpoints Phase 1 must satisfy

### 6.1 `make check` gate (`Makefile:9-22`)

Steps relevant to a new `fltk-parser-core` crate:
- `cargo-check` (line 40-41): `cargo check -q` — workspace-wide; picks up new crate automatically once added to `members`.
- `cargo-test` (line 43-44): `cargo test -q` — workspace-wide.
- `cargo-test-no-python` (line 51-53): currently tests `fltk-cst-core --no-default-features` and `fltk-cst-spike`. Phase 1 must add: `cargo test -q -p fltk-parser-core` (no `--no-default-features` needed; the crate has no `python` feature to disable).
- `cargo-clippy-no-python` (line 55-58): currently covers `fltk-cst-core --no-default-features`, `fltk-cst-spike`, `fltk-cst-spike --features python`. Must add `cargo clippy -q -p fltk-parser-core -- -D warnings`.
- `check-no-pyo3` (line 63-71): uses `cargo tree -p <crate> --edges normal,build` and asserts `pyo3` absent. Must add equivalent for `fltk-parser-core`: positive control (fltk-cst-core present in tree), negative assertion (pyo3 absent).

### 6.2 `check-no-pyo3` mechanics (`Makefile:63-71`)

```makefile
out="$(cargo tree -p fltk-cst-spike --edges normal,build)"
# positive control: fltk-cst-core present
! echo "$out" | grep -q pyo3  # negative: pyo3 absent
core="$(cargo tree -p fltk-cst-core --no-default-features --edges normal,build)"
! echo "$core" | grep -q pyo3
```

For `fltk-parser-core`: `cargo tree -p fltk-parser-core` (no `--no-default-features` needed). The positive control checks `fltk-cst-core` is in the tree (it's a dependency); negative checks pyo3 absent.

### 6.3 `cargo-test-no-python` isolation note (`Makefile:49-53`)

The comment on line 49: `-p selection` is required because workspace feature unification would re-enable pyo3 via `fltk-native`'s dependency. `fltk-parser-core` is always pyo3-free, so `-p fltk-parser-core` (without `--no-default-features`) suffices — no feature union issue.

---

## 7. Codepoint/byte boundary — key facts for `TerminalSource` implementation

All positions throughout the Python runtime are **Unicode codepoint indices** (matching Python `str` indexing):
- `terminalsrc.py:165`: `self.terminals_len = len(terminals)` — codepoint count
- `terminalsrc.py:168-175`: `consume_literal` iterates `self.terminals[pos + i]` — codepoint indexing
- `terminalsrc.py:177`: `re.compile(regex).match(terminals, pos=pos)` — Python `re.match(pos=...)` takes a codepoint offset; Python `re` then handles byte offset conversion internally
- `span.rs:133`: doc comment confirms codepoint semantics: "start and end are Unicode codepoint indices, matching Python's string indexing semantics"

Rust `TerminalSource` must maintain a `Vec<usize>` codepoint→byte-offset table built once at construction. Design spec (design.md §3.1): `consume_regex` calls `Regex::find_at(full_text, byte_pos)` (not a slice) to preserve `\b`/`^` semantics.

`pos_to_line_col` in Python (terminalsrc.py:183-205): lazily computes `line_ends` as codepoint indices of `\n` characters. Returns `LineColPos { line: int, col: int, line_span: Span }`. The `line_span` uses codepoint indices. In format_error_message (errors.py:60): `terminals.terminals[error_linecol.line_span.start : error_linecol.line_span.end]` — byte-slice of the Python str (works because Python slicing uses codepoints).

---

## 8. Open factual questions

1. **`TerminalSource` re-exports**: design.md §3.1 says `fltk-parser-core` re-exports `pub use regex;`. The generated parser references `fltk_parser_core::regex::Regex`. No existing precedent for this pattern in the current codebase — `fltk-cst-core` does not re-export any dependency.

2. **`SourceText` ownership in `TerminalSource`**: design.md §3.1 says `TerminalSource` holds a `SourceText` (single owner). Spans produced by `consume_literal`/`consume_regex` are `Span::new_with_source(start, end, &self.source_text)`. Since `SourceText::inner` is `Arc<SourceInner>`, `new_with_source` clones the `Arc` — O(1), no text copy. `TerminalSource::source_text()` accessor gives the generated parser a `&SourceText` to pass to `Span::new_with_source`.

3. **`format_error_message` signature**: Python takes `TerminalSource` as a concrete type (errors.py:55). Rust equivalent will take `&TerminalSource`. The `rule_name_lookup` is `fn(u32) -> &str` or equivalent; the generated parser passes a static table.

4. **`pos_to_line_col` laziness**: Python builds `line_ends` lazily on first call. Rust can build at construction (always O(n)) or lazily with `OnceLock`. For unit tests this distinction is irrelevant; for large grammars laziness avoids work if no error occurs. Either is a valid implementation choice.
