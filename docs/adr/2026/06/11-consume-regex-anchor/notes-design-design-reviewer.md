# Design review notes: consume-regex-anchor

No findings.

Verification record (all claims checked against source at base 7ddec4a):
- File/line citations accurate: `terminalsrc.rs:148-169` (find_at + start check), `lib.rs:22` (`pub use regex`), `gsm2parser_rs.py:271/307-320/941/6-13`, fixture `parser.rs:12` in both fixture crates.
- `regex` dep removal safe: only `lib.rs` and `terminalsrc.rs` reference it; fixture Cargo.tomls declare no direct `regex` dep; `make gencode` regenerates both fixture parsers (`build-fegen-rust-parser`, `gen-rust-parser` targets, Makefile:126-131,180-183).
- Config parity verified in vendored sources: `regex-1.12.3/src/builders.rs:50-57` sets `nfa_size_limit(10*(1<<20))` + `hybrid_cache_capacity(2*(1<<20))` (= meta defaults, `regex-automata-0.4.14/src/meta/regex.rs:3134,3151`); `build_one_string` (builders.rs:70-85) additionally sets `match_kind(LeftmostFirst)`, `utf8_empty(true)`, syntax `utf8(true)` — all also equal meta/syntax defaults (regex.rs:3095-3096,3103-3105), so the design's "config-identical" conclusion holds and its "leftmost-first, utf8_empty on" statement covers them.
- API claims accurate: `meta::Regex::new(&str) -> Result<Regex, BuildError>` (meta/regex.rs:302), `search(&Input) -> Option<Match>` (meta/regex.rs:919); `Anchored`/`Input` re-exported at `regex_automata` root.
- Feature superset claim accurate: regex-automata defaults = regex's enabled set + `dfa-build`/`dfa-search` (Cargo.toml feature maps of both crates).
- Requirements coverage complete: anchored fix, re-export/generator/test updates, fixture regen, byte-identical equivalence argument, config-parity confirmation (explicit request item), regression-guard test kept, new `\Bello` context test, generator emission assertion, no timing asserts, TODO bookkeeping (TODO.md:35 entry + sole code site terminalsrc.rs:145). No scope creep; internally consistent.
