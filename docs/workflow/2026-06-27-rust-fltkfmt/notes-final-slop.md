# Slop review — 2026-06-27-rust-fltkfmt

Commit reviewed: 7a699c396903a618711132240392279d52bcbc51

---

## slop-1

**File:** `crates/fltk-fmt-cli/src/lib.rs` — `validate()` tests block (~line 706–737 in diff)

**Quote:**
```rust
fn in_place_with_output_is_rejected() { ... }
fn in_place_with_check_is_rejected() { ... }
fn output_with_multiple_inputs_is_rejected() { ... }
// (no test for check + output)
```

**What's wrong:** `validate()` has six rejection branches. Five have corresponding unit tests. The `check && output.is_some()` branch (line 110 in diff, with its own explanatory comment) is never exercised. The code comment even explains why the check exists ("reject it rather than let the `check` branch win by dispatch order in `run_inner`"), but there is no test confirming that the validation fires.

**Consequence:** A reviewer counting tests against branches will notice the gap immediately. The comment acknowledges the subtlety (silent dispatch override), which makes the missing test conspicuous — it looks like someone explained the edge case but forgot to lock it down. The behavior is correct today, but there is no regression guard if the dispatch order in `run_inner` changes.

**Suggested fix:** Add `fn check_with_output_is_rejected()` alongside the other rejection tests:
```rust
#[test]
fn check_with_output_is_rejected() {
    let args =
        FmtArgs::try_parse_from(["fltkfmt", "--check", "-o", "out.fltkg", "in.fltkg"]).unwrap();
    assert_eq!(run_args_only(&args), 2);
}
```

---

## slop-2

**File:** `crates/fltk-fmt-cli/src/lib.rs` — test helper docstring (~line 592 in diff)

**Quote:**
```rust
/// Stub format_fn: returns the source unchanged.
fn identity(
    src: &str,
    _filename: Option<&str>,
    _cfg: RendererConfig,
) -> Result<String, String> {
    Ok(src.to_string())
}
```

**What's wrong:** The docstring "returns the source unchanged" restates the function name `identity` and the single-line body verbatim. It adds no information that `fn identity` does not already convey. The adjacent stubs (`upper` and `fail`) have docstrings that add value — "a visible, non-identity transform" and "models a parse error" — which makes this one stand out as filler.

**Consequence:** Classic LLM self-explanatory-comment tell. A reviewer scanning the test helper block will notice the hollow docstring against the substantive ones next to it.

**Suggested fix:** Drop the docstring, or replace it with the *why*:
```rust
/// No-op: used to verify that `--check` exits 0 when input is already formatted.
fn identity(...) {
```
