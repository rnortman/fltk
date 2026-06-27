## reuse-1

**File:line**: `tests/rust_parser_fixture/src/native_tests.rs:1008` (`render_native!` macro); new code at `crates/fltk-fmt-cli/src/lib.rs:206` (`fltk_formatter_main!` macro).

**What is duplicated**: Both macros inline the same parse → guard → unparse → resolve → render pipeline:

```
Parser::new(src, …, true)
  → parser.$parse(0)  [error on None]
  → consumed check
  → parsed.result.read()
  → Unparser::new().$unparse(&*guard)  [error on None]
  → resolve_spacing_specs(unparsed.doc())
  → Renderer::new(cfg).render(&resolved)
```

**Existing function/utility**: `render_native!` at `tests/rust_parser_fixture/src/native_tests.rs:1008` contains this pipeline verbatim. It pre-dates the new macro and was the "proven pipeline" the design cited as justification for the approach.

**Consequence**: The two macros already diverge on the consumed check — `render_native!` uses strict equality (`parsed.pos == src.chars().count() as i64`) while `fltk_formatter_main!` uses whitespace-tolerant `fully_consumed`. Any future change to the pipeline (new step, renamed function, changed signature for `resolve_spacing_specs` or `Renderer::new`) must be applied to both independently. De-duplication is not straightforwardly possible because `render_native!` panics and returns a `String` (test harness), while `fltk_formatter_main!` returns `Result<String, String>` through `run_main`; no shared trait bounds exist on the generated `Parser`/`Unparser` types that would allow a common callable.
