# Design: anchored regex matching in consume_regex

Style: concise, precise, complete, unambiguous. No padding, no preamble. All docs in this workflow follow this style.

Requirements: `request.md` in this dir. Validation: `exploration.md` in this dir.

## 1. Root cause / context

`TerminalSource::consume_regex` (`crates/fltk-parser-core/src/terminalsrc.rs:148-169`) calls `regex::Regex::find_at(text, byte_pos)`, which performs an *unanchored* leftmost search over `[byte_pos, len)`. On non-match at `byte_pos` the engine scans the rest of the haystack before failing; the `m.start() != byte_pos` check at `terminalsrc.rs:155-158` then discards forward matches. Correctness is fine; the scan cost is wasted. With packrat memoization bounding calls to O(R×N) and each failing call costing up to O(N), worst case is O(R×N²) — a complexity DoS on untrusted input. Python's `re.match(pos=...)` anchors and fails immediately; the Rust backend should match that cost profile.

`regex::Regex` offers no anchored-at-offset API, and `\A`-prepending anchors to haystack byte 0, not span start (exploration §5). The fix must drop to `regex_automata::meta::Regex` (exploration §7, §9).

## 2. Proposed approach

Switch the regex type used by the runtime and generated code from `regex::Regex` to `regex_automata::meta::Regex`, and perform an anchored span search.

### 2.1 `crates/fltk-parser-core/Cargo.toml`

- Remove `regex = "1"`.
- Add `regex-automata = "0.4"` (default features).

Nothing else in the crate uses `regex` after this change. Default `regex-automata` features are a superset of what `regex = "1"` enables (adds full-DFA build/search); all `regex-automata` engines implement identical match semantics by that crate's documented contract, so the superset can only change internal strategy selection, never results.

### 2.2 `crates/fltk-parser-core/src/lib.rs`

- Replace `pub use regex;` with `pub use regex_automata;`.
- Update the crate-level "Re-exports" doc: same version-coherence rationale, new crate name. Generated code references `fltk_parser_core::regex_automata::meta::Regex` exclusively; consumer crates need no direct `regex-automata` dependency.

This is a breaking change to `fltk-parser-core`'s API, explicitly sanctioned by the request ("This changes types inside the generated parser file and `fltk-parser-core`'s API"). Generated `.rs` internals and the runtime crate version together; downstream consumers regenerate parsers when updating the runtime crate. No Python-visible or CST-node surface changes.

### 2.3 `crates/fltk-parser-core/src/terminalsrc.rs`

- Imports: `use regex_automata::meta::Regex;` and `use regex_automata::{Anchored, Input};` (replacing `use regex::Regex;`).
- `consume_regex(&self, pos: i64, regex: &Regex)` signature keeps its shape; only the `Regex` type changes. Body:

  ```rust
  let byte_pos = self.cp_to_byte[pos as usize];
  let text = self.text();
  let input = Input::new(text)
      .anchored(Anchored::Yes)
      .span(byte_pos..text.len());
  let m = regex.search(&input)?;
  debug_assert_eq!(m.start(), byte_pos, "anchored search must start at the search span start");
  ```

  The runtime `if m.start() != byte_pos { return None; }` check becomes a `debug_assert_eq!`: `Anchored::Yes` guarantees any match begins at the span start (`regex-automata` `search.rs:251-252`, exploration §7). Byte→codepoint end conversion is unchanged.
- Doc comment: replace the "Complexity note" paragraph and the `TODO(consume-regex-anchor)` comment with a statement of the anchored semantics: full haystack passed via `Input::span` so `\b`/`\B` resolve against the character before `byte_pos` (matching Python `re.match(pos=...)`), and non-match at `byte_pos` fails without scanning. Fix the "look-behind" wording — the `regex` syntax has no look-behind; `\b`/`\B` context is the preserved feature (exploration §4).
- Unit tests: change `regex::Regex::new(...)` to the imported meta `Regex::new(...)` (same constructor signature, `Result<Regex, BuildError>`). All existing assertions stay, including `consume_regex_anchor_rejection` (kept as the anchored-semantics regression guard) and `consume_regex_empty_match_at_end` (pins `Input::span(len..len)` empty-match behavior).

### 2.4 `fltk/fegen/gsm2parser_rs.py`

Four emission sites plus the docstring:

