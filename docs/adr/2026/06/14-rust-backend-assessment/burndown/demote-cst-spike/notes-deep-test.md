Commit reviewed: be08c47 (ad7174d + be08c47)

## Wiring — tests are NOT orphaned

The 43 tests from `crates/fltk-cst-spike/src/spike_tests.rs` are byte-for-byte identical to
the new `tests/rust_poc_cst/src/spike_tests.rs` (confirmed via diff: empty output).

`tests/rust_poc_cst/src/lib.rs` wires them in:

```rust
#[cfg(test)]
mod spike_tests;
```

`cargo-test-no-python` in the Makefile runs them:

```makefile
cargo test -q --manifest-path tests/rust_poc_cst/Cargo.toml --no-default-features
```

`cargo-test-no-python` is a named step in `check-common`, which is called by both `check` and
`check-ci`. Tests are alive and will run in CI.

## Coverage vs deleted crate — one gap found

### test-1

**File:** `tests/rust_poc_cst/src/lib.rs`
**What's wrong:** The old `crates/fltk-cst-spike/src/lib.rs` carried `#![cfg_attr(not(feature = "python"), forbid(unsafe_code))]`. That attribute was a compile-time enforcement that the python-off build of the spike never smuggled in unsafe code. The new `lib.rs` omits it entirely. There is no test or attribute that replaces this guard.
**Consequence:** If a future change to `cst.rs` or `spike_tests.rs` (or `fltk-cst-core`) introduces `unsafe` code in the python-off configuration, nothing will catch it at compile time. The regression would be silent — `cargo test` would still pass.
**Fix:** Add `#![cfg_attr(not(feature = "python"), forbid(unsafe_code))]` to `tests/rust_poc_cst/src/lib.rs`, matching what the deleted crate had.

### test-2

**File:** `Makefile`, `cargo-clippy` target
**What's wrong:** The old crate had two clippy runs for the python-on feature set:
`cargo clippy -q -p fltk-cst-spike -- -D warnings` (python-off, default) and
`cargo clippy -q -p fltk-cst-spike --features python -- -D warnings` (python-on).
The new `cargo-clippy` target runs `tests/rust_poc_cst` only once, without `--features python`:
`cargo clippy -q --manifest-path tests/rust_poc_cst/Cargo.toml -- -D warnings`.
The default feature set for `poc-cst` is `extension-module` (which enables `python`), so this
clippy run IS python-on by default — that part is fine. But `cargo-clippy-no-python` runs it
`--no-default-features` (python-off). The `spike_tests` module is compiled in both feature
configurations. Neither clippy run is clearly labeled as exercising `spike_tests` in python-off.
This is cosmetically inconsistent with the old explicit two-pass scheme but is functionally
equivalent: the two passes (default = python-on in cargo-clippy, no-default-features in
cargo-clippy-no-python) together cover both configurations. No coverage is actually lost.
**Consequence:** None (functional parity exists). Noting for completeness; this is informational
rather than a blocking finding.

## Quality assessment

All 43 tests are substantive. Every test asserts on a specific observable outcome — no smoke
tests, no vacuous `assert!(result.is_some())` patterns. Error-path tests (test-1 through the
`CstError` family) confirm the correct error variant, not merely "an error occurred." The full
set exercises construction, traversal, span text, merge, intersect, structural equality,
reference semantics (`Shared<T>`), Debug formatting, `kind()`, per-label read/write accessors,
and `CstError::Display`. Happy paths and error paths are both covered throughout.

The sole actionable finding is test-1 above: the dropped `forbid(unsafe_code)` attribute.
