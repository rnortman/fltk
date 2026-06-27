# Dispositions — prepass review (slop + scope), base 61fc5e8..ff7d198

Commit applying fixes: 1b48755794ecca64a81f799fc91550904ea0970c

## slop-1
- Disposition: Fixed
- Action: Rewrote the `char_index_not_byte_index` test in
  `crates/fltk-fmt-cli/src/lib.rs:87-108`. Removed the vacuously-true
  `assert!(fully_consumed(src, byte_len))` (byte_len=9 on a 7-char string skips to
  an empty iterator, so `all(is_whitespace)` is trivially true and the char-vs-byte
  distinction was never actually demonstrated). Replaced the corpus with
  `src = "éx  "` (4 chars, 5 bytes): the parser stop point "consumed é" is char
  index 1 (remainder `"x  "` contains non-whitespace ⇒ `fully_consumed` returns
  false, a genuine partial parse) versus byte offset 2 (in bounds; remainder `"  "`
  is whitespace-only ⇒ returns true). This is a non-vacuous divergent verdict for
  the same stop point, and every assertion now tests correct function behavior while
  the comment explains why callers must pass char indices, not byte offsets. Crate
  tests (10 passed) and `cargo clippy -- -D warnings` are clean.
- Severity assessment: Low. Test-only readability/clarity issue; the finding is
  accurate that the prior assertion was vacuous and misleading to a reader, but the
  shipped `fully_consumed` behavior was correct either way.

## Scope notes
- `notes-prepass-scope.md` recorded "No findings." Nothing to disposition.
