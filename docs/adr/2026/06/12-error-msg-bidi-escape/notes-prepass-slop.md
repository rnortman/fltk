## slop-1

**File:** `tests/test_pyrt_errors.py` — `test_escape_mixed_xhh_and_uxxxx`, second assertion (diff line ~714)

**Quote:**
```python
assert escape_control_chars("‎\tabc") == "\\x80\\u200e\tabc"
```

**What's wrong:** The comment says the input is "C1 (\x80) + LRM (bidi mark) + TAB + plain text", but the visible Python literal is `"‎\tabc"` — U+200E (LRM) followed by TAB and ASCII. There is no `\x80` byte in that input. `escape_control_chars("‎\tabc")` should produce `"\\u200e\tabc"`, not `"\\x80\\u200e\tabc"`. Either the test literal is wrong (missing the `\x80` prefix character) or the expected string is wrong. The test will fail or silently pass against incorrect behavior depending on which side is broken.

**Consequence:** A mismatched input/expected pair in the cross-backend pin test — either the test is always failing (blocked CI) or the input actually does contain `\x80` but the diff rendering obscures it (C1 byte displayed as a non-printing glyph that looks like nothing). Either way, a reviewer cannot verify correctness from the diff alone, which is exactly the thing a cross-pin test is supposed to guarantee.

**Suggested fix:** Make both the input and expected string unambiguous. If the intent is `\x80` + LRM + TAB + text:
```python
assert escape_control_chars("\x80‎\tabc") == "\\x80\\u200e\tabc"
```
Use only ASCII-safe Python escape sequences in test literals (no raw non-printing codepoints) so the diff is always readable.

---

## slop-2

**File:** `crates/fltk-cst-core/src/lib.rs` (diff lines ~351-354)

**Quote:**
```rust
pub mod escape;
```

**What's wrong:** `needs_escape` is a private `fn` inside `escape.rs`, so that's fine — but `pub mod escape` makes the entire module, including its public items, part of the crate's public API surface. The callers (`cross_cdylib.rs`, `fltk-parser-core`) only need `escape_control_chars`. Exposing the module publicly is broader than necessary and is observable by downstream crate consumers who import `fltk_cst_core`.

**Consequence:** Minor API surface leak. If `needs_escape` is ever made `pub` for testing convenience, or if new items are added to the module, they silently become public crate API. Not blocking, but worth a comment or `pub(crate)`.

**Suggested fix:** Change to `pub(crate) mod escape;` and add a re-export at crate root if `fltk-parser-core`'s `pub use fltk_cst_core::escape::escape_control_chars` requires it (it does — change the re-export to `pub use fltk_cst_core::escape::escape_control_chars;` which still works with `pub(crate) mod` because the function itself is `pub fn`). Actually `pub use` of a `pub fn` from a `pub(crate)` module works fine from an external crate — the item is reachable via the re-export even if the module is not. So `pub(crate) mod escape;` is safe.
