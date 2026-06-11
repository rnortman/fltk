# Escalation: scope findings require re-entering implementation

The four scope findings collectively represent significant net-new implementation
work that was specified in the design but not shipped. Handling them as Fixed in
respond mode would bypass incremental scoping; marking them TODO would
retroactively narrow a design that was declared done. Escalation is warranted.

---

## scope-1 — Generator missing `_gen_regex_compile_test` (design §2.4)

**What's missing:** `RustParserGenerator` has no `_gen_regex_compile_test` method
and `generate()` does not call it. Neither committed `parser.rs` (rust_cst_fegen
nor rust_parser_fixture) contains the `#[cfg(test)] mod generated_regex_tests`
block that design §2.4 specifies verbatim.

**Rationale for escalation:** This is a new generator method + call site + two
regenerated committed `.rs` files. It's a generator feature, not a one-line omission.

---

## scope-2 — `make check` does not gate the fixture crates (design §2.7)

**What's missing:** `cargo-test-no-python`, `cargo-clippy-no-python`, and
`cargo-check` in the Makefile are unchanged from before Phase 2. The design
specifies adding `cargo test -q --manifest-path tests/rust_parser_fixture/Cargo.toml`,
`cargo test -q --manifest-path tests/rust_cst_fegen/Cargo.toml --no-default-features`,
corresponding clippy lines, and `cargo check -q --manifest-path tests/rust_cst_fegen/Cargo.toml`.

**Rationale for escalation:** 4-5 Makefile lines, but they're what makes the
design's "Phase 2 lands with its artifacts gated" claim true. Without them
`make check` does not test or lint the fixture crates.

---

## scope-3 — Fixture grammar missing left recursion + multibyte coverage (design §2.6 B)

**What's missing:** `rust_parser_fixture.fltkg` has no left-recursive rule (direct
or indirect) and no multibyte literal or regex. Design §2.6 B explicitly requires
both as the only grammar features that cannot be tested via Python's dynamic grammar
compilation. Rust-side tests for associativity/termination and codepoint-offset
assertions are consequently absent from `native_tests.rs`.

**Rationale for escalation:** Requires new grammar rules + regenerating `cst.rs` and
`parser.rs` for the fixture crate (committed artifacts) + new Rust test functions.
This is not a one-line patch.

---

## scope-4 — Missing Rust test cases in `rust_parser_fixture/native_tests.rs` (design §4 item 3)

**What's missing:** `Shared::ptr_eq` memo-sharing test; `error_position()` on a
failing parse; out-of-range and negative `pos` tests (non-nullable → `None`;
nullable → empty match). The generated regex-compile test is also absent (covered
by scope-1).

**Rationale for escalation:** Scope-4 is smaller than scope-3 (it's adding test
functions to an existing file), but it is bound to scope-3 (the left-recursion
and multibyte tests live in the same file) and to scope-1 (the regex-compile
test appears in the generated file, not hand-written). All four scope findings
are coupled: scope-1 must land before scope-3/4 can be verified green under
`make check` (scope-2).

---

## Recommendation

Resume incremental mode. Suggested increments (each small enough to be atomic):

1. scope-1: add `_gen_regex_compile_test` to generator; regenerate both `parser.rs` files.
2. scope-2: add the four Makefile lines; verify `make check` green.
3. scope-3 + scope-4: extend `rust_parser_fixture.fltkg` with left-recursive and
   multibyte rules; regenerate `cst.rs` + `parser.rs`; add the Rust test cases
   (left recursion, multibyte, `Shared::ptr_eq`, `error_position`, boundary `pos`).
