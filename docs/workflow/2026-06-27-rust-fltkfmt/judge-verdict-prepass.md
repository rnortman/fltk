# Judge verdict — prepass (slop + scope)

Phase: prepass. Base 61fc5e8..HEAD 1b48755. Round 1.
Notes: 2 reviewer files (slop, scope); 1 finding total.

## Added TODOs walk

No TODO-dispositioned findings, and `git diff 61fc5e8..1b48755 | grep '+.*TODO'`
returns nothing — no TODO comments added by this change. Nothing to score.

## Other findings walk

### slop-1 — Fixed
Claim: in `char_index_not_byte_index` (`crates/fltk-fmt-cli/src/lib.rs`), the final
`assert!(fully_consumed(src, byte_len))` passed *vacuously* — `byte_len=9` on a
7-char string makes `chars().skip(9)` an empty iterator, so `all(is_whitespace)` is
trivially true. Consequence: the assertion documents a footgun as if it validated
correct behavior, and the char-vs-byte distinction the test name promises was never
actually demonstrated (both 7 and 9 return true, for different reasons).

Inspection of the fix (`lib.rs:87-109`, fix commit 1b48755):
- New corpus `src = "éx  "` — 4 chars, 5 bytes (asserted at `:92-93`).
- `fully_consumed(src, 1)` → skips 1 char, remainder `"x  "` contains non-whitespace
  → `false`; `assert!(!fully_consumed(src, 1))` at `:97`. Genuine partial parse at the
  correct char index for the "consumed é" stop point.
- `fully_consumed(src, 2)` → byte offset of the *same* stop point; in-bounds as a char
  index (4 chars), skips 2 chars, remainder `"  "` is whitespace-only → `true`;
  `assert!(fully_consumed(src, 2))` at `:105`. Non-vacuous: the scan runs over a
  non-empty suffix and returns the *wrong* "consumed" verdict, which is the footgun.
- `fully_consumed(src, 4)` sanity at `:108`.

`fully_consumed` (`lib.rs:54-59`) interprets its argument as a char index
(`chars().skip(pos)`), so the byte-vs-char conflation at the same stop point yielding
divergent verdicts (`false` vs `true`) is exactly the distinction the test name
promised. The vacuous assertion is gone; every assertion now tests real behavior.
Ran `cargo test char_index_not_byte_index` — passes.

Assessment: fix addresses the consequence at the named location, non-vacuously, and
matches the reviewer's own suggested remedy (a partial-parse case where byte and char
interpretations diverge). Accept.

### Scope notes
`notes-prepass-scope.md` recorded "No findings." Confirmed nothing to disposition.

## Approved

1 finding: 1 Fixed verified (slop-1). Scope: no findings.

---

## Verdict: APPROVED

The single finding (slop-1) is correctly Fixed; the reworked test is non-vacuous and
demonstrates the char-vs-byte divergence as claimed. No added TODOs. Scope reviewer
raised nothing.
