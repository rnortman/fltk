# Quality review: rust-fltkfmt increments 1–3

Commit range: `61fc5e8..1b48755`

---

## quality-1 — Stale test assertions left broken across four commits via `--no-verify`

**File:line**: `tests/test_rust_unparser_generator.py:1968-1981` and `2035-2052`

**Issue**: The generator fix in increment 1 (`e5bb7ec`) correctly changed `_gen_has_preservable_trivia_method` and `_gen_count_newlines_in_trivia_method` to emit `if let` forms instead of `match { Variant => …, _ => {} }` when the trivia child enum has more than one variant. Two tests were not updated to match the new emitted form:

- `test_count_newlines_in_trivia_multi_variant_emits_catchall` (line 1968) still asserts `"cst::TriviaChild::Span(span) => {"` and `"_ => {}"` (the old match syntax). The generator now emits `if let cst::TriviaChild::Span(span) = &child.1 {`.
- `test_has_preservable_trivia_matches_configured_node_types` (line 2035) still asserts `"cst::TriviaChild::Comment(_) => return true,"` and `"_ => {}"`. The generator now emits a bare `if let cst::TriviaChild::Comment(_) = &child.1 {` / `return true;` body.

Both tests were confirmed failing at review time (`uv run pytest` shows 2 failed). All three subsequent commits (`7df6761`, `ff7d198`, `1b48755`) used `--no-verify` to bypass the pre-commit hook, carrying these failures across the entire branch.

**Consequence**: The tests now permanently document behavior that the code does not exhibit — they have become false-positive detectors. A future generator change that accidentally reverts to the match-plus-wildcard form would let these tests pass again, masking a regression. Carrying known failures via `--no-verify` across unrelated commits also establishes a precedent that makes it harder to distinguish "known stale" from "newly broken" in code review. The fix is trivial (two test body updates), so the deferral has no technical justification.

**Fix**: In the same branch, update both tests to assert the `if let` form the generator now emits:

- `test_count_newlines_in_trivia_multi_variant_emits_catchall`: replace assertions on `"cst::TriviaChild::Span(span) => {"` and `"_ => {}"` with assertions on `'if let cst::TriviaChild::Span(span) = &child.1 {'` and absence of `"_ => {}"`.
- `test_has_preservable_trivia_matches_configured_node_types`: replace assertions on `"cst::TriviaChild::Comment(_) => return true,"` and `"_ => {}"` with assertions on `'if let cst::TriviaChild::Comment(_) = &child.1 {'` and `"return true;"` on a separate line.

---

## quality-2 — Grammar-specific `about` text baked into generic scaffolding struct

**File:line**: `crates/fltk-fmt-cli/src/lib.rs:20`

```rust
#[command(version, about = "Format FLTK grammar files.")]
pub struct FmtArgs {
```

**Issue**: `fltk-fmt-cli` is designed as "shared, publishable infrastructure that downstream formatter crates depend on" (design §2.2). `FmtArgs` is the public struct that every consumer binary will use to parse its command line. The hardcoded `about = "Format FLTK grammar files."` refers specifically to `.fltkg` files. A downstream FLTK consumer building a formatter for their own grammar (e.g., a configuration language or DSL) will inherit this description verbatim in their binary's `--help` output, misleading their end users.

clap's `#[derive(Parser)]` on a library struct does not offer a mechanism for the calling binary to override `about` after the fact — the text is frozen at the library's compile time. The `fltk_formatter_main!` macro (increment 4) will call `FmtArgs::parse()` with no hook to inject a per-consumer description, so the problem will be sealed in once the macro ships.

**Consequence**: Every non-`fltkfmt` binary built on `fltk-fmt-cli` will display "Format FLTK grammar files." when users run `--help`, regardless of what language that binary actually formats. This couples a generic abstraction to one specific grammar type, making the crate misleading in every other use case. Because `FmtArgs::parse()` is called inside `run_main`, fixing this post-macro will require either a breaking API change (new parameter to `run_main`) or forking `FmtArgs` (defeating the reuse purpose).

**Fix**: Remove the `about` from `FmtArgs`'s `#[command]` attribute (or replace it with `about = env!("CARGO_PKG_DESCRIPTION")` so it resolves to the consuming crate's package description). Add an `about: &'static str` key to the `fltk_formatter_main!` macro so each consumer supplies their own binary description. The `fltkfmt` invocation would pass `about: "Format .fltkg grammar files."` and other consumers supply their own text. This is a one-line addition per consumer and removes the last grammar-specific string from the scaffolding crate.
