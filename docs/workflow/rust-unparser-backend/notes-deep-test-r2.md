# Test review — batch 2 (rust-unparser-backend)

Reviewed commit range d5914359..e65e4f66.
Files in scope: `crates/fltk-unparser-core/src/render.rs`, `crates/fltk-unparser-core/src/result.rs`, `fltk/unparse/gsm2unparser_rs.py`, `tests/test_rust_unparser_generator.py`.

---

## test-1

**File:line** `crates/fltk-unparser-core/src/render.rs:990–997`

**What's wrong** The only `#[should_panic]` test for the unresolved-spec path in `render()` constructs `Doc::AfterSpec`. The other three variants handled by the same match arm — `Doc::Join`, `Doc::BeforeSpec`, `Doc::SeparatorSpec` — are never passed to `render()` in any test.

**Consequence** A refactor that accidentally narrows the match arm (e.g., removes one of the three variants) would go undetected. Compilation continues to succeed because the compiler does not enforce that every pattern actually panics; only a runtime test catches the regression.

**Fix** Add one `#[should_panic(expected = "Unknown document type")]` test each for `Doc::Join` and `Doc::BeforeSpec` (or at minimum one more variant), mirroring the `unresolved_spec_panics` structure. `SeparatorSpec` can be covered by symmetry if the other two are added.

---

## test-2

**File:line** `crates/fltk-unparser-core/src/render.rs` (test module, no existing test)

**What's wrong** The Python test suite has `test_multiple_subgroups_algorithm_limitation`, which verifies that an outer group containing three sibling sub-groups (`group1 line() group2 line() group3`) breaks when their combined flat width exceeds `max_width`, even though each sub-group alone would fit. No Rust test covers this sibling-group scenario. The existing Rust tests (`parent_breaks_before_child`, `broken_child_forces_parent_break`) cover a parent/child nesting axis, not the sibling-groups axis.

**Consequence** A port-level defect in how `fits()` accumulates width across sibling groups — for instance if the queue state is not properly propagated between siblings — would not be caught by any existing test.

**Fix** Add a test:
```rust
let g1 = group(concat(vec![text("short"), line(), text("one")]));   // "short one" = 9
let g2 = group(concat(vec![text("also"), line(), text("short")]));  // "also short" = 10
let g3 = group(concat(vec![text("tiny")]));                          // "tiny" = 4
let outer = group(concat(vec![g1, line(), g2, line(), g3]));
// "short one also short tiny" = 25 chars, max_width=24 → outer must break
assert_eq!(
    render_with(RendererConfig { indent_width: 4, max_width: 24 }, outer),
    "short one\nalso short\ntiny"
);
```

---

## test-3

**File:line** `tests/test_rust_unparser_generator.py:17–27` (`test_generate_emits_header_and_struct`)

**What's wrong** The test checks for the presence of the doc comment, the `use` import, and struct/constructor tokens, but does not assert that `#![allow(non_snake_case)]` is emitted. The generator emits this attribute at `gsm2unparser_rs.py:89` because later increments will emit function names like `unparse_{rule}__alt{N}__item{M}` that violate Rust's snake_case convention.

**Consequence** If the attribute is dropped during a generator refactor, the omission is not caught until the Rust crate is built (added in a later increment), at which point the compiler emits warnings or errors for every generated function name. The batch-2 generator tests should catch this regression early.

**Fix** Add `assert "#![allow(non_snake_case)]" in src` to `test_generate_emits_header_and_struct`.

---

## test-4

**File:line** `tests/test_rust_unparser_generator.py:22` (`test_generate_emits_header_and_struct`)

**What's wrong** `assert "use fltk_unparser_core::{" in src` confirms only that the import block opens; it does not verify any of the six symbols the generator is supposed to import (`DocAccumulator`, `Doc`, `UnparseResult`, `RendererConfig`, `Renderer`, `resolve_spacing_specs`).

**Consequence** If a generator change accidentally drops or misspells a required symbol — for example removing `Renderer` or `UnparseResult` from the use list — the test still passes. The regression would not surface until the Rust crate compiles in a later increment.

**Fix** Spot-check at least the symbols that are structurally significant to the generator's contract and not yet exercised by compilation. Minimal additions to `test_generate_emits_header_and_struct`:
```python
assert "Renderer" in src
assert "UnparseResult" in src
assert "resolve_spacing_specs" in src
```

---

## test-5

**File:line** `tests/test_rust_unparser_generator.py:30–33` (`test_generate_source_name_in_header`)

**What's wrong** The only `source_name` value tested is `"greeting.fltkg"`, which contains no characters that exercise the `_rust_str_lit` escaping path (backslash → `\\`, double-quote → `\"`, control chars → `\u{xx}`). The generator applies `_rust_str_lit` to the source name before embedding it in a `//!` doc-comment line (`gsm2unparser_rs.py:83–84`), but this escaping behavior is never exercised by any test.

**Consequence** A source name that is a Windows path (`path\to\grammar.fltkg`) or contains a quote would produce a silently wrong doc-comment line, and no test would catch it.

**Fix** Add a test with a source name containing a backslash, e.g.:
```python
src = RustUnparserGenerator(
    parse_grammar(_SIMPLE_GRAMMAR), source_name=r"path\to\grammar.fltkg"
).generate()
# Confirm the expected rendering of the escaped (or literal) path appears.
assert r"path" in src and "grammar.fltkg" in src
```
The exact expected string depends on the intended escaping contract for doc comments, but the test should at minimum confirm no crash and a deterministic output.
