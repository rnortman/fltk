Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 097ea96

## quality-1

**File:line** `fltk/fegen/gsm2parser_rs.py:989` (generator source); also in every generated file, e.g. `tests/rust_cst_fegen/src/parser.rs:1343` and `tests/rust_parser_fixture/src/parser.rs:1226`.

**Issue** The panic message inside `all_regex_patterns_compile` reads `"not supported by the regex crate"` — the old crate name. After this change the type is `regex_automata::meta::Regex`; the message is factually wrong.

**Consequence** When a downstream consumer writes an unsupported grammar regex and this test fires, the diagnostic names the wrong crate, making the error harder to act on. Because the message is emitted by the generator, every future downstream-generated parser inherits the stale string until it is fixed in the generator; the error will propagate to all new consumers.

**Fix** In `_gen_regex_compile_test` (gsm2parser_rs.py line 989), change the panic string to name `regex-automata` (or `regex_automata::meta::Regex`) instead of `the regex crate`. Regenerate the two fixture parsers.

---

## quality-2

**File:line** `fltk/fegen/gsm2parser_rs.py:7-8` (module docstring).

**Issue** The docstring still says "the Rust `regex` crate" twice: "grammar regexes must use the common subset of Python `re` and the Rust `regex` crate" and "the Rust `regex` crate rejects them at compile time." The runtime crate is now `regex-automata`; the `regex` crate is no longer a dependency.

**Consequence** The docstring is the first thing a developer reads to understand the regex constraint. The wrong crate name sends them to the wrong documentation and makes the constraint harder to verify. It also contradicts the updated sentence directly below it that names `regex_automata::meta::Regex::new`.

**Fix** Replace both occurrences of "the Rust `regex` crate" with "the Rust `regex-automata` crate" (or "`regex_automata::meta::Regex`"). Keep the "common subset" framing accurate: the syntax is the same (`regex-syntax` is shared), but the runtime type is `regex_automata`. A precise wording: "grammar regexes must use the common subset of Python `re` and `regex-syntax` (shared by both the `regex` and `regex-automata` crates). Lookahead, lookbehind, and backreferences are not supported; `regex_automata::meta::Regex` rejects them at compile time."