- `_gen_header` (line 271): emit `use fltk_parser_core::regex_automata::meta::Regex;` instead of `use fltk_parser_core::regex::Regex;`.
- `_gen_constants` (lines 307-320): `REGEX_CELLS: [OnceLock<Regex>; N]`, `regex_at`, and `Regex::new(REGEX_PATTERNS[idx])` are textually unchanged — the `Regex` name now resolves to `meta::Regex`. `meta::Regex::new` has the same signature and its `BuildError` implements `Display`, so the `panic!("invalid regex pattern {:?}: {e}", ...)` format string is unchanged.
- `_gen_regex_compile_test` (line 941): emit `fltk_parser_core::regex_automata::meta::Regex::new(pat)`. The test's purpose (reject unsupported syntax at consumer `cargo test` time) is preserved: `meta::Regex` uses the same `regex-syntax` parser and rejects look-around/backreferences identically.
- Module docstring (lines 6-13): keep the "common subset of Python `re` and the Rust `regex` crate" framing (the syntax *is* the `regex` crate's syntax — `regex-automata` shares `regex-syntax`); adjust the sentence naming `Regex::new` to note the generated test now compiles via `regex_automata::meta::Regex`.

### 2.5 Regenerate fixtures

`make gencode` (covers `tests/rust_cst_fegen/src/parser.rs` and `tests/rust_parser_fixture/src/parser.rs`, the only in-tree files referencing `fltk_parser_core::regex`), then `make fix`. The fixture crates declare no direct `regex` dependency (they use the re-export), so no fixture `Cargo.toml` changes.

### 2.6 TODO bookkeeping

Remove the `consume-regex-anchor` entry from `TODO.md` and the `TODO(consume-regex-anchor)` comment in `terminalsrc.rs` (the only code site).

## 3. Behavioral equivalence argument

Parse results must be byte-identical (request constraint). Equivalence of "anchored search at `byte_pos`" vs "unanchored leftmost search from `byte_pos` + start check":

- Unanchored leftmost search returns the *earliest-starting* match in `[byte_pos, len)`. If any match starts at `byte_pos`, leftmost search starts there, the start check passes, and leftmost-first semantics select the match end. If no match starts at `byte_pos`, either the search fails or returns a later start, which the check rejects → `None`.
- Anchored search considers exactly the matches starting at `byte_pos`, with the same leftmost-first selection from that start → same end, or `None` when none exists.

The accepted-match sets and selection rules are identical; only the wasted scan on the `None` path is eliminated.

Config parity (verified in vendored sources): `regex::Regex::new` builds `meta::Config::new().nfa_size_limit(Some(10 << 20)).hybrid_cache_capacity(2 << 20)` with default `syntax::Config` (`regex-1.12.3/src/builders.rs:50-57`); those two explicit values equal `meta::Config`'s own defaults (`regex-automata-0.4.14/src/meta/regex.rs:3134-3152`). So `meta::Regex::new(pattern)` is config-identical to `regex::Regex::new(pattern)`: same syntax defaults (Unicode on, UTF-8 on), same match semantics (leftmost-first, `utf8_empty` on). Existing grammar regexes compile and match identically; the generated `all_regex_patterns_compile` test plus the parity corpus verify this empirically.

## 4. Edge cases / failure modes

- **`pos == len` (empty match at end)**: `Input::span(len..len)` is valid; `a*` matches empty. Pinned by existing `consume_regex_empty_match_at_end` test.
- **`\b`/`\B` at `byte_pos > 0`**: the full haystack is passed; only the search start is constrained, so `\b`/`\B` assertions see the character before `byte_pos` (exploration §7). New test pins this (§5).
- **Empty-match-in-codepoint**: `utf8_empty` defaults on in both wrappers; empty matches cannot split a codepoint — same as before. The `debug_assert!` on `cp_to_byte` boundary lookup is unchanged and would catch any violation in debug builds.
- **Pattern compile failure**: `regex_at`'s panic path is unchanged (`BuildError: Display`); the generated compile test surfaces unsupported patterns at consumer `cargo test` time, as today.
- **Feature drift**: default `regex-automata` features ⊇ `regex`'s enabled set; strategy selection may differ (e.g. full DFA for small patterns) but match semantics are contractually identical across engines. Parity corpus is the backstop.
- **Out-of-tree consumers compiling against `fltk_parser_core::regex`**: removed re-export breaks them only when they update the runtime crate, at which point they regenerate parsers (runtime and generator version together). No Python-visible surface changes.

## 5. Test plan

After the change:

- **Existing** `terminalsrc.rs` unit tests, ported to `meta::Regex` construction with assertions unchanged — including `consume_regex_anchor_rejection` (matches at pos+2, not at pos → `None`; the anchored-semantics regression guard required by the request) and `consume_regex_empty_match_at_end`.
- **New** `terminalsrc.rs` unit test `consume_regex_context_before_pos`: text `"hello"`, pattern `\Bello`, `pos = 1` → matches (span 1..5). `\B` at position 1 requires seeing `h` before the search start; this fails under any slice-the-haystack implementation and pins the full-haystack `Input::span` behavior. (The existing `\b` tests cover the rejection side.)
- **Existing generator tests** (`fltk/fegen/test_gsm2parser_rs.py`): no current assertion names the `fltk_parser_core::regex` import path; add one assertion that generated source contains `use fltk_parser_core::regex_automata::meta::Regex;` to pin the new emission.
- **Regenerated fixtures**: `make gencode && make fix`; `cargo test` (workspace + `tests/rust_cst_fegen` + `tests/rust_parser_fixture`, including the generated `all_regex_patterns_compile` tests) and `uv run pytest` (including the parity corpus) all pass with no behavioral diffs.
- No timing-based assertions (request: perf demonstration optional, not asserted; omitted).

## 6. Open questions

None.
