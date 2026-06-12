Style: concise, precise, complete, unambiguous. No padding, no preamble.

Commit reviewed: 8da7924

## quality-1

**File:line:** `crates/fltk-parser-core/src/errors.rs:152-155`

**Issue:** `format_error_message` collects `line_text` into a `Vec<char>` solely to split at a codepoint index, then immediately reconstructs two `String`s from the halves. This is an unnecessarily indirect pattern: `char_indices` yields `(byte_offset, char)` pairs and would give the byte position of the split point in one pass, allowing a direct `&str` slice (`&line_text[..byte_offset]` / `&line_text[byte_offset..]`) that feeds `escape_control_chars` with zero intermediate allocations.

```rust
// current: three allocations
let chars: Vec<char> = line_text.chars().collect();
let split_clamped = split.min(chars.len());
let prefix: String = chars[..split_clamped].iter().collect();
let suffix: String = chars[split_clamped..].iter().collect();
```

**Consequence:** Three heap allocations (Vec, prefix String, suffix String) where one `char_indices` scan suffices. More critically, the pattern has a non-obvious correctness dependency: `split` is a codepoint index (documented in `terminalsrc.rs`), but the comment "split is a codepoint index; collect chars to slice safely" is the only thing preventing a future maintainer from simplifying to a direct byte-index slice, which would be UB-adjacent (byte mid-codepoint panic) on multibyte input. The indirect pattern obscures the invariant that matters.

**Fix:** Replace with a `char_indices`-based byte-offset search:

```rust
let split_bytes = line_text
    .char_indices()
    .nth(split)
    .map(|(b, _)| b)
    .unwrap_or(line_text.len());
let escaped_prefix = escape_control_chars(&line_text[..split_bytes]);
let escaped_suffix = escape_control_chars(&line_text[split_bytes..]);
```

`nth(split)` returns `None` when `split >= char_count` (mirrors `split.min(chars.len())`), in which case `unwrap_or(line_text.len())` gives an empty suffix. The invariant (`split` is a codepoint index) is explicit at the call site and no intermediate collection hides it.

---

## quality-2

**File:line:** `crates/fltk-parser-core/src/errors.rs:93`

**Issue:** `escape_control_chars` uses `out.push_str(&format!("\\x{:02x}", cp))` inside the per-character loop, allocating a temporary `String` per escaped character.

**Consequence:** Every escaped character in any input causes a heap allocation. `escape_control_chars` is public API (`pub use` in `lib.rs`) and its doc comment flags it as reusable ("safe for reuse"); the allocation-per-escape cost will propagate to all future callers. The project already uses `use std::fmt::Write` in adjacent code (`py_repr_str` at line 235 has the same pattern, so this is a copy-forward of a pre-existing issue into new public API). For the current call sites (error-reporting paths) this is harmless, but publishing a function that allocates per escaped character when `write!` is free is a latent maintenance cost — the function teaches callers the allocation is unavoidable.

**Fix:** Add `use std::fmt::Write;` at the top of the function or module and replace with:

```rust
write!(out, "\\x{:02x}", cp).unwrap();
```

`String`'s `Write` impl is infallible; the `.unwrap()` is a formality and will be compiled away. Apply the same fix to `py_repr_str` line 235 while here — both functions have the same pattern.

---

No other findings.
