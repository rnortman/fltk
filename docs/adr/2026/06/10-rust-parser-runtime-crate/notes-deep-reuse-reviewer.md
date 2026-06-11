Style note: concise, precise, complete, unambiguous. Audience: smart LLM/human. No padding.

Commit reviewed: 1521372a8313ad9c61503e43db9d98cd23c8c1a0

---

reuse-1: Redundant byte-offset `char_indices` scan inside `line_ends` lazy initialiser vs the `cp_to_byte` table that already encodes the same information.

File:line: `crates/fltk-parser-core/src/terminalsrc.rs:184-190`

Duplicated: the `line_ends` initialiser calls `text.char_indices()` to get byte offsets of `\n` characters, then immediately calls `self.cp_to_byte.partition_point(|&b| b < byte_idx)` to convert each byte offset back to a codepoint index. `cp_to_byte[i] == byte_idx` for all valid `i`, so the reverse lookup is equivalent to iterating `cp_to_byte.iter().enumerate().filter(|(_, &b)| ...)`. The existing `cp_to_byte` table is the canonical byte→codepoint mapping already in hand; a direct enumeration replaces both the `char_indices` call and the binary search.

Existing utility: `self.cp_to_byte` built at `TerminalSource::from_source_text` (terminalsrc.rs:57-63). The forward direction `cp_to_byte[i]` → byte offset is used throughout; the reverse direction (byte → codepoint) is what `partition_point` computes. An explicit enumerate loop over `cp_to_byte` avoids the dual scan.

Consequence: as written the initialiser scans `text` once via `char_indices` and then does a binary search per `\n` into `cp_to_byte`. Replacing it with a single enumeration of `cp_to_byte` would remove the redundant `text` scan entirely. The duplication is localised to one `OnceLock::get_or_init` closure; if the representation of `cp_to_byte` ever changes (e.g., `u32` offsets as noted in the memory comment on line 41), the `char_indices`-based path would need an independent update and could silently diverge.

---

No other findings. The `Span::text()` linear scan in `fltk-cst-core/src/span.rs:289-319` and the `cp_to_byte` table in `terminalsrc.rs` both solve codepoint→byte translation, but cannot share code: `Span` has no cached table and `TerminalSource` cannot expose its table through `Span`. The duplication is structural — two different ownership models — not actionable reuse. The `build_expected_block` grouping pattern in `errors.rs:134-167` (Vec for order + HashMap for membership) has no existing equivalent in the codebase to reuse.
