## slop-1

**File:** `crates/fltk-unparser-core/src/doc.rs` — helper constructors

**Quotes:**
```rust
/// Create a text node.
pub fn text(s: impl Into<String>) -> Doc {

/// Create an empty document.
pub fn nil() -> Doc {

/// Create a soft line break (space or newline).
pub fn line() -> Doc {

/// Indent content by `indent` when breaking.
pub fn nest(indent: u32, content: Doc) -> Doc {
```

**What's wrong:** The first two docstrings restate the identifier name verbatim. `text` creates a text node; `nil` creates an empty document — neither sentence carries information not already in the symbol. `nest`'s docstring echoes back the parameter name `indent` as the subject. `line`'s "(space or newline)" does add value but follows the same rote formula as the others.

**Consequence:** These read as auto-generated doc-comment filler (the canonical LLM tell). A reviewer or downstream consumer opening the rendered docs finds four one-liners that say nothing beyond the signature. It signals "LLM wrote stub docs and stopped," which undermines confidence in the commentary that does carry weight (the `concat`, `drop`, iterative-teardown explanations).

**Suggested fix:** Promote the doc comment to something the identifier can't already say:
- `text` → "Literal content that renders verbatim; never broken or re-indented."
- `nil` → "The identity element for `concat`; contributes no output and is dropped by `concat` and `concat_rc`."
- `line` → already improved if kept; the current wording is acceptable.
- `nest` → "Increase indentation by `indent` spaces when the enclosing group breaks; a no-op when the group fits on one line."

---

## slop-2

**File:** `crates/fltk-unparser-core/src/resolve.rs` — `resolve_spacing` vs. `mutate_after_sep_before`

**Quote (caller):**
```rust
// mutate_after_sep_before, line ~1210
let spacing = resolve_spacing(after, before, sep_spacing, preserved_trivia);
```

**Quote (callee):**
```rust
fn resolve_spacing(
    after: &Rc<Doc>,
    before: &Rc<Doc>,
    sep_spacing: &Option<Rc<Doc>>,
    sep_preserved_trivia: &Option<Rc<Doc>>,
) -> Option<Rc<Doc>> {
    if let Some(trivia) = sep_preserved_trivia {
        return Some(resolve_rc(trivia));
    }
    assert!(
        sep_spacing.is_some(),
        "Separator has neither preserved trivia nor spacing"
    );
    merge_spacing(Some(after), Some(before))
}
```

**What's wrong:** `resolve_spacing` asserts `sep_spacing.is_some()`, but the `required` field of `SeparatorSpec` is not passed in and not consulted. The two 2-element sibling patterns (`mutate_after_sep`, `mutate_sep_before`) both guard with `sep_spacing.is_some() || *required` and call `pick_spacing_with_blank_lines` which gracefully handles `spacing=None`; the 3-element pattern delegates to `resolve_spacing` which panics for `SeparatorSpec { required: true, spacing: None, preserved_trivia: None }`. The asymmetry is visible entirely within the diff.

**Consequence:** A `SeparatorSpec` with `required=true` and no explicit spacing that is flanked by both an `AfterSpec` and a `BeforeSpec` reaches `resolve_spacing` and panics rather than falling through to the `merge_spacing(after, before)` call that is the natural result. Whether this combination can appear in generated output is not visible in the diff, but the 2-element patterns demonstrably defend against it while the 3-element one does not. A reviewer cannot tell whether the assert is a correct invariant or a latent crash.

**Suggested fix:** Either pass `required` into `resolve_spacing` and guard identically to the 2-element patterns (`if sep_spacing.is_none() && !required { return None; }`), or add a comment to `mutate_after_sep_before` documenting why `required=true, spacing=None` is unreachable in that specific position. As-is the assert fires opaquely and the asymmetry invites doubt.
