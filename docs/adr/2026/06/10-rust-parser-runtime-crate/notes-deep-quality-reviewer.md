Reviewed commit: 1521372 (base: d23d1df)

quality-1
File: crates/fltk-parser-core/src/errors.rs:117
The "Syntax error at unknown position" fallback path calls `build_expected_block` and interpolates the result directly without prepending `"Expected:\n"`:
```
return format!("Syntax error at unknown position\n{expected_block}");
```
The normal path at line 123 includes `"Expected:\n"` in the format string before calling `build_expected_block`. The function docstring (line 133) says it builds `"Expected:\n  From rule..."` but the function body does NOT include the `"Expected:\n"` header — it only builds the `"  From rule..."` lines. The docstring is false and the fallback path silently omits the header.
Consequence: two divergent output formats between the reachable and "unreachable" paths; if the invariant breaks (e.g., in a future caller that doesn't hold `longest_parse_len ∈ [-1, len]`), the difference won't be noticed because the "unreachable" path has no test and its output format diverges silently. Fix: either include `"Expected:\n"` inside `build_expected_block` (rename to `build_expected_section`) and remove it from the format string in the normal path, or add it to the fallback `format!`.

quality-2
File: crates/fltk-parser-core/src/memo.rs:261
`setup_recursion` has a dead parameter `_existing_ri: Option<RecursionInfo>`. The caller (lines 166–170) extracts the `Option<RecursionInfo>` from the cache entry to drop the borrow, then passes it to `setup_recursion` which ignores it entirely (underscore prefix, never read). The function re-reads the cache entry itself at line 278.
Consequence: every future call site of `setup_recursion` must supply a dead argument, and the pattern of "extract a value purely to satisfy a parameter that's never used" will propagate to any refactor or new call site. Fix: remove `_existing_ri` from the signature. The caller already drops the borrow by letting the match result fall out of scope before line 170; the extract-and-pass pattern adds no value.

quality-3
File: crates/fltk-parser-core/src/terminalsrc.rs:183–191
The `line_ends` `OnceLock` initializer uses `char_indices()` (yields `(byte_offset, char)`) then binary-searches `cp_to_byte` to convert each `\n`'s byte offset back to a codepoint index:
```rust
.map(|(byte_idx, _)| {
    self.cp_to_byte.partition_point(|&b| b < byte_idx) as i64
})
```
This is a roundabout path: `char_indices` discards the codepoint index, then binary search reconstructs it. `chars().enumerate()` yields `(codepoint_index, char)` directly, eliminating both the `char_indices` byte-offset output and the per-newline `O(log n)` binary search:
```rust
let mut ends: Vec<i64> = text
    .chars()
    .enumerate()
    .filter(|(_, c)| *c == '\n')
    .map(|(i, _)| i as i64)
    .collect();
```
Consequence: the current code is harder to read (binary search inside a map inside a filter, requiring the `cp_to_byte` borrow inside the closure) and slower for inputs with many newlines. The unnecessary complexity will mislead maintainers into thinking a binary search is load-bearing here.

quality-4
File: crates/fltk-parser-core/src/errors.rs:137–138
`build_expected_block` uses a fully-qualified `std::collections::HashMap` path instead of a `use` import, while `memo.rs` (line 13) does `use std::collections::{HashMap, HashSet}`. The rest of the crate uses the import style; this single `HashMap` usage is inconsistent.
Consequence: minor inconsistency that signals the function was assembled separately; adds visual noise in a function already doing non-trivial grouping logic. Fix: add `use std::collections::HashMap;` at the top of `errors.rs`.
