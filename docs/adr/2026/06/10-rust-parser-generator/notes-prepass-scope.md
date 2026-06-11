## scope-1

**File:** `fltk/fegen/gsm2parser_rs.py` — missing generated regex compile test emission (design §2.4)

**Expected:** Generator emits a `#[cfg(test)] mod generated_regex_tests` block with `all_regex_patterns_compile` test at the end of every generated file when the regex table is non-empty (design §2.4, verbatim code shown).

**Actual:** No such block emitted. Confirmed by inspecting `gsm2parser_rs.py` (no `generated_regex_tests` anywhere in the generator), and verifying the committed generated files (`tests/rust_parser_fixture/src/parser.rs`, `tests/rust_cst_fegen/src/parser.rs`) contain no `cfg(test)` content.

**Consequence:** The design-mandated compile-time gate that catches unsupported regex patterns in downstream consumers' `cargo test` does not exist. A grammar regex rejected by the `regex` crate will fail at runtime (panic in `regex_at`) rather than at `cargo test` time, defeating the design's stated enforcement goal for controlling design §3.1. All downstream consumers are silently missing this test.

**Suggested fix:** Add a `_gen_regex_compile_test` method to `RustParserGenerator` that emits the §2.4 block; call it from `generate()` after the function bodies when `self._regex_patterns` is non-empty. Regenerate both fixture `parser.rs` files.

---

## scope-2

**File:** `Makefile:51-61` — `cargo-test-no-python` and `cargo-clippy-no-python` not extended for Phase 2 fixture crates (design §2.7)

**Expected:** Design §2.7 specifies: add `cargo test -q --manifest-path tests/rust_parser_fixture/Cargo.toml` to `cargo-test-no-python`; add `cargo test -q --manifest-path tests/rust_cst_fegen/Cargo.toml --no-default-features` to `cargo-test-no-python`; corresponding `cargo clippy -D warnings` entries in `cargo-clippy-no-python`; and `cargo check -q --manifest-path tests/rust_cst_fegen/Cargo.toml` (default features) in `cargo-check`.

**Actual:** `cargo-test-no-python` (lines 51-55) and `cargo-clippy-no-python` (lines 57-61) and `cargo-check` (line 41) are unchanged from before this diff — they reference only workspace crates (`fltk-cst-core`, `fltk-cst-spike`, `fltk-parser-core`). The standalone fixture crates in `tests/rust_parser_fixture/` and `tests/rust_cst_fegen/` are never invoked by `make check`. Convenience targets `test-native-parser` and `test-rust-parser-fixture` exist but are not wired into `check`.

**Consequence:** `make check` does not test or lint the generated parser code in the two fixture crates. The fixtures can contain compile errors, correctness bugs, or clippy violations and pass CI undetected. The design's stated "artifacts gated" claim (§2.7 "Phase 2 lands with its artifacts gated") is not met.

**Suggested fix:** Per design §2.7, add to `cargo-test-no-python`: `cargo test -q --manifest-path tests/rust_parser_fixture/Cargo.toml` and `cargo test -q --manifest-path tests/rust_cst_fegen/Cargo.toml --no-default-features`. Add corresponding clippy lines to `cargo-clippy-no-python`. Add `cargo check -q --manifest-path tests/rust_cst_fegen/Cargo.toml` (default features) to `cargo-check`.

---

## scope-3

**File:** `fltk/fegen/test_data/rust_parser_fixture.fltkg` — fixture grammar does not cover left recursion (direct or indirect) or multibyte literals/regex (design §2.6 B)

**Expected:** Design §2.6 B: fixture grammar covers "direct + indirect left recursion" and "a multibyte literal + a regex matching multibyte text."

**Actual:** The committed `rust_parser_fixture.fltkg` has rules `num`, `name`, `atom`, `paren_expr`, `stmt`, `items`, `opt_item`, `zero_items`. No rule refers back to itself or creates a left-recursive cycle. No multibyte literal or regex is present. The grammar header comment (`// Covers: ...`) does not mention left recursion or multibyte — this is not presented as a deliberate deviation; it appears to be an omission.

**Consequence:** The left-recursion wiring test described in §2.6 B ("direct + indirect left recursion parses with correct associativity/nesting and terminates") and the multibyte span assertion are never exercised by Rust-side `cargo test`. These are the only grammar features that cannot be tested via Python's dynamic grammar compilation, so they have zero automated coverage.

**Suggested fix:** Add left-recursive rules (e.g., `expr := expr:expr "+" rhs:atom | atom:atom`) and at least one rule with a multibyte literal (e.g., `uni := "→"`) or multibyte-matching regex to the fixture grammar. Regenerate `cst.rs` and `parser.rs`. Add native_tests covering associativity/termination for the left-recursive rule and codepoint-offset assertions for the multibyte rule.

---

## scope-4

**File:** `tests/rust_parser_fixture/src/native_tests.rs` — missing test cases required by design §4 test plan item 3

**Expected:** Design §4 test plan item 3 for `rust_parser_fixture/native_tests.rs` specifies: sub-expression inlining (`extend_children` results); memo sharing via `Shared::ptr_eq`; `error_position()` on failure inputs; out-of-range and negative `pos` (non-nullable rule → `None`; nullable rule → empty match); the generated regex-compile test.

**Actual:** Present tests cover: basic parse/fail for each rule, WS_REQUIRED pass/fail, `+`/`?`/`*` quantifiers, `capture_trivia` on/off, `error_message`/`rule_names`. Missing: no `Shared::ptr_eq` test (memo sharing); no `error_position()` call; no out-of-range or negative `pos` tests; no sub-expression inlining structural assertion (only presence check, not children shape). The generated regex compile test is absent from the generator itself (scope-1).

**Consequence:** Memo sharing correctness, `error_position` API, and boundary-`pos` behavior are untested at the Rust level. The design states these as explicit test cases because they pin Python-equivalent behavior.

**Suggested fix:** Add test cases: call `apply__parse_<rule>` twice at the same position and assert `Shared::ptr_eq` on the results; call `parser.error_position()` on a failing parse and assert `is_some()`; call `apply__parse_num(-1)` and `apply__parse_num(999)` asserting `None`; call a nullable rule (e.g., `apply__parse_zero_items(-1)`) asserting `Some` with `pos == -1` (or 0, depending on empty-span semantics).

---

*Aggregate assessment:* scope-1, scope-2, and scope-3 together represent implementation work that is not incidental (scope-1 is a generator feature, scope-2 is build wiring, scope-3 requires new grammar content + Rust tests). The design explicitly specifies all three and presents them as requirements for landing green. However, none requires architectural rethinking — each is a targeted addition to existing code. scope-4 is minor test-completeness work.
