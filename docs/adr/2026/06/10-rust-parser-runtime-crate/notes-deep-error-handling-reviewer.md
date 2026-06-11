# Error-handling review: fltk-parser-core (commit 1521372)

Style: concise, precise, complete. Audience: smart LLM/human. No padding.

---

## errhandling-1

**File:** `crates/fltk-parser-core/src/memo.rs:115–121`

**Path:** `apply` → growth-cycle branch → `!has_cache_entry && !is_head_or_involved` → fall-through to `assert!(has_cache_entry)`

The control flow has a logic error in the invariant-enforcement sequence. When `has_cache_entry == false` and `is_head_or_involved == true`, the code falls through the `if !has_cache_entry && !is_head_or_involved` guard (which doesn't fire) and then immediately `assert!(has_cache_entry)` — which panics. This is fine *in intent* (the assert is the correct failure), but the preceding `panic!` for the untested corner case fires only when *both* conditions are false. The problem: when `!has_cache_entry && is_head_or_involved` (cache miss but rule is head/involved), execution falls out of the panic guard, hits the assert, and panics with the generic invariant message rather than the documented untested-corner-case message. These two distinct conditions produce indistinguishable panics for on-call. Not a correctness bug — both correctly crash — but the wrong message fires for the `is_head_or_involved && !has_cache_entry` subcase, making it harder to distinguish "the untested algorithm path fired" from "cache was corrupted".

**Consequence:** On-call sees `"memo invariant: cache entry must exist during growth cycle"` for a condition that is actually the Python memo.py:181 untested corner case. The meaningful diagnostic ("Untested corner case; see source code for more information") is lost. Post-mortem analysis is harder.

**Fix:** Replace the two-step sequence with a single explicit three-way dispatch:
```rust
if !has_cache_entry && !is_head_or_involved {
    panic!("Untested corner case; see source code for more information.");
}
if !has_cache_entry {
    // has_cache_entry == false, is_head_or_involved == true:
    // also untested, or a distinct invariant violation — panic with distinct message
    panic!("memo invariant: growth-cycle rule is head/involved but has no cache entry");
}
```

---

## errhandling-2

**File:** `crates/fltk-parser-core/src/memo.rs:309–341` (`grow_seed`)

**Path:** `grow_seed` → loop body → `entry.result = MemoResult::Value(call_result.unwrap().result)` (line 341)

`call_result.unwrap()` is called after a branch that only breaks when `!has_result || new_pos <= entry.final_pos`. When `has_result == true` and `new_pos > entry.final_pos`, `call_result` is `Some(...)` and the `unwrap` succeeds. This is therefore not a false-panic risk. However, the `unwrap` appears in a non-trivial control flow path with no comment explaining why it cannot be `None`, and a future refactor that changes the break condition would introduce a hidden panic. Low risk now, but the intent should be stated explicitly.

**Consequence:** Not currently reachable as a panic. Risk is forward-maintenance: if the break condition is relaxed, `unwrap()` silently becomes reachable on a `None`.

**Fix:** Replace with `unwrap_or_else(|| unreachable!("grow_seed: call_result is None but loop did not break"))` or restructure to destructure `call_result` only in the `has_result && new_pos > entry.final_pos` arm directly.

---

## errhandling-3

**File:** `crates/fltk-parser-core/src/terminalsrc.rs:181–196` (`pos_to_line_col` → `line_ends` init closure)

**Path:** `get_or_init` closure → `partition_point` to convert newline byte offsets to codepoint indices

The closure maps newline byte positions to codepoint indices using `self.cp_to_byte.partition_point(|&b| b < byte_idx)`. This is correct only when `byte_idx` is a valid UTF-8 char boundary that appears in `cp_to_byte`. Newline (`\n`) is a single-byte ASCII character, so its byte index from `char_indices()` is always a char boundary, and the search will always hit an exact entry. This is safe in the current code. However, unlike the `consume_regex` path (which has a `debug_assert` validating the exact-hit invariant at line 151–154), this path has no such assertion. A future change that introduces non-newline sentinel characters could silently compute a wrong codepoint index without any diagnostic.

**Consequence:** Not currently reachable as a silent corruption. Risk: if the sentinel character ever changes to a multibyte character, line/col values would be silently wrong with no assertion to catch it. On-call would see wrong error positions with no indication of the cause.

**Fix:** Add a `debug_assert!(self.cp_to_byte.get(self.cp_to_byte.partition_point(|&b| b < byte_idx)) == Some(&byte_idx), ...)` mirror of the one in `consume_regex`. Minimal cost, consistent invariant documentation.

---

No findings for: `errors.rs` (all error paths handled; fallback on unreachable `pos_to_line_col` returns `None` is logged via the output message; `unwrap_or_default` on `line_span.text()` is correct and documented); `terminalsrc.rs` `consume_literal`/`consume_regex` (bounds checked before every `as usize` cast); `memo.rs` `setup_recursion` (all `unwrap` calls are on keys just confirmed present; panics documented as invariant violations).
