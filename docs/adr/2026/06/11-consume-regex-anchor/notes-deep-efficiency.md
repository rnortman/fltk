# Deep efficiency review — consume-regex-anchor

Style: concise, precise, complete, unambiguous. No padding, no preamble.

Reviewed: `git diff 32a6c4e..097ea96` (HEAD 097ea96).

The change itself is an efficiency fix (anchored O(1)-reject vs O(N) scan-and-discard) and is implemented correctly for that purpose: `Input::span` per call is allocation-free; `Anchored::Yes` is served by fast engines (meta builds forward DFAs/hybrid with start-state support for anchored searches — verified in `regex-automata-0.4.14/src/meta/wrappers.rs:880-930`); the removed `m.start()` branch is correctly downgraded to `debug_assert_eq!` (free in release).

## efficiency-1: default `regex-automata` features are a strict superset of what `regex = "1"` shipped — extra compile time/binary size for every downstream consumer, and `Regex::new` behavior diverges from the design's "config-identical" claim

- **Where**: `crates/fltk-parser-core/Cargo.toml:16` (`regex-automata = "0.4"`, default features).
- **Problem**: `regex 1.x`'s default features enable `regex-automata`'s `hybrid`, `dfa-onepass`, `nfa-backtrack`, etc. — but **not** `dfa-build`/`dfa-search` (those sit behind the non-default `perf-dfa-full` feature; verified in `regex-1.12.3/Cargo.toml:61-95`). `regex-automata`'s default feature set includes `dfa = ["dfa-build", "dfa-search", "dfa-onepass"]` (`regex-automata-0.4.14/Cargo.toml:66-79`). Two consequences:
  1. The full-DFA determinizer and dense-DFA search code is now compiled into `fltk-parser-core` and every downstream consumer crate, where it never was under `regex = "1"`.
  2. `meta::Config::get_dfa()` returns `self.dfa.unwrap_or(true)` **when `dfa-build` is enabled** (`regex-automata-0.4.14/src/meta/regex.rs:3223-3228`), so `meta::Regex::new` now attempts full-DFA construction per pattern — something `regex::Regex::new` under its own feature set never does. The design's §3 "config-identical to `regex::Regex::new`" claim compares config values but misses that the *feature set* flips this default.
- **Consequence**: (a) one-time, per-build: longer `cargo build` and larger binaries for `fltk-parser-core` and all out-of-tree consumer crates (the determinizer + dense DFA modules are nontrivial); (b) one-time, per-process, per-pattern (behind the generated `OnceLock`s): a bounded full-DFA build attempt at first use of each regex — tightly capped (NFA state limit 30, small size limit, `meta/regex.rs:3157-3186`) and usually a *search-speed win* for the small grammar regexes, so runtime cost is negligible; the recurring cost is build-side. Bites every downstream consumer on every compile, forever.
- **Fix/direction**: either pin the feature set to what `regex 1` actually used — `regex-automata = { version = "0.4", default-features = false, features = ["std", "syntax", "perf", "unicode", "meta", "nfa-backtrack", "nfa-pikevm", "hybrid", "dfa-onepass"] }` — which also restores the literal `get_dfa() == false` parity the design argues for; or keep defaults deliberately (the full-DFA path is a search-time optimization) and amend the design/doc to state the compile-time/binary-size cost and the `get_dfa` divergence explicitly instead of "config-identical". Design §2.1 chose defaults on a semantics argument only; the cost side was not weighed.

## Non-findings (checked, fine)

- `Input` construction per `consume_regex` call: stack-only builder, no allocation.
- Workspace `Cargo.lock` still contains `regex 1.12.4`: dev-dependency via `criterion` only; not shipped.
- `consume_regex` byte→codepoint binary search and `cp_to_byte` lookup: unchanged from base.
- Generated `all_regex_patterns_compile` test recompiles patterns: test-time only.

Reviewed commit: 097ea96.
